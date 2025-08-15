# main.py
import sys
import os
import argparse
from PySide6.QtWidgets import QApplication
from ui_main import MainWindow
from logger import logger
from controller import ProcessingController
from models import PDFFileItem


def main():
    parser = argparse.ArgumentParser(description="DocDeck PDF Processor")
    parser.add_argument("--source", help="Source folder or PDF files", nargs="+")
    parser.add_argument("--output", help="Output directory")
    # options
    parser.add_argument("--structured", action="store_true", help="Enable Acrobat-friendly structured headers/footers")
    parser.add_argument("--normalize-a4", action="store_true", help="Normalize pages to A4 before processing")
    parser.add_argument("--header-font", help="Header font name")
    parser.add_argument("--header-size", type=int, help="Header font size (pt)")
    parser.add_argument("--header-x", type=int, help="Header X position (pt)")
    parser.add_argument("--header-y", type=int, help="Header Y position (pt)")
    parser.add_argument("--footer-font", help="Footer font name")
    parser.add_argument("--footer-size", type=int, help="Footer font size (pt)")
    parser.add_argument("--footer-x", type=int, help="Footer X position (pt)")
    parser.add_argument("--footer-y", type=int, help="Footer Y position (pt)")
    parser.add_argument("--structured-cn-fixed", action="store_true", help="Use fixed font for structured Chinese")
    parser.add_argument("--structured-cn-font", help="Fixed font name for structured Chinese")
    parser.add_argument("--merge", action="store_true", help="Merge processed outputs")
    parser.add_argument("--add-page-numbers", action="store_true", help="Add page numbers to merged PDF")

    args = parser.parse_args()

    if args.source and args.output:
        logger.info("命令行批量处理启动")
        controller = ProcessingController(None)  # no GUI
        # Build settings
        header_settings = {}
        footer_settings = {}
        if args.structured:
            header_settings["structured"] = True
            footer_settings["structured"] = True
        if args.normalize_a4:
            header_settings["normalize_a4"] = True
            footer_settings["normalize_a4"] = True
        if args.header_font: header_settings["font_name"] = args.header_font
        if args.header_size: header_settings["font_size"] = args.header_size
        if args.header_x: header_settings["x"] = args.header_x
        if args.header_y: header_settings["y"] = args.header_y
        if args.footer_font: footer_settings["font_name"] = args.footer_font
        if args.footer_size: footer_settings["font_size"] = args.footer_size
        if args.footer_x: footer_settings["x"] = args.footer_x
        if args.footer_y: footer_settings["y"] = args.footer_y
        if args.structured_cn_fixed:
            header_settings["structured_cn_fixed"] = True
            footer_settings["structured_cn_fixed"] = True
        if args.structured_cn_font:
            header_settings["structured_cn_font"] = args.structured_cn_font
            footer_settings["structured_cn_font"] = args.structured_cn_font
        # 处理源文件列表
        file_items = []
        for source_path in args.source:
            if os.path.isfile(source_path) and source_path.lower().endswith('.pdf'):
                file_items.append(PDFFileItem(source_path))
            elif os.path.isdir(source_path):
                # 递归扫描目录
                for root, dirs, files in os.walk(source_path):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            file_path = os.path.join(root, file)
                            file_items.append(PDFFileItem(file_path))
        
        if not file_items:
            logger.error("未找到PDF文件")
            sys.exit(1)
            
        logger.info(f"找到 {len(file_items)} 个PDF文件")
        
        # 执行批处理
        results = controller.handle_batch_process(file_items, args.output, header_settings, footer_settings)
        
        # 如果启用合并，执行合并操作
        if args.merge and results:
            success_files = [r.get("output_path") for r in results if r.get("success") and r.get("output_path")]
            if success_files:
                try:
                    merge_output = os.path.join(args.output, "merged_output.pdf")
                    controller.merge_pdfs(success_files, merge_output, add_page_numbers=args.add_page_numbers)
                    logger.info(f"合并完成: {merge_output}")
                except Exception as e:
                    logger.error(f"合并失败: {e}")
        logger.info("批处理完成")
        sys.exit(0)
    else:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        logger.info("DocDeck 应用启动")
        sys.exit(app.exec())


if __name__ == "__main__":
    main()