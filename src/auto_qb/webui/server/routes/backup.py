"""配置备份 bundle 导出/导入路由(计划 26-11-14-0624 S1/S2): GET /api/backup/export + POST /api/backup/import

一次导出 = 一个 JSON bundle 文件(§03 形态): 服务端三段 + 前端一段:
- ``config_yaml``: config.yml 原文 -> ruamel round-trip -> 整体掩码(新单点
  ``config.writer.mask_yaml_text``, 与 GET /api/config 的 mask_tree 同一套判定)。
  **掩码不出机**(D2 不变量): 导出端点是纯掩码面 —— bundle 永不含明文凭据,
  也不新增「秘密读取原语」; 导入侧(S2)遇哨兵回填本机现值。
- ``webui_keys``: 经现有 ``routes.keys.load_keys_doc``(与 GET /api/keys 同源同形状)。
- ``gtm``: 经 ``traffic_monitor._source_status``(与 GET /api/traffic/monitor/status 同源,
  只经 HTTP 契约通信); 工具离线/未就绪该段为 null(缺段 = 不含该面, 导入跳过)。
- ``ui_prefs``: 浏览器 localStorage 偏好(D3 拍板「只存浏览器」) —— **服务端零接触**,
  由前端把该段并进已下载的服务端 bundle 再落盘, 故本端点响应不含该键。

响应为可下载 JSON(文件名 auto-qb-backup-<YYYYMMDD-HHMMSS>.json), 沿用 .torrent 导出的
``Response`` + ``Content-Disposition`` 先例(全仓无 FileResponse)。

导入(S2, D6 整份替换 + 先验整体拒): 请求体只带勾选段
``{"bundle_version": <int 可选>, "sections": {"config_yaml"?: str, "webui_keys"?: dict, "gtm"?: dict}}``
(bundle 内对应段原文; ui_prefs 留前端不经服务端), 响应 ``{applied, skipped, warnings}``:

- ``config_yaml``: 空串段 skip+warnings -> 长度上限 -> ruamel 解析(异常 500 只留类型名, D2
  收口; 嵌套过深 422)-> 形状闸(alias 共享引用拒收 + 节点数/深度上限 —— 本端点是后端唯一
  不可信 YAML 解析面, 堵 alias 放大/深嵌套把下游递归与序列化打爆)-> 根非映射 / config 段
  缺失-空映射-非映射 422 -> bundle_version / config schema_version 闸(高于本机 422 拒并提示
  先升级; 低于/缺失放行 = 旧版本 bundle 原样落盘, schema 迁移靠下次启动
  materialize_schema_migration 链, R2)-> 掩码 resolve + readonly 回退 + load_config 全量聚合
  校验 + 整份替换写盘**同一 _WRITE_LOCK 临界区**(writer.commit_import_yaml_doc 读改写闭环,
  R8: 并发 PUT /api/config 不撕窗; 不可 resolve 聚合 422 逐路径 R1、残留哨兵兜底闸, 绝不把
  哨兵字面量写盘; 注释随 bundle 保留)-> reload_config enqueue(旧版本 bundle 由 loaders
  内存迁移)。
- ``webui_keys``: 复用 PUT /api/keys 的 sanitize + 原子写 + .bak; sanitize 失败 422。
- ``gtm``: 走 ``_ready_endpoint`` + 工具 PUT /config 代理(traffic_monitor 写端点同款);
  工具离线/未就绪 -> skipped + 原因(不致命, D9); 工具 400 校验错透传进 warnings(R3),
  不阻断 config/keys 应用; section 信封内未知键(tool_version 等)忽略不报错。
- 未知顶层 section: 忽略 + warnings(向前兼容)。

失败语义(fail-fast 黄金法则): config/keys 先验任一失败 -> 422 聚合整体拒绝, 不半应用;
gtm 是唯一「可跳过」面。错误 detail 绝不拼异常原文(ruamel DuplicateKeyError 等异常文本
逐字回显明文值, 泄敏)。

direct 端点(非 cmd 透传): 写面只落 config.yml / webui-keys.json(+ .bak), 不碰任务队列与
state_file; reload_config 经 ctx.enqueue 投递主循环(黄金法则 5)。鉴权由 factory 全局
dependencies 单点覆盖, 本模块不另挂依赖。日志命名空间见包 __init__(K3)。
"""
import copy
import io
import json
import logging
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..common import config_backup_path, content_disposition
from ..context import WebContext
from . import traffic_monitor as _tm
from .keys import keys_file_path, load_keys_doc

