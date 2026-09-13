"""配置写回: WEB UI 提交的 YAML 形状树 -> 校验 -> R 级字段回退 -> round-trip 写盘

职责与边界(与 ai/06 的约定一致):
- **校验唯一入口仍是 `load_config`**(先把树落到临时文件, 走与程序启动完全相同的路径),
  本模块不自建任何正确性规则
- **R 级字段(state_file/data_dir)不可热切换**: 树中对应值回退为磁盘旧值(旧行为不变),
  其余级别字段照常写入并热重载
- **ruamel round-trip 写盘**: 已存在键的注释保留; 列表项与新增键无注释(设计取舍, 见计划)

前端持有的树与磁盘 YAML 同构(标量全为字符串, 由 yaml.BaseLoader 语义决定), 因此
`read_tree` 读出的树可直接编辑后原样提交, 无需任何格式往返转换。
"""
import os
import re
import tempfile
from dataclasses import dataclass
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .impact import LEVEL_R, ConfigChange, diff_config_impacts
from .loaders import load_config

# 树根键(与 validate_config 的"根节点仅允许 config"一致)
ROOT_KEY = "config"


@dataclass
class WriteResult:
    """写盘结果: 变更列表 + 需重启字段(R 级)"""
    changes: List[ConfigChange]
    restart_required: List[str]


def read_tree(config_path: str) -> Dict[str, Any]:
    """读取配置为 YAML 形状树(标量全为字符串; 文件不存在/为空 -> 空 config 段)

    用 yaml.BaseLoader 与 load_config 完全一致, 保证"读出来再写回去"不产生格式漂移。
    """
    if not os.path.exists(config_path):
        return {ROOT_KEY: {}}
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.load(f, Loader=yaml.BaseLoader)
    if not isinstance(data, dict):
        return {ROOT_KEY: {}}
    if not isinstance(data.get(ROOT_KEY), dict):
        data[ROOT_KEY] = {}
    return data


def write_tree(config_path: str, tree: Dict[str, Any], old_config) -> WriteResult:
    """校验并写回配置树

    流程: 结构自检 -> 临时文件校验(load_config) -> R 级字段回退旧值 -> 备份 -> round-trip 写盘。
    校验失败抛 `ConfigError`(由调用方转 400 且不触碰磁盘); 结构非法抛 `ValueError`。
    """
    changes, restart_required = _prepare(config_path, tree, old_config)
    _backup(config_path)
    _dump_roundtrip(config_path, tree)
    return WriteResult(changes=changes, restart_required=restart_required)


def preview_tree(config_path: str, tree: Dict[str, Any], old_config) -> str:
    """生成"即将写入"的 YAML 文本(含 R 级字段回退), 不落盘 —— 供 UI 只读预览

    与 write_tree 共用校验与 round-trip 逻辑, 因此预览内容与写入内容一致(除注释形态);
    校验失败同样抛 ConfigError。
    """
    _prepare(config_path, tree, old_config)
    buf = StringIO()
    _build_yaml().dump(_build_doc(config_path, tree), buf)
    return buf.getvalue()


def _prepare(config_path: str, tree: Dict[str, Any], old_config) -> Tuple[List[ConfigChange], List[str]]:
    """写盘/预览的公共前置: 结构自检 -> 校验 -> R 级字段回退(就地修改 tree)"""
    if not isinstance(tree, dict) or not isinstance(tree.get(ROOT_KEY), dict):
        raise ValueError(f"配置树必须是含 {ROOT_KEY} 段的对象")

    new_config = _validate_tree(tree)
    old_tree = read_tree(config_path)
    changes = diff_config_impacts(old_config, new_config)
    restart_required = [c.path for c in changes if c.level == LEVEL_R]
    if restart_required:
        _fallback_restart_fields(tree, old_tree, changes)
    return changes, restart_required


def _validate_tree(tree: Dict[str, Any]) -> Any:
    """把树落到临时文件后用 load_config 校验(与启动同一路径), 返回解析后的 Config"""
    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yml", delete=False) as f:
            tmp_path = f.name
            yaml.dump(tree, f, allow_unicode=True, default_flow_style=False)
        return load_config(tmp_path)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def _fallback_restart_fields(tree: dict, old_tree: dict, changes: List[ConfigChange]) -> None:
    """R 级字段回退为磁盘旧值: 旧值存在则覆盖, 旧值不存在则删除该键(走默认值)"""
    for change in changes:
        if change.level != LEVEL_R:
            continue
        parts = [ROOT_KEY, *change.path.split(".")]
        old_value = _get_path(old_tree, parts)
        if old_value is None:
            _delete_path(tree, parts)
        else:
            _set_path(tree, parts, old_value)


def _get_path(tree: Any, parts: List[str]):
    node = tree
    for p in parts:
        if not isinstance(node, dict) or p not in node:
            return None
        node = node[p]
    return node


