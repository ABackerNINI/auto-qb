"""WEB UI 后端: FastAPI 应用工厂(只读快照 + 命令投递, 不直接触碰主循环状态)

线程模型: uvicorn 在独立线程运行; 本模块的所有请求处理器只做两件事——
1) 读取 manager 暴露的只读快照(_group_view/status_snapshot, 主循环每 tick 原子替换);
2) 向 manager.web_commands 投递控制命令(由主循环线程消费执行, 写操作只在主循环线程)。

鉴权: 所有 /api/* 请求校验 Bearer 密钥; 密钥来自 config.web.token, 留空则随机生成并
持久化到 <data_dir>/web.token(0600), 启动日志打印一次。默认仅监听 127.0.0.1。
"""
import logging
import os
import re
import secrets
import threading
import time
from typing import List, Optional
from urllib.parse import quote

import uvicorn
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .mixins.web_commands import SELF_POSTED_COMMANDS
from .utils import decode_group_key, open_path, path_normalize

logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "web_ui", "static")

# 头值清洗: 控制字符(含 CR/LF)会截断响应头或造成头注入
_HEADER_UNSAFE_RE = re.compile(r"[\x00-\x1f\x7f]")
# ASCII 回退名有效性判定: 至少含一个字母/数字, 否则视为清洗残留(仅有 `_`/`.`/空格)
_ASCII_ALNUM_RE = re.compile(r"[A-Za-z0-9]")

# 热重载重启服务器的时间预算: uvicorn 的 should_exit 只是"请求退出"(主循环每 0.1s 才读一次,
# 之后才关闭监听套接字), 不等旧线程退出就启新服务会撞 Errno 10048 —— 见 stop_web_server。
WEB_STOP_TIMEOUT = 5.0
WEB_START_TIMEOUT = 5.0


def _app_version() -> str:
    """包版本号(供前端顶栏展示)。

    必须函数内延迟导入: `auto_qb/__init__.py` 先 `from .qbmanager import QbManager` 再赋值
    `__version__`, 模块顶层导入版本号会在包初始化未完成时抛 ImportError。
    """
    from . import __version__
    return __version__


def _config_backup_path(manager) -> str:
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


def _is_loopback_host(host) -> bool:
    """是否为本机 loopback 地址: 仅 127.0.0.1 / ::1 及其 IPv4-mapped 形式"""
    if not host:
        return False
    return host in ("127.0.0.1", "::1", "::ffff:127.0.0.1")


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


def _group_key_param(text: str) -> tuple:
    """URL/请求体里的分组标识 → (剧名, 文件 tuple); 畸形标识转 400 而不是 500

    `decode_group_key` 在 base64 非 ASCII / 非法 JSON / 结构不符时会抛(binascii.Error 与
    json.JSONDecodeError 均为 ValueError 子类, 另有 TypeError / IndexError / KeyError)——
    不拦截就是一条 500 + 栈回溯: 前端手输或被篡改的 key 都能打到服务端错误页。客户端错误应回 400。
    """
    try:
        return decode_group_key(text)
    except (ValueError, TypeError, LookupError):  # LookupError 覆盖 IndexError / KeyError
        raise HTTPException(status_code=400, detail="分组标识无效")


