import os
import logging
from pdf_analyzer import PdfAnalyzer
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError
from typing import List

logger = logging.getLogger(__name__)
# 兼容层：统一委托至 PdfAnalyzer（仅检测/读取功能）
_analyzer = PdfAnalyzer()

def get_pdf_page_count(path: str) -> int:
    """
    Returns the number of pages in a PDF file.

    Args:
        path (str): Path to the PDF file.

    Returns:
        int: Number of pages, or 0 if the file could not be read.
    """
    try:
        return _analyzer.get_pdf_page_count(path)
    except Exception as e:
        logger.exception(f"[Page Count] (compat) Unexpected error for {path}: {e}")
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
        return _analyzer.get_pdf_file_size_mb(path)
    except Exception as e:
        logger.exception(f"[File Size] (compat) Error reading {path}: {e}")
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
        return _analyzer.get_pdf_metadata(path)
    except Exception as e:
        logger.exception(f"[Metadata] (compat) Unexpected error for {path}: {e}")
        return {}

def get_pdf_fonts(path: str) -> list[str]:
    """
    Attempts to list font names used in the first page of a PDF.

    Args:
        path (str): Path to the PDF file.

    Returns:
        list[str]: List of font identifiers found (if any).
    """
    try:
        data = _analyzer.get_pdf_fonts(path, pages=1)
        # 兼容旧返回：仅返回第一页字体键列表
        if isinstance(data, dict) and "pages" in data and data["pages"]:
            first = data["pages"][0]
            return list(first.get("fonts", []) or [])
        return []
    except Exception as e:
        logger.exception(f"[Fonts] (compat) Unexpected error in {path}: {e}")
        return []


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

def extract_artifact_headers_footers(path: str, max_pages: int = 5) -> dict:
    """
    扫描前几页内容流，提取 Acrobat 风格的 Artifact 分页工件中的 ASCII 文本。
    返回结构：{"pages": [{"page":1, "header":["..."], "footer":["..."]}, ...]}
    仅适用于我们注入的 ASCII 文字或其他简单 Tj 情况。
    """
    # 早返回：统一委托 PdfAnalyzer（保持旧签名）
    try:
        return _analyzer.extract_artifact_headers_footers(path, max_pages=max_pages)
    except Exception as e:
        logger.warning(f"[Artifact] (compat) Extraction failed for {path}: {e}")
        return {"pages": []}

def detect_headers_footers_heuristic(path: str, max_pages: int = 5) -> dict:
    """
    使用改进的启发式方法检测页眉页脚，不依赖Artifact标签。
    通过文本位置聚类、重复性分析、语义分析等方法识别。
    
    返回结构：{"pages": [{"page":1, "header":["..."], "footer":["..."]}, ...]}
    """
    # 早返回：统一委托 PdfAnalyzer（保持旧签名）
    try:
        return _analyzer.detect_headers_footers_heuristic(path, max_pages=max_pages)
    except Exception as e:
        logger.warning(f"Heuristic header/footer detection failed (compat): {e}")
        return {"pages": []}

def _is_likely_header_footer_improved(text: str, font_size: float, font_name: str, all_texts: List[str]) -> bool:
    """
    改进的判断文本是否可能是页眉页脚
    """
    # 基础过滤条件
    if not text or len(text.strip()) < 2:
        return False
    
    # 过滤掉页码（纯数字）
    if text.isdigit() and len(text) <= 3:
        return False
    
    # 过滤掉太长的文本（可能是正文）
    if len(text) > 100:
        return False
    
    # 语义分析：检查是否包含正文特征（标点符号等）
    content_indicators = ['。', '，', '！', '？', '；', '：', '（', '）', '【', '】', '、']
    if any(char in text for char in content_indicators):
        return False
    
    # 重复性检测：只有跨页重复的文本才可能是页眉页脚
    text_occurrences = all_texts.count(text)
    if text_occurrences < 2:  # 至少出现2次
        return False
    
    # 检查是否包含常见的页眉页脚关键词
    header_footer_keywords = [
        '公司', '部门', '标题', '文档', '机密', '草稿', '最终版',
        'page', 'page', '第', '页', '共', 'of', 'confidential',
        'draft', 'final', 'version', 'company', 'department',
        '证据', '日期'  # 根据您的报告添加特定关键词
    ]
    
    text_lower = text.lower()
    if any(keyword in text_lower for keyword in header_footer_keywords):
        return True
    
    # 检查字体大小（页眉页脚通常较小）
    if font_size > 0 and font_size < 16:
        return True
    
    # 检查字体名称（某些字体常用于页眉页脚）
    header_footer_fonts = ['arial', 'helvetica', 'times', 'simsun', 'simhei']
    if any(font in font_name.lower() for font in header_footer_fonts):
        return True
    
    return False

def extract_all_headers_footers(path: str, max_pages: int = 5) -> dict:
    """
    综合提取页眉页脚：同时使用Artifact方法和启发式方法，并合并结果
    增加结果验证和去重逻辑
    """
    # 早返回：统一委托 PdfAnalyzer（保持旧签名）
    try:
        return _analyzer.extract_all_headers_footers(path, max_pages=max_pages)
    except Exception as e:
        logger.warning(f"[Combined] (compat) Extraction failed for {path}: {e}")
        return {"pages": []}

def _clean_and_validate_headers_footers(text_list: List[str]) -> List[str]:
    """
    清理和验证页眉页脚文本列表
    """
    if not text_list:
        return []
    
    cleaned = []
    for text in text_list:
        # 去除空白和过短文本
        if not text or len(text.strip()) < 2:
            continue
        
        # 去除纯数字（页码）
        if text.strip().isdigit() and len(text.strip()) <= 3:
            continue
        
        # 去除明显不是页眉页脚的内容
        if len(text.strip()) > 100:
            continue
        
        # 检查是否包含正文特征
        content_indicators = ['。', '，', '！', '？', '；', '：', '（', '）', '【', '】', '、']
        if any(char in text for char in content_indicators):
            continue
        
        cleaned.append(text.strip())
    
    # 去重并保持顺序
    seen = set()
    unique_list = []
    for text in cleaned:
        if text not in seen:
            seen.add(text)
            unique_list.append(text)
    
    return unique_list
