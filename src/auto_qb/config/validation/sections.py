"""config 各段校验器: 顶层简单段(log/qbittorrent/hr/grouping/web/notify 等)"""
import ipaddress
import logging
import re
import sys
from typing import List, Tuple

from ...infra.utils import is_loopback_host, parse_bool, parse_fsize, parse_hr_condition, parse_speed, parse_time
from .. import site_presets
from ..schema.fields import LOG_LEVELS, NOTIFY_CHANNELS, NOTIFY_LEVELS, RELOCATE_VERIFY_MODES
from .core import (
    _check_regex_patterns,
    _check_str_list,
    _check_unknown_keys,
    _fmt_s,
    _try,
    _try_number,
    _try_port,
    _try_port_or_zero,
    _try_time,
    _try_time_window,
)
from .rules import _check_rule_refs

logger = logging.getLogger(__name__)

KNOWN_LOG_KEYS = {"level", "file", "max_bytes", "format"}

KNOWN_QBITTORRENT_KEYS = {"host", "port", "username", "password"}

KNOWN_GROUPING_KEYS = {"enabled", "check_missing_files", "missing_tag", "cross_group_conflict_check"}

# fs(文件访问, plan 26-09-27-1407): 容器部署路径映射, 空表 = 现状(保守默认)
KNOWN_FS_KEYS = {"path_map"}

# path_map 条目的合法键(YAML 空间): from = qB 报回的宿主路径前缀, to = 容器挂载点
KNOWN_PATH_MAP_ENTRY_KEYS = {"from", "to"}

# relocate(整组迁移, 计划 26-10-18-1604 §3.7): 新顶层段(不塞 fs —— 那是 R 级要重启);
# 由 RelocateModule.sections() 认领, 热重载即生效; enabled=false(缺省) = 三入口逐字节现状。
# 空间键只认二进制单位(parse_fsize 单点): YAML 写 "10GiB" 而非 "10G"。
KNOWN_RELOCATE_KEYS = {
    "enabled",
    "alias_file_threshold",
    "hard_max_links",
    "verify",
    "allow_uac",
    "move_stall_timeout",
    "move_warn_after",
    "finalize_timeout",
    "low_space_warn",
}

KNOWN_WEB_KEYS = {"enabled", "host", "port", "token", "skip_local_verify", "skip_check_menu"}

KNOWN_NOTIFY_KEYS = {"enabled", "min_level", "quiet_hours", "max_per_hour", "dedup_window", "channels"}

# qb_traffic(qB 口径流量采样, plan 26-10-03-0946 §06; flush_interval 为 v3 新键, 计划 26-10-04-1957 §06.1)
KNOWN_QB_TRAFFIC_KEYS = {"enabled", "sample_interval", "flush_interval", "raw_window", "rollup_window"}

# traffic_source(全局流量来源, 计划 26-10-17-0339 S15; 26-10-17-1737 S1 增 enabled 总开关):
# 一键切换取数数据源; provider 决定生效来源(两来源参数可并存, 但只有 provider 指向的那个参与取数, D1 严格互斥)
# refresh_interval 为 26-10-18-0813 A3 新增: 来源侧快照节奏, 与曲线 interval 解绑
KNOWN_TRAFFIC_SOURCE_KEYS = {"enabled", "provider", "refresh_interval", "traffic_monitor", "global_traffic_monitor"}
#: traffic_source.traffic_monitor(Traffic Monitor dat 来源)
KNOWN_TRAFFIC_SOURCE_TM_KEYS = {"dat_path"}
#: traffic_source.global_traffic_monitor(整机流量监视器 gtm 来源)
#: !无 data_dir(R2/D20): 数据目录由工具的发现指针提供, 配置里不再存副本 —— 出现该键按未知键拒绝
KNOWN_TRAFFIC_SOURCE_TOOL_KEYS = {"tool_dir", "tool_exe", "notify_cooldown_s"}

# qb_traffic.flush_interval 边界(v3 计划 26-10-04-1957 §06.1): 缓冲批量落盘周期 —— 下限防写放大
# (fsync 风暴), 上限防崩溃丢失窗口过大; 须为整数秒(游标/块头时间戳按整秒粒度推算)
FLUSH_INTERVAL_MIN_S = 60.0
FLUSH_INTERVAL_MAX_S = 3600.0

