"""快捷键自定义路由: GET/PUT /api/keys(计划 26-09-28-0354 W6, 决策点⑥).

存储单点 auto-qb-data/webui-keys.json(<state_file 同目录, 与 web.token 同寻址规则);
web 线程独占读写, 与 state.json(主循环单写线程, 黄金法则 5)互不干扰。后端只做**结构层**
校验(fail-fast 精神): 键位语义(冲突/黑名单/危险档)归前端注册表单一事实源 —— 面板拦截 +
守阵断言, 后端不重复(计划 §4.4: "黑名单/冲突仍由前端面板拦截")。

结构(§4.4/§4.7 预埋): {"schema_version": 1, "template": "aqb-default", "overrides": {<action_id>: <归一化串 or 空>}}
- overrides 只存用户改过的条目, 未提及的 action 用模板基准(前端注册表); 空串 = 显式禁用;
- 读时兜底链: 主文件损坏 -> WARN + 尝试 .bak -> 仍坏用默认表(atomic_write keep_backup 范式);
- schema_version 不识别(未来版本)同走兜底链回默认表 —— 宁可回默认也不带病生效;
- 未知 action_id 不在后端过滤(前端注册表合并时自然忽略, 注册表前向兼容)。
鉴权由 factory 的全局 dependencies 单点覆盖, 本模块不另挂依赖。
日志命名空间见包 __init__(K3)。
"""

import json
import logging
import os
import re

from fastapi import APIRouter, HTTPException

from ....infra.utils import atomic_write
from ..context import WebContext

logger = logging.getLogger("auto_qb.web")

_KEYS_SCHEMA_VERSION = 1
# 与 shortcuts.js KB_DEF_RE 同一正则(修饰键固定序 + 单个 e.code); 改一边必须改另一边
_KEYS_SERIAL_RE = re.compile(r"^(Ctrl\+)?(Alt\+)?(Shift\+)?(Meta\+)?[A-Z][A-Za-z0-9]*$")
_KEYS_DEFAULT = {"schema_version": _KEYS_SCHEMA_VERSION, "template": "aqb-default", "overrides": {}}


def keys_file_path(manager) -> str:
    """webui-keys.json 路径: <state_file 同目录>(与 web.token 同寻址规则, 计划 §4.4)"""
    return os.path.join(os.path.dirname(manager.state_file) or ".", "webui-keys.json")


def _sanitize(doc):
    """读时结构校验(严格): 任何一处不符即视为损坏(返回 None 走兜底链), 不做局部修补。

    - 必须是 dict; schema_version 必须是当前支持的整数(未来版本走升级链口径: 回默认表 + WARN);
    - template 必须是非空字符串(v1 仅 aqb-default 一套, 模板名合法性归前端注册表);
    - overrides 必须是 dict[str, str], 值要么是空串(显式禁用), 要么匹配归一化串正则。
    """
    if not isinstance(doc, dict):
        return None
    if doc.get("schema_version") != _KEYS_SCHEMA_VERSION or isinstance(doc.get("schema_version"), bool):
        return None
    template = doc.get("template")
    if not isinstance(template, str) or not template:
        return None
    overrides = doc.get("overrides", {})
    if not isinstance(overrides, dict):
        return None
    for k, v in overrides.items():
        if not isinstance(k, str) or not isinstance(v, str):
            return None
        if v and not _KEYS_SERIAL_RE.match(v):
            return None
    return {"schema_version": _KEYS_SCHEMA_VERSION, "template": template, "overrides": overrides}


def load_keys_doc(manager) -> dict:
    """读时兜底链: 主文件 -> .bak -> 默认表; 每级失败都 WARN(失效模式可测可查, 计划 §4.2)。"""
    path = keys_file_path(manager)
    for cand, note in ((path, ""), (path + ".bak", ".bak 备份")):
        try:
            with open(cand, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except FileNotFoundError:
            continue
        except (OSError, ValueError) as e:
            logger.warning(f"快捷键配置{note}读取失败({e}), 兜底: 尝试 .bak -> 仍坏用默认表: {path}")
            continue
        clean = _sanitize(doc)
        if clean is not None:
            return clean
        logger.warning(f"快捷键配置{note}结构不符(schema_version/overrides 形状), 兜底: 尝试 .bak -> 仍坏用默认表: {path}")
    return dict(_KEYS_DEFAULT)


def build_router(ctx: WebContext) -> APIRouter:
    manager = ctx.manager
    router = APIRouter()

    @router.get("/api/keys")
    def api_keys_get():
        """当前快捷键配置(服务端存储真值): 前端拿它与注册表模板基准合并出生效表

        文件不存在(用户从未自定义)返回默认表; 损坏走兜底链(见 load_keys_doc), 服务不炸。
        """
        return load_keys_doc(manager)

    @router.put("/api/keys")
    def api_keys_put(body: dict):
        """保存整份快捷键配置(面板「保存」按钮, PUT 整份替换): 结构校验失败 422 且不触碰磁盘"""
        if not isinstance(body, dict):
            raise HTTPException(status_code=422, detail="body 必须是对象")
        clean = _sanitize(body)
        if clean is None:
            raise HTTPException(
                status_code=422,
                detail="快捷键配置结构不符: 需要 {schema_version: 1, template: 非空串, "
                "overrides: {action_id: 归一化串或空串}}",
            )
        path = keys_file_path(manager)

        def _write(f):
            json.dump(clean, f, ensure_ascii=False, indent=2)
            f.write("\n")

        atomic_write(path, _write, keep_backup=True)
        return clean

    return router
