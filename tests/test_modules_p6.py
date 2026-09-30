"""test_modules_p6 测试计划: 收尾段 —— 段认领完备守阵(plan kernel-module-refactor P6)

P6 指定守阵(hot-reload-simplify §3.3 规则 3 / 拍板决策 3): 配置每个顶层段至少被一个
认领面覆盖(模块 sections() 或内核段), 未认领段变更落 WARN + 全量重建兜底(保守性可解释)。

## 测试计划(每个测试函数一条)
- test_claim_completeness_covers_all_config_sections: 配置全段 ⊆ 模块认领 ∪ 内核段(正向);
  认领面里不存在配置没有的段(反向, 防 sections 拼写漂移)
- test_kernel_sections_are_config_fields_and_disjoint: 内核认领面/重启闸都是真实配置段且互斥
- test_unclaimed_section_change_warns_and_rebuilds: 认领面漂移(模块 sections 被裁剪)时,
  变更段落 WARN + rebuild_runtime 相位触发全量重建 + 回执含 kernel 兜底动作
- test_claimed_section_change_no_fallback: 正常认领段变更不触发兜底(回执无 kernel 动作)
- test_zero_diff_save_no_actions_no_fallback: 零差异保存零动作、不触发兜底
- test_rebuild_runtime_phase_single_subscriber: rebuild_runtime 相位恰 rules 一家认领
"""
import copy
import logging
import os
import tempfile
from unittest import mock

from auto_qb.config import Config
from auto_qb.config.impact import KERNEL_SECTIONS, RESTART_SECTIONS
from helpers import make_manager


def _mgr(td):
    return make_manager(os.path.join(td, "state.json"))


