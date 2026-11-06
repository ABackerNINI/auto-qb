"""test_recycle_daemon 测试计划: fastresume 回收 daemon 竞态矩阵(计划 26-11-05-0808 §3.4 S3)

覆盖面: journal 协议扩展(rewritten 相位/成员改写账/daemon 心跳账/pending 口径单点,
relocate_journal S3 扩展段)+ 回收 daemon 主体(D12 简化形制)的竞态矩阵。全部替身:
「qB 在不在」桩在 socket.create_connection(端口证)+ 进程名册(证一)上, 不起真进程、
不回连真端口; fastresume 用 tmp 目录真实构造(test_core_fastresume 同款造法, 不 mock
编辑器 —— 改写落盘/幂等/坏样本语义全走真实代码); spec/journal/daemon.json 落 tmp_path;
时钟/睡眠注入, 无真实等待。

## 测试计划(每个测试函数一条; 竞态矩阵五项加注)

协议面(relocate_journal S3 扩展):
- test_instance_key_sanitizes_for_filename: 实例键文件名安全形制(冒号/IPv6/保留字折叠)
- test_daemon_state_write_touch_read_roundtrip: daemon.json 写-touch-读; touch 保诊断字段/
  更 ts; 外来 pid touch 拒写不落盘(退位互斥写侧闸)
- test_daemon_heartbeat_age_and_missing_is_inf: 无记录/无 ts => 无穷大
- test_daemon_stale_matrix: 挂死重拉判定 —— 无记录/pid 死/心跳过期 => stale; 健康在位 =>
  不 stale(alive 替身注入)
- test_release_daemon_state_owner_only: 按归属释放; 外来者删不掉新主记录
- test_release_daemon_state_remove_failure_is_false: 删除 OSError => False 不抛
- test_list_spec_jobs_missing_dir_is_empty: relocate 目录缺失 => 空清单
- test_spec_members_non_dict_entries_fall_back_to_hashes: members 形不符 => 退 hashes 派生
- test_record_rewrites_merges_members_and_refuses_terminal: 成员账合并(不丢前账)/fresh 建账
  相位 armed/翻相 rewritten 保账/终态拒收(取消收口即时生效的协议级闸)/终态相位参数 fail-fast
- test_pending_members_settled_semantics: pending 口径 —— rewritten/already/unmatched 出账,
  failed/not_found/无账留守; members 字段优先于 hashes 派生

daemon 主体:
- test_rewrite_member_status_mapping: retarget 三态 + not_found/异常到记账 status 的映射表;
  fails 承前累计(失败 +1, 成功保值)
- test_scan_jobs_filters_instance_optin_and_terminal: 实例字面过滤/bt_backup opt-in(旧链
  spec 不碰)/终态剔除/残缺 spec 剔除/翻相 flag
- test_owner_beat_throttles_touch: 心跳 10s 节流(D12); 被退位自检在 touch 之前; 记录消失
  重新认主; touch 间隙被拒不炸
- test_run_flips_settled_phase_without_window: 全员已收口(账在相位未翻)+ qB 在线 => 只补翻
  相位, 零改写零进窗(journal 写不限窗口, D13)
- test_run_waits_for_stable_window_before_window: 进窗第三证(稳定窗)—— 下线未持续满
  stable 不动手(关机风暴形态: 窗口短于稳定窗 => 错过无害), 零落盘
- test_run_grace_exit_after_idle_period: pending 空 => 宽限计时, 计满才 idle 退出
  (grace < max_wait 时宽限先到, 非 timeout)
- test_cli_main_idle_exit_zero: CLI 入口空载 idle 退出码 0

竞态矩阵:
- [抢先回升/零写入] test_qb_revives_before_first_write_zero_member_writes: 进窗后第一次
  落盘前 qB 回升(名册第二次现读时翻 state)=> 本轮放弃, 零成员改写, 账面零 records
- [抢先回升/中途] test_qb_revives_mid_sequence_abandons_rest: A 改写落账后 qB 回升(retarget
  钩子翻 state)=> B 不再尝试不落账不落盘; A 已写部分留存(N4 自愈面)
- [半途崩溃] test_crash_mid_window_journal_consistent_and_next_round_replays: A 收口后 daemon
  终止(B 持续失败至 max_wait => timeout 模拟进程死亡) => 账面一致(A rewritten/B failed 计数
  在账); 修好 B 后新 daemon 重放: 只试 B(A 零重试), B 收口, 相位翻 rewritten
- [重复重放] test_replay_after_journal_loss_records_already: fastresume 已在目标值而账本清零
  (账丢失/新 daemon) => retarget unchanged+already => 记 already 出账, 文件字节零改动, 无
  .bak 产生(黄金法则 1)
- [窗口内重试] test_window_retry_until_success_counts_failures: 瞬态故障(坏样本第一拍修复)
  => 窗口内第二拍改写成功(D8 重试至成功), 失败计数 1 进账不丢
- [取消即时生效] test_main_loop_cancel_mid_window_skips_rest: A 落账的同一间隙对账落终态
  => B 写前现读见终态即弃, 不落盘; 终态相位不被 daemon 回退(前向合并)
- test_record_refused_when_terminal_lands_in_gap: 收口落在写前检查与落账间隙 => 落账拒收
  (False) => job 立即放弃(协议级终态闸门在 daemon 侧的出口)
- [退位互斥] test_deposed_old_daemon_self_checks_and_exits: 新主 pid 抢占(纯文件写, 无
  taskkill) => 旧 daemon 下一拍自检见外来 pid 即 deposed 退出, 退出前零覆盖(新主 ts 原样),
  release 不误删新主记录
- [退位互斥/窗口内] test_deposed_at_window_pass_top_aborts_round: 会话中抢占 => 拍顶自检
  即整轮 deposed, 已落账部分留存
- [退位互斥/成员拍] test_deposed_mid_window_member_beat_aborts: 成员 A 处理中途抢占 =>
  成员 B 拍级自检放弃, B 零触碰
- test_run_already_running_healthy_watcher_untouched: 健康 watcher(心跳新鲜 + pid 活)=>
  already_running 让路, daemon.json 零触碰
- test_run_preempts_dead_pid_record: 记录 pid 已死 => pid 抢占接管, 后续正常空载 idle
- test_run_timeout_keeps_pending: max_wait 到点 => timeout, pending 原样(账面零 records),
  daemon.json 按归属释放
- test_cli_main_timeout_exit_one: CLI timeout 档退出码 1
- test_module_main_entry_exits_with_result_code: python -m 入口结论码经 sys.exit 上抛

覆盖率缺口清偿(26-11-07, test.full 99.31% -> 99.5% 闸):
- test_write_journal_refuses_nonterminal_over_terminal: 终态闸门(非终态拒/终态互覆)
- test_alive_posix_fallback_paths: _alive POSIX 支(kill 探活/进程不在/信号不支持)
- test_verify_replays_of_bad_shape_is_zero: verify_replays 坏形 => 0
- test_reset_rewrites_terminal_refused_and_keeps_unsettled: 重放入口终态拒(-1)/非 settled 原样保留
- test_tasklist_ignores_non_quoted_lines: tasklist CSV 非引号行跳过
- test_names_from_proc_tolerates_unreadable_comm: /proc 名册逐项容错(comm 打不开跳过;
  pid 1 comm 重定向真实文件 => 可读支两平台非空可断, 修 Windows 主平台空转断言)
- test_qb_process_names_dispatches_non_windows: 进程名册分派(ps 支/proc 支)

收口评审修复轮(26-11-07):
- test_spec_retarget_mid_window_rewrites_remaining_to_new_dst: 窗口中段 spec.dst 被改道
  (supersede 账面段不需 qB 在线)=> 剩余成员按新 dst 改写(评审 #4: 旧实现用窗口 scan
  快照, 剩余成员写旧 dst)/ spec 现读失败 => 本 job 本拍放弃不拿旧快照改写
- test_spec_unreadable_mid_window_skips_job_without_stale_rewrite: spec 现读失败(撕态/被删)
  => 本 job 本拍放弃, 零改写零落账不拿旧快照(评审 #4 容错支)
- test_proc_absent_dual_evidence_and_roster_fallback: 证一判定(评审 #6)—— 名册可用时
  「进程不在 AND 端口拒连」合取(名册见 qB + 端口拒连 = 不进窗, WebUI 不可达 != 进程
  不在)/ 名册无 qB + 拒连成立 / 名册不可用退端口单证但告警降级 / 无端口退名册单证
"""
import logging
import os
from pathlib import Path
from unittest import mock

