"""test_versioning 测试计划: infra/versioning 落盘文件 schema 版本与逐级升级链(计划 26-09-26-0506)

## 测试计划(每个测试函数一条)
- test_detect_version_missing_is_v1: 字段缺失 = v1(存量文件口径, 存量文件零迁移成本)
- test_detect_version_valid: 合法 int 原样返回
- test_detect_version_non_int_rejected: 字符串 / None 等非 int 报 SchemaVersionError
- test_detect_version_bool_rejected: bool 是 int 子类, 必须显式排除(True 不算 1)
- test_detect_version_below_one_rejected: < 1 报错
- test_detect_version_future_rejected: 高于 CURRENT 报错, 且报错同时说清两个版本号
- test_detect_version_unknown_kind_rejected: 未注册 kind 报错
- test_migrate_noop: 已是最新版本原样返回(不触发任何注册项, 也不打版本章)
- test_migrate_state_v1_v3_strips_upload_snapshots: 生产迁移 v1→v3 清 upload_snapshots + 补 field_snapshots
- test_migrate_state_v2_v3_adds_field_snapshots: 生产迁移 v2→v3 补空 field_snapshots(升级零事件风暴)
- test_migrate_state_v3_field_snapshots_preserved: v3 数据已有 field_snapshots 时迁移/重读不覆盖
- test_migrate_chain_runs_stepwise: 临时注册 v1→v2→v3, 断言沿链逐级执行、中间态不被跳过
- test_migrate_stamps_version_each_step: 每完成一级由框架盖 schema_version 章(迁移函数不必自己改)
- test_migrate_idempotent: 对已迁移数据重复 apply 无二次变更(崩溃后重放同一条链即幂等)
- test_migrate_missing_step_fails_fast: 版本表抬了、迁移表没跟上 -> fail-fast, 不静默跳级
- test_migrate_with_notes_collects_step_notes: 迁移函数返回 (dict, notes) 时明细沿链汇聚; migrate() 二元组契约不变
- test_migrate_with_notes_plain_dict_steps: 迁移函数返回裸 dict(无明细)时 notes 为空 —— 兼容全部既有迁移
- test_migrate_hr_site_v1_v2_full: quota->rate / refresh->wave 两个 dict 支路, 旧键清理 + 保留键原样
- test_migrate_hr_site_v1_v2_non_dict_quota_refresh: quota / refresh 非 dict -> 不派生 rate / wave
- test_migrate_hr_site_v1_v2_bad_values_fallback: 非法数值兜底(缺键 / 非 int 计数 / 不可转换时间戳)
"""
import pytest

from auto_qb.infra import versioning
from auto_qb.infra.errors import SchemaVersionError
from auto_qb.infra.versioning import detect_version, migrate


def test_detect_version_missing_is_v1():
    """字段缺失 = v1(存量文件口径): state.json 现行结构即 v1, 不带字段也照常加载"""
    assert detect_version("state", {"exec_history": {}}) == 1


def test_detect_version_valid():
    """合法 int 原样返回"""
    assert detect_version("state", {"schema_version": 1}) == 1


def test_detect_version_non_int_rejected():
    """非 int(字符串 / None / 浮点)报 SchemaVersionError, 与内容损坏区别对待"""
    for bad in ("1", None, 1.0, [1]):
        with pytest.raises(SchemaVersionError):
            detect_version("state", {"schema_version": bad})


def test_detect_version_bool_rejected():
    """bool 是 int 的子类, 必须显式排除 —— 否则 True 会被 isinstance(int) 放行成 1"""
    with pytest.raises(SchemaVersionError):
        detect_version("state", {"schema_version": True})


def test_detect_version_below_one_rejected():
    """< 1 报错"""
    with pytest.raises(SchemaVersionError):
        detect_version("state", {"schema_version": 0})
    with pytest.raises(SchemaVersionError):
        detect_version("state", {"schema_version": -2})


def test_detect_version_future_rejected():
    """高于 CURRENT 报错(fail-fast), 且同时说清文件版本与程序支持版本 —— 排障的唯一线索"""
    with pytest.raises(SchemaVersionError) as ei:
        detect_version("state", {"schema_version": 99})
    msg = str(ei.value)
    assert "schema_version=99" in msg and f"支持的 {versioning.CURRENT_VERSIONS['state']}" in msg


def test_detect_version_unknown_kind_rejected():
    """未注册 kind 报错(接入框架必须先在 CURRENT_VERSIONS 登记, 拼错 kind 早暴露)"""
    with pytest.raises(SchemaVersionError):
        detect_version("stete", {})


def test_migrate_noop():
    """已是最新版本: 原样返回, 不触发任何注册项, 也不打版本章(盖章是写点的职责)"""
    data = {"schema_version": versioning.CURRENT_VERSIONS["state"], "exec_history": {"k": 1}}
    out, desc = migrate("state", data)
    assert out is data and desc == ""
    assert out["schema_version"] == versioning.CURRENT_VERSIONS["state"]


