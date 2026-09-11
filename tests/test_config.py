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
- test_data_dir_derives_runtime_paths: data_dir 主目录派生 state_file/log.file; 显式优先; log.file 留空/空串=默认落盘
- test_validate_unknown_keys_aggregated: 各段未知键聚合一次性报告(含路径)
- test_validate_root_unknown_key: 顶层未知键报错
- test_validate_required_missing: 缺 domains / 站点 hr 缺 required_seeding_time 报错
- test_validate_bad_formats: 非法格式聚合(main_tick/port/log.level/限速/布尔)
- test_validate_rule_spec: 规则 spec 键/取值域/未知条件动作/多键项报错
- test_validate_state_condition_spec: state 条件非法 is_* 属性/裸枚举成员名报错
- test_validate_checking_action_spec: checking 动作 spec 深度校验聚合报错(非dict/缺键/非法值/段/未知键)
- test_validate_rule_refs: tracker.rules 引用必须 @ 开头且目标存在
- test_validate_regex_patterns: 非法 regex: 模式报错
- test_validate_condition_and_remove_tags_regex: tags/category/trackers 条件与 remove_tags 动作非法 regex: fail-fast
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
from auto_qb.errors import AutoQbError


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
        except ConfigError as e:
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
    except ConfigError as e:
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
            "  skip_checking_tag:\n"
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
        assert cfg.data_dir == "auto-qb-data"  # 数据主目录默认
        assert cfg.skip_checking_tag == "zSkipChecked"  # 跳检标签默认名(留空被 _strip_none 视为未配置)
        assert cfg.state_file == "auto-qb-data/state.json"  # 留空走默认(由 data_dir 派生)
        assert cfg.logging.file == "auto-qb-data/logs/auto-qb.log"  # log 留空 -> 默认落盘到主目录
        assert cfg.logging.level == logging.INFO
        assert cfg.trackers["T1"].hr.extra_seeding_time == 0
        assert cfg.trackers["T1"].hr.required_share_ratio == 0.0


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


def test_data_dir_derives_runtime_paths():
    """data_dir 数据主目录派生 state_file/log.file; 显式配置优先; log.file 空串=仅控制台"""
    with tempfile.TemporaryDirectory() as td:
        # 1. 自定义 data_dir(含尾部斜杠归一化), 未配 state_file/log.file -> 派生到主目录下
        text = ("config:\n"
                "  data_dir: mydata/\n"
                "  trackers:\n"
                "    T1:\n"
                "      domains:\n"
                "        - a.com\n")
        cfg = load_config(_write_raw(td, text))
        assert cfg.data_dir == "mydata/"
        assert cfg.state_file == "mydata/state.json"
        assert cfg.logging.file == "mydata/logs/auto-qb.log"  # 未配 log.file -> 默认落盘到主目录

        # 2. 显式 state_file/log.file 优先于 data_dir 派生
        text2 = (
            "config:\n"
            "  data_dir: mydata\n"
            "  state_file: custom/state.json\n"
            "  log:\n"
            "    file: custom/run.log\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains:\n"
            "        - a.com\n"
        )
        cfg2 = load_config(_write_raw(td, text2))
        assert cfg2.state_file == "custom/state.json"
        assert cfg2.logging.file == "custom/run.log"

        # 3. log.file 显式空串/留空 -> 配置体系统一视为"未配置", 走默认落盘(无法用空串表达仅控制台)
        text3 = (
            "config:\n"
            "  data_dir: mydata\n"
            "  log:\n"
            "    file: \"\"\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains:\n"
            "        - a.com\n"
        )
        cfg3 = load_config(_write_raw(td, text3))
        assert cfg3.logging.file == "mydata/logs/auto-qb.log"  # 空串=未配置=默认落盘


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
        err = _load_errors(
            td, "config:\n  trackers:\n    T1:\n      domains: [a.com]\n      hr:\n        condition: 80%\n"
        )
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
            "      trigger: on_torrent_frob\n"
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
        assert "trigger 取值非法: 'on_torrent_frob'" in err, err
        assert "config.example_rules.rule1.cooldown: 无效时间格式" in err, err
        assert "未知条件 'sizee'" in err, err
        assert "必须是单键字典" in err, err
        assert "未知动作 'star'" in err, err


