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
- test_validate_max_tasks_per_tick_range: max_tasks_per_tick 非正值报错(0/负值被 TaskQueue 当"不限量", 与配置语义相反)
- test_validate_value_ranges: 取值范围收紧聚合(interval/main_tick/sync_interval 上下界, max_tasks_per_tick 上界, log.max_bytes 轮转区间, required_share_ratio 有限性与范围, hr.condition 边界, notify 上界, 规则 interval 正时间)
- test_validate_rule_spec: 规则 spec 键/取值域/未知条件动作/多键项报错
- test_validate_state_condition_spec: state 条件非法 is_* 属性/裸枚举成员名报错
- test_validate_checking_action_spec: checking 动作 spec 深度校验聚合报错(非dict/缺键/非法值/段/未知键)
- test_validate_rule_refs: tracker.rules 引用必须 @ 开头且目标存在
- test_validate_regex_patterns: 非法 regex: 模式报错
- test_validate_condition_and_remove_tags_regex: tags/category/trackers 条件与 remove_tags 动作非法 regex: fail-fast
- test_validate_notify: notify 段校验(未知键/min_level/quiet_hours/max_per_hour/dedup_window/channels)
- test_load_notify_config: notify 段解析(默认 platform 渠道/min_level 归一/dedup_window 时间解析)
- test_validate_gslc: global_speed_limit_curve 原生校验器聚合错误
- test_validate_gslc_enabled_key: global_speed_limit_curve.enabled 总开关(缺省 True/false/true 解析/非布尔报错)
- test_validate_empty_file: 空文件/非字典根节点报错
- test_config_error_wraps_io_and_yaml: 文件读取/YAML 解析异常统一包装为 ConfigError
- test_models_default_sources: 默认值单一来源 = dataclass 字段默认(段级/Config 顶层标量)
- test_validate_section_type_errors: 各段非字典/非列表类型错误聚合(log/qbittorrent/grouping/hr/add_episode_tags/delete_tags 坏项)
- test_validate_hr_value_errors: 站点 hr 段值错误聚合(extra_seeding_time/required_share_ratio/condition/布尔)
- test_validate_tracker_groups: 站点 groups 非列表/空串项报错(fail-fast)
- test_load_tracker_groups: groups 解析回填 TrackerConfig, 未配置默认空列表
- test_validate_state_save_interval: state_save_interval 0(关闭)与 >=30s 合法; 低于下限/坏格式报错(防误配置写放大)
- test_config_schema_version_load_and_migrate_dispatch: schema_version 缺失=v1 加载成功; 非法/未来版本经迁移分派报 ConfigError(报清两个版本号)
- test_validate_schema_version_shape: validate_config 形状校验(须为整数/须>=1, 防御层)
- test_example_minimal_yml_passes_fail_fast: minimal.yml 过 fail-fast 校验 + 钉 README 开箱语义(web/集数标签默认开) —— 示例文件无 schema 守卫会静默漂移(pitfalls/docs/drift.md)
- test_example_docker_config_yml_passes_fail_fast: docker/config.example.yml 过 fail-fast 校验 + 钉容器契约字段(data_dir=/data / web 0.0.0.0:8080 开 / notify 关(无桌面会话)/ grouping.check_missing_files 关(读宿主磁盘, 不关会误暂停整组 + 打 MISSING 标签) —— compose.yaml 的端口映射与 healthcheck 依赖)
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
    QbittorrentConfig,
    TrackerConfig,
    load_config,
    load_tracker_hr,
)
from auto_qb.infra.errors import AutoQbError


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


