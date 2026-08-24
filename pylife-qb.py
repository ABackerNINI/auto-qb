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

DEFAULT_CONFIG_FILE = "config.yml"


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
    upload_limit: Optional[int]  # 字节/秒
    download_limit: Optional[int]  # 字节/秒
    hr_rule: Optional[str]  # HR规则字符串

    _upload_limit_raw: Optional[str]
    _download_limit_raw: Optional[str]


@dataclass
class Config:
    interval: int
    qbittorrent: QbittorrentConfig
    trackers: Dict[str, TrackerConfig]


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


def parse_time(time_str: str) -> int:
    """将时间字符串（如 '3D', '12H'）转换为秒"""
    if not time_str:
        return 0
    units = {
        "H": 3600,
        "D": 86400,
        "W": 604800,
        "M": 2592000,  # 30天
        "Y": 31536000,  # 365天
    }
    pattern = re.compile(r"^([\d.]+)\s*([HDWMY])$", re.IGNORECASE)
    match = pattern.match(time_str.strip().upper())
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")
    value, unit = match.groups()
    return int(float(value) * units[unit])


def parse_hr_rule(rule_str: str) -> Tuple[int, Optional[Tuple[str, float]], int]:
    """
    解析HR规则字符串，返回 (required_time_seconds, condition, extra_time_seconds)
    condition: 可以是 ('ratio', value) 或 ('upload', value_in_bytes) 或 None
    示例: "3D@70%+12H" -> (3D秒数, ('ratio', 0.7), 12H秒数)
         "20H@30%"    -> (20H秒数, ('ratio', 0.3), 0)
         "20H@10MB"   -> (20H秒数, ('upload', 10MB字节), 0)
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
        if cond_part.endswith("%"):
            ratio = float(cond_part[:-1]) / 100.0
            condition = ("ratio", ratio)
        else:
            # 假设是上传量，如 "10MB"
            upload_bytes = parse_speed(cond_part)  # 复用速度解析，但去掉/s
            # 但 parse_speed 需要 "10MiB/s"，我们去掉最后的 /s
            # 简单处理：提取数字和单位
            pattern = re.compile(r"^([\d.]+)\s*([KMG]?i?B)$", re.IGNORECASE)
            match = pattern.match(cond_part.strip())
            if not match:
                raise ValueError(f"Invalid condition format: {cond_part}")
            value, unit = match.groups()
            # 单位转换为字节
            units = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3}
            upload_bytes = int(float(value) * units[unit])
            condition = ("upload", upload_bytes)
    else:
        required_time = parse_time(main.strip())
        condition = None  # 仅时间要求，无分享率/上传量要求（但通常PT需要分享率，我们视为100%分享率？）
        # 根据用户说明，默认80%触发，所以我们设默认ratio=0.8
        condition = ("ratio", 0.8)

    return required_time, condition, extra_time


def load_config(config_path: str) -> Config:
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    cfg = data["config"]
    qb = cfg["qbittorrent"]
    qb_config = QbittorrentConfig(
        host=qb["host"],
        port=qb["port"],
        username=qb["username"],
        password=qb["password"],
    )

    trackers = {}
    for name, tdata in cfg["trackers"].items():
        up = parse_speed(tdata.get("U", "0")) if "U" in tdata else None
        down = parse_speed(tdata.get("D", "0")) if "D" in tdata else None
        trackers[name] = TrackerConfig(
            name=name,
            domains=tdata["domains"],
            tags=tdata.get("tags", []),
            upload_limit=up,
            download_limit=down,
            hr_rule=tdata.get("HR"),
            _upload_limit_raw=tdata.get("U", "") if "U" in tdata else None,
            _download_limit_raw=tdata.get("D", "") if "D" in tdata else None,
        )

    return Config(
        interval=cfg.get("interval", 60), qbittorrent=qb_config, trackers=trackers
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

    def run(self):
        """主循环"""
        if not self.connect():
            return

        self.logger.info(f"Starting PT manager with interval {self.config.interval}s")
        while True:
            try:
                self._process_all_torrents()
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
            time.sleep(self.config.interval)

    def _process_all_torrents(self):
        """获取所有种子并处理"""
        torrents = self.client.torrents_info()
        self.logger.info(f"Processing {len(torrents)} torrents")
        for tor in torrents:
            try:
                # Print each torrent for debugging
                # print(tor)
                # print()
                self._process_single_torrent(tor)
            except Exception as e:
                self.logger.error(f"Error processing torrent {tor.hash}: {e}")

    def _process_single_torrent(self, tor: TorrentDictionary):
        """处理单个种子"""
        # 1. 检查文件丢失（先做，若丢失则暂停并分类，跳过其他）
        if self._check_and_handle_missing_files(tor):
            return  # 已处理，跳过后续

        # 2. 匹配 tracker 配置
        tracker_conf = self._match_tracker(tor)
        if not tracker_conf:
            return  # 未匹配，不处理

        # 3. 添加标签
        self._add_tags(tor, tracker_conf.tags)

        # 4. 应用限速
        # self._apply_limits(tor, tracker_conf.upload_limit, tracker_conf.download_limit)

        # 5. 处理 HR 规则
        # if tracker_conf.hr_rule:
        #     self._handle_hr(tor, tracker_conf.hr_rule)

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

    def _add_tags(self, tor: TorrentDictionary, tags: List[str]):
        """为种子添加标签（若不存在）"""
        if not tags:
            return
        current_tags = set(tor.tags.split(",")) if tor.tags else set()
        new_tags = [t for t in tags if t not in current_tags]
        if new_tags:
            self.client.torrents_add_tags(tags=new_tags, torrent_hashes=tor.hash)
            self.logger.info(f"Added tags {new_tags} to {tor.hash}")

    def _apply_limits(
        self, tor: TorrentDictionary, up_limit: Optional[int], down_limit: Optional[int]
    ):
        """设置种子的上传/下载限速"""
        if up_limit is not None and tor.upload_limit != up_limit:
            self.client.torrents_set_upload_limit(tor.hash, upload_limit=up_limit)
            self.logger.info(f"Set upload limit {up_limit} for {tor.hash}")
        if down_limit is not None and tor.download_limit != down_limit:
            self.client.torrents_set_download_limit(tor.hash, download_limit=down_limit)
            self.logger.info(f"Set download limit {down_limit} for {tor.hash}")

    def _handle_hr(self, tor: TorrentDictionary, rule_str: str):
        """处理 HR 规则：添加 HR tag，检查是否满足 HR-DONE"""
        required_time, condition, extra_time = parse_hr_rule(rule_str)

        # 检查做种时间是否满足
        seeding_time = tor.seeding_time  # 秒
        if seeding_time < required_time:
            return  # 时间不足，不添加任何 HR tag

        # 检查条件（分享率或上传量）
        condition_met = False
        if condition is None:
            condition_met = True
        else:
            cond_type, cond_value = condition
            if cond_type == "ratio":
                ratio = tor.ratio if tor.downloaded > 0 else float("inf")
                condition_met = ratio >= cond_value
            elif cond_type == "upload":
                condition_met = tor.uploaded >= cond_value

        if not condition_met:
            return

        # 满足基础 HR 条件，添加 HR tag
        # 从规则中提取时间部分用于 tag，如 "3D" -> "HR3D"
        time_part = re.match(r"^([\d.]+[HDWMY])", rule_str)
        hr_tag = f"HR{time_part.group(1)}" if time_part else "HR"
        self._add_tags(tor, [hr_tag])

        # 检查额外时间是否满足（+12H等）
        if extra_time > 0 and seeding_time >= required_time + extra_time:
            # 满足 HR-DONE 条件
            self._mark_hr_done(tor)

    def _mark_hr_done(self, tor: TorrentDictionary):
        """标记种子为 HR-DONE 分类并强制汇报"""
        if tor.category != "HR-DONE":
            self.client.torrents_set_category(tor.hash, category="HR-DONE")
            self.logger.info(f"Marked {tor.hash} as HR-DONE")
        # 强制汇报
        self.client.torrents_reannounce(tor.hash)
        self.logger.info(f"Reannounced {tor.hash}")

    def _check_and_handle_missing_files(self, tor: TorrentDictionary) -> bool:
        """
        检查种子文件是否存在，如果已完成但文件缺失，则暂停并添加分类"丢失"
        返回 True 表示已处理（已暂停），否则 False
        """
        # 只处理已完成的种子
        if tor.amount_left > 0:
            return False

        # 获取文件列表
        files = self.client.torrents_files(tor.hash)
        save_path = tor.save_path
        missing = False
        for f in files:
            # 组合完整路径
            full_path = os.path.join(save_path, f.name)
            if not os.path.exists(full_path):
                missing = True
                break

        if missing:
            # 暂停种子
            if tor.state != "pausedUP" and tor.state != "pausedDL":
                self.client.torrents_pause(tor.hash)
                self.logger.info(f"Paused {tor.hash} due to missing files")
            # 添加分类"丢失"
            if tor.category != "丢失":
                self.client.torrents_set_category(tor.hash, category="丢失")
                self.logger.info(f"Set category '丢失' for {tor.hash}")
            return True
        return False

    # ---------- 导出未配置的 Tracker 模板 ----------

    def export_missing_trackers(self, output_path: str):
        """
        导出所有种子中未在配置中定义的 tracker 域名，生成 YAML 配置模板。
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

        if not missing_domains:
            self.logger.info("No missing trackers found. Nothing to export.")
            return

        self.logger.info(f"Found {len(missing_domains)} missing tracker domains.")
        self.logger.info(f"Missing tracker domains: {missing_domains}")

        # 4. 构建新的配置结构
        # 保留原有的 interval 和 qbittorrent 设置
        export_config = {
            "config": {
                "interval": self.config.interval,
                "qbittorrent": {
                    "host": self.config.qbittorrent.host,
                    "port": self.config.qbittorrent.port,
                    "username": self.config.qbittorrent.username,
                    "password": self.config.qbittorrent.password,
                },
                "trackers": {},
            }
        }

        # 先复制已有的 trackers
        for name, tracker_conf in self.config.trackers.items():
            export_config["config"]["trackers"][name] = {
                "domains": tracker_conf.domains,
                "tags": [",".join(tracker_conf.tags)],
                "U": tracker_conf._upload_limit_raw if tracker_conf._upload_limit_raw else "-1KiB/s",
                "D": (
                    tracker_conf._download_limit_raw if tracker_conf._download_limit_raw else "-1KiB/s"
                ),
                "HR": tracker_conf.hr_rule or "",
            }

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
            default_name = f"{domain.split('.')[-2]}"

            export_config["config"]["trackers"][name] = {
                "domains": [domain],
                "tags": [default_name],  # 需用户自定义
                "U": "-1KiB/s",  # 需用户自定义
                "D": "-1KiB/s",  # 需用户自定义
                "HR": "",  # 示例，需用户修改
            }

        # 5. 写入 YAML 文件
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(export_config, f, allow_unicode=True, sort_keys=False, indent=2)
        self.logger.info(f"Exported missing tracker template to {output_path}")


# ======================== 主入口 ========================


def main():
    parser = argparse.ArgumentParser(description="PT Seed Manager for qBittorrent")
    parser.add_argument(
        "config", nargs='?', default=DEFAULT_CONFIG_FILE, help="Path to configuration YAML file"
    )
    parser.add_argument(
        "--export-missing",
        "-e",
        metavar="OUTPUT",
        help="Export missing tracker templates to OUTPUT file and exit",
    )
    args = parser.parse_args()

    manager = PTManager(args.config)

    if args.export_missing:
        # 导出模式
        manager.export_missing_trackers(args.export_missing)
        return

    # 正常运行模式
    try:
        manager.run()
    except KeyboardInterrupt:
        logging.info("Shutting down...")


if __name__ == "__main__":
    main()
