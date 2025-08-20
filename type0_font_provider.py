# type0_font_provider.py
"""
此模块负责为PDF文档提供 Type0 字体资源。

核心功能是 `ensure_type0_font`，它采用“载体PDF”策略：
1. 使用 ReportLab 在内存中生成一个包含特定中文字体的单页PDF。ReportLab 会负责正确地
   构建和嵌入 Type0 字体描述符、CIDFont、ToUnicode CMap 等复杂对象。
2. 使用 pikepdf 打开这个“载体PDF”，并将其中的字体资源复制到目标PDF文档中。
3. 返回在目标PDF中可用的字体资源名称。

这种方法避免了手动构造 Type0 字体的复杂性，稳定可靠。
"""

from typing import Dict, Optional
import pikepdf
from pikepdf import Name
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

from logger import logger
from font_manager import register_font_safely

# 缓存已创建的字体载体PDF，避免重复生成
_FONT_CARRIER_CACHE: Dict[str, bytes] = {}


def _create_font_carrier_pdf(font_name: str) -> Optional[bytes]:
    """
    使用 ReportLab 创建一个包含指定字体的单页PDF。
    这个PDF被称为“字体载体”，因为它包含了所有需要的 Type0 字体描述符。
    """
    if not register_font_safely(font_name):
        logger.error(f"[Type0] 字体 '{font_name}' 注册失败，无法创建字体载体。")
        return None
    
    try:
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=(100, 100))
        can.setFont(font_name, 10)
        # 写入一个常见的汉字来强制嵌入字体信息
        can.drawString(10, 50, "字")
        can.save()
        return packet.getvalue()
    except Exception as e:
        logger.error(f"[Type0] 创建字体载体PDF时出错: {e}", exc_info=True)
        return None

def ensure_type0_font(pdf: pikepdf.Pdf, font_name: str) -> Optional[str]:
    """
    确保目标PDF中有所需的 Type0 字体资源。

    Args:
        pdf: 目标 pikepdf.Pdf 对象。
        font_name: 需要确保存在的字体名（系统中的 TTF 字体名）。

    Returns:
        在PDF内部的字体资源名（例如 '/F1'），如果失败则返回 None。
    """
    carrier_bytes = _FONT_CARRIER_CACHE.get(font_name)
    if not carrier_bytes:
        logger.info(f"[Type0] 缓存未命中，为字体 '{font_name}' 创建新的载体PDF。")
        carrier_bytes = _create_font_carrier_pdf(font_name)
        if not carrier_bytes:
            return None
        _FONT_CARRIER_CACHE[font_name] = carrier_bytes
    else:
        logger.debug(f"[Type0] 缓存命中，重复使用字体 '{font_name}' 的载体PDF。")

    try:
        with pikepdf.open(BytesIO(carrier_bytes)) as carrier_pdf:
            carrier_page = carrier_pdf.pages[0]
            # ReportLab 通常会将字体资源放在页面的 /Resources/Font 下
            carrier_fonts = carrier_page.obj.get(Name('/Resources'), {}).get(Name('/Font'), {})
            
            if not carrier_fonts:
                logger.error(f"[Type0] 载体PDF中未找到字体资源。")
                return None

            # 遍历载体中的所有字体，并将它们复制到目标PDF中
            # 通常只有一个，但为了稳健性我们遍历
            target_font_res_name = None
            for font_key, font_obj in carrier_fonts.items():
                # 检查目标PDF中是否已有同名字体资源
                # 为避免冲突，我们生成一个新的、唯一的资源名
                i = 1
                new_font_key = f"/TTF{i}"
                # 查找一个在整个文档的 /Resources/Font 中都唯一的 key
                # (这是一个简化逻辑，实际应用中可能需要更复杂的全局唯一性检查)
                while any(Name(new_font_key) in p.obj.get(Name('/Resources'), {}).get(Name('/Font'), {}) for p in pdf.pages):
                    i += 1
                    new_font_key = f"/TTF{i}"
                
                # 复制字体对象。copy_foreign 会处理所有依赖的子对象。
                copied_font_obj = pdf.copy_foreign(font_obj)
                
                # 将复制的字体资源添加到每一页
                # 注意：更优化的做法是添加到文档级别的资源字典，但添加到每页更简单直接
                for page in pdf.pages:
                    if page.obj.get(Name('/Resources')) is None:
                        page.obj[Name('/Resources')] = pikepdf.Dictionary()
                    
                    page_res = page.obj.get(Name('/Resources'))
                    if page_res.get(Name('/Font')) is None:
                        page_res[Name('/Font')] = pikepdf.Dictionary()
                        
                    page_res.get(Name('/Font'))[Name(new_font_key)] = copied_font_obj

                logger.info(f"[Type0] 成功将字体 '{font_name}' 从载体复制到目标PDF，资源名为 '{new_font_key}'。")
                target_font_res_name = new_font_key.lstrip('/')
                # 我们只需要复制第一个找到的字体
                break
            
            return target_font_res_name

    except Exception as e:
        logger.error(f"[Type0] 从载体PDF复制字体资源时出错: {e}", exc_info=True)
        return None
