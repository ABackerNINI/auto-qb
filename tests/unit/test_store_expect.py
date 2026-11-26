"""test_store_expect 测试计划: 期望落地有界追平(issue 26-10-30-0626 候选 A)

## 测试计划(每个测试函数一条)
- test_expect_skips_hashes_already_in_snapshot: 已在快照里的 hash 不登记(不必追); 全已存在/空输入 -> 无待办零开销
- test_expect_due_is_shortly_in_the_future: 登记后到期时刻 ≈ now+80ms 且恒为未来时刻(调用方不会算出 0 超时)
- test_settle_clears_when_all_landed: 落地后自动出局; 全落地即清空(追平结束, 不多问一次)
- test_settle_reschedules_on_partial_landing: 只落地一部分 -> 保留缺的 + 排下一次(80ms 后), 计数 +1
- test_settle_gives_up_after_max_retries: 连续不落地 -> 3 次后放弃(有界: 不无限重试, 交给常规节拍)
- test_expect_ttl_expires_and_clears: 超过 TTL -> due 归 0 且待办清空(断连/暂停时不拖住主循环)
- test_clear_expect_resets_all_state: clear_expect 幂等复位(断连分支与热重载共用)
"""
import time

from auto_qb.torrents.store import _EXPECT_MAX_RETRIES, _EXPECT_RETRY_INTERVAL, TorrentStore
from platform_tolerance import SLEEP_LOWER_MARGIN_S


def _land(store: TorrentStore, *hashes: str) -> None:
    """让这些 hash 进快照(走真 _apply 路径, 连带触发结算)"""
    store._apply({h: {"hash": h} for h in hashes}, [], full=False)


def test_expect_skips_hashes_already_in_snapshot():
    """已在快照里的 hash 不登记(不必追); 全已存在/空输入 -> 无待办零开销"""
    store = TorrentStore()
    _land(store, "H1")

    store.expect_hashes(["H1"])
    assert store.expect_due_at() == 0.0, "已存在的不该登记"

    store.expect_hashes([])
    store.expect_hashes([""])
    assert store.expect_due_at() == 0.0, "空输入不得登记"

    store.expect_hashes(["H1", "H2"])
    assert store._expect_pending == {"H2"}, "只登记缺的那个"


def test_expect_due_is_shortly_in_the_future():
    """登记后到期时刻 ≈ now+80ms 且恒为未来时刻(调用方不会算出 0 超时)"""
    store = TorrentStore()
    before = time.time()
    store.expect_hashes(["H1"])
    due = store.expect_due_at()
    assert due > before, "到期时刻必须是未来 —— 过去值会让主循环算出 0 超时空转"
    assert before + _EXPECT_RETRY_INTERVAL - SLEEP_LOWER_MARGIN_S <= due <= before + _EXPECT_RETRY_INTERVAL + 0.2


def test_settle_clears_when_all_landed():
    """落地后自动出局; 全落地即清空(追平结束, 不多问一次)"""
    store = TorrentStore()
    store.expect_hashes(["H1", "H2"])
    assert store._expect_pending == {"H1", "H2"}

    _land(store, "H1", "H2")
    assert store._expect_pending == set(), "全部落地后不得残留待办"
    assert store.expect_due_at() == 0.0, "追平结束即归零(主循环不再提前同步节拍)"


def test_settle_reschedules_on_partial_landing():
    """只落地一部分 -> 保留缺的 + 排下一次(80ms 后), 计数 +1"""
    store = TorrentStore()
    store.expect_hashes(["H1", "H2"])

    _land(store, "H1")
    assert store._expect_pending == {"H2"}, "缺的那个必须留着继续追"
    assert store._expect_retries == 1
    due = store.expect_due_at()
    assert due > time.time(), "下一次追平必须是未来时刻"
    assert due <= time.time() + _EXPECT_RETRY_INTERVAL + 0.05


def test_settle_gives_up_after_max_retries():
    """连续不落地 -> 3 次后放弃(有界: 不无限重试, 交给常规节拍)"""
    store = TorrentStore()
    store.expect_hashes(["H1"])

    # 每轮都是「同步跑了但没拿到」: 零变化轮走 _apply 早退分支, 结算同样生效
    for _ in range(_EXPECT_MAX_RETRIES):
        store._apply({}, [], full=False)
        assert store._expect_pending == {"H1"}, "次数未用尽前应继续追"

    store._apply({}, [], full=False)
    assert store._expect_pending == set(), "超过上限必须放弃"
    assert store.expect_due_at() == 0.0


def test_expect_ttl_expires_and_clears():
    """超过 TTL -> due 归 0 且待办清空(断连/暂停时不拖住主循环)"""
    store = TorrentStore()
    store.expect_hashes(["H1"])
    store._expect_deadline = time.time() - 0.01  # 直接把 TTL 拨到过去

    assert store.expect_due_at() == 0.0
    assert store._expect_pending == set()


def test_clear_expect_resets_all_state():
    """clear_expect 幂等复位(断连分支与热重载共用)"""
    store = TorrentStore()
    store.expect_hashes(["H1"])
    store._apply({}, [], full=False)  # 排过一次下一次追平

    store.clear_expect()
    assert store._expect_pending == set()
    assert store._expect_retries == 0
    assert store.expect_due_at() == 0.0

    store.clear_expect()  # 幂等: 无待办时再清一次不炸
    assert store.expect_due_at() == 0.0