import pytest

from auto_qb.core import fastresume as frmod
from auto_qb.hr.bencode import compute_infohashes
from auto_qb.infra import relocate_journal as rj
from auto_qb.tools import recycle_daemon as rd

HOST = "127.0.0.1"
PORT = 36596

# ---------------------------------------------------------------------------
# 造法(test_core_fastresume 同款: 真实 bencode/fastresume, 不 mock 编辑器)
# ---------------------------------------------------------------------------


def _member_fixture(backup: Path, tag: bytes, old_root: str, *, rewritten_to: str = "") -> str:
    """BT_backup 落一对 <v1>.torrent + <v1>.fastresume, 返回 v1 hash。
    save_path 反斜杠风味(lt 键, N1 实测字节), qBt 键正斜杠风味; rewritten_to 非空时
    直接落"已在目标值"形态(重复重放测试用)。"""
    info = {b"name": tag, b"piece length": 16384, b"pieces": b"\x00" * 20, b"length": 1}
    torrent = frmod.bencode({b"announce": b"http://tracker.example/ann", b"info": info})
    v1, _, _ = compute_infohashes(torrent)
    name = tag.decode()
    root = rewritten_to or old_root
    val = {
        b"save_path": (root + "\\" + name).encode("utf-8"),
        b"qBt-savePath": (root.replace("\\", "/") + "/" + name).encode("utf-8"),
        b"qBt-name": tag,
        b"completed": 1,
    }
    backup.mkdir(parents=True, exist_ok=True)
    (backup / f"{v1}.torrent").write_bytes(torrent)
    (backup / f"{v1}.fastresume").write_bytes(frmod.bencode(val))
    return v1


def _write_job(
    tmp_path: Path,
    data_dir: str,
    job_id: str,
    hashes,
    *,
    host=HOST,
    port=PORT,
    bt_backup=True,
    members=None,
    src=None,
    dst=None,
    journal_phase=None
) -> dict:
    src = str(tmp_path / "src") if src is None else src
    dst = str(tmp_path / "dst") if dst is None else dst
    spec = {
        "job_id": job_id,
        "src": src,
        "dst": dst,
        "scope": dst,
        "hashes": list(hashes),
        "host": host,
        "port": port,
        "alias_paths": [],
        "files": [],
    }
    if bt_backup:
        spec["bt_backup"] = str(tmp_path / "BT_backup")
    if members is not None:
        spec["members"] = members
    rj.write_spec(data_dir, job_id, spec)
    if journal_phase:
        rj.write_journal(data_dir, job_id, {"phase": journal_phase})
    return spec


def _stub_qb(monkeypatch, state):
    """三证桩: 端口证桩在 socket.create_connection(连得上=在/拒连=不在, rd 内三证判据
    消费同一 socket 模块对象); 进程名册与 state 联动 —— qB 在 = 名册含 qbittorrent,
    不在 = 名册可用但只有无关进程(评审 #6 起 _proc_absent 双判合取, 名册参与判定;
    单实例机器语义: qB 真死时名册自然无 qB 进程, 合取不损窗口可用性)。state["up"]=True
    即「qB 在」。"""
    def _connect(addr, timeout=None):
        if state["up"]:
            return mock.MagicMock()
        raise OSError(10061, "refused")

    monkeypatch.setattr(rd.socket, "create_connection", _connect)
    monkeypatch.setattr(
        rd, "_qb_process_names", lambda: ("qbittorrent.exe", ) if state["up"] else ("explorer.exe", "svchost.exe")
    )


def _clock_gen(start=1000.0, step=5.0):
    state = {"t": start}

    def _clock():
        state["t"] += step
        return state["t"]

    return _clock


def _run(
    data_dir,
    *,
    host=HOST,
    port=PORT,
    stable=0.0,
    poll=0.0,
    grace=0.0,
    heartbeat=10.0,
    max_wait=0.0,
    clock=None,
    sleep=None
):
    return rd.run(
        data_dir,
        host,
        port,
        stable=stable,
        poll=poll,
        grace=grace,
        heartbeat=heartbeat,
        max_wait=max_wait,
        clock=clock or _clock_gen(),
        sleep=sleep or (lambda s: None),
    )


def _fr_path(tmp_path: Path, h1: str) -> Path:
    return tmp_path / "BT_backup" / f"{h1}.fastresume"


# ---------------------------------------------------------------------------
# 协议面: instance_key / daemon.json / 心跳 / stale 判定
# ---------------------------------------------------------------------------


def test_instance_key_sanitizes_for_filename():
    k = rj.instance_key("127.0.0.1", 8080)
    assert k == "127.0.0.1_8080"
    # IPv6/怪字符一律折叠(Windows 文件名禁冒号); 折叠不可逆, 身份判定以 (host, port) 原值
    for host in ("::1", "fe80::1%eth0", "a b"):
        key = rj.instance_key(host, 8080)
        assert not (set(key) & set(":\\/*?\"<>|")), key
    assert rj.instance_key("h", 1) == rj.instance_key("h", 1)


def test_daemon_state_write_touch_read_roundtrip(tmp_path):
    d = str(tmp_path)
    rj.write_daemon_state(d, "k", 7, host="h1", port=9, ts=100.0)
    st = rj.read_daemon_state(d, "k")
    assert st["pid"] == 7 and st["host"] == "h1" and st["port"] == 9 and st["ts"] == 100.0
    # touch: 归属核验通过 => 更 ts, 诊断字段保留
    assert rj.touch_daemon_state(d, "k", 7, ts=150.0) is True
    st = rj.read_daemon_state(d, "k")
    assert st["ts"] == 150.0 and st["host"] == "h1" and st["port"] == 9
    # 被退位(记录 pid 非我): 拒 touch 且不落盘(不得用心跳覆盖新主 pid)
    assert rj.touch_daemon_state(d, "k", 8, ts=200.0) is False
    assert rj.read_daemon_state(d, "k")["ts"] == 150.0


