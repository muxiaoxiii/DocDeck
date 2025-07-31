# main.py
import sys
import argparse
import os
from PySide6.QtWidgets import QApplication
from ui_main import MainWindow
from logger import logger
from controller import ProcessingController

def main():
    parser = argparse.ArgumentParser(description="DocDeck PDF Processor")
    parser.add_argument("--source", help="Source folder or PDF files", nargs="+")
    parser.add_argument("--output", help="Output directory")
    args = parser.parse_args()

    if args.source and args.output:
        logger.info("命令行批量处理启动")
        controller = ProcessingController(None)  # no GUI
        controller.handle_cli_batch_process(args.source, args.output)
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