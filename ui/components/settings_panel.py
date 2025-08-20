"""
Settings Panel Module
管理页眉页脚设置面板的创建和信号处理
"""

from PySide6.QtWidgets import (
    QGroupBox, QGridLayout, QLabel, QComboBox, QSpinBox, 
    QPushButton, QHBoxLayout, QVBoxLayout, QLineEdit, QSizePolicy
)
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QFont
from font_manager import get_system_fonts


class SettingsPanel(QObject):
    """页眉页脚设置面板管理器"""
    
    # 信号定义
    settings_changed = Signal(dict)
    font_changed = Signal(str)
    size_changed = Signal(int)
    position_changed = Signal(int, int)
    alignment_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self._setup_ui_elements()
        
    def _setup_ui_elements(self):
        """初始化UI元素引用"""
        self.font_select = None
        self.footer_font_select = None
        self.font_size_spin = None
        self.footer_font_size_spin = None
        self.x_input = None
        self.footer_x_input = None
        self.y_input = None
        self.footer_y_input = None
        self.left_btn = None
        self.center_btn = None
        self.right_btn = None
        self.footer_left_btn = None
        self.footer_center_btn = None
        self.footer_right_btn = None
        self.global_footer_input = None
        self.unit_combo = None
        
    def create_settings_group(self) -> QGroupBox:
        """创建页眉页脚设置网格组"""
        group = QGroupBox("⚙️ " + self.parent._("Header & Footer Settings"))
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
        grid.setSpacing(12)
        grid.setContentsMargins(10, 20, 20, 20)
        # 收窄第0列宽度（“设置”列），增大内容列权重
        # 三列比例 1:2:2
        grid.setColumnMinimumWidth(0, 40)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 2)
        
        # 设置标签
        settings_header = QLabel(self.parent._("Settings"))
        settings_header.setStyleSheet("""
            font-weight: bold; 
            color: #2c3e50; 
            font-size: 13px;
            padding: 6px;
            background-color: #e9ecef;
            border-radius: 6px;
        """)
        settings_header.setAlignment(Qt.AlignCenter)
        # 固定“设置”标签宽度，进一步压缩该列
        # 不固定宽度，随列宽缩放
        settings_header.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        header_header = QLabel(self.parent._("Header"))
        header_header.setStyleSheet("""
            font-weight: bold; 
            color: #2c3e50; 
            font-size: 13px;
            padding: 8px;
            background-color: #d1ecf1;
            border-radius: 6px;
        """)
        header_header.setAlignment(Qt.AlignCenter)
        
        footer_header = QLabel(self.parent._("Footer"))
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
        font_label = QLabel(self.parent._("Font:"))
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
        self.font_select.currentTextChanged.connect(self._on_font_changed)
        
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
        self.footer_font_select.currentTextChanged.connect(self._on_font_changed)
        
        grid.addWidget(font_label, 1, 0)
        grid.addWidget(self.font_select, 1, 1)
        grid.addWidget(self.footer_font_select, 1, 2)
        
        # 字体大小
        size_label = QLabel(self.parent._("Size:"))
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
        self.font_size_spin.valueChanged.connect(self._on_size_changed)
        
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
        self.footer_font_size_spin.valueChanged.connect(self._on_size_changed)
        
        grid.addWidget(size_label, 2, 0)
        grid.addWidget(self.font_size_spin, 2, 1)
        grid.addWidget(self.footer_font_size_spin, 2, 2)
        
        # X位置
        x_label = QLabel(self.parent._("X Position:"))
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
        self.x_input.valueChanged.connect(self._on_position_changed)
        
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
        self.footer_x_input.valueChanged.connect(self._on_position_changed)
        
        grid.addWidget(x_label, 3, 0)
        grid.addWidget(self.x_input, 3, 1)
        grid.addWidget(self.footer_x_input, 3, 2)
        
        # Y位置
        y_label = QLabel(self.parent._("Y Position:"))
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
        self.y_input.valueChanged.connect(self._on_position_changed)
        
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
        self.footer_y_input.valueChanged.connect(self._on_position_changed)
        
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
        align_label = QLabel(self.parent._("Alignment:"))
        align_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        align_label.setAlignment(Qt.AlignRight)
        
        # 页眉对齐按钮
        header_align_layout = QHBoxLayout()
        header_align_layout.setSpacing(8)
        
        self.left_btn = QPushButton(self.parent._("Left"))
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
        self.left_btn.clicked.connect(lambda: self._on_alignment_changed("left"))
        
        self.center_btn = QPushButton(self.parent._("Center"))
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
        self.center_btn.clicked.connect(lambda: self._on_alignment_changed("center"))
        
        self.right_btn = QPushButton(self.parent._("Right"))
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
        self.right_btn.clicked.connect(lambda: self._on_alignment_changed("right"))
        
        header_align_layout.addWidget(self.left_btn)
        header_align_layout.addWidget(self.center_btn)
        header_align_layout.addWidget(self.right_btn)
        
        # 页脚对齐按钮
        footer_align_layout = QHBoxLayout()
        footer_align_layout.setSpacing(8)
        
        self.footer_left_btn = QPushButton(self.parent._("Left"))
        self.footer_left_btn.setMinimumHeight(30)
        self.footer_left_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.footer_left_btn.clicked.connect(lambda: self._on_alignment_changed("footer_left"))
        
        self.footer_center_btn = QPushButton(self.parent._("Center"))
        self.footer_center_btn.setMinimumHeight(30)
        self.footer_center_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.footer_center_btn.clicked.connect(lambda: self._on_alignment_changed("footer_center"))
        
        self.footer_right_btn = QPushButton(self.parent._("Right"))
        self.footer_right_btn.setMinimumHeight(30)
        self.footer_right_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.footer_right_btn.clicked.connect(lambda: self._on_alignment_changed("footer_right"))
        
        footer_align_layout.addWidget(self.footer_left_btn)
        footer_align_layout.addWidget(self.footer_center_btn)
        footer_align_layout.addWidget(self.footer_right_btn)
        
        grid.addWidget(align_label, 5, 0)
        grid.addLayout(header_align_layout, 5, 1)
        grid.addLayout(footer_align_layout, 5, 2)
        
        # 全局页脚文本
        global_footer_label = QLabel(self.parent._("Global Footer Text:"))
        global_footer_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        global_footer_label.setAlignment(Qt.AlignRight)
        
        self.global_footer_input = QLineEdit()
        self.global_footer_input.setPlaceholderText(self.parent._("Use {page} for current page, {total} for total pages."))
        self.global_footer_input.setMinimumHeight(30)
        self.global_footer_input.setStyleSheet("""
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
        self.global_footer_input.textChanged.connect(self._on_settings_changed)
        
        grid.addWidget(global_footer_label, 6, 0)
        grid.addWidget(self.global_footer_input, 6, 1, 1, 2)
        
        # 单位选择
        unit_label = QLabel(self.parent._("单位:"))
        unit_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        unit_label.setAlignment(Qt.AlignRight)
        
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["pt", "mm", "cm", "inch"])
        self.unit_combo.setCurrentText("pt")
        self.unit_combo.setMinimumHeight(30)
        self.unit_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 80px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
        """)
        self.unit_combo.currentTextChanged.connect(self._on_settings_changed)
        
        grid.addWidget(unit_label, 7, 0)
        grid.addWidget(self.unit_combo, 7, 1)
        
        group.setLayout(grid)
        return group
        
    def _create_warning_label(self) -> QLabel:
        """创建警告标签"""
        warning = QLabel("⚠️")
        warning.setToolTip(self.parent._("This position is too close to the edge..."))
        warning.setStyleSheet("color: #e74c3c; font-size: 16px;")
        return warning
        
    def _on_font_changed(self):
        """字体改变时的处理"""
        if self.font_select and self.footer_font_select:
            self.font_changed.emit(self.font_select.currentText())
            self._on_settings_changed()
            
    def _on_size_changed(self):
        """字体大小改变时的处理"""
        if self.font_size_spin and self.footer_font_size_spin:
            self.size_changed.emit(self.font_size_spin.value())
            self._on_settings_changed()
            
    def _on_position_changed(self):
        """位置改变时的处理"""
        if self.x_input and self.y_input:
            self.position_changed.emit(self.x_input.value(), self.y_input.value())
            self._on_settings_changed()
            
    def _on_alignment_changed(self, alignment: str):
        """对齐方式改变时的处理"""
        self.alignment_changed.emit(alignment)
        self._on_settings_changed()
        
    def _on_settings_changed(self):
        """设置改变时的处理"""
        settings = self.get_current_settings()
        self.settings_changed.emit(settings)
        
    def get_current_settings(self) -> dict:
        """获取当前设置"""
        if not all([self.font_select, self.font_size_spin, self.x_input, self.y_input, 
                   self.footer_font_select, self.footer_font_size_spin, self.footer_x_input, 
                   self.footer_y_input, self.global_footer_input, self.unit_combo]):
            return {}
            
        return {
            'header_font': self.font_select.currentText(),
            'header_font_size': self.font_size_spin.value(),
            'header_x': self.x_input.value(),
            'header_y': self.y_input.value(),
            'footer_font': self.footer_font_select.currentText(),
            'footer_font_size': self.footer_font_size_spin.value(),
            'footer_x': self.footer_x_input.value(),
            'footer_y': self.footer_y_input.value(),
            'global_footer_text': self.global_footer_input.text(),
            'unit': self.unit_combo.currentText()
        }
        
    def apply_settings(self, settings: dict):
        """应用设置"""
        if not settings:
            return
            
        if 'header_font' in settings and self.font_select:
            self.font_select.setCurrentText(settings['header_font'])
        if 'header_font_size' in settings and self.font_size_spin:
            self.font_size_spin.setValue(settings['header_font_size'])
        if 'header_x' in settings and self.x_input:
            self.x_input.setValue(settings['header_x'])
        if 'header_y' in settings and self.y_input:
            self.y_input.setValue(settings['header_y'])
        if 'footer_font' in settings and self.footer_font_select:
            self.footer_font_select.setCurrentText(settings['footer_font'])
        if 'footer_font_size' in settings and self.footer_font_size_spin:
            self.footer_font_size_spin.setValue(settings['footer_font_size'])
        if 'footer_x' in settings and self.footer_x_input:
            self.footer_x_input.setValue(settings['footer_x'])
        if 'footer_y' in settings and self.footer_y_input:
            self.footer_y_input.setValue(settings['footer_y'])
        if 'global_footer_text' in settings and self.global_footer_input:
            self.global_footer_input.setText(settings['global_footer_text'])
        if 'unit' in settings and self.unit_combo:
            self.unit_combo.setCurrentText(settings['unit'])
