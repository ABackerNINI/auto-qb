"""文件系统路由: /api/paths · /api/fs/dirs · /api/fs/mkdir · /api/open-path(白名单安全边界单点).

端点体逐字平移(plan 26-09-22-1857 W4); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""

import logging
import os
from typing import List
from fastapi import HTTPException

from ....infra.utils import add_long_path_prefix_for_win, path_normalize
from .. import common
from ..common import group_key_param as _group_key_param

from fastapi import APIRouter
from ..context import WebContext

logger = logging.getLogger("auto_qb.web")  # noqa: F401  (mkdir 记录)


def _bare(p: str) -> str:
    """剥掉 Windows 扩展长度前缀 `\\\\?\\`(`\\\\?\\UNC\\` 还原成 `\\\\`), 非 Windows/无前缀原样返回

    `\\\\?\\` 会让同一个路径**有两种写法**, 而比较与返回都只认一种:
    - `os.path.normcase` **不会**剥它 ⇒ 前缀差异会被当成"不同路径"(见 `_fs_real`);
    - `path_normalize` 更危险: 它先把 `\\` 折成 `/` 再压重复斜杠 ⇒ `\\\\?\\H:\\a` 变成
      `/?/H:/a`(**损坏**) ⇒ 所以必须先剥再规范化。

    放在模块级(而非 `build_router` 闭包内)是为了能在**任何平台**上单测这条归一契约 ——
    真前缀只在 Windows 上出现, 留在闭包里就只剩 Windows 上才守得住(见 test_web 的对应用例)。
    """
    if p.startswith("\\\\?\\UNC\\"):
        return "\\\\" + p[8:]
    return p[4:] if p.startswith("\\\\?\\") else p


def _fs(p: str) -> str:
    """**本地文件系统调用**用路径: 规范化分隔符 + Windows 长路径前缀(非 Windows 是空操作)。

    长路径(>MAX_PATH 260)在未开长路径支持的机器上裸路径一律失败(`isdir` 给假 /
    `scandir` 抛 WinError 3 / `mkdir` 抛 OSError) ⇒ 所有真实 syscall 都必须过这里。
    ⚠ 前缀**只用于本地调用**: 返回值仍取未加前缀的 `target`, 否则前端会把前缀回传、
    甚至写进 save_path。入参先过 `_bare` ⇒ 本函数**幂等**(重复加前缀不会叠加/损坏)。
    """
    return add_long_path_prefix_for_win(path_normalize(_bare(p)))


def _fs_real(p: str) -> str:
    """规范化到可比较的绝对真实路径(realpath 解符号链接, normcase 在 Windows 上统一大小写/斜杠)

    ❗必须**先剥 `\\\\?\\` 前缀**: 比较双方可能一侧带前缀(如 `os.scandir(_fs(target))` 给出的
    `entry.path`)、一侧不带(如允许根) —— 不剥就会因前缀差异被判成"越界", 实测后果是
    **子目录被全部过滤掉**(目录树恒空)。realpath 是否保留前缀**与路径长度有关**
    (实测短路径保留、长路径剥掉), 不能依赖它。

    ⚠ 已知限制(实测, 本次不改): `os.path.realpath` 对 >MAX_PATH 的路径**静默退化成 abspath**
    (不抛错) ⇒ 长路径上的符号链接/junction 解析不可用, 逃逸防护退化为词法比较。
    两侧都过 normcase, 大小写差异不会误判。
    """
    return os.path.normcase(os.path.realpath(_bare(p)))


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    _require_torrent = ctx.require_torrent
    logger = logging.getLogger("auto_qb.web")
    router = APIRouter()

    # 同 /api/state: 返回裸 dict 会让 FastAPI 白跑一遍 jsonable_encoder(见 api_state 注释)

    @router.get("/api/paths")
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

    def _within_roots(target: str, roots: List[str]) -> bool:
        """目标是否落在某个允许根内(相等或为其子目录) —— 越界一律拒绝"""
        t = _fs_real(target)
        for r in roots:
            rr = _fs_real(r)
            if t == rr or t.startswith(rr.rstrip("\\/") + os.sep):
                return True
        return False

    @router.get("/api/fs/dirs")
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
        if not os.path.isdir(_fs(target)):
            raise HTTPException(status_code=404, detail="目录不存在或不可访问")
        dirs = []
        try:
            with os.scandir(_fs(target)) as it:
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

    @router.post("/api/fs/mkdir")
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
        if not os.path.isdir(_fs(base)):
            raise HTTPException(status_code=404, detail="目录不存在或不可访问")
        target = os.path.join(base, name)
        if os.path.exists(_fs(target)):
            if os.path.isdir(_fs(target)):
                return {"created": path_normalize(target), "existed": True}
            raise HTTPException(status_code=409, detail="同名文件已存在")
        try:
            os.mkdir(_fs(target))
        except OSError as e:
            raise HTTPException(status_code=400, detail=f"新建失败: {e.strerror or e}")
        logger.info(f"WEB 新建目录: {target}")
        return {"created": path_normalize(target), "existed": False}

    @router.post("/api/open-path")
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
            if content and not os.path.isdir(_fs(content)):
                target, select = content, True  # 单文件种子: 定位选中, 不降级成"只打开父目录"
            else:
                target = content or path_normalize(rec.save_path or "")
        else:
            raise HTTPException(status_code=400, detail="kind 必须是 group 或 torrent")
        target = path_normalize(target)
        if select:
            if not os.path.isfile(_fs(target)):
                raise HTTPException(status_code=404, detail="目标文件不存在或不可访问")
        elif not target or not os.path.isdir(_fs(target)):
            raise HTTPException(status_code=404, detail="目标目录不存在或不可访问")
        common.open_path(target, select=select)
        return {"opened": target, "select": select}

    return router
