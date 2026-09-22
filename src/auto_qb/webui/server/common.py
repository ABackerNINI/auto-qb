"""web 包纯工具: 版本号 / web.token 生成 / Content-Disposition / 分组 key 解码.

除 HTTPException 外无 FastAPI 依赖。拆分更名: _app_version→app_version、
_group_key_param→group_key_param(factory 以别名引用, 端点体零改动)。

❗本模块 logger 显式取名 "auto_qb.web"(见包 __init__ K3) —— ensure_web_token 的
  生成提示日志被 test_web_token_not_printed_in_logs 按 r.name 钉死。
"""
import logging
import os
import re
import secrets
from urllib.parse import quote

from fastapi import HTTPException

from ...infra.utils import decode_group_key, open_path  # noqa: F401  (open_path 供 open-path 端点经 common.open_path 调用 —— patch 地址稳定, test_api_open_path_endpoint 钉此处)

logger = logging.getLogger("auto_qb.web")

# 头值清洗: 控制字符(含 CR/LF)会截断响应头或造成头注入
_HEADER_UNSAFE_RE = re.compile(r"[\x00-\x1f\x7f]")
# ASCII 回退名有效性判定: 至少含一个字母/数字, 否则视为清洗残留(仅有 `_`/`.`/空格)
_ASCII_ALNUM_RE = re.compile(r"[A-Za-z0-9]")


def app_version() -> str:
    """包版本号(供前端顶栏展示)。

    必须函数内延迟导入: `auto_qb/__init__.py` 先 `from .qbmanager import QbManager` 再赋值
    `__version__`, 模块顶层导入版本号会在包初始化未完成时抛 ImportError。
    """
    from auto_qb import __version__
    return __version__


def config_backup_path(manager) -> str:
    """配置保存前的备份路径: `<data_dir>/<配置文件名>.bak`

    备份集中到运行时数据目录(与 state/log/web.token 同处), 不在项目根目录产生 config.yml.bak。
    data_dir 为相对路径时以 cwd 为基准 —— 与 state_file 的派生口径一致(见 config/loaders._under)。
    """
    return os.path.join(manager.config.data_dir, os.path.basename(manager.config_path) + ".bak")


def ensure_web_token(manager) -> str:
    """确定 WEB 访问密钥: 显式配置优先; 否则随机生成并持久化到 data_dir/web.token(0600)"""
    if manager.config.web.token:
        return manager.config.web.token
    token_file = os.path.join(os.path.dirname(manager.state_file) or ".", "web.token")
    if os.path.exists(token_file):
        with open(token_file, "r", encoding="ascii") as f:
            token = f.read().strip()
        if token:
            return token
    token = secrets.token_hex(32)
    fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as f:
        f.write(token)
    # 密钥内容**不进日志**: 记 WARNING 会被 notify 处理器(min_level 默认 WARNING)推到系统
    # 通知, 且落到日志文件后 /api/log 可读回 —— 拿到密钥即等于拿到改配置/删种子的能力。
    # 改为 INFO 只提示文件路径: 用户打开 web.token 即可, 或配置 web.token 使用固定密钥。
    logger.info(f"WEB 访问密钥已生成: {token_file}(密钥内容只存该文件、不打印到日志, 需查看请打开它)")
    return token


def content_disposition(filename: str, fallback: str, ext: str = "") -> str:
    """构造 Content-Disposition 值(RFC 6266): HTTP 头只能 latin-1 编码, 中文/emoji 名必须走 `filename*`

    直接 `filename="中文.torrent"` 会让 Starlette 编码头时抛 UnicodeEncodeError(整个响应 500)。
    双段写法: ASCII 回退名给老旧客户端, `filename*=UTF-8''<百分号编码>` 给现代浏览器(取回原名)。
    另剔除引号/路径符/控制字符(换行会截断头, 即头注入)。
    """
    name = _HEADER_UNSAFE_RE.sub("", filename or "")
    name = name.replace('"', "").replace("\\", "_").replace("/", "_").strip()
    suffix = f".{ext}" if ext else ""
    ascii_name = name.encode("ascii", "ignore").decode("ascii").strip()
    if not _ASCII_ALNUM_RE.search(ascii_name):
        ascii_name = fallback  # 只剩清洗残留符号(如纯中文名的 "/" -> "_")时用 hash, 回退名才可辨识
    quoted = quote(name, safe="")
    return f"attachment; filename=\"{ascii_name}{suffix}\"; filename*=UTF-8''{quoted}{suffix}"


def group_key_param(text: str) -> tuple:
    """URL/请求体里的分组标识 → (剧名, 文件 tuple); 畸形标识转 400 而不是 500

    `decode_group_key` 在 base64 非 ASCII / 非法 JSON / 结构不符时会抛(binascii.Error 与
    json.JSONDecodeError 均为 ValueError 子类, 另有 TypeError / IndexError / KeyError)——
    不拦截就是一条 500 + 栈回溯: 前端手输或被篡改的 key 都能打到服务端错误页。客户端错误应回 400。
    """
    try:
        return decode_group_key(text)
    except (ValueError, TypeError, LookupError):  # LookupError 覆盖 IndexError / KeyError
        raise HTTPException(status_code=400, detail="分组标识无效")
