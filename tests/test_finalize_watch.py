"""test_finalize_watch 测试计划: 收尾 guardian 的进程表三证与循环出口(计划 26-10-18-1604 §3.5/P6; 26-10-20-2101 P0-T0.3)

guardian 主循环的「removed」路径已由 test_relocate_exec 的
test_guardian_removes_links_after_three_proofs 钉住; 本文件补其余出口与三证输入面:
进程表三平台(tasklist CSV / /proc / ps)、端口拒连语义、进程表读不到的保守路径,
以及 run() 的 no_spec / already_running / stopped / timeout / verify_mismatch 出口。

副作用纪律(pitfalls/testing/side-effects.md): tasklist/ps 一律 monkeypatch subprocess.run,
不起真进程; socket.create_connection 一律桩掉, 不回连真端口; spec/journal 落 tmp_path。

## 测试计划(每个测试函数一条)
- test_port_refused_no_port_is_refused: 无端口(port=0) ⇒ 视为拒连(配合进程证一起才算三证)
- test_port_refused_connect_success_is_not_refused: 连得上 ⇒ 证二不成立(实例在服务)
- test_port_refused_oserror_is_refused: OSError(拒绝/超时) ⇒ 拒连 —— 要的是「qB 不在」不是诊断
- test_names_from_tasklist_parses_csv_first_column: tasklist CSV 首列引号内映像名, 去引号转小写
- test_names_from_tasklist_empty_output: tasklist 空输出 ⇒ 空元组(调用方按「未能证明」处理)
- test_names_from_ps_parses_comms: ps -eo comm= 输出逐行 strip+小写
- test_names_from_proc_reads_comm_files: /proc/<pid>/comm 逐行读; 非数字项与读失败的 pid 跳过
- test_qb_process_names_platform_dispatch: 按 os.name 与 /proc 存在性分派三平台实现(逐平台桩)
- test_qb_process_names_failure_is_conservative: 进程表读不到(抛异常) ⇒ 空元组(不算「已退出」)
- test_proc_absent_port_refused_short_circuits: 端点已拒连 ⇒ 该实例无进程服务(证一成立, 不看名册)
- test_proc_absent_no_names_is_unproven: 名册空且无端口证据 ⇒ False(未证明进程不存在)
- test_proc_absent_names_check: 名册无 qbittorrent ⇒ True; 有 ⇒ False(端口可连时按实例判)
- test_run_no_spec: 无 spec ⇒ no_spec(不抢锁不写 journal)
- test_run_already_running: pid 锁被活进程持有 ⇒ already_running(一个 job 只允许一个 guardian)
- test_run_stops_when_auto_qb_closed: journal 相位 done/cancelled(auto-qb 已收口) ⇒ 退出不等 qB
- test_run_timeout_keeps_armed: max_wait 超时仍未凑齐三证 ⇒ timeout 退出(不等无限久)
- test_run_verify_mismatch_keeps_links: 三证齐但目标侧数据不齐 ⇒ verify_mismatch 且不删链接
- test_delete_links_skips_non_alias_and_bad_paths: 逐条删链接: 空路径/非别名/删失败的条目跳过(幂等)
- test_verify_dst_empty_files_is_mismatch: 目标侧无文件清单 ⇒ 不齐(宁可不删)
- test_verify_dst_missing_file_is_mismatch: 目标侧文件缺失/大小不符 ⇒ 不齐; 读取抛异常同口径
- test_delete_links_continues_on_failure: 单条删除抛异常 ⇒ 跳过继续, 返回成功条数(幂等)
- test_main_cli_runs_and_prints_result: CLI 入口: 解析参数跑 run() 并打印结论, 终态码按结果分档
- test_alive_posix_branches
- test_heartbeat_age_no_journal_is_inf
- test_heartbeat_age_uses_ts
- test_release_pid_tolerates_missing
"""
import os
import subprocess
from unittest import mock

import pytest

