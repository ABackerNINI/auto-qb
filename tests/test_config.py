"""test_config 测试计划: 配置加载与 HR 规则解析

## 测试计划(每个测试函数一条)
- test_load_config_basic: 加载基础配置
- test_config_tracker_tags_expand: tracker 标签展开(全局+站点)
- test_parse_hr_spec_missing_required: HR 规范缺必填项报错
- test_parse_hr_spec_site_overrides_global: 站点 HR 覆盖全局
- test_parse_hr_spec_condition: HR 规范条件解析
- test_hr_rule_defaults: HRRule 默认值
- test_config_tracker_tags_expand_ignore_case: @tracker_tags:ignore_case 展开附加后缀
"""
import os
import tempfile

import yaml

from auto_qb.config import HRRule, QbittorrentConfig, load_config, load_tracker_hr


def _write_config(td, **extra_cfg):
    cfg = {
        "config":
            {
                "qbittorrent": {
                    "host": "127.0.0.1",
                    "port": 16585,
                    "username": "u",
                    "password": "p",
                },
                "trackers":
                    {
                        "HHan": {
                            "domains": ["tracker.hhanclub.net"],
                            "tags": ["HHan"]
                        },
                        "Kufirc": {
                            "domains": ["kufirc.com"],
                            "tags": ["Kufirc"]
                        },
                    },
            }
    }
    cfg["config"].update(extra_cfg)
    cfg_path = os.path.join(td, "config.yml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)
    return cfg_path


def test_load_config_basic():
    """基础解析: qbittorrent / interval / state_file / trackers"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = _write_config(td)
        cfg = load_config(cfg_path)
        assert cfg.qbittorrent.host == "127.0.0.1"
        assert cfg.qbittorrent.port == 16585
        assert cfg.qbittorrent.username == "u"
        assert cfg.qbittorrent.password == "p"
        assert cfg.qbittorrent.base_url == "http://127.0.0.1:16585"
        assert cfg.interval == 60  # 默认 60s
        assert set(cfg.trackers) == {"HHan", "Kufirc"}
        assert cfg.trackers["HHan"].tags == ["HHan"]
        assert cfg.trackers["HHan"].hr is None  # 无 hr 段


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
        except ValueError:
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


def test_hr_rule_defaults():
    """HRRule 数据类默认值"""
    rule = HRRule()
    assert rule.required_seeding_time == 0
    assert rule.required_share_ratio == 0.0
    assert rule.condition == ("dlratio", 0.8)
    assert rule.add_category == ""
    assert rule.overwrite_category is False
