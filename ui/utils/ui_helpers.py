from PySide6.QtWidgets import QTableWidget

def ensure_selection_or_first_row(file_table: QTableWidget) -> int:
    """确保有选中行，若无则选中第0行并返回行号；若失败返回-1。"""
    try:
        row = file_table.currentRow()
        if row < 0 and file_table.rowCount() > 0:
            file_table.selectRow(0)
            return 0
        return row
    except Exception:
        return -1