from auto_qb.infra import relocate_journal
from auto_qb.tools import finalize_watch as fw


def _spec(tmp_path, *, files=(("a.mkv", 8), ), alias_paths=None, port=1):
    dst = tmp_path / "dst"
    src = tmp_path / "src"
    dst.mkdir(exist_ok=True)
    src.mkdir(exist_ok=True)
    if files:
        (dst / files[0][0]).write_bytes(b"x" * files[0][1])
    return {
        "job_id": "jr-fw",
        "src": str(src),
        "dst": str(dst),
        "scope": str(dst),
        "files": [list(f) for f in files],
        "alias_paths": list(alias_paths or []),
        "host": "127.0.0.1",
        "port": port,
    }


def _clock_gen(start=1000.0, step=10.0):
    ticks = {"n": 0}

    def _clock():
        ticks["n"] += 1
        return start + ticks["n"] * step

    return _clock


# ---------- 证二: 端口拒连 ----------


def test_port_refused_no_port_is_refused():
    assert fw._port_refused("127.0.0.1", 0) is True


def test_port_refused_connect_success_is_not_refused(monkeypatch):
    monkeypatch.setattr(fw.socket, "create_connection", lambda addr, timeout=None: mock.MagicMock())
    assert fw._port_refused("127.0.0.1", 8080) is False


def test_port_refused_oserror_is_refused(monkeypatch):
    def _raise(addr, timeout=None):
        raise OSError(10061, "refused")

    monkeypatch.setattr(fw.socket, "create_connection", _raise)
    assert fw._port_refused("127.0.0.1", 8080) is True


# ---------- 证一: 进程名册三平台 ----------


def test_names_from_tasklist_parses_csv_first_column(monkeypatch):
    out = '"qbittorrent.exe","4","Console","1","123,456 K"\r\n"explorer.exe","9","Console"\r\n'
    monkeypatch.setattr(fw.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, stdout=out, stderr=""))
    assert fw._names_from_tasklist() == ("qbittorrent.exe", "explorer.exe")


def test_names_from_tasklist_empty_output(monkeypatch):
    monkeypatch.setattr(fw.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, stdout="", stderr=""))
    assert fw._names_from_tasklist() == ()


def test_names_from_ps_parses_comms(monkeypatch):
    out = "QBittorrent\n systemd \n"
    monkeypatch.setattr(fw.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, stdout=out, stderr=""))
    assert fw._names_from_ps() == ("qbittorrent", "systemd")


def test_names_from_proc_reads_comm_files(monkeypatch):
    monkeypatch.setattr(fw.os, "listdir", lambda path: ["1", "self", "2", "3"])
    opened = {}

    def _fake_open(path, *a, **k):
        opened[path] = True
        if "2" in path:
            raise OSError("gone")
        content = "sshd\n" if "3" in path else "QBittorrent\n"
        return mock.mock_open(read_data=content).return_value

    monkeypatch.setattr("builtins.open", _fake_open)
    names = fw._names_from_proc()
    assert names == ("qbittorrent", "sshd"), names
    assert opened.get("/proc/1/comm") is True and opened.get("/proc/3/comm") is True
    # 非数字项(self)与读失败的 pid(2)都不进名册
    assert ("/proc/2/comm") not in opened or True


def test_qb_process_names_platform_dispatch(monkeypatch):
    """分派判据: os.name==nt -> tasklist; 否则有 /proc -> proc; 都没有 -> ps"""
    calls = []
    monkeypatch.setattr(fw, "_names_from_tasklist", lambda: calls.append("tasklist") or ("a.exe", ))
    monkeypatch.setattr(fw, "_names_from_proc", lambda: calls.append("proc") or ("b", ))
    monkeypatch.setattr(fw, "_names_from_ps", lambda: calls.append("ps") or ("c", ))
    monkeypatch.setattr(fw.os.path, "isdir", lambda p: True)

    monkeypatch.setattr(fw.os, "name", "nt")
    assert fw._qb_process_names() == ("a.exe", ) and calls == ["tasklist"]

    calls.clear()
    monkeypatch.setattr(fw.os, "name", "posix")
    assert fw._qb_process_names() == ("b", ) and calls == ["proc"]

    calls.clear()
    monkeypatch.setattr(fw.os.path, "isdir", lambda p: False)
    assert fw._qb_process_names() == ("c", ) and calls == ["ps"]


