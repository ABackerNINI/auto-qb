"""路径链读取端点: `GET /api/relocate/chain?hash=...`(计划 26-11-04-1042 P2-1)

只收 hash: 起点由服务端从种子记录派生(root_path / content_path 优先, 回退 save_path),
客户端传路径参数一律忽略 —— 避免把文件系统探测变成任意路径读。
403 门控与 fs.py 的允许根白名单同口径; 结果短缓存, refresh=1 强制重探。

S3 追加(计划 26-11-05-0808): 链结果附带 `finalize` 收尾反馈面(pending/daemon_stale/
window, §3.2「失败反馈面」行); `POST /api/relocate/finalize-now` = D14「立即收尾」按钮
(显式确认 → qB app/shutdown → 回收 daemon 捕窗改写 → 用户手动重启 qB)。
"""
import re
from typing import List

from fastapi import APIRouter, HTTPException

from ....core.modules.relocate_units import FINALIZE_WINDOW_PHASES as _WINDOW_PHASES
from ....infra import alias_fs, file_access
from ..context import WebContext
from .fs import browse_roots
from ... import relocate_chain
from .torrent_cmds import _require_relocate

#: D14 现场说明(显式确认框的权威文案; §07 风险表「按钮误触」行: 关闭 qB / 改写 / 需手动重启)
_FINALIZE_NOW_NOTE = ("将向 qB 下达关闭指令: qB 退出后, 回收 daemon 会在下线窗口改写成员 fastresume 指向新位置; "
                      "改写完成后需要你手动重启 qB。期间该组不可用。")

#: 只接受 v1(40) / v2(64) 十六进制 infohash; 其它形态(含路径分隔符)直接 422
_HASH_RE = re.compile(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}")


def _start_path(rec, roots: List[str], mapped: bool) -> str:
    """从种子记录派生探测起点: root_path / content_path 优先, 回退 save_path

    Local 下优先取**实际可用**的候选(存在且可 lstat); 全都不可用时返回首选候选,
    让链结果如实显示「路径不存在」而不是随手换一个路径假装成功。
    Mapped 不做 syscall, 直接按偏好取第一个非空值。
    """
    candidates = []
    for attr in ("root_path", "content_path", "save_path"):
        value = alias_fs.strip_device_prefix(str(getattr(rec, attr, "") or ""))
        if value:
            candidates.append(value)
    if not candidates:
        return ""
    if mapped:
        return candidates[0]
    for candidate in candidates:
        if not relocate_chain.path_within_roots(candidate, roots):
            continue
        # Local qB 也可能配 UNC / 盘符映射的网络盘保存路径: 判 remote 前不得在本机 lstat
        # (共享不可达时 lstat 会长时间阻塞线程池; 计划 4.1「远端不做 syscall」)
        if alias_fs.is_remote_path(candidate):
            return candidate
        if alias_fs.inspect_path(candidate).status == "ok":
            return candidate
    return candidates[0]


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    cache = relocate_chain.make_cache()
    router = APIRouter()

    @router.get("/api/relocate/chain")
    def api_relocate_chain(hash: str = "", refresh: int = 0):
        """A -> B -> C 路径链(只读; 只由浮窗打开/显式刷新触发)"""
        _require_relocate(ctx)
        if not _HASH_RE.fullmatch(hash or ""):
            raise HTTPException(status_code=422, detail="hash 参数非法(只接受 40/64 位十六进制种子 hash)")
        rec = ctx.require_torrent(hash)
        fa = file_access.get_file_access()
        mapped = isinstance(fa, file_access.MappedFileAccess)
        roots = browse_roots(manager)
        start = _start_path(rec, roots, mapped)

        env = relocate_chain.ENV_LOCAL
        if mapped:
            env = relocate_chain.ENV_MAPPED
        elif alias_fs.is_remote_path(start):
            env = relocate_chain.ENV_REMOTE

        mod = getattr(getattr(manager, "ctx", None), "relocate", None)
        getter = getattr(mod, "jobs_snapshot", None)
        snapshot = getter() if callable(getter) else None
        alias_index = relocate_chain.build_alias_index(snapshot, hash)
        generation = int(getattr(snapshot, "generation", 0) or 0)
        key = f"{hash}|{start}|{env}|{generation}"

        def _load():
            result = relocate_chain.probe_chain(start, roots, alias_index, hash, env=env)
            result["hash"] = hash
            return result

        result, cached = cache.get(key, _load, refresh=bool(refresh))
        result["cached"] = cached
        # 收尾反馈面不进缓存: pending/daemon_stale 随心跳与改写随时变, TTL 20s 的旧值会
        # 误导「立即收尾」按钮判据 —— 每次现读(文件读侧原子, 与链探测同级的按需成本)
        job = relocate_chain.pick_job_for(snapshot, hash)
        if job is not None:
            data_dir = str(getattr(getattr(manager, "config", None), "data_dir", "") or "auto-qb-data")
            qbt = getattr(getattr(manager, "config", None), "qbittorrent", None)
            host = str(getattr(qbt, "host", "") or "")
            try:
                port = int(getattr(qbt, "port", 0) or 0)
            except (TypeError, ValueError):
                port = 0
            result["finalize"] = relocate_chain.finalize_face(job, data_dir, host, port)
        return result

    @router.post("/api/relocate/finalize-now")
    def api_relocate_finalize_now(body: dict | None = None):
        """D14「立即收尾」(计划 §06 D14 / §07 按钮误触行): 显式确认 → qB app/shutdown →
        回收 daemon 捕窗改写 → 用户手动重启 qB

        保守默认: 不重试、不自动重启; app/shutdown 缺失/被拒/断连一律降级(cls=degraded,
        提示手动重启 qB), HTTP 恒 200 —— 降级是成功的交互结果, 不是服务端错误。
        窗口判据单点 = relocate_units.FINALIZE_WINDOW_PHASES(S4 新相位集 {armed, rewritten}); 服务端按快照
        复核非空才动手, 前端可见性不是授权(与预检-执行无信任传递同口径)。body
        {confirm: bool, job_id?: "..."}; 未确认只回现场说明(cls=confirm, 数据零动作,
        与 relocate_cancel 的成本先行同口径)。
        """
        _require_relocate(ctx)
        b = body or {}
        job_id = str(b.get("job_id") or "").strip()
        if not b.get("confirm"):
            return {"cls": "confirm", "note": _FINALIZE_NOW_NOTE}
        mod = getattr(getattr(manager, "ctx", None), "relocate", None)
        getter = getattr(mod, "jobs_snapshot", None)
        snapshot = getter() if callable(getter) else None
        candidates = [j for j in (getattr(snapshot, "jobs", ()) or ()) if str(j.get("phase") or "") in _WINDOW_PHASES]
        if job_id:
            candidates = [j for j in candidates if str(j.get("job_id") or "") == job_id]
        if not candidates:
            return {"cls": "blocked", "note": "当前没有处于收尾窗口的迁移任务, 无需关闭 qB"}
        client = ctx.require_client()  # 断连即 503: 前端按降级提示手动重启
        try:
            client.app_shutdown()
        except Exception as e:  # noqa: BLE001 - 存在性/被拒/断连统一降级(不重试, D14)
            return {
                "cls": "degraded",
                "note": f"关闭指令未送达({type(e).__name__}), 请手动重启 qB 完成收尾",
            }
        return {"cls": "ok", "note": "已向 qB 下达关闭指令, 待收尾改写完成后请手动重启 qB"}

    return router
