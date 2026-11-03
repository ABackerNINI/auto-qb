"""LogsMixin: 搜索索引 / 日志域命令处理器

move-only 自 commands.py 切出(计划 26-11-02-2342 §07 R5), 未改语义。
"""
from .commands_common import logger


class LogsMixin:
    def _cmd_build_search_index(self):
        """WEB UI 命令: 构建搜索索引(Web 线程检测到索引脏后投递, 主循环线程执行)。

        限流构建可能需多轮: 仅在全部拉取完成(不再脏)时记录完成日志, 避免分批刷屏。
        """
        self.build_search_index()
        if not self.web.search_index_dirty:
            logger.info(f"WEB UI | 搜索索引已构建: {len(self.web.search_index)} 个种子")
