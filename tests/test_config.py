"""test_config 测试计划: 配置加载与 HR 规则解析

## 测试计划(每个测试函数一条)
- test_load_config_basic: 加载基础配置
- test_config_tracker_tags_expand: tracker 标签展开(全局+站点)
- test_parse_hr_spec_missing_required: HR 规范缺必填项报错
- test_parse_hr_spec_site_overrides_global: 站点 HR 覆盖全局
- test_parse_hr_spec_condition: HR 规范条件解析
- test_hr_rule_defaults: HRRule 默认值
- test_config_tracker_tags_expand_ignore_case: @tracker_tags:ignore_case 展开附加后缀
- test_validate_trackers_empty_and_non_dict: trackers 留空合法; 非字典报错(fail-fast)
- test_config_tracker_tags_expand_no_tracker_tags: 无任何 tracker tags 时 @tracker_tags 展开为空
- test_config_tracker_tags_expand_dedup: 重复 tag/@tracker_tags 引用去重保序
- test_validate_minimal_ok: 仅必填项的最小配置通过校验
- test_validate_empty_sections_use_defaults: 显式留空的段/键视为未配置(走默认值)
- test_validate_unknown_keys_aggregated: 各段未知键聚合一次性报告(含路径)
- test_validate_root_unknown_key: 顶层未知键报错
- test_validate_required_missing: 缺 domains / 站点 hr 缺 required_seeding_time 报错
- test_validate_bad_formats: 非法格式聚合(main_tick/port/log.level/限速/布尔)
- test_validate_rule_spec: 规则 spec 键/取值域/未知条件动作/多键项报错
- test_validate_rule_refs: tracker.rules 引用必须 @ 开头且目标存在
- test_validate_regex_patterns: 非法 regex: 模式报错
- test_validate_gslc: global_speed_limit_curve 原生校验器聚合错误
- test_validate_empty_file: 空文件/非字典根节点报错
- test_config_error_wraps_io_and_yaml: 文件读取/YAML 解析异常统一包装为 ConfigError
- test_models_default_sources: 默认值单一来源 = dataclass 字段默认(段级/Config 顶层标量)
"""
import logging
import os
import tempfile

import pytest
import yaml

from auto_qb.config import (
    Config,
    ConfigError,
    HRRule,
    QbittorrentConfig,
    TrackerConfig,
    load_config,
    load_tracker_hr,
)


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


def test_validate_trackers_empty_and_non_dict():
    """trackers 留空(未配置站点)合法; 非字典是配置错误 -> 报错(fail-fast)"""
    with tempfile.TemporaryDirectory() as td:
        # 留空: 合法(trackers: 经 yaml 解析为 None, 视为未配置任何站点)
        empty_path = os.path.join(td, "empty.yml")
        with open(empty_path, "w", encoding="utf-8") as f:
            f.write("config:\n  qbittorrent:\n    host: h\n  trackers:\n")
        cfg = load_config(empty_path)
        assert cfg.trackers == {}
        # 非字典: 报错
        cfg_path = _write_config(td, trackers="not-a-dict")
        try:
            load_config(cfg_path)
            assert False, "trackers 非字典应报错"
        except ValueError as e:
            assert "config.trackers: 必须是字典" in str(e)


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
        assert rule.add_category_for_satisfied == "--HR${required_seeding_time}--"  # 全局fallback
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


# ---------- fail-fast 全量配置校验 ----------


