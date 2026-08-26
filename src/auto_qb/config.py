"""配置结构与加载: 默认常量 / 数据类 / load_config"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml

from .utils import parse_bool, parse_speed, parse_time

DEFAULT_CONFIG_FILE = "config.yml"
DEFAULT_STATE_FILE = "auto-qb-state.json"

DEFAULT_INTERVAL = "60s"
DEFAULT_TICK_INTERVAL = "2s"  # 主循环 tick 间隔: 慢速队列(异步校验)轮询粒度
DEFAULT_REMOVE_SIMILAR_TAGS = False
DEFAULT_CHECK_MISSING_FILES = True

DEFAULT_ADD_HR_TAGS = False
DEFAULT_HR_TAG_FORMAT = "!!HR${time}!!"

DEFAULT_ADD_HR_CATEGORIES = False
DEFAULT_HR_CATEGORY_FORMAT = "!!HR${time}!!"
DEFAULT_OVERWRITE_CATEGORY_FOR_HR = False

DEFAULT_SKIP_CHECKING_FOR_CROSS_SEEDING = False
DEFAULT_SKIP_CHECKING_AUTO_START = False
DEFAULT_ADD_SKIP_CHECKING_TAGS = False
DEFAULT_SKIP_CHECKING_TAG_FORMAT = "SKIP_CHECKING"

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
class TrackerConfig:
    name: str
    domains: List[str]
    tags: List[str]
    remove_tags: List[str]
    upload_limit: Optional[int]  # 字节/秒
    download_limit: Optional[int]  # 字节/秒
    hr_rule: Optional[str]  # HR规则字符串
    rules: List[str] = field(default_factory=list)  # 规则引用列表, 如 ["@rule_set", "@rule_set.rule1"]


@dataclass
class Config:
    interval: int
    tick_interval: int  # 主循环 tick 间隔(慢速队列轮询粒度), 秒

    state_file: str  # 状态持久化文件(规则执行历史/上传量快照)
    rules_config: dict  # 规则集原始配置: {规则集名: {规则名: spec}}, 来自 config 下 *_rules 段

    remove_similar_tags: bool
    check_missing_files: bool

    add_hr_tags: bool
    hr_tag_format: str

    add_hr_categories: bool
    hr_category_format: str
    overwrite_category_for_hr: bool

    skip_checking_for_cross_seeding: bool
    skip_checking_auto_start: bool
    add_skip_checking_tags: bool
    skip_checking_tag_format: str

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

    trackers = {}
    for name, tdata in cfg["trackers"].items():
        up = parse_speed(tdata.get("U", UNLIMITED_SPEED))
        down = parse_speed(tdata.get("D", UNLIMITED_SPEED))
        trackers[name] = TrackerConfig(
            name=name,
            domains=tdata["domains"],
            tags=tdata.get("tags", []),
            remove_tags=tdata.get("remove_tags", []),
            upload_limit=up,
            download_limit=down,
            hr_rule=tdata.get("HR"),
            rules=tdata.get("rules", []) or [],
        )

    return Config(
        interval=parse_time(cfg.get("interval", DEFAULT_INTERVAL)),
        tick_interval=parse_time(cfg.get("tick_interval", DEFAULT_TICK_INTERVAL)),
        state_file=cfg.get("state_file", DEFAULT_STATE_FILE),
        rules_config=rules_config,
        remove_similar_tags=parse_bool(cfg.get("remove_similar_tags", DEFAULT_REMOVE_SIMILAR_TAGS)),
        check_missing_files=parse_bool(cfg.get("check_missing_files", DEFAULT_CHECK_MISSING_FILES)),
        add_hr_tags=parse_bool(cfg.get("add_hr_tags", DEFAULT_ADD_HR_TAGS)),
        hr_tag_format=cfg.get("hr_tag_format", DEFAULT_HR_TAG_FORMAT),
        add_hr_categories=parse_bool(cfg.get("add_hr_categories", DEFAULT_ADD_HR_CATEGORIES)),
        hr_category_format=cfg.get("hr_category_format", DEFAULT_HR_CATEGORY_FORMAT),
        overwrite_category_for_hr=parse_bool(cfg.get("overwrite_category_for_hr", DEFAULT_OVERWRITE_CATEGORY_FOR_HR)),
        skip_checking_for_cross_seeding=parse_bool(
            cfg.get(
                "skip_checking_for_cross_seeding",
                DEFAULT_SKIP_CHECKING_FOR_CROSS_SEEDING,
            )
        ),
        skip_checking_auto_start=parse_bool(cfg.get("skip_checking_auto_start", DEFAULT_SKIP_CHECKING_AUTO_START)),
        add_skip_checking_tags=parse_bool(cfg.get("add_skip_checking_tags", DEFAULT_ADD_SKIP_CHECKING_TAGS)),
        skip_checking_tag_format=cfg.get("skip_checking_tag_format", DEFAULT_SKIP_CHECKING_TAG_FORMAT),
        qbittorrent=qb_config,
        trackers=trackers,
    )