# hr_check(HR 在线核实, v3 15 键口径, 计划 26-09-28-1932 §6.1 + 26-09-30-0240); 站点级与全局共用区分两套键集
# channel 段 8 键(去端口+跨机, 计划 26-10-14-1241 S1): host / port(0=随机) / discovery_port(0=关) / pairing 新增
KNOWN_HR_CHANNEL_KEYS = {
    "enabled",
    "host",
    "port",
    "discovery_port",
    "pairing",
    "token",
    "extension_id",
    "request_timeout",
}

#: channel.pairing 取值域(计划 §04 S3): auto = host 非回环时强制; on = 恒要; off = 恒不要(校验拦危险组合)
CHANNEL_PAIRING_MODES = ("auto", "on", "off")


def _channel_ephemeral_port_range() -> Tuple[int, int]:
    """OS 临时端口段(计划 §04 S1 ⑥): Windows 49152-65535 / 类 Unix(Linux) 32768-60999

    只用作 discovery_port 的告警判据(V12): 落入段内 = 易与系统临时端口分配相撞
    (Windows 还有 Hyper-V/WSL2 动态排除段, 无监听者也绑不上、随重启漂移)。
    做成函数而非常量: 测试要按平台参数化(monkeypatch), 判据以本仓实际运行平台为准。
    """
    if sys.platform == "win32":
        return (49152, 65535)
    return (32768, 60999)


#: 回环判据单点在 infra.utils.is_loopback_host(config 校验与 hr 配对门共用, 不得各写一份)
_is_loopback_host = is_loopback_host


def _validate_channel_host(value, where: str, errors: List[str]) -> None:
    """channel.host 校验(S1 ①): 非空且为合法 IPv4/IPv6 字面量或 localhost

    不支持主机名: 扩展侧 normalize 按字面量判私网段, 主机名无法分类(计划 §01 派生口径);
    NAS 部署请直接填 NAS 的内网 IP。
    """
    host = str(value if value is not None else "").strip()
    if not host:
        errors.append(f"{where}: 不能为空(留空请直接删掉该键, 走默认 127.0.0.1)")
        return
    if host.lower() == "localhost":
        return
    try:
        ipaddress.ip_address(host)
    except ValueError:
        errors.append(f"{where}: 须为 IPv4/IPv6 字面量或 localhost(不支持主机名): {host}")


KNOWN_HR_CHECK_KEYS = {
    "enabled",
    "min_interval",
    "max_requests_per_day",
    "max_pages_per_wave",
    "allow_window",
    "shared_dir",
    "reuse_window",
    "channel",
    "sites",
}

# hr_check.sites.<档案 id> 条目键集(v3): enabled + tracker 显式映射 + refresh_interval
# + idle_refresh_interval(稳态降频, 计划 26-10-05-0555 S1)。
# adapter / hr_page_url / download_path / page_param / listing 五个页面事实由内置站点档案
# (config/site_presets.py)填充, 任何配置位置都不再接受。
KNOWN_HR_SITE_KEYS = {
    "enabled",
    "tracker",
    "refresh_interval",
    "idle_refresh_interval",
}
#: Chrome 扩展 id 形态(32 位 a~p) —— 语义与 `hr.channel.EXTENSION_ID_RE` 一致。
#: 此处**故意不复用** hr 包的那个常量: config 是被 hr 依赖的下层, 反向 import 会形成环;
#: 两处等价性由 tests/test_hr_channel.py 的对照用例钉死。
_EXTENSION_ID_RE = re.compile(r"^[a-p]{32}$")

# notify.channels 已知渠道已收敛至 schema.fields 单点(issue 26-10-11-0031, 顶部导入)

