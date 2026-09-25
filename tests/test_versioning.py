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
- test_migrate_chain_runs_stepwise: 临时注册 v1→v2→v3, 断言沿链逐级执行、中间态不被跳过
- test_migrate_stamps_version_each_step: 每完成一级由框架盖 schema_version 章(迁移函数不必自己改)
- test_migrate_idempotent: 对已迁移数据重复 apply 无二次变更(崩溃后重放同一条链即幂等)
- test_migrate_missing_step_fails_fast: 版本表抬了、迁移表没跟上 -> fail-fast, 不静默跳级
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
    assert "schema_version=99" in msg and "支持的 1" in msg


def test_detect_version_unknown_kind_rejected():
    """未注册 kind 报错(接入框架必须先在 CURRENT_VERSIONS 登记, 拼错 kind 早暴露)"""
    with pytest.raises(SchemaVersionError):
        detect_version("stete", {})


def test_migrate_noop():
    """已是最新版本: 原样返回, 不触发任何注册项, 也不打版本章(盖章是写点的职责)"""
    data = {"exec_history": {"k": 1}}
    out, desc = migrate("state", data)
    assert out is data and desc == ""
    assert "schema_version" not in out


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
