"""test_config_traffic_monitor 测试计划: traffic_source 段(计划 26-10-17-0339 S15)

> 本文件原覆盖已退休的 global_traffic_monitor 段; S15 后同文件改覆盖新顶层 traffic_source 段
> (校验 + loader + v4→v5 迁移), 文件名保留以免与既有引用/基线对不上。

## 测试计划(每个测试函数一条)
- test_validate_absent_section_ok: 整段缺省(None)合法 -> 走默认值(provider=traffic_monitor)
- test_validate_unknown_key_rejected: 顶层未知键被拒, 已知键集合与 schema 单点一致(黄金法则 4; 含 S1 总开关 enabled)
- test_validate_provider_enum: provider 非枚举值被拒; 缺省/留空 = traffic_monitor 合法(只要有 dat_path)
- test_validate_default_provider_requires_dat_path: provider=traffic_monitor 时 dat_path 缺失/空/非串 -> 拒绝
- test_validate_tool_branch_structure: global_traffic_monitor 子块未知键/非串路径被拒; provider=global 时无需 dat_path
- test_validate_tool_data_dir_key_is_gone: data_dir 已从工具子段删除(R2/D20), 出现即按未知键拒绝
- test_validate_notify_cooldown_bounds: notify_cooldown_s 须可解析为时间且 0~24H(负/超界拒, 0 合法)
- test_validate_refresh_interval_bounds: refresh_interval(A3) 须可解析为时间且 10S~1H(边界含, 9S/2H/非串拒)
- test_validate_valid_section_ok: 全键合法值一次通过(两来源参数可并存)
- test_loader_parses_explicit_values: 显式值按类型解析(str/time, 含 A3 的 refresh_interval), 与字段默认不同的值真正进入 Config
- test_loader_defaults_when_absent: 段缺省 -> 全部字段默认
- test_loader_non_dict_spec_defaults: 段值非字典(如字符串) -> 全默认(不抛)
- test_loader_blank_provider_falls_back: provider 留空/纯空白 -> 兜底 traffic_monitor
  (取数路径解析见 test_traffic_source_paths.py: active_dat_path 已随 R2/D20 退休)
- test_round_trip_through_load_config: 新段经 load_config 真链路(读文件 -> 剥空 -> 迁移 -> 校验 -> 解析)回读一致
- test_migrate_v4_merges_curve_source: 旧曲线段内联 dat_path 迁到顶层, 曲线段内 traffic_source 键删除、其余保留
- test_migrate_v4_removes_global_monitor_section: 旧 gtm 段: 仅 notify_cooldown_s 迁走, 其余键与整段删除
- test_migrate_v4_derives_provider: 旧 gtm 段非空 -> provider=global_traffic_monitor; 否则 traffic_monitor
- test_migrate_v4_notes_per_key: 每个被删/被迁的键各产出一条可读 note
- test_migrate_v4_is_idempotent: 对已是 v5 形状的输入无副作用(不产 note, 不改结构)
- test_migrate_v4_through_load_config: v4 旧配置经 load_config 全链路升到 v5, 取数路径与旧行为等价
- test_migrate_v4_defensive_shapes_skipped: 曲线内 traffic_source 非列表/列表项非字典/dat_path 空 —— 三类畸形形状静默跳过取数, 键照删(255/257/259 假弧)
- test_migrate_v4_keeps_existing_traffic_source_dicts: 顶层 traffic_source 与其两子块已是字典时就地改写不重建空壳(279/288/300 假弧), 显式键原样保留
- test_migrate_v4_with_gtm_section_through_load_config
"""
from pathlib import Path

import yaml

from auto_qb.config.loaders import load_traffic_source_config
from auto_qb.config.models import Config, TrafficSourceConfig
from auto_qb.config.validation import (
    KNOWN_TRAFFIC_SOURCE_KEYS,
    KNOWN_TRAFFIC_SOURCE_TM_KEYS,
    KNOWN_TRAFFIC_SOURCE_TOOL_KEYS,
    validate_config,
)
from auto_qb.core.traffic_source import paths as traffic_paths
from auto_qb.infra.versioning import MIGRATIONS

#: v4→v5 迁移函数(注册表取用 = 被测的是真注册项, 不是同名的旁路实现)
_migrate_v4_to_v5 = MIGRATIONS["config"][4]


def _errors(section) -> list:
    return validate_config({"config": {"traffic_source": section}})


def test_validate_absent_section_ok():
    assert validate_config({"config": {}}) == []
    assert validate_config({"config": {"traffic_source": None}}) == []