def test_validate_max_tasks_per_tick_range():
    """max_tasks_per_tick 非正值 must 报错

    `TaskQueue._pop_due` 把 `max_tasks <= 0` 当"不限量"的内部语义, 配置放行 0/负值会让
    "每轮最多 N 个"反转成"一轮弹出全部到期任务"; schema 的 min=1 只管前端控件, 不进校验。
    """
    with tempfile.TemporaryDirectory() as td:
        for bad in ("0", "-5"):
            err = _load_errors(td, "config:\n  max_tasks_per_tick: %s\n" % bad)
            assert "config.max_tasks_per_tick: 须 >= 1" in err, err
        # 合法值与非整数不得被误伤(非整数的格式错误由 _try 记录)
        assert "config.max_tasks_per_tick" not in _load_errors(td, "config:\n  max_tasks_per_tick: 20\n")


def test_validate_state_save_interval():
    """state_save_interval: 0(关闭)与 >=30s 合法; 低于下限/坏格式报错(防误配置写放大)"""
    with tempfile.TemporaryDirectory() as td:
        # 合法: 0=关闭 / 下限值 / 常规值 / 带单位换算
        assert "state_save_interval" not in _load_errors(td, "config:\n  state_save_interval: 0S\n")
        assert "state_save_interval" not in _load_errors(td, "config:\n  state_save_interval: 30S\n")
        assert "state_save_interval" not in _load_errors(td, "config:\n  state_save_interval: 120S\n")
        assert "state_save_interval" not in _load_errors(td, "config:\n  state_save_interval: 2M\n")
        # 低于下限 -> 拒绝(下限 30s 防误配置写放大, issue 26-09-21-1347 拍板)
        err = _load_errors(td, "config:\n  state_save_interval: 29S\n")
        assert "config.state_save_interval: 须为 0(关闭)或 >= 30S(防误配置写放大): 29S" in err, err
        # 坏格式(裸数字无单位)/负数 -> 格式报错
        assert "config.state_save_interval: 无效时间格式" in _load_errors(td, "config:\n  state_save_interval: 120\n")
        assert "config.state_save_interval: 无效时间格式" in _load_errors(td, "config:\n  state_save_interval: -5S\n")


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


def test_validate_notify():
    """notify 段校验: 未知键/min_level/quiet_hours/max_per_hour/dedup_window/channels 聚合报错"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  notify:\n"
            "    unknown_key: 1\n"
            "    min_level: DEBUG\n"
            "    quiet_hours: '25:00-99:99'\n"
            "    max_per_hour: 0\n"
            "    dedup_window: abc\n"
            "    channels:\n"
            "      - dingtalk: {}\n"
        )
        err = _load_errors(td, text)
        assert "config.notify: 未知键 ['unknown_key']" in err, err
        assert "config.notify.min_level: 须为 INFO/WARNING/ERROR 之一: 'DEBUG'" in err, err
        assert "config.notify.quiet_hours('25:00-99:99')" in err, err
        assert "config.notify.max_per_hour: 必须为正整数" in err, err
        assert "config.notify.dedup_window" in err, err
        assert "config.notify.channels[0]: 未知渠道 'dingtalk'" in err, err


def test_load_notify_config():
    """notify 段解析: 默认 platform 渠道/min_level 大小写归一/dedup_window 时间解析/quiet_hours 透传"""
    with tempfile.TemporaryDirectory() as td:
        cfg = load_config(
            _write_config(
                td,
                notify={
                    "enabled": "true",
                    "min_level": "error",
                    "quiet_hours": "23:00-08:00",
                    "max_per_hour": "5",
                    "dedup_window": "1M",
                },
            )
        )
        assert cfg.notify.enabled is True
        assert cfg.notify.min_level == "ERROR"
        assert cfg.notify.quiet_hours == "23:00-08:00"
        assert cfg.notify.max_per_hour == 5
        assert cfg.notify.dedup_window == 60.0
        assert cfg.notify.channels == ["platform"]  # 未显式配置 -> 默认启用平台渠道


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


def test_validate_section_type_errors():
    """各段非字典/非列表类型错误聚合(log/qbittorrent/grouping/hr/add_episode_tags/delete_tags/坏项)"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  log: [not-a-dict]\n"
            "  qbittorrent: 123\n"
            "  grouping: not-dict\n"
            "  hr: 456\n"
            "  add_episode_tags: not-dict\n"
            "  delete_tags: ["
            ", 5]\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
            "      tags: not-a-list\n"
        )
        err = _load_errors(td, text)
        assert "config.log: 必须是字典" in err, err
        assert "config.qbittorrent: 必须是字典" in err, err
        assert "config.grouping: 必须是字典" in err, err
        assert "config.hr: 必须是字典" in err, err
        assert "config.add_episode_tags: 必须是字典" in err, err
        assert "config.delete_tags: 第 [0] 项必须是非空字符串" in err, err
        assert "config.trackers.T1.tags: 必须是列表" in err, err


