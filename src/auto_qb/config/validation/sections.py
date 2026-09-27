"""config 各段校验器: 顶层简单段(log/qbittorrent/hr/grouping/web/notify 等)"""
import logging
import re
from typing import List

from ...infra.utils import parse_bool, parse_fsize, parse_hm, parse_hr_condition, parse_speed, parse_time
from .. import site_presets
from .core import _check_regex_patterns, _check_str_list, _check_unknown_keys, _try, _try_number, _try_time
from .rules import _check_rule_refs

KNOWN_LOG_KEYS = {"level", "file", "max_bytes", "format"}

KNOWN_QBITTORRENT_KEYS = {"host", "port", "username", "password"}

KNOWN_GROUPING_KEYS = {"enabled", "check_missing_files", "missing_tag"}

KNOWN_WEB_KEYS = {"enabled", "host", "port", "token", "skip_local_verify"}

KNOWN_NOTIFY_KEYS = {"enabled", "min_level", "quiet_hours", "max_per_hour", "dedup_window", "channels"}

# hr_check(HR 在线核实, 计划 §7); 站点级与全局共用区分两套键集
KNOWN_HR_CHANNEL_KEYS = {"enabled", "port", "token", "extension_id", "request_timeout"}

KNOWN_HR_CHECK_KEYS = {
    "enabled",
    "min_torrent_interval",
    "max_torrents_per_hour",
    "max_torrents_per_day",
    "failure_threshold",
    "failure_cooldown",
    "allow_window",
    "unknown_policy",
    "verified_ttl",
    "index_retention",
    "max_download_retries",
    "channel_silence_warn",
    "shared_dir",
    "lock_timeout",
    "poll_interval",
    "parse_missing_rate_max",
    "channel",
    "sites",
}

# hr_check.sites.<档案 id> 条目键集(计划 26-09-27-1318 REV2): mode + 微调项。
# adapter / hr_page_url / download_path / page_param 四个页面事实由内置站点档案
# (config/site_presets.py)填充, 任何配置位置都不再接受(旧键 trackers.*.hr_check 例外: 兼容
# 接受但读取后丢弃, 见 _validate_trackers 的兼容模式)
KNOWN_HR_SITE_KEYS = {
    "mode",
    "hr_page_scopes",
    "refresh_interval",
    "max_pages_per_refresh",
    "completed_age_limit",
    "max_torrents_per_hour",
}

#: 站点模式: off = 不启用 | partial = 在线核实 | all = 站点侧驱动 + 未核实恒受管束
HR_CHECK_MODES = ("off", "partial", "all")
#: Chrome 扩展 id 形态(32 位 a~p) —— 语义与 `hr.channel.EXTENSION_ID_RE` 一致。
#: 此处**故意不复用** hr 包的那个常量: config 是被 hr 依赖的下层, 反向 import 会形成环;
#: 两处等价性由 tests/test_hr_channel.py 的对照用例钉死。
_EXTENSION_ID_RE = re.compile(r"^[a-p]{32}$")

#: 未核实种子的处置: hr = 保守按 HR(默认) | not-hr = 按非 HR(等于自愿放弃一重保证)
HR_CHECK_UNKNOWN_POLICIES = ("hr", "not-hr")

# notify.channels 已知渠道(v1 仅平台原生单渠道; 多渠道按 traffic_source 同模式演进)
NOTIFY_CHANNELS = {"platform"}

NOTIFY_LEVELS = ("INFO", "WARNING", "ERROR")

KNOWN_HR_KEYS = {
    "add_tag",
    "add_category",
    "overwrite_category",
    "add_tag_for_satisfied",
    "add_category_for_satisfied",
    "overwrite_category_for_satisfied",
}

KNOWN_TRACKER_KEYS = {
    "domains",
    "tags",
    "remove_tags",
    "groups",
    "upload_speed_limit",
    "download_speed_limit",
    "hr",
    "hr_check",
    "rules",
    "remove_similar_tags",
}

KNOWN_TRACKER_HR_KEYS = {
    "required_seeding_time", "required_share_ratio", "extra_seeding_time", "condition", *KNOWN_HR_KEYS
}


