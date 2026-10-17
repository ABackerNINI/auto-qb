"""config schema 迁移函数(计划 26-09-26-0506 版本链; 首个 config 生产迁移 = v1→v2, 计划 26-09-27-1930)

迁移是版本链上的一次性纯函数变换, 不是常驻兼容层: 旧结构 trackers.<名>.hr_check 在这里被翻成
新结构 hr_check.sites.<档案 id> 后即不存在, 程序其余部分(loader/校验)不再有任何伺候旧键的分支。
import 即注册(auto_qb.config.__init__ 导入本模块), 早于任何 load_config; infra 的版本表只抬号,
迁移函数需要 SITE_PRESETS 做档案定位, 依赖纪律决定它落 config 层而非 infra。

改写规则(计划 26-09-27-1930 §3.4), 对每个 trackers.<名>.hr_check:
- mode=off 或非字典 -> 直接删除(新口径下 off = 键不存在);
- mode != off 且 hr_page_url 的 host(web 命名空间)按 preset_for_web_host 定位到档案 ->
  在 hr_check.sites.<档案 id> 建/并入条目(搬 mode 与微调项; 页面事实四键
  adapter/hr_page_url/download_path/page_param 丢弃 —— 值一律以档案为准), 然后删除旧键;
  新旧并存时新位置获胜;
- 定位不到档案(缺 hr_page_url / host 陌生) -> 旧键原地保留, 交给校验层报废除错。

schema_version 盖章由 infra.versioning.migrate 框架统一负责, 函数体不碰版本字段。

v3→v4(report 26-10-03-0504 方案 B 阶段 1, 「删除类似标签」全局/站点作用域混淆修复): v4 起站点段
4 个 str 输出键(hr.add_tag / add_category / add_tag_for_satisfied / add_category_for_satisfied)的
显式空串语义翻转为「覆盖为空」(_strip_none 不再剥)。v3 及更早里这些 '' 写了也白写(= 未配置),
为让升级语义不变, 迁移把 9 键作用域内的显式置空值整体移除 —— 站点 4 个 str 键是语义翻转保护,
其余(全局段同名键 / bool / list 键的 '', 本就被 strip 剥成未配置)属死值顺手清理。每个被移除键的
路径经 (dict, notes) 返回形态交 migrate_with_notes, 由 loaders.migrate_config_schema 逐键打 WARNING。

v4→v5(计划 26-10-17-0339 S15, 全局流量来源合并): 曲线段内联数据源 + 顶层 global_traffic_monitor
段合并为顶层 traffic_source 段; 每键迁移/删除产出一条 note(见 _migrate_config_4_5)。
"""
from typing import Dict, List, Tuple
from urllib.parse import urlparse

from ..infra.versioning import MIGRATIONS
from . import site_presets
from .schema.trackers import HR_OUTPUT_FIELDS

#: 随迁的微调项(旧键 -> sites 条目同键名直搬); 页面事实四键一律丢弃
_MIGRATE_TUNING_KEYS = (
    "hr_page_scopes", "refresh_interval", "max_pages_per_refresh", "completed_age_limit", "max_torrents_per_hour"
)


def _url_host(url) -> str:
    """取 URL 的 host(小写); 缺失/非串/解析失败返回空串(定位不到档案, 旧键原地保留)"""
    if not isinstance(url, str):
        return ""
    try:
        return (urlparse(url).hostname or "").strip().lower()
    except ValueError:
        return ""