def create_app(manager) -> FastAPI:
    """构建 WEB 应用: 只读快照 + 命令投递 + 设置读写, 全部 /api/* 经 Bearer 密钥鉴权"""
    _local_skip_logged = False  # 免鉴权提示每个进程只记一次(见下)

    def require_token(request: Request, authorization: str = Header(default="")):
        nonlocal _local_skip_logged
        # 公开只读端点: 前端登录前读取本机免鉴权等标志(不含任何机密), 免 token 放行
        if request.url.path == "/api/config/public":
            return
        # 跳过本地验证: 本机(loopback)连接免 token 鉴权, 直接放行进入(web.skip_local_verify)。
        # 提示日志**只记一次**且为 INFO: 免鉴权是用户显式开启的配置(非异常), 记 WARNING 会经 notify
        # 推送扰民; 又因免鉴权模式下前端按设计不发 Authorization 头(R10-01), 每请求都记会把轮询
        # 日志刷满(实测 2 条/轮); 首次记一条足以说明"这个实例不校验密钥"。
        if manager.config.web.skip_local_verify and _is_loopback_host(request.client.host if request.client else None):
            if not authorization.startswith("Bearer ") and not _local_skip_logged:
                _local_skip_logged = True
                logger.info("WEB 跳过本地验证: 本机连接免密钥放行(web.skip_local_verify=true)")
            return
        # 鉴权范围 = /api/*: 静态页面与 UI 重定向路由无密钥也可访问(页面本身不含数据,
        # 密钥由前端加载后带 Authorization 头访问 API; 旧实现仅靠"StaticFiles 挂载不经
        # 依赖系统"这个副作用放行静态, UI 目录化后根路径/重定向是真实路由, 必须显式放行)。
        # 缺省/畸形凭证(无头、scheme 错误、空 token)静默 401: 属客户端常态(登录框空提交、
        # 轮询竞态、端口探测), 记 WARNING 会经 notify 推送扰民(历史上前端空 token 请求被
        # HTTP 头 OWS 裁剪成裸 "Bearer", 曾持续误报); 仅"携带了但错误"的密钥记一条不含密钥
        # 内容的 WARNING, 保留真实错密钥/探测信号。比较走 compare_digest 防时序侧信道。
        if not request.url.path.startswith("/api"):
            return
        scheme = "Bearer "
        if not authorization.startswith(scheme):
            raise HTTPException(status_code=401, detail="invalid token")
        token = authorization[len(scheme):].strip()
        if not token:
            raise HTTPException(status_code=401, detail="invalid token")
        if not secrets.compare_digest(token, manager._web_token):
            logger.warning("WEB 鉴权失败: 密钥不匹配")
            raise HTTPException(status_code=401, detail="invalid token")

    app = FastAPI(
        title="auto-qb",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        dependencies=[Depends(require_token)],
    )

    @app.get("/api/config/public")
    def api_config_public():
        """前端登录前读取的公开只读标志(不含密钥等机密): 本机免鉴权开关"""
        return {"web": {"skip_local_verify": manager.config.web.skip_local_verify}}

    def _enqueue(cmd: str, payload: dict) -> dict:
        """投递控制命令并生成回执 ID: 前端据 cmd_id 轮询 /api/cmd/{id} 获取执行结果"""
        cmd_id = secrets.token_hex(8)
        body = dict(payload or {})
        body["cmd_id"] = cmd_id
        # P0-0 埋点: 投递时刻随命令走(下划线前缀的键在 drain 侧被剔除, 不会传给 handler),
        # 回执据此拆出"排队等主循环 wait_ms"与"执行 exec_ms"两段耗时
        body["_queued_ts"] = time.time()
        manager.web_commands.put((cmd, body))
        # 唤醒主循环立即消费(命令延迟 0~main_tick -> 近乎 0); 自投递命令不唤醒, 见
        # mixins/web_commands.py 的 SELF_POSTED_COMMANDS —— 否则会自激打满 CPU。
        if cmd not in SELF_POSTED_COMMANDS:
            manager.wake()
        return {"queued": True, "cmd_id": cmd_id}

    @app.get("/api/status")
    def api_status():
        manager.touch_web_client()
        snap = manager.status_snapshot()
        return {
            "connected": snap["connected"],
            "paused": snap["paused"],
            "torrents": snap["torrents"],
            "groups": len(manager._group_view),
            "version": _app_version(),
            "traffic": manager._traffic_view,
        }

    @app.get("/api/state")
    def api_state(rid: int = -1):
        """合并端点: status + groups 一次返回(前端单请求轮询, 请求数减半)

        rid 为前端已持有的分组视图版本: 版本一致时只回 status(体积极小), groups 不回传,
        前端据此跳过整表替换与重渲染; rid 缺省/不匹配时回传全量分组数据。
        """
        manager.touch_web_client()
        snap = manager.status_snapshot()
        return {
            "status":
                {
                    "connected": snap["connected"],
                    "paused": snap["paused"],
                    "torrents": snap["torrents"],
                    "groups": len(manager._group_view),
                    "version": _app_version(),
                    # 限速/流量快照: 恒回传(不受 rid 门控) —— 数据源是限速曲线任务而非分组视图,
                    # 若参与版本门控会与 groups 的脏语义耦合, 反而可能长时间不刷新
                    "traffic": manager._traffic_view,
                    # qB 全局状态(server_state: 连接状态/全局速度/累计流量/磁盘剩余等)。
                    # 与 traffic 同为"恒回传"口径: 数据源是 sync 快照而非分组视图, 不参与
                    # rid 门控。此前前端状态栏要为此**单独再打一次 /api/stats**, 两条链路
                    # 刷新频率不同 ⇒ 出现"状态栏速度正常、种子行速度滞后"的错位观测;
                    # 合并后每轮只剩 1 条请求, 且两者同源同轮。
                    "server": manager.store.server_state,
                },
            **manager.ensure_group_state(rid),
        }

    @app.get("/api/groups")
    def api_groups():
        manager.touch_web_client()
        return {"groups": manager.ensure_group_view()}

    @app.get("/api/search")
    def api_search(q: str = ""):
        """按种子名/文件列表搜索种子(主循环构建的缓存索引, Web 线程只读; 索引脏时投递构建命令)"""
        manager.touch_web_client()
        return manager.search_torrents(q)

    @app.get("/api/paths")
    def api_paths():
        """已知目录聚合(DLG-04, 决策 D3): 添加种子对话框「保存位置」下拉的推荐目录集

        浏览器无法枚举本地目录树, 聚合两组已知目录排序去重后返回, 前端仍允许自由输入:
        ①当前分组索引各组 key 首元(store.groups 的 key = (规范化 save_path, 文件列表), 组空即删,
        无陈旧条目); ②store 现有种子的 save_path(经 path_normalize 归一分隔符后参与去重, 与组 key
        同径不重复出现)。只读快照, 无副作用(不触发视图重建/不投命令)。
        """
        manager.touch_web_client()
        paths = {key[0] for key in manager.store.groups if key and key[0]}
        paths.update(path_normalize(rec.save_path) for rec in manager.store.by_hash.values() if rec.save_path)
        return {"paths": sorted(paths)}

    def _browse_roots() -> List[str]:
        """目录浏览的**允许根**集合(R10-11): 与 /api/paths 同源的已知保存路径。

        白名单只由服务端从自己的快照派生, 不接受客户端传参 —— 这是文件系统读端点的第一道闸门。
        """
        roots = {path_normalize(rec.save_path or "") for rec in manager.store.by_hash.values() if rec.save_path}
        return sorted(r for r in roots if r)

    def _fs_real(p: str) -> str:
        """规范化到可比较的绝对真实路径(realpath 解符号链接, normcase 在 Windows 上统一大小写/斜杠)"""
        return os.path.normcase(os.path.realpath(p))

    def _within_roots(target: str, roots: List[str]) -> bool:
        """目标是否落在某个允许根内(相等或为其子目录) —— 越界一律拒绝"""
        t = _fs_real(target)
        for r in roots:
            rr = _fs_real(r)
            if t == rr or t.startswith(rr.rstrip("\\/") + os.sep):
                return True
        return False

    @app.get("/api/fs/dirs")
    def api_fs_dirs(path: str = ""):
        """目录浏览(R10-11 决策 D2-A): 给添加种子窗口的"选择位置"提供真实目录树。

        为何由服务端提供: 浏览器拿不到任意目录的绝对路径(目录上传控件只暴露相对路径,
        File System Access API 同样不返回绝对路径) —— "像选 .torrent 那样弹系统选择器"在前端
        物理上做不到, 结果等价的做法只能是服务端给路径。

        **安全边界**(本项目唯一新增的文件系统读能力, 后续改动必须保持):
        ① 只列**目录**, 绝不返回文件条目、不读文件内容;
        ② 允许根白名单 = 已知保存路径(与 /api/paths 同源); 路径经 realpath 规范化后必须落在
           某个根之内(相等或为子目录), 否则 403 —— 同时挡掉 `..` 穿越;
        ③ 逐条子目录同样过白名单 -> 指向根外的符号链接/junction 不会出现在列表里(逃逸防护);
        ④ 鉴权沿用全局 require_token 依赖(本机免鉴权同样放行, 与其它端点一致)。
        path 为空 = 返回允许根列表(前端首屏入口)。
        """
        manager.touch_web_client()
        roots = _browse_roots()
        if not roots:
            return {"path": "", "parent": "", "roots": [], "dirs": []}
        if not path:
            return {"path": "", "parent": "", "roots": roots, "dirs": [{"name": r, "path": r} for r in roots]}
        if not _within_roots(path, roots):
            raise HTTPException(status_code=403, detail="路径不在允许的保存路径范围内")
        target = os.path.realpath(path)
        if not os.path.isdir(target):
            raise HTTPException(status_code=404, detail="目录不存在或不可访问")
        dirs = []
        try:
            with os.scandir(target) as it:
                for entry in it:
                    if not entry.is_dir() or not _within_roots(entry.path, roots):
                        continue
                    dirs.append({"name": entry.name, "path": path_normalize(os.path.join(target, entry.name))})
        except OSError as e:
            raise HTTPException(status_code=404, detail=f"目录不可读: {e.strerror or e}")
        dirs.sort(key=lambda d: d["name"].lower())
        parent = os.path.dirname(target)
        return {
            "path": path_normalize(target),
            "parent": path_normalize(parent) if _within_roots(parent, roots) else "",
            "roots": roots,
            "dirs": dirs,
        }

    @app.post("/api/fs/mkdir")
    def api_fs_mkdir(body: dict = None):
        """在允许根内的目录下新建文件夹(目录浏览器的"新建"按钮)。

        安全边界与 /api/fs/dirs 同源, 另加: ① name 必须是**单层名字**(不含分隔符、不为 . / ..),
        不接受任何路径成分; ② 已存在同名目录直接返回(幂等), 同名**文件**报 409;
        ③ 这是本项目唯一的文件系统**写**能力, 不扩展到重命名/删除/递归。
        不触碰任务队列与 state_file -> 不违反单一写线程假设。
        """
        b = body or {}
        name = str(b.get("name") or "").strip()
        parent = str(b.get("path") or "").strip()
        roots = _browse_roots()
        if not name or name in (".", "..") or any(sep in name for sep in ("/", "\\")):
            raise HTTPException(status_code=400, detail="文件夹名不合法")
        if not parent or not _within_roots(parent, roots):
            raise HTTPException(status_code=403, detail="路径不在允许的保存路径范围内")
        base = os.path.realpath(parent)
        if not os.path.isdir(base):
            raise HTTPException(status_code=404, detail="目录不存在或不可访问")
        target = os.path.join(base, name)
        if os.path.exists(target):
            if os.path.isdir(target):
                return {"created": path_normalize(target), "existed": True}
            raise HTTPException(status_code=409, detail="同名文件已存在")
        try:
            os.mkdir(target)
        except OSError as e:
            raise HTTPException(status_code=400, detail=f"新建失败: {e.strerror or e}")
        logger.info(f"WEB 新建目录: {target}")
        return {"created": path_normalize(target), "existed": False}

    @app.post("/api/open-path")
    def api_open_path(body: dict = None):
        """用系统默认方式打开辅种组/种子的目标文件夹(FX-14)。

        **安全红线**: 绝不接受客户端传入任意路径 —— os.startfile / open / xdg-open 会用系统
        默认程序打开目标, 等于把"任意文件执行"暴露给 WEB 端点。故请求只带 kind + 标识,
        路径一律由服务端从自己的快照派生, 且只允许**已存在的目录或(单文件种子的)文件**。

        解析口径: group 取组 key 首元(store.groups 的 key = (规范化 save_path, 文件列表),
        组内成员路径天然一致, 无需再比对); torrent 的 content_path 指向文件时是**单文件种子**
        —— 打开所在目录并**定位选中**该文件(R10-10 用户诉求: "没有创建文件夹的要在文件夹中
        选中相关文件"), 否则取 content_path, 都缺则回退 save_path。
        只读: 不投命令、不写 state —— 单一写线程假设不受影响。
        """
        manager.touch_web_client()
        b = body or {}
        kind = str(b.get("kind") or "").strip()
        select = False
        if kind == "group":
            key = _group_key_param(str(b.get("key") or ""))
            if key not in manager.store.groups:
                raise HTTPException(status_code=404, detail="辅种不存在")
            target = key[0] or ""
        elif kind == "torrent":
            rec = _require_torrent(str(b.get("hash") or "").strip())
            content = path_normalize(rec.content_path or "")
            if content and not os.path.isdir(content):
                target, select = content, True  # 单文件种子: 定位选中, 不降级成"只打开父目录"
            else:
                target = content or path_normalize(rec.save_path or "")
        else:
            raise HTTPException(status_code=400, detail="kind 必须是 group 或 torrent")
        target = path_normalize(target)
        if select:
            if not os.path.isfile(target):
                raise HTTPException(status_code=404, detail="目标文件不存在或不可访问")
        elif not target or not os.path.isdir(target):
            raise HTTPException(status_code=404, detail="目标目录不存在或不可访问")
        open_path(target, select=select)
        return {"opened": target, "select": select}

    @app.post("/api/groups/{key}/pause")
    def api_pause(key: str):
        return _enqueue("pause_group", {"key": _group_key_param(key)})

    @app.post("/api/groups/{key}/resume")
    def api_resume(key: str):
        return _enqueue("resume_group", {"key": _group_key_param(key)})

    @app.post("/api/groups/{key}/reannounce")
    def api_reannounce(key: str):
        return _enqueue("reannounce_group", {"key": _group_key_param(key)})

    @app.post("/api/groups/{key}/delete")
    def api_delete(key: str, body: dict = None):
        delete_files = bool((body or {}).get("delete_files", False))
        result = _enqueue("delete_group", {"key": _group_key_param(key), "delete_files": delete_files})
        result["delete_files"] = delete_files
        return result

    @app.post("/api/torrents/{hash}/pause")
    def api_t_pause(hash: str):
        return _enqueue("pause_torrent", {"hash": hash})

    @app.post("/api/torrents/{hash}/resume")
    def api_t_resume(hash: str):
        return _enqueue("resume_torrent", {"hash": hash})

    @app.post("/api/torrents/{hash}/reannounce")
    def api_t_reannounce(hash: str):
        return _enqueue("reannounce_torrent", {"hash": hash})

    @app.post("/api/torrents/{hash}/delete")
    def api_t_delete(hash: str, body: dict = None):
        delete_files = bool((body or {}).get("delete_files", False))
        result = _enqueue("delete_torrent", {"hash": hash, "delete_files": delete_files})
        result["delete_files"] = delete_files
        return result

    # ---- 种子控制写端点(WEB UI 替代 qB 界面二轮: 全部 POST + _enqueue, 主循环线程执行) ----
    # 除 bulk 外, hash 不在快照时主循环侧静默跳过(照 pause_torrent 样板); 参数错误由
    # _cmd_* 抛 ValueError -> 命令分发层写 error 回执。qB 写后的快照同步策略见 QbApi。

    @app.post("/api/torrents/{hash}/recheck")
    def api_t_recheck(hash: str):
        return _enqueue("recheck_torrent", {"hash": hash})

    @app.post("/api/torrents/{hash}/super-seeding")
    def api_t_super_seeding(hash: str, body: dict = None):
        enable = bool((body or {}).get("enable", False))
        return _enqueue("super_seeding", {"hash": hash, "enable": enable})

    @app.post("/api/torrents/{hash}/force-start")
    def api_t_force_start(hash: str, body: dict = None):
        enable = bool((body or {}).get("enable", False))
        return _enqueue("force_start", {"hash": hash, "enable": enable})

    @app.post("/api/torrents/{hash}/limits")
    def api_t_limits(hash: str, body: dict = None):
        """种子传输限速(bytes/s, 0=不限); 两方向均可缺省(缺省的方向不下发)"""
        b = body or {}
        payload = {"hash": hash}
        if b.get("up_limit") is not None:
            payload["up_limit"] = int(b["up_limit"])
        if b.get("dl_limit") is not None:
            payload["dl_limit"] = int(b["dl_limit"])
        return _enqueue("set_torrent_limits", payload)

    @app.post("/api/torrents/{hash}/share-limits")
    def api_t_share_limits(hash: str, body: dict = None):
        """分享限制: -1=不限制, -2=用全局; 前端应从详情回填三值后整组提交"""
        b = body or {}
        payload = {"hash": hash}
        if b.get("ratio_limit") is not None:
            payload["ratio_limit"] = float(b["ratio_limit"])
        if b.get("seeding_time_limit") is not None:
            payload["seeding_time_limit"] = int(b["seeding_time_limit"])
        if b.get("inactive_seeding_time_limit") is not None:
            payload["inactive_seeding_time_limit"] = int(b["inactive_seeding_time_limit"])
        return _enqueue("set_share_limits", payload)

    @app.post("/api/torrents/{hash}/location")
    def api_t_location(hash: str, body: dict = None):
        location = str((body or {}).get("location") or "")
        return _enqueue("set_torrent_location", {"hash": hash, "location": location})

    @app.post("/api/torrents/{hash}/rename")
    def api_t_rename(hash: str, body: dict = None):
        name = str((body or {}).get("name") or "")
        return _enqueue("rename_torrent", {"hash": hash, "name": name})

    @app.post("/api/torrents/{hash}/queue")
    def api_t_queue(hash: str, body: dict = None):
        action = str((body or {}).get("action") or "")
        return _enqueue("queue_torrent", {"hash": hash, "action": action})

    @app.post("/api/torrents/{hash}/auto-tmm")
    def api_t_auto_tmm(hash: str, body: dict = None):
        enable = bool((body or {}).get("enable", False))
        return _enqueue("set_auto_tmm", {"hash": hash, "enable": enable})

    @app.post("/api/torrents/{hash}/trackers/add")
    def api_t_trackers_add(hash: str, body: dict = None):
        urls = [str(u) for u in ((body or {}).get("urls") or []) if u]
        return _enqueue("add_trackers", {"hash": hash, "urls": urls})

    @app.post("/api/torrents/{hash}/trackers/edit")
    def api_t_trackers_edit(hash: str, body: dict = None):
        b = body or {}
        payload = {"hash": hash, "orig_url": str(b.get("orig_url") or ""), "new_url": str(b.get("new_url") or "")}
        return _enqueue("edit_tracker", payload)

    @app.post("/api/torrents/{hash}/trackers/remove")
    def api_t_trackers_remove(hash: str, body: dict = None):
        url = str((body or {}).get("url") or "")
        return _enqueue("remove_tracker", {"hash": hash, "url": url})

    @app.post("/api/torrents/{hash}/files/priority")
    def api_t_file_priority(hash: str, body: dict = None):
        b = body or {}
        payload = {
            "hash": hash,
            "indices": [int(i) for i in (b.get("indices") or [])],
            "priority": int(b.get("priority") or 0),
        }
        return _enqueue("set_file_priority", payload)

    @app.post("/api/torrents/{hash}/rename-fs")
    def api_t_rename_fs(hash: str, body: dict = None):
        b = body or {}
        payload = {
            "hash": hash,
            "old_path": str(b.get("old_path") or ""),
            "new_path": str(b.get("new_path") or ""),
            "is_folder": bool(b.get("is_folder", False)),
        }
        return _enqueue("rename_fs", payload)

    @app.post("/api/torrents/bulk")
    def api_t_bulk(body: dict = None):
        """批量操作(平铺视图多选): 单命令批量, 主循环侧一次 API 调用传全部目标

        两种模式(DLG-02): hashes=种子 hash 列表; keys=分组 key 列表(URL 编码态, 与
        /api/groups/{key}/delete 同一编解码), 可混合。主循环侧展开组成员并与 hashes
        合并去重后一次调用; 回执结构与纯 hash 模式一致(queued/cmd_id + 聚合回执)。
        """
        b = body or {}
        payload = {
            "hashes": [str(h) for h in (b.get("hashes") or []) if h],
            "action": str(b.get("action") or ""),
            "delete_files": bool(b.get("delete_files", False)),
        }
        # 组键模式(DLG-02): 非空才入 payload, 纯 hash 调用的队列载荷与历史形态完全一致
        keys = [_group_key_param(str(k)) for k in (b.get("keys") or []) if k]
        if keys:
            payload["keys"] = keys
        return _enqueue("bulk_torrents", payload)

    # ---- 种子中心视图读端点(WEB UI 替代 qB 界面: 详情抽屉/全局统计) ----
    # 全部只读: 快照读 store, tracker/文件/peer 按需直读 client(不写 store 惰性缓存 ——
    # 缓存写入只在主循环线程, 保持 Web 线程无副作用); qB 断连时 503, 未知 hash 404。

    def _require_torrent(hash: str):
        rec = manager.store.get(hash)
        if rec is None:
            raise HTTPException(status_code=404, detail="种子不存在")
        return rec

    def _require_client():
        if manager.client is None:
            raise HTTPException(status_code=503, detail="qB 未连接")
        return manager.client

    @app.get("/api/torrents/{hash}")
    def api_torrent_detail(hash: str):
        """单种子全量详情: TorrentRecord.to_dict 全字段(含 _raw 前向兼容字段)
        + site(站点名) + HR 展示字段(与分组成员视图同源) —— 详情抽屉 General tab 数据源"""
        manager.touch_web_client()
        rec = _require_torrent(hash)
        return {"torrent": {**rec.to_dict(), "site": rec.tracker_name, **manager._hr_view_fields(rec)}}

    @app.get("/api/torrents/{hash}/trackers")
    def api_torrent_trackers(hash: str):
        """单种子 tracker 列表(qB 透传; 含 **/[DHT]/[PeX]/[LSD] 虚拟条目, 前端自行弱化)"""
        manager.touch_web_client()
        _require_torrent(hash)
        return list(_require_client().torrents_trackers(hash) or [])

    @app.get("/api/torrents/{hash}/files")
    def api_torrent_files(hash: str):
        """单种子文件列表(qB 透传; 详情抽屉 Content tab 数据源)"""
        manager.touch_web_client()
        _require_torrent(hash)
        return list(_require_client().torrents_files(hash) or [])

    @app.get("/api/torrents/{hash}/peers")
    def api_torrent_peers(hash: str):
        """单种子 peer 列表(qB 透传; 详情抽屉打开期间前端按需轮询, 关闭即停, 不进主循环 tick)

        走 sync/torrentPeers(qbittorrent-api 2026.8.1 无 torrents_peers 方法, 旧调用线上
        AttributeError): 响应整包含 rid/full_update/peers/peers_removed, 前端对 peers 键
        做 dict/数组双形态归一。
        """
        manager.touch_web_client()
        _require_torrent(hash)
        return dict(_require_client().sync_torrent_peers(torrent_hash=hash) or {})

    @app.get("/api/stats")
    def api_stats():
        """qB 全局状态(sync/maindata 的 server_state: 会话/累计流量/DHT 节点/连接状态等)

        数据源是主循环增量同步时原子替换的只读引用; 降级全量(无 sync 端点)或
        尚未同步到响应时为 null, 前端按空态渲染。
        """
        manager.touch_web_client()
        return {"server": manager.store.server_state}

    # ---- 管理端点(R2B: 分类/标签/限速覆盖/添加种子/导出/日志) ----

    @app.get("/api/categories")
    def api_categories_list():
        """全部分类(name -> {save_path,...}, 读 store 缓存; 首次访问可能触发一次 qB 拉取)"""
        manager.touch_web_client()
        return {"categories": manager.api.torrents_categories()}

    @app.get("/api/tags")
    def api_tags_list():
        """全部标签(读 store 缓存)"""
        manager.touch_web_client()
        return {"tags": manager.api.torrents_tags()}

    @app.post("/api/categories")
    def api_category_create(body: dict = None):
        b = body or {}
        name = str(b.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="分类名不能为空")
        return _enqueue("create_category", {"name": name, "save_path": str(b.get("save_path") or "").strip()})

    @app.post("/api/categories/edit")
    def api_category_edit(body: dict = None):
        b = body or {}
        name = str(b.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="分类名不能为空")
        return _enqueue("edit_category", {"name": name, "save_path": str(b.get("save_path") or "").strip()})

    @app.post("/api/categories/remove")
    def api_category_remove(body: dict = None):
        names = [str(n).strip() for n in ((body or {}).get("names") or []) if str(n).strip()]
        if not names:
            raise HTTPException(status_code=400, detail="未提供要删除的分类")
        return _enqueue("remove_categories", {"names": names})

    @app.post("/api/tags")
    def api_tags_create(body: dict = None):
        tags = [str(t).strip() for t in ((body or {}).get("tags") or []) if str(t).strip()]
        if not tags:
            raise HTTPException(status_code=400, detail="未提供要新建的标签")
        return _enqueue("create_tags", {"tags": tags})

    @app.post("/api/tags/remove")
    def api_tags_remove(body: dict = None):
        tags = [str(t).strip() for t in ((body or {}).get("tags") or []) if str(t).strip()]
        if not tags:
            raise HTTPException(status_code=400, detail="未提供要删除的标签")
        return _enqueue("delete_tags", {"tags": tags})

    @app.get("/api/speed/mode")
    def api_speed_mode():
        """限速托管状态(D2): 曲线目标来自限速曲线任务快照(_traffic_view);
        qB 当前全局限速直读(只读, 无状态副作用 —— 与 peers 透传同一先例)"""
        manager.touch_web_client()
        view = manager._traffic_view
        curve_enabled = view.get("state") not in (None, "", "disabled")
        # 曲线存在但 enabled=False: 功能整体停用, 视为未启用(快照滞后/未发布时也兜底正确)
        gslc = manager.config.global_speed_limit_curve
        if gslc is not None and not gslc.enabled:
            curve_enabled = False
        target = None
        if curve_enabled:
            t = (view.get("limit") or {}).get("target") or {}
            target = {"upload_kib": t.get("up"), "download_kib": t.get("down")}
        current = None
        if manager.client is not None:
            try:
                current = manager.api.get_global_speed_limits()
            except Exception:
                current = None
        return {"curve_enabled": curve_enabled, "curve_target": target, "current": current}

    @app.post("/api/speed/override")
    def api_speed_override(body: dict = None):
        """全局限速手动覆盖(D2 语义): 曲线启用时为临时覆盖(下一档位切换恢复), 停用即常态设置"""
        b = body or {}
        return _enqueue(
            "speed_override", {
                "upload_kib": int(b.get("upload_kib") or 0),
                "download_kib": int(b.get("download_kib") or 0),
            }
        )

    @app.post("/api/torrents/add")
    def api_torrents_add(body: dict = None):
        """添加种子(JSON): .torrent 文件由前端 FileReader 读取为 base64 随 JSON 提交,
        后端解码后经命令队列内存直传 qB(qbittorrent-api 原生支持 bytes) ——
        零临时文件、零额外依赖(multipart 需要 python-multipart, 不引入); 布尔字段为真布尔"""
        import base64

        b = body or {}
        file_payload: List[bytes] = []
        for item in b.get("files_b64") or []:
            try:
                data = base64.b64decode(str(item), validate=False)
            except Exception:
                raise HTTPException(status_code=400, detail="torrent 文件 base64 解码失败")
            if data:
                file_payload.append(data)
        url_list = [u.strip() for u in (b.get("urls") or []) if str(u).strip()]
        if not file_payload and not url_list:
            raise HTTPException(status_code=400, detail="未提供 .torrent 文件或 magnet/URL")
        return _enqueue(
            "add_torrents", {
                "files": file_payload,
                "urls": url_list,
                "save_path": str(b.get("save_path") or "").strip(),
                "category": str(b.get("category") or "").strip(),
                "tags": [str(t).strip() for t in (b.get("tags") or []) if str(t).strip()],
                "paused": bool(b.get("paused")),
                "skip_checking": bool(b.get("skip_checking")),
                "sequential": bool(b.get("sequential")),
                "first_last_piece_prio": bool(b.get("first_last_piece_prio")),
                "auto_tmm": bool(b.get("auto_tmm")),
            }
        )

    @app.get("/api/torrents/{hash}/export")
    def api_torrent_export(hash: str):
        """导出 .torrent(QbApi 透传原始字节): Content-Disposition 附种子名(浏览器下载)"""
        manager.touch_web_client()
        rec = _require_torrent(hash)
        client = _require_client()
        data = client.torrents_export(torrent_hash=hash)
        return Response(
            content=data,
            media_type="application/x-bittorrent",
            headers={"Content-Disposition": content_disposition(rec.name or "", hash, "torrent")},
        )

    @app.get("/api/log")
    def api_log(lines: int = 200, level: str = ""):
        """auto-qb 自身日志 tail(只读; qB 日志不在范围)。level 按 [LEVEL] 标记过滤;
        日志文件未配置/不存在时返回空列表(前端空态)。"""
        manager.touch_web_client()
        path = getattr(manager.config.logging, "file", "") or ""
        out: List[str] = []
        if path and os.path.isfile(path):
            n = max(10, min(int(lines or 200), 2000))
            with open(path, "rb") as f:
                raw = f.read()[-256 * 1024:]
            all_lines = [ln for ln in raw.decode("utf-8", errors="replace").splitlines() if ln.strip()]
            lv = (level or "").strip().upper()
            if lv:
                all_lines = [ln for ln in all_lines if f"[{lv}" in ln]
            out = all_lines[-n:]
        return {"lines": out, "file": path}

    @app.get("/api/cmd/{cmd_id}")
    def api_cmd_result(cmd_id: str):
        """命令执行结果查询(前端投递后轮询): pending = 主循环尚未执行完或仍在确认中

        reannounce 的回执由主循环的 tracker 确认跟踪器在确认成功/失败/超时后写入,
        其余命令执行完立即写入。结果只由主循环线程写, 此处只读。
        """
        manager.touch_web_client()
        result = manager._web_results.get(cmd_id)
        return dict(result) if result else {"status": "pending"}

    @app.get("/api/traffic/history")
    def api_traffic_history():
        """历史流量按日行(dat 原始数据, 升序): 供前端历史流量柱状图按天/月/年聚合

        数据源是限速曲线任务每轮发布的只读快照(_traffic_view["history"]), Web 线程只读;
        未启用限速曲线或数据源不可用时 history 为空数组, state 供前端判断展示分支。
        """
        manager.touch_web_client()
        view = manager._traffic_view
        return {"state": view.get("state"), "history": view.get("history") or []}

    @app.get("/api/config/schema")
    def api_config_schema():
        """配置表单元数据(分组/字段/控件/帮助) + 热重载级别(唯一来源: config.impact)"""
        from .config import schema as config_schema
        from .config.impact import SECTION_LEVELS, TRACKER_FIELD_LEVELS

        payload = config_schema.schema_payload()
        # 级别表由 impact 单一维护(与热重载实际分级同源), API 层只做合并
        payload["levels"] = {"sections": SECTION_LEVELS, "tracker_fields": TRACKER_FIELD_LEVELS}
        return payload

    @app.get("/api/config")
    def api_config_get():
        """当前配置树(YAML 同构, 标量为字符串) + 写盘路径

        敏感字段(qB 密码 / tracker passkey / WEB 密钥)按**键名**掩码为 MASK_SENTINEL: 明文
        进浏览器内存、截图与日志即为凭据泄漏。保存时 PUT 会用磁盘旧值还原哨兵 —— 掩码只影响
        展示, 不会把密码写死成占位串。
        """
        from .config.writer import MASK_SENTINEL, mask_tree, read_tree

        return {
            "tree": mask_tree(read_tree(manager.config_path)),
            "path": manager.config_path,
            "masked": True,
            "mask_sentinel": MASK_SENTINEL,
        }

    @app.put("/api/config")
    def api_config_put(body: dict):
        """保存图形化配置: 结构校验(与启动同路径) -> R 级字段回退 -> round-trip 写盘 -> 投递热重载

        校验失败不触碰磁盘; R 级字段(state_file/data_dir)保留旧值, 其余立即生效。
        提交树里的掩码哨兵先按磁盘旧值还原(见 api_config_get), 未修改的密码保持原值。
        """
        from .config.errors import ConfigError
        from .config.loaders import load_config
        from .config.writer import read_tree, unmask_tree, write_tree

        tree = (body or {}).get("tree")
        if not isinstance(tree, dict):
            raise HTTPException(status_code=400, detail="tree 必须是对象")
        unmask_tree(tree, read_tree(manager.config_path))
        try:
            result = write_tree(manager.config_path, tree, manager.config, _config_backup_path(manager))
        except (ConfigError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))

        # 投递热重载(主循环线程应用; R 级字段已在树中回退为旧值)
        _enqueue("reload_config", {"config": load_config(manager.config_path)})
        return {
            "applied": True,
            "changes": [{
                "path": c.path,
                "level": c.level
            } for c in result.changes],
            "restart_required": result.restart_required,
        }

    @app.post("/api/config/preview")
    def api_config_preview(body: dict):
        """只读预览: 返回"即将写入"的 YAML 文本(不落盘、不投递热重载), 校验口径与保存一致

        与 PUT 同口径: 先还原掩码哨兵, 否则预览里会显示一串占位符(与实际写入结果不符)。
        """
        from .config.errors import ConfigError
        from .config.writer import preview_tree, read_tree, unmask_tree

        tree = (body or {}).get("tree")
        if not isinstance(tree, dict):
            raise HTTPException(status_code=400, detail="tree 必须是对象")
        unmask_tree(tree, read_tree(manager.config_path))
        try:
            text = preview_tree(manager.config_path, tree, manager.config)
        except (ConfigError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"yaml": text}

    # 静态前端(UI 目录化: atlas=星图(旧) / prism=棱镜(新) / shared=公共逻辑层; 目录即 URL,
    # 新增 UI = static/<名字>/ 一个目录, 无需后端改动)
    static_dir = os.path.join(os.path.dirname(__file__), "web_ui", "static")
    if os.path.isdir(static_dir):

        @app.get("/", include_in_schema=False)
        async def _ui_root() -> RedirectResponse:
            """根路径进默认 UI(星图): StaticFiles 根下已无 index.html, 由重定向兜底。"""
            return RedirectResponse("/atlas/", status_code=307)

        @app.get("/newui", include_in_schema=False)
        @app.get("/newui/{rest:path}", include_in_schema=False)
        async def _newui_legacy(rest: str = "") -> RedirectResponse:
            """旧 /newui/* 书签兼容: 307 到 /prism/*(观察一轮后可撤)。"""
            return RedirectResponse(f"/prism/{rest}", status_code=307)

        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

        @app.middleware("http")
        async def _static_no_cache(request, call_next):
            """静态资源禁用启发式缓存(不加 Cache-Control 时浏览器会自行缓存数小时)

            症状: 升级程序后仍加载旧 app.js/style.css, 界面“改了但没变”。
            用 no-cache(仍允许存储, 但每次必须带 ETag 重新校验): 未变更走 304, 变更为新内容。
            仅作用于非 /api 响应, 不影响接口语义。
            """
            response = await call_next(request)
            if not request.url.path.startswith("/api"):
                response.headers["Cache-Control"] = "no-cache"
            return response

    return app


