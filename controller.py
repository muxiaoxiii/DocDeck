import os
from pdf_unlocker import unlock_pdf
from file_namer import get_unique_filename
import os
from typing import List
from models import PDFFileItem, PDFProcessResult
from folder_importer import filter_pdf_files
from pdf_utils import get_pdf_file_size_mb, get_pdf_page_count
from pdf_handler import process_pdfs_in_batch
from logger import logger
from font_manager import get_recommended_fonts


class ProcessingController:
    def __init__(self, view=None):
        self.view = view
        self._recommended_fonts = []

    def handle_file_import(self, paths: List[str]) -> List[PDFFileItem]:
        pdf_paths = filter_pdf_files(paths)
        file_items = []
        for path in pdf_paths:
            try:
                name = os.path.basename(path)
                size = get_pdf_file_size_mb(path)
                page_count = get_pdf_page_count(path)
                file_items.append(PDFFileItem(
                    path=path,
                    name=name,
                    size_mb=size,
                    page_count=page_count,
                    header_text=name,
                    footer_text="",  # 默认空
                    footer_font="Helvetica",
                    footer_font_size=9,
                    footer_x=72,
                    footer_y=30
                ))
            except Exception as e:
                logger.error(f"Error loading file: {path} - {e}", exc_info=True)
        if file_items:
            self._recommended_fonts = get_recommended_fonts(pdf_paths)
            logger.debug(f"Recommended fonts: {self._recommended_fonts}")
        return file_items

    def handle_batch_process(
        self,
        file_items: List[PDFFileItem],
        output_dir: str,
        header_settings: dict,
        footer_settings: dict,
        signals=None
    ) -> List[PDFProcessResult]:
        logger.info(f"Start batch processing: {len(file_items)} files")
        for item in file_items:
            item.footer_text = footer_settings.get("text", "")
            item.footer_font = item.footer_font or footer_settings.get("font_name", "Helvetica")
            item.footer_font_size = item.footer_font_size or footer_settings.get("font_size", 9)
            item.footer_x = item.footer_x or footer_settings.get("x", 72)
            item.footer_y = item.footer_y or footer_settings.get("y", 30)
        results = process_pdfs_in_batch(
            file_infos=file_items,
            output_dir=output_dir,
            header_settings=header_settings,
            footer_settings=footer_settings,
            signals=signals
        )
        for result in results:
            if not result["success"]:
                logger.error(f"Failed to process file: {result['input']} | Reason: {result['error']}")
        return results

    def handle_cli_batch_process(
        self,
        source_dir: str,
        output_dir: str,
        font_name: str = "Helvetica",
        font_size: int = 12,
        x: int = 72,
        y: int = 800,
        footer_text: str = "",
        footer_font_name: str = "Helvetica",
        footer_font_size: int = 9,
        footer_x: int = 72,
        footer_y: int = 30
    ) -> List[PDFProcessResult]:
        if not os.path.isdir(source_dir):
            logger.error(f"Invalid source directory: {source_dir}")
            return []
        if not os.path.isdir(output_dir):
            logger.error(f"Invalid output directory: {output_dir}")
            return []
        all_paths = [os.path.join(source_dir, f) for f in os.listdir(source_dir)]
        file_items = self.handle_file_import(all_paths)
        return self.handle_batch_process(
            file_items=file_items,
            output_dir=output_dir,
            header_settings={
                "font_name": font_name,
                "font_size": font_size,
                "x": x,
                "y": y
            },
            footer_settings={
                "font_name": footer_font_name,
                "font_size": footer_font_size,
                "x": footer_x,
                "y": footer_y,
                "text": footer_text
            }
        )

    def apply_header_mode(
        self,
        file_items: List[PDFFileItem],
        mode: str,
        numbering_prefix: str = "Doc-",
        numbering_start: int = 1,
        numbering_step: int = 1,
        numbering_suffix: str = ""
    ) -> None:
        if mode == "filename":
            for item in file_items:
                item.header_text = item.name
        elif mode == "auto_number":
            for i, item in enumerate(file_items):
                number = numbering_start + i * numbering_step
                item.header_text = f"{numbering_prefix}{number:03d}{numbering_suffix}"
        elif mode == "custom":
            # Keep existing header_text values as-is
            pass
        else:
            logger.warning(f"Unknown header mode: {mode}")

    def get_recommended_fonts_cached(self) -> List[str]:
        return self._recommended_fonts

    def handle_unlock_pdf(self, item: PDFFileItem, password: str, output_dir: str) -> dict:
        """Controller 解锁入口，接收所有上下文信息。"""
        try:
            if not output_dir or not os.path.isdir(output_dir):
                logger.warning(f"无效的输出目录 '{output_dir}'，使用当前工作目录代替。")
                output_dir = os.getcwd()

            filename = item.name
            base_name = os.path.splitext(filename)[0]
            output_path = get_unique_filename(output_dir, f"{base_name}_unlocked.pdf")

            result = unlock_pdf(item.path, output_path, password)
            return result
        except Exception as e:
            logger.error(f"Unlock failed for {item.path}: {e}", exc_info=True)
            return {"success": False, "message": str(e), "method": "异常", "output_path": None}