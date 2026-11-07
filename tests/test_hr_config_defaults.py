"""test_hr_config_defaults 测试计划: hr_check 配置段(v3 15 键口径, 计划 26-09-28-1932 §6/§7 + 26-09-30-0240)

配置是 fail-fast 的第一道闸门: 站点启用(enabled)却没配 hr 段时, 保护会**静默失效**
(check_hr_condition 第一行 `if not self.tracker_conf.hr: return False`), 故必须在配置期拦下。

v3 收敛: 判定语义硬编码(四行判定表), 配置只留「用户身份类」事实 —— 全局 6 键 +
channel 8 键(26-10-14-1241 去端口+跨机: host/port:0/discovery_port/pairing 三新键) +
sites 条目 4 键(enabled/tracker/refresh_interval/idle_refresh_interval,
末者为稳态降频间隔, 计划 26-10-05-0555 S1, 拍板默认 24H 默认启用)。旧 v2 键 26 个由
config v2→v3 迁移(config/migrations.py)一次性删除或改名, 无常驻兼容层。绑定机制不变
(26-09-27-1930 映射制): 默认绑定 = 档案已知 announce 域在用户 domains 查表, 未命中/歧义
用显式键 `tracker` 直取; 页面事实五键(含 listing)一律由档案填充。

## 测试计划(每个测试函数一条)
- test_defaults_when_absent: 整段缺省 -> 全默认(功能关闭), 不报错
- test_global_section_parsed: 全局段解析(时间串 -> 秒 / channel 子段)
- test_reuse_window_default_and_parsed: 数据复用窗(26-09-30-0240)默认 2H / 自定义时间串解析
- test_reuse_window_range: 复用窗边界 —— 60s 下限与 7d 上限, 之外报错
- test_sites_entry_parsed: sites 条目解析 + 绑定派生(三键来自配置 / 页面事实来自档案 / tracker 回填)
- test_idle_refresh_interval_default_and_parsed: 稳态降频间隔(26-10-05-0555 S1)缺省 24H / 自定义解析 / 派生视图透传
- test_idle_refresh_interval_below_refresh_errors: 交叉校验 —— idle < refresh 报「降频不能比常态还快」
- test_idle_refresh_interval_cross_check_uses_defaults: 交叉校验按缺省补齐比较 —— refresh 配 >24H 而未配 idle 照样报错
- test_idle_refresh_interval_range: 60s 下限 / 30d 上限(与 refresh_interval 同款口径), 之外报错
- test_idle_refresh_interval_equal_to_refresh_valid: idle == refresh 合法(等效关闭降频)
- test_page_url_derived_from_web_domain: HR 页地址恒为档案 web 域派生, 与用户 domains 写法无关
- test_unknown_keys_aggregated: hr_check / channel / sites 条目的未知键一次性报错
- test_ranges_and_formats: 间隔下限 / 日额范围 / 页上限 / 时间窗格式聚合报错
- test_channel_extension_id_format: extension_id 只接受 32 位 a~p
- test_channel_request_timeout_range: request_timeout 上下限
- test_config_error_message_points_to_section: 校验失败经 ConfigError 抛出, 消息里带具体路径
- test_channel_partial_section_uses_channel_defaults: hr_check.channel 给了字典但缺键 -> 缺的键走 HrChannelConfig 字段默认(而非 None)
- test_hr_check_range_endpoints: 频控三键闭区间**端点逐值** —— min_interval [5s,1D] 与日额/页上限 [1,100000] 的两端合法 + 端点外一档非法(旧用例只喂 1S/10/1.5)
- test_hr_check_request_timeout_endpoints: channel.request_timeout [5s,3600s] 两端逐值(旧用例只给了 1S/2H 两个远离端点的非法值)
- test_hr_site_interval_range_endpoints: sites 条目 refresh/idle 两键 [60s,30D] 的**未覆盖半边**; 并改用「完整路径+精确下限文案」断言(既有用例的 `须 >=` 松匹配被交叉校验文案顶替 = 假绿)
- test_hr_site_confs_derivation_single_point: 守阵(issue hr-site-derive-convention-dup) 站点接入派生单点在 Config.hr_site_confs —— 推导全仓只许出现在 models.py 与 routes/hr.py(webui 半, 轮 15 合流)
- test_loaders_non_dict_specs_return_defaults: loader 层「段形状非字典」早退(load_hr_check_config/load_site_hr_check_config/load_fs_config/load_relocate_config —— 校验层已拦, loader 仍保守回默认而非 AttributeError)
- test_channel_host_literal_only: channel.host 只认 IPv4/IPv6 字面量与 localhost —— 空/None 报「不能为空」, localhost 大小写与两族字面量放行, 主机名(含 .local 后缀)报「须为 IPv4/IPv6 字面量」
- test_channel_pairing_enum_and_token_type: pairing 取值域 auto/on/off(非法值报错并列出可选值, 大小写不敏感) + token 非字符串报错(类型错会让密钥比对静默失效)
- test_channel_port_collision_with_discovery: port 与 discovery_port 相同报「两端口不能相同」(现产 port:18788 撞默认 discovery 18788 的形态); 任一侧 0(随机)不判撞
- test_channel_lan_off_without_token_rejected: ⑤ 非回环 + pairing=off + 无 token 必须拦(V4); 配 token / 回环 / pairing=auto 三档放行
- test_channel_discovery_port_ephemeral_warns_not_blocks: ⑥ discovery_port 落入 OS 临时端口段只告警不阻断(V12); 段值按平台取(Windows 49152-65535 / 类 Unix 32768-60999), dport=0 整段跳过
- test_channel_token_ascii_only: token 含非 ASCII 字符报「ASCII」错(常数时间密钥比较要求两侧均为 ASCII, 非 ASCII 密钥旧校验放行、运行期逐请求 TypeError 兜 500 —— 必须配置期拦下); 纯 ASCII 放行, 非字符串仍报「必须是字符串」
"""