def _validate_add_episode_tags(spec, errors: List[str]) -> None:
    """校验 config.add_episode_tags 段(布尔 enabled + 单集/多集模板字符串)"""
    if not isinstance(spec, dict):
        errors.append("config.add_episode_tags: 必须是字典")
        return
    if "enabled" in spec:
        _try(parse_bool, spec["enabled"], "config.add_episode_tags.enabled", errors)
    for key in ("add_tag_single", "add_tag_multi"):
        if key in spec and (not isinstance(spec[key], str) or not spec[key].strip()):
            errors.append(f"config.add_episode_tags.{key}: 必须是非空字符串")


def _validate_log(spec, errors: List[str]) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.log: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_LOG_KEYS, "config.log", errors)
    if "level" in spec:
        level = getattr(logging, str(spec["level"]).upper(), None)
        if not isinstance(level, int):
            errors.append(f"config.log.level: 非法日志等级 '{spec['level']}', 可选: DEBUG/INFO/WARNING/ERROR/CRITICAL")
    if "max_bytes" in spec:
        n = _try(parse_fsize, spec["max_bytes"], "config.log.max_bytes", errors)
        # 0 在 RotatingFileHandler 语义 = 从不轮转(单文件无限增长直至磁盘写满);
        # 过小(<1MiB)则每条日志都可能触发轮转(IO 放大); 上界防轮转失去意义
        if n is not None and not 1024**2 <= n <= 1024**3:
            errors.append(f"config.log.max_bytes: 须在 1MiB-1GiB 范围内: {spec['max_bytes']}")


def _validate_qbittorrent(spec, errors: List[str]) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.qbittorrent: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_QBITTORRENT_KEYS, "config.qbittorrent", errors)
    if "port" in spec:
        try:
            port = int(spec["port"])
        except (TypeError, ValueError):
            errors.append(f"config.qbittorrent.port: 必须是整数: {spec['port']}")
        else:
            if not 1 <= port <= 65535:
                errors.append(f"config.qbittorrent.port: 超出范围 1-65535: {port}")


def _validate_global_hr(spec, errors: List[str]) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.hr: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_HR_KEYS, "config.hr", errors)
    for key in ("overwrite_category", "overwrite_category_for_satisfied"):
        if key in spec:
            _try(parse_bool, spec[key], f"config.hr.{key}", errors)


