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

# 新增：错误处理和统计功能
class ErrorTracker:
    """错误追踪和统计"""
    
    def __init__(self):
        self.error_count = 0
        self.warning_count = 0
        self.error_types = {}
        self.warning_types = {}
    
    def track_error(self, error_type: str, message: str, exception: Optional[Exception] = None):
        """追踪错误"""
        self.error_count += 1
        if error_type not in self.error_types:
            self.error_types[error_type] = 0
        self.error_types[error_type] += 1
        
        if exception:
            logger.error(f"[{error_type}] {message}", exc_info=True)
        else:
            logger.error(f"[{error_type}] {message}")
    
    def track_warning(self, warning_type: str, message: str):
        """追踪警告"""
        self.warning_count += 1
        if warning_type not in self.warning_types:
            self.warning_types[warning_type] = 0
        self.warning_types[warning_type] += 1
        
        logger.warning(f"[{warning_type}] {message}")
    
    def get_summary(self) -> dict:
        """获取错误统计摘要"""
        return {
            'total_errors': self.error_count,
            'total_warnings': self.warning_count,
            'error_types': self.error_types.copy(),
            'warning_types': self.warning_types.copy()
        }
    
    def reset(self):
        """重置统计"""
        self.error_count = 0
        self.warning_count = 0
        self.error_types.clear()
        self.warning_types.clear()

# 全局错误追踪器
error_tracker = ErrorTracker()

def track_error(error_type: str, message: str, exception: Optional[Exception] = None):
    """便捷的错误追踪函数"""
    error_tracker.track_error(error_type, message, exception)

def track_warning(warning_type: str, message: str):
    """便捷的警告追踪函数"""
    error_tracker.track_warning(warning_type, message)

def get_error_summary() -> dict:
    """获取错误统计摘要"""
    return error_tracker.get_summary()

def reset_error_tracking():
    """重置错误统计"""
    error_tracker.reset()

# 性能监控功能
import time
from functools import wraps

def log_performance(operation: str, context: str = ""):
    """性能日志装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"性能 [{context}]: {operation} 耗时 {duration:.3f}秒")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"性能 [{context}]: {operation} 失败，耗时 {duration:.3f}秒，错误: {e}")
                raise
        return wrapper
    return decorator

def log_user_action(action: str, details: str = "", context: str = ""):
    """记录用户操作"""
    try:
        logger.info(f"用户操作 [{context}]: {action} - {details}")
    except Exception as e:
        print(f"用户操作日志记录失败: {e}")

def log_system_event(event: str, details: str = "", context: str = ""):
    """记录系统事件"""
    try:
        logger.info(f"系统事件 [{context}]: {event} - {details}")
    except Exception as e:
        print(f"系统事件日志记录失败: {e}")

# 安全执行函数
def safe_execute(func, *args, context: str = "", fallback=None, **kwargs):
    """安全执行函数，自动处理异常"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        track_error("SafeExecute", f"执行失败 [{context}]: {e}", e)
        if fallback:
            try:
                return fallback(*args, **kwargs)
            except Exception as fallback_error:
                track_error("SafeExecute", f"Fallback执行失败 [{context}]: {fallback_error}", fallback_error)
        return None

def safe_execute_with_retry(func, max_retries: int = 3, *args, context: str = "", **kwargs):
    """带重试的安全执行"""
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            logger.warning(f"执行失败，尝试 {attempt + 1}/{max_retries}: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(0.5 * (attempt + 1))
    
    # 所有重试都失败了
    track_error("SafeExecuteRetry", f"重试{max_retries}次后失败 [{context}]: {last_error}", last_error)
    return None