"""配置结构与加载: 默认常量 / 数据类 / load_config"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml

from .utils import parse_bool, parse_hr_condition, parse_speed, parse_time

DEFAULT_CONFIG_FILE = "config.yml"
DEFAULT_STATE_FILE = "auto-qb-state.json"

DEFAULT_INTERVAL = "60s"
DEFAULT_REMOVE_SIMILAR_TAGS = False
DEFAULT_CHECK_MISSING_FILES = True

# 全局 HR 默认输出设置(站点 hr 段未设置时使用)
DEFAULT_HR_OUTPUT = {
    "add_tag": "",
    "add_category": "!!HR${required_seeding_time}!!",
    "overwrite_category": False,
    "add_tag_for_satisfied": "",
    "add_category_for_satisfied": "--HR${required_seeding_time}--",
    "overwrite_category_for_satisfied": False,
}

DEFAULT_SKIP_CHECKING_FOR_CROSS_SEEDING = False
DEFAULT_SKIP_CHECKING_AUTO_START = False
DEFAULT_ADD_SKIP_CHECKING_TAGS = False
DEFAULT_SKIP_CHECKING_TAG_FORMAT = "SKIP_CHECKING"

# 种子分组管理(辅种管理): 将指向相同文件列表的种子归为一组, 统一检查
DEFAULT_GROUPING_ENABLED = False
DEFAULT_GROUPING_INTERVAL = "5M"  # 分组检查间隔(拉全量文件列表开销大, 默认降频)
DEFAULT_GROUPING_MISSING_TAG = "MISSING"

UNLIMITED_SPEED = "0KiB/s"


@dataclass
class QbittorrentConfig:
    host: str
    port: int
    username: str
    password: str

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class HRRule:
    """一条 HR 规则(站点级, 已合并全局默认输出设置)

    required_seeding_time: 做种时长要求(秒)
    required_seeding_time_raw: 原始时间字符串(如 "3D"), 用于 ${required_seeding_time} 变量替换
    required_share_ratio: 分享率要求, 0 = 不要求
    extra_seeding_time: 额外做种时间(秒), 做种满 required+extra 视为 "satisfied"
    condition: ('dlratio', ratio) 或 ('dlsize', bytes) 触发条件(下载比例/下载量)
    以下为输出设置(站点覆盖全局后的最终值):
      add_tag / add_category: 满足触发条件时添加的标签/分类(支持 ${required_seeding_time})
      overwrite_category: 添加分类时是否覆盖已有分类
      add_tag_for_satisfied / add_category_for_satisfied: 做种时长已满足要求+额外时间时添加
      overwrite_category_for_satisfied: 同上, 覆盖已有分类
    """
    required_seeding_time: int = 0
    required_seeding_time_raw: str = ""
    required_share_ratio: float = 0.0
    extra_seeding_time: int = 0
    condition: tuple = ("dlratio", 0.8)
    add_tag: str = ""
    add_category: str = ""
    overwrite_category: bool = False
    add_tag_for_satisfied: str = ""
    add_category_for_satisfied: str = ""
    overwrite_category_for_satisfied: bool = False


def parse_hr_spec(spec: dict, global_hr: dict) -> HRRule:
    """解析站点 hr 配置段, 与全局 hr 默认输出设置合并(站点字段优先, 全局兜底)

    站点段: required_seeding_time(必填) / required_share_ratio / extra_seeding_time /
            condition(80% 或 10MiB) + 可覆盖全局的输出字段
    """
    time_raw = str(spec.get("required_seeding_time", "") or "").strip()
    if not time_raw:
        raise ValueError("hr 配置缺少 required_seeding_time")
    # 提取原始时间字符串用于变量替换: "3D" / "12H" / "1.5D"
    raw = time_raw.upper()

    # 输出设置: 站点显式设置优先, 否则用全局默认
    def out(key: str):
        return spec.get(key, global_hr.get(key, DEFAULT_HR_OUTPUT.get(key, "")))

    def out_bool(key: str):
        return parse_bool(spec.get(key, global_hr.get(key, DEFAULT_HR_OUTPUT.get(key, False))))

    return HRRule(
        required_seeding_time=parse_time(raw),
        required_seeding_time_raw=raw,
        required_share_ratio=float(spec.get("required_share_ratio", 0) or 0),
        extra_seeding_time=parse_time(str(spec.get("extra_seeding_time", "0S") or "0S")),
        condition=parse_hr_condition(spec.get("condition", "80%")),
        add_tag=out("add_tag"),
        add_category=out("add_category"),
        overwrite_category=out_bool("overwrite_category"),
        add_tag_for_satisfied=out("add_tag_for_satisfied"),
        add_category_for_satisfied=out("add_category_for_satisfied"),
        overwrite_category_for_satisfied=out_bool("overwrite_category_for_satisfied"),
    )


@dataclass
class TrackerConfig:
    name: str
    domains: List[str]
    tags: List[str]
    remove_tags: List[str]
    upload_limit: Optional[int]  # 字节/秒
    download_limit: Optional[int]  # 字节/秒
    hr: Optional[HRRule] = None  # HR 规则(已合并全局默认输出设置), None = 无 HR 配置
    rules: List[str] = field(default_factory=list)  # 规则引用列表, 如 ["@rule_set", "@rule_set.rule1"]
    remove_similar_tags: bool = False  # 删除类似标签(站点覆盖全局后的值)


@dataclass
class GroupingConfig:
    """种子分组管理(辅种管理): 将指向相同文件列表的种子归为一组

    enabled: 启用分组检查(缺文件检查统一由分组事件驱动承担, 同组共享一次磁盘扫描)
    interval: 已废弃: 分组改为事件驱动(_refresh_torrents 检测到删除/状态变化/保存路径变化立即处理),
              不再创建周期轮询任务; 字段保留仅为配置兼容
    missing_tag: 文件丢失时整组添加的标签
    """
    enabled: bool
    interval: int
    missing_tag: str


@dataclass
class Config:
    interval: int  # 默认任务间隔: 种子列表刷新/种子级内置功能任务的默认 interval, 秒

    state_file: str  # 状态持久化文件(规则执行历史/上传量快照)
    rules_config: dict  # 规则集原始配置: {规则集名: {规则名: spec}}, 来自 config 下 *_rules 段

    remove_similar_tags: bool
    check_missing_files: bool  # 已废弃: 缺文件检查统一由分组事件驱动承担, 字段保留仅为配置兼容

    hr: HRRule  # 全局 HR 默认输出设置(站点 hr 段未设置时兜底; 规则字段为空)

    skip_checking_for_cross_seeding: bool
    skip_checking_auto_start: bool
    add_skip_checking_tags: bool
    skip_checking_tag_format: str

    # 全局标签清理: 彻底删除的标签格式 / 彻底删除无种子的标签格式(均支持正则, regex: 前缀)
    delete_tags: List[str]
    delete_tags_if_has_no_torrents: List[str]

    grouping: GroupingConfig  # 种子分组管理(辅种管理)

    qbittorrent: QbittorrentConfig
    trackers: Dict[str, TrackerConfig]


def load_config(config_path: str) -> Config:
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.load(f, Loader=yaml.BaseLoader)

    cfg = data["config"]
    qb = cfg["qbittorrent"]
    qb_config = QbittorrentConfig(
        host=qb["host"],
        port=int(qb["port"]),
        username=qb["username"],
        password=qb["password"],
    )

    # 规则集: config 段下所有以 "_rules" 结尾的键
    rules_config = {k: v for k, v in cfg.items() if k.endswith("_rules") and isinstance(v, dict)}

    global_hr = cfg.get("hr") or {}
    global_remove_similar = parse_bool(cfg.get("remove_similar_tags", DEFAULT_REMOVE_SIMILAR_TAGS))

    trackers = {}
    for name, tdata in cfg["trackers"].items():
        up = parse_speed(tdata.get("U", UNLIMITED_SPEED))
        down = parse_speed(tdata.get("D", UNLIMITED_SPEED))

        hr = None
        hr_spec = tdata.get("hr")
        if isinstance(hr_spec, dict):
            hr = parse_hr_spec(hr_spec, global_hr)
        trackers[name] = TrackerConfig(
            name=name,
            domains=tdata["domains"],
            tags=tdata.get("tags", []),
            remove_tags=tdata.get("remove_tags", []),
            upload_limit=up,
            download_limit=down,
            hr=hr,
            rules=tdata.get("rules", []) or [],
            remove_similar_tags=parse_bool(tdata.get("remove_similar_tags", global_remove_similar)),
        )

    # 全局标签清理格式: @tracker_tags 引用展开为所有 tracker 配置的 tags 并集
    tracker_tags = sorted({t for tc in trackers.values() for t in tc.tags})
    delete_tags = _expand_tracker_tags_refs(cfg.get("delete_tags", []) or [], tracker_tags)
    delete_tags_if_has_no_torrents = _expand_tracker_tags_refs(
        cfg.get("delete_tags_if_has_no_torrents", []) or [], tracker_tags
    )

    return Config(
        interval=parse_time(cfg.get("interval", DEFAULT_INTERVAL)),
        state_file=cfg.get("state_file", DEFAULT_STATE_FILE),
        rules_config=rules_config,
        remove_similar_tags=global_remove_similar,
        check_missing_files=parse_bool(cfg.get("check_missing_files", DEFAULT_CHECK_MISSING_FILES)),
        hr=HRRule(
            add_tag=global_hr.get("add_tag", DEFAULT_HR_OUTPUT["add_tag"]),
            add_category=global_hr.get("add_category", DEFAULT_HR_OUTPUT["add_category"]),
            overwrite_category=parse_bool(global_hr.get("overwrite_category", DEFAULT_HR_OUTPUT["overwrite_category"])),
            add_tag_for_satisfied=global_hr.get("add_tag_for_satisfied", DEFAULT_HR_OUTPUT["add_tag_for_satisfied"]),
            add_category_for_satisfied=global_hr.get(
                "add_category_for_satisfied", DEFAULT_HR_OUTPUT["add_category_for_satisfied"]
            ),
            overwrite_category_for_satisfied=parse_bool(
                global_hr.get(
                    "overwrite_category_for_satisfied", DEFAULT_HR_OUTPUT["overwrite_category_for_satisfied"]
                )
            ),
        ),
        skip_checking_for_cross_seeding=parse_bool(
            cfg.get(
                "skip_checking_for_cross_seeding",
                DEFAULT_SKIP_CHECKING_FOR_CROSS_SEEDING,
            )
        ),
        skip_checking_auto_start=parse_bool(cfg.get("skip_checking_auto_start", DEFAULT_SKIP_CHECKING_AUTO_START)),
        add_skip_checking_tags=parse_bool(cfg.get("add_skip_checking_tags", DEFAULT_ADD_SKIP_CHECKING_TAGS)),
        skip_checking_tag_format=cfg.get("skip_checking_tag_format", DEFAULT_SKIP_CHECKING_TAG_FORMAT),
        delete_tags=delete_tags,
        delete_tags_if_has_no_torrents=delete_tags_if_has_no_torrents,
        grouping=GroupingConfig(
            enabled=parse_bool(cfg.get("grouping", {}).get("enabled", DEFAULT_GROUPING_ENABLED)),
            interval=parse_time(cfg.get("grouping", {}).get("interval", DEFAULT_GROUPING_INTERVAL)),
            missing_tag=cfg.get("grouping", {}).get("missing_tag", DEFAULT_GROUPING_MISSING_TAG) or
            DEFAULT_GROUPING_MISSING_TAG,
        ),
        qbittorrent=qb_config,
        trackers=trackers,
    )


def _expand_tracker_tags_refs(items: List[str], tracker_tags: List[str]) -> List[str]:
    """展开 @tracker_tags 引用: 替换为所有 tracker 配置的 tags 并集(去重保序)"""
    out: List[str] = []
    seen = set()
    for it in items or []:
        it = str(it).strip()

        ignore_case = ""
        if it.endswith(":ignore_case"):
            ignore_case = ":ignore_case"
            it = it[:-12]

        if it == "@tracker_tags":
            for tag in tracker_tags:
                tag = tag + ignore_case
                if tag not in seen:
                    seen.add(tag)
                    out.append(tag)
        elif it and it not in seen:
            seen.add(it + ignore_case)
            out.append(it + ignore_case)
    return out
