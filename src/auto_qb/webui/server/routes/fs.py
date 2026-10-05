"""文件系统路由: /api/paths · /api/fs/dirs · /api/fs/mkdir · /api/open-path(白名单安全边界单点).

端点体逐字平移(plan 26-09-22-1857 W4); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。
26-09-27: 本地 syscall 全部改经文件访问层(infra/file_access, plan 26-09-27-1407) ——
Windows 长路径前缀收编进 Local 实现单点, 容器映射(Mapped)在此透明生效;
白名单比较保持在**逻辑空间**(与组 key/回传 qB 同空间, 见报告 §04)。
"""

import errno
import logging
import os
from typing import List
from fastapi import HTTPException

from ....infra import file_access
from ....infra.utils import path_normalize
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

    单点实现在 file_access._strip_win_prefix(调用点只交逻辑路径后由包装层自理) ——
    这里保留薄委托是为了让既有归一契约测试(test_web)继续钉在路由模块上。
    """
    return file_access._strip_win_prefix(p)


def _fs_real(p: str) -> str:
    """规范化到可比较的绝对路径(经文件访问层)

    Local 实现: realpath 解符号链接 + normcase 统一大小写/斜杠(路径真实存在, 可解析);
    Mapped 实现: 纯词法 normcase + normpath —— 逻辑路径在容器里不真实存在, realpath 只会
    把它拼坏。符号链接逃逸防护**不在**本函数做: Mapped 下由包装层的挂载根逃逸校验承担
    (infra/file_access SEC-1: 容器侧 realpath 跳出挂载根按 miss → 三态消费点语义化 404,
    scandir 逃逸条目直接剔除), 本函数只负责逻辑空间白名单比较的归一。

    !实现内部先剥 `\\\\?\\` 前缀: 比较双方可能一侧带前缀(如 `os.scandir` 家族返回值)、
    一侧不带 —— 不剥就会因前缀差异被判成"越界", 实测后果是**子目录被全部过滤掉**
    (目录树恒空)。

    WARN: 已知限制(沿用, 仅 Local): 对 >MAX_PATH 的路径 realpath **静默退化成 abspath**(不抛错)
    ⇒ 长路径上的符号链接/junction 解析不可用, 逃逸防护退化为词法比较(Mapped 无此限制)。
    """
    return file_access.get_file_access().realpath_lexical(p)


def _determinable(value, detail: str):
    """三态存在性消费单点: UNDETERMINED → 语义化 404, 其余原样透传

    UNDETERMINED 禁止布尔化(隐式真值判断抛 TypeError = 裸 500)。Mapped 模式下白名单内
    但未命中 fs.path_map 映射的路径会走到本路由 —— 必须在此显式分流成带原因的 404
    (「不可判定」不冒充「不存在」也不炸 500, 报告 §05; Local 实现永不产生
    UNDETERMINED, 本helper恒零开销透传)。
    """
    if value is file_access.UNDETERMINED:
        raise HTTPException(status_code=404, detail=detail)
    return value


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
        1.当前分组索引各组 key 首元(store.groups 的 key = (规范化 save_path, 文件列表), 组空即删,
        无陈旧条目); 2.store 现有种子的 save_path(经 path_normalize 归一分隔符后参与去重, 与组 key
        同径不重复出现)。只读快照, 无副作用(不触发视图重建/不投命令)。
        """
        manager.web.touch()
        paths = {key[0] for key in manager.store.groups if key and key[0]}
        paths.update(path_normalize(rec.save_path) for rec in manager.store.by_hash.values() if rec.save_path)
        return {"paths": sorted(paths)}

    def _browse_roots() -> List[str]:
        """目录浏览的**允许根**集合(R10-11): 与 /api/paths 同源的已知保存路径。

        白名单只由服务端从自己的快照派生, 不接受客户端传参 —— 这是文件系统读端点的第一道闸门。
        !roots 恒为**逻辑空间**路径(qB 报回的 save_path) —— 与映射无关, 见报告 §04。
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
        1. 只列**目录**, 绝不返回文件条目、不读文件内容;
        2. 允许根白名单 = 已知保存路径(与 /api/paths 同源, 逻辑空间); 路径经 _fs_real 规范化后
           必须落在某个根之内(相等或为子目录), 否则 403 —— 同时挡掉 `..` 穿越;
        3. 逐条子目录同样过白名单 -> 指向根外的符号链接/junction 不会出现在列表里(逃逸防护;
           Local 实现靠 realpath 解析符号链接, Mapped 实现由包装层剔除容器侧逃逸挂载根的
           条目(SEC-1) —— 下载目录内指向挂载外的符号链接既不出现、点进去也按「不可判定」404);
        4. 鉴权沿用全局 require_token 依赖(本机免鉴权同样放行, 与其它端点一致)。
        path 为空 = 返回允许根列表(前端首屏入口)。

        扫描与子路径构造全程在**逻辑空间**进行(包装层把 entry 译回逻辑空间, 报告 §04):
        旧实现先 realpath 再扫描, 现改为词法基准 + 逐条白名单 realpath, 对无符号链接的
        普通目录行为一致。
        """
        manager.web.touch()
        roots = _browse_roots()
        if not roots:
            return {"path": "", "parent": "", "roots": [], "dirs": []}
        if not path:
            return {"path": "", "parent": "", "roots": roots, "dirs": [{"name": r, "path": r} for r in roots]}
        if not _within_roots(path, roots):
            raise HTTPException(status_code=403, detail="路径不在允许的保存路径范围内")
        fa = file_access.get_file_access()
        target = path_normalize(_bare(path))  # 逻辑路径基准(保大小写, 不解析符号链接)
        if not _determinable(fa.isdir(target), "目录不可判定(未命中 fs.path_map 映射, 请检查 config.fs.path_map)"):
            raise HTTPException(status_code=404, detail="目录不存在或不可访问")
        try:
            entries = fa.scandir(target)
        except OSError as e:
            raise HTTPException(status_code=404, detail=f"目录不可读: {e.strerror or e}")
        dirs = [
            {
                "name": e.name,
                "path": path_normalize(e.path)
            } for e in entries if e.is_dir and _within_roots(e.path, roots)
        ]
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

        安全边界与 /api/fs/dirs 同源, 另加: 1. name 必须是**单层名字**(不含分隔符、不为 . / ..),
        不接受任何路径成分; 2. 已存在同名目录直接返回(幂等), 同名**文件**报 409;
        3. 这是本项目唯一的文件系统**写**能力, 不扩展到重命名/删除/递归。
        不触碰任务队列与 state_file -> 不违反单一写线程假设。

        容器(Mapped)实现下 mkdir 真实执行: 挂载点可写(:rw)即成功, 只读挂载由 OS 的
        EROFS/EACCES 冒泡后在此语义化为 403(不让裸 strerror 变乱码)。
        """
        b = body or {}
        name = str(b.get("name") or "").strip()
        parent = str(b.get("path") or "").strip()
        roots = _browse_roots()
        if not name or name in (".", "..") or any(sep in name for sep in ("/", "\\")):
            raise HTTPException(status_code=400, detail="文件夹名不合法")
        if not parent or not _within_roots(parent, roots):
            raise HTTPException(status_code=403, detail="路径不在允许的保存路径范围内")
        fa = file_access.get_file_access()
        base = path_normalize(_bare(parent))
        if not _determinable(fa.isdir(base), "目录不可判定(未命中 fs.path_map 映射, 请检查 config.fs.path_map)"):
            raise HTTPException(status_code=404, detail="目录不存在或不可访问")
        target = os.path.join(base, name)
        if _determinable(fa.exists(target), "目录不可判定(未命中 fs.path_map 映射, 请检查 config.fs.path_map)"):
            if fa.isdir(target):
                return {"created": path_normalize(target), "existed": True}
            raise HTTPException(status_code=409, detail="同名文件已存在")
        try:
            fa.mkdir(target)
        except file_access.NotSupported:
            raise HTTPException(status_code=501, detail="当前运行环境不支持新建文件夹")
        except OSError as e:
            if e.errno in (errno.EACCES, errno.EPERM, errno.EROFS):
                raise HTTPException(
                    status_code=403,
                    detail="下载目录挂载为只读, 无法新建(容器部署默认 :ro; 确需新建请改 :rw 挂载)",
                )
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
        组内成员路径天然一致, 无需再比对); torrent 按 content_path 的**实际存在形态**三段分流:
        文件存在 = 单文件种子, 打开所在目录并**定位选中**该文件(R10-10 用户诉求: "没有创建
        文件夹的要在文件夹中选中相关文件"); 目录存在 = 多文件种子, 打开内容目录; 都不存在
        (下载中最常见 —— qB 报的 content_path 是逻辑完成名, 文件未落盘 / 启用 .!qB 未完成
        后缀时磁盘上没有该路径) 则回退 save_path, 至少把目录打开, 不因"未完成"而 404。
        content_path 与 save_path 都缺时同样回退 save_path(空)。
        只读: 不投命令、不写 state —— 单一写线程假设不受影响。

        容器(Mapped)实现 open_path 恒 NotSupported —— 优雅降级为 501 + 引导「复制路径」
        (把原先 404/500 两层根因收敛成一句话, 报告 §05)。
        """
        manager.web.touch()
        b = body or {}
        kind = str(b.get("kind") or "").strip()
        select = False
        fa = file_access.get_file_access()
        if kind == "group":
            key = _group_key_param(str(b.get("key") or ""))
            if key not in manager.store.groups:
                raise HTTPException(status_code=404, detail="辅种不存在")
            target = key[0] or ""
        elif kind == "torrent":
            rec = _require_torrent(str(b.get("hash") or "").strip())
            content = path_normalize(rec.content_path or "")
            if content and _determinable(fa.isfile(content), "路径不可判定(未命中 fs.path_map 映射, 请检查 config.fs.path_map)"):
                target, select = content, True  # 单文件种子(文件已落盘): 定位选中, 不降级成"只打开父目录"
            elif content and _determinable(fa.isdir(content), "目录不可判定(未命中 fs.path_map 映射, 请检查 config.fs.path_map)"):
                target = content  # 多文件种子: 打开内容目录
            else:
                target = path_normalize(rec.save_path or "")  # content 未落盘(下载中) -> 回退保存路径
        else:
            raise HTTPException(status_code=400, detail="kind 必须是 group 或 torrent")
        target = path_normalize(target)
        if select:
            if not _determinable(fa.isfile(target), "路径不可判定(未命中 fs.path_map 映射, 请检查 config.fs.path_map)"):
                raise HTTPException(status_code=404, detail="目标文件不存在或不可访问")
        elif not target or not _determinable(fa.isdir(target), "目录不可判定(未命中 fs.path_map 映射, 请检查 config.fs.path_map)"):
            raise HTTPException(status_code=404, detail="目标目录不存在或不可访问")
        try:
            common.open_path(target, select=select)
        except file_access.NotSupported:
            raise HTTPException(status_code=501, detail="容器环境不支持打开文件夹, 请使用「复制路径」")
        return {"opened": target, "select": select}

    return router
