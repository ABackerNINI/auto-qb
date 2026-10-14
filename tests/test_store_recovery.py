"""test_store_recovery 测试计划: 读坏恢复链 infra 单点(issue 26-10-11-0240-refactor-hr-store-recover-lock-family-dup)

## 测试计划(每个测试函数一条)
- test_recover_quarantines_before_reading_backup: 编排顺序纪律 —— 先处置坏文件(留证)后读备份(顺序反了会丢现场)
- test_recover_without_quarantine_keeps_file_in_place: 不传 quarantine = 原地保留(state.json 口径), move_failed 恒 False
- test_recover_move_failure_flag: 处置回调返回空串(挪不动) -> moved_to 空 + move_failed True
- test_recover_backup_unavailable_reason_passthrough: 备份不可用时原因原样透出(recovered=False, data=None)
- test_recover_recovered_data_passthrough: 备份可用时数据原样透出(recovered=True)
- test_quarantine_bad_file_moves_with_timestamp: 坏文件挪到 `<path>.bad-<ts>`, 内容原样保留
- test_quarantine_bad_file_missing_returns_empty: 文件不存在(无处可挪) -> 空串
- test_quarantine_bad_file_replace_failure_returns_empty: 挪不动(OSError) -> 空串 + debug 留痕, 原文件保留现场
- test_recovery_chain_single_point_in_infra: 静态守阵 —— 恢复链编排单点只在 infra/store_recovery.py;
  hr/store.py 与 core/state.py 必须委托(自抄 `.bad-{int(time.time())}` 时间戳留证即红)
- test_filelock_dependency_single_point_in_infra_locking: 静态守阵 —— `from filelock import` 只在
  infra/locking.py(hr 站点锁与单实例锁同族收口; 别处再裸 import 即红)
"""
import logging
import os

import pytest

from auto_qb.infra import store_recovery
from auto_qb.infra.store_recovery import BadFileRecovery, quarantine_bad_file, recover_corrupt_file


def test_recover_quarantines_before_reading_backup(tmp_path, caplog):
    """编排顺序纪律: 先处置坏文件(留证)后读备份 —— 顺序反了会丢现场"""
    order = []

    def _quarantine():
        order.append("quarantine")
        return str(tmp_path / "s.json.bad-1")

    def _read_backup():
        order.append("read_backup")
        return {"k": 1}, None

    rec = recover_corrupt_file(
        read_backup=_read_backup,
        quarantine=_quarantine,
        logger=logging.getLogger("test"),
        what="测试",
    )
    assert order == ["quarantine", "read_backup"], "必须先留证再读备份(备份也不可用时, 写盘会覆盖现场)"
    assert rec == BadFileRecovery(
        recovered=True, data={"k": 1}, moved_to=str(tmp_path / "s.json.bad-1"), move_failed=False
    )


def test_recover_without_quarantine_keeps_file_in_place(tmp_path):
    """不传 quarantine = 原地保留(state.json 口径: 损坏文件原样保留待查, 不删除)"""
    rec = recover_corrupt_file(
        read_backup=lambda: ({
            "k": 1
        }, None),
        logger=logging.getLogger("test"),
        what="测试",
    )
    assert rec.moved_to == "" and rec.move_failed is False
    assert rec.recovered is True and rec.data == {"k": 1}


def test_recover_move_failure_flag(tmp_path):
    """处置回调返回空串(挪不动: 被占用等) -> moved_to 空 + move_failed True"""
    rec = recover_corrupt_file(
        read_backup=lambda: ({
            "k": 1
        }, None),
        quarantine=lambda: "",
        logger=logging.getLogger("test"),
        what="测试",
    )
    assert rec.moved_to == "" and rec.move_failed is True
    assert rec.recovered is True, "备份是否可用与坏文件挪不挪得动无关(hr: 挪不动时 keep_backup 置 False)"


def test_recover_backup_unavailable_reason_passthrough():
    """备份不可用时原因原样透出(recovered=False, data=None) —— 调用方写自己的消息"""
    rec = recover_corrupt_file(
        read_backup=lambda: (None, "没有备份文件"),
        quarantine=lambda: "",
        logger=logging.getLogger("test"),
        what="测试",
    )
    assert rec.recovered is False and rec.data is None and rec.backup_reason == "没有备份文件"


