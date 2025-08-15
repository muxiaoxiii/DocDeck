import fitz  # PyMuPDF
from typing import Optional, TypedDict

# 使用您项目中统一的logger实例
from logger import logger, log_and_display_error

class WrongPasswordError(Exception):
    """当提供的密码不正确时引发的自定义异常。"""
    pass

class UnlockResult(TypedDict):
    """定义解锁函数返回值的类型。"""
    success: bool
    message: str
    method: str
    output_path: Optional[str]

def unlock_pdf(input_path: str, output_path: str, password: str = '') -> UnlockResult:
    """
    尝试使用PyMuPDF解锁PDF文件并移除其所有限制。

    该函数能处理两种情况：
    1.  限制编辑的PDF (有所有者密码): 默认使用空密码('')尝试移除限制。
    2.  限制查看的PDF (有用户密码): 需要提供正确的密码才能解锁。

    成功解锁后，生成的新PDF文件将没有任何密码。

    参数:
        input_path (str): 输入PDF的路径。
        output_path (str): 输出解锁后PDF的路径。
        password (str): 解锁密码。对于仅限制编辑的PDF，此项可留空。

    返回:
        UnlockResult: 包含解锁结果的字典。
    """
    doc = None # 在try外部初始化doc变量，确保finally块可以访问
    if not output_path:
        logger.warning("未提供有效的输出文件路径。")
        return {
            "success": False,
            "message": "未指定输出路径。",
            "method": "失败",
            "output_path": None
        }

    try:
        # 打开PDF文件
        doc = fitz.open(input_path)

        # 检查PDF是否加密。如果是，则尝试验证密码。
        if doc.is_encrypted:
            logger.info(f"文件 '{input_path}' 已加密，尝试解锁...")

            # 使用提供的密码进行验证。
            if not doc.authenticate(password):
                # 如果验证失败，说明密码错误或缺失。
                raise WrongPasswordError("提供的密码不正确或缺失。")

            logger.info(f"成功解锁文件: '{input_path}'")
        else:
            logger.info(f"文件 '{input_path}' 未加密，将直接进行保存。")

        # 保存文档。PyMuPDF的save方法会自动移除加密。
        doc.save(output_path)
        
        logger.info(f"文件 '{input_path}' 成功处理，输出保存到: {output_path}")
        
        return {
            "success": True,
            "message": "PDF处理成功，所有限制已移除。",
            "method": "PyMuPDF",
            "output_path": output_path
        }

    except WrongPasswordError as e:
        msg = f"解锁失败: {input_path}。原因: {e}"
        log_and_display_error(msg) # 直接调用，不接收返回值
        return {
            "success": False,
            "message": str(e),
            "method": "失败",
            "output_path": None
        }

    except Exception as e:
        msg = f"处理文件时发生未知错误: {input_path}。"
        log_and_display_error(msg, exception=e) # 直接调用，不接收返回值
        return {
            "success": False,
            "message": f"发生未知错误: {e}",
            "method": "失败",
            "output_path": None
        }
    
    finally:
        # 确保文档对象在使用后被关闭
        if doc:
            try:
                doc.close()
                logger.debug(f"成功关闭文档: {input_path}") # 关闭日志级别可以设为DEBUG
            except Exception as close_error:
                logger.error(f"关闭文档 '{input_path}' 时发生错误: {close_error}")