def test_migrate_state_v1_v3_strips_upload_snapshots():
    """生产迁移 v1→v3(两连跳): 清掉 upload_snapshots(计划 26-09-27-1232) + 补空 field_snapshots
    (计划 26-09-27-1438), 其余键原样保留"""
    data = {
        "exec_history": {
            "r:h": {
                "ts": 1.0,
                "date": "2026-09-27",
                "hour": 12
            }
        },
        "upload_snapshots": {
            "daily": {
                "key": "2026-09-27",
                "baseline": {
                    "H1": 100
                }
            }
        },
    }
    out, desc = migrate("state", data)
    assert desc == f"v1→v{versioning.CURRENT_VERSIONS['state']}"
    assert out["schema_version"] == versioning.CURRENT_VERSIONS["state"]
    assert "upload_snapshots" not in out
    assert out["exec_history"] == data["exec_history"]
    assert out["field_snapshots"] == {}, "v2→v3 应补空 field_snapshots(全部种子按首见处理, 零事件风暴)"


def test_migrate_state_v2_v3_adds_field_snapshots():
    """生产迁移 v2→v3: 仅补空 field_snapshots 表, 其余结构不动(升级即按首见落基线)"""
    data = {"schema_version": 2, "exec_history": {"r:h": {"ts": 1.0}}}
    out, desc = migrate("state", data)
    assert desc == "v2→v3"
    assert out["schema_version"] == 3
    assert out["field_snapshots"] == {}
    assert out["exec_history"] == data["exec_history"]


def test_migrate_state_v3_field_snapshots_preserved():
    """v3 数据已带 field_snapshots: setdefault 幂等, 重放/重读不覆盖已有基线"""
    data = {
        "schema_version": 3,
        "field_snapshots": {
            "H1": {
                "tags": ["R"],
                "category": "pass"
            }
        },
    }
    out, desc = migrate("state", data)
    assert desc == ""
    assert out["field_snapshots"] == {"H1": {"tags": ["R"], "category": "pass"}}


def test_migrate_chain_runs_stepwise(monkeypatch):
    """临时注册假 v1→v2→v3: 沿链逐级执行, 中间态不被跳过(执行顺序即链序)"""
    calls = []

    def step_1_2(d):
        calls.append("1→2")
        return {**d, "v2": d["base"] + 1}

    def step_2_3(d):
        calls.append("2→3")
        assert "v2" in d and "v3" not in d, "每级只看到上一级的产物, 不感知更早历史"
        return {**d, "v3": d["v2"] * 2}

    monkeypatch.setitem(versioning.CURRENT_VERSIONS, "state", 3)
    monkeypatch.setitem(versioning.MIGRATIONS, "state", {1: step_1_2, 2: step_2_3})
    data, desc = migrate("state", {"base": 1})
    assert calls == ["1→2", "2→3"], f"必须按链序逐级执行: {calls}"
    assert data == {"base": 1, "v2": 2, "v3": 4, "schema_version": 3}
    assert desc == "v1→v3"


def test_migrate_stamps_version_each_step(monkeypatch):
    """每完成一级由框架盖 schema_version 章 —— 迁移函数只管结构, 不必自己改版本字段"""
    def step_1_2(d):
        assert d["schema_version"] == 1, "进入迁移函数时版本章还是旧级别"
        return {**d, "new": True}

    monkeypatch.setitem(versioning.CURRENT_VERSIONS, "state", 2)
    monkeypatch.setitem(versioning.MIGRATIONS, "state", {1: step_1_2})
    data, _ = migrate("state", {"schema_version": 1})
    assert data["schema_version"] == 2


def test_migrate_idempotent(monkeypatch):
    """对已迁移数据重复 apply 无二次变更 —— 落盘前崩溃时, 下次启动重放同一条链即收敛"""
    def step_1_2(d):
        return {**d, "n": d.get("n", 0) + 1}

    monkeypatch.setitem(versioning.CURRENT_VERSIONS, "state", 2)
    monkeypatch.setitem(versioning.MIGRATIONS, "state", {1: step_1_2})
    once, desc = migrate("state", {"schema_version": 1})
    assert once["n"] == 1 and desc == "v1→v2"
    twice, desc2 = migrate("state", once)
    assert twice == once and desc2 == "", "第二次应识别为已是最新, 不再执行任何迁移"


def test_migrate_missing_step_fails_fast(monkeypatch):
    """版本表抬到 3 但迁移表只有 1→2: fail-fast 报缺项, 不静默跳级(两表必须同步演化)"""
    def step_1_2(d):
        return {**d, "v2": True}

    monkeypatch.setitem(versioning.CURRENT_VERSIONS, "state", 3)
    monkeypatch.setitem(versioning.MIGRATIONS, "state", {1: step_1_2})
    with pytest.raises(SchemaVersionError) as ei:
        migrate("state", {"schema_version": 1})
    assert "v2→v3" in str(ei.value)


