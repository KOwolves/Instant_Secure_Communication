import logging
from server import SecureChatServer
from config import LOG_FILE # 从 config 导入日志配置

def setup_logging():
    """配置日志系统。"""
    # 根据字符串获取日志级别，如果配置中不存在，则默认为 INFO
    log_level = getattr(logging, 'INFO', logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),  # 输出到文件
            logging.StreamHandler()                           # 输出到控制台
        ]
    )

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("服务器程序启动。")
    try:
        chat_server = SecureChatServer()
        chat_server.start()
    except Exception as e:
        logger.critical(f"服务器主程序运行中发生严重错误: {e}", exc_info=True)
    logger.info("服务器程序结束。")