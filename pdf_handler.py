# pdf_handler.py
import os
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
            fallback_font = "Helvetica" # More common fallback
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

def _add_marked_text(pdf: pikepdf.Pdf, page: pikepdf.Page, text: str, font_size: int, x: float, y: float, subtype: str = 'Header'):
    """将 ASCII 文本作为带 Artifact 的分页工件写入页面内容流。"""
    _ensure_base_font_resource(pdf, page, font_key='/F1', base_font='/Helvetica')
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

def _process_single_file_with_overlay(item: PDFFileItem, output_dir: str, header_settings: Dict[str, Any], footer_settings: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """复用现有 PyPDF2+ReportLab 覆盖路径处理单文件。返回 (success, output_path, error)."""
    try:
        reader = PdfReader(item.path)
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

def process_pdfs_in_batch(
    file_infos: List[PDFFileItem],
    output_dir: str,
    header_settings: Dict[str, Any],
    footer_settings: Dict[str, Any],
    signals: WorkerSignals = None
) -> List[Dict[str, Any]]:
    """
    对一批PDF文件进行处理，添加页眉和/或页脚。
    当 header_settings/footer_settings 中包含 structured=True 时，优先尝试以 Artifact 方式写入（仅 ASCII 文本），否则回退到覆盖方式。
    """
    results = []
    total_files = len(file_infos)
    structured = bool(header_settings.get("structured") or footer_settings.get("structured"))
    for idx, item in enumerate(file_infos):
        try:
            logger.info(f"Processing file {idx + 1}/{total_files}: {item.name}")
            if structured and ((_is_ascii(item.header_text or "")) and (_is_ascii(item.footer_text or ""))):
                # 结构化路径（ASCII）
                with pikepdf.open(item.path) as pdf:
                    page_total = len(pdf.pages)
                    for i, page in enumerate(pdf.pages):
                        if item.header_text:
                            _add_marked_text(pdf, page, item.header_text, int(header_settings.get("font_size", 9)), float(header_settings.get("x", 72)), float(header_settings.get("y", 752)), subtype='Header')
                        if item.footer_text:
                            footer_text = (item.footer_text or "").format(page=i + 1, total=page_total)
                            _add_marked_text(pdf, page, footer_text, int(footer_settings.get("font_size", 9)), float(footer_settings.get("x", 72)), float(footer_settings.get("y", 40)), subtype='Footer')
                    output_name = get_unique_filename(output_dir, f"{os.path.splitext(item.name)[0]}_processed.pdf")
                    output_path = os.path.join(output_dir, output_name)
                    pdf.save(output_path)
                    results.append({"input": item.path, "output": output_path, "success": True, "error": None})
            else:
                # 回退：原有覆盖方式
                ok, output_path, err = _process_single_file_with_overlay(item, output_dir, header_settings, footer_settings)
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