def _migrate_config_1_2(cfg: dict) -> dict:
    """v1→v2: 旧键 trackers.<名>.hr_check 一次性改写到 hr_check.sites.<档案 id>(映射制绑定)"""
    trackers = cfg.get("trackers")
    if not isinstance(trackers, dict):
        return cfg
    for tdata in trackers.values():
        if not isinstance(tdata, dict) or "hr_check" not in tdata:
            continue
        legacy = tdata["hr_check"]
        if not isinstance(legacy, dict):
            del tdata["hr_check"]  # 形状烂到读不出 mode: 无处可迁, 直接删除
            continue
        mode = str(legacy.get("mode", "off")).strip().lower()
        if mode == "off":
            del tdata["hr_check"]  # 新口径下 off = 键不存在
            continue
        preset = site_presets.preset_for_web_host(_url_host(legacy.get("hr_page_url")))
        if preset is None:
            continue  # 定位不到档案: 原地保留, 校验层报废除错(指引到 hr_check.sites 重配)
        hr_check = cfg.get("hr_check")
        if not isinstance(hr_check, dict):
            hr_check = {}
            cfg["hr_check"] = hr_check
        sites = hr_check.get("sites")
        if not isinstance(sites, dict):
            sites = {}
            hr_check["sites"] = sites
        if preset.preset_id not in sites:  # 新旧并存: 新位置获胜, 旧键只是丢弃
            entry: Dict[str, object] = {"mode": mode}
            entry.update({key: legacy[key] for key in _MIGRATE_TUNING_KEYS if key in legacy})
            sites[preset.preset_id] = entry
        del tdata["hr_check"]
    return cfg


# import 即注册(见模块 docstring); 注册表缺位 = 版本表与迁移表不同步, migrate() 会 fail-fast
MIGRATIONS["config"][1] = _migrate_config_1_2

#: v2→v3 删除的全局段键(计划 26-09-28-1932 §6.2 废弃键去向表; min_torrent_interval 改名保留)
_V3_DROP_GLOBAL_KEYS = (
    "max_torrents_per_hour",
    "max_torrents_per_day",
    "page_rate_per_hour",
    "page_burst",
    "torrent_rate_per_hour",
    "torrent_burst",
    "max_pages_per_day",
    "min_page_interval",
    "quota_model",
    "failure_threshold",
    "failure_cooldown",
    "unknown_policy",
    "verified_ttl",
    "index_retention",
    "max_download_retries",
    "channel_silence_warn",
    "lock_timeout",
    "poll_interval",
    "parse_missing_rate_max",
    "max_pages_per_round",
)


def _migrate_config_2_3(cfg: dict) -> dict:
    """v2→v3: HR 14 键口径(计划 26-09-28-1932 §6/§7.1)。

    - 全局段: 删除 26 个废弃键; min_torrent_interval 改名 min_interval(语义接管页面间隔)。
    - sites 条目: mode partial/all → enabled: true, mode off 条目整体删除; 无 mode 但带
      enabled 的条目(v1 章缺失的新写法)原样保留 enabled —— 迁移是版本链上的一次性变换,
      但「缺版本章 = 按 v1 处理」的存量口径意味着新写法也会走到这里, 不能误杀。
      tracker / refresh_interval / idle_refresh_interval 原样保留(末者 v4 期新增键
      计划 26-10-05-0555 S1: 非破坏变更刻意不抬版本, 无章新写法沿本迁移经过时不得丢键)。
    - trackers.*.hr_check 残留直接删除(v2 迁移已收敛过一轮, 不再提供旧位置兼容)。
    """
    hr = cfg.get("hr_check")
    if isinstance(hr, dict):
        if "min_torrent_interval" in hr:
            hr.setdefault("min_interval", hr["min_torrent_interval"])
            del hr["min_torrent_interval"]
        for key in _V3_DROP_GLOBAL_KEYS:
            hr.pop(key, None)
        sites = hr.get("sites")
        if isinstance(sites, dict):
            for preset_id, entry in list(sites.items()):
                new_entry: Dict[str, object] = {}
                if isinstance(entry, dict):
                    mode = str(entry.get("mode", "")).strip().lower()
                    if "enabled" in entry:
                        new_entry["enabled"] = entry["enabled"]  # 已是新口径: 原样保留(loader 再 parse)
                    elif mode in ("partial", "all"):
                        new_entry["enabled"] = True
                    if entry.get("tracker"):
                        new_entry["tracker"] = entry["tracker"]
                    if "refresh_interval" in entry:
                        new_entry["refresh_interval"] = entry["refresh_interval"]
                    if "idle_refresh_interval" in entry:
                        new_entry["idle_refresh_interval"] = entry["idle_refresh_interval"]
                if new_entry:
                    sites[preset_id] = new_entry
                else:
                    del sites[preset_id]
    trackers = cfg.get("trackers")
    if isinstance(trackers, dict):
        for tdata in trackers.values():
            if isinstance(tdata, dict):
                tdata.pop("hr_check", None)
    return cfg


