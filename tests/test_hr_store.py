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
- test_write_keeps_previous_version_as_backup: 每次写入把上一版留为 `.bak`(读坏时的兜底)
- test_corrupt_file_is_quarantined_and_recovered_from_backup: 坏文件挪到 `.bad-<ts>` 留证 + 从 `.bak` 恢复,
  且恢复后的写入**不得**把好备份盖成坏内容
- test_corrupt_file_without_backup_warns_once: 无备份 -> 空数据 + 同一坏文件只告警一次
- test_repeated_read_failure_does_not_rewarn: 坏文件挪不走(被占用)时也不逐轮重报(降 DEBUG)
- test_schema_mismatch_is_not_quarantined: schema 不符是版本迁移, 不挪走也不从备份猜
- test_schema_version_old_migrates_and_materializes_on_commit: 旧版本沿链迁移(旧迁新拒), 随下次 commit 物化新版本
- test_schema_migration_logs_once: 迁移 INFO 只报一次(读路径含无锁只读, 防通知轰炸)
"""
import json
import logging

import pytest

from auto_qb.infra import versioning
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


# ---------- 站点文件读坏: 留证 + 备份兜底 + 只报一次 ----------


def _write_versions(tmp_path, site="s", *, entries=(1, )):
    """写两版(第二版多一条) —— 目的是让 `<site>.json.bak` 里躺着一份**好数据**"""
    store = HrSiteStore(site, str(tmp_path), owner="me")
    for revision, tids in enumerate((entries, entries + (2, )), start=1):
        with store.hold() as session:
            for tid in tids:
                session.data.index[tid] = HrEntry(tid=tid, name=f"t{tid}")
            assert session.commit(now=float(revision)) == "written"
    return store


def test_write_keeps_previous_version_as_backup(tmp_path):
    """每次写入把上一版留为 `.bak`(读坏时的兜底: 索引 / 已取记录 / 放行记录都在里面)"""
    _write_versions(tmp_path, entries=(1, ))
    backup = tmp_path / "s.json.bak"
    assert backup.exists()
    assert json.loads(backup.read_text(encoding="utf-8"))["revision"] == 1
    assert json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))["revision"] == 2


def test_corrupt_file_is_quarantined_and_recovered_from_backup(tmp_path):
    """坏文件: 挪到 `.bad-<ts>` 留证 + 从 `.bak` 恢复; 好备份不得被坏内容盖掉"""
    store = _write_versions(tmp_path, entries=(1, ))
    backup_before = (tmp_path / "s.json.bak").read_bytes()
    (tmp_path / "s.json").write_text("", encoding="utf-8")  # 被清空(编辑器/同步盘/写盘中断)

    with store.hold() as session:
        assert "文件为空 0 字节" in session.read_error, session.read_error
        assert session.recovered_from_backup is True
        # `.bak` 是**上一版**(写入前复制): 能救回它里面的内容, 但最新一轮的改动救不回来
        assert set(session.data.index) == {1}, "备份里的条目应当恢复出来"
        assert "已从备份(.bak)恢复" in session.read_error
        assert session.writable is True, "恢复后必须还能写回去(否则自愈反而变砖)"
        assert session.commit(now=9.0) == "written"

    data, err = store.read_unlocked()
    assert err is None and set(data.index) == {1}
    bad = list(tmp_path.glob("s.json.bad-*"))
    assert len(bad) == 1 and bad[0].read_text(encoding="utf-8") == "", "坏文件要原样留证"
    assert (tmp_path / "s.json.bak").read_bytes() == backup_before, "恢复后的写入不得把好备份盖成坏内容"


def test_corrupt_file_without_backup_warns_once(tmp_path, caplog):
    """没有备份时按空数据处理(保守回落未核实), 且**同一坏文件只告警一次**(逐轮重报 = 通知轰炸)"""
    (tmp_path / "s.json").write_text("{ 这不是 json", encoding="utf-8")
    store = HrSiteStore("s", str(tmp_path))

    with caplog.at_level(logging.WARNING, logger="auto_qb.hr.store"):
        with store.hold() as session:
            assert "备份不可用(没有备份文件)" in session.read_error
            assert session.data.index == {}
            assert session.read_alerted is True
            assert session.commit(now=1.0) == "written"
        with store.hold() as session:
            assert session.read_error is None, "坏文件已挪走 => 这一轮读到的是新写的完整文档"

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1, [w.getMessage() for w in warnings]
    assert "坏文件已挪走" in warnings[0].getMessage()


def test_repeated_read_failure_does_not_rewarn(tmp_path, caplog):
    """坏文件挪不走时(如被占用), 同一文本只 WARNING 一次, 后续轮次降 DEBUG"""
    (tmp_path / "s.json").write_text("{ 坏", encoding="utf-8")
    store = HrSiteStore("s", str(tmp_path))
    store.quarantine = lambda: ""  # 模拟挪走失败(被别的程序占用)
    alerted: list[bool] = []

    with caplog.at_level(logging.DEBUG, logger="auto_qb.hr.store"):
        for _ in range(3):
            with store.hold() as session:
                assert "坏文件未能挪走" in session.read_error
                alerted.append(session.read_alerted)

    assert alerted == [True, False, False], "坏文件是持续状态: 只报一次, 其余轮次降 DEBUG"
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1, f"同一坏文件只告警一次: {[w.getMessage() for w in warnings]}"


def test_schema_mismatch_is_not_quarantined(tmp_path):
    """schema_version 不符 = 版本迁移, 不是「坏文件」: 不挪走也不从备份恢复(备份里是同一个旧版本)"""
    (tmp_path / "old.json").write_text(json.dumps({"schema_version": 99, "index": []}), encoding="utf-8")
    store = HrSiteStore("old", str(tmp_path))
    with store.hold() as session:
        assert "schema_version=99" in session.read_error
        assert session.recovered_from_backup is False
        assert session.data.index == {}
    assert (tmp_path / "old.json").exists()
    assert not list(tmp_path.glob("old.json.bad-*"))


def test_schema_version_old_migrates_and_materializes_on_commit(tmp_path, monkeypatch):
    """旧版本沿链迁移(计划 26-09-26-0506「旧迁新拒」): 内存生效, 随下次 commit 物化新版本"""
    def step_1_2(raw):
        assert raw["schema_version"] == 1, "迁移函数拿到的版本章还是旧级别(框架逐级盖章)"
        return {**raw, "index": raw.get("index") or []}

    monkeypatch.setitem(versioning.CURRENT_VERSIONS, "hr_site", 2)
    monkeypatch.setitem(versioning.MIGRATIONS, "hr_site", {1: step_1_2})
    (tmp_path / "old.json").write_text(json.dumps({"schema_version": 1, "index": []}), encoding="utf-8")
    store = HrSiteStore("old", str(tmp_path))
    with store.hold() as session:
        assert session.read_error is None, "旧版本应迁移后正常解析, 不再报「不符即拒」"
        assert session.commit(now=1000.0) == "written"
    data, err = store.read_unlocked()
    assert err is None and data.schema_version == 2, "迁移结果随 commit 物化(文件已升级到新版本)"
    assert json.loads((tmp_path / "old.json").read_text(encoding="utf-8"))["schema_version"] == 2


def test_schema_migration_logs_once(tmp_path, monkeypatch, caplog):
    """迁移完成 INFO 只报一次 —— 无锁只读路径也会解析旧文件, 逐轮重报等于通知轰炸"""

    monkeypatch.setitem(versioning.CURRENT_VERSIONS, "hr_site", 2)
    monkeypatch.setitem(versioning.MIGRATIONS, "hr_site", {1: lambda raw: {**raw, "index": []}})
    (tmp_path / "old.json").write_text(json.dumps({"schema_version": 1, "index": []}), encoding="utf-8")
    store = HrSiteStore("old", str(tmp_path))
    with caplog.at_level(logging.INFO, logger="auto_qb.hr.store"):
        for _ in range(3):
            data, err = store.read_unlocked()
            assert err is None
    infos = [r for r in caplog.records if r.levelno == logging.INFO and "已迁移" in r.getMessage()]
    assert len(infos) == 1, f"迁移 INFO 只报一次: {[i.getMessage() for i in infos]}"
