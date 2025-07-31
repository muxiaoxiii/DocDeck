# logger.py
import logging
import os

def setup_logger(log_dir="logs", log_file="app.log", level=logging.INFO, debug=False):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger("DocDeck")
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.setLevel(logging.DEBUG if debug else level)
    logger.propagate = False

    # 主日志文件
    fh = logging.FileHandler(os.path.join(log_dir, log_file), encoding="utf-8")
    fh.setLevel(logging.DEBUG if debug else level)

    # 错误日志文件
    eh = logging.FileHandler(os.path.join(log_dir, "error.log"), encoding="utf-8")
    eh.setLevel(logging.ERROR)

    # 控制台
    ch = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    fh.setFormatter(formatter)
    eh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(eh)
    logger.addHandler(ch)
    return logger

logger = setup_logger(debug=False)


# 统一错误日志和状态栏提示
from typing import Optional

def log_and_display_error(message: str, exception: Optional[Exception] = None):
    full_msg = f"{message}"
    if exception:
        logger.error(full_msg, exc_info=True)
    else:
        logger.error(full_msg)
    return full_msg  # 供 UI 状态栏等调用