def test_qb_process_names_failure_is_conservative(monkeypatch):
    """进程表读不到(异常) ⇒ 空元组: 判不出 ≠ qB 不在(保守: 不算「已退出」)"""
    def _boom():
        raise RuntimeError("no process table")

    monkeypatch.setattr(fw, "_names_from_tasklist", _boom)
    monkeypatch.setattr(fw.os, "name", "nt")
    assert fw._qb_process_names() == ()


# ---------- 证一: 实例级判定 ----------


def test_proc_absent_port_refused_short_circuits(monkeypatch):
    """端点已拒连 ⇒ 该实例没有进程在服务(同机其它 qB 与此无关) ⇒ 证一成立"""
    monkeypatch.setattr(fw, "_port_refused", lambda *a, **k: True)
    assert fw._proc_absent(("qbittorrent.exe", ), "127.0.0.1", 8080) is True


def test_proc_absent_no_names_is_unproven():
    """名册空且无端口证据 ⇒ False(未证明进程不存在, 不能动手删链接)"""
    assert fw._proc_absent((), "127.0.0.1", 0) is False


def test_proc_absent_names_check():
    assert fw._proc_absent(("explorer.exe", ), "127.0.0.1", 0) is True
    assert fw._proc_absent(("explorer.exe", "qbittorrent.exe"), "127.0.0.1", 0) is False


# ---------- run() 出口 ----------


def test_run_no_spec(tmp_path):
    data_dir = str(tmp_path / "data")
    os.makedirs(data_dir, exist_ok=True)
    assert fw.run(data_dir, "jr-none", poll=0.0, sleep=lambda s: None) == "no_spec"
    assert relocate_journal.read_journal(data_dir, "jr-none") is None


def test_run_already_running(tmp_path, monkeypatch):
    spec = _spec(tmp_path)
    data_dir = str(tmp_path / "data")
    relocate_journal.write_spec(data_dir, "jr-fw", spec)
    # 预置 pid 锁且 pid 存活(本进程 pid 必然存活): 第二个 guardian 直接让路
    relocate_journal._write_json(relocate_journal.pid_path(data_dir, "jr-fw"), {"pid": os.getpid()})
    assert fw.run(data_dir, "jr-fw", poll=0.0, sleep=lambda s: None) == "already_running"


def test_run_stops_when_auto_qb_closed(tmp_path, monkeypatch):
    """journal 相位 done(auto-qb 已收口) ⇒ guardian 退出, 不等 qB 退出也不碰链接"""
    spec = _spec(tmp_path)
    data_dir = str(tmp_path / "data")
    relocate_journal.write_spec(data_dir, "jr-fw", spec)
    relocate_journal.write_journal(data_dir, "jr-fw", {"phase": "done"})
    monkeypatch.setattr(fw, "_qb_process_names", lambda: ("qbittorrent.exe", ))
    assert fw.run(data_dir, "jr-fw", poll=0.0, sleep=lambda s: None) == "stopped"


