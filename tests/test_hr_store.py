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
- test_non_utf8_file_is_quarantined_and_recovered_from_backup: 守阵(26-10-06-0028 B2-01)——非 UTF-8 字节(GBK 重存)
  同属「坏文件」, 归入隔离 -> .bak 自愈链而非每波 ERROR 刷屏
- test_non_utf8_bytes_never_raise_on_unlocked_read_and_backup: 守阵(26-10-06-0028 B2-01)——无锁只读 / 备份路径
  对非 UTF-8 文件「读坏不抛」如实带回错误(status.py 契约钉死)
- test_schema_mismatch_is_not_quarantined: schema 不符是版本迁移, 不挪走也不从备份猜
- test_schema_version_old_migrates_and_materializes_on_commit: 旧版本沿链迁移(旧迁新拒), 随下次 commit 物化新版本
- test_schema_migration_logs_once: 迁移 INFO 只报一次(读路径含无锁只读, 防通知轰炸)
- test_history_roundtrip_all_fields: history 事件数组全字段往返(经站点文件落盘, 含 lanes/notes 复合结构), 逐字段相等
- test_history_missing_key_legacy_compat: 旧 JSON 不含 history 键 -> from_json 得空表且其余字段无损(存量文件零迁移)
- test_history_cap_keeps_latest: 超 HISTORY_CAP(2000)条时修剪助手保留最新 HISTORY_CAP 条(原表不动)
- test_history_age_prune_boundary: 按龄修剪: 超过 183 天剔、恰好 183 天边界保留、未来时刻保留

