# pdf_handler.py
import os
import tempfile
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.errors import PdfReadError
from reportlab.pdfgen import canvas
from io import BytesIO
from typing import List, Dict, Any, Tuple, Optional
from models import PDFFileItem, EncryptionStatus
from PySide6.QtCore import QObject, Signal
from file_namer import get_unique_filename
from logger import logger
import pikepdf
from pikepdf import Name, Dictionary
from pdf_utils import register_font_safely
from font_manager import suggest_chinese_fallback_font

class WorkerSignals(QObject):
    progress = Signal(int, int, str)

def _apply_overlay(page, text: str, font_name: str, font_size: int, x: float, y: float):
    """在内存中创建一个包含文本的图层并应用到给定的页面对象上。"""
    try:
        packet = BytesIO()
        # 使用当前页尺寸而不是固定 letter
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)
        can = canvas.Canvas(packet, pagesize=(page_width, page_height))

        if register_font_safely(font_name):
            can.setFont(font_name, font_size)
        else:
            fallback_font = "Helvetica"  # More common fallback
            logger.warning(f"Font '{font_name}' not found or failed to register, falling back to {fallback_font}.")
            can.setFont(fallback_font, font_size)

        can.drawString(x, y, text)
        can.save()

        packet.seek(0)
        overlay_pdf = PdfReader(packet)
        page.merge_page(overlay_pdf.pages[0])
    except Exception as e:
        logger.error(f"Failed to apply text overlay: '{text}'. Error: {e}", exc_info=True)

def _is_ascii(text: str) -> bool:
    try:
        text.encode("ascii")
        return True
    except Exception:
        return False