logger = logging.getLogger("auto_qb.web")  # noqa: F401  (K3: server 包内 logger 名冻结; 本模块现无直接日志点)

BUNDLE_FORMAT = "auto-qb-config-bundle"
BUNDLE_VERSION = 1

# bundle config_yaml 解析面加固(评审): 本端点是后端唯一的不可信 YAML 解析面(手造 bundle),
# 解析前限长 + 解析后形状闸(常量与判据见 _scan_yaml_doc_shape)。生产 config.yml 为 KB 量级,
# 各上限远超合法 bundle(掩码只给敏感值加引号形态)。
_MAX_BUNDLE_YAML_CHARS = 1_000_000  # ~1MiB 文本长度上限(防手造超长文本的解析耗时/内存)
_MAX_YAML_DOC_NODES = 100_000  # 节点数上限(防超大文档拖垮下游校验/写盘链)
_MAX_YAML_DOC_DEPTH = 100  # 嵌套深度上限(防深嵌套把递归遍历打进 RecursionError/慢路径)

# 请求体 sections 的已知段(未知段忽略 + warnings 向前兼容; ui_prefs 留前端不经服务端, D3)
KNOWN_SECTIONS = ("config_yaml", "webui_keys", "gtm")


def _config_yaml_section(manager) -> str:
    """config_yaml 段: 读原文 -> mask_yaml_text(掩码 + 注释保留); 文件不存在回空串"""
    if not os.path.exists(manager.config_path):
        return ""
    with open(manager.config_path, "r", encoding="utf-8") as f:
        text = f.read()
    from ....config.writer import mask_yaml_text

    try:
        return mask_yaml_text(text)
    except Exception as e:  # noqa: BLE001  (ruamel YAMLError/OSError 统一收口为明确 500)
        # detail 只留固定文案 + 异常类型名, 绝不拼 {e} —— ruamel DuplicateKeyError 的异常
        # 文本逐字回显重复键的明文值(实测: found duplicate key "password" with value "b"),
        # detail 进响应体 = 凭据泄敏, 违反 D2(掩码不出机)。也不为拼日志在此打点。
        raise HTTPException(status_code=500, detail=f"配置文件掩码化失败(bundle 导出中止): {type(e).__name__}") from e