MIGRATIONS["config"][2] = _migrate_config_2_3

# ---- v3→v4: 9 键作用域内显式置空值移除(report 26-10-03-0504 方案 B 阶段 1) ----

#: 9 键作用域内全局/站点 hr 段共用的输出键(tri_state 4 str + overwrite 2 bool + exclude 2 list);
#: 键清单单一事实来源 = schema 的 HR_OUTPUT_FIELDS(与 validation 的 KNOWN_HR_KEYS 同面, 有守卫)
_HR_OUTPUT_KEYS: Tuple[str, ...] = tuple(f.key for f in HR_OUTPUT_FIELDS)

#: 「显式置空已移除」的统一指引(WARNING 文案单点, 用户拍板口径)
_EMPTY_REMOVED_HINT = "显式置空已移除, 语义为使用默认值; 如需覆盖为空请重新显式配置"


def _collect_explicit_empty_paths(cfg: dict) -> List[str]:
    """收集 9 键作用域内显式置空('')的键路径(纯函数; 迁移移除与 WARNING 明细共用同一清单)

    作用域: config.remove_similar_tags(全局) / config.hr.<8 输出键>(全局) /
    config.trackers.<名>.remove_similar_tags 与 config.trackers.<名>.hr.<8 输出键>(站点)。
    只认标量 ''(BaseLoader 对 `key:` 留空的解析形态); None / 空列表等其它形态不在本迁移范围。
    """
    paths: List[str] = []
    if cfg.get("remove_similar_tags") == "":
        paths.append("config.remove_similar_tags")
    hr = cfg.get("hr")
    if isinstance(hr, dict):
        paths.extend(f"config.hr.{key}" for key in _HR_OUTPUT_KEYS if hr.get(key) == "")
    trackers = cfg.get("trackers")
    if isinstance(trackers, dict):
        for name, tdata in trackers.items():
            if not isinstance(tdata, dict):
                continue
            if tdata.get("remove_similar_tags") == "":
                paths.append(f"config.trackers.{name}.remove_similar_tags")
            site_hr = tdata.get("hr")
            if isinstance(site_hr, dict):
                paths.extend(f"config.trackers.{name}.hr.{key}" for key in _HR_OUTPUT_KEYS if site_hr.get(key) == "")
    return paths


def _delete_config_path(cfg: dict, path: str) -> None:
    """按点路径删除 config 块内的一键(path 首段 "config" 即 cfg 本身; 逐段必为 dict, 收集与删除同源)"""
    parts = path.split(".")
    node = cfg
    for p in parts[1:-1]:
        node = node[p]
    del node[parts[-1]]


def _migrate_config_3_4(cfg: dict):
    """v3→v4: 移除 9 键作用域内的显式置空值(站点级「覆盖为空」三态的语义翻转保护)

    v4 起 config.trackers.<名>.hr.<4 个 tri_state str 键> 的 '' = 覆盖为空; 存量(v3 及更早)的 ''
    语义是「未配置」, 若不随迁移移除, 升级即静默翻转为「本站不打标/不加分类」。返回
    (cfg, notes): 每个被移除键一条 note(路径 + 用户拍板的指引文案), 经 migrate_with_notes
    交 loaders.migrate_config_schema 逐键打 WARNING —— 迁移函数不 log(纯函数纪律)。
    无可移除项时返回裸 dict(框架两种返回形态都接受)。
    """
    paths = _collect_explicit_empty_paths(cfg)
    if not paths:
        return cfg
    for path in paths:
        _delete_config_path(cfg, path)
    notes = [f"{path}: {_EMPTY_REMOVED_HINT}" for path in paths]
    return cfg, notes


MIGRATIONS["config"][3] = _migrate_config_3_4

# ---- v4→v5: 数据源并入顶层 traffic_source 段(计划 26-10-17-0339 S15) ----


