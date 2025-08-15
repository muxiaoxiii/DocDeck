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

def detect_headers_footers_heuristic(path: str, max_pages: int = 5) -> dict:
    """
    使用启发式方法检测页眉页脚，不依赖Artifact标签。
    通过文本位置聚类、重复性分析等方法识别。
    
    返回结构：{"pages": [{"page":1, "header":["..."], "footer":["..."]}, ...]}
    """
    try:
        import fitz
        doc = fitz.open(path)
        results = {"pages": []}
        
        # 分析前几页
        pages_to_analyze = min(max_pages, len(doc))
        
        # 收集所有文本块的位置信息
        all_text_blocks = []
        for page_num in range(pages_to_analyze):
            page = doc[page_num]
            blocks = page.get_text("dict")
            
            for block in blocks.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line.get("spans", []):
                            if span.get("text", "").strip():
                                all_text_blocks.append({
                                    "page": page_num + 1,
                                    "text": span["text"].strip(),
                                    "bbox": span["bbox"],  # [x0, y0, x1, y1]
                                    "size": span.get("size", 0),
                                    "font": span.get("font", "")
                                })
        
        if not all_text_blocks:
            return results
        
        # 按页面分组
        pages_data = {}
        for block in all_text_blocks:
            page_num = block["page"]
            if page_num not in pages_data:
                pages_data[page_num] = []
            pages_data[page_num].append(block)
        
        # 分析每页
        for page_num in range(1, pages_to_analyze + 1):
            if page_num not in pages_data:
                continue
                
            page_blocks = pages_data[page_num]
            page_height = doc[page_num - 1].rect.height
            
            # 定义页眉页脚区域（页面顶部和底部20%）
            header_zone = page_height * 0.2
            footer_zone = page_height * 0.8
            
            headers = []
            footers = []
            
            for block in page_blocks:
                bbox = block["bbox"]
                y_pos = bbox[1]  # y0位置
                text = block["text"]
                
                # 过滤掉太短的文本
                if len(text) < 2:
                    continue
                
                # 根据Y位置判断是页眉还是页脚
                if y_pos < header_zone:
                    # 页眉区域
                    if _is_likely_header_footer(text, block["size"], block["font"]):
                        headers.append(text)
                elif y_pos > footer_zone:
                    # 页脚区域
                    if _is_likely_header_footer(text, block["size"], block["font"]):
                        footers.append(text)
            
            # 去重并排序
            headers = list(set(headers))
            footers = list(set(footers))
            
            # 按Y位置排序
            headers.sort(key=lambda x: next((b["bbox"][1] for b in page_blocks if b["text"] == x), 0))
            footers.sort(key=lambda x: next((b["bbox"][1] for b in page_blocks if b["text"] == x), 0))
            
            results["pages"].append({
                "page": page_num,
                "header": headers,
                "footer": footers
            })
        
        doc.close()
        return results
        
    except Exception as e:
        logger.warning(f"Heuristic header/footer detection failed: {e}")
        return {"pages": []}

def _is_likely_header_footer(text: str, font_size: float, font_name: str) -> bool:
    """
    判断文本是否可能是页眉页脚
    """
    # 过滤条件
    if not text or len(text.strip()) < 2:
        return False
    
    # 过滤掉页码（纯数字）
    if text.isdigit() and len(text) <= 3:
        return False
    
    # 过滤掉太长的文本（可能是正文）
    if len(text) > 100:
        return False
    
    # 过滤掉包含特殊字符的文本（可能是正文）
    special_chars = ['。', '，', '！', '？', '；', '：', '（', '）', '【', '】']
    if any(char in text for char in special_chars):
        return False
    
    # 检查是否包含常见的页眉页脚关键词
    header_footer_keywords = [
        '公司', '部门', '标题', '文档', '机密', '草稿', '最终版',
        'page', 'page', '第', '页', '共', 'of', 'confidential',
        'draft', 'final', 'version', 'company', 'department'
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
    综合提取页眉页脚：先尝试Artifact方法，再使用启发式方法
    """
    # 首先尝试Artifact方法
    artifact_result = extract_artifact_headers_footers(path, max_pages)
    
    # 如果Artifact方法没有结果，使用启发式方法
    if not artifact_result or not artifact_result.get("pages"):
        return detect_headers_footers_heuristic(path, max_pages)
    
    # 合并结果
    heuristic_result = detect_headers_footers_heuristic(path, max_pages)
    
    # 合并两种方法的结果
    merged_result = {"pages": []}
    artifact_pages = {p["page"]: p for p in artifact_result["pages"]}
    heuristic_pages = {p["page"]: p for p in heuristic_result["pages"]}
    
    all_pages = set(artifact_pages.keys()) | set(heuristic_pages.keys())
    
    for page_num in sorted(all_pages):
        merged_page = {"page": page_num, "header": [], "footer": []}
        
        # 合并页眉
        if page_num in artifact_pages:
            merged_page["header"].extend(artifact_pages[page_num].get("header", []))
        if page_num in heuristic_pages:
            merged_page["header"].extend(heuristic_pages[page_num].get("header", []))
        
        # 合并页脚
        if page_num in artifact_pages:
            merged_page["footer"].extend(artifact_pages[page_num].get("footer", []))
        if page_num in heuristic_pages:
            merged_page["footer"].extend(heuristic_pages[page_num].get("footer", []))
        
        # 去重
        merged_page["header"] = list(set(merged_page["header"]))
        merged_page["footer"] = list(set(merged_page["footer"]))
        
        merged_result["pages"].append(merged_page)
    
    return merged_result
