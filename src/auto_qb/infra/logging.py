import logging
import re
from functools import lru_cache
from logging.handlers import RotatingFileHandler
import sys, os
from typing import List, Sequence, Tuple

# 格式串里一个字段: `%(name)s` / `%(asctime)s` / `%(lineno)d` / `%(levelname)-8s`
_LOG_FIELD_RE = re.compile(r"%\((\w+)\)([-+#0 ]*\d*(?:\.\d+)?)?([diouxXeEfFgGcrsa])")

# 按等级筛不了时的提示语(前端显示; 空串 = 无需提示)。两种"筛不了"必须说出来 ——
# 否则界面只剩下"日志文件暂无内容", 用户会把"筛不了"当成"没有该等级的日志"。
NOTE_NO_LEVEL_FIELD = "当前日志格式未含 %(levelname)s, 无法按等级过滤(已显示全部级别)"
NOTE_FORMAT_MISMATCH = "已存的日志行与当前日志格式不符, 无法按等级过滤(已显示全部级别)"


@lru_cache(maxsize=16)
def _level_line_re(format: str):
    """把日志格式串编译成"能从一行里取出等级名"的正则; 格式未含 %(levelname)s 时 None。

    等级名在格式化后的行里**没有固定形状** —— 默认格式包在方括号里, 而 format 是用户可配的
    (config.logging.format), 生产配置就是 `%(asctime)s - %(levelname)s - %(message)s` 这种
    不带括号的写法。所以不能靠 `"[WARNING"` 这类字面量去捞(那样按等级过滤恒空), 只能按格式串
    把 `%(levelname)s` 那一段的位置还原出来。

    其余字段一律当"到下一个字面量为止"的通配符 —— 过滤只要定位等级名, 不需要还原各字段的值。
    保留字面量的原样(不把空格放宽成 `\\s*`): 字面量正是字段之间的分隔证据, 放宽会让等级名
    之前的纯字母字段把它吃掉(`%(name)s %(levelname)s` 下会把 `core` 当成等级)。

    限界: 右对齐的 `%(levelname)8s`(等级名前补空格)定位不到 —— 这种格式会走"筛不了"的提示语,
    不会静默给空。
    """
    fmt = format or ""
    parts: List[str] = []
    seen_level = False
    pos = 0
    for m in _LOG_FIELD_RE.finditer(fmt):
        parts.append(re.escape(fmt[pos:m.start()].replace("%%", "%")))
        pos = m.end()
        name, conv = m.group(1), m.group(3)
        if name == "levelname":
            seen_level = True
            # 尾随可空空白: `%(levelname)-8s` 这类宽度声明会在等级名后补空格(实测漏了这条,
            # 带宽度字段名的格式一行都对不上、整份日志退化成"筛不了")。
            parts.append(r"(?P<level>[A-Za-z]+) *")
        elif name == "message":
            parts.append(r".*")  # message 之后是消息正文, 直接吞到行尾
        elif conv in "diouxX":
            parts.append(r"\d+")
        else:
            parts.append(r".*?")
    parts.append(re.escape(fmt[pos:].replace("%%", "%")))
    return re.compile("^" + "".join(parts) + "$") if seen_level else None


def filter_log_lines(format: str, lines: Sequence[str], level: str) -> Tuple[List[str], str]:
    """按等级筛日志行, 返回 (命中行, 提示语)。level 为空 = 不过滤。

    命中行**含该记录的续行** —— 多行日志(有 13 处 `exc_info=True` 会打出整段 traceback)折行后
    每行都带不上等级标记, 若按行独立判, 筛 ERROR 就只剩 `... 执行异常: ...` 这一行、把用户真正
    要看的栈丢了。所以按"记录"判: 解析得出的行开启新记录, 解析不出的行跟随上一条记录的取舍。
    """
    lv = (level or "").strip().upper()
    if not lv:
        return list(lines), ""
    rx = _level_line_re(format)
    if rx is None:
        return list(lines), NOTE_NO_LEVEL_FIELD
    out: List[str] = []
    matched = False
    keep = False
    for ln in lines:
        m = rx.match(ln)
        if m:
            matched = True
            keep = m.group("level").upper() == lv
        if keep:
            out.append(ln)
    if not matched and lines:
        # 格式里有等级字段却一行都对不上: 典型是改了 format, 文件里还是旧格式的历史行
        return list(lines), NOTE_FORMAT_MISMATCH
    return out, ""


def setup_logging(file: str, level: int, max_bytes: int, format: str):
    """设置日志: 控制台与文件均跟随配置等级。

    - root 跟随 level(默认 INFO): 拦截第三方库的 DEBUG(urllib3 等)
    - auto_qb logger 放开 DEBUG: 本项目调试信息可穿透到 handler(level=DEBUG 时收录)
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

    # 4. 作用域调整: 本项目 DEBUG 放开; qbittorrentapi 封顶 INFO(排除请求/响应 DEBUG 噪音);
    #    urllib3 封顶 ERROR(排除断连期间连接重试的 Retry WARNING 刷屏, 程序自身日志已有节流摘要)
    logging.getLogger("auto_qb").setLevel(logging.DEBUG)
    logging.getLogger("qbittorrentapi").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.ERROR)

    # 可选：记录一条启动信息
    logger.info("日志初始化完成")
