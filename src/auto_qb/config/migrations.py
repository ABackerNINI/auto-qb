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

v5→v6(计划 26-11-07-0708 S4, 退役键清洗): relocate.finalize_timeout 随旧「setLocation 收尾,
超时判 failed」链退役后已无任何消费者 —— loaders 只读显式键, 残留本无害, 但校验层对未知键
fail-fast, 迁移先把残留键清洗掉(幂等), 逐键产出一条 note 经 migrate_with_notes 落成 WARNING。

v6→v7(计划 26-11-10-0252 S2, 采样间隔键演进): qb_traffic.sample_interval(秒值, 接受时间串)
换成 qb_traffic.sample_interval_multiplier(int 倍数, 倍数 x main_tick = 生效秒数)。旧键在新口径
下是未知键, 校验层 fail-fast, 故迁移先换算: main_tick 从同一 config 树现读(缺失/不可解析兜
2.0, 与 models.Config.main_tick 同源), 倍数 = ceil(旧秒/main_tick) 后钳到 v7 有效秒上限
floor(600/main_tick) 且下限 1(D8); 换算与被钳制均逐键一条 note。旧值不可解析时**保留旧键不动**
(不猜测用户意图), 只交一条 note —— 随后由校验层以未知键/解析错 fail-fast, 不静默曲解(D1)。
未设旧键的配置不动(D9): 默认值由 30s 变为 1 倍即 1 x main_tick, 该行为变更由升级行为本身承担,
迁移不补写新键(补写会把「用户显式选了 1 倍」与「沿默认」混为一谈)。

v7→v8(计划 26-11-11-0259 S2, 顶层 bt_backup 表收编为标量): 旧顶层 bt_backup 多实例表
{"host:port": 路径} 的唯一消费方(bt_backup_path_of)只按当前 qB 连接身份查表 —— 表里第二个
条目永远无人消费, v8 收编为 relocate.bt_backup 单实例标量(D1)。一次性搬运口径(D7):
恰一条非空条目 -> 值搬成 relocate.bt_backup(唯一候选无歧义); 多于一条非空 -> 删键 + note
提示重配(哪个条目对应当前 qB 身份迁移无从得知, 拒绝替用户挑); 全空/无有效值(含整段非字典)
-> 删键 + note 提示重配。旧键缺失 -> 仅抬版本号。无兼容读法(D2): 校验器/加载器只认新形状,
旧形状只存在于本迁移入口。
"""
from math import ceil, floor
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from ..infra.utils import parse_time
from ..infra.versioning import MIGRATIONS
from . import site_presets
from .schema.trackers import HR_OUTPUT_FIELDS

#: 随迁的微调项(旧键 -> sites 条目同键名直搬); 页面事实四键一律丢弃
_MIGRATE_TUNING_KEYS = (
    "hr_page_scopes", "refresh_interval", "max_pages_per_refresh", "completed_age_limit", "max_torrents_per_hour"
)


def _url_host(url: Any) -> str:
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

    - 全局段: 删除 20 个废弃键(以 _V3_DROP_GLOBAL_KEYS 实数为准); min_torrent_interval
      改名 min_interval(语义接管页面间隔)。
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


def _migrate_config_3_4(cfg: dict) -> dict | Tuple[dict, List[str]]:
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


def _migrate_config_4_5(cfg: dict) -> dict | Tuple[dict, List[str]]:
    """v4→v5: 把「顶层 global_traffic_monitor 段 + 曲线段内联 traffic_source」合并为顶层 traffic_source 段

    - 旧曲线段内联数据源 global_speed_limit_curve.traffic_source[].traffic_monitor.dat_path ->
      config.traffic_source.traffic_monitor.dat_path; 曲线段内的 traffic_source 键删除,
      其余键(interval/enabled/curves)原样保留。
    - 旧 config.global_traffic_monitor 段: 仅把 notify_cooldown_s 迁到
      config.traffic_source.global_traffic_monitor.notify_cooldown_s; enabled / tool_url /
      tool_token_path / subscribe / autostart 一律删除; 整段从 config 删除(该段在 v5 退休)。
    - provider 推导: 旧 global_traffic_monitor 段存在(非空) -> "global_traffic_monitor";
      否则 -> "traffic_monitor"。
      !已知不精确(R2 记录, 未改行为): 推导只看"段是否存在", 不看旧段的 enabled —— 旧段
      `enabled: false`(用户显式关过联动)也会被推成 global_traffic_monitor, 即取数来源被静默
      切走。测试期按计划 26-10-17-0339 R2 的口径手工处理(改 config.yml 的 provider); 已升级到
      v5 的配置不会重跑本迁移, 故此处不改判据 —— 改了只影响尚未升级的机器, 收益小于引入
      "同一版本号两种迁移结果"的风险。
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