def test_recover_recovered_data_passthrough():
    """备份可用时数据原样透出(recovered=True) —— 解析口径(迁移链/三态)差异封在调用方回调"""
    rec = recover_corrupt_file(
        read_backup=lambda: ({
            "schema_version": 3
        }, None),
        quarantine=lambda: "",
        logger=logging.getLogger("test"),
        what="测试",
    )
    assert rec.recovered is True and rec.data == {"schema_version": 3} and rec.backup_reason == ""


def test_quarantine_bad_file_moves_with_timestamp(tmp_path):
    """坏文件挪到 `<path>.bad-<ts>`, 内容原样保留"""
    path = tmp_path / "s.json"
    path.write_text("{ 坏", encoding="utf-8")
    target = quarantine_bad_file(str(path), logger=logging.getLogger("test"), what="测试")
    assert target.startswith(str(path) + ".bad-")
    assert target.endswith(str(int(target.rsplit(".bad-", 1)[1]))), "时间戳形态: <path>.bad-<int ts>"
    assert not path.exists(), "坏文件已挪走"
    assert open(target, encoding="utf-8").read() == "{ 坏", "内容原样留证"


def test_quarantine_bad_file_missing_returns_empty(tmp_path):
    """文件不存在(无处可挪) -> 空串"""
    assert quarantine_bad_file(str(tmp_path / "never.json"), logger=logging.getLogger("test"), what="测试") == ""


def test_quarantine_bad_file_replace_failure_returns_empty(tmp_path, caplog, monkeypatch):
    """挪不动(被占用等 OSError) -> 空串 + debug 留痕, 原文件保留现场"""
    path = tmp_path / "s.json"
    path.write_text("{ 坏", encoding="utf-8")

    def boom(src, dst):
        raise OSError(13, "拒绝访问")

    monkeypatch.setattr(store_recovery.os, "replace", boom)
    with caplog.at_level(logging.DEBUG, logger="test.logger"):
        got = quarantine_bad_file(str(path), logger=logging.getLogger("test.logger"), what="测试")
    assert got == ""
    assert path.exists(), "挪不动时原文件保留现场"
    assert any("坏文件挪走失败" in r.getMessage() for r in caplog.records), "失败要留痕(debug, 不抛)"
    monkeypatch.undo()


def test_recovery_chain_single_point_in_infra():
    """静态守阵(issue 26-10-11-0240): 恢复链编排单点只在 infra/store_recovery.py

    hr/store.py 与 core/state.py 必须委托 recover_corrupt_file; 自抄「时间戳留证」
    (`.bad-{int(time.time())}` 挪文件)或各自重复「损坏 -> 读 .bak」编排即红。
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src" / "auto_qb"
    hits = sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*.py") if ".bad-{int(time.time())}" in p.read_text(encoding="utf-8")
    )
    assert hits == ["infra/store_recovery.py"], f"时间戳留证(.bad-<ts>)只允许在 infra 单点, 现分布: {hits}"
    for rel, needle in (
        ("hr/store.py", "recover_corrupt_file"),
        ("core/state.py", "recover_corrupt_file"),
    ):
        text = (root / rel).read_text(encoding="utf-8")
        assert needle in text, f"{rel} 必须委托 infra.store_recovery.{needle}"
        assert "quarantine_bad_file" in text or rel == "core/state.py", f"{rel} 的坏文件挪走应经 infra 单点"


def test_filelock_dependency_single_point_in_infra_locking():
    """静态守阵(issue 26-10-11-0240): filelock 依赖只在 infra/locking.py 单点

    hr 站点锁此前与单实例锁同族两套(各自裸 import filelock); 收口后别处再裸 import 即红。
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src" / "auto_qb"
    hits = sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*.py") if "from filelock import" in p.read_text(encoding="utf-8")
    )
    assert hits == ["infra/locking.py"], f"filelock 依赖只允许在 infra/locking.py 单点, 现分布: {hits}"
