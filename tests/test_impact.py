"""test_impact 测试计划: 配置变更影响分析(热重载分级)

被测模块: `config/impact.py` —— 递归 diff 新旧配置, 为每项变更判定热重载级别
(L0 即时 / L1 轻量 / L2 结构重建 / R 需重启进程), 供 WEB UI 保存设置与热重载消费。

## 测试计划(每个测试函数一条)
- test_no_changes: 配置相同 -> 空变更列表
- test_l0_scalar_change: L0 运行时动态读取项(main_tick) -> 单条 L0 且携带新旧值
- test_l1_section_change: L1 轻量应用段(logging/notify/qbittorrent/web) -> 整段单条 L1
- test_l2_default_section: 未在级别表声明的段默认 L2(保守: 重建保证生效)
- test_r_level_paths: R 级段(state_file/data_dir, 进程身份) -> R
- test_l0_dict_section_field_diff: L0 段为纯 dict 时字段级 diff(未变更字段不入结果)
- test_l0_dataclass_section_whole_change: L0 段为 dataclass(真实 Config)时整段一条 L0
- test_dict_section_nested_recursive: dict 段嵌套递归展开到叶子路径
- test_dict_section_type_change: 一侧变非 dict -> 该路径整体一条变更
- test_tracker_added_or_removed: tracker 增删 -> 整项 L2(old/new 一侧为 None)
- test_tracker_field_levels: 同名 tracker 逐字段按 TRACKER_FIELD_LEVELS 定级
- test_tracker_unknown_field_defaults_l2: tracker 未声明字段 -> L2
- test_tracker_unchanged_no_change: tracker 内容相同 -> 不产生变更(多站点中仅未变的不入结果)
- test_changes_sorted_by_path: 变更按路径排序(与配置段书写顺序无关)
- test_max_level: 最高影响级别(空 -> L0; 混合 -> R)
- test_max_level_unknown_level_is_highest: 未知级别视为最高(保守, 顺序表外值判 99)
- test_restart_required_paths: 仅返回 R 级路径且保持变更顺序
"""
from types import SimpleNamespace

from auto_qb.config.impact import (
    LEVEL_L0,
    LEVEL_L1,
    LEVEL_L2,
    LEVEL_R,
    ConfigChange,
    diff_config_impacts,
    max_level,
    restart_required_paths,
)
from auto_qb.config.models import Config, TrackerConfig


def _ns(**kw) -> SimpleNamespace:
    """构造配置替身: diff 只依赖 vars() 浅层字段, 无需真实 Config"""
    return SimpleNamespace(**kw)


def test_no_changes():
    """配置相同 -> 空变更列表"""
    assert diff_config_impacts(Config(), Config()) == []
    same = Config()
    assert diff_config_impacts(same, same) == [], "同一对象也不应产生变更"


def test_l0_scalar_change():
    """L0 运行时动态读取项(main_tick) -> 单条 L0 且携带新旧值"""
    old, new = Config(), Config()
    new.main_tick = 5.0
    changes = diff_config_impacts(old, new)
    assert len(changes) == 1, changes
    c = changes[0]
    assert (c.path, c.level) == ("main_tick", LEVEL_L0)
    assert c.old == 2.0 and c.new == 5.0


def test_l1_section_change():
    """L1 轻量应用段(logging/notify/qbittorrent/web) -> 整段单条 L1(不展开字段级)"""
    for attr, section in (
        ("logging", "logging"),
        ("notify", "notify"),
        ("qbittorrent", "qbittorrent"),
        ("web", "web"),
    ):
        old, new = Config(), Config()
        setattr(new, attr, SimpleNamespace(some_field="changed"))  # 段对象整体不等 -> 整段一条
        changes = diff_config_impacts(old, new)
        assert [(c.path, c.level) for c in changes] == [(section, LEVEL_L1)], f"{attr}: {changes}"


def test_l2_default_section():
    """未在级别表声明的段默认 L2(保守: 重建保证生效)"""
    old, new = Config(), Config()
    new.interval = 120.0
    assert [(c.path, c.level) for c in diff_config_impacts(old, new)] == [("interval", LEVEL_L2)]
    # 表外字段(模拟新增配置项未补表) -> 同样默认 L2
    a, b = _ns(new_feature=1), _ns(new_feature=2)
    assert [(c.path, c.level) for c in diff_config_impacts(a, b)] == [("new_feature", LEVEL_L2)]


