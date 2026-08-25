#!/usr/bin/env python3
"""
PT Seed Manager for qBittorrent
自动管理 PT 种子的工具，包括添加标签、限速、HR 标记、文件丢失检测等。
支持导出未配置的 tracker 模板。
"""

import os
import time
import re
import logging
import argparse
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from urllib.parse import urlparse

import yaml
from qbittorrentapi import Client, TorrentDictionary

# TODO: 优化性能
# TODO: 拆分成多文件

# TODO: use dict to store global config?

DEFAULT_CONFIG_FILE = "config.yml"

DEFAULT_INTERVAL = "60s"
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

# ======================== 配置结构与解析 ========================


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


@dataclass
class Config:
    interval: int

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


def parse_bool(value: str | bool) -> bool:
    """将字符串转换为布尔值"""
    if isinstance(value, bool):
        return value

    if value.lower() in ["true", "1"]:
        return True
    elif value.lower() in ["false", "0"]:
        return False
    else:
        raise ValueError(f"Invalid boolean value: {value}")


def convert_bool_in_dict(d: dict):
    """递归地将字典中的字符串布尔值转换为bool类型"""
    if isinstance(d, str):
        try:
            d = parse_bool(d)
        except ValueError:
            pass

    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, str) and not v.isdecimal():
                d[k] = convert_bool_in_dict(v)
            elif isinstance(v, dict):
                d[k] = convert_bool_in_dict(v)
            elif isinstance(v, list):
                d[k] = [convert_bool_in_dict(item) for item in v]
                pass

    return d


def parse_speed(speed_str: str) -> int:
    """将速度字符串（如 '10MiB/s'）转换为字节/秒"""
    if not speed_str:
        return 0
    units = {
        "B/s": 1,
        "KiB/s": 1024,
        "MiB/s": 1024**2,
        "GiB/s": 1024**3,
    }
    pattern = re.compile(r"^([\d.]+)\s*([KMG]?i?B/s)$", re.IGNORECASE)
    match = pattern.match(speed_str.strip())
    if not match:
        raise ValueError(f"Invalid speed format: {speed_str}")
    value, unit = match.groups()
    return int(float(value) * units[unit])


def parse_fsize(fsize_str: str) -> int:
    """将文件大小字符串（如 '10.5 GiB'）转换为字节"""
    units = {
        "B": 1,
        "KiB": 1024,
        "MiB": 1024**2,
        "GiB": 1024**3,
        "TiB": 1024**4,
        "PiB": 1024**5,
    }
    pattern = re.compile(r"^([\d.]+)\s*([KMGTP]?iB)$", re.IGNORECASE)
    match = pattern.match(fsize_str.strip().upper())
    if not match:
        raise ValueError(f"Invalid file size format: {fsize_str}")
    value, unit = match.groups()
    return int(float(value) * units[unit])


def parse_time(time_str: str) -> int:
    """将时间字符串（如 '3D', '12H'）转换为秒"""
    if not time_str:
        return 0
    units = {"S": 1, "M": 60, "H": 3600, "D": 86400}
    pattern = re.compile(r"^([\d.]+)\s*([SMHD])$", re.IGNORECASE)
    match = pattern.match(time_str.strip().upper())
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")
    value, unit = match.groups()
    return int(float(value) * units[unit])


def parse_hr_rule(rule_str: str) -> Tuple[int, Tuple[str, float], int]:
    """
    解析HR规则字符串，返回 (required_time_seconds, condition, extra_time_seconds)
    condition: 可以是 ('dlratio', value) 或 ('dlsize', value_in_bytes) 或 None
    示例: "3D@70%+12H" -> (3D秒数, ('dlratio', 0.7), 12H秒数)
         "20H@30%"    -> (20H秒数, ('dlratio', 0.3), 0)
         "20H@10MB"   -> (20H秒数, ('dlsize', 10MB字节), 0)
    """

    extra_time = 0
    if "+" in rule_str:
        main, extra = rule_str.split("+", 1)
        extra_time = parse_time(extra.strip())
    else:
        main = rule_str

    if "@" in main:
        time_part, cond_part = main.split("@", 1)
        required_time = parse_time(time_part.strip())
        cond_part = cond_part.strip()
        if cond_part.endswith("%"):  # 百分比, 如 "10%"
            ratio = float(cond_part[:-1]) / 100.0
            condition = ("dlratio", ratio)
        else:  # 下载量，如 "10MiB"
            download_bytes = parse_fsize(cond_part)
            condition = ("dlsize", download_bytes)
    else:
        required_time = parse_time(main.strip())
        # 根据用户说明，默认80%触发，所以我们设默认ratio=0.8
        condition = ("dlratio", 0.8)

    return required_time, condition, extra_time


def capitalize_special_tag(text: str) -> str:
    """
    将字符串中的 "hd" 或 "pt"（不区分大小写）转为大写，
    并将其后紧跟的一个字母（如果存在）也转为大写。
    """

    def repl(match):
        prefix = match.group(1).upper()  # "HD" 或 "PT"
        suffix = match.group(2)  # 紧跟的字母（可能为 None）
        return prefix + (suffix.upper() if suffix else "")

    # 匹配 "hd" 或 "pt"（忽略大小写），后面可跟一个字母（a-zA-Z）
    pattern = r"(hd|pt)([a-zA-Z])?"
    return re.sub(pattern, repl, text, flags=re.IGNORECASE)


def gen_default_tag(domain: str):
    """
    给域名生成默认标签名称, 默认标签名称为倒数第二级域名, 如: www.example.com -> example.
    首字母大写并大写"hd", "pt"等常见词
    """
    # 生成默认名称: 域名倒数第二级
    default_tag = f"{domain.split('.')[-2]}"

    if not default_tag:
        return ""

    # 首字母大写
    default_tag = default_tag.capitalize()

    # 将default_tag中的"hd", "pt"以及紧跟的字母替换成大写
    default_tag = capitalize_special_tag(default_tag)

    return default_tag


def add_long_path_prefix_for_win(path: str) -> str:
    """
    为 Windows 文件路径添加长路径支持前缀, 解决路径过长或特殊字符问题
    """
    # 1. 将相对路径转为绝对路径 (Windows API 要求 \\?\ 后必须为绝对路径)
    abs_path = os.path.abspath(path)

    # 2. 统一替换正斜杠为反斜杠 (\\?\ 前缀强制要求使用反斜杠)
    abs_path = abs_path.replace("/", "\\")

    # 3. 如果已经有前缀，直接返回
    if abs_path.startswith("\\\\?\\"):
        return abs_path

    # 4. 判断是否为 UNC (网络共享) 路径，例如 \\server\share\file
    # 注意：UNC 路径必须以两个反斜杠开头
    if abs_path.startswith("\\\\"):
        # 去除开头的两个反斜杠，拼接为 \\?\UNC\server\share\file
        # 例如：\\\\server\share -> abs_path[1:] 是 \server\share
        return "\\\\?\\UNC" + abs_path[1:]
    else:
        # 普通本地盘符路径，例如 C:\folder\file
        return "\\\\?\\" + abs_path


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
        )

    return Config(
        interval=parse_time(cfg.get("interval", DEFAULT_INTERVAL)),
        remove_similar_tags=parse_bool(
            cfg.get("remove_similar_tags", DEFAULT_REMOVE_SIMILAR_TAGS)
        ),
        check_missing_files=parse_bool(
            cfg.get("check_missing_files", DEFAULT_CHECK_MISSING_FILES)
        ),
        add_hr_tags=parse_bool(cfg.get("add_hr_tags", DEFAULT_ADD_HR_TAGS)),
        hr_tag_format=cfg.get("hr_tag_format", DEFAULT_HR_TAG_FORMAT),
        add_hr_categories=parse_bool(
            cfg.get("add_hr_categories", DEFAULT_ADD_HR_CATEGORIES)
        ),
        hr_category_format=cfg.get("hr_category_format", DEFAULT_HR_CATEGORY_FORMAT),
        overwrite_category_for_hr=parse_bool(
            cfg.get("overwrite_category_for_hr", DEFAULT_OVERWRITE_CATEGORY_FOR_HR)
        ),
        skip_checking_for_cross_seeding=parse_bool(
            cfg.get(
                "skip_checking_for_cross_seeding",
                DEFAULT_SKIP_CHECKING_FOR_CROSS_SEEDING,
            )
        ),
        skip_checking_auto_start=parse_bool(
            cfg.get("skip_checking_auto_start", DEFAULT_SKIP_CHECKING_AUTO_START)
        ),
        add_skip_checking_tags=parse_bool(
            cfg.get("add_skip_checking_tags", DEFAULT_ADD_SKIP_CHECKING_TAGS)
        ),
        skip_checking_tag_format=cfg.get(
            "skip_checking_tag_format", DEFAULT_SKIP_CHECKING_TAG_FORMAT
        ),
        qbittorrent=qb_config,
        trackers=trackers,
    )


# ======================== 管理器主类 ========================


class PTManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.client = None
        self._setup_logging()
        # 缓存已处理的哈希，避免重复操作（但为了简单，每次检查）
        # 也可用set记录已经添加过HR tag或done的hash，但考虑到需要持续检查，我们用状态判断

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger("PTManager")

    def connect(self) -> bool:
        """连接 qBittorrent"""
        try:
            self.client = Client(
                host=self.config.qbittorrent.base_url,
                username=self.config.qbittorrent.username,
                password=self.config.qbittorrent.password,
            )
            self.client.auth_log_in()
            self.logger.info("Connected to qBittorrent successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to qBittorrent: {e}")
            return False

    def run(self, dry_run: bool):
        """主循环"""
        if not self.connect():
            return

        self.logger.info(f"Starting PT manager with interval {self.config.interval}s")
        while True:
            try:
                self._process_all_torrents(dry_run)
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
            time.sleep(self.config.interval)

    def _process_all_torrents(self, dry_run: bool):
        """获取所有种子并处理"""
        torrents = self.client.torrents_info()
        self.logger.info(f"Processing {len(torrents)} torrents")

        # Print each torrent for debugging
        # with open("torrents.txt", "w", encoding="utf-8") as f:
        #     for tor in torrents:
        #         print(tor, file=f)
        #         print("", file=f)

        for tor in torrents:
            try:
                self._process_single_torrent(tor, dry_run)
            except Exception as e:
                self.logger.error(f"Error processing torrent {tor.hash}: {e}")

    def _process_single_torrent(self, tor: TorrentDictionary, dry_run: bool):
        """处理单个种子"""
        # 1. 检查文件丢失（先做，若丢失则暂停并分类，跳过其他）
        if self.config.check_missing_files:
            if self._check_and_handle_missing_files(tor, dry_run):
                return  # 已处理，跳过后续

        # 2. 辅种跳检
        if self.config.skip_checking_for_cross_seeding:
            self._skip_checking_for_cross_seeding(tor, dry_run)

        # 3. 匹配 tracker 配置
        tracker_conf = self._match_tracker(tor)
        if not tracker_conf:
            return  # 未匹配，不处理

        # 4. 添加标签
        self._add_tags(tor, tracker_conf.tags, dry_run)

        # 5. 删除标签
        self._remove_tags(tor, tracker_conf.remove_tags, dry_run)

        # 6. 删除相似标签
        if self.config.remove_similar_tags:
            self._remove_similar_tags(tor, tracker_conf.tags, dry_run)

        # 7. 应用限速
        # self._apply_limits(tor, tracker_conf.upload_limit, tracker_conf.download_limit, dry_run)

        # 8. 处理 HR 规则
        if tracker_conf.hr_rule and (
            self.config.add_hr_tags or self.config.add_hr_categories
        ):
            self._add_hr_tag_or_category(tor, tracker_conf.hr_rule, dry_run)

    # ---------- 辅助方法 ----------

    def _match_tracker(self, tor: TorrentDictionary) -> Optional[TrackerConfig]:
        """
        根据种子的 tracker URLs 匹配配置中的 tracker
        返回第一个匹配的 TrackerConfig，若无匹配则返回 None
        """
        trackers_info = self.client.torrents_trackers(tor.hash)
        tracker_urls = [t["url"] for t in trackers_info if t.get("url")]

        for conf in self.config.trackers.values():
            for domain in conf.domains:
                for url in tracker_urls:
                    if domain in url:  # 简单包含匹配
                        return conf
        return None

    def _add_tags(self, tor: TorrentDictionary, tags: List[str], dry_run: bool):
        """为种子添加标签（若不存在）"""
        if not tags:
            return

        current_tags = (
            set(part.strip() for part in tor.tags.split(",")) if tor.tags else set()
        )
        new_tags = [t for t in tags if t not in current_tags]
        if new_tags:
            if not dry_run:
                self.client.torrents_add_tags(tags=new_tags, torrent_hashes=tor.hash)
            self.logger.info(f"Added tags '{new_tags}' to '{tor.name}'")

    def _remove_tags(
        self, tor: TorrentDictionary, tags_to_remove: List[str], dry_run: bool
    ):
        """为种子删除标签"""
        if not tags_to_remove:
            return

        current_tags = (
            set(part.strip() for part in tor.tags.split(",")) if tor.tags else set()
        )
        tags_to_remove = set(tags_to_remove) & current_tags
        if tags_to_remove:
            if not dry_run:
                self.client.torrents_remove_tags(
                    tags=tags_to_remove, torrent_hashes=tor.hash
                )
            self.logger.info(f"Removed tags '{tags_to_remove}' from '{tor.name}'")

    def _remove_similar_tags(
        self, tor: TorrentDictionary, tags: List[str], dry_run: bool
    ):
        """删除类似(单词相同大小写不同)的tag"""
        if not tags:
            return

        current_tags = (
            set(part.strip() for part in tor.tags.split(",")) if tor.tags else set()
        )

        # 删除单词相同但大小写不一致的标签
        for tag in current_tags:
            if tag.lower() in [t.lower() for t in tags] and tag not in tags:
                if not dry_run:
                    self.client.torrents_remove_tags(tags=tag, torrent_hashes=tor.hash)
                self.logger.info(f"Removed similar tag '{tag}' from '{tor.name}'")

    def _apply_limits(
        self, tor: TorrentDictionary, up_limit: int, down_limit: int, dry_run: bool
    ):
        """设置种子的上传/下载限速"""
        if up_limit >= 0 and tor.upload_limit != up_limit:
            if not dry_run:
                self.client.torrents_set_upload_limit(tor.hash, upload_limit=up_limit)
            self.logger.info(f"Set upload limit {up_limit} for '{tor.name}'")
        if down_limit >= 0 and tor.download_limit != down_limit:
            if not dry_run:
                self.client.torrents_set_download_limit(
                    tor.hash, download_limit=down_limit
                )
            self.logger.info(f"Set download limit {down_limit} for '{tor.name}'")

    def _add_hr_tag_or_category(
        self, tor: TorrentDictionary, rule_str: str, dry_run: bool
    ):
        """添加HR标签或分类"""
        required_time, condition, extra_time = parse_hr_rule(rule_str)

        # 检查下载条件, 主要为了排除辅种
        condition_met = False

        cond_type, cond_value = condition
        if cond_type == "dlratio":
            dlratio = tor.downloaded / tor.total_size
            condition_met = dlratio >= cond_value
        elif cond_type == "dlsize":
            condition_met = tor.downloaded >= cond_value

        if not condition_met:
            return

        # 满足基础 HR 条件，添加 HR tag
        # 从规则中提取时间部分，如 "3D" -> "HR3D"
        time_part = re.match(r"^([\d.]+[SMHD])", rule_str)
        if not time_part:
            raise ValueError(f"Invalid rule format: '{rule_str}'")

        # 添加 HR tag
        if self.config.add_hr_tags:
            hr_tag = self.config.hr_tag_format.replace("${time}", time_part.group(1))
            self._add_tags(tor, [hr_tag], dry_run)

        # 添加 HR 分类
        if self.config.add_hr_categories:
            hr_category = self.config.hr_category_format.replace(
                "${time}", time_part.group(1)
            )
            self._set_category(
                tor, hr_category, self.config.overwrite_category_for_hr, dry_run
            )

    def _set_category(
        self, tor: TorrentDictionary, category: str, overwrite: bool, dry_run: bool
    ):
        """设置种子的分类"""
        old_category = tor.category.strip()

        if old_category == category:  # 分类已存在
            return

        if not old_category or overwrite:  # 分类为空或者强制覆盖
            self._create_category_if_not_exists(category, dry_run)

            # 设置分类
            if not dry_run:
                self.client.torrents_set_category(
                    category=category, torrent_hashes=tor.hash
                )

            # 打印日志
            if old_category:
                self.logger.info(
                    f"Set category from '{old_category}' to '{category}' for '{tor.name}'"
                )
            else:
                self.logger.info(f"Set category to '{category}' for '{tor.name}'")
        else:  # 存在分类但不覆盖
            self.logger.warning(
                f"Skipping '{tor.name}' as it already has category '{old_category}'"
            )

    def _create_category_if_not_exists(self, category: str, dry_run: bool):
        """如果分类不存在则创建分类"""
        current_categories = self.client.torrents_categories()
        if category not in current_categories:  # 分类不存在
            if not dry_run:
                self.client.torrents_create_category(name=category)
            self.logger.info(f"Created category '{category}'")

    def _mark_hr_done(self, tor: TorrentDictionary, dry_run: bool):
        """标记种子为 HR-DONE 分类并强制汇报"""
        if tor.category != "HR-DONE":
            if not dry_run:
                self.client.torrents_set_category(tor.hash, category="HR-DONE")
            self.logger.info(f"Marked {tor.hash} as HR-DONE")
        # 强制汇报
        if not dry_run:
            self.client.torrents_reannounce(tor.hash)
        self.logger.info(f"Reannounced {tor.hash}")

    def _check_and_handle_missing_files(
        self, tor: TorrentDictionary, dry_run: bool
    ) -> bool:
        """
        检查种子文件是否存在，如果已完成但文件缺失，则暂停并添加标签"MISSING"
        返回 True 表示已处理（已暂停），否则 False
        """
        # 只处理已完成且正在做种的种子
        if tor.amount_left > 0 or not tor.state_enum.is_uploading:
            return False

        # 获取文件列表
        files = self.client.torrents_files(tor.hash)
        save_path = tor.save_path
        missing = False
        for f in files:
            # 组合完整路径, 添加长路径前缀
            full_path = add_long_path_prefix_for_win(
                os.path.normpath(os.path.join(save_path, f.name))
            )

            if not os.path.exists(full_path):  # 查看文件是否存在
                self.logger.warning(
                    f"File missing: '{full_path}' of torrent '{tor.name}'!"
                )
                missing = True
                break

            if os.path.getsize(full_path) != f.size:  # 比较文件大小
                self.logger.warning(
                    f"File size mismatch: '{full_path}' of torrent '{tor.name}', expected {f.size}, got {os.path.getsize(full_path)}!"
                )
                missing = True
                break

        if missing:
            # 暂停种子
            if not dry_run:
                self.client.torrents_stop(tor.hash)
            self.logger.warning(f"Paused {tor.hash} due to missing files")

            # 设置标签
            self._add_tags(tor, ["MISSING"], dry_run)
            return True
        return False

    def _skip_checking_for_cross_seeding(self, tor: TorrentDictionary, dry_run: bool):
        """
        辅种任务跳过检查并自动开始, 添加跳检标签.
        下载量/完成量/进度为0 且 状态为暂停stop 的种子视为辅种任务.
        """

        if tor.downloaded > 0:  # 下载量必须为0
            return False

        if tor.completed != 0:  # 完成量必须为0
            return False

        if tor.progress != 0:  # 进度必须为0
            return False

        if not tor.state_enum.is_stopped:  # 必须是停止状态
            return False

        # 对文件进行简单检查: 确保所有文件都存在且大小一致
        files = self.client.torrents_files(tor.hash)
        save_path = tor.save_path
        missing = False
        for f in files:
            # 组合完整路径, 添加长路径前缀
            full_path = add_long_path_prefix_for_win(
                os.path.normpath(os.path.join(save_path, f.name))
            )

            if not os.path.exists(full_path):  # 查看文件是否存在
                # self.logger.warning(
                #     f"File missing: '{full_path}' of torrent '{tor.name}'!"
                # )
                missing = True
                break

            if os.path.getsize(full_path) != f.size:  # 比较文件大小
                # self.logger.warning(
                #     f"File size mismatch: '{full_path}' of torrent '{tor.name}', expected {f.size}, got {os.path.getsize(full_path)}!"
                # )
                missing = True
                break

        if missing:
            # self.logger.info(
            #     f"Torrent '{tor.name}' is missing some files"
            # )
            return

        self.logger.info(f"Skip checking for torrent '{tor.name}'")

        # 获取种子的关键属性，以便重新添加时保留
        save_path = tor.save_path
        category = tor.category
        tags = tor.tags
        # 注意：此处未保留上传/下载限速等高级设置，如有需要可自行添加

        # 重要：从 qBittorrent 中导出 .torrent 文件
        # 这是为了保留 tracker 等信息
        if not dry_run:
            torrent_file_data = self.client.torrents_export(torrent_hash=tor.hash)
        self.logger.info(f"  Exporting torrent")

        # 删除原种子（注意：不要删除已下载的数据文件）
        if not dry_run:
            self.client.torrents_delete(torrent_hashes=tor.hash, delete_files=False)
        self.logger.info(f"  Deleting torrent")

        # --- 4. 使用“跳过校验”选项重新添加 ---
        # is_skip_checking=True 即为跳过哈希校验的关键参数[reference:3][reference:4]
        if not dry_run:
            self.client.torrents_add(
                torrent_files=torrent_file_data,  # 使用导出的 .torrent 文件数据
                save_path=save_path,  # 恢复原保存路径
                category=category,  # 恢复原分类
                tags=tags,  # 恢复原标签
                is_skip_checking=True,  # 核心：跳过校验！
                is_paused=False,  # 添加后自动开始
            )
        self.logger.info(f"  Re-adding torrent")

        # 开始刚添加的种子
        if self.config.skip_checking_auto_start:
            if not dry_run:
                self.client.torrents_start(torrent_hashes=tor.hash)
            self.logger.info(f"  Starting torrent")

        # 添加跳检标签
        if self.config.add_skip_checking_tags:
            self._add_tags(tor, [self.config.skip_checking_tag_format], dry_run)

        return True

    # ---------- 导出YAML配置模板 ----------

    def export_yaml_template(self, output_path: str, dry_run: bool):
        """
        生成 YAML 配置模板: 导出所有种子中未在配置中定义的 tracker 域名。
        """

        if not self.connect():
            self.logger.error("Cannot export: qBittorrent connection failed")
            return

        # 1. 获取所有种子
        torrents = self.client.torrents_info()
        self.logger.info(f"Scanning {len(torrents)} torrents for tracker URLs")

        # 2. 收集所有种子的 tracker 域名（去重）
        all_domains: Set[str] = set()
        for tor in torrents:
            trackers_info = self.client.torrents_trackers(tor.hash)
            for t in trackers_info:
                url = t.get("url")
                if not url:
                    continue
                try:
                    parsed = urlparse(url)
                    host = parsed.hostname
                    if host:
                        all_domains.add(host)
                except Exception:
                    continue

        self.logger.info(f"Found {len(all_domains)} unique tracker domains")

        # 3. 筛选出未配置的域名
        configured_domains: Set[str] = set()
        for tracker_conf in self.config.trackers.values():
            for domain in tracker_conf.domains:
                configured_domains.add(domain)

        missing_domains: Set[str] = set()
        for host in all_domains:
            # 检查是否匹配已配置的任意 domain（沿用包含关系）
            matched = False
            for configured in configured_domains:
                if configured in host or host in configured:
                    matched = True
                    break
            if not matched:
                missing_domains.add(host)

        # if not missing_domains:
        #     self.logger.info("No missing trackers found. Nothing to export.")
        #     return

        self.logger.info(f"Found {len(missing_domains)} missing tracker domains.")

        if missing_domains:
            self.logger.info(f"Missing tracker domains: {missing_domains}")

        # 4. 构建新的配置结构
        export_config = None

        # 从配置文件中读取原始配置结构
        with open(self.config_path, "r", encoding="utf-8") as f:
            export_config = yaml.load(f, Loader=yaml.BaseLoader)

        # 转换字符串布尔值
        export_config = convert_bool_in_dict(export_config)

        # 添加缺失的 tracker 条目（每个域名一个条目）
        for domain in sorted(missing_domains):
            # 生成一个合法的名称：去除点号和横线，限制为字母数字下划线
            name = re.sub(r"[^a-zA-Z0-9_]", "_", domain)
            # 如果名称冲突，添加后缀
            base_name = name
            counter = 1
            while name in export_config["config"]["trackers"]:
                name = f"{base_name}_{counter}"
                counter += 1

            # 生成默认名称: 域名倒数第二级
            default_tag = gen_default_tag(domain)

            export_config["config"]["trackers"][name] = {
                "domains": [domain],
                "tags": [default_tag],  # 需用户自定义
                "U": UNLIMITED_SPEED,  # 需用户自定义
                "D": UNLIMITED_SPEED,  # 需用户自定义
                "HR": "",  # 示例，需用户修改
            }

        # 5. 写入 YAML 文件
        if not dry_run:
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    export_config,
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=4,
                    explicit_start=True,
                )
        self.logger.info(f"Exported YAML template to {output_path}")


# ======================== 主入口 ========================


def main():
    parser = argparse.ArgumentParser(description="PT Seed Manager for qBittorrent")
    parser.add_argument(
        "config",
        nargs="?",
        default=DEFAULT_CONFIG_FILE,
        help="Path to configuration YAML file",
    )
    parser.add_argument(
        "--export-yaml",
        "-e",
        metavar="OUTPUT",
        help="Export YAML templates to OUTPUT file and exit",
    )
    parser.add_argument("--dry-run", "-n", action="store_true", help="Dry run")
    args = parser.parse_args()

    manager = PTManager(args.config)

    if args.export_yaml:
        # 导出模式
        manager.export_yaml_template(args.export_yaml, args.dry_run)
        return

    # 正常运行模式
    try:
        manager.run(args.dry_run)
    except KeyboardInterrupt:
        logging.info("Shutting down...")


if __name__ == "__main__":
    main()
