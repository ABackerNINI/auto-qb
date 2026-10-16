"""S5 守阵: 自启 installer 三平台幂等注册/卸载 (平台命令层 mock, 全 hermetic).

覆盖计划 §04 S5 出口判据: 三平台注册/卸载/重复注册(幂等) + 不支持平台的明确提示。
真机侧 (Windows 计划任务真的注册并拉起来) 走冒烟, 不进本文件 —— 本文件一行都不碰真机:
平台命令全部经注入的 FakeRunner, 文件系统根全部经 tmp_path。

设计单点: memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html (S5)。
"""

from __future__ import annotations

import os
import plistlib
import sys
from pathlib import Path

import pytest

from gtm import __main__ as gtm_main
from gtm.installer import (
    ACTION_ABSENT,
    ACTION_REGISTERED,
    ACTION_SKIPPED,
    ACTION_UNREGISTERED,
    DEFAULT_LAUNCHD_LABEL,
    DEFAULT_SYSTEMD_UNIT,
    DEFAULT_WINDOWS_TASK,
    PLATFORM_LINUX,
    PLATFORM_MACOS,
    PLATFORM_WINDOWS,
    AutostartError,
    AutostartPlan,
    AutostartResult,
    CommandResult,
    LaunchdBackend,
    SystemdUserBackend,
    UnsupportedPlatformError,
    WindowsTaskBackend,
    _decode,
    build_installer,
    default_runner,
    detect_platform,
    platform_from_sys,
)

EXE = sys.executable  # 真实存在 -> 过 build_installer 的解释器存在性检查


class FakeRunner:
    """平台命令替身: 全部调用留痕, 退出码按 handler 决定 (默认全 0)."""
    def __init__(self, handler=None):
        self.calls: list[list[str]] = []
        self._handler = handler or (lambda argv: CommandResult(0, "", ""))

    def __call__(self, argv):
        argv = list(argv)
        self.calls.append(argv)
        out = self._handler(argv)
        return out if isinstance(out, CommandResult) else CommandResult(out, "", f"rc={out}")

    def heads(self) -> list[str]:
        return [c[0] for c in self.calls]

    def only(self, head: str) -> list[list[str]]:
        return [c for c in self.calls if c[0] == head]


def make_plan(data_dir, exe=EXE) -> AutostartPlan:
    return AutostartPlan(python_exe=exe, data_dir=os.path.abspath(str(data_dir)))


def rc_handler(mapping, default=0):
    """argv[0] -> 退出码 的 handler (未列出的命令取 default)."""
    def handler(argv):
        return mapping.get(argv[0], default)

    return handler


def make_win(data_dir, runner):
    return WindowsTaskBackend(make_plan(data_dir), runner)


def make_linux(data_dir, runner, home):
    return SystemdUserBackend(make_plan(data_dir), runner, home=str(home))


def make_macos(data_dir, runner, home, uid=501):
    return LaunchdBackend(make_plan(data_dir), runner, home=str(home), uid=uid)


# ---- 平台探测与装配 ----


def test_platform_from_sys_maps_three_platforms():
    """win32/linux/darwin 映射到三个内部平台名."""
    assert platform_from_sys("win32") == PLATFORM_WINDOWS
    assert platform_from_sys("linux") == PLATFORM_LINUX
    assert platform_from_sys("darwin") == PLATFORM_MACOS


@pytest.mark.parametrize("value", ["freebsd12", "cygwin", "emscripten", "aix"])
def test_platform_from_sys_rejects_unsupported_with_clear_hint(value):
    """不支持的平台给出明确提示 (含原始平台名与支持清单), 不是静默跳过."""
    with pytest.raises(UnsupportedPlatformError) as ei:
        platform_from_sys(value)
    msg = str(ei.value)
    assert value in msg and "Windows" in msg and "macOS" in msg


def test_detect_platform_agrees_with_sys_platform():
    """生产探测口径 = sys.platform 的映射 (本机真实平台)."""
    assert detect_platform() == platform_from_sys(sys.platform)


def test_build_installer_rejects_unsupported_platform():
    """build_installer 对未知平台名 fail-fast (不落到默认后端)."""
    with pytest.raises(UnsupportedPlatformError):
        build_installer("x", platform="freebsd", python_exe=EXE, home="x")


