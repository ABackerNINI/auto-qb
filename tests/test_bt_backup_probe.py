"""test_bt_backup_probe 测试计划: BT_backup 探测后端纯函数(计划 26-11-11-0259 S3, tmpdir 合成矩阵)

零真实网络零真实 qB 零真实子进程: 子进程面 monkeypatch 替身(含命令串捕获), 文件系统面全走
tmp_path 合成目录, 平台经 candidates(platform) 参数合成 win/linux/mac 场景(本机是 Windows)。

## 测试计划
- test_host_platform_predicate_mapping: host_platform() 三平台谓词命中与未知平台空串(生产入口)
- test_win_default_profile_candidates: win 默认 profile 推导(LOCALAPPDATA + 配置目录后缀枚举)
- test_linux_default_profile_new_and_legacy: linux 新旧布局双候选, 同后缀成对
- test_mac_default_profile_candidates: mac Application Support + Preferences *.ini 后缀枚举
- test_multiple_suffixes_enumerated: 多 configuration 并存全部列为候选(歧义交 hash 自证消歧)
- test_win_env_fallback_to_home: LOCALAPPDATA/APPDATA 缺失/空白回退 home 派生 + 非空带空白 strip 归一
- test_unsupported_platform_evidence_only: 未知平台零候选 + 证据行, 不触碰 exe 定位
- test_coverage_note_always_present: --profile/QBT_PROFILE/远程 qB 不可探测的覆盖面说明恒在
- test_portable_candidates_via_injected_locator: 便携候选推导(exe 旁 profile/ 存在 + 后缀枚举 + 去重)
- test_portable_locator_failure_is_evidence_line: 定位失败 = 证据行不抛栈, 零便携候选
- test_portable_exe_without_profile_dir_skipped: exe 无 profile/ = 非便携, 证据行
- test_posix_exe_scanner_via_proc: /proc readlink 扫描真实实现(monkeypatch os 面)
- test_posix_exe_scanner_failure_is_evidence: /proc 不可枚举降级证据行
- test_powershell_query_pins_utf8_and_timeout: argv/命令串/UTF-8 钉码/超时守护断言
- test_powershell_query_has_no_injection_surface: 命令串恒等于编译期常量(不拼 env/home 任何输入)
- test_powershell_query_failure_modes: 超时/OSError/非零退出各降级证据行
- test_win_portable_dirs_mixed_output: 便携 exe 循环(非绝对路径守卫/exe->目录推导/同目录去重/逐 exe 证据)
- test_qualify_fastresume_ids: ^40hex\\.fastresume$ 合格 + 大小写归一 + 非法形态不计
- test_qualify_queue_file: queue 文件单独构成资格
- test_qualify_empty_or_missing_dir: 空目录/不存在/传文件路径/不可读均不资格且带原因
- test_torrent_ids_double_count_v1_and_v2trunc: get_best() 双算(v1 + v2 前 40 hex)
- test_torrent_id_set_batch: (v1, v2) 对序列合成全集, 畸形输入跳过
- test_verify_intersects_fastresume_names: TorrentID 集合与候选 40hex 文件名求交(含归一)
- test_verify_hybrid_44x_v1_named: 4.4.x hybrid 以 v1 命名的目录被双算集合命中
- test_verdict_hit_single_qualified_online_verified: 恰一个合格 + 在线 + 交集 >= 1 -> hit(自证)
- test_verdict_hit_single_qualified_offline: 离线 -> hit + 未自证标注 + SQLite 未排除说明
- test_verdict_hit_single_qualified_online_zero_intersection: 在线但交集 0 -> hit + 警示原因
- test_verdict_disambiguation_by_hash: 多候选 hash 消歧命中唯一 -> hit
- test_verdict_ambiguous_multiple_hash_hits: 多候选多命中 -> ambiguous(拒不猜测)
- test_verdict_ambiguous_structure_only: 多候选零命中(含离线) -> ambiguous
- test_verdict_miss_zero_qualified: 零合格 -> miss(列已扫描候选)
- test_verdict_unusable_sqlite_before_manual_set: SQLite(含整数 1 形态)先于 manual-set 短路
- test_verdict_manual_set_short_circuits_hit: manual-set 吞掉 hit(仅供核对, 证据保留)
- test_verdict_offline_ignores_matches: online=False 时传入 matches 被机械忽略
- test_verdict_unknown_storage_value_noted: 非 Legacy 已知值 -> 证据行提示运行面拦截
- test_verdict_reports_join_by_path: CandidateReport 逐候选证据按路径联接 + 未判定兜底
- test_end_to_end_synthetic_matrix: 推导+资格+自证+裁决全链路(默认 profile 命中回填场景)
"""
from __future__ import annotations

