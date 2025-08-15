# ui_main.py
import os
import pathlib
from typing import Dict, Any
from models import PDFFileItem, EncryptionStatus
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog, QMessageBox, QTableWidget,
    QTableWidgetItem, QLabel, QHBoxLayout, QHeaderView, QComboBox, QSpinBox, QCheckBox,
    QGroupBox, QGridLayout, QLineEdit, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, QCoreApplication, QThread, QTimer
from PySide6.QtGui import QPainter, QPen, QFont, QPixmap

from controller import ProcessingController, Worker
from font_manager import get_system_fonts
from pdf_handler import merge_pdfs, add_page_numbers
from position_utils import suggest_safe_header_y, is_out_of_print_safe_area
from merge_dialog import MergeDialog
from logger import logger

def _(text: str) -> str:
    """为国际化提供翻译函数"""
    return QCoreApplication.translate("MainWindow", text)

class MainWindow(QMainWindow):
    """
    应用程序主窗口。
    - 处理UI布局和用户交互。
    - 将业务逻辑委托给ProcessingController。
    - 提供PDF导入、设置页眉页脚、预览和触发处理的功能。
    """
    MODE_FILENAME = "filename"
    MODE_AUTO_NUMBER = "auto_number"
    MODE_CUSTOM = "custom"

    def __init__(self):
        super().__init__()
        self._font_linked_once = False
        self.mode = self.MODE_FILENAME
        self.file_items = []
        self.settings_map: Dict[str, QWidget] = {}

        self.setWindowTitle("DocDeck - PDF Header & Footer Tool")
        self.resize(1100, 850)
        self.controller = ProcessingController(self)
        
        self._setup_ui()
        self._setup_menu()
        self._map_settings_to_widgets()
        self._connect_signals()

        self.setAcceptDrops(True)
        from config import load_settings
        self._apply_settings(load_settings())
        self._update_ui_state()

    # --- UI Setup Methods ---
    def _setup_ui(self):
        """初始化和布局所有UI控件"""
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        top_layout = self._create_top_bar()
        self.auto_number_group = self._create_auto_number_group()
        settings_group = self._create_settings_grid_group()
        table_layout = self._create_table_area()
        output_layout = self._create_output_layout()

        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.auto_number_group)
        main_layout.addWidget(settings_group)
        main_layout.addLayout(table_layout)
        main_layout.addLayout(output_layout)
        
        self.setCentralWidget(central_widget)

    def _create_top_bar(self) -> QHBoxLayout:
        """创建顶部包含导入、清空和模式选择的工具栏"""
        layout = QHBoxLayout()
        self.import_button = QPushButton(_("Import Files or Folders"))
        self.clear_button = QPushButton(_("Clear List"))
        mode_label = QLabel(_("Header Mode:"))
        self.mode_select_combo = QComboBox()
        self.mode_select_combo.addItems([_("Filename Mode"), _("Auto Number Mode"), _("Custom Mode")])
        layout.addWidget(self.import_button); layout.addWidget(self.clear_button)
        layout.addStretch(); layout.addWidget(mode_label); layout.addWidget(self.mode_select_combo)
        return layout

    def _create_auto_number_group(self) -> QGroupBox:
        """创建自动编号设置的控件组"""
        group = QGroupBox(_("Auto Number Settings"))
        layout = QHBoxLayout()
        self.prefix_input = QLineEdit("Doc-")
        self.start_spin = QSpinBox(); self.start_spin.setRange(1, 9999); self.start_spin.setValue(1)
        self.step_spin = QSpinBox(); self.step_spin.setRange(1, 100); self.step_spin.setValue(1)
        self.digits_spin = QSpinBox(); self.digits_spin.setRange(1, 6); self.digits_spin.setValue(3)
        self.suffix_input = QLineEdit("")
        
        layout.addWidget(QLabel(_("Prefix:"))); layout.addWidget(self.prefix_input)
        layout.addWidget(QLabel(_("Start #:"))); layout.addWidget(self.start_spin)
        layout.addWidget(QLabel(_("Step:"))); layout.addWidget(self.step_spin)
        layout.addWidget(QLabel(_("Digits:"))); layout.addWidget(self.digits_spin)
        layout.addWidget(QLabel(_("Suffix:"))); layout.addWidget(self.suffix_input)
        group.setLayout(layout)
        group.setVisible(False)
        return group

    def _create_settings_grid_group(self) -> QGroupBox:
        """创建页眉页脚的网格布局设置控件组（新版：设置与预览横向并排，预览为横条，仅Header/Footer）"""
        group = QGroupBox(_("Header & Footer Settings"))
        group.setObjectName("Header & Footer Settings")
        grid = QGridLayout()
        grid.setColumnStretch(1, 1); grid.setColumnStretch(2, 1); grid.setColumnStretch(3, 1)

        # 设置控件部分
        grid.addWidget(QLabel("<b>" + _("Settings") + "</b>"), 0, 0, Qt.AlignRight)
        grid.addWidget(QLabel("<b>" + _("Header") + "</b>"), 0, 1, Qt.AlignCenter)
        grid.addWidget(QLabel("<b>" + _("Footer") + "</b>"), 0, 2, Qt.AlignCenter)
        
        self.font_select = QComboBox(); self.font_select.addItems(get_system_fonts())
        self.footer_font_select = QComboBox(); self.footer_font_select.addItems(get_system_fonts())
        self.font_size_spin = QSpinBox(); self.font_size_spin.setRange(6, 72); self.font_size_spin.setValue(9)
        self.footer_font_size_spin = QSpinBox(); self.footer_font_size_spin.setRange(6, 72); self.footer_font_size_spin.setValue(9)
        grid.addWidget(QLabel(_("Font:")), 1, 0, Qt.AlignRight); grid.addWidget(self.font_select, 1, 1); grid.addWidget(self.footer_font_select, 1, 2)
        grid.addWidget(QLabel(_("Size:")), 2, 0, Qt.AlignRight); grid.addWidget(self.font_size_spin, 2, 1); grid.addWidget(self.footer_font_size_spin, 2, 2)
        
        self.x_input = QSpinBox(); self.x_input.setRange(0, 1000); self.x_input.setValue(72)
        self.footer_x_input = QSpinBox(); self.footer_x_input.setRange(0, 1000); self.footer_x_input.setValue(72)
        self.y_input = QSpinBox(); self.y_input.setRange(0, 1000); self.y_input.setValue(suggest_safe_header_y())
        self.header_y_warning_label = self._create_warning_label()
        header_y_layout = QHBoxLayout(); header_y_layout.addWidget(self.y_input); header_y_layout.addWidget(self.header_y_warning_label)
        self.footer_y_input = QSpinBox(); self.footer_y_input.setRange(0, 1000); self.footer_y_input.setValue(40)
        self.footer_y_warning_label = self._create_warning_label()
        footer_y_layout = QHBoxLayout(); footer_y_layout.addWidget(self.footer_y_input); footer_y_layout.addWidget(self.footer_y_warning_label)
        grid.addWidget(QLabel(_("X Position:")), 3, 0, Qt.AlignRight); grid.addWidget(self.x_input, 3, 1); grid.addWidget(self.footer_x_input, 3, 2)
        grid.addWidget(QLabel(_("Y Position:")), 4, 0, Qt.AlignRight); grid.addLayout(header_y_layout, 4, 1); grid.addLayout(footer_y_layout, 4, 2)

        self.left_btn = QPushButton(_("Left")); self.center_btn = QPushButton(_("Center")); self.right_btn = QPushButton(_("Right"))
        header_align_layout = QHBoxLayout(); header_align_layout.addWidget(self.left_btn); header_align_layout.addWidget(self.center_btn); header_align_layout.addWidget(self.right_btn)
        self.footer_left_btn = QPushButton(_("Left")); self.footer_center_btn = QPushButton(_("Center")); self.footer_right_btn = QPushButton(_("Right"))
        footer_align_layout = QHBoxLayout(); footer_align_layout.addWidget(self.footer_left_btn); footer_align_layout.addWidget(self.footer_center_btn); footer_align_layout.addWidget(self.footer_right_btn)
        grid.addWidget(QLabel(_("Alignment:")), 5, 0, Qt.AlignRight); grid.addLayout(header_align_layout, 5, 1); grid.addLayout(footer_align_layout, 5, 2)

        grid.addWidget(QLabel(_("Global Footer Text:")), 6, 0, Qt.AlignRight)
        self.global_footer_text = QLineEdit(_("Page {page} of {total}"))
        self.global_footer_text.setToolTip(_("Use {page} for current page, {total} for total pages."))
        self.apply_footer_template_button = QPushButton(_("Apply to All"))
        footer_template_layout = QHBoxLayout(); footer_template_layout.addWidget(self.global_footer_text); footer_template_layout.addWidget(self.apply_footer_template_button)
        grid.addLayout(footer_template_layout, 6, 1, 1, 2)

        # 新：预览区域横向长条，仅Header/Footer
        preview_group = QVBoxLayout()
        preview_label = QLabel(_("Header/Footer Preview")); preview_label.setAlignment(Qt.AlignCenter)
        self.preview_canvas = QLabel(); self.preview_canvas.setFixedSize(600, 80)
        self.preview_canvas.setStyleSheet("background: white; border: 1px solid #ccc;")
        preview_group.addWidget(preview_label)
        preview_group.addWidget(self.preview_canvas)

        # 结构化模式开关
        self.structured_checkbox = QCheckBox(_("Structured mode (Acrobat-friendly)"))
        self.structured_checkbox.setChecked(False)
        grid.addWidget(self.structured_checkbox, 7, 0, 1, 3)

        # 横向布局：设置控件 + 预览
        horizontal_layout = QHBoxLayout()
        horizontal_layout.addLayout(grid, 3)
        horizontal_layout.addLayout(preview_group, 2)

        group.setLayout(horizontal_layout)
        return group

    def _create_table_area(self) -> QHBoxLayout:
        """创建文件列表及右侧的控制按钮"""
        layout = QHBoxLayout()
        self.file_table = QTableWidget(0, 6)
        self.file_table.setHorizontalHeaderLabels([_("No."), _("Filename"), _("Size (MB)"), _("Page Count"), _("Header Text"), _("Footer Text")])
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_table.setEditTriggers(QTableWidget.DoubleClicked)
        # 表格编辑或选择变化时，实时刷新预览
        self.file_table.itemChanged.connect(lambda *_: self.update_preview())
        self.file_table.itemSelectionChanged.connect(self.update_preview)
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        
        controls_layout = QVBoxLayout()
        self.move_up_button = QPushButton(_("Move Up"))
        self.move_down_button = QPushButton(_("Move Down"))
        self.remove_button = QPushButton(_("Remove"))
        controls_layout.addStretch()
        controls_layout.addWidget(self.move_up_button)
        controls_layout.addWidget(self.move_down_button)
        controls_layout.addWidget(self.remove_button)
        controls_layout.addStretch()
        
        layout.addWidget(self.file_table, 10)
        layout.addLayout(controls_layout, 1)
        return layout

    def _create_output_layout(self) -> QVBoxLayout:
        """创建输出和执行按钮的布局"""
        layout = QVBoxLayout()
        h_layout = QHBoxLayout()
        
        default_download_path = str(pathlib.Path.home() / "Downloads")
        self.output_path_display = QLabel(default_download_path); self.output_path_display.setStyleSheet("color: grey;")
        self.output_folder = default_download_path
        
        self.select_output_button = QPushButton(_("Select Output Folder"))
        self.start_button = QPushButton(_("Start Processing")); self.start_button.setStyleSheet("font-weight: bold; padding: 5px;")

        h_layout.addWidget(QLabel(_("Output Folder:"))); h_layout.addWidget(self.output_path_display, 1)
        h_layout.addWidget(self.select_output_button); h_layout.addWidget(self.start_button)
        
        checkbox_layout = QHBoxLayout()
        self.merge_checkbox = QCheckBox(_("Merge after processing"))
        self.page_number_checkbox = QCheckBox(_("Add page numbers after merge"))
        checkbox_layout.addWidget(self.merge_checkbox); checkbox_layout.addWidget(self.page_number_checkbox)
        checkbox_layout.addStretch()

        self.progress_label = QLabel(""); self.progress_label.setAlignment(Qt.AlignCenter)

        layout.addLayout(h_layout); layout.addLayout(checkbox_layout); layout.addWidget(self.progress_label)
        return layout
    
    def _create_warning_label(self) -> QLabel:
        label = QLabel("⚠️"); label.setToolTip(_("This position is too close to the edge...")); label.setVisible(False)
        return label

    def _setup_menu(self):
        menubar = self.menuBar(); help_menu = menubar.addMenu(_("Help"))
        about_action = help_menu.addAction(_("About")); about_action.triggered.connect(self.show_about_dialog)

    def _map_settings_to_widgets(self):
        """将设置项键名映射到UI控件，用于简化配置的存取"""
        self.settings_map = {
            "header_font_name": self.font_select, "header_font_size": self.font_size_spin,
            "header_x": self.x_input, "header_y": self.y_input,
            "footer_font_name": self.footer_font_select, "footer_font_size": self.footer_font_size_spin,
            "footer_x": self.footer_x_input, "footer_y": self.footer_y_input,
            "merge": self.merge_checkbox, "page_numbering": self.page_number_checkbox,
            "structured": self.structured_checkbox,
        }

    def _connect_signals(self):
        """使用循环和映射来连接信号与槽，减少重复代码"""
        button_slots = {
            self.import_button: self.import_files, self.clear_button: self.clear_file_list,
            self.move_up_button: self.move_item_up, self.move_down_button: self.move_item_down,
            self.apply_footer_template_button: self.apply_global_footer_template,
            self.select_output_button: self.select_output_folder, self.start_button: self.start_processing,
            self.left_btn: lambda: self._update_alignment("left", self.font_size_spin, self.x_input),
            self.center_btn: lambda: self._update_alignment("center", self.font_size_spin, self.x_input),
            self.right_btn: lambda: self._update_alignment("right", self.font_size_spin, self.x_input),
            self.footer_left_btn: lambda: self._update_alignment("left", self.footer_font_size_spin, self.footer_x_input),
            self.footer_center_btn: lambda: self._update_alignment("center", self.footer_font_size_spin, self.footer_x_input),
            self.footer_right_btn: lambda: self._update_alignment("right", self.footer_font_size_spin, self.footer_x_input),
        }
        for btn, slot in button_slots.items(): btn.clicked.connect(slot)

        self.remove_button.clicked.connect(self.remove_selected_items)

        self.mode_select_combo.currentIndexChanged.connect(self.header_mode_changed)
        self.file_table.customContextMenuRequested.connect(self._show_context_menu)
        
        auto_number_controls = [self.prefix_input, self.suffix_input, self.start_spin, self.step_spin, self.digits_spin]
        for control in auto_number_controls:
            if isinstance(control, QLineEdit): control.textChanged.connect(self.update_header_texts)
            else: control.valueChanged.connect(self.update_header_texts)

        preview_controls = [self.font_select, self.footer_font_select, self.font_size_spin, self.footer_font_size_spin, self.x_input, self.footer_x_input, self.structured_checkbox]
        for control in preview_controls:
            if isinstance(control, QComboBox): control.currentTextChanged.connect(self.update_preview)
            else:
                if hasattr(control, 'valueChanged'):
                    control.valueChanged.connect(self.update_preview)
                elif hasattr(control, 'stateChanged'):
                    control.stateChanged.connect(self.update_preview)
        
        validation_controls = [self.y_input, self.footer_y_input]
        for control in validation_controls:
            control.valueChanged.connect(self.update_preview)
            control.valueChanged.connect(self._validate_positions)

        self.font_select.currentTextChanged.connect(self._on_font_changed)
        self.footer_font_select.currentTextChanged.connect(self._on_font_changed)

    def remove_selected_items(self):
        selected_rows = sorted([r.row() for r in self.file_table.selectionModel().selectedRows()], reverse=True)
        for row in selected_rows:
            self.file_items.pop(row)
            self.file_table.removeRow(row)
        self._update_ui_state()

    # --- UI State and Interaction Methods ---
    def _set_controls_enabled(self, enabled: bool):
        """启用或禁用所有输入控件"""
        self.import_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
        self.file_table.setEnabled(enabled)
        self.move_up_button.setEnabled(enabled)
        self.move_down_button.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        
        # <<< FIX: Correctly iterate over widget types to call findChildren >>>
        widget_types_to_toggle = (QPushButton, QComboBox, QSpinBox, QLineEdit, QCheckBox)
        
        groups = [self.auto_number_group, self.centralWidget().findChild(QGroupBox, "Header & Footer Settings")]
        
        for group in groups:
            if group:
                for widget_type in widget_types_to_toggle:
                    for widget in group.findChildren(widget_type):
                        # The start_button is not in these groups, so no special check needed.
                        widget.setEnabled(enabled)
    
    def _update_ui_state(self):
        """根据当前是否有文件来更新UI控件的启用状态"""
        has_files = bool(self.file_items)
        self._set_controls_enabled(True)
        
        settings_group = self.centralWidget().findChild(QGroupBox, "Header & Footer Settings")
        if has_files:
            if settings_group:
                settings_group.setEnabled(True)
        else:
            widgets_to_disable = [self.clear_button, self.start_button, self.move_up_button, self.move_down_button, self.auto_number_group]
            if settings_group:
                widgets_to_disable.append(settings_group)
            for widget in widgets_to_disable:
                if widget:
                    widget.setEnabled(False)
        
        self.start_button.setEnabled(has_files)

    def _on_font_changed(self, text: str):
        """当字体改变时，如果是首次，则同步页眉和页脚的字体选择。"""
        if not self._font_linked_once:
            self._font_linked_once = True
            sender = self.sender()
            
            self.font_select.blockSignals(True); self.footer_font_select.blockSignals(True)
            if sender == self.font_select: self.footer_font_select.setCurrentText(text)
            else: self.font_select.setCurrentText(text)
            self.font_select.blockSignals(False); self.footer_font_select.blockSignals(False)

    def _show_context_menu(self, pos):
        """显示文件列表的右键菜单"""
        index = self.file_table.indexAt(pos)
        if not index.isValid():
            return
        menu = QMenu(self)
        unlock_action = menu.addAction("移除文件限制...")
        unlock_action.triggered.connect(lambda: self._attempt_unlock(index.row()))
        menu.exec(self.file_table.viewport().mapToGlobal(pos))

    def _attempt_unlock(self, row_index: int):
        """尝试解密选定的PDF文件，并提供详细错误反馈"""
        item = self.file_items[row_index]
        if not self.output_folder:
            QMessageBox.warning(self, _("Output Folder Not Set"), _("Please select an output folder..."))
            return
        encryption_status = getattr(item, "encryption_status", "ok")
        if encryption_status == "locked":
            QMessageBox.warning(self, _("Locked File"), _("This file is encrypted and cannot be opened without a password."))
            password, ok = QInputDialog.getText(self, _("Decrypt PDF"), f"{item.name}\n\n{_('Please enter the password:')}")
            if not ok:
                return
        elif encryption_status == "restricted":
            response = QMessageBox.question(
                self, _("Restricted PDF"),
                _("This PDF is restricted and cannot be modified.\nDo you want to attempt automatic unlocking?"),
                QMessageBox.Yes | QMessageBox.No
            )
            if response == QMessageBox.No:
                return
            # Always use the UI's selected output folder
            output_dir = self.output_folder
            result = self.controller.handle_unlock_pdf(item=item, password="", output_dir=output_dir)
            if result["success"]:
                QMessageBox.information(self, _("Unlock Success"), result["message"])
                if result.get("output_path"):
                    self.progress_label.setText(_("Unlocked file saved to: ") + result.get("output_path", "") + " (" + output_dir + ")")
                    self.output_path_display.setText(output_dir)
                    new_items = self.controller.handle_file_import([result["output_path"]])
                    if new_items:
                        new_items[0].unlocked_path = result.get("output_path", None)
                        self.file_items[row_index] = new_items[0]
                        self._populate_table_from_items()
            else:
                self.show_error(_("Unlock Failed"), Exception(result["message"]))
            return
        else:
            return  # Not encrypted or already handled

        # 密码验证流程
        attempts = 3
        while attempts > 0:
            output_dir = self.output_folder
            result = self.controller.handle_unlock_pdf(item=item, password=password, output_dir=output_dir)
            if result["success"]:
                QMessageBox.information(self, _("Unlock Success"), result["message"])
                if result.get("output_path"):
                    # Show unlock file path in progress label
                    self.progress_label.setText(_("Unlocked file saved to: ") + result.get("output_path", "") + " (" + output_dir + ")")
                    self.output_path_display.setText(output_dir)
                    new_items = self.controller.handle_file_import([result["output_path"]])
                    if new_items:
                        new_items[0].unlocked_path = result.get("output_path", None)
                        self.file_items[row_index] = new_items[0]
                        self._populate_table_from_items()
                return
            else:
                attempts -= 1
                if attempts == 0:
                    choice = QMessageBox.question(
                        self, _("Unlock Failed"),
                        _("Password incorrect. Would you like to attempt forced unlock without password?"),
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if choice == QMessageBox.Yes:
                        output_dir = self.output_folder
                        result = self.controller.handle_unlock_pdf(item=item, password="", output_dir=output_dir)
                        if result["success"]:
                            QMessageBox.information(self, _("Unlock Success"), result["message"])
                            if result.get("output_path"):
                                # Show unlock file path in progress label
                                self.progress_label.setText(_("Unlocked file saved to: ") + result.get("output_path", "") + " (" + output_dir + ")")
                                self.output_path_display.setText(output_dir)
                                new_items = self.controller.handle_file_import([result["output_path"]])
                                if new_items:
                                    new_items[0].unlocked_path = result.get("output_path", None)
                                    self.file_items[row_index] = new_items[0]
                                    self._populate_table_from_items()
                        else:
                            self.show_error(_("Unlock Failed"), Exception(result["message"]))
                    return
                else:
                    password, ok = QInputDialog.getText(self, _("Retry Password"), f"{item.name}\n\n{_('Incorrect password. Try again:')}")
                    if not ok:
                        return

    def _update_alignment(self, alignment: str, font_size_spin: QSpinBox, x_input: QSpinBox):
        """根据对齐方式更新X坐标（通用函数）"""
        from position_utils import estimate_standard_header_width, get_aligned_x_position
        text_width = estimate_standard_header_width(font_size_spin.value())
        new_x = int(get_aligned_x_position(alignment, 595, text_width))
        x_input.setValue(new_x)
        self.update_preview()

    def _reset_auto_number_fields(self):
        """重置自动编号相关的输入控件"""
        self.prefix_input.setText("Doc-"); self.start_spin.setValue(1)
        self.step_spin.setValue(1); self.digits_spin.setValue(3); self.suffix_input.clear()

    # --- Core Logic Methods ---
    def header_mode_changed(self, index: int):
        """处理页眉模式切换，并清理UI状态"""
        modes = [self.MODE_FILENAME, self.MODE_AUTO_NUMBER, self.MODE_CUSTOM]
        self.mode = modes[index]
        self.auto_number_group.setVisible(self.mode == self.MODE_AUTO_NUMBER)
        if self.mode != self.MODE_AUTO_NUMBER: self._reset_auto_number_fields()
        self.update_header_texts()

    def update_header_texts(self):
        """根据当前模式更新所有文件的页眉文本"""
        if not self.file_items: return
        self.controller.apply_header_mode(
            file_items=self.file_items, mode=self.mode,
            numbering_prefix=self.prefix_input.text(), numbering_start=self.start_spin.value(),
            numbering_step=self.step_spin.value(), numbering_suffix=self.suffix_input.text(),
            numbering_digits=self.digits_spin.value()
        )
        self._populate_table_from_items()
        self.update_preview()

    def import_files(self):
        """打开文件对话框以导入PDF文件"""
        paths, _ = QFileDialog.getOpenFileNames(self, _("Select PDF Files or Folders"), "", "PDF Files (*.pdf)")
        if paths: self._process_imported_paths(paths)

    def clear_file_list(self):
        """清空文件列表"""
        self.file_items.clear()
        self._populate_table_from_items()

    def _populate_table_from_items(self):
        """用文件数据填充表格"""
        self.file_table.setRowCount(0)
        for idx, item in enumerate(self.file_items):
            if not hasattr(item, "name") or not hasattr(item, "size_mb"):
                continue
            self.file_table.insertRow(idx)
            name_item = QTableWidgetItem(item.name); name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled); name_item.setToolTip(item.name)
            self.file_table.setItem(idx, 0, QTableWidgetItem(str(idx + 1)))
            self.file_table.setItem(idx, 1, name_item)
            self.file_table.setItem(idx, 2, QTableWidgetItem(f"{item.size_mb:.2f}"))
            self.file_table.setItem(idx, 3, QTableWidgetItem(str(item.page_count)))
            self.file_table.setItem(idx, 4, QTableWidgetItem(item.header_text))
            self.file_table.setItem(idx, 5, QTableWidgetItem(item.footer_text or ""))
        
        self._update_ui_state()
        if self.file_items: self._font_linked_once = False

    def _recommend_fonts(self):
        """从文件中提取并推荐字体"""
        if not self.file_items: return
        recommended = self.controller.get_recommended_fonts_cached([item.path for item in self.file_items[:3]])
        if recommended:
            existing = [self.font_select.itemText(i) for i in range(self.font_select.count())]
            for font in reversed(recommended):
                if font not in existing: self.font_select.insertItem(0, font)
            if recommended and recommended[0] == "---": self.font_select.insertSeparator(len(recommended))

    def select_output_folder(self):
        """选择输出文件夹"""
        folder = QFileDialog.getExistingDirectory(self, _("Select Output Directory"))
        if folder: self.output_path_display.setText(folder); self.output_folder = folder

    def move_item_up(self):
        """上移选中的文件"""
        selected_rows = sorted([r.row() for r in self.file_table.selectionModel().selectedRows()], reverse=True)
        for row in selected_rows:
            if row > 0:
                self.file_items.insert(row - 1, self.file_items.pop(row))
        self._populate_table_from_items()

    def move_item_down(self):
        """下移选中的文件"""
        selected_rows = sorted([r.row() for r in self.file_table.selectionModel().selectedRows()])
        for row in selected_rows:
            if row < len(self.file_items) - 1:
                self.file_items.insert(row + 1, self.file_items.pop(row))
        self._populate_table_from_items()

    def apply_global_footer_template(self):
        """将全局页脚模板应用到所有文件"""
        template = self.global_footer_text.text()
        if not template: return
        for item in self.file_items:
            item.footer_text = template
        self._populate_table_from_items()

    def start_processing(self):
        """开始批处理流程"""
        if not self.file_items:
            QMessageBox.warning(self, _("No Files"), _("Please import PDF files first."))
            return
        if not self.output_folder:
            QMessageBox.warning(self, _("No Output Folder"), _("Please select an output folder."))
            return

        # 先同步 file_items 的 header_text 和 footer_text
        try:
            for row in range(self.file_table.rowCount()):
                self.file_items[row].header_text = self.file_table.item(row, 4).text()
                self.file_items[row].footer_text = self.file_table.item(row, 5).text()
        except Exception as e:
            logger.error("Error syncing data from table", exc_info=True)

        # 然后再检查加密
        if not self._check_for_encrypted_files():
            self._set_controls_enabled(True)
            return

        self._set_controls_enabled(False)

        settings = self._get_current_settings()
        header_settings = {k.replace('header_', ''): v for k, v in settings.items() if k.startswith('header_')}
        footer_settings = {k.replace('footer_', ''): v for k, v in settings.items() if k.startswith('footer_')}
        # 传递结构化模式参数
        if settings.get('structured'):
            header_settings['structured'] = True
            footer_settings['structured'] = True

        self.progress_label.setText(_("Processing... (0%)"))
        self.thread = QThread()
        self.worker = Worker(self.controller, self.file_items, self.output_folder, header_settings, footer_settings)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.signals.finished.connect(self.on_processing_finished)
        self.worker.signals.progress.connect(self.update_progress)
        self.thread.start()
        # 启动时刷新一次预览，确保 UI 有反馈
        QTimer.singleShot(0, self.update_preview)

    def _check_for_encrypted_files(self) -> bool:
        encrypted = [item.name for item in self.file_items if getattr(item, "encryption_status", None) != EncryptionStatus.OK]
        if encrypted:
            msg = _("The following files are encrypted or restricted:") + "\n\n"
            msg += "\n".join(f"- {name}" for name in encrypted)
            msg += "\n\n" + _("Please unlock them using the right-click menu before processing.")
            QMessageBox.warning(self, _("Encrypted Files Detected"), msg)
            return False
        return True

    def on_processing_finished(self, results: list):
        """处理完成后的回调函数"""
        self.processed_paths = [res["output"] for res in results if res["success"]]
        failed = [res for res in results if not res["success"]]

        self.progress_label.setText(_("Completed {} files").format(len(self.processed_paths)))

        if failed:
            msg = "\n".join([f"{os.path.basename(res['input'])}: {res['error']}" for res in failed])
            QMessageBox.warning(self, _("Some Files Failed"), msg)
        else:
            QMessageBox.information(self, _("Done"), _("All files processed successfully."))
            self.progress_label.setText("")

        if self.merge_checkbox.isChecked() and self.processed_paths:
            dlg = MergeDialog(self.processed_paths, self)
            dlg.merge_confirmed.connect(self.handle_merge_confirmation)
            dlg.exec()
        
        self._set_controls_enabled(True)

    def handle_merge_confirmation(self, ordered_paths: list):
        """处理合并确认后的逻辑，包含统一的成功/失败提示"""
        save_path, _ = QFileDialog.getSaveFileName(self, _("Save Merged PDF"), "", "PDF Files (*.pdf)")
        if not save_path: return
        
        try:
            success, err = merge_pdfs(ordered_paths, save_path)
            if not success: raise Exception(err)

            final_message = _("Files merged successfully and saved to:\n") + save_path
            if self.page_number_checkbox.isChecked():
                add_page_numbers(
                    input_pdf=save_path, output_pdf=save_path,
                    font_name=self.footer_font_select.currentText(), font_size=self.footer_font_size_spin.value(),
                    x=self.footer_x_input.value(), y=self.footer_y_input.value()
                )
                final_message = _("Files merged and page numbers added successfully:\n") + save_path
            
            QMessageBox.information(self, _("Success"), final_message)
        except Exception as e:
            self.show_error(_("Operation Failed"), e)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        """处理文件拖放，增强校验"""
        if not event.mimeData().hasUrls(): return
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in urls if url.isLocalFile() and url.toLocalFile().lower().endswith('.pdf')]
        
        if not paths: QMessageBox.warning(self, _("Invalid Files"), _("Only PDF files can be imported.")); return
        self._process_imported_paths(paths)
        event.acceptProposedAction()

    def _process_imported_paths(self, paths: list):
        """处理导入的文件路径列表（来自对话框或拖放）"""
        try:
            new_items = self.controller.handle_file_import(paths)
            # 只添加 PDFFileItem 类型且有 name 和 size_mb 属性的 item，防止嵌套导致后续 item.name 报错
            self.file_items.extend([
                item for item in new_items
                if isinstance(item, PDFFileItem) and hasattr(item, "name") and hasattr(item, "size_mb")
            ])
            self._populate_table_from_items()
            QTimer.singleShot(100, self._recommend_fonts)

            # 新增：分析加密状态并提示
            locked_files = [item.name for item in new_items if isinstance(item, PDFFileItem) and getattr(item, "encryption_status", None) == EncryptionStatus.LOCKED]
            restricted_files = [item.name for item in new_items if isinstance(item, PDFFileItem) and getattr(item, "encryption_status", None) == EncryptionStatus.RESTRICTED]
            if locked_files or restricted_files:
                msg = ""
                if locked_files:
                    msg += _("The following files are fully encrypted and require a password:\n") + "\n".join(f"• {f}" for f in locked_files) + "\n\n"
                if restricted_files:
                    msg += _("The following files are restricted (e.g., can't be modified):\n") + "\n".join(f"• {f}" for f in restricted_files)
                QMessageBox.information(self, _("Encrypted Files Notice"), msg.strip())

        except Exception as e:
            self.show_error(_("Failed to import files"), e)

    def update_preview(self):
        """更新页眉页脚位置的预览图像（横向长条：显示 Header/Footer 文本与大致 X 位置提示）"""
        width, height = 600, 80
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.white)
        painter = QPainter(pixmap)
        settings = self._get_current_settings()

        # 分割线
        painter.setPen(QPen(Qt.gray, 1, Qt.DashLine))
        painter.drawLine(0, height // 2, width, height // 2)

        # 取当前选中行的 header/footer 文本（若无选中则示例文案）
        header_text = "Header"
        footer_text = "Footer"
        current_row = self.file_table.currentRow()
        if current_row >= 0:
            try:
                header_item = self.file_table.item(current_row, 4)
                footer_item = self.file_table.item(current_row, 5)
                if header_item and header_item.text():
                    header_text = header_item.text()
                if footer_item and footer_item.text():
                    footer_text = footer_item.text()
            except Exception:
                pass

        # Header 在上方
        painter.setPen(QPen(Qt.black))
        header_font_name = settings.get("header_font_name", "Helvetica")
        if not QFont(header_font_name).exactMatch():
            header_font_name = QFont().defaultFamily()
        header_font_size = max(int(settings.get("header_font_size", 9)), 8)
        painter.setFont(QFont(header_font_name, header_font_size))
        header_x = max(int(settings.get("header_x", 72)) // 4, 10)  # 简化：将 pt 映射到小画布像素
        painter.drawText(header_x, height // 2 - 15, header_text[:40])

        # Footer 在下方
        painter.setPen(QPen(Qt.darkGray))
        footer_font_name = settings.get("footer_font_name", "Helvetica")
        if not QFont(footer_font_name).exactMatch():
            footer_font_name = QFont().defaultFamily()
        footer_font_size = max(int(settings.get("footer_font_size", 9)), 8)
        painter.setFont(QFont(footer_font_name, footer_font_size))
        footer_x = max(int(settings.get("footer_x", 72)) // 4, 10)
        painter.drawText(footer_x, height // 2 + 25, footer_text[:40])

        painter.end()
        self.preview_canvas.setPixmap(pixmap)

    def _validate_positions(self):
        """验证Y坐标是否在打印安全区内"""
        self.header_y_warning_label.setVisible(is_out_of_print_safe_area(self.y_input.value(), top=True))
        self.footer_y_warning_label.setVisible(is_out_of_print_safe_area(self.footer_y_input.value(), top=False))

    def _get_current_settings(self) -> dict:
        """从UI控件中提取所有设置项"""
        settings = {}
        for key, widget in self.settings_map.items():
            if isinstance(widget, QComboBox): settings[key] = widget.currentText()
            elif isinstance(widget, QSpinBox): settings[key] = widget.value()
            elif isinstance(widget, QCheckBox): settings[key] = widget.isChecked()
        return settings

    def _apply_settings(self, settings: dict):
        """将加载的配置应用到UI控件，增强容错"""
        if not settings: return
        from config import apply_defaults
        try:
            settings = apply_defaults(settings)
            for key, widget in self.settings_map.items():
                if key in settings:
                    if isinstance(widget, QComboBox): widget.setCurrentText(settings[key])
                    elif isinstance(widget, QSpinBox): widget.setValue(settings[key])
                    elif isinstance(widget, QCheckBox): widget.setChecked(settings[key])
            self.update_preview()
        except Exception as e:
            self.show_error(_("Failed to apply settings due to an error. Please check the logs."), e)

    def closeEvent(self, event):
        """在关闭应用前保存设置"""
        from config import save_settings
        save_settings(self._get_current_settings())
        event.accept()

    def show_error(self, message: str, exception: Exception = None):
        """显示错误信息对话框和日志，增强日志记录"""
        self.progress_label.setText(message)
        if exception: logger.error(f"UI Error: '{message}'", exc_info=True)
        QMessageBox.critical(self, _("Error"), f"{message}\n\n{str(exception or '')}")
    
    def update_progress(self, current: int, total: int, filename: str):
        """更新进度条标签"""
        percent = int((current / total) * 100)
        self.progress_label.setText(f"{_('Processing...')} ({percent}%) - {filename}")
    
    def show_about_dialog(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, "About DocDeck",
            "DocDeck - PDF Header & Footer Tool\n"
            "Version 1.0.5 (Production Final)\n\n"
            "Author: 木小樨\n"
            "Project Homepage:\n"
            "https://hs2wxdogy2.feishu.cn/wiki/Kjv3wQfV5iKpGXkQ8aCcOkj6nVf"
        )
