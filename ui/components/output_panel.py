# output_panel.py - 输出控制组件
"""
输出控制组件模块
从ui_main.py中提取的输出相关UI创建逻辑
"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton, QCheckBox, QFileDialog
)
from PySide6.QtCore import Qt
import os
import sys
import subprocess
import platform


class OutputPanel:
    """输出面板管理器"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self._ = main_window._
        # 获取默认输出文件夹
        import os
        self.output_folder = os.path.expanduser("~/Downloads")
        
    def create_output_layout(self) -> QVBoxLayout:
        """创建输出控制布局"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 创建合并的输出控制组
        output_group = self._create_combined_output_group()
        
        layout.addWidget(output_group)
        
        return layout
        
    def _create_combined_output_group(self) -> QGroupBox:
        """创建合并的输出控制组"""
        group = QGroupBox(self._("Output & Processing"))
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        # 主布局：水平排列
        main_layout = QHBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 左侧：处理选项（上下排列）
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)
        
        # 合并选项
        self.main_window.merge_checkbox = QCheckBox("📄 " + self._("Merge after processing"))
        self.main_window.merge_checkbox.setChecked(False)
        self.main_window.merge_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #2c3e50;
                font-size: 12px;
                padding: 8px;
                background-color: #f8f9fa;
                border-radius: 6px;
            }
        """)
        
        self.main_window.page_numbers_checkbox = QCheckBox("🔢 " + self._("Add page numbers after merge"))
        self.main_window.page_numbers_checkbox.setChecked(False)
        self.main_window.page_numbers_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #2c3e50;
                font-size: 12px;
                padding: 8px;
                background-color: #f8f9fa;
                border-radius: 6px;
            }
        """)
        
        left_panel.addWidget(self.main_window.merge_checkbox)
        left_panel.addWidget(self.main_window.page_numbers_checkbox)
        left_panel.addStretch()  # 添加弹性空间
        
        # 中间：输出文件夹选择（宽度为1/3）
        middle_panel = QVBoxLayout()
        middle_panel.setSpacing(8)
        
        folder_label = QLabel("📁 " + self._("Output Folder:"))
        folder_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #2c3e50;
                font-size: 12px;
            }
        """)
        
        # 选择按钮
        self.main_window.select_output_button = QPushButton("📂 " + self._("Select"))
        self.main_window.select_output_button.setMinimumHeight(30)
        self.main_window.select_output_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 12px;
            }
        """)
        self.main_window.select_output_button.clicked.connect(self._select_output_folder)
        
        # 路径显示按钮（宽度限制为1/3）
        self.main_window.output_path_button = QPushButton(self.main_window.output_folder)
        self.main_window.output_path_button.setStyleSheet("""
            QPushButton {
                background-color: #e9ecef;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 6px 10px;
                color: #6c757d;
                text-align: left;
                font-size: 11px;
            }
        """)
        self.main_window.output_path_button.clicked.connect(self._open_output_folder)
        
        middle_panel.addWidget(folder_label)
        middle_panel.addWidget(self.main_window.select_output_button)
        middle_panel.addWidget(self.main_window.output_path_button)
        
        # 右侧：开始处理按钮
        right_panel = QVBoxLayout()
        right_panel.addStretch()  # 顶部弹性空间
        
        self.main_window.start_button = QPushButton("▶️ " + self._("Start Processing"))
        self.main_window.start_button.setMinimumHeight(50)
        self.main_window.start_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
            }
        """)
        self.main_window.start_button.clicked.connect(self._start_processing)
        
        right_panel.addWidget(self.main_window.start_button)
        right_panel.addStretch()  # 底部弹性空间
        
        # 组装布局
        main_layout.addLayout(left_panel, 1)      # 左侧：处理选项
        main_layout.addLayout(middle_panel, 1)    # 中间：输出文件夹（1/3宽度）
        main_layout.addLayout(right_panel, 2)     # 右侧：开始处理按钮（2/3宽度）
        
        group.setLayout(main_layout)
        return group
        
    def _open_output_folder(self):
        """打开输出文件夹"""
        try:
            if os.path.exists(self.main_window.output_folder):
                if sys.platform == "win32":
                    os.startfile(self.main_window.output_folder)
                elif sys.platform == "darwin":
                    subprocess.run(["open", self.main_window.output_folder])
                else:
                    subprocess.run(["xdg-open", self.main_window.output_folder])
            else:
                self.main_window.show_error(self._("Output folder does not exist"), 
                                         f"Path: {self.main_window.output_folder}")
        except Exception as e:
            self.main_window.show_error(self._("Failed to open output folder"), e)
    
    def _select_output_folder(self):
        """选择输出文件夹"""
        try:
            folder = QFileDialog.getExistingDirectory(
                self.main_window,
                self._("Select Output Folder"),
                self.main_window.output_folder or os.path.expanduser("~/Downloads")
            )
            if folder:
                self.main_window.output_folder = folder
                self.main_window.output_path_button.setText(folder)
                # 保存设置
                from config import save_settings
                save_settings({"output_folder": folder})
        except Exception as e:
            self.main_window.show_error(self._("Failed to select output folder"), e)
    
    def _start_processing(self):
        """开始处理"""
        try:
            # 调用主窗口的处理方法
            self.main_window.start_processing()
        except Exception as e:
            self.main_window.show_error(self._("Failed to start processing"), e)