class WebServerHandle:
    """WEB 服务器句柄(uvicorn 独立线程)

    stop() 仅请求退出(异步: uvicorn 主循环每 0.1s 才读一次 should_exit, 随后才关闭监听套接字);
    wait() 等待服务线程真正退出。**重启同端口必须 stop 后 wait**, 否则新服务 bind 报
    Errno 10048(每个套接字地址只允许使用一次)。
    """

    __slots__ = ("server", "thread")

    def __init__(self, server: uvicorn.Server, thread: threading.Thread) -> None:
        self.server = server
        self.thread = thread

    def stop(self) -> None:
        """请求停止(返回时服务仍在退出中, 需 wait() 确认已释放端口)"""
        self.server.should_exit = True

    def wait(self, timeout: Optional[float] = None) -> bool:
        """等待服务线程退出; 返回是否已退出(False = 超时仍在运行)"""
        self.thread.join(timeout)
        return not self.thread.is_alive()

    @property
    def started(self) -> bool:
        """监听是否已就绪(uvicorn 在 create_server 成功后置位)"""
        return bool(self.server.started)


def _run_server(server: uvicorn.Server) -> None:
    """服务线程入口: 把 uvicorn 的失败退出记进日志

    bind 失败时 uvicorn 走 sys.exit(STARTUP_FAILURE), 而 SystemExit 在非主线程被 threading
    静默吞掉(只剩 uvicorn 自己那行无时间戳的 ERROR), 日志上看不出"WEB UI 已经死了"。
    这里就地记录(含异常链: OSError -> SystemExit)后不再上抛 —— 上抛同样被吞, 只会多一份噪音。
    """
    try:
        server.run()
    except BaseException:
        logger.error("WEB UI 服务异常退出(端口被占用/监听失败?)", exc_info=True)


