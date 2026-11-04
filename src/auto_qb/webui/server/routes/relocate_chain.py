"""路径链读取端点: `GET /api/relocate/chain?hash=...`(计划 26-11-04-1042 P2-1)

只收 hash: 起点由服务端从种子记录派生(root_path / content_path 优先, 回退 save_path),
客户端传路径参数一律忽略 —— 避免把文件系统探测变成任意路径读。
403 门控与 fs.py 的允许根白名单同口径; 结果短缓存, refresh=1 强制重探。
"""
import re
from typing import List

from fastapi import APIRouter, HTTPException

from ....infra import alias_fs, file_access
from ..context import WebContext
from .fs import browse_roots
from ... import relocate_chain
from .torrent_cmds import _require_relocate

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
        # Local qB 也可能配 UNC 保存路径: 判 remote 前不得在本机 lstat 远端路径
        # (共享不可达时 lstat 会长时间阻塞线程池; 计划 4.1「远端不做 syscall」)
        if alias_fs.is_unc(candidate):
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
        elif alias_fs.is_unc(start):
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
        return result

    return router