def test_daemon_heartbeat_age_and_missing_is_inf(tmp_path):
    d = str(tmp_path)
    assert rj.daemon_heartbeat_age(d, "none") == float("inf")
    rj.write_daemon_state(d, "k", 7, ts=1000.0)
    assert rj.daemon_heartbeat_age(d, "k", now=1005.0) == 5.0
    rj._write_json(rj.daemon_state_path(d, "bad"), {"pid": 7})  # 无 ts(坏记录)
    assert rj.daemon_heartbeat_age(d, "bad") == float("inf")


def test_daemon_stale_matrix(tmp_path):
    """挂死重拉判定(对账 ACT_ENSURE_DAEMON 的判据单点, 本期提供函数、接线下一任务)"""
    d = str(tmp_path)
    assert rj.daemon_stale(d, "none", max_age=60.0, now=1000.0) is True, "无记录 => 可重拉"
    rj.write_daemon_state(d, "k", 4242, ts=1000.0)
    assert rj.daemon_stale(d, "k", max_age=60.0, now=1050.0, alive=True) is False, "健康在位"
    assert rj.daemon_stale(d, "k", max_age=60.0, now=1061.0, alive=True) is True, "心跳过期"
    assert rj.daemon_stale(d, "k", max_age=60.0, now=1001.0, alive=False) is True, "pid 已死"
    rj._write_json(rj.daemon_state_path(d, "bad"), {"pid": 0, "ts": 1000.0})
    assert rj.daemon_stale(d, "bad", max_age=60.0, now=1001.0, alive=True) is True, "坏记录"


def test_release_daemon_state_owner_only(tmp_path):
    d = str(tmp_path)
    rj.write_daemon_state(d, "k", 7, ts=1.0)
    assert rj.release_daemon_state(d, "k", 8) is False, "外来者不得删"
    assert rj.read_daemon_state(d, "k") is not None
    assert rj.release_daemon_state(d, "k", 7) is True
    assert rj.read_daemon_state(d, "k") is None
    assert rj.release_daemon_state(d, "k", 7) is False


def test_release_daemon_state_remove_failure_is_false(tmp_path, monkeypatch):
    """删除失败(OSError)⇒ False 不抛(调用方在 finally 里, 退出路径不得炸)"""
    d = str(tmp_path)
    rj.write_daemon_state(d, "k", 7, ts=1.0)

    def _raise(p):
        raise OSError("busy")

    monkeypatch.setattr(rj.os, "remove", _raise)
    assert rj.release_daemon_state(d, "k", 7) is False


def test_list_spec_jobs_missing_dir_is_empty(tmp_path):
    assert rj.list_spec_jobs(str(tmp_path / "no-such-dir")) == []


def test_spec_members_non_dict_entries_fall_back_to_hashes():
    """members 字段全非 dict(形不符)⇒ 退回 hashes 派生(不空转不炸)"""
    spec = {"members": ["not-a-dict", 42], "hashes": ["h1"]}
    pend = rj.pending_members(spec, {})
    assert [rj.member_key(m) for m in pend] == ["h1"]


# ---------------------------------------------------------------------------
# 协议面: 成员改写账与 pending 口径
# ---------------------------------------------------------------------------


def test_record_rewrites_merges_members_and_refuses_terminal(tmp_path):
    d = str(tmp_path)
    # fresh 建账: 无 journal 时相位落 armed(相位模型主干), 账随写随在
    assert rj.record_rewrites(d, "j", {"h1": {"status": "rewritten"}}, ts=1.0, pid=9) is True
    j = rj.read_journal(d, "j")
    assert j["phase"] == "armed" and j["rewrites"]["h1"]["status"] == "rewritten" and j["pid"] == 9
    # 合并: 后写不丢前账; 记录缺省补 ts
    assert rj.record_rewrites(d, "j", {"h2": {"status": "failed"}}, ts=2.0) is True
    rw = rj.read_rewrites(d, "j")
    assert rw["h1"]["status"] == "rewritten" and rw["h2"]["status"] == "failed"
    assert rw["h2"]["ts"] == 2.0
    # 翻相: rewritten 相位落账且账保全
    assert rj.record_rewrites(d, "j", {}, phase=rj.PHASE_REWRITTEN, ts=3.0) is True
    j = rj.read_journal(d, "j")
    assert j["phase"] == "rewritten" and j["rewrites"]["h1"]["status"] == "rewritten"
    # 终态拒收: 对账已收口 => 拒写(取消/完成对 daemon 即时生效的协议级闸门)
    rj.write_journal(d, "j", {"phase": "done"})
    assert rj.record_rewrites(d, "j", {"h3": {"status": "rewritten"}}) is False
    assert rj.read_journal(d, "j")["phase"] == "done"
    # 终态相位参数 fail-fast(终态是主循环专属写权)
    try:
        rj.record_rewrites(d, "j2", {}, phase="done")
        raise AssertionError("终态相位参数必须 ValueError")
    except ValueError:
        pass


def test_pending_members_settled_semantics():
    spec = {"hashes": ["h1", "h2", "h3", "h4", "h5"]}
    rewrites = {
        "h1": {
            "status": "rewritten"
        },
        "h2": {
            "status": "already"
        },
        "h3": {
            "status": "unmatched"
        },
        "h4": {
            "status": "failed",
            "fails": 2
        },
    }
    pend = rj.pending_members(spec, rewrites)
    # rewritten/already/unmatched 出账(REWRITE_SETTLED); failed 与无账留守
    assert [rj.member_key(m) for m in pend] == ["h4", "h5"]
    assert rj.pending_members(spec, {}) and len(rj.pending_members(spec, {})) == 5
    # members 字段优先于 hashes 派生(v2/hybrid 显式双 hash 形态)
    spec2 = {"hashes": ["hA"], "members": [{"hash_v1": "", "hash_v2": "v2id"}]}
    pend2 = rj.pending_members(spec2, {})
    assert len(pend2) == 1 and rj.member_key(pend2[0]) == "v2id"


# ---------------------------------------------------------------------------
# daemon 主体: 记账映射 / 扫描 / 心跳节流 / 翻相 / CLI
# ---------------------------------------------------------------------------


def test_rewrite_member_status_mapping(tmp_path):
    old_root = str(tmp_path / "src")
    new_root = str(tmp_path / "dst")
    backup = tmp_path / "BT_backup"
    spec = {"bt_backup": str(backup), "src": old_root, "dst": new_root}
    h_ok = _member_fixture(backup, b"m-ok", old_root)
    h_already = _member_fixture(backup, b"m-already", old_root, rewritten_to=new_root)
    h_elsewhere = _member_fixture(backup, b"m-elsewhere", old_root)
    h_missing = "0" * 40
    h_bad = _member_fixture(backup, b"m-bad", old_root)
    (_fr_path(tmp_path, h_bad)).write_bytes(b"garbage-not-bencode")
    # elsewhere: 路径键全不命中旧根 => unmatched(确定性无操作)
    p = _fr_path(tmp_path, h_elsewhere)
    val = frmod.load_fastresume(p)
    val[b"save_path"] = rb"Q:\elsewhere\x"
    val[b"qBt-savePath"] = b"Q:/elsewhere/x"
    p.write_bytes(frmod.bencode(val))

    assert rd._rewrite_member(spec, {"hash_v1": h_ok}, None)["status"] == "rewritten"
    rec = rd._rewrite_member(spec, {"hash_v1": h_already}, None)
    assert rec["status"] == "already" and "save_path" in rec["keys"]
    assert rd._rewrite_member(spec, {"hash_v1": h_elsewhere}, None)["status"] == "unmatched"
    assert rd._rewrite_member(spec, {"hash_v1": h_missing}, None)["status"] == "not_found"
    bad = rd._rewrite_member(spec, {"hash_v1": h_bad}, None)
    assert bad["status"] == "failed" and bad["error"] and bad[rj.REWRITE_FAILS_KEY] == 1
    # fails 承前累计: 失败 +1, 成功保值(失败计数进账, D8); ok 已被上面真改写过, 用新成员
    bad2 = rd._rewrite_member(spec, {"hash_v1": h_bad}, {"status": "failed", "fails": 3})
    assert bad2["status"] == "failed" and bad2[rj.REWRITE_FAILS_KEY] == 4
    h_ok2 = _member_fixture(backup, b"m-ok2", old_root)
    ok2 = rd._rewrite_member(spec, {"hash_v1": h_ok2}, {"status": "failed", "fails": 2})
    assert ok2["status"] == "rewritten" and ok2[rj.REWRITE_FAILS_KEY] == 2
    # 契约错(old==new, 调用方责任) => failed 记账, daemon 不崩(fail-fast 面收进账里)
    h_same = _member_fixture(backup, b"m-same", old_root)
    same = rd._rewrite_member({"bt_backup": str(backup), "src": old_root, "dst": old_root}, {"hash_v1": h_same}, None)
    assert same["status"] == "failed" and "无改写差异" in same["error"]