def _validate_hr_check(spec, errors: List[str]) -> None:
    """校验 config.hr_check 段(HR 在线核实: 功能开关 + 频控 + 本地取数通道)

    整段缺省合法(走默认值 = 功能关闭); 保守默认, 故不配就什么都不发生。
    """
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.hr_check: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_HR_CHECK_KEYS, "config.hr_check", errors)
    if "enabled" in spec:
        _try(parse_bool, spec["enabled"], "config.hr_check.enabled", errors)
    # 间隔下限 5s: HR 站点的访问频度是账号安全的第一条防线, 过小等于「根本限不住」
    if "min_torrent_interval" in spec:
        _try_time(spec["min_torrent_interval"], "config.hr_check.min_torrent_interval", errors, min_s=5, max_s=86400)
    for key, where in (
        ("max_torrents_per_hour", "时"),
        ("max_torrents_per_day", "天"),
    ):
        if key in spec:
            _try_number(spec[key], f"config.hr_check.{key}(须为正整数, {where}配额)", errors, integer=True, min=1, max=10000)
    if "failure_threshold" in spec:
        _try_number(
            spec["failure_threshold"], "config.hr_check.failure_threshold", errors, integer=True, min=1, max=100
        )
    if "failure_cooldown" in spec:
        _try_time(spec["failure_cooldown"], "config.hr_check.failure_cooldown", errors, positive=True, max_s=30 * 86400)
    if "allow_window" in spec:
        # 语义与 notify.quiet_hours 相反(那个是「该时段不发」, 本项是「仅该时段取数」), 故文案必须写清
        v = str(spec["allow_window"] or "").strip()
        if v:
            try:
                start_s, end_s = v.split("-", 1)
                parse_hm(start_s)
                parse_hm(end_s)
            except ValueError as e:
                errors.append(f"config.hr_check.allow_window: 须为 'HH:MM-HH:MM'(可跨午夜): {e}")
    if "unknown_policy" in spec:
        if str(spec["unknown_policy"]).strip().lower() not in HR_CHECK_UNKNOWN_POLICIES:
            errors.append(
                f"config.hr_check.unknown_policy: 须为 {'/'.join(HR_CHECK_UNKNOWN_POLICIES)} 之一: "
                f"'{spec['unknown_policy']}'"
            )
    # verified_ttl 下限 60s: 小于一个刷新粒度等于「放行当场失效」, 与默认跟随刷新周期的意图相反
    if "verified_ttl" in spec:
        _try_time(spec["verified_ttl"], "config.hr_check.verified_ttl", errors, min_s=60, max_s=30 * 86400)
    if "index_retention" in spec:
        _try_time(spec["index_retention"], "config.hr_check.index_retention", errors, min_s=86400, max_s=3650 * 86400)
    if "max_download_retries" in spec:
        _try_number(
            spec["max_download_retries"], "config.hr_check.max_download_retries", errors, integer=True, min=1, max=10
        )
    if "channel_silence_warn" in spec:
        _try_time(
            spec["channel_silence_warn"],
            "config.hr_check.channel_silence_warn",
            errors,
            positive=True,
            max_s=30 * 86400
        )
    if "lock_timeout" in spec:
        _try_time(spec["lock_timeout"], "config.hr_check.lock_timeout", errors, min_s=0, max_s=3600)
    if "poll_interval" in spec:
        _try_time(spec["poll_interval"], "config.hr_check.poll_interval", errors, positive=True, min_s=5, max_s=3600)
    if "parse_missing_rate_max" in spec:
        _try_number(spec["parse_missing_rate_max"], "config.hr_check.parse_missing_rate_max", errors, min=0, max=1)
    if "token" in spec and not isinstance(spec["token"], str):
        errors.append("config.hr_check.token: 必须是字符串")
    if "shared_dir" in spec and not isinstance(spec["shared_dir"], str):
        errors.append("config.hr_check.shared_dir: 必须是字符串")
    if "channel" in spec:
        channel = spec["channel"]
        if not isinstance(channel, dict):
            errors.append("config.hr_check.channel: 必须是字典")
        else:
            _check_unknown_keys(channel, KNOWN_HR_CHANNEL_KEYS, "config.hr_check.channel", errors)
            if "enabled" in channel:
                _try(parse_bool, channel["enabled"], "config.hr_check.channel.enabled", errors)
            if "port" in channel:
                try:
                    port = int(channel["port"])
                except (TypeError, ValueError):
                    errors.append(f"config.hr_check.channel.port: 必须是整数: {channel['port']}")
                else:
                    if not 1 <= port <= 65535:
                        errors.append(f"config.hr_check.channel.port: 超出范围 1-65535: {port}")
            if "token" in channel and not isinstance(channel["token"], str):
                errors.append("config.hr_check.channel.token: 必须是字符串")
            if "extension_id" in channel:
                # 填了就按它钉死 CORS origin(chrome-extension://<id>); 留空 = 放行任意扩展 origin
                # (真鉴权是 token, origin 白名单只是第二道)。id 形态错 = 写了也不会生效 ⇒ fail-fast
                ext_id = str(channel["extension_id"] or "").strip()
                if ext_id and not _EXTENSION_ID_RE.match(ext_id):
                    errors.append(f"config.hr_check.channel.extension_id: 须为 32 位 Chrome 扩展 id(a~p): '{ext_id}'")
            if "request_timeout" in channel:
                # 下限 5s: 太短会让正常取数(分钟级)全判超时; 上限 1h: 太长会让持锁线程长期挂住
                _try_time(
                    channel["request_timeout"],
                    "config.hr_check.channel.request_timeout",
                    errors,
                    positive=True,
                    min_s=5,
                    max_s=3600
                )
    if "sites" in spec:
        # 站点接入(计划 26-09-27-1318 REV2): 键必须是已登记的内置档案 id, 未登记 = 该站
        # 没有 adapter 支撑, 放行到运行期只会「静默跳过」, 必须配置期拦下并给出已支持清单
        sites = spec["sites"]
        if not isinstance(sites, dict):
            errors.append("config.hr_check.sites: 必须是字典(键 = 内置站点档案 id)")
        else:
            for preset_id, entry in sites.items():
                preset = site_presets.find_preset(str(preset_id))
                if preset is None:
                    supported = " / ".join(sorted(site_presets.SITE_PRESETS))
                    errors.append(
                        f"config.hr_check.sites.{preset_id}: 未支持的站点档案 '{preset_id}'(已支持: {supported});"
                        " 未入档案的站点不允许启用 HR 在线核实"
                    )
                    continue
                _validate_hr_site_entry(entry, f"config.hr_check.sites.{preset_id}", errors)