def test_build_installer_rejects_missing_interpreter(tmp_path):
    """解释器不存在 -> 拒绝注册 (免得自启项指向跑不起来的命令)."""
    with pytest.raises(AutostartError) as ei:
        build_installer("x", platform=PLATFORM_WINDOWS, python_exe=str(tmp_path / "nope" / "python.exe"))
    assert "解释器不存在" in str(ei.value)


def test_build_installer_resolves_data_dir_to_absolute(tmp_path, monkeypatch):
    """data_dir 解析成绝对路径写死进注册项 (自启拉起不依赖环境变量)."""
    monkeypatch.chdir(tmp_path)
    backend = build_installer("rel/data", platform=PLATFORM_WINDOWS, python_exe=EXE, runner=FakeRunner())
    assert backend.plan.data_dir == os.path.join(str(tmp_path), "rel", "data")


def test_build_installer_picks_backend_per_platform(tmp_path):
    """平台 -> 后端类型 (三平台各一)."""
    runner = FakeRunner()
    assert isinstance(
        build_installer("d", platform=PLATFORM_WINDOWS, python_exe=EXE, runner=runner),
        WindowsTaskBackend,
    )
    assert isinstance(
        build_installer("d", platform=PLATFORM_LINUX, python_exe=EXE, home=str(tmp_path), runner=runner),
        SystemdUserBackend,
    )
    assert isinstance(
        build_installer("d", platform=PLATFORM_MACOS, python_exe=EXE, home=str(tmp_path), uid=501, runner=runner),
        LaunchdBackend,
    )


# ---- Windows: schtasks ----


def test_windows_register_creates_onlogon_task(tmp_path):
    """未注册 -> schtasks /Create /SC ONLOGON /TR <引号命令>; 先查后建."""
    runner = FakeRunner(lambda argv: 1 if "/Query" in argv else 0)
    data_dir = str(tmp_path / "data")
    result = make_win(data_dir, runner).register()

    assert result.action == ACTION_REGISTERED and result.changed
    assert runner.calls == [
        ["schtasks", "/Query", "/TN", DEFAULT_WINDOWS_TASK],
        [
            "schtasks",
            "/Create",
            "/TN",
            DEFAULT_WINDOWS_TASK,
            "/SC",
            "ONLOGON",
            "/TR",
            f'"{EXE}" -m gtm run --data-dir "{data_dir}"',
            "/F",
        ],
    ]


def test_windows_register_skips_when_task_exists(tmp_path):
    """已存在 -> 跳过, 一条 /Create 都不发 (计划「注册前检查存在则跳过」)."""
    runner = FakeRunner(lambda argv: 0)  # Query 命中
    result = make_win(tmp_path, runner).register()

    assert result.action == ACTION_SKIPPED and not result.changed
    assert runner.only("schtasks") == [["schtasks", "/Query", "/TN", DEFAULT_WINDOWS_TASK]]


def test_windows_register_twice_is_idempotent(tmp_path):
    """重复注册幂等: 第二次跳过, 全程只有一条 /Create (任务不重复)."""
    created = {"n": 0}

    def handler(argv):
        if "/Create" in argv:
            created["n"] += 1
            return 0
        return 0 if created["n"] else 1  # 建过之后 Query 才命中

    runner = FakeRunner(handler)
    backend = make_win(tmp_path, runner)
    first = backend.register()
    second = backend.register()

    assert first.action == ACTION_REGISTERED
    assert second.action == ACTION_SKIPPED
    assert len([c for c in runner.calls if "/Create" in c]) == 1
    assert created["n"] == 1


def test_windows_unregister_absent_is_noop(tmp_path):
    """本来就没注册 -> absent, 不发 /Delete."""
    runner = FakeRunner(lambda argv: 1)
    result = make_win(tmp_path, runner).unregister()

    assert result.action == ACTION_ABSENT and not result.changed
    assert [c for c in runner.calls if "/Delete" in c] == []


def test_windows_unregister_deletes_task(tmp_path):
    """已注册 -> /Delete /F, 结果为 unregistered."""
    runner = FakeRunner(lambda argv: 0)
    result = make_win(tmp_path, runner).unregister()

    assert result.action == ACTION_UNREGISTERED and result.changed
    assert runner.calls[-1] == ["schtasks", "/Delete", "/TN", DEFAULT_WINDOWS_TASK, "/F"]