def _write_raw(td, text: str) -> str:
    """写入原始 yaml 文本(BaseLoader 语义: 全部标量为字符串, 留空为 None)"""
    path = os.path.join(td, "raw.yml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def _load_errors(td, text: str) -> str:
    """加载配置并返回聚合错误文本(不抛错则返回空串)"""
    try:
        load_config(_write_raw(td, text))
        return ""
    except ValueError as e:
        return str(e)


def test_validate_minimal_ok():
    """仅必填项(qbittorrent 可全默认, tracker 只填 domains)的最小配置通过校验"""
    with tempfile.TemporaryDirectory() as td:
        cfg = load_config(_write_raw(td, "config:\n  trackers:\n    T1:\n      domains:\n        - a.com\n"))
        assert cfg.trackers["T1"].domains == ["a.com"]
        assert cfg.trackers["T1"].hr is None
        assert cfg.main_tick == 2.0  # 默认 2s


def test_validate_empty_sections_use_defaults():
    """显式留空的键/段(BaseLoader 解析为空串)视为未配置, 走默认值"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  main_tick:\n"
            "  interval:\n"
            "  state_file:\n"
            "  log:\n"
            "  grouping:\n"
            "  hr:\n"
            "  delete_tags:\n"
            "  qbittorrent:\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains:\n"
            "        - a.com\n"
            "      tags:\n"
            "      remove_tags:\n"
            "      hr:\n"
            "        required_seeding_time: 3D\n"
            "        extra_seeding_time:\n"
            "        required_share_ratio:\n"
        )
        cfg = load_config(_write_raw(td, text))
        assert cfg.main_tick == 2.0 and cfg.interval == 60  # 默认值
        assert cfg.state_file == "auto-qb-state.json"  # 留空走默认
        assert cfg.logging.level == logging.INFO
        assert cfg.trackers["T1"].hr.extra_seeding_time == 0
        assert cfg.trackers["T1"].hr.required_share_ratio == 0.0


def test_validate_unknown_keys_aggregated():
    """多段未知键聚合一次性报告, 每条带配置路径"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  unknow_top: 1\n"
            "  qbittorrent:\n"
            "    hos: 127.0.0.1\n"
            "  grouping:\n"
            "    enable: true\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
            "      domain: [a.com]\n"
        )
        err = _load_errors(td, text)
        assert "共 4 处" in err, err
        assert "[1] config: 未知键 ['unknow_top']" in err, err
        assert "config.qbittorrent: 未知键 ['hos']" in err, err
        assert "config.grouping: 未知键 ['enable']" in err, err
        assert "config.trackers.T1: 未知键 ['domain']" in err, err


def test_validate_root_unknown_key():
    """config 键之外的顶层内容报错"""
    with tempfile.TemporaryDirectory() as td:
        err = _load_errors(td, "config:\n  interval: 5S\nother: 1\n")
        assert "根节点: 未知键 ['other']" in err, err


def test_validate_required_missing():
    """tracker 缺 domains / 站点 hr 缺 required_seeding_time -> 明确报错"""
    with tempfile.TemporaryDirectory() as td:
        err = _load_errors(td, "config:\n  trackers:\n    T1:\n      tags: [a]\n")
        assert "config.trackers.T1: 缺少必填键 domains" in err, err
        err = _load_errors(td, "config:\n  trackers:\n    T1:\n      domains: [a.com]\n      hr:\n        condition: 80%\n")
        assert "config.trackers.T1.hr: 缺少必填键 required_seeding_time" in err, err


def test_validate_bad_formats():
    """非法值格式聚合: 时间/整数/端口/日志等级/限速/布尔/状态文件"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  main_tick: abc\n"
            "  max_tasks_per_tick: 1.5\n"
            "  remove_similar_tags: maybe\n"
            "  log:\n"
            "    level: VERBOSE\n"
            "    max_bytes: 10MB\n"
            "  qbittorrent:\n"
            "    port: 99999\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
            "      upload_speed_limit: 100MPH\n"
        )
        err = _load_errors(td, text)
        assert "config.main_tick: 无效时间格式" in err, err
        assert "config.max_tasks_per_tick" in err, err
        assert "config.remove_similar_tags: 无效布尔值" in err, err
        assert "config.log.level: 非法日志等级" in err, err
        assert "config.log.max_bytes" in err, err  # MB 非二进制单位
        assert "config.qbittorrent.port: 超出范围" in err, err
        assert "config.trackers.T1.upload_speed_limit: 无效速度格式" in err, err


def test_validate_rule_spec():
    """规则 spec: 未知键/取值域/未知条件与动作/多键项/空值 -> 聚合报错"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  example_rules:\n"
            "    rule1:\n"
            "      enabled: true\n"
            "      unknow: 1\n"
            "      execute_once: someday\n"
            "      stop_following_rules_if: sometimes\n"
            "      trigger: on_torrent_added\n"
            "      cooldown: 5X\n"
            "      conditions:\n"
            "        - sizee: \">=1MiB\"\n"
            "        - path: /a\n"
            "          size: \">=1MiB\"\n"
            "        - notadict\n"
            "      actions:\n"
            "        - star: true\n"
        )
        err = _load_errors(td, text)
        assert "config.example_rules.rule1: 未知键 ['unknow']" in err, err
        assert "execute_once 取值非法: 'someday'" in err, err
        assert "stop_following_rules_if 取值非法: 'sometimes'" in err, err
        assert "trigger 取值非法: 'on_torrent_added'" in err, err
        assert "config.example_rules.rule1.cooldown: 无效时间格式" in err, err
        assert "未知条件 'sizee'" in err, err
        assert "必须是单键字典" in err, err
        assert "未知动作 'star'" in err, err