def _validate_hr_site_bindings(cfg: dict, errors: List[str]) -> None:
    """站点绑定类校验(计划 26-09-27-1318 §3.3): 绑不上 / 绑多个 / 绑定站点缺 hr 段

    校验器看不到 loader 产物, 故直接读 yaml spec + domains 独立做一遍(与 loader 的
    _resolve_hr_site_bindings 同一判定口径, 单点在 site_presets.match_trackers);
    loader 不报错只填值 —— 与「合法性唯一入口是 validate_config」口径一致。
    """
    trackers = cfg.get("trackers")
    if not isinstance(trackers, dict):
        return
    domains_by_tracker: dict = {}
    hr_sections: set = set()
    for name, tdata in trackers.items():
        if not isinstance(tdata, dict):
            continue
        if isinstance(tdata.get("domains"), list):
            domains_by_tracker[name] = tdata["domains"]
        if "hr" in tdata:
            hr_sections.add(name)

    # 新位置: hr_check.sites.<档案 id>(键合法性已在 _validate_hr_check 报过, 这里只管绑定)
    hr_check = cfg.get("hr_check")
    sites = hr_check.get("sites") if isinstance(hr_check, dict) else None
    enabled_new: set = set()
    if isinstance(sites, dict):
        for preset_id, entry in sites.items():
            preset = site_presets.find_preset(str(preset_id))
            if preset is None or not isinstance(entry, dict):
                continue
            mode = str(entry.get("mode", "off")).strip().lower()
            if mode not in HR_CHECK_MODES or mode == "off":
                continue
            where = f"config.hr_check.sites.{preset_id}"
            matched = site_presets.match_trackers(preset, domains_by_tracker)
            if not matched:
                errors.append(
                    f"{where}: 已启用(mode={mode})但没有站点的 domains 包含"
                    f" {' / '.join(preset.domains)} —— 请在对应站点的域名里补上该域名"
                )
                continue
            if len(matched) > 1:
                errors.append(
                    f"{where}: 绑定必须唯一, 站点 {'、'.join(matched)} 的 domains 都包含"
                    f" {' / '.join(preset.domains)} —— 请去掉多余的域名或关闭其中一个站点的接入"
                )
                continue
            enabled_new.add(preset.preset_id)
            if matched[0] not in hr_sections:
                errors.append(
                    f"{where}: 已绑定站点 {matched[0]}, 但该站点未配置 hr 段(要求做种时长等参数)"
                    " —— 请在「站点」分区的 HR 规则里补齐, 否则该站保护会静默失效"
                )

    # 旧键兼容: trackers.<站点>.hr_check(mode != off)等价迁移口径 —— 绑不上档案报未支持,
    # 绑上了则与 sites 同口径要求 hr 段; 同档案已在新位置启用时旧键被忽略(新位置获胜)
    for name, tdata in trackers.items():
        if not isinstance(tdata, dict) or not isinstance(tdata.get("hr_check"), dict):
            continue
        legacy = tdata["hr_check"]
        mode = str(legacy.get("mode", "off")).strip().lower()
        if mode not in HR_CHECK_MODES or mode == "off":
            continue
        where = f"config.trackers.{name}.hr_check"
        preset = site_presets.preset_for_domains(tdata.get("domains") or ())
        if preset is None:
            supported = " / ".join(sorted(site_presets.SITE_PRESETS))
            errors.append(
                f"{where}: 已启用(mode={mode})但没有内置站点档案匹配该站点的 domains"
                f" —— 未入档案的站点不允许启用 HR 在线核实(已支持: {supported});"
                " 启用方式已上收至 config.hr_check.sites, 建议迁移到新位置"
            )
        elif preset.preset_id in enabled_new:
            continue  # 新旧并存: 新位置获胜, 旧键忽略(等价迁移语义见计划 §3.4)
        elif name not in hr_sections:
            errors.append(f"{where}: 已启用(mode={mode})的站点必须同时配置 hr 段(要求做种时长等参数),"
                          " 否则该站保护会静默失效")


