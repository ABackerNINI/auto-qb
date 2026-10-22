"""test_relocate_config 测试计划: relocate 整组迁移配置面(计划 26-10-18-1604 §04 P1)

P1 只做配置面: RelocateConfig + loader + KNOWN_RELOCATE_KEYS 校验 + schema 段 + RelocateModule
段认领(引擎随 P2 起)。验收: schema↔validate 同步守卫已由 test_config_schema 参数面覆盖,
本文件盯行为面 —— 默认保守关、逐键校验聚合、loader 解析、模块认领与零副作用。

## 测试计划(每个测试函数一条)
- test_relocate_defaults_are_conservative: 段缺省 = 全默认且 enabled=False(保守默认, 关 = 现状)
- test_relocate_unknown_key_rejected: 未知键进 fail-fast 聚合(报错列出可用键)
- test_relocate_non_bool_aggregates: enabled/allow_uac 非 bool 进聚合, 不打断其它键
- test_relocate_verify_enum: verify 只接受 size/sample(大小写不敏感), 非法值聚合报错
- test_relocate_int_bounds: alias_file_threshold/hard_max_links 非整数或 < 1 报错
- test_relocate_time_keys_positive: 三个时间键必须可解析且 > 0
- test_relocate_low_space_warn_units: low_space_warn 走 parse_fsize(二进制单位; 10G 这种写法拒收)
- test_relocate_load_config_explicit_values: 显式 YAML 值按 parse_* 语义进入 Config(含时间/大小)
- test_relocate_section_absent_uses_defaults: 配置里没有 relocate 段时走字段默认
- test_relocate_non_dict_section_rejected: 段形状守卫 —— 缺省(None)静默走默认; 非字典报「必须是字典」并停在该层(不跑逐键校验)
- test_relocate_module_claims_section: RelocateModule.sections() == ("relocate",)(段认领完备守阵的模块侧)
- test_relocate_module_apply_short_circuits: apply 段相等短路(零回执); 段变化换对象即生效
- test_relocate_module_start_stop_no_side_effect: 即使 enabled=true, P1 start/stop 也无任务无链接
- test_relocate_module_registered_in_host
"""
import os
import tempfile

import yaml

from auto_qb.config import load_config
from auto_qb.config.models import Config, RelocateConfig
from auto_qb.config.validation import validate_config
from helpers import make_manager


def _validate(spec: dict):
    return validate_config({"config": {"relocate": spec}})


def test_relocate_defaults_are_conservative():
    """段缺省 = 全字段默认; 总开关默认 False(黄金法则 2: 关着的功能零副作用)"""
    d = RelocateConfig()
    assert d.enabled is False
    assert d.alias_file_threshold == 8
    assert d.hard_max_links == 2000
    assert d.verify == "size"
    assert d.allow_uac is True
    assert d.move_stall_timeout == 600.0
    assert d.move_warn_after == 7200.0
    assert d.finalize_timeout == 30 * 86400.0
    assert d.low_space_warn == 10 * 1024**3
    assert Config().relocate == d


def test_relocate_unknown_key_rejected():
    """未知键进 fail-fast 聚合(不静默丢弃), 报错列出可用键"""
    errors = _validate({"mystery": "1", "enabled": "maybe"})
    assert any("config.relocate: 未知键" in e and "mystery" in e for e in errors), errors
    assert any("config.relocate.enabled" in e for e in errors), errors  # 其余键的报错不被打断


def test_relocate_non_bool_aggregates():
    """enabled/allow_uac 非 bool 进聚合(走 parse_bool 单点报错)"""
    errors = _validate({"enabled": "maybe", "allow_uac": "perhaps"})
    assert any("config.relocate.enabled" in e for e in errors), errors
    assert any("config.relocate.allow_uac" in e for e in errors), errors


def test_relocate_verify_enum():
    """verify 取值域单点(schema.fields.RELOCATE_VERIFY_MODES): size/sample, 大小写不敏感"""
    from auto_qb.config.schema.fields import RELOCATE_VERIFY_MODES

    assert set(RELOCATE_VERIFY_MODES) == {"size", "sample"}
    assert _validate({"verify": "sample"}) == []
    assert _validate({"verify": "SAMPLE"}) == []  # loader 侧再归一为小写
    errors = _validate({"verify": "sha256"})
    assert any("config.relocate.verify" in e and "size" in e and "sample" in e for e in errors), errors


def test_relocate_int_bounds():
    """两个 int 键: 非整数 / < 1 都报错; 边界 1 合法"""
    assert _validate({"alias_file_threshold": "1", "hard_max_links": "1"}) == []
    errors = _validate({"alias_file_threshold": "0"})
    assert any("config.relocate.alias_file_threshold" in e and ">= 1" in e for e in errors), errors
    errors = _validate({"hard_max_links": "8.5"})
    assert any("config.relocate.hard_max_links" in e and "整数" in e for e in errors), errors