KNOWN_HR_KEYS = {
    "add_tag",
    "add_category",
    "overwrite_category",
    "add_tag_for_satisfied",
    "add_category_for_satisfied",
    "overwrite_category_for_satisfied",
    # HR 排除表(计划 26-09-28-1805): 命中的种子不纳入 HR 体系; 全局与站点段共用本键集
    "exclude_tags",
    "exclude_categories",
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
            errors.append(f"config.log.level: 非法日志等级 '{spec['level']}', 可选: {'/'.join(LOG_LEVELS)}")
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
        _try_port(spec["port"], "config.qbittorrent.port", errors)


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
    for key in ("exclude_tags", "exclude_categories"):
        if key in spec and _check_str_list(spec[key], f"config.hr.{key}", errors):
            _check_regex_patterns(spec[key], f"config.hr.{key}", errors)


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
    if "min_interval" in spec:
        _try_time(spec["min_interval"], "config.hr_check.min_interval", errors, min_s=5, max_s=86400)
    for key in ("max_requests_per_day", "max_pages_per_wave"):
        if key in spec:
            _try_number(spec[key], f"config.hr_check.{key}(须为正整数)", errors, integer=True, min=1, max=100000)
    if "allow_window" in spec:
        # 语义与 notify.quiet_hours 相反(那个是「该时段不发」, 本项是「仅该时段取数」), 方向语义由 help/文档表达
        _try_time_window(spec["allow_window"], "config.hr_check.allow_window", errors)
    if "shared_dir" in spec and not isinstance(spec["shared_dir"], str):
        errors.append("config.hr_check.shared_dir: 必须是字符串")
    if "reuse_window" in spec:
        # 数据复用窗(计划 26-09-30-0240): 上限 7d —— 复用窗只影响数据新鲜度, 调再大也不增加站点访问,
        # 但过大会让「数据已过期」的假象长期存在; 下限 60s 与站点级 refresh_interval 同款
        _try_time(
            spec["reuse_window"], "config.hr_check.reuse_window", errors, positive=True, min_s=60, max_s=7 * 86400
        )
    if "channel" in spec:
        channel = spec["channel"]
        if not isinstance(channel, dict):
            errors.append("config.hr_check.channel: 必须是字典")
        else:
            _check_unknown_keys(channel, KNOWN_HR_CHANNEL_KEYS, "config.hr_check.channel", errors)
            if "enabled" in channel:
                _try(parse_bool, channel["enabled"], "config.hr_check.channel.enabled", errors)
            if "host" in channel:
                _validate_channel_host(channel["host"], "config.hr_check.channel.host", errors)
            if "port" in channel:
                _try_port_or_zero(channel["port"], "config.hr_check.channel.port", errors)
            if "discovery_port" in channel:
                _try_port_or_zero(channel["discovery_port"], "config.hr_check.channel.discovery_port", errors)
            if "pairing" in channel:
                mode = str(channel["pairing"]).strip().lower()
                if mode not in CHANNEL_PAIRING_MODES:
                    errors.append(
                        f"config.hr_check.channel.pairing: 取值非法: '{channel['pairing']}', "
                        f"可选: {'/'.join(CHANNEL_PAIRING_MODES)}"
                    )
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

            # ---- 交叉规则(S1 ③⑤⑥): 各键自身格式已由上面各自己报, 这里只在两侧解析成功时比较 ----

            def _chan_int(key: str, default: int):
                if key not in channel:
                    return default
                try:
                    return int(channel[key])
                except (TypeError, ValueError):
                    return None  # 已由端口校验报过

            port_v = _chan_int("port", 0)
            dport_v = _chan_int("discovery_port", 18788)
            raw_host = str(channel.get("host") or "").strip()
            host_v = raw_host if raw_host else "127.0.0.1"
            pairing_v = str(channel.get("pairing") or "auto").strip().lower()
            token_v = str(channel.get("token") or "").strip()
            # ③ 两端口相撞(计划 §01 派生口径 + §08 迁移): 用户现产 port:18788 + 默认 discovery 18788 即此形态
            if port_v and dport_v and port_v == dport_v:
                errors.append(
                    f"config.hr_check.channel.port: 与 discovery_port({dport_v})相同 —— 两端口不能相同; "
                    "把 port 改 0(推荐: 本端口转作发现端口、数据端口随机), 或把 discovery_port 显式改成别的端口"
                )
            # ⑤ 非回环 + 永不配对 + 未配置密钥 = LAN 上无人工关口的密钥分发器, 一道都不许少(V4)
            if pairing_v == "off" and not _is_loopback_host(host_v) and not token_v:
                errors.append(
                    f"config.hr_check.channel: host={host_v} 非回环且 pairing=off 且未配置 token —— "
                    "三选一: pairing 改 on/auto、显式配置 token、或把 host 改回回环"
                )
            # ⑥ discovery_port 落入 OS 临时端口段 => 告警不阻断(V12; 默认 18788 在段外)
            if dport_v:
                lo, hi = _channel_ephemeral_port_range()
                if lo <= dport_v <= hi:
                    logger.warning(
                        "config.hr_check.channel.discovery_port: %s 落入本机临时端口段(%s-%s) —— "
                        "易与系统临时端口分配相撞(Windows 还需排查 Hyper-V/WSL2 动态排除段); "
                        "本条为告警不阻断, 建议改用段外端口(默认 18788 在段外)",
                        dport_v,
                        lo,
                        hi,
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
    """站点绑定类校验(计划 26-09-27-1930 §3.3/§5): 映射制口径 —— 默认映射 0 命中/歧义、
    显式 tracker 键不存在、唯一性、绑定站点缺 hr 段

    校验器看不到 loader 产物, 故直接读 yaml spec 独立做一遍(与 loader 的
    _resolve_hr_site_bindings 同一判定口径, 单点在 site_presets.match_trackers);
    loader 不报错只填值 —— 与「合法性唯一入口是 validate_config」口径一致。
    web 域与 announce 域永不互相比对: 绑定只发生在 announce 命名空间(档案已知
    tracker_domain vs 用户 domains)或显式条目名直取。
    """
    trackers = cfg.get("trackers")
    if not isinstance(trackers, dict):
        return
    domains_by_tracker: dict = {}
    tracker_names: set = set()
    hr_sections: set = set()
    for name, tdata in trackers.items():
        if not isinstance(tdata, dict):
            continue
        tracker_names.add(name)
        if isinstance(tdata.get("domains"), list):
            domains_by_tracker[name] = tdata["domains"]
        if "hr" in tdata:
            hr_sections.add(name)

    # hr_check.sites.<档案 id>(键合法性已在 _validate_hr_check 报过, 这里只管绑定)
    hr_check = cfg.get("hr_check")
    sites = hr_check.get("sites") if isinstance(hr_check, dict) else None
    if not isinstance(sites, dict):
        return
    claimed: dict = {}  # 已绑定的 tracker 条目名 -> 档案 id(唯一性: 一个站点配置只服务一个档案)
    for preset_id, entry in sites.items():
        preset = site_presets.find_preset(str(preset_id))
        if preset is None or not isinstance(entry, dict):
            continue
        enabled = entry.get("enabled")
        try:
            enabled_bool = parse_bool(enabled) if enabled is not None else False
        except ValueError:
            continue  # 键类型已由 _validate_hr_site_entry 报过
        if not enabled_bool:
            continue
        where = f"config.hr_check.sites.{preset_id}"
        explicit = str(entry.get("tracker", "") or "").strip()
        if explicit:
            # 显式映射: 按 trackers 键名直取(字符串相等引用, 无匹配语义)
            if explicit not in tracker_names:
                errors.append(f"{where}.tracker: 站点配置 '{explicit}' 不存在 —— 须为 trackers 下的条目名")
                continue
            bound = explicit
        else:
            # 默认映射: 档案已知 announce 域在同命名空间(用户 domains)查表
            matched = site_presets.match_trackers(preset, domains_by_tracker)
            if not matched:
                errors.append(
                    f"{where}: 已启用但档案默认映射未命中 —— 档案已知该站 announce 域为"
                    f" {preset.tracker_domain}, 请确认目标站点的 domains 含该域(或其子域);"
                    " 也可在该条目显式填 tracker 指定"
                )
                continue
            if len(matched) > 1:
                errors.append(f"{where}: 默认映射命中多个站点({'、'.join(matched)}) —— 请在该条目显式填 tracker 指定其一")
                continue
            bound = matched[0]
        if bound in claimed:
            errors.append(f"{where}: 站点配置 {bound} 已被条目 {claimed[bound]} 绑定"
                          " —— 一个站点配置只能服务一个站点档案")
            continue
        claimed[bound] = preset.preset_id
        if bound not in hr_sections:
            errors.append(f"{where}: 已绑定站点 {bound}, 但该站点未配置 hr 段(要求做种时长等参数)"
                          " —— 请在「站点」分区的 HR 规则里补齐, 否则该站保护会静默失效")


def _validate_hr_site_entry(spec, where: str, errors: List[str]) -> None:
    """校验 hr_check.sites.<档案 id> 条目(enabled + tracker 显式映射 + refresh_interval
    + idle_refresh_interval; v3)

    !fail-fast 重点: enabled 时绑定站点的 `hr` 段必填 —— 由 _validate_hr_site_bindings
    在绑定层检查(绑定关系要等默认映射查表/显式直取解析完才知道)。
    """
    if not isinstance(spec, dict):
        errors.append(f"{where}: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_HR_SITE_KEYS, where, errors)
    if "enabled" in spec:
        _try(parse_bool, spec["enabled"], f"{where}.enabled", errors)
    if "tracker" in spec and not isinstance(spec["tracker"], str):
        errors.append(f"{where}.tracker: 必须是字符串(trackers 下的条目名; 留空 = 用档案默认映射)")
    if "refresh_interval" in spec:
        _try_time(
            spec["refresh_interval"], f"{where}.refresh_interval", errors, positive=True, min_s=60, max_s=30 * 86400
        )
    # 稳态降频间隔(计划 26-10-05-0555 S1): 与 refresh_interval 同款口径(60s 下限 / 30d 上限)
    if "idle_refresh_interval" in spec:
        _try_time(
            spec["idle_refresh_interval"],
            f"{where}.idle_refresh_interval",
            errors,
            positive=True,
            min_s=60,
            max_s=30 * 86400
        )
    # 交叉校验(计划 26-10-05-0555 S1): 降频不能比常态还快。两侧按缺省补齐成有效值后比较 ——
    # 覆盖「refresh 配得比默认 idle(24H)还长而未配 idle」的场景(只看显式键会漏掉它)。
    # 某侧键存在但格式非法时其错误已由 _try_time 报过, 该侧返回 None 使交叉校验整体跳过
    # (不拿默认值顶替参与比较, 避免与用户原意无关的叠加文案)。
    def _effective_s(side_key: str, default_s: float):
        """条目时间键的有效秒值: 缺省按 default_s 补齐; 存在但格式非法返回 None"""
        if side_key not in spec:
            return default_s
        try:
            return parse_time(spec[side_key])
        except ValueError:
            return None

    from ..models import SiteHrCheckConfig  # 延迟导入防环(与 core._current_main_tick 同款)

    defaults = SiteHrCheckConfig()
    idle_s = _effective_s("idle_refresh_interval", defaults.idle_refresh_interval)
    refresh_s = _effective_s("refresh_interval", defaults.refresh_interval)
    if idle_s is not None and refresh_s is not None and idle_s < refresh_s:
        errors.append(
            f"{where}.idle_refresh_interval: 降频不能比常态还快 —— 稳态拉取间隔({_fmt_s(idle_s)}s)"
            f"须 >= 拉取间隔({_fmt_s(refresh_s)}s); 相等 = 等效关闭降频"
        )


def _validate_grouping(spec, errors: List[str]) -> None:
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.grouping: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_GROUPING_KEYS, "config.grouping", errors)
    for key in ("enabled", "check_missing_files", "cross_group_conflict_check"):
        if key in spec:
            _try(parse_bool, spec[key], f"config.grouping.{key}", errors)


def _norm_prefix(p: str) -> str:
    """映射前缀的归一口径(与 infra/file_access.MappedFileAccess 的匹配规则同源):
    折叠分隔符(`\\`→`/`)+ 压缩重复斜杠 + 去尾斜杠; 大小写折叠由调用方按需叠加"""
    from ...infra.utils import path_normalize
    return path_normalize(p).rstrip("/")


def _validate_fs(spec, errors: List[str]) -> None:
    """fs 段(文件访问, plan 26-09-27-1407): path_map 映射表

    from 必须是绝对路径(带盘符 / UNC / 以 / 开头); to 必须以 / 开头(容器挂载点);
    两侧尾斜杠归一后再比较; from 重复(大小写/尾斜杠归一后)报错;
    两条 from 互不为对方前缀(带 `/` 边界)报错 —— 否则命中顺序依赖表序, 语义歧义。
    """
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.fs: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_FS_KEYS, "config.fs", errors)
    raw = spec.get("path_map")
    if raw is None:
        return
    where = "config.fs.path_map"
    if not isinstance(raw, list):
        errors.append(f"{where}: 必须是列表")
        return
    seen: dict = {}  # casefold 后的 from 归一形 -> 条目序号(重复检测)
    normed: List[tuple] = []  # (归一形, 原始值, 序号) 供前缀歧义检查
    for i, item in enumerate(raw):
        w = f"{where}[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{w}: 必须是字典 {{from, to}}")
            continue
        _check_unknown_keys(item, KNOWN_PATH_MAP_ENTRY_KEYS, w, errors)
        src = str(item.get("from", "") or "").strip()
        dst = str(item.get("to", "") or "").strip()
        if not src:
            errors.append(f"{w}.from: 不能为空")
        elif not (re.match(r"^[A-Za-z]:[\\/]", src) or src.startswith(("/", "\\\\"))):
            errors.append(f"{w}.from: 必须是绝对路径(带盘符如 D:/Downloads、UNC 或以 / 开头): {src}")
        if not dst:
            errors.append(f"{w}.to: 不能为空")
        elif not dst.startswith("/"):
            errors.append(f"{w}.to: 必须是以 / 开头的容器挂载点(如 /mnt/downloads): {dst}")
        if not src or not dst:
            continue
        src_n = _norm_prefix(src)
        dst_n = _norm_prefix(dst)
        if not src_n:
            errors.append(f"{w}.from: 归一后为空: {src}")
            continue
        if not dst_n:
            errors.append(f"{w}.to: 归一后为空(不能只是根 /): {dst}")
            continue
        key = src_n.casefold()
        if key in seen:
            errors.append(f"{w}.from: 与第 {seen[key]} 条重复(尾斜杠/大小写/分隔符归一后): {src}")
        else:
            seen[key] = i
        normed.append((src_n, src, i))
    # 前缀歧义: 任一 from 互不为对方前缀(带 / 边界, 如 D:/Downloads 不得歧义命中 D:/Downloads2;
    # 而 D:/Downloads 与 D:/Downloads/sub 会按表序决定翻译结果 —— 一并拦下)
    for ai, (a, a_raw, _i) in enumerate(normed):
        for bi, (b, b_raw, _j) in enumerate(normed):
            if ai == bi:
                continue
            if (a.casefold() + "/").startswith(b.casefold() + "/"):
                errors.append(f"{where}[{_i}].from: 是第 {_j} 条 from 的前缀(尾斜杠/大小写归一后), 命中有歧义: '{a_raw}' vs '{b_raw}'")
                break