def test_r_level_paths():
    """R 级段(state_file/data_dir, 进程身份) -> R(热重载拒绝, 提示重启进程)"""
    old, new = Config(), Config()
    new.state_file = "other/state.json"
    new.data_dir = "other-data"
    changes = diff_config_impacts(old, new)
    assert sorted((c.path, c.level) for c in changes) == [
        ("data_dir", LEVEL_R),
        ("state_file", LEVEL_R),
    ], changes


def test_l0_dict_section_field_diff():
    """L0 段为纯 dict 时字段级 diff(未变更字段不入结果, 仅变更字段计入 L0)"""
    old = _ns(grouping={"enabled": True, "missing_tag": "MISSING"})
    new = _ns(grouping={"enabled": False, "missing_tag": "MISSING"})
    changes = diff_config_impacts(old, new)
    assert [(c.path, c.level) for c in changes] == [("grouping.enabled", LEVEL_L0)], changes
    assert changes[0].old is True and changes[0].new is False


def test_l0_dataclass_section_whole_change():
    """L0 段为 dataclass(非 dict)时 -> 整段一条 L0(真实 Config 的 grouping/add_episode_tags 即此形态)

    注意与 test_l0_dict_section_field_diff 的区别: `_diff_flat` 的字段级展开仅适用于纯 dict 段;
    真实 Config 的 L0 段都是 dataclass 实例, 故此处 path 只到段名(级别仍为 L0, 热重载行为正确,
    差异仅在变更条目粒度/日志计数)。本测试固化该现状, 使未来若要改为字段级展开成为有意改动。
    """
    for attr in ("grouping", "add_episode_tags"):
        old, new = Config(), Config()
        setattr(new, attr, SimpleNamespace(changed="x"))  # 段对象不等 -> 整段一条
        changes = diff_config_impacts(old, new)
        assert [(c.path, c.level) for c in changes] == [(attr, LEVEL_L0)], f"{attr}: {changes}"


def test_dict_section_nested_recursive():
    """dict 段嵌套递归展开到叶子路径(仅变化的叶子路径计入, 同级未变字段忽略)"""
    old = _ns(grouping={"outer": {"inner": 1, "same": 9}, "flat": 7})
    new = _ns(grouping={"outer": {"inner": 2, "same": 9}, "flat": 7})
    assert [(c.path, c.level) for c in diff_config_impacts(old, new)] == [("grouping.outer.inner", LEVEL_L0)]


def test_dict_section_type_change():
    """一侧变非 dict -> 该路径整体一条变更(不再向下递归)"""
    old = _ns(grouping={"outer": {"inner": 1}})
    new = _ns(grouping={"outer": 5})
    changes = diff_config_impacts(old, new)
    assert [(c.path, c.level) for c in changes] == [("grouping.outer", LEVEL_L0)], changes
    assert changes[0].old == {"inner": 1} and changes[0].new == 5


def test_tracker_added_or_removed():
    """tracker 增删 -> 整项 L2(old/new 一侧为 None)"""
    tc = TrackerConfig(name="HHan", domains=["d.com"])
    added = diff_config_impacts(_ns(trackers={}), _ns(trackers={"HHan": tc}))
    assert [(c.path, c.level) for c in added] == [("trackers.HHan", LEVEL_L2)]
    assert added[0].old is None and added[0].new is tc
    removed = diff_config_impacts(_ns(trackers={"HHan": tc}), _ns(trackers={}))
    assert [(c.path, c.level) for c in removed] == [("trackers.HHan", LEVEL_L2)]
    assert removed[0].old is tc and removed[0].new is None
    # trackers 段被显式置空(None)时按空字典处理(不崩)
    assert diff_config_impacts(_ns(trackers=None), _ns(trackers={"HHan": tc}))[0].level == LEVEL_L2


def test_tracker_field_levels():
    """同名 tracker 逐字段按 TRACKER_FIELD_LEVELS 定级(运行时动态读取项 L0, 绑定固化项 L2)"""
    old = TrackerConfig(name="HHan", domains=["old.com"], tags=["old"], upload_speed_limit=0, download_speed_limit=0)
    old.hr = None
    old.rules = ["@rs"]
    new = TrackerConfig(
        name="HHan", domains=["new.com"], tags=["new"], upload_speed_limit=1024, download_speed_limit=2048
    )
    new.hr = SimpleNamespace(required_seeding_time=86400)
    new.rules = ["@rs2"]
    new.remove_tags = ["x"]
    new.remove_similar_tags = True
    changes = diff_config_impacts(_ns(trackers={"HHan": old}), _ns(trackers={"HHan": new}))
    levels = {c.path: c.level for c in changes}
    assert levels == {
        "trackers.HHan.tags": LEVEL_L0,
        "trackers.HHan.remove_tags": LEVEL_L0,
        "trackers.HHan.remove_similar_tags": LEVEL_L0,
        "trackers.HHan.upload_speed_limit": LEVEL_L0,
        "trackers.HHan.download_speed_limit": LEVEL_L0,
        "trackers.HHan.hr": LEVEL_L0,
        "trackers.HHan.domains": LEVEL_L2,
        "trackers.HHan.rules": LEVEL_L2,
    }, changes