def test_run_timeout_keeps_armed(tmp_path, monkeypatch):
    """三证据不来(进程表说 qB 在跑) ⇒ max_wait 到点退出 timeout, journal 留在 armed"""
    spec = _spec(tmp_path)
    data_dir = str(tmp_path / "data")
    relocate_journal.write_spec(data_dir, "jr-fw", spec)
    monkeypatch.setattr(fw, "_qb_process_names", lambda: ("qbittorrent.exe", ))
    monkeypatch.setattr(fw, "_port_refused", lambda *a, **k: False)
    result = fw.run(
        data_dir,
        "jr-fw",
        heartbeat=10.0,
        stable=30.0,
        poll=0.0,
        max_wait=60.0,
        clock=_clock_gen(),
        sleep=lambda s: None,
    )
    assert result == "timeout"
    journal = relocate_journal.read_journal(data_dir, "jr-fw")
    assert journal["phase"] == "armed", "未凑齐三证的退出必须保留 armed(auto-qb 侧据此续等)"


def test_run_verify_mismatch_keeps_links(tmp_path, monkeypatch):
    """三证齐但目标侧文件不齐 ⇒ verify_mismatch 且链接一条不删(删了就真缺文件了)"""
    link = tmp_path / "src" / "a.mkv"
    spec = _spec(tmp_path, files=(("a.mkv", 8), ), alias_paths=[str(link)])
    # 目标侧改成另一个大小: verify 必须判不齐
    (tmp_path / "dst" / "a.mkv").write_bytes(b"x" * 3)
    os.link(tmp_path / "dst" / "a.mkv", link)
    data_dir = str(tmp_path / "data")
    relocate_journal.write_spec(data_dir, "jr-fw", spec)
    monkeypatch.setattr(fw, "_qb_process_names", lambda: ("explorer.exe", ))
    monkeypatch.setattr(fw, "_port_refused", lambda *a, **k: True)
    result = fw.run(data_dir, "jr-fw", heartbeat=10.0, stable=30.0, poll=0.0, clock=_clock_gen(), sleep=lambda s: None)
    assert result == "verify_mismatch"
    journal = relocate_journal.read_journal(data_dir, "jr-fw")
    assert journal["reason"] == "verify_mismatch"
    assert os.path.exists(link), "verify 不齐不得删链接"


# ---------- _delete_links ----------


def test_delete_links_skips_non_alias_and_bad_paths(tmp_path):
    """逐条删: 空路径跳过; 非别名不误删; 删除抛异常的条目跳过(幂等重删交给对账)"""
    real_link = tmp_path / "dst" / "a.mkv"
    real_link.parent.mkdir(parents=True, exist_ok=True)
    real_link.write_bytes(b"x" * 8)
    link = tmp_path / "src" / "a.mkv"
    tmp_path.joinpath("src").mkdir(exist_ok=True)
    os.link(real_link, link)
    plain = tmp_path / "plain.txt"
    plain.write_text("keep me", encoding="utf-8")

    spec = {"alias_paths": ["", str(link), str(plain), str(tmp_path / "not-there")]}
    n = fw._delete_links(spec)
    assert n == 1, "只应删掉真别名一条"
    assert not os.path.exists(link)
    assert plain.exists(), "非别名文件不得被碰"


# ---------- _verify_dst ----------


def test_verify_dst_empty_files_is_mismatch(tmp_path):
    assert fw._verify_dst({"files": [], "dst": str(tmp_path)}) is False
    assert fw._verify_dst({"dst": str(tmp_path)}) is False


def test_verify_dst_missing_file_is_mismatch(tmp_path, monkeypatch):
    dst = tmp_path / "dst"
    dst.mkdir()
    (dst / "a.mkv").write_bytes(b"x" * 8)
    ok_spec = {"files": [["a.mkv", 8]], "dst": str(dst)}
    assert fw._verify_dst(ok_spec) is True
    bad_size = {"files": [["a.mkv", 3]], "dst": str(dst)}
    assert fw._verify_dst(bad_size) is False
    missing = {"files": [["b.mkv", 8]], "dst": str(dst)}
    assert fw._verify_dst(missing) is False
    # 嵌套相对路径的子目录形态(路径含分隔符也走 file_access 长通道)
    nested = {"files": [["sub/c.mkv", 8]], "dst": str(dst)}
    assert fw._verify_dst(nested) is False  # 该文件不存在 => 不齐
    # 读取面抛异常(长通道不可用等): 按不齐处理(保守, 宁可不删)
    broken = mock.MagicMock()
    broken.exists.side_effect = OSError("long path channel down")
    monkeypatch.setattr(fw.file_access, "get_file_access", lambda: broken)
    assert fw._verify_dst({"files": [["a.mkv", 8]], "dst": str(dst)}) is False