def _validate_hr_site_entry(spec, where: str, errors: List[str]) -> None:
    """校验 hr_check.sites.<档案 id> 条目(mode + 微调项; 计划 26-09-27-1318 REV2)

    ❗fail-fast 重点: mode != off 时绑定站点的 `hr` 段必填 —— 由 _validate_hr_site_bindings
    在绑定层检查(绑定关系要等域名交集算完才知道)。
    """
    if not isinstance(spec, dict):
        errors.append(f"{where}: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_HR_SITE_KEYS, where, errors)
    mode = str(spec.get("mode", "off")).strip().lower()
    if mode not in HR_CHECK_MODES:
        errors.append(f"{where}.mode: 须为 {'/'.join(HR_CHECK_MODES)} 之一: '{spec.get('mode')}'")
    if "hr_page_scopes" in spec:
        scopes = spec["hr_page_scopes"]
        if not (isinstance(scopes, list) and scopes and all(isinstance(s, str) and s.strip() for s in scopes)):
            errors.append(f"{where}.hr_page_scopes: 必须是非空字符串列表(如 [A, B, C])")
        elif not set(s.strip().upper() for s in scopes) <= {"A", "B", "C", "D"}:
            errors.append(f"{where}.hr_page_scopes: 只允许 A/B/C/D(考察中/已达标/未达标/已免罪): {scopes}")
        elif not {"A", "B", "C"} <= set(s.strip().upper() for s in scopes):
            # 只抓 A(考察中)会把「已达标」的 HR 种子当成非 HR ⇒ 覆盖证明成立时误放行 ⇒ 漏 HR
            errors.append(
                f"{where}.hr_page_scopes: 必须包含 A/B/C(考察中/已达标/未达标) —— 少抓一档会让该档种子"
                "在完整刷新里「未列出」而被误放行; D(已免罪)可加可不加"
            )
    if "refresh_interval" in spec:
        _try_time(
            spec["refresh_interval"], f"{where}.refresh_interval", errors, positive=True, min_s=60, max_s=30 * 86400
        )
    if "max_pages_per_refresh" in spec:
        _try_number(
            spec["max_pages_per_refresh"], f"{where}.max_pages_per_refresh", errors, integer=True, min=1, max=100
        )
    if "completed_age_limit" in spec:
        # 0 = 关闭; 开启时下限 1d: HR 考核窗口没有以小时计的, 更小的值几乎必然是单位写错
        # (比如本意 365D 写成 365S) —— 那等于把整站刚完成的种子集体豁免, 必须配置期拦下
        where_age = f"{where}.completed_age_limit"
        try:
            age_s = parse_time(spec["completed_age_limit"])
        except ValueError as e:
            errors.append(f"{where_age}: {e}")
        else:
            if age_s != 0 and not 86400 <= age_s <= 3650 * 86400:
                errors.append(f"{where_age}: 须为 0(关闭)或 1D~3650D: {spec['completed_age_limit']}")
    if "max_torrents_per_hour" in spec:
        _try_number(
            spec["max_torrents_per_hour"], f"{where}.max_torrents_per_hour", errors, integer=True, min=1, max=10000
        )


def _validate_grouping(spec, errors: List[str]) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.grouping: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_GROUPING_KEYS, "config.grouping", errors)
    for key in ("enabled", "check_missing_files"):
        if key in spec:
            _try(parse_bool, spec[key], f"config.grouping.{key}", errors)


