"""test_hr_store 测试计划: 站点数据文件(每站点一个 JSON + 每站点一把锁)

## 测试计划(每个测试函数一条)
- test_roundtrip_all_substructures: 索引/已取记录/失败记账/放行记录/覆盖证明/配额/熔断全量往返
- test_missing_file_is_empty_not_error: 文件不存在 = 全新站点(不是错误), 读回空数据
- test_corrupt_file_is_reported_and_isolated: 坏 JSON 不入库, 报错且按空数据处理(保守回落未核实)
- test_schema_version_mismatch_is_rejected: schema_version 不符 -> 不入库
- test_hr_dir_follows_shared_dir: shared_dir 非空时用它, 否则落 <data_dir>/hr/
- test_lock_is_per_site: 同站点互斥(HrLockBusy), 不同站点互不阻塞(锁粒度=站点)
- test_revision_regression_degrades_to_readonly: revision 回退 -> 判锁不生效, 退化为只读不写盘
- test_heartbeat_overwritten_degrades_to_readonly: 本实例心跳被覆盖 -> 同样退化为只读
- test_commit_bumps_revision_and_heartbeat: 写入抬 revision 并记写者心跳, 文件始终是完整 JSON
- test_read_unlocked_sees_complete_document: 无锁只读拿到完整文档(写入是原子替换)
"""
import json

import pytest

from auto_qb.hr.model import (
    HrDownloaded,
    HrDlFail,
    HrEntry,
    HrFuse,
    HrQuota,
    HrRefreshMeta,
    HrSiteData,
    HrVerified,
)
from auto_qb.hr.store import HrLockBusy, HrSiteStore, hr_dir


def _sample() -> HrSiteData:
    data = HrSiteData()
    data.index[313852] = HrEntry(
        tid=313852,
        name="EXAMPLE S01",
        lane="A",
        downloaded_bytes=123,
        remain_seconds=99,
        infohash_v1="aa" * 20,
        infohash_v2="bb" * 32,
        first_seen=1.0,
        last_seen=2.0,
    )
    data.downloaded[313852] = HrDownloaded(
        tid=313852, ts=5.0, name="EXAMPLE S01", infohash_v1="aa" * 20, infohash_v2="bb" * 32
    )
    data.fails[313997] = HrDlFail(tid=313997, count=2, last_ts=6.0)
    data.verified["cc" * 20] = HrVerified(
        infohash="cc" * 20, tid=1, verified_ts=7.0, source="not-listed", anchor_added_on=100, anchor_downloaded=200
    )
    data.refresh = HrRefreshMeta(
        last_success_ts=7.0,
        scopes_done=["A", "B"],
        pages_fetched=3,
        reached_last_page=True,
        entry_count=1,
        complete=True
    )
    data.quota = HrQuota(
        hour_window="2026-09-24T20", hour_count=2, day_window="2026-09-24", day_count=5, last_fetch_ts=7.0
    )
    data.fuse = HrFuse(failures=1, until_ts=70.0, reason="连续失败")
    return data


def test_roundtrip_all_substructures(tmp_path):
    """索引/已取记录/失败记账/放行记录/覆盖证明/配额/熔断全量往返"""
    store = HrSiteStore("btschool", str(tmp_path))
    with store.hold() as session:
        session.data.index = _sample().index
        session.data.downloaded = _sample().downloaded
        session.data.fails = _sample().fails
        session.data.verified = _sample().verified
        session.data.refresh = _sample().refresh
        session.data.quota = _sample().quota
        session.data.fuse = _sample().fuse
        assert session.commit(now=1000.0) == "written"

    data, err = HrSiteStore("btschool", str(tmp_path)).read_unlocked()
    assert err is None
    assert data.schema_version == 1
    assert data.revision == 1
    assert data.writer_heartbeat == 1000.0
    assert data.index[313852].name == "EXAMPLE S01"
    assert data.index[313852].infohash_v1 == "aa" * 20
    assert data.downloaded[313852].ts == 5.0
    assert data.fails[313997].count == 2
    assert data.verified["cc" * 20].anchor_downloaded == 200
    assert data.refresh.complete is True and data.refresh.scopes_done == ["A", "B"]
    assert data.quota.day_count == 5
    assert data.fuse.until_ts == 70.0
    # 反查表只在读取时现建, 且以 tid 为主键(不存双份)
    assert data.index_by_infohash() == {"aa" * 20: 313852, "bb" * 32: 313852}