import os
import subprocess

from auto_qb.infra import bt_backup_probe as probe

V1 = "a" * 40  # infohash_v1 形态(sha1, 40 hex)
V1B = "c" * 40
V2_64 = "b" * 64  # infohash_v2 形态(sha256, 64 hex)
V2TRUNC = "b" * 40  # v2 截断前 20 字节 = 前 40 hex


def _no_portable():
    """默认场景替身: 便携定位器无结果无证据(让用例专注默认 profile 面)"""
    return (), ()


def _scan(*paths: str) -> probe.CandidateScan:
    """verdict 用例的合成扫描结果: 全部按默认 profile 候选装配"""
    cands = tuple(probe.Candidate(p, probe.ORIGIN_DEFAULT, "", "合成候选") for p in paths)
    return probe.CandidateScan(cands, ("合成扫描证据", ))


def _qual(path: str, *ids: str, has_queue: bool = False) -> probe.Qualification:
    return probe.Qualification(path, True, "合成合格", frozenset(ids), has_queue)


def _cp(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(["powershell"], returncode, stdout=stdout, stderr="")


def _install_run(monkeypatch, handler):
    """把 subprocess.run 换成假实现, 返回调用记录 [(cmd, kwargs), ...](替身捕获命令串)"""
    calls: list = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return handler(cmd, kwargs, len(calls) - 1)

    monkeypatch.setattr(probe.subprocess, "run", fake_run)
    return calls


# ---- 候选推导: 默认 profile(三平台合成) ----


def test_host_platform_predicate_mapping(monkeypatch):
    """生产入口(S4 端点以其返回值进 candidates()): 三平台谓词命中与未知平台空串逐态钉死"""
    def with_predicates(win: bool, mac: bool, linux: bool):
        monkeypatch.setattr(probe, "is_windows", lambda: win)
        monkeypatch.setattr(probe, "is_mac", lambda: mac)
        monkeypatch.setattr(probe, "is_linux", lambda: linux)

    with_predicates(True, False, False)
    assert probe.host_platform() == probe.PLATFORM_WINDOWS
    with_predicates(False, False, True)
    assert probe.host_platform() == probe.PLATFORM_LINUX
    with_predicates(False, True, False)
    assert probe.host_platform() == probe.PLATFORM_MAC
    with_predicates(False, False, False)
    assert probe.host_platform() == "", "未知平台空串 -> candidates() 走「不支持的平台」证据行降级"


def test_win_default_profile_candidates(tmp_path):
    local = tmp_path / "Local"
    roaming = tmp_path / "Roaming"
    (roaming / "qBittorrent").mkdir(parents=True)
    scan = probe.candidates(
        probe.PLATFORM_WINDOWS,
        env={
            "LOCALAPPDATA": str(local),
            "APPDATA": str(roaming)
        },
        home=tmp_path,
        exe_locator=_no_portable,
    )
    assert [c.path for c in scan.candidates] == [str(local / "qBittorrent" / "BT_backup")]
    c = scan.candidates[0]
    assert c.origin == probe.ORIGIN_DEFAULT and c.suffix == ""
    assert "Windows 默认 profile" in c.note
    assert any("仅默认实例" in line for line in scan.evidence)


def test_linux_default_profile_new_and_legacy(tmp_path):
    data = tmp_path / "share"
    cfg = tmp_path / "config"
    (cfg / "qBittorrent").mkdir(parents=True)
    scan = probe.candidates(
        probe.PLATFORM_LINUX,
        env={
            "XDG_DATA_HOME": str(data),
            "XDG_CONFIG_HOME": str(cfg)
        },
        home=tmp_path,
        exe_locator=_no_portable,
    )
    assert [c.path for c in scan.candidates] == [
        str(data / "qBittorrent" / "BT_backup"),
        str(data / "data" / "qBittorrent" / "BT_backup"),
    ]
    assert "4.3.0+" in scan.candidates[0].note and "legacy" in scan.candidates[1].note
    assert all(c.origin == probe.ORIGIN_DEFAULT for c in scan.candidates)


def test_mac_default_profile_candidates(tmp_path):
    prefs = tmp_path / "Library" / "Preferences"
    prefs.mkdir(parents=True)
    (prefs / "qBittorrent.ini").write_text("x", encoding="utf-8")
    (prefs / "qBittorrent_alt.ini").write_text("x", encoding="utf-8")
    (prefs / "qBittorrentNotIni.txt").write_text("x", encoding="utf-8")
    support = tmp_path / "Library" / "Application Support"
    scan = probe.candidates(probe.PLATFORM_MAC, env={}, home=tmp_path, exe_locator=_no_portable)
    assert [c.path for c in scan.candidates] == [
        str(support / "qBittorrent" / "BT_backup"),
        str(support / "qBittorrent_alt" / "BT_backup"),
    ]
    assert scan.candidates[0].suffix == "" and scan.candidates[1].suffix == "_alt"


def test_multiple_suffixes_enumerated(tmp_path):
    """多 configuration 并存: 后缀枚举出新旧全部候选, 不做择一(歧义交 hash 自证消歧)"""
    local = tmp_path / "Local"
    roaming = tmp_path / "Roaming"
    for name in ("qBittorrent", "qBittorrent_enhanced", "qBittorrent_b", "not-qb", "qBittorrentBad"):
        (roaming / name).mkdir(parents=True)
    (roaming / "qBittorrent_stray.ini").write_text("x", encoding="utf-8")  # win 配置面只认目录
    scan = probe.candidates(
        probe.PLATFORM_WINDOWS,
        env={
            "LOCALAPPDATA": str(local),
            "APPDATA": str(roaming)
        },
        home=tmp_path,
        exe_locator=_no_portable,
    )
    assert [c.suffix for c in scan.candidates] == ["", "_b", "_enhanced"]
    assert scan.candidates[2].path == str(local / "qBittorrent_enhanced" / "BT_backup")
    assert any("_b, _enhanced" in line for line in scan.evidence)


def test_win_env_fallback_to_home(tmp_path):
    """LOCALAPPDATA/APPDATA 缺失/空白 -> home 派生回退; 非空带首尾空白 strip 归一(不猜更深的形态)"""
    scan = probe.candidates(
        probe.PLATFORM_WINDOWS, env={
            "LOCALAPPDATA": "  ",
            "APPDATA": ""
        }, home=tmp_path, exe_locator=_no_portable
    )
    assert [c.path for c in scan.candidates] == [str(tmp_path / "AppData" / "Local" / "qBittorrent" / "BT_backup")]

    padded = tmp_path / "padded"
    scan2 = probe.candidates(
        probe.PLATFORM_WINDOWS,
        env={
            "LOCALAPPDATA": f"  {padded}  ",
            "APPDATA": str(padded)
        },
        home=tmp_path,
        exe_locator=_no_portable,
    )
    assert [c.path for c in scan2.candidates] == [
        str(padded / "qBittorrent" / "BT_backup")
    ], "判空与转 Path 用同一 strip 归一值, 带空白非空值不产出带空白候选(防误 miss)"


def test_unsupported_platform_evidence_only():
    """未知平台: 零候选 + 证据行, 也不触碰 exe 定位(无注入 locator 且平台无默认定位器)"""
    scan = probe.candidates("freebsd", env={}, home="/home/x")
    assert scan.candidates == ()
    assert any("不支持的平台" in line and "freebsd" in line for line in scan.evidence)


def test_coverage_note_always_present(tmp_path):
    for platform in (probe.PLATFORM_WINDOWS, probe.PLATFORM_LINUX, probe.PLATFORM_MAC, "freebsd"):
        scan = probe.candidates(platform, env={}, home=tmp_path, exe_locator=_no_portable)
        assert any("--profile" in line and "QBT_PROFILE" in line for line in scan.evidence), platform


# ---- 候选推导: 便携(替身注入) ----


def test_portable_candidates_via_injected_locator(tmp_path):
    exe_dir = tmp_path / "qb-portable"
    profile = exe_dir / "profile"
    (profile / "qBittorrent").mkdir(parents=True)
    other = tmp_path / "qb-portable2"
    (other / "profile" / "qBittorrent").mkdir(parents=True)

    def locator():
        return (str(exe_dir), str(exe_dir), str(other)), (f"便携 qBittorrent 进程 exe: {exe_dir}", )

    scan = probe.candidates(probe.PLATFORM_WINDOWS, env={}, home=tmp_path, exe_locator=locator)
    portable = [c for c in scan.candidates if c.origin == probe.ORIGIN_PORTABLE]
    assert [c.path for c in portable] == [
        str(profile / "qBittorrent" / "data" / "BT_backup"),
        str(other / "profile" / "qBittorrent" / "data" / "BT_backup"),
    ], "同 exe 目录重复出现须去重; 便携布局恒带 data 中间层"
    assert portable[0].note.startswith("便携 profile(exe:")
    assert any(exe_dir.name in line for line in scan.evidence if "进程 exe" in line)


def test_portable_locator_failure_is_evidence_line(tmp_path):
    def locator():
        return (), ("便携 exe 定位失败: PowerShell CIM 查询超时(>3s)(降级: 便携候选不参与, 手动键兜底)", )

    local = tmp_path / "Local"
    (tmp_path / "Roaming" / "qBittorrent").mkdir(parents=True)
    scan = probe.candidates(
        probe.PLATFORM_WINDOWS,
        env={
            "LOCALAPPDATA": str(local),
            "APPDATA": str(tmp_path / "Roaming")
        },
        home=tmp_path,
        exe_locator=locator,
    )
    assert [c.origin for c in scan.candidates] == [probe.ORIGIN_DEFAULT], "定位失败只丢便携面, 默认候选保留"
    assert any("定位失败" in line and "超时" in line for line in scan.evidence)


def test_portable_exe_without_profile_dir_skipped(tmp_path):
    exe_dir = tmp_path / "installed-qb"
    exe_dir.mkdir()

    def locator():
        return (str(exe_dir), ), ()

    scan = probe.candidates(probe.PLATFORM_WINDOWS, env={}, home=tmp_path, exe_locator=locator)
    assert all(c.origin != probe.ORIGIN_PORTABLE for c in scan.candidates), "非便携 exe 不产便携候选"
    assert any("无 profile/ 目录" in line and "非便携" in line for line in scan.evidence)


def test_posix_exe_scanner_via_proc(monkeypatch):
    targets = {"100": "/usr/bin/qbittorrent", "200": "/usr/bin/python3", "300": "/usr/bin/qbittorrent-nox"}

    def fake_listdir(path):
        assert path == probe.PROC_DIR
        return ["100", "200", "300", "self", "thread-self"]

    def fake_readlink(path):
        pid = path.split("/")[2]
        if pid == "300":
            raise PermissionError(pid)
        return targets[pid]

    monkeypatch.setattr(probe.os, "listdir", fake_listdir)
    monkeypatch.setattr(probe.os, "readlink", fake_readlink)
    dirs, evidence = probe._posix_portable_dirs()
    assert dirs == ("/usr/bin", )
    assert evidence == ("便携 qBittorrent 进程 exe: /usr/bin/qbittorrent", )


def test_posix_exe_scanner_failure_is_evidence(monkeypatch):
    def fake_listdir(path):
        raise OSError(2, "No such file or directory", path)

    monkeypatch.setattr(probe.os, "listdir", fake_listdir)
    dirs, evidence = probe._posix_portable_dirs()
    assert dirs == ()
    assert any("/proc 枚举失败" in line for line in evidence)


# ---- PowerShell CIM 查询(R6: UTF-8 钉码 + 超时守护 + 无注入面) ----


def test_powershell_query_pins_utf8_and_timeout(monkeypatch):
    exe = r"D:\Apps\qbittorrent.exe"
    calls = _install_run(monkeypatch, lambda cmd, kwargs, index: _cp(f"{exe}\n{exe}\n \n"))

    paths, err = probe._run_powershell_exe_query()

    assert (paths, err) == ((exe, ), "")
    cmd, kwargs = calls[0]
    assert cmd[0] == "powershell" and "-NoProfile" in cmd and "-NonInteractive" in cmd
    assert cmd[-1] == probe._WIN_EXE_SCRIPT
    assert "Get-CimInstance" in cmd[-1] and "Win32_Process" in cmd[-1]
    assert kwargs["encoding"] == "utf-8" and kwargs["errors"] == "replace", "R6: 两项必填, 缺一即 cp1252 前科"
    assert kwargs["text"] is True and kwargs["capture_output"] is True
    assert kwargs["timeout"] <= probe.WIN_EXE_TIMEOUT_S, "超时守护必须有界"


def test_powershell_query_has_no_injection_surface(monkeypatch, tmp_path):
    """env/home 注入恶意串也不得进命令串: 脚本恒等于编译期常量"""
    evil = "C:\\x' -Command Remove-Item -Path C:\\ -Recurse"
    (tmp_path / "Roaming" / "qBittorrent").mkdir(parents=True)
    calls = _install_run(monkeypatch, lambda cmd, kwargs, index: _cp(""))
    scan = probe.candidates(
        probe.PLATFORM_WINDOWS,
        env={
            "LOCALAPPDATA": evil,
            "APPDATA": evil
        },
        home=tmp_path,
        exe_locator=None,  # 走真实定位链 -> _run_powershell_exe_query
    )
    assert all(c.origin != probe.ORIGIN_PORTABLE for c in scan.candidates), "查询无输出 = 无进程 = 零便携候选"
    cmd, _ = calls[0]
    assert cmd[-1] == probe._WIN_EXE_SCRIPT
    assert evil not in cmd[-1] and "Remove-Item" not in cmd[-1], "调用方输入不得拼进命令串"


def test_powershell_query_failure_modes(monkeypatch):
    def timeout_handler(cmd, kwargs, index):
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    _install_run(monkeypatch, timeout_handler)
    assert probe._run_powershell_exe_query() == ((), f"PowerShell CIM 查询超时(>{probe.WIN_EXE_TIMEOUT_S:g}s)")

    def missing_handler(cmd, kwargs, index):
        raise FileNotFoundError(2, "not found", "powershell")

    _install_run(monkeypatch, missing_handler)
    paths, err = probe._run_powershell_exe_query()
    assert paths == () and "PowerShell 不可用" in err

    _install_run(monkeypatch, lambda cmd, kwargs, index: _cp("boom", returncode=2))
    paths, err = probe._run_powershell_exe_query()
    assert paths == () and "退出码 2" in err and "boom" in err


def test_win_portable_dirs_mixed_output(monkeypatch, tmp_path):
    """_win_portable_dirs 循环: 非绝对路径守卫 + exe->目录推导 + 同目录去重 + 逐 exe 证据行"""
    exe_a = tmp_path / "portable" / "qbittorrent.exe"
    exe_a2 = tmp_path / "portable" / "qbittorrent-enhanced.exe"  # 同目录双进程 -> 目录只留一份
    exe_b = tmp_path / "other" / "qbittorrent.exe"
    monkeypatch.setattr(
        probe,
        "_run_powershell_exe_query",
        lambda: ((str(exe_a), "qbittorrent.exe", str(exe_a2), str(exe_b)), ""),  # 第二条为异常相对路径形态
    )

    dirs, evidence = probe._win_portable_dirs()

    assert dirs == (str(tmp_path / "other"), str(tmp_path / "portable")), "仅绝对路径进入目录集, 同目录去重"
    assert any("非绝对路径(qbittorrent.exe)" in line and "跳过" in line for line in evidence)
    assert evidence.count(f"便携 qBittorrent 进程 exe: {exe_a}") == 1
    assert evidence.count(f"便携 qBittorrent 进程 exe: {exe_b}") == 1


# ---- 资格判定(qualify) ----


def test_qualify_fastresume_ids(tmp_path):
    d = tmp_path / "BT_backup"
    d.mkdir()
    (d / f"{V1.upper()}.fastresume").write_bytes(b"x")  # 大小写不敏感, 归一小写
    (d / f"{V1B}.fastresume").write_bytes(b"x")
    (d / "nothex.fastresume").write_bytes(b"x")  # 非 40hex 不计
    (d / f"{V1B}.torrent").write_bytes(b"x")  # .torrent 伴生文件不计
    (d / f"{V1}.fastresume.bak").write_bytes(b"x")  # 备份后缀不计
    sub = d / "sub"
    sub.mkdir()
    (sub / f"{V1}.fastresume").write_bytes(b"x")  # 子目录不计

    q = probe.qualify(d)

    assert q.qualified and q.has_queue is False
    assert q.fastresume_ids == {V1, V1B}
    assert q.reason == "fastresume x2"


def test_qualify_queue_file(tmp_path):
    d = tmp_path / "BT_backup"
    d.mkdir()
    (d / "queue").write_text(f"{V1}\n", encoding="utf-8")
    (d / "queue.bak").write_text("", encoding="utf-8")  # 精确同名才认

    q = probe.qualify(d)

    assert q.qualified and q.has_queue and q.fastresume_ids == frozenset()
    assert q.reason == "queue"


def test_qualify_empty_or_missing_dir(tmp_path, monkeypatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    q_empty = probe.qualify(empty)
    assert not q_empty.qualified and q_empty.fastresume_ids == frozenset() and not q_empty.has_queue
    assert "空目录" in q_empty.reason

    q_missing = probe.qualify(tmp_path / "nope")
    assert not q_missing.qualified and "目录不存在" in q_missing.reason

    a_file = tmp_path / "a.txt"
    a_file.write_text("x", encoding="utf-8")
    q_file = probe.qualify(a_file)
    assert not q_file.qualified and "目录不存在" in q_file.reason, "路径存在但不是目录同按不存在处置"

    def boom(path):
        raise PermissionError(13, "denied", str(path))

    monkeypatch.setattr(os, "scandir", boom)
    q_denied = probe.qualify(empty)
    assert not q_denied.qualified and "目录不可读" in q_denied.reason


# ---- hash 自证(v1 + v2trunc 双算, R2) ----


def test_torrent_ids_double_count_v1_and_v2trunc():
    assert probe.torrent_ids_from_infohashes(V1, V2_64) == {V1, V2TRUNC}, "双算两种命名世代"
    assert probe.torrent_ids_from_infohashes(V1, "") == {V1}, "v1-only 只有 v1"
    assert probe.torrent_ids_from_infohashes("", V2_64) == {V2TRUNC}, "纯 v2 取截断"
    assert probe.torrent_ids_from_infohashes("  " + V1.upper() + "  ", V2_64) == {V1, V2TRUNC}, "归一大小写空白"
    assert probe.torrent_ids_from_infohashes("xyz", "short") == frozenset(), "畸形输入跳过不猜"
    assert probe.torrent_ids_from_infohashes() == frozenset()


def test_torrent_id_set_batch():
    pairs = [(V1, V2_64), (V1B, ""), ("", ""), ("bad", V2_64[:39] + "g")]
    assert probe.torrent_id_set(pairs) == {V1, V2TRUNC, V1B}


def test_verify_intersects_fastresume_names(tmp_path):
    d = tmp_path / "BT_backup"
    d.mkdir()
    (d / f"{V1}.fastresume").write_bytes(b"x")
    (d / f"{V2TRUNC}.fastresume").write_bytes(b"x")
    q = probe.qualify(d)
    matches = probe.verify({V1.upper(), "  " + V2TRUNC + "  ", V1B}, [q])
    assert matches[0].path == str(d)
    assert matches[0].matched_ids == {V1, V2TRUNC}


def test_verify_hybrid_44x_v1_named(tmp_path):
    """4.4.x hybrid 以 v1 命名: 双算集合中的 v1 侧命中(R2 兜底形态)"""
    d = tmp_path / "BT_backup"
    d.mkdir()
    (d / f"{V1}.fastresume").write_bytes(b"x")
    q = probe.qualify(d)
    matches = probe.verify(probe.torrent_ids_from_infohashes(V1, V2_64), [q])
    assert matches[0].matched_ids == {V1}


# ---- 五态裁决(verdict) ----


def test_verdict_hit_single_qualified_online_verified():
    scan = _scan("C:\\bt")
    quals = [_qual("C:\\bt", V1, V2TRUNC)]
    matches = probe.verify({V1}, quals)

    result = probe.verdict(scan, qualifications=quals, matches=matches, storage_type="Legacy", online=True)

    assert result.state == probe.VERDICT_HIT
    assert "hash 自证通过" in result.reason
    assert result.candidates[0].hash_matched and result.candidates[0].fastresume_count == 2


def test_verdict_hit_single_qualified_offline():
    result = probe.verdict(_scan("C:\\bt"), qualifications=[_qual("C:\\bt", V1)], online=False)

    assert result.state == probe.VERDICT_HIT
    assert "离线" in result.reason and "未自证" in result.reason
    assert any("离线未自证" in line for line in result.notes)
    assert any("SQLite 存储模式未排除" in line for line in result.notes)


def test_verdict_hit_single_qualified_online_zero_intersection():
    scan = _scan("C:\\bt")
    quals = [_qual("C:\\bt", V1)]
    matches = probe.verify({V1B}, quals)  # 在线但交集为 0: 候选可能属于其他实例

    result = probe.verdict(scan, qualifications=quals, matches=matches, online=True)

    assert result.state == probe.VERDICT_HIT, "hit 判据 = 恰一个合格; 交集是加分自证不是门槛"
    assert "交集为 0" in result.reason and "未自证" in result.reason


def test_verdict_disambiguation_by_hash():
    scan = _scan("C:\\a", "C:\\b")
    quals = [_qual("C:\\a", V1), _qual("C:\\b", V1B)]
    matches = probe.verify({V1B}, quals)

    result = probe.verdict(scan, qualifications=quals, matches=matches, online=True)

    assert result.state == probe.VERDICT_HIT
    assert "消歧命中唯一" in result.reason and "C:\\b" in result.reason


def test_verdict_ambiguous_multiple_hash_hits():
    scan = _scan("C:\\a", "C:\\b")
    quals = [_qual("C:\\a", V1), _qual("C:\\b", V1B)]
    matches = probe.verify({V1, V1B}, quals)

    result = probe.verdict(scan, qualifications=quals, matches=matches, online=True)

    assert result.state == probe.VERDICT_AMBIGUOUS
    assert "无法消歧" in result.reason and "D5" in result.reason


def test_verdict_ambiguous_structure_only():
    scan = _scan("C:\\a", "C:\\b")
    quals = [_qual("C:\\a", V1), _qual("C:\\b", V1B, has_queue=True)]

    result = probe.verdict(scan, qualifications=quals, matches=(), online=False)

    assert result.state == probe.VERDICT_AMBIGUOUS
    assert "结构自证" in result.reason
    assert all(not r.hash_matched for r in result.candidates), "离线时交集证据一律为空"


def test_verdict_miss_zero_qualified(tmp_path):
    scan = _scan(str(tmp_path / "missing"), str(tmp_path / "empty"))
    quals = [probe.qualify(p) for p in (tmp_path / "missing", tmp_path / "empty")]

    result = probe.verdict(scan, qualifications=quals, online=True, storage_type="Legacy")

    assert result.state == probe.VERDICT_MISS
    assert "零合格候选" in result.reason and "共扫描 2 个" in result.reason
    assert any("目录不存在" in r.qualification_reason for r in result.candidates)


def test_verdict_unusable_sqlite_before_manual_set():
    scan = _scan("C:\\bt")
    quals = [_qual("C:\\bt", V1)]

    for raw in ("SQLite", "sqlite", 1, "1"):
        result = probe.verdict(scan, qualifications=quals, manual_set=True, storage_type=raw, online=True)
        assert result.state == probe.VERDICT_UNUSABLE_SQLITE, raw
        assert "非主存储" in result.reason
    for raw in ("Legacy", "legacy", 0, "", None):
        result = probe.verdict(scan, qualifications=quals, manual_set=True, storage_type=raw, online=True)
        assert result.state == probe.VERDICT_MANUAL_SET, raw


def test_verdict_manual_set_short_circuits_hit():
    scan = _scan("C:\\bt")
    quals = [_qual("C:\\bt", V1)]
    matches = probe.verify({V1}, quals)

    result = probe.verdict(scan, qualifications=quals, matches=matches, manual_set=True, online=True)

    assert result.state == probe.VERDICT_MANUAL_SET
    assert "仅供核对" in result.reason
    assert result.candidates[0].hash_matched, "证据保留, 供核对展示"


def test_verdict_offline_ignores_matches():
    scan = _scan("C:\\a", "C:\\b")
    quals = [_qual("C:\\a", V1), _qual("C:\\b", V1B)]
    matches = probe.verify({V1B}, quals)  # 调用方矛盾输入: offline 却给了非空交集

    result = probe.verdict(scan, qualifications=quals, matches=matches, online=False)

    assert result.state == probe.VERDICT_AMBIGUOUS, "离线时交集不得参与消歧(机械忽略)"
    assert all(not r.hash_matched for r in result.candidates)


def test_verdict_unknown_storage_value_noted():
    result = probe.verdict(_scan("C:\\bt"), qualifications=[_qual("C:\\bt", V1)], storage_type="2", online=True)
    assert result.state == probe.VERDICT_HIT
    assert any("非 Legacy 已知值" in line and "fail-closed" in line for line in result.notes)


def test_verdict_reports_join_by_path(tmp_path):
    """verdict 的真 FS 面只有 qualify 一处, 全走 tmp_path; C:\\ 路径标签永不触碰真机"""
    empty = tmp_path / "empty"
    empty.mkdir()
    scan = _scan("C:\\hit", str(empty), "C:\\noqual")
    quals = [_qual("C:\\hit", V1, has_queue=True), probe.qualify(empty)]
    matches = probe.verify({V1}, quals)

    result = probe.verdict(scan, qualifications=quals, matches=matches, online=True, storage_type="Legacy")

    by_path = {r.path: r for r in result.candidates}
    hit = by_path["C:\\hit"]
    assert hit.qualified and hit.has_queue and hit.hash_matched and hit.matched_ids == (V1, )
    assert hit.origin == probe.ORIGIN_DEFAULT and hit.suffix == ""
    assert by_path[str(empty)].qualified is False and by_path[str(empty)].fastresume_count == 0
    assert by_path["C:\\noqual"].qualification_reason.startswith("未判定")


def test_end_to_end_synthetic_matrix(tmp_path):
    """推导+资格+自证+裁决全链路: win 默认 profile 命中回填场景(G5 的合成预演)"""
    local = tmp_path / "Local"
    roaming = tmp_path / "Roaming"
    backup = local / "qBittorrent" / "BT_backup"
    backup.mkdir(parents=True)
    (backup / f"{V1}.fastresume").write_bytes(b"x")
    (backup / f"{V2TRUNC}.fastresume").write_bytes(b"x")
    (backup / "queue").write_text(f"{V1}\n{V2TRUNC}\n", encoding="utf-8")
    (roaming / "qBittorrent").mkdir(parents=True)

    scan = probe.candidates(
        probe.PLATFORM_WINDOWS,
        env={
            "LOCALAPPDATA": str(local),
            "APPDATA": str(roaming)
        },
        home=tmp_path,
        exe_locator=_no_portable,
    )
    quals = [probe.qualify(c.path) for c in scan.candidates]
    matches = probe.verify(probe.torrent_id_set([(V1, V2_64)]), quals)
    result = probe.verdict(
        scan,
        qualifications=quals,
        matches=matches,
        manual_set=False,
        storage_type="Legacy",
        online=True,
    )

    assert result.state == probe.VERDICT_HIT
    assert quals[0].reason == "fastresume x2 + queue"
    assert result.candidates[0].matched_ids == (V1, V2TRUNC)
    assert any("探测覆盖面" in line for line in result.notes)
