import os
import traceback
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.errors import PdfReadError
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from typing import List, Dict, Any
from models import PDFFileItem
from PySide6.QtCore import QObject, Signal
from file_namer import get_unique_filename
from logger import logger
import pikepdf
from pdf_utils import register_font_safely

class WorkerSignals(QObject):
    progress = Signal(int, int, str)

def _apply_overlay(page, text: str, font_name: str, font_size: int, x: float, y: float):
    """在内存中创建一个包含文本的图层并应用到给定的页面对象上。"""
    try:
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)

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

def process_pdfs_in_batch(
    file_infos: List[PDFFileItem],
    output_dir: str,
    header_settings: Dict[str, Any],
    footer_settings: Dict[str, Any],
    signals: WorkerSignals = None
) -> List[Dict[str, Any]]:
    """
    对一批PDF文件进行处理，添加页眉和/或页脚。
    """
    results = []
    total_files = len(file_infos)
    for idx, item in enumerate(file_infos):
        try:
            logger.info(f"Processing file {idx + 1}/{total_files}: {item.name}")
            
            reader = PdfReader(item.path)
            if reader.is_encrypted:
                raise PdfReadError("File is encrypted. Please unlock it first.")

            writer = PdfWriter()
            page_total = len(reader.pages)

            for i, page in enumerate(reader.pages):
                # --- Apply Header ---
                if item.header_text:
                    # <<< ENHANCEMENT: Added descriptive debug log for header ---
                    logger.debug(f"  - Page {i+1}: Applying header '{item.header_text}'")
                    _apply_overlay(
                        page, item.header_text,
                        header_settings.get("font_name"),
                        header_settings.get("font_size"),
                        header_settings.get("x"),
                        header_settings.get("y")
                    )

                # --- Apply Footer with Template Formatting ---
                if item.footer_text:
                    # Replace placeholders for current page and total pages
                    footer_text = item.footer_text.format(page=i + 1, total=page_total)
                    
                    # <<< ENHANCEMENT: Added descriptive debug log for footer ---
                    logger.debug(f"  - Page {i+1}: Applying footer '{footer_text}' (from template: '{item.footer_text}')")
                    _apply_overlay(
                        page, footer_text,
                        footer_settings.get("font_name"),
                        footer_settings.get("font_size"),
                        footer_settings.get("x"),
                        footer_settings.get("y")
                    )
                
                writer.add_page(page)

            output_name = get_unique_filename(output_dir, f"{os.path.splitext(item.name)[0]}_processed.pdf")
            output_path = os.path.join(output_dir, output_name)
            
            with open(output_path, "wb") as f:
                writer.write(f)

            logger.info(f"Successfully processed and saved to: {output_path}")
            results.append({"input": item.path, "output": output_path, "success": True, "error": None})

            if signals:
                signals.progress.emit(idx + 1, total_files, item.name)

        except (PdfReadError, Exception) as e:
            error_msg = str(e)
            logger.error(f"Failed to process: {item.name}. Reason: {error_msg}", exc_info=True)
            results.append({"input": item.path, "output": None, "success": False, "error": error_msg})
    
    return results

def merge_pdfs(input_paths: List[str], output_path: str) -> (bool, str):
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

def add_page_numbers(input_pdf: str, output_pdf: str, font_name="Helvetica", font_size=9, x=72, y=40):
    """为PDF添加页码，格式为 '当前页 / 总页数'。"""
    try:
        reader = PdfReader(input_pdf)
        if reader.is_encrypted:
            raise PdfReadError("Encrypted file")

        writer = PdfWriter()
        page_total = len(reader.pages)

        for i, page in enumerate(reader.pages):
            text = f"{i + 1} / {page_total}"
            # <<< ENHANCEMENT: Added descriptive debug log for page numbers ---
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
