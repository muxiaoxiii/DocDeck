# locale_manager.py - 语言管理器
"""
语言管理器模块
负责系统语言检测和翻译文本获取
"""

import locale
from typing import Dict, Any
from .translations import TRANSLATIONS


class LocaleManager:
    """语言管理器"""
    
    def __init__(self):
        self.current_locale = self._detect_system_language()
        self.translations = TRANSLATIONS
    
    def _detect_system_language(self) -> str:
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
    
    def _(self, text: str) -> str:
        """获取本地化文本"""
        return self.translations.get(self.current_locale, {}).get(text, text)
    
    def set_locale(self, locale_code: str):
        """设置语言"""
        if locale_code in self.translations:
            self.current_locale = locale_code
    
    def get_current_locale(self) -> str:
        """获取当前语言"""
        return self.current_locale
    
    def get_available_locales(self) -> list:
        """获取可用语言列表"""
        return list(self.translations.keys())


# 全局实例（单例模式）
_locale_manager_instance = None

def get_locale_manager() -> LocaleManager:
    """获取语言管理器单例"""
    global _locale_manager_instance
    if _locale_manager_instance is None:
        _locale_manager_instance = LocaleManager()
    return _locale_manager_instance