def _validate_relocate(spec, errors: List[str]) -> None:
    """relocate 段(整组迁移, 计划 26-10-18-1604 §3.7): 9 键逐一键级校验

    阈值分流细节(alias_file_threshold 的 7/8/9 边界、hard_max_links 与目录别名的取舍)
    由 P2 引擎纯函数表驱动测试覆盖, 本处只做形状与粗范围: 两个 int >= 1; verify 取值域
    单点(RELOCATE_VERIFY_MODES, schema.fields 同源); 三个时间键 > 0; low_space_warn 走
    parse_fsize(二进制单位, YAML 写 10GiB; 0 = 不告警)。
    """
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.relocate: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_RELOCATE_KEYS, "config.relocate", errors)
    for key in ("enabled", "allow_uac"):
        if key in spec:
            _try(parse_bool, spec[key], f"config.relocate.{key}", errors)
    for key in ("alias_file_threshold", "hard_max_links"):
        if key not in spec:
            continue
        n = _try(int, spec[key], f"config.relocate.{key}(须为整数)", errors)
        if n is not None and n < 1:
            errors.append(f"config.relocate.{key}: 须 >= 1(文件数/链接条数): {spec[key]}")
    if "verify" in spec:
        mode = str(spec["verify"]).strip().lower()
        if mode not in RELOCATE_VERIFY_MODES:
            errors.append(f"config.relocate.verify: 取值非法: '{spec['verify']}', 可选: {'/'.join(RELOCATE_VERIFY_MODES)}")
    for key in ("move_stall_timeout", "move_warn_after", "finalize_timeout"):
        if key in spec:
            _try_time(spec[key], f"config.relocate.{key}", errors, positive=True)
    if "low_space_warn" in spec:
        _try(parse_fsize, spec["low_space_warn"], "config.relocate.low_space_warn(如 10GiB)", errors)


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
    for key in ("exclude_tags", "exclude_categories"):
        if key in spec and _check_str_list(spec[key], f"{where}.{key}", errors):
            _check_regex_patterns(spec[key], f"{where}.{key}", errors)


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
            # 兜底报废除错(计划 26-09-27-1930 §3.4/§5): 旧键已随 schema v1→v2 迁移链废除,
            # 正常流走到这里的配置不该再有本键 —— 出现即说明文件被手改过版本号, 或迁移无法
            # 定位档案(缺 hr_page_url / host 陌生)。不设常驻兼容层, 一次性指路到新位置。
            supported = " / ".join(sorted(site_presets.SITE_PRESETS))
            errors.append(
                f"{where}.hr_check: 该键已于 schema v2 废除 —— 存量配置应由迁移链自动改写;"
                " 出现本错误说明文件被手改过版本号或迁移无法定位档案,"
                f" 请在 config.hr_check.sites.<档案 id> 重新配置(已支持: {supported})"
            )