def _set_path(tree: dict, parts: List[str], value) -> None:
    node = tree
    for p in parts[:-1]:
        nxt = node.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            node[p] = nxt
        node = nxt
    node[parts[-1]] = value


def _delete_path(tree: dict, parts: List[str]) -> None:
    node = tree
    for p in parts[:-1]:
        node = node.get(p)
        if not isinstance(node, dict):
            return
    if isinstance(node, dict):
        node.pop(parts[-1], None)


def _backup(config_path: str) -> None:
    """写盘前备份为 <config>.bak(与旧行为一致)"""
    if not os.path.exists(config_path):
        return
    with open(config_path, "r", encoding="utf-8") as src, open(config_path + ".bak", "w", encoding="utf-8") as dst:
        dst.write(src.read())


def _build_yaml():
    """ruamel 实例工厂: 与原 config.yml 的 4 空格缩进风格一致, 保留引号形态"""
    from ruamel.yaml import YAML

    ry = YAML()
    ry.preserve_quotes = True
    ry.indent(mapping=4, sequence=4, offset=2)
    return ry


def _build_doc(config_path: str, tree: Dict[str, Any]):
    """读现有文件为 CommentedMap(保留注释)并把树同步进去, 返回待 dump 的文档对象"""
    ry = _build_yaml()
    doc = None
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            doc = ry.load(f)
    if not isinstance(doc, dict):
        doc = {}
    _sync_mapping(doc, tree)
    return doc


def _dump_roundtrip(config_path: str, tree: Dict[str, Any]) -> None:
    """ruamel round-trip 写盘: 已存在键原地改值以保留注释, 新增键追加, 缺失键删除

    列表整体替换(项级注释不保留) —— 树与磁盘的同构结构使其可安全重建。
    """
    ry = _build_yaml()
    doc = _build_doc(config_path, tree)
    with open(config_path, "w", encoding="utf-8") as f:
        ry.dump(doc, f)


def _sync_mapping(commented: dict, plain: dict) -> None:
    """把普通树同步到 CommentedMap: 递归已有 mapping(保注释), 其余整体赋值/删除

    值未变化的键**跳过赋值** —— 保留磁盘上的原标量及其注释/引号形态(否则 ruamel 会把
    原本无引号的 16585/true 重写为带引号字符串, 白白改变文件可读性)。
    """
    for key in list(commented):
        if key not in plain:
            del commented[key]
    for key, value in plain.items():
        existing = commented.get(key)
        if isinstance(value, dict) and isinstance(existing, dict):
            _sync_mapping(existing, value)
            continue
        if isinstance(value, list) and isinstance(existing, list) and _same_value(existing, value):
            continue
        if not isinstance(value, (dict, list)) and not isinstance(existing,
                                                                  (dict, list)) and _same_value(existing, value):
            continue
        commented[key] = _plain_scalar(value)


def _same_value(existing: Any, value: Any) -> bool:
    """按 YAML BaseLoader 语义比较(标量一律字符串), 用于"值未变则不动原节点"判定"""
    if existing is None:
        return False
    return _as_builtin(existing) == _as_builtin(value)


def _as_builtin(node: Any) -> Any:
    """把 ruamel 节点(CommentedMap/CommentedSeq/标量)转为普通结构

    标量统一为**字符串**且布尔小写化 —— 与 yaml.BaseLoader 的读取语义对齐(round-trip
    loader 会把 true/16585 读成 bool/int, 直接比较会误判为"值已变化"而重写整个标量)。
    """
    if isinstance(node, bool):
        return "true" if node else "false"
    if isinstance(node, dict):
        return {str(k): _as_builtin(v) for k, v in node.items()}
    if isinstance(node, (list, tuple)):
        return [_as_builtin(v) for v in node]
    return "" if node is None else str(node)


# 本项目 YAML 风格(见 config.yml): 数字/布尔均不以引号包裹, 由 BaseLoader 统一读为字符串
_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")


def _plain_scalar(value: Any) -> Any:
    """数字/布尔样式的字符串写成原生标量, 保持与原文件一致的书写风格(递归处理新增子树)

    ruamel 为保证"字符串类型守恒"会把 16585/true 写成 '16585'/'true'; 而本项目 YAML 读写
    全程走 BaseLoader(标量一律字符串), 写成原生标量后 BaseLoader 读回仍是字符串, 语义完全
    等价 —— 因此这里优先与磁盘原有风格保持一致; 其它字符串交给 ruamel 自行判断/加引号。

    **必须做等值校验**: 只有 `str(转换结果) == 原字符串` 才转换, 否则会丢失信息
    (如 "1.10" → 1.1 → 读回 "1.1"; "007" → 7 → 读回 "7")。
    """
    if isinstance(value, dict):
        return {k: _plain_scalar(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain_scalar(v) for v in value]
    if not isinstance(value, str):
        return value
    if _INT_RE.match(value) and str(int(value)) == value:
        return int(value)
    if _FLOAT_RE.match(value) and str(float(value)) == value:
        return float(value)
    lowered = value.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    return value