def _escape_pdf_text(text: str) -> str:
    """Escape backslashes and parentheses for PDF literal strings."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

_BASE14_MAP = {
    "Helvetica": "/Helvetica",
    "Arial": "/Helvetica",
    "Times": "/Times-Roman",
    "Times New Roman": "/Times-Roman",
    "Courier": "/Courier",
}

def _map_to_base14(font_name: Optional[str]) -> str:
    if not font_name:
        return "/Helvetica"
    # 粗略匹配常见名
    for key, base in _BASE14_MAP.items():
        if font_name.lower().startswith(key.lower()):
            return base
    return "/Helvetica"

def _ensure_base_font_resource(pdf: pikepdf.Pdf, page: pikepdf.Page, font_key: str = "/F1", base_font: str = "/Helvetica"):
    page_dict = page.obj
    resources = page_dict.get(Name('/Resources'))
    if resources is None:
        resources = Dictionary()
        page_dict[Name('/Resources')] = resources
    fonts = resources.get(Name('/Font'))
    if fonts is None:
        fonts = Dictionary()
        resources[Name('/Font')] = fonts
    if Name(font_key) not in fonts:
        font_dict = Dictionary({
            Name('/Type'): Name('/Font'),
            Name('/Subtype'): Name('/Type1'),
            Name('/BaseFont'): Name(base_font),
        })
        fonts[Name(font_key)] = pdf.make_indirect(font_dict)

def _add_marked_text(pdf: pikepdf.Pdf, page: pikepdf.Page, text: str, font_size: int, x: float, y: float, subtype: str = 'Header', base_font: Optional[str] = None):
    """将 ASCII 文本作为带 Artifact 的分页工件写入页面内容流。"""
    base = base_font or "/Helvetica"
    _ensure_base_font_resource(pdf, page, font_key='/F1', base_font=base)
    # 设置 MarkInfo.Marked = true
    root = pdf.root
    markinfo = root.get(Name('/MarkInfo'))
    if markinfo is None:
        root[Name('/MarkInfo')] = Dictionary({Name('/Marked'): True})
    else:
        markinfo[Name('/Marked')] = True
    escaped = _escape_pdf_text(text)
    # 使用 Tm 设置绝对位置矩阵，随后写入文本，包裹在 Artifact 标记内
    content = f"/Artifact << /Type /Pagination /Subtype /{subtype} >> BDC BT /F1 {font_size} Tf 1 0 0 1 {x} {y} Tm ({escaped}) Tj ET EMC\n"
    try:
        page.add_content(content)
    except AttributeError:
        # 旧版本兜底：直接在 Contents 末尾追加一个新流
        new_stream = pikepdf.Stream(pdf, content.encode('latin-1'))
        contents = page.obj.get(Name('/Contents'))
        if contents is None:
            page.obj[Name('/Contents')] = pdf.make_indirect(new_stream)
        elif isinstance(contents, pikepdf.Array):
            contents.append(pdf.make_indirect(new_stream))
        else:
            page.obj[Name('/Contents')] = pikepdf.Array([contents, pdf.make_indirect(new_stream)])

# === Structured Chinese (non-ASCII) via Form XObject ===

def _build_overlay_pdf_bytes(page_width: float, page_height: float, text: str, font_name: str, font_size: int, x: float, y: float) -> bytes:
    """用 ReportLab 生成一页 PDF（含嵌入字体），返回字节，用于作为 Form XObject 导入。"""
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))
    
    # 改进的字体处理
    if register_font_safely(font_name):
        can.setFont(font_name, font_size)
    else:
        # 尝试常见的中文字体
        chinese_fonts = ["SimSun", "SimHei", "Microsoft YaHei", "PingFang SC", "STSong", "STHeiti"]
        font_found = False
        for chinese_font in chinese_fonts:
            if register_font_safely(chinese_font):
                can.setFont(chinese_font, font_size)
                font_found = True
                logger.info(f"[Structured CN] Using fallback Chinese font: {chinese_font}")
                break
        
        if not font_found:
            fallback_font = "Helvetica"
            logger.warning(f"[Structured CN] No Chinese fonts found, fallback to {fallback_font}.")
            can.setFont(fallback_font, font_size)
    
    can.drawString(x, y, text)
    can.save()
    return packet.getvalue()

def _add_marked_form_overlay(pdf: pikepdf.Pdf, page: pikepdf.Page, overlay_pdf_bytes: bytes, subtype: str, bbox_w: float, bbox_h: float):
    """将 overlay PDF 的第一页作为 Form XObject 注入目标页面，并用 Artifact 包裹。"""
    try:
        src_pdf = pikepdf.open(BytesIO(overlay_pdf_bytes))
        src_page = src_pdf.pages[0]
        # 拷贝资源到当前文档
        resources = src_page.obj.get(Name('/Resources'))
        if resources is not None:
            resources = pdf.copy_foreign(resources)
        # 合并内容流
        contents = src_page.obj.get(Name('/Contents'))
        if isinstance(contents, pikepdf.Array):
            content_bytes = b"".join([c.read_bytes() for c in contents])
        elif isinstance(contents, pikepdf.Stream):
            content_bytes = contents.read_bytes()
        else:
            content_bytes = b""
        xobj_stream = pikepdf.Stream(pdf, content_bytes, dict={
            Name('/Type'): Name('/XObject'),
            Name('/Subtype'): Name('/Form'),
            Name('/BBox'): pikepdf.Array([0, 0, bbox_w, bbox_h]),
        })
        if resources is not None:
            xobj_stream[Name('/Resources')] = resources
        xobj_ref = pdf.make_indirect(xobj_stream)
        # 注册到页面资源
        page_res = page.obj.get(Name('/Resources'))
        if page_res is None:
            page_res = Dictionary()
            page.obj[Name('/Resources')] = page_res
        xobjs = page_res.get(Name('/XObject'))
        if xobjs is None:
            xobjs = Dictionary()
            page_res[Name('/XObject')] = xobjs
        # 生成唯一名称
        idx = 1
        name = f"FmHF{idx}"
        while Name(f"/{name}") in xobjs:
            idx += 1
            name = f"FmHF{idx}"
        xobjs[Name(f"/{name}")] = xobj_ref
        # 写入内容，包裹 Artifact
        content = f"/Artifact << /Type /Pagination /Subtype /{subtype} >> BDC q 1 0 0 1 0 0 cm /{name} Do Q EMC\n"
        page.add_content(content)
    except Exception as e:
        logger.error(f"[Structured CN] Failed to add form overlay: {e}")

# === Page normalization to A4 ===
A4_PORTRAIT = (595.0, 842.0)
A4_LANDSCAPE = (842.0, 595.0)

def _get_page_box(page: pikepdf.Page, name: str):
    box = page.obj.get(Name(f'/{name}'))
    return box if (box is not None and len(box) == 4) else None

def _normalize_page_to_a4(page: pikepdf.Page):
    """
    重构的A4规范化函数：更智能的方向识别和内容处理
    """
    try:
        # 获取页面尺寸信息
        crop = _get_page_box(page, 'CropBox')
        mb = _get_page_box(page, 'MediaBox')
        box = crop or mb
        
        if not box:
            logger.warning("无法获取页面尺寸信息")
            return
            
        # 计算实际内容尺寸
        width = float(box[2] - box[0])
        height = float(box[3] - box[1])
        
        # 获取旋转信息
        rotate = int(page.obj.get(Name('/Rotate'), 0)) % 360
        
        # 智能方向判断：考虑旋转后的实际显示方向
        if rotate in (90, 270):
            # 旋转90/270度时，交换宽高
            display_width = height
            display_height = width
        else:
            display_width = width
            display_height = height
            
        # 判断是否为纵向（高度大于宽度）
        is_portrait = display_height > display_width
        
        # 选择目标A4尺寸
        if is_portrait:
            target_width, target_height = A4_PORTRAIT
        else:
            target_width, target_height = A4_LANDSCAPE
            
        # 计算缩放比例（保持宽高比）
        scale_x = target_width / display_width
        scale_y = target_height / display_height
        scale = min(scale_x, scale_y)  # 取较小值，确保内容完全适应
        
        # 计算居中偏移
        scaled_width = display_width * scale
        scaled_height = display_height * scale
        offset_x = (target_width - scaled_width) / 2.0
        offset_y = (target_height - scaled_height) / 2.0
        
        # 构建变换矩阵
        # 先应用旋转，再缩放，最后平移
        if rotate == 0:
            transform_matrix = f"q {scale:.6f} 0 0 {scale:.6f} {offset_x:.6f} {offset_y:.6f} cm\n"
        elif rotate == 90:
            transform_matrix = f"q 0 {scale:.6f} {-scale:.6f} 0 {target_width - offset_y:.6f} {offset_x:.6f} cm\n"
        elif rotate == 180:
            transform_matrix = f"q {-scale:.6f} 0 0 {-scale:.6f} {target_width - offset_x:.6f} {target_height - offset_y:.6f} cm\n"
        elif rotate == 270:
            transform_matrix = f"q 0 {-scale:.6f} {scale:.6f} 0 {offset_y:.6f} {target_height - offset_x:.6f} cm\n"
        else:
            # 其他角度，使用通用变换
            transform_matrix = f"q {scale:.6f} 0 0 {scale:.6f} {offset_x:.6f} {offset_y:.6f} cm\n"
            
        # 应用变换到页面内容
        try:
            # 获取现有内容流
            contents = page.obj.get(Name('/Contents'))
            
            # 创建新的内容流
            new_contents = f"{transform_matrix}"
            
            if contents is not None:
                # 如果有现有内容，将其包装在变换中
                if isinstance(contents, pikepdf.Array):
                    # 多个内容流
                    for content in contents:
                        new_contents += f"q\n{content.read_bytes().decode('latin-1', errors='ignore')}\nQ\n"
                else:
                    # 单个内容流
                    new_contents += f"q\n{contents.read_bytes().decode('latin-1', errors='ignore')}\nQ\n"
            else:
                # 没有内容，添加空白页面
                new_contents += "0 0 m 0 0 l s\n"
                
            new_contents += "Q\n"  # 结束变换
            
            # 创建新的内容流对象
            new_stream = pikepdf.Stream(page.obj.pdf, new_contents.encode('latin-1'))
            page.obj[Name('/Contents')] = page.obj.pdf.make_indirect(new_stream)
            
        except Exception as content_error:
            logger.warning(f"内容流处理失败: {content_error}")
            # 如果内容流处理失败，至少设置尺寸
            
        # 更新页面尺寸
        new_box = pikepdf.Array([0, 0, target_width, target_height])
        page.obj[Name('/MediaBox')] = new_box
        page.obj[Name('/CropBox')] = new_box
        
        # 清除旋转信息（因为已经通过变换矩阵处理）
        if page.obj.get(Name('/Rotate')) is not None:
            page.obj[Name('/Rotate')] = 0
            
        logger.info(f"页面A4规范化成功: {width:.1f}x{height:.1f} -> {target_width:.1f}x{target_height:.1f}, 旋转: {rotate}°")
        
    except Exception as e:
        logger.warning(f"Normalize page to A4 failed: {str(e)}")
        # 回退：至少设置A4尺寸
        try:
            new_box = pikepdf.Array([0, 0, A4_PORTRAIT[0], A4_PORTRAIT[1]])
            page.obj[Name('/MediaBox')] = new_box
            page.obj[Name('/CropBox')] = new_box
            logger.info("已设置回退A4尺寸")
        except Exception as fallback_error:
            logger.error(f"回退设置也失败: {fallback_error}")

def _normalize_pdf_file_to_a4(input_path: str) -> str:
    """将整份 PDF 正规化为 A4，返回临时文件路径。"""
    try:
        with pikepdf.open(input_path) as pdf:
            for page in pdf.pages:
                _normalize_page_to_a4(page)
            tmp = tempfile.NamedTemporaryFile(prefix="docdeck_a4_", suffix=".pdf", delete=False)
            tmp_path = tmp.name
            tmp.close()
            pdf.save(tmp_path)
            return tmp_path
    except Exception as e:
        logger.warning(f"Normalize PDF failed for {input_path}: {e}")
        return input_path

def _process_single_file_with_overlay(item: PDFFileItem, output_dir: str, header_settings: Dict[str, Any], footer_settings: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """复用现有 PyPDF2+ReportLab 覆盖路径处理单文件。返回 (success, output_path, error)."""
    temp_to_cleanup = None
    try:
        source_path = item.path
        if header_settings.get("normalize_a4") or footer_settings.get("normalize_a4"):
            source_path = _normalize_pdf_file_to_a4(source_path)
            if source_path != item.path:
                temp_to_cleanup = source_path
        reader = PdfReader(source_path)
        item.page_count = len(reader.pages)
        item.encryption_status = EncryptionStatus.LOCKED if reader.is_encrypted else EncryptionStatus.OK
        if reader.is_encrypted:
            raise PdfReadError("File is encrypted. Please unlock it first.")
        writer = PdfWriter()
        page_total = len(reader.pages)
        for i, page in enumerate(reader.pages):
            if item.header_text:
                _apply_overlay(
                    page, item.header_text,
                    header_settings.get("font_name"), header_settings.get("font_size"),
                    header_settings.get("x"), header_settings.get("y")
                )
            if item.footer_text:
                footer_text = item.footer_text.format(page=i + 1, total=page_total)
                _apply_overlay(
                    page, footer_text,
                    footer_settings.get("font_name"), footer_settings.get("font_size"),
                    footer_settings.get("x"), footer_settings.get("y")
                )
            writer.add_page(page)
        output_name = get_unique_filename(output_dir, f"{os.path.splitext(item.name)[0]}_processed.pdf")
        output_path = os.path.join(output_dir, output_name)
        with open(output_path, "wb") as f:
            writer.write(f)
        return True, output_path, None
    except Exception as e:
        return False, None, str(e)
    finally:
        if temp_to_cleanup and os.path.exists(temp_to_cleanup):
            try:
                os.remove(temp_to_cleanup)
            except Exception:
                pass

def process_pdfs_in_batch(
    file_infos: List[PDFFileItem],
    output_dir: str,
    header_settings: Dict[str, Any],
    footer_settings: Dict[str, Any],
    signals: WorkerSignals = None
) -> List[Dict[str, Any]]:
    """
    对一批PDF文件进行处理，添加页眉和/或页脚。
    当 header_settings/footer_settings 中包含 structured=True 时，优先尝试以 Artifact 方式写入；
    - ASCII 文本：直接写入文字（Base14 字体）
    - 非 ASCII（中文等）：将 ReportLab 生成的覆盖页作为 Form XObject 注入，并包裹 Artifact
    否则回退到覆盖方式。
    """
    results = []
    total_files = len(file_infos)
    structured = bool(header_settings.get("structured") or footer_settings.get("structured"))
    normalize_a4 = bool(header_settings.get("normalize_a4") or footer_settings.get("normalize_a4"))
    for idx, item in enumerate(file_infos):
        try:
            logger.info(f"Processing file {idx + 1}/{total_files}: {item.name}")
            if structured:
                with pikepdf.open(item.path) as pdf:
                    # 需要时先规范化到 A4
                    if normalize_a4:
                        for page in pdf.pages:
                            _normalize_page_to_a4(page)
                    page_total = len(pdf.pages)
                    header_base = _map_to_base14(header_settings.get("font_name"))
                    footer_base = _map_to_base14(footer_settings.get("font_name"))
                    for i, page in enumerate(pdf.pages):
                        w = float(page.obj.get(Name('/MediaBox'))[2])
                        h = float(page.obj.get(Name('/MediaBox'))[3])
                        if item.header_text:
                            if _is_ascii(item.header_text or ""):
                                _add_marked_text(
                                    pdf, page, item.header_text,
                                    int(header_settings.get("font_size", 9)),
                                    float(header_settings.get("x", 72)),
                                    float(header_settings.get("y", 752)),
                                    subtype='Header', base_font=header_base)
                            else:
                                cn_font = header_settings.get("structured_cn_font") if header_settings.get("structured_cn_fixed") else suggest_chinese_fallback_font(header_settings.get("font_name"))
                                ov_bytes = _build_overlay_pdf_bytes(w, h, item.header_text, cn_font, int(header_settings.get("font_size", 9)), float(header_settings.get("x", 72)), float(header_settings.get("y", 752)))
                                _add_marked_form_overlay(pdf, page, ov_bytes, 'Header', w, h)
                        if item.footer_text:
                            footer_text = (item.footer_text or "").format(page=i + 1, total=page_total)
                            if _is_ascii(footer_text):
                                _add_marked_text(
                                    pdf, page, footer_text,
                                    int(footer_settings.get("font_size", 9)),
                                    float(footer_settings.get("x", 72)),
                                    float(footer_settings.get("y", 40)),
                                    subtype='Footer', base_font=footer_base)
                            else:
                                cn_font_f = footer_settings.get("structured_cn_font") if footer_settings.get("structured_cn_fixed") else suggest_chinese_fallback_font(footer_settings.get("font_name"))
                                ov_bytes = _build_overlay_pdf_bytes(w, h, footer_text, cn_font_f, int(footer_settings.get("font_size", 9)), float(footer_settings.get("x", 72)), float(footer_settings.get("y", 40)))
                                _add_marked_form_overlay(pdf, page, ov_bytes, 'Footer', w, h)
                    output_name = get_unique_filename(output_dir, f"{os.path.splitext(item.name)[0]}_processed.pdf")
                    output_path = os.path.join(output_dir, output_name)
                    pdf.save(output_path)
                    results.append({"input": item.path, "output": output_path, "success": True, "error": None})
            else:
                # 回退：原有覆盖方式（支持中文）
                ok, output_path, err = _process_single_file_with_overlay(item, output_dir, header_settings | {"normalize_a4": normalize_a4}, footer_settings | {"normalize_a4": normalize_a4})
                if ok:
                    results.append({"input": item.path, "output": output_path, "success": True, "error": None})
                else:
                    raise Exception(err or "Unknown error in overlay path")

            if signals:
                signals.progress.emit(idx + 1, total_files, item.name)

        except (PdfReadError, Exception) as e:
            error_msg = str(e)
            logger.error(f"Failed to process: {item.name}. Reason: {error_msg}", exc_info=True)
            results.append({"input": item.path, "output": None, "success": False, "error": error_msg})
    
    return results

def process_pdfs_in_batch_with_memory_optimization(
    file_infos: List[PDFFileItem],
    output_dir: str,
    header_settings: Dict[str, Any],
    footer_settings: Dict[str, Any],
    signals: WorkerSignals = None,
    chunk_size: int = 10  # 每次处理10个文件
) -> List[Dict[str, Any]]:
    """
    带内存优化的大文件批处理版本
    """
    results = []
    total_files = len(file_infos)
    
    # 分块处理文件
    for i in range(0, total_files, chunk_size):
        chunk = file_infos[i:i + chunk_size]
        chunk_results = process_pdfs_in_batch(
            chunk, output_dir, header_settings, footer_settings, signals
        )
        results.extend(chunk_results)
        
        # 强制垃圾回收
        import gc
        gc.collect()
        
        # 报告进度
        if signals:
            progress = min(100, int((i + len(chunk)) / total_files * 100))
            signals.progress.emit(progress, total_files, f"处理中... ({i + len(chunk)}/{total_files})")
    
    return results

def _optimize_memory_for_large_pdf(input_path: str, max_memory_mb: int = 500) -> str:
    """
    为大PDF文件优化内存使用，必要时创建压缩版本
    """
    try:
        import os
        import fitz
        
        # 检查文件大小
        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        
        if file_size_mb <= max_memory_mb:
            return input_path  # 文件不大，直接返回
        
        # 文件过大，创建压缩版本
        doc = fitz.open(input_path)
        
        # 创建临时压缩文件
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf", prefix="docdeck_compressed_")
        os.close(temp_fd)
        
        # 压缩PDF（降低分辨率，移除不必要的元数据）
        doc.save(
            temp_path,
            garbage=4,  # 最大垃圾回收
            deflate=True,  # 使用deflate压缩
            clean=True,  # 清理元数据
            linear=True  # 线性化PDF
        )
        doc.close()
        
        logger.info(f"大文件 {input_path} ({file_size_mb:.1f}MB) 已压缩到 {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.warning(f"PDF压缩失败: {e}")
        return input_path

def _cleanup_temp_files(temp_files: List[str]):
    """清理临时文件"""
    import os
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.debug(f"临时文件已清理: {temp_file}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {temp_file}, 错误: {e}")

def merge_pdfs(input_paths: List[str], output_path: str) -> Tuple[bool, Optional[str]]:
    """使用 PikePDF 合并多个PDF，以保留书签等元数据。"""
    try:
        new_pdf = pikepdf.Pdf.new()
        for path in input_paths:
            try:
                with pikepdf.open(path) as src:
                    new_pdf.pages.extend(src.pages)
            except Exception as e:
                logger.warning(f"Skipping unreadable file during merge: {path}, Error: {e}")
        new_pdf.save(output_path)
        return True, None
    except Exception as e:
        logger.exception("An error occurred while merging PDFs.")
        return False, "PDF merge failed. See logs for details."

def add_page_numbers(input_pdf: str, output_pdf: str, font_name="Helvetica", font_size=9, x=72, y=40) -> Tuple[bool, Optional[str]]:
    """为PDF添加页码，格式为 '当前页 / 总页数'。"""
    try:
        reader = PdfReader(input_pdf)
        if reader.is_encrypted:
            raise PdfReadError("Encrypted file")

        writer = PdfWriter()
        page_total = len(reader.pages)

        for i, page in enumerate(reader.pages):
            text = f"{i + 1} / {page_total}"
            logger.debug(f"  - Page {i+1}: Adding page number '{text}'")
            _apply_overlay(page, text, font_name, font_size, x, y)
            writer.add_page(page)

        with open(output_pdf, "wb") as f:
            writer.write(f)
        logger.info(f"Successfully added page numbers to: {output_pdf}")
        return True, None
    except Exception as e:
        logger.error(f"Failed to add page numbers to {input_pdf}: {e}", exc_info=True)
        return False, str(e)
