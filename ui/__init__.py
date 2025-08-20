# UI模块
"""UI 包入口
- 优先导出 `ui.main_window.MainWindow`
- 失败时回退到 `ui_main.MainWindow`
"""

MainWindow = None
try:
    from ui.main_window import MainWindow as _PreferredMainWindow
    MainWindow = _PreferredMainWindow
except Exception:  # pragma: no cover
    try:
        from ui_main import MainWindow as _LegacyMainWindow
        MainWindow = _LegacyMainWindow
    except Exception:
        MainWindow = None

__all__ = [
    'MainWindow',
]
