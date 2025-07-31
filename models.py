from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PDFFileItem:
    path: str                     # Full file path
    name: str                     # File name (basename)
    size_mb: float                # File size in MB
    page_count: int               # Number of pages
    header_text: str              # Header text to be added

    footer_text: Optional[str] = ""        # Optional footer (for future use)
    status: str = "pending"                # Status: pending, processed, failed
    original_header: Optional[str] = None  # Extracted header if available
    error_message: Optional[str] = None    # Error message if processing failed

    # Optional header styling and positioning
    header_font: Optional[str] = None
    header_font_size: Optional[int] = None
    header_x: Optional[int] = None
    header_y: Optional[int] = None

    # Optional footer styling and positioning
    footer_font: Optional[str] = None
    footer_font_size: Optional[int] = None
    footer_x: Optional[int] = None
    footer_y: Optional[int] = None
