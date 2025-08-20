"""
Toolbar Manager Module
管理顶部工具栏的创建和信号处理
"""

from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QLabel, QComboBox, QGroupBox,
    QVBoxLayout, QLineEdit, QSpinBox, QHBoxLayout
)
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFont


class ToolbarManager(QObject):
    """顶部工具栏管理器"""
    
    # 信号定义
    import_requested = Signal()
    clear_requested = Signal()
    unlock_requested = Signal()
    mode_changed = Signal(str)
    auto_number_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self._setup_ui_elements()
        
    def _setup_ui_elements(self):
        """初始化UI元素引用"""
        self.import_button = None
        self.clear_button = None
        self.unlock_button = None
        self.mode_select_combo = None
        self.prefix_input = None
        self.start_number_input = None
        self.step_input = None
        self.digits_input = None
        self.suffix_input = None
        
    def create_top_bar(self) -> QHBoxLayout:
        """创建顶部包含导入、清空和模式选择的工具栏"""
        layout = QHBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # 创建标题标签
        title_label = QLabel("📄 " + self.parent._("DocDeck - PDF Header & Footer Tool"))
        title_label.setObjectName("title_label")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # 导入按钮组
        import_group = QHBoxLayout()
        import_group.setSpacing(10)
        
        self.import_button = QPushButton("📁 " + self.parent._("Import Files or Folders"))
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
        self.import_button.clicked.connect(self.import_requested.emit)
        
        self.clear_button = QPushButton("🗑️ " + self.parent._("Clear List"))
        self.clear_button.setMinimumHeight(35)
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                font-size: 13px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.clear_button.clicked.connect(self.clear_requested.emit)
        
        import_group.addWidget(self.import_button)
        import_group.addWidget(self.clear_button)
        
        # 实体解锁按钮（批量解锁所选文件）
        self.unlock_button = QPushButton("🔓 " + self.parent._("移除文件限制..."))
        self.unlock_button.setMinimumHeight(35)
        self.unlock_button.setStyleSheet("""
            QPushButton {
                background-color: #8e44ad;
                color: white;
                font-size: 13px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #7d3c98;
            }
        """)
        self.unlock_button.clicked.connect(self.unlock_requested.emit)
        import_group.addWidget(self.unlock_button)
        layout.addLayout(import_group)
        
        layout.addStretch()
        
        # 模式选择组
        mode_group = QHBoxLayout()
        mode_group.setSpacing(10)
        
        mode_label = QLabel(self.parent._("Header Mode:"))
        mode_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        
        self.mode_select_combo = QComboBox()
        self.mode_select_combo.addItems([
            self.parent._("Filename Mode"), 
            self.parent._("Auto Number Mode"), 
            self.parent._("Custom Mode")
        ])
        self.mode_select_combo.setMinimumHeight(35)
        self.mode_select_combo.setStyleSheet("""
            QComboBox {
                font-size: 13px;
                padding: 8px 15px;
                min-width: 150px;
            }
        """)
        self.mode_select_combo.currentTextChanged.connect(self._on_mode_changed)
        
        mode_group.addWidget(mode_label)
        mode_group.addWidget(self.mode_select_combo)
        layout.addLayout(mode_group)
        
        return layout
        
    def create_auto_number_group(self) -> QGroupBox:
        """创建自动编号设置的控件组"""
        group = QGroupBox("🔢 " + self.parent._("Auto Number Settings"))
        group.setStyleSheet("""
            QGroupBox {
                background-color: #ecf0f1;
                border: 2px solid #bdc3c7;
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 第一行：前缀、起始编号、步长
        row1 = QHBoxLayout()
        
        # 前缀
        prefix_layout = QVBoxLayout()
        prefix_label = QLabel(self.parent._("Prefix:"))
        prefix_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.prefix_input = QLineEdit("Doc-")
        self.prefix_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        self.prefix_input.textChanged.connect(self._on_auto_number_changed)
        prefix_layout.addWidget(prefix_label)
        prefix_layout.addWidget(self.prefix_input)
        row1.addLayout(prefix_layout)
        
        # 起始编号
        start_layout = QVBoxLayout()
        start_label = QLabel(self.parent._("Start #:"))
        start_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.start_number_input = QSpinBox()
        self.start_number_input.setRange(1, 9999)
        self.start_number_input.setValue(1)
        self.start_number_input.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        self.start_number_input.valueChanged.connect(self._on_auto_number_changed)
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_number_input)
        row1.addLayout(start_layout)
        
        # 步长
        step_layout = QVBoxLayout()
        step_label = QLabel(self.parent._("Step:"))
        step_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.step_input = QSpinBox()
        self.step_input.setRange(1, 100)
        self.step_input.setValue(1)
        self.step_input.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        self.step_input.valueChanged.connect(self._on_auto_number_changed)
        step_layout.addWidget(step_label)
        step_layout.addWidget(self.step_input)
        row1.addLayout(step_layout)
        
        layout.addLayout(row1)
        
        # 第二行：位数、后缀
        row2 = QHBoxLayout()
        
        # 位数
        digits_layout = QVBoxLayout()
        digits_label = QLabel(self.parent._("Digits:"))
        digits_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.digits_input = QSpinBox()
        self.digits_input.setRange(1, 6)
        self.digits_input.setValue(3)
        self.digits_input.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        self.digits_input.valueChanged.connect(self._on_auto_number_changed)
        digits_layout.addWidget(digits_label)
        digits_layout.addWidget(self.digits_input)
        row2.addLayout(digits_layout)
        
        # 后缀
        suffix_layout = QVBoxLayout()
        suffix_label = QLabel(self.parent._("Suffix:"))
        suffix_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.suffix_input = QLineEdit("")
        self.suffix_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        self.suffix_input.textChanged.connect(self._on_auto_number_changed)
        suffix_layout.addWidget(suffix_label)
        suffix_layout.addWidget(self.suffix_input)
        row2.addLayout(suffix_layout)
        
        layout.addLayout(row2)
        group.setLayout(layout)
        
        return group
        
    def _on_mode_changed(self, mode: str):
        """模式改变时的处理"""
        self.mode_changed.emit(mode)
        
    def _on_auto_number_changed(self):
        """自动编号设置改变时的处理"""
        if self.prefix_input and self.start_number_input and self.step_input and self.digits_input and self.suffix_input:
            settings = {
                'prefix': self.prefix_input.text(),
                'start_number': self.start_number_input.value(),
                'step': self.step_input.value(),
                'digits': self.digits_input.value(),
                'suffix': self.suffix_input.text()
            }
            self.auto_number_changed.emit(settings)
            
    def get_current_mode(self) -> str:
        """获取当前选择的模式"""
        return self.mode_select_combo.currentText() if self.mode_select_combo else ""
        
    def get_auto_number_settings(self) -> dict:
        """获取自动编号设置"""
        if not all([self.prefix_input, self.start_number_input, self.step_input, self.digits_input, self.suffix_input]):
            return {}
            
        return {
            'prefix': self.prefix_input.text(),
            'start_number': self.start_number_input.value(),
            'step': self.step_input.value(),
            'digits': self.digits_input.value(),
            'suffix': self.suffix_input.text()
        }
        
    def set_auto_number_settings(self, settings: dict):
        """设置自动编号参数"""
        if self.prefix_input and 'prefix' in settings:
            self.prefix_input.setText(settings['prefix'])
        if self.start_number_input and 'start_number' in settings:
            self.start_number_input.setValue(settings['start_number'])
        if self.step_input and 'step' in settings:
            self.step_input.setValue(settings['step'])
        if self.digits_input and 'digits' in settings:
            self.digits_input.setValue(settings['digits'])
        if self.suffix_input and 'suffix' in settings:
            self.suffix_input.setText(settings['suffix'])
