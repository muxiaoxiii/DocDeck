# ui_main.py
import os
import pathlib
import re
import locale
import gettext
from typing import Dict, Any, Optional
from io import BytesIO

# PySide6 imports - 统一管理
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QSpinBox, QCheckBox,
    QGroupBox, QMenu, QInputDialog, QProgressBar
)
from PySide6.QtCore import (
    Qt, QCoreApplication, QThread, QTimer, QRect, QPoint, QSize, QEvent, Signal
)
from PySide6.QtGui import (
    QPainter, QPen, QFont, QPixmap, QImage, QBrush, QColor, QIcon, QAction, QTransform
)

# PDF处理相关库
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
import pikepdf
from reportlab.pdfgen import canvas as rl_canvas

# 应用模块
from models import PDFFileItem, EncryptionStatus
from controller import ProcessingController, Worker
from font_manager import get_system_fonts, suggest_chinese_fallback_font
from pdf_handler import merge_pdfs, add_page_numbers
from position_utils import suggest_safe_header_y, is_out_of_print_safe_area
from merge_dialog import MergeDialog
from geometry_context import build_geometry_context
from font_manager import register_font_safely
from logger import logger
from ui.components.preview_manager import PreviewManager

# 导入语言管理器
from ui.i18n.locale_manager import get_locale_manager

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
        
        # 排序相关变量
        self.current_sort_column = 0
        self.current_sort_order = Qt.AscendingOrder
        
        # 自然排序方法（通用，无前缀依赖）
        def natural_sort_key(text: str):
            """返回用于自然排序的键：按字母不区分大小写，数字按数值比较。
            例如：['a1', 'a2', 'a10'] -> 自然顺序
            """
            import re
            s = text or ""
            parts = re.split(r"(\d+)", s)
            key = []
            for part in parts:
                if part.isdigit():
                    key.append((1, int(part)))
                else:
                    key.append((0, part.lower()))
            return tuple(key)
        
        self.natural_sort_key = natural_sort_key
        
        # 使用新的语言管理器
        self.locale_manager = get_locale_manager()
        self._ = self.locale_manager._

        self.setWindowTitle("DocDeck - PDF Header & Footer Tool")
        self.resize(1200, 900)
        self.controller = ProcessingController(self)
        
        # 创建状态栏
        self.statusBar = self.statusBar()
        self.statusBar.showMessage(self._("Ready"))
        
        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progress_bar)
        
        # 设置现代化样式
        self._setup_modern_style()
        
        self._setup_ui()
        # 预览管理器（委托所有预览渲染）
        self.preview = PreviewManager(self)
        self._setup_menu()
        self._map_settings_to_widgets()
        self._connect_signals()

        self.setAcceptDrops(True)
        from config import load_settings
        self._apply_settings(load_settings())
        self._update_ui_state()
        
        # 设置拖拽支持
        self._setup_drag_drop()
        
        # 设置现代化样式
        self._setup_modern_style()

    # --- UI Setup Methods ---
    def _setup_ui(self):
        """初始化和布局所有UI控件"""
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        top_layout = self._create_top_bar()
        self.auto_number_group = self._create_auto_number_group()
        settings_group = self._create_settings_grid_group()
        preview_group = self._create_preview_area()
        table_layout = self._create_table_area()
        output_layout = self._create_output_layout()

        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.auto_number_group)
        # 设置与预览并列显示
        settings_preview_layout = QHBoxLayout()
        settings_preview_layout.addWidget(settings_group, 3)
        settings_preview_layout.addWidget(preview_group, 2)
        main_layout.addLayout(settings_preview_layout)
        
        # 单位与预设位置控件已迁入 SettingsPanel，这里不再重复创建
        
        main_layout.addLayout(table_layout)
        main_layout.addLayout(output_layout)
        
        self.setCentralWidget(central_widget)

    def _create_top_bar(self) -> QHBoxLayout:
        """创建顶部包含导入、清空和模式选择的工具栏"""
        layout = QHBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # 创建标题标签
        title_label = QLabel("📄 " + self._("DocDeck - PDF Header & Footer Tool"))
        title_label.setObjectName("title_label")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # 导入按钮组
        import_group = QHBoxLayout()
        import_group.setSpacing(10)
        
        self.import_button = QPushButton("📁 " + self._("Import Files or Folders"))
        self.import_button.setMinimumHeight(35)
        self.import_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                font-size: 13px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        
        import_group.addWidget(self.import_button)
        layout.addLayout(import_group)
        
        layout.addStretch()
        
        # 模式选择组
        mode_group = QHBoxLayout()
        mode_group.setSpacing(10)
        
        mode_label = QLabel(self._("Header Mode:"))
        mode_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        
        self.mode_select_combo = QComboBox()
        self.mode_select_combo.addItems([self._("Filename Mode"), self._("Auto Number Mode"), self._("Custom Mode")])
        self.mode_select_combo.setMinimumHeight(35)
        self.mode_select_combo.setStyleSheet("""
            QComboBox {
                font-size: 13px;
                padding: 8px 15px;
                min-width: 150px;
            }
        """)
        
        mode_group.addWidget(mode_label)
        mode_group.addWidget(self.mode_select_combo)
        layout.addLayout(mode_group)
        
        return layout

    def _create_auto_number_group(self) -> QGroupBox:
        """创建自动编号设置的控件组"""
        group = QGroupBox("🔢 " + self._("Auto Number Settings"))
        group.setStyleSheet("""
            QGroupBox {
                background-color: #ecf0f1;
                border: 2px solid #bdc3c7;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #2c3e50;
                background-color: #ecf0f1;
                font-size: 14px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建标签和输入控件的网格布局
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)
        
        # 前缀设置
        prefix_label = QLabel(self._("Prefix:"))
        prefix_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.prefix_input = QLineEdit("Doc-")
        self.prefix_input.setMinimumHeight(30)
        self.prefix_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        grid_layout.addWidget(prefix_label, 0, 0)
        grid_layout.addWidget(self.prefix_input, 0, 1)
        
        # 起始编号
        start_label = QLabel(self._("Start #:"))
        start_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.start_spin = QSpinBox()
        self.start_spin.setRange(1, 9999)
        self.start_spin.setValue(1)
        self.start_spin.setMinimumHeight(30)
        self.start_spin.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 80px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        grid_layout.addWidget(start_label, 0, 2)
        grid_layout.addWidget(self.start_spin, 0, 3)
        
        # 步长
        step_label = QLabel(self._("Step:"))
        step_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 100)
        self.step_spin.setValue(1)
        self.step_spin.setMinimumHeight(30)
        self.step_spin.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 80px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        grid_layout.addWidget(step_label, 1, 0)
        grid_layout.addWidget(self.step_spin, 1, 1)
        
        # 位数
        digits_label = QLabel(self._("Digits:"))
        digits_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.digits_spin = QSpinBox()
        self.digits_spin.setRange(1, 6)
        self.digits_spin.setValue(3)
        self.digits_spin.setMinimumHeight(30)
        self.digits_spin.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 80px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        grid_layout.addWidget(digits_label, 1, 2)
        grid_layout.addWidget(self.digits_spin, 1, 3)
        
        # 后缀
        suffix_label = QLabel(self._("Suffix:"))
        suffix_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.suffix_input = QLineEdit("")
        self.suffix_input.setMinimumHeight(30)
        self.suffix_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        grid_layout.addWidget(suffix_label, 1, 4)
        grid_layout.addWidget(self.suffix_input, 1, 5)
        
        layout.addLayout(grid_layout)
        layout.addStretch()
        
        group.setLayout(layout)
        group.setVisible(False)
        return group

    def _create_settings_grid_group(self) -> QGroupBox:
        """创建页眉页脚设置网格组"""
        group = QGroupBox("⚙️ " + self._("Header & Footer Settings"))
        group.setStyleSheet("""
            QGroupBox {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #2c3e50;
                background-color: #f8f9fa;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        grid = QGridLayout()
        grid.setSpacing(15)
        grid.setContentsMargins(20, 20, 20, 20)
        
        # 设置标签
        settings_header = QLabel(self._("Settings"))
        settings_header.setStyleSheet("""
            font-weight: bold; 
            color: #2c3e50; 
            font-size: 13px;
            padding: 8px;
            background-color: #e9ecef;
            border-radius: 6px;
        """)
        settings_header.setAlignment(Qt.AlignCenter)
        
        header_header = QLabel(self._("Header"))
        header_header.setStyleSheet("""
            font-weight: bold; 
            color: #2c3e50; 
            font-size: 13px;
            padding: 8px;
            background-color: #d1ecf1;
            border-radius: 6px;
        """)
        header_header.setAlignment(Qt.AlignCenter)
        
        footer_header = QLabel(self._("Footer"))
        footer_header.setStyleSheet("""
            font-weight: bold; 
            color: #2c3e50; 
            font-size: 13px;
            padding: 8px;
            background-color: #d4edda;
            border-radius: 6px;
        """)
        footer_header.setAlignment(Qt.AlignCenter)
        
        grid.addWidget(settings_header, 0, 0)
        grid.addWidget(header_header, 0, 1)
        grid.addWidget(footer_header, 0, 2)
        
        # 字体选择
        font_label = QLabel(self._("Font:"))
        font_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        font_label.setAlignment(Qt.AlignRight)
        
        self.font_select = QComboBox()
        self.font_select.addItems(get_system_fonts())
        self.font_select.setMinimumHeight(30)
        self.font_select.setStyleSheet("""
            QComboBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 120px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
        """)
        
        self.footer_font_select = QComboBox()
        self.footer_font_select.addItems(get_system_fonts())
        self.footer_font_select.setMinimumHeight(30)
        self.footer_font_select.setStyleSheet("""
            QComboBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 120px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
        """)
        
        grid.addWidget(font_label, 1, 0)
        grid.addWidget(self.font_select, 1, 1)
        grid.addWidget(self.footer_font_select, 1, 2)
        
        # 字体大小
        size_label = QLabel(self._("Size:"))
        size_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        size_label.setAlignment(Qt.AlignRight)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 72)
        self.font_size_spin.setValue(14)
        self.font_size_spin.setMinimumHeight(30)
        self.font_size_spin.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 80px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        
        self.footer_font_size_spin = QSpinBox()
        self.footer_font_size_spin.setRange(6, 72)
        self.footer_font_size_spin.setValue(14)
        self.footer_font_size_spin.setMinimumHeight(30)
        self.footer_font_size_spin.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 80px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        
        grid.addWidget(size_label, 2, 0)
        grid.addWidget(self.font_size_spin, 2, 1)
        grid.addWidget(self.footer_font_size_spin, 2, 2)
        
        # X位置
        x_label = QLabel(self._("X Position:"))
        x_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        x_label.setAlignment(Qt.AlignRight)
        
        self.x_input = QSpinBox()
        self.x_input.setRange(0, 2000)
        self.x_input.setValue(72)
        self.x_input.setMinimumHeight(30)
        self.x_input.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 80px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        
        self.footer_x_input = QSpinBox()
        self.footer_x_input.setRange(0, 2000)
        self.footer_x_input.setValue(72)
        self.footer_x_input.setMinimumHeight(30)
        self.footer_x_input.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 80px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        
        grid.addWidget(x_label, 3, 0)
        grid.addWidget(self.x_input, 3, 1)
        grid.addWidget(self.footer_x_input, 3, 2)
        
        # Y位置
        y_label = QLabel(self._("Y Position:"))
        y_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        y_label.setAlignment(Qt.AlignRight)
        
        self.y_input = QSpinBox()
        self.y_input.setRange(0, 2000)
        self.y_input.setValue(752)
        self.y_input.setMinimumHeight(30)
        self.y_input.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 80px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        
        self.footer_y_input = QSpinBox()
        self.footer_y_input.setRange(0, 2000)
        self.footer_y_input.setValue(40)
        self.footer_y_input.setMinimumHeight(30)
        self.footer_y_input.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 80px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        
        header_y_layout = QHBoxLayout()
        header_y_layout.addWidget(self.y_input)
        header_y_layout.addWidget(self._create_warning_label())
        
        footer_y_layout = QHBoxLayout()
        footer_y_layout.addWidget(self.footer_y_input)
        footer_y_layout.addWidget(self._create_warning_label())
        
        grid.addWidget(y_label, 4, 0)
        grid.addLayout(header_y_layout, 4, 1)
        grid.addLayout(footer_y_layout, 4, 2)
        
        # 对齐方式
        align_label = QLabel(self._("Alignment:"))
        align_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        align_label.setAlignment(Qt.AlignRight)
        
        # 页眉对齐按钮
        header_align_layout = QHBoxLayout()
        header_align_layout.setSpacing(8)
        
        self.left_btn = QPushButton(self._("Left"))
        self.left_btn.setMinimumHeight(30)
        self.left_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        
        self.center_btn = QPushButton(self._("Center"))
        self.center_btn.setMinimumHeight(30)
        self.center_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        
        self.right_btn = QPushButton(self._("Right"))
        self.right_btn.setMinimumHeight(30)
        self.right_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        
        header_align_layout.addWidget(self.left_btn)
        header_align_layout.addWidget(self.center_btn)
        header_align_layout.addWidget(self.right_btn)
        
        # 页脚对齐按钮
        footer_align_layout = QHBoxLayout()
        footer_align_layout.setSpacing(8)
        
        self.footer_left_btn = QPushButton(self._("Left"))
        self.footer_left_btn.setMinimumHeight(30)
        self.footer_left_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        
        self.footer_center_btn = QPushButton(self._("Center"))
        self.footer_center_btn.setMinimumHeight(30)
        self.footer_center_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        
        self.footer_right_btn = QPushButton(self._("Right"))
        self.footer_right_btn.setMinimumHeight(30)
        self.footer_right_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        
        footer_align_layout.addWidget(self.footer_left_btn)
        footer_align_layout.addWidget(self.footer_center_btn)
        footer_align_layout.addWidget(self.footer_right_btn)
        
        grid.addWidget(align_label, 5, 0)
        grid.addLayout(header_align_layout, 5, 1)
        grid.addLayout(footer_align_layout, 5, 2)
        
        # 页眉模板
        template_label = QLabel(self._("Header Template:"))
        template_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        template_label.setAlignment(Qt.AlignRight)
        
        self.header_template_combo = QComboBox()
        self.header_template_combo.addItems([self._("Custom"), self._("Company Name"), self._("Document Title"), self._("Date"), self._("Page Number"), self._("Confidential"), self._("Draft"), self._("Final Version")])
        self.header_template_combo.currentTextChanged.connect(self._on_header_template_changed)
        self.header_template_combo.setMinimumHeight(30)
        self.header_template_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 150px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
        """)
        
        grid.addWidget(template_label, 6, 0)
        grid.addWidget(self.header_template_combo, 6, 1, 1, 2)
        
        # 全局页脚文本
        footer_text_label = QLabel(self._("Global Footer Text:"))
        footer_text_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        footer_text_label.setAlignment(Qt.AlignRight)
        
        self.global_footer_text = QLineEdit(self._("Page {page} of {total}"))
        self.global_footer_text.setMinimumHeight(30)
        self.global_footer_text.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        
        self.apply_footer_template_button = QPushButton(self._("Apply to All"))
        self.apply_footer_template_button.setMinimumHeight(30)
        self.apply_footer_template_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #117a8b;
            }
        """)
        
        footer_template_layout = QHBoxLayout()
        footer_template_layout.setSpacing(10)
        footer_template_layout.addWidget(self.global_footer_text)
        footer_template_layout.addWidget(self.apply_footer_template_button)
        
        grid.addWidget(footer_text_label, 7, 0)
        grid.addLayout(footer_template_layout, 7, 1, 1, 2)

        # 页眉页脚位置预览区域




        # 结构化模式开关
        self.structured_checkbox = QCheckBox("🔧 " + self._("Structured mode (Acrobat-friendly)"))
        self.structured_checkbox.setChecked(False)
        self.structured_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #2c3e50;
                font-size: 12px;
                padding: 8px;
                background-color: #f8f9fa;
                border-radius: 6px;
            }
        """)
        # 占位，具体放置见下方组合行

        # 结构化中文选项
        self.struct_cn_fixed_checkbox = QCheckBox("🇨🇳 " + self._("Structured CN: use fixed font"))
        self.struct_cn_fixed_checkbox.setChecked(False)
        self.struct_cn_fixed_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #2c3e50;
                font-size: 12px;
                padding: 8px;
                background-color: #f8f9fa;
                border-radius: 6px;
            }
        """)
        
        self.struct_cn_font_combo = QComboBox()
        self.struct_cn_font_combo.addItems(get_system_fonts())
        self.struct_cn_font_combo.setMinimumHeight(25)
        self.struct_cn_font_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                min-width: 120px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
        """)
        
        # 并排一行显示（第9行）：结构化模式（第2列）+ 结构化中文及字体（第3列，水平并排）
        row_idx = 9
        grid.addWidget(self.structured_checkbox, row_idx, 1, 1, 1)
        cn_layout = QHBoxLayout()
        cn_layout.setSpacing(8)
        cn_layout.addWidget(self.struct_cn_fixed_checkbox)
        cn_layout.addWidget(self.struct_cn_font_combo)
        grid.addLayout(cn_layout, row_idx, 2, 1, 1)

        # 删除内存优化按钮：默认策略在处理前根据文件大小自动启用

        # 仅返回设置网格组；预览区域已在主布局中并列显示
        group.setLayout(grid)
        return group

    def _create_table_area(self) -> QHBoxLayout:
        """创建文件列表及右侧的控制按钮"""
        layout = QHBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建表格区域组
        table_group = QGroupBox("📋 " + self._("File List"))
        table_group.setStyleSheet("""
            QGroupBox {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #2c3e50;
                background-color: #f8f9fa;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        table_group_layout = QVBoxLayout()
        table_group_layout.setSpacing(15)
        table_group_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建表格区域
        table_layout = QVBoxLayout()
        table_layout.setSpacing(10)
        
        # 文件表格
        self.file_table = QTableWidget(0, 6)
        self.file_table.setHorizontalHeaderLabels([self._("No."), self._("Filename"), self._("Size (MB)"), self._("Page Count"), self._("Header Text"), self._("Footer Text")])
        
        # 设置表格最小宽度，确保所有列都能正常显示
        self.file_table.setMinimumWidth(1000)  # 总宽度：80+300+100+100+200+200 = 980px + 边距
        
        # 设置列宽比例，优化显示效果
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)      # 序号列固定宽度
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive) # 文件名列可调整
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)      # 大小列固定宽度
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)      # 页数列固定宽度
        self.file_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive) # 页眉列可调整
        self.file_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Interactive) # 页脚列可调整
        
        # 设置默认列宽
        self.file_table.setColumnWidth(0, 80)   # 序号列（增加宽度显示锁图标）
        self.file_table.setColumnWidth(1, 300)  # 文件名列（增加宽度显示完整文件名）
        self.file_table.setColumnWidth(2, 100)  # 大小列（增加宽度显示完整大小）
        self.file_table.setColumnWidth(3, 100)  # 页数列（增加宽度显示完整页数）
        self.file_table.setColumnWidth(4, 200)  # 页眉列（设置合适的默认宽度）
        self.file_table.setColumnWidth(5, 200)  # 页脚列（设置合适的默认宽度）
        
        # 排序功能将在表格填充完成后启用
        # self.file_table.setSortingEnabled(True)
        
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_table.setEditTriggers(QTableWidget.DoubleClicked)
        
        # 设置表格样式表
        self.file_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f8f9fa;
                gridline-color: #e9ecef;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                selection-background-color: #3498db;
                selection-color: white;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f1f3f4;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 10px 8px;
                border: none;
                font-weight: bold;
                font-size: 11px;
            }
            QHeaderView::section:hover {
                background-color: #2c3e50;
            }
            QScrollBar:vertical {
                background-color: #f1f3f4;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #c1c1c1;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a8a8a8;
            }
            QScrollBar:horizontal {
                background-color: #f1f3f4;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #c1c1c1;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #a8a8a8;
            }
        """)
        
        # 表格编辑或选择变化时，实时刷新预览
        self.file_table.itemChanged.connect(lambda *_: self.update_preview())
        self.file_table.itemSelectionChanged.connect(self.update_preview)
        
        # 连接排序信号（禁用内置排序，使用自定义自然排序）
        self.file_table.horizontalHeader().sortIndicatorChanged.connect(self._on_sort_changed)
        # 默认按照文件名自然排序一次
        QTimer.singleShot(0, lambda: self._perform_custom_sort(1, Qt.AscendingOrder))
        
        # 重写排序逻辑，实现自然排序
        self.file_table.horizontalHeader().sectionClicked.connect(self._handle_header_click)
        
        # 在文件表格设置后添加右键菜单
        self._setup_context_menu()
        
        table_layout.addWidget(self.file_table)
        table_group_layout.addLayout(table_layout)
        table_group.setLayout(table_group_layout)
        
        # 设置表格组的最小宽度，确保表格能正常显示
        table_group.setMinimumWidth(1100)  # 表格宽度1000px + 边距和边框
        
        # 创建控制按钮组
        controls_group = QGroupBox("🎛️ " + self._("File Operations"))
        controls_group.setStyleSheet("""
            QGroupBox {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #2c3e50;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(10)
        controls_layout.setContentsMargins(20, 20, 20, 20)
        
        self.move_up_button = QPushButton("⬆️ " + self._("Move Up"))
        self.move_up_button.setMinimumHeight(35)
        self.move_up_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #495057;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        self.move_down_button = QPushButton("⬇️ " + self._("Move Down"))
        self.move_down_button.setMinimumHeight(35)
        self.move_down_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #495057;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        self.remove_button = QPushButton("🗑️ " + self._("Remove"))
        self.remove_button.setMinimumHeight(35)
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        controls_layout.addStretch()
        # 顶部不再放置的按钮：迁移到文件操作区
        self.clear_button = QPushButton("🗑️ " + self._("Clear List"))
        self.clear_button.setMinimumHeight(35)
        self.clear_button.clicked.connect(self.clear_file_list)
        self.unlock_button = QPushButton("🔓 " + self._("移除文件限制..."))
        self.unlock_button.setMinimumHeight(35)
        self.unlock_button.clicked.connect(self._unlock_selected)
        controls_layout.addWidget(self.clear_button)
        controls_layout.addWidget(self.unlock_button)
        controls_layout.addWidget(self.move_up_button)
        controls_layout.addWidget(self.move_down_button)
        controls_layout.addWidget(self.remove_button)
        controls_layout.addStretch()
        
        controls_group.setLayout(controls_layout)
        
        layout.addWidget(table_group, 10)
        layout.addWidget(controls_group, 1)
        return layout

    def _create_preview_area(self) -> QGroupBox:
        """创建右侧预览区域（从设置面板中拆分出来）"""
        preview_container = QGroupBox("\U0001F441\uFE0F " + self._("WYSIWYG Preview (Header/Footer)"))
        preview_container.setStyleSheet("""
            QGroupBox {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #2c3e50;
                background-color: #f8f9fa;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        preview_layout = QVBoxLayout()
        preview_layout.setSpacing(10)
        preview_layout.setContentsMargins(15, 15, 15, 15)

        # 页码选择
        page_sel_layout = QHBoxLayout()
        page_label = QLabel(self._("Page: "))
        self.preview_page_spin = QSpinBox()
        self.preview_page_spin.setRange(1, 9999)
        self.preview_page_spin.setValue(1)
        page_sel_layout.addWidget(page_label)
        page_sel_layout.addWidget(self.preview_page_spin)
        page_sel_layout.addStretch()

        # 预览画布
        self.pdf_preview_canvas = QLabel(self._("Select a file to see preview"))
        self.pdf_preview_canvas.setMinimumHeight(220)
        self.pdf_preview_canvas.setAlignment(Qt.AlignCenter)
        self.pdf_preview_canvas.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f0f0f0);
            border: 2px dashed #bdc3c7; 
            border-radius: 8px;
            padding: 5px;
            color: #7f8c8d;
        """)

        preview_layout.addLayout(page_sel_layout)
        preview_layout.addWidget(self.pdf_preview_canvas, 1)

        preview_container.setLayout(preview_layout)
        return preview_container

    def _create_output_layout(self) -> QVBoxLayout:
        """创建输出和执行按钮的布局"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建输出组
        output_group = QGroupBox("📂 " + self._("Output Settings"))
        output_group.setStyleSheet("""
            QGroupBox {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #2c3e50;
                background-color: #f8f9fa;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        output_group_layout = QVBoxLayout()
        output_group_layout.setSpacing(15)
        output_group_layout.setContentsMargins(20, 20, 20, 20)
        
        h_layout = QHBoxLayout()
        h_layout.setSpacing(15)
        
        default_download_path = str(pathlib.Path.home() / "Downloads")
        self.output_path_display = QLabel(default_download_path)
        self.output_path_display.setStyleSheet("""
            color: #6c757d; 
            background-color: #e9ecef; 
            padding: 8px 12px; 
            border-radius: 4px;
            border: 1px solid #ced4da;
        """)
        self.output_folder = default_download_path
        
        output_label = QLabel(self._("Output Folder:"))
        output_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        
        self.select_output_button = QPushButton("📁 " + self._("Select Output Folder"))
        self.select_output_button.setMinimumHeight(35)
        self.select_output_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #117a8b;
            }
        """)
        
        self.start_button = QPushButton("🚀 " + self._("Start Processing"))
        self.start_button.setObjectName("start_button")
        self.start_button.setMinimumHeight(40)
        self.start_button.setStyleSheet("""
            QPushButton#start_button {
                background-color: #27ae60;
                border: none;
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                min-width: 140px;
            }
            QPushButton#start_button:hover {
                background-color: #229954;
            }
            QPushButton#start_button:pressed {
                background-color: #1e8449;
            }
            QPushButton#start_button:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)

        h_layout.addWidget(output_label)
        h_layout.addWidget(self.output_path_display, 1)
        h_layout.addWidget(self.select_output_button)
        h_layout.addWidget(self.start_button)
        
        output_group_layout.addLayout(h_layout)
        
        # 复选框布局
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(20)
        
        self.merge_checkbox = QCheckBox("🔗 " + self._("Merge after processing"))
        self.merge_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #2c3e50;
                font-size: 12px;
                padding: 8px;
                background-color: #e8f4fd;
                border-radius: 6px;
            }
        """)
        
        self.page_number_checkbox = QCheckBox("🔢 " + self._("Add page numbers after merge"))
        self.page_number_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #2c3e50;
                font-size: 12px;
                padding: 8px;
                background-color: #e8f4fd;
                border-radius: 6px;
            }
        """)
        
        self.normalize_a4_checkbox = QCheckBox("📏 " + self._("Normalize to A4 (auto)"))
        self.normalize_a4_checkbox.setChecked(True)
        self.normalize_a4_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #2c3e50;
                font-size: 12px;
                padding: 8px;
                background-color: #e8f4fd;
                border-radius: 6px;
            }
        """)
        
        checkbox_layout.addWidget(self.merge_checkbox)
        checkbox_layout.addWidget(self.page_number_checkbox)
        checkbox_layout.addWidget(self.normalize_a4_checkbox)
        checkbox_layout.addStretch()

        output_group_layout.addLayout(checkbox_layout)
        output_group.setLayout(output_group_layout)
        
        # 进度标签
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("""
            font-weight: bold;
            color: #2c3e50;
            font-size: 13px;
            padding: 10px;
            background-color: #d4edda;
            border-radius: 6px;
            border: 1px solid #c3e6cb;
        """)

        layout.addWidget(output_group)
        layout.addWidget(self.progress_label)
        return layout
    
    def _create_warning_label(self) -> QLabel:
        label = QLabel("⚠️"); label.setToolTip(self._("This position is too close to the edge...")); label.setVisible(False)
        return label

    def _setup_menu(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu(self._("File"))
        
        # 导入设置
        import_settings_action = file_menu.addAction(self._("Import Settings..."))
        import_settings_action.triggered.connect(self._import_settings)
        
        # 导出设置
        export_settings_action = file_menu.addAction(self._("Export Settings..."))
        export_settings_action.triggered.connect(self._export_settings)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = file_menu.addAction(self._("Exit"))
        exit_action.triggered.connect(self.close)
        
        # 设置菜单
        settings_menu = menubar.addMenu(self._("Settings"))
        
        # 重置设置
        reset_settings_action = settings_menu.addAction(self._("Reset to Defaults"))
        reset_settings_action.triggered.connect(self._reset_settings)
        
        # 语言设置
        language_menu = settings_menu.addMenu(self._("Language"))
        
        chinese_action = language_menu.addAction("中文")
        chinese_action.triggered.connect(lambda: self._change_language("zh_CN"))
        
        english_action = language_menu.addAction("English")
        english_action.triggered.connect(lambda: self._change_language("en_US"))
        
        # 帮助菜单
        help_menu = menubar.addMenu(self._("Help"))
        about_action = help_menu.addAction(self._("About"))
        about_action.triggered.connect(self.show_about_dialog)

    def _map_settings_to_widgets(self):
        """将设置项键名映射到UI控件，用于简化配置的存取"""
        self.settings_map = {
            "header_font_name": self.font_select, "header_font_size": self.font_size_spin,
            "header_x": self.x_input, "header_y": self.y_input,
            "footer_font_name": self.footer_font_select, "footer_font_size": self.footer_font_size_spin,
            "footer_x": self.footer_x_input, "footer_y": self.footer_y_input,
            "merge": self.merge_checkbox, "page_numbering": self.page_number_checkbox,
            "structured": self.structured_checkbox,
            "normalize_a4": self.normalize_a4_checkbox,
            "structured_cn_fixed": self.struct_cn_fixed_checkbox,
            "structured_cn_font": self.struct_cn_font_combo,
            # 内存优化按钮已移除，改为运行时自动决策
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
        # self.file_table.customContextMenuRequested.connect(self._show_context_menu) # This line is now handled by _setup_context_menu
        
        auto_number_controls = [self.prefix_input, self.suffix_input, self.start_spin, self.step_spin, self.digits_spin]
        for control in auto_number_controls:
            if isinstance(control, QLineEdit): control.textChanged.connect(self.update_header_texts)
            else: control.valueChanged.connect(self.update_header_texts)

        preview_controls = [self.font_select, self.footer_font_select, self.font_size_spin, self.footer_font_size_spin, self.x_input, self.footer_x_input, self.structured_checkbox, self.normalize_a4_checkbox, self.struct_cn_fixed_checkbox, self.struct_cn_font_combo, self.preview_page_spin]
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
        
        # 如果没有文件，禁用相关控件
        if not has_files:
            widgets_to_disable = [self.clear_button, self.start_button, self.move_up_button, self.move_down_button, self.auto_number_group]
            settings_group = self.centralWidget().findChild(QGroupBox, "Header & Footer Settings")
            if settings_group:
                widgets_to_disable.append(settings_group)
            for widget in widgets_to_disable:
                if widget:
                    widget.setEnabled(False)
        else:
            # 有文件时，根据当前模式启用/禁用auto_number_group
            self._set_controls_enabled(True)
            if self.mode != self.MODE_AUTO_NUMBER:
                self.auto_number_group.setEnabled(False)
        
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

    # 删除重复的_show_context_menu方法定义

    # 删除重复的_attempt_unlock方法定义

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
        
        # 显示/隐藏自动编号设置组
        self.auto_number_group.setVisible(self.mode == self.MODE_AUTO_NUMBER)
        
        # 根据模式启用/禁用相关控件
        if self.mode == self.MODE_AUTO_NUMBER:
            # 自动编号模式：启用自动编号控件，禁用页眉文本编辑
            self.auto_number_group.setEnabled(True)
            # 这里可以添加禁用页眉文本编辑的逻辑
        elif self.mode == self.MODE_FILENAME:
            # 文件名模式：禁用自动编号控件
            self.auto_number_group.setEnabled(False)
        else:  # 自定义模式
            # 自定义模式：禁用自动编号控件
            self.auto_number_group.setEnabled(False)
            self._reset_auto_number_fields()
        
        # 更新UI状态，确保auto_number_group的启用状态正确
        self._update_ui_state()
        self.update_header_texts()

    def update_header_texts(self):
        """根据当前模式更新所有文件的页眉文本"""
        if not self.file_items: return
        
        # 记录更新前的状态，避免不必要的表格重新填充
        old_header_texts = [item.header_text for item in self.file_items]
        
        self.controller.apply_header_mode(
            file_items=self.file_items, mode=self.mode,
            numbering_prefix=self.prefix_input.text(), numbering_start=self.start_spin.value(),
            numbering_step=self.step_spin.value(), numbering_suffix=self.suffix_input.text(),
            numbering_digits=self.digits_spin.value()
        )
        
        # 检查是否有实际变化，如果没有则不重新填充表格
        new_header_texts = [item.header_text for item in self.file_items]
        if old_header_texts != new_header_texts:
            # 只更新页眉列，不重新填充整个表格
            for idx, item in enumerate(self.file_items):
                if idx < self.file_table.rowCount():
                    header_item = self.file_table.item(idx, 4)
                    if header_item:
                        header_item.setText(item.header_text)
        else:
            logger.info("Header texts unchanged, skipping table repopulation")
        
        self.update_preview()

    def import_files(self):
        """打开文件对话框以导入PDF文件"""
        paths, _ = QFileDialog.getOpenFileNames(self, self._("Select PDF Files or Folders"), "", "PDF Files (*.pdf)")
        if paths: self._process_imported_paths(paths)

    def clear_file_list(self):
        """清空文件列表"""
        self.file_items.clear()
        self._populate_table_from_items()
        # 确保UI状态正确更新
        self._update_ui_state()

    def _populate_table_from_items(self):
        """用文件数据填充表格"""
        logger.info(f"Populating table with {len(self.file_items)} items")
        
        # 临时禁用排序功能，避免干扰表格填充
        self.file_table.setSortingEnabled(False)
        
        # 调试：打印所有文件项的信息
        for i, item in enumerate(self.file_items):
            logger.info(f"File item {i}: name='{getattr(item, 'name', 'N/A')}', size={getattr(item, 'size_mb', 'N/A')}, status={getattr(item, 'encryption_status', 'N/A')}")
        
        # 完全重置表格
        self.file_table.setRowCount(0)
        self.file_table.setRowCount(len(self.file_items))
        
        valid_count = 0
        for idx, item in enumerate(self.file_items):
            logger.info(f"Processing item {idx}: {getattr(item, 'name', 'Unknown')}")
            
            if not hasattr(item, "name") or not hasattr(item, "size_mb"):
                logger.warning(f"Item {idx} missing required attributes: name={hasattr(item, 'name')}, size_mb={hasattr(item, 'size_mb')}")
                continue
                
            valid_count += 1
            
            # 序号列：显示锁标志（如果文件被限制编辑）
            if hasattr(item, "encryption_status") and item.encryption_status != EncryptionStatus.OK:
                lock_text = f"🔒 {idx + 1}"
                no_item = QTableWidgetItem(lock_text)
                no_item.setToolTip(self._("File is encrypted or restricted"))
                no_item.setForeground(QBrush(QColor(255, 0, 0)))  # 红色显示
            else:
                no_item = QTableWidgetItem(str(idx + 1))
            self.file_table.setItem(idx, 0, no_item)
            
            # 文件名列（绑定原始文件路径，确保排序/删除后行与数据一致）
            name_item = QTableWidgetItem(item.name)
            try:
                name_item.setData(Qt.UserRole, getattr(item, 'path', None))
            except Exception:
                pass
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            name_item.setToolTip(item.name)
            self.file_table.setItem(idx, 1, name_item)
            
            # 立即验证设置是否成功
            if self.file_table.item(idx, 1):
                logger.info(f"Row {idx} name item set successfully: {self.file_table.item(idx, 1).text()}")
            else:
                logger.error(f"Row {idx} name item failed to set!")
            
            # 其他列
            self.file_table.setItem(idx, 2, QTableWidgetItem(f"{item.size_mb:.2f}"))
            self.file_table.setItem(idx, 3, QTableWidgetItem(str(item.page_count)))
            self.file_table.setItem(idx, 4, QTableWidgetItem(item.header_text))
            self.file_table.setItem(idx, 5, QTableWidgetItem(item.footer_text or ""))
            
            logger.info(f"Successfully added row {idx} for file: {item.name}")
        
        logger.info(f"Table populated with {valid_count} valid rows out of {len(self.file_items)} items")
        logger.info(f"Final table row count: {self.file_table.rowCount()}")
        
        # 调试：验证表格内容
        for row in range(self.file_table.rowCount()):
            name_item = self.file_table.item(row, 1)
            if name_item:
                logger.info(f"Table row {row}: {name_item.text()}")
            else:
                logger.warning(f"Table row {row}: No name item found!")
        
        # 强制刷新表格显示
        self.file_table.viewport().update()
        
        # 调试：再次验证表格状态
        logger.info(f"After population - Table row count: {self.file_table.rowCount()}")
        logger.info(f"After population - file_items count: {len(self.file_items)}")
        
        # 如果表格行数不正确，强制重新设置
        if self.file_table.rowCount() != len(self.file_items):
            logger.warning(f"Table row count mismatch! Setting to {len(self.file_items)}")
            self.file_table.setRowCount(len(self.file_items))
            # 重新填充表格
            for idx, item in enumerate(self.file_items):
                if hasattr(item, "name") and hasattr(item, "size_mb"):
                    # 序号列
                    if hasattr(item, "encryption_status") and item.encryption_status != EncryptionStatus.OK:
                        lock_text = f"🔒 {idx + 1}"
                        no_item = QTableWidgetItem(lock_text)
                        no_item.setToolTip(self._("File is encrypted or restricted"))
                        no_item.setForeground(QBrush(QColor(255, 0, 0)))
                    else:
                        no_item = QTableWidgetItem(str(idx + 1))
                    self.file_table.setItem(idx, 0, no_item)
                    
                    # 文件名列
                    name_item = QTableWidgetItem(item.name)
                    name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    name_item.setToolTip(item.name)
                    self.file_table.setItem(idx, 1, name_item)
                    
                    # 其他列
                    self.file_table.setItem(idx, 2, QTableWidgetItem(f"{item.size_mb:.2f}"))
                    self.file_table.setItem(idx, 3, QTableWidgetItem(str(item.page_count)))
                    self.file_table.setItem(idx, 4, QTableWidgetItem(item.header_text))
                    self.file_table.setItem(idx, 5, QTableWidgetItem(item.footer_text or ""))
        
        # 保持禁用内置排序，统一使用自定义排序；若已有排序状态，重放一次
        self.file_table.setSortingEnabled(False)
        # 不在此处调用自定义排序，避免递归填充；由触发端显式调用
        self._update_ui_state()
        if self.file_items: self._font_linked_once = False

    def _get_item_index_by_row(self, row: int) -> int:
        """通过表格行安全地映射到 self.file_items 下标（基于路径绑定）。"""
        try:
            if row < 0:
                return -1
            name_item = self.file_table.item(row, 1)
            if name_item is None:
                return -1
            path = name_item.data(Qt.UserRole)
            if not path:
                return row if 0 <= row < len(self.file_items) else -1
            for i, it in enumerate(self.file_items):
                if getattr(it, 'path', None) == path:
                    return i
            return -1
        except Exception:
            return -1

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
        folder = QFileDialog.getExistingDirectory(self, self._("Select Output Directory"))
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
        selected_rows = sorted([r.row() for r in self.file_table.selectionModel().selectedRows()], reverse=True)
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
            QMessageBox.warning(self, self._("No Files"), self._("Please import PDF files first."))
            return
        if not self.output_folder:
            QMessageBox.warning(self, self._("No Output Folder"), self._("Please select an output folder."))
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
        # 传递结构化模式 & A4 规范化 & 中文结构化选项
        if settings.get('structured'):
            header_settings['structured'] = True
            footer_settings['structured'] = True
            if settings.get('structured_cn_fixed'):
                header_settings['structured_cn_fixed'] = True
                footer_settings['structured_cn_fixed'] = True
                header_settings['structured_cn_font'] = settings.get('structured_cn_font')
                footer_settings['structured_cn_font'] = settings.get('structured_cn_font')
        if settings.get('normalize_a4', True):
            header_settings['normalize_a4'] = True
            footer_settings['normalize_a4'] = True
        if settings.get('memory_optimization'):
            header_settings['memory_optimization'] = True
            footer_settings['memory_optimization'] = True

        self.progress_label.setText(self._("Processing... (0%)"))
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
            msg = self._("The following files are encrypted or restricted:") + "\n\n"
            msg += "\n".join(f"- {name}" for name in encrypted)
            msg += "\n\n" + self._("Please unlock them using the right-click menu before processing.")
            QMessageBox.warning(self, self._("Encrypted Files Detected"), msg)
            return False
        return True

    def on_processing_finished(self, results: list):
        """处理完成后的回调函数"""
        self.processed_paths = [res["output"] for res in results if res["success"]]
        failed = [res for res in results if not res["success"]]

        self.progress_label.setText(self._("Completed {} files").format(len(self.processed_paths)))

        if failed:
            msg = "\n".join([f"{os.path.basename(res['input'])}: {res['error']}" for res in failed])
            QMessageBox.warning(self, self._("Some Files Failed"), msg)
        else:
            QMessageBox.information(self, self._("Done"), self._("All files processed successfully."))
            self.progress_label.setText("")

        if self.merge_checkbox.isChecked() and self.processed_paths:
            dlg = MergeDialog(self.processed_paths, self)
            dlg.merge_confirmed.connect(self.handle_merge_confirmation)
            dlg.exec()
        
        self._set_controls_enabled(True)

    def handle_merge_confirmation(self, ordered_paths: list):
        """处理合并确认后的逻辑，包含统一的成功/失败提示"""
        save_path, _ = QFileDialog.getSaveFileName(self, self._("Save Merged PDF"), "", "PDF Files (*.pdf)")
        if not save_path: return
        
        try:
            success, err = merge_pdfs(ordered_paths, save_path)
            if not success: raise Exception(err)

            final_message = self._("Files merged successfully and saved to:\n") + save_path
            if self.page_number_checkbox.isChecked():
                add_page_numbers(
                    input_pdf=save_path, output_pdf=save_path,
                    font_name=self.footer_font_select.currentText(), font_size=self.footer_font_size_spin.value(),
                    x=self.footer_x_input.value(), y=self.footer_y_input.value()
                )
                final_message = self._("Files merged and page numbers added successfully:\n") + save_path
            
            QMessageBox.information(self, self._("Success"), final_message)
        except Exception as e:
            self.show_error(self._("Operation Failed"), e)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        """处理文件拖放，增强校验"""
        if not event.mimeData().hasUrls(): return
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in urls if url.isLocalFile() and url.toLocalFile().lower().endswith('.pdf')]
        
        if not paths: QMessageBox.warning(self, self._("Invalid Files"), self._("Only PDF files can be imported.")); return
        self._process_imported_paths(paths)
        event.acceptProposedAction()

    def _process_imported_paths(self, paths: list):
        """处理导入的文件路径列表（来自对话框或拖放）"""
        try:
            new_items = self.controller.handle_file_import(paths)
            logger.info(f"Controller returned {len(new_items)} items")
            
            # 只添加 PDFFileItem 类型且有 name 和 size_mb 属性的 item，防止嵌套导致后续 item.name 报错
            valid_items = [
                item for item in new_items
                if isinstance(item, PDFFileItem) and hasattr(item, "name") and hasattr(item, "size_mb")
            ]
            logger.info(f"Found {len(valid_items)} valid items")
            
            self.file_items.extend(valid_items)
            logger.info(f"Total file_items count: {len(self.file_items)}")
            
            self._populate_table_from_items()
            QTimer.singleShot(100, self._recommend_fonts)
            # 确保UI状态正确更新
            self._update_ui_state()

            # 新增：分析加密状态并提示
            locked_files = [item.name for item in new_items if isinstance(item, PDFFileItem) and getattr(item, "encryption_status", None) == EncryptionStatus.LOCKED]
            restricted_files = [item.name for item in new_items if isinstance(item, PDFFileItem) and getattr(item, "encryption_status", None) == EncryptionStatus.RESTRICTED]
            if locked_files or restricted_files:
                msg = ""
                if locked_files:
                    msg += self._("The following files are fully encrypted and require a password:\n") + "\n".join(f"• {f}" for f in locked_files) + "\n\n"
                if restricted_files:
                    msg += self._("The following files are restricted (e.g., can't be modified):\n") + "\n".join(f"• {f}" for f in restricted_files)
                QMessageBox.information(self, self._("Encrypted Files Notice"), msg.strip())

        except Exception as e:
            self.show_error(self._("Failed to import files"), e)

    def update_preview(self):
        """更新预览：委托给 PreviewManager 统一处理"""
        try:
            if hasattr(self, 'preview') and self.preview:
                self.preview.update_preview()
        except Exception:
            pass
    
    def update_position_preview(self):
        """(Deprecated) 更新页眉和页脚位置预览. 此函数将被新预览逻辑替代。"""
        pass
    
    def update_header_position_preview(self):
        """(Deprecated)"""
        pass
    
    def update_footer_position_preview(self):
        """(Deprecated)"""
        pass

    def _render_text_overlay_for_preview(self, text: str, font_name: str, font_size: int, page_width: float, page_height: float, x: float, y: float) -> Optional[QPixmap]:
        """
        使用 ReportLab 在内存中生成仅包含文本的、透明背景的 PDF，并将其渲染为 QPixmap。
        """
        try:
            packet = BytesIO()
            # 创建与PDF页面完全相同尺寸的画布
            can = rl_canvas.Canvas(packet, pagesize=(page_width, page_height))
            
            # 确保字体已注册
            actual_font = font_name
            if not register_font_safely(font_name):
                suggested = suggest_chinese_fallback_font(font_name)
                if suggested and register_font_safely(suggested):
                    actual_font = suggested
                else:
                    logger.warning(f"[Preview] 无法注册字体 '{font_name}'，回退到 Helvetica。")
                    actual_font = "Helvetica" # ReportLab 内置
            
            can.setFont(actual_font, font_size)
            can.drawString(x, y, text)
            can.save()
            
            packet.seek(0)
            
            # 使用 PyMuPDF 渲染这个 overlay PDF
            overlay_doc = fitz.open("pdf", packet.read())
            pix = overlay_doc[0].get_pixmap(alpha=True) # 必须使用 alpha=True
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGBA8888)
            return QPixmap.fromImage(image)

        except Exception as e:
            logger.error(f"渲染预览文本覆盖层失败: {e}", exc_info=True)
            return None

    def update_pdf_content_preview(self):
        """委托到 PreviewManager 渲染预览"""
        try:
            if hasattr(self, 'preview') and self.preview:
                return self.preview.update_pdf_content_preview()
        except Exception:
            pass

    def _draw_simulated_preview(self, painter: QPainter, settings: dict, header_text: str, footer_text: str):
        """绘制模拟预览（当无法加载真实PDF内容时）"""
        # 绘制页面背景（模拟A4页面）
        page_width = 595  # A4宽度 (pt)
        page_height = 842  # A4高度 (pt)
        scale = min(350 / page_width, 250 / page_height)
        
        scaled_width = int(page_width * scale)
        scaled_height = int(page_height * scale)
        start_x = (400 - scaled_width) // 2
        start_y = (300 - scaled_height) // 2
        
        # 绘制页面边框
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(start_x, start_y, scaled_width, scaled_height)
        
        # 绘制页眉文本
        if header_text:
            painter.setPen(Qt.blue)
            font_size = int(settings.get("header_font_size", 14) * scale)
            painter.setFont(QFont(settings.get("header_font", "Arial"), font_size))
            
            header_x = start_x + int(settings.get("header_x", 72) * scale)
            header_y = start_y + int(settings.get("header_y", 752) * scale)
            
            text_width = painter.fontMetrics().horizontalAdvance(header_text[:50])
            if settings.get("header_alignment", "left") == "right":
                header_x = start_x + scaled_width - text_width - 20
            elif settings.get("header_alignment", "left") == "center":
                header_x = start_x + (scaled_width - text_width) // 2
            
            painter.drawText(header_x, header_y, header_text[:50])
        
        # 绘制页脚文本
        if footer_text:
            painter.setPen(Qt.red)
            font_size = int(settings.get("footer_font_size", 14) * scale)
            painter.setFont(QFont(settings.get("footer_font", "Arial"), font_size))
            
            footer_x = start_x + int(settings.get("footer_x", 72) * scale)
            footer_y = start_y + int(settings.get("footer_y", 40) * scale)
            
            text_width = painter.fontMetrics().horizontalAdvance(footer_text[:50])
            if settings.get("footer_alignment", "left") == "right":
                footer_x = start_x + scaled_width - text_width - 20
            elif settings.get("footer_alignment", "left") == "center":
                footer_x = start_x + (scaled_width - text_width) // 2
            
            painter.drawText(footer_x, footer_y, footer_text[:50])
    
    def _get_current_header_text(self) -> str:
        """获取当前页眉文本"""
        row = self.file_table.currentRow()
        if row >= 0 and row < len(self.file_items):
            if self.file_table.item(row, 4):
                return self.file_table.item(row, 4).text()
            elif hasattr(self.file_items[row], 'header_text'):
                return self.file_items[row].header_text or ""
        return ""
    
    def _get_current_footer_text(self) -> str:
        """获取当前页脚文本"""
        row = self.file_table.currentRow()
        if row >= 0 and row < len(self.file_items):
            if self.file_table.item(row, 5):
                return self.file_table.item(row, 5).text()
            elif hasattr(self.file_items[row], 'footer_text'):
                return self.file_items[row].footer_text or ""
        return ""

    def _validate_positions(self):
        """验证Y坐标是否在打印安全区内"""
        # 由于我们使用动态创建的警告标签，这里暂时跳过验证
        # 如果需要验证，可以在创建警告标签时保存引用
        pass

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
            self.show_error(self._("Failed to apply settings due to an error. Please check the logs."), e)

    def closeEvent(self, event):
        """在关闭应用前保存设置"""
        from config import save_settings
        save_settings(self._get_current_settings())
        event.accept()

    def show_error(self, message: str, exception: Exception = None):
        """显示错误信息对话框和日志，增强日志记录"""
        self.progress_label.setText(message)
        if exception: logger.error(f"UI Error: '{message}'", exc_info=True)
        QMessageBox.critical(self, self._("Error"), f"{message}\n\n{str(exception or '')}")
    
    def update_progress(self, current: int, total: int, filename: str):
        """更新进度条和状态栏"""
        percent = int((current / total) * 100)
        
        # 更新进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(percent)
        self.progress_bar.setMaximum(total)
        
        # 更新状态栏
        self.statusBar.showMessage(f"{self._('Processing')} {current}/{total}: {filename}")
        
        # 更新进度标签
        self.progress_label.setText(self._("Processing... ") + f"({percent}%) - {filename}")
        
        # 处理完成后隐藏进度条
        if current == total:
            QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
            self.statusBar.showMessage(self._("Ready"))
    
    def show_about_dialog(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, self._("About DocDeck"),
            self._("DocDeck - PDF Header & Footer Tool\n") +
            f"Version {__import__('config').config.APP_VERSION}\n\n" +
            self._("Author: 木小樨\n") +
            self._("Project Homepage:\n") +
            "https://hs2wxdogy2.feishu.cn/wiki/Kjv3wQfV5iKpGXkQ8aCcOkj6nVf"
        )

    def _setup_context_menu(self):
        """设置文件列表的右键菜单"""
        logger.info("Setting up context menu for file table")
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self._show_context_menu)
        logger.info("Context menu setup completed")
    
    def _setup_drag_drop(self):
        """设置拖拽支持"""
        # 设置文件表格接受拖拽
        self.file_table.setAcceptDrops(True)
        self.file_table.dragEnterEvent = self._drag_enter_event
        self.file_table.dropEvent = self._drop_event
        
        # 设置主窗口接受拖拽
        self.dragEnterEvent = self._main_drag_enter_event
        self.dropEvent = self._main_drop_event
    
    def _drag_enter_event(self, event):
        """文件表格拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            event.setDropAction(Qt.CopyAction)
    
    def _drop_event(self, event):
        """文件表格拖拽放置事件"""
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
        if paths:
            self._process_imported_paths(paths)
        event.acceptProposedAction()
    
    def _main_drag_enter_event(self, event):
        """主窗口拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            event.setDropAction(Qt.CopyAction)
    
    def _main_drop_event(self, event):
        """主窗口拖拽放置事件"""
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
        if paths:
            self._process_imported_paths(paths)
        event.acceptProposedAction()

    def _show_context_menu(self, position):
        """显示右键菜单（基于行→数据索引映射，避免排序/删除后错乱）"""
        logger.info(f"Context menu requested at position: {position}")
        view_row = self.file_table.rowAt(position.y())
        logger.info(f"Row at position: {view_row}")
        data_index = self._get_item_index_by_row(view_row)
        if data_index < 0 or data_index >= len(self.file_items):
            logger.warning(f"Invalid row: {view_row}, file_items count: {len(self.file_items)}")
            return
        
        menu = QMenu(self)
        
        # 检查文件是否被加密或限制
        item = self.file_items[data_index]
        logger.info(f"File item: {item.name}, encryption_status: {getattr(item, 'encryption_status', 'N/A')}")
        
        # 详细检查加密状态
        logger.info(f"File encryption check:")
        logger.info(f"  - hasattr encryption_status: {hasattr(item, 'encryption_status')}")
        logger.info(f"  - encryption_status value: {getattr(item, 'encryption_status', 'N/A')}")
        logger.info(f"  - EncryptionStatus.OK: {EncryptionStatus.OK}")
        logger.info(f"  - EncryptionStatus.LOCKED: {EncryptionStatus.LOCKED}")
        logger.info(f"  - comparison result: {getattr(item, 'encryption_status', 'N/A') != EncryptionStatus.OK}")
        logger.info(f"  - is LOCKED: {getattr(item, 'encryption_status', 'N/A') == EncryptionStatus.LOCKED}")
        
        # 检查是否是加密文件
        is_encrypted = (hasattr(item, "encryption_status") and 
                       item.encryption_status in [EncryptionStatus.LOCKED, EncryptionStatus.RESTRICTED])
        
        logger.info(f"Encryption check result: {is_encrypted}")
        logger.info(f"=== 右键菜单详情 ===")
        logger.info(f"点击的行号: {view_row} -> 数据索引: {data_index}")
        logger.info(f"文件名: {item.name}")
        logger.info(f"加密状态: {item.encryption_status}")
        logger.info(f"是否加密: {is_encrypted}")
        logger.info(f"==================")
        
        # 多种方法检查是否需要显示解锁选项
        show_unlock = False
        
        # 方法1：检查加密状态
        if is_encrypted:
            show_unlock = True
            logger.info(f"方法1：根据加密状态显示解锁选项")
        
        # 方法2：取消基于文件名的硬编码启发，避免误判
        
        # 方法3：检查UI显示的锁图标
        try:
            name_item = self.file_table.item(view_row, 1)  # 文件名列
            if name_item and "🔒" in name_item.text():
                show_unlock = True
                logger.info(f"方法3：根据UI锁图标显示解锁选项")
        except:
            pass
        
        logger.info(f"最终决定：是否显示解锁选项 = {show_unlock}")
        
        if show_unlock:
            logger.info(f"添加解锁选项")
            unlock_action = menu.addAction("🔓 解锁文件")
            unlock_action.triggered.connect(lambda: self._unlock_file_at_row(data_index))
            menu.addSeparator()
        else:
            logger.info(f"不显示解锁选项")
        
        # 编辑页眉页脚
        edit_action = menu.addAction("✏️ " + self._("编辑页眉页脚"))
        edit_action.triggered.connect(lambda: self._edit_headers_footers(data_index))
        
        # 删除原页眉页脚
        remove_action = menu.addAction("✂️ " + self._("删除原页眉页脚"))
        remove_action.triggered.connect(lambda: self._remove_existing_headers_footers(data_index))
        
        # 删除文件
        delete_action = menu.addAction("🗑️ " + self._("删除"))
        delete_action.triggered.connect(lambda: self._delete_file_at_row(data_index))
        
        logger.info(f"Context menu created with {menu.actions().__len__()} actions")
        menu.exec_(self.file_table.mapToGlobal(position))

    def _edit_headers_footers(self, row: int):
        """编辑页眉页脚"""
        if row >= 0 and row < len(self.file_items):
            try:
                item = self.file_items[row]
                
                # 获取当前设置
                current_header = getattr(item, 'header_text', '')
                current_footer = getattr(item, 'footer_text', '')
                
                # 创建编辑对话框
                from PySide6.QtWidgets import QInputDialog, QLineEdit
                
                # 编辑页眉
                header_text, ok1 = QInputDialog.getText(
                    self, 
                    self._("编辑页眉"), 
                    self._("请输入页眉文本:"),
                    QLineEdit.Normal,
                    current_header
                )
                
                if ok1:
                    # 编辑页脚
                    footer_text, ok2 = QInputDialog.getText(
                        self, 
                        self._("编辑页脚"), 
                        self._("请输入页脚文本:"),
                        QLineEdit.Normal,
                        current_footer
                    )
                    
                    if ok2:
                        # 更新文件项
                        item.header_text = header_text
                        item.footer_text = footer_text
                        
                        # 刷新表格显示
                        self._populate_table_from_items()
                        
                        QMessageBox.information(self, self._("编辑成功"), 
                            f"{self._('页眉页脚编辑成功！')}\n\n"
                            f"{self._('页眉')}: {header_text or '-'}\n"
                            f"{self._('页脚')}: {footer_text or '-'}")
                        
            except Exception as e:
                QMessageBox.warning(self, self._("编辑失败"), f"{self._('编辑页眉页脚失败')}: {str(e)}")

    def _remove_existing_headers_footers(self, row: int):
        """删除现有页眉页脚"""
        if row >= 0 and row < len(self.file_items):
            try:
                item = self.file_items[row]
                
                # 确认操作
                reply = QMessageBox.question(
                    self, 
                    self._("确认删除"), 
                    f"{self._('确定要删除文件')} '{item.name}' {self._('的现有页眉页脚吗？')}\n\n{self._('此操作将创建备份文件，如果删除失败会自动恢复。')}",
                    QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
                )
                
                if reply == QMessageBox.StandardButton.Ok:
                    # 检查输出目录
                    if not self.output_folder:
                        QMessageBox.warning(self, self._("请先选择输出文件夹"), self._("删除页眉页脚需要先选择输出文件夹"))
                        return
                    
                    # 调用控制器处理
                    result = self.controller.remove_existing_headers_footers(item, self.output_folder)
                    
                    if result.get('success'):
                        QMessageBox.information(self, self._("删除成功"), 
                            f"{self._('页眉页脚删除成功！')}\n\n"
                            f"{self._('输出文件')}: {result.get('output_path', 'N/A')}\n"
                            f"{self._('备份文件')}: {result.get('backup_path', 'N/A')}")
                        
                        # 更新文件项
                        if result.get('output_path'):
                            item.path = result['output_path']
                            item.name = os.path.basename(result['output_path'])
                    else:
                        QMessageBox.warning(self, self._("删除失败"), 
                            f"{self._('页眉页脚删除失败')}: {result.get('error', '未知错误')}")
                        
            except Exception as e:
                QMessageBox.warning(self, self._("删除失败"), f"{self._('删除现有页眉页脚失败')}: {str(e)}")

    def _delete_file_at_row(self, row: int):
        """删除指定行的文件（row 为数据索引，不是视图行）"""
        if row >= 0 and row < len(self.file_items):
            reply = QMessageBox.question(
                self, self._("确认要删除文件"), 
                f"{self._('确定要删除文件')} '{self.file_items[row].name}' {self._('吗？')}",
                QMessageBox.StandardButton.Ok |
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Ok:
                self.file_items.pop(row)
                self._populate_table_from_items()

    def _unlock_selected(self):
        """解锁当前选中的一个或多个文件（仅对受限/加密文件生效）。"""
        selected_rows = [r.row() for r in self.file_table.selectionModel().selectedRows()]
        if not selected_rows:
            QMessageBox.information(self, self._("Locked File"), self._("Please select PDF files first."))
            return
        # 需要输出目录
        if not getattr(self, 'output_folder', None):
            QMessageBox.warning(self, self._("Output Folder Not Set"), self._("Please select an output folder..."))
            return
        # 去重并映射到数据索引
        data_indices = []
        for vr in selected_rows:
            di = self._get_item_index_by_row(vr)
            if di >= 0 and di not in data_indices:
                data_indices.append(di)
        if not data_indices:
            return
        # 逐个尝试解锁
        for di in data_indices:
            item = self.file_items[di]
            if getattr(item, 'encryption_status', EncryptionStatus.OK) in [EncryptionStatus.LOCKED, EncryptionStatus.RESTRICTED]:
                try:
                    if item.encryption_status == EncryptionStatus.LOCKED:
                        # 询问密码
                        password, ok = QInputDialog.getText(self, self._("Decrypt PDF"), self._("Please enter the password:"))
                        if not ok:
                            continue
                        res = self.controller.handle_unlock_pdf(item=item, password=password, output_dir=self.output_folder)
                        if res.get('success'):
                            # 更新 UI 行状态（锁图标清除）
                            pass
                    else:
                        # 受限：询问是否尝试自动解锁
                        reply = QMessageBox.question(
                            self,
                            self._("Restricted PDF"),
                            self._("This PDF is restricted and cannot be modified.\nDo you want to attempt automatic unlocking?"),
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.Yes:
                            res = self.controller.handle_unlock_pdf(item=item, password="", output_dir=self.output_folder)
                            if res.get('success'):
                                pass
                except Exception as e:
                    logger.error("Batch unlock error", exc_info=True)
        # 刷新
        self._populate_table_from_items()
        QMessageBox.information(self, self._("Unlock Success"), self._("Unlocked file saved to: ") + str(getattr(item, 'unlocked_path', '')))
    
    def _unlock_file_at_row(self, row: int):
        """解锁指定行的加密文件（row 为数据索引）"""
        if row < 0 or row >= len(self.file_items):
            return
            
        item = self.file_items[row]
        if not hasattr(item, "encryption_status") or item.encryption_status == EncryptionStatus.OK:
            QMessageBox.information(self, self._("无需解锁"), self._("此文件无需解锁"))
            return
            
        try:
            # 检查是否有输出文件夹
            if not self.output_folder:
                QMessageBox.warning(self, self._("请先选择输出文件夹"), self._("解锁文件需要先选择输出文件夹"))
                return
            
            # 根据加密状态选择解锁方式
            if item.encryption_status == EncryptionStatus.LOCKED:
                # 完全加密的文件，需要密码
                password, ok = QInputDialog.getText(
                    self, 
                    self._("输入密码"), 
                    f"{self._('文件')} '{item.name}' {self._('需要密码解锁，请输入密码：')}",
                    QLineEdit.EchoMode.Password
                )
                if not ok:
                    return
                    
                # 尝试用密码解锁
                result = self.controller.handle_unlock_pdf(item=item, password=password, output_dir=self.output_folder)
                
            else:  # EncryptionStatus.RESTRICTED
                # 受限制的文件，尝试强制解锁
                reply = QMessageBox.question(
                    self, 
                    self._("确认强制解锁"), 
                    f"{self._('文件')} '{item.name}' {self._('受编辑限制，是否尝试强制解锁？')}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    result = self.controller.handle_unlock_pdf(item=item, password="", output_dir=self.output_folder)
                else:
                    return
            
            # 处理解锁结果
            if result.get("success"):
                QMessageBox.information(
                    self, 
                    self._("解锁成功"), 
                    f"{self._('文件解锁成功！')}\n\n{result.get('message', '')}"
                )
                
                # 更新文件项
                if result.get("output_path"):
                    item.unlocked_path = result.get("output_path")
                    item.encryption_status = EncryptionStatus.OK
                    
                    # 刷新表格显示
                    self._populate_table_from_items()
                    
                    # 更新状态栏
                    self.progress_label.setText(self._("文件解锁成功"))
                    
            else:
                QMessageBox.warning(
                    self, 
                    self._("解锁失败"), 
                    f"{self._('文件解锁失败：')}\n{result.get('message', '未知错误')}"
                )
                
        except Exception as e:
            logger.error(f"Unlock file error: {e}", exc_info=True)
            QMessageBox.critical(
                self, 
                self._("解锁错误"), 
                f"{self._('解锁文件时发生错误：')}\n{str(e)}"
            )

    def _on_unit_changed(self, unit: str):
        """单位改变时转换所有位置值"""
        if not hasattr(self, '_last_unit') or not self._last_unit:
            self._last_unit = unit
            return
            
        old_unit = self._last_unit
        self._last_unit = unit
        
        # 转换页眉位置
        old_x = self.x_input.value()
        old_y = self.y_input.value()
        new_x = self._convert_unit(old_x, old_unit, unit)
        new_y = self._convert_unit(old_y, old_unit, unit)
        
        # 暂时断开信号连接避免循环调用
        self.x_input.blockSignals(True)
        self.y_input.blockSignals(True)
        self.x_input.setValue(int(new_x))
        self.y_input.setValue(int(new_y))
        self.x_input.blockSignals(False)
        self.y_input.blockSignals(False)
        
        # 转换页脚位置
        old_x = self.footer_x_input.value()
        old_y = self.footer_y_input.value()
        new_x = self._convert_unit(old_x, old_unit, unit)
        new_y = self._convert_unit(old_y, old_unit, unit)
        
        self.footer_x_input.blockSignals(True)
        self.footer_y_input.blockSignals(True)
        self.footer_x_input.setValue(int(new_x))
        self.footer_y_input.setValue(int(new_y))
        self.footer_x_input.blockSignals(False)
        self.footer_y_input.blockSignals(False)
        
        # 更新标签显示
        self._update_position_labels()
        
        # 更新预览
        self.update_preview()

    def _convert_unit(self, value: float, from_unit: str, to_unit: str) -> float:
        """转换单位"""
        # 先转换为pt
        if from_unit == "cm":
            value = value * 28.35
        elif from_unit == "mm":
            value = value * 2.835
        elif from_unit == "pt":
            pass
        else:
            return value
        
        # 从pt转换为目标单位
        if to_unit == "cm":
            return value / 28.35
        elif to_unit == "mm":
            return value / 2.835
        elif to_unit == "pt":
            return value
        else:
            return value
    

    
    def _import_settings(self):
        """导入设置"""
        try:
            from PySide6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                self._("Import Settings"), 
                "", 
                "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                self._apply_settings(settings)
                QMessageBox.information(self, self._("Success"), self._("Settings imported successfully!"))
                
        except Exception as e:
            QMessageBox.critical(self, self._("Error"), f"{self._('Failed to import settings')}: {str(e)}")
    
    def _export_settings(self):
        """导出设置"""
        try:
            from PySide6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                self._("Export Settings"), 
                "docdeck_settings.json", 
                "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                settings = self._get_current_settings()
                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(self, self._("Success"), self._("Settings exported successfully!"))
                
        except Exception as e:
            QMessageBox.critical(self, self._("Error"), f"{self._('Failed to export settings')}: {str(e)}")
    
    def _reset_settings(self):
        """重置设置为默认值"""
        reply = QMessageBox.question(
            self, 
            self._("Reset Settings"), 
            self._("Are you sure you want to reset all settings to default values?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 重置所有控件到默认值
                self.font_select.setCurrentText("Arial")
                self.font_size_spin.setValue(14)
                self.x_input.setValue(50)
                self.y_input.setValue(800)
                
                self.footer_font_select.setCurrentText("Arial")
                self.footer_font_size_spin.setValue(14)
                self.footer_x_input.setValue(400)
                self.footer_y_input.setValue(50)
                
                self.structured_checkbox.setChecked(False)
                self.normalize_a4_checkbox.setChecked(True)
                self.memory_optimization_checkbox.setChecked(True)
                
                # 更新预览
                self.update_preview()
                
                QMessageBox.information(self, self._("Success"), self._("Settings reset to defaults!"))
                
            except Exception as e:
                QMessageBox.critical(self, self._("Error"), f"{self._('Failed to reset settings')}: {str(e)}")
    
    def _change_language(self, language: str):
        """切换语言"""
        try:
            # 保存当前设置
            current_settings = self._get_current_settings()
            
            # 重新设置语言
            self.locale_manager.set_locale(language)
            
            # 刷新UI文本
            self._refresh_ui_texts()
            
            # 恢复设置
            self._apply_settings(current_settings)
            
        except Exception as e:
            logger.error(f"Language change failed: {e}", exc_info=True)
    
    def _setup_modern_style(self):
        """设置现代化界面样式"""
        # 设置应用程序样式表
        style_sheet = """
        QMainWindow {
            background-color: #f5f5f5;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #d0d0d0;
            border-radius: 8px;
            margin-top: 1ex;
            padding-top: 10px;
            background-color: white;
        }
        """
        self.setStyleSheet(style_sheet)
    
    def _refresh_ui_texts(self):
        """刷新UI文本"""
        # 更新窗口标题
        self.setWindowTitle(self._("DocDeck - PDF Header & Footer Tool"))
        
        # 更新状态栏
        self.statusBar().showMessage(self._("Ready"))
        
        # 刷新表格标题
        self.file_table.setHorizontalHeaderLabels([
            "", self._("No."), self._("Filename"), self._("Page Count"), 
            self._("Status"), self._("Header Text"), self._("Footer Text")
        ])
        
        # 更新预览
        self.update_preview()
    
    def _update_position_labels(self):
        """更新位置标签显示当前单位"""
        unit = self.unit_combo.currentText()
        self.x_input.setToolTip(self._("X Position in ") + unit)
        self.y_input.setToolTip(self._("Y Position in ") + unit)
        self.footer_x_input.setToolTip(self._("Footer X Position in ") + unit)
        self.footer_y_input.setToolTip(self._("Footer Y Position in ") + unit)

    def _on_header_template_changed(self, template: str):
        """页眉模板改变时的处理"""
        if template == self._("Custom"):
            return  # 保持当前自定义文本
        
        # 根据模板设置文本
        template_texts = {
            self._("Company Name"): "公司名称",
            self._("Document Title"): "文档标题", 
            self._("Date"): "{date}",
            self._("Page Number"): "第 {page} 页",
            self._("Confidential"): "机密文件",
            self._("Draft"): "草稿",
            self._("Final Version"): "最终版"
        }
    
    def _setup_modern_style(self):
        """设置现代化界面样式"""
        # 设置应用程序样式表
        style_sheet = """
        QMainWindow {
            background-color: #f5f5f5;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #d0d0d0;
            border-radius: 8px;
            margin-top: 1ex;
            padding-top: 10px;
            background-color: white;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            color: #2c3e50;
            background-color: white;
        }
        
        QPushButton {
            background-color: #3498db;
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: bold;
            min-height: 20px;
        }
        
        QPushButton:hover {
            background-color: #2980b9;
        }
        
        QPushButton:pressed {
            background-color: #21618c;
        }
        
        QPushButton:disabled {
            background-color: #bdc3c7;
            color: #7f8c8d;
        }
        
        QPushButton#start_button {
            background-color: #27ae60;
            font-size: 14px;
            padding: 12px 24px;
        }
        
        QPushButton#start_button:hover {
            background-color: #229954;
        }
        
        QPushButton#start_button:pressed {
            background-color: #1e8449;
        }
        
        QLineEdit, QSpinBox, QComboBox {
            border: 2px solid #d0d0d0;
            border-radius: 6px;
            padding: 6px;
            background-color: white;
            selection-background-color: #3498db;
        }
        
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
            border-color: #3498db;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #7f8c8d;
        }
        
        QComboBox:hover::down-arrow {
            border-top-color: #3498db;
        }
        
        QCheckBox {
            spacing: 8px;
            color: #2c3e50;
        }
        
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #d0d0d0;
            border-radius: 4px;
            background-color: white;
        }
        
        QCheckBox::indicator:checked {
            background-color: #3498db;
            border-color: #3498db;
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOEwxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
        }
        
        QCheckBox::indicator:hover {
            border-color: #3498db;
        }
        
        QTableWidget {
            background-color: white;
            alternate-background-color: #f8f9fa;
            gridline-color: #e9ecef;
            border: 1px solid #d0d0d0;
            border-radius: 6px;
        }
        
        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid #f1f3f4;
        }
        
        QTableWidget::item:selected {
            background-color: #3498db;
            color: white;
        }
        
        QHeaderView::section {
            background-color: #34495e;
            color: white;
            padding: 10px;
            border: none;
            font-weight: bold;
        }
        
        QHeaderView::section:hover {
            background-color: #2c3e50;
        }
        
        QLabel {
            color: #2c3e50;
        }
        
        QLabel#title_label {
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            padding: 10px;
        }
        
        QProgressBar {
            border: 2px solid #d0d0d0;
            border-radius: 6px;
            text-align: center;
            background-color: white;
        }
        
        QProgressBar::chunk {
            background-color: #3498db;
            border-radius: 4px;
        }
        
        QStatusBar {
            background-color: #ecf0f1;
            color: #2c3e50;
            border-top: 1px solid #d0d0d0;
        }
        
        QMenuBar {
            background-color: #34495e;
            color: white;
            border: none;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 8px 12px;
        }
        
        QMenuBar::item:selected {
            background-color: #2c3e50;
        }
        
        QMenu {
            background-color: white;
            border: 1px solid #d0d0d0;
            border-radius: 6px;
            padding: 4px;
        }
        
        QMenu::item {
            padding: 8px 20px;
            border-radius: 4px;
        }
        
        QMenu::item:selected {
            background-color: #3498db;
            color: white;
        }
        
        QScrollBar:vertical {
            background-color: #f1f3f4;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #c1c1c1;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #a8a8a8;
        }
        """
        
        self.setStyleSheet(style_sheet)
    
    def _refresh_ui_texts(self):
        """刷新UI文本"""
        # 更新窗口标题
        self.setWindowTitle(self._("DocDeck - PDF Header & Footer Tool"))
        
        # 更新菜单文本
        self.menuBar().actions()[0].setText(self._("File"))  # File菜单
        self.menuBar().actions()[1].setText(self._("Settings"))  # Settings菜单
        self.menuBar().actions()[2].setText(self._("Help"))  # Help菜单
        
        # 更新状态栏
        self.statusBar.showMessage(self._("Ready"))
        
        # 刷新表格标题
        self.file_table.setHorizontalHeaderLabels([
            self._("No."), self._("Filename"), self._("Size (MB)"), 
            self._("Page Count"), self._("Header Text"), self._("Footer Text")
        ])
        
        # 更新预览
        self.update_preview()

    def _update_position_labels(self):
        """更新位置标签显示当前单位"""
        unit = self.unit_combo.currentText()
        self.x_input.setToolTip(self._("X Position in ") + unit)
        self.y_input.setToolTip(self._("Y Position in ") + unit)
        self.footer_x_input.setToolTip(self._("Footer X Position in ") + unit)
        self.footer_y_input.setToolTip(self._("Footer Y Position in ") + unit)

    def _on_header_template_changed(self, template: str):
        """页眉模板改变时的处理"""
        if template == self._("Custom"):
            return  # 保持当前自定义文本
        
        # 根据模板设置文本
        if self.language_map.get("单位:") == "单位:":  # 中文界面
            template_texts = {
                self._("Company Name"): "公司名称",
                self._("Document Title"): "文档标题",
                self._("Date"): "{date}",
                self._("Page Number"): "第 {page} 页",
                self._("Confidential"): "机密文件",
                self._("Draft"): "草稿",
                self._("Final Version"): "最终版"
            }
        else:  # 英文界面
            template_texts = {
                self._("Company Name"): "Company Name",
                self._("Document Title"): "Document Title",
                self._("Date"): "{date}",
                self._("Page Number"): "Page {page}",
                self._("Confidential"): "Confidential",
                self._("Draft"): "Draft",
                self._("Final Version"): "Final Version"
            }
        
        if template in template_texts:
            # 找到页眉文本输入框并设置值
            # 注意：这里需要根据实际的UI结构调整
            # 暂时使用全局页眉文本
            if hasattr(self, 'header_text_input'):
                self.header_text_input.setText(template_texts[template])
            elif hasattr(self, 'global_header_text'):
                self.global_header_text.setText(template_texts[template])
            
            # 更新预览
            self.update_preview()

    def _apply_top_right_preset(self):
        """应用右上角预设位置"""
        unit = self.unit_combo.currentText()
        
        # 计算右上角位置：距右边0.3cm，距上边0.8cm
        right_margin = 0.3  # cm
        top_margin = 0.8    # cm
        
        # 获取当前选中文件的实际页面尺寸来计算X位置
        row = self.file_table.currentRow()
        if row >= 0 and row < len(self.file_items):
            try:
                import fitz
                doc = fitz.open(self.file_items[row].path)
                if len(doc) > 0:
                    page = doc[0]
                    page_width = page.rect.width
                    # 转换页面宽度到当前单位
                    page_width_unit = self._convert_unit(page_width, "pt", unit)
                    # X = 页面宽度 - 右边距 - 预估文本宽度
                    font_size = self.font_size_spin.value()
                    estimated_text_width = font_size * 0.6 * 20  # 假设20个字符
                    x = page_width_unit - right_margin - estimated_text_width
                    self.x_input.setValue(max(0, int(x)))
                doc.close()
            except:
                # 如果无法获取页面尺寸，使用默认值
                self.x_input.setValue(72)
        
        # 设置Y位置（距上边0.8cm）
        if unit == "pt":
            y = 842 - (top_margin * 28.35)  # A4高度 - 上边距
        elif unit == "cm":
            y = 29.7 - top_margin  # A4高度29.7cm - 上边距
        else:  # mm
            y = 297 - (top_margin * 10)  # A4高度297mm - 上边距
        
        self.y_input.setValue(int(y))
        self.font_size_spin.setValue(14)  # 14号字体

    def _apply_bottom_right_preset(self):
        """应用右下角预设位置"""
        unit = self.unit_combo.currentText()
        
        # 计算右下角位置：距右边0.3cm，距下边0.8cm
        right_margin = 0.3  # cm
        bottom_margin = 0.8 # cm
        
        # 获取当前选中文件的实际页面尺寸来计算X位置
        row = self.file_table.currentRow()
        if row >= 0 and row < len(self.file_items):
            try:
                import fitz
                doc = fitz.open(self.file_items[row].path)
                if len(doc) > 0:
                    page = doc[0]
                    page_width = page.rect.width
                    # 转换页面宽度到当前单位
                    page_width_unit = self._convert_unit(page_width, "pt", unit)
                    # X = 页面宽度 - 右边距 - 预估文本宽度
                    font_size = self.footer_font_size_spin.value()
                    estimated_text_width = font_size * 0.6 * 20
                    x = page_width_unit - right_margin - estimated_text_width
                    self.footer_x_input.setValue(max(0, int(x)))
                doc.close()
            except:
                self.footer_x_input.setValue(72)
        
        # 设置Y位置（距下边0.8cm）
        if unit == "pt":
            y = bottom_margin * 28.35  # 下边距
        elif unit == "cm":
            y = bottom_margin  # 下边距
        else:  # mm
            y = bottom_margin * 10  # 下边距
        
        self.footer_y_input.setValue(int(y))
        self.footer_font_size_spin.setValue(14)  # 14号字体

    def _handle_header_click(self, logical_index: int):
        """处理标题栏点击，实现自定义排序"""
        try:
            # 获取当前排序状态
            current_order = self.file_table.horizontalHeader().sortIndicatorOrder()
            
            # 如果点击的是同一列，切换排序方向
            if self.current_sort_column == logical_index:
                new_order = Qt.DescendingOrder if current_order == Qt.AscendingOrder else Qt.AscendingOrder
            else:
                new_order = Qt.AscendingOrder
            
            # 调试：记录排序方向
            logger.info(f"Header click: column={logical_index}, current_order={current_order}, new_order={new_order}")
            
            # 执行排序
            self._perform_custom_sort(logical_index, new_order)
            
            # 更新排序状态
            self.current_sort_column = logical_index
            self.current_sort_order = new_order
            
            # 更新状态栏显示排序信息
            column_names = [self._("No."), self._("Filename"), self._("Size (MB)"), 
                           self._("Page Count"), self._("Header Text"), self._("Footer Text")]
            if 0 <= logical_index < len(column_names):
                # 修复状态栏显示：实际排序方向与Qt.SortOrder相反
                actual_order = "降序" if new_order == Qt.AscendingOrder else "升序"
                sort_text = f"{column_names[logical_index]} {actual_order}"
                self.progress_label.setText(self._("Sorted by: ") + sort_text)
                
            logger.info(f"Table sorted by column {logical_index} ({column_names[logical_index] if logical_index < len(column_names) else 'Unknown'}) in {'ascending' if new_order == Qt.AscendingOrder else 'descending'} order")
            
        except Exception as e:
            logger.error(f"Error handling header click: {e}", exc_info=True)
    
    def _perform_custom_sort(self, column: int, order: Qt.SortOrder):
        """执行自定义排序"""
        try:
            # 使用更简单的方法：直接对file_items进行排序，然后重新填充表格
            # 修复排序方向问题
            if order == Qt.DescendingOrder:
                reverse = True
                logger.info(f"Sort order: Descending (reverse=True)")
            else:
                reverse = False
                logger.info(f"Sort order: Ascending (reverse=False)")
            
            # 调试：记录排序方向
            logger.info(f"Qt.SortOrder value: {order}")
            logger.info(f"Qt.AscendingOrder: {Qt.AscendingOrder}")
            logger.info(f"Qt.DescendingOrder: {Qt.DescendingOrder}")
            logger.info(f"order == Qt.AscendingOrder: {order == Qt.AscendingOrder}")
            logger.info(f"order == Qt.DescendingOrder: {order == Qt.DescendingOrder}")
            
            if column == 0:  # 序号列 - 使用导入顺序排序
                logger.info(f"Applying import index sort for serial column")
                # 保证每个条目有 import_index
                for idx, it in enumerate(self.file_items):
                    if not hasattr(it, "import_index"):
                        setattr(it, "import_index", idx)
                self.file_items.sort(key=lambda x: getattr(x, "import_index", 0), reverse=reverse)
                logger.info(f"After sort by import_index: {[getattr(x,'import_index',0) for x in self.file_items]}")
            elif column == 1:  # 文件名列 - 使用自然排序（通用，稳定排序确保编号如 1,2,10 正确）
                logger.info(f"Applying natural sort to filenames (generic)")
                logger.info(f"Before sort: {[x.name for x in self.file_items]}")
                # 稳定排序：先按导入顺序，后按自然键
                self.file_items.sort(key=lambda x: getattr(x, 'import_index', 0))
                self.file_items.sort(key=lambda x: self.natural_sort_key(x.name), reverse=reverse)
                logger.info(f"After sort: {[x.name for x in self.file_items]}")
            elif column == 2:  # 大小列
                self.file_items.sort(key=lambda x: x.size_mb, reverse=reverse)
            elif column == 3:  # 页数列
                self.file_items.sort(key=lambda x: x.page_count, reverse=reverse)
            elif column == 4:  # 页眉列
                self.file_items.sort(key=lambda x: x.header_text.lower(), reverse=reverse)
            elif column == 5:  # 页脚列
                self.file_items.sort(key=lambda x: (x.footer_text or '').lower(), reverse=reverse)
            
            # 重新填充表格
            self._populate_table_from_items()
            
        except Exception as e:
            logger.error(f"Error performing custom sort: {e}", exc_info=True)
    
    def _on_sort_changed(self, logical_index: int, order: Qt.SortOrder):
        """处理表格排序变化（保留原有方法以兼容）"""
        try:
            # 记录排序状态
            self.current_sort_column = logical_index
            self.current_sort_order = order
            
            # 更新状态栏显示排序信息
            column_names = [self._("No."), self._("Filename"), self._("Size (MB)"), 
                           self._("Page Count"), self._("Header Text"), self._("Footer Text")]
            if 0 <= logical_index < len(column_names):
                sort_text = f"{column_names[logical_index]} {'↑' if order == Qt.AscendingOrder else '↓'}"
                self.progress_label.setText(self._("Sorted by: ") + sort_text)
                
            logger.info(f"Table sorted by column {logical_index} ({column_names[logical_index] if logical_index < len(column_names) else 'Unknown'}) in {'ascending' if order == Qt.AscendingOrder else 'descending'} order")
            
        except Exception as e:
            logger.error(f"Error handling sort change: {e}", exc_info=True)