import logging

import os

import pytest

import yaml

from auto_qb.config import ConfigError, load_config

from auto_qb.config.impact import diff_config_impacts, restart_required_paths

from auto_qb.config.migrations import _migrate_config_1_2, _migrate_config_2_3

from auto_qb.config.models import Config

from auto_qb.config.validation import validate_config

from hr_config_support import (
    _bts_site,
    _validate,
    _write,
)


def test_defaults_when_absent(tmp_path):
    """整段缺省 -> 全默认(功能关闭), 不报错"""
    cfg = load_config(_write(tmp_path, {"trackers": {"s": {"domains": ["a.example"]}}}))
    assert cfg.hr_check.enabled is False
    assert cfg.hr_check.min_interval == 90.0
    assert cfg.hr_check.max_requests_per_day == 240
    assert cfg.hr_check.max_pages_per_wave == 30
    assert cfg.hr_check.allow_window == ""
    assert cfg.hr_check.shared_dir == ""
    assert cfg.hr_check.reuse_window == 2 * 3600.0
    assert cfg.hr_check.channel.enabled is False
    assert cfg.hr_check.channel.host == "127.0.0.1"
    assert cfg.hr_check.channel.port == 0, "去端口(计划 26-10-14-1241): 默认交 OS 随机"
    assert cfg.hr_check.channel.discovery_port == 18788
    assert cfg.hr_check.channel.pairing == "auto"
    assert cfg.hr_check.sites == {}
    assert cfg.trackers["s"].hr_check is None


