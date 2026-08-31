import logging
from logging.handlers import RotatingFileHandler
import sys, os


def setup_logging(file: str, level: int, max_bytes: int, format: str):
    """
    设置日志
    """
    logging.basicConfig(level=level, format=format)

    # 1. 获取 root logger（或自定义 logger）
    logger = logging.getLogger()

    # 移除已有的 handlers（避免重复添加）
    logger.handlers.clear()

    # 2. 添加控制台 handler（始终输出）
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    formatter = logging.Formatter(format)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 3. 如果指定了文件路径，添加 RotatingFileHandler
    if file.strip():
        # 创建文件夹如果不存在
        dir_path = os.path.dirname(file)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        # 轮转备份数量，可根据需要调整（这里默认 5 个）
        backup_count = 5
        file_handler = RotatingFileHandler(file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 可选：记录一条启动信息
    logger.info("Logging configured successfully")
