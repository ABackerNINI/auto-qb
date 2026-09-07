import logging
from logging.handlers import RotatingFileHandler
import sys, os


def setup_logging(file: str, level: int, max_bytes: int, format: str):
    """设置日志: 控制台跟随配置等级; 文件恒为 DEBUG(本项目调试信息全量落盘)。

    - root 跟随 level(默认 INFO): 拦截第三方库的 DEBUG(urllib3 等)
    - auto_qb logger 放开 DEBUG: 本项目调试信息可穿透到 handler(文件收录)
    - qbittorrentapi 封顶 INFO: 排除其请求/响应 DEBUG 噪音(自身 INFO 仍入文件)
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

    # 4. 作用域调整: 本项目 DEBUG 放开; qbittorrentapi 封顶 INFO(排除请求/响应 DEBUG 噪音)
    logging.getLogger("auto_qb").setLevel(logging.DEBUG)
    logging.getLogger("qbittorrentapi").setLevel(logging.INFO)

    # 可选：记录一条启动信息
    logger.info("日志初始化完成")