def test_validate_unknown_key_rejected():
    errs = _errors({"provider": "traffic_monitor", "traffic_monitor": {"dat_path": "/x.dat"}, "bogus": "1"})
    assert any("未知键" in e and "bogus" in e for e in errs), errs
    # 已知键集合与 schema 单点一致(顶层 5 键 + TM 1 键 + 工具 3 键)
    # 顶层 5 键含 26-10-17-0339 S1 的 enabled 总开关(停取数/停订阅/停拉起)
    # 与 26-10-18-0813 A3 的 refresh_interval(来源侧刷新节奏, 与曲线 interval 解绑)
    assert KNOWN_TRAFFIC_SOURCE_KEYS == {
        "enabled", "provider", "refresh_interval", "traffic_monitor", "global_traffic_monitor"
    }
    assert KNOWN_TRAFFIC_SOURCE_TM_KEYS == {"dat_path"}
    assert KNOWN_TRAFFIC_SOURCE_TOOL_KEYS == {"tool_dir", "tool_exe", "notify_cooldown_s"}


def test_validate_provider_enum():
    # 缺省/留空 = traffic_monitor(只要有 dat_path 即合法)
    assert _errors({"traffic_monitor": {"dat_path": "/x.dat"}}) == []
    assert _errors({"provider": "", "traffic_monitor": {"dat_path": "/x.dat"}}) == []
    errs = _errors({"provider": "bogus", "traffic_monitor": {"dat_path": "/x.dat"}})
    assert any("config.traffic_source.provider" in e for e in errs), errs


def test_validate_default_provider_requires_dat_path():
    # provider 缺省 = traffic_monitor -> 必须给非空 dat_path
    for bad in (
        {}, {
            "traffic_monitor": {}
        }, {
            "traffic_monitor": {
                "dat_path": ""
            }
        }, {
            "traffic_monitor": {
                "dat_path": "   "
            }
        }, {
            "traffic_monitor": {
                "dat_path": ["x"]
            }
        }
    ):
        errs = _errors(bad)
        assert any("traffic_monitor.dat_path" in e for e in errs), (bad, errs)
    assert _errors({"traffic_monitor": {"dat_path": "/x.dat"}}) == []


def test_validate_tool_branch_structure():
    # provider=global_traffic_monitor: 无需 traffic_monitor.dat_path
    assert _errors({"provider": "global_traffic_monitor", "global_traffic_monitor": {"tool_dir": "/d"}}) == []
    # 工具子块未知键被拒
    errs = _errors({"provider": "global_traffic_monitor", "global_traffic_monitor": {"bogus": "1"}})
    assert any("global_traffic_monitor" in e and "bogus" in e for e in errs), errs
    # 路径键非字符串被拒
    errs = _errors({"provider": "global_traffic_monitor", "global_traffic_monitor": {"tool_dir": ["x"]}})
    assert any("global_traffic_monitor.tool_dir" in e for e in errs), errs


def test_validate_tool_data_dir_key_is_gone():
    """data_dir 已从工具子段删除(R2/D20): 数据目录由工具发现指针提供, 配置里存副本会漂移

    出现该键走通用未知键报错(不做专用指路) —— 宁可让残留配置启动即失败, 也不静默忽略:
    忽略会让用户以为"配了 data_dir 就在生效", 正是 26-10-17 事故的误判来源。
    """
    errs = _errors({"provider": "global_traffic_monitor", "global_traffic_monitor": {"data_dir": "/opt/gtm/data"}})
    assert any("未知键" in e and "data_dir" in e for e in errs), errs


def test_validate_notify_cooldown_bounds():
    def _tool(cooldown):
        return _errors(
            {
                "provider": "global_traffic_monitor",
                "global_traffic_monitor": {
                    "notify_cooldown_s": cooldown
                },
            }
        )

    assert _tool("0S") == []
    assert _tool("10M") == []
    assert _tool("24H") == []
    assert any("notify_cooldown_s" in e for e in _tool("-1S"))
    assert any("notify_cooldown_s" in e for e in _tool("48H"))
    assert any("notify_cooldown_s" in e for e in _tool("abc"))


