import os
import traceback
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.errors import PdfReadError
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from typing import List
from models import PDFFileItem  # Ensure this exists
from PySide6.QtCore import QObject, Signal
from file_namer import get_unique_filename
from logger import logger
from matplotlib.font_manager import findfont, FontProperties
import pikepdf  # 新增导入
from pdf_utils import register_font_safely

class WorkerSignals(QObject):
    progress = Signal(int, int, str)

def add_header_to_pdf(input_path, output_path, header_text, font_name="Helvetica", font_size=9, x=72, y=772):
    try:
        # Read input PDF
        reader = PdfReader(input_path)
        writer = PdfWriter()

        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]

            # Create a PDF with the header
            packet = BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)

            can.setFont(font_name, font_size)
            can.drawString(x, y, header_text)
            can.save()

            # Move to the beginning of the BytesIO buffer
            packet.seek(0)
            overlay_pdf = PdfReader(packet)
            overlay_page = overlay_pdf.pages[0]

            # Merge the overlay page with the original
            page.merge_page(overlay_page)
            writer.add_page(page)

        # Write output PDF
        with open(output_path, "wb") as f:
            writer.write(f)

        return True, None
    except PdfReadError:
        logger.warning(f"无法读取文件，可能已加密或已损坏: {input_path}")
        return False, "文件已加密或已损坏，无法读取。"
    except Exception as e:
        logger.exception("添加页眉时出错")
        return False, "发生未知错误，详细信息已记录日志。"

def add_footer_to_pdf(input_path, output_path, footer_text, font_name="Helvetica", font_size=9, x=72, y=40):
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()

        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]

            packet = BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)

            can.setFont(font_name, font_size)
            can.drawString(x, y, footer_text)
            can.save()

            packet.seek(0)
            overlay_pdf = PdfReader(packet)
            overlay_page = overlay_pdf.pages[0]

            page.merge_page(overlay_page)
            writer.add_page(page)

        final_output_path = output_path
        with open(final_output_path, "wb") as f:
            writer.write(f)

        logger.info(f"已成功添加页脚，输出文件: {final_output_path}")
        return True, None
    except PdfReadError:
        logger.warning(f"无法读取文件，可能已加密或已损坏: {input_path}")
        return False, "文件已加密或已损坏，无法读取。"
    except Exception as e:
        logger.exception("添加页脚时出错")
        return False, "发生未知错误，详细信息已记录日志。"


def _apply_overlay(page, text, font_name, font_size, x, y):
    """在内存中创建一个包含文本的图层并应用到给定的页面对象上。"""
    try:
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)

        if register_font_safely(font_name):
            can.setFont(font_name, font_size)
        else:
            logger.warning(f"字体 '{font_name}' 无法找到或注册，回退到 Helvetica。")
            can.setFont("Helvetica", font_size)

        can.drawString(x, y, text)
        can.save()

        packet.seek(0)
        overlay_pdf = PdfReader(packet)
        page.merge_page(overlay_pdf.pages[0])
    except Exception as e:
        logger.error(f"应用文本图层失败: {text}, 错误: {e}", exc_info=True)

def process_pdfs_in_batch(
    file_infos: List[PDFFileItem],
    output_dir: str,
    header_settings: dict,
    footer_settings: dict,
    signals: WorkerSignals = None
):
    results = []
    for idx, item in enumerate(file_infos):
        try:
            logger.info(f"正在处理: {item.name}")
            
            reader = PdfReader(item.path)
            writer = PdfWriter()

            for page in reader.pages:
                if item.header_text:
                    _apply_overlay(
                        page, item.header_text,
                        header_settings.get("font_name", "Helvetica"),
                        header_settings.get("font_size", 9),
                        header_settings.get("x", 72),
                        header_settings.get("y", 772)
                    )

                if item.footer_text:
                    _apply_overlay(
                        page, item.footer_text,
                        footer_settings.get("font_name", "Helvetica"),
                        footer_settings.get("font_size", 9),
                        footer_settings.get("x", 72),
                        footer_settings.get("y", 40)
                    )
                
                writer.add_page(page)

            output_name = get_unique_filename(output_dir, f"{os.path.splitext(item.name)[0]}_processed.pdf")
            output_path = os.path.join(output_dir, output_name)
            
            with open(output_path, "wb") as f:
                writer.write(f)

            logger.info(f"输出至: {output_path}")
            results.append({"input": item.path, "output": output_path, "success": True, "error": None})

            if signals:
                signals.progress.emit(idx + 1, len(file_infos), item.name)

        except PdfReadError as e:
            error_msg = "文件已加密或已损坏。"
            logger.warning(f"处理失败: {item.name}, 错误: {error_msg} - {e}")
            results.append({"input": item.path, "output": None, "success": False, "error": error_msg})

        except Exception as e:
            logger.error(f"处理失败: {item.name}\n{traceback.format_exc()}")
            results.append({"input": item.path, "output": None, "success": False, "error": f"未知错误: {e}"})
    
    return results

def merge_pdfs(input_paths, output_path):
    """使用 PikePDF 合并多个PDF，以保留书签等元数据。"""
    try:
        new_pdf = pikepdf.Pdf.new()
        for path in input_paths:
            try:
                with pikepdf.open(path) as src:
                    new_pdf.pages.extend(src.pages)
            except Exception as e:
                logger.warning(f"跳过无法读取的文件: {path}, 错误: {e}")
        new_pdf.save(output_path)
        return True, None
    except Exception as e:
        logger.exception("合并 PDF 时出错")
        return False, "PDF 合并失败，详细信息已记录日志。"