def _validate_tag_lists(cfg: dict, errors: List[str]) -> None:
    """delete_tags / delete_tags_if_has_no_torrents: 字符串列表 + regex: 前缀可编译"""
    for key in ("delete_tags", "delete_tags_if_has_no_torrents"):
        if key not in cfg:
            continue
        where = f"config.{key}"
        if _check_str_list(cfg[key], where, errors):
            _check_regex_patterns(cfg[key], where, errors)


def _validate_tracker_hr(spec, where: str, errors: List[str]) -> None:
    if not isinstance(spec, dict):
        errors.append(f"{where}: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_TRACKER_HR_KEYS, where, errors)
    if not str(spec.get("required_seeding_time", "") or "").strip():
        errors.append(f"{where}: 缺少必填键 required_seeding_time(要求做种时间, 如 3D)")
    else:
        _try_time(spec["required_seeding_time"], f"{where}.required_seeding_time", errors)
    if "extra_seeding_time" in spec:
        _try_time(spec["extra_seeding_time"], f"{where}.extra_seeding_time", errors)
    if "required_share_ratio" in spec:
        # [0, 100] 且拦 nan/inf: 负数→立即满足(误打标)、nan→比较恒 False 永不满足(静默失效)
        _try_number(spec["required_share_ratio"], f"{where}.required_share_ratio(须为数字)", errors, min=0, max=100)
    if "condition" in spec:
        _try(parse_hr_condition, spec["condition"], f"{where}.condition(如 80% 或 10MiB)", errors)
    for key in ("overwrite_category", "overwrite_category_for_satisfied"):
        if key in spec:
            _try(parse_bool, spec[key], f"{where}.{key}", errors)


def _validate_trackers(spec, rules_config: dict, errors: List[str]) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.trackers: 必须是字典(留空表示未配置任何站点)")
        return
    for name, tdata in spec.items():
        where = f"config.trackers.{name}"
        if not isinstance(tdata, dict):
            errors.append(f"{where}: 必须是字典")
            continue
        _check_unknown_keys(tdata, KNOWN_TRACKER_KEYS, where, errors)
        # domains: 必填(无默认值), 非空字符串列表
        domains = tdata.get("domains")
        if domains is None:
            errors.append(f"{where}: 缺少必填键 domains(站点域名列表)")
        elif not (isinstance(domains, list) and domains and all(isinstance(d, str) and d.strip() for d in domains)):
            errors.append(f"{where}.domains: 必须是非空字符串列表")
        for key in ("tags", "remove_tags", "groups"):
            if key in tdata:
                if _check_str_list(tdata[key], f"{where}.{key}", errors) and key == "remove_tags":
                    _check_regex_patterns(tdata[key], f"{where}.{key}", errors)
        for key in ("upload_speed_limit", "download_speed_limit"):
            if key in tdata:
                _try(parse_speed, tdata[key], f"{where}.{key}", errors)
        if "remove_similar_tags" in tdata:
            _try(parse_bool, tdata["remove_similar_tags"], f"{where}.remove_similar_tags", errors)
        if "rules" in tdata:
            if _check_str_list(tdata["rules"], f"{where}.rules", errors):
                _check_rule_refs(tdata["rules"], rules_config, f"{where}.rules", errors)
        if "hr" in tdata:
            _validate_tracker_hr(tdata["hr"], f"{where}.hr", errors)
        if "hr_check" in tdata:
            # 旧键兼容模式(计划 26-09-27-1318 §3.4): HR 在线核实的站点配置已整体上收到
            # config.hr_check.sites, 本键只为生产 config.yml 零修改保留 —— 仅校 dict 形状与
            # mode 合法, 其余子键(adapter/hr_page_url/download_path/page_param/微调项)接受
            # 但忽略(值一律以档案为准); 绑定与「缺 hr 段」检查在 _validate_hr_site_bindings
            hc = tdata["hr_check"]
            if not isinstance(hc, dict):
                errors.append(f"{where}.hr_check: 必须是字典(该键为兼容保留: 启用方式已上收至 config.hr_check.sites)")
            else:
                mode = str(hc.get("mode", "off")).strip().lower()
                if mode not in HR_CHECK_MODES:
                    errors.append(
                        f"{where}.hr_check.mode: 须为 {'/'.join(HR_CHECK_MODES)} 之一: '{hc.get('mode')}'"
                        "(该键为兼容保留: 启用方式已上收至 config.hr_check.sites, 建议迁移)"
                    )


def _validate_web(spec, errors: List[str]) -> None:
    """校验 config.web 段(仅本机默认; token 留空 = 随机生成)"""
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.web: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_WEB_KEYS, "config.web", errors)
    if "enabled" in spec:
        _try(parse_bool, spec["enabled"], "config.web.enabled", errors)
    if "host" in spec:
        if not isinstance(spec["host"], str) or not spec["host"].strip():
            errors.append("config.web.host: 必须是非空字符串")
    if "port" in spec:
        try:
            port = int(spec["port"])
        except (TypeError, ValueError):
            errors.append(f"config.web.port: 必须是整数: {spec['port']}")
        else:
            if not 1 <= port <= 65535:
                errors.append(f"config.web.port: 超出范围 1-65535: {port}")
    if "token" in spec and not isinstance(spec["token"], str):
        errors.append("config.web.token: 必须是字符串")
    if "skip_local_verify" in spec:
        _try(parse_bool, spec["skip_local_verify"], "config.web.skip_local_verify", errors)