def test_scan_jobs_filters_instance_optin_and_terminal(tmp_path):
    data_dir = str(tmp_path / "data")
    backup = tmp_path / "BT_backup"
    h1 = _member_fixture(backup, b"m-1", str(tmp_path / "src"))
    _write_job(tmp_path, data_dir, "job-mine", [h1])  # 本实例 + opt-in
    _write_job(tmp_path, data_dir, "job-other-host", [h1], host="10.0.0.9")  # 别实例
    _write_job(tmp_path, data_dir, "job-other-port", [h1], port=1)  # 别实例
    _write_job(tmp_path, data_dir, "job-oldchain", [h1], bt_backup=False)  # 旧链 spec(无 opt-in)
    _write_job(tmp_path, data_dir, "job-terminal", [h1], journal_phase="cancelled")  # 已收口
    _write_job(tmp_path, data_dir, "job-broken", [h1], src="", dst="")  # 残缺 spec
    (Path(data_dir) / "relocate" / "job-corrupt.spec.json").write_bytes(b"{not-json")  # 坏 spec
    _write_job(tmp_path, data_dir, "job-badport", [h1], port="abc")  # port 非数值
    # 翻相 flag: 全员收口 + 账在 + 相位未翻
    _write_job(tmp_path, data_dir, "job-settled", [h1])
    rj.record_rewrites(data_dir, "job-settled", {h1: {"status": "rewritten"}}, ts=1.0)

    jobs = {j["job_id"]: j for j in rd._scan_jobs(data_dir, HOST, PORT)}
    assert set(jobs) == {"job-mine", "job-settled"}
    assert [rj.member_key(m) for m in jobs["job-mine"]["pending"]] == [h1]
    assert jobs["job-settled"]["pending"] == [] and jobs["job-settled"]["flip"] is True


def test_owner_beat_throttles_touch(tmp_path, monkeypatch):
    d = str(tmp_path)
    owner = rd._Owner(d, "k", 7, heartbeat=10.0)
    assert owner.claim(1000.0, max_age=60.0) == "claimed"
    assert rj.read_daemon_state(d, "k")["ts"] == 1000.0
    assert owner.beat(1005.0) is True, "间隔未到: 自检过但不写"
    assert rj.read_daemon_state(d, "k")["ts"] == 1000.0
    assert owner.beat(1010.5) is True, "到点 touch"
    assert rj.read_daemon_state(d, "k")["ts"] == 1010.5
    # 被退位: 自检先于 touch => False 且新主记录原样
    rj.write_daemon_state(d, "k", 99, ts=1.0)
    assert owner.beat(1020.0) is False
    assert rj.read_daemon_state(d, "k")["pid"] == 99
    # 记录异常消失: 重新落盘认主(daemon 不因账文件消失而白死)
    os.remove(rj.daemon_state_path(d, "k"))
    assert owner.beat(1030.0) is True
    assert rj.read_daemon_state(d, "k")["pid"] == 7
    # touch 被拒(退位落在自检读与落账写的微秒间隙)⇒ beat False(写侧闸兜底)
    monkeypatch.setattr(rd.rj, "touch_daemon_state", lambda *a, **k: False)
    assert owner.beat(1040.0) is False


def test_run_flips_settled_phase_without_window(tmp_path, monkeypatch):
    """全员已收口而相位未翻(窗口中崩溃错过翻相)+ qB 在线 => 只补翻 rewritten, 零进窗零改写
    (journal 写不限窗口, D13; fastresume 落盘才限窗口, N1)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root, rewritten_to=str(tmp_path / "dst"))
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    rj.record_rewrites(data_dir, "job-1", {h1: {"status": "rewritten"}}, ts=1.0)
    state = {"up": True}
    _stub_qb(monkeypatch, state)
    calls = {"n": 0}
    real = rd.fastresume.retarget

    def _count(*a, **k):
        calls["n"] += 1
        return real(*a, **k)

    monkeypatch.setattr(rd.fastresume, "retarget", _count)
    assert _run(data_dir) == "idle"
    assert calls["n"] == 0, "零进窗零改写"
    assert rj.read_journal(data_dir, "job-1")["phase"] == rj.PHASE_REWRITTEN
    assert rj.read_daemon_state(data_dir, rj.instance_key(HOST, PORT)) is None, "空闲退出按归属释放"


def test_run_waits_for_stable_window_before_window(tmp_path, monkeypatch):
    """进窗第三证(稳定窗): 下线须持续满 stable 才动手(语义照搬 guardian)——窗口短于稳定窗
    (关机风暴形态)错过无害, 零落盘(N9 断言「窗口 < 稳定窗 => 错过、下一窗口收敛」的单元面)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    before = _fr_path(tmp_path, h1).read_bytes()
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}  # 全程「下线」, 但从未持续满 stable
    _stub_qb(monkeypatch, state)
    assert _run(data_dir, stable=100.0, max_wait=25.0) == "timeout", "稳定窗未满不进窗"
    assert rj.read_rewrites(data_dir, "job-1") == {}
    assert _fr_path(tmp_path, h1).read_bytes() == before


def test_run_grace_exit_after_idle_period(tmp_path, monkeypatch):
    data_dir = str(tmp_path / "data")
    state = {"up": True}
    _stub_qb(monkeypatch, state)
    # 无任何 job: 宽限 30s 计满才退(grace=30 < max_wait=100 => idle 先到, 非 timeout)
    assert _run(data_dir, grace=30.0, max_wait=100.0, clock=_clock_gen(step=10.0)) == "idle"
    assert rj.read_daemon_state(data_dir, rj.instance_key(HOST, PORT)) is None


def test_cli_main_idle_exit_zero(tmp_path, capsys):
    data_dir = str(tmp_path / "data")
    code = rd.main(["--data-dir", data_dir, "--host", HOST, "--port", str(PORT), "--grace", "0", "--poll", "0"])
    assert code == 0
    out = capsys.readouterr().out
    assert "idle" in out and HOST in out


