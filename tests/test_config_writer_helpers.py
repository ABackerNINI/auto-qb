"""test_config_writer_helpers 测试计划: 配置写回(结构化树 -> 校验 -> R 级回退 -> round-trip 写盘)

## 测试计划(每个测试函数一条)
- test_backup_atomic_write_no_partial_bak: 保存前备份走 atomic_write(与 backup_versioned 统一), 写盘中断不留半截 .bak
- test_collect_explicit_empty_paths_all_trackers: v3→v4 显式置空收集不被非 dict 条目中断(continue 而非 break)
- test_url_host_shapes: host 提取(非串/畸形 IPv6 -> 空串; 正常小写化)
- test_path_helpers_mid_node_shapes: _set_path 中途节点非 dict 重建 / _delete_path 中途非 dict 与裸标量树安全返回
- test_prepare_passes_old_tree_to_restart_fallback: _prepare 调 R 级回退时 old_tree 来自 read_tree(不是 None)
- test_build_yaml_preserves_quotes_and_indent_profile: _build_yaml 保留引号 + 4/4/2 缩进档案(preserve_quotes/indent 三参)
- test_build_doc_reads_existing_and_falls_back_to_empty: _build_doc 读已有 CommentedMap/非映射与缺失文件都回退空文档重建
- test_fallback_helpers_split_dot_paths_and_rebuild_missing_nodes: R 级回退按 `.` 切点路径取旧值、嵌套覆盖、磁盘无旧值则删键(不写 None)
- test_delete_path_removes_last_segment_only: _delete_path 精确删最后一段(不倒索引/不误删兄弟键), 末段缺失静默
- test_sync_mapping_skips_unchanged_scalar_and_list_nodes: _sync_mapping「值未变不动原节点」对标量与列表都成立(保注释/引号形态)
- test_sync_mapping_scalar_vs_container_not_skipped: _sync_mapping 标量与容器互转不得被「未变化」逻辑吞掉(and 链不得写坏)
- test_same_value_none_and_as_builtin_semantics: _same_value(None,..)=False; _as_builtin 布尔小写/None→空串/数字→str/容器递归
- test_plain_scalar_bool_and_lossless_rules: _plain_scalar 布尔识别大小写无关, 有损数字串(007/1.10)保持字符串
- test_set_path_rebuilds_non_mapping_mid_nodes: _set_path 复用已有 dict 中途节点(不丢兄弟键)/标量重建/缺失现场建
- test_backup_skips_when_source_missing_and_keeps_encoding: _backup 源缺失零副作用; 按 dirname 建目录; utf-8 读写无损
"""

import copy

import os

import pytest

from auto_qb.config.errors import ConfigError

from auto_qb.config.loaders import load_config

from auto_qb.config.writer import materialize_schema_migration, preview_tree, read_tree, write_tree

from helpers import LEGACY_V1

from config_writer_support import (
    BASE,
    _bak,
    _make,
    _text,
)


def test_backup_atomic_write_no_partial_bak(tmp_path, monkeypatch):
    """保存前备份走 utils.atomic_write(与 backup_versioned 统一): 写盘中断不留半截 .bak

    备份恰是坏配置的恢复资产, 半截比没有更危险(issue 26-10-06-0028 chore-config-writer-backup-atomic;
    原 "w" 直写从 O_TRUNC 守阵面外漏过)。
    """
    from auto_qb.config import writer as writer_mod
    from auto_qb.infra import utils as infra_utils

    path = _make(tmp_path, BASE)
    backup = _bak(tmp_path)

    routed = []
    real_atomic = infra_utils.atomic_write

    def spy_atomic(p, fn, keep_backup=False):
        routed.append(p)
        real_atomic(p, fn, keep_backup)

    monkeypatch.setattr(infra_utils, "atomic_write", spy_atomic)
    writer_mod._backup(path, backup)
    assert routed == [backup], "保存前备份必须经 utils.atomic_write(与 backup_versioned 统一)"
    assert _text(backup) == _text(path), ".bak 内容 = 写盘前原样"

    # 写盘中断(内容写到一半抛): 干净路径上不得出现半截文件(atomic_write 失败即无目标文件)
    backup2 = str(tmp_path / "data" / "config2.yml.bak")

    def interrupted(p, fn, keep_backup=False):
        def boom(f):
            f.write("半截")
            raise RuntimeError("模拟写盘中断")

        real_atomic(p, boom, keep_backup)

    monkeypatch.setattr(infra_utils, "atomic_write", interrupted)
    with pytest.raises(RuntimeError):
        writer_mod._backup(path, backup2)
    assert not os.path.exists(backup2), "写盘中断不得留半截 .bak(atomic_write 失败即无目标文件)"
    assert _text(backup) == _text(path), "已存在的旧备份在中断场景保持原样(不被截断)"


