HEADER_SAFE_MIN_Y = 720  # 792 pt - 72 pt (top safe area)
FOOTER_SAFE_MAX_Y = 72   # bottom safe area
PRINT_MARGIN_LIMIT = 12  # within 12 pt from edge is risky for print


def is_within_header_region(y: float, page_height: float = 792) -> bool:
    """
    Check if y is within Acrobat-recognized header region (top 72pt).

    Args:
        y (float): Y-coordinate to check.
        page_height (float): Total height of the page.

    Returns:
        bool: True if within header region.
    """
    return y >= (page_height - 72)


def is_within_footer_region(y: float) -> bool:
    """
    Check if y is within Acrobat-recognized footer region (bottom 72pt).

    Args:
        y (float): Y-coordinate to check.

    Returns:
        bool: True if within footer region.
    """
    return y <= 72


def is_out_of_print_safe_area(y: float, top: bool = True) -> bool:
    """
    Return True if y is too close to physical printer edge (less than PRINT_MARGIN_LIMIT pt).

    Args:
        y (float): Y-coordinate to check.
        top (bool): True if checking top margin, False for bottom.

    Returns:
        bool: True if out of safe margin area.
    """
    if top:
        return y > 792 - PRINT_MARGIN_LIMIT
    else:
        return y < PRINT_MARGIN_LIMIT


def suggest_safe_header_y() -> float:
    """
    Recommended Y position for header (40 pt from top).

    Returns:
        float: Suggested Y position for header.
    """
    return 752  # 792 - 40


def suggest_safe_footer_y() -> float:
    """
    Recommended Y position for footer (40 pt from bottom).

    Returns:
        float: Suggested Y position for footer.
    """
    return 40

def estimate_text_width(text: str, font_size: float) -> float:
    """
    Estimate the width of a text string using a basic heuristic.
    Assumes average character width = 0.5 * font_size.

    Args:
        text (str): The text whose width to estimate.
        font_size (float): The font size in points.

    Returns:
        float: Estimated width of the text.
    """
    return len(text) * font_size * 0.5


def get_aligned_x_position(alignment, page_width, text_width, margin=72):
    """
    Return X coordinate based on alignment:
    - 'left'   → margin
    - 'center' → center horizontally
    - 'right'  → page_width - margin - text_width
    """
    if alignment == "left":
        return margin
    elif alignment == "center":
        return (page_width - text_width) / 2
    elif alignment == "right":
        return page_width - margin - text_width
    else:
        raise ValueError("Invalid alignment: expected 'left', 'center', or 'right'")


def estimate_standard_header_width(font_size: int, test_text: str = "示例文档-000-v1") -> float:
    """
    Estimate header text width using a fixed representative string.
    This ensures consistent alignment across different files.

    Args:
        font_size (int): Font size in points.
        test_text (str): The representative header string to estimate width.

    Returns:
        float: Estimated width of the header text.
    """
    return estimate_text_width(test_text, font_size)