def test_windows_create_failure_raises_with_output(tmp_path):
    """schtasks /Create 非 0 -> AutostartError, 附注平台输出 (不静默)."""
    runner = FakeRunner(
        lambda argv: CommandResult(1, "", "错误: 拒绝访问。") if "/Create" in argv else CommandResult(1, "", "")
    )
    with pytest.raises(AutostartError) as ei:
        make_win(tmp_path, runner).register()
    assert "schtasks /Create" in str(ei.value) and "拒绝访问" in str(ei.value)


def test_windows_missing_command_is_reported(tmp_path):
    """本机没有 schtasks (命令缺失) -> AutostartError 明说找不到命令."""
    def boom(argv):
        raise FileNotFoundError(argv[0])

    with pytest.raises(AutostartError) as ei:
        make_win(tmp_path, FakeRunner(boom)).register()
    assert "找不到命令" in str(ei.value)


def test_windows_tr_quotes_paths_with_spaces(tmp_path):
    """python 路径与 data_dir 含空格时 TR 仍是一个可解析的命令行 (各自带引号)."""
    plan = AutostartPlan(
        python_exe="C:/Program Files/gtm/.venv/Scripts/python.exe",
        data_dir="C:/my data/gtm",
    )
    assert plan.windows_command(
    ) == ('"C:/Program Files/gtm/.venv/Scripts/python.exe" -m gtm run --data-dir "C:/my data/gtm"')
    assert plan.daemon_argv() == [
        "C:/Program Files/gtm/.venv/Scripts/python.exe",
        "-m",
        "gtm",
        "run",
        "--data-dir",
        "C:/my data/gtm",
    ]


# ---- Linux: systemd --user ----


def test_linux_register_writes_unit_and_enables(tmp_path):
    """首次注册: 写单元文件 -> daemon-reload -> enable --now."""
    runner = FakeRunner()
    backend = make_linux(tmp_path / "d", runner, tmp_path)
    result = backend.register()

    assert result.action == ACTION_REGISTERED
    assert runner.calls == [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", DEFAULT_SYSTEMD_UNIT],
    ]
    unit = Path(backend.target)
    assert unit.is_file()
    text = unit.read_text(encoding="utf-8")
    exec_lines = [line for line in text.splitlines() if line.startswith("ExecStart=")]
    assert len(exec_lines) == 1
    assert exec_lines[0].startswith("ExecStart=") and "-m gtm run --data-dir" in exec_lines[0]
    assert os.path.abspath(str(tmp_path / "d")) in exec_lines[0]
    assert "WantedBy=default.target" in text and "Restart=on-failure" in text


def test_linux_execstart_quotes_paths_with_spaces(tmp_path):
    """ExecStart 对含空格的路径逐段加引号 (systemd 解析所需)."""
    plan = AutostartPlan(
        python_exe="C:/Program Files/py/python.exe",
        data_dir="C:/my data/gtm",
    )
    unit = SystemdUserBackend(plan, FakeRunner(), home=str(tmp_path)).render_unit()

    assert ('ExecStart="C:/Program Files/py/python.exe" -m gtm run --data-dir "C:/my data/gtm"' in unit)


def test_linux_unit_is_lf_and_utf8(tmp_path):
    """单元文件是生成物: UTF-8 无 BOM + LF (Windows 上也不会被写成 CRLF)."""
    runner = FakeRunner()
    backend = make_linux(tmp_path / "d", runner, tmp_path)
    backend.register()
    raw = Path(backend.target).read_bytes()

    assert b"\r\n" not in raw
    assert not raw.startswith(b"\xef\xbb\xbf")
    raw.decode("utf-8")  # 不抛即 UTF-8 合法


def test_linux_register_second_time_skips(tmp_path):
    """内容一致 + 已启用 -> 跳过, 一条 systemctl 都不发."""
    first = FakeRunner()
    backend = make_linux(tmp_path / "d", first, tmp_path)
    backend.register()

    second = FakeRunner(rc_handler({"systemctl": 0}))  # is-enabled 命中
    backend2 = make_linux(tmp_path / "d", second, tmp_path)
    result = backend2.register()

    assert result.action == ACTION_SKIPPED and not result.changed
    assert second.calls == [["systemctl", "--user", "is-enabled", DEFAULT_SYSTEMD_UNIT]]