def test_collect_explicit_empty_paths_all_trackers():
    """v3→v4 显式置空收集: 非 dict 的 tracker 条目不得中断后续收集(continue 而非 break)"""
    from auto_qb.config.migrations import _collect_explicit_empty_paths

    cfg = {
        "remove_similar_tags": "",
        "trackers":
            {
                "Bad": "oops",  # 非 dict: 跳过它, 但不得中断后续 tracker 的收集
                "T1": {
                    "remove_similar_tags": "",
                    "hr": {
                        "add_tag": ""
                    }
                },
            },
    }
    paths = _collect_explicit_empty_paths(cfg)
    assert "config.remove_similar_tags" in paths, paths
    assert "config.trackers.T1.remove_similar_tags" in paths, paths
    assert "config.trackers.T1.hr.add_tag" in paths, paths


def test_url_host_shapes():
    """host 提取: 非串/解析失败 -> 空串(定位不到档案, 旧键原地保留); 正常 URL 小写化"""
    from auto_qb.config.migrations import _url_host

    assert _url_host(None) == ""
    assert _url_host(123) == ""
    assert _url_host("http://[::1/x") == "", "畸形 IPv6 -> ValueError -> 空串"
    assert _url_host("https://PT.BTSchool.club/myhr.php") == "pt.btschool.club"


def test_path_helpers_mid_node_shapes():
    """_set_path / _delete_path 的形状防御(纯函数直测): 中途节点非 dict 时 set 重建、delete 静默返回;
    单段路径打在非映射树上 delete 也是安全空转 —— R 级回退对烂形状的容错底座"""
    from auto_qb.config.writer import _delete_path, _set_path

    # set: 中途节点是标量 -> 整体替换为新 dict 再落值
    tree = {"config": {"web": "junk"}}
    _set_path(tree, ["config", "web", "port"], "123")
    assert tree["config"]["web"] == {"port": "123"}

    # set: 中途节点缺失 -> 现场建 dict
    tree = {"config": {}}
    _set_path(tree, ["config", "fs", "path_map"], [{"from": "a", "to": "b"}])
    assert tree["config"]["fs"]["path_map"] == [{"from": "a", "to": "b"}]

    # delete: 中途节点是标量 -> 无处可删, 原样返回不炸
    tree = {"config": {"web": "junk"}}
    _delete_path(tree, ["config", "web", "port"])
    assert tree["config"]["web"] == "junk"

    # delete: 中途节点缺失 -> 同样静默返回
    tree = {"config": {}}
    _delete_path(tree, ["config", "fs", "path_map"])
    assert tree == {"config": {}}

    # delete: 路径本身只有一段且树非映射 -> 循环零圈, 树不是 dict 则跳过 pop
    _delete_path("plain", ["config"])
    tree = {"config": {"a": 1}}
    _delete_path(tree, ["config", "a"])
    assert tree == {"config": {}}, "正常单段删除: 键被移除"


def test_prepare_passes_old_tree_to_restart_fallback(tmp_path, monkeypatch):
    """_prepare 调 R 级回退时 old_tree 必须来自 read_tree(**不是 None**)

    变异把 `_fallback_restart_fields(tree, old_tree, ...)` 的第二实参改成 None —— 回退就再也读不到
    磁盘旧值。守阵: 用 spy 验证收到的 old_tree 含磁盘真实段值(而不是被换成的 None).
    """
    from auto_qb.config import writer as writer_mod

    path = _make(tmp_path, BASE + "  data_dir: disk-dir\n")
    old_config = load_config(path)
    tree = read_tree(path)
    tree["config"]["data_dir"] = "ui-dir"
    seen = []
    real = writer_mod._fallback_restart_fields

    def spy(t, old_tree, changes):
        seen.append(old_tree)
        return real(t, old_tree, changes)

    monkeypatch.setattr(writer_mod, "_fallback_restart_fields", spy)
    writer_mod._prepare(path, tree, old_config)
    assert seen, "命中 R 闸时必须调用 R 级回退"
    assert seen[0]["config"]["data_dir"] == "disk-dir", "R 级回退必须拿到磁盘旧树(传 None 会回退失败)"


def test_build_yaml_preserves_quotes_and_indent_profile():
    """_build_yaml 的三项配置必须是项目 YAML 风格(引号保留 + 4/4/2 缩进)

    变异簇把 preserve_quotes 改成 None/False、indent 的 mapping/sequence/offset 改值或删参 —
    这些只改格式不改语义, 但正是「写回后文件可读性」的守阵面。直接断言 ruamel 实例属性。
    """
    from auto_qb.config.writer import _build_yaml

    ry = _build_yaml()
    assert ry.preserve_quotes is True, "必须保留磁盘原有引号形态"
    assert ry.map_indent == 4, "映射缩进 4(与原 config.yml 风格一致)"
    assert ry.sequence_indent == 4, "序列缩进 4"
    assert ry.sequence_dash_offset == 2, "序列破折号偏移 2"


def test_build_doc_reads_existing_and_falls_back_to_empty(tmp_path):
    """_build_doc: 已存在文件读为 CommentedMap; 非映射/不存在 -> 以空文档重建

    变异把 `doc = None` 改成 `doc = ""`(初始值形状)或把 open 的 `"r"` 删掉 —— 前者在
    「文件不存在」时 `isinstance(doc, dict)` 仍为 False 从而走 {} 分支(看似无害, 实则丢了
    None 哨兵语义); 这条直接覆盖两条路径的行为契约.
    """
    from auto_qb.config.writer import _build_doc

    path = _make(tmp_path, "config:\n    web:\n        # 注释\n        port: 1\n")
    doc = _build_doc(path, {"config": {"web": {"port": "2"}}})
    assert isinstance(doc, dict)
    assert doc["config"]["web"]["port"] == 2, "树的值须同步进文档"

    # 文件不存在 -> 从空文档建起, 树内容仍完整同步
    missing = str(tmp_path / "nope.yml")
    doc2 = _build_doc(missing, {"config": {"web": {"port": "3"}}})
    assert isinstance(doc2, dict) and doc2["config"]["web"]["port"] == 3

    # 磁盘是非映射 YAML -> 以空文档重建
    np = _make(tmp_path, "- a\n- b\n")
    doc3 = _build_doc(np, {"config": {"web": {"port": "4"}}})
    assert isinstance(doc3, dict) and doc3["config"]["web"]["port"] == 4


def test_fallback_helpers_split_dot_paths_and_rebuild_missing_nodes(tmp_path):
    """R 级/readonly 回退必须按 `.` 正确切分点路径并重建中途节点

    变异簇: `.split(".")` 改 `.split(None)`/`"XX.XX"`(切分错 → 找不到旧值); `_set_path` 的
    `node.get(p)` 改 None/get(None)(中途节点被无视 → 结构写错位). 这条用「磁盘有旧值须覆盖」
    +「磁盘无旧值须删除」两侧夹住.
    """
    from auto_qb.config.impact import ConfigChange
    from auto_qb.config.writer import _fallback_restart_fields

    # 磁盘旧值存在(嵌套路径 state_file 在 config 段下) -> 提交树的新值被覆盖为旧值
    old_tree = {"config": {"state_file": "old-state.json", "nested": {"x": "old"}}}
    tree = {"config": {"state_file": "new-state.json", "nested": {"x": "new"}}}
    changes = [
        ConfigChange(path="state_file", old="old-state.json", new="new-state.json"),
        ConfigChange(path="nested.x", old="old", new="new"),
    ]
    _fallback_restart_fields(tree, old_tree, changes)
    assert tree["config"]["state_file"] == "old-state.json", "点路径切分正确才能取到旧值"
    assert tree["config"]["nested"]["x"] == "old", "嵌套点路径须正确切分并覆盖"

    # 磁盘无旧值 -> 键须被删除(走默认值), 不得把 None 写进去
    tree2 = {"config": {"data_dir": "ui-dir"}}
    _fallback_restart_fields(tree2, {"config": {}}, [ConfigChange(path="data_dir", old=None, new="ui-dir")])
    assert "data_dir" not in tree2["config"], "磁盘未配置的 R 级键须删除, 不是写成 None"


