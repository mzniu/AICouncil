import logging
import sys
import requests
import threading
from src import config

class WebLogHandler(logging.Handler):
    """自定义日志处理器，将日志发送到 Web 监控面板。"""
    def __init__(self, url):
        super().__init__()
        self.url = url

    def emit(self, record):
        log_entry = self.format(record)
        # 使用线程发送请求，避免阻塞主流程
        threading.Thread(target=self._send_log, args=(log_entry,), daemon=True).start()

    def _send_log(self, message):
        try:
            requests.post(self.url, json={"type": "log", "content": message}, timeout=0.5)
        except:
            pass

def setup_logger(name: str = "AICouncil"):
    logger = logging.getLogger(name)
    # Set the root logger to DEBUG so it captures everything
    logger.setLevel(logging.DEBUG)

    # Prevent adding multiple handlers if setup_logger is called multiple times
    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )

        # File handler: Always record everything (DEBUG and above)
        file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        # Console handler: Follow the configured LOG_LEVEL (default INFO)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(config.LOG_LEVEL)
        logger.addHandler(console_handler)

        # Web handler: 发送到 Flask 服务器
        web_handler = WebLogHandler("http://127.0.0.1:5000/api/update")
        web_handler.setFormatter(formatter)
        web_handler.setLevel(logging.DEBUG)
        logger.addHandler(web_handler)

    return logger

# Global logger instance
logger = setup_logger()
