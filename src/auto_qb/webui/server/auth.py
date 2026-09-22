"""鉴权单点: require_token 依赖工厂(plan 26-09-22-1857 决策 K2).

原 create_app 内联闭包改工厂: ``make_require_token(manager)`` 返回依赖函数,
"免鉴权提示只记一次"标志经闭包保持**每 app 实例一份**(测试会对同一 manager 多次
create_app, 不得提升为模块级全局)。鉴权语义逐字保留: /api/config/public 免 token;
web.skip_local_verify=true 时 loopback 免密钥(INFO 只记一次); 非 /api 路径放行;
SSE ?token= 查询串兜底; compare_digest 防时序侧信道; 错密钥恰好一条不含密钥内容的 WARNING。

❗本模块 logger 显式取名 "auto_qb.web"(见包 __init__ K3) —— tests/test_web.py 按
  ``r.name == "auto_qb.web"`` 断言 caplog 记录, 用 __name__ 会漂移必红。
"""
import logging
import secrets

from fastapi import Header, HTTPException, Request

logger = logging.getLogger("auto_qb.web")


def _is_loopback_host(host) -> bool:
    """是否为本机 loopback 地址: 仅 127.0.0.1 / ::1 及其 IPv4-mapped 形式"""
    if not host:
        return False
    return host in ("127.0.0.1", "::1", "::ffff:127.0.0.1")


def make_require_token(manager):
    """构造 require_token 依赖(factory 里挂 FastAPI 全局 dependencies 单点)"""

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
        # SSE(/api/events)用的是 EventSource, **发不出** Authorization 头 —— 允许把密钥放在
        # 查询串 ?token= 上作为兜底。代价: 密钥可能出现在访问日志里; 本机 skip_local_verify
        # 场景(默认)根本走不到这条路径。
        qtok = request.query_params.get("token") or ""
        if qtok and secrets.compare_digest(qtok, manager._web_token):
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

    return require_token