# ---- v5→v6: 退役键 relocate.finalize_timeout 清洗(计划 26-11-07-0708 S4) ----


def _migrate_config_5_6(cfg: dict) -> dict | Tuple[dict, List[str]]:
    """v5→v6: 移除退役键 relocate.finalize_timeout(收尾已改走 fastresume 改写链, 键无任何消费者)

    loaders 只读显式键, 残留本无害; 但 validation._check_unknown_keys 对未知键 fail-fast ——
    迁移(load 在 validate 之前)先把残留清洗掉再进校验。幂等: 无该键(relocate 缺席/非字典/
    已是 v6 形状)时零副作用, 返回裸 dict(框架两种返回形态都接受); 有该键时产出一条人读
    note(经 migrate_with_notes 落成 WARNING), 让用户知道配置面少了一键且其本无行为效果。
    """
    relocate = cfg.get("relocate")
    if isinstance(relocate, dict) and "finalize_timeout" in relocate:
        del relocate["finalize_timeout"]
        return cfg, ["config.relocate.finalize_timeout: 已移除(退役键无消费者, 改动它本无任何行为效果; 收尾现走 fastresume 改写链)"]
    return cfg


MIGRATIONS["config"][5] = _migrate_config_5_6

# ---- v6→v7: qb_traffic 采样间隔键演进 sample_interval(秒) -> sample_interval_multiplier(倍数)(计划 26-11-10-0252) ----

#: main_tick 缺失/不可解析时的兜底(秒), 与 models.Config.main_tick 字段默认同值
_DEFAULT_MAIN_TICK_S = 2.0

#: v7 有效采样秒数上限(倍数 x main_tick <= 本值)。刻意在本模块冻结一份快照而非 import
#: validation.sections.SAMPLE_INTERVAL_MAX_S —— 迁移是历史快照, 校验上限日后若调整不应回头
#: 改写已完成版本的历史换算结果。
_V7_SAMPLE_INTERVAL_MAX_S = 600.0


def _migrate_config_6_7(cfg: dict) -> dict | Tuple[dict, List[str]]:
    """v6→v7: qb_traffic.sample_interval(秒值) 换算为 sample_interval_multiplier(int 倍数)

    - 旧键缺席(qb_traffic 非字典 / 无 sample_interval) -> 原样返回裸 dict, 零副作用(D9:
      未设旧键者不补写新键, 默认由 30s 变为 1 x main_tick 属升级行为本身的行为变更)。
    - 旧值解析失败 -> 旧键原地保留 + 一条 note(不猜测用户意图; 校验层随后以未知键 fail-fast,
      符合 D1「不静默曲解」)。
    - 换算(D8): mult = max(1, min(ceil(旧秒/main_tick), floor(600/main_tick))) —— 非整除向上
      取整(采样更密, 不丢数据点); 超出 v7 有效秒上限时钳到 floor, main_tick > 600s 时 floor 为 0,
      由 max(1, ...) 兜成 1 并在 note 里明说该配置下上限不可满足。
    - 幂等: 旧键删除后重放即走「旧键缺席」分支, 零 diff。
    """
    qbt = cfg.get("qb_traffic")
    if not isinstance(qbt, dict) or "sample_interval" not in qbt:
        return cfg
    old_raw = qbt["sample_interval"]
    try:
        old_s = parse_time(old_raw)
    except (TypeError, ValueError):
        return cfg, [
            f"config.qb_traffic.sample_interval: 旧值 {old_raw!r} 无法解析为时间, 旧键保留未改动, "
            "请手工改为 config.qb_traffic.sample_interval_multiplier(int 倍数, 生效秒数 = 倍数 x main_tick)"
        ]

    main_tick = _DEFAULT_MAIN_TICK_S
    raw_tick = cfg.get("main_tick")
    if raw_tick is not None:
        try:
            main_tick = parse_time(raw_tick)
        except (TypeError, ValueError):
            main_tick = _DEFAULT_MAIN_TICK_S
    if main_tick <= 0:  # 空串经 parse_time 得 0: 不做除数, 回退默认(校验层随后会报 main_tick 非法)
        main_tick = _DEFAULT_MAIN_TICK_S

    wanted = ceil(old_s / main_tick)
    cap = floor(_V7_SAMPLE_INTERVAL_MAX_S / main_tick)
    mult = max(1, min(wanted, cap))
    qbt["sample_interval_multiplier"] = int(mult)
    del qbt["sample_interval"]

    note = (
        "config.qb_traffic.sample_interval -> config.qb_traffic.sample_interval_multiplier: "
        f"旧值 {old_raw!r}({old_s:g}s) 按 main_tick={main_tick:g}s 换算为 {mult} 倍"
        f"(实际生效 {mult * main_tick:g}s)"
    )
    if cap < 1:
        note += "; main_tick 超过 600s, v7 的有效秒上限在该配置下不可满足, 倍数置 1"
    elif wanted > cap:
        note += f"; 原换算 {wanted} 倍超出 v7 有效秒上限(600s), 已钳制到 {mult} 倍"
    return cfg, [note]