def test_validate_refresh_interval_bounds():
    """来源侧快照节奏(26-10-18-0813 A3/D9): 可解析为时间且 10S~1H, 与曲线 interval 各自校验

    下限防「每个 tick 读盘 + 发布」空转, 上限防历史图停在一天前; 非时间串同样拒绝。
    """
    def _sec(value):
        return _errors(
            {
                "provider": "traffic_monitor",
                "traffic_monitor": {
                    "dat_path": "/x.dat"
                },
                "refresh_interval": value
            }
        )

    assert _sec("10S") == []  # 下限含边界
    assert _sec("10M") == []  # 默认值必须合法
    assert _sec("1H") == []  # 上限含边界
    assert any("refresh_interval" in e for e in _sec("9S")), "低于 10S 必须拒绝"
    assert any("refresh_interval" in e for e in _sec("2H")), "高于 1H 必须拒绝"
    assert any("refresh_interval" in e for e in _sec("abc")), "非时间串必须拒绝"


def test_validate_valid_section_ok():
    assert _errors(
        {
            "provider": "global_traffic_monitor",
            "traffic_monitor": {
                "dat_path": "/x/history_traffic.dat"
            },
            "global_traffic_monitor":
                {
                    "tool_dir": "/opt/gtm",
                    "tool_exe": "/opt/gtm/monitor.exe",
                    "notify_cooldown_s": "5M",
                },
        }
    ) == []


def test_loader_parses_explicit_values():
    cfg = load_traffic_source_config(
        {
            "provider": "global_traffic_monitor",
            "refresh_interval": "15M",
            "traffic_monitor": {
                "dat_path": "/probe/tm.dat"
            },
            "global_traffic_monitor":
                {
                    "tool_dir": "/probe/gtm",
                    "tool_exe": "/probe/gtm/monitor.exe",
                    "notify_cooldown_s": "90S",
                },
        }
    )
    assert cfg.provider == "global_traffic_monitor"
    assert cfg.refresh_interval == 900.0  # A3: time 串解析为秒
    assert cfg.traffic_monitor.dat_path == "/probe/tm.dat"
    assert cfg.global_traffic_monitor.tool_dir == "/probe/gtm"
    assert cfg.global_traffic_monitor.tool_exe == "/probe/gtm/monitor.exe"
    assert cfg.global_traffic_monitor.notify_cooldown_s == 90.0


def test_loader_defaults_when_absent():
    d = TrafficSourceConfig()
    assert load_traffic_source_config(None) == d
    assert load_traffic_source_config({}) == d
    assert Config().traffic_source == d
    assert d.provider == "traffic_monitor"
    assert d.refresh_interval == 600.0  # A3: 默认 10M, 与 schema 声明的 default 同值
    assert d.traffic_monitor.dat_path == ""
    assert d.global_traffic_monitor.tool_dir == "" and d.global_traffic_monitor.tool_exe == ""
    assert d.global_traffic_monitor.notify_cooldown_s == 600.0


def test_loader_non_dict_spec_defaults():
    assert load_traffic_source_config("nonsense") == TrafficSourceConfig()


def test_loader_blank_provider_falls_back():
    assert load_traffic_source_config({"provider": ""}).provider == "traffic_monitor"
    assert load_traffic_source_config({"provider": "   "}).provider == "traffic_monitor"


def test_round_trip_through_load_config(tmp_path):
    """新段经 load_config 真链路回读一致(显式 schema_version=5, 不走迁移)"""
    from auto_qb.config import load_config

    probe = {
        "config":
            {
                "schema_version": 5,
                "traffic_source":
                    {
                        "provider": "global_traffic_monitor",
                        "traffic_monitor": {
                            "dat_path": "/probe/tm.dat"
                        },
                        "global_traffic_monitor":
                            {
                                "tool_dir": "/probe/gtm",
                                "tool_exe": "/probe/gtm/monitor.exe",
                                "notify_cooldown_s": "3M",
                            },
                    },
            }
    }
    path = Path(tmp_path) / "cfg.yml"
    path.write_text(yaml.safe_dump(probe, allow_unicode=True), encoding="utf-8")
    ts = load_config(str(path)).traffic_source
    assert ts.provider == "global_traffic_monitor"
    assert ts.traffic_monitor.dat_path == "/probe/tm.dat"
    assert ts.global_traffic_monitor.tool_dir == "/probe/gtm"
    assert ts.global_traffic_monitor.notify_cooldown_s == 180.0


def test_migrate_v4_merges_curve_source():
    cfg = {
        "global_speed_limit_curve":
            {
                "enabled": "true",
                "interval": "10M",
                "traffic_source": [{
                    "traffic_monitor": {
                        "dat_path": "/old/history_traffic.dat"
                    }
                }],
                "curves": [],
            }
    }
    out, notes = _migrate_v4_to_v5(cfg)
    assert out["traffic_source"]["provider"] == "traffic_monitor"
    assert out["traffic_source"]["traffic_monitor"]["dat_path"] == "/old/history_traffic.dat"
    # 曲线段其余键保留、内联 traffic_source 键删除
    assert out["global_speed_limit_curve"] == {"enabled": "true", "interval": "10M", "curves": []}
    assert any("dat_path" in n for n in notes) and any("global_speed_limit_curve.traffic_source" in n for n in notes)


