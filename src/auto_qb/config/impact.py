"""配置变更影响分析: 递归 diff 新旧配置 + R 级重启闸(W4 表退役后只留这两件事)

统一挂载口(hot-reload-simplify 方向一, plan kernel-module-refactor §4.3)落地后,
L0/L1/L2 三张手写级别表退役 —— 「哪些段变了之后要做什么」是各模块 apply 的自判知识
(比较与状态同居组件侧, 整段相等即短路); 本模块只回答内核仍需要的两件事:
- diff: 变更了哪些顶层段(路径粒度 = 段), 供零差异判定 / 变更计数 / 回执展示;
- R 闸: 进程身份/路径派生类(state_file/data_dir/fs)拒绝热应用, 提示重启进程。
  (fs: 文件访问层单例按 fs.path_map 在构造期构建一次, plan 26-09-27-1407)

schema_version 等「格式标记」无需特判: 级别表退役后默认语义就是「换对象即生效」,
不再有「未列出默认 L2 触发结构重建」的保守兜底。
"""
from dataclasses import dataclass
from typing import Any, List

# R 级重启闸(热重载拒绝项): 顶层段名
RESTART_SECTIONS = frozenset(
    (
        "state_file",  # 进程身份: state.json 路径
        "data_dir",  # 路径派生: HR 站点文件目录/令牌等从它派生
        "fs",  # 文件访问层单例按 fs.path_map 构造期一次(plan 26-09-27-1407)
    )
)

# 内核自认领段(非模块消费, plan kernel-module-refactor §3.1): 主循环三条时间线与周期落盘
# 计时每轮现读(L0 换对象即生效), qbittorrent 连接管理属内核(段变 apply_new_config 自判重连)。
# R 级三段同属内核面 —— 单点在 RESTART_SECTIONS(R 闸), 段认领完备守阵(P6)取两者并集。
# 新增配置顶层段必须落到「某模块 sections() 认领 or 本表 or RESTART_SECTIONS」之一, 否则
# 守阵 test_modules_p6 红表 + 运行期落「未认领段 WARN + 全量重建兜底」。
KERNEL_SECTIONS = frozenset(
    (
        "main_tick",  # 主循环节拍(run() 每轮现读)
        "sync_interval",  # 同步线节拍(每轮现读, 钳制 <= main_tick)
        "max_tasks_per_tick",  # 任务线速率语义(任务线现读)
        "state_save_interval",  # 周期落盘间隔(maybe_flush 每次现读传入)
        "qbittorrent",  # 连接管理属内核(plan §3.1): 段变自判重连
    )
)


@dataclass
class ConfigChange:
    """一项配置变更: 顶层段路径 + 新旧值(段内嵌套不再展开 —— 级别表退役后无粒度消费方)"""

    path: str
    old: Any
    new: Any


def _flatten_config(config: Any) -> dict:
    """Config(普通类) -> {段名: 值} 的浅层字典(嵌套 dataclass 保持对象, 整段比较)"""
    return {name: getattr(config, name) for name in vars(config)}


def diff_config_impacts(old: Any, new: Any) -> List[ConfigChange]:
    """递归 diff 新旧配置, 返回发生变更的顶层段列表, 按段名排序"""
    changes: List[ConfigChange] = []
    old_d, new_d = _flatten_config(old), _flatten_config(new)
    for name in sorted(set(old_d) | set(new_d)):
        old_v, new_v = old_d.get(name), new_d.get(name)
        if old_v == new_v:
            continue
        changes.append(ConfigChange(name, old_v, new_v))
    return changes


def restart_required_paths(changes: List[ConfigChange]) -> List[str]:
    """R 级闸: 变更段命中重启集合的路径列表(空 = 全部可热应用)"""
    return [c.path for c in changes if c.path in RESTART_SECTIONS]
