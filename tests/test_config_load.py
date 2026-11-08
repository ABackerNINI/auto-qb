"""test_config_load 测试计划: 配置加载与 HR 规则解析

## 测试计划(每个测试函数一条)
- test_load_config_basic: 加载基础配置
- test_hr_rule_defaults: HRRule 默认值
- test_validate_empty_sections_use_defaults: 显式留空的段/键视为未配置(走默认值)
- test_data_dir_derives_runtime_paths: data_dir 主目录派生 state_file/log.file; 显式优先; log.file 留空/空串=默认落盘
- test_validate_unknown_keys_aggregated: 各段未知键聚合一次性报告(含路径)
- test_validate_root_unknown_key: 顶层未知键报错
- test_load_notify_config: notify 段解析(默认 platform 渠道/min_level 归一/dedup_window 时间解析)
- test_notify_min_level_default_is_error: 未配置 min_level 时默认 ERROR(等级整改 26-09-27-1126)
- test_validate_config_none_body_uses_defaults: config 裸键(None) = 合法空配置走默认零报错; 非字典标量才报「必须是字典」
- test_models_default_sources: 默认值单一来源 = dataclass 字段默认(段级/Config 顶层标量)
- test_load_tracker_groups: groups 解析回填 TrackerConfig, 未配置默认空列表
- test_config_schema_version_load_and_migrate_dispatch: schema_version 缺失=v1 加载成功; 非法/未来版本经迁移分派报 ConfigError(报清两个版本号)
- test_load_web_ctx_menu_passthrough: web.ctx_menu 原样 dict 透传(合法形状回读逐位相等; 缺省 None = 默认布局)
- test_example_minimal_yml_passes_fail_fast: minimal.yml 过 fail-fast 校验 + 钉 README 开箱语义(web/集数标签默认开) —— 示例文件无 schema 守卫会静默漂移(pitfalls/docs/drift.md)
- test_example_docker_config_yml_passes_fail_fast: docker/config.example.yml 过 fail-fast 校验 + 钉容器契约字段(data_dir=/data / web 0.0.0.0:8080 开 / notify 关(无桌面会话)/ grouping.check_missing_files 关(读宿主磁盘, 不关会误暂停整组 + 打 MISSING 标签) —— compose.yaml 的端口映射与 healthcheck 依赖)
- test_loader_defaults_tracker_config_keys_absent: load_tracker_config 键全缺省 -> TrackerConfig 字段默认(而非 None)
- test_loader_defaults_tracker_hr_output_chain: load_tracker_hr 输出键全缺省 -> HRRule 字段默认(回退链末段)
- test_loader_defaults_config_top_level_scalars: load_config 顶层标量键全缺省 -> Config 字段默认
- test_loader_defaults_sections_when_absent: 各段整段缺省 -> 段内键逐个走该段字段默认
- test_loader_defaults_gslc_optional_keys: global_speed_limit_curve 可选键缺省 -> interval=None/enabled=True/省略方向=None
- test_load_transfer_targets_non_list_defaults_empty: web.transfer 有段但 targets 缺失/非列表 -> TransferConfig() 空过(未配置语义)
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
    ROOT,
    _load_errors,
    _write_config,
    _write_raw,
)


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


def test_hr_rule_defaults():
    """HRRule 数据类默认值"""
    rule = HRRule()
    assert rule.required_seeding_time == 0
    assert rule.required_share_ratio == 0.0
    assert rule.condition == ("dlratio", 0.8)
    assert rule.add_category == ""
    assert rule.overwrite_category is False


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


def test_notify_min_level_default_is_error():
    """未配置 notify.min_level 时默认 ERROR(等级整改 26-09-27-1126: 只有真正危险才弹窗)"""
    with tempfile.TemporaryDirectory() as td:
        cfg = load_config(_write_config(td, notify={"enabled": "true"}))
        assert cfg.notify.min_level == "ERROR", "notify.min_level 默认必须是 ERROR"
        # 数据模型直构默认值同口径(NotifyConfig() 不经 YAML)
        assert NotifyConfig().min_level == "ERROR"


def test_validate_config_none_body_uses_defaults():
    """config 键存在但值为 None(空文件被 YAML 解析成 `config:` 裸键) -> 全部走默认, 零报错

    与「非字典」不同: None 是**合法的空配置**语义(`config:` 空段), 早退不报错;
    变异面: 把 None 与其它标量一起走 isinstance 分支 -> 空配置被误判「必须是字典」,
    首次启动即 fail-fast。
    """
    from auto_qb.config.validation import validate_config

    assert validate_config({}) == []
    assert validate_config({"config": None}) == []
    assert any("必须是字典" in e for e in validate_config({"config": ["x"]}))


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
    assert (
        c.download_fuse.enabled, c.download_fuse.download_limit, c.download_fuse.confirm_ticks, c.download_fuse.fuse_tag
    ) == (False, 13 * 1024, 3, "zFusePaused")


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
    # fs.path_map(plan 26-09-27-1407): 容器示例默认空表 = 映射关(保守默认); 带映射的注释样例在文件内
    assert config.fs.path_map == ()


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

        # 未来版本: fail-fast 且同时说清文件版本与程序支持版本(支持版本随 CURRENT_VERSIONS 演化, 不写死)
        from auto_qb.infra.versioning import CURRENT_VERSIONS

        err = _load_errors(td, "config:\n  schema_version: 9\n  trackers:\n    T1:\n      domains:\n        - a.com\n")
        assert "schema_version=9" in err and f"支持的 {CURRENT_VERSIONS['config']}" in err, \
            f"未来版本须报两个版本号: {err}"

        # 非整数 / < 1: 同样经迁移分派的 SchemaVersionError -> ConfigError
        err = _load_errors(
            td, "config:\n  schema_version: abc\n  trackers:\n    T1:\n      domains:\n        - a.com\n"
        )
        assert "必须是整数" in err
        err = _load_errors(td, "config:\n  schema_version: 0\n  trackers:\n    T1:\n      domains:\n        - a.com\n")
        assert ">= 1" in err


def test_load_web_ctx_menu_passthrough():
    """web.ctx_menu 原样透传(计划 26-10-20-0024 W1): 合法形状过校验并回读; 缺省 None = 默认布局"""
    base = "config:\n  trackers:\n    T1:\n      domains:\n        - a.com\n"
    text = base + (
        "  web:\n    ctx_menu:\n      group:\n        order: [resume, \"sep:d1\", delete]\n"
        "        hidden: [export]\n        sub:\n          order: [queue-top]\n          hidden: []\n"
    )
    with tempfile.TemporaryDirectory() as td:
        cfg = load_config(_write_raw(td, text))
        assert cfg.web.ctx_menu == {
            "group":
                {
                    "order": ["resume", "sep:d1", "delete"],
                    "hidden": ["export"],
                    "sub": {
                        "order": ["queue-top"],
                        "hidden": []
                    }
                }
        }
        cfg = load_config(_write_raw(td, base))
        assert cfg.web.ctx_menu is None  # 缺省 = 四支默认布局(与静态模板逐位一致)


def test_load_transfer_targets_non_list_defaults_empty():
    """web.transfer 有段但 targets 键缺失/非列表 -> TransferConfig() 空过(「未配置」语义, loader 不做形状兜底)"""
    from auto_qb.config import TransferConfig, load_web_config

    assert load_web_config({"transfer": {}}).transfer == TransferConfig()  # targets 键缺失
    assert load_web_config({"transfer": {"targets": "nope"}}).transfer == TransferConfig()  # targets 非列表
    assert load_web_config({"transfer": None}).transfer == TransferConfig()  # 整段缺省(另一早退)
    # 真实链路: transfer 空段过校验, 回读 = 未配置
    base = "config:\n  trackers:\n    T1:\n      domains:\n        - a.com\n"
    with tempfile.TemporaryDirectory() as td:
        cfg = load_config(_write_raw(td, base + "  web:\n    transfer: {}\n"))
        assert cfg.web.transfer == TransferConfig()


def test_loader_defaults_tracker_config_keys_absent():
    """load_tracker_config: 站点段只给 domains —— 其余键全缺省 -> 取 TrackerConfig 字段默认(而非 None)

    变异面: `_get(spec, KEY, d.<field>)` 的默认值换成 None、或整个关键字实参被删。池内旧用例
    都显式给了这些键(只钉「给了值 -> 解析对」), 缺「键缺省 -> 走字段默认」这条路径。
    """
    with tempfile.TemporaryDirectory() as td:
        cfg = load_config(_write_raw(td, "config:\n  trackers:\n    T1:\n      domains:\n        - a.com\n"))
        t = cfg.trackers["T1"]
        assert t.tags == [] and t.remove_tags == []
        assert t.upload_speed_limit == 0 and t.download_speed_limit == 0  # 0 = 不限速
        assert t.rules == [] and t.groups == []
        assert t.remove_similar_tags is False  # 全局也未配 -> 回退字段默认
        assert t.hr is None and t.hr_check is None


def test_loader_defaults_tracker_hr_output_chain():
    """load_tracker_hr: 站点段与全局段都没写输出键 -> 回退链末段取 HRRule 字段默认(而非 None)

    变异面: _load_hr_output_fields 字段默认末段 `getattr(d, key)` -> None。bool 分支会当场抛
    「无效布尔值」(可被别的用例撞见), str 分支静默变 None —— 正是本条要钉的。
    """
    rule = load_tracker_hr({"required_seeding_time": "3D"}, {})
    assert rule.add_tag == "" and rule.add_category == ""
    assert rule.add_tag_for_satisfied == "" and rule.add_category_for_satisfied == ""
    assert rule.overwrite_category is False and rule.overwrite_category_for_satisfied is False
    assert rule.required_share_ratio == 0.0 and rule.extra_seeding_time == 0
    assert rule.condition == ("dlratio", 0.8)
    assert rule.exclude_tags == [] and rule.exclude_categories == []
    # 回退链中段: 全局段给了值 -> 走全局(既不是字段默认也不是 None)
    assert load_tracker_hr({"required_seeding_time": "3D"}, {"add_tag": "zG"}).add_tag == "zG"


def test_loader_defaults_config_top_level_scalars():
    """load_config: 顶层标量键全缺省 -> 取 Config 字段默认(而非 None)

    main_tick / interval / data_dir / state_file / skip_checking_tag 已有旧用例钉住; 本条补齐
    sync_interval / state_save_interval / max_tasks_per_tick / maintenance_tag_mode /
    remove_similar_tags(全局) —— 后两者是运行参数, 变 None 不会报错只会静默改语义。
    """
    with tempfile.TemporaryDirectory() as td:
        cfg = load_config(_write_raw(td, "config:\n  trackers:\n    T1:\n      domains:\n        - a.com\n"))
        assert cfg.sync_interval == 1.5
        assert cfg.state_save_interval == 120.0
        assert cfg.max_tasks_per_tick == 20
        assert cfg.maintenance_tag_mode == "interval"
        assert cfg.remove_similar_tags is False
        assert cfg.skip_checking_tag == "zSkipChecked"


def test_loader_defaults_sections_when_absent():
    """各段整段缺省: 段内键逐个走该段 dataclass 字段默认(而非 None)

    段级 loader 都是「非字典 -> 返回 d 空实例」的早退形态之外, 还有「字典在但键缺」的分支;
    整段缺省走的是后者(`_get(cfg, "<段>", {})` -> 空字典), 本条钉住这条分支的默认值来源。
    """
    with tempfile.TemporaryDirectory() as td:
        cfg = load_config(_write_raw(td, "config:\n  trackers:\n    T1:\n      domains:\n        - a.com\n"))
        q = cfg.qbittorrent
        assert (q.host, q.port, q.username, q.password) == ("127.0.0.1", 8080, "", "")
        assert cfg.logging.level == logging.INFO
        assert cfg.logging.max_bytes == 10 * 1024**2
        assert cfg.logging.format == "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        g = cfg.grouping
        assert (g.enabled, g.check_missing_files, g.missing_tag,
                g.cross_group_conflict_check) == (True, True, "MISSING", False)
        w = cfg.web
        assert (w.host, w.port, w.token) == ("127.0.0.1", 8080, "")
        assert w.enabled is False and w.skip_local_verify is False and w.skip_check_menu is False
        n = cfg.notify
        assert (n.enabled, n.min_level, n.quiet_hours, n.max_per_hour,
                n.dedup_window) == (False, "ERROR", "", 20, 600.0)
        assert n.channels == ["platform"]  # 缺省即 platform 单渠道(不是空表)
        assert cfg.hr.add_tag == "" and cfg.hr.add_category == "" and cfg.hr.overwrite_category is False
        assert cfg.fs.path_map == ()
        d = cfg.download_fuse
        assert (d.enabled, d.download_limit, d.confirm_ticks, d.fuse_tag) == (False, 13 * 1024, 3, "zFusePaused")
        assert cfg.delete_tags == [] and cfg.delete_tags_if_has_no_torrents == []


def test_loader_defaults_gslc_optional_keys():
    """global_speed_limit_curve: 可选键全缺省 -> interval=None(回退主 interval) / enabled=True /
    省略方向的曲线=None(该方向不管理)

    变异面: `if "interval" in spec else None` 的 None 被换成具体秒数 —— 曲线任务会脱离主
    interval 独立跑; `if "download_curve" in curve_spec else None` 的 None 被换成空表 ——
    语义从「不管理该方向」翻成「该方向档位为空」。
    """
    with tempfile.TemporaryDirectory() as td:
        text = (
            "config:\n"
            "  traffic_source:\n"
            "    traffic_monitor:\n"
            "      dat_path: /tmp/history_traffic.dat\n"
            "  global_speed_limit_curve:\n"
            "    curves:\n"
            "      - curve:\n"
            "          period: 1D\n"
            "          upload_curve:\n"
            "            - 10GiB: {upload_speed_limit: 6MiB/s}\n"
        )
        cfg = load_config(_write_raw(td, text))
        g = cfg.global_speed_limit_curve
        assert g.enabled is True  # 缺省 True = 现行行为
        assert g.interval is None  # 未指定 -> 回退 config.interval
        assert traffic_paths.dat_path(cfg) == "/tmp/history_traffic.dat"
        assert g.curves[0].period == "day"
        assert g.curves[0].upload_points is not None
        assert g.curves[0].download_points is None  # 省略 download_curve = 不管理下载方向
