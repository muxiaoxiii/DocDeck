"""
UI Dialogs Module
包含所有对话框的模块化实现
"""

# 兼容导出：现有实现位于 ui/components/dialogs/header_footer_editor.py
try:
    from ui.components.dialogs.header_footer_editor import HeaderFooterEditorDialog as HeaderFooterEditDialog
except Exception:  # pragma: no cover
    HeaderFooterEditDialog = None

__all__ = [
    'HeaderFooterEditDialog',
    'HeaderFooterEditDialog'  # 兼容名称
]