def _validate_notify(spec, errors: List[str]) -> None:
    """校验 config.notify 段(主动通知); 未配置(None)合法, 走默认值"""
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.notify: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_NOTIFY_KEYS, "config.notify", errors)
    if "enabled" in spec:
        _try(parse_bool, spec["enabled"], "config.notify.enabled", errors)
    if "min_level" in spec:
        if str(spec["min_level"]).strip().upper() not in NOTIFY_LEVELS:
            errors.append(f"config.notify.min_level: 须为 {'/'.join(NOTIFY_LEVELS)} 之一: '{spec['min_level']}'")
    if "quiet_hours" in spec:
        v = str(spec["quiet_hours"] or "").strip()
        if v and "-" in v:
            start_s, _, end_s = v.partition("-")
            for part in (start_s, end_s):
                _try(parse_hm, part, f"config.notify.quiet_hours('{v}')", errors)
        elif v:
            errors.append(f"config.notify.quiet_hours: 须为 \"HH:MM-HH:MM\" 格式(支持跨午夜): '{v}'")
    if "max_per_hour" in spec:
        try:
            n = int(spec["max_per_hour"])
        except (TypeError, ValueError):
            errors.append(f"config.notify.max_per_hour: 必须为整数: {spec['max_per_hour']}")
        else:
            if n <= 0:
                errors.append("config.notify.max_per_hour: 必须为正整数")
            elif n > 100:
                errors.append("config.notify.max_per_hour: 须 <= 100")  # 防风暴参数自身无上界则失去意义
    if "dedup_window" in spec:
        # 0 = 不去重(合法); 上限 24H: 过大 → 相同前缀的真实 ERROR 被长期压制(掩盖故障)
        _try_time(spec["dedup_window"], "config.notify.dedup_window", errors, max_s=86400)
    if "channels" in spec:
        ch = spec["channels"]
        if not isinstance(ch, list) or not ch:
            errors.append("config.notify.channels: 必须是非空列表")
        else:
            for i, item in enumerate(ch):
                if not isinstance(item, dict) or len(item) != 1:
                    errors.append(f"config.notify.channels[{i}]: 必须是单键映射(如 - platform: {{}})")
                    continue
                name = next(iter(item))
                if name not in NOTIFY_CHANNELS:
                    errors.append(f"config.notify.channels[{i}]: 未知渠道 '{name}', 可用: {sorted(NOTIFY_CHANNELS)}")
