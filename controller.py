import os
from typing import List, Tuple
from PySide6.QtCore import QObject, Signal, Slot
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

from models import PDFFileItem, PDFProcessResult, EncryptionStatus
from pdf_unlocker import unlock_pdf
from file_namer import get_unique_filename
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
                
                status = EncryptionStatus.OK
                page_count = 0
                try:
                    reader = PdfReader(path)
                    page_count = len(reader.pages)
                    if reader.is_encrypted:
                        if not reader.decrypt(""):
                            status = EncryptionStatus.LOCKED
                        else:
                            status = EncryptionStatus.RESTRICTED
                except PdfReadError:
                    status = EncryptionStatus.LOCKED
                except Exception:
                    status = EncryptionStatus.LOCKED

                file_item = PDFFileItem(
                    path=path,
                    name=name,
                    size_mb=size,
                    page_count=page_count,
                    header_text=name,
                    footer_text="",
                    encryption_status=status,
                    unlocked_path="",
                    footer_digit=3
                )
                file_items.append(file_item)
            except Exception as e:
                logger.error(f"Error loading file: {path} - {e}", exc_info=True)
        
        if file_items:
            self._recommended_fonts = get_recommended_fonts([item.path for item in file_items])
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
            if item.unlocked_path and os.path.exists(item.unlocked_path):
                item.path = item.unlocked_path

        results = process_pdfs_in_batch(
            file_infos=file_items,
            output_dir=output_dir,
            header_settings=header_settings,
            footer_settings=footer_settings,
            signals=signals
        )
        return results

    def apply_header_mode(
        self,
        file_items: List[PDFFileItem],
        mode: str,
        numbering_prefix: str = "Doc-",
        numbering_start: int = 1,
        numbering_step: int = 1,
        numbering_suffix: str = "",
        numbering_digits: int = 3
    ) -> None:
        if mode == "filename":
            for item in file_items:
                item.header_text = item.name
        elif mode == "auto_number":
            for i, item in enumerate(file_items):
                number = numbering_start + i * numbering_step
                item.header_text = f"{numbering_prefix}{number:0{numbering_digits}d}{numbering_suffix}"
        elif mode == "custom":
            pass
        else:
            logger.warning(f"Unknown header mode: {mode}")

    def get_recommended_fonts_cached(self, file_items: List[str] = None) -> List[str]:
        return self._recommended_fonts

    def handle_unlock_pdf(self, item: PDFFileItem, password: str, output_dir: str) -> dict:
        try:
            if not output_dir or not os.path.isdir(output_dir):
                output_dir = os.getcwd()

            base_name = os.path.splitext(item.name)[0]
            output_path = get_unique_filename(output_dir, f"{base_name}_unlocked.pdf")

            result = unlock_pdf(item.path, output_path, password)
            result["status"] = "SUCCESS" if result.get("success") else "FAILED"

            if result.get("success"):
                item.unlocked_path = result.get("output_path", output_path)
                item.path = item.unlocked_path  # Update for immediate downstream use
                result["updated_path"] = item.path

                try:
                    reader = PdfReader(item.unlocked_path)
                    item.page_count = len(reader.pages)
                    item.encryption_status = EncryptionStatus.OK
                except Exception as e:
                    logger.warning(f"Failed to re-parse unlocked file: {item.unlocked_path} - {e}")

            return result
        except Exception as e:
            logger.error(f"Unlock failed for {item.path}: {e}", exc_info=True)
            return {"success": False, "status": "ERROR", "message": str(e), "method": "Exception", "output_path": None}

class Worker(QObject):
    signals = Signal(list)

    def __init__(self, controller, file_items, output_dir, header_settings, footer_settings):
        super().__init__()
        self.controller = controller
        self.file_items = file_items
        self.output_dir = output_dir
        self.header_settings = header_settings
        self.footer_settings = footer_settings
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        results = self.controller.handle_batch_process(
            self.file_items,
            self.output_dir,
            self.header_settings,
            self.footer_settings,
            self.signals
        )
        self.signals.finished.emit(results)

class WorkerSignals(QObject):
    finished = Signal(list)
    progress = Signal(int, int, str)