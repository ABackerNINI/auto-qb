"""配置变更影响分析: 递归 diff 新旧配置并判定每项变更的热重载级别

级别模型(热重载分层应用, 见 memory-bank/modules.md 与计划):
- L0 即时生效: 运行时每轮/每次执行时动态读取, 替换 Config 对象字段即生效
  (main_tick/state_save_interval/max_tasks_per_tick/remove_similar_tags/skip_checking_tag/grouping.*/add_episode_tags.*/)
- L1 轻量应用: 需毫秒级副动作(logging 重挂/通知 handler 重挂/qbittorrent 重连/web 重启)
- L2 结构重建: 读取时机在创建/绑定时固化(规则/任务/tracker 匹配), 需重建任务队列与规则
  并对全部记录重匹配 tracker(store 记录/分组/执行历史保留)
- R 重启进程: 进程身份/路径派生类(state_file/data_dir), 热重载拒绝该项

分级用表驱动: 未列出的配置项默认 L2(保守——重建保证生效); 显式声明的 L0/L1 为
"运行时动态读取"的例外白名单(新增配置项时按读取时机补表)。
"""
import ctypes
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

LEVEL_R = "R"
LEVEL_L2 = "L2"
LEVEL_L1 = "L1"
LEVEL_L0 = "L0"

# 顶层配置项级别表(未列出 = L2 保守重建)
SECTION_LEVELS = {
    # L0: 运行时动态读取
    "main_tick": LEVEL_L0,
    "sync_interval": LEVEL_L0,  # 主循环每轮读取的同步节拍阈值, 改值下一轮即生效
    "state_save_interval": LEVEL_L0,  # 主循环每轮到期检查时读取, 改值下一轮即生效
    "max_tasks_per_tick": LEVEL_L0,
    "remove_similar_tags": LEVEL_L0,
    "skip_checking_tag": LEVEL_L0,
    "grouping": LEVEL_L0,
    "add_episode_tags": LEVEL_L0,
    "hr_check": LEVEL_L0,  # 字段级见表 HR_CHECK_FIELD_LEVELS(取数线程每轮从 self.config 现读)
    # L1: 轻量应用
    "logging": LEVEL_L1,
    "notify": LEVEL_L1,
    "qbittorrent": LEVEL_L1,
    "web": LEVEL_L1,
    # L2: 结构重建
    "interval": LEVEL_L2,
    "rules_config": LEVEL_L2,
    "delete_tags": LEVEL_L2,
    "delete_tags_if_has_no_torrents": LEVEL_L2,
    "global_speed_limit_curve": LEVEL_L2,
    # R: 进程身份
    "state_file": LEVEL_R,
    "data_dir": LEVEL_R,
    # trackers: 特殊处理(字段级), 见 _tracker_field_level
    "trackers": None,
}

# trackers.X.<field> 字段级别(tags/移除/限速/hr 运行时动态读; domains/rules/groups 绑定固化:
# groups 经 record.tracker_conf 引用被 tracker_group 条件读取, 热重载需 L2 重匹配才能看到新值;
# hr_check 整段 L0: 刷新管道每轮从 self.config 现读站点配置)
TRACKER_FIELD_LEVELS = {
    "tags": LEVEL_L0,
    "remove_tags": LEVEL_L0,
    "remove_similar_tags": LEVEL_L0,
    "upload_speed_limit": LEVEL_L0,
    "download_speed_limit": LEVEL_L0,
    "hr": LEVEL_L0,
    "hr_check": LEVEL_L0,
    "domains": LEVEL_L2,
    "rules": LEVEL_L2,
    "groups": LEVEL_L2,
}

# hr_check 段内部字段级别(逐字段表, 未列出 = L2 保守)。当前**全部 L0**: 刷新管道每轮现读配置,
# 替换 Config 对象即生效。
# ❗落地取数通道(本地端点 + 取数线程)时, `channel` 与 `shared_dir` 必须改为 LEVEL_L1 ——
#   端点与共享层需「先停旧、等线程退出、再启新」重挂(与 web 段同款), 并在
#   QbManager.apply_new_config 的 L1 分支补上挂载动作; 否则改端口会被当成「已热重载」而实际未生效。
HR_CHECK_FIELD_LEVELS = {
    "enabled": LEVEL_L0,
    "min_torrent_interval": LEVEL_L0,
    "max_torrents_per_hour": LEVEL_L0,
    "max_torrents_per_day": LEVEL_L0,
    "failure_threshold": LEVEL_L0,
    "failure_cooldown": LEVEL_L0,
    "allow_window": LEVEL_L0,
    "unknown_policy": LEVEL_L0,
    "verified_ttl": LEVEL_L0,
    "index_retention": LEVEL_L0,
    "max_download_retries": LEVEL_L0,
    "channel_silence_warn": LEVEL_L0,
    "shared_dir": LEVEL_L0,
    "lock_timeout": LEVEL_L0,
    "poll_interval": LEVEL_L0,
    "parse_missing_rate_max": LEVEL_L0,
    "channel": LEVEL_L0,
}