def test_cli_main_timeout_exit_one(tmp_path, monkeypatch, capsys):
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": True}  # qB 在线无窗可进
    _stub_qb(monkeypatch, state)
    code = rd.main(["--data-dir", data_dir, "--host", HOST, "--port", str(PORT), "--poll", "0", "--max-wait", "20"])
    assert code == 1, "timeout 档退出码 1"
    assert "timeout" in capsys.readouterr().out


def test_module_main_entry_exits_with_result_code(tmp_path, monkeypatch):
    """python -m 入口: main() 结论码经 sys.exit 上抛(空载 idle 档退出码 0)"""
    import runpy
    import sys

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "recycle_daemon", "--data-dir",
            str(tmp_path / "none"), "--host", HOST, "--port",
            str(PORT), "--grace", "0", "--poll", "0"
        ],
    )
    with pytest.raises(SystemExit) as ei:
        runpy.run_module("auto_qb.tools.recycle_daemon", run_name="__main__")
    assert ei.value.code == 0


# ---------------------------------------------------------------------------
# 竞态矩阵
# ---------------------------------------------------------------------------


def test_qb_revives_before_first_write_zero_member_writes(tmp_path, monkeypatch):
    """[抢先回升/零写入] 进窗后第一次落盘之前 qB 回升 => 本轮放弃, 零成员改写, 账面零 records

    回升时机桩: 进程名册第 2 次现读(第一次=主循环下线判定, 第二次=窗口拍级复验)时把
    state 翻成「在」—— 名册现读正是 N1 铁律的守门点, 翻转落在两次现读之间即「写前复验
    拦住回升」。流程确定性由桩保证, 不依赖真实时序。"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    before = _fr_path(tmp_path, h1).read_bytes()
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))

    state = {"up": False}
    _stub_qb(monkeypatch, state)
    roster = {"n": 0}

    def _roster():
        roster["n"] += 1
        if roster["n"] >= 2:
            state["up"] = True  # 第二次名册现读时 qB 已回升
        # 评审 #6 合取语义: 名册与 state 联动(down = 名册可用但无 qB, up = 名册见 qB) ——
        # 旧桩恒含 qbittorrent, 在合取判定下窗永不开, 进窗/回升路径覆盖不到
        return ("qbittorrent.exe", ) if state["up"] else ("explorer.exe", )

    monkeypatch.setattr(rd, "_qb_process_names", _roster)
    assert _run(data_dir, max_wait=60.0) == "timeout", "回升后无窗可进, max_wait 收束"
    assert rj.read_rewrites(data_dir, "job-1") == {}, "零成员记账"
    assert _fr_path(tmp_path, h1).read_bytes() == before, "零落盘"


def test_qb_revives_mid_sequence_abandons_rest(tmp_path, monkeypatch):
    """[抢先回升/中途] A 改写落账后 qB 回升 => B 不再尝试(不落账不落盘); A 留存(N4 自愈面)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    new_root = str(tmp_path / "dst")
    h_a = _member_fixture(backup, b"m-a", old_root)
    h_b = _member_fixture(backup, b"m-b", old_root)
    b_before = _fr_path(tmp_path, h_b).read_bytes()
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h_a, h_b], src=old_root, dst=new_root)

    state = {"up": False}
    _stub_qb(monkeypatch, state)
    real = rd.fastresume.retarget

    def _retarget_then_revive(backup_dir, h1, h2, old, new):
        rep = real(backup_dir, h1, h2, old, new)
        if h1 == h_a:
            state["up"] = True  # A 刚落盘 qB 即回升
        return rep

    monkeypatch.setattr(rd.fastresume, "retarget", _retarget_then_revive)
    assert _run(data_dir, max_wait=60.0) == "timeout"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert set(rw) == {h_a} and rw[h_a]["status"] == "rewritten", "只 A 记账"
    d = frmod.load_fastresume(_fr_path(tmp_path, h_a))
    assert d[b"save_path"] == (new_root + "\\m-a").encode("utf-8")
    assert d[b"qBt-savePath"] == (new_root.replace("\\", "/") + "/m-a").encode("utf-8")
    assert _fr_path(tmp_path, h_b).read_bytes() == b_before, "B 零落盘"
    assert rj.read_journal(data_dir, "job-1")["phase"] == "armed", "未收口不翻相"


def test_crash_mid_window_journal_consistent_and_next_round_replays(tmp_path, monkeypatch):
    """[半途崩溃] A 收口后 daemon 终止(B 持续失败至 max_wait => timeout 模拟进程死亡)
    => 账面一致(A rewritten / B failed 且计数在账); 修好 B 后新 daemon 重放: 只试 B
    (A 零重试), B 收口, 相位翻 rewritten"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h_a = _member_fixture(backup, b"m-a", old_root)
    h_b = _member_fixture(backup, b"m-b", old_root)
    (_fr_path(tmp_path, h_b)).write_bytes(b"garbage-not-bencode")  # B 坏样本: 持续失败
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h_a, h_b], src=old_root, dst=str(tmp_path / "dst"))

    state = {"up": False}
    _stub_qb(monkeypatch, state)
    calls = {"a": 0, "b": 0}
    real = rd.fastresume.retarget

    def _count(backup_dir, h1, h2, old, new):
        calls["a" if h1 == h_a else "b"] += 1
        return real(backup_dir, h1, h2, old, new)

    monkeypatch.setattr(rd.fastresume, "retarget", _count)
    assert _run(data_dir, max_wait=200.0) == "timeout", "daemon 终止(崩溃替身)"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h_a]["status"] == "rewritten", "A 的账已落(崩溃前)"
    assert rw[h_b]["status"] == "failed" and rw[h_b][rj.REWRITE_FAILS_KEY] >= 2, "B 失败计数进账"
    assert rj.read_journal(data_dir, "job-1")["phase"] == "armed", "未收口不翻相"
    a_calls_after_crash = calls["a"]

    # 新 daemon 起来(账在, 崩溃无痕): 修好 B, 重放只试 B
    good = {
        b"save_path": (old_root + "\\m-b").encode("utf-8"),
        b"qBt-savePath": (old_root.replace("\\", "/") + "/m-b").encode("utf-8"),
        b"completed": 1,
    }
    (_fr_path(tmp_path, h_b)).write_bytes(frmod.bencode(good))
    assert _run(data_dir) == "idle"
    assert calls["a"] == a_calls_after_crash, "A 已收口, 零重试"
    assert calls["b"] >= 2, "B 被重放"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h_b]["status"] == "rewritten" and rw[h_b][rj.REWRITE_FAILS_KEY] >= 2, "计数承前不丢"
    assert rj.read_journal(data_dir, "job-1")["phase"] == rj.PHASE_REWRITTEN, "全收口翻相"


def test_replay_after_journal_loss_records_already(tmp_path, monkeypatch):
    """[重复重放] fastresume 已在目标值而账本清零 => retarget unchanged+already => 记 already
    出账, 文件字节零改动, 无 .bak 产生(黄金法则 1: 幂等重放零副作用)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root, rewritten_to=str(tmp_path / "dst"))
    fr = _fr_path(tmp_path, h1)
    before = fr.read_bytes()
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    assert _run(data_dir) == "idle"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h1]["status"] == "already", "已在目标值记 already(出账)"
    assert "save_path" in rw[h1]["keys"]
    assert fr.read_bytes() == before, "文件字节零改动"
    assert not fr.with_name(fr.name + ".bak").exists(), "未落盘即无 .bak"
    assert rj.read_journal(data_dir, "job-1")["phase"] == rj.PHASE_REWRITTEN