def test_validate_state_condition_spec():
    """state 条件 spec 深度校验: 非法 is_* 属性(拼写错)/裸枚举成员名(恒真值) -> 报错"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  example_rules:\n"
            "    rule1:\n"
            "      conditions:\n"
            "        - state: \"is_stopp\"\n"
            "      actions:\n"
            "        - stop: true\n"
            "    rule2:\n"
            "      conditions:\n"
            "        - state: \"is_stopped&UPLOADING\"\n"
            "      actions:\n"
            "        - stop: true\n"
            "    rule3:\n"
            "      conditions:\n"
            "        - state: \"is_stopped&is_complete\"\n"
            "      actions:\n"
            "        - stop: true\n"
        )
        err = _load_errors(td, text)
        assert "非法状态属性 'is_stopp'" in err, err
        assert "非法状态属性 'UPLOADING'" in err, err  # 裸枚举成员名在实例上恒真值, 拒绝
        assert "rule3" not in err, err  # 合法 spec 不报错


def test_validate_checking_action_spec():
    """checking 动作 spec 深度校验: 非dict/缺basic_check/非法值/段非dict/非法mode/未知键/custom缺program -> 聚合报错"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  example_rules:\n"
            "    rule1:\n"
            "      actions:\n"
            "        - checking: \"skip-checking\"\n"
            "    rule2:\n"
            "      actions:\n"
            "        - checking:\n"
            "            with_reference: {mode: skip-checking}\n"
            "    rule3:\n"
            "      actions:\n"
            "        - checking:\n"
            "            basic_check: xxx\n"
            "    rule4:\n"
            "      actions:\n"
            "        - checking:\n"
            "            basic_check: filelist\n"
            "            with_reference: \"skip-checking\"\n"
            "    rule5:\n"
            "      actions:\n"
            "        - checking:\n"
            "            basic_check: filelist\n"
            "            with_reference: {mode: xxx}\n"
            "    rule6:\n"
            "      actions:\n"
            "        - checking:\n"
            "            basic_check: filelist\n"
            "            poll_timeout: 60S\n"
            "    rule7:\n"
            "      actions:\n"
            "        - checking:\n"
            "            basic_check: custom\n"
            "    rule8:\n"
            "      actions:\n"
            "        - checking:\n"
            "            basic_check: filelist\n"
            "            with_reference: {mode: skip-checking, auto_start: true}\n"
            "            without_reference: {mode: full-checking}\n"
            "    rule9:\n"
            "      actions:\n"
            "        - checking:\n"
            "            basic_check: filelist\n"
            "            skip_checking_tag: zSkipChecked\n"
        )
        err = _load_errors(td, text)
        assert "checking 动作只接受 dict 配置" in err, err
        assert "必须配置 basic_check" in err, err
        assert "basic_check 取值非法: 'xxx'" in err, err
        assert "with_reference: 必须是字典" in err, err
        assert "mode 取值非法: 'xxx'" in err, err
        assert "未知键 ['poll_timeout']" in err, err
        assert "basic_check=custom 时必须配置 custom_basic_check_program_path" in err, err
        # skip_checking_tag 为全局配置, spec 配同名键报未知键
        assert "未知键 ['skip_checking_tag']" in err, err
        assert "rule8" not in err, err  # 合法 spec 不报错


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
            text.replace("- example_rules", "- '@example_rules'").replace("        - '@example_rules.ruleX'\n",
                                                                          "").replace("        - '@no_such_set'\n", "")
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


def test_validate_condition_and_remove_tags_regex():
    """tags/category/trackers 条件与 remove_tags 动作的非法 regex: 模式在 config 阶段 fail-fast"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  my_rules:\n"
            "    r1:\n"
            "      conditions:\n"
            "        - tags: ['regex:[x']\n"
            "        - category: 'regex:[y'\n"
            "        - trackers: 'regex:[z'\n"
            "      actions:\n"
            "        - remove_tags: ['regex:[w']\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
        )
        err = _load_errors(td, text)
        assert "config.my_rules.r1.conditions[0].tags[0]: 非法正则" in err, err
        assert "config.my_rules.r1.conditions[1].category[0]: 非法正则" in err, err
        assert "config.my_rules.r1.conditions[2].trackers[0]: 非法正则" in err, err
        assert "config.my_rules.r1.actions[0].remove_tags[0]: 非法正则" in err, err


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
        assert issubclass(ConfigError, AutoQbError)  # 根异常(CLI 单点捕获)


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
    assert c.max_tasks_per_tick == 20 and c.state_file == "auto-qb-data/state.json"
    assert c.remove_similar_tags is False and c.add_episode_tags.enabled is False
    assert c.add_episode_tags.add_tag_single == "zE${episode_first}"
    assert c.add_episode_tags.add_tag_multi == "zE${episode_first}-${episode_last}"
    assert c.trackers == {} and c.global_speed_limit_curve is None
