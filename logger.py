# logger.py
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(log_dir="logs", log_file="app.log", level=logging.INFO, debug=False):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    debug = debug or os.getenv("DOCDECK_DEBUG", "0") == "1"

    logger = logging.getLogger("DocDeck")
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.setLevel(logging.DEBUG if debug else level)
    logger.propagate = False

    # 主日志文件 - 使用轮转日志
    fh = RotatingFileHandler(os.path.join(log_dir, log_file), maxBytes=5 * 1024 * 1024, backupCount=3)
    fh.setLevel(logging.DEBUG if debug else level)

    # 错误日志文件 - 使用轮转日志
    eh = RotatingFileHandler(os.path.join(log_dir, "error.log"), maxBytes=2 * 1024 * 1024, backupCount=2)
    eh.setLevel(logging.ERROR)

    # 控制台
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    fh.setFormatter(formatter)
    eh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(eh)
    logger.addHandler(ch)

    # 初始化信息记录
    import platform
    logger.info(f"DocDeck logger initialized")
    logger.info(f"Python version: {platform.python_version()}")
    logger.info(f"Platform: {platform.platform()}")

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

def log_exception(msg: str, exc: Exception):
    logger.error(f"{msg}: {str(exc)}", exc_info=True)