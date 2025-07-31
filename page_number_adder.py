from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from typing import Tuple
from pdf_utils import register_font_safely

def add_page_numbers(
    input_path: str,
    output_path: str,
    font_name: str = "Helvetica",
    font_size: int = 9,
    x: float = 300,
    y: float = 40,
    start_number: int = 1,
    show_total: bool = True,
    format_template: str = "{current} / {total}"
) -> Tuple[bool, str | None]:
    """
    Add page numbers to each page of a PDF.

    Parameters:
        input_path (str): Path to the source PDF.
        output_path (str): Path to save the new PDF with page numbers.
        font_name (str): Font used for the page number.
        font_size (int): Font size.
        x (float): X coordinate for page number placement.
        y (float): Y coordinate for page number placement.
        start_number (int): Starting number for page numbering.
        show_total (bool): Whether to include total page count (e.g., '3 / 10').
        format_template (str): Template string for page number display. Supports {current} and {total}.

    Returns:
        (bool, str | None): Tuple with success status and error message if any.
    """
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        total_pages = len(reader.pages)

        for i, page in enumerate(reader.pages):
            packet = BytesIO()
            c = canvas.Canvas(packet, pagesize=letter)
            number = start_number + i
            label = format_template.format(current=number, total=total_pages)
            if register_font_safely(font_name):
                c.setFont(font_name, font_size)
            else:
                c.setFont("Helvetica", font_size)
            c.drawString(x, y, label)
            c.save()

            packet.seek(0)
            overlay = PdfReader(packet)
            page.merge_page(overlay.pages[0])
            writer.add_page(page)

        with open(output_path, "wb") as f:
            writer.write(f)

        return True, None
    except Exception as e:
        return False, str(e)