def _gtm_section(manager) -> dict | None:
    """gtm 段: 工具在线 -> {config 合并树, tool_version, captured_at}; 离线 -> None(D9 不抛错)

    同源单点: 复用 traffic_monitor._source_status(与 GET /api/traffic/monitor/status 逐字
    同一状态面), 不另起探活链路。reachable 但 /status 回显缺失(非 200 竞态)同样按 None。
    """
    st = _tm._source_status(manager)
    if not st["reachable"]:
        return None
    status = st.get("status")
    if not isinstance(status, dict):
        return None
    return {
        "config": status.get("config"),  # 外部契约(工具 /status 回显), 保留 get 防御
        "tool_version": st["version"] or "",  # _source_status 自产字典, 直接访问
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def build_backup_bundle(manager) -> dict:
    """组装服务端侧 bundle(§03 形态; ui_prefs 由前端并入, 本函数不含)"""
    # 延迟导入: 本模块经 routes/__init__ 在 auto_qb/__init__ 的 import 链上被拉起,
    # 顶层 `from .... import __version__` 会撞 partially initialized(循环导入)
    from .... import __version__

    return {
        "format": BUNDLE_FORMAT,
        "bundle_version": BUNDLE_VERSION,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "app_version": __version__,
        "config_yaml": _config_yaml_section(manager),
        "webui_keys": load_keys_doc(manager),
        "gtm": _gtm_section(manager),
    }


# ---------------------------------------------------------------------------
# 导入(S2): 先验阶段(fail-fast 聚合, 整体拒) -> 应用阶段(config -> keys -> reload -> gtm)
# ---------------------------------------------------------------------------


def _r1_message(missing) -> str:
    """R1(掩码不可 resolve)的聚合报错文案单点(precheck 聚合与提交兜底共用)"""
    return (
        "config_yaml: 掩码值无法还原为本机现值(bundle 有哨兵条目而本机无对应键 —— 跨机导入请"
        "先在本机建好对应条目, 或编辑 bundle 填入新机明文值), 共 "
        f"{len(missing)} 处:\n" + "\n".join(f"  [{i + 1}] {p}" for i, p in enumerate(missing))
    )


def _scan_yaml_doc_shape(doc, errors) -> bool:
    """bundle 文档形状闸(评审 fix3): alias 共享引用拒收 + 节点数/深度上限; 通过返回 True

    选型说明(评审给的两案取「解析后上限」而非「文本扫描 &/*」): 文本扫描要正确跳过引号区/
    注释/块标量/流式集合, 误杀面难控(合法值以 &/* 开头或含未闭合引号形态); 解析后检测零误杀
    且直接挡住放大面 ——
    - alias 检测: 容器对象被引用两次 = alias(billion laughs 的放大机制是共享容器引用)。
      合法导出 bundle(mask_yaml_text round-trip)永不含共享容器; ruamel 对 alias 的 load/
      dump 本身线性(实测, 共享引用原样重发 anchor), 但下游递归(unmask/残留哨兵扫描/
      load_config 校验)会沿共享 DAG 指数展开 —— 检出即拒, 在一切遍历之前。
    - 节点数/深度上限: 堵无 alias 的超大/深嵌套文档把下游递归与校验拖进 RecursionError/
      慢路径。id 去重的显式栈遍历(线性, 本身不吃深度炸弹)。
    """
    seen = set()
    stack = [(doc, 0)]
    nodes = 0
    while stack:
        node, depth = stack.pop()
        if depth > _MAX_YAML_DOC_DEPTH:
            errors.append(f"config_yaml: 文档嵌套超过 {_MAX_YAML_DOC_DEPTH} 层, 已拒")
            return False
        if isinstance(node, (dict, list)):
            if id(node) in seen:
                errors.append("config_yaml: 文档含 YAML anchor/alias(容器共享引用 —— 合法导出 bundle 不会"
                              "出现, alias 展开是解析放大面), 已拒")
                return False
            seen.add(id(node))
            nodes += 1
            children = node.values() if isinstance(node, dict) else node
            for child in children:
                stack.append((child, depth + 1))
        else:
            nodes += 1
        if nodes > _MAX_YAML_DOC_NODES:
            errors.append(f"config_yaml: 文档节点数超过 {_MAX_YAML_DOC_NODES}, 已拒")
            return False
    return True


def _aggregate_config_precheck(manager, doc, errors) -> None:
    """锁内只读先验(仅用于聚合报错面): resolve/readonly 回退/load_config 校验, 不写盘

    只在其它段已有错误时调用(传**副本**进来): 把 config 侧错误并进同一个 422。提交路径不
    走这里 —— commit_import_yaml_doc 在写盘同一临界区内现读现 resolve(R8), 无需单独先验。
    """
    from ....config.errors import ConfigError
    from ....config.writer import prepare_import_yaml_doc

    try:
        missing = prepare_import_yaml_doc(manager.config_path, doc)
    except ConfigError as e:
        errors.append(f"config_yaml: {e}")
        return
    except Exception as e:  # noqa: BLE001  (本机 config.yml 坏 YAML; D2 收口: 不拼异常文本)
        raise HTTPException(status_code=500, detail=f"本机配置文件解析失败: {type(e).__name__}") from e
    if missing:
        errors.append(_r1_message(missing))


def _parse_config_yaml(text, errors, skipped, warnings):
    """config_yaml 段纯内存先验 -> 返回未 resolve 的原样文档(失败时 None, 原因聚合进 errors)

    顺序: 空段 skip -> 长度闸 -> ruamel 解析 -> 形状闸(alias/节点/深度) -> 根非映射 ->
    config 段形状 -> schema 版本闸。doc 保持哨兵原样不改写 —— resolve 在写盘同一临界区内做
    (commit_import_yaml_doc, R8)。任何失败只记 errors 不写盘(整体拒, 不半应用)。
    """
    from ....infra.errors import SchemaVersionError
    from ....infra.versioning import detect_version
    from ....config.loaders import normalize_schema_version
    from ....config.writer import ROOT_KEY, _build_yaml

    if not isinstance(text, str) or not text.strip():
        # 空 config_yaml 段(离线导出的畸形 bundle / 前端漏带): skip + warnings, 不致命
        reason = "config_yaml 段为空串(bundle 不含该面), 已跳过"
        skipped.append({"section": "config_yaml", "reason": reason})
        warnings.append(reason)
        return None
    if len(text) > _MAX_BUNDLE_YAML_CHARS:
        errors.append(f"config_yaml: 文本超长({len(text)} > {_MAX_BUNDLE_YAML_CHARS} 字符), 已拒")
        return None
    ry = _build_yaml()
    try:
        doc = ry.load(io.StringIO(text))
    except RecursionError:
        raise HTTPException(status_code=422, detail="bundle config_yaml 嵌套过深(解析递归溢出), 已拒")
    except Exception as e:  # noqa: BLE001  (D2 同款收口: 异常文本可能逐字回显明文凭据)
        raise HTTPException(status_code=500, detail=f"bundle config_yaml 解析失败: {type(e).__name__}") from e
    if not isinstance(doc, dict):
        errors.append("config_yaml: bundle 段不是映射文档, 无可导入内容")
        return None
    if not _scan_yaml_doc_shape(doc, errors):
        return None
    # config 段形状闸(major 评审): 根是映射但 config 段缺失/非映射/空映射 -> 同口径拒 ——
    # 放行会经 fallback 的 _set_path 把该路径整体替换成存根, load_config 按全默认值过校验,
    # 整份落盘 = 一次 200 导入静默重置生产配置(导入是整份替换, 空段没有「重置」语义)
    cfg = doc.get(ROOT_KEY)
    if not isinstance(cfg, dict) or not cfg:
        errors.append("config_yaml: bundle 段缺 config(或为空映射/非映射), 无可导入内容 —— "
                      "整份替换语义下拒绝, 以免静默重置本机配置")
        return None
    # schema 版本闸(R2): 高于当前 = bundle 由更新版本程序写出 -> 拒; 低于/缺失 = 旧版本
    # bundle 放行(原样落盘, 磁盘版本章不盖当前值, 迁移靠下次启动 materialize 链)
    normalize_schema_version(cfg)
    try:
        detect_version("config", cfg)
    except SchemaVersionError as e:
        errors.append(f"config_yaml: {e}")
        return None
    return doc


def _prepare_webui_keys(doc, errors):
    """webui_keys 段先验: 复用 PUT /api/keys 的 sanitize(结构层校验单点); 失败聚合进 errors"""
    from .keys import _sanitize

    clean = _sanitize(doc) if isinstance(doc, dict) else None
    if clean is None:
        errors.append("webui_keys: 结构不符 —— 需要 {schema_version: 1, template: 非空串, "
                      "overrides: {action_id: 归一化串或空串}}")
        return None
    return clean


def _apply_gtm_section(manager, section, applied, skipped, warnings) -> None:
    """gtm 段应用: 走 _ready_endpoint + 工具 PUT /config 代理(traffic_monitor 写端点同款)

    工具离线/未就绪/不可达 -> skipped + 原因(不致命, D9); 工具 400 校验错透传进 warnings
    (R3, 该段不应用但不阻断 config/keys); 信封内未知键(tool_version 等)忽略不报错;
    config 缺失/非对象(null = 离线导出)按缺面跳过。
    """
    payload = section.get("config") if isinstance(section, dict) else None
    if not isinstance(payload, dict):
        skipped.append({"section": "gtm", "reason": "bundle gtm 段无 config(null = 离线导出), 不含该面"})
        return
    try:
        base_url, token = _tm._ready_endpoint(manager)
        code, resp = _tm._call_tool(base_url, "/config", "PUT", token, payload)
    except _tm.ToolUnreachable as e:
        skipped.append({"section": "gtm", "reason": f"工具不可达: {e}"})
        return
    except HTTPException as e:  # _ready_endpoint 502: 工具未运行/未就绪(离线不致命)
        skipped.append({"section": "gtm", "reason": str(e.detail)})
        return
    if code == 200:
        applied.append("gtm")
    elif code == 400:  # 工具侧校验拒绝(R3): 逐条错误透传进 warnings, 该段不应用
        warnings.append(f"gtm: 工具侧校验拒绝(400), 该段未应用: {_tm._error_text(resp, code)}")
        skipped.append({"section": "gtm", "reason": "工具侧校验拒绝(400)"})
    else:
        skipped.append({"section": "gtm", "reason": f"工具返回非预期状态码 {code}: {_tm._error_text(resp, code)}"})


def _enqueue_reload(ctx, manager) -> None:
    """config 应用后投递热重载(与 PUT /api/config 同款): 主循环线程应用, Web 线程只投意图

    bundle 为旧版本时磁盘保持原版本章, load_config 内部迁移链内存生效(loaders 内存迁移),
    磁盘终态迁移由下次启动 materialize_schema_migration 兜底(R2)。
    """
    from ....config.loaders import load_config

    ctx.enqueue("reload_config", {"config": load_config(manager.config_path)})


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    router = APIRouter()

    @router.get("/api/backup/export")
    def api_backup_export():
        """导出配置备份 bundle(可下载 JSON, 掩码不出机): 详见模块 docstring"""
        manager.web.touch()
        bundle = build_backup_bundle(manager)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return Response(
            content=json.dumps(bundle, ensure_ascii=False, indent=2),
            media_type="application/json",
            # content_disposition 自拼扩展名(与 .torrent 导出同口径): 传不带后缀的基名
            headers={"Content-Disposition": content_disposition(f"auto-qb-backup-{stamp}", "auto-qb-backup", "json")},
        )

    @router.post("/api/backup/import")
    def api_backup_import(body: dict):
        """导入配置备份 bundle(勾选段整份应用): 详见模块 docstring"""
        manager.web.touch()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="body 必须是对象")
        # bundle_version 闸(R2): 高于本机 = bundle 由更新版本的程序导出, 拒绝并提示先升级
        bundle_version = body.get("bundle_version")
        if bundle_version is not None:
            if isinstance(bundle_version, bool) or not isinstance(bundle_version, int):
                raise HTTPException(status_code=400, detail="bundle_version 必须是整数")
            if bundle_version > BUNDLE_VERSION:
                raise HTTPException(
                    status_code=422,
                    detail=f"bundle 版本(v{bundle_version})高于本机(v{BUNDLE_VERSION}) —— "
                    "bundle 由更新版本的程序导出, 请先升级本机程序后再导入",
                )
        sections = body.get("sections")
        known = [k for k in KNOWN_SECTIONS if k in (sections or {})]
        if not isinstance(sections, dict) or not known:
            raise HTTPException(
                status_code=400,
                detail="sections 必须是对象且至少勾选一个已知段(config_yaml/webui_keys/gtm)",
            )

        applied = []
        skipped = []
        warnings = []
        errors = []

        unknown = sorted(str(k) for k in sections if k not in KNOWN_SECTIONS)
        if unknown:
            warnings.append(f"未知 section 已忽略(向前兼容): {', '.join(unknown)}")

        # ---- 先验阶段(fail-fast 聚合): config 纯内存闸 + keys sanitize, 任一失败整体 422 ----
        config_doc = None
        if "config_yaml" in sections:
            config_doc = _parse_config_yaml(sections["config_yaml"], errors, skipped, warnings)
        keys_doc = None
        if "webui_keys" in sections:
            keys_doc = _prepare_webui_keys(sections["webui_keys"], errors)
        if config_doc is not None and errors:
            # keys 等已有错: 用副本跑锁内只读先验, 把 config 侧错误并进同一 422(不写盘)——
            # 原文档保持哨兵原样, 提交路径在写盘同一临界区内现读现 resolve(R8)
            _aggregate_config_precheck(manager, copy.deepcopy(config_doc), errors)
        if errors:
            raise HTTPException(status_code=422, detail="\n".join(errors))

        # ---- 应用阶段: config 整份替换(锁内读改写闭环) -> keys -> reload enqueue -> gtm ----
        if config_doc is not None:
            from ....config.errors import ConfigError
            from ....config.writer import commit_import_yaml_doc

            try:
                missing = commit_import_yaml_doc(manager.config_path, config_doc, config_backup_path(manager))
            except ConfigError as e:  # 校验失败/残留哨兵兜底闸 —— 未写盘, .bak 也未创建
                raise HTTPException(status_code=422, detail=f"config_yaml: {e}")
            except Exception as e:  # noqa: BLE001  (本机 config.yml 坏 YAML 竞态; D2 收口不拼文本)
                raise HTTPException(status_code=500, detail=f"本机配置文件解析失败: {type(e).__name__}") from e
            if missing:  # 理论不可达(precheck 已聚合; 两临界区之间本机状态变化的兜底), 同口径 422
                raise HTTPException(status_code=422, detail=_r1_message(missing))
            applied.append("config_yaml")
        if keys_doc is not None:
            from ....infra.utils import atomic_write

            def _write_keys(f):
                json.dump(keys_doc, f, ensure_ascii=False, indent=2)
                f.write("\n")

            atomic_write(keys_file_path(manager), _write_keys, keep_backup=True)
            applied.append("webui_keys")
        if config_doc is not None:
            _enqueue_reload(ctx, manager)
        if "gtm" in sections:
            _apply_gtm_section(manager, sections["gtm"], applied, skipped, warnings)

        return {"applied": applied, "skipped": skipped, "warnings": warnings}

    return router
