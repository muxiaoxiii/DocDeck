import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PDFFileItem:
    """
    Represents a single PDF file in the application list.
    This simplified model stores only the essential per-file data.
    Styling and positioning are handled globally by the UI and passed during processing.
    """
    path: str                     # Full file path
    name: str                     # File name (basename)
    size_mb: float                # File size in MB
    page_count: int               # Number of pages
    header_text: str              # Header text to be added
    footer_text: Optional[str] = "" # Footer text to be added (can be a template)

@dataclass
class PDFProcessResult:
    """
    Represents the result of a processing operation on a single PDF.
    """
    input: str                          # Input PDF file path
    output: Optional[str] = None        # Output PDF file path
    success: bool = True                # Whether processing was successful
    error: Optional[str] = None         # Error message if processing failed
