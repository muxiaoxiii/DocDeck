import sys
import os
from typing import List
from PySide6.QtGui import QFontDatabase
from logger import logger

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("The 'fitz' module is missing. Please install it via 'pip install pymupdf'")

def get_system_fonts() -> List[str]:
    """
    Return a list of available system font family names.
    """
    fonts = QFontDatabase()
    return fonts.families()

def is_chinese_supported(font_name: str) -> bool:
    """
    Check if a given font supports Chinese characters.
    """
    db = QFontDatabase()
    return db.supportedWritingSystems(font_name).count(QFontDatabase.WritingSystem.SimplifiedChinese) > 0

def extract_header_fonts(path: str, y_threshold: int = 820, page_limit: int = 3) -> List[str]:
    """
    Scan the top Y region of each page (typically page header) and extract font names.

    Args:
        path (str): Path to the PDF file.
        y_threshold (int): Y-coordinate threshold for detecting header text (default 820 pt).
        page_limit (int): Number of pages to scan for fonts.

    Returns:
        List[str]: Unique font names detected in the header region.
    """
    fonts = set()
    try:
        doc = fitz.open(path)
        for page in doc[:min(len(doc), page_limit)]:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        y_top = span["bbox"][1]
                        if y_top <= y_threshold:
                            fonts.add(span.get("font", "Unknown"))
    except Exception as e:
        logger.error(f"Error extracting header fonts from {path}: {e}")
    return list(fonts)

def extract_footer_fonts(path: str, y_threshold: int = 100, page_limit: int = 3) -> List[str]:
    """
    Scan the bottom Y region of each page (typically footer) and extract font names.

    Args:
        path (str): Path to the PDF file.
        y_threshold (int): Y-coordinate threshold for detecting footer text (default 100 pt).
        page_limit (int): Number of pages to scan for fonts.

    Returns:
        List[str]: Unique font names detected in the footer region.
    """
    fonts = set()
    try:
        doc = fitz.open(path)
        for page in doc[:min(len(doc), page_limit)]:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        y_bottom = span["bbox"][1]
                        if y_bottom <= y_threshold:
                            fonts.add(span.get("font", "Unknown"))
    except Exception as e:
        logger.error(f"Error extracting footer fonts from {path}: {e}")
    return list(fonts)

def suggest_chinese_fallback_font(preferred: str = None) -> str:
    """
    Suggest a fallback font that supports Chinese characters.

    Args:
        preferred (str, optional): Font name to test first.

    Returns:
        str: A valid font name that supports Simplified Chinese.
    """
    if preferred and is_chinese_supported(preferred):
        return preferred
    for font in get_system_fonts():
        if is_chinese_supported(font):
            return font
    return "SimHei"  # fallback fallback


def get_recommended_fonts(pdf_paths: List[str], max_files: int = 3, y_threshold: int = 820) -> List[str]:
    """
    扫描多个PDF的页眉区域字体，清洗并返回一个带分隔符的推荐列表。
    """
    seen_fonts = set()
    for path in pdf_paths[:max_files]:
        fonts = extract_header_fonts(path, y_threshold=y_threshold)
        seen_fonts.update(fonts)

    recommended = [font for font in seen_fonts if font and isinstance(font, str)]
    recommended = list(dict.fromkeys(recommended))  # 去重保序
    if recommended:
        recommended.insert(0, "---")  # 在列表开头插入分隔符
    return recommended