def test_delete_path_removes_last_segment_only():
    """_delete_path 必须删**最后一段**(变异把 parts[-1] 改成 parts[+1] → IndexError/删错键)"""
    from auto_qb.config.writer import _delete_path

    tree = {"config": {"a": "1", "b": "2"}}
    _delete_path(tree, ["config", "a"])
    assert tree == {"config": {"b": "2"}}, "须精确删除目标键, 不动兄弟键"

    # 单段路径: parts[-1] == parts[0], 同样必须命中
    tree2 = {"only": "1"}
    _delete_path(tree2, ["only"])
    assert tree2 == {}

    # 末段不存在: 静默无操作(不抛)
    _delete_path({"config": {}}, ["config", "ghost"])


def test_sync_mapping_skips_unchanged_scalar_and_list_nodes():
    """_sync_mapping「值未变则不动原节点」必须对**标量与列表**都成立

    变异簇把 _same_value 的两侧实参换成 None、或把 `not isinstance(...)` 的 and 链写坏 —— 后果是
    「未修改的节点被重写」, 表现为磁盘上的引号/注释形态漂移。守阵: 用带引号标量与列表两类节点
    夹住「未变保持原对象」这个契约(注释保留是它的可观测副作用).
    """
    from ruamel.yaml.comments import CommentedMap

    from auto_qb.config.writer import _sync_mapping

    doc = CommentedMap()
    doc["port"] = "16585"  # 磁盘原标量(ruamel 读作 str, 因为引号形态)
    doc.yaml_set_comment_before_after_key("port", before="keep-me", after="tail")
    doc["tags"] = ["A", "B"]
    port_node = doc["port"]
    tags_node = doc["tags"]

    # 树里的值与磁盘同构(标量字符串一致 / 列表项一致) -> 必须跳过赋值, 原节点不动
    _sync_mapping(doc, {"port": "16585", "tags": ["A", "B"]})
    assert doc["port"] is port_node, "未变化的标量不得被替换(否则注释/引号形态被重写)"
    assert doc["tags"] is tags_node, "未变化的列表不得被替换"
    assert doc.get("port") == "16585"

    # 值真变了 -> 替换
    _sync_mapping(doc, {"port": "999", "tags": ["C"]})
    assert doc["port"] == 999 or doc["port"] == "999"
    assert list(doc["tags"]) == ["C"]

    # 树里缺失的键 -> 从磁盘删除
    _sync_mapping(doc, {})
    assert "port" not in doc and "tags" not in doc


def test_sync_mapping_scalar_vs_container_not_skipped():
    """_sync_mapping 的类型分派: `not isinstance(value, (dict, list)) and not isinstance(existing, ...)`
    的 and 链不得被写坏(变异把两侧 not 去掉/换 or → 标量与容器互转时误跳过或误比较)

    守阵: ①标量值覆盖容器节点 ②容器值覆盖标量节点 —— 两种都不得被"未变化"逻辑吞掉.
    """
    from ruamel.yaml.comments import CommentedMap

    from auto_qb.config.writer import _sync_mapping

    # 标量 -> 覆盖磁盘上的 dict 节点
    doc = CommentedMap()
    doc["x"] = CommentedMap()
    doc["x"]["old"] = "1"
    _sync_mapping(doc, {"x": "scalar"})
    assert doc["x"] == "scalar", "标量须能覆盖原容器节点(类型不同不得误判为未变)"

    # dict -> 覆盖磁盘上的标量节点
    doc2 = CommentedMap()
    doc2["y"] = "plain"
    _sync_mapping(doc2, {"y": {"k": "v"}})
    assert isinstance(doc2["y"], dict) and doc2["y"]["k"] == "v", "容器须能覆盖原标量节点"