def test_global_section_parsed(tmp_path):
    """全局段解析: 时间串 -> 秒 / channel 子段"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check":
                    {
                        "enabled": "true",
                        "min_interval": "2M",
                        "max_requests_per_day": "300",
                        "max_pages_per_wave": "40",
                        "allow_window": "01:00-06:00",
                        "shared_dir": "//nas/share",
                        "reuse_window": "3H",
                        "channel":
                            {
                                "enabled": "true",
                                "port": "8899",
                                "token": "abc",
                                "extension_id": "a" * 32,
                                "request_timeout": "90S",
                            },
                    },
            }
        )
    )
    hr_check = cfg.hr_check
    assert hr_check.enabled is True
    assert hr_check.min_interval == 120.0
    assert hr_check.max_requests_per_day == 300
    assert hr_check.max_pages_per_wave == 40
    assert hr_check.allow_window == "01:00-06:00"
    assert hr_check.shared_dir == "//nas/share"
    assert hr_check.reuse_window == 3 * 3600.0
    assert (hr_check.channel.enabled, hr_check.channel.port, hr_check.channel.token) == (True, 8899, "abc")
    assert hr_check.channel.extension_id == "a" * 32
    assert hr_check.channel.request_timeout == 90.0


def test_sites_entry_parsed(tmp_path):
    """sites 条目解析 + 绑定派生: 三键来自配置, 页面事实五键(含 listing)来自档案"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check":
                    {
                        "enabled": "true",
                        "sites": {
                            "btschool": {
                                "enabled": "true",
                                "refresh_interval": "6H",
                            }
                        },
                    },
                "trackers": {
                    "btschool": _bts_site()
                },
            }
        )
    )
    site = cfg.trackers["btschool"].hr_check
    assert site is not None
    assert site.enabled is True
    assert site.refresh_interval == 6 * 3600.0
    # 页面事实: 配置里根本没写, 全部由内置档案填充
    assert site.adapter == "btschool"  # 标准 myhr 表格 + 页头 H&R 计数(M2 起, 见 adapters/btschool.py)
    assert site.hr_page_url == "https://pt.btschool.club/myhr.php"
    assert site.download_path == "/download.php?id={id}"
    assert site.page_param == "page"
    assert site.listing == "list"
    # 超额线判据从绑定站点的 hr 规则派生(required + extra)
    assert site.required_seeding_time == 3 * 86400.0
    # 派生视图的 tracker 字段回填解析出的条目名(默认映射命中)
    assert site.tracker == "btschool"
    # 配置真相在 hr_check.sites, trackers.*.hr_check 只是派生视图
    assert set(cfg.hr_check.sites) == {"btschool"}
    assert cfg.hr_check.sites["btschool"].tracker == ""

    # required_seeding_time 派生含 extra
    cfg2 = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "enabled": "true"
                        }
                    }
                },
                "trackers":
                    {
                        "btschool":
                            {
                                "domains": ["pt.btschool.club"],
                                "hr": {
                                    "required_seeding_time": "3D",
                                    "extra_seeding_time": "1D"
                                }
                            }
                    },
            }
        )
    )
    assert cfg2.trackers["btschool"].hr_check.required_seeding_time == 4 * 86400.0


