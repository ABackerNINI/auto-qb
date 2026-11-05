"""导出 YAML 配置模板: 找出未配置的 tracker 域名

支持两种模式:
- 追加模式(默认): 将缺失站点条目追加到现有配置后完整导出
- 仅缺失模式(only_missing): 只导出未配置的站点, 生成最小骨架
"""
import logging
import re
from typing import Any, List, Tuple

import yaml

from ..config import UNLIMITED_SPEED, Config, _strip_none
from ..infra.errors import TrackerScanBatchError
from ..infra.utils import convert_bool_in_dict, extract_tracker_hostnames
from ..infra.versioning import CURRENT_VERSIONS

logger = logging.getLogger(__name__)


def collect_configured_domains(config: Config) -> set:
    """收集配置中所有 tracker 的域名"""
    configured = set()
    for tracker_conf in config.trackers.values():
        configured.update(tracker_conf.domains)
    return configured


def collect_torrent_tracker_hostnames_with_failures(api: Any) -> Tuple[List[set], int]:
    """逐种子收集 tracker hostname, 返回 (torrent_sets, 失败数) 二元组

    单种查询失败 = 该种空集 + 失败数 +1(沿用现状静默容忍单种); 但批量失败(qB 断连/重启等
    系统性故障)同样被吞成空集, 会冒充「没有缺失站点」静默漏站(issue 26-11-04-2347), 所以
    把失败数交给调用方按 tracker_scan_batch_failed(WebUI/CLI 共用单一判据)裁决, 不在本函数
    内自行抛错。
    走 Facade 的 fresh 直查旁路记录级惰性缓存(issue 26-11-04-0228): 扫描是低频事件,
    缓存只被产品自身 tracker 写操作失效, qB 侧改 tracker 后二次扫描会吃到首扫旧值;
    非 Facade 客户端(测试桩/兼容客户端)没有 fresh 方法, 回退普通 torrents_trackers。
    """
    fetch_trackers = getattr(api, "torrents_trackers_fresh", None) or api.torrents_trackers
    torrent_sets = []
    failed_count = 0
    for tor in api.torrents_info():
        try:
            trackers_info = fetch_trackers(tor.hash)
        except Exception:
            trackers_info = []
            failed_count += 1
        torrent_sets.append(extract_tracker_hostnames(trackers_info))
    return torrent_sets, failed_count


def collect_torrent_tracker_hostnames(api: Any) -> List[set]:
    """逐种子收集 tracker hostname, 每颗种子一个集合(单种查询失败 = 空集, 沿用现状静默跳过)

    需要感知批量失败的调用方(WebUI /api/sites/missing 与 --export-yaml)走
    collect_torrent_tracker_hostnames_with_failures 拿失败数; fresh 直查旁路说明见其 docstring。
    """
    torrent_sets, _ = collect_torrent_tracker_hostnames_with_failures(api)
    return torrent_sets


def tracker_scan_batch_failed(failed_count: int, torrent_count: int) -> bool:
    """批量失败判据(WebUI 与 CLI 共用的单一判据): 有种子且逐种 tracker 查询失败过半(严格多数)

    单种失败属预期容忍(种子被删/瞬时错误); 过半失败基本只能是 qB 断连/重启等系统性故障,
    此时吞成空集 = 静默漏站 —— 宁可报错也不出「没有缺失站点」的假结果(issue 26-11-04-2347)。
    """
    return torrent_count > 0 and failed_count * 2 > torrent_count


def collect_all_tracker_hostnames(api: Any) -> set:
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
    def repl(match: re.Match[str]) -> str:
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

    def find(x: str) -> str:
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

    groups: dict[str, list[str]] = {}
    for domain in missing:
        groups.setdefault(find(domain), []).append(domain)
    return sorted(sorted(group) for group in groups.values())


def build_merged_entry(domains: list, taken: set) -> tuple:
    """为一组共现缺失域名生成合并条目: 代表域名 = 组内最短(tie 取字典序)。

    返回 (name, entry) 二元组: name = gen_tracker_name(代表域名, taken) 生成的站点名
    (已就地登记进 taken); entry 其余字段复用 build_tracker_entry(代表域名),
    domains 键改写为整组 sorted 列表。
    """
    rep = min(domains, key=lambda d: (len(d), d))
    name = gen_tracker_name(rep, taken)
    entry = build_tracker_entry(rep)
    entry["domains"] = sorted(domains)
    return name, entry


def export_yaml_template(
    api: Any,
    config: Config,
    config_path: str,
    output_path: str,
    dry_run: bool,
    only_missing: bool = False,
    split_trackers: bool = False,
) -> None:
    """
    生成 YAML 配置模板: 导出种子中未在配置里定义的 tracker 域名。

    only_missing=True 时只导出未配置的站点(最小骨架, 不含已有配置, 便于直接复制);
    否则将缺失条目追加到现有配置后完整导出。
    split_trackers=False(默认)时同一颗种子共现的缺失域名合并为一个站点;
    True 拆回逐域名(行为与改造前一致)。
    """
    # 1. 获取所有种子并收集 tracker 域名(逐种集合保留, 共现分组复用同一次逐种遍历)
    torrents = api.torrents_info()
    logger.info(f"扫描 {len(torrents)} 个种子的 tracker")
    torrent_sets, failed_count = collect_torrent_tracker_hostnames_with_failures(api)
    if tracker_scan_batch_failed(failed_count, len(torrent_sets)):
        # 批量失败(过半)拒绝出结果: 空结果会被当成「无缺失站点」静默漏站(issue 26-11-04-2347);
        # CLI 经 main() 的 AutoQbError 出口 stderr 干净退出 + 退出码 1
        raise TrackerScanBatchError(
            f"扫描 qB tracker 批量失败({failed_count}/{len(torrent_sets)} 颗种子查询报错), "
            f"导出结果不可信(会静默漏站): 请检查 qB 连接后重试"
        )
    all_domains = set()
    for host_set in torrent_sets:
        all_domains |= host_set
    logger.info(f"发现 {len(all_domains)} 个去重 tracker 域名")

    # 2. 筛选出未配置的域名
    missing_domains = find_missing_domains(all_domains, collect_configured_domains(config))
    logger.info(f"发现 {len(missing_domains)} 个未配置域名")
    if missing_domains:
        logger.info(f"未配置域名: {missing_domains}")

    # 3. 构建导出内容
    if only_missing:
        # 只导出未配置的站点: 生成最小配置骨架
        export_config: dict[str, Any] = {"config": {"trackers": {}}}
    else:
        # 读取原始配置结构并追加缺失条目(同一文件已经 load_config fail-fast 校验, 仅剔除留空段)
        with open(config_path, "r", encoding="utf-8") as f:
            export_config = _strip_none(yaml.load(f, Loader=yaml.BaseLoader))
        export_config = convert_bool_in_dict(export_config)

    trackers_config = export_config.get("config", {}).get("trackers", {})

    taken = set(trackers_config)
    if split_trackers:
        # 拆分路径(= 改造前行为): 逐域名一条
        for domain in sorted(missing_domains):
            trackers_config[gen_tracker_name(domain, taken)] = build_tracker_entry(domain)
    else:
        # 默认合并: 同一颗种子共现的缺失域名并为一个站点(全单元素组时退化为逐域名)
        for group in group_missing_domains(torrent_sets, missing_domains):
            name, entry = build_merged_entry(group, taken)
            trackers_config[name] = entry

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
