from dataclasses import dataclass
from typing import Tuple, Optional
import pikepdf
from pikepdf import Name

# A4 in points
A4_PORTRAIT = (595.0, 842.0)
A4_LANDSCAPE = (842.0, 595.0)


@dataclass
class GeometryContext:
    """
    存储单个PDF页面的几何信息，用于统一写入和预览的坐标计算。
    所有尺寸单位均为 PDF 点（points）。
    """
    # 原始页面尺寸信息
    original_media_box: Tuple[float, float, float, float]
    original_crop_box: Tuple[float, float, float, float]
    original_rotation: int

    # A4规范化或旋转后的最终有效页面尺寸
    effective_page_width: float
    effective_page_height: float

    # 从原始坐标到最终有效坐标的变换参数
    # 例如，对于A4规范化，这里会存储缩放比例和平移量
    transform_scale: float = 1.0
    transform_offset_x: float = 0.0
    transform_offset_y: float = 0.0
    
    # 最终的变换矩阵（pikepdf.Matrix 或类似结构），用于写入内容流
    # transform_matrix: any = None  # 待定具体类型


def calculate_a4_normalization_params(
    page_width: float,
    page_height: float,
    rotation: int,
) -> dict:
    """
    根据页面尺寸和旋转角度，计算将其规范化到A4尺寸所需的变换参数。
    这是一个纯计算函数，不依赖任何外部PDF库的对象。

    返回:
        一个包含变换参数的字典，包括目标尺寸、缩放比例和偏移量。
    """
    # 智能方向判断：考虑旋转后的实际显示方向
    if rotation in (90, 270):
        display_width = page_height
        display_height = page_width
    else:
        display_width = page_width
        display_height = page_height
        
    is_portrait = display_height > display_width
    
    if is_portrait:
        target_width, target_height = A4_PORTRAIT
    else:
        target_width, target_height = A4_LANDSCAPE
        
    scale_x = target_width / display_width
    scale_y = target_height / display_height
    scale = min(scale_x, scale_y)
    
    scaled_width = display_width * scale
    scaled_height = display_height * scale
    offset_x = (target_width - scaled_width) / 2.0
    offset_y = (target_height - scaled_height) / 2.0
    
    return {
        "target_width": target_width,
        "target_height": target_height,
        "scale": scale,
        "offset_x": offset_x,
        "offset_y": offset_y,
    }

def get_page_box(page: pikepdf.Page, name: str) -> Optional[Tuple[float, float, float, float]]:
    """安全地获取页面的尺寸框，返回一个元组或None。"""
    box = page.obj.get(Name(f'/{name}'))
    if box is not None and len(box) == 4:
        return tuple(float(v) for v in box)
    return None

def build_geometry_context(page: pikepdf.Page, normalize_a4: bool) -> GeometryContext:
    """
    根据 pikepdf.Page 对象构建 GeometryContext。
    
    Args:
        page: pikepdf 页面对象。
        normalize_a4: 是否应用A4规范化。
        
    Returns:
        一个填充了页面几何信息的 GeometryContext 实例。
    """
    # 1. 获取原始尺寸和旋转信息
    media_box = get_page_box(page, 'MediaBox')
    crop_box = get_page_box(page, 'CropBox')
    
    # MediaBox 是必须的，如果不存在则无法继续
    if not media_box:
        raise ValueError("无法获取页面的 MediaBox，无法构建几何上下文。")

    # CropBox 是可选的，如果不存在则使用 MediaBox
    active_box = crop_box or media_box
    
    original_width = active_box[2] - active_box[0]
    original_height = active_box[3] - active_box[1]
    rotation = int(page.obj.get(Name('/Rotate'), 0)) % 360

    # 2. 如果不进行A4规范化，则有效尺寸即为原始尺寸
    if not normalize_a4:
        return GeometryContext(
            original_media_box=media_box,
            original_crop_box=crop_box,
            original_rotation=rotation,
            effective_page_width=original_width,
            effective_page_height=original_height,
        )

    # 3. 如果进行A4规范化，则计算变换参数
    params = calculate_a4_normalization_params(original_width, original_height, rotation)
    
    return GeometryContext(
        original_media_box=media_box,
        original_crop_box=crop_box,
        original_rotation=rotation,
        effective_page_width=params["target_width"],
        effective_page_height=params["target_height"],
        transform_scale=params["scale"],
        transform_offset_x=params["offset_x"],
        transform_offset_y=params["offset_y"],
    )