def test_same_value_none_and_as_builtin_semantics():
    """_same_value/_as_builtin 的 BaseLoader 语义(变异把两侧实参换 None / 布尔小写化写坏)

    - `existing is None` -> False(空节点不算「未变化」)
    - 布尔统一小写字符串; None -> ""; 数字 -> str; 容器递归
    """
    from auto_qb.config.writer import _as_builtin, _same_value

    assert _same_value(None, "x") is False, "existing 为 None 必须判为「有变化」"
    assert _same_value("true", True) is True, "字符串 true 与 bool True 在 BaseLoader 语义下同值"
    assert _same_value("16585", 16585) is True
    assert _same_value("1", "2") is False

    assert _as_builtin(True) == "true" and _as_builtin(False) == "false", "布尔须小写字符串化"
    assert _as_builtin(None) == "", "None -> 空串"
    assert _as_builtin(7) == "7", "数字 -> 字符串"
    assert _as_builtin({"a": True}) == {"a": "true"}, "映射递归且键字符串化"
    assert _as_builtin([1, False]) == ["1", "false"], "列表递归"


def test_plain_scalar_bool_and_lossless_rules():
    """_plain_scalar: 布尔识别大小写无关且**信息无损**才转换

    变异把 `low` 改成 `hi`/`FALSE` —— 「FALSE」将不再被识别为布尔, 写回时形态漂移。守阵覆盖
    大小写两侧 + 有损数字串(007/1.10)必须保持字符串.
    """
    from auto_qb.config.writer import _plain_scalar

    assert _plain_scalar("true") is True
    assert _plain_scalar("TRUE") is True, "布尔识别须大小写无关"
    assert _plain_scalar("False") is False
    assert _plain_scalar("FALSE") is False, "布尔识别须大小写无关(小写化后再判定)"
    assert _plain_scalar("16585") == 16585
    assert _plain_scalar("007") == "007", "有损(前导零)不得转换"
    assert _plain_scalar("1.10") == "1.10", "有损(尾零)不得转换"
    assert _plain_scalar({"a": ["TRUE", "1"]}) == {"a": [True, 1]}, "递归处理新子树"


def test_set_path_rebuilds_non_mapping_mid_nodes():
    """_set_path 中途节点非映射时必须**重建为 dict**(变异把 `node.get(p)` 改 None/get(None))

    前者让已存在的 dict 节点被无视而覆盖重建(丢兄弟键); 后者拿不到任何节点。守阵用 spy 语义:
    已有 dict 的中途节点须**原地复用**(兄弟键保留), 非 dict 的须重建.
    """
    from auto_qb.config.writer import _set_path

    # 中途节点已是 dict -> 原地复用, 兄弟键保留
    tree = {"config": {"web": {"port": "1", "host": "h"}}}
    _set_path(tree, ["config", "web", "port"], "2")
    assert tree["config"]["web"] == {"port": "2", "host": "h"}, "须复用已有 dict 节点(不丢兄弟键)"

    # 中途节点是标量 -> 重建为 dict
    tree2 = {"config": {"web": "junk"}}
    _set_path(tree2, ["config", "web", "port"], "3")
    assert tree2["config"]["web"] == {"port": "3"}

    # 中途节点缺失 -> 现场建 dict
    tree3 = {"config": {}}
    _set_path(tree3, ["config", "fs", "path_map"], ["x"])
    assert tree3["config"]["fs"]["path_map"] == ["x"]


def test_backup_skips_when_source_missing_and_keeps_encoding(tmp_path):
    """_backup: 源文件不存在时**直接返回**(不建任何东西); 存在时按 utf-8 读并原子写

    变异簇: `os.path.dirname` → None(父目录漏建) + open 的 `"r"` 被删 —— 前者让嵌套备份目录
    不建, 后者改变读模式语义。守阵两侧夹住。
    """
    from auto_qb.config import writer as writer_mod

    missing = str(tmp_path / "nope.yml")
    nested_backup = tmp_path / "deep" / "x.bak"
    writer_mod._backup(missing, str(nested_backup))
    assert not nested_backup.exists() and not (tmp_path / "deep").exists(), "源缺失时零副作用"

    path = _make(tmp_path, BASE)
    writer_mod._backup(path, str(nested_backup))
    assert nested_backup.exists(), "须按 dirname 建父目录并落备份"
    with open(nested_backup, encoding="utf-8") as f:
        assert f.read() == BASE

    # 非 ASCII 内容往返(验证 utf-8 读写契约)
    path2 = _make(tmp_path, BASE + "  web:\n    title: 中文标题\n")
    b2 = str(tmp_path / "deep2" / "y.bak")
    writer_mod._backup(path2, b2)
    with open(b2, encoding="utf-8") as f:
        assert "中文标题" in f.read(), "utf-8 读取须无损"
