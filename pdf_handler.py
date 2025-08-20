# pdf_handler.py
import os
import tempfile
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.errors import PdfReadError
from reportlab.pdfgen import canvas
from io import BytesIO
from typing import List, Dict, Any, Tuple, Optional
import re
from datetime import datetime
from models import PDFFileItem, EncryptionStatus
from PySide6.QtCore import QObject, Signal
from file_namer import get_unique_filename
from logger import logger
import pikepdf
from pikepdf import Name, Dictionary
from font_manager import register_font_safely
from font_manager import suggest_chinese_fallback_font
from geometry_context import A4_PORTRAIT, build_geometry_context
from type0_font_provider import ensure_type0_font

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

def _utf16be_hex_str(text: str) -> str:
    """将字符串编码为UTF-16BE，并返回其十六进制表示形式。"""
    return text.encode('utf-16be').hex()

_DATE_FIELD_RE = re.compile(r"\{date(?::([^}]+))?\}")

def _expand_placeholders(raw: str, *, page: int, total: int, source_path: str) -> str:
    """展开占位符：{page} {total} {filename} {basename} {date[:fmt]}。
    默认日期格式为 %Y-%m-%d。
    """
    if not raw:
        return ""
    filename = os.path.basename(source_path)
    basename, _ = os.path.splitext(filename)
    out = raw.replace("{page}", str(page)).replace("{total}", str(total))
    out = out.replace("{filename}", filename).replace("{basename}", basename)

    def _date_sub(m: re.Match) -> str:
        fmt = m.group(1) or "%Y-%m-%d"
        try:
            return datetime.now().strftime(fmt)
        except Exception:
            return datetime.now().strftime("%Y-%m-%d")
    out = _DATE_FIELD_RE.sub(_date_sub, out)
    return out

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

def _add_marked_text(
    pdf: pikepdf.Pdf,
    page: pikepdf.Page,
    text: str,
    font_size: int,
    x: float,
    y: float,
    subtype: str = 'Header',
    base_font: Optional[str] = None,
    meta: Optional[Dict[str, str]] = None,
):
    """将 ASCII 文本作为带 Artifact 的分页工件写入页面内容流，并可携带DocDeck元数据。"""
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
    # 元数据片段
    meta_str = ""
    if meta:
        for k, v in meta.items():
            esc = _escape_pdf_text(str(v))
            meta_str += f" /DD{k} ({esc})"
    content = (
        f"/Artifact << /Type /Pagination /Subtype /{subtype}{meta_str} >> BDC BT /F1 {font_size} Tf "
        f"1 0 0 1 {x} {y} Tm ({escaped}) Tj ET EMC\n"
    )
    try:
        page.add_content(content)
    except AttributeError:
        new_stream = pikepdf.Stream(pdf, content.encode('latin-1'))
        contents = page.obj.get(Name('/Contents'))
        if contents is None:
            page.obj[Name('/Contents')] = pdf.make_indirect(new_stream)
        elif isinstance(contents, pikepdf.Array):
            contents.append(pdf.make_indirect(new_stream))
        else:
            page.obj[Name('/Contents')] = pikepdf.Array([contents, pdf.make_indirect(new_stream)])

# === Structured Chinese (non-ASCII) via Form XObject === (将被废弃)


# === Page normalization to A4 ===
A4_PORTRAIT = (595.0, 842.0)
A4_LANDSCAPE = (842.0, 595.0)

def _get_page_box(page: pikepdf.Page, name: str):
    box = page.obj.get(Name(f'/{name}'))
    return box if (box is not None and len(box) == 4) else None

