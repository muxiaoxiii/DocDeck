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
from PySide6.QtGui import QPainter, QPen, QFont, QPixmap, QImage, QBrush, QColor
try:
	import fitz  # PyMuPDF
except ImportError:
	fitz = None

from controller import ProcessingController, Worker
from font_manager import get_system_fonts
from pdf_handler import merge_pdfs, add_page_numbers
from position_utils import suggest_safe_header_y, is_out_of_print_safe_area
from merge_dialog import MergeDialog
from logger import logger

import locale
import gettext

def _detect_system_language():
    """检测系统语言"""
    try:
        # 获取系统语言
        system_locale = locale.getdefaultlocale()[0]
        if system_locale:
            if system_locale.startswith('zh'):
                return 'zh_CN'
            elif system_locale.startswith('en'):
                return 'en_US'
        # 强制使用中文界面
        return 'zh_CN'
    except:
        return 'zh_CN'

def _setup_language():
    """设置界面语言"""
    lang = _detect_system_language()
    
    if lang == 'zh_CN':
        # 中文界面
        return {
            "Import Files or Folders": "导入文件或文件夹",
            "Clear List": "清空列表",
            "Header Mode:": "页眉模式:",
            "Filename Mode": "文件名模式",
            "Auto Number Mode": "自动编号模式",
            "Custom Mode": "自定义模式",
            "Auto Number Settings": "自动编号设置",
            "Prefix:": "前缀:",
            "Start #:": "起始编号:",
            "Step:": "步长:",
            "Digits:": "位数:",
            "Suffix:": "后缀:",
            "Header & Footer Settings": "页眉页脚设置",
            "Settings": "设置",
            "Header": "页眉",
            "Footer": "页脚",
            "Font:": "字体:",
            "Size:": "大小:",
            "X Position:": "X 位置:",
            "Y Position:": "Y 位置:",
            "Alignment:": "对齐:",
            "Left": "左对齐",
            "Center": "居中",
            "Right": "右对齐",
            "Global Footer Text:": "全局页脚文本:",
            "Use {page} for current page, {total} for total pages.": "使用 {page} 表示当前页，{total} 表示总页数。",
            "Apply to All": "应用到全部",
            "Header/Footer Preview": "页眉/页脚预览",
            "Page: ": "页码: ",
            "Structured mode (Acrobat-friendly)": "结构化模式 (Acrobat友好)",
            "Structured CN: use fixed font": "结构化中文：使用固定字体",
            "Memory optimization (for large files)": "内存优化 (适用于大文件)",
            "Enable chunked processing and memory cleanup for large PDF files": "启用分块处理和内存清理，适用于大PDF文件",
            "Move Up": "上移",
            "Move Down": "下移",
            "Remove": "删除",
            "Output Folder:": "输出文件夹:",
            "Select Output Folder": "选择输出文件夹",
            "Start Processing": "开始处理",
            "Merge after processing": "处理后合并",
            "Add page numbers after merge": "合并后添加页码",
            "Normalize to A4 (auto)": "自动规范化到A4",
            "单位:": "单位:",
            "预设位置:": "预设位置:",
            "右上角": "右上角",
            "右下角": "右下角",
            "No.": "序号",
            "Filename": "文件名",
            "Size (MB)": "大小 (MB)",
            "Page Count": "页数",
            "Header Text": "页眉文本",
            "Footer Text": "页脚文本",
            "读取现有页眉/页脚": "读取现有页眉/页脚",
            "删除": "删除",
            "Header Template:": "页眉模板:",
            "Custom": "自定义",
            "Company Name": "公司名称",
            "Document Title": "文档标题",
            "Date": "日期",
            "Page Number": "页码",
            "Confidential": "机密文件",
            "Draft": "草稿",
            "Final Version": "最终版",
            "Help": "帮助",
            "About DocDeck": "关于 DocDeck",
            "DocDeck - PDF Header & Footer Tool": "DocDeck - PDF 页眉页脚工具",
            "Author: 木小樨": "作者: 木小樨",
            "Project Homepage:": "项目主页:",
            "移除文件限制...": "移除文件限制...",
            "Output Folder Not Set": "未设置输出文件夹",
            "Please select an output folder...": "请选择输出文件夹...",
            "Locked File": "加密文件",
            "This file is encrypted and cannot be opened without a password.": "此文件已加密，需要密码才能打开。",
            "Decrypt PDF": "解密PDF",
            "Please enter the password:": "请输入密码:",
            "Restricted PDF": "受限PDF",
            "This PDF is restricted and cannot be modified.\nDo you want to attempt automatic unlocking?": "此PDF受限，无法修改。\n是否尝试自动解锁？",
            "Unlock Success": "解锁成功",
            "Unlocked file saved to: ": "解锁文件已保存到: ",
            "Unlock Failed": "解锁失败",
            "Password incorrect. Would you like to attempt forced unlock without password?": "密码错误。是否尝试无密码强制解锁？",
            "Retry Password": "重试密码",
            "Incorrect password. Try again:": "密码错误，请重试:",
            "Select PDF Files or Folders": "选择PDF文件或文件夹",
            "Select Output Directory": "选择输出目录",
            "No Files": "没有文件",
            "Please import PDF files first.": "请先导入PDF文件。",
            "No Output Folder": "未选择输出文件夹",
            "Please select an output folder.": "请选择输出文件夹。",
            "Processing... (0%)": "处理中... (0%)",
            "The following files are encrypted or restricted:": "以下文件已加密或受限:",
            "Please unlock them using the right-click menu before processing.": "处理前请使用右键菜单解锁。",
            "Encrypted Files Detected": "检测到加密文件",
            "Completed {} files": "已完成 {} 个文件",
            "Some Files Failed": "部分文件处理失败",
            "Done": "完成",
            "All files processed successfully.": "所有文件处理成功。",
            "Save Merged PDF": "保存合并的PDF",
            "Files merged successfully and saved to:\n": "文件合并成功并保存到:\n",
            "Files merged and page numbers added successfully:\n": "文件合并并添加页码成功:\n",
            "Success": "成功",
            "Operation Failed": "操作失败",
            "Invalid Files": "无效文件",
            "Only PDF files can be imported.": "只能导入PDF文件。",
            "The following files are fully encrypted and require a password:\n": "以下文件完全加密，需要密码:\n",
            "The following files are restricted (e.g., can't be modified):\n": "以下文件受限（例如，无法修改）:\n",
            "Encrypted Files Notice": "加密文件通知",
            "Failed to import files": "导入文件失败",
            "No preview": "无预览",
            "Preview failed": "预览失败",
            "Failed to apply settings due to an error. Please check the logs.": "应用设置失败，请检查日志。",
            "Error": "错误",
            "Processing... ": "处理中... ",
            "This position is too close to the edge...": "此位置太靠近边缘...",
            "读取现有页眉/页脚失败": "读取现有页眉/页脚失败",
            "确定要删除文件": "确定要删除文件",
            "吗？": "吗？"
        }
    else:
        # 英文界面
        return {
            "Import Files or Folders": "Import Files or Folders",
            "Clear List": "Clear List",
            "Header Mode:": "Header Mode:",
            "Filename Mode": "Filename Mode",
            "Auto Number Mode": "Auto Number Mode",
            "Custom Mode": "Custom Mode",
            "Auto Number Settings": "Auto Number Settings",
            "Prefix:": "Prefix:",
            "Start #:": "Start #:",
            "Step:": "Step:",
            "Digits:": "Digits:",
            "Suffix:": "Suffix:",
            "Header & Footer Settings": "Header & Footer Settings",
            "Settings": "Settings",
            "Header": "Header",
            "Footer": "Footer",
            "Font:": "Font:",
            "Size:": "Size:",
            "X Position:": "X Position:",
            "Y Position:": "Y Position:",
            "Alignment:": "Alignment:",
            "Left": "Left",
            "Center": "Center",
            "Right": "Right",
            "Global Footer Text:": "Global Footer Text:",
            "Use {page} for current page, {total} for total pages.": "Use {page} for current page, {total} for total pages.",
            "Apply to All": "Apply to All",
            "Header/Footer Preview": "Header/Footer Preview",
            "Page: ": "Page: ",
            "Structured mode (Acrobat-friendly)": "Structured mode (Acrobat-friendly)",
            "Structured CN: use fixed font": "Structured CN: use fixed font",
            "Memory optimization (for large files)": "Memory optimization (for large files)",
            "Enable chunked processing and memory cleanup for large PDF files": "Enable chunked processing and memory cleanup for large PDF files",
            "Move Up": "Move Up",
            "Move Down": "Move Down",
            "Remove": "Remove",
            "Output Folder:": "Output Folder:",
            "Select Output Folder": "Select Output Folder",
            "Start Processing": "Start Processing",
            "Merge after processing": "Merge after processing",
            "Add page numbers after merge": "Add page numbers after merge",
            "Normalize to A4 (auto)": "Normalize to A4 (auto)",
            "单位:": "Unit:",
            "预设位置:": "Preset Position:",
            "右上角": "Top Right",
            "右下角": "Bottom Right",
            "No.": "No.",
            "Filename": "Filename",
            "Size (MB)": "Size (MB)",
            "Page Count": "Page Count",
            "Header Text": "Header Text",
            "Footer Text": "Footer Text",
            "读取现有页眉/页脚": "Read Existing Headers/Footers",
            "删除": "Delete",
            "Header Template:": "Header Template:",
            "Custom": "Custom",
            "Company Name": "Company Name",
            "Document Title": "Document Title",
            "Date": "Date",
            "Page Number": "Page Number",
            "Confidential": "Confidential",
            "Draft": "Draft",
            "Final Version": "Final Version",
            "Help": "Help",
            "About DocDeck": "About DocDeck",
            "DocDeck - PDF Header & Footer Tool": "DocDeck - PDF Header & Footer Tool",
            "Author: 木小樨": "Author: 木小樨",
            "Project Homepage:": "Project Homepage:",
            "移除文件限制...": "Remove File Restrictions...",
            "Output Folder Not Set": "Output Folder Not Set",
            "Please select an output folder...": "Please select an output folder...",
            "Locked File": "Locked File",
            "This file is encrypted and cannot be opened without a password.": "This file is encrypted and cannot be opened without a password.",
            "Decrypt PDF": "Decrypt PDF",
            "Please enter the password:": "Please enter the password:",
            "Restricted PDF": "Restricted PDF",
            "This PDF is restricted and cannot be modified.\nDo you want to attempt automatic unlocking?": "This PDF is restricted and cannot be modified.\nDo you want to attempt automatic unlocking?",
            "Unlock Success": "Unlock Success",
            "Unlocked file saved to: ": "Unlocked file saved to: ",
            "Unlock Failed": "Unlock Failed",
            "Password incorrect. Would you like to attempt forced unlock without password?": "Password incorrect. Would you like to attempt forced unlock without password?",
            "Retry Password": "Retry Password",
            "Incorrect password. Try again:": "Incorrect password. Try again:",
            "Select PDF Files or Folders": "Select PDF Files or Folders",
            "Select Output Directory": "Select Output Directory",
            "No Files": "No Files",
            "Please import PDF files first.": "Please import PDF files first.",
            "No Output Folder": "No Output Folder",
            "Please select an output folder.": "Please select an output folder.",
            "Processing... (0%)": "Processing... (0%)",
            "The following files are encrypted or restricted:": "The following files are encrypted or restricted:",
            "Please unlock them using the right-click menu before processing.": "Please unlock them using the right-click menu before processing.",
            "Encrypted Files Detected": "Encrypted Files Detected",
            "Completed {} files": "Completed {} files",
            "Some Files Failed": "Some Files Failed",
            "Done": "Done",
            "All files processed successfully.": "All files processed successfully.",
            "Save Merged PDF": "Save Merged PDF",
            "Files merged successfully and saved to:\n": "Files merged successfully and saved to:\n",
            "Files merged and page numbers added successfully:\n": "Files merged and page numbers added successfully:\n",
            "Success": "Success",
            "Operation Failed": "Operation Failed",
            "Invalid Files": "Invalid Files",
            "Only PDF files can be imported.": "Only PDF files can be imported.",
            "The following files are fully encrypted and require a password:\n": "The following files are fully encrypted and require a password:\n",
            "The following files are restricted (e.g., can't be modified):\n": "The following files are restricted (e.g., can't be modified):\n",
            "Encrypted Files Notice": "Encrypted Files Notice",
            "Failed to import files": "Failed to import files",
            "No preview": "No preview",
            "Preview failed": "Preview failed",
            "Failed to apply settings due to an error. Please check the logs.": "Failed to apply settings due to an error. Please check the logs.",
            "Error": "Error",
            "Processing... ": "Processing... ",
            "This position is too close to the edge...": "This position is too close to the edge...",
            "读取现有页眉/页脚失败": "Failed to read existing headers/footers",
            "确定要删除文件": "Are you sure you want to delete the file",
            "吗？": "?"
        }

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
        
        # 设置语言
        self.language_map = _setup_language()
        
        # 定义本地化方法
        def _(text: str) -> str:
            """获取本地化文本"""
            return self.language_map.get(text, text)
        self._ = _

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
        table_layout = self._create_table_area()
        output_layout = self._create_output_layout()

        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.auto_number_group)
        main_layout.addWidget(settings_group)
        
        # 单位选择和预设按钮布局
        unit_preset_layout = QHBoxLayout()
        
        # 单位选择
        unit_layout = QHBoxLayout()
        unit_layout.addWidget(QLabel(self._("单位:")))
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["pt", "cm", "mm"])
        self.unit_combo.setCurrentText("pt")
        self.unit_combo.currentTextChanged.connect(self._on_unit_changed)
        unit_layout.addWidget(self.unit_combo)
        unit_preset_layout.addLayout(unit_layout)
        
        # 预设按钮
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel(self._("预设位置:")))
        self.top_right_btn = QPushButton(self._("右上角"))
        self.top_right_btn.clicked.connect(self._apply_top_right_preset)
        preset_layout.addWidget(self.top_right_btn)
        self.bottom_right_btn = QPushButton(self._("右下角"))
        self.bottom_right_btn.clicked.connect(self._apply_bottom_right_preset)
        preset_layout.addWidget(self.bottom_right_btn)
        unit_preset_layout.addLayout(preset_layout)
        
        unit_preset_layout.addStretch()
        main_layout.addLayout(unit_preset_layout)
        
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
        
        self.clear_button = QPushButton("🗑️ " + self._("Clear List"))
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
        
        import_group.addWidget(self.import_button)
        import_group.addWidget(self.clear_button)
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
        self.x_input.setRange(0, 1000)
        self.x_input.setValue(50)  # 距左边50pt
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
        self.footer_x_input.setRange(0, 1000)
        self.footer_x_input.setValue(400)  # 页脚靠右
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
        self.y_input.setRange(0, 1000)
        self.y_input.setValue(800)  # 距顶部800pt (A4高度842pt)
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
        self.footer_y_input.setRange(0, 1000)
        self.footer_y_input.setValue(50)  # 距底部50pt
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
        preview_group = QVBoxLayout()
        preview_group.setSpacing(10)
        
        preview_label = QLabel("📍 " + self._("Header/Footer Position Preview"))
        preview_label.setAlignment(Qt.AlignCenter)
        preview_label.setStyleSheet("""
            font-weight: bold; 
            color: #2c3e50; 
            font-size: 13px;
            padding: 8px;
            background-color: #e8f4fd;
            border-radius: 6px;
        """)
        
        self.position_preview_canvas = QLabel()
        self.position_preview_canvas.setFixedSize(400, 200)
        self.position_preview_canvas.setStyleSheet("""
            background: white; 
            border: 2px solid #3498db; 
            border-radius: 8px;
            padding: 10px;
        """)
        
        preview_group.addWidget(preview_label)
        preview_group.addWidget(self.position_preview_canvas)

        # PDF内容预览区域
        pdf_preview_group = QVBoxLayout()
        pdf_preview_group.setSpacing(10)
        
        pdf_preview_label = QLabel("📄 " + self._("PDF Content Preview"))
        pdf_preview_label.setAlignment(Qt.AlignCenter)
        pdf_preview_label.setStyleSheet("""
            font-weight: bold; 
            color: #2c3e50; 
            font-size: 13px;
            padding: 8px;
            background-color: #e8f4fd;
            border-radius: 6px;
        """)
        
        self.pdf_preview_canvas = QLabel()
        self.pdf_preview_canvas.setFixedSize(400, 300)
        self.pdf_preview_canvas.setStyleSheet("""
            background: white; 
            border: 2px solid #3498db; 
            border-radius: 8px;
            padding: 10px;
        """)
        
        page_sel_layout = QHBoxLayout()
        page_sel_layout.setSpacing(10)
        
        page_label = QLabel(self._("Page: "))
        page_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        
        self.preview_page_spin = QSpinBox()
        self.preview_page_spin.setRange(1, 9999)
        self.preview_page_spin.setValue(1)
        self.preview_page_spin.setMinimumHeight(25)
        self.preview_page_spin.setStyleSheet("""
            QSpinBox {
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                min-width: 60px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
        """)
        
        page_sel_layout.addWidget(page_label)
        page_sel_layout.addWidget(self.preview_page_spin)
        page_sel_layout.addStretch()
        
        pdf_preview_group.addWidget(pdf_preview_label)
        pdf_preview_group.addLayout(page_sel_layout)
        pdf_preview_group.addWidget(self.pdf_preview_canvas)

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
        grid.addWidget(self.structured_checkbox, 8, 0, 1, 3)

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
        
        grid.addWidget(self.struct_cn_fixed_checkbox, 9, 0, 1, 1)
        grid.addWidget(self.struct_cn_font_combo, 9, 1, 1, 2)

        # 内存优化选项
        self.memory_optimization_checkbox = QCheckBox(self._("Memory optimization (for large files)"))
        self.memory_optimization_checkbox.setChecked(True)
        self.memory_optimization_checkbox.setToolTip(self._("Enable chunked processing and memory cleanup for large PDF files"))
        grid.addWidget(self.memory_optimization_checkbox, 10, 0, 1, 3)

        # 三列布局：设置控件 + 位置预览 + PDF预览
        horizontal_layout = QHBoxLayout()
        horizontal_layout.addLayout(grid, 4)
        horizontal_layout.addLayout(preview_group, 2)
        horizontal_layout.addLayout(pdf_preview_group, 2)

        group.setLayout(horizontal_layout)
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
        
        # 设置列宽比例，使列表更紧凑
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)  # 序号列固定宽度
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)  # 文件名列可调整
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)  # 大小列固定宽度
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)  # 页数列固定宽度
        self.file_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)  # 页眉列拉伸
        self.file_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)  # 页脚列拉伸
        
        # 设置默认列宽
        self.file_table.setColumnWidth(0, 60)   # 序号列
        self.file_table.setColumnWidth(1, 200)  # 文件名列
        self.file_table.setColumnWidth(2, 80)   # 大小列
        self.file_table.setColumnWidth(3, 80)   # 页数列
        
        # 启用排序功能
        self.file_table.setSortingEnabled(True)
        
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
                padding: 12px;
                border: none;
                font-weight: bold;
                font-size: 12px;
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
        """)
        
        # 表格编辑或选择变化时，实时刷新预览
        self.file_table.itemChanged.connect(lambda *_: self.update_preview())
        self.file_table.itemSelectionChanged.connect(self.update_preview)
        
        # 在文件表格设置后添加右键菜单
        self._setup_context_menu()
        
        table_layout.addWidget(self.file_table)
        table_group_layout.addLayout(table_layout)
        table_group.setLayout(table_group_layout)
        
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
        controls_layout.addWidget(self.move_up_button)
        controls_layout.addWidget(self.move_down_button)
        controls_layout.addWidget(self.remove_button)
        controls_layout.addStretch()
        
        controls_group.setLayout(controls_layout)
        
        layout.addWidget(table_group, 10)
        layout.addWidget(controls_group, 1)
        return layout

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
            "memory_optimization": self.memory_optimization_checkbox,
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

        preview_controls = [self.font_select, self.footer_font_select, self.font_size_spin, self.footer_font_size_spin, self.x_input, self.footer_x_input, self.structured_checkbox, self.normalize_a4_checkbox, self.struct_cn_fixed_checkbox, self.struct_cn_font_combo, self.memory_optimization_checkbox, self.preview_page_spin]
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

    def _show_context_menu(self, pos):
        """显示文件列表的右键菜单"""
        index = self.file_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        item = self.file_items[row]
        
        menu = QMenu(self)
        
        # 如果文件被限制编辑，显示解锁选项
        if hasattr(item, "encryption_status") and item.encryption_status != EncryptionStatus.OK:
            unlock_action = menu.addAction(self._("移除文件限制..."))
            unlock_action.triggered.connect(lambda: self._attempt_unlock(row))
            menu.addSeparator()
        
        # 添加其他菜单项
        read_action = menu.addAction(self._("读取现有页眉/页脚"))
        read_action.triggered.connect(lambda: self._read_existing_headers_footers(row))
        
        delete_action = menu.addAction(self._("删除"))
        delete_action.triggered.connect(lambda: self._delete_file_at_row(row))
        
        menu.exec(self.file_table.viewport().mapToGlobal(pos))

    def _attempt_unlock(self, row_index: int):
        """尝试解密选定的PDF文件，并提供详细错误反馈"""
        item = self.file_items[row_index]
        if not self.output_folder:
            QMessageBox.warning(self, self._("Output Folder Not Set"), self._("Please select an output folder..."))
            return
        encryption_status = getattr(item, "encryption_status", "ok")
        if encryption_status == "locked":
            QMessageBox.warning(self, self._("Locked File"), self._("This file is encrypted and cannot be opened without a password."))
            password, ok = QInputDialog.getText(self, self._("Decrypt PDF"), f"{item.name}\n\n{self._('Please enter the password:')}")
            if not ok:
                return
        elif encryption_status == "restricted":
            response = QMessageBox.question(
                self, self._("Restricted PDF"),
                self._("This PDF is restricted and cannot be modified.\nDo you want to attempt automatic unlocking?"),
                QMessageBox.Yes | QMessageBox.No
            )
            if response == QMessageBox.No:
                return
            # Always use the UI's selected output folder
            output_dir = self.output_folder
            result = self.controller.handle_unlock_pdf(item=item, password="", output_dir=output_dir)
            if result["success"]:
                QMessageBox.information(self, self._("Unlock Success"), result["message"])
                if result.get("output_path"):
                    self.progress_label.setText(self._("Unlocked file saved to: ") + result.get("output_path", "") + " (" + output_dir + ")")
                    self.output_path_display.setText(output_dir)
                    new_items = self.controller.handle_file_import([result["output_path"]])
                    if new_items:
                        new_items[0].unlocked_path = result.get("output_path", None)
                        self.file_items[row_index] = new_items[0]
                        self._populate_table_from_items()
            else:
                self.show_error(self._("Unlock Failed"), Exception(result["message"]))
            return
        else:
            return  # Not encrypted or already handled

        # 密码验证流程
        attempts = 3
        while attempts > 0:
            output_dir = self.output_folder
            result = self.controller.handle_unlock_pdf(item=item, password=password, output_dir=output_dir)
            if result["success"]:
                QMessageBox.information(self, self._("Unlock Success"), result["message"])
                if result.get("output_path"):
                    # Show unlock file path in progress label
                    self.progress_label.setText(self._("Unlocked file saved to: ") + result.get("output_path", "") + " (" + output_dir + ")")
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
                        self, self._("Unlock Failed"),
                        self._("Password incorrect. Would you like to attempt forced unlock without password?"),
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if choice == QMessageBox.Yes:
                        output_dir = self.output_folder
                        result = self.controller.handle_unlock_pdf(item=item, password="", output_dir=output_dir)
                        if result["success"]:
                            QMessageBox.information(self, self._("Unlock Success"), result["message"])
                            if result.get("output_path"):
                                # Show unlock file path in progress label
                                self.progress_label.setText(self._("Unlocked file saved to: ") + result.get("output_path", "") + " (" + output_dir + ")")
                                self.output_path_display.setText(output_dir)
                                new_items = self.controller.handle_file_import([result["output_path"]])
                                if new_items:
                                    new_items[0].unlocked_path = result.get("output_path", None)
                                    self.file_items[row_index] = new_items[0]
                                    self._populate_table_from_items()
                        else:
                            self.show_error(self._("Unlock Failed"), Exception(result["message"]))
                    return
                else:
                    password, ok = QInputDialog.getText(self, self._("Retry Password"), f"{item.name}\n\n{self._('Incorrect password. Try again:')}")
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
        self.file_table.setRowCount(0)
        for idx, item in enumerate(self.file_items):
            if not hasattr(item, "name") or not hasattr(item, "size_mb"):
                continue
            self.file_table.insertRow(idx)
            
            # 序号列：显示锁标志（如果文件被限制编辑）
            if hasattr(item, "encryption_status") and item.encryption_status != EncryptionStatus.OK:
                lock_text = f"🔒 {idx + 1}"
                no_item = QTableWidgetItem(lock_text)
                no_item.setToolTip(self._("File is encrypted or restricted"))
                no_item.setForeground(QBrush(QColor(255, 0, 0)))  # 红色显示
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
            # 只添加 PDFFileItem 类型且有 name 和 size_mb 属性的 item，防止嵌套导致后续 item.name 报错
            self.file_items.extend([
                item for item in new_items
                if isinstance(item, PDFFileItem) and hasattr(item, "name") and hasattr(item, "size_mb")
            ])
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
        """更新预览：包括位置预览和PDF内容预览"""
        self.update_position_preview()
        self.update_pdf_content_preview()
    
    def update_position_preview(self):
        """显示页眉和页脚位置预览：两个长条状区域，垂直居中，左右贯通"""
        if not self.file_items:
            # 无文件时的预览
            pixmap = QPixmap(400, 200)
            pixmap.fill(Qt.white)
            p = QPainter(pixmap)
            p.setPen(QPen(Qt.gray))
            p.drawText(20, 100, self._("No files to preview"))
            p.end()
            self.position_preview_canvas.setPixmap(pixmap)
            return
            
        try:
            # 创建位置预览画布
            pixmap = QPixmap(400, 200)
            pixmap.fill(Qt.white)
            p = QPainter(pixmap)
            
            # 获取当前设置
            settings = self._get_current_settings()
            
            # 绘制页面背景（模拟A4页面）
            page_width = 595  # A4宽度 (pt)
            page_height = 842  # A4高度 (pt)
            scale = min(350 / page_width, 150 / page_height)  # 缩放以适应预览区域
            
            scaled_width = int(page_width * scale)
            scaled_height = int(page_height * scale)
            start_x = (400 - scaled_width) // 2
            start_y = (200 - scaled_height) // 2
            
            # 绘制页面边框
            p.setPen(QPen(Qt.black, 1))
            p.drawRect(start_x, start_y, scaled_width, scaled_height)
            
            # 绘制页眉区域（顶部长条状，左右贯通）
            header_y = start_y + 20
            header_height = 25
            p.setPen(QPen(Qt.blue, 2))
            p.setBrush(QBrush(QColor(200, 200, 255, 150)))  # 半透明蓝色
            p.drawRect(start_x, header_y, scaled_width, header_height)
            
            # 绘制页眉文本
            header_text = self._get_current_header_text()
            if header_text:
                p.setPen(Qt.blue)
                p.setFont(QFont("Arial", 10))
                # 计算页眉位置（基于设置）
                header_x = start_x + int(settings.get("header_x", 50) * scale)
                header_y_text = header_y + 17
                
                # 根据对齐方式调整位置
                text_width = p.fontMetrics().horizontalAdvance(header_text[:30])
                if settings.get("header_alignment", "left") == "right":
                    header_x = start_x + scaled_width - text_width - 10
                elif settings.get("header_alignment", "left") == "center":
                    header_x = start_x + (scaled_width - text_width) // 2
                
                p.drawText(header_x, header_y_text, header_text[:30])
                
                # 绘制页眉位置指示器
                p.setPen(QPen(Qt.blue, 1))
                p.drawLine(header_x, header_y + header_height, header_x, header_y + header_height + 8)
                p.drawText(header_x - 15, header_y + header_height + 20, f"X:{settings.get('header_x', 50)}")
            
            # 绘制分割线
            center_y = start_y + scaled_height // 2
            p.setPen(QPen(Qt.gray, 1, Qt.DashLine))
            p.drawLine(start_x, center_y, start_x + scaled_width, center_y)
            
            # 绘制页脚区域（底部长条状，左右贯通）
            footer_y = start_y + scaled_height - 45
            footer_height = 25
            p.setPen(QPen(Qt.red, 2))
            p.setBrush(QBrush(QColor(255, 200, 200, 150)))  # 半透明红色
            p.drawRect(start_x, footer_y, scaled_width, footer_height)
            
            # 绘制页脚文本
            footer_text = self._get_current_footer_text()
            if footer_text:
                p.setPen(Qt.red)
                p.setFont(QFont("Arial", 10))
                # 计算页脚位置（基于设置）
                footer_x = start_x + int(settings.get("footer_x", 400) * scale)
                footer_y_text = footer_y + 17
                
                # 根据对齐方式调整位置
                text_width = p.fontMetrics().horizontalAdvance(footer_text[:30])
                if settings.get("footer_alignment", "left") == "right":
                    footer_x = start_x + scaled_width - text_width - 10
                elif settings.get("footer_alignment", "left") == "center":
                    footer_x = start_x + (scaled_width - text_width) // 2
                
                p.drawText(footer_x, footer_y_text, footer_text[:30])
                
                # 绘制页脚位置指示器
                p.setPen(QPen(Qt.red, 1))
                p.drawLine(footer_x, footer_y - 8, footer_x, footer_y)
                p.drawText(footer_x - 15, footer_y - 15, f"X:{settings.get('footer_x', 400)}")
            
            p.end()
            self.position_preview_canvas.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"Position preview error: {e}", exc_info=True)
    
    def update_pdf_content_preview(self):
        """显示PDF内容预览，根据页眉页脚设置实时渲染"""
        row = self.file_table.currentRow()
        if row < 0 or row >= len(self.file_items):
            # 无文件时的预览
            pixmap = QPixmap(400, 300)
            pixmap.fill(Qt.white)
            p = QPainter(pixmap)
            p.setPen(QPen(Qt.gray))
            p.drawText(20, 150, self._("No file selected"))
            p.end()
            self.pdf_preview_canvas.setPixmap(pixmap)
            return
            
        try:
            # 创建PDF内容预览画布
            pixmap = QPixmap(400, 300)
            pixmap.fill(Qt.white)
            p = QPainter(pixmap)
            
            # 获取当前设置
            settings = self._get_current_settings()
            
            # 获取页眉页脚文本
            header_text = self._get_current_header_text()
            footer_text = self._get_current_footer_text()
            
            # 尝试加载真实PDF内容
            item = self.file_items[row]
            page_num = self.preview_page_spin.value() - 1  # 转换为0基索引
            
            try:
                # 使用PyMuPDF加载PDF页面
                if fitz:
                    doc = fitz.open(item.path)
                    if 0 <= page_num < len(doc):
                        page = doc[page_num]
                        
                        # 获取页面尺寸
                        page_width = page.rect.width
                        page_height = page.rect.height
                        
                        # 计算缩放比例
                        scale = min(350 / page_width, 250 / page_height)
                        
                        scaled_width = int(page_width * scale)
                        scaled_height = int(page_height * scale)
                        start_x = (400 - scaled_width) // 2
                        start_y = (300 - scaled_height) // 2
                        
                        # 渲染PDF页面到图像
                        mat = fitz.Matrix(scale, scale)
                        pix = page.get_pixmap(matrix=mat)
                        
                        # 转换为QPixmap
                        img_data = pix.tobytes("ppm")
                        img = QImage.fromData(img_data)
                        pdf_pixmap = QPixmap.fromImage(img)
                        
                        # 绘制PDF页面
                        p.drawPixmap(start_x, start_y, pdf_pixmap)
                        
                        # 绘制页面边框
                        p.setPen(QPen(Qt.black, 1))
                        p.drawRect(start_x, start_y, scaled_width, scaled_height)
                        
                        # 绘制页眉文本（根据设置渲染）
                        if header_text:
                            p.setPen(QPen(Qt.blue, 2))
                            font_size = int(settings.get("header_font_size", 14) * scale)
                            p.setFont(QFont(settings.get("header_font", "Arial"), font_size))
                            
                            # 计算页眉位置
                            header_x = start_x + int(settings.get("header_x", 50) * scale)
                            header_y = start_y + int(settings.get("header_y", 800) * scale)
                            
                            # 根据对齐方式调整位置
                            text_width = p.fontMetrics().horizontalAdvance(header_text[:50])
                            if settings.get("header_alignment", "left") == "right":
                                header_x = start_x + scaled_width - text_width - 20
                            elif settings.get("header_alignment", "left") == "center":
                                header_x = start_x + (scaled_width - text_width) // 2
                            
                            # 绘制文本背景（半透明）
                            p.setBrush(QBrush(QColor(255, 255, 255, 180)))
                            p.setPen(Qt.NoPen)
                            text_rect = p.fontMetrics().boundingRect(header_text[:50])
                            p.drawRect(header_x, header_y - text_rect.height(), text_rect.width(), text_rect.height())
                            
                            # 绘制文本
                            p.setPen(QPen(Qt.blue, 2))
                            p.drawText(header_x, header_y, header_text[:50])
                        
                        # 绘制页脚文本（根据设置渲染）
                        if footer_text:
                            p.setPen(QPen(Qt.red, 2))
                            font_size = int(settings.get("footer_font_size", 14) * scale)
                            p.setFont(QFont(settings.get("footer_font", "Arial"), font_size))
                            
                            # 计算页脚位置
                            footer_x = start_x + int(settings.get("footer_x", 400) * scale)
                            footer_y = start_y + int(settings.get("footer_y", 50) * scale)
                            
                            # 根据对齐方式调整位置
                            text_width = p.fontMetrics().horizontalAdvance(footer_text[:50])
                            if settings.get("footer_alignment", "left") == "right":
                                footer_x = start_x + scaled_width - text_width - 20
                            elif settings.get("footer_alignment", "left") == "center":
                                footer_x = start_x + (scaled_width - text_width) // 2
                            
                            # 绘制文本背景（半透明）
                            p.setBrush(QBrush(QColor(255, 255, 255, 180)))
                            p.setPen(Qt.NoPen)
                            text_rect = p.fontMetrics().boundingRect(footer_text[:50])
                            p.drawRect(footer_x, footer_y - text_rect.height(), text_rect.width(), text_rect.height())
                            
                            # 绘制文本
                            p.setPen(QPen(Qt.red, 2))
                            p.drawText(footer_x, footer_y, footer_text[:50])
                        
                        doc.close()
                    else:
                        # 页码超出范围，显示错误信息
                        p.setPen(QPen(Qt.red))
                        p.drawText(20, 150, self._("Page number out of range"))
                        doc.close()
                else:
                    # 如果没有PyMuPDF，使用模拟预览
                    self._draw_simulated_preview(p, settings, header_text, footer_text)
                    
            except Exception as e:
                logger.warning(f"Failed to load PDF content: {e}")
                # 回退到模拟预览
                self._draw_simulated_preview(p, settings, header_text, footer_text)
            
            p.end()
            self.pdf_preview_canvas.setPixmap(pixmap)
            
        except Exception as e:
            logger.error(f"PDF content preview error: {e}", exc_info=True)
            # 显示错误预览
            pixmap = QPixmap(400, 300)
            pixmap.fill(Qt.white)
            p = QPainter(pixmap)
            p.setPen(QPen(Qt.red))
            p.drawText(20, 150, self._("Preview failed"))
            p.drawText(20, 170, f"Error: {str(e)}")
            p.end()
            self.pdf_preview_canvas.setPixmap(pixmap)
    
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
            
            header_x = start_x + int(settings.get("header_x", 50) * scale)
            header_y = start_y + int(settings.get("header_y", 800) * scale)
            
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
            
            footer_x = start_x + int(settings.get("footer_x", 400) * scale)
            footer_y = start_y + int(settings.get("footer_y", 50) * scale)
            
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
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self._show_context_menu)
    
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
        """显示右键菜单"""
        row = self.file_table.rowAt(position.y())
        if row < 0 or row >= len(self.file_items):
            return
            
        menu = QMenu(self)
        
        # 读取现有页眉/页脚
        read_action = menu.addAction(self._("读取现有页眉/页脚"))
        read_action.triggered.connect(lambda: self._read_existing_headers_footers(row))
        
        # 删除文件
        delete_action = menu.addAction(self._("删除"))
        delete_action.triggered.connect(lambda: self._delete_file_at_row(row))
        
        menu.exec_(self.file_table.mapToGlobal(position))

    def _read_existing_headers_footers(self, row: int):
        """读取现有页眉页脚"""
        if row >= 0 and row < len(self.file_items):
            try:
                item = self.file_items[row]
                # 这里可以添加读取现有页眉页脚的逻辑
                QMessageBox.information(self, self._("读取结果"), self._("未检测到现有的页眉/页脚"))
            except Exception as e:
                QMessageBox.warning(self, self._("读取失败"), f"{self._('读取现有页眉/页脚失败')}: {str(e)}")

    def _delete_file_at_row(self, row: int):
        """删除指定行的文件"""
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
            if language == "zh_CN":
                self.language_map = _setup_language()
            else:
                # 英文界面
                self.language_map = {
                    "Import Files or Folders": "Import Files or Folders",
                    "Clear List": "Clear List",
                    "Header Mode:": "Header Mode:",
                    "Filename Mode": "Filename Mode",
                    "Auto Number Mode": "Auto Number Mode",
                    "Custom Mode": "Custom Mode",
                    "Auto Number Settings": "Auto Number Settings",
                    "Prefix:": "Prefix:",
                    "Start #:": "Start #:",
                    "Step:": "Step:",
                    "Digits:": "Digits:",
                    "Suffix:": "Suffix:",
                    "Header & Footer Settings": "Header & Footer Settings",
                    "Settings": "Settings",
                    "Header": "Header",
                    "Footer": "Footer",
                    "Font:": "Font:",
                    "Size:": "Size:",
                    "X Position:": "X Position:",
                    "Y Position:": "Y Position:",
                    "Alignment:": "Alignment:",
                    "Left": "Left",
                    "Center": "Center",
                    "Right": "Right",
                    "Global Footer Text:": "Global Footer Text:",
                    "Use {page} for current page, {total} for total pages.": "Use {page} for current page, {total} for total pages.",
                    "Apply to All": "Apply to All",
                    "Header/Footer Preview": "Header/Footer Preview",
                    "Page: ": "Page: ",
                    "Structured mode (Acrobat-friendly)": "Structured mode (Acrobat-friendly)",
                    "Structured CN: use fixed font": "Structured CN: use fixed font",
                    "Memory optimization (for large files)": "Memory optimization (for large files)",
                    "Enable chunked processing and memory cleanup for large PDF files": "Enable chunked processing and memory cleanup for large PDF files",
                    "Move Up": "Move Up",
                    "Move Down": "Move Down",
                    "Remove": "Remove",
                    "Output Folder:": "Output Folder:",
                    "Select Output Folder": "Select Output Folder",
                    "Start Processing": "Start Processing",
                    "Merge after processing": "Merge after processing",
                    "Add page numbers after merge": "Add page numbers after merge",
                    "Normalize to A4 (auto)": "Normalize to A4 (auto)",
                    "单位:": "Unit:",
                    "预设位置:": "Preset Position:",
                    "右上角": "Top Right",
                    "右下角": "Bottom Right",
                    "No.": "No.",
                    "Filename": "Filename",
                    "Size (MB)": "Size (MB)",
                    "Page Count": "Page Count",
                    "Header Text": "Header Text",
                    "Footer Text": "Footer Text",
                    "读取现有页眉/页脚": "Read Existing Headers/Footers",
                    "删除": "Delete",
                    "Header Template:": "Header Template:",
                    "Custom": "Custom",
                    "Company Name": "Company Name",
                    "Document Title": "Document Title",
                    "Date": "Date",
                    "Page Number": "Page Number",
                    "Confidential": "Confidential",
                    "Draft": "Draft",
                    "Final Version": "Final Version",
                    "Help": "Help",
                    "About DocDeck": "About DocDeck",
                    "DocDeck - PDF Header & Footer Tool": "DocDeck - PDF Header & Footer Tool",
                    "Author: 木小樨": "Author: 木小樨",
                    "Project Homepage:": "Project Homepage:",
                    "移除文件限制...": "Remove File Restrictions...",
                    "Output Folder Not Set": "Output Folder Not Set",
                    "Please select an output folder...": "Please select an output folder...",
                    "Locked File": "Locked File",
                    "This file is encrypted and cannot be opened without a password.": "This file is encrypted and cannot be opened without a password.",
                    "Decrypt PDF": "Decrypt PDF",
                    "Please enter the password:": "Please enter the password:",
                    "Restricted PDF": "Restricted PDF",
                    "This PDF is restricted and cannot be modified.\nDo you want to attempt automatic unlocking?": "This PDF is restricted and cannot be modified.\nDo you want to attempt automatic unlocking?",
                    "Unlock Success": "Unlock Success",
                    "Unlocked file saved to: ": "Unlocked file saved to: ",
                    "Unlock Failed": "Unlock Failed",
                    "Password incorrect. Would you like to attempt forced unlock without password?": "Password incorrect. Would you like to attempt forced unlock without password?",
                    "Operation Failed": "Operation Failed",
                    "Invalid Files": "Invalid Files",
                    "Only PDF files can be imported.": "Only PDF files can be imported.",
                    "The following files are fully encrypted and require a password:\n": "The following files are fully encrypted and require a password:\n",
                    "The following files are restricted (e.g., can't be modified):\n": "The following files are restricted (e.g., can't be modified):\n",
                    "Encrypted Files Notice": "Encrypted Files Notice",
                    "Failed to import files": "Failed to import files",
                    "No preview": "No preview",
                    "Preview failed": "Preview failed",
                    "Failed to apply settings due to an error. Please check the logs.": "Failed to apply settings due to an error. Please check the logs.",
                    "Error": "Error",
                    "Processing... ": "Processing... ",
                    "This position is too close to the edge...": "This position is too close to the edge...",
                    "读取现有页眉/页脚失败": "Failed to read existing headers/footers",
                    "确定要删除文件": "Confirm file deletion",
                    "吗？": "?",
                    "Ready": "Ready",
                    "Processing": "Processing",
                    "Success": "Success",
                    "Settings imported successfully!": "Settings imported successfully!",
                    "Settings exported successfully!": "Settings exported successfully!",
                    "Reset Settings": "Reset Settings",
                    "Are you sure you want to reset all settings to default values?": "Are you sure you want to reset all settings to default values?",
                    "Settings reset to defaults!": "Settings reset to defaults!",
                    "Failed to import settings": "Failed to import settings",
                    "Failed to export settings": "Failed to export settings",
                    "Failed to reset settings": "Failed to reset settings",
                    "File": "File",
                    "Import Settings...": "Import Settings...",
                    "Export Settings...": "Export Settings...",
                    "Exit": "Exit",
                    "Settings": "Settings",
                    "Reset to Defaults": "Reset to Defaults",
                    "Language": "Language",
                    "Search:": "Search:",
                    "Type to search files...": "Type to search files...",
                    "All": "All",
                    "Clear": "Clear",
                    "No files to preview": "No files to preview",
                    "No file selected": "No file selected",
                    "Page number out of range": "Page number out of range",
                    "File is encrypted or restricted": "File is encrypted or restricted",
                    "Header/Footer Position Preview": "Header/Footer Position Preview",
                    "PDF Content Preview": "PDF Content Preview"
                }
            
            # 重新应用设置
            self._apply_settings(current_settings)
            
            # 刷新UI
            self._refresh_ui_texts()
            
            QMessageBox.information(self, self._("Success"), self._("Language changed successfully!"))
            
        except Exception as e:
            QMessageBox.critical(self, self._("Error"), f"{self._('Failed to change language')}: {str(e)}")
    
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
                self.x_input.setValue(500)
        
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
                self.footer_x_input.setValue(500)
        
        # 设置Y位置（距下边0.8cm）
        if unit == "pt":
            y = bottom_margin * 28.35  # 下边距
        elif unit == "cm":
            y = bottom_margin  # 下边距
        else:  # mm
            y = bottom_margin * 10  # 下边距
        
        self.footer_y_input.setValue(int(y))
        self.footer_font_size_spin.setValue(14)  # 14号字体
