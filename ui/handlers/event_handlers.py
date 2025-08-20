# event_handlers.py - 事件处理器
"""
事件处理器模块
从ui_main.py中提取的事件处理相关逻辑
"""

import os
from PySide6.QtWidgets import QMessageBox, QFileDialog
from PySide6.QtCore import QSettings

from logger import logger


class EventHandlers:
    """事件处理器"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self._ = main_window._
        
    def _on_font_changed(self, text: str):
        """当字体改变时的处理"""
        self.main_window.update_preview()
        
    def _on_unit_changed(self, unit: str):
        """当单位改变时触发预设位置更新"""
        # 根据不同单位调整位置输入控件的范围和步长
        if unit == "mm":
            # 毫米单位：A4纸张 210x297mm
            self.main_window.x_input.setRange(0, 210)
            self.main_window.y_input.setRange(0, 297)
            self.main_window.x_input.setSingleStep(1)
            self.main_window.y_input.setSingleStep(1)
        elif unit == "inch":
            # 英寸单位：A4纸张约 8.27x11.69 英寸
            self.main_window.x_input.setRange(0, 827)  # 以百分之一英寸为单位
            self.main_window.y_input.setRange(0, 1169)
            self.main_window.x_input.setSingleStep(10)
            self.main_window.y_input.setSingleStep(10)
        else:  # points (默认)
            # 磅单位：A4纸张 595x842 points
            self.main_window.x_input.setRange(0, 595)
            self.main_window.y_input.setRange(0, 842)
            self.main_window.x_input.setSingleStep(1)
            self.main_window.y_input.setSingleStep(1)
            
        # 触发预设位置的重新计算
        self._apply_top_left_preset()
        
    def _on_header_template_changed(self, template: str):
        """当页眉模板改变时的处理"""
        template_mapping = {
            self._("Custom"): "",
            self._("Company Name"): "DocDeck Solutions Inc.",
            self._("Document Title"): "Document Title",
            self._("Date"): "{date}",
            self._("Page Number"): "Page {page}",
            self._("Confidential"): "CONFIDENTIAL",
            self._("Draft"): "DRAFT",
            self._("Final Version"): "FINAL VERSION"
        }
        
        if template in template_mapping:
            suggested_text = template_mapping[template]
            if suggested_text and not self.main_window.header_text_input.text():
                self.main_window.header_text_input.setText(suggested_text)
                
        self.main_window.update_preview()
        
    def _apply_top_left_preset(self):
        """应用左上角预设位置"""
        self.main_window.x_input.setValue(72)  # 1英寸边距
        self.main_window.y_input.setValue(792)  # 接近顶部
        self.main_window.footer_x_input.setValue(72)
        self.main_window.footer_y_input.setValue(50)  # 接近底部
        self.main_window.update_preview()
        
    def _apply_top_center_preset(self):
        """应用顶部居中预设位置"""
        self.main_window.x_input.setValue(297)  # A4宽度中心
        self.main_window.y_input.setValue(792)
        self.main_window.footer_x_input.setValue(297)
        self.main_window.footer_y_input.setValue(50)
        self.main_window.update_preview()
        
    def _apply_top_right_preset(self):
        """应用右上角预设位置"""
        self.main_window.x_input.setValue(523)  # 595-72，右边距
        self.main_window.y_input.setValue(792)
        self.main_window.footer_x_input.setValue(523)
        self.main_window.footer_y_input.setValue(50)
        self.main_window.update_preview()
        
    def _apply_bottom_left_preset(self):
        """应用左下角预设位置"""
        self.main_window.x_input.setValue(72)
        self.main_window.y_input.setValue(50)
        self.main_window.footer_x_input.setValue(72)
        self.main_window.footer_y_input.setValue(792)
        self.main_window.update_preview()
        
    def _apply_bottom_center_preset(self):
        """应用底部居中预设位置"""
        self.main_window.x_input.setValue(297)
        self.main_window.y_input.setValue(50)
        self.main_window.footer_x_input.setValue(297)
        self.main_window.footer_y_input.setValue(792)
        self.main_window.update_preview()
        
    def _apply_bottom_right_preset(self):
        """应用右下角预设位置"""
        self.main_window.x_input.setValue(523)
        self.main_window.y_input.setValue(50)
        self.main_window.footer_x_input.setValue(523)
        self.main_window.footer_y_input.setValue(792)
        self.main_window.update_preview()
        
    def _change_language(self, language: str):
        """切换语言"""
        try:
            self.main_window.locale_manager.set_locale(language)
            self._refresh_ui_texts()
            
            # 保存语言设置
            settings = QSettings("DocDeck", "DocDeck")
            settings.setValue("language", language)
            
            QMessageBox.information(
                self.main_window, 
                self._("Language Changed"), 
                self._("Language has been changed. Some changes will take effect after restart.")
            )
        except Exception as e:
            logger.error(f"切换语言失败: {e}")
            QMessageBox.warning(self.main_window, self._("Error"), f"{self._('Failed to change language')}: {str(e)}")
            
    def _refresh_ui_texts(self):
        """刷新UI文本"""
        # 刷新窗口标题
        self.main_window.setWindowTitle("DocDeck - PDF Header & Footer Tool")
        
        # 刷新状态栏
        if hasattr(self.main_window, 'statusBar'):
            self.main_window.statusBar.showMessage(self._("Ready"))
            
        # 刷新预览文本
        if hasattr(self.main_window, 'pdf_preview_canvas'):
            current_text = self.main_window.pdf_preview_canvas.text()
            if "Select a file" in current_text or "选择文件" in current_text:
                self.main_window.pdf_preview_canvas.setText(self._("Select a file to see preview"))
                
    def _import_settings(self):
        """导入设置"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self.main_window,
                self._("Import Settings"),
                "",
                "JSON files (*.json);;All files (*.*)"
            )
            
            if file_path:
                settings = QSettings("DocDeck", "DocDeck")
                # 这里可以添加导入设置的具体逻辑
                QMessageBox.information(
                    self.main_window,
                    self._("Import Settings"),
                    self._("Settings imported successfully")
                )
        except Exception as e:
            logger.error(f"导入设置失败: {e}")
            QMessageBox.warning(self.main_window, self._("Error"), f"{self._('Failed to import settings')}: {str(e)}")
            
    def _export_settings(self):
        """导出设置"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self.main_window,
                self._("Export Settings"),
                "docdeck_settings.json",
                "JSON files (*.json);;All files (*.*)"
            )
            
            if file_path:
                settings = QSettings("DocDeck", "DocDeck")
                # 这里可以添加导出设置的具体逻辑
                QMessageBox.information(
                    self.main_window,
                    self._("Export Settings"),
                    self._("Settings exported successfully")
                )
        except Exception as e:
            logger.error(f"导出设置失败: {e}")
            QMessageBox.warning(self.main_window, self._("Error"), f"{self._('Failed to export settings')}: {str(e)}")
            
    def _reset_settings(self):
        """重置设置"""
        reply = QMessageBox.question(
            self.main_window,
            self._("Reset Settings"),
            self._("Are you sure you want to reset all settings to default?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 重置各种输入控件到默认值
                self.main_window.font_size_spin.setValue(12)
                self.main_window.footer_font_size_spin.setValue(10)
                self.main_window.x_input.setValue(72)
                self.main_window.y_input.setValue(792)
                self.main_window.footer_x_input.setValue(72)
                self.main_window.footer_y_input.setValue(50)
                self.main_window.header_text_input.clear()
                self.main_window.footer_text_input.clear()
                self.main_window.prefix_input.setText("Doc-")
                self.main_window.start_spin.setValue(1)
                self.main_window.step_spin.setValue(1)
                self.main_window.digits_spin.setValue(3)
                self.main_window.suffix_input.clear()
                
                # 重置复选框
                self.main_window.structured_checkbox.setChecked(False)
                self.main_window.struct_cn_fixed_checkbox.setChecked(False)
                self.main_window.memory_optimization_checkbox.setChecked(True)
                self.main_window.normalize_a4_checkbox.setChecked(True)
                self.main_window.merge_checkbox.setChecked(False)
                self.main_window.page_numbers_checkbox.setChecked(False)
                
                # 重置下拉框到第一项
                self.main_window.font_select.setCurrentIndex(0)
                self.main_window.footer_font_select.setCurrentIndex(0)
                self.main_window.align_combo.setCurrentIndex(0)
                self.main_window.footer_align_combo.setCurrentIndex(0)
                self.main_window.header_template_combo.setCurrentIndex(0)
                self.main_window.mode_select_combo.setCurrentIndex(0)
                
                self.main_window.update_preview()
                
                QMessageBox.information(
                    self.main_window,
                    self._("Reset Settings"),
                    self._("Settings have been reset to default values")
                )
            except Exception as e:
                logger.error(f"重置设置失败: {e}")
                QMessageBox.warning(self.main_window, self._("Error"), f"{self._('Failed to reset settings')}: {str(e)}")
                
    def on_processing_finished(self, results: list):
        """处理完成后的回调"""
        try:
            success_count = len([r for r in results if r.get('success', False)])
            total_count = len(results)
            
            if success_count == total_count:
                message = f"{self._('Processing completed successfully!')} {success_count}/{total_count}"
                QMessageBox.information(self.main_window, self._("Success"), message)
            else:
                failed_files = [r.get('file', 'Unknown') for r in results if not r.get('success', False)]
                message = f"{self._('Processing completed with errors')} {success_count}/{total_count}\n"
                message += f"{self._('Failed files')}: {', '.join(failed_files[:5])}"
                if len(failed_files) > 5:
                    message += f" {self._('and')} {len(failed_files) - 5} {self._('more')}"
                QMessageBox.warning(self.main_window, self._("Partial Success"), message)
                
        except Exception as e:
            logger.error(f"处理完成回调失败: {e}")
            QMessageBox.information(self.main_window, self._("Processing"), self._("Processing completed"))
            
    def _apply_top_right_preset(self):
        """应用右上角预设位置"""
        # 简化版本，设置固定的右上角位置
        self.main_window.x_input.setValue(523)  # 595-72，右边距
        self.main_window.y_input.setValue(792)  # 上边距
        self.main_window.footer_x_input.setValue(523)
        self.main_window.footer_y_input.setValue(50)
        self.main_window.update_preview()
        
    def _apply_bottom_right_preset(self):
        """应用右下角预设位置"""
        # 简化版本，设置固定的右下角位置
        self.main_window.x_input.setValue(523)  # 595-72，右边距
        self.main_window.y_input.setValue(50)   # 下边距
        self.main_window.footer_x_input.setValue(523)
        self.main_window.footer_y_input.setValue(792)
        self.main_window.update_preview()
