"""种子转移路由: /api/transfer/run + /api/transfer/test(计划 26-10-31-0306 §04 W3)

两端点都经 _enqueue 走 cmd 管线(与 bulk / 预检同通道): 执行体在主循环线程**同步串行**
(单一写线程假设, 不开线程不并发), 回执复用 waitCmd(queued/cmd_id -> /api/cmd/{id});
逐种子结果与版本信息经 truth 字段带出(与跳检/迁移预检同族: drain 不用裸 ok 覆盖)。

目标预检验读实时配置(ctx.manager.config 引用现取, 热重载后立即生效, 不按值持有旧
Config —— pitfalls/backend/hot-reload-held-config.md); 判据与命令层
commands._resolve_transfer_target 同字段单点(name 存在性 / enabled 开关都取自
web.transfer.targets[] 条目), 两处各薄查一遍: 路由层即时 400(前端免轮询), 命令层
兜底「投递-执行之间目标被删/停用」的热重载窗口(写 error 回执, 绝不带残缺目标执行)。

门控口径(W3): run 要求目标存在**且已启用**(转移是高风险动作, 保守默认); test 只要求
存在 —— 设置页要对尚未启用的目标先行测连通(W1 验收口径), 启用门槛只拦执行。
鉴权由 factory 的全局 dependencies 单点覆盖(Bearer + 跨站闸), 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""
from typing import Any, Optional, Tuple

from fastapi import APIRouter, HTTPException

from ..context import WebContext


def _find_target(ctx: WebContext, target_id: str, require_enabled: bool) -> Tuple[Optional[Any], Optional[str]]:
    """路由层目标预检: (target, None) 或 (None, 错误文案)

    判据与命令层 commands._resolve_transfer_target 同字段(name 匹配 + enabled 开关),
    各自薄查一遍(理由见模块 docstring); require_enabled 仅 run 传 True。
    """
    transfer = getattr(ctx.manager.config.web, "transfer", None)
    for target in (getattr(transfer, "targets", None) or ()):
        if str(getattr(target, "name", "")) == target_id:
            if require_enabled and not getattr(target, "enabled", False):
                return None, f"转移目标未启用: {target_id}(配置键 web.transfer.targets[].enabled)"
            return target, None
    return None, f"转移目标不存在: {target_id}(见配置键 web.transfer.targets)"


def build_router(ctx: WebContext) -> APIRouter:
    _enqueue = ctx.enqueue
    router = APIRouter()

    @router.post("/api/transfer/run")
    def api_transfer_run(body: dict = None):
        """执行一次转移批次(计划 26-10-31-0306 W3): body {target_id, hashes[], keep_source?}

        校验在路由层 400 拒收不入队(同 skip-check 预检先例, 前端即时可见): target_id 空 /
        hashes 空列表 / 目标不存在 / 目标未启用。keep_source(「仅本次保留源种子」, D1)
        按「提供才透传」—— 缺省队列载荷不带该键, 命令层缺省 False(默认删源)。
        回执(经 cmd 通道): status=ok + truth={results: [{hash, 状态(成功/跳过/失败),
        原因}], summary: {success, skipped, failed}, target: 目标名}, 逐种子结果由
        orchestrator 结果结构直出, 单种子失败不中断批次(D6)。
        """
        b = body or {}
        target_id = str(b.get("target_id") or "").strip()
        if not target_id:
            raise HTTPException(status_code=400, detail="未提供 target_id(转移目标不能为空)")
        hashes = [str(h) for h in (b.get("hashes") or []) if h]
        if not hashes:
            raise HTTPException(status_code=400, detail="未提供任何 hash(转移批次不能为空)")
        target, err = _find_target(ctx, target_id, require_enabled=True)
        if target is None:
            raise HTTPException(status_code=400, detail=err or "转移目标不可用")
        payload = {"target_id": target_id, "hashes": hashes}
        if b.get("keep_source"):
            payload["keep_source"] = True
        return _enqueue("transfer_run", payload)

    @router.post("/api/transfer/test")
    def api_transfer_test(body: dict = None):
        """测试目标下载器连通(计划 W3): body {target_id}; 只读探测, 不改任何状态

        目标只需**存在**(不要求启用 —— 设置页对未启用目标先行测连通, 见模块 docstring
        门控口径); 不存在 400 拒收不入队。回执(经 cmd 通道): 成功 status=ok +
        truth={info: 版本等描述}; 失败 status=error(文案可直接回显, 命令层不另加工);
        tr 目标按 stub 口径回「暂未实现」类 error 回执(D10 不做假接口)。
        """
        b = body or {}
        target_id = str(b.get("target_id") or "").strip()
        if not target_id:
            raise HTTPException(status_code=400, detail="未提供 target_id(转移目标不能为空)")
        target, err = _find_target(ctx, target_id, require_enabled=False)
        if target is None:
            raise HTTPException(status_code=400, detail=err or "转移目标不可用")
        return _enqueue("transfer_test", {"target_id": target_id})

    return router