def _migrate_config_4_5(cfg: dict):
    """v4→v5: 把「顶层 global_traffic_monitor 段 + 曲线段内联 traffic_source」合并为顶层 traffic_source 段

    - 旧曲线段内联数据源 global_speed_limit_curve.traffic_source[].traffic_monitor.dat_path ->
      config.traffic_source.traffic_monitor.dat_path; 曲线段内的 traffic_source 键删除,
      其余键(interval/enabled/curves)原样保留。
    - 旧 config.global_traffic_monitor 段: 仅把 notify_cooldown_s 迁到
      config.traffic_source.global_traffic_monitor.notify_cooldown_s; enabled / tool_url /
      tool_token_path / subscribe / autostart 一律删除; 整段从 config 删除(该段在 v5 退休)。
    - provider 推导: 旧 global_traffic_monitor 段存在(非空) -> "global_traffic_monitor";
      否则 -> "traffic_monitor"。
    每个被删除/被迁移的键产出一条人读 note, 经 migrate_with_notes 落成 WARNING(D3)。幂等:
    对已是 v5 形状的输入(无旧曲线 traffic_source 键、无旧 gtm 段)不产生任何副作用。
    """
    notes: List[str] = []
    curve = cfg.get("global_speed_limit_curve")
    had_curve_source = isinstance(curve, dict) and "traffic_source" in curve
    legacy_dat_path = ""
    if had_curve_source:
        srcs = curve.get("traffic_source")
        if isinstance(srcs, list):
            for item in srcs:
                if isinstance(item, dict):
                    tm = item.get("traffic_monitor")
                    if isinstance(tm, dict) and str(tm.get("dat_path", "") or "").strip():
                        legacy_dat_path = str(tm["dat_path"]).strip()
        del curve["traffic_source"]
        notes.append("config.global_speed_limit_curve.traffic_source: 已移除, 数据源迁到顶层 traffic_source 段")

    legacy_gtm = cfg.get("global_traffic_monitor")
    had_gtm = isinstance(legacy_gtm, dict)
    legacy_cooldown = None
    if had_gtm:
        legacy_cooldown = legacy_gtm.get("notify_cooldown_s")
        for key in ("enabled", "tool_url", "tool_token_path", "subscribe", "autostart"):
            if key in legacy_gtm:
                notes.append(f"config.global_traffic_monitor.{key}: 已移除(该联动段退休, 相关能力由后续步骤重接)")
        del cfg["global_traffic_monitor"]
        notes.append("config.global_traffic_monitor: 已移除(退休段)")

    if not had_curve_source and not had_gtm:
        return cfg  # 已是 v5 形状: 无旧键可迁, 无副作用(幂等)

    ts = cfg.get("traffic_source")
    if not isinstance(ts, dict):
        ts = {}
        cfg["traffic_source"] = ts

    provider = "global_traffic_monitor" if (isinstance(legacy_gtm, dict) and bool(legacy_gtm)) else "traffic_monitor"
    ts["provider"] = provider
    notes.append(f"config.traffic_source.provider: 设为 {provider}(由旧配置推导)")

    tm_in = ts.get("traffic_monitor")
    if not isinstance(tm_in, dict):
        tm_in = {}
    if legacy_dat_path:
        tm_in["dat_path"] = legacy_dat_path
        notes.append(
            "config.global_speed_limit_curve.traffic_source[0].traffic_monitor.dat_path -> "
            "config.traffic_source.traffic_monitor.dat_path: 数据源已迁到顶层 traffic_source 段"
        )
    if tm_in:
        ts["traffic_monitor"] = tm_in

    tool_in = ts.get("global_traffic_monitor")
    if not isinstance(tool_in, dict):
        tool_in = {}
    if legacy_cooldown is not None:
        tool_in["notify_cooldown_s"] = legacy_cooldown
        notes.append(
            "config.global_traffic_monitor.notify_cooldown_s -> "
            "config.traffic_source.global_traffic_monitor.notify_cooldown_s: 参数已迁到 traffic_source 段"
        )
    if tool_in:
        ts["global_traffic_monitor"] = tool_in

    return cfg, notes


MIGRATIONS["config"][4] = _migrate_config_4_5