def test_window_retry_until_success_counts_failures(tmp_path, monkeypatch):
    """[窗口内重试] 瞬态故障(坏样本第一拍后自愈) => 窗口内第二拍改写成功(D8: 重试至成功),
    失败计数 1 进账不丢"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    good_again = {
        b"save_path": (old_root + "\\m-1").encode("utf-8"),
        b"qBt-savePath": (old_root.replace("\\", "/") + "/m-1").encode("utf-8"),
        b"completed": 1,
    }
    (_fr_path(tmp_path, h1)).write_bytes(b"garbage-not-bencode")  # 先坏
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    calls = {"n": 0}
    real = rd.fastresume.retarget

    def _flaky(backup_dir, h1_, h2_, old, new):
        calls["n"] += 1
        try:
            return real(backup_dir, h1_, h2_, old, new)
        finally:
            if calls["n"] == 1:
                (_fr_path(tmp_path, h1)).write_bytes(frmod.bencode(good_again))  # 第一拍后自愈

    monkeypatch.setattr(rd.fastresume, "retarget", _flaky)
    assert _run(data_dir) == "idle"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h1]["status"] == "rewritten"
    assert rw[h1][rj.REWRITE_FAILS_KEY] == 1, "失败计数进账且不丢"
    assert calls["n"] >= 2, "窗口内重试确有发生"
    assert rj.read_journal(data_dir, "job-1")["phase"] == rj.PHASE_REWRITTEN


def test_main_loop_cancel_mid_window_skips_rest(tmp_path, monkeypatch):
    """[取消即时生效] A 落账的同一间隙对账落终态 => B 写前现读见终态即弃(不落盘),
    终态相位不被 daemon 回退(前向合并)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h_a = _member_fixture(backup, b"m-a", old_root)
    h_b = _member_fixture(backup, b"m-b", old_root)
    b_before = _fr_path(tmp_path, h_b).read_bytes()
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h_a, h_b], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    real_rec = rd.rj.record_rewrites

    def _rec_then_cancel(data_dir_, job_id, records, **kw):
        ok = real_rec(data_dir_, job_id, records, **kw)
        if ok and h_a in records:
            rj.write_journal(data_dir_, job_id, {"phase": "cancelled"})  # 对账同间隙收口
        return ok

    monkeypatch.setattr(rd.rj, "record_rewrites", _rec_then_cancel)
    assert _run(data_dir) == "idle"
    assert rj.read_journal(data_dir, "job-1")["phase"] == "cancelled", "终态不被回退"
    assert _fr_path(tmp_path, h_b).read_bytes() == b_before, "取消后 B 零落盘"


def test_deposed_old_daemon_self_checks_and_exits(tmp_path, monkeypatch):
    """[退位互斥] 新主 pid 抢占(纯文件写, 绝不 taskkill) => 旧 daemon 下一拍自检见外来
    pid 即 deposed 退出; 退出前零覆盖(新主记录原样), release 不误删新主记录"""
    data_dir = str(tmp_path / "data")
    foreign_pid = os.getpid() + 100000  # 外来 pid(只在文件里, 不探测不杀)
    foreign_ts = 123.0
    scan = {"n": 0}
    real_scan = rd._scan_jobs

    def _scan_then_preempt(data_dir_, host, port):
        n = scan["n"] + 1
        scan["n"] = n
        if n == 1:
            # "新 daemon" 在旧主第一拍扫描时抢占: 纯 pid 抢占(写文件)
            rj.write_daemon_state(data_dir_, rj.instance_key(HOST, PORT), foreign_pid, ts=foreign_ts)
        return real_scan(data_dir_, host, port)

    monkeypatch.setattr(rd, "_scan_jobs", _scan_then_preempt)
    assert _run(data_dir, grace=10.0**9) == "deposed", "旧主自检自杀"
    st = rj.read_daemon_state(data_dir, rj.instance_key(HOST, PORT))
    assert st["pid"] == foreign_pid and st["ts"] == foreign_ts, "旧主退出前零覆盖"
    assert scan["n"] >= 1