def test_migrate_with_notes_collects_step_notes(monkeypatch):
    """migrate_with_notes: 迁移函数返回 (dict, notes) 时明细沿链逐级汇聚(顺序即链序)

    config v3→v4 的「显式置空已移除」逐键 WARNING 走此通道(迁移函数不 log, 明细交调用链)。
    既有 migrate() 的二元组契约不变 —— state/hr_site 调用方零改动。
    """
    def step_1_2(d):
        return {**d, "v2": True}, ["k1: 已移除"]

    def step_2_3(d):
        return {**d, "v3": True}, ["k2: 已移除"]

    monkeypatch.setitem(versioning.CURRENT_VERSIONS, "state", 3)
    monkeypatch.setitem(versioning.MIGRATIONS, "state", {1: step_1_2, 2: step_2_3})
    data, desc, notes = versioning.migrate_with_notes("state", {"schema_version": 1})
    assert data["schema_version"] == 3 and desc == "v1→v3", "检测/逐级/盖章口径与 migrate() 一致"
    assert notes == ["k1: 已移除", "k2: 已移除"]

    # 既有 migrate() 二元组解包照常工作, 明细不外泄
    data2, desc2 = migrate("state", {"schema_version": 1})
    assert desc2 == "v1→v3" and data2["schema_version"] == 3


def test_migrate_with_notes_plain_dict_steps(monkeypatch):
    """迁移函数返回裸 dict(无明细)时 notes 为空 —— 兼容全部既有迁移, 无需逐个改造"""
    monkeypatch.setitem(versioning.CURRENT_VERSIONS, "state", 2)
    monkeypatch.setitem(versioning.MIGRATIONS, "state", {1: lambda d: {**d, "v2": True}})
    data, desc, notes = versioning.migrate_with_notes("state", {"schema_version": 1})
    assert desc == "v1→v2" and notes == [] and data["schema_version"] == 2


def test_migrate_hr_site_v1_v2_full():
    """生产迁移 hr_site v1→v2(波次模型 v3): quota→rate / refresh→wave 两个 dict 支路,
    5 个旧键 + refresh 整键清理, 保留键(index/downloaded/fails/verified/revision/
    fetched_at/expires_at/writer)原样"""
    kept = {
        "index": {
            "h1": {
                "row": 1
            }
        },
        "downloaded": ["h1"],
        "fails": 1,
        "verified": {
            "h1": 100.0
        },
        "revision": 7,
        "fetched_at": 123.0,
        "expires_at": 456.0,
        "writer": "test",
    }
    data = {
        "schema_version": 1,
        **kept,
        "quota": {
            "day_window": "2026-10-01",
            "day_count": 3,
            "last_fetch_ts": 100.5
        },
        "torrent_quota": {
            "dl": 1
        },
        "fuse": {
            "trips": 1
        },
        "suspended": True,
        "login_backoff_until": 99.0,
        "login_expired_streak": 2,
        "refresh": {
            "last_success_ts": 55.5,
            "reason": "ok",
            "rows_baseline": 10
        },
    }
    out, desc = migrate("hr_site", data)
    assert desc == "v1→v2" and out["schema_version"] == 2
    # quota → rate(单账本): day_window / day_count / last_fetch_ts 逐字段对齐
    assert out["rate"] == {"day_window": "2026-10-01", "day_count": 3, "last_fetch_ts": 100.5}
    # refresh → wave: last_success_ts 同时喂 wave_ts 与 healthy_ts, reason 变 notes
    assert out["wave"] == {"wave_ts": 55.5, "healthy_ts": 55.5, "notes": "ok"}
    for gone in (
        "quota", "torrent_quota", "fuse", "suspended", "login_backoff_until", "login_expired_streak", "refresh"
    ):
        assert gone not in out, f"{gone} 应随 v2 退役"
    for k, v in kept.items():
        assert out[k] == v, f"保留键 {k} 必须原样"


def test_migrate_hr_site_v1_v2_non_dict_quota_refresh():
    """quota / refresh 非 dict(损坏或异构存量) -> 两个支路都不派生, 迁移本身不炸"""
    data = {"schema_version": 1, "revision": 1, "quota": None, "refresh": "bad"}
    out, desc = migrate("hr_site", data)
    assert desc == "v1→v2"
    assert "rate" not in out and "wave" not in out
    assert out["revision"] == 1


def test_migrate_hr_site_v1_v2_bad_values_fallback():
    """非法数值兜底: day_window 缺失 -> "", day_count 非 int -> 0, 时间戳不可转换(None/
    非数字串) -> 0.0, reason 缺失 -> "" —— 迁移不因脏数据中断"""
    data = {
        "schema_version": 1,
        "quota": {
            "day_count": "3",
            "last_fetch_ts": "abc"
        },  # day_window 缺失; 计数非 int; ts 非数字
        "refresh": {
            "last_success_ts": None
        },  # reason 缺失; ts None
    }
    out, _ = migrate("hr_site", data)
    assert out["rate"] == {"day_window": "", "day_count": 0, "last_fetch_ts": 0.0}
    assert out["wave"] == {"wave_ts": 0.0, "healthy_ts": 0.0, "notes": ""}