def test_missing_file_is_empty_not_error(tmp_path):
    """文件不存在 = 全新站点(不是错误)"""
    data, err = HrSiteStore("newsite", str(tmp_path)).read_unlocked()
    assert err is None
    assert data.revision == 0
    assert data.index == {}


def test_corrupt_file_is_reported_and_isolated(tmp_path):
    """坏 JSON 不入库, 报错且按空数据处理(保守回落未核实)"""
    (tmp_path / "bad.json").write_text("{ 这不是 json", encoding="utf-8")
    store = HrSiteStore("bad", str(tmp_path))
    with store.hold() as session:
        assert session.read_error is not None
        assert session.data.index == {}
        # 仍可写入(修复坏文件): commit 后是按空数据重建的完整文档
        assert session.commit(now=1.0) == "written"
    data, err = store.read_unlocked()
    assert err is None and data.revision == 1


def test_schema_version_mismatch_is_rejected(tmp_path):
    """schema_version 不符 -> 不入库(结构变更必须显式迁移, 不能猜)"""
    (tmp_path / "old.json").write_text(json.dumps({"schema_version": 99, "index": []}), encoding="utf-8")
    data, err = HrSiteStore("old", str(tmp_path)).read_unlocked()
    assert err is not None and "schema_version" in err
    assert data.index == {}


def test_hr_dir_follows_shared_dir(tmp_path):
    """shared_dir 非空时用它(多实例共享), 否则落 <data_dir>/hr/"""
    assert hr_dir(str(tmp_path / "data")) == str(tmp_path / "data" / "hr")
    assert hr_dir(str(tmp_path / "data"), str(tmp_path / "share")) == str(tmp_path / "share" / "hr")
    assert hr_dir(str(tmp_path / "data") + "/", str(tmp_path / "share") + "\\") == str(tmp_path / "share" / "hr")


def test_lock_is_per_site(tmp_path):
    """同站点互斥; 不同站点互不阻塞(锁粒度 = 站点, 抓 A 不挡 B)"""
    a1 = HrSiteStore("sitea", str(tmp_path), owner="i1")
    a2 = HrSiteStore("sitea", str(tmp_path), owner="i2")
    b1 = HrSiteStore("siteb", str(tmp_path), owner="i1")
    with a1.hold():
        with b1.hold():  # 另一个站点: 照常进
            pass
        with pytest.raises(HrLockBusy):
            with a2.hold():
                pass


def test_revision_regression_degrades_to_readonly(tmp_path):
    """revision 回退 -> 判共享目录上锁不生效 -> 只读退化(宁可保守, 不可双写)"""
    store = HrSiteStore("s", str(tmp_path), owner="me")
    with store.hold() as session:
        session.commit(now=10.0)
    # 别人用更旧的 revision 覆盖了文件(锁没生效才会发生)
    payload = json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))
    payload["revision"] = 0
    (tmp_path / "s.json").write_text(json.dumps(payload), encoding="utf-8")
    with store.hold() as session:
        assert session.writable is False
        assert session.commit(now=11.0) == "readonly"


def test_heartbeat_overwritten_degrades_to_readonly(tmp_path):
    """本实例心跳被覆盖 -> 同样只读退化"""
    store = HrSiteStore("s", str(tmp_path), owner="me")
    with store.hold() as session:
        session.commit(now=10.0)
    payload = json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))
    payload["writer"] = {"instance_id": "me", "heartbeat": 1.0}  # 心跳回退
    (tmp_path / "s.json").write_text(json.dumps(payload), encoding="utf-8")
    with store.hold() as session:
        assert session.writable is False
        assert session.commit(now=12.0) == "readonly"


def test_commit_bumps_revision_and_heartbeat(tmp_path):
    """写入抬 revision 并记写者心跳, 文件始终是完整 JSON(原子替换)"""
    store = HrSiteStore("s", str(tmp_path), owner="me")
    for expected in (1, 2, 3):
        with store.hold() as session:
            assert session.commit(now=float(expected)) == "written"
        data, err = store.read_unlocked()
        assert err is None
        assert data.revision == expected
        assert data.writer_instance == "me"
        assert data.writer_heartbeat == float(expected)
        assert json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))["revision"] == expected


def test_read_unlocked_sees_complete_document(tmp_path):
    """无锁只读拿到完整文档(写入是「同目录 tmp + 原子替换」, 不会读到半截)"""
    store = HrSiteStore("s", str(tmp_path))
    with store.hold() as session:
        session.data.index[1] = HrEntry(tid=1, name="x")
        session.commit(now=1.0)
    data, err = store.read_unlocked()
    assert err is None and data.index[1].name == "x"
