"""test_config_rules 测试计划: 配置加载与 HR 规则解析

## 测试计划(每个测试函数一条)
- test_config_tracker_tags_expand: tracker 标签展开(全局+站点)
- test_parse_hr_spec_missing_required: HR 规范缺必填项报错
- test_parse_hr_spec_site_overrides_global: 站点 HR 覆盖全局
- test_parse_hr_spec_condition: HR 规范条件解析
- test_parse_hr_exclude_union: HR 排除表全局∪站点并集(去重保序)
- test_validate_hr_exclude_errors: HR 排除表校验(未知键/非列表/空串/非法 regex, 全局与站点)
- test_config_tracker_tags_expand_ignore_case: @tracker_tags:ignore_case 展开附加后缀
- test_config_tracker_tags_expand_no_tracker_tags: 无任何 tracker tags 时 @tracker_tags 展开为空
- test_config_tracker_tags_expand_dedup: 重复 tag/@tracker_tags 引用去重保序
- test_non_tri_state_empty_still_stripped: 全局段与站点段非 tri_state 键的显式空串照剥(语义不随 v4 翻转)
- test_load_web_skip_check_menu_tristate: web.skip_check_menu 三态(显式 true / 显式 false / 缺省默认 false, 计划 26-10-02-1955 W1)
- test_skip_checking_tag_global_default_and_override
"""

import logging

import os

import tempfile

from pathlib import Path

import pytest

import yaml

from auto_qb.config import (
    Config,
    ConfigError,
    HRRule,
    NotifyConfig,
    QbittorrentConfig,
    TrackerConfig,
    load_config,
    load_global_hr,
    load_tracker_hr,
)

from auto_qb.core.traffic_source import paths as traffic_paths

from auto_qb.infra.errors import AutoQbError

from config_write_support import (
    _load_errors,
    _write_config,
    _write_raw,
)


def test_config_tracker_tags_expand():
    """@tracker_tags 引用展开为所有 tracker 配置的 tags 并集"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = _write_config(td, delete_tags_if_has_no_torrents=["@tracker_tags", "regex:^ORPHAN"])
        cfg = load_config(cfg_path)
        assert set(cfg.delete_tags_if_has_no_torrents) == {"HHan", "Kufirc", "regex:^ORPHAN"}, \
            f"@tracker_tags 展开错误: {cfg.delete_tags_if_has_no_torrents}"


def test_config_tracker_tags_expand_ignore_case():
    """@tracker_tags:ignore_case 引用展开时给每个 tag 附加 :ignore_case 后缀"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = _write_config(td, delete_tags=["@tracker_tags:ignore_case"])
        cfg = load_config(cfg_path)
        assert set(cfg.delete_tags) == {"HHan:ignore_case", "Kufirc:ignore_case"}, \
            f"@tracker_tags:ignore_case 展开错误: {cfg.delete_tags}"


def test_config_tracker_tags_expand_no_tracker_tags():
    """没有任何 tracker 配置 tags 时 @tracker_tags 展开为空列表"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = _write_config(td, trackers={"NoTag": {"domains": ["x.com"], "tags": []}})
        cfg = load_config(cfg_path)
        assert cfg.delete_tags_if_has_no_torrents == []


def test_config_tracker_tags_expand_dedup():
    """重复 tag 与重复 @tracker_tags 引用: 去重保序"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = _write_config(td, delete_tags=["@tracker_tags", "HHan", "@tracker_tags", "regex:^seed-"])
        cfg = load_config(cfg_path)
        assert cfg.delete_tags == ["HHan", "Kufirc", "regex:^seed-"], \
            f"去重展开错误: {cfg.delete_tags}"


