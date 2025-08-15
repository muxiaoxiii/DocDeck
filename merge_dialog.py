from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QPushButton,
    QHBoxLayout, QListWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt, Signal
import os

class MergeDialog(QDialog):
    merge_confirmed = Signal(list)

    def __init__(self, pdf_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("合并 PDF 文件")
        self.resize(500, 400)
        self.pdf_paths = pdf_paths
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("拖动以排序，双击以移除要合并的 PDF 文件："))

        # 添加智能排序按钮
        sort_layout = QHBoxLayout()
        self.sort_button = QPushButton("智能排序")
        self.sort_button.clicked.connect(self._smart_sort)
        sort_layout.addWidget(self.sort_button)
        sort_layout.addStretch()
        layout.addLayout(sort_layout)

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        for path in self.pdf_paths:
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(path)  # 显示完整路径
            item.setData(Qt.UserRole, path)  # 保存完整路径
        self.list_widget.itemDoubleClicked.connect(self.remove_item)
        layout.addWidget(self.list_widget)

        # 添加加减按钮
        add_remove_layout = QHBoxLayout()
        self.add_button = QPushButton("+ 添加文件")
        self.remove_button = QPushButton("- 移除选中")
        self.add_button.clicked.connect(self._add_files)
        self.remove_button.clicked.connect(self._remove_selected)
        add_remove_layout.addWidget(self.add_button)
        add_remove_layout.addWidget(self.remove_button)
        add_remove_layout.addStretch()
        layout.addLayout(add_remove_layout)

        btn_layout = QHBoxLayout()
        self.ok_button = QPushButton("合并并保存")
        self.cancel_button = QPushButton("取消")
        self.ok_button.clicked.connect(self._emit_merge_confirmed)
        self.cancel_button.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_button)
        btn_layout.addWidget(self.cancel_button)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def remove_item(self, item):
        # 添加确认对话框
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要移除文件 '{item.text()}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.list_widget.takeItem(self.list_widget.row(item))

    def _smart_sort(self):
        """智能排序：按文件名排序"""
        items = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            items.append((item.text(), item.data(Qt.UserRole)))
        
        # 按文件名排序
        items.sort(key=lambda x: x[0].lower())
        
        # 重新填充列表
        self.list_widget.clear()
        for name, path in items:
            item = QListWidgetItem(name)
            item.setToolTip(path)
            item.setData(Qt.UserRole, path)
            self.list_widget.addItem(item)

    def _add_files(self):
        """添加更多文件"""
        from PySide6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(self, "选择PDF文件", "", "PDF Files (*.pdf)")
        for path in paths:
            if path not in [self.list_widget.item(i).data(Qt.UserRole) for i in range(self.list_widget.count())]:
                item = QListWidgetItem(os.path.basename(path))
                item.setToolTip(path)
                item.setData(Qt.UserRole, path)
                self.list_widget.addItem(item)

    def _remove_selected(self):
        """移除选中的文件"""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要移除选中的 {len(selected_items)} 个文件吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            for item in selected_items:
                self.list_widget.takeItem(self.list_widget.row(item))

    def get_ordered_paths(self):
        return [self.list_widget.item(i).data(Qt.UserRole) for i in range(self.list_widget.count())]

    def _emit_merge_confirmed(self):
        paths = self.get_ordered_paths()
        if not paths:
            return
        self.merge_confirmed.emit(paths)
        self.accept()