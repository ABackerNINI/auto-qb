"""qB 客户端构造: 本地地址关闭 requests trust_env 的会话策略

从 qbmanager.py 拆出(2026-09-15 大文件拆分批次一): 客户端构造与主循环/任务队列无关,
单独成模块便于 test_local_qb_service 等直接导入。
"""
from urllib.parse import urlparse

from qbittorrentapi import Client

from .config import QbittorrentConfig

# 本地 qB 地址(关闭 requests trust_env: 环境代理与 ~/.netrc 解析对本机连接无意义)
_LOCAL_HOSTS = frozenset(("127.0.0.1", "localhost", "::1"))
def _is_local_qb(qb: QbittorrentConfig) -> bool:
    """qB 地址是否指向本机(取 base_url 解析后的 hostname, 兼容带端口/带协议写法)"""
    return urlparse(qb.base_url).hostname in _LOCAL_HOSTS
class LocalQbClient(Client):
    """本地 qB 客户端: 每个(重)建的 requests Session 都强制关闭 trust_env

    背景: 打开 trust_env 时 requests 每次请求都要解析环境代理(get_environ_proxies ->
    proxy_bypass_registry 读注册表)与 ~/.netrc(get_netrc_auth 走 expanduser + os.path.exists),
    对 127.0.0.1/localhost 连接毫无意义(实测单请求 0.276ms -> 0.043ms)。

    ❗为什么不"连上后给 client._session.trust_env 赋 False": 库的 `Request._session` 是**只读
    property**(qbittorrentapi/request.py), 且库在 `build_base_url()`(首次请求)与
    `_initialize_context()`(登录过期/qB 重启)中都会调用 `_trigger_session_initialization()`
    **丢弃当前 Session 并在下次访问时重建** —— 旧实现赋的值在第一次真实请求时即被清除
    (静默失效, 从未生效过; 实测: 赋值后触发重建 -> trust_env 回到 True 且对象已换)。
    此处改为覆盖 property, 在返回前强制关闭, 因此对任何时刻新建的 Session 都生效。

    仅本地地址使用本子类, 远程/域名连接保留 requests 默认行为(企业代理/~/.netrc 可能真实需要)。
    """
    @property
    def _session(self):
        session = super()._session
        session.trust_env = False
        return session
def _new_client(qb: QbittorrentConfig) -> Client:
    """按配置构造 qB 客户端(本地地址用关闭 trust_env 的 LocalQbClient)"""
    cls = LocalQbClient if _is_local_qb(qb) else Client
    return cls(host=qb.base_url, username=qb.username, password=qb.password)