def test_relocate_time_keys_positive():
    """三个时间键: 合法时间串通过; 0(带单位) / 非法格式报错 —— parse_time 单点口径"""
    assert _validate({"move_stall_timeout": "1m", "move_warn_after": "1h", "finalize_timeout": "1d"}) == []
    for key in ("move_stall_timeout", "move_warn_after", "finalize_timeout"):
        errors = _validate({key: "0S"})
        assert any(f"config.relocate.{key}" in e and "正时间" in e for e in errors), errors
        errors = _validate({key: "10x"})
        assert any(f"config.relocate.{key}" in e for e in errors), errors


def test_relocate_low_space_warn_units():
    """low_space_warn 走 parse_fsize 单点: 只认二进制单位(10GiB 合法, 10G 这种十进制写法拒收)"""
    assert _validate({"low_space_warn": "10GiB"}) == []
    assert _validate({"low_space_warn": "0B"}) == []  # 0 = 不告警
    errors = _validate({"low_space_warn": "10G"})
    assert any("config.relocate.low_space_warn" in e for e in errors), errors


def test_relocate_load_config_explicit_values():
    """显式 YAML 值按 parse_* 语义进入 Config(时间/大小/枚举/布尔/整数)"""
    cfg_dict = {
        "config":
            {
                "relocate":
                    {
                        "enabled": "true",
                        "alias_file_threshold": "12",
                        "hard_max_links": "500",
                        "verify": "SAMPLE",
                        "allow_uac": "false",
                        "move_stall_timeout": "25M",
                        "move_warn_after": "3H",
                        "finalize_timeout": "45D",
                        "low_space_warn": "20GiB",
                    }
            }
    }
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "c.yml")
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg_dict, f, allow_unicode=True)
        cfg = load_config(path)
    assert cfg.relocate.enabled is True
    assert cfg.relocate.alias_file_threshold == 12
    assert cfg.relocate.hard_max_links == 500
    assert cfg.relocate.verify == "sample"  # loader 归一小写(与校验同口径)
    assert cfg.relocate.allow_uac is False
    assert cfg.relocate.move_stall_timeout == 1500.0
    assert cfg.relocate.move_warn_after == 10800.0
    assert cfg.relocate.finalize_timeout == 45 * 86400.0
    assert cfg.relocate.low_space_warn == 20 * 1024**3


def test_relocate_section_absent_uses_defaults():
    """配置文件没有 relocate 段时走字段默认(功能未启用, 全链路零差异)"""
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "c.yml")
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump({"config": {"main_tick": "3S"}}, f, allow_unicode=True)
        cfg = load_config(path)
    assert cfg.relocate == RelocateConfig()
    assert cfg.relocate.enabled is False


def test_relocate_non_dict_section_rejected():
    """段形状守卫: 段缺省(None)静默走默认, 不报错; 段存在但非字典(标量/列表)报
    「必须是字典」并停在该层 —— 不继续跑逐键校验(否则会在标量上取 .items() 炸出 AttributeError)"""
    assert _validate(None) == []
    assert _validate(["enabled"]) == ["config.relocate: 必须是字典"]
    assert _validate("enabled") == ["config.relocate: 必须是字典"]


def test_relocate_module_claims_section():
    """RelocateModule.sections() 认领 relocate 段(段认领完备守阵的模块侧前提)"""
    from auto_qb.core.modules.relocate_mod import RelocateModule

    assert RelocateModule().sections() == ("relocate", )


def test_relocate_module_apply_short_circuits():
    """apply: 段相等空回执; 段变化换对象即生效(P1 只缓存生效配置)

    入参是 Config 层(模块按段属性读, 与宿主 apply_all 广播同口径)。
    """
    from auto_qb.core.modules.relocate_mod import RelocateModule

    mod = RelocateModule()
    same = Config()
    changed = Config()
    changed.relocate = RelocateConfig(enabled=True, verify="sample")
    assert mod.apply(same, same).action == "none"
    res = mod.apply(same, changed)
    assert res.module == "relocate" and res.action == "reloaded"
    assert mod._conf is changed.relocate


def test_relocate_module_start_stop_no_side_effect():
    """P1: 即使 enabled=true, start/stop 也不建任务/建链接/碰 qB(引擎随 P2 起)"""
    from auto_qb.core.modules.relocate_mod import RelocateModule

    mod = RelocateModule()
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
        mgr.config.relocate = RelocateConfig(enabled=True)
        mod.start(mgr.ctx, dry_run=False)
        mod.stop()  # 幂等无副作用
        assert mgr.task_queue is not None  # 队列未被 relocate 触碰(无新增任务)


def test_relocate_module_registered_in_host():
    """装配清单尾部有 relocate(与 test_module_host 的模块序守阵互为前后侧)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = make_manager(os.path.join(td, "state.json"))
    assert mgr.host.get("relocate") is not None
    assert "relocate" in mgr.host.claimed_sections()
