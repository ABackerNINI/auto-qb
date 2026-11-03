"""导出 YAML 配置模板: 找出未配置的 tracker 域名

支持两种模式:
- 追加模式(默认): 将缺失站点条目追加到现有配置后完整导出
- 仅缺失模式(only_missing): 只导出未配置的站点, 生成最小骨架
"""
import logging
import re

import yaml

from ..config import UNLIMITED_SPEED, _strip_none
from ..infra.utils import convert_bool_in_dict, extract_tracker_hostnames
from ..infra.versioning import CURRENT_VERSIONS

logger = logging.getLogger(__name__)


def collect_configured_domains(config) -> set:
    """收集配置中所有 tracker 的域名"""
    configured = set()
    for tracker_conf in config.trackers.values():
        configured.update(tracker_conf.domains)
    return configured


def collect_torrent_tracker_hostnames(api) -> list:
    """逐种子收集 tracker hostname, 每颗种子一个集合(单种查询失败 = 空集, 沿用现状静默跳过)"""
    torrent_sets = []
    for tor in api.torrents_info():
        try:
            trackers_info = api.torrents_trackers(tor.hash)
        except Exception:
            trackers_info = []
        torrent_sets.append(extract_tracker_hostnames(trackers_info))
    return torrent_sets


def collect_all_tracker_hostnames(api) -> set:
    """从所有种子中收集去重的 tracker hostname(api 为 QbApi Facade或兼容客户端)"""
    all_domains = set()
    for host_set in collect_torrent_tracker_hostnames(api):
        all_domains |= host_set
    return all_domains


def find_missing_domains(all_domains: set, configured_domains: set) -> set:
    """筛选出未配置的域名(沿用包含关系匹配)"""
    missing = set()
    for host in all_domains:
        if not any(configured in host or host in configured for configured in configured_domains):
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


def gen_tracker_name(domain: str, taken: set) -> str:
    """生成合法站点名: 非法字符替换为下划线, 与 taken 冲突时加 _N 后缀并就地登记"""
    name = re.sub(r"[^a-zA-Z0-9_]", "_", domain)
    base_name = name
    counter = 1
    while name in taken:
        name = f"{base_name}_{counter}"
        counter += 1
    taken.add(name)
    return name


def build_tracker_entry(domain: str) -> dict:
    """为单个域名生成 tracker 配置条目"""
    return {
        "domains": [domain],
        "tags": [gen_default_tag(domain)],  # 需用户自定义
        "upload_speed_limit": UNLIMITED_SPEED,  # 需用户自定义
        "download_speed_limit": UNLIMITED_SPEED,  # 需用户自定义
        "hr":
            {
                "required_seeding_time": "3D",  # 示例，需用户修改
                "required_share_ratio": 0,
                "extra_seeding_time": "12H",
                "condition": "80%",
                # "exclude_tags": ["noHR"],           # 命中的种子不纳入 HR 管理(支持 regex:/ :ignore_case)
                # "exclude_categories": ["free"],
            },  # 示例，需用户修改; 输出设置(add_tag 等)可覆盖全局 hr:
    }


def group_missing_domains(torrent_sets: list, missing: set) -> list:
    """仅对 missing 域名按种子共现做 union-find: 同一种子内同现即合并, 跨种子传递闭包。

    已配置域名不在 missing 里, 不参与粘合(两个缺失域名不因都碰过某已配置域名而合并)。
    返回每组一个组内 sorted 的域名列表, 组间也 sorted(确定性); 全单元素组时退化为逐域名。
    """
    parent = {domain: domain for domain in missing}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # 路径压缩
            x = parent[x]
        return x

    for hosts in torrent_sets:
        present = sorted(hosts & missing)
        for host in present[1:]:
            root, other = find(present[0]), find(host)
            if root != other:
                parent[max(root, other)] = min(root, other)

    groups = {}
    for domain in missing:
        groups.setdefault(find(domain), []).append(domain)
    return sorted(sorted(group) for group in groups.values())


def build_merged_entry(domains: list, taken: set) -> dict:
    """为一组共现缺失域名生成合并条目: 代表域名 = 组内最短(tie 取字典序)。

    站点名经 gen_tracker_name(代表域名, taken) 生成并就地登记;
    其余字段复用 build_tracker_entry(代表域名), domains 键改写为整组 sorted 列表。
    """
    rep = min(domains, key=lambda d: (len(d), d))
    gen_tracker_name(rep, taken)
    entry = build_tracker_entry(rep)
    entry["domains"] = sorted(domains)
    return entry


def export_yaml_template(api, config, config_path: str, output_path: str, dry_run: bool, only_missing: bool = False):
    """
    生成 YAML 配置模板: 导出种子中未在配置里定义的 tracker 域名。

    only_missing=True 时只导出未配置的站点(最小骨架, 不含已有配置, 便于直接复制);
    否则将缺失条目追加到现有配置后完整导出。
    """
    # 1. 获取所有种子并收集 tracker 域名
    torrents = api.torrents_info()
    logger.info(f"扫描 {len(torrents)} 个种子的 tracker")
    all_domains = collect_all_tracker_hostnames(api)
    logger.info(f"发现 {len(all_domains)} 个去重 tracker 域名")

    # 2. 筛选出未配置的域名
    missing_domains = find_missing_domains(all_domains, collect_configured_domains(config))
    logger.info(f"发现 {len(missing_domains)} 个未配置域名")
    if missing_domains:
        logger.info(f"未配置域名: {missing_domains}")

    # 3. 构建导出内容
    if only_missing:
        # 只导出未配置的站点: 生成最小配置骨架
        export_config = {"config": {"trackers": {}}}
    else:
        # 读取原始配置结构并追加缺失条目(同一文件已经 load_config fail-fast 校验, 仅剔除留空段)
        with open(config_path, "r", encoding="utf-8") as f:
            export_config = _strip_none(yaml.load(f, Loader=yaml.BaseLoader))
        export_config = convert_bool_in_dict(export_config)

    trackers_config = export_config.get("config", {}).get("trackers", {})

    taken = set(trackers_config)
    for domain in sorted(missing_domains):
        trackers_config[gen_tracker_name(domain, taken)] = build_tracker_entry(domain)

    export_config["config"]["trackers"] = trackers_config
    # 写出侧打标(计划 26-09-26-0506): 模板统一带当前 schema 版本, 用户拿去填键即被版本链接管
    export_config["config"]["schema_version"] = CURRENT_VERSIONS["config"]

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
    logger.info(f"已导出 YAML 模板: {output_path}")