def test_linux_register_reenables_when_disabled(tmp_path):
    """文件一致但服务被 disable -> 收敛: 不重写文件, 重新 enable --now.

    (只查「文件存在」的判据会在这里谎报成功 —— 这正是判据取完整期望态的理由.)
    """
    make_linux(tmp_path / "d", FakeRunner(), tmp_path).register()
    unit = Path(tmp_path) / ".config" / "systemd" / "user" / DEFAULT_SYSTEMD_UNIT
    before = unit.read_bytes()

    runner = FakeRunner(lambda argv: 1 if "is-enabled" in argv else 0)
    result = make_linux(tmp_path / "d", runner, tmp_path).register()

    assert result.action == ACTION_REGISTERED
    assert unit.read_bytes() == before  # 未重写
    assert runner.calls == [
        ["systemctl", "--user", "is-enabled", DEFAULT_SYSTEMD_UNIT],
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", DEFAULT_SYSTEMD_UNIT],
    ]
    assert "未变" in result.message


def test_linux_register_rewrites_drifted_unit(tmp_path):
    """单元文件被改坏/参数过期 -> 收敛回期望内容."""
    make_linux(tmp_path / "d", FakeRunner(), tmp_path).register()
    unit = Path(tmp_path) / ".config" / "systemd" / "user" / DEFAULT_SYSTEMD_UNIT
    unit.write_text("# drifted\n", encoding="utf-8")

    backend = make_linux(tmp_path / "d", FakeRunner(), tmp_path)
    result = backend.register()

    assert result.action == ACTION_REGISTERED
    assert unit.read_text(encoding="utf-8") == backend.render_unit()
    assert "已重写单元内容" in result.message


def test_linux_unregister_absent_is_noop(tmp_path):
    """单元文件不存在 -> absent, 一条 systemctl 都不发."""
    runner = FakeRunner()
    result = make_linux(tmp_path / "d", runner, tmp_path).unregister()

    assert result.action == ACTION_ABSENT and not result.changed
    assert runner.calls == []


def test_linux_unregister_removes_unit_and_reloads(tmp_path):
    """卸载: disable --now -> 删单元 -> daemon-reload."""
    backend = make_linux(tmp_path / "d", FakeRunner(), tmp_path)
    backend.register()
    unit = Path(backend.target)

    runner = FakeRunner()
    result = make_linux(tmp_path / "d", runner, tmp_path).unregister()

    assert result.action == ACTION_UNREGISTERED and result.changed
    assert not unit.exists()
    assert runner.calls == [
        ["systemctl", "--user", "disable", "--now", DEFAULT_SYSTEMD_UNIT],
        ["systemctl", "--user", "daemon-reload"],
    ]


def test_linux_unregister_tolerates_disable_failure(tmp_path):
    """disable 非 0 (如单元未加载) 不阻断卸载: 文件仍删, 原因写进结论."""
    backend = make_linux(tmp_path / "d", FakeRunner(), tmp_path)
    backend.register()
    unit = Path(backend.target)

    runner = FakeRunner(lambda argv: 1 if "disable" in argv else 0)
    result = make_linux(tmp_path / "d", runner, tmp_path).unregister()

    assert result.action == ACTION_UNREGISTERED
    assert not unit.exists()
    assert "WARN" in result.message


def test_linux_enable_failure_raises(tmp_path):
    """enable --now 非 0 -> AutostartError (不静默留个没启用的单元)."""
    runner = FakeRunner(lambda argv: 1 if "enable" in argv else 0)
    with pytest.raises(AutostartError) as ei:
        make_linux(tmp_path / "d", runner, tmp_path).register()
    assert "enable --now" in str(ei.value)


# ---- macOS: launchd ----