def _validate_traffic_source(spec, errors: List[str]) -> None:
    """校验 config.traffic_source 段(全局流量来源, 计划 26-10-17-0339 S15/D1)

    未配置(None)合法 = 走默认值(provider=traffic_monitor)。两来源参数可并存, 但只有 provider
    指向的那个参与取数(D1 严格互斥); provider=traffic_monitor 时其 dat_path 必须非空(未配数据源
    则功能取不到数 —— fail-fast)。两个子块一律做结构校验(未知键 + 类型), 与 provider 无关。
    provider=global_traffic_monitor 时**启动期没有必填项**(R2/D20): 取数路径是工具运行期报出的
    事实(发现指针), 配置面无从校验 —— 缺路径由状态区与运行期日志承担, 不在这里猜。
    """
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.traffic_source: 必须是字典")
        return
    where = "config.traffic_source"
    _check_unknown_keys(spec, KNOWN_TRAFFIC_SOURCE_KEYS, where, errors)
    # enabled 总开关(26-10-17-1737 S1/D1): bool, 缺省 true。关闭的连带停摆(曲线/expr/工具
    # 订阅)由运行期闸门承载, 这里只管形状 —— 不因 enabled=false 免检其余键(关来源也要能改配置)
    if "enabled" in spec:
        _try(parse_bool, spec["enabled"], f"{where}.enabled", errors)
    # 来源侧快照节奏(26-10-18-0813 A3/D9): 10S ~ 1H。下限防"每 tick 读盘 + 发布"空转(读的是
    # 一个随流量增长的文件), 上限防历史图停在一天前; 与曲线 interval 是两个独立节奏, 各自校验。
    if "refresh_interval" in spec:
        _try_time(spec["refresh_interval"], f"{where}.refresh_interval", errors, min_s=10, max_s=3600)
    # provider 缺省/留空 = traffic_monitor(与 loader 同口径)
    provider = str(spec.get("provider") or "traffic_monitor").strip()
    if provider not in ("traffic_monitor", "global_traffic_monitor"):
        errors.append(f"{where}.provider: 取值非法: '{spec.get('provider')}', 可选: traffic_monitor/global_traffic_monitor")
    tm = spec.get("traffic_monitor")
    if tm is not None:
        tm_where = f"{where}.traffic_monitor"
        if not isinstance(tm, dict):
            errors.append(f"{tm_where}: 必须是字典")
        else:
            _check_unknown_keys(tm, KNOWN_TRAFFIC_SOURCE_TM_KEYS, tm_where, errors)
            if "dat_path" in tm and not isinstance(tm["dat_path"], str):
                errors.append(f"{tm_where}.dat_path: 必须是字符串(路径)")
    tool = spec.get("global_traffic_monitor")
    if tool is not None:
        tool_where = f"{where}.global_traffic_monitor"
        if not isinstance(tool, dict):
            errors.append(f"{tool_where}: 必须是字典")
        else:
            _check_unknown_keys(tool, KNOWN_TRAFFIC_SOURCE_TOOL_KEYS, tool_where, errors)
            for key in ("tool_dir", "tool_exe"):
                if key in tool and not isinstance(tool[key], str):
                    errors.append(f"{tool_where}.{key}: 必须是字符串(路径)")
            if "notify_cooldown_s" in tool:
                # 0 = 不冷却(合法; 事件号去重仍在); 上限 24H: 过大等于永不刷新历史图
                _try_time(tool["notify_cooldown_s"], f"{tool_where}.notify_cooldown_s", errors, min_s=0, max_s=86400)
    # enabled=false 时来源已整体停摆(26-10-17-1737 S1/D1): 免检 dat_path —— 关来源本就是
    # "没配好数据源"时的出路; 若仍要求 dat_path, 用户无法从设置页把没配好的来源关掉
    # (保存必败, 且 UI 里找不到能改的地方)。非法值不当成关闭(parse_bool 已在上面报错)。
    source_off = str(spec.get("enabled") or "").strip().lower() == "false"
    # 按 provider 校验所需字段: traffic_monitor 来源必须有 dat_path
    if provider == "traffic_monitor" and not source_off:
        dat = tm.get("dat_path") if isinstance(tm, dict) else None
        if not isinstance(dat, str) or not dat.strip():
            errors.append(f"{where}.traffic_monitor.dat_path: provider=traffic_monitor 时必须配置非空的 dat 文件路径")


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
        _try_port(spec["port"], "config.web.port", errors)
    if "token" in spec and not isinstance(spec["token"], str):
        errors.append("config.web.token: 必须是字符串")
    if "skip_local_verify" in spec:
        _try(parse_bool, spec["skip_local_verify"], "config.web.skip_local_verify", errors)
    if "skip_check_menu" in spec:
        _try(parse_bool, spec["skip_check_menu"], "config.web.skip_check_menu", errors)


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
        _try_time_window(spec["quiet_hours"], "config.notify.quiet_hours", errors)
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