MIGRATIONS["config"][6] = _migrate_config_6_7

# ---- v7→v8: 顶层 bt_backup 多实例表收编为 relocate.bt_backup 单实例标量(计划 26-11-11-0259 S2) ----


def _migrate_config_7_8(cfg: dict) -> dict | Tuple[dict, List[str]]:
    """v7→v8: 旧顶层 bt_backup 表 {"host:port": 路径} 一次性搬成 relocate.bt_backup 标量(D7)

    - 旧键缺席 -> 原样返回裸 dict, 零副作用(仅抬版本号, 由框架盖章)。
    - 恰一条非空条目(值为 strip 后非空的字符串) -> 值搬成 relocate.bt_backup + 一条 note
      (唯一候选, 无歧义可猜); 新位置已有非空值时新位置获胜, 旧值只丢弃(v1→v2 新旧并存同款,
      不覆盖用户已显式写好的标量)。
    - 多于一条非空 / 全空或无有效值(含整段非字典的畸形形状) -> 删键 + note 提示重配(D7 不猜:
      多实例表里哪个条目对应当前 qB 连接身份, 迁移无从得知 —— 表的唯一消费方只按当前身份查,
      猜错条目 = 把 fastresume 收尾静默指到别人的 BT_backup)。
    - 幂等: 旧键删除后重放即走「旧键缺席」分支, 零 diff。
    """
    if "bt_backup" not in cfg:
        return cfg
    legacy = cfg.pop("bt_backup")
    valid = [(key, value.strip()) for key, value in legacy.items()
             if isinstance(value, str) and value.strip()] if isinstance(legacy, dict) else []
    if len(valid) == 1:
        key, path = valid[0]
        relocate = cfg.get("relocate")
        if not isinstance(relocate, dict):
            relocate = {}  # 段缺失即建; 畸形形状(v7 校验层本会拒)按 v1→v2 建 hr_check 同款重建
            cfg["relocate"] = relocate
        if str(relocate.get("bt_backup") or "").strip():
            return cfg, [
                f"config.bt_backup[{key!r}]: 已移除(relocate.bt_backup 已有显式配置, 新位置获胜; "
                f"旧值 {path!r} 未搬运, 如需以它为准请自行改 config.relocate.bt_backup)"
            ]
        relocate["bt_backup"] = path
        return cfg, [f"config.bt_backup[{key!r}] -> config.relocate.bt_backup: 旧表唯一非空条目已收编为单实例标量(值 {path!r})"]
    if len(valid) > 1:
        return cfg, [
            f"config.bt_backup: 已移除(旧表有 {len(valid)} 条非空条目, 无法判定哪条对应当前 qB 实例, 不做猜测搬运; "
            "如需启用 fastresume 收尾, 请在 config.relocate.bt_backup 手工填写该实例的 BT_backup 路径)"
        ]
    return cfg, [
        "config.bt_backup: 已移除(旧表无有效条目; 如需启用 fastresume 收尾, "
        "请在 config.relocate.bt_backup 手工填写该实例的 BT_backup 路径)"
    ]


MIGRATIONS["config"][7] = _migrate_config_7_8