def test_macos_register_writes_plist_and_bootstraps(tmp_path):
    """首次注册: 写 plist (ProgramArguments = 守护 argv) -> launchctl bootstrap."""
    runner = FakeRunner(lambda argv: 1 if argv[0] == "launchctl" and argv[1] == "print" else 0)
    backend = make_macos(tmp_path / "d", runner, tmp_path, uid=501)
    result = backend.register()

    assert result.action == ACTION_REGISTERED
    payload = plistlib.loads(Path(backend.target).read_bytes())
    assert payload["Label"] == DEFAULT_LAUNCHD_LABEL
    assert payload["ProgramArguments"] == backend.plan.daemon_argv()
    assert payload["RunAtLoad"] is True and payload["KeepAlive"] is True
    assert runner.calls == [
        ["launchctl", "print", f"gui/501/{DEFAULT_LAUNCHD_LABEL}"],
        ["launchctl", "bootstrap", "gui/501", backend.target],
    ]


def test_macos_register_second_time_skips(tmp_path):
    """plist 一致 + 已加载 -> 跳过, 只发生一次 print 探测."""
    make_macos(tmp_path / "d", FakeRunner(), tmp_path).register()

    runner = FakeRunner(lambda argv: 0)  # print 命中 (已加载)
    result = make_macos(tmp_path / "d", runner, tmp_path).register()

    assert result.action == ACTION_SKIPPED and not result.changed
    assert runner.calls == [["launchctl", "print", f"gui/501/{DEFAULT_LAUNCHD_LABEL}"]]


def test_macos_register_reloads_on_drift(tmp_path):
    """已加载但 plist 与期望不一致 -> bootout 旧 -> 重写 -> bootstrap."""
    backend = make_macos(tmp_path / "d", FakeRunner(), tmp_path)
    backend.register()
    Path(backend.target).write_bytes(b"<plist/>")

    runner = FakeRunner(lambda argv: 0)  # print 命中 (已加载)
    result = make_macos(tmp_path / "d", runner, tmp_path).register()

    assert result.action == ACTION_REGISTERED
    assert runner.calls[0] == ["launchctl", "print", f"gui/501/{DEFAULT_LAUNCHD_LABEL}"]
    assert runner.calls[1] == ["launchctl", "bootout", f"gui/501/{DEFAULT_LAUNCHD_LABEL}"]
    assert runner.calls[2] == ["launchctl", "bootstrap", "gui/501", backend.target]
    assert plistlib.loads(Path(backend.target).read_bytes()) == plistlib.loads(backend.render_plist())


def test_macos_unregister_absent_is_noop(tmp_path):
    """plist 不存在 -> absent, 一条 launchctl 都不发."""
    runner = FakeRunner()
    result = make_macos(tmp_path / "d", runner, tmp_path).unregister()

    assert result.action == ACTION_ABSENT
    assert runner.calls == []


def test_macos_unregister_removes_plist(tmp_path):
    """卸载: bootout -> 删 plist."""
    backend = make_macos(tmp_path / "d", FakeRunner(), tmp_path)
    backend.register()
    path = Path(backend.target)

    runner = FakeRunner()
    result = make_macos(tmp_path / "d", runner, tmp_path).unregister()

    assert result.action == ACTION_UNREGISTERED
    assert not path.exists()
    assert runner.calls == [["launchctl", "bootout", f"gui/501/{DEFAULT_LAUNCHD_LABEL}"]]


def test_macos_unregister_tolerates_bootout_failure(tmp_path):
    """bootout 非 0 不阻断卸载: plist 仍删, 原因写进结论."""
    backend = make_macos(tmp_path / "d", FakeRunner(), tmp_path)
    backend.register()

    runner = FakeRunner(lambda argv: 1)
    result = make_macos(tmp_path / "d", runner, tmp_path).unregister()

    assert result.action == ACTION_UNREGISTERED
    assert not Path(backend.target).exists()
    assert "WARN" in result.message


# ---- 命令层 (生产 runner 与解码兜底链) ----


def test_default_runner_real_subprocess_roundtrip():
    """生产 runner: 真起子进程收字节自解, 退出码与 stdout 都对."""
    r = default_runner([EXE, "-c", "print('ok')"])
    assert r.returncode == 0 and r.stdout.strip() == "ok"


def test_default_runner_reports_nonzero():
    """生产 runner 非 0 退出码原样上报 (语义只认退出码)."""
    r = default_runner([EXE, "-c", "import sys; sys.exit(3)"])
    assert r.returncode == 3