def test_parse_hr_spec_missing_required():
    """hr 段缺少 required_seeding_time 抛 ValueError"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = _write_config(td)
        # 给 tracker 配置缺 required_seeding_time 的 hr 段(全局 hr 为空字典不解析)
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.BaseLoader)
        data["config"]["trackers"]["HHan"]["hr"] = {}
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        try:
            load_config(cfg_path)
            assert False, "缺少 required_seeding_time 应抛 ValueError"
        except ConfigError:
            pass


def test_parse_hr_spec_site_overrides_global():
    """站点 hr 输出字段优先, 未设置的字段用全局默认"""
    with tempfile.TemporaryDirectory() as td:
        global_hr = {
            "add_category": "!!HR${required_seeding_time}!!",
            "add_category_for_satisfied": "--HR${required_seeding_time}--",
        }
        spec = {
            "required_seeding_time": "3D",
            "add_category": "SITE-HR!!",
            "overwrite_category": True,
        }
        rule = load_tracker_hr(spec, global_hr)
        assert rule.required_seeding_time == 3 * 86400
        assert rule.required_seeding_time_raw == "3D"
        assert rule.add_category == "SITE-HR!!"  # 站点覆盖
        assert rule.overwrite_category is True
        assert rule.add_category_for_satisfied == "--HR${required_seeding_time}--"  # 全局兜底
        assert rule.condition == ("dlratio", 0.8)  # 默认触发条件


def test_parse_hr_spec_condition():
    """condition: 百分比 -> dlratio, 大小 -> dlsize"""
    with tempfile.TemporaryDirectory() as td:
        rule = load_tracker_hr({"required_seeding_time": "12H", "condition": "10MiB"}, {})
        assert rule.condition == ("dlsize", 10 * 1024**2)
        assert rule.extra_seeding_time == 0
        rule2 = load_tracker_hr({"required_seeding_time": "1D", "extra_seeding_time": "12H"}, {})
        assert rule2.extra_seeding_time == 12 * 3600


def test_parse_hr_exclude_union():
    """HR 排除表(计划 26-09-28-1805): 全局 ∪ 站点并集(去重保序), 不是站点覆盖全局"""
    global_hr = {"exclude_tags": ["a", "c"], "exclude_categories": ["free"]}
    rule = load_tracker_hr({"required_seeding_time": "3D", "exclude_tags": ["b", "a"]}, global_hr)
    assert rule.exclude_tags == ["a", "c", "b"], "并集去重保序: 全局在前, 站点追加在后"
    assert rule.exclude_categories == ["free"]
    assert load_tracker_hr({"required_seeding_time": "3D"}, {"exclude_tags": ["x"]}).exclude_tags == ["x"], "全局单独生效"
    assert load_tracker_hr({"required_seeding_time": "3D", "exclude_tags": ["y"]}, {}).exclude_tags == ["y"], "站点单独生效"
    assert load_tracker_hr({"required_seeding_time": "3D"}, {}).exclude_tags == [], "双方皆缺 = 空表"
    assert load_global_hr({"exclude_tags": ["g"]}).exclude_tags == ["g"], "全局段自身也能读出排除表"


def test_non_tri_state_empty_still_stripped():
    """全局段与站点段非 tri_state 键的显式空串仍是「未配置」(照剥, 语义不随 v4 翻转)

    全局 tri_state 键的 '' 语义仍是「使用默认值」(豁免仅对站点段路径生效); bool 键不标
    (config 层 "false" 本可区分), list 键不标(exclude_* 保持并集语义, 空 == 缺失)。
    """
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  schema_version: 4\n"
            "  hr:\n"
            "    add_tag: ''\n"  # 全局 tri_state 键: '' 仍是「使用默认值」, 照剥
            "    overwrite_category: ''\n"  # 全局 bool: 照剥
            "  trackers:\n"
            "    T1:\n"
            "      domains:\n"
            "        - a.com\n"
            "      remove_similar_tags: ''\n"  # 站点 bool: 照剥 -> 回退全局(全局未配 -> false)
            "      hr:\n"
            "        required_seeding_time: 3D\n"
            "        exclude_categories: ''\n"  # 站点 list: 照剥 -> 并集语义不变
        )
        cfg = load_config(_write_raw(td, text))
        assert cfg.hr.add_tag == "", "全局段的 '' = 未配置(使用默认值), 不保留"
        assert cfg.hr.overwrite_category is False
        assert cfg.trackers["T1"].remove_similar_tags is False
        assert cfg.trackers["T1"].hr.exclude_categories == []


def test_skip_checking_tag_global_default_and_override():
    """顶层 config.skip_checking_tag: 缺省走 models 默认 zSkipChecked; 显式配置覆盖默认名

    与 log.file 同约定: YAML 留空/空串被 _strip_none 视为未配置(见 test_validate_empty_sections_use_defaults)。
    checking 动作不配置该键(全局统一, spec 配同名键报未知键), 动作运行时经 ctx 直接读取全局值。
    """
    with tempfile.TemporaryDirectory() as td:
        base = "  trackers:\n    T1:\n      domains:\n        - a.com\n"

        # 1. 未配置 -> models dataclass 默认值(默认值唯一来源, 动作类不再硬编码)
        cfg = load_config(_write_raw(td, "config:\n" + base))
        assert cfg.skip_checking_tag == "zSkipChecked"

        # 2. 显式配置 -> 覆盖默认名(全局统一, 动作运行时读取)
        cfg2 = load_config(_write_raw(td, "config:\n  skip_checking_tag: zGlobalTag\n" + base))
        assert cfg2.skip_checking_tag == "zGlobalTag"


def test_validate_hr_exclude_errors():
    """HR 排除表校验(计划 26-09-28-1805): 未知键(拼写错)/非列表/空白串项/非法 regex, 全局与站点两处都拦

    纯空串项会被 _strip_none 过滤(视为未配置), 故空项用空格串触发。
    """
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  hr:\n"
            "    excluded_tags: [x]\n"  # 未知键(拼写错, 全局)
            "    exclude_tags: not-a-list\n"  # 非列表
            "    exclude_categories: [\" \"]\n"  # 空白串项
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
            "      hr:\n"
            "        required_seeding_time: 3D\n"
            "        exclude_tags: [\"regex:[\"]\n"  # 非法正则(站点段)
        )
        err = _load_errors(td, text)
        assert "excluded_tags" in err and "config.hr: 未知键" in err, err
        assert "config.hr.exclude_tags: 必须是列表" in err, err
        assert "config.hr.exclude_categories" in err and "必须是非空字符串" in err, err
        assert "config.trackers.T1.hr.exclude_tags[0]: 非法正则" in err, err


def test_load_web_skip_check_menu_tristate():
    """web.skip_check_menu 三态(计划 26-10-02-1955 W1): 显式 true / 显式 false / 缺省默认 false"""
    base = "config:\n  trackers:\n    T1:\n      domains:\n        - a.com\n"
    with tempfile.TemporaryDirectory() as td:
        cfg = load_config(_write_raw(td, base + "  web:\n    skip_check_menu: true\n"))
        assert cfg.web.skip_check_menu is True
        cfg = load_config(_write_raw(td, base + "  web:\n    skip_check_menu: false\n"))
        assert cfg.web.skip_check_menu is False
        cfg = load_config(_write_raw(td, base))
        assert cfg.web.skip_check_menu is False  # 缺省走保守默认(菜单不显示 + 端点拒绝)
