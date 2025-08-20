# file_table.py - 文件表格组件
"""
文件表格组件模块
从ui_main.py中提取的文件列表相关UI创建逻辑
"""

from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QGroupBox, QTableWidget, QHeaderView, 
    QPushButton, QAbstractItemView, QLabel, QProgressBar
)
from PySide6.QtCore import Qt


class FileTableManager:
    """文件表格管理器"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self._ = main_window._
        
    def create_table_area(self) -> QHBoxLayout:
        """创建文件列表及右侧的控制按钮"""
        layout = QHBoxLayout()
        layout.setSpacing(10)  # 减少间距
        layout.setContentsMargins(10, 10, 10, 10)  # 减少边距
        
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
        table_group_layout.setContentsMargins(10, 10, 10, 10)  # 减少边距
        
        # 创建文件表格
        self.main_window.file_table = QTableWidget()
        self.main_window.file_table.setColumnCount(8)
        
        # 设置表头
        self.main_window.file_table.setHorizontalHeaderLabels([
            self._("No."), 
            self._("Flags"),
            self._("Mode"),
            self._("Filename"), 
            self._("Size (MB)"), 
            self._("Page Count"), 
            self._("Header Text"), 
            self._("Footer Text")
        ])
        
        # 设置表格属性
        self.main_window.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.main_window.file_table.setAlternatingRowColors(True)
        self.main_window.file_table.setSortingEnabled(True)
        self.main_window.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # 连接排序事件
        self.main_window.file_table.horizontalHeader().sectionClicked.connect(self.main_window._on_header_clicked)
        
        # 设置列宽
        header = self.main_window.file_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 序号列
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Flags
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Mode
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # 文件名（拉伸填充）
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 大小
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 页数
        header.setSectionResizeMode(6, QHeaderView.Interactive)  # 页眉
        header.setSectionResizeMode(7, QHeaderView.Interactive)  # 页脚
        
        # 设置最小列宽，确保内容可见
        header.setMinimumSectionSize(80)
        
        # 初始列宽设置
        self.main_window.file_table.setColumnWidth(3, 250)  # 文件名列宽
        self.main_window.file_table.setColumnWidth(6, 150)  # 页眉列宽
        self.main_window.file_table.setColumnWidth(7, 150)  # 页脚列宽
        
        # 确保表头可见并可点击
        header.setVisible(True)
        header.setStretchLastSection(True)
        header.setSectionsClickable(True)
        
        # 允许用户调整列宽
        header.setSectionsMovable(False)  # 禁止移动列
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # 表格样式
        self.main_window.file_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                gridline-color: #e9ecef;
                selection-background-color: #e3f2fd;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e9ecef;
                min-height: 30px;  /* 确保行高足够 */
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                border: none;
                border-bottom: 2px solid #dee2e6;
                padding: 8px;
                color: #2c3e50;
                font-weight: bold;
                min-height: 30px;  /* 确保表头高度足够 */
            }
            QHeaderView::section:hover {
                background-color: #e9ecef;
                cursor: pointer;  /* 显示为手型光标，提示可点击 */
            }
            QComboBox {
                min-height: 25px;
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: white;
                color: black;
            }
            QComboBox::drop-down {
                width: 20px;
                border-left: 1px solid #ccc;
            }
            QLineEdit {
                min-height: 25px;
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: white;
                color: black;
            }
        """)
        
        # 在表格上方添加状态显示区域
        status_layout = QHBoxLayout()
        status_layout.setSpacing(10)
        status_layout.setContentsMargins(0, 5, 0, 5)
        
        # 左侧：处理状态标签
        self.main_window.progress_label = QLabel("")
        self.main_window.progress_label.setAlignment(Qt.AlignLeft)
        self.main_window.progress_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-weight: bold;
                font-size: 12px;
                padding: 8px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                min-width: 200px;
            }
        """)
        
        # 中间：弹性空间
        status_layout.addWidget(self.main_window.progress_label)
        status_layout.addStretch()
        
        # 右侧：进度条
        self.main_window.progress_bar = QProgressBar()
        self.main_window.progress_bar.setVisible(False)
        self.main_window.progress_bar.setMinimumWidth(200)
        self.main_window.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 4px;
            }
        """)
        
        status_layout.addWidget(self.main_window.progress_bar)
        
        # 将状态显示添加到表格组布局
        table_group_layout.addLayout(status_layout)
        table_group_layout.addWidget(self.main_window.file_table)
        
        table_group.setLayout(table_group_layout)
        
        # 创建右侧控制按钮组
        control_group = self._create_control_buttons()
        
        # 布局组装
        layout.addWidget(table_group, 4)  # 表格占大部分空间
        layout.addWidget(control_group, 1)  # 控制按钮占小部分空间
        
        return layout
        
    def _create_control_buttons(self) -> QGroupBox:
        """创建右侧控制按钮组"""
        control_group = QGroupBox("🎛️ " + self._("File Operations"))
        control_group.setStyleSheet("""
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
        
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(15, 15, 15, 15)
        
        # 移动按钮
        self.main_window.move_up_button = QPushButton("⬆️ " + self._("Move Up"))
        self.main_window.move_up_button.setMinimumHeight(35)
        self.main_window.move_up_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        self.main_window.move_down_button = QPushButton("⬇️ " + self._("Move Down"))
        self.main_window.move_down_button.setMinimumHeight(35)
        self.main_window.move_down_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        # 删除按钮
        self.main_window.remove_button = QPushButton("🗑️ " + self._("Remove"))
        self.main_window.remove_button.setMinimumHeight(35)
        self.main_window.remove_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #c62828;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        # 解锁按钮
        self.main_window.unlock_button = QPushButton("🔓 " + self._("移除文件限制..."))
        self.main_window.unlock_button.setMinimumHeight(35)
        self.main_window.unlock_button.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:pressed {
                background-color: #6A1B9A;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        
        # 布局组装
        button_layout.addWidget(self.main_window.move_up_button)
        button_layout.addWidget(self.main_window.move_down_button)
        button_layout.addWidget(self.main_window.remove_button)
        button_layout.addWidget(self.main_window.unlock_button)
        button_layout.addStretch()
        
        control_group.setLayout(button_layout)
        return control_group
