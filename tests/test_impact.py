"""test_impact 测试计划: 配置变更影响分析(W4 收缩后: diff + R 级重启闸)

被测模块: `config/impact.py` —— 统一挂载口(plan kernel-module-refactor §4.3, W4)落地后,
L0/L1/L2 三张手写级别表退役, 「段变了之后做什么」由各模块 apply 自判(比较与状态同居
组件侧); 本模块只回答内核仍需要的两件事: 变更了哪些顶层段(diff)与哪些段拒绝热应用
(R 闸: state_file/data_dir/fs)。

## 测试计划(每个测试函数一条)
- test_no_changes: 配置相同 -> 空变更列表
- test_scalar_section_change: 顶层段变化 -> 单条变更且携带新旧值
- test_dataclass_section_whole_change: dataclass 段不等 -> 整段一条(粒度 = 段)
- test_r_level_paths: R 级段(state_file/data_dir, 进程身份) -> 变更被检出
- test_new_section_reported: 一侧多出的段(新增配置项)按变更报告(不再有默认 L2 兜底)
- test_one_sided_section_reported: 一侧独有的段(键集不重叠)按变更报告 —— 钉住 diff 用并集而非交集
- test_changes_sorted_by_path: 变更按段名排序(与配置段书写顺序无关)
- test_restart_required_paths: 仅返回命中 R 闸的路径且保持变更顺序
"""
from types import SimpleNamespace

from auto_qb.config.impact import (
    RESTART_SECTIONS,
    ConfigChange,
    diff_config_impacts,
    restart_required_paths,
)
from auto_qb.config.models import Config


def _ns(**kw) -> SimpleNamespace:
    """构造配置替身: diff 只依赖 vars() 浅层字段, 无需真实 Config"""
    return SimpleNamespace(**kw)


def test_no_changes():
    """配置相同 -> 空变更列表"""
    assert diff_config_impacts(Config(), Config()) == []
    same = Config()
    assert diff_config_impacts(same, same) == [], "同一对象也不应产生变更"


def test_scalar_section_change():
    """顶层标量段变化 -> 单条变更且携带新旧值"""
    old, new = Config(), Config()
    new.main_tick = 5.0
    changes = diff_config_impacts(old, new)
    assert len(changes) == 1, changes
    c = changes[0]
    assert c.path == "main_tick"
    assert c.old == 2.0 and c.new == 5.0


def test_dataclass_section_whole_change():
    """dataclass 段不等 -> 整段一条(粒度 = 段; 段内字段展开无消费方, W4 后不再做)"""
    for attr in ("logging", "grouping", "add_episode_tags"):
        old, new = Config(), Config()
        setattr(new, attr, SimpleNamespace(changed="x"))  # 段对象不等 -> 整段一条
        changes = diff_config_impacts(old, new)
        assert [c.path for c in changes] == [attr], f"{attr}: {changes}"


def test_r_level_paths():
    """R 级段(state_file/data_dir, 进程身份)变化被检出(热重载拒绝, 提示重启进程)"""
    old, new = Config(), Config()
    new.state_file = "other/state.json"
    new.data_dir = "other-data"
    changes = diff_config_impacts(old, new)
    assert sorted(c.path for c in changes) == ["data_dir", "state_file"], changes
    assert restart_required_paths(changes) == ["data_dir", "state_file"]


def test_restart_gate_covers_fs_section():
    """R 闸三段: state_file / data_dir / fs(文件访问层单例构造期一次, plan 26-09-27-1407)"""
    assert RESTART_SECTIONS == frozenset(("state_file", "data_dir", "fs"))
    changes = [ConfigChange("fs", {"path_map": {}}, {"path_map": {"r": "x"}})]
    assert restart_required_paths(changes) == ["fs"]


def test_new_section_reported():
    """一侧多出的段(新增配置项)按变更报告 —— 级别表退役后无「默认 L2」兜底,
    新段是否需要动作由认领它的模块 apply 自判(plan §4.3)"""
    a, b = _ns(new_feature=1), _ns(new_feature=2)
    changes = diff_config_impacts(a, b)
    assert [c.path for c in changes] == ["new_feature"]
    assert restart_required_paths(changes) == [], "未命中 R 闸的段不提示重启"


def test_one_sided_section_reported():
    """一侧独有的段(新增/删除配置项)必须报告 —— diff 的键集是**并集**而非交集

    test_new_section_reported 两侧用了**同一个**键名(new_feature), 因此看不出并集与交集的
    区别; 这里用「两侧键集不同」把 union 语义钉死(mutmut 变异 6: `|` -> `&` 的守阵)。
    """
    # 新增段(右侧独有)
    changes = diff_config_impacts(_ns(a=1), _ns(a=1, b=2))
    assert [c.path for c in changes] == ["b"], changes
    # 删除段(左侧独有)
    changes = diff_config_impacts(_ns(a=1, b=2), _ns(a=1))
    assert [c.path for c in changes] == ["b"], changes
    # 两侧完全不重叠
    changes = diff_config_impacts(_ns(alpha=1), _ns(beta=2))
    assert [c.path for c in changes] == ["alpha", "beta"], changes


def test_changes_sorted_by_path():
    """变更按段名排序(与配置段书写无关), 保证前端展示与日志稳定"""
    old, new = Config(), Config()
    new.main_tick = 5.0
    new.interval = 120.0
    new.state_file = "x/state.json"
    paths = [c.path for c in diff_config_impacts(old, new)]
    assert paths == ["interval", "main_tick", "state_file"] == sorted(paths)


def test_restart_required_paths():
    """仅返回命中 R 闸的路径且保持变更顺序(供 CLI/UI 提示需重启进程)"""
    changes = [
        ConfigChange("interval", 1, 2),
        ConfigChange("state_file", "a", "b"),
        ConfigChange("data_dir", "a", "b"),
        ConfigChange("main_tick", 1, 2),
    ]
    assert restart_required_paths(changes) == ["state_file", "data_dir"]
    assert restart_required_paths([ConfigChange("interval", 1, 2)]) == []
