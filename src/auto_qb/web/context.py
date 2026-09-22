"""路由共享件 WebContext: manager 引用 + 命令投递 + 只读缓存 + 快照判别.

线程模型不变式(与拆分前一致, 见包 __init__ docstring): 请求处理器只读快照 + 投递命令,
写操作只在主循环线程。RoCache 与 auth 的"免鉴权只记一次"标志同样是**每 app 实例一份**
(测试会对同一 manager 多次 create_app), 不得提升为模块级全局(决策 K4)。
"""
import threading
import time

from fastapi import HTTPException


class RoCache:
    """Web 线程"直连 qB"只读端点的短缓存。

    P1-4: 打开抽屉会连打一串这类请求(trackers / files / peers + categories / tags),
    加 1~2s TTL 后同一时间窗内的重复请求合并为一次 qB 调用。数据最多旧 1~2s ——
    抽屉是观察用途, 可接受。
    ❗失效靠 `manager._web_write_seq`(任何写命令执行成功即自增, 见 WebCommandsMixin):
    不加这道保险会出现"刚改完文件优先级、重取还拿到缓存旧值"这种**看起来没生效**的假象。
    """
    def __init__(self, manager) -> None:
        self._manager = manager
        self._cache: dict = {}
        self._lock = threading.Lock()
        self.ttl = 2.0  # 秒; peers 更"活", 调用方以 ttl 参数单独用更短的窗口

    def get(self, key: str, fn, ttl: float = None):
        """带写失效的短缓存: 键里带上写序号, 任何写命令后自动换键(= 缓存失效)"""
        if ttl is None:
            ttl = self.ttl
        full_key = (key, getattr(self._manager, "_web_write_seq", 0))
        now = time.time()
        with self._lock:
            hit = self._cache.get(full_key)
            if hit is not None and now - hit[0] < ttl:
                return hit[1]
            if len(self._cache) > 128:  # 防无界增长: 只留新鲜的
                self._cache.clear()
        value = fn()
        with self._lock:
            self._cache[full_key] = (time.time(), value)
        return value


class WebContext:
    """一次 create_app 一个实例, 各 routes 模块经 build_router(ctx) 共享。"""
    def __init__(self, manager) -> None:
        self.manager = manager
        self.ro_cache = RoCache(manager)

    # ---- 原 create_app 闭包件逐字平移(仅 manager → self.manager) ----

    def cached_read(self, key: str, fn, ttl: float = None):
        """带写失效的短缓存(RoCache.get 转发; 原 create_app._cached_read)"""
        return self.ro_cache.get(key, fn, ttl)

    def enqueue(self, cmd: str, payload: dict) -> dict:
        """投递控制命令: 经表现层门面(生成 cmd_id / 入队 / 按需唤醒), 返回 cmd_id 供前端轮询

        投递的三种语义(生成回执 ID、埋点时间戳、自投递不唤醒)统一在
        `WebUIRuntime.post_command` —— Web 传输层不再自己拼命令体, 避免两处判据漂移。
        """
        return self.manager.web.post_command(cmd, payload)

    def require_torrent(self, hash: str):
        """hash 不在快照 -> 404(原 create_app._require_torrent)"""
        rec = self.manager.store.get(hash)
        if rec is None:
            raise HTTPException(status_code=404, detail="种子不存在")
        return rec

    def require_client(self):
        """qB 断连 -> 503(原 create_app._require_client)"""
        if self.manager.client is None:
            raise HTTPException(status_code=503, detail="qB 未连接")
        return self.manager.client
