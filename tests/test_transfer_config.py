"""test_transfer_config 测试计划: 种子转移配置层(web.transfer, 计划 26-10-31-0306 §03/§04-W1)

## 覆盖面(拍板 D3 per-target 字段集 / D4 配置存放 web.transfer / D9 转移后状态单选)
- 新建模板默认(§03 字段集表): 除超级做种外字段全开、保存路径锁死必开、跳检开、保持原状态、映射空、enabled 关(保守默认)
- 合法配置 load_config 往返无损(多目标 qb+tr、字段集显式值、映射表、密码等全字段)
- loader 字段集缺键补「新建模板默认」(键闭合完整产出, 下游不做缺键兜底)
- 非法 targets 聚合报错(一条配置多个非法点一次全报, 保存被拦不落盘)
- 字段集键闭合校验(未知键报错) + save_path 显式 false 拒绝(同机硬约束)
- 字段集值须为布尔(parse_bool 域)
- 路径映射规则表校验(列表形状/条目 {from, to} 键闭合/两侧非空)
- target 名称非空且全表唯一
- type 枚举(qb/tr)与 after_state 单选(keep/paused)
- base_url URL 形状(http(s)://host) + enabled=true 时必填
- 段/条目形状错误(transfer 非字典 / targets 非列表 / 条目非字典 / 各级未知键)
- 取值域常量单源守卫(validation 与 schema.fields 同一对象, is 断言)

## 测试计划(每个测试函数一条)
- test_transfer_default_template_matches_plan
- test_transfer_valid_config_round_trip
- test_transfer_fields_missing_keys_fill_template_defaults
- test_transfer_invalid_targets_aggregate_errors
- test_transfer_field_set_key_closure_and_save_path_locked
- test_transfer_field_set_values_must_be_bool
- test_transfer_path_map_validation
- test_transfer_target_name_required_and_unique
- test_transfer_type_and_after_state_enum
- test_transfer_base_url_shape_and_required_when_enabled
- test_transfer_section_shape_errors
- test_transfer_enum_constants_are_schema_derived
"""
import tempfile
from pathlib import Path

import yaml

from auto_qb.config import TransferConfig, TransferTargetConfig, default_transfer_fields, load_config, schema
from auto_qb.config.models import TRANSFER_FIELD_KEYS
from auto_qb.config.validation import validate_config

# 校验入口统一带 config 根节点(与真实 YAML 同构)
_VALID_TARGET = {
    "name": "backup-qb",
    "type": "qb",
    "base_url": "http://127.0.0.1:8081",
    "username": "admin",
    "password": "secret",
    "enabled": "true",
    "fields": {
        "category": "false",
        "super_seeding": "true"
    },
    "after_state": "paused",
    "skip_check": "false",
    "path_map": [{
        "from": "D:/Downloads",
        "to": "/mnt/downloads"
    }],
}


def _validate_transfer(transfer_spec):
    return validate_config({"config": {"web": {"transfer": transfer_spec}}})


def _write_and_load(transfer_spec) -> TransferConfig:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "config.yml"
        path.write_text(
            yaml.safe_dump({"config": {
                "web": {
                    "transfer": transfer_spec
                }
            }}, allow_unicode=True), encoding="utf-8"
        )
        return load_config(str(path)).web.transfer


# ---------------- 新建模板默认(计划 §03 字段集表; D3) ----------------


def test_transfer_default_template_matches_plan():
    """缺省 = 未配置(空目标表); 新建模板默认: 除超级做种外字段全开、跳检开、保持原状态、映射空、enabled 关"""
    cfg = TransferConfig()
    assert cfg.targets == ()
    d = TransferTargetConfig()
    assert d.enabled is False  # 保守默认(黄金法则 2): 转移是高风险动作
    assert d.type == "qb"  # qb 先行(tr 留接口 stub)
    assert d.after_state == "keep"  # D9: 保持原状态为默认
    assert d.skip_check is True  # 跳过校验默认开(未完成种子由执行层降级)
    assert d.path_map == ()  # 映射空 = 原样
    assert d.fields == {
        "save_path": True,  # 锁死必开(同机硬约束)
        "category": True,
        "tags": True,
        "share_ratio_limit": True,
        "seeding_time_limit": True,
        "up_limit": True,
        "down_limit": True,
        "super_seeding": False,  # 高危项默认关
    }


# ---------------- 合法配置往返无损(§04-W1 验收判据) ----------------


