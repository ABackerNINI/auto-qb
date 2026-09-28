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
"""
from typing import Dict
from urllib.parse import urlparse

from ..infra.versioning import MIGRATIONS
from . import site_presets

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
      tracker / refresh_interval 原样保留。
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