def test_validate_hr_value_errors():
    """站点 hr 段值错误聚合(extra_seeding_time/required_share_ratio/condition/布尔非法)"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  grouping:\n"
            "    enabled: not-bool\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
            "      hr:\n"
            "        required_seeding_time: 3D\n"
            "        extra_seeding_time: abc\n"
            "        required_share_ratio: not-number\n"
            "        condition: bad-cond\n"
            "        overwrite_category: not-bool\n"
        )
        err = _load_errors(td, text)
        assert "config.grouping.enabled" in err, err
        assert "config.trackers.T1.hr.extra_seeding_time" in err, err
        assert "config.trackers.T1.hr.required_share_ratio(须为数字)" in err, err
        assert "config.trackers.T1.hr.condition(如 80% 或 10MiB)" in err, err
        assert "config.trackers.T1.hr.overwrite_category" in err, err


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


def test_validate_gslc_enabled_key():
    """global_speed_limit_curve.enabled 功能总开关: 缺省 True / false 关闭 / true 开启 / 非布尔报错"""
    base = (
        "config:\n"
        "  global_speed_limit_curve:\n"
        "    traffic_source:\n"
        "      - traffic_monitor:\n"
        "          dat_path: a.dat\n"
        "    curves:\n"
        "      - curve:\n"
        "          period: 1D\n"
        "          upload_curve:\n"
        "            - 10GiB: {upload_speed_limit: 6MiB/s}\n"
    )
    with tempfile.TemporaryDirectory() as td:
        cfg = load_config(_write_raw(td, base))
        assert cfg.global_speed_limit_curve.enabled is True  # 缺省 True = 现行行为

        cfg = load_config(_write_raw(td, base + "    enabled: false\n"))
        assert cfg.global_speed_limit_curve.enabled is False

        cfg = load_config(_write_raw(td, base + "    enabled: true\n"))
        assert cfg.global_speed_limit_curve.enabled is True

        err = _load_errors(td, base + "    enabled: not-bool\n")
        assert "config.global_speed_limit_curve.enabled" in err, err


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


def test_validate_section_type_errors():
    """各段非字典/非列表类型错误聚合(log/qbittorrent/grouping/hr/add_episode_tags/delete_tags/坏项)"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  log: [not-a-dict]\n"
            "  qbittorrent: 123\n"
            "  grouping: not-dict\n"
            "  hr: 456\n"
            "  add_episode_tags: not-dict\n"
            "  delete_tags: [\" \", 5]\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
            "      tags: not-a-list\n"
        )
        err = _load_errors(td, text)
        assert "config.log: 必须是字典" in err, err
        assert "config.qbittorrent: 必须是字典" in err, err
        assert "config.grouping: 必须是字典" in err, err
        assert "config.hr: 必须是字典" in err, err
        assert "config.add_episode_tags: 必须是字典" in err, err
        assert "config.delete_tags: 第 [0] 项必须是非空字符串" in err, err
        assert "config.trackers.T1.tags: 必须是列表" in err, err