## R17 变异审计补测(序列化与持久化)
- test_model_entry_roundtrip_all_fields: HrEntry 全字段非默认往返(钉键名与取值)
- test_model_entry_optional_none_roundtrip: HrEntry 可选字段全 None 往返(None 原样穿过, 不折 0)
- test_model_entry_missing_keys_use_defaults: HrEntry 键全缺走字段默认(active 默认 True 等)
- test_model_downloaded_roundtrip_and_defaults: HrDownloaded 全字段往返 + 键缺省默认
- test_model_verified_roundtrip_and_defaults: HrVerified 往返 + source/ anchor_completion_on 默认
- test_model_lanestate_roundtrip_and_defaults: HrLaneState 往返 + count_claim/count_match 的 None 语义
- test_model_wavemeta_roundtrip_and_defaults: HrWaveMeta 往返 + retention_ratio/retention_ok 默认
- test_model_rateledger_roundtrip_and_defaults: HrRateLedger 往返 + day_window 空串默认
- test_model_history_event_missing_keys_use_defaults: HrHistoryEvent 键缺走空串, notes 里 None 折空串
- test_model_sitedata_roundtrip_all_fields: HrSiteData 顶层标量 + 子表 + wave/rate/history 全字段往返
- test_model_sitedata_schema_version_and_writer_fallback: schema_version 从 raw 取; writer 三级回退链
- test_model_sitedata_verified_filter_positive_ts: 放行入账闸 verified_ts > 0(正小数也算)
- test_store_instance_id_is_twelve_hex: 实例标识固定 12 位十六进制
- test_store_hr_dir_strips_trailing_separators: 尾部分隔符剥掉; 目录名以 X 结尾不误剥
- test_store_init_defaults_and_lock_timeout: 构造默认(owner 12 位 / 锁超时 0 / 各旗标初始态)
- test_store_missing_file_recoverable_flag: 文件不存在 recoverable=False(不是坏文件)
- test_store_parse_valid_and_schema_mismatch_recoverable_flags: 正常/schema 不符都不 recoverable
- test_store_error_hints_include_file_head: 三条错误路径的取证串都带文件开头
- test_store_file_hint_variants: 取证串三态(不存在 -> 空串 / 空文件 -> 专用文案 / 有内容 -> 截 40 字符)
- test_store_write_default_keeps_backup: _write 默认 keep_backup=True 留 .bak
- test_store_write_unicode_and_sorted_keys: 落盘 ensure_ascii=False + sort_keys=True
- test_store_session_read_alerted_false_when_clean: 读正常时 read_alerted 初始 False
- test_store_check_lock_heartbeat_zero_is_not_unsafe: 心跳自检下界严格 0 <(心跳 0 不算被覆盖)
- test_store_recover_unmovable_keeps_backup: 坏文件挪不走时本次写盘不盖好备份
"""
import json
import logging
import os

import pytest

from auto_qb.infra import versioning
from auto_qb.hr.model import (
    HISTORY_CAP,
    HISTORY_MAX_AGE_S,
    LANE_OK,
    LANE_SCOPE,
    LANE_UNSATISFIED,
    SOURCE_NOT_LISTED,
    SOURCE_SATISFIED,
    HrDownloaded,
    HrDlFail,
    HrEntry,
    HrHistoryEvent,
    HrLaneState,
    HrRateLedger,
    HrSiteData,
    HrVerified,
    HrWaveMeta,
    prune_history,
)
import auto_qb.hr.store as hr_store
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
    data.wave = HrWaveMeta(
        wave_ts=7.0,
        healthy_ts=7.0,
        lanes={"A": HrLaneState(lane="A", status="ok", pages=2, rows=1, full_depth=True)},
        releases_enabled=True,
        prev_a_tids={313852: "aa" * 20},
    )
    data.rate = HrRateLedger(day_window="2026-09-24", day_count=5, last_fetch_ts=7.0)
    data.empty_confirmed_at = 0.0
    return data


def test_roundtrip_all_substructures(tmp_path):
    """索引/已取记录/失败记账/放行记录/覆盖证明/配额/熔断全量往返"""
    sample = _sample()
    store = HrSiteStore("btschool", str(tmp_path))
    with store.hold() as session:
        session.data.index = sample.index
        session.data.downloaded = sample.downloaded
        session.data.fails = sample.fails
        session.data.verified = sample.verified
        session.data.wave = sample.wave
        session.data.rate = sample.rate
        assert session.commit(now=1000.0) == "written"

    data, err = HrSiteStore("btschool", str(tmp_path)).read_unlocked()
    assert err is None
    assert data.schema_version == versioning.CURRENT_VERSIONS["hr_site"]
    assert data.revision == 1
    assert data.writer_heartbeat == 1000.0
    assert data.index[313852].name == "EXAMPLE S01"
    assert data.index[313852].infohash_v1 == "aa" * 20
    assert data.downloaded[313852].ts == 5.0
    assert data.fails[313997].count == 2
    assert data.verified["cc" * 20].anchor_downloaded == 200
    assert data.wave.lanes["A"].full_depth is True and data.wave.releases_enabled is True
    assert data.wave.prev_a_tids == {313852: "aa" * 20}
    assert data.rate.day_count == 5
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


def test_non_utf8_file_is_quarantined_and_recovered_from_backup(tmp_path):
    """守阵(26-10-06-0028 B2-01): 非 UTF-8 字节(编辑器 ANSI/GBK 重存)同属「坏文件」

    UnicodeDecodeError(ValueError 子类)必须归入既有 quarantine -> .bak 自愈链,
    不许从 _read_full 逃出(否则自愈链全程不可达, 每波 ERROR 刷屏 + 视图面发布中止)。
    """
    store = _write_versions(tmp_path, entries=(1, ))
    # 模拟 Windows 编辑器按 GBK 重存站点 JSON(中文种子名)
    (tmp_path / "s.json").write_text('{"index": [{"tid": 1, "name": "例站 S01"}]}', encoding="gbk")

    with store.hold() as session:
        assert "站点文件读取失败" in session.read_error, session.read_error
        assert session.recovered_from_backup is True, "GBK 坏文件必须走 .bak 兜底, 不是每波 ERROR 刷屏"
        assert set(session.data.index) == {1}, "备份里的条目应当恢复出来"
        assert session.commit(now=9.0) == "written"
    data, err = store.read_unlocked()
    assert err is None and set(data.index) == {1}
    assert len(list(tmp_path.glob("s.json.bad-*"))) == 1, "GBK 坏文件要原样留证"


def test_non_utf8_bytes_never_raise_on_unlocked_read_and_backup(tmp_path):
    """守阵(26-10-06-0028 B2-01): 非 UTF-8 文件在无锁只读 / 备份路径「读坏不抛」, 如实带回错误

    status.py「站点文件读坏时不抛」契约对 encoding 类读坏同样成立(WebUI /hr 路由不 500)。
    """
    (tmp_path / "u.json").write_text('{"index": [{"tid": 1, "name": "例站 S01"}]}', encoding="gbk")
    data, err = HrSiteStore("u", str(tmp_path)).read_unlocked()  # 不抛
    assert err is not None and "读取失败" in err and data.index == {}

    (tmp_path / "b.json.bak").write_bytes(b"\xb9\xf9\xb2\xcb\xd6\xd0\xce\xc4")  # GBK 字节
    bdata, berr = HrSiteStore("b", str(tmp_path)).read_backup()  # 不抛
    assert berr is not None and bdata.index == {}


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


# ==================== 拉取历史(HrHistoryEvent, 计划 26-10-04-0312 S1) ====================


def _history_events() -> list:
    """两条历史事件: 第一条全字段拉满(reason 200 字符 + lanes 3 档 + notes 5 条), 第二条只填核心字段验默认值"""
    full = HrHistoryEvent(
        ts=1000.5,
        kind="wave",
        trigger="auto",
        action="refreshed",
        reason="r" * 200,
        reason_kind="",
        pages=6,
        rows=214,
        torrents_ok=3,
        torrents_fail=1,
        verified=2,
        elapsed_s=42.6,
        lanes=[
            {
                "lane": "A",
                "status": "ok",
                "pages": 3,
                "rows": 96,
                "detail": ""
            },
            {
                "lane": "B",
                "status": "ok",
                "pages": 2,
                "rows": 78,
                "detail": "命中本地全集"
            },
            {
                "lane": "C",
                "status": "failed",
                "pages": 1,
                "rows": 0,
                "detail": "表头缺失"
            },
        ],
        notes=["n1", "n2", "n3", "n4", "n5"],
        by="abcdef",
    )
    minimal = HrHistoryEvent(
        ts=2000.0,
        kind="defer",
        trigger="manual",
        action="waiting",
        reason="未到可取时刻(min_interval, 还差 812s)",
        reason_kind="budget",
        by="xyz789"
    )
    return [full, minimal]


def test_history_roundtrip_all_fields(tmp_path):
    """history 事件数组全字段往返(经站点文件落盘), 逐字段相等"""
    sample = _history_events()
    store = HrSiteStore("btschool", str(tmp_path))
    with store.hold() as session:
        session.data.history = sample
        assert session.commit(now=3000.0) == "written"

    data, err = HrSiteStore("btschool", str(tmp_path)).read_unlocked()
    assert err is None
    assert len(data.history) == 2
    full = data.history[0]
    assert full.ts == 1000.5
    assert full.kind == "wave" and full.trigger == "auto" and full.action == "refreshed"
    assert full.reason == "r" * 200 and full.reason_kind == ""
    assert full.pages == 6 and full.rows == 214
    assert full.torrents_ok == 3 and full.torrents_fail == 1
    assert full.verified == 2 and full.elapsed_s == 42.6
    assert full.lanes == [
        {
            "lane": "A",
            "status": "ok",
            "pages": 3,
            "rows": 96,
            "detail": ""
        },
        {
            "lane": "B",
            "status": "ok",
            "pages": 2,
            "rows": 78,
            "detail": "命中本地全集"
        },
        {
            "lane": "C",
            "status": "failed",
            "pages": 1,
            "rows": 0,
            "detail": "表头缺失"
        },
    ]
    assert full.notes == ["n1", "n2", "n3", "n4", "n5"]
    assert full.by == "abcdef"
    # 第二条只填核心字段: 缺省字段按默认值往返(读侧对元素缺字段容忍)
    mini = data.history[1]
    assert mini.ts == 2000.0 and mini.action == "waiting" and mini.reason_kind == "budget"
    assert mini.pages == 0 and mini.rows == 0 and mini.lanes == [] and mini.notes == [] and mini.elapsed_s == 0.0
    # dataclass 级纯往返(不经站点文件): to_json -> from_json 逐字段相等
    assert HrHistoryEvent.from_json(sample[0].to_json()) == sample[0]
    assert HrHistoryEvent.from_json(sample[1].to_json()) == sample[1]


def test_history_missing_key_legacy_compat(tmp_path):
    """旧 JSON 不含 history 键 -> from_json 得空表且其余字段无损(存量文件零迁移)"""
    payload = {
        "schema_version": versioning.CURRENT_VERSIONS["hr_site"],
        "revision": 7,
        "fetched_at": 111.0,
        "writer": {
            "instance_id": "legacy",
            "heartbeat": 222.0
        },
        "index": [{
            "tid": 5,
            "name": "t5"
        }],
        "rate": {
            "day_window": "2026-10-04",
            "day_count": 9
        },
    }
    (tmp_path / "s.json").write_text(json.dumps(payload), encoding="utf-8")
    data, err = HrSiteStore("s", str(tmp_path)).read_unlocked()
    assert err is None
    assert data.history == []
    # 其余字段无损
    assert data.revision == 7 and data.fetched_at == 111.0
    assert data.writer_instance == "legacy" and data.writer_heartbeat == 222.0
    assert data.index[5].name == "t5" and data.rate.day_count == 9


def test_history_cap_keeps_latest():
    """超 HISTORY_CAP(2000)条时修剪助手保留最新 HISTORY_CAP 条(顺序不变, 原表不动)"""
    events = [HrHistoryEvent(ts=float(i)) for i in range(HISTORY_CAP + 500)]
    now = float(HISTORY_CAP + 500)  # now 贴着事件时刻: 只验容量截断, 不触发按龄剔除
    pruned = prune_history(events, now=now)
    assert len(pruned) == HISTORY_CAP
    assert pruned[0].ts == 500.0, "最旧的 500 条被截掉"
    assert pruned[-1].ts == float(HISTORY_CAP + 499), "最新一条保留在末尾"
    assert [e.ts for e in pruned] == [e.ts for e in events[-HISTORY_CAP:]]
    assert len(events) == HISTORY_CAP + 500, "修剪返回新表, 不改传入表"
    # 恰好等于 cap: 原样全保留
    exact = [HrHistoryEvent(ts=float(i)) for i in range(HISTORY_CAP)]
    assert [e.ts for e in prune_history(exact, now=now)] == [e.ts for e in exact]


def test_history_age_prune_boundary():
    """按龄修剪: 超过 HISTORY_MAX_AGE_S(183 天)剔除; 恰好等于期限(边界)保留; 未来时刻保留"""
    now = 10_000_000.0
    too_old = HrHistoryEvent(ts=now - HISTORY_MAX_AGE_S - 1.0)
    at_edge = HrHistoryEvent(ts=now - HISTORY_MAX_AGE_S)
    fresh = HrHistoryEvent(ts=now - 60.0)
    future = HrHistoryEvent(ts=now + 120.0)
    pruned = prune_history([too_old, at_edge, fresh, future], now=now)
    assert [e.ts for e in pruned] == [at_edge.ts, fresh.ts, future.ts], "只剔严格超龄的, 边界值与未来时刻保留"


# ==================== P1 覆盖率提升轮: 存储层错误路径长尾 ====================


def test_read_oserror_reports_and_keeps_hint(tmp_path, monkeypatch):
    """站点文件读取失败(OSError) -> 报「读取失败」, 取证提示带文件大小"""
    store = HrSiteStore("s", str(tmp_path))
    store.path.write_text("x" * 128, encoding="utf-8")

    def boom(self, *a, **kw):
        raise PermissionError(13, "拒绝访问")

    monkeypatch.setattr("pathlib.Path.read_text", boom)
    data, err, recoverable = store._read_full()
    assert data.index == {} and err and "站点文件读取失败" in err
    assert recoverable is True and "(文件 128 字节)" in err, "text 缺失的取证提示按大小描述"


def test_root_not_dict_is_bad_file(tmp_path):
    """根节点不是字典(如数组) -> 「坏文件」可以从 .bak 兜底"""
    store = HrSiteStore("s", str(tmp_path))
    store.path.write_text("[1, 2]", encoding="utf-8")
    data, err, recoverable = store._read_full()
    assert "根节点不是字典" in err and recoverable is True


def test_field_parse_failure_reported(tmp_path, monkeypatch):
    """字段解析失败(TypeError/ValueError/KeyError) -> 报「字段解析失败」(坏文件, 可恢复)"""
    store = HrSiteStore("s", str(tmp_path))
    store.path.write_text(json.dumps({"schema_version": versioning.CURRENT_VERSIONS["hr_site"]}), encoding="utf-8")

    def boom(cls, raw):
        raise ValueError("坏字段")

    monkeypatch.setattr(hr_store.HrSiteData, "from_json", classmethod(boom))
    data, err, recoverable = store._parse(store.path.read_text(encoding="utf-8"))
    assert "字段解析失败" in err and recoverable is True
    assert "开头" in err, "字段解析失败的取证串也要带文件开头(R17)"
    monkeypatch.undo()


def test_quarantine_absent_file_returns_empty(tmp_path):
    """文件不存在时 quarantine 无事可做 -> 空串"""
    store = HrSiteStore("never", str(tmp_path))
    assert store.quarantine() == ""


def test_quarantine_failure_returns_empty(tmp_path, monkeypatch):
    """坏文件挪不走(被占用等) -> 返回空串, 调用方继续跑但须知悉"""
    store = HrSiteStore("s", str(tmp_path))
    store.path.write_text("{bad json", encoding="utf-8")

    def boom(src, dst):
        raise OSError(13, "拒绝访问")

    monkeypatch.setattr(hr_store.os, "replace", boom)
    assert store.quarantine() == ""
    assert store.path.exists(), "原文件保留现场"
    monkeypatch.undo()


def test_backup_read_failure_reported(tmp_path, monkeypatch):
    """.bak 存在但读不了 -> 报「备份读取失败」(不抛)"""
    store = HrSiteStore("s", str(tmp_path))
    backup = tmp_path / "s.json.bak"
    backup.write_text("{}", encoding="utf-8")

    def boom(self, *a, **kw):
        raise PermissionError(13, "拒绝访问")

    monkeypatch.setattr("pathlib.Path.read_text", boom)
    data, err = store.read_backup()
    assert data.index == {} and "备份读取失败" in err
    monkeypatch.undo()


def test_warn_unsafe_only_once_per_store(tmp_path):
    """锁不生效的 ERROR 只报一次: 第二次判定直接静默返回 False"""
    store = HrSiteStore("s", str(tmp_path), owner="me")
    with store.hold() as session:
        session.commit(now=10.0)
    payload = json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))
    payload["revision"] = 0
    (tmp_path / "s.json").write_text(json.dumps(payload), encoding="utf-8")
    with store.hold() as session:
        assert store._unsafe_warned is True
        # 第二次: _warn_unsafe 早退(不重复告警), 判定仍 False
        assert store._check_lock_effective(session.data) is False
        assert store._warn_unsafe("再次检测") is None


def test_lock_session_site_property(tmp_path):
    """会话的 site 属性来自被包装的 store(报告与日志用)"""
    store = HrSiteStore("mysite", str(tmp_path))
    with store.hold() as session:
        assert session.site == "mysite"


# ==================== R17: 序列化契约(model 全字段往返 + 键缺省默认) ====================


def test_model_entry_roundtrip_all_fields():
    """HrEntry 全字段非默认值往返: 键名被改写 / 取值被整段置 None 都要变红"""
    entry = HrEntry(
        tid=313852,
        dl_id=173107,
        name="例站 S01",
        lane=LANE_UNSATISFIED,
        uploaded_bytes=11,
        downloaded_bytes=22,
        ratio=1.5,
        need_seed_seconds=33,
        done_iso="2026-09-27T12:00:00",
        remain_seconds=44,
        infohash_v1="aa" * 20,
        infohash_v2="bb" * 32,
        first_seen=1.5,
        last_seen=2.5,
        active=False,
        missing_streak=3,
    )
    assert HrEntry.from_json(entry.to_json()) == entry


def test_model_entry_optional_none_roundtrip():
    """HrEntry 可选字段全 None 往返: _opt_int/_opt_float 的「None 原样穿过」语义(不折成 0)"""
    entry = HrEntry(
        tid=1,
        dl_id=None,
        uploaded_bytes=None,
        downloaded_bytes=None,
        ratio=None,
        need_seed_seconds=None,
        done_iso=None,
        remain_seconds=None,
    )
    assert HrEntry.from_json(entry.to_json()) == entry


def test_model_entry_missing_keys_use_defaults():
    """HrEntry 键全缺: 一律走字段默认(active 默认 True / 空串 / 0 / None), 不猜非默认值"""
    entry = HrEntry.from_json({})
    assert entry == HrEntry(tid=0)
    assert entry.active is True and entry.lane == LANE_SCOPE
    assert entry.dl_id is None and entry.ratio is None and entry.done_iso is None
    assert entry.name == "" and entry.infohash_v1 == "" and entry.infohash_v2 == ""
    assert entry.first_seen == 0.0 and entry.last_seen == 0.0 and entry.missing_streak == 0


def test_model_downloaded_roundtrip_and_defaults():
    """HrDownloaded 全字段往返 + 键缺省默认(空串不是占位符)"""
    got = HrDownloaded(tid=9, ts=5.5, name="n9", infohash_v1="V1", infohash_v2="V2")
    assert HrDownloaded.from_json(got.to_json()) == got
    assert HrDownloaded.from_json({"tid": 9}) == HrDownloaded(tid=9)


def test_model_verified_roundtrip_and_defaults():
    """HrVerified 全字段往返 + 键缺省默认(source 默认 not-listed / anchor_completion_on 默认 -1)"""
    ver = HrVerified(
        infohash="cc" * 20,
        tid=7,
        verified_ts=8.5,
        source=SOURCE_SATISFIED,
        anchor_added_on=100,
        anchor_downloaded=200,
        anchor_completion_on=300,
        anchor_progress=0.75,
    )
    assert HrVerified.from_json(ver.to_json()) == ver
    d = HrVerified.from_json({"infohash": "cc" * 20, "tid": 7, "verified_ts": 1.0})
    assert d.source == SOURCE_NOT_LISTED
    assert d.anchor_completion_on == -1 and d.anchor_progress == 0.0 and d.anchor_added_on == 0


def test_model_lanestate_roundtrip_and_defaults():
    """HrLaneState 全字段往返 + 键缺省默认(count_claim/count_match 的 None 语义必须原样穿过)"""
    lane = HrLaneState(
        lane=LANE_SCOPE,
        wave_ts=1.5,
        status=LANE_OK,
        pages=3,
        rows=99,
        cutoff_done=2.5,
        full_depth=True,
        detail="d",
        fail_streak=2,
        count_claim=100,
        count_match=False,
        count_mismatch_streak=3,
    )
    assert HrLaneState.from_json(lane.to_json()) == lane
    d = HrLaneState.from_json({})
    assert d == HrLaneState()
    assert d.count_claim is None and d.count_match is None


def test_model_wavemeta_roundtrip_and_defaults():
    """HrWaveMeta 全字段往返 + 键缺省默认(retention_ratio 默认 -1.0 / retention_ok 默认 True)"""
    wave = HrWaveMeta(
        wave_ts=1.5,
        healthy_ts=2.5,
        idle_mode=True,
        releases_enabled=True,
        zero_rows=True,
        retention_ratio=0.8,
        retention_ok=False,
        lanes={"A": HrLaneState(lane="A", status=LANE_OK)},
        prev_a_tids={5: "aa" * 20},
        notes="n",
    )
    assert HrWaveMeta.from_json(wave.to_json()) == wave
    d = HrWaveMeta.from_json({})
    assert d == HrWaveMeta()
    assert d.retention_ratio == -1.0 and d.retention_ok is True


def test_model_rateledger_roundtrip_and_defaults():
    """HrRateLedger 全字段往返 + 键缺省默认(day_window 空串)"""
    rate = HrRateLedger(day_window="2026-09-28", day_count=5, last_fetch_ts=7.5)
    assert HrRateLedger.from_json(rate.to_json()) == rate
    assert HrRateLedger.from_json({}) == HrRateLedger()


def test_model_history_event_missing_keys_use_defaults():
    """HrHistoryEvent 键缺: 字符串字段走空串(不是占位符); notes 里的 None 折成空串"""
    ev = HrHistoryEvent.from_json({"ts": 1.0})
    assert ev.kind == "" and ev.trigger == "" and ev.action == ""
    assert ev.reason == "" and ev.reason_kind == "" and ev.by == ""
    assert ev.lanes == [] and ev.notes == []
    assert HrHistoryEvent.from_json({"ts": 1.0, "notes": [None, "x"]}).notes == ["", "x"]


def test_model_sitedata_roundtrip_all_fields():
    """HrSiteData 全字段往返: 顶层标量 + 四个子表 + wave/rate/history 复合结构逐字段相等"""
    data = HrSiteData(
        schema_version=versioning.CURRENT_VERSIONS["hr_site"],
        revision=7,
        fetched_at=1.5,
        expires_at=2.5,
        writer_instance="inst",
        writer_heartbeat=3.5,
        empty_confirmed_at=4.5,
        retry_after_until=5.5,
    )
    data.index[1] = HrEntry(tid=1, name="n1", infohash_v1="aa" * 20)
    data.downloaded[1] = HrDownloaded(tid=1, ts=6.5, infohash_v1="bb" * 20)
    data.fails[1] = HrDlFail(tid=1, count=2, last_ts=7.5)
    data.verified["cc" * 20] = HrVerified(infohash="cc" * 20, tid=1, verified_ts=8.5)
    data.wave = HrWaveMeta(wave_ts=9.5, retention_ratio=0.5)
    data.rate = HrRateLedger(day_window="2026-09-28", day_count=1, last_fetch_ts=10.5)
    data.history = [HrHistoryEvent(ts=11.5, kind="wave")]
    assert HrSiteData.from_json(data.to_json()) == data


def test_model_sitedata_schema_version_and_writer_fallback():
    """schema_version 从 raw 取(键缺才落 SCHEMA_VERSION); writer 走 writer.instance_id -> 顶层 writer_instance -> 空串"""
    assert HrSiteData.from_json({"schema_version": 5}).schema_version == 5
    assert HrSiteData.from_json({}).schema_version == versioning.CURRENT_VERSIONS["hr_site"]
    assert HrSiteData.from_json({"writer": {"instance_id": "i1"}}).writer_instance == "i1"
    assert HrSiteData.from_json({"writer_instance": "legacy"}).writer_instance == "legacy"
    assert HrSiteData.from_json({}).writer_instance == ""
    assert HrSiteData.from_json({"writer_heartbeat": 4.5}).writer_heartbeat == 4.5


def test_model_sitedata_verified_filter_positive_ts():
    """放行记录入账闸: 有 infohash 且 verified_ts > 0(0.5 这种正小数也算)"""
    raw = {
        "verified":
            [
                {
                    "infohash": "aa" * 20,
                    "tid": 1,
                    "verified_ts": 0.5
                },
                {
                    "infohash": "bb" * 20,
                    "tid": 2,
                    "verified_ts": 0
                },
                {
                    "tid": 3,
                    "verified_ts": 9.0
                },
            ]
    }
    assert set(HrSiteData.from_json(raw).verified) == {"aa" * 20}


# ==================== R17: 存储层(构造默认 / 原子写 / 取证串 / 恢复路径) ====================


def test_store_instance_id_is_twelve_hex():
    """实例标识固定 12 位十六进制(多实例分辨用)"""
    iid = hr_store.instance_id()
    assert len(iid) == 12 and all(c in "0123456789abcdef" for c in iid)


def test_store_hr_dir_strips_trailing_separators():
    """尾部分隔符被剥掉; 目录名以 X 结尾时不误剥(只在分隔符集合上 rstrip)"""
    assert hr_dir("/data/x/") == os.path.join("/data/x", "hr")
    assert hr_dir("/data/x\\") == os.path.join("/data/x", "hr")
    assert hr_dir("/data/xX") == os.path.join("/data/xX", "hr")
    assert hr_dir("/data/x", "/share/xX") == os.path.join("/share/xX", "hr")


def test_store_init_defaults_and_lock_timeout(tmp_path):
    """构造默认: owner 自生成 12 位; 锁超时默认 0(不等); 心跳自检基线/告警旗标初始态"""
    store = HrSiteStore("s", str(tmp_path))
    assert len(store.owner) == 12
    assert store._lock.timeout == 0.0
    assert store._last_write_rev == 0 and store._last_write_heartbeat == 0.0
    assert store._unsafe_warned is False
    assert store._read_error_warned == ""
    assert store._migration_logged is False


def test_store_missing_file_recoverable_flag(tmp_path):
    """文件不存在 -> (空数据, 无错, recoverable=False): 不是「坏文件」, 不该走 .bak 兜底"""
    store = HrSiteStore("newsite", str(tmp_path))
    data, err, recoverable = store._read_full()
    assert err is None and recoverable is False


def test_store_parse_valid_and_schema_mismatch_recoverable_flags(tmp_path):
    """正常解析 recoverable=False; schema 不符也不可恢复(备份里是同一个旧版本, 猜没意义)"""
    store = HrSiteStore("s", str(tmp_path))
    text = json.dumps({"schema_version": versioning.CURRENT_VERSIONS["hr_site"], "index": []})
    _d, err, recoverable = store._parse(text)
    assert err is None and recoverable is False
    _d2, err2, recoverable2 = store._parse(json.dumps({"schema_version": 99, "index": []}))
    assert err2 is not None and recoverable2 is False


def test_store_error_hints_include_file_head(tmp_path):
    """坏文件取证串要带「开头 ...」: 只报 Expecting value 人分不清是空文件还是内容被写坏"""
    store = HrSiteStore("s", str(tmp_path))
    store.path.write_text("[1, 2]", encoding="utf-8")
    _d, err, _r = store._parse("[1, 2]")  # 根节点不是字典
    assert "开头 '[1, 2]'" in err, err
    store.path.write_text("{ bad json", encoding="utf-8")
    _d2, err2, _r2 = store._parse("{ bad json")  # JSON 解析失败
    assert "开头 '{ bad json'" in err2, err2
    store.path.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    _d3, err3, _r3 = store._parse(json.dumps({"schema_version": 99}))  # schema 不符
    assert "开头" in err3, err3


def test_store_file_hint_variants(tmp_path):
    """取证串: 文件不存在 -> 空串; 空文件 -> 专用文案; 有内容 -> 截 40 字符"""
    store = HrSiteStore("s", str(tmp_path))
    assert store._file_hint() == ""  # stat 失败(文件不存在)
    store.path.write_text("", encoding="utf-8")
    assert store._file_hint() == "(文件为空 0 字节: 可能被编辑器 / 同步盘清空, 或写盘被中断)"
    text = "A" * 50
    store.path.write_text(text, encoding="utf-8")
    assert store._file_hint(text) == f"(文件 50 字节, 开头 {'A' * 40!r})"


def test_store_write_default_keeps_backup(tmp_path):
    """_write 默认 keep_backup=True: 不传实参也把上一版留为 .bak(commit 显式传参, 这里钉默认值)"""
    store = HrSiteStore("s", str(tmp_path), owner="me")
    with store.hold() as session:
        session.commit(now=1.0)
    assert not (tmp_path / "s.json.bak").exists(), "首次写盘无旧文件 -> 不产生 .bak"
    store._write(HrSiteData(), 2.0)
    assert (tmp_path / "s.json.bak").exists()


def test_store_write_unicode_and_sorted_keys(tmp_path):
    """落盘: ensure_ascii=False(中文不转义) + sort_keys=True(键序稳定, 便于 diff 与取证)"""
    store = HrSiteStore("s", str(tmp_path), owner="me")
    with store.hold() as session:
        session.data.index[1] = HrEntry(tid=1, name="例站 中文")
        session.commit(now=1.0)
    text = (tmp_path / "s.json").read_text(encoding="utf-8")
    assert "例站 中文" in text, "中文不得被转义(ensure_ascii=False)"
    assert text.startswith('{"downloaded"'), "顶层键按 sort_keys=True 排序"


def test_store_session_read_alerted_false_when_clean(tmp_path):
    """读正常时 read_alerted 初始为 False(供调用方决定是否另报一次)"""
    store = HrSiteStore("s", str(tmp_path))
    with store.hold() as session:
        assert session.read_alerted is False


def test_store_check_lock_heartbeat_zero_is_not_unsafe(tmp_path):
    """心跳自检下界是**严格** 0 < heartbeat: 心跳为 0 表示无快照, 不得判成「被覆盖」"""
    store = HrSiteStore("s", str(tmp_path), owner="me")
    with store.hold() as session:
        session.commit(now=10.0)  # 让 _last_write_heartbeat > 0
    payload = json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))
    payload["writer"] = {"instance_id": "me", "heartbeat": 0}  # 心跳 0(无快照)
    (tmp_path / "s.json").write_text(json.dumps(payload), encoding="utf-8")
    with store.hold() as session:
        assert session.writable is True, "0 < heartbeat 为假 -> 不是「心跳被覆盖」"


def test_store_recover_unmovable_keeps_backup(tmp_path):
    """坏文件挪不走时: 本次写盘不得把好备份盖成坏内容(keep_backup 要随恢复置 False)"""
    store = _write_versions(tmp_path, entries=(1, ))
    backup_before = (tmp_path / "s.json.bak").read_bytes()
    store.quarantine = lambda: ""  # 模拟挪走失败(被别的程序占用)
    (tmp_path / "s.json").write_text("{ 坏", encoding="utf-8")
    with store.hold() as session:
        assert session.recovered_from_backup is True
        assert "坏文件未能挪走(它将被下次写盘覆盖); 已从备份" in session.read_error, session.read_error
        assert session.commit(now=9.0) == "written"
    assert (tmp_path / "s.json.bak").read_bytes() == backup_before, "恢复后的写入不得把好备份盖成坏内容"
