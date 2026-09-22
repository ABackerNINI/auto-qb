"""配置族路由: /api/config/public|schema|get|put|preview + /api/expr/eval(试算).

端点体逐字平移(plan 26-09-22-1857 W5); 仅 @app.* → @router.* 与共享件别名(原闭包名不变)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。"""

from fastapi import HTTPException

from ..common import config_backup_path as _config_backup_path

from fastapi import APIRouter
from ..context import WebContext


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    _enqueue = ctx.enqueue
    router = APIRouter()

    @router.get("/api/config/public")
    def api_config_public():
        """前端登录前读取的公开只读标志(不含密钥等机密): 本机免鉴权开关"""
        return {"web": {"skip_local_verify": manager.config.web.skip_local_verify}}

    @router.post("/api/expr/eval")
    def api_expr_eval(body: dict = None):
        """表达式**试算**(配置编辑器的「试算」按钮)

        - 不给 hash: 只做编译 + 语义校验, 返回用到的取值名 —— 语法/名字拼写错的即时反馈
          (否则要等保存时后端校验才知道)
        - 给 hash: 用该种子求值, 返回布尔结果 + **中间值**(每个名字/函数取到了什么),
          让人看清判断依据; 求值出错时返回错误(与运行期同口径: 数据源不可用等)
        只读: 不碰任务队列与 state_file, 不违反单一写线程假设。
        ⚠ 用到 tracker.names 时会走一次 qB tracker 查询(试算是手动触发的偶发请求, 可接受)。
        """
        b = body or {}
        text = str(b.get("text") or "")
        tor_hash = str(b.get("hash") or "").strip()
        from ...rules.base import RuleContext
        from ...rules.expr import env
        from ...rules.expr import compile_expr, validate
        from ...rules.expr.errors import ExprError
        from ...rules.expr.eval import evaluate, trace

        try:
            root = compile_expr(text).root
            validate(root)
        except ExprError as e:
            return {"ok": False, "error": str(e)}
        used = sorted(env.used_names(root))
        if not tor_hash:
            return {"ok": True, "used": used, "value": None, "trace": []}

        rec = manager.store.get(tor_hash)
        if rec is None:
            return {"ok": False, "error": f"找不到种子: {tor_hash[:8]}", "used": used}
        ctx = RuleContext(manager, getattr(manager, "client", None), manager.config, tor_hash, dry_run=True)
        try:
            value = evaluate(root, ctx)
        except ExprError as e:
            return {"ok": False, "error": str(e), "used": used}
        return {"ok": True, "used": used, "value": bool(value), "trace": trace(root, ctx)}

    @router.get("/api/config/schema")
    def api_config_schema():
        """配置表单元数据(分组/字段/控件/帮助) + 热重载级别(唯一来源: config.impact)"""
        from ...config import schema as config_schema
        from ...config.impact import SECTION_LEVELS, TRACKER_FIELD_LEVELS

        payload = config_schema.schema_payload()
        # 级别表由 impact 单一维护(与热重载实际分级同源), API 层只做合并
        payload["levels"] = {"sections": SECTION_LEVELS, "tracker_fields": TRACKER_FIELD_LEVELS}
        # ⚠ 这里**不能**改 JSONResponse 直返(与 /api/state 不同): schema_payload() 里是
        # dataclass 实例(Group / Field / Plugin), 靠 FastAPI 的 jsonable_encoder 转成 dict;
        # 直返会在 json.dumps 处抛 `Object of type Group is not JSON serializable` 变 500
        # (2026-09-19 实测)。判据: **载荷里有没有非 JSON 原生类型** —— 有就必须保留编码器。
        return payload

    @router.get("/api/config")
    def api_config_get():
        """当前配置树(YAML 同构, 标量为字符串) + 写盘路径

        敏感字段(qB 密码 / tracker passkey / WEB 密钥)按**键名**掩码为 MASK_SENTINEL: 明文
        进浏览器内存、截图与日志即为凭据泄漏。保存时 PUT 会用磁盘旧值还原哨兵 —— 掩码只影响
        展示, 不会把密码写死成占位串。
        """
        from ...config.writer import MASK_SENTINEL, mask_tree, read_tree

        return {
            "tree": mask_tree(read_tree(manager.config_path)),
            "path": manager.config_path,
            "masked": True,
            "mask_sentinel": MASK_SENTINEL,
        }

    @router.put("/api/config")
    def api_config_put(body: dict):
        """保存图形化配置: 结构校验(与启动同路径) -> R 级字段回退 -> round-trip 写盘 -> 投递热重载

        校验失败不触碰磁盘; R 级字段(state_file/data_dir)保留旧值, 其余立即生效。
        提交树里的掩码哨兵先按磁盘旧值还原(见 api_config_get), 未修改的密码保持原值。
        """
        from ...config.errors import ConfigError
        from ...config.loaders import load_config
        from ...config.writer import read_tree, unmask_tree, write_tree

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

    @router.post("/api/config/preview")
    def api_config_preview(body: dict):
        """只读预览: 返回"即将写入"的 YAML 文本(不落盘、不投递热重载), 校验口径与保存一致

        与 PUT 同口径: 先还原掩码哨兵, 否则预览里会显示一串占位符(与实际写入结果不符)。
        """
        from ...config.errors import ConfigError
        from ...config.writer import preview_tree, read_tree, unmask_tree

        tree = (body or {}).get("tree")
        if not isinstance(tree, dict):
            raise HTTPException(status_code=400, detail="tree 必须是对象")
        unmask_tree(tree, read_tree(manager.config_path))
        try:
            text = preview_tree(manager.config_path, tree, manager.config)
        except (ConfigError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"yaml": text}

    return router