def test_validate_hr_value_errors():
    """站点 hr 段值错误聚合(extra_seeding_time/required_share_ratio/condition/布尔非法)"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  grouping:\n"
            "    enabled: not-bool\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
            "      hr:\n"
            "        required_seeding_time: 3D\n"
            "        extra_seeding_time: abc\n"
            "        required_share_ratio: not-number\n"
            "        condition: bad-cond\n"
            "        overwrite_category: not-bool\n"
        )
        err = _load_errors(td, text)
        assert "config.grouping.enabled" in err, err
        assert "config.trackers.T1.hr.extra_seeding_time" in err, err
        assert "config.trackers.T1.hr.required_share_ratio(须为数字)" in err, err
        assert "config.trackers.T1.hr.condition(如 80% 或 10MiB)" in err, err
        assert "config.trackers.T1.hr.overwrite_category" in err, err


def test_validate_value_errors_extended():
    """值错误扩展: add_episode_tags 模板/端口非整数/hr 未知键与布尔/trackers 标量与字段/规则集结构/触发白名单

    注意: 空串值会被 _strip_none 过滤(走默认), 因此"必须非空"类断言用纯空格串触发。
    """
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  add_episode_tags:\n"
            "    enabled: not-bool\n"
            "    add_tag_single: \" \"\n"
            "  qbittorrent:\n"
            "    host: h\n"
            "    port: not-int\n"
            "  hr:\n"
            "    unknown_key: 1\n"
            "    overwrite_category: not-bool\n"
            "  trackers: 123\n"
            "  example_rules:\n"
            "    r1:\n"
            "      conditions: not-a-list\n"
            "      actions: not-a-list\n"
            "      trigger: bad-trigger\n"
        )
        err = _load_errors(td, text)
        assert "config.add_episode_tags.enabled" in err, err
        assert "config.add_episode_tags.add_tag_single: 必须是非空字符串" in err, err
        assert "config.qbittorrent.port: 必须是整数" in err, err
        assert "config.hr: 未知键" in err, err
        assert "config.hr.overwrite_category" in err, err
        assert "config.trackers: 必须是字典" in err, err
        assert "config.example_rules.r1.conditions: 必须是列表" in err, err
        assert "config.example_rules.r1.actions: 必须是列表" in err, err
        assert "config.example_rules.r1: trigger 取值非法" in err, err


def test_validate_tracker_groups():
    """站点 groups 字段: 非列表/纯空白串项报错(空串项被 _strip_none 视为未配置剔除, 项目统一约定; 空列表合法)"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
            "      groups: not-a-list\n"
            "    T2:\n"
            "      domains: [b.com]\n"
            "      groups: ['  ']\n"
        )
        err = _load_errors(td, text)
        assert "config.trackers.T1.groups: 必须是列表" in err, err
        assert "config.trackers.T2.groups: 第 [0] 项必须是非空字符串" in err, err


def test_load_tracker_groups():
    """站点 groups 解析回填 TrackerConfig(字符串列表); 未配置默认空列表"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
            "      groups: [国内, 影视]\n"
            "    T2:\n"
            "      domains: [b.com]\n"
        )
        path = os.path.join(td, "config.yml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        cfg = load_config(path)
        assert cfg.trackers["T1"].groups == ["国内", "影视"]
        assert cfg.trackers["T2"].groups == []


def test_validate_tracker_field_errors():
    """trackers 字段错误: domains 空列表/remove_similar_tags 非布尔/hr 非字典"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: []\n"
            "      remove_similar_tags: not-bool\n"
            "      hr: not-dict\n"
            "    T2: not-dict\n"
        )
        err = _load_errors(td, text)
        assert "config.trackers.T1.domains: 必须是非空字符串列表" in err, err
        assert "config.trackers.T2: 必须是字典" in err, err
        assert "config.trackers.T1.remove_similar_tags" in err, err
        assert "config.trackers.T1.hr: 必须是字典" in err, err


