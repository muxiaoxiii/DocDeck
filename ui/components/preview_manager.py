# preview_manager.py - 预览管理器
"""
预览管理器模块
从ui_main.py中提取的预览相关逻辑
"""

import os
from io import BytesIO
from typing import Optional
try:
    import fitz
except Exception:  # pragma: no cover
    fitz = None
import pikepdf
from PySide6.QtWidgets import QLabel, QGroupBox, QVBoxLayout
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QRect
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics

from geometry_context import build_geometry_context
from font_manager import register_font_safely
from logger import logger

class PreviewManager:
    """预览管理器 - 完整的预览功能实现"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self._ = main_window._
        # 基页渲染缓存：key = (path, page_num, normalize, scale)
        self._base_image_cache = {}
        
    def update_preview(self):
        """更新预览显示"""
        try:
            logger.debug("[Preview] update_preview called")
            logger.debug(f"[Preview] file_items count: {len(self.main_window.file_items)}")
            logger.debug(f"[Preview] current_row: {self.main_window.file_table.currentRow()}")
            
            # 获取当前选中的文件
            current_row = self.main_window.file_table.currentRow()
            if current_row < 0 or current_row >= len(self.main_window.file_items):
                logger.debug("[Preview] No valid row selected")
                return
                
            item = self.main_window.file_items[current_row]
            if not item or not item.path:
                logger.debug("[Preview] No valid item or path")
                return
                
            logger.debug(f"[Preview] Processing item: {item.path}")
            
            # 更新PDF内容预览
            self.update_pdf_content_preview()
            
        except Exception as e:
            logger.error(f"[Preview] Error in update_preview: {e}", exc_info=True)
            from logger import track_error
            track_error("PreviewUpdate", f"预览更新失败: {e}", e)
            
    def update_position_preview(self):
        """更新位置预览（已弃用）"""
        pass
        
    def update_header_position_preview(self):
        """更新页眉位置预览（已弃用）"""
        pass
        
    def update_footer_position_preview(self):
        """更新页脚位置预览（已弃用）"""
        pass
        
    def _render_text_overlay_for_preview(self, text: str, font_name: str, font_size: int, 
                                       page_width: float, page_height: float, x: float, y: float) -> Optional[QPixmap]:
        """使用ReportLab生成透明文本叠加层，然后用PyMuPDF渲染为QPixmap"""
        try:
            # 创建内存中的PDF
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
            
            # 注册字体
            ok = register_font_safely(font_name)
            try:
                if not ok:
                    # 字体注册失败，尝试中文回退字体或内置字体
                    from font_manager import suggest_chinese_fallback_font
                    fallback = suggest_chinese_fallback_font() or 'Helvetica'
                    register_font_safely(fallback)
                    c.setFont(fallback, font_size)
                else:
                    c.setFont(font_name, font_size)
            except Exception:
                # 最后的兜底
                c.setFont('Helvetica', font_size)
            
            # 绘制文本（ReportLab坐标系：左下角为原点）
            c.drawString(x, y, text)
            c.save()
            
            # 用PyMuPDF打开并渲染
            buffer.seek(0)
            pdf_doc = fitz.open("pdf", buffer.getvalue())
            page = pdf_doc[0]
            
            # 渲染为图像
            mat = fitz.Matrix(2, 2)  # 2倍缩放提高清晰度
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # 转换为QPixmap
            qimg = QImage.fromData(img_data)
            pixmap = QPixmap.fromImage(qimg)
            
            pdf_doc.close()
            return pixmap
            
        except Exception as e:
            logger.error(f"文本叠加渲染失败: {e}")
            return None

    def _render_text_layer(self,
                            header_text: str,
                            footer_text: str,
                            geom_context,
                            header_font_name: str,
                            header_font_size: int,
                            footer_font_name: str,
                            footer_font_size: int,
                            scale_factor: float) -> Optional[QPixmap]:
        """使用ReportLab渲染文本层（含中文字体注册），再用PyMuPDF渲染为透明位图。"""
        try:
            if not header_text.strip() and not footer_text.strip():
                return None
            # 构造PDF文本层
            buffer = BytesIO()
            from reportlab.pdfgen import canvas as rl_canvas
            c = rl_canvas.Canvas(buffer, pagesize=(geom_context.effective_page_width, geom_context.effective_page_height))

            # 注册并设置中文字体（页眉）
            ok = register_font_safely(header_font_name)
            if not ok:
                from font_manager import suggest_chinese_fallback_font
                header_font_name = suggest_chinese_fallback_font() or 'Helvetica'
                register_font_safely(header_font_name)

            # 注册并设置中文字体（页脚）
            ok2 = register_font_safely(footer_font_name)
            if not ok2:
                from font_manager import suggest_chinese_fallback_font
                footer_font_name = suggest_chinese_fallback_font() or 'Helvetica'
                register_font_safely(footer_font_name)

            # 翻转Y轴：ReportLab坐标为左下角
            # 同时注意：几何上下文的偏移在基页绘制中已体现；文本层保持“有效页面”坐标系
            if header_text.strip():
                c.setFont(header_font_name, max(1, int(header_font_size)))
                hx = float(self.main_window.x_input.value())
                hy = float(self.main_window.y_input.value())
                
                # 检查是否有对齐设置
                header_align = getattr(self.main_window, 'header_align_combo', None)
                if header_align is not None:
                    align = header_align.currentText().lower()
                    if align == 'center':
                        # 居中对齐
                        text_width = c.stringWidth(header_text, header_font_name, header_font_size)
                        page_width = geom_context.effective_page_width
                        hx = (page_width - text_width) / 2
                    elif align == 'right':
                        # 右对齐
                        text_width = c.stringWidth(header_text, header_font_name, header_font_size)
                        page_width = geom_context.effective_page_width
                        hx = page_width - text_width - hx  # 使用hx作为右边距
                
                c.drawString(hx, hy, header_text)

            if footer_text.strip():
                c.setFont(footer_font_name, max(1, int(footer_font_size)))
                fx = float(self.main_window.footer_x_input.value())
                fy = float(self.main_window.footer_y_input.value())
                
                # 检查是否有对齐设置
                footer_align = getattr(self.main_window, 'footer_align_combo', None)
                if footer_align is not None:
                    align = footer_align.currentText().lower()
                    if align == 'center':
                        # 居中对齐
                        text_width = c.stringWidth(footer_text, footer_font_name, footer_font_size)
                        page_width = geom_context.effective_page_width
                        fx = (page_width - text_width) / 2
                    elif align == 'right':
                        # 右对齐
                        text_width = c.stringWidth(footer_text, footer_font_name, footer_font_size)
                        page_width = geom_context.effective_page_width
                        fx = page_width - text_width - fx  # 使用fx作为右边距
                
                c.drawString(fx, fy, footer_text)

            c.save()
            buffer.seek(0)

            # 用 PyMuPDF 渲染为带透明通道的图像
            if fitz is None:
                return None
            doc = fitz.open("pdf", buffer.getvalue())
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(scale_factor, scale_factor), alpha=True)
            img_data = pix.tobytes("png")
            qimg = QImage.fromData(img_data)
            return QPixmap.fromImage(qimg)
        except Exception as e:
            logger.error(f"文本层渲染失败: {e}", exc_info=True)
            return None
            
    def update_pdf_content_preview(self):
        """更新PDF内容预览 - WYSIWYG风格，显示页眉+页脚条带"""
        if not self.main_window.file_items:
            self.main_window.pdf_preview_canvas.setText(self._("Select a file to see preview"))
            return
            
        # 获取当前选中的文件
        try:
            current_row = self.main_window.file_table.currentRow()
            if current_row < 0:
                current_row = 0
        except:
            current_row = 0
            
        if current_row >= len(self.main_window.file_items):
            self.main_window.pdf_preview_canvas.setText(self._("Invalid file selection"))
            return
            
        item = self.main_window.file_items[current_row]
        if not os.path.exists(item.path):
            self.main_window.pdf_preview_canvas.setText(self._("File not found"))
            return
        
        # 运行环境检查
        if fitz is None:
            self.main_window.pdf_preview_canvas.setText(self._("PyMuPDF (fitz) is not available"))
            return
            
        # 获取预览页码
        preview_page_num = self.main_window.preview_page_spin.value() - 1  # 转为0基
        
        pdf_for_geom = None
        doc = None
        try:
            # 需要同时用 pikepdf 获取几何信息，用 fitz 渲染
            # 对加密/受限PDF增加降级处理：pikepdf失败时，使用fitz尺寸近似构建几何
            try:
                pdf_for_geom = pikepdf.open(item.path)
            except Exception as ge:
                logger.warning(f"[Preview] pikepdf open failed for {item.path}: {ge}")
                pdf_for_geom = None
            doc = fitz.open(item.path)
            
            if not doc or doc.page_count == 0:
                self.main_window.pdf_preview_canvas.setText(self._("Cannot open or empty PDF"))
                return
                
            if preview_page_num >= doc.page_count:
                preview_page_num = 0
                self.main_window.preview_page_spin.setValue(1)
                
            # 更新页码范围
            self.main_window.preview_page_spin.setRange(1, doc.page_count)
            
            # 获取页面和几何上下文
            normalize = True
            try:
                if hasattr(self.main_window, 'normalize_a4_checkbox'):
                    normalize = bool(self.main_window.normalize_a4_checkbox.isChecked())
            except Exception:
                normalize = True

            if pdf_for_geom is not None:
                pikepdf_page = pdf_for_geom.pages[preview_page_num]
                geom_context = build_geometry_context(pikepdf_page, normalize_a4=normalize)
            else:
                # pikepdf 不可用时，基于fitz页面尺寸近似构建几何上下文（不规范化）
                page_rect = doc[preview_page_num].rect
                from geometry_context import GeometryContext
                geom_context = GeometryContext(
                    original_media_box=(0.0, 0.0, float(page_rect.width), float(page_rect.height)),
                    original_crop_box=None,
                    original_rotation=0,
                    effective_page_width=float(page_rect.width),
                    effective_page_height=float(page_rect.height),
                    transform_scale=1.0,
                    transform_offset_x=0.0,
                    transform_offset_y=0.0,
                )
            
            # 用fitz渲染基础页面（带缓存）
            fitz_page = doc[preview_page_num]
            scale_factor = 1.5
            cache_key = (item.path, preview_page_num, bool(geom_context.transform_scale != 1.0), scale_factor)
            base_qimg = self._base_image_cache.get(cache_key)
            if base_qimg is None:
                mat = fitz.Matrix(scale_factor, scale_factor)
                base_pix = fitz_page.get_pixmap(matrix=mat)
                base_img_data = base_pix.tobytes("png")
                base_qimg = QImage.fromData(base_img_data)
                self._base_image_cache[cache_key] = base_qimg
            
            # 创建合成画布（原始大小 * scale_factor）
            canvas_width = int(geom_context.effective_page_width * scale_factor)
            canvas_height = int(geom_context.effective_page_height * scale_factor)
            canvas_img = QImage(canvas_width, canvas_height, QImage.Format_ARGB32)
            canvas_img.fill(Qt.white)
            
            painter = QPainter(canvas_img)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 应用A4变换并绘制基础图像
            if geom_context.transform_scale != 1.0:
                # 计算变换后的位置和大小
                scaled_width = int(base_qimg.width() * geom_context.transform_scale)
                scaled_height = int(base_qimg.height() * geom_context.transform_scale)
                offset_x = int(geom_context.transform_offset_x * scale_factor)
                offset_y = int(geom_context.transform_offset_y * scale_factor)
                
                # 绘制缩放和偏移后的图像
                scaled_base = base_qimg.scaled(scaled_width, scaled_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawImage(offset_x, offset_y, scaled_base)
            else:
                # 直接绘制
                painter.drawImage(0, 0, base_qimg)
                
            # 获取页眉页脚文本和设置
            header_text = self._get_header_text_for_item(item)
            footer_text = self._get_footer_text_for_item(item)
            
            # 根据模式决定是否渲染“新文本层”与“原有Artifact层”
            # 逐文件模式取自 file_items[row].preview_mode
            per_file_mode = 'keep'
            try:
                per_file_mode = self.main_window.file_items[current_row].preview_mode
            except Exception:
                pass
            mode_text = self._("替换") if per_file_mode == 'replace' else self._("保留")
            overlay_compare = bool(getattr(self.main_window, 'overlay_compare_checkbox', None) and self.main_window.overlay_compare_checkbox.isChecked())

            # 新文本层（替换模式或叠加对比开启时渲染）
            header_font_name = self.main_window.font_select.currentText()
            header_font_size = self.main_window.font_size_spin.value()
            footer_font_name = self.main_window.footer_font_select.currentText()
            footer_font_size = self.main_window.footer_font_size_spin.value()
            # 当 header/footer 文本或位置存在时，才绘制新层；避免空白阻挡误判
            should_draw_new = bool(header_text.strip() or footer_text.strip())
            if should_draw_new and (mode_text in (self._("替换"),) or (overlay_compare and mode_text == self._("保留"))):
                text_layer_pix = self._render_text_layer(
                    header_text=header_text,
                    footer_text=footer_text,
                    geom_context=geom_context,
                    header_font_name=header_font_name,
                    header_font_size=header_font_size,
                    footer_font_name=footer_font_name,
                    footer_font_size=footer_font_size,
                    scale_factor=scale_factor,
                )
                if text_layer_pix is not None:
                    painter.drawPixmap(0, 0, text_layer_pix)
                        
            painter.end()
            
            # 提取页眉和页脚条带区域
            strip_height = 80  # 每个条带的高度
            header_strip_rect = QRect(0, 0, canvas_width, strip_height)
            footer_strip_rect = QRect(0, canvas_height - strip_height, canvas_width, strip_height)
            
            # 创建最终预览图像（两个条带拼接）
            final_height = strip_height * 2 + 10  # 两个条带 + 间隔
            final_img = QImage(canvas_width, final_height, QImage.Format_ARGB32)
            final_img.fill(Qt.white)
            
            final_painter = QPainter(final_img)
            
            # 绘制页眉条带
            header_strip = canvas_img.copy(header_strip_rect)
            final_painter.drawImage(0, 0, header_strip)
            
            # 绘制分隔线
            final_painter.setPen(QColor(200, 200, 200))
            final_painter.drawLine(0, strip_height + 5, canvas_width, strip_height + 5)
            
            # 绘制页脚条带
            footer_strip = canvas_img.copy(footer_strip_rect)
            final_painter.drawImage(0, strip_height + 10, footer_strip)
            
            final_painter.end()
            
            # 设置到预览画布
            final_pixmap = QPixmap.fromImage(final_img)
            self.main_window.pdf_preview_canvas.setPixmap(final_pixmap)
            
        except Exception as e:
            logger.error(f"预览更新失败: {e}", exc_info=True)
            self.main_window.pdf_preview_canvas.setText(f"{self._('Preview error')}: {str(e)}")
        finally:
            if pdf_for_geom:
                pdf_for_geom.close()
            if doc:
                doc.close()
                
    def _get_header_text_for_item(self, item) -> str:
        """获取项目的页眉文本"""
        # 优先使用表格中的文本
        current_row = self.main_window.file_table.currentRow()
        if current_row >= 0 and current_row < self.main_window.file_table.rowCount():
            header_item = self.main_window.file_table.item(current_row, 6)
            if header_item and header_item.text().strip():
                return header_item.text()
        
        # 其次使用 item 中的文本
        if hasattr(item, 'header_text') and item.header_text:
            return item.header_text
        
        # 根据模式生成默认文本
        mode = self.main_window.mode_select_combo.currentIndex()
        if mode == 0:  # 文件名模式
            # 去掉扩展名
            filename = os.path.splitext(os.path.basename(item.path))[0]
            return filename
        elif mode == 1:  # 自动编号模式
            prefix = self.main_window.prefix_input.text()
            start = self.main_window.start_spin.value()
            step = self.main_window.step_spin.value()
            digits = self.main_window.digits_spin.value()
            suffix = self.main_window.suffix_input.text()
            
            # 计算当前项目的编号
            index = self.main_window.file_items.index(item)
            number = start + index * step
            number_str = str(number).zfill(digits)
            
            return f"{prefix}{number_str}{suffix}"
        else:  # 自定义模式
            return self.main_window.header_text_input.text()
            
    def _get_footer_text_for_item(self, item) -> str:
        """获取项目的页脚文本"""
        # 优先使用表格中的文本
        current_row = self.main_window.file_table.currentRow()
        if current_row >= 0 and current_row < self.main_window.file_table.rowCount():
            footer_item = self.main_window.file_table.item(current_row, 7)
            if footer_item and footer_item.text().strip():
                return footer_item.text()
        
        # 其次使用 item 中的文本
        if hasattr(item, 'footer_text') and item.footer_text:
            return item.footer_text
        
        # 使用全局页脚文本
        # 采用主窗体的全局页脚模板输入框（与UI一致）
        footer_template = getattr(self.main_window, 'global_footer_text', None)
        footer_template = footer_template.text() if footer_template is not None else ""
        if not footer_template:
            return ""
            
        # 替换占位符（这里简化处理，实际应用中可能需要更复杂的逻辑）
        result = footer_template.replace("{page}", "1").replace("{total}", "1")
        return result
        
    def _draw_simulated_preview(self, painter: QPainter, settings: dict, header_text: str, footer_text: str):
        """绘制模拟预览（已弃用的方法，保持兼容性）"""
        pass