def _normalize_page_to_a4(page: pikepdf.Page):
    """
    将单个页面规范化为A4尺寸。
    此函数现在完全依赖 `geometry_context` 模块进行计算。
    """
    try:
        # 1. 使用 build_geometry_context 获取所有计算参数
        ctx = build_geometry_context(page, normalize_a4=True)
        
        # 如果页面已经是目标尺寸且无需旋转，则无需操作
        if ctx.transform_scale == 1.0 and ctx.original_rotation == 0 and \
           abs(ctx.effective_page_width - ctx.original_media_box[2] + ctx.original_media_box[0]) < 1 and \
           abs(ctx.effective_page_height - ctx.original_media_box[3] + ctx.original_media_box[1]) < 1:
            return

        # 2. 构建变换矩阵
        rotate = ctx.original_rotation
        scale = ctx.transform_scale
        offset_x = ctx.transform_offset_x
        offset_y = ctx.transform_offset_y
        target_width = ctx.effective_page_width
        target_height = ctx.effective_page_height

        if rotate == 0:
            transform_matrix = f"q {scale:.6f} 0 0 {scale:.6f} {offset_x:.6f} {offset_y:.6f} cm\n"
        elif rotate == 90:
            transform_matrix = f"q 0 {scale:.6f} {-scale:.6f} 0 {target_width - offset_y:.6f} {offset_x:.6f} cm\n"
        elif rotate == 180:
            transform_matrix = f"q {-scale:.6f} 0 0 {-scale:.6f} {target_width - offset_x:.6f} {target_height - offset_y:.6f} cm\n"
        elif rotate == 270:
            transform_matrix = f"q 0 {-scale:.6f} {scale:.6f} 0 {offset_y:.6f} {target_height - offset_x:.6f} cm\n"
        else:
            transform_matrix = f"q {scale:.6f} 0 0 {scale:.6f} {offset_x:.6f} {offset_y:.6f} cm\n"
            
        # 3. 应用变换到页面内容（与之前逻辑相同）
        try:
            contents = page.obj.get(Name('/Contents'))
            
            new_contents = f"{transform_matrix}"
            
            if contents is not None:
                if isinstance(contents, pikepdf.Array):
                    for content in contents:
                        new_contents += f"q\n{content.read_bytes().decode('latin-1', errors='ignore')}\nQ\n"
                else:
                    new_contents += f"q\n{contents.read_bytes().decode('latin-1', errors='ignore')}\nQ\n"
            else:
                new_contents += "0 0 m 0 0 l s\n"
                
            new_contents += "Q\n"
            
            new_stream = pikepdf.Stream(page.obj.pdf, new_contents.encode('latin-1'))
            page.obj[Name('/Contents')] = page.obj.pdf.make_indirect(new_stream)
            
        except Exception as content_error:
            logger.warning(f"内容流处理失败: {content_error}")
            
        # 4. 更新页面尺寸和旋转信息
        new_box = pikepdf.Array([0, 0, target_width, target_height])
        page.obj[Name('/MediaBox')] = new_box
        page.obj[Name('/CropBox')] = new_box
        
        if page.obj.get(Name('/Rotate')) is not None:
            page.obj[Name('/Rotate')] = 0
            
        logger.info(f"页面A4规范化成功: {ctx.original_media_box[2]:.1f}x{ctx.original_media_box[3]:.1f} -> {target_width:.1f}x{target_height:.1f}, 旋转: {rotate}°")
        
    except Exception as e:
        logger.warning(f"Normalize page to A4 failed: {str(e)}")
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
    当 `structured=True` 时，使用 Type0 字体直写（中文）或 Base14 字体（ASCII）
    的方式进行结构化写入。否则回退到覆盖方式。
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
                    if normalize_a4:
                        for page in pdf.pages:
                            _normalize_page_to_a4(page)
                            
                    # 为非ASCII字体预先准备好字体资源
                    # 这会一次性将字体复制到所有页面
                    header_font_res_name = None
                    if item.header_text and not _is_ascii(item.header_text):
                        cn_font_h = header_settings.get("structured_cn_font") if header_settings.get("structured_cn_fixed") else suggest_chinese_fallback_font(header_settings.get("font_name"))
                        header_font_res_name = ensure_type0_font(pdf, cn_font_h)

                    footer_font_res_name = None
                    if item.footer_text and not _is_ascii(item.footer_text):
                        cn_font_f = footer_settings.get("structured_cn_font") if footer_settings.get("structured_cn_fixed") else suggest_chinese_fallback_font(footer_settings.get("font_name"))
                        footer_font_res_name = ensure_type0_font(pdf, cn_font_f)

                    page_total = len(pdf.pages)
                    header_base_font = _map_to_base14(header_settings.get("font_name"))
                    footer_base_font = _map_to_base14(footer_settings.get("font_name"))

                    for i, page in enumerate(pdf.pages):
                        # 逐文件模式接入：默认保留，替换=删同类再写，删除=仅删（不写）
                        mode = getattr(item, 'preview_mode', 'keep')
                        if item.header_text and mode != 'remove':
                            header_text_expanded = _expand_placeholders(
                                item.header_text, page=i + 1, total=page_total, source_path=item.path
                            )
                            hdr_meta = {
                                'Template': item.header_text or '',
                                'DateFmt': header_settings.get('date_fmt', '%Y-%m-%d'),
                                'Align': header_settings.get('align', 'left'),
                                'Unit': 'pt',
                                'Version': '1.0',
                                'Type': 'Header',
                            }
                            if _is_ascii(header_text_expanded):
                                _add_marked_text(
                                    pdf, page, header_text_expanded,
                                    int(header_settings.get("font_size", 9)),
                                    float(header_settings.get("x", 72)),
                                    float(header_settings.get("y", 752)),
                                    subtype='Header', base_font=header_base_font, meta=hdr_meta)
                            elif header_font_res_name:
                                hex_bytes = _utf16be_hex_str(header_text_expanded)
                                meta_str = (
                                    f" /DDTemplate ({_escape_pdf_text(item.header_text or '')})"
                                    f" /DDDateFmt ({_escape_pdf_text(header_settings.get('date_fmt', '%Y-%m-%d'))})"
                                    f" /DDAlign ({_escape_pdf_text(header_settings.get('align', 'left'))})"
                                    f" /DDUnit (pt) /DDVersion (1.0) /DDType (Header)"
                                )
                                content = (f"/Artifact << /Type /Pagination /Subtype /Header{meta_str} >> BDC "
                                           f"BT /{header_font_res_name} {header_settings.get('font_size', 9)} Tf "
                                           f"1 0 0 1 {header_settings.get('x', 72)} {header_settings.get('y', 752)} Tm "
                                           f"<{hex_bytes}> Tj ET EMC\n")
                                page.add_content(content)

                        if item.footer_text and mode != 'remove':
                            footer_text_expanded = _expand_placeholders(
                                item.footer_text or "", page=i + 1, total=page_total, source_path=item.path
                            )
                            ftr_meta = {
                                'Template': item.footer_text or '',
                                'DateFmt': footer_settings.get('date_fmt', '%Y-%m-%d'),
                                'Align': footer_settings.get('align', 'left'),
                                'Unit': 'pt',
                                'Version': '1.0',
                                'Type': 'Footer',
                            }
                            if _is_ascii(footer_text_expanded):
                                _add_marked_text(
                                    pdf, page, footer_text_expanded,
                                    int(footer_settings.get("font_size", 9)),
                                    float(footer_settings.get("x", 72)),
                                    float(footer_settings.get("y", 40)),
                                    subtype='Footer', base_font=footer_base_font, meta=ftr_meta)
                            elif footer_font_res_name:
                                hex_bytes = _utf16be_hex_str(footer_text_expanded)
                                meta_str = (
                                    f" /DDTemplate ({_escape_pdf_text(item.footer_text or '')})"
                                    f" /DDDateFmt ({_escape_pdf_text(footer_settings.get('date_fmt', '%Y-%m-%d'))})"
                                    f" /DDAlign ({_escape_pdf_text(footer_settings.get('align', 'left'))})"
                                    f" /DDUnit (pt) /DDVersion (1.0) /DDType (Footer)"
                                )
                                content = (f"/Artifact << /Type /Pagination /Subtype /Footer{meta_str} >> BDC "
                                           f"BT /{footer_font_res_name} {footer_settings.get('font_size', 9)} Tf "
                                           f"1 0 0 1 {footer_settings.get('x', 72)} {footer_settings.get('y', 40)} Tm "
                                           f"<{hex_bytes}> Tj ET EMC\n")
                                page.add_content(content)
                    
                    # 确保 MarkInfo 设置
                    root = pdf.root
                    if root.get(Name('/MarkInfo')) is None:
                        root[Name('/MarkInfo')] = Dictionary({Name('/Marked'): True})
                    else:
                        root.get(Name('/MarkInfo'))[Name('/Marked')] = True

                    output_name = get_unique_filename(output_dir, f"{os.path.splitext(item.name)[0]}_processed.pdf")
                    output_path = os.path.join(output_dir, output_name)
                    pdf.save(output_path)
                    results.append({"input": item.path, "output": output_path, "success": True, "error": None})
            else:
                # 回退：原有覆盖方式
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