def test_validate_plugin_entry_and_notify_edges():
    """插件项空值/ignore_next 非布尔/notify 非字典"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  my_rules:\n"
            "    r1:\n"
            "      conditions:\n"
            "        - tags:\n"
            "      actions:\n"
            "        - {}\n"
            "        - ignore_next_action_error: not-bool\n"
            "        - reannounce: true\n"
            "  notify: not-dict\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
        )
        err = _load_errors(td, text)
        assert "值不能为空" in err, err
        assert "config.my_rules.r1.actions[1].ignore_next_action_error" in err, err
        assert "config.notify: 必须是字典" in err, err


def test_validate_trackers_and_rules_structure():
    """trackers 非字典/规则集非字典/规则 spec 非字典/conditions-actions 非列表"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  trackers: 123\n"
            "  example_rules: 456\n"
            "  more_rules:\n"
            "    r1: not-dict\n"
            "    r2:\n"
            "      conditions: not-a-list\n"
            "      actions: not-a-list\n"
        )
        err = _load_errors(td, text)
        assert "config.trackers: 必须是字典" in err, err
        assert "config.example_rules: 必须是字典(规则名 -> 规则spec)" in err, err
        assert "config.more_rules.r1: 必须是字典" in err, err
        assert "config.more_rules.r2.conditions: 必须是列表" in err, err
        assert "config.more_rules.r2.actions: 必须是列表" in err, err


def test_validate_notify_and_root_edges():
    """notify 字段边界(quiet_hours 无-/max_per_hour 非整数/channels 结构)/根节点 config 非字典/gslc 阈值非法"""
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  notify:\n"
            "    quiet_hours: 2300\n"
            "    max_per_hour: []\n"
            "    channels: not-a-list\n"
            "  global_speed_limit_curve:\n"
            "    traffic_source:\n"
            "      - traffic_monitor:\n"
            "          dat_path: x.dat\n"
            "    curves:\n"
            "      - curve:\n"
            "          period: DAY\n"
            "          upload_curve:\n"
            "            - abc: {upload_speed_limit: 1MiB/s}\n"
            "  trackers:\n"
            "    T1:\n"
            "      domains: [a.com]\n"
        )
        err = _load_errors(td, text)
        assert "config.notify.quiet_hours: 须为" in err, err
        assert "config.notify.max_per_hour: 必须为整数" in err, err
        assert "config.notify.channels: 必须是非空列表" in err, err
        assert "config: 必须是字典" not in err, err
        assert "abc" in err, err


def test_validate_root_config_not_dict():
    """根节点 config 非字典 -> 必须是字典"""
    with tempfile.TemporaryDirectory() as td:
        text = "config: 123\n"
        err = _load_errors(td, text)
        assert "config: 必须是字典" in err, err


