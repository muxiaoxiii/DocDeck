from enum import Enum

# === App Version ===
APP_VERSION = "2.0.0"

# === Default Output Settings ===
DEFAULT_OUTPUT_DIR_NAME = "with header"
DEFAULT_LANGUAGE = "zh_CN"  # zh_CN, en_US

# === Font Settings ===
DEFAULT_FONT_NAME = "Helvetica"
DEFAULT_FONT_SIZE = 9

# === Header/Footer Placement ===
DEFAULT_HEADER_Y = 752  # 792 - 40pt
DEFAULT_FOOTER_Y = 40
PAGE_HEIGHT_PT = 792  # Letter size
PAGE_WIDTH_PT = 612   # Letter size
LEFT_MARGIN = 72
RIGHT_MARGIN = 72
TOP_MARGIN = 72
BOTTOM_MARGIN = 72

# === Header Modes ===
class HeaderMode(Enum):
    FILE_NAME = "file_name"
    AUTO_NUMBER = "auto_number"
    CUSTOM = "custom"

# === Auto Numbering Defaults ===
DEFAULT_NUMBER_START = 1
DEFAULT_NUMBER_STEP = 1
DEFAULT_NUMBER_PREFIX = ""
DEFAULT_NUMBER_SUFFIX = ""

# === File Naming Templates ===
DEFAULT_FILENAME_TEMPLATE = "{name}"            # e.g., original file name
DEFAULT_NUMBER_TEMPLATE = "Doc-{num:03d}"       # e.g., Doc-001

# === Merge & Page Number Settings ===
ENABLE_PAGE_NUMBER_AFTER_MERGE = True
MERGED_FILE_NAME = "merged_output.pdf"

# === Logging Settings ===
LOG_DIR = "logs"
LOG_FILE = "app.log"
LOG_LEVEL = "INFO"

# === UI Defaults ===
TABLE_COLUMNS = ["序号", "文件名", "大小 (MB)", "页数", "页眉内容"]
SUPPORTED_LANGUAGES = {
    "zh_CN": "简体中文",
    "en_US": "English"
}

# === UI Layout Parameters ===
UI_MARGIN = 12
UI_SPACING = 8

# === Font Fallbacks ===
FONT_FALLBACKS = {
    "zh_CN": ["SimSun", "Microsoft YaHei", "PingFang SC"],
    "en_US": ["Arial", "Times New Roman", "Helvetica"]
}

# === Header Scanner Defaults ===
MAX_PREVIEW_PAGES = 3
HEADER_SCAN_Y_THRESHOLD = 820  # Y <= 820 pt considered header

# === Preset Config Keys ===
PRESET_KEYS = [
    "font_name",
    "font_size",
    "header_y",
    "footer_y",
    "header_mode",
    "output_dir",
    "number_start",
    "number_step",
    "number_prefix",
    "number_suffix",
    "language"
]

import os
import json
import logging

CONFIG_FILE_NAME = ".docdeck_config.json"
CONFIG_DIR = os.path.expanduser("~/.docdeck")
CONFIG_PATH = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)

def save_settings(settings: dict):
    """保存用户设置到配置文件"""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.getLogger(__name__).error("配置保存失败", exc_info=True)

def load_settings() -> dict:
    """从配置文件加载用户设置"""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.getLogger(__name__).error("配置加载失败", exc_info=True)
    return {}


# === Settings Defaults & Compatibility ===
def apply_defaults(settings: dict) -> dict:
    """确保配置包含所有默认值（适用于旧版配置文件）"""
    defaults = {
        "font_name": DEFAULT_FONT_NAME,
        "font_size": DEFAULT_FONT_SIZE,
        "header_y": DEFAULT_HEADER_Y,
        "footer_y": DEFAULT_FOOTER_Y,
        "header_mode": HeaderMode.FILE_NAME.value,
        "output_dir": DEFAULT_OUTPUT_DIR_NAME,
        "number_start": DEFAULT_NUMBER_START,
        "number_step": DEFAULT_NUMBER_STEP,
        "number_prefix": DEFAULT_NUMBER_PREFIX,
        "number_suffix": DEFAULT_NUMBER_SUFFIX,
        "language": DEFAULT_LANGUAGE,
    }
    for key, value in defaults.items():
        if key not in settings:
            settings[key] = value
        else:
            if key in ["font_size", "header_y", "footer_y", "number_start", "number_step"]:
                try:
                    settings[key] = int(settings[key])
                except Exception:
                    settings[key] = value
    return settings