# === Header/Footer removal (artifact-aware with heuristic fallback) ===
import re as _re
from pikepdf import Stream as _PdfStream


def remove_headers_footers(
    input_pdf: str,
    output_pdf: str,
    detection_result: dict,
    header_strip_ratio: float = 0.10,
    footer_strip_ratio: float = 0.10,
) -> dict:
    """
    删除PDF中的页眉页脚：
    1) 优先删除带 /Artifact /Pagination /Subtype /Header|/Footer 的内容段（不依赖具体文本）
    2) 若该页启发式检测到头/脚但无Artifact可删，则在相应条带区域绘制白色矩形遮盖（保底）

    参数：
    - input_pdf: 源PDF路径
    - output_pdf: 输出PDF路径
    - detection_result: 检测模块返回的结构（extract_all_headers_footers 的结果）
    - header_strip_ratio/footer_strip_ratio: 无Artifact时用于遮盖的页眉/页脚条带比例（相对于页面高度）
    """
    pages_info = {p.get("page"): p for p in detection_result.get("pages", [])}
    pages_modified = 0
    try:
        with pikepdf.open(input_pdf) as pdf:
            for page_index, page in enumerate(pdf.pages):
                page_num = page_index + 1
                info = pages_info.get(page_num, {"header": [], "footer": []})
                has_header = bool(info.get("header"))
                has_footer = bool(info.get("footer"))

                # 读取并拼接内容流
                contents = page.obj.get(Name('/Contents'))
                if contents is None:
                    continue
                if isinstance(contents, pikepdf.Array):
                    original_bytes = b"".join([c.read_bytes() for c in contents])
                elif isinstance(contents, pikepdf.Stream):
                    original_bytes = contents.read_bytes()
                else:
                    original_bytes = b""

                text = original_bytes.decode('latin-1', errors='ignore')

                # 删除 Artifact 段：Header/Footer（不匹配具体文字）
                header_pattern = r"/Artifact\s*<<[^>]*?/Subtype\s*/Header[^>]*?>>\s*BDC[\s\S]*?EMC"
                footer_pattern = r"/Artifact\s*<<[^>]*?/Subtype\s*/Footer[^>]*?>>\s*BDC[\s\S]*?EMC"

                new_text = _re.sub(header_pattern, "", text, flags=_re.IGNORECASE)
                new_text2 = _re.sub(footer_pattern, "", new_text, flags=_re.IGNORECASE)

                artifact_removed = (new_text2 != text)

                # 写回内容流（合并为单一流简化处理）
                if artifact_removed:
                    new_stream = _PdfStream(pdf, new_text2.encode('latin-1', errors='ignore'))
                    page.obj[Name('/Contents')] = pdf.make_indirect(new_stream)
                    pages_modified += 1

                # 若无Artifact删除但检测判定存在，则遮盖保底
                if (has_header or has_footer) and not artifact_removed:
                    try:
                        # 页面宽高
                        mbox = page.obj.get(Name('/MediaBox'))
                        if mbox is None or len(mbox) < 4:
                            pw, ph = A4_PORTRAIT
                        else:
                            pw = float(mbox[2]) - float(mbox[0])
                            ph = float(mbox[3]) - float(mbox[1])

                        overlay_cmds = []
                        overlay_cmds.append("q 1 1 1 rg 1 1 1 RG\n")  # 白色填充/描边
                        if has_header and header_strip_ratio > 0:
                            h = max(10.0, ph * header_strip_ratio)
                            overlay_cmds.append(f"0 {ph - h:.2f} {pw:.2f} {h:.2f} re f\n")
                        if has_footer and footer_strip_ratio > 0:
                            h = max(10.0, ph * footer_strip_ratio)
                            overlay_cmds.append(f"0 0 {pw:.2f} {h:.2f} re f\n")
                        overlay_cmds.append("Q\n")

                        overlay_stream = _PdfStream(pdf, ("".join(overlay_cmds)).encode('latin-1'))
                        existing = page.obj.get(Name('/Contents'))
                        if isinstance(existing, pikepdf.Array):
                            existing.append(pdf.make_indirect(overlay_stream))
                        else:
                            page.obj[Name('/Contents')] = pikepdf.Array([existing, pdf.make_indirect(overlay_stream)]) if existing else pdf.make_indirect(overlay_stream)
                        pages_modified += 1
                    except Exception:
                        pass

            pdf.save(output_pdf)

        return {"success": True, "output_path": output_pdf, "pages_modified": pages_modified}
    except Exception as e:
        logger.error(f"remove_headers_footers failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