def test_validate_value_ranges():
    """取值范围收紧聚合: 防止"格式合法但危险"的值进入运行时

    - config.interval: 0 会经 TaskQueue._norm_interval 归一化成 1s(全部种子级任务每秒跑)
    - log.max_bytes: 0 在 RotatingFileHandler 语义 = 从不轮转(单文件无限增长)
    - required_share_ratio: 负数/nan/inf 会静默破坏 HR 判定语义(nan 比较恒 False)
    - hr.condition: "0%"/负数立即满足、">100%"永不触发, 均与配置意图相反
    - 规则 interval: 显式 0 同样归一化成每秒全量跑; cooldown=0 是文档化的"不冷却"语义, 不拦
    """
    with tempfile.TemporaryDirectory() as td:
        # --- config.interval: 上下界(1s-1D), 边界值合法
        assert "config.interval: 须 >= 1s" in _load_errors(td, "config:\n  interval: 0S\n")
        assert "config.interval: 须 <= 86400s" in _load_errors(td, "config:\n  interval: 2D\n")
        assert _load_errors(td, "config:\n  interval: 1S\n") == ""
        assert _load_errors(td, "config:\n  interval: 1D\n") == ""
        # --- main_tick / sync_interval: 高频下限与失效上限
        assert "config.main_tick: 须 >= 0.5s" in _load_errors(td, "config:\n  main_tick: 0.1S\n")
        assert "config.main_tick: 须 <= 3600s" in _load_errors(td, "config:\n  main_tick: 2H\n")
        assert _load_errors(td, "config:\n  main_tick: 30M\n") == ""
        assert "config.sync_interval: 须 >= 1s" in _load_errors(td, "config:\n  sync_interval: 0.5S\n")
        assert _load_errors(td, "config:\n  sync_interval: 10M\n") == ""
        # --- max_tasks_per_tick 上界(下界已有独立测试)
        assert "config.max_tasks_per_tick: 须 <= 500" in _load_errors(td, "config:\n  max_tasks_per_tick: 501\n")
        assert _load_errors(td, "config:\n  max_tasks_per_tick: 500\n") == ""
        # --- log.max_bytes: 0B/过小/过大都拦, 默认值合法(裸数字无单位是格式错误, 不进范围检查)
        err = _load_errors(td, "config:\n  log:\n    max_bytes: 0B\n")
        assert "config.log.max_bytes: 须在 1MiB-1GiB 范围内" in err, err
        assert "config.log.max_bytes" in _load_errors(td, "config:\n  log:\n    max_bytes: 512KiB\n")
        assert "config.log.max_bytes" in _load_errors(td, "config:\n  log:\n    max_bytes: 2GiB\n")
        assert _load_errors(td, "config:\n  log:\n    max_bytes: 10MiB\n") == ""

        def _hr_ratio(value):
            return _load_errors(
                td,
                "config:\n  trackers:\n    T1:\n      domains: [a.com]\n      hr:\n"
                "        required_seeding_time: 3D\n        required_share_ratio: %s\n" % value,
            )

        # --- required_share_ratio: nan/inf/负数/超上界, 边界 0(不要求)与 100 合法
        assert "须为有限数字" in _hr_ratio("nan")
        assert "须为有限数字" in _hr_ratio("inf")
        assert "须 >= 0" in _hr_ratio("-1")
        assert "须 <= 100" in _hr_ratio("101")
        assert _hr_ratio("0") == ""
        assert _hr_ratio("100") == ""

        def _hr_cond(value):
            return _load_errors(
                td,
                "config:\n  trackers:\n    T1:\n      domains: [a.com]\n      hr:\n"
                "        required_seeding_time: 3D\n        condition: %s\n" % value,
            )

        # --- hr.condition: 百分比 (0,100] / 下载量 >0, 边界合法
        assert "HR 百分比条件须 (0, 100]" in _hr_cond("0%")
        assert "HR 百分比条件须 (0, 100]" in _hr_cond("200%")
        assert "HR 百分比条件须 (0, 100]" in _hr_cond("-5%")
        assert "HR 下载量条件须 > 0" in _hr_cond("0MiB")
        assert _hr_cond("80%") == ""
        assert _hr_cond("100%") == ""
        assert _hr_cond("10MiB") == ""
        # --- notify: max_per_hour 上界; dedup_window 上限(0=不去重仍合法)
        assert "config.notify.max_per_hour: 须 <= 100" in _load_errors(td, "config:\n  notify:\n    max_per_hour: 101\n")
        assert _load_errors(td, "config:\n  notify:\n    max_per_hour: 100\n") == ""
        assert "config.notify.dedup_window: 须 <= 86400s" in _load_errors(
            td, "config:\n  notify:\n    dedup_window: 25H\n"
        )
        assert _load_errors(td, "config:\n  notify:\n    dedup_window: 0S\n") == ""
        # --- 规则 interval: 显式 0 拦(队列归一化成 1s); cooldown=0 是"不冷却"语义, 不拦
        assert "config.rr_rules.r1.interval: 必须为正时间" in _load_errors(
            td, "config:\n  rr_rules:\n    r1:\n      interval: 0S\n"
        )
        assert _load_errors(td, "config:\n  rr_rules:\n    r1:\n      interval: 5S\n") == ""
        assert _load_errors(td, "config:\n  rr_rules:\n    r1:\n      cooldown: 0S\n") == ""


