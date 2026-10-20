"""正主注册与让位判定守阵 (计划 26-10-20-1316 §03, identity 模块).

同机多安装 (auto-qb A/B 各带一份 gtm) 的身份层: 三处 ID (安装/指针记录/数据) +
启动判定矩阵 ①②③④ + 让位/被拒注记。全部用例 hermetic: tmp_path 造安装根与指针
目录, monkeypatch 重定向 gtm.identity 的路径单点 (resolve_tool_root/pointer_dir)
与代拉起单点 (_spawn), 不碰真实安装目录与真实进程。

## 测试计划

- 安装 ID: 缺失 -> 生成 uuid4 落盘 (二次加载原样读回, 幂等); 已存在 -> 原样加载;
  读失败 (ID 路径是目录, OSError) -> IdentityError; 写失败 -> IdentityError
  (没有持久身份的安装不许静默用内存值参与判定)
- 正主记录读: 缺失 -> None; 合法 -> PrimaryRecord (install_path realpath 归一);
  坏 JSON / schema 未知 / 顶层非对象 / 缺 id 或缺 install_path -> None 且不抛
  (一律按无记录降级, 照指针同族纪律, 不猜字段)
- 认领: O_EXCL 原子建文件 (payload schema+四字段); 已存在 -> PrimaryRecordExists;
  写半途失败 (fsync 抛) -> 撤占位不留坏记录, 包装 IdentityError 上抛
- data_dir 补写: 仅「自己的记录且 data_dir 为空」才写; 非空 / 非己 / 无记录 -> 不动
  (记录零自动刷新的唯一例外)
- 数据归属: tool-id 缺失 -> 写入本安装 id; 相同 -> 过; 不同 -> IdentityError
  (跨版本接管拒绝); 落盘失败 -> IdentityError
- 注记: write -> payload 含 schema/reason/from/target/detail/at; clear 幂等 (缺失
  不抛); 写失败只 WARNING 不抛 (可见性便利不阻断让位)
- 判定矩阵: 无记录 -> claim; id 同 path 同 -> primary; id 同 path 异 -> refuse
  (拷贝件/被移动); id 异且自洽 -> relay; id 异但记录 install_path 指向自己 -> refuse
  (记录自相矛盾); id 异但目标安装 tool-id 与记录 id 不符 -> refuse (张冠李戴)
- resolve_startup: 无记录 -> 认领后 primary; 记录已存在 (别的安装) -> relay 不认领;
  记录存在但不可解析 (schema 未知) -> IdentityError, 不覆盖不猜
- 代拉: 启动器存在 -> _spawn (cmd.exe /c launch.cmd 或 sh launch.sh, cwd=安装根)
  且返回启动器路径; 启动器缺失 -> None 且不 spawn; spawn 抛 OSError -> None
- cmd_run 集成 (退出码 + 注记): 安装 ID 不可写 -> 1; refuse -> 1 + deferred
  reason=refused; relay -> 0 + reason=relayed + _spawn 已呼叫
- cmd_claim 集成 (人工易主通道, D5): 成功 -> 记录三项全换成本安装事实 + data-id
  认领 + 清注记; 工具在跑 (锁争) -> 拒绝且不碰记录; data-id 异 -> 拒绝且不碰记录
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pytest

from gtm.__main__ import cmd_claim, cmd_run
from gtm.identity import (
    Decision,
    DeferredNote,
    Identity,
    IdentityError,
    PrimaryRecord,
    PrimaryRecordExists,
    claim_primary,
    clear_deferred,
    ensure_data_ownership,
    evaluate_startup,
    fill_primary_data_dir,
    load_or_create_install_id,
    read_primary,
    relay_launch,
    resolve_startup,
    write_deferred,
)
from gtm.storage import SingleInstanceLock, instance_lock_path

LAUNCHER_NAME = "launch.cmd" if os.name == "nt" else "launch.sh"

# ---------------- hermetic 助手 ----------------


def fake_install(tmp_path: Path, name: str, install_id: str | None = None) -> str:
    """造一个假安装根 (realpath 归一, 与 read_primary 的归一口径一致); 可选预置 tool-id."""
    root = os.path.realpath(str(tmp_path / name))
    os.makedirs(root, exist_ok=True)
    if install_id is not None:
        (Path(root) / "tool-id").write_text(install_id + "\n", encoding="utf-8")
    return root


def patch_paths(monkeypatch, tmp_path: Path, install_root: str, pointer: str) -> None:
    """重定向路径单点: gtm.identity (安装根 + 记录/注记) 与 gtm.storage (claim 的单实例锁).

    两个命名空间各持一份 pointer_dir 引用 (identity 与 storage 各自 import), 必须同址
    重定向, 否则 claim 的锁与记录会落在不同目录。
    """
    monkeypatch.setattr("gtm.identity.resolve_tool_root", lambda: install_root)
    monkeypatch.setattr("gtm.identity.pointer_dir", lambda: pointer)
    monkeypatch.setattr("gtm.storage.pointer_dir", lambda: pointer)


def write_primary_file(
    pointer: str, *, id_: str, install_path: str, data_dir: str = "", version: str = "9.9.9"
) -> None:
    """直接往指针目录写一份 primary.json (绕过认领, 造既有事实)."""
    payload = {
        "schema": 1,
        "id": id_,
        "install_path": install_path,
        "data_dir": data_dir,
        "version": version,
    }
    Path(pointer).mkdir(parents=True, exist_ok=True)
    Path(pointer, "primary.json").write_text(json.dumps(payload), encoding="utf-8")


def read_deferred(pointer: str) -> dict:
    return json.loads(Path(pointer, "deferred.json").read_text(encoding="utf-8"))


def run_args() -> argparse.Namespace:
    return argparse.Namespace(command="run", data_dir=None, autostart=False)


# ---------------- 安装 ID ----------------


def test_install_id_created_then_loaded_idempotent(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")
    patch_paths(monkeypatch, tmp_path, root, str(tmp_path / "ptr"))
    identity = load_or_create_install_id()
    assert identity.install_root == root
    assert identity.install_id
    assert (Path(root) / "tool-id").read_text(encoding="utf-8").strip() == identity.install_id
    # 幂等: 二次加载读回同一 id (不重新生成)
    assert load_or_create_install_id().install_id == identity.install_id


def test_install_id_existing_loaded_as_is(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst", install_id="fixed-id-123")
    patch_paths(monkeypatch, tmp_path, root, str(tmp_path / "ptr"))
    assert load_or_create_install_id().install_id == "fixed-id-123"


def test_install_id_read_failure_raises(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")
    # 把 tool-id 占成目录: open 读抛 IsADirectoryError (OSError 家族)
    os.makedirs(Path(root) / "tool-id", exist_ok=True)
    patch_paths(monkeypatch, tmp_path, root, str(tmp_path / "ptr"))
    with pytest.raises(IdentityError):
        load_or_create_install_id()


def test_install_id_write_failure_raises(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")

    def boom(path, text):
        raise OSError("readonly install dir")

    monkeypatch.setattr("gtm.identity.atomic_write_text", boom)
    patch_paths(monkeypatch, tmp_path, root, str(tmp_path / "ptr"))
    with pytest.raises(IdentityError):
        load_or_create_install_id()


# ---------------- 正主记录读 ----------------


def test_read_primary_missing_returns_none(tmp_path, monkeypatch):
    patch_paths(monkeypatch, tmp_path, fake_install(tmp_path, "inst"), str(tmp_path / "ptr"))
    assert read_primary() is None


def test_read_primary_valid(tmp_path, monkeypatch):
    root_b = fake_install(tmp_path, "b")
    ptr = str(tmp_path / "ptr")
    write_primary_file(ptr, id_="id-a", install_path=root_b, data_dir="/d", version="1.2.3")
    patch_paths(monkeypatch, tmp_path, fake_install(tmp_path, "a"), ptr)
    record = read_primary()
    assert record is not None
    assert record.id == "id-a"
    assert record.install_path == root_b
    assert record.data_dir == "/d"
    assert record.version == "1.2.3"


@pytest.mark.parametrize(
    "text",
    [
        "{ not json",  # 坏 JSON
        '{"schema": 999, "id": "x", "install_path": "/p"}',  # schema 未知
        '["not", "an", "object"]',  # 顶层非对象
        '{"schema": 1, "install_path": "/p"}',  # 缺 id
        '{"schema": 1, "id": "x"}',  # 缺 install_path
    ]
)
def test_read_primary_degraded_to_none(tmp_path, monkeypatch, text):
    ptr = str(tmp_path / "ptr")
    Path(ptr).mkdir(parents=True, exist_ok=True)
    Path(ptr, "primary.json").write_text(text, encoding="utf-8")
    patch_paths(monkeypatch, tmp_path, fake_install(tmp_path, "inst"), ptr)
    assert read_primary() is None  # 一律按无记录降级, 不抛不猜


# ---------------- 认领 ----------------


def test_claim_primary_creates_record(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")
    ptr = str(tmp_path / "ptr")
    patch_paths(monkeypatch, tmp_path, root, ptr)
    identity = Identity(install_root=root, install_id="id-x")
    record = claim_primary(identity)
    assert record.id == "id-x" and record.install_path == root
    payload = json.loads(Path(ptr, "primary.json").read_text(encoding="utf-8"))
    assert payload["schema"] == 1
    assert payload["data_dir"] == ""  # data_dir 由启动时补写, 认领时为空
    assert payload["version"]


def test_claim_primary_existing_raises(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")
    ptr = str(tmp_path / "ptr")
    patch_paths(monkeypatch, tmp_path, root, ptr)
    claim_primary(Identity(install_root=root, install_id="id-x"))
    with pytest.raises(PrimaryRecordExists):
        claim_primary(Identity(install_root=root, install_id="id-y"))


def test_claim_primary_write_failure_leaves_no_record(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")
    ptr = str(tmp_path / "ptr")
    patch_paths(monkeypatch, tmp_path, root, ptr)

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(os, "fsync", boom)
    # 写半途失败撤占位, 且包装为 IdentityError (cmd_run 只捕模块规范异常)
    with pytest.raises(IdentityError):
        claim_primary(Identity(install_root=root, install_id="id-x"))
    # 撤占位: 不留坏记录挡后来者
    assert not Path(ptr, "primary.json").exists()


# ---------------- data_dir 补写 ----------------


def test_fill_primary_data_dir_only_when_own_and_empty(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")
    ptr = str(tmp_path / "ptr")
    patch_paths(monkeypatch, tmp_path, root, ptr)
    identity = Identity(install_root=root, install_id="id-x")
    write_primary_file(ptr, id_="id-x", install_path=root, data_dir="")
    fill_primary_data_dir(identity, "/data/dir")
    assert read_primary().data_dir == "/data/dir"
    # 非空不动
    fill_primary_data_dir(identity, "/other/dir")
    assert read_primary().data_dir == "/data/dir"


def test_fill_primary_data_dir_skips_foreign_or_missing(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")
    other = fake_install(tmp_path, "other")
    ptr = str(tmp_path / "ptr")
    patch_paths(monkeypatch, tmp_path, root, ptr)
    # 非己记录: 不动
    write_primary_file(ptr, id_="id-other", install_path=other, data_dir="")
    fill_primary_data_dir(Identity(install_root=root, install_id="id-x"), "/data/dir")
    assert read_primary().data_dir == ""
    # 无记录: 不动 (不凭空造)
    Path(ptr, "primary.json").unlink()
    fill_primary_data_dir(Identity(install_root=root, install_id="id-x"), "/data/dir")
    assert read_primary() is None


# ---------------- 数据归属 ----------------


def test_ensure_data_ownership_claim_same_different(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")
    patch_paths(monkeypatch, tmp_path, root, str(tmp_path / "ptr"))
    identity = Identity(install_root=root, install_id="id-x")
    data_dir = str(tmp_path / "data")
    # 缺失 -> 认领写入
    ensure_data_ownership(data_dir, identity)
    assert (Path(data_dir) / "tool-id").read_text(encoding="utf-8").strip() == "id-x"
    # 相同 -> 过 (幂等)
    ensure_data_ownership(data_dir, identity)
    # 不同 -> IdentityError (跨版本接管拒绝)
    with pytest.raises(IdentityError):
        ensure_data_ownership(data_dir, Identity(install_root=root, install_id="id-y"))


def test_ensure_data_ownership_write_failure_raises(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")
    patch_paths(monkeypatch, tmp_path, root, str(tmp_path / "ptr"))

    def boom(path, text):
        raise OSError("readonly data dir")

    monkeypatch.setattr("gtm.identity.atomic_write_text", boom)
    with pytest.raises(IdentityError):
        ensure_data_ownership(str(tmp_path / "data"), Identity(install_root=root, install_id="id-x"))


# ---------------- 注记 ----------------


def test_deferred_write_clear_idempotent(tmp_path, monkeypatch):
    ptr = str(tmp_path / "ptr")
    patch_paths(monkeypatch, tmp_path, fake_install(tmp_path, "inst"), ptr)
    write_deferred(
        DeferredNote(reason="relayed", from_install="/from", target_install="/to", target_id="id-a", detail="msg")
    )
    note = read_deferred(ptr)
    assert note["reason"] == "relayed" and note["from_install"] == "/from"
    assert note["target_install"] == "/to" and note["target_id"] == "id-a"
    assert note["detail"] == "msg" and note["at"] and note["schema"] == 1
    clear_deferred()
    assert not Path(ptr, "deferred.json").exists()
    clear_deferred()  # 幂等: 缺失不抛


def test_deferred_write_failure_only_warns(tmp_path, monkeypatch):
    ptr = str(tmp_path / "ptr")
    patch_paths(monkeypatch, tmp_path, fake_install(tmp_path, "inst"), ptr)

    def boom(path, text):
        raise OSError("readonly pointer dir")

    monkeypatch.setattr("gtm.identity.atomic_write_text", boom)
    write_deferred(DeferredNote(reason="refused", from_install="/from"))  # 不抛
    assert not Path(ptr, "deferred.json").exists()


# ---------------- 判定矩阵 ①②③④ ----------------


def test_matrix_claim_when_no_record(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")
    patch_paths(monkeypatch, tmp_path, root, str(tmp_path / "ptr"))
    decision = evaluate_startup(Identity(install_root=root, install_id="id-x"))
    assert decision.kind == "claim"
    assert decision.record is None


def test_matrix_primary_when_id_and_path_match(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")
    ptr = str(tmp_path / "ptr")
    write_primary_file(ptr, id_="id-x", install_path=root)
    patch_paths(monkeypatch, tmp_path, root, ptr)
    decision = evaluate_startup(Identity(install_root=root, install_id="id-x"))
    assert decision.kind == "primary"
    assert decision.record.id == "id-x"


def test_matrix_refuse_when_id_matches_path_differs(tmp_path, monkeypatch):
    root_a = fake_install(tmp_path, "a", install_id="id-x")  # 正主 (记录里的)
    root_copy = fake_install(tmp_path, "copy", install_id="id-x")  # 拷贝件: 同 id 异 path
    ptr = str(tmp_path / "ptr")
    write_primary_file(ptr, id_="id-x", install_path=root_a)
    patch_paths(monkeypatch, tmp_path, root_copy, ptr)
    decision = evaluate_startup(Identity(install_root=root_copy, install_id="id-x"))
    assert decision.kind == "refuse"
    assert "install_path" in decision.message


def test_matrix_relay_when_other_install_is_primary(tmp_path, monkeypatch):
    root_a = fake_install(tmp_path, "a", install_id="id-a")  # 注册正主
    root_b = fake_install(tmp_path, "b", install_id="id-b")  # 本安装 (后启动的 B)
    ptr = str(tmp_path / "ptr")
    write_primary_file(ptr, id_="id-a", install_path=root_a)
    patch_paths(monkeypatch, tmp_path, root_b, ptr)
    decision = evaluate_startup(Identity(install_root=root_b, install_id="id-b"))
    assert decision.kind == "relay"
    assert decision.record.install_path == root_a


def test_matrix_refuse_when_record_points_at_self_but_id_differs(tmp_path, monkeypatch):
    root_b = fake_install(tmp_path, "b", install_id="id-b")
    ptr = str(tmp_path / "ptr")
    # 记录 install_path 指向本安装, 但 id 不符: 自相矛盾
    write_primary_file(ptr, id_="id-a", install_path=root_b)
    patch_paths(monkeypatch, tmp_path, root_b, ptr)
    decision = evaluate_startup(Identity(install_root=root_b, install_id="id-b"))
    assert decision.kind == "refuse"
    assert "矛盾" in decision.message


def test_matrix_refuse_when_target_install_id_mismatches_record(tmp_path, monkeypatch):
    root_a = fake_install(tmp_path, "a", install_id="id-real-a")  # 真实 id 与记录不符
    root_b = fake_install(tmp_path, "b", install_id="id-b")
    ptr = str(tmp_path / "ptr")
    write_primary_file(ptr, id_="id-a", install_path=root_a)  # 张冠李戴
    patch_paths(monkeypatch, tmp_path, root_b, ptr)
    decision = evaluate_startup(Identity(install_root=root_b, install_id="id-b"))
    assert decision.kind == "refuse"
    assert "矛盾" in decision.message


# ---------------- resolve_startup (判定 + 认领 + 并发输家重判) ----------------


def test_resolve_startup_claims_when_no_record(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")
    ptr = str(tmp_path / "ptr")
    patch_paths(monkeypatch, tmp_path, root, ptr)
    decision = resolve_startup(Identity(install_root=root, install_id="id-x"))
    assert decision.kind == "primary"
    assert read_primary().id == "id-x"  # 确实落了记录


def test_resolve_startup_relays_when_record_exists(tmp_path, monkeypatch):
    root_a = fake_install(tmp_path, "a", install_id="id-a")
    root_b = fake_install(tmp_path, "b", install_id="id-b")
    ptr = str(tmp_path / "ptr")
    write_primary_file(ptr, id_="id-a", install_path=root_a)
    patch_paths(monkeypatch, tmp_path, root_b, ptr)
    decision = resolve_startup(Identity(install_root=root_b, install_id="id-b"))
    assert decision.kind == "relay"  # 不认领, 让位


def test_resolve_startup_unparsable_record_raises(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")
    ptr = str(tmp_path / "ptr")
    # schema 未知: evaluate 判 claim -> 认领撞 PrimaryRecordExists -> 重判仍 claim
    Path(ptr).mkdir(parents=True, exist_ok=True)
    Path(ptr, "primary.json").write_text('{"schema": 999, "id": "x", "install_path": "/p"}', encoding="utf-8")
    patch_paths(monkeypatch, tmp_path, root, ptr)
    with pytest.raises(IdentityError):
        resolve_startup(Identity(install_root=root, install_id="id-x"))
    # 坏记录原样保留 (不覆盖不猜)
    assert json.loads(Path(ptr, "primary.json").read_text(encoding="utf-8"))["schema"] == 999


# ---------------- 代拉 ----------------


def test_relay_launch_spawns_target_launcher(tmp_path, monkeypatch):
    root_a = fake_install(tmp_path, "a", install_id="id-a")
    Path(root_a, LAUNCHER_NAME).write_text("rem\n", encoding="utf-8")
    spawned: list = []
    monkeypatch.setattr("gtm.identity._spawn", lambda args, **kw: spawned.append((args, kw)))
    launcher = relay_launch(root_a)
    assert launcher == os.path.join(root_a, LAUNCHER_NAME)
    args, kwargs = spawned[0]
    assert args[:2] == (["cmd.exe", "/c"] if os.name == "nt" else ["/bin/sh"])
    assert args[-1] == launcher
    assert kwargs["cwd"] == root_a  # 相对定位以安装根为准


def test_relay_launch_missing_launcher_returns_none(tmp_path, monkeypatch):
    root_a = fake_install(tmp_path, "a", install_id="id-a")  # 无启动器
    spawned: list = []
    monkeypatch.setattr("gtm.identity._spawn", lambda args, **kw: spawned.append((args, kw)))
    assert relay_launch(root_a) is None
    assert not spawned  # 不 spawn


def test_relay_launch_spawn_failure_returns_none(tmp_path, monkeypatch):
    root_a = fake_install(tmp_path, "a", install_id="id-a")
    Path(root_a, LAUNCHER_NAME).write_text("rem\n", encoding="utf-8")

    def boom(args, **kw):
        raise OSError("spawn denied")

    monkeypatch.setattr("gtm.identity._spawn", boom)
    assert relay_launch(root_a) is None


# ---------------- cmd_run 集成 (退出码 + 注记 + 代拉) ----------------


def test_cmd_run_refuse_exits_1_with_note(tmp_path, monkeypatch):
    root_a = fake_install(tmp_path, "a", install_id="id-x")  # 注册正主
    root_copy = fake_install(tmp_path, "copy", install_id="id-x")  # 拷贝件本安装
    ptr = str(tmp_path / "ptr")
    write_primary_file(ptr, id_="id-x", install_path=root_a)
    patch_paths(monkeypatch, tmp_path, root_copy, ptr)
    assert cmd_run(run_args()) == 1
    note = read_deferred(ptr)
    assert note["reason"] == "refused"
    assert note["from_install"] == root_copy
    assert note["target_install"] == root_a  # 记录里指向的正主


def test_cmd_run_relay_exits_0_spawns_and_notes(tmp_path, monkeypatch):
    root_a = fake_install(tmp_path, "a", install_id="id-a")
    Path(root_a, LAUNCHER_NAME).write_text("rem\n", encoding="utf-8")
    root_b = fake_install(tmp_path, "b", install_id="id-b")  # 本安装 (让位方)
    ptr = str(tmp_path / "ptr")
    write_primary_file(ptr, id_="id-a", install_path=root_a)
    patch_paths(monkeypatch, tmp_path, root_b, ptr)
    spawned: list = []
    monkeypatch.setattr("gtm.identity._spawn", lambda args, **kw: spawned.append((args, kw)))
    assert cmd_run(run_args()) == 0
    assert spawned and spawned[0][1]["cwd"] == root_a  # 代拉正主
    note = read_deferred(ptr)
    assert note["reason"] == "relayed"
    assert note["from_install"] == root_b and note["target_install"] == root_a


def test_cmd_run_relay_missing_launcher_still_notes(tmp_path, monkeypatch):
    root_a = fake_install(tmp_path, "a", install_id="id-a")  # 无启动器
    root_b = fake_install(tmp_path, "b", install_id="id-b")
    ptr = str(tmp_path / "ptr")
    write_primary_file(ptr, id_="id-a", install_path=root_a)
    patch_paths(monkeypatch, tmp_path, root_b, ptr)
    spawned: list = []
    monkeypatch.setattr("gtm.identity._spawn", lambda args, **kw: spawned.append((args, kw)))
    assert cmd_run(run_args()) == 0
    assert not spawned
    assert "启动器缺失" in read_deferred(ptr)["detail"]


def test_cmd_run_identity_error_exits_1(tmp_path, monkeypatch):
    root = fake_install(tmp_path, "inst")  # 无 tool-id -> 走生成 -> 落盘被禁
    ptr = str(tmp_path / "ptr")

    def boom(path, text):
        raise OSError("readonly install dir")

    monkeypatch.setattr("gtm.identity.atomic_write_text", boom)
    patch_paths(monkeypatch, tmp_path, root, ptr)
    assert cmd_run(run_args()) == 1
    assert not Path(ptr, "deferred.json").exists()  # 身份层故障不是让位, 不写注记


# ---------------- cmd_claim 集成 (人工易主通道, D5) ----------------


def claim_args(data_dir: str) -> argparse.Namespace:
    return argparse.Namespace(command="claim", data_dir=data_dir, autostart=False)


def test_cmd_claim_success_rewrites_record_and_clears_note(tmp_path, monkeypatch):
    root_a = fake_install(tmp_path, "a", install_id="id-a")  # 原正主 (另一安装)
    root_b = fake_install(tmp_path, "b", install_id="id-b")  # 本安装, 易主过来
    ptr = str(tmp_path / "ptr")
    write_primary_file(ptr, id_="id-a", install_path=root_a)
    patch_paths(monkeypatch, tmp_path, root_b, ptr)
    # 注记须在 patch_paths 之后写: write_deferred 走 identity 命名空间的指针目录, 提前写会落真实目录
    write_deferred(DeferredNote(reason="relayed", from_install=root_b, target_install=root_a))
    data_dir = str(tmp_path / "data")
    assert cmd_claim(claim_args(data_dir)) == 0
    # 记录三项全换成本安装事实
    record = read_primary()
    assert record.id == "id-b" and record.install_path == root_b and record.data_dir == data_dir
    # data-id 同时认领 (与启动矩阵共用的归属判据)
    assert (Path(data_dir) / "tool-id").read_text(encoding="utf-8").strip() == "id-b"
    # claim 成功清注记 (权威时刻)
    assert not Path(ptr, "deferred.json").exists()


def test_cmd_claim_refused_when_tool_running(tmp_path, monkeypatch):
    root_b = fake_install(tmp_path, "b", install_id="id-b")
    ptr = str(tmp_path / "ptr")
    patch_paths(monkeypatch, tmp_path, root_b, ptr)
    # 先占住单实例锁 (模拟工具正在运行)
    lock = SingleInstanceLock(instance_lock_path())
    lock.acquire()
    try:
        assert cmd_claim(claim_args(str(tmp_path / "data"))) == 1
        assert read_primary() is None  # 拒绝且不碰记录
    finally:
        lock.release()


def test_cmd_claim_refused_when_data_belongs_to_other_install(tmp_path, monkeypatch):
    root_b = fake_install(tmp_path, "b", install_id="id-b")
    ptr = str(tmp_path / "ptr")
    patch_paths(monkeypatch, tmp_path, root_b, ptr)
    data_dir = str(tmp_path / "data")
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    (Path(data_dir) / "tool-id").write_text("id-other\n", encoding="utf-8")
    assert cmd_claim(claim_args(data_dir)) == 1
    assert read_primary() is None  # 拒绝且不碰记录


# ---- 身份层容错出口与代拉实现 (26-10-21 覆盖率门禁 P2-T2.3) ----


def test_read_id_file_oserror_degrades_to_missing(tmp_path, caplog):
    """读 ID 文件遇 OSError (路径是目录/无权限): 只 WARNING 并按「缺失」降级, 不抛."""
    from gtm.identity import read_id_file

    path = tmp_path / "tool-id"
    path.mkdir()  # 路径是目录 -> open 抛 IsADirectoryError
    with caplog.at_level("WARNING", logger="gtm.identity"):
        assert read_id_file(str(path)) is None
    assert "读取 ID 文件失败" in caplog.text


def test_fill_primary_data_dir_write_failure_only_warns(tmp_path, monkeypatch, caplog):
    """补写 data_dir 失败只 WARNING: 它是信息位, 不能反过来让正主启动失败."""
    root = fake_install(tmp_path, "inst", install_id="id-a")
    ptr = str(tmp_path / "ptr")
    patch_paths(monkeypatch, tmp_path, root, ptr)
    write_primary_file(ptr, id_="id-a", install_path=root)  # data_dir 为空 -> 进入补写分支
    identity = Identity(install_root=root, install_id="id-a")

    def boom(record):
        raise OSError("磁盘满")

    monkeypatch.setattr("gtm.identity.write_primary", boom)
    with caplog.at_level("WARNING", logger="gtm.identity"):
        fill_primary_data_dir(identity, str(tmp_path / "data"))  # 不抛
    assert "补写正主记录 data_dir 失败" in caplog.text


def test_clear_deferred_swallows_oserror(tmp_path, monkeypatch, caplog):
    """清注记遇非「已缺失」的 OSError: 只 WARNING (注记残留不影响权威方启动)."""
    ptr = str(tmp_path / "ptr")
    Path(ptr).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("gtm.identity.pointer_dir", lambda: ptr)
    Path(ptr, "deferred.json").mkdir()  # 注记路径变成目录 -> os.remove 抛 OSError
    with caplog.at_level("WARNING", logger="gtm.identity"):
        clear_deferred()  # 不抛
    assert "让位注记删除失败" in caplog.text


def test_spawn_uses_detached_windowless_form(tmp_path, monkeypatch):
    """_spawn 的生产形态: 三路 DEVNULL + close_fds + 平台专属参数 (无窗口 / 新会话)."""
    import subprocess as real_subprocess

    from gtm.identity import _spawn

    seen: list[tuple] = []

    class FakePopen:
        def __init__(self, args, **kwargs):
            seen.append((args, kwargs))

    monkeypatch.setattr("gtm.identity.subprocess.Popen", FakePopen)
    _spawn(["launcher", "arg"], cwd=str(tmp_path))
    args, kwargs = seen[0]
    assert args == ["launcher", "arg"]
    assert kwargs["stdin"] is real_subprocess.DEVNULL
    assert kwargs["stdout"] is real_subprocess.DEVNULL
    assert kwargs["stderr"] is real_subprocess.DEVNULL
    assert kwargs["close_fds"] is True
    assert kwargs["cwd"] == str(tmp_path)
    if sys.platform.startswith("win"):
        assert kwargs["creationflags"] == getattr(real_subprocess, "CREATE_NO_WINDOW", 0x08000000)
    else:
        assert kwargs["start_new_session"] is True


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX 启动器形态只在非 Windows 生效")
def test_relay_launch_posix_uses_sh(tmp_path, monkeypatch):
    """POSIX 侧代拉走 /bin/sh launch.sh (Windows 侧走 launch.cmd 的解释器分支)."""
    root = tmp_path / "other"
    root.mkdir()
    (root / "launch.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    spawned: list = []
    monkeypatch.setattr("gtm.identity._spawn", lambda args, **kw: spawned.append((args, kw)))
    assert relay_launch(str(root)) == str(root / "launch.sh")
    assert spawned[0][0] == ["/bin/sh", str(root / "launch.sh")]


def test_resolve_startup_returns_winner_decision_after_claim_race(tmp_path, monkeypatch):
    """认领竞争输家: 首次判定 claim -> claim_primary 撞 PrimaryRecordExists -> 按赢家重判.

    这是**真竞态形态**, 不能用「一开始就判 relay」的夹具冒充: 那条路径在
    `decision.kind != "claim"` 就返回了, 根本走不到认领 (夹具假绿)。
    """
    other = fake_install(tmp_path, "a", install_id="id-a")
    root = fake_install(tmp_path, "b", install_id="id-b")
    ptr = str(tmp_path / "ptr")
    patch_paths(monkeypatch, tmp_path, root, ptr)
    write_primary_file(ptr, id_="id-a", install_path=other)
    identity = Identity(install_root=root, install_id="id-b")
    winner = PrimaryRecord(id="id-a", install_path=other, data_dir="", version="9.9.9")
    decisions = [
        Decision("claim", None, "无正主记录, 本安装尝试认领"),
        Decision("relay", winner, "已让位: 注册正主是另一安装"),
    ]
    seen: list[str] = []

    def fake_evaluate(ident):
        decision = decisions.pop(0)
        seen.append(decision.kind)
        return decision

    monkeypatch.setattr("gtm.identity.evaluate_startup", fake_evaluate)
    monkeypatch.setattr("gtm.identity.claim_primary", lambda ident: (_ for _ in ()).throw(PrimaryRecordExists()))
    decision = resolve_startup(identity)
    assert seen == ["claim", "relay"]  # 真的走了认领 -> 撞车 -> 重判
    assert decision.kind == "relay"
    assert decision.record.id == "id-a"