@dataclass
class ConfigChange:
    """一项配置变更: 字段路径 + 热重载级别 + 新旧值"""

    path: str
    level: str
    old: Any
    new: Any


def _diff_flat(old: Any, new: Any, prefix: str, changes: List[ConfigChange], level: str) -> None:
    """对齐两个 mapping 的键做逐字段 diff(仅比较两侧均存在的嵌套, 其余按整体)"""
    for name in sorted(set(old) | set(new)):
        path = f"{prefix}.{name}"
        old_v, new_v = old.get(name), new.get(name)
        if old_v == new_v:
            continue
        if isinstance(old_v, dict) and isinstance(new_v, dict):
            _diff_flat(old_v, new_v, path, changes, level)
        else:
            changes.append(ConfigChange(path, level, old_v, new_v))


def _diff_trackers(old_t: dict, new_t: dict, changes: List[ConfigChange]) -> None:
    """trackers 段: tracker 增删为 L2; 同名 tracker 逐字段按 TRACKER_FIELD_LEVELS"""
    for name in sorted(set(old_t) | set(new_t)):
        path = f"trackers.{name}"
        old_conf, new_conf = old_t.get(name), new_t.get(name)
        if old_conf is None or new_conf is None:
            changes.append(ConfigChange(path, LEVEL_L2, old_conf, new_conf))
            continue
        if old_conf == new_conf:
            continue
        old_d, new_d = vars(old_conf), vars(new_conf)
        for fname in sorted(set(old_d) | set(new_d)):
            if old_d.get(fname) == new_d.get(fname):
                continue
            level = TRACKER_FIELD_LEVELS.get(fname, LEVEL_L2)
            changes.append(ConfigChange(f"{path}.{fname}", level, old_d.get(fname), new_d.get(fname)))


def _flatten_config(config: Any) -> dict:
    """Config(普通类) -> {段名: 值} 的浅层字典(嵌套 dataclass 保持对象, 由级别表处理)"""
    return {name: getattr(config, name) for name in vars(config)}


def _diff_dataclass_fields(
    old: Any, new: Any, prefix: str, changes: List[ConfigChange], levels: dict, default_level: str
) -> None:
    """两个 dataclass 实例逐字段 diff(未在 levels 中声明的字段按 default_level)"""
    old_d, new_d = vars(old), vars(new)
    for fname in sorted(set(old_d) | set(new_d)):
        if old_d.get(fname) == new_d.get(fname):
            continue
        changes.append(
            ConfigChange(f"{prefix}.{fname}", levels.get(fname, default_level), old_d.get(fname), new_d.get(fname))
        )


def diff_config_impacts(old: Any, new: Any) -> List[ConfigChange]:
    """递归 diff 新旧配置, 返回变更列表(含热重载级别), 按路径排序

    嵌套结构(trackers dict of dataclass / 普通段 dataclass)按级别表展开到字段级;
    未在级别表中声明的项默认 L2(保守: 重建保证生效)。
    """
    changes: List[ConfigChange] = []
    old_d, new_d = _flatten_config(old), _flatten_config(new)
    for name in sorted(set(old_d) | set(new_d)):
        old_v, new_v = old_d.get(name), new_d.get(name)
        if old_v == new_v:
            continue
        if name == "trackers":
            old_t = old_v if isinstance(old_v, dict) else {}
            new_t = new_v if isinstance(new_v, dict) else {}
            _diff_trackers(old_t, new_t, changes)
            continue
        if name == "hr_check":
            level = SECTION_LEVELS.get(name, LEVEL_L2)
            if old_v is None or new_v is None:
                changes.append(ConfigChange(name, level, old_v, new_v))
            else:
                _diff_dataclass_fields(old_v, new_v, name, changes, HR_CHECK_FIELD_LEVELS, LEVEL_L2)
            continue
        level = SECTION_LEVELS.get(name, LEVEL_L2)
        if isinstance(old_v, dict) and isinstance(new_v, dict) and level == LEVEL_L0:
            # L0 段(grouping 等)内字段级 diff, 仅变更字段计入级别
            _diff_flat(old_v, new_v, name, changes, level)
        else:
            changes.append(ConfigChange(name, level, old_v, new_v))
    changes.sort(key=lambda c: c.path)
    return changes


def max_level(changes: List[ConfigChange]) -> str:
    """变更列表中的最高影响级别(无变更返回 L0)"""
    order = {LEVEL_L0: 0, LEVEL_L1: 1, LEVEL_L2: 2, LEVEL_R: 3}
    return max((c.level for c in changes), key=lambda lv: order.get(lv, 99), default=LEVEL_L0)


def restart_required_paths(changes: List[ConfigChange]) -> List[str]:
    return [c.path for c in changes if c.level == LEVEL_R]
