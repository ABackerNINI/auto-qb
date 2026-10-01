"""鉴权单点: require_token 依赖工厂(plan 26-09-22-1857 决策 K2).

原 create_app 内联闭包改工厂: ``make_require_token(manager)`` 返回依赖函数,
"免鉴权提示只记一次"标志经闭包保持**每 app 实例一份**(测试会对同一 manager 多次
create_app, 不得提升为模块级全局)。鉴权语义逐字保留: /api/config/public 免 token;
web.skip_local_verify=true 时 loopback 免密钥(INFO 只记一次); 非 /api 路径放行;
SSE ?token= 查询串兜底; compare_digest 防时序侧信道; 错密钥恰好一条不含密钥内容的 WARNING。

跨站防护(issue 26-09-21-1408): skip_local_verify **开启**时, 无凭证请求先过
``_reject_cross_site`` —— Host 白名单(全部路径, 废 DNS rebinding)+ 写方法 Origin
同源(废 CSRF), 403 明确拒绝; 默认关闭路径行为零变化。

!本模块 logger 显式取名 "auto_qb.web"(见包 __init__ K3) —— tests/test_web.py 按
  ``r.name == "auto_qb.web"`` 断言 caplog 记录, 用 __name__ 会漂移必红。
"""
import logging
import secrets
from typing import Optional, Tuple
from urllib.parse import urlsplit

from fastapi import Header, HTTPException, Request

logger = logging.getLogger("auto_qb.web")

# 视为"写动作"的 HTTP 方法: CSRF 的危害面 = 跨站可驱动的状态变更。按方法守而不按路由
# 清单逐个守 —— 闸门挂在全局依赖单点上, 今后新增任何写端点自动进覆盖面
_WRITE_METHODS = frozenset({"POST", "PUT", "DELETE", "PATCH"})

# loopback 主机名的合法书写变体(与 _is_loopback_host 的地址集对齐; localhost 是
# 浏览器把 127.0.0.1/::1 解析后的常客, Host 头里两者都可能出现)
_LOOPBACK_HOSTNAMES = frozenset({"localhost", "127.0.0.1", "::1", "::ffff:127.0.0.1"})


def _is_loopback_host(host) -> bool:
    """是否为本机 loopback 地址: 仅 127.0.0.1 / ::1 及其 IPv4-mapped 形式"""
    if not host:
        return False
    return host in ("127.0.0.1", "::1", "::ffff:127.0.0.1")


def _host_header_parts(host_header: str) -> Tuple[str, Optional[int]]:
    """Host 头 -> (hostname, port|None): urlsplit 兜着处理 [::1]:8787 / host:port 形态

    解析失败回 ("", None) —— 调用方按"不在白名单"拒绝(fail-closed)。
    """
    try:
        parts = urlsplit("//" + (host_header or "").strip())
        return (parts.hostname or ""), parts.port
    except ValueError:
        return "", None


def _allowed_hostnames(config_host: str) -> frozenset:
    """Host/Origin 白名单: loopback 变体 + 用户自配监听地址(合法变体都放行)"""
    hosts = set(_LOOPBACK_HOSTNAMES)
    if config_host and config_host.strip():
        hosts.add(config_host.strip().strip("[]").lower())
    return frozenset(hosts)


def _origin_allowed(origin: str, allowed: frozenset, host_port: Optional[int]) -> bool:
    """Origin 是否可放行: http(s) 且 host 在白名单, 且(可判定时)端口与 Host 头一致

    Origin 由浏览器控制, 攻击页无法伪造成白名单 host —— host 命中白名单即排除
    evil.com 类跨站; 端口一致性是余量防线(Host 缺省端口时不判定, 放宽)。
    """
    try:
        parts = urlsplit(origin)
    except ValueError:
        return False
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    if parts.hostname not in allowed:
        return False
    origin_port = parts.port or (443 if parts.scheme == "https" else 80)
    return host_port is None or origin_port == host_port


def _log_reject(reason: str, value: str) -> None:
    """拒绝留痕: 值经白名单化(防日志注入)并截断; WARNING 与错密钥同级(安全信号)"""
    safe = "".join(ch if ch.isalnum() or ch in "._-[]:%" else "?" for ch in value)[:100]
    logger.warning(f"WEB 跨站防护拒绝({reason}): {safe}")


def _reject_cross_site(request: Request, config_host: str) -> None:
    """skip_local_verify 开启时的跨站防护(issue 26-09-21-1408, 只对无凭证请求生效):

    - Host 白名单(全部路径): DNS rebinding 下 attacker.com 指向本机, Host 头是外部域名 ——
      不在白名单一律 403, rebinding 的读写面整体作废;
    - 写方法 Origin 同源: 跨站简单请求(表单/不触发预检的 fetch)浏览器必带外部 Origin,
      删除/暂停/限速等写命令因此被挡在入队之前。
    失败一律 403 明确拒绝, 不静默。!本函数只在 skip_local_verify=true 且请求**未携带任何
    凭证**时被调用 —— 浏览器无法跨站伪造 Authorization/查询串凭证, 持密请求不在
    CSRF/rebinding 威胁模型内, 交由既有 token 逻辑裁决。
    """
    host_header = request.headers.get("host") or ""
    hostname, host_port = _host_header_parts(host_header)
    allowed = _allowed_hostnames(config_host)
    if not hostname or hostname not in allowed:
        _log_reject("Host 不在白名单", host_header)
        raise HTTPException(status_code=403, detail="host not allowed (cross-site protection)")
    if request.method in _WRITE_METHODS:
        origin = request.headers.get("origin") or ""
        if origin and not _origin_allowed(origin, allowed, host_port):
            _log_reject("Origin 跨站", origin)
            raise HTTPException(status_code=403, detail="origin not allowed (cross-site protection)")


def make_require_token(manager):
    """构造 require_token 依赖(factory 里挂 FastAPI 全局 dependencies 单点)"""

    _local_skip_logged = False  # 免鉴权提示每个进程只记一次(见下)

    def require_token(request: Request, authorization: str = Header(default="")):
        nonlocal _local_skip_logged
        # 跨站防护闸(issue 26-09-21-1408): 仅 skip_local_verify **开启**时生效 —— 默认
        # 关闭路径行为零变化; 携带任意凭证(Authorization 头/查询串 token)的请求绕过本闸,
        # 交由下方既有 token 逻辑裁决(凭证是跨站伪造不出来的, 持密即可信方)。
        if manager.config.web.skip_local_verify and not (
            (authorization or "").strip() or (request.query_params.get("token") or "")
        ):
            _reject_cross_site(request, manager.config.web.host)
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
        # SSE(/api/events)用的是 EventSource, **发不出** Authorization 头 —— 允许把密钥放在
        # 查询串 ?token= 上作为兜底。代价: 密钥可能出现在访问日志里; 本机 skip_local_verify
        # 场景(默认)根本走不到这条路径。
        qtok = request.query_params.get("token") or ""
        if qtok and secrets.compare_digest(qtok, manager.web.token):
            return
        scheme = "Bearer "
        if not authorization.startswith(scheme):
            raise HTTPException(status_code=401, detail="invalid token")
        token = authorization[len(scheme):].strip()
        if not token:
            raise HTTPException(status_code=401, detail="invalid token")
        if not secrets.compare_digest(token, manager.web.token):
            logger.warning("WEB 鉴权失败: 密钥不匹配")
            raise HTTPException(status_code=401, detail="invalid token")

    return require_token