def test_migrate_v4_removes_global_monitor_section():
    cfg = {
        "global_traffic_monitor":
            {
                "enabled": "true",
                "tool_url": "http://127.0.0.1:8099",
                "tool_token_path": "/x/monitor.token",
                "subscribe": "false",
                "notify_cooldown_s": "5M",
                "autostart": "true",
            }
    }
    out, notes = _migrate_v4_to_v5(cfg)
    assert "global_traffic_monitor" not in out
    assert out["traffic_source"]["global_traffic_monitor"] == {"notify_cooldown_s": "5M"}
    for key in ("enabled", "tool_url", "tool_token_path", "subscribe", "autostart"):
        assert any(f"global_traffic_monitor.{key}" in n for n in notes), key
    assert any("notify_cooldown_s -> config.traffic_source" in n for n in notes)


def test_migrate_v4_derives_provider():
    # 旧 gtm 段非空 -> global_traffic_monitor
    out, _ = _migrate_v4_to_v5({"global_traffic_monitor": {"enabled": "true"}})
    assert out["traffic_source"]["provider"] == "global_traffic_monitor"
    # 无 gtm 段(仅曲线内联数据源) -> traffic_monitor
    out, _ = _migrate_v4_to_v5(
        {"global_speed_limit_curve": {
            "traffic_source": [{
                "traffic_monitor": {
                    "dat_path": "/x.dat"
                }
            }]
        }}
    )
    assert out["traffic_source"]["provider"] == "traffic_monitor"
    # 旧 gtm 段存在但空 -> traffic_monitor(「非空」才是切换信号)
    out, _ = _migrate_v4_to_v5({"global_traffic_monitor": {}})
    assert out["traffic_source"]["provider"] == "traffic_monitor"


def test_migrate_v4_notes_per_key():
    cfg = {
        "global_speed_limit_curve": {
            "traffic_source": [{
                "traffic_monitor": {
                    "dat_path": "/old.dat"
                }
            }]
        },
        "global_traffic_monitor": {
            "enabled": "true",
            "notify_cooldown_s": "5M"
        },
    }
    out, notes = _migrate_v4_to_v5(cfg)
    # 被迁/被删的键各一条: 曲线 traffic_source + gtm.enabled + gtm.notify_cooldown_s + gtm 整段 + provider
    assert len(notes) >= 5, notes
    assert all(isinstance(n, str) and n for n in notes)


def test_migrate_v4_is_idempotent():
    cfg = {
        "traffic_source": {
            "provider": "traffic_monitor",
            "traffic_monitor": {
                "dat_path": "/x.dat"
            }
        },
        "global_speed_limit_curve": {
            "curves": [],
            "enabled": "true"
        },
    }
    import copy

    snapshot = copy.deepcopy(cfg)
    out = _migrate_v4_to_v5(cfg)
    assert out == snapshot  # 无副作用(结构不变)
    assert out is cfg


def test_migrate_v4_through_load_config(tmp_path):
    """v4「仅 TM dat_path」旧配置经 load_config 全链路升到 v5: 取数路径与旧行为等价, provider=traffic_monitor"""
    from auto_qb.config import load_config

    probe = {
        "config":
            {
                "schema_version": 4,
                "global_speed_limit_curve":
                    {
                        "traffic_source": [{
                            "traffic_monitor": {
                                "dat_path": "/old/history_traffic.dat"
                            }
                        }],
                        "curves":
                            [
                                {
                                    "curve":
                                        {
                                            "period": "1D",
                                            "upload_curve": [{
                                                "10GiB": {
                                                    "upload_speed_limit": "6MiB/s"
                                                }
                                            }],
                                        }
                                }
                            ],
                    },
            }
    }
    path = Path(tmp_path) / "cfg.yml"
    path.write_text(yaml.safe_dump(probe, allow_unicode=True), encoding="utf-8")
    cfg = load_config(str(path))
    # 无旧 gtm 段 -> provider 推导为 traffic_monitor; 取数路径与旧行为等价(旧 dat_path = /old/history_traffic.dat)
    assert cfg.traffic_source.provider == "traffic_monitor"
    assert cfg.traffic_source.traffic_monitor.dat_path == "/old/history_traffic.dat"
    assert traffic_paths.dat_path(cfg) == "/old/history_traffic.dat"
    # 曲线段不再有 dat_path 字段(结构退休), 其余键保留
    assert not hasattr(cfg.global_speed_limit_curve, "dat_path")
    assert cfg.global_speed_limit_curve.enabled is True


