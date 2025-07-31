# ui_main.py
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog, QMessageBox, QTableWidget,
    QTableWidgetItem, QLabel, QHBoxLayout, QHeaderView, QComboBox, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QPainter, QPen, QFont

from PySide6.QtCore import QThread
from controller import ProcessingController
from controller import Worker  # 导入 Worker 类

from logger import logger
from font_manager import get_system_fonts
from models import PDFFileItem
from pdf_handler import merge_pdfs
from file_namer import resolve_output_filename
from position_utils import estimate_text_width, get_aligned_x_position, suggest_safe_header_y
from merge_dialog import MergeDialog
from page_number_adder import add_page_numbers
import os
import platform

def _(text):
    return QCoreApplication.translate("MainWindow", text)

class MainWindow(QMainWindow):
    """
    The main application window. Handles UI layout and delegates logic to the controller.
    Provides interface for importing PDFs, previewing and applying headers/footers, 
    and triggering PDF processing and merging.
    """
    def __init__(self):
        super().__init__()
        # Future: Replace tight coupling with signal-slot mechanism if needed
        self.setWindowTitle("DocDeck - PDF Header & Footer Tool")
        self.resize(1000, 600)
        self._setup_ui()
        # 添加菜单栏“帮助” -> “关于”
        menubar = self.menuBar()
        help_menu = menubar.addMenu(_("Help"))
        about_action = help_menu.addAction(_("About"))
        about_action.triggered.connect(self.show_about_dialog)
        self.setAcceptDrops(True)
        self.controller = ProcessingController(self)
        # 加载上次配置并应用设置
        from config import load_settings, apply_defaults
        self._apply_settings(load_settings())

    def _setup_ui(self):
        central = QWidget()
        layout = QVBoxLayout()
        header = QLabel(_("Import PDF Files"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin: 8px 0;")

        self.import_button = QPushButton(_("Select Files or Folders"))
        self.import_button.clicked.connect(self.import_files)

        mode_layout = QHBoxLayout()
        self.mode_label = QLabel(_("Header Mode:"))
        self.mode_select_combo = QComboBox()
        self.mode_select_combo.addItems([_("Filename Mode"), _("Auto Number Mode"), _("Custom Mode")])
        self.mode_select_combo.currentIndexChanged.connect(self.header_mode_changed)
        mode_layout.addWidget(self.mode_label)
        mode_layout.addWidget(self.mode_select_combo)
        layout.addWidget(header)
        layout.addWidget(self.import_button)
        layout.addLayout(mode_layout)

        # Dynamically populate font select with system fonts
        self.font_select = QComboBox()
        self.font_select.clear()
        self.font_select.addItems(get_system_fonts())

        # Auto-numbering controls
        from PySide6.QtWidgets import QGroupBox, QLineEdit
        self.auto_number_group = QGroupBox(_("Auto Number Settings"))
        auto_layout = QHBoxLayout()
        self.prefix_input = QLineEdit("Doc-")
        self.start_spin = QSpinBox()
        self.start_spin.setRange(1, 9999)
        self.start_spin.setValue(1)
        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 100)
        self.step_spin.setValue(1)
        self.suffix_input = QLineEdit("")
        auto_layout.addWidget(QLabel(_("Prefix:")))
        auto_layout.addWidget(self.prefix_input)
        auto_layout.addWidget(QLabel(_("Start #:")))
        auto_layout.addWidget(self.start_spin)
        auto_layout.addWidget(QLabel(_("Step:")))
        auto_layout.addWidget(self.step_spin)
        auto_layout.addWidget(QLabel(_("Suffix:")))
        auto_layout.addWidget(self.suffix_input)
        self.auto_number_group.setLayout(auto_layout)
        self.auto_number_group.setVisible(False)
        layout.addWidget(self.auto_number_group)

        # Connect auto-numbering inputs to header update
        self.prefix_input.textChanged.connect(lambda: self.update_header_texts(mode=self.mode))
        self.start_spin.valueChanged.connect(lambda: self.update_header_texts(mode=self.mode))
        self.step_spin.valueChanged.connect(lambda: self.update_header_texts(mode=self.mode))
        self.suffix_input.textChanged.connect(lambda: self.update_header_texts(mode=self.mode))

        # Header settings
        settings_layout = QHBoxLayout()

        self.font_label = QLabel(_("Font:"))
        # self.font_select already created above and filled

        self.font_size_label = QLabel(_("Size:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 72)
        self.font_size_spin.setValue(9)

        self.x_label = QLabel(_("X Position:"))
        self.x_input = QSpinBox()
        self.x_input.setRange(0, 1000)
        self.x_input.setValue(72)

        self.y_label = QLabel(_("Y Position:"))
        self.y_input = QSpinBox()
        self.y_input.setRange(0, 1000)
        self.y_input.setValue(suggest_safe_header_y())

        self.header_y_warning_label = QLabel("⚠️")
        self.header_y_warning_label.setToolTip(_("This position is too close to the edge and may not print correctly."))
        self.header_y_warning_label.setVisible(False)

        self.left_btn = QPushButton(_("Left"))
        self.center_btn = QPushButton(_("Center"))
        self.right_btn = QPushButton(_("Right"))
        self.left_btn.clicked.connect(lambda: self.update_alignment("left"))
        self.center_btn.clicked.connect(lambda: self.update_alignment("center"))
        self.right_btn.clicked.connect(lambda: self.update_alignment("right"))

        settings_layout.addWidget(self.font_label)
        settings_layout.addWidget(self.font_select)
        settings_layout.addWidget(self.font_size_label)
        settings_layout.addWidget(self.font_size_spin)
        settings_layout.addWidget(self.x_label)
        settings_layout.addWidget(self.x_input)
        settings_layout.addWidget(self.y_label)
        settings_layout.addWidget(self.y_input)
        settings_layout.addWidget(self.header_y_warning_label)
        settings_layout.addWidget(self.left_btn)
        settings_layout.addWidget(self.center_btn)
        settings_layout.addWidget(self.right_btn)
        layout.addLayout(settings_layout)

        # Footer settings (expanded to mirror header controls)
        footer_settings_layout = QHBoxLayout()
        self.footer_y_label = QLabel(_("Footer Y:"))
        self.footer_y_input = QSpinBox()
        self.footer_y_input.setRange(0, 1000)
        self.footer_y_input.setValue(40)
        self.footer_y_warning_label = QLabel("⚠️")
        self.footer_y_warning_label.setToolTip(_("This position is too close to the edge and may not print correctly."))
        self.footer_y_warning_label.setVisible(False)
        footer_settings_layout.addWidget(self.footer_y_label)
        footer_settings_layout.addWidget(self.footer_y_input)
        footer_settings_layout.addWidget(self.footer_y_warning_label)
        # Expanded footer controls
        self.footer_font_label = QLabel(_("Font:"))
        self.footer_font_select = QComboBox()
        self.footer_font_select.addItems(get_system_fonts())

        self.footer_font_size_label = QLabel(_("Size:"))
        self.footer_font_size_spin = QSpinBox()
        self.footer_font_size_spin.setRange(6, 72)
        self.footer_font_size_spin.setValue(9)

        self.footer_x_label = QLabel(_("X Position:"))
        self.footer_x_input = QSpinBox()
        self.footer_x_input.setRange(0, 1000)
        self.footer_x_input.setValue(72)

        self.footer_left_btn = QPushButton(_("Left"))
        self.footer_center_btn = QPushButton(_("Center"))
        self.footer_right_btn = QPushButton(_("Right"))
        self.footer_left_btn.clicked.connect(lambda: self.update_footer_alignment("left"))
        self.footer_center_btn.clicked.connect(lambda: self.update_footer_alignment("center"))
        self.footer_right_btn.clicked.connect(lambda: self.update_footer_alignment("right"))

        footer_settings_layout.addWidget(self.footer_font_label)
        footer_settings_layout.addWidget(self.footer_font_select)
        footer_settings_layout.addWidget(self.footer_font_size_label)
        footer_settings_layout.addWidget(self.footer_font_size_spin)
        footer_settings_layout.addWidget(self.footer_x_label)
        footer_settings_layout.addWidget(self.footer_x_input)
        footer_settings_layout.addWidget(self.footer_left_btn)
        footer_settings_layout.addWidget(self.footer_center_btn)
        footer_settings_layout.addWidget(self.footer_right_btn)
        layout.addLayout(footer_settings_layout)

        # Preview canvas
        self.preview_label = QLabel(_("Header Position Preview"))
        self.preview_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview_label)

        self.preview_canvas = QLabel()
        self.preview_canvas.setFixedSize(420, 595)  # scaled A4
        self.preview_canvas.setStyleSheet("background: white; border: 1px solid #ccc;")
        layout.addWidget(self.preview_canvas, alignment=Qt.AlignCenter)
        self.update_preview()

        self.file_table = QTableWidget(0, 13)
        self.file_table.setHorizontalHeaderLabels([
            _("No."), _("Filename"), _("Size (MB)"), _("Page Count"), _("Header Text"),
            _("Header Font"), _("Header Size"), _("Header X"), _("Header Y"),
            _("Footer Font"), _("Footer Size"), _("Footer Y"), _("Footer X")
        ])
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_table.setEditTriggers(QTableWidget.DoubleClicked)

        layout.addWidget(self.file_table)

        # 右键菜单绑定
        from PySide6.QtCore import Qt
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self._show_context_menu)

        # Output options
        output_layout = QHBoxLayout()
        self.output_label = QLabel(_("Output Folder:"))
        self.output_path_display = QLabel("")
        self.select_output_button = QPushButton(_("Select Output Folder"))
        self.select_output_button.clicked.connect(self.select_output_folder)
        self.start_button = QPushButton(_("Start Processing"))
        self.start_button.clicked.connect(self.start_processing)

        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_path_display, 1)
        output_layout.addWidget(self.select_output_button)
        output_layout.addWidget(self.start_button)
        layout.addLayout(output_layout)

        self.merge_checkbox = QCheckBox(_("Merge after processing"))
        layout.addWidget(self.merge_checkbox)
        self.page_number_checkbox = QCheckBox(_("Add page numbers after merge"))
        layout.addWidget(self.page_number_checkbox)

        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_label)

        central.setLayout(layout)
        self.setCentralWidget(central)

        # Connect settings changes to preview update
        self.x_input.valueChanged.connect(self.update_preview)
        self.y_input.valueChanged.connect(self.update_preview)
        self.font_size_spin.valueChanged.connect(self.update_preview)

        # Connect footer input widgets to validation and preview logic
        self.footer_y_input.valueChanged.connect(self._validate_positions)
        self.footer_font_size_spin.valueChanged.connect(self.update_preview)
        self.footer_x_input.valueChanged.connect(self.update_preview)
        self._validate_positions()

    def _show_context_menu(self, pos):
        index = self.file_table.indexAt(pos)
        if not index.isValid():
            return
        from PySide6.QtWidgets import QMenu, QInputDialog, QMessageBox
        menu = QMenu(self)
        unlock_action = menu.addAction("移除文件限制...")
        unlock_action.triggered.connect(lambda: self._attempt_unlock(index.row()))
        menu.exec(self.file_table.viewport().mapToGlobal(pos))

    def _attempt_unlock(self, row_index):
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        item = self.file_items[row_index]
        if not hasattr(self, 'output_folder') or not self.output_folder:
            QMessageBox.warning(self, _("Output Folder Not Set"),
                                _("Please select an output folder before unlocking a file."))
            return
        password, ok = QInputDialog.getText(self, "解密PDF", f"输入密码以解锁: {item.name}")
        if not ok:
            return
        # Call controller and let it determine output path; pass output_dir if available
        result = self.controller.handle_unlock_pdf(
            item=item,
            password=password,
            output_dir=getattr(self, "output_folder", None)
        )

        if result["success"]:
            QMessageBox.information(self, "解锁成功", result["message"])
            # 重新导入解锁后的文件
            new_items = self.controller.handle_file_import([result.get("output_path")])
            self.file_items.extend(new_items)
            self._populate_table_from_items(self.file_items)
        else:
            QMessageBox.warning(self, "解锁失败", result["message"])
    def update_footer_alignment(self, alignment):
        font_size = self.footer_font_size_spin.value()
        page_width = 595
        from position_utils import estimate_standard_header_width, get_aligned_x_position
        footer_width = estimate_standard_header_width(font_size)
        new_x = int(get_aligned_x_position(alignment, page_width, footer_width))
        self.footer_x_input.setValue(new_x)

    def update_alignment(self, alignment):
        if not hasattr(self, 'file_items') or not self.file_items:
            return
        font_size = self.font_size_spin.value()
        page_width = 595  # A4 portrait width in points
        from position_utils import estimate_standard_header_width
        header_width = estimate_standard_header_width(font_size)
        new_x = int(get_aligned_x_position(alignment, page_width, header_width))
        self.x_input.setValue(new_x)

    def header_mode_changed(self, index):
        if index == 0:
            self.mode = "filename"
            self.auto_number_group.setVisible(False)
            self.update_header_texts(mode="filename")
        elif index == 1:
            self.mode = "auto_number"
            self.auto_number_group.setVisible(True)
            self.update_header_texts(mode="auto_number")
        else:
            self.mode = "custom"
            self.auto_number_group.setVisible(False)
            self.update_header_texts(mode="custom")

    def update_header_texts(self, mode="filename"):
        if not hasattr(self, 'file_items'):
            return

        prefix = self.prefix_input.text()
        start = self.start_spin.value()
        step = self.step_spin.value()
        suffix = self.suffix_input.text()

        self.controller.apply_header_mode(
            file_items=self.file_items,
            mode=mode,
            numbering_prefix=prefix,
            numbering_start=start,
            numbering_step=step,
            numbering_suffix=suffix
        )

        for idx, item in enumerate(self.file_items):
            if self.file_table.item(idx, 4):
                self.file_table.item(idx, 4).setText(item.header_text)

    def import_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, _("Select PDF Files or Folders"), "", "PDF Files (*.pdf)"
        )
        if paths:
            try:
                self.file_items = self.controller.handle_file_import(paths)
                self._populate_table_from_items(self.file_items)
            except Exception as e:
                self.show_error(_("Failed to import files"), e)

    def _populate_table_from_items(self, file_items):
        self.file_table.setRowCount(0)
        for idx, item in enumerate(file_items):
            self.file_table.insertRow(idx)
            self.file_table.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))
            self.file_table.setItem(idx, 1, QTableWidgetItem(item.name))
            self.file_table.setItem(idx, 2, QTableWidgetItem(f"{item.size_mb}"))
            self.file_table.setItem(idx, 3, QTableWidgetItem(str(item.page_count)))
            header_item = QTableWidgetItem(item.header_text)
            self.file_table.setItem(idx, 4, header_item)
            self.file_table.setItem(idx, 5, QTableWidgetItem(item.header_font or ""))
            self.file_table.setItem(idx, 6, QTableWidgetItem(str(item.header_font_size or "")))
            self.file_table.setItem(idx, 7, QTableWidgetItem(str(item.header_x or "")))
            self.file_table.setItem(idx, 8, QTableWidgetItem(str(item.header_y or "")))
            # 页脚相关三列
            self.file_table.setItem(idx, 9, QTableWidgetItem(item.footer_font or ""))
            self.file_table.setItem(idx, 10, QTableWidgetItem(str(item.footer_font_size or "")))
            self.file_table.setItem(idx, 11, QTableWidgetItem(str(item.footer_y or "")))
            # 页脚X
            self.file_table.setItem(idx, 12, QTableWidgetItem(str(item.footer_x or "")))

        # 异步字体推荐逻辑
        from PySide6.QtCore import QTimer
        def recommend_fonts():
            # The controller.get_recommended_fonts now handles all internal extraction and logic.
            recommended_fonts = self.controller.get_recommended_fonts([item.path for item in file_items[:3]])
            if recommended_fonts:
                existing_fonts = [self.font_select.itemText(i) for i in range(self.font_select.count())]
                for font in reversed(recommended_fonts):
                    if font not in existing_fonts:
                        self.font_select.insertItem(0, font)
                if recommended_fonts and recommended_fonts[0] == "---":
                    self.font_select.insertSeparator(len(recommended_fonts))
        QTimer.singleShot(200, recommend_fonts)


    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, _("Select Output Directory"))
        if folder:
            self.output_path_display.setText(folder)
            self.output_folder = folder

    def start_processing(self):
        # Ensure self.mode is defined before being used
        self.mode = getattr(self, 'mode', 'filename')

        if not hasattr(self, 'file_items') or not self.file_items:
            QMessageBox.warning(self, _("No Files"), _("Please import PDF files first."))
            return
        if not hasattr(self, 'output_folder') or not self.output_folder:
            QMessageBox.warning(self, _("No Output Folder"), _("Please select an output folder."))
            return

        # ▼▼▼ 新增：同步表格编辑到数据模型（包括header和footer） ▼▼▼
        try:
            for row in range(self.file_table.rowCount()):
                self.file_items[row].header_text = self.file_table.item(row, 4).text()
                self.file_items[row].header_font = self.file_table.item(row, 5).text()
                try:
                    self.file_items[row].header_font_size = int(self.file_table.item(row, 6).text() or 0)
                    self.file_items[row].header_x = int(self.file_table.item(row, 7).text() or 0)
                    self.file_items[row].header_y = int(self.file_table.item(row, 8).text() or 0)
                except Exception as e:
                    logger.warning("Invalid per-file header settings", exc_info=True)
                # 同步footer相关字段
                try:
                    self.file_items[row].footer_font = self.file_table.item(row, 9).text() or ""
                    self.file_items[row].footer_font_size = int(self.file_table.item(row, 10).text() or 0)
                    self.file_items[row].footer_y = int(self.file_table.item(row, 11).text() or 0)
                    self.file_items[row].footer_x = int(self.file_table.item(row, 12).text() or 0)
                except Exception as e:
                    logger.warning("Invalid per-file footer settings", exc_info=True)
        except Exception as e:
            logger.error("同步表格数据时出错", exc_info=True)
        # ▲▲▲ 新增完毕 ▲▲▲

        # Prepare header and footer settings dicts
        header_settings = {
            "font_name": self.font_select.currentText(),
            "font_size": self.font_size_spin.value(),
            "x": self.x_input.value(),
            "y": self.y_input.value()
        }
        footer_settings = {
            "font_name": self.footer_font_select.currentText(),
            "font_size": self.footer_font_size_spin.value(),
            "x": self.footer_x_input.value(),
            "y": self.footer_y_input.value()
        }

        self.start_button.setEnabled(False)
        self.progress_label.setText(_("Processing... (0%)"))

        self.thread = QThread()
        self.worker = Worker(self.controller, self.file_items, self.output_folder, header_settings, footer_settings)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.signals.finished.connect(self.on_processing_finished)
        self.worker.signals.progress.connect(self.update_progress)
        self.worker.signals.finished.connect(self.thread.quit)
        self.worker.signals.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def handle_merge_confirmation(self, ordered_paths):
        save_path, _ = QFileDialog.getSaveFileName(self, _("Save Merged PDF"), "", "PDF Files (*.pdf)")
        if not save_path:
            return
        success, err = merge_pdfs(ordered_paths, save_path)
        if success:
            if self.page_number_checkbox.isChecked():
                try:
                    add_page_numbers(
                        input_pdf=save_path,
                        output_pdf=save_path,
                        font_name=self.footer_font_select.currentText(),
                        font_size=self.footer_font_size_spin.value(),
                        x=self.footer_x_input.value(),
                        y=self.footer_y_input.value()
                    )
                    QMessageBox.information(self, _("Merged"),
                        _("Files merged and page numbers added successfully:\n") + save_path)
                except Exception as e:
                    self.progress_label.setText(_("Failed to add page numbers"))
                    logger.error("Failed to add page numbers", exc_info=True)
                    QMessageBox.warning(self, _("Page Number Error"), str(e))
            else:
                QMessageBox.information(self, _("Merged"),
                    _("Files merged successfully:\n") + save_path)
        else:
            QMessageBox.warning(self, _("Merge Failed"), err)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not event.mimeData().hasUrls():
            return
        try:
            paths = [url.toLocalFile() for url in event.mimeData().urls()]
            self.file_items = self.controller.handle_file_import(paths)
            self._populate_table_from_items(self.file_items)
            event.acceptProposedAction()
        except Exception as e:
            self.show_error(_("Failed to handle drag-and-drop import"), e)
    def update_preview(self):
        from PySide6.QtGui import QPixmap
        canvas = QPixmap(420, 595)
        canvas.fill(Qt.white)
        painter = QPainter(canvas)
        painter.setPen(QPen(Qt.black))
        font = QFont(self.font_select.currentText(), self.font_size_spin.value())
        painter.setFont(font)
        preview_scale_x = 0.7  # scale input to preview canvas width (595pt to 420px)
        x = self.x_input.value() * preview_scale_x
        y = self.y_input.value()       # already near 1:1 on height
        painter.drawText(int(x), int(y), "示例 Header")  # preview text
        # Draw footer preview
        footer_font = QFont(self.footer_font_select.currentText(), self.footer_font_size_spin.value())
        painter.setFont(footer_font)
        fx = self.footer_x_input.value() * preview_scale_x
        fy = self.footer_y_input.value()
        painter.drawText(int(fx), int(fy), "示例 Footer")
        painter.end()
        self.preview_canvas.setPixmap(canvas)
    def _validate_positions(self):
        from position_utils import is_out_of_print_safe_area

        header_y = self.y_input.value()
        is_header_unsafe = is_out_of_print_safe_area(header_y, top=True)
        self.header_y_warning_label.setVisible(is_header_unsafe)

        footer_y = self.footer_y_input.value()
        is_footer_unsafe = is_out_of_print_safe_area(footer_y, top=False)
        self.footer_y_warning_label.setVisible(is_footer_unsafe)
    def _apply_settings(self, settings):
        if not settings:
            return
        from config import apply_defaults
        try:
            settings = apply_defaults(settings)
        except Exception as e:
            logger.warning("Failed to apply default settings: %s", e)
            return
        try:
            self.font_select.setCurrentText(settings.get("font", self.font_select.currentText()))
            self.font_size_spin.setValue(settings.get("font_size", self.font_size_spin.value()))
            self.x_input.setValue(settings.get("x", self.x_input.value()))
            self.y_input.setValue(settings.get("y", self.y_input.value()))
            self.footer_font_select.setCurrentText(settings.get("footer_font", self.footer_font_select.currentText()))
            self.footer_font_size_spin.setValue(settings.get("footer_font_size", self.footer_font_size_spin.value()))
            self.footer_x_input.setValue(settings.get("footer_x", self.footer_x_input.value()))
            self.footer_y_input.setValue(settings.get("footer_y", self.footer_y_input.value()))
            self.merge_checkbox.setChecked(settings.get("merge", self.merge_checkbox.isChecked()))
            self.page_number_checkbox.setChecked(settings.get("page_number", self.page_number_checkbox.isChecked()))
        except Exception as e:
            logger.warning("Failed to apply settings: %s", e)

    def closeEvent(self, event):
        from config import save_settings
        settings = {
            "font": self.font_select.currentText(),
            "font_size": self.font_size_spin.value(),
            "x": self.x_input.value(),
            "y": self.y_input.value(),
            "footer_font": self.footer_font_select.currentText(),
            "footer_font_size": self.footer_font_size_spin.value(),
            "footer_x": self.footer_x_input.value(),
            "footer_y": self.footer_y_input.value(),
            "merge": self.merge_checkbox.isChecked(),
            "page_number": self.page_number_checkbox.isChecked()
        }
        save_settings(settings)
        event.accept()
    def show_error(self, message, exception=None):
        self.progress_label.setText(message)
        if exception:
            logger.error(message, exc_info=True)
            self.statusBar().showMessage(str(exception))
        QMessageBox.critical(self, _("Error"), message)
    def update_progress(self, current, total, filename):
        percent = int((current / total) * 100)
        self.progress_label.setText(f"{_('Processing...')} ({percent}%) - {filename}")

    def on_processing_finished(self, results):
        self.start_button.setEnabled(True)
        self.processed_paths = []
        failed = []
        for result in results:
            if result["success"]:
                self.processed_paths.append(result["output"])
            else:
                failed.append((result["input"], result["error"]))

        self.progress_label.setText(_("Completed {} files").format(len(self.processed_paths)))

        if failed:
            msg = "\n".join([f"{os.path.basename(name)}: {err}" for name, err in failed])
            self.progress_label.setText(_("Some files failed. See details."))
            QMessageBox.warning(self, _("Some Files Failed"), msg)
        else:
            QMessageBox.information(self, _("Done"), _("All files processed successfully."))
            # Also clear the progress label if all files succeeded
            self.progress_label.setText("")
            if self.merge_checkbox.isChecked():
                dlg = MergeDialog(self.processed_paths, self)
                dlg.merge_confirmed.connect(self.handle_merge_confirmation)
                dlg.exec()
    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "About DocDeck",
            "DocDeck - PDF Header & Footer Tool\n"
            "Version 1.0beta\n\n"
            "Author: 木小樨\n"
            "Project Homepage:\n"
            "https://hs2wxdogy2.feishu.cn/wiki/Kjv3wQfV5iKpGXkQ8aCcOkj6nVf"
        )