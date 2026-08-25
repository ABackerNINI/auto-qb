"""导出 YAML 配置模板: 找出未配置的 tracker 域名并追加到配置"""
import logging
import re

import yaml

from .config import UNLIMITED_SPEED
from .utils import convert_bool_in_dict, extract_tracker_hostnames

logger = logging.getLogger("PTManager")


def collect_configured_domains(config) -> set:
    """收集配置中所有 tracker 的域名"""
    configured = set()
    for tracker_conf in config.trackers.values():
        configured.update(tracker_conf.domains)
    return configured


def collect_all_tracker_hostnames(client) -> set:
    """从所有种子中收集去重的 tracker hostname"""
    all_domains = set()
    for tor in client.torrents_info():
        try:
            trackers_info = client.torrents_trackers(tor.hash)
        except Exception:
            continue
        all_domains |= extract_tracker_hostnames(trackers_info)
    return all_domains


def find_missing_domains(all_domains: set, configured_domains: set) -> set:
    """筛选出未配置的域名(沿用包含关系匹配)"""
    missing = set()
    for host in all_domains:
        if not any(
            configured in host or host in configured
            for configured in configured_domains
        ):
            missing.add(host)
    return missing


def capitalize_special_tag(text: str) -> str:
    """将字符串中的 "hd"/"pt"(不区分大小写)及其后紧跟的一个字母转为大写"""

    def repl(match):
        prefix = match.group(1).upper()
        suffix = match.group(2)
        return prefix + (suffix.upper() if suffix else "")

    return re.sub(r"(hd|pt)([a-zA-Z])?", repl, text, flags=re.IGNORECASE)


def gen_default_tag(domain: str) -> str:
    """由域名生成默认标签: 倒数第二级域名, 首字母大写并大写hd/pt"""
    parts = domain.split(".")
    if len(parts) < 2:
        return ""
    default_tag = parts[-2]
    if not default_tag or default_tag.isdigit():  # IP地址(如 1.2.3.4)不生成标签
        return ""
    return capitalize_special_tag(default_tag.capitalize())


def build_tracker_entry(domain: str) -> dict:
    """为单个域名生成 tracker 配置条目"""
    return {
        "domains": [domain],
        "tags": [gen_default_tag(domain)],  # 需用户自定义
        "U": UNLIMITED_SPEED,  # 需用户自定义
        "D": UNLIMITED_SPEED,  # 需用户自定义
        "HR": "",  # 示例，需用户修改
    }


def export_yaml_template(client, config, config_path: str, output_path: str, dry_run: bool):
    """
    生成 YAML 配置模板: 导出所有种子中未在配置中定义的 tracker 域名。
    """
    # 1. 获取所有种子并收集 tracker 域名
    torrents = client.torrents_info()
    logger.info(f"Scanning {len(torrents)} torrents for tracker URLs")
    all_domains = collect_all_tracker_hostnames(client)
    logger.info(f"Found {len(all_domains)} unique tracker domains")

    # 2. 筛选出未配置的域名
    missing_domains = find_missing_domains(all_domains, collect_configured_domains(config))
    logger.info(f"Found {len(missing_domains)} missing tracker domains.")
    if missing_domains:
        logger.info(f"Missing tracker domains: {missing_domains}")

    # 3. 读取原始配置结构并追加缺失条目
    with open(config_path, "r", encoding="utf-8") as f:
        export_config = yaml.load(f, Loader=yaml.BaseLoader)
    export_config = convert_bool_in_dict(export_config)

    for domain in sorted(missing_domains):
        # 生成合法名称: 去除点号和横线, 限制为字母数字下划线
        name = re.sub(r"[^a-zA-Z0-9_]", "_", domain)
        base_name = name
        counter = 1
        while name in export_config["config"]["trackers"]:
            name = f"{base_name}_{counter}"
            counter += 1
        export_config["config"]["trackers"][name] = build_tracker_entry(domain)

    # 4. 写入 YAML 文件
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
    logger.info(f"Exported YAML template to {output_path}")