# ============================================================
# 段认领完备(配置全段有主)
# ============================================================
def test_claim_completeness_covers_all_config_sections():
    """配置每个顶层段至少被一个认领面覆盖; 认领面也不得出现配置没有的段(拼写漂移防线)

    认领面 = 各模块 sections() 并集(ModuleHost.claimed_sections)∪ 内核自认领段
    (KERNEL_SECTIONS)∪ R 级重启闸(RESTART_SECTIONS)。新增配置顶层段而漏登记认领时,
    本断言红表 —— 这正是 hot-reload-simplify「新键忘登记 = 静默失效」的结构性防线。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        config_sections = set(vars(Config()))
        assert config_sections, "真实 Config 必须可实例化并列出全段"
        claimed = mgr.host.claimed_sections() | KERNEL_SECTIONS | RESTART_SECTIONS
        missing = config_sections - claimed
        assert not missing, f"以下配置段无任何认领面(模块 sections / 内核段): {sorted(missing)}"
        unknown = claimed - config_sections
        assert not unknown, f"认领面出现了配置不存在的段(拼写漂移?): {sorted(unknown)}"


def test_kernel_sections_are_config_fields_and_disjoint():
    """内核自认领段与 R 级重启闸都必须是真实配置段, 且两个集合互斥(各答各的语义)

    KERNEL_SECTIONS = 内核现读/自判的段(节拍/落盘计时/qb 连接); RESTART_SECTIONS = R 闸
    (拒绝热应用)。两者都是内核认领面, 但语义不同 —— 交集非空说明段的双语义没分清。
    """
    config_sections = set(vars(Config()))
    assert KERNEL_SECTIONS <= config_sections, "KERNEL_SECTIONS 出现了配置不存在的段"
    assert RESTART_SECTIONS <= config_sections, "RESTART_SECTIONS 出现了配置不存在的段"
    assert not KERNEL_SECTIONS & RESTART_SECTIONS, "内核现读段与 R 级重启闸不得重叠"


# ============================================================
# 未认领段兜底(WARN + 全量重建)
# ============================================================
class _ModuleLogCapture:
    """捕获指定模块 logger 输出(QbManager 构造清空 root handlers, caplog 失效 —— 惯例见 test_speed_curve)"""
    def __init__(self, name, level=logging.DEBUG):
        self._name = name
        self._level = level
        self.records = []

    def __enter__(self):
        self._lg = logging.getLogger(self._name)
        self._handler = _RecHandler(self.records)
        self._handler.setLevel(self._level)
        self._old_level = self._lg.level
        self._lg.setLevel(self._level)
        self._lg.addHandler(self._handler)
        return self

    def __exit__(self, *exc):
        self._lg.removeHandler(self._handler)
        self._lg.setLevel(self._old_level)
        return False


class _RecHandler(logging.Handler):
    def __init__(self, sink):
        super().__init__()
        self._sink = sink

    def emit(self, record):
        self._sink.append(record)


def test_unclaimed_section_change_warns_and_rebuilds():
    """认领面漂移(模块 sections 被裁剪)时: 变更段落 WARN + rebuild_runtime 相位重建 + 回执含兜底动作

    正常装配下不可达(上一测试锁认领完备), 本例模拟漂移: 把 maintenance 模块的 sections
    裁空后改 add_episode_tags 段 —— 变更段失去全部认领面, 内核必须保守兜底
    (hot-reload-simplify 拍板决策 3), 而不是静默「换对象即生效」。段的选择有讲究:
    add_episode_tags 是 maintenance 独占认领、BaseModule.apply 无重挂动作、也不在 rules
    重建判据里 —— 兜底之外零副作用(改 notify 段会经 force 挂载泄漏真 handler 到全局
    logger, 改 delete_tags/trackers 会触发 rules 自身的 L2 重建, 都会搅浑本例)。
    """
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        maint = mgr.host.get("maintenance")
        maint.sections = lambda: ()  # 模拟认领面漂移(漏登/裁剪)
        rebuild = mock.MagicMock()
        mgr.host.get("rules").rebuild_runtime = rebuild

        old = mgr.config
        new = copy.copy(old)  # 浅拷贝: 未动的段保持同一对象(替身类可能没有 __eq__, 深拷贝会误报段变)
        new.add_episode_tags = copy.deepcopy(old.add_episode_tags)
        new.add_episode_tags.enabled = not old.add_episode_tags.enabled
        with _ModuleLogCapture("auto_qb.core.qbmanager") as cap:
            receipt = mgr.apply_new_config(new)
        warns = [r for r in cap.records if "add_episode_tags" in r.getMessage()]
        assert warns and warns[0].levelno == logging.WARNING, "未认领段变更必须落 WARN 且点名段名(保守性可解释)"
        rebuild.assert_called_once(), "兜底 = 全量重建(经 rebuild_runtime 相位由 rules 执行)"
        fallback = [a for a in receipt["actions"] if a["module"] == "kernel"]
        assert fallback and fallback[0]["action"] == "rebuild_fallback", "回执必须含 kernel 兜底动作"


def test_claimed_section_change_no_fallback():
    """正常认领段变更: 模块自判动作, 不触发内核兜底(回执无 kernel 动作、无重建)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        rebuild = mock.MagicMock()
        mgr.host.get("rules").rebuild_runtime = rebuild
        old = mgr.config
        new = copy.copy(old)  # 浅拷贝: 未动的段保持同一对象(替身类可能没有 __eq__, 深拷贝会误报段变)
        new.web = copy.deepcopy(old.web)
        new.web.port = old.web.port + 1  # web 段被 webui 认领: 监听身份变化归模块自判
        receipt = mgr.apply_new_config(new)
        assert not rebuild.called, "认领段变更不得触发内核兜底重建"
        assert not [a for a in receipt["actions"] if a["module"] == "kernel"]
        assert receipt["changes"] == 1 and receipt["restart_required"] == []


def test_zero_diff_save_no_actions_no_fallback():
    """零差异保存: 变更 0 项, 全模块短路, 不触发兜底(W4 后的既有语义, 兜底不得破坏)"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        rebuild = mock.MagicMock()
        mgr.host.get("rules").rebuild_runtime = rebuild
        receipt = mgr.apply_new_config(copy.copy(mgr.config))  # 浅拷贝: 全部段同对象 -> diff 必然为空
        assert receipt["applied"] is True and receipt["changes"] == 0
        assert all(a["action"] == "none" for a in receipt["actions"] if a["module"] != "kernel")
        assert not [a for a in receipt["actions"] if a["module"] == "kernel"]
        assert not rebuild.called


def test_rebuild_runtime_phase_single_subscriber():
    """rebuild_runtime 相位(非刷新类, 与 queue_rebuilt 同款)恰 rules 一家认领"""
    with tempfile.TemporaryDirectory() as td:
        mgr = _mgr(td)
        handlers = mgr.events._handlers
        assert [h.__self__.name for h in handlers.get("rebuild_runtime", [])] == ["rules"]
