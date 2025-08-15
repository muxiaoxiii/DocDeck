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
        return 'en_US'  # 默认英语
    except:
        return 'en_US'

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
        self.import_button = QPushButton(self._("Import Files or Folders"))
        self.clear_button = QPushButton(self._("Clear List"))
        mode_label = QLabel(self._("Header Mode:"))
        self.mode_select_combo = QComboBox()
        self.mode_select_combo.addItems([self._("Filename Mode"), self._("Auto Number Mode"), self._("Custom Mode")])
        layout.addWidget(self.import_button); layout.addWidget(self.clear_button)
        layout.addStretch(); layout.addWidget(mode_label); layout.addWidget(self.mode_select_combo)
        return layout

    def _create_auto_number_group(self) -> QGroupBox:
        """创建自动编号设置的控件组"""
        group = QGroupBox(self._("Auto Number Settings"))
        layout = QHBoxLayout()
        self.prefix_input = QLineEdit("Doc-")
        self.start_spin = QSpinBox(); self.start_spin.setRange(1, 9999); self.start_spin.setValue(1)
        self.step_spin = QSpinBox(); self.step_spin.setRange(1, 100); self.step_spin.setValue(1)
        self.digits_spin = QSpinBox(); self.digits_spin.setRange(1, 6); self.digits_spin.setValue(3)
        self.suffix_input = QLineEdit("")
        
        layout.addWidget(QLabel(self._("Prefix:"))); layout.addWidget(self.prefix_input)
        layout.addWidget(QLabel(self._("Start #:"))); layout.addWidget(self.start_spin)
        layout.addWidget(QLabel(self._("Step:"))); layout.addWidget(self.step_spin)
        layout.addWidget(QLabel(self._("Digits:"))); layout.addWidget(self.digits_spin)
        layout.addWidget(QLabel(self._("Suffix:"))); layout.addWidget(self.suffix_input)
        group.setLayout(layout)
        group.setVisible(False)
        return group

    def _create_settings_grid_group(self) -> QGroupBox:
        """创建页眉页脚的网格布局设置控件组（新版：设置与预览横向并排，预览为横条，仅Header/Footer）"""
        group = QGroupBox(self._("Header & Footer Settings"))
        group.setObjectName("Header & Footer Settings")
        grid = QGridLayout()
        grid.setColumnStretch(1, 1); grid.setColumnStretch(2, 1); grid.setColumnStretch(3, 1)

        # 设置控件部分
        grid.addWidget(QLabel("<b>" + self._("Settings") + "</b>"), 0, 0, Qt.AlignRight)
        grid.addWidget(QLabel("<b>" + self._("Header") + "</b>"), 0, 1, Qt.AlignCenter)
        grid.addWidget(QLabel("<b>" + self._("Footer") + "</b>"), 0, 2, Qt.AlignCenter)
        
        self.font_select = QComboBox(); self.font_select.addItems(get_system_fonts())
        self.footer_font_select = QComboBox(); self.footer_font_select.addItems(get_system_fonts())
        self.font_size_spin = QSpinBox(); self.font_size_spin.setRange(6, 72); self.font_size_spin.setValue(14)
        self.footer_font_size_spin = QSpinBox(); self.footer_font_size_spin.setRange(6, 72); self.footer_font_size_spin.setValue(14)
        grid.addWidget(QLabel(self._("Font:")), 1, 0, Qt.AlignRight); grid.addWidget(self.font_select, 1, 1); grid.addWidget(self.footer_font_select, 1, 2)
        grid.addWidget(QLabel(self._("Size:")), 2, 0, Qt.AlignRight); grid.addWidget(self.font_size_spin, 2, 1); grid.addWidget(self.footer_font_size_spin, 2, 2)
        
        # 设置合理的默认位置：页眉在顶部，页脚在右下角
        self.x_input = QSpinBox(); self.x_input.setRange(0, 1000); self.x_input.setValue(50)  # 距左边50pt
        self.footer_x_input = QSpinBox(); self.footer_x_input.setRange(0, 1000); self.footer_x_input.setValue(400)  # 页脚靠右
        self.y_input = QSpinBox(); self.y_input.setRange(0, 1000); self.y_input.setValue(800)  # 距顶部800pt (A4高度842pt)
        self.header_y_warning_label = self._create_warning_label()
        header_y_layout = QHBoxLayout(); header_y_layout.addWidget(self.y_input); header_y_layout.addWidget(self.header_y_warning_label)
        self.footer_y_input = QSpinBox(); self.footer_y_input.setRange(0, 1000); self.footer_y_input.setValue(50)  # 距底部50pt
        self.footer_y_warning_label = self._create_warning_label()
        footer_y_layout = QHBoxLayout(); footer_y_layout.addWidget(self.footer_y_input); footer_y_layout.addWidget(self.footer_y_warning_label)
        grid.addWidget(QLabel(self._("X Position:")), 3, 0, Qt.AlignRight); grid.addWidget(self.x_input, 3, 1); grid.addWidget(self.footer_x_input, 3, 2)
        grid.addWidget(QLabel(self._("Y Position:")), 4, 0, Qt.AlignRight); grid.addLayout(header_y_layout, 4, 1); grid.addLayout(footer_y_layout, 4, 2)

        self.left_btn = QPushButton(self._("Left")); self.center_btn = QPushButton(self._("Center")); self.right_btn = QPushButton(self._("Right"))
        header_align_layout = QHBoxLayout(); header_align_layout.addWidget(self.left_btn); header_align_layout.addWidget(self.center_btn); header_align_layout.addWidget(self.right_btn)
        self.footer_left_btn = QPushButton(self._("Left")); self.footer_center_btn = QPushButton(self._("Center")); self.footer_right_btn = QPushButton(self._("Right"))
        footer_align_layout = QHBoxLayout(); footer_align_layout.addWidget(self.footer_left_btn); footer_align_layout.addWidget(self.footer_center_btn); footer_align_layout.addWidget(self.footer_right_btn)
        grid.addWidget(QLabel(self._("Alignment:")), 5, 0, Qt.AlignRight); grid.addLayout(header_align_layout, 5, 1); grid.addLayout(footer_align_layout, 5, 2)

        # 页眉模板选择
        grid.addWidget(QLabel(self._("Header Template:")), 6, 0, Qt.AlignRight)
        self.header_template_combo = QComboBox()
        self.header_template_combo.addItems([
            self._("Custom"),
            self._("Company Name"),
            self._("Document Title"),
            self._("Date"),
            self._("Page Number"),
            self._("Confidential"),
            self._("Draft"),
            self._("Final Version")
        ])
        self.header_template_combo.currentTextChanged.connect(self._on_header_template_changed)
        grid.addWidget(self.header_template_combo, 6, 1, 1, 2)

        grid.addWidget(QLabel(self._("Global Footer Text:")), 7, 0, Qt.AlignRight)
        self.global_footer_text = QLineEdit(self._("Page {page} of {total}"))
        self.global_footer_text.setToolTip(self._("Use {page} for current page, {total} for total pages."))
        self.apply_footer_template_button = QPushButton(self._("Apply to All"))
        footer_template_layout = QHBoxLayout(); footer_template_layout.addWidget(self.global_footer_text); footer_template_layout.addWidget(self.apply_footer_template_button)
        grid.addLayout(footer_template_layout, 7, 1, 1, 2)

        # 新：预览区域横向长条，仅Header/Footer
        preview_group = QVBoxLayout()
        preview_label = QLabel(self._("Header/Footer Preview")); preview_label.setAlignment(Qt.AlignCenter)
        self.preview_canvas = QLabel(); self.preview_canvas.setFixedSize(600, 360)
        self.preview_canvas.setStyleSheet("background: white; border: 1px solid #ccc;")
        page_sel_layout = QHBoxLayout(); page_sel_layout.addWidget(QLabel(self._("Page: ")))
        self.preview_page_spin = QSpinBox(); self.preview_page_spin.setRange(1, 9999); self.preview_page_spin.setValue(1)
        page_sel_layout.addWidget(self.preview_page_spin); page_sel_layout.addStretch()
        preview_group.addWidget(preview_label)
        preview_group.addLayout(page_sel_layout)
        preview_group.addWidget(self.preview_canvas)

        # 结构化模式开关
        self.structured_checkbox = QCheckBox(self._("Structured mode (Acrobat-friendly)"))
        self.structured_checkbox.setChecked(False)
        grid.addWidget(self.structured_checkbox, 8, 0, 1, 3)

        # 结构化中文选项
        self.struct_cn_fixed_checkbox = QCheckBox(self._("Structured CN: use fixed font"))
        self.struct_cn_fixed_checkbox.setChecked(False)
        self.struct_cn_font_combo = QComboBox(); self.struct_cn_font_combo.addItems(get_system_fonts())
        grid.addWidget(self.struct_cn_fixed_checkbox, 9, 0, 1, 1)
        grid.addWidget(self.struct_cn_font_combo, 9, 1, 1, 2)

        # 内存优化选项
        self.memory_optimization_checkbox = QCheckBox(self._("Memory optimization (for large files)"))
        self.memory_optimization_checkbox.setChecked(True)
        self.memory_optimization_checkbox.setToolTip(self._("Enable chunked processing and memory cleanup for large PDF files"))
        grid.addWidget(self.memory_optimization_checkbox, 10, 0, 1, 3)

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
        self.file_table.setHorizontalHeaderLabels([self._("No."), self._("Filename"), self._("Size (MB)"), self._("Page Count"), self._("Header Text"), self._("Footer Text")])
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.file_table.setEditTriggers(QTableWidget.DoubleClicked)
        # 表格编辑或选择变化时，实时刷新预览
        self.file_table.itemChanged.connect(lambda *_: self.update_preview())
        self.file_table.itemSelectionChanged.connect(self.update_preview)
        # 在文件表格设置后添加右键菜单
        self._setup_context_menu()
        
        controls_layout = QVBoxLayout()
        self.move_up_button = QPushButton(self._("Move Up"))
        self.move_down_button = QPushButton(self._("Move Down"))
        self.remove_button = QPushButton(self._("Remove"))
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
        
        self.select_output_button = QPushButton(self._("Select Output Folder"))
        self.start_button = QPushButton(self._("Start Processing")); self.start_button.setStyleSheet("font-weight: bold; padding: 5px;")

        h_layout.addWidget(QLabel(self._("Output Folder:"))); h_layout.addWidget(self.output_path_display, 1)
        h_layout.addWidget(self.select_output_button); h_layout.addWidget(self.start_button)
        
        checkbox_layout = QHBoxLayout()
        self.merge_checkbox = QCheckBox(self._("Merge after processing"))
        self.page_number_checkbox = QCheckBox(self._("Add page numbers after merge"))
        self.normalize_a4_checkbox = QCheckBox(self._("Normalize to A4 (auto)"))
        self.normalize_a4_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.merge_checkbox); checkbox_layout.addWidget(self.page_number_checkbox)
        checkbox_layout.addWidget(self.normalize_a4_checkbox)
        checkbox_layout.addStretch()

        self.progress_label = QLabel(""); self.progress_label.setAlignment(Qt.AlignCenter)

        layout.addLayout(h_layout); layout.addLayout(checkbox_layout); layout.addWidget(self.progress_label)
        return layout
    
    def _create_warning_label(self) -> QLabel:
        label = QLabel("⚠️"); label.setToolTip(self._("This position is too close to the edge...")); label.setVisible(False)
        return label

    def _setup_menu(self):
        menubar = self.menuBar(); help_menu = menubar.addMenu(self._("Help"))
        about_action = help_menu.addAction(self._("About")); about_action.triggered.connect(self.show_about_dialog)

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
        unlock_action = menu.addAction(self._("移除文件限制..."))
        unlock_action.triggered.connect(lambda: self._attempt_unlock(index.row()))
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
        """显示页眉和页脚的条状预览，模拟PDF页面布局"""
        row = self.file_table.currentRow()
        if row < 0 or row >= len(self.file_items):
            # 无文件时的预览
            pixmap = QPixmap(600, 360)
            pixmap.fill(Qt.white)
            p = QPainter(pixmap)
            p.setPen(QPen(Qt.gray))
            p.drawText(20, 40, self._("No preview"))
            p.end()
            self.preview_canvas.setPixmap(pixmap)
            return
            
        try:
            # 创建预览画布
            pixmap = QPixmap(600, 360)
            pixmap.fill(Qt.white)
            p = QPainter(pixmap)
            
            # 设置字体
            header_font = QFont("Arial", 14)
            footer_font = QFont("Arial", 14)
            p.setFont(header_font)
            
            # 获取当前设置
            settings = self._get_current_settings()
            
            # 获取页眉页脚文本，优先从表格获取
            header_text = ""
            footer_text = ""
            
            if self.file_table.item(row, 4):
                header_text = self.file_table.item(row, 4).text()
            elif hasattr(self.file_items[row], 'header_text'):
                header_text = self.file_items[row].header_text or ""
                
            if self.file_table.item(row, 5):
                footer_text = self.file_table.item(row, 5).text()
            elif hasattr(self.file_items[row], 'footer_text'):
                footer_text = self.file_items[row].footer_text or ""
            
            # 绘制页面背景（模拟A4页面）
            page_width = 595  # A4宽度 (pt)
            page_height = 842  # A4高度 (pt)
            scale = min(500 / page_width, 300 / page_height)  # 缩放以适应预览区域
            
            scaled_width = int(page_width * scale)
            scaled_height = int(page_height * scale)
            start_x = (600 - scaled_width) // 2
            start_y = (360 - scaled_height) // 2
            
            # 绘制页面边框
            p.setPen(QPen(Qt.black, 1))
            p.drawRect(start_x, start_y, scaled_width, scaled_height)
            
            # 绘制页眉区域（顶部条状）
            header_y = start_y + 20
            header_height = 30
            p.setPen(QPen(Qt.blue, 2))
            p.setBrush(QBrush(QColor(200, 200, 255, 100)))  # 半透明蓝色
            p.drawRect(start_x, header_y, scaled_width, header_height)
            
            # 绘制页眉文本
            if header_text:
                p.setPen(Qt.blue)
                p.setFont(header_font)
                # 计算页眉位置（基于设置）
                header_x = start_x + int(settings.get("header_x", 50) * scale)
                header_y_text = header_y + 20
                
                # 计算文本宽度，从右到左定位（右对齐）
                text_width = p.fontMetrics().horizontalAdvance(header_text[:50])
                if settings.get("header_alignment", "left") == "right":
                    header_x = start_x + scaled_width - text_width - 20  # 右对齐，留20pt边距
                elif settings.get("header_alignment", "left") == "center":
                    header_x = start_x + (scaled_width - text_width) // 2  # 居中
                
                p.drawText(header_x, header_y_text, header_text[:50])  # 限制文本长度
                
                # 绘制页眉位置指示器
                p.setPen(QPen(Qt.blue, 2))
                p.drawLine(header_x, header_y + header_height, header_x, header_y + header_height + 10)
                p.drawText(header_x - 20, header_y + header_height + 25, f"X:{settings.get('header_x', 50)}")
            
            # 绘制页脚区域（底部条状）
            footer_y = start_y + scaled_height - 50
            footer_height = 30
            p.setPen(QPen(Qt.red, 2))
            p.setBrush(QBrush(QColor(255, 200, 200, 100)))  # 半透明红色
            p.drawRect(start_x, footer_y, scaled_width, footer_height)
            
            # 绘制页脚文本
            if footer_text:
                p.setPen(Qt.red)
                p.setFont(footer_font)
                # 计算页脚位置（基于设置）
                footer_x = start_x + int(settings.get("footer_x", 400) * scale)
                footer_y_text = footer_y + 20
                
                # 计算文本宽度，从右到左定位（右对齐）
                text_width = p.fontMetrics().horizontalAdvance(footer_text[:50])
                if settings.get("footer_alignment", "left") == "right":
                    footer_x = start_x + scaled_width - text_width - 20  # 右对齐，留20pt边距
                elif settings.get("footer_alignment", "left") == "center":
                    footer_x = start_x + (scaled_width - text_width) // 2  # 居中
                
                p.drawText(footer_x, footer_y_text, footer_text[:50])  # 限制文本长度
                
                # 绘制页脚位置指示器
                p.setPen(QPen(Qt.red, 2))
                p.drawLine(footer_x, footer_y, footer_x, footer_y - 10)
                p.drawText(footer_x - 20, footer_y - 15, f"Y:{settings.get('footer_y', 50)}")
            
            # 绘制坐标信息
            p.setPen(Qt.black)
            p.setFont(QFont("Arial", 10))
            info_text = f"Header: ({settings.get('header_x', 50)}, {settings.get('header_y', 800)}) | Footer: ({settings.get('footer_x', 400)}, {settings.get('footer_y', 50)})"
            p.drawText(10, 350, info_text)
            
            # 绘制单位信息
            unit = self.unit_combo.currentText()
            p.drawText(10, 340, f"Unit: {unit}")
            
            p.end()
            self.preview_canvas.setPixmap(pixmap)
            
        except Exception as e:
            # 预览失败时的fallback
            pixmap = QPixmap(600, 360)
            pixmap.fill(Qt.white)
            p = QPainter(pixmap)
            p.setPen(QPen(Qt.gray))
            p.drawText(20, 40, self._("Preview failed"))
            p.drawText(20, 60, f"Error: {str(e)}")
            p.end()
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
        """更新进度条标签"""
        percent = int((current / total) * 100)
        self.progress_label.setText(self._("Processing... ") + f"({percent}%) - {filename}")
    
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
        delete_action.triggered.connect(lambda: self._delete_file(row))
        
        menu.exec_(self.file_table.mapToGlobal(position))

    def _read_existing_headers_footers(self, row):
        """读取指定文件的现有页眉/页脚"""
        if row < 0 or row >= len(self.file_items):
            return
            
        file_path = self.file_items[row].path
        try:
            from pdf_utils import extract_all_headers_footers
            result = extract_all_headers_footers(file_path, max_pages=5)
            
            if not result or not result.get("pages"):
                QMessageBox.information(self, self._("读取结果"), self._("未检测到现有的页眉/页脚"))
                return
                
            # 构建显示内容
            content = self._("检测到以下页眉/页脚内容：\n\n")
            for page_info in result["pages"]:
                content += f"第 {page_info['page']} 页:\n"
                if page_info.get("header"):
                    content += f"  页眉: {', '.join(page_info['header'])}\n"
                if page_info.get("footer"):
                    content += f"  页脚: {', '.join(page_info['footer'])}\n"
                content += "\n"
            
            # 创建更详细的对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(self._("现有页眉/页脚"))
            msg_box.setText(content)
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Ok | 
                QMessageBox.StandardButton.Cancel
            )
            msg_box.setInformativeText(self._("检测结果包含结构化标签和启发式识别的页眉/页脚"))
            
            # 添加操作按钮
            if result["pages"]:
                # 尝试自动识别页眉页脚文本
                all_headers = []
                all_footers = []
                for page_info in result["pages"]:
                    all_headers.extend(page_info.get("header", []))
                    all_footers.extend(page_info.get("footer", []))
                
                if all_headers:
                    most_common_header = max(set(all_headers), key=all_headers.count)
                    msg_box.setDetailedText(f"建议页眉: {most_common_header}")
                
                if all_footers:
                    most_common_footer = max(set(all_footers), key=all_footers.count)
                    if msg_box.detailedText():
                        msg_box.setDetailedText(msg_box.detailedText() + f"\n建议页脚: {most_common_footer}")
                    else:
                        msg_box.setDetailedText(f"建议页脚: {most_common_footer}")
            
            msg_box.exec_()
            
        except Exception as e:
            QMessageBox.warning(self, self._("读取失败"), f"{self._('读取现有页眉/页脚失败')}: {str(e)}")

    def _delete_file(self, row):
        """删除指定文件"""
        if row < 0 or row >= len(self.file_items):
            return
            
        reply = QMessageBox.question(
            self, self._("确认删除"), 
            f"{self._('确定要删除文件')} '{self.file_items[row].name}' {self._('吗？')}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.file_items.pop(row)
            self._update_file_table()
            self.update_preview()

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
        """转换单位：pt <-> cm <-> mm"""
        # 先转换为pt
        pt_value = value
        if from_unit == "cm":
            pt_value = value * 28.35
        elif from_unit == "mm":
            pt_value = value * 2.835
        
        # 从pt转换为目标单位
        if to_unit == "pt":
            return pt_value
        elif to_unit == "cm":
            return pt_value / 28.35
        elif to_unit == "mm":
            return pt_value / 2.835
        return pt_value

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