def test_validate_rule_refs():
    """tracker.rules 引用: 必须 @ 开头且规则集/规则存在"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  example_rules:\n"
            "    rule1:\n"
            "      conditions:\n"
            "        - path: /a\n"
            "      actions:\n"
            "        - stop: true\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
            "      rules:\n"
            "        - example_rules\n"
            "        - '@example_rules.ruleX'\n"
            "        - '@no_such_set'\n"
        )
        err = _load_errors(td, text)
        assert "规则引用必须以 @ 开头: 'example_rules'" in err, err
        assert "引用的规则不存在: @example_rules.ruleX" in err, err
        assert "引用的规则集不存在: @no_such_set" in err, err
        # 合法引用通过(移除两条非法引用)
        ok = (
            text.replace("- example_rules", "- '@example_rules'")
            .replace("        - '@example_rules.ruleX'\n", "")
            .replace("        - '@no_such_set'\n", "")
        )
        cfg = load_config(_write_raw(td, ok))
        assert cfg.trackers["T1"].rules == ["@example_rules"]


def test_validate_regex_patterns():
    """delete_tags / tracker.remove_tags 中非法 regex: 模式报错"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  delete_tags:\n"
            "    - 'regex:^a(b'\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
            "      remove_tags:\n"
            "        - 'regex:[x'\n"
        )
        err = _load_errors(td, text)
        assert "config.delete_tags[0]: 非法正则" in err, err
        assert "config.trackers.T1.remove_tags[0]: 非法正则" in err, err


def test_validate_gslc():
    """global_speed_limit_curve 由原生校验器 _validate_global_speed_limit_curve 聚合错误"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  global_speed_limit_curve:\n"
            "    curves:\n"
            "      - curve:\n"
            "          period: WEEK\n"
        )
        err = _load_errors(td, text)
        assert "config.global_speed_limit_curve.traffic_source: 必须是非空列表" in err, err


def test_validate_empty_file():
    """空文件/非字典根节点 -> 明确报错"""
    with tempfile.TemporaryDirectory() as td:
        assert "配置文件为空或根节点不是字典" in _load_errors(td, "")
        assert "配置文件为空或根节点不是字典" in _load_errors(td, "- a\n- b\n")


def test_config_error_wraps_io_and_yaml():
    """文件读取/YAML 解析异常统一包装为 ConfigError(ValueError 子类, 供 CLI 单点捕获)"""
    with tempfile.TemporaryDirectory() as td:
        with pytest.raises(ConfigError, match="配置文件读取失败"):
            load_config(os.path.join(td, "no-such.yml"))
        with pytest.raises(ConfigError, match="YAML 解析失败"):
            load_config(_write_raw(td, "config: [unclosed"))
        assert issubclass(ConfigError, ValueError)  # 兼容既有 except ValueError 调用方


def test_models_default_sources():
    """默认值单一来源 = dataclass 字段默认(段级/Config 顶层标量), loader 经 _get 引用"""
    qb = QbittorrentConfig()
    assert (qb.host, qb.port, qb.username, qb.password) == ("127.0.0.1", 8080, "", "")
    t = TrackerConfig(name="x", domains=["a.com"])
    assert t.tags == [] and t.remove_tags == [] and t.rules == []
    assert t.upload_speed_limit == 0 and t.download_speed_limit == 0  # 0 = 不限速
    assert t.remove_similar_tags is False and t.hr is None
    c = Config()
    assert c.main_tick == 2.0 and c.interval == 60.0
    assert c.max_tasks_per_tick == 20 and c.state_file == "auto-qb-state.json"
    assert c.remove_similar_tags is False and c.add_episode_tags is False
    assert c.trackers == {} and c.global_speed_limit_curve is None