def test_transfer_valid_config_round_trip():
    """合法多目标配置(qb 启用 + tr 停用)经 load_config 真链路往返, 全字段无损; 校验零报错"""
    second = {
        "name": "tr-stub",
        "type": "tr",
        "base_url": "https://nas.example.local:9091",
        "username": "tr-user",
        "password": "tr-pass",
    }
    errs = _validate_transfer({"targets": [_VALID_TARGET, second]})
    assert errs == []
    loaded = _write_and_load({"targets": [_VALID_TARGET, second]})
    assert len(loaded.targets) == 2
    a, b = loaded.targets
    assert (a.name, a.type, a.base_url, a.username,
            a.password) == ("backup-qb", "qb", "http://127.0.0.1:8081", "admin", "secret")
    assert a.enabled is True
    assert a.after_state == "paused"
    assert a.skip_check is False
    # 字段集: 显式值保留, 未写的键补模板默认(合并结果, 键闭合)
    assert a.fields["category"] is False
    assert a.fields["super_seeding"] is True
    assert a.fields["save_path"] is True
    assert a.fields["tags"] is True
    assert len(a.path_map) == 1
    assert a.path_map[0].src == "D:/Downloads" and a.path_map[0].dst == "/mnt/downloads"
    # 未配任何可选键的目标: 全部落模板默认
    assert (b.name, b.type) == ("tr-stub", "tr")
    assert b.enabled is False
    assert b.fields == default_transfer_fields()
    assert b.path_map == ()


def test_transfer_fields_missing_keys_fill_template_defaults():
    """fields 只写部分键时, loader 把缺失键补成新建模板默认(产出键闭合完整字段集, 下游零缺键兜底)"""
    loaded = _write_and_load({"targets": [{"name": "t1", "fields": {"tags": "false"}}]})
    fields = loaded.targets[0].fields
    assert set(fields) == set(TRANSFER_FIELD_KEYS)  # 键闭合
    assert fields["tags"] is False  # 显式值原样保留
    for key, expected in default_transfer_fields().items():
        if key == "tags":
            continue
        assert fields[key] is expected, key


# ---------------- 非法 targets 聚合报错不落盘(§04-W1 验收判据) ----------------


def test_transfer_invalid_targets_aggregate_errors():
    """一条配置里多个非法点(name 空/重名/type 非法/URL 形状/after_state/未知字段键/映射 from 空)一次全报"""
    bad_a = {"name": "", "type": "qb", "base_url": "http://127.0.0.1:8081"}
    bad_b = {
        "name": "dup",
        "type": "ftp",
        "base_url": "127.0.0.1:8080",  # 缺 scheme
        "after_state": "delete",
        "fields": {
            "bogus_key": "true"
        },
        "path_map": [{
            "from": "",
            "to": "/x"
        }],
    }
    bad_c = {"name": "dup"}  # 与 bad_b 重名
    errors = _validate_transfer({"targets": [bad_a, bad_b, bad_c]})
    joined = "\n".join(errors)
    assert "targets[0].name: 不能为空" in joined
    assert "targets[1].type: 取值非法: 'ftp'" in joined
    assert "targets[1].base_url: 须为 http(s) URL" in joined
    assert "targets[1].after_state: 取值非法: 'delete'" in joined
    assert "targets[1].fields: 未知键 ['bogus_key']" in joined
    assert "targets[1].path_map[0].from: 不能为空" in joined
    assert "targets[2].name: 与 targets[1] 重名: dup" in joined
    # 聚合: 不是只报第一个错
    assert len(errors) >= 7


# ---------------- 字段集校验(D3: 键闭合 + 保存路径锁死) ----------------


def test_transfer_field_set_key_closure_and_save_path_locked():
    """字段集键闭合: 未知键报错; save_path 显式 false 拒绝(同机硬约束: 关掉 = 目标侧数据不可达)"""
    errors = _validate_transfer({"targets": [{"name": "t1", "fields": {"save_path": "false"}}]})
    assert any("fields.save_path: 保存路径锁死必开" in e for e in errors)
    errors = _validate_transfer({"targets": [{"name": "t1", "fields": {"unknown_x": "true", "super_seeding": "true"}}]})
    assert any("fields: 未知键 ['unknown_x']" in e for e in errors)
    # save_path 显式 true / 缺省(补模板默认) 均合法
    assert _validate_transfer({"targets": [{"name": "t1", "fields": {"save_path": "true"}}]}) == []
    assert _validate_transfer({"targets": [{"name": "t1"}]}) == []


def test_transfer_field_set_values_must_be_bool():
    """字段集值须在 parse_bool 域(true/false/1/0/yes/no/on/off); 乱串进 errors 聚合"""
    errors = _validate_transfer({"targets": [{"name": "t1", "fields": {"tags": "maybe"}}]})
    assert any("fields.tags" in e for e in errors)
    assert _validate_transfer({"targets": [{"name": "t1", "fields": {"tags": "no", "up_limit": "on"}}]}) == []


# ---------------- 路径映射规则表校验(§03: 有序 from→to, 默认空 = 原样) ----------------