def test_deposed_at_window_pass_top_aborts_round(tmp_path, monkeypatch):
    """[退位互斥/窗口内] 新主在窗口会话中抢占(记账后落外来 pid) => 下一拍顶部自检即弃,
    整轮 deposed 收束, 不再碰任何成员"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    data_dir = str(tmp_path / "data")
    key = rj.instance_key(HOST, PORT)
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    foreign_pid = os.getpid() + 200000
    real_rec = rd.rj.record_rewrites

    def _rec_then_preempt(data_dir_, job_id, records, **kw):
        ok = real_rec(data_dir_, job_id, records, **kw)
        if ok:
            rj.write_daemon_state(data_dir_, key, foreign_pid, ts=999.0)  # 新主抢占(纯文件写)
        return ok

    monkeypatch.setattr(rd.rj, "record_rewrites", _rec_then_preempt)
    assert _run(data_dir, grace=10.0**9) == "deposed", "拍顶自检自杀"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h1]["status"] == "rewritten", "已落账部分留存"
    st = rj.read_daemon_state(data_dir, key)
    assert st["pid"] == foreign_pid and st["ts"] == 999.0, "退位者零覆盖"


def test_deposed_mid_window_member_beat_aborts(tmp_path, monkeypatch):
    """[退位互斥/成员拍] 抢占落在成员 A 检查与记账之间 => 成员 B 的拍级自检见外来 pid
    即整轮放弃, B 零触碰"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h_a = _member_fixture(backup, b"m-a", old_root)
    h_b = _member_fixture(backup, b"m-b", old_root)
    b_before = _fr_path(tmp_path, h_b).read_bytes()
    data_dir = str(tmp_path / "data")
    key = rj.instance_key(HOST, PORT)
    _write_job(tmp_path, data_dir, "job-1", [h_a, h_b], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    foreign_pid = os.getpid() + 300000
    real_wo = rd._window_open
    wo = {"n": 0}

    def _wo_then_preempt(host, port):
        wo["n"] += 1
        if wo["n"] == 2:  # 拍级(1)之后的成员级复验点: A 处理中途新主抢占
            rj.write_daemon_state(data_dir, key, foreign_pid, ts=999.0)
        return real_wo(host, port)

    monkeypatch.setattr(rd, "_window_open", _wo_then_preempt)
    assert _run(data_dir, grace=10.0**9) == "deposed"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert set(rw) == {h_a}, "只 A 记账"
    assert _fr_path(tmp_path, h_b).read_bytes() == b_before, "B 零触碰"


def test_record_refused_when_terminal_lands_in_gap(tmp_path, monkeypatch):
    """收口落在写前检查与落账的间隙 => record_rewrites 拒收(False) => 该 job 立即放弃
    (协议级终态闸门在 daemon 侧的出口)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    real_rec = rd.rj.record_rewrites

    def _rec_after_terminal(data_dir_, job_id, records, **kw):
        rj.write_journal(data_dir_, job_id, {"phase": "cancelled"})  # 主循环恰在间隙收口
        return real_rec(data_dir_, job_id, records, **kw)  # => False(终态拒收)

    monkeypatch.setattr(rd.rj, "record_rewrites", _rec_after_terminal)
    assert _run(data_dir) == "idle"
    assert rj.read_journal(data_dir, "job-1")["phase"] == "cancelled", "终态不被回退"


def test_run_already_running_healthy_watcher_untouched(tmp_path):
    data_dir = str(tmp_path / "data")
    key = rj.instance_key(HOST, PORT)
    rj.write_daemon_state(data_dir, key, os.getpid(), ts=1000.0)  # 健康 watcher(本进程必活)
    assert _run(data_dir) == "already_running"
    st = rj.read_daemon_state(data_dir, key)
    assert st["pid"] == os.getpid() and st["ts"] == 1000.0, "让路者零触碰"


def test_run_preempts_dead_pid_record(tmp_path, monkeypatch):
    data_dir = str(tmp_path / "data")
    key = rj.instance_key(HOST, PORT)
    rj.write_daemon_state(data_dir, key, 424242, ts=1000.0)  # 记录 pid 已死
    monkeypatch.setattr(rj, "_alive", lambda pid: pid == os.getpid())
    seen = {}
    real_scan = rd._scan_jobs

    def _snap(data_dir_, host, port):
        seen.setdefault("st", rj.read_daemon_state(data_dir_, key))  # 抢占落定后的记录
        return real_scan(data_dir_, host, port)

    monkeypatch.setattr(rd, "_scan_jobs", _snap)
    assert _run(data_dir) == "idle", "抢占后正常接管(空载宽限退出)"
    assert seen["st"]["pid"] == os.getpid(), "pid 抢占已落账"


def test_run_timeout_keeps_pending(tmp_path, monkeypatch):
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    before = _fr_path(tmp_path, h1).read_bytes()
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": True}  # qB 在线: 无窗可进
    _stub_qb(monkeypatch, state)
    assert _run(data_dir, max_wait=40.0) == "timeout"
    assert rj.read_rewrites(data_dir, "job-1") == {}, "pending 原样"
    assert _fr_path(tmp_path, h1).read_bytes() == before
    assert rj.read_daemon_state(data_dir, rj.instance_key(HOST, PORT)) is None, "按归属释放"


# ---------------------------------------------------------------------------
# 覆盖率缺口清偿(26-11-07): journal 协议边角 / 进程名册跨平台支
# ---------------------------------------------------------------------------


def test_write_journal_refuses_nonterminal_over_terminal(tmp_path):
    """终态闸门: journal 已收口(done/cancelled)时非终态写被拒(False), 终态互覆仍放行"""
    assert rj.write_journal(str(tmp_path), "j1", {"phase": "done"}) is True
    assert rj.write_journal(str(tmp_path), "j1", {"phase": "armed"}) is False, "终态不被非终态回退"
    assert rj.write_journal(str(tmp_path), "j1", {"phase": "cancelled"}) is True, "终态互覆 last-writer-wins"


def test_alive_posix_fallback_paths(monkeypatch):
    """_alive POSIX 支: os.kill 探活 / 进程不在 / 信号不支持, 三路都有归宿(Windows 桩 os.name)"""
    monkeypatch.setattr(rj.os, "name", "posix")
    monkeypatch.setattr(rj.os, "kill", lambda pid, sig: None)
    assert rj._alive(os.getpid()) is True

    def _no_proc(pid, sig):
        raise OSError(3, "no such process")

    monkeypatch.setattr(rj.os, "kill", _no_proc)
    assert rj._alive(999999) is False

    def _unsupported(pid, sig):
        raise AttributeError("kill unsupported")

    monkeypatch.setattr(rj.os, "kill", _unsupported)
    assert rj._alive(1) is False


def test_verify_replays_of_bad_shape_is_zero(tmp_path):
    """verify_replays 坏形(非数字) => 0(从未重放), 不抛"""
    rj.write_journal(str(tmp_path), "j1", {"phase": "armed", "verify_replays": "not-a-number"})
    assert rj.verify_replays_of(str(tmp_path), "j1") == 0


def test_reset_rewrites_terminal_refused_and_keeps_unsettled(tmp_path):
    """重放入口: 终态拒(-1); settled 清回 pending 时非 settled 记录原样保留"""
    assert rj.reset_rewrites(str(tmp_path), "gone", ts=1.0) == 0, "无 journal: 无 settled 可重置(幂等 0)"
    rj.write_journal(str(tmp_path), "j1", {"phase": "done"})
    assert rj.reset_rewrites(str(tmp_path), "j1", ts=1.0) == -1, "终态拒重放"
    rj.write_journal(
        str(tmp_path),
        "j2",
        {
            "phase": "rewritten",
            "rewrites": {
                "HA": {
                    "status": "rewritten"
                },
                "HB": {
                    "status": "failed",
                    "error": "x"
                },
            },
        },
    )
    n = rj.reset_rewrites(str(tmp_path), "j2", ts=2.0)
    assert n == 1, "只有 settled(rewritten)被清"
    rewrites = rj.read_rewrites(str(tmp_path), "j2")
    assert rewrites["HA"]["status"] == rj.REWRITE_RESET_STATUS and rewrites["HA"]["prev_status"] == "rewritten"
    assert rewrites["HB"] == {"status": "failed", "error": "x"}, "非 settled 记录原样保留"


def test_tasklist_ignores_non_quoted_lines(monkeypatch):
    """tasklist CSV 解析: 非引号开头行(表头/空行)跳过, 只收引号内映像名"""
    class _Out:
        stdout = '"qbittorrent.exe","1234","Console","1"\nheader-without-quotes\n'

    monkeypatch.setattr(rd.subprocess, "run", lambda *a, **kw: _Out())
    assert rd._names_from_tasklist() == ("qbittorrent.exe", )


def test_names_from_proc_tolerates_unreadable_comm(monkeypatch, tmp_path):
    """/proc 名册: 非数字项跳过; comm 打不开(权限/消失)逐项跳过不炸, 可读项照常收"""
    monkeypatch.setattr(rd.os, "listdir", lambda p: ["1", "self", "2"])
    # pid 1 的 comm 重定向到已知内容的真实文件: Windows 无 /proc, 不重定向则可读支在
    # 主平台空转(名册空 tuple, all(()) 恒真断言失效), 重定向后两平台都断到非空名册
    comm1 = tmp_path / "comm1"
    comm1.write_text("systemd\n", encoding="utf-8")
    real_open = open

    def _open(path, *a, **kw):
        p = str(path).replace("\\", "/")
        if p.endswith("/comm"):
            if "/2/" in p:
                raise OSError(13, "permission")
            if "/1/" in p:
                return real_open(str(comm1), *a, **kw)
        return real_open(path, *a, **kw)

    import builtins

    monkeypatch.setattr(builtins, "open", _open)
    names = rd._names_from_proc()
    assert isinstance(names, tuple)
    # 真断言(评审 #7: 原行 "X or True" 恒真): 可读项(pid 1 重定向文件)收进名册, 不可读
    # 项(拒读的 pid 2)跳过, 不产空串垃圾项 —— 两平台名册均非空, 断言不再空转
    assert names == ("systemd", )


def test_qb_process_names_dispatches_non_windows(monkeypatch):
    """进程名册分派: 非 Windows 且无 /proc -> ps 支; 非 Windows 且有 /proc -> proc 支"""
    monkeypatch.setattr(rd.os, "name", "posix")
    monkeypatch.setattr(rd.os.path, "isdir", lambda p: False)
    monkeypatch.setattr(rd, "_names_from_ps", lambda: ("ps-qbittorrent-nox", ))
    assert rd._qb_process_names() == ("ps-qbittorrent-nox", )
    monkeypatch.setattr(rd.os.path, "isdir", lambda p: True)
    monkeypatch.setattr(rd, "_names_from_proc", lambda: ("proc-qbittorrent", ))
    assert rd._qb_process_names() == ("proc-qbittorrent", )


def test_proc_absent_dual_evidence_and_roster_fallback(monkeypatch, caplog):
    """证一判定(评审 #6): 名册可用时「进程不在 AND 端口拒连」双判合取 —— 端口拒连只证明
    WebUI 不可达, 不证明进程不在; 旧实现端口短路恒 True, qB 存活但 WebUI 不可达时假阳性
    进窗, daemon 在 qB 运行期改写 fastresume(N1 零写入被破)"""
    port_state = {"refused": True}
    monkeypatch.setattr(rd, "_port_refused", lambda host, port, timeout=1.0: port_state["refused"])
    # 名册见 qB + 端口拒连 => False(评审 #6 核心支: 不进窗)
    assert rd._proc_absent(("qbittorrent.exe", ), "127.0.0.1", 8080) is False
    # 名册见 qB + 端口可连 => False
    port_state["refused"] = False
    assert rd._proc_absent(("qbittorrent.exe", ), "127.0.0.1", 8080) is False
    # 名册无 qB + 端口可连 => False(端口证不成立)
    assert rd._proc_absent(("chrome.exe", ), "127.0.0.1", 8080) is False
    # 名册无 qB + 端口拒连 => True(合取成立; qB 真死两证自然同向, 窗口可用性不受损)
    port_state["refused"] = True
    assert rd._proc_absent(("chrome.exe", ), "127.0.0.1", 8080) is True
    # 名册不可用(空)+ 端口拒连 => 端口单证 True, 但告警降级留痕(证据链弱化不许静默)
    with caplog.at_level(logging.WARNING, logger="auto_qb.tools.recycle_daemon"):
        assert rd._proc_absent((), "127.0.0.1", 8080) is True
    assert any("名册不可用" in r.message for r in caplog.records), caplog.text
    # 名册不可用 + 端口可连 => False(端口在服务, 不告警)
    caplog.clear()
    port_state["refused"] = False
    assert rd._proc_absent((), "127.0.0.1", 8080) is False
    assert not any("名册不可用" in r.message for r in caplog.records)
    # 无端口可判(port=0): 退回名册单证(旧行为, 兼容无端口场景)
    assert rd._proc_absent(("chrome.exe", ), "", 0) is True
    assert rd._proc_absent(("qbittorrent.exe", ), "", 0) is False
    # 无端口且无名册 => 未证明(保守 False, 旧口径「判不出不算已退出」不变)
    assert rd._proc_absent((), "", 0) is False


def test_spec_retarget_mid_window_rewrites_remaining_to_new_dst(tmp_path, monkeypatch):
    """[supersede 即时生效/评审 #4] 窗口中段 spec.dst 被改道(retarget_spec 不需 qB 在线)
    => 剩余成员按新 dst 改写; 旧实现沿用窗口 scan 快照会把剩余成员写旧 dst(改写方向错)。
    另: spec 现读失败(被并发重写撕态) => 本 job 本拍放弃, 绝不拿旧快照改写。"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst1").mkdir()
    tmp_path.joinpath("dst2").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    dst1, dst2 = str(tmp_path / "dst1"), str(tmp_path / "dst2")
    h_a = _member_fixture(backup, b"m-a", old_root)
    h_b = _member_fixture(backup, b"m-b", old_root)
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h_a, h_b], src=old_root, dst=dst1)
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    real = rd.fastresume.retarget

    def _retarget_then_redirect(backup_dir, h1, h2, old, new):
        # A 改写落盘的同一间隙, supersede 改道 spec.dst(dst1 -> dst2; 账面段不需 qB 在线)
        assert new == dst1, "前置: 改道发生在窗口 scan 之后, 本拍仍按 scan 快照的目标"
        out = real(backup_dir, h1, h2, old, new)
        assert rj.retarget_spec(data_dir, "job-1", dst2)
        return out

    calls = {"n": 0}

    def _hook(backup_dir, h1, h2, old, new):
        calls["n"] += 1
        if calls["n"] == 1:
            return _retarget_then_redirect(backup_dir, h1, h2, old, new)
        return real(backup_dir, h1, h2, old, new)

    monkeypatch.setattr(rd.fastresume, "retarget", _hook)
    assert _run(data_dir) == "idle"
    assert rj.read_spec(data_dir, "job-1")["dst"] == dst2, "改道已落盘"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert rw[h_a]["status"] == "rewritten", "A: 改道前按当时账面 dst1 改写(时序正确)"
    assert rw[h_b]["status"] == "rewritten", "B: 改道后必须按新 dst 改写"
    fr_b = _fr_path(tmp_path, h_b)
    val, _pos = frmod.bdecode(fr_b.read_bytes())
    assert val[b"save_path"] == (dst2 + "\\m-b").encode("utf-8"), "B 落到新 dst(旧实现会写 dst1)"
    assert val[b"qBt-savePath"] == (dst2.replace("\\", "/") + "/m-b").encode("utf-8")
    fr_a = _fr_path(tmp_path, h_a)
    val_a, _pos = frmod.bdecode(fr_a.read_bytes())
    assert val_a[b"save_path"] == (dst1 + "\\m-a").encode("utf-8"), "A 维持改道前的 dst1(已写部分不追改)"