def _validate_qb_traffic(spec, errors: List[str], main_tick: float = None) -> None:
    """校验 config.qb_traffic 段(qB 口径流量采样, plan 26-10-03-0946 方案C §06); 未配置(None)合法 = 不启用

    边界依据(§06 表; v3 计划 26-10-04-1957 §06.1 修订): sample_interval 下限 = main_tick(硬校验,
    main_tick 从同一份 config 现取 —— 采样任务由主循环节拍驱动, 比 tick 还细的间隔调度上不可实现;
    上限 600 防视图颗粒过粗); flush_interval 60-3600s 整数秒(v3 新键: 缓冲批量落盘周期, 缺省 600);
    raw_window 1h-90d(原 72h 上限防单文件超体量, 用户接受体量换 3 个月高分辨率);
    rollup_window 7d 起、无上限(原 90d 上限取消 —— 设得足够久即等效永久保留)。
    「main_tick 整数倍」不在本层校验(裁决 D5): 失配只是精度损耗不致错误行为, 告警落采样模块检测点。
    """
    if spec is None:
        return
    if not isinstance(spec, dict):
        errors.append("config.qb_traffic: 必须是字典")
        return
    _check_unknown_keys(spec, KNOWN_QB_TRAFFIC_KEYS, "config.qb_traffic", errors)
    if "enabled" in spec:
        _try(parse_bool, spec["enabled"], "config.qb_traffic.enabled", errors)
    if "sample_interval" in spec:
        seconds = _try(parse_time, spec["sample_interval"], "config.qb_traffic.sample_interval", errors)
        if seconds is not None:
            if seconds <= 0:
                errors.append(f"config.qb_traffic.sample_interval: 必须为正时间: {spec['sample_interval']}")
            elif seconds > 600:
                errors.append("config.qb_traffic.sample_interval: 须 <= 600s")
            elif main_tick is not None and seconds < main_tick:
                errors.append(
                    f"config.qb_traffic.sample_interval: 须 >= main_tick({_fmt_s(main_tick)}s)"
                    f"(采样节奏不细于主循环节拍): {spec['sample_interval']}"
                )
    if "flush_interval" in spec:
        seconds = _try(parse_time, spec["flush_interval"], "config.qb_traffic.flush_interval", errors)
        if seconds is not None:
            if seconds < FLUSH_INTERVAL_MIN_S:
                errors.append(f"config.qb_traffic.flush_interval: 须 >= {_fmt_s(FLUSH_INTERVAL_MIN_S)}s")
            elif seconds > FLUSH_INTERVAL_MAX_S:
                errors.append(f"config.qb_traffic.flush_interval: 须 <= {_fmt_s(FLUSH_INTERVAL_MAX_S)}s")
            elif seconds != int(seconds):
                errors.append(f"config.qb_traffic.flush_interval: 须为整数秒: {spec['flush_interval']}")
    if "raw_window" in spec:
        _try_time(
            spec["raw_window"], "config.qb_traffic.raw_window", errors, positive=True, min_s=3600, max_s=90 * 86400
        )
    if "rollup_window" in spec:
        # 无 max_s: 保留窗不设上限, 设得足够久(如 3650D)即等效永久保留
        _try_time(spec["rollup_window"], "config.qb_traffic.rollup_window", errors, positive=True, min_s=7 * 86400)