def test_page_url_derived_from_web_domain(tmp_path):
    """HR 页地址 = https://{档案 web_domain}{page_path}, 与用户 domains 写法完全无关"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "enabled": "true"
                        }
                    }
                },
                "trackers": {
                    "btschool": _bts_site()
                },
            }
        )
    )
    assert cfg.trackers["btschool"].hr_check.hr_page_url == "https://pt.btschool.club/myhr.php"


def test_unknown_keys_aggregated():
    """hr_check / channel / sites 条目的未知键一次性报错(聚合, 不打地鼠)"""
    errors = _validate(
        {
            "hr_check": {
                "typo_key": 1,
                "channel": {
                    "typo_channel": 1
                },
                "sites": {
                    "btschool": {
                        "typo_site": 1
                    }
                },
            },
            "trackers": {
                "btschool": _bts_site()
            },
        }
    )
    joined = "; ".join(errors)
    assert "config.hr_check: 未知键 ['typo_key']" in joined
    assert "config.hr_check.channel" in joined and "typo_channel" in joined
    assert "config.hr_check.sites.btschool: 未知键 ['typo_site']" in joined


def test_ranges_and_formats():
    """间隔下限 / 日额范围 / 页上限 / 时间窗格式聚合报错"""
    errors = _validate(
        {
            "hr_check":
                {
                    "min_interval": "1S",  # 低于 5s 下限
                    "max_requests_per_day": 0,
                    "max_pages_per_wave": -1,
                    "allow_window": "25:00-99:00",
                    "shared_dir": 123,
                },
        }
    )
    joined = "; ".join(errors)
    assert "min_interval" in joined
    assert "max_requests_per_day" in joined
    assert "max_pages_per_wave" in joined
    assert "allow_window" in joined
    assert "shared_dir" in joined


def test_reuse_window_default_and_parsed(tmp_path):
    """数据复用窗(26-09-30-0240): 缺省 2H, 自定义时间串正常解析(节奏归 refresh_interval, 新鲜度归本键)"""
    cfg = load_config(_write(tmp_path, {"hr_check": {"enabled": "true", "reuse_window": "30M"}}))
    assert cfg.hr_check.reuse_window == 30 * 60.0


def test_reuse_window_range():
    """复用窗边界: 60s 下限 / 7d 上限(调大只影响数据新鲜度, 但过大会让陈旧数据长期存活)"""
    assert _validate({"hr_check": {"reuse_window": "1M"}}) == []
    assert _validate({"hr_check": {"reuse_window": "7D"}}) == []
    for bad in ("59S", "7D1S", "8D"):
        errors = _validate({"hr_check": {"reuse_window": bad}})
        assert any("reuse_window" in e for e in errors), (bad, errors)


def test_idle_refresh_interval_default_and_parsed(tmp_path):
    """稳态降频间隔(26-10-05-0555 S1): 缺省 24H(拍板默认启用降频), 自定义时间串解析, 派生视图透传"""
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "enabled": "true"
                        }
                    }
                },
                "trackers": {
                    "btschool": _bts_site()
                },
            }
        )
    )
    assert cfg.hr_check.sites["btschool"].idle_refresh_interval == 24 * 3600.0
    # 派生视图(trackers.*.hr_check)同值透传, 下游只读派生视图
    assert cfg.trackers["btschool"].hr_check.idle_refresh_interval == 24 * 3600.0

    cfg2 = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "sites": {
                        "btschool": {
                            "enabled": "true",
                            "idle_refresh_interval": "2D",
                        }
                    }
                },
                "trackers": {
                    "btschool": _bts_site()
                },
            }
        )
    )
    assert cfg2.hr_check.sites["btschool"].idle_refresh_interval == 2 * 86400.0
    assert cfg2.trackers["btschool"].hr_check.idle_refresh_interval == 2 * 86400.0


def test_idle_refresh_interval_below_refresh_errors():
    """交叉校验(26-10-05-0555 S1): idle < refresh 报「降频不能比常态还快」; 互换后合法"""
    errors = _validate(
        {"hr_check": {
            "sites": {
                "btschool": {
                    "idle_refresh_interval": "6H",
                    "refresh_interval": "12H"
                }
            }
        }}
    )
    assert any("idle_refresh_interval" in e and "降频不能比常态还快" in e for e in errors), errors
    assert _validate({"hr_check": {
        "sites": {
            "btschool": {
                "idle_refresh_interval": "12H",
                "refresh_interval": "6H"
            }
        }
    }}) == []


def test_idle_refresh_interval_cross_check_uses_defaults():
    """交叉校验按缺省补齐比较(26-10-05-0555 S1): refresh 配 >24H 而未配 idle(有效 idle = 默认 24H)照样报错;
    反之 idle 配 >24H 而 refresh 缺省(12H)合法"""
    errors = _validate({"hr_check": {"sites": {"btschool": {"refresh_interval": "25H"}}}})
    assert any("降频不能比常态还快" in e for e in errors), errors
    assert _validate({"hr_check": {"sites": {"btschool": {"idle_refresh_interval": "25H"}}}}) == []


def test_idle_refresh_interval_range():
    """idle_refresh_interval 边界: 60s 下限 / 30d 上限(与 refresh_interval 同款口径), 之外报错"""
    # 边界内合法(与 refresh 同值配对, 避免踩缺省补齐的交叉校验)
    assert _validate(
        {"hr_check": {
            "sites": {
                "btschool": {
                    "idle_refresh_interval": "60S",
                    "refresh_interval": "60S"
                }
            }
        }}
    ) == []
    assert _validate(
        {"hr_check": {
            "sites": {
                "btschool": {
                    "idle_refresh_interval": "30D",
                    "refresh_interval": "30D"
                }
            }
        }}
    ) == []
    for bad in ("59S", "30D1S", "31D"):
        errors = _validate({"hr_check": {"sites": {"btschool": {"idle_refresh_interval": bad}}}})
        assert any("idle_refresh_interval" in e and ("须 >=" in e or "须 <=" in e or "无效时间格式" in e)
                   for e in errors), (bad, errors)


def test_idle_refresh_interval_equal_to_refresh_valid():
    """idle == refresh 合法(拍板口径: 相等 = 等效关闭降频)"""
    errors = _validate(
        {"hr_check": {
            "sites": {
                "btschool": {
                    "idle_refresh_interval": "12H",
                    "refresh_interval": "12H"
                }
            }
        }}
    )
    assert errors == [], errors


def test_channel_extension_id_format():
    """extension_id 只接受 32 位 a~p(形态错 = 写了也不会生效, 必须配置期拦下)"""
    errors = _validate({"hr_check": {"channel": {"extension_id": "z" * 32}}})
    assert any("32 位 Chrome 扩展 id" in e for e in errors), errors
    assert _validate({"hr_check": {"channel": {"extension_id": "a" * 32}}}) == []


def test_channel_request_timeout_range():
    """request_timeout 上下限(太短误杀正常取数 / 太长挂死取数线程)"""
    errors = _validate({"hr_check": {"channel": {"request_timeout": "1S"}}})
    assert any("request_timeout" in e for e in errors), errors
    errors = _validate({"hr_check": {"channel": {"request_timeout": "2H"}}})
    assert any("request_timeout" in e for e in errors), errors


def test_channel_host_literal_only():
    """channel.host 只认 IPv4/IPv6 字面量与 localhost(S1 ①): 空/None -> 报「不能为空」;
    localhost(大小写不敏感)与两族字面量放行; 主机名(含 .local 后缀)报错 —— 扩展侧 normalize
    按字面量判私网段, 主机名无法分类(NAS 部署请直接填内网 IP)"""
    assert any("不能为空" in e for e in _validate({"hr_check": {"channel": {"host": "   "}}}))
    assert any("不能为空" in e for e in _validate({"hr_check": {"channel": {"host": None}}}))
    assert _validate({"hr_check": {"channel": {"host": "localhost"}}}) == []
    assert _validate({"hr_check": {"channel": {"host": "LOCALHOST"}}}) == []
    assert _validate({"hr_check": {"channel": {"host": "192.168.1.5"}}}) == []
    assert _validate({"hr_check": {"channel": {"host": "::1"}}}) == []
    errors = _validate({"hr_check": {"channel": {"host": "nas.local"}}})
    assert any("须为 IPv4/IPv6 字面量或 localhost" in e and "nas.local" in e for e in errors), errors


def test_channel_pairing_enum_and_token_type():
    """pairing 取值域 auto/on/off(计划 §04 S3): 非法值报错并列出可选值, 大小写不敏感;
    token 非字符串报错(类型错会让密钥比对静默失效, 必须配置期拦下)"""
    errors = _validate({"hr_check": {"channel": {"pairing": "always"}}})
    assert any("取值非法" in e and "auto/on/off" in e for e in errors), errors
    assert _validate({"hr_check": {"channel": {"pairing": "OFF"}}}) == []
    errors = _validate({"hr_check": {"channel": {"token": 123}}})
    assert any("config.hr_check.channel.token: 必须是字符串" in e for e in errors), errors
    assert _validate({"hr_check": {"channel": {"token": "abc"}}}) == []


def test_channel_token_ascii_only():
    """token 字符集限 ASCII: 含非 ASCII 字符报错并聚合(issue 26-11-07-0527 #1)

    常数时间密钥比较的 str 形态要求两侧均为 ASCII, 非 ASCII 密钥(如中文)能过旧
    「必须是字符串」校验, 运行期每个请求在鉴权处抛 TypeError 被兜成 500, 通道整体
    不可用 —— 必须在配置期拦下; 纯 ASCII 放行, 非字符串仍走「必须是字符串」不串档。
    """
    errors = _validate({"hr_check": {"channel": {"token": "密钥"}}})
    assert any("config.hr_check.channel.token" in e and "ASCII" in e for e in errors), errors
    errors = _validate({"hr_check": {"channel": {"token": "ok中"}}})
    assert any("config.hr_check.channel.token" in e and "ASCII" in e for e in errors), errors
    assert _validate({"hr_check": {"channel": {"token": "plain-KEY_42"}}}) == []
    errors = _validate({"hr_check": {"channel": {"token": 123}}})
    assert any("config.hr_check.channel.token: 必须是字符串" in e for e in errors), errors
    assert not any("ASCII" in e for e in errors), "非字符串不串档到字符集报错"


def test_channel_port_collision_with_discovery():
    """③ port 与 discovery_port 相同 -> 报「两端口不能相同」(计划 §01 派生口径 + §08 迁移:
    现产 port:18788 撞默认 discovery 18788 即此形态); 任一侧 0(交 OS 随机)不判撞"""
    errors = _validate({"hr_check": {"channel": {"port": 18788, "discovery_port": 18788}}})
    assert any("两端口不能相同" in e and "18788" in e for e in errors), errors
    assert _validate({"hr_check": {"channel": {"port": 18788, "discovery_port": 18888}}}) == []
    # dport=0: ⑥ 的临时端口段判定整段跳过(`if dport_v:` 假弧), 不误报
    assert _validate({"hr_check": {"channel": {"port": 0, "discovery_port": 0}}}) == []


def test_channel_lan_off_without_token_rejected():
    """⑤ 非回环 + pairing=off + 未配 token = LAN 上无人工关口的密钥分发器, 一道都不许少(V4);
    配了 token / host 回环 / pairing=auto 三档均放行"""
    errors = _validate({"hr_check": {"channel": {"host": "192.168.1.5", "pairing": "off"}}})
    assert any("非回环且 pairing=off 且未配置 token" in e for e in errors), errors
    assert _validate({"hr_check": {"channel": {"host": "192.168.1.5", "pairing": "off", "token": "k"}}}) == []
    assert _validate({"hr_check": {"channel": {"host": "127.0.0.1", "pairing": "off"}}}) == []
    assert _validate({"hr_check": {"channel": {"host": "192.168.1.5", "pairing": "auto"}}}) == []


def test_channel_discovery_port_ephemeral_warns_not_blocks(monkeypatch):
    """⑥ discovery_port 落入 OS 临时端口段 -> 告警不阻断(V12; 默认 18788 在段外);
    段值按平台取: Windows 49152-65535 / 类 Unix 32768-60999"""
    from auto_qb.config.validation import sections as v_sections

    monkeypatch.setattr(v_sections.sys, "platform", "win32")
    assert v_sections._channel_ephemeral_port_range() == (49152, 65535)
    monkeypatch.setattr(v_sections.sys, "platform", "linux")
    assert v_sections._channel_ephemeral_port_range() == (32768, 60999)

    records = []

    class _Rec(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    lg = logging.getLogger("auto_qb.config.validation.sections")
    handler = _Rec()
    handler.setLevel(logging.DEBUG)
    old_level = lg.level
    lg.setLevel(logging.DEBUG)
    lg.addHandler(handler)
    try:
        assert _validate({"hr_check": {"channel": {"discovery_port": 50000}}}) == [], "告警不阻断"
        assert any("临时端口段" in m for m in records), records
        records.clear()
        assert _validate({"hr_check": {"channel": {"discovery_port": 18788}}}) == []
        assert records == [], "默认 18788 在段外, 不该告警"
    finally:
        lg.removeHandler(handler)
        lg.setLevel(old_level)


def test_config_error_message_points_to_section(tmp_path):
    """校验失败经 ConfigError 抛出, 消息里带具体路径"""
    path = _write(tmp_path, {"hr_check": {"min_interval": "1S"}})
    with pytest.raises(ConfigError) as ei:
        load_config(path)
    assert "hr_check.min_interval" in str(ei.value)


def test_channel_partial_section_uses_channel_defaults(tmp_path):
    """hr_check.channel 给了字典但缺键 -> 缺的键走 HrChannelConfig 字段默认(而非 None)

    变异面: `_get(channel_spec, KEY, channel_default.<field>)` 的默认值换成 None。整段缺省走
    的是「非字典 -> 用 channel_default 实例」那条路(已被 test_defaults_when_absent 钉住),
    「字典在但键缺」这条分支没有用例 —— 端口/超时变 None 不会报错, 只在运行时才炸。
    """
    cfg = load_config(
        _write(
            tmp_path, {
                "hr_check": {
                    "channel": {
                        "token": "tok-abc"
                    }
                },
                "trackers": {
                    "s": {
                        "domains": ["a.example"]
                    }
                },
            }
        )
    )
    ch = cfg.hr_check.channel
    assert ch.token == "tok-abc"  # 显式给的键照常解析
    assert ch.enabled is False  # 保守默认
    assert ch.host == "127.0.0.1"
    assert ch.port == 0
    assert ch.discovery_port == 18788
    assert ch.pairing == "auto"
    assert ch.extension_id == ""
    assert ch.request_timeout == 180.0

    # 反面对照: 只给 port -> 缺的 token 必须落字段默认 ""(而不是 None)
    cfg2 = load_config(
        _write(tmp_path, {
            "hr_check": {
                "channel": {
                    "port": "8899"
                }
            },
            "trackers": {
                "s": {
                    "domains": ["a.example"]
                }
            },
        })
    )
    assert cfg2.hr_check.channel.port == 8899
    assert cfg2.hr_check.channel.token == ""
    assert cfg2.hr_check.channel.extension_id == ""


def test_hr_check_range_endpoints():
    """hr_check 频控三键的闭区间**端点逐值** —— 池内旧用例只喂 1S / 10 / 1.5 这类远离边界的值

    - min_interval [5s, 1D]: 5S 与 1D 合法, 4S 与 86401S 非法
    - max_requests_per_day / max_pages_per_wave [1, 100000]: 1 与 100000 合法, 0 与 100001 非法
      (上界端点 100000 此前没喂过 —— `max=100000` -> `99999` 会让合法配置变非法而全绿)
    """
    def err(**kv) -> str:
        return "; ".join(_validate({"hr_check": kv}))

    # --- min_interval 两端
    assert err(min_interval="5S") == ""
    assert err(min_interval="1D") == ""
    assert "config.hr_check.min_interval: 须 >= 5s" in err(min_interval="4S")
    assert "config.hr_check.min_interval: 须 <= 86400s" in err(min_interval="86401S")
    # --- 日额与页上限两端(同款 `_try_number(integer=True, min=1, max=100000)` 判据)
    for key in ("max_requests_per_day", "max_pages_per_wave"):
        assert err(**{key: 1}) == "", key
        assert err(**{key: 100000}) == "", key
        assert f"config.hr_check.{key}(须为正整数): 须 >= 1" in err(**{key: 0}), key
        assert f"config.hr_check.{key}(须为正整数): 须 <= 100000" in err(**{key: 100001}), key


def test_hr_check_request_timeout_endpoints():
    """channel.request_timeout 闭区间 [5s, 3600s] 端点逐值

    既有用例只给了 1S(低于下限)与 2H(高于上限)两个**远离端点**的非法值: 端点本身(5S / 3600S)
    与「端点外一档」(4S / 3601S)都没喂过, 故 `min_s=5` -> `6` 或 `max_s=3600` -> `3599` 全绿。
    """
    def err(v) -> str:
        return "; ".join(_validate({"hr_check": {"channel": {"request_timeout": v}}}))

    assert err("5S") == ""
    assert err("3600S") == ""
    assert "config.hr_check.channel.request_timeout: 须 >= 5s" in err("4S")
    assert "config.hr_check.channel.request_timeout: 须 <= 3600s" in err("3601S")


def test_hr_site_interval_range_endpoints():
    """sites.<档案>.refresh_interval / idle_refresh_interval 闭区间 [60s, 30D] 的**未覆盖半边**

    两处判据缺口:
    - refresh 一侧此前**完全没喂过**越界值(既有 `test_idle_refresh_interval_range` 的 bad 列表只写
      `idle_refresh_interval`), 故 refresh 的 `min_s=60` -> `59` 与 `max_s=30*86400` -> `31*86400` 全存活;
    - 既有用例用 `"须 >=" in e` 这种松匹配断言 idle 的 59S, 而**交叉校验文案里也带「须 >= 拉取间隔(...)」**
      ⇒ 该断言被交叉校验顶替, 是**假绿**(实测 idle 下界 -1 的变异因此存活)。本用例按
      「完整路径 + 精确下限文案」断言。
    """
    def err(entry: dict) -> str:
        return "; ".join(_validate({"hr_check": {"sites": {"btschool": entry}}}))

    w = "config.hr_check.sites.btschool"
    # --- refresh 下界外一档 59S(idle 缺省 24H >= 59S, 不触发交叉校验, 单断言即命中)
    assert f"{w}.refresh_interval: 须 >= 60s" in err({"refresh_interval": "59S"})
    # --- refresh 上界: 须与 idle 同值配对, 否则交叉校验的报错会混进来干扰归因
    assert f"{w}.refresh_interval: 须 <= 2592000s" in err({"refresh_interval": "31D", "idle_refresh_interval": "31D"})
    # --- 两端端点合法(同值配对 => 相等 = 等效关闭降频, 不报交叉校验)
    assert err({"refresh_interval": "60S", "idle_refresh_interval": "60S"}) == ""
    assert err({"refresh_interval": "30D", "idle_refresh_interval": "30D"}) == ""
    # --- idle 下界外一档 59S: 精确文案(松匹配被交叉校验顶替过的那一处)
    assert f"{w}.idle_refresh_interval: 须 >= 60s" in err({"idle_refresh_interval": "59S"})


def test_hr_site_confs_derivation_single_point():
    """守阵(issue hr-site-derive-convention-dup): 「哪些站点接入 hr_check」派生单点在 Config.hr_site_confs

    此前 hr/runtime.site_confs 与 hr/report._site_confs 各抄一份逐字同推导。静态:
    `hr_check is not None` 全仓只允许出现在 config/models.py(单点本体)与
    webui/server/routes/hr.py(webui 半 —— 归轮 15 合流, 合流改走单点后从白名单移除)。
    行为: 全默认 Config 派生空表(无站点接入)。
    红验: 任何第三处重抄推导(哪怕换变量名)即红; runtime/report 改回自写同红。
    """
    from pathlib import Path

    from auto_qb.config.models import Config

    root = Path(__file__).resolve().parents[1] / "src" / "auto_qb"
    hits = sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*.py") if "hr_check is not None" in p.read_text(encoding="utf-8")
    )
    assert hits == ["config/models.py", "webui/server/routes/hr.py"], (f"站点接入派生只允许在单点与 webui 半(轮 15 合流), 现分布: {hits}")
    assert Config().hr_site_confs() == {}, "全默认配置应派生空表"


def test_loaders_non_dict_specs_return_defaults():
    """四个 loader 的非字典段早退: 喂 None / 标量 / 列表 -> 恒回字段默认, 不 AttributeError

    变异面: `if not isinstance(spec, dict): return d` 整行删掉 -> `spec.get(...)` 对非字典
    直接抛(load_config 路径上不可达, 但 loader 是公开半, 单测钉住保守回退)。
    """
    from auto_qb.config.loaders import (
        load_fs_config,
        load_hr_check_config,
        load_relocate_config,
        load_site_hr_check_config,
    )
    from auto_qb.config.models import FsConfig, HrCheckConfig, RelocateConfig, SiteHrCheckConfig

    for bad in (None, "", 1, [], 3.5):
        assert load_hr_check_config(bad) == HrCheckConfig(), bad
        assert load_site_hr_check_config(bad) == SiteHrCheckConfig(), bad
        assert load_fs_config(bad) == FsConfig(), bad
        assert load_relocate_config(bad) == RelocateConfig(), bad