def test_spec_unreadable_mid_window_skips_job_without_stale_rewrite(tmp_path, monkeypatch):
    """spec 现读失败(撕态/被删) => 本 job 本拍放弃, 不拿窗口 scan 快照改写(评审 #4 容错支)"""
    tmp_path.joinpath("src").mkdir()
    tmp_path.joinpath("dst").mkdir()
    backup = tmp_path / "BT_backup"
    old_root = str(tmp_path / "src")
    h1 = _member_fixture(backup, b"m-1", old_root)
    data_dir = str(tmp_path / "data")
    _write_job(tmp_path, data_dir, "job-1", [h1], src=old_root, dst=str(tmp_path / "dst"))
    state = {"up": False}
    _stub_qb(monkeypatch, state)
    real_read_spec = rj.read_spec
    spec_calls = {"n": 0}

    def _flaky_spec(dd, job_id):
        spec_calls["n"] += 1
        if spec_calls["n"] <= 1:
            return real_read_spec(dd, job_id)  # 窗口 scan 时 spec 还在
        return None  # 窗口内逐成员现读: 撕态/被删

    monkeypatch.setattr(rd.rj, "read_spec", _flaky_spec)
    assert _run(data_dir, max_wait=200.0) == "timeout", "spec 恒读不到 => 放弃本 job(pending 留守), max_wait 兜底"
    assert spec_calls["n"] >= 2, "窗口内确有逐成员现读(非只用 scan 快照)"
    rw = rj.read_rewrites(data_dir, "job-1")
    assert not rw, "零改写零落账: 绝不拿旧快照改写(下一窗口按新账重放)"
    assert not (rj.read_journal(data_dir, "job-1") or {}), "零建账(从未落过改写记录)"
