from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QPushButton,
    QHBoxLayout, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal

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

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        for path in self.pdf_paths:
            item = QListWidgetItem(path)
            self.list_widget.addItem(item)
        self.list_widget.itemDoubleClicked.connect(self.remove_item)
        layout.addWidget(self.list_widget)

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
        self.list_widget.takeItem(self.list_widget.row(item))

    def get_ordered_paths(self):
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]

    def _emit_merge_confirmed(self):
        paths = self.get_ordered_paths()
        if not paths:
            return
        self.merge_confirmed.emit(paths)
        self.accept()