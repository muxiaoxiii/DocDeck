"""
ui_main.py (legacy shim)
- Deprecated: use `ui.main_window.MainWindow`
- This file remains as a thin compatibility layer for older imports
"""
from __future__ import annotations

import warnings

warnings.warn(
    "ui_main.MainWindow 已弃用，请改用 ui.main_window.MainWindow",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export MainWindow from the modern module
from ui.main_window import MainWindow  # noqa: F401

__all__ = ["MainWindow"] 