# ---------- 示例配置守阵: 示例文件没有守卫会随 schema 演进静默漂移(pitfalls/docs/drift.md, 2026-09-25 实证) ----------

ROOT = Path(__file__).resolve().parents[1]


def test_example_minimal_yml_passes_fail_fast():
    """minimal.yml 必须过 fail-fast 校验(README 快速开始的入口配置)。
    曾因 add_episode_tags 旧布尔形态漂移: 校验红是小事, 真坑是 enabled 默认 false 被静默解析成关。
    除"能加载"外钉住 README 承诺的开箱语义: Web UI 默认开启 + 集数标签默认开启。"""
    config = load_config(str(ROOT / "minimal.yml"))
    assert config.web.enabled is True
    assert config.add_episode_tags.enabled is True


def test_example_docker_config_yml_passes_fail_fast():
    """docker/config.example.yml 必须过 fail-fast 校验, 且容器契约字段不被改坏
    (compose.yaml 的端口映射 / named volume / healthcheck 都写死依赖这些值)。"""
    config = load_config(str(ROOT / "docker" / "config.example.yml"))
    assert config.data_dir == "/data"  # compose: named volume auto-qb-data -> /data
    assert config.web.host == "0.0.0.0"  # 容器内 127.0.0.1 = 端口映射过去谁也连不上
    assert config.web.enabled is True  # healthcheck 探的就是这个端口
    assert config.web.port == 8080  # compose ports "8081:8080" 与 healthcheck 写死 8080
    assert config.notify.enabled is False  # 容器无桌面会话, 平台通知预期不可用
    # 缺文件扫描读的是 qB 报回的宿主保存路径 —— 容器内恒"不存在" ⇒ 误暂停整组 + 打 MISSING 标签(真实写 qB)
    assert config.grouping.check_missing_files is False


def test_config_schema_version_load_and_migrate_dispatch(td=None):
    """schema 版本链(计划 26-09-26-0506): 无键=v1 存量口径加载成功; 非法/未来版本 ConfigError 报清两个版本号

    用最小配置(仅 trackers 必填)直载: _load_errors 走的就是 load_config 完整路径(含迁移分派)。
    """
    with tempfile.TemporaryDirectory() as td:
        # 无键(存量口径)与显式 v1 都正常加载
        cfg = load_config(_write_raw(td, "config:\n  trackers:\n    T1:\n      domains:\n        - a.com\n"))
        assert cfg.trackers["T1"].domains == ["a.com"]
        cfg = load_config(
            _write_raw(td, "config:\n  schema_version: 1\n  trackers:\n    T1:\n      domains:\n        - a.com\n")
        )
        assert cfg.trackers["T1"].domains == ["a.com"]

        # 未来版本: fail-fast 且同时说清文件版本与程序支持版本
        err = _load_errors(td, "config:\n  schema_version: 9\n  trackers:\n    T1:\n      domains:\n        - a.com\n")
        assert "schema_version=9" in err and "支持的 1" in err, f"未来版本须报两个版本号: {err}"

        # 非整数 / < 1: 同样经迁移分派的 SchemaVersionError -> ConfigError
        err = _load_errors(
            td, "config:\n  schema_version: abc\n  trackers:\n    T1:\n      domains:\n        - a.com\n"
        )
        assert "必须是整数" in err
        err = _load_errors(td, "config:\n  schema_version: 0\n  trackers:\n    T1:\n      domains:\n        - a.com\n")
        assert ">= 1" in err


def test_validate_schema_version_shape():
    """validate_config 形状校验(防御层): schema_version 非整数/负值聚合报错"""
    from auto_qb.config.validation import validate_config

    errors = validate_config({"config": {"schema_version": "abc"}})
    assert any("须为整数" in e for e in errors)
    errors = validate_config({"config": {"schema_version": "-3"}})
    assert any("须 >= 1" in e for e in errors)
    assert validate_config({"config": {"schema_version": "1"}}) == []
