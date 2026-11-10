"""test_config_writer_mask 测试计划: 配置写回(结构化树 -> 校验 -> R 级回退 -> round-trip 写盘)

## 测试计划(每个测试函数一条)
- test_mask_tree_hides_sensitive_scalars: 敏感键(键名含 password/passkey/token)的非空标量被掩码; 空值与普通键不受影响; 原树不被就地修改
- test_unmask_tree_restores_from_disk: 提交树里的掩码哨兵按磁盘旧值还原 —— 前端"未改密码"原样保存不会把密码写成占位串
- test_unmask_tree_restores_nested_and_toplevel: 哨兵还原遍历整棵树, 嵌套分支命中后顶层后续键仍还原
- test_mask_tree_non_dict_passthrough: 掩码只处理映射, 列表整体不动
- test_unmask_tree_guards_and_sentinel_old_value: 非映射树原样返回; 旧值缺失/本身是哨兵时保持哨兵
- test_unmask_tree_init_and_guards: unmask_tree 非映射入口原样返回; 旧值缺失/旧值即哨兵时保持哨兵
- test_unmask_tree_only_touches_sentinel_values: unmask_tree 只还原恰为哨兵的键, 用户真改的值不得被旧值覆盖
- test_mask_tree_recurses_into_nested_dicts: mask_tree 递归进嵌套映射掩码深层敏感键; 空值不掩码; 原树不改
- test_mask_tree_masks_transfer_target_passwords: targets 定向下钻(计划 26-10-31-0306 D4) —— 条目非空 password 掩码, 空密码/非敏感字段不动; 非定向键面的列表仍整体不动; 重复掩码幂等
- test_transfer_targets_mask_roundtrip_write: GET→PUT 往返无损 —— 多条目各还原各的旧值, 重复还原零变化, 写盘后磁盘仍是各自真密码且无哨兵
- test_unmask_transfer_targets_typed_and_new_entries: 用户真改的密码/新增条目的密码(含空)原样保留, 不得被旧值覆盖
- test_unmask_transfer_targets_rename_and_delete_pairing: 配对两轮 —— name 为主, 等量剩余按下标兜底「只改名」; 删除后幸存者按 name 对上; 改名+删除(数量不等)不猜, 哨兵原样留下; 旧值缺失/即哨兵同守卫
- test_unmask_transfer_targets_swap_rename_identity_guard: 第二轮下标配对前做非敏感身份键(type/base_url)一致性核对(批次4 #16) —— 两以上条目同时改名且顺序对调不串密码(哨兵留下), 正常对位仍回填, 身份键缺失不算反证
- test_transfer_target_api_key_mask_and_unmask: targets 条目 api_key 与 password 同套哨兵(issue 26-11-01-0335) —— 非空掩码/空不掩/GET→PUT 还原旧值; 逐键判定(只改 password 不动 api_key 哨兵, 反之亦然)
- test_mask_tree_target_non_dict_entry_passthrough: targets 里的非 dict 条目掩码原样放行(交给校验层报错), dict 条目照常掩码
- test_unmask_targets_skips_non_dict_and_unnamed_old_entries: 旧表非 dict 条目/无名条目不进 name 索引; 提交表非 dict 条目跳过还原; 按 name 配对照常
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


def test_mask_tree_hides_sensitive_scalars():
    """掩码只作用于 dict 内非空标量: 密码/passkey/token 类键被替换, 空值与普通键原样返回

    空值不掩码是刻意的 —— 空密码掩码后前端会以为"已设置密码", 反而误导。
    """
    from auto_qb.config.writer import MASK_SENTINEL, mask_tree

    tree = {
        "config":
            {
                "qbittorrent": {
                    "host": "h",
                    "username": "u",
                    "password": "p"
                },
                "web": {
                    "token": "",
                    "enabled": "true"
                },
            }
    }
    masked = mask_tree(tree)
    assert masked["config"]["qbittorrent"]["password"] == MASK_SENTINEL
    assert masked["config"]["qbittorrent"]["host"] == "h", "非敏感键不得被动到"
    assert masked["config"]["web"]["token"] == "", "空值不掩码(否则前端以为已设置)"
    assert tree["config"]["qbittorrent"]["password"] == "p", "掩码不得就地修改原树"


def test_unmask_tree_restores_from_disk(tmp_path):
    """提交树里的哨兵按磁盘旧值还原: 前端"没改密码"地原样保存不会把密码写成占位串

    这是掩码能否成立的关键 —— 只掩码不还原的话, 一次保存就会毁掉生产配置里的 qB 密码。
    """
    from auto_qb.config.writer import MASK_SENTINEL, mask_tree, unmask_tree

    path = _make(tmp_path, BASE)
    old = read_tree(path)
    submitted = mask_tree(old)
    assert submitted["config"]["qbittorrent"]["password"] == MASK_SENTINEL, "前置: GET 侧确实掩码了"

    submitted["config"]["main_tick"] = "5s"  # 模拟用户只改了一个无关字段
    unmask_tree(submitted, old)
    assert submitted["config"]["qbittorrent"]["password"] == "p", "哨兵应还原为磁盘旧值"

    write_tree(path, submitted, load_config(path), _bak(tmp_path))
    text = _text(path)
    assert "password: p" in text, f"未改密码不应被写成占位串: {text}"
    assert "5s" in text, "真正改动的字段仍应写回"


def test_unmask_tree_restores_nested_and_toplevel():
    """哨兵还原须遍历整棵树: 嵌套分支命中后不得中断顶层遍历(continue 而非 break)"""
    from auto_qb.config.writer import MASK_SENTINEL, unmask_tree

    tree = {"qbittorrent": {"password": MASK_SENTINEL}, "token": MASK_SENTINEL}
    old = {"qbittorrent": {"password": "p"}, "token": "t"}
    unmask_tree(tree, old)
    assert tree["qbittorrent"]["password"] == "p", "嵌套分支应还原"
    assert tree["token"] == "t", "嵌套分支命中后, 顶层后续键仍须还原"


def test_mask_tree_non_dict_passthrough():
    """掩码只处理映射: 顶层/嵌套列表整体不动(列表项无法与磁盘旧值稳定对应)"""
    from auto_qb.config.writer import mask_tree

    assert mask_tree(["a", "b"]) == ["a", "b"]
    assert mask_tree({"config": {
        "delete_tags": ["X", "Y"],
        "web": {
            "token": "secret"
        }
    }})["config"]["delete_tags"] == ["X", "Y"]
    assert mask_tree({"config": {"web": {"token": "secret"}}})["config"]["web"]["token"] == "********"


def test_unmask_tree_guards_and_sentinel_old_value():
    """还原守卫: 非映射树原样返回; 旧值缺失/旧值本身是哨兵时保持哨兵(宁可占位不可静默清密)"""
    from auto_qb.config.writer import MASK_SENTINEL, unmask_tree

    assert unmask_tree("plain", {}) == "plain"
    tree = {"config": {"password": MASK_SENTINEL}}
    # 旧值就是哨兵: 保持不动
    out = unmask_tree(copy.deepcopy(tree), {"config": {"password": MASK_SENTINEL}})
    assert out["config"]["password"] == MASK_SENTINEL
    # 旧值缺失: 同样保持哨兵, 不静默写成空
    out = unmask_tree(copy.deepcopy(tree), {"config": {}})
    assert out["config"]["password"] == MASK_SENTINEL
    # 旧值真实存在: 回填
    out = unmask_tree(copy.deepcopy(tree), {"config": {"password": "real"}})
    assert out["config"]["password"] == "real"


_TRANSFER_YAML = (
    "config:\n"
    "  schema_version: 8\n"
    "  qbittorrent:\n"
    "    host: h\n"
    "    port: 1\n"
    "    username: u\n"
    "    password: p\n"
    "  web:\n"
    "    transfer:\n"
    "      targets:\n"
    "        - name: a\n"
    "          type: qb\n"
    "          base_url: http://a:8080\n"
    "          username: ua\n"
    "          password: pa\n"
    "          enabled: false\n"
    "        - name: b\n"
    "          type: qb\n"
    "          base_url: http://b:8080\n"
    "          username: ub\n"
    "          password: pb\n"
    "          enabled: false\n"
    "          after_state: paused\n"
)


def test_mask_tree_masks_transfer_target_passwords():
    """targets 定向下钻: 条目非空 password 掩码, 空密码与非敏感字段不动; 其它列表仍整体不动

    只对 config.web.transfer.targets 这一条已知键面下钻(条目有 name 唯一键, 可与磁盘旧条目
    稳定配对), 不做通用列表递归 —— 其它列表(path_map/trackers 等)没有稳定配对键, 掩了还原不回。
    """
    from auto_qb.config.writer import MASK_SENTINEL, mask_tree

    tree = {
        "config":
            {
                "web":
                    {
                        "transfer":
                            {
                                "targets":
                                    [
                                        {
                                            "name": "a",
                                            "password": "pa",
                                            "enabled": "false"
                                        },
                                        {
                                            "name": "b",
                                            "password": "",
                                            "enabled": "true"
                                        },
                                    ]
                            }
                    },
                "web_plain": {
                    "targets": [{
                        "name": "x",
                        "password": "px"
                    }]
                },  # 非定向键面
            }
    }
    masked = mask_tree(tree)
    targets = masked["config"]["web"]["transfer"]["targets"]
    assert targets[0]["password"] == MASK_SENTINEL, "targets 条目非空 password 应掩码"
    assert targets[0]["name"] == "a" and targets[0]["enabled"] == "false", "非敏感字段不得被动到"
    assert targets[1]["password"] == "", "空密码不掩码(否则前端以为已设置)"
    assert masked["config"]["web_plain"]["targets"][0]["password"] == "px", "非定向键面的列表不下钻"
    assert tree["config"]["web"]["transfer"]["targets"][0]["password"] == "pa", "掩码不得就地修改原树"
    assert mask_tree(masked) == masked, "重复掩码幂等(哨兵再掩码仍是哨兵)"


def test_transfer_targets_mask_roundtrip_write(tmp_path):
    """GET→PUT 往返无损(多条目各还原各的旧值): 掩码保存后磁盘仍是各自真密码, 且二轮稳定"""
    from auto_qb.config.writer import MASK_SENTINEL, mask_tree, unmask_tree

    path = _make(tmp_path, _TRANSFER_YAML)
    old = read_tree(path)
    submitted = mask_tree(old)
    targets = submitted["config"]["web"]["transfer"]["targets"]
    assert targets[0]["password"] == MASK_SENTINEL and targets[1]["password"] == MASK_SENTINEL, \
        "前置: GET 侧确实掩码了"

    submitted["config"]["main_tick"] = "5s"  # 模拟用户只改了一个无关字段
    unmask_tree(submitted, old)
    assert targets[0]["password"] == "pa" and targets[1]["password"] == "pb", "各条目还原各自的旧值"
    snapshot = copy.deepcopy(submitted)
    unmask_tree(submitted, old)
    assert submitted == snapshot, "重复还原必须零变化(幂等)"

    write_tree(path, submitted, load_config(path), _bak(tmp_path))
    text = _text(path)
    assert "password: pa" in text and "password: pb" in text, f"磁盘应保留各自真密码: {text}"
    assert MASK_SENTINEL not in text, "哨兵不得落盘"


def test_unmask_transfer_targets_typed_and_new_entries():
    """用户真改的密码/新增条目的密码(含空)原样保留 —— 哨兵之外的一律不还原"""
    from auto_qb.config.writer import mask_tree, unmask_tree

    old = {"config": {"web": {"transfer": {"targets": [{"name": "a", "password": "pa"}]}}}}
    submitted = mask_tree(copy.deepcopy(old))
    targets = submitted["config"]["web"]["transfer"]["targets"]
    targets[0]["password"] = "new-pa"  # 用户在编辑器键入了新密码(留空 = 不修改语义的另一侧)
    targets.append({"name": "c", "password": "pc"})  # 新增条目(带密码)
    targets.append({"name": "d", "password": ""})  # 新增条目(未填密码)
    unmask_tree(submitted, old)
    assert targets[0]["password"] == "new-pa", "真改的密码不得被旧值覆盖"
    assert targets[1]["password"] == "pc", "新增条目的密码原样保留"
    assert targets[2]["password"] == "", "新增条目的空密码原样保留"


def test_unmask_transfer_targets_rename_and_delete_pairing():
    """条目配对两轮: 按 name 为主(唯一键), 等量剩余按下标兜底「只改名」; 数量不等不猜

    改名是唯一 name 配不上的常见形态: 剩余数量相等时按下标配对(顺序未动 = 改名),
    覆盖「改名但保留密码」; 数量不等说明同时增删过, 不猜 —— 哨兵原样留下, 与顶层标量
    「旧值缺失保持哨兵」同口径(宁可留明显占位串让人发现, 不静默写错密码)。
    """
    from auto_qb.config.writer import MASK_SENTINEL, unmask_tree

    def _tree(targets):
        return {"config": {"web": {"transfer": {"targets": targets}}}}

    # 只改名: name 配不上, 等量剩余按下标兜底还原
    old = _tree([{"name": "a", "password": "pa"}])
    submitted = _tree([{"name": "x", "password": MASK_SENTINEL}])
    unmask_tree(submitted, old)
    assert submitted["config"]["web"]["transfer"]["targets"][0]["password"] == "pa", "只改名应按下标兜底还原"

    # 删除后条目前移: 幸存者按 name 对上(下标已错位, 位置配对会写错)
    old = _tree([{"name": "a", "password": "pa"}, {"name": "b", "password": "pb"}])
    submitted = _tree([{"name": "b", "password": MASK_SENTINEL}])
    unmask_tree(submitted, old)
    assert submitted["config"]["web"]["transfer"]["targets"][0]["password"] == "pb"

    # 改名 + 删除(剩余数量不等): 不猜, 哨兵原样留下
    old = _tree([{"name": "a", "password": "pa"}, {"name": "b", "password": "pb"}])
    submitted = _tree([{"name": "x", "password": MASK_SENTINEL}])
    unmask_tree(submitted, old)
    assert submitted["config"]["web"]["transfer"]["targets"][0]["password"] == MASK_SENTINEL

    # 磁盘旧值本身是哨兵/缺失: 保持哨兵(与顶层标量同守卫, 宁可占位不可静默写空)
    old = _tree([{"name": "a", "password": MASK_SENTINEL}])
    submitted = _tree([{"name": "a", "password": MASK_SENTINEL}])
    unmask_tree(submitted, old)
    assert submitted["config"]["web"]["transfer"]["targets"][0]["password"] == MASK_SENTINEL
    submitted = _tree([{"name": "a", "password": MASK_SENTINEL}])
    unmask_tree(submitted, _tree([]))
    assert submitted["config"]["web"]["transfer"]["targets"][0]["password"] == MASK_SENTINEL


def test_unmask_transfer_targets_swap_rename_identity_guard():
    """第二轮下标配对前做非敏感身份键一致性核对(批次4 #16): 顺序对调的改名不串密码

    旧 [T1(pa), T2(pb)], 提交 [X(原T2改名c, 哨兵), Y(原T1改名d, 哨兵)] 相对顺序被调换:
    数量相等即 zip 配对会把 T1 的 pa 回填进 X(base_url 是 T2 的)—— 凭据静默写串。
    type/base_url 在改名场景原样保留, 是仅有的稳定身份锚: 有非空值且不同 = 配错对象,
    不猜, 哨兵原样留下(与「数量不等不猜」同口径); 正常对位(只改名不调序)仍回填成功;
    身份键缺失/空值不算反证(改名 + 未配 base_url 的合法编辑不被误拒)。
    """
    from auto_qb.config.writer import MASK_SENTINEL, unmask_tree

    def _tree(targets):
        return {"config": {"web": {"transfer": {"targets": targets}}}}

    # 顺序对调: X(原T2)按下标对上 T1, base_url 不同 -> 不猜, 哨兵原样留下
    old = _tree(
        [
            {
                "name": "T1",
                "type": "webdav",
                "base_url": "https://a",
                "password": "pa"
            },
            {
                "name": "T2",
                "type": "webdav",
                "base_url": "https://b",
                "password": "pb"
            },
        ]
    )
    submitted = _tree(
        [
            {
                "name": "c",
                "type": "webdav",
                "base_url": "https://b",
                "password": MASK_SENTINEL
            },
            {
                "name": "d",
                "type": "webdav",
                "base_url": "https://a",
                "password": MASK_SENTINEL
            },
        ]
    )
    unmask_tree(submitted, old)
    targets = submitted["config"]["web"]["transfer"]["targets"]
    assert targets[0]["password"] == MASK_SENTINEL, "base_url 对不上 = 配错对象, 不得把 T1 密码回填进 X"
    assert targets[1]["password"] == MASK_SENTINEL, "Y 对 T2 同样身份矛盾, 不回填"

    # 只改名不调序: 身份键两边一致 -> 仍按下标配对正常回填(不误伤既有「只改名」覆盖面)
    old2 = _tree(
        [
            {
                "name": "T1",
                "type": "webdav",
                "base_url": "https://a",
                "password": "pa"
            },
            {
                "name": "T2",
                "type": "webdav",
                "base_url": "https://b",
                "password": "pb"
            },
        ]
    )
    submitted2 = _tree(
        [
            {
                "name": "d",
                "type": "webdav",
                "base_url": "https://a",
                "password": MASK_SENTINEL
            },
            {
                "name": "c",
                "type": "webdav",
                "base_url": "https://b",
                "password": MASK_SENTINEL
            },
        ]
    )
    unmask_tree(submitted2, old2)
    targets2 = submitted2["config"]["web"]["transfer"]["targets"]
    assert targets2[0]["password"] == "pa", "正常对位(身份键一致)仍回填成功"
    assert targets2[1]["password"] == "pb"

    # type 不同同样拦下(base_url 双方都未配时 type 是唯一锚)
    old3 = _tree([{"name": "T1", "type": "webdav", "password": "pa"}])
    submitted3 = _tree([{"name": "x", "type": "smb", "password": MASK_SENTINEL}])
    unmask_tree(submitted3, old3)
    assert submitted3["config"]["web"]["transfer"]["targets"][0]["password"] == MASK_SENTINEL, \
        "type 对不上不回填"

    # 身份键缺失不算反证: 只改名 + 双方都没配身份键, 维持原位置配对语义
    old4 = _tree([{"name": "T1", "password": "pa"}])
    submitted4 = _tree([{"name": "x", "password": MASK_SENTINEL}])
    unmask_tree(submitted4, old4)
    assert submitted4["config"]["web"]["transfer"]["targets"][0]["password"] == "pa", \
        "身份键都缺失时不得误拒合法改名编辑"


def test_transfer_target_api_key_mask_and_unmask():
    """targets 条目 api_key 与 password 同套哨兵(issue 26-11-01-0335): 非空掩码/空不掩/还原旧值; 逐键判定互不覆盖"""
    from auto_qb.config.writer import MASK_SENTINEL, mask_tree, unmask_tree

    old = {
        "config":
            {
                "web":
                    {
                        "transfer":
                            {
                                "targets":
                                    [
                                        {
                                            "name": "a",
                                            "password": "pa",
                                            "api_key": "qbt_key"
                                        },
                                        {
                                            "name": "b",
                                            "password": "pb",
                                            "api_key": ""
                                        },
                                    ]
                            }
                    }
            }
    }
    submitted = mask_tree(copy.deepcopy(old))
    targets = submitted["config"]["web"]["transfer"]["targets"]
    assert targets[0]["api_key"] == MASK_SENTINEL, "非空 api_key 应与 password 同掩码"
    assert targets[0]["password"] == MASK_SENTINEL
    assert targets[1]["api_key"] == "", "空 api_key 不掩码(与空密码同口径)"

    # 逐键判定: 用户真改了 password、api_key 留哨兵 -> 只回填 api_key, 新 password 不被旧值覆盖
    targets[0]["password"] = "new-pa"
    unmask_tree(submitted, old)
    assert targets[0]["password"] == "new-pa", "真改的 password 不得被旧值覆盖"
    assert targets[0]["api_key"] == "qbt_key", "哨兵 api_key 还原为磁盘旧值"
    assert targets[1]["password"] == "pb" and targets[1]["api_key"] == ""

    # 只改 api_key: password 哨兵不受影响, 同一轮各回各的
    old2 = {"config": {"web": {"transfer": {"targets": [{"name": "a", "password": "pa", "api_key": "old_key"}]}}}}
    submitted2 = mask_tree(copy.deepcopy(old2))
    t2 = submitted2["config"]["web"]["transfer"]["targets"]
    t2[0]["api_key"] = "new_key"
    unmask_tree(submitted2, old2)
    assert t2[0]["api_key"] == "new_key", "真改的 api_key 不得被旧值覆盖"
    assert t2[0]["password"] == "pa", "未动的 password 哨兵照常还原"


def test_mask_tree_target_non_dict_entry_passthrough():
    """targets 里的非 dict 条目(手编畸形)掩码原样放行, 交给校验层报错; dict 条目照常掩码"""
    from auto_qb.config.writer import MASK_SENTINEL, mask_tree

    tree = {"config": {"web": {"transfer": {"targets": ["junk", {"name": "a", "password": "pa"}]}}}}
    masked = mask_tree(tree)
    targets = masked["config"]["web"]["transfer"]["targets"]
    assert targets[0] == "junk", "非 dict 条目原样放行"
    assert targets[1]["password"] == MASK_SENTINEL, "dict 条目照常掩码"
    assert tree["config"]["web"]["transfer"]["targets"][0] == "junk", "掩码不得就地修改原树"


def test_unmask_targets_skips_non_dict_and_unnamed_old_entries():
    """旧表非 dict 条目 / 无名(空 name)条目不进 name 索引; 提交表非 dict 条目跳过还原

    按 name 配对的主路径不受畸形条目影响 —— 有名旧条目照常认领回填。
    """
    from auto_qb.config.writer import MASK_SENTINEL, unmask_tree

    old = {
        "config":
            {
                "web":
                    {
                        "transfer":
                            {
                                "targets":
                                    [
                                        "junk",  # 非 dict 旧条目: 不进 name 索引, 也不进位置配对
                                        {
                                            "name": "",
                                            "password": "px"
                                        },  # 无名旧条目: 不进 name 索引
                                        {
                                            "name": "a",
                                            "password": "pa"
                                        },
                                    ]
                            }
                    },
            }
    }
    submitted = {
        "config":
            {
                "web":
                    {
                        "transfer":
                            {
                                "targets": [
                                    "junk",  # 提交表非 dict 条目: 原样跳过
                                    {
                                        "name": "a",
                                        "password": MASK_SENTINEL
                                    },
                                ]
                            }
                    }
            }
    }
    unmask_tree(submitted, old)
    targets = submitted["config"]["web"]["transfer"]["targets"]
    assert targets[0] == "junk", "提交表非 dict 条目不动"
    assert targets[1]["password"] == "pa", "有名条目按 name 正常配对还原"


def test_unmask_tree_init_and_guards():
    """unmask_tree 的入口守卫与哨兵判定(变异把 isinstance 判断/环回写坏)

    - 非映射 tree 或 old_tree -> 原样返回(不做任何写)
    - 哨兵命中但旧值缺失/旧值本身也是哨兵 -> 保持哨兵(不静默清空密码)
    """
    from auto_qb.config.writer import MASK_SENTINEL, unmask_tree

    assert unmask_tree("plain", {"config": {}}) == "plain", "非映射 tree 原样返回"
    assert unmask_tree({"config": {}}, "plain") == {"config": {}}, "非映射 old_tree 原样返回"

    # 哨兵 + 旧值也是哨兵 -> 保持(宁可占位)
    t = {"config": {"password": MASK_SENTINEL}}
    out = unmask_tree(copy.deepcopy(t), {"config": {"password": MASK_SENTINEL}})
    assert out["config"]["password"] == MASK_SENTINEL
    # 哨兵 + 旧值缺失 -> 保持
    out2 = unmask_tree(copy.deepcopy(t), {"config": {}})
    assert out2["config"]["password"] == MASK_SENTINEL
    # 哨兵 + 有真实旧值 -> 回填
    out3 = unmask_tree(copy.deepcopy(t), {"config": {"password": "real"}})
    assert out3["config"]["password"] == "real"


def test_unmask_tree_only_touches_sentinel_values():
    """unmask_tree 只还原**值恰为哨兵**的键; 旧树里有值但提交值不是哨兵时不得改动

    变异把 `value == MASK_SENTINEL` 写成 `!=` 或对非哨兵值也回填 —— 后果是「用户真改了值却被
    磁盘旧值覆盖」, 这是掩码链路最危险的静默数据丢失。守阵两侧夹住。
    """
    from auto_qb.config.writer import MASK_SENTINEL, unmask_tree

    # 提交值不是哨兵(用户真改了) -> 必须保留用户新值, 不得回填旧值
    tree = {"config": {"password": "user-changed", "token": "another"}}
    old = {"config": {"password": "disk-old", "token": "disk-token"}}
    unmask_tree(tree, old)
    assert tree["config"]["password"] == "user-changed", "非哨兵值不得被磁盘旧值覆盖"
    assert tree["config"]["token"] == "another"

    # 混合: 哨兵回填, 非哨兵保持
    tree2 = {"config": {"password": MASK_SENTINEL, "token": "new-token"}}
    unmask_tree(tree2, old)
    assert tree2["config"]["password"] == "disk-old", "哨兵须回填"
    assert tree2["config"]["token"] == "new-token", "非哨兵须保持"


def test_mask_tree_recurses_into_nested_dicts():
    """mask_tree 必须递归进嵌套映射(变异把递归分支写坏 -> 深层密码明文泄露)

    守阵: 深两层的敏感键必须被掩码, 且空值不掩码(空值掩码会误导前端以为已设置).
    """
    from auto_qb.config.writer import MASK_SENTINEL, mask_tree

    tree = {
        "config":
            {
                "qbittorrent": {
                    "password": "secret",
                    "user": "u"
                },
                "web": {
                    "authkey": "k",
                    "apikey": "plain"
                },
                "trackers": {
                    "T": {
                        "passkey": "pk",
                        "cookie": "ck"
                    }
                },
                "empty_password": "",
                "nothing": None,
            }
    }
    out = mask_tree(tree)
    cfg = out["config"]
    assert cfg["qbittorrent"]["password"] == MASK_SENTINEL
    assert cfg["qbittorrent"]["user"] == "u", "非敏感键不得被掩码"
    assert cfg["web"]["authkey"] == MASK_SENTINEL, "键名含 authkey -> 掩码"
    assert cfg["web"]["apikey"] == "plain", "不含敏感词的键不得被掩码"
    assert cfg["trackers"]["T"]["passkey"] == MASK_SENTINEL, "深层敏感键须递归掩码"
    assert cfg["trackers"]["T"]["cookie"] == MASK_SENTINEL
    assert cfg["empty_password"] == "" and cfg["nothing"] is None, "空值不掩码(避免误导已设置)"
    assert tree["config"]["qbittorrent"]["password"] == "secret", "原树不得被就地修改"