def test_transfer_path_map_validation():
    """path_map 须为列表, 条目须为 {from, to} 字典且两侧非空; 键闭合复用 fs 的 from/to 键集"""
    errors = _validate_transfer({"targets": [{"name": "t1", "path_map": "D:/x"}]})
    assert any("path_map: 必须是列表" in e for e in errors)
    errors = _validate_transfer({"targets": [{"name": "t1", "path_map": ["not-a-dict"]}]})
    assert any("path_map[0]: 必须是字典 {from, to}" in e for e in errors)
    errors = _validate_transfer({"targets": [{"name": "t1", "path_map": [{"from": "D:/x", "src": "y"}]}]})
    assert any("path_map[0]: 未知键 ['src']" in e for e in errors)
    errors = _validate_transfer({"targets": [{"name": "t1", "path_map": [{"from": "D:/x"}]}]})
    assert any("path_map[0].to: 不能为空" in e for e in errors)
    # 合法形态零报错(空表 = 原样; 多条有序规则)
    assert _validate_transfer({"targets": [{"name": "t1", "path_map": []}]}) == []
    assert _validate_transfer(
        {"targets": [{
            "name": "t1",
            "path_map": [{
                "from": "D:/a",
                "to": "/mnt/a"
            }, {
                "from": "D:/b",
                "to": "/mnt/b"
            }]
        }]}
    ) == []


# ---------------- 名称非空唯一 / 枚举 / URL ----------------


def test_transfer_target_name_required_and_unique():
    """名称非空且全表唯一(含停用目标 —— 目标编辑器按名引用, 重名即歧义)"""
    errors = _validate_transfer({"targets": [{"name": "  "}, {"name": "x"}, {"name": "x"}]})
    joined = "\n".join(errors)
    assert "targets[0].name: 不能为空" in joined
    assert "targets[2].name: 与 targets[1] 重名: x" in joined
    assert _validate_transfer({"targets": [{"name": "a"}, {"name": "b"}]}) == []


def test_transfer_type_and_after_state_enum():
    """type 枚举 qb/tr(D10: tr 为 stub, 不做假接口); after_state 单选 keep/paused(D9)"""
    errors = _validate_transfer({"targets": [{"name": "t1", "type": "deluge"}]})
    assert any("type: 取值非法: 'deluge', 可选: qb/tr" in e for e in errors)
    errors = _validate_transfer({"targets": [{"name": "t1", "after_state": "paused"}]})
    assert errors == []
    errors = _validate_transfer({"targets": [{"name": "t1", "after_state": "resume"}]})
    assert any("after_state: 取值非法: 'resume', 可选: keep/paused" in e for e in errors)


def test_transfer_base_url_shape_and_required_when_enabled():
    """base_url 非空时须为 http(s) URL 形状; enabled=true 时必须配置; 停用目标可为空(草稿态)"""
    for bad in ("127.0.0.1:8080", "ftp://x", "http://", ""):
        errors = _validate_transfer({"targets": [{"name": "t1", "base_url": bad, "enabled": "true"}]})
        assert errors, f"enabled 目标 base_url={bad!r} 应报错"
    errors = _validate_transfer({"targets": [{"name": "t1", "base_url": "https://192.0.2.1:8081", "enabled": "true"}]})
    assert errors == []
    # 停用目标 base_url 留空 = 草稿, 不拦(编辑器允许先建后填)
    assert _validate_transfer({"targets": [{"name": "t1"}]}) == []
    # 非空就查形状, 无论启用与否
    errors = _validate_transfer({"targets": [{"name": "t1", "base_url": "no-scheme"}]})
    assert any("base_url: 须为 http(s) URL" in e for e in errors)


def test_transfer_section_shape_errors():
    """段/列表/条目形状错误聚合: transfer 非字典 / 顶层未知键 / targets 非列表 / 条目非字典 / 条目未知键"""
    errors = validate_config({"config": {"web": {"transfer": "nope"}}})
    assert any("config.web.transfer: 必须是字典" in e for e in errors)
    errors = _validate_transfer({"bogus": []})
    assert any("config.web.transfer: 未知键 ['bogus']" in e for e in errors)
    errors = _validate_transfer({"targets": {"name": "t1"}})
    assert any("config.web.transfer.targets: 必须是列表" in e for e in errors)
    errors = _validate_transfer({"targets": ["nope", {"name": "t1", "bogus": 1}]})
    assert any("targets[0]: 必须是字典" in e for e in errors)
    assert any("targets[1]: 未知键 ['bogus']" in e for e in errors)
    # transfer 缺省/空字典均合法
    assert _validate_transfer({}) == []
    assert _validate_transfer({"targets": []}) == []


def test_transfer_enum_constants_are_schema_derived():
    """取值域常量单源守卫(与 test_config_schema 的枚举族守卫同模式): validation 引用的必须就是
    schema.fields 对象(is 断言, 防第二份手写声明回潮); models 的字段集键表与模板默认一致"""
    from auto_qb.config import validation
    from auto_qb.config.schema import fields as schema_fields
    from auto_qb.config.validation import sections

    assert sections.TRANSFER_TARGET_TYPES is schema_fields.TRANSFER_TARGET_TYPES
    assert sections.TRANSFER_AFTER_STATES is schema_fields.TRANSFER_AFTER_STATES
    assert set(schema.TRANSFER_TARGET_TYPES) == {"qb", "tr"}
    assert set(schema.TRANSFER_AFTER_STATES) == {"keep", "paused"}
    assert set(TRANSFER_FIELD_KEYS) == set(default_transfer_fields())