def test_decode_fallback_chain_never_raises():
    """解码兜底链: UTF-8 优先, 非 UTF-8 字节 (本地码页/GBK) 不抛."""
    assert _decode("已注册".encode("utf-8")) == "已注册"
    assert isinstance(_decode(b"\xd2\xd1\xc9\xfa"), str)  # GBK 字节, 任一路径都得给出 str


# ---- CLI ----


class StubBackend:
    def __init__(self, result=None, exc=None):
        self.result = result
        self.exc = exc
        self.calls: list[str] = []

    def _do(self, name):
        self.calls.append(name)
        if self.exc:
            raise self.exc
        return self.result

    def register(self):
        return self._do("register")

    def unregister(self):
        return self._do("unregister")


def test_cli_parser_exposes_autostart_subcommands():
    """两个子命令在解析面上 (install 带 --data-dir, uninstall 不带)."""
    parser = gtm_main.build_parser()
    assert parser.parse_args(["install-autostart", "--data-dir", "D:/x"]).data_dir == "D:/x"
    assert parser.parse_args(["uninstall-autostart"]).command == "uninstall-autostart"


def test_cli_install_autostart_prints_message_and_exits_zero(monkeypatch, capsys):
    """成功路径: 结论打到 stdout, 退出码 0."""
    stub = StubBackend(result=AutostartResult(ACTION_REGISTERED, "已注册开机自启: 计划任务 'gtm-autostart'"))
    monkeypatch.setattr(gtm_main, "build_installer", lambda data_dir: stub)
    assert gtm_main.main(["install-autostart"]) == 0
    assert stub.calls == ["register"]
    assert "已注册开机自启" in capsys.readouterr().out


def test_cli_uninstall_autostart_calls_unregister(monkeypatch, capsys):
    """卸载路径走 unregister (不是 register)."""
    stub = StubBackend(result=AutostartResult(ACTION_ABSENT, "自启未注册, 无需卸载"))
    monkeypatch.setattr(gtm_main, "build_installer", lambda data_dir: stub)
    assert gtm_main.main(["uninstall-autostart"]) == 0
    assert stub.calls == ["unregister"]


def test_cli_passes_data_dir_to_installer(monkeypatch):
    """--data-dir 透传到 build_installer (自启项写死的就是它)."""
    seen = {}
    stub = StubBackend(result=AutostartResult(ACTION_SKIPPED, "已注册, 跳过"))

    def fake_build(data_dir):
        seen["data_dir"] = data_dir
        return stub

    monkeypatch.setattr(gtm_main, "build_installer", fake_build)
    assert gtm_main.main(["install-autostart", "--data-dir", "D:/tmp/gtm-data"]) == 0
    assert seen["data_dir"] == "D:/tmp/gtm-data"


def test_cli_unsupported_platform_exits_two(monkeypatch, capsys):
    """平台不支持 -> 退出码 2 + 明确提示 (S6 设置页据此区分「不支持」与「失败」)."""
    def boom(data_dir):
        raise UnsupportedPlatformError("当前平台不支持自启注册: 'freebsd12' (仅支持 Windows / Linux / macOS)")

    monkeypatch.setattr(gtm_main, "build_installer", boom)
    assert gtm_main.main(["install-autostart"]) == 2
    err = capsys.readouterr().err
    assert "不支持自启注册" in err and "freebsd12" in err


def test_cli_installer_error_exits_one(monkeypatch, capsys):
    """平台命令失败 -> 退出码 1 + 错误打到 stderr."""
    stub = StubBackend(exc=AutostartError("schtasks /Create 失败 (rc=1): 拒绝访问"))
    monkeypatch.setattr(gtm_main, "build_installer", lambda data_dir: stub)
    assert gtm_main.main(["install-autostart"]) == 1
    err = capsys.readouterr().err
    assert "自启注册失败" in err and "拒绝访问" in err


def test_cli_build_error_exits_one(monkeypatch, capsys):
    """装配期失败 (如解释器不存在) 也走退出码 1 且不炸栈."""
    monkeypatch.setattr(gtm_main, "build_installer", lambda data_dir: (_ for _ in ()).throw(AutostartError("解释器不存在")))
    assert gtm_main.main(["uninstall-autostart"]) == 1
    assert "自启卸载失败" in capsys.readouterr().err
