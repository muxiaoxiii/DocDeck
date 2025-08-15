import os
import logging
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

logger = logging.getLogger(__name__)

def get_pdf_page_count(path: str) -> int:
    """
    Returns the number of pages in a PDF file.

    Args:
        path (str): Path to the PDF file.

    Returns:
        int: Number of pages, or 0 if the file could not be read.
    """
    try:
        reader = PdfReader(path)
        return len(reader.pages)
    except (FileNotFoundError, PdfReadError) as e:
        logger.warning(f"[Page Count] Cannot read {path}: {e}")
    except Exception as e:
        logger.exception(f"[Page Count] Unexpected error for {path}: {e}")
    return 0

def get_pdf_file_size_mb(path: str) -> float:
    """
    Returns the file size of a PDF in megabytes.

    Args:
        path (str): Path to the PDF file.

    Returns:
        float: Size in MB, or 0.0 if the file could not be accessed.
    """
    try:
        size_bytes = os.path.getsize(path)
        return round(size_bytes / (1024 * 1024), 2)
    except FileNotFoundError as e:
        logger.warning(f"[File Size] File not found: {path}: {e}")
    except Exception as e:
        logger.exception(f"[File Size] Error reading {path}: {e}")
    return 0.0


# --- Additional PDF utilities ---
def get_pdf_metadata(path: str) -> dict:
    """
    Extracts metadata such as title, author, and creation date from a PDF.

    Args:
        path (str): Path to the PDF file.

    Returns:
        dict: Metadata dictionary or empty if unavailable.
    """
    try:
        reader = PdfReader(path)
        meta = reader.metadata
        return {
            "title": meta.title if meta else None,
            "author": meta.author if meta else None,
            "creator": meta.creator if meta else None,
            "producer": meta.producer if meta else None,
            "created": meta.get("/CreationDate", None) if meta else None
        }
    except (FileNotFoundError, PdfReadError) as e:
        logger.warning(f"[Metadata] Cannot extract from {path}: {e}")
    except Exception as e:
        logger.exception(f"[Metadata] Unexpected error for {path}: {e}")
    return {}

def get_pdf_fonts(path: str) -> list[str]:
    """
    Attempts to list font names used in the first page of a PDF.

    Args:
        path (str): Path to the PDF file.

    Returns:
        list[str]: List of font identifiers found (if any).
    """
    fonts: list[str] = []
    try:
        reader = PdfReader(path)
        page = reader.pages[0]
        resources = page.get("/Resources", {})
        if "/Font" in resources:
            font_dict = resources["/Font"]
            if hasattr(font_dict, "keys"):
                fonts = list(font_dict.keys())
    except (FileNotFoundError, PdfReadError) as e:
        logger.warning(f"[Fonts] Failed to read {path}: {e}")
    except Exception as e:
        logger.exception(f"[Fonts] Unexpected error in {path}: {e}")
    return fonts


# --- Font registration utility ---
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from matplotlib.font_manager import findfont, FontProperties

def register_font_safely(font_name: str) -> bool:
    """
    Safely registers a font by trying to find it on the system.

    Args:
        font_name (str): Name of the font to register.

    Returns:
        bool: True if registration succeeded or already registered, False otherwise.
    """
    if font_name in pdfmetrics.getRegisteredFontNames():
        logger.debug(f"[Font] '{font_name}' already registered.")
        return True
    try:
        font_prop = FontProperties(family=font_name)
        font_path = findfont(font_prop, fallback_to_default=True)
        if font_path:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            logger.info(f"[Font] Registered '{font_name}' from: {font_path}")
            return True
        else:
            logger.warning(f"[Font] Could not find path for font: {font_name}")
            return False
    except Exception as e:
        logger.warning(f"[Font] Failed to register font '{font_name}': {e}")
        return False

# --- Artifact header/footer extraction ---
import re
import pikepdf
from pikepdf import Name

def extract_artifact_headers_footers(path: str, max_pages: int = 3) -> dict:
    """
    扫描前几页内容流，提取 Acrobat 风格的 Artifact 分页工件中的 ASCII 文本。
    返回结构：{"pages": [{"page":1, "header":["..."], "footer":["..."]}, ...]}
    仅适用于我们注入的 ASCII 文字或其他简单 Tj 情况。
    """
    result = {"pages": []}
    try:
        with pikepdf.open(path) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages]):
                content_obj = page.obj.get(Name('/Contents'))
                if content_obj is None:
                    result["pages"].append({"page": i+1, "header": [], "footer": []})
                    continue
                # 拼接内容字节
                if isinstance(content_obj, pikepdf.Array):
                    content_bytes = b"".join([c.read_bytes() for c in content_obj])
                elif isinstance(content_obj, pikepdf.Stream):
                    content_bytes = content_obj.read_bytes()
                else:
                    content_bytes = b""
                text = content_bytes.decode('latin-1', errors='ignore')
                header_matches = re.findall(r"/Artifact\s*<<[^>]*?/Subtype\s*/Header[^>]*?>>\s*BDC(.*?)EMC", text, re.DOTALL)
                footer_matches = re.findall(r"/Artifact\s*<<[^>]*?/Subtype\s*/Footer[^>]*?>>\s*BDC(.*?)EMC", text, re.DOTALL)
                # 提取括号字符串
                def _extract_strings(segment: str) -> list[str]:
                    raw = re.findall(r"\((.*?)(?<!\\)\)", segment, re.DOTALL)
                    # 反转义 \\ \( \)
                    out = [s.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\") for s in raw]
                    return [s.strip() for s in out if s.strip()]
                headers = []
                for seg in header_matches:
                    headers.extend(_extract_strings(seg))
                footers = []
                for seg in footer_matches:
                    footers.extend(_extract_strings(seg))
                result["pages"].append({"page": i+1, "header": headers, "footer": footers})
        return result
    except Exception as e:
        logger.warning(f"[Artifact] Extraction failed for {path}: {e}")
        return result