def test_tracker_unknown_field_defaults_l2():
    """tracker 未声明字段 -> L2(表驱动: 未列出即保守重建)"""
    old = SimpleNamespace(tags=["a"], custom_field=1)
    new = SimpleNamespace(tags=["a"], custom_field=2)
    changes = diff_config_impacts(_ns(trackers={"T": old}), _ns(trackers={"T": new}))
    assert [(c.path, c.level) for c in changes] == [("trackers.T.custom_field", LEVEL_L2)], changes


def test_tracker_unchanged_no_change():
    """tracker 内容相同 -> 不产生任何变更; 多个 tracker 中仅未变的那些不入结果"""
    tc = TrackerConfig(name="HHan", domains=["d.com"], tags=["a"])
    assert diff_config_impacts(_ns(trackers={"HHan": tc}), _ns(trackers={"HHan": tc})) == []

    # 同名 tracker 内容未变, 但 trackers 段整体有变化(另一站点变更) -> 未变站点仍不入结果
    other_old = TrackerConfig(name="MT", domains=["old.com"])
    other_new = TrackerConfig(name="MT", domains=["new.com"])
    changes = diff_config_impacts(
        _ns(trackers={
            "HHan": tc,
            "MT": other_old
        }), _ns(trackers={
            "HHan": tc,
            "MT": other_new
        })
    )
    assert [(c.path, c.level) for c in changes] == [("trackers.MT.domains", LEVEL_L2)], changes


def test_changes_sorted_by_path():
    """变更按路径排序(与配置段书写无关), 保证前端展示与日志稳定"""
    old, new = Config(), Config()
    new.main_tick = 5.0  # 路径 "main_tick"
    new.interval = 120.0  # 路径 "interval"
    new.state_file = "x/state.json"  # 路径 "state_file"
    paths = [c.path for c in diff_config_impacts(old, new)]
    assert paths == ["interval", "main_tick", "state_file"] == sorted(paths)

    # trackers 段内多名也排序
    a = TrackerConfig(name="B", domains=["d.com"])
    b = TrackerConfig(name="A", domains=["d.com"])
    added = diff_config_impacts(_ns(trackers={}), _ns(trackers={"B": a, "A": b}))
    assert [c.path for c in added] == ["trackers.A", "trackers.B"]


def test_max_level():
    """最高影响级别: 空 -> L0; 混合取最高(R > L2 > L1 > L0)"""
    assert max_level([]) == LEVEL_L0
    assert max_level([ConfigChange("a", LEVEL_L0, 1, 2)]) == LEVEL_L0
    assert max_level([ConfigChange("a", LEVEL_L0, 1, 2), ConfigChange("b", LEVEL_L2, 1, 2)]) == LEVEL_L2
    assert max_level(
        [ConfigChange("a", LEVEL_L1, 1, 2),
         ConfigChange("b", LEVEL_L2, 1, 2),
         ConfigChange("c", LEVEL_R, 1, 2)]
    ) == LEVEL_R


def test_max_level_unknown_level_is_highest():
    """未知级别视为最高(顺序表外值判 99, 方向保守: 宁可提示重启/重建)"""
    assert max_level([ConfigChange("a", LEVEL_L0, 1, 2), ConfigChange("b", "X", 1, 2)]) == "X"


def test_restart_required_paths():
    """仅返回 R 级路径且保持变更顺序(供 CLI/UI 提示需重启进程)"""
    changes = [
        ConfigChange("interval", LEVEL_L2, 1, 2),
        ConfigChange("state_file", LEVEL_R, "a", "b"),
        ConfigChange("data_dir", LEVEL_R, "a", "b"),
    ]
    assert restart_required_paths(changes) == ["state_file", "data_dir"]
    assert restart_required_paths([ConfigChange("interval", LEVEL_L2, 1, 2)]) == []
