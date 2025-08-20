from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QSpinBox,
    QPushButton, QListWidget, QListWidgetItem, QCheckBox
)
from PySide6.QtCore import Qt


class HeaderFooterEditorDialog(QDialog):
    """简化版页眉/页脚编辑对话框。
    - 展示候选（Artifact/启发式）
    - 模板字符串、对齐、日期格式、位置
    - 确定后写回主窗口控件，并将当前文件模式切换为“替换”
    - 取消时恢复原值
    """

    def __init__(self, main_window, row_index: int, parent=None):
        super().__init__(parent or main_window)
        self.setWindowTitle(main_window._("编辑页眉/页脚"))
        self.main_window = main_window
        self.row_index = row_index
        self._ = main_window._

        # 备份原值（取消时恢复）
        self._backup = {
            'header_text': self.main_window.header_text_input.text() if hasattr(self.main_window, 'header_text_input') else "",
            'footer_text': self.main_window.footer_text_input.text() if hasattr(self.main_window, 'footer_text_input') else "",
            'x': self.main_window.x_input.value() if hasattr(self.main_window, 'x_input') else 72,
            'y': self.main_window.y_input.value() if hasattr(self.main_window, 'y_input') else 752,
            'fx': self.main_window.footer_x_input.value() if hasattr(self.main_window, 'footer_x_input') else 72,
            'fy': self.main_window.footer_y_input.value() if hasattr(self.main_window, 'footer_y_input') else 40,
        }

        layout = QVBoxLayout()

        # 候选列表
        layout.addWidget(QLabel(self._("候选（双击应用）")))
        lists_layout = QHBoxLayout()
        self.header_list = QListWidget()
        self.footer_list = QListWidget()
        lists_layout.addWidget(QLabel(self._("Header")))
        lists_layout.addWidget(self.header_list, 1)
        lists_layout.addWidget(QLabel(self._("Footer")))
        lists_layout.addWidget(self.footer_list, 1)
        layout.addLayout(lists_layout)

        # 模板与格式/对齐
        form_layout = QVBoxLayout()
        self.header_line = QLineEdit(self._backup['header_text'])
        self.footer_line = QLineEdit(self._backup['footer_text'])
        self.date_fmt_line = QLineEdit("%Y-%m-%d")
        self.header_align_combo = QComboBox(); self.header_align_combo.addItems([self._("Left"), self._("Center"), self._("Right")])
        self.footer_align_combo = QComboBox(); self.footer_align_combo.addItems([self._("Left"), self._("Center"), self._("Right")])
        form_layout.addWidget(QLabel(self._("Header 模板")))
        form_layout.addWidget(self.header_line)
        form_layout.addWidget(QLabel(self._("Header 对齐")))
        form_layout.addWidget(self.header_align_combo)
        form_layout.addWidget(QLabel(self._("Footer 模板")))
        form_layout.addWidget(self.footer_line)
        form_layout.addWidget(QLabel(self._("Footer 对齐")))
        form_layout.addWidget(self.footer_align_combo)
        form_layout.addWidget(QLabel(self._("日期格式（{date:fmt}）")))
        form_layout.addWidget(self.date_fmt_line)

        # 位置
        pos_layout = QHBoxLayout()
        self.x_spin = QSpinBox(); self.x_spin.setRange(0, 2000); self.x_spin.setValue(self._backup['x'])
        self.y_spin = QSpinBox(); self.y_spin.setRange(0, 2000); self.y_spin.setValue(self._backup['y'])
        self.fx_spin = QSpinBox(); self.fx_spin.setRange(0, 2000); self.fx_spin.setValue(self._backup['fx'])
        self.fy_spin = QSpinBox(); self.fy_spin.setRange(0, 2000); self.fy_spin.setValue(self._backup['fy'])
        pos_layout.addWidget(QLabel(self._("Header X"))); pos_layout.addWidget(self.x_spin)
        pos_layout.addWidget(QLabel(self._("Header Y"))); pos_layout.addWidget(self.y_spin)
        pos_layout.addWidget(QLabel(self._("Footer X"))); pos_layout.addWidget(self.fx_spin)
        pos_layout.addWidget(QLabel(self._("Footer Y"))); pos_layout.addWidget(self.fy_spin)
        form_layout.addLayout(pos_layout)
        layout.addLayout(form_layout)

        # 按钮
        btns = QHBoxLayout()
        self.live_preview_checkbox = QCheckBox(self._("实时预览"))
        self.live_preview_checkbox.setChecked(True)
        ok_btn = QPushButton(self._("确定"))
        preview_btn = QPushButton(self._("预览"))
        cancel_btn = QPushButton(self._("取消"))
        btns.addStretch()
        btns.addWidget(self.live_preview_checkbox)
        btns.addWidget(preview_btn)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

        self.setLayout(layout)

        # 绑定事件
        self.header_list.itemDoubleClicked.connect(lambda it: self.header_line.setText(it.text()))
        self.footer_list.itemDoubleClicked.connect(lambda it: self.footer_line.setText(it.text()))
        ok_btn.clicked.connect(self._on_accept)
        preview_btn.clicked.connect(lambda: self.main_window.update_preview())
        cancel_btn.clicked.connect(self._on_reject)

        # 加载候选
        self._load_candidates()

        # 实时预览联动
        def _maybe_preview():
            if self.live_preview_checkbox.isChecked():
                # 将当前编辑框值临时写入主UI控件，调用主预览
                try:
                    # 单独写入 header/footer 文本，避免页脚跟随页眉问题
                    if hasattr(self.main_window, 'header_text_input'):
                        self.main_window.header_text_input.blockSignals(True)
                        self.main_window.header_text_input.setText(self.header_line.text())
                        self.main_window.header_text_input.blockSignals(False)
                    if hasattr(self.main_window, 'footer_text_input'):
                        self.main_window.footer_text_input.blockSignals(True)
                        self.main_window.footer_text_input.setText(self.footer_line.text())
                        self.main_window.footer_text_input.blockSignals(False)
                    self.main_window.x_input.setValue(self.x_spin.value())
                    self.main_window.y_input.setValue(self.y_spin.value())
                    self.main_window.footer_x_input.setValue(self.fx_spin.value())
                    self.main_window.footer_y_input.setValue(self.fy_spin.value())
                except Exception:
                    pass
                self.main_window.update_preview()

        for w in [self.header_line, self.footer_line, self.date_fmt_line]:
            w.textChanged.connect(_maybe_preview)
        for w in [self.x_spin, self.y_spin, self.fx_spin, self.fy_spin]:
            w.valueChanged.connect(_maybe_preview)

    def _load_candidates(self):
        try:
            item = self.main_window.file_items[self.row_index]
            from pdf_analyzer import PdfAnalyzer
            analyzer = PdfAnalyzer()
            art = analyzer.extract_all_headers_footers(item.path, max_pages=5)
            # Artifact
            headers = []
            footers = []
            for p in art.get('pages', []):
                headers += p.get('header', []) or []
                footers += p.get('footer', []) or []
            # 启发式
            try:
                # 直接使用 PdfAnalyzer
                from pdf_analyzer import PdfAnalyzer
                heur = PdfAnalyzer().detect_headers_footers_heuristic(item.path, max_pages=5)
                for p in heur.get('pages', []):
                    # 已有 _is_likely 判定
                    pass
            except Exception:
                pass
            # 填充列表
            for t in sorted(set(headers)):
                self.header_list.addItem(QListWidgetItem(t))
            for t in sorted(set(footers)):
                self.footer_list.addItem(QListWidgetItem(t))
        except Exception:
            pass

    def _on_accept(self):
        # 将编辑内容回写到主窗口控件
        try:
            if hasattr(self.main_window, 'header_text_input'):
                self.main_window.header_text_input.setText(self.header_line.text())
            if hasattr(self.main_window, 'footer_text_input'):
                self.main_window.footer_text_input.setText(self.footer_line.text())
            self.main_window.x_input.setValue(self.x_spin.value())
            self.main_window.y_input.setValue(self.y_spin.value())
            self.main_window.footer_x_input.setValue(self.fx_spin.value())
            self.main_window.footer_y_input.setValue(self.fy_spin.value())
            # 切换该文件的模式为替换
            self.main_window.file_items[self.row_index].preview_mode = 'replace'
            # 如果表格存在Mode下拉，设置为替换
            try:
                mode_combo = self.main_window.file_table.cellWidget(self.row_index, 2)
                if mode_combo:
                    mode_combo.setCurrentIndex(1)
            except Exception:
                pass
            self.main_window.update_preview()
        except Exception:
            pass
        self.accept()

    def _on_reject(self):
        # 恢复原值
        try:
            self.main_window.header_text_input.setText(self._backup['header_text'])
            self.main_window.footer_text_input.setText(self._backup['footer_text'])
            self.main_window.x_input.setValue(self._backup['x'])
            self.main_window.y_input.setValue(self._backup['y'])
            self.main_window.footer_x_input.setValue(self._backup['fx'])
            self.main_window.footer_y_input.setValue(self._backup['fy'])
            self.main_window.update_preview()
        except Exception:
            pass
        self.reject()