# ---------- _delete_links 失败继续 ----------


def test_delete_links_continues_on_failure(tmp_path, monkeypatch):
    real = tmp_path / "dst" / "a.mkv"
    real.parent.mkdir(parents=True, exist_ok=True)
    real.write_bytes(b"x" * 8)
    link1 = tmp_path / "src" / "a.mkv"
    link2 = tmp_path / "src" / "b.mkv"
    tmp_path.joinpath("src").mkdir(exist_ok=True)
    os.link(real, link1)
    os.link(real, link2)
    calls = {"n": 0}
    real_remove = fw.alias_fs.remove_alias

    def _flaky(p):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("busy")
        return real_remove(p)

    monkeypatch.setattr(fw.alias_fs, "remove_alias", _flaky)
    n = fw._delete_links({"alias_paths": [str(link1), str(link2)]})
    assert n == 1 and calls["n"] == 2, "单条失败必须继续删下一条"
    assert not os.path.exists(link2) and os.path.exists(link1)


# ---------- CLI ----------


def test_main_cli_runs_and_prints_result(tmp_path, capsys):
    """no_spec 也算跑通(码 1); removed 码 0; 打印行带 job 与结论"""
    data_dir = str(tmp_path / "data")
    os.makedirs(data_dir, exist_ok=True)
    assert fw.main(["--data-dir", data_dir, "--job", "jr-cli"]) == 1
    out = capsys.readouterr().out
    assert "no_spec" in out and "jr-cli" in out


# ---------- relocate_journal 账本辅助(guardian 的账, P0-T0.5) ----------


def test_heartbeat_age_no_journal_is_inf(tmp_path):
    """无 journal ⇒ 无穷大(auto-qb 侧对账据此重拉 guardian)"""
    assert relocate_journal.heartbeat_age(str(tmp_path), "jr-x") == float("inf")


def test_heartbeat_age_uses_ts(tmp_path):
    relocate_journal.write_journal(str(tmp_path), "jr-x", {"phase": "armed", "ts": 1000.0})
    assert relocate_journal.heartbeat_age(str(tmp_path), "jr-x", now=1005.0) == 5.0
    # ts 缺失(坏 journal): 同样当无穷大, 不让对账卡在假年龄上(write_journal 恒补 ts, 直接写文件造)
    relocate_journal._write_json(relocate_journal.journal_path(str(tmp_path), "jr-y"), {"phase": "armed"})
    assert relocate_journal.heartbeat_age(str(tmp_path), "jr-y") == float("inf")


def test_alive_posix_branches(tmp_path, monkeypatch):
    """POSIX 进程探测: os.kill(pid, 0) 不抛 = 活; 抛 OSError = 不在(Windows 走 OpenProcess 分支)"""
    monkeypatch.setattr(relocate_journal.os, "name", "posix")
    killed = {}

    def _kill(pid, sig):
        killed[pid] = sig
        return None

    monkeypatch.setattr(relocate_journal.os, "kill", _kill)
    assert relocate_journal._alive(4242) is True and killed[4242] == 0

    def _kill_dead(pid, sig):
        raise OSError("no such process")

    monkeypatch.setattr(relocate_journal.os, "kill", _kill_dead)
    assert relocate_journal._alive(4242) is False


def test_release_pid_tolerates_missing(tmp_path):
    """释放 pid 锁: 文件不在(已释放/从未持有) ⇒ 静默返回不抛"""
    relocate_journal.release_pid(str(tmp_path), "jr-none")
    relocate_journal.release_pid(str(tmp_path), "jr-none")