def _wait_until_started(handle: WebServerHandle, timeout: float) -> bool:
    """等待监听就绪: server.started 置位即成功; 线程提前退出(启动失败)/超时返回 False"""
    deadline = time.monotonic() + timeout
    while not handle.started:
        if not handle.thread.is_alive():
            return False
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.01)
    return True


def start_web_server(manager) -> WebServerHandle:
    """启动 WEB 服务器(独立线程); 返回句柄(stop()/wait())

    就绪(或确认失败)后才打日志: 起线程后立即打印会掩盖 bind 失败(端口被占用时依然显示"已启动")。
    """
    manager._web_token = ensure_web_token(manager)
    app = create_app(manager)
    config = uvicorn.Config(
        app,
        host=manager.config.web.host,
        port=manager.config.web.port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=_run_server, args=(server, ), name="auto-qb-web", daemon=True)
    thread.start()
    handle = WebServerHandle(server, thread)
    if _wait_until_started(handle, WEB_START_TIMEOUT):
        logger.warning(
            f"WEB UI 已启动: http://{manager.config.web.host}:{manager.config.web.port} "
            f"(密钥见 {os.path.join(os.path.dirname(manager.state_file) or '.', 'web.token')})"
        )
    else:
        logger.error(
            f"WEB UI 启动失败: {manager.config.web.host}:{manager.config.web.port} 无法监听"
            "(端口被占用? 详见上方 uvicorn 错误)"
        )
    return handle


def stop_web_server(handle: WebServerHandle, timeout: float = WEB_STOP_TIMEOUT) -> bool:
    """请求停止并等待服务线程退出; 返回是否已退出(False = 超时仍在运行, 调用方自行决定)

    热重载重启(host/port 变更)必须先走本函数: 只 handle.stop() 就立刻启新服务,
    旧服务的监听套接字尚未释放 -> Errno 10048。
    """
    handle.stop()
    if handle.wait(timeout):
        return True
    logger.warning(f"WEB UI 旧服务在 {timeout:g}s 内未退出, 仍尝试重启(监听套接字通常已释放)")
    return False