def test_migrate_v4_defensive_shapes_skipped():
    """v4→v5 迁移对畸形曲线内联数据源的保守跳过(255/257/259 三处 isinstance 假弧)

    旧键形状不可控(手改/第三方模板), 迁移只取它认得的形状: traffic_source 非列表整段跳过、
    列表项非字典跳过、traffic_monitor 非字典或 dat_path 空/纯空白跳过 —— 三类都必须静默,
    而键照删(留着会让校验层按未知键拒单, 迁一半的配置启动即失败)。
    """
    # 非列表: 无可取 dat_path, 键照删, 顶层段不建空壳
    out, _ = _migrate_v4_to_v5({"global_speed_limit_curve": {"traffic_source": {"x": 1}}})
    assert "traffic_source" not in out["global_speed_limit_curve"]
    assert "traffic_monitor" not in out["traffic_source"]
    # 列表项非字典 + traffic_monitor 非字典 + dat_path 纯空白: 逐项跳过, 末项可取(多轮迭代)
    out, _ = _migrate_v4_to_v5(
        {
            "global_speed_limit_curve":
                {
                    "traffic_source":
                        [
                            "not-a-dict",
                            {
                                "traffic_monitor": "not-a-dict"
                            },
                            {
                                "traffic_monitor": {
                                    "dat_path": "   "
                                }
                            },
                            {
                                "traffic_monitor": {
                                    "dat_path": "/good.dat"
                                }
                            },
                        ]
                }
        }
    )
    assert out["traffic_source"]["traffic_monitor"]["dat_path"] == "/good.dat"


def test_migrate_v4_keeps_existing_traffic_source_dicts():
    """v4→v5 迁移: 顶层 traffic_source 与其子块已是字典时就地改写, 不重建空壳(279/288/300 假弧)

    过渡期用户可能已手写顶层 traffic_source(带 refresh_interval/enabled 等 v5 键) ——
    `if not isinstance(ts, dict): ts = {}` 的 False 侧必须**保留**这些显式键, 只补
    provider / dat_path / notify_cooldown_s; 子块同理。变异面: 无条件 `ts = {}` 会静默
    清空用户显式配置。
    """
    cfg = {
        "traffic_source":
            {
                "refresh_interval": "15M",
                "enabled": "false",
                "traffic_monitor": {
                    "dat_path": "/keep/tm.dat"
                },
                "global_traffic_monitor": {
                    "tool_dir": "/keep/gtm"
                },
            },
        "global_traffic_monitor": {
            "notify_cooldown_s": "5M"
        },
    }
    out, _ = _migrate_v4_to_v5(cfg)
    ts = out["traffic_source"]
    assert ts["refresh_interval"] == "15M" and ts["enabled"] == "false", "显式 v5 键必须保留"
    assert ts["traffic_monitor"]["dat_path"] == "/keep/tm.dat", "子块 dict 就地改写, 不得清空"
    assert ts["global_traffic_monitor"] == {"tool_dir": "/keep/gtm", "notify_cooldown_s": "5M"}
    assert ts["provider"] == "global_traffic_monitor", "旧 gtm 非空 -> provider 推导"


def test_migrate_v4_with_gtm_section_through_load_config(tmp_path):
    """v4 带旧 gtm 段的配置: provider 推导为 global_traffic_monitor, notify_cooldown_s 迁走"""
    from auto_qb.config import load_config

    probe = {
        "config": {
            "schema_version": 4,
            "global_traffic_monitor": {
                "enabled": "true",
                "notify_cooldown_s": "5M"
            },
        }
    }
    path = Path(tmp_path) / "cfg.yml"
    path.write_text(yaml.safe_dump(probe, allow_unicode=True), encoding="utf-8")
    cfg = load_config(str(path))
    assert cfg.traffic_source.provider == "global_traffic_monitor"
    assert cfg.traffic_source.global_traffic_monitor.notify_cooldown_s == 300.0
    # 旧 gtm 段已从配置面退休(S15), 过渡 stub 字段也随 S17 删除 —— 顶层属性不再存在
    assert not hasattr(cfg, "global_traffic_monitor")
