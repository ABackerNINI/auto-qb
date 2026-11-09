"""test_utils_windows 测试计划: utils 工具函数

## 测试计划(每个测试函数一条)
- test_check_filelist_qb_transitional_twin_hint: 缺失且 .!qB 孪生存在 -> 文案含疑似过渡态提示(返回语义不变)
- test_qb_incomplete_twin_path: .!qB 后缀单点常量与孪生路径拼接(纯函数)
- test_os_platform_helpers: 平台判定(is_windows/is_linux/is_mac/is_posix)
- test_platform_detect_single_point_static_guard: 静态守阵(issue 26-10-11-0352-refactor-infra-platform-detect-bypass-dup)——src/ 全域禁止裸 sys.platform.startswith 另立判据, 平台判定只走 utils.is_* 单点(单点自身豁免)
- test_add_long_path_prefix_non_windows: 非 Windows 原样返回
- test_open_path_select_file_per_platform: open_path(select=True) 单文件定位选中(PIDL 不可用时 win explorer /select, · mac open -R · linux 退化父目录 · 非文件退化为普通打开)
- test_open_path_windows_long_path_uses_shell_pidl: Windows 长路径"进入目录"(enter)/"定位选中"走 Shell PIDL, 绝不触达 os.startfile 与 explorer
- test_open_path_windows_falls_back_to_string_route: PIDL 返回 False 时退回字符串路线(不静默什么都不做)
- test_open_path_non_windows_never_calls_shell_pidl: 非 Windows 平台绝不触达 PIDL 路线(防守阵假阳性)
- test_open_path_windows_schedules_foreground_bringup: Windows 打开后调度后台置前(参数 = 打开前快照 + 目录名), 非 Windows 不调度
- test_win_foreground_new_explorer_new_window: 快照差集命中新窗口 -> 抬到顶层
- test_win_foreground_new_explorer_reused_window_title_match: 无新窗口(复用已有窗口) -> 按标题匹配抬到顶层; 标题不匹配不置前
- test_win_explorer_hwnds_non_windows_empty: 非 Windows 快照恒空集(不碰 ctypes)
- test_win_wait_explorer_prefers_new_window_over_title_match: 新窗口优先于标题匹配的复用窗口; 两者都无 -> None(超时)
- test_win_force_foreground_zorder_raised_even_when_focus_denied: 取焦被前台锁拒绝时 Z 序提升照做 + SwitchToThisWindow 兜底
- test_win_force_foreground_true_when_focus_taken: 抢到焦点即返回 True, 不再走兜底硬切
- test_win_force_foreground_dead_hwnd_silent: 句柄已失效 -> 零 API 调用, 返回 False
- test_win_topmost_once_toggles_and_clears: TOPMOST 挂一下立刻摘 + SWP_NOACTIVATE(只动顺序不抢焦)
- test_win_force_foreground_retries_until_focus: 单次被拒后有封顶重试(不无限执念)
- test_win_user32_kernel32_non_windows_none: 非 Windows 上句柄取用返回 None(靠早退而非"恰好抛异常")
- test_win_dll_missing_windll_returns_none: 平台伪装 win32 但 ctypes 无 windll/WINFUNCTYPE(POSIX 实况)-> None 不抛错(签名工厂求值顺序守阵)
- test_win_user32_binds_signatures: 每个 user32 API 必须绑死 argtypes —— 不绑时 x64 传参静默失效(本轮真根因的守阵)
- test_win_shell_open_non_windows_returns_false: 非 Windows 上 _win_shell_open / _win_shell_enter 前置返回 False, 不碰 ctypes

### P1 覆盖率提升轮: infra 长尾
- test_win_shell_open_pidl_routes: PIDL 三分支(成功/解析失败/打开失败/COM 异常) + 前缀剥离 + 配对卸载
- test_win_shell_enter_pidl_routes: 进入目录经 ShellExecuteExW(结构体契约 fMask/lpVerb/PIDL/nShow/cbSize) + 失败降级 + 无导出兜底
- test_win_user32_and_kernel32_bind_signatures: user32/kernel32 惰性句柄绑定与缓存
- test_win_explorer_hwnds_and_topmost_and_switch: Explorer 枚举/TOPMOST 开关/SwitchToThisWindow + 失败静默
- test_win_force_foreground_matrix: 三层升级矩阵(还原/显示/焦点/借线程/硬切/异常)
- test_win_reuse_and_wait_explorer: 复用窗口标题匹配/差集新窗口/超时 None/置前重试封顶
  (本组 Shell 测试全部用假替身, 不碰真窗口; _win_shell_open 直调经 sidefx._saved 取回原函数避开记账假阳性;
   平台差异: 涉及 Windows 分支的用例一律 monkeypatch sys.platform, 并用 `_shim_posix_ctypes` 在 POSIX 上
   补 `ctypes.windll`/`WINFUNCTYPE` 门面 —— 否则 Linux CI 上必红; `_win_reuse_title_candidates` 另把
   utils 模块内的 os 固定为 ntpath)
- test_win_string_open_degrades_long_path_to_ancestor: 字符串路线遇超长路径上溯到最近的可达祖先
- test_win_shell_with_pidl_missing_windll_returns_false: ctypes 无 windll 门面 -> False 降级不抛错
- test_win_api_missing_attribute_silent: 四个 Windows 入口缺导出时静默降级(空集 / False / "" / False)
- test_win_force_foreground_skips_attach_when_no_foreground: 无前台窗口(0)时不借线程权限, 但取焦照发
- test_win_wait_explorer_no_title_candidates_skips_match: 复用标题候选为空集时跳过标题匹配, 超时即 None
- test_win_foreground_explorer_async_spawns_daemon_thread: 置前后台化线程真执行(Event 等, 不断言线程对象)
- test_win_shell_open_not_windows
"""

import hashlib

import ntpath

import os

import pytest

import sys

import tempfile

import threading

from pathlib import Path

from types import SimpleNamespace

from unittest import mock

from auto_qb.infra import utils

from auto_qb.core.modules.ops_mod import OpsModule

from helpers import FakeClient, FakeTorrent


def test_check_filelist_qb_transitional_twin_hint():
    """文件缺失但 <原名>.!qB 孪生存在 -> 文案追加疑似 qB 过渡态提示(返回语义不变, 仍非 None)"""
    with tempfile.TemporaryDirectory() as td:
        client = FakeClient()
        tor = FakeTorrent(hash="H1", name="Movie", save_path=td)
        client.files = [SimpleNamespace(name="movie.mkv", size=100)]
        with open(os.path.join(td, "movie.mkv.!qB"), "wb") as f:
            f.write(b"x" * 100)
        result = OpsModule.check_filelist(client, tor)
        assert result is not None, "孪生存在不改变返回语义(仍报缺失)"
        assert "文件缺失" in result
        assert "疑似 qB .!qB 过渡态" in result, f"应含过渡态提示(取证锚): {result}"

        # 对照: 无孪生 -> 纯缺失文案, 不带提示
        os.remove(os.path.join(td, "movie.mkv.!qB"))
        result2 = OpsModule.check_filelist(client, tor)
        assert result2 is not None and "文件缺失" in result2
        assert "过渡态" not in result2, f"无孪生不应带过渡态提示: {result2}"


def test_qb_incomplete_twin_path():
    """.!qB 后缀单点定义: QB_INCOMPLETE_SUFFIX 常量与 qb_incomplete_twin_path 拼接(纯字符串函数)"""
    assert utils.QB_INCOMPLETE_SUFFIX == ".!qB"
    assert utils.qb_incomplete_twin_path(r"D:/dl/movie.mkv") == r"D:/dl/movie.mkv.!qB"
    assert utils.qb_incomplete_twin_path("plain") == "plain.!qB"


def test_os_platform_helpers(monkeypatch):
    """平台判断: is_windows/is_linux/is_mac/is_posix 随 sys.platform 变化"""
    monkeypatch.setattr(sys, "platform", "win32")
    assert utils.is_windows()
    assert not utils.is_linux()
    assert not utils.is_mac()
    assert not utils.is_posix()

    monkeypatch.setattr(sys, "platform", "linux")
    assert utils.is_linux()
    assert not utils.is_windows()
    assert utils.is_posix()

    monkeypatch.setattr(sys, "platform", "darwin")
    assert utils.is_mac()
    assert not utils.is_windows()
    assert utils.is_posix()

    monkeypatch.setattr(sys, "platform", "freebsd")
    assert not utils.is_windows()
    assert utils.is_posix()  # BSD 属 Unix 类


def test_platform_detect_single_point_static_guard():
    """静态守阵(issue 26-10-11-0352-refactor-infra-platform-detect-bypass-dup): 平台判定单点

    `utils.is_windows/is_linux/is_mac/is_posix` 是「当前平台」事实的唯一口径 —— src/ 下
    任何模块不得再裸写 `sys.platform.startswith(...)` 另立判据: autostart.py 曾 6 处 +
    tray/app.py 1 处绕过单点, 且与单点的 "win" 前缀口径不一致(旁路写 "win32"), 新增平台
    分支时各处判断不一致。本守阵扫 src/ 全部 .py, 仅豁免单点自身(infra/utils.py 与
    R5 拆分后的 infra/utils_parse.py —— 平台判定定义的现居所);
    新旁路直接判红。notify.py 取 `sys.platform` 字符串值作平台标识(非 startswith 判据)不拦。
    """
    src_root = Path(__file__).resolve().parents[1] / "src"
    single_points = {
        src_root / "auto_qb" / "infra" / "utils.py",
        src_root / "auto_qb" / "infra" / "utils_parse.py",
    }
    offenders = []
    for path in sorted(src_root.rglob("*.py")):
        if path in single_points:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "sys.platform.startswith" in line:
                rel = path.relative_to(src_root.parent)
                offenders.append(f"{rel}:{lineno}")
    assert not offenders, f"平台判定应走 utils.is_*() 单点, 发现裸 sys.platform.startswith: {offenders}"


def test_add_long_path_prefix_non_windows(monkeypatch):
    """非 Windows 系统 -> 原样返回路径"""
    monkeypatch.setattr(sys, "platform", "linux")
    p = r"R:\Downloads\Movie"
    assert utils.add_long_path_prefix_for_win(p) == p


def _fake_windows(monkeypatch):
    """把宿主伪装成 Windows: 固定 `sys.platform` 并**中和长路径前缀**。

    宿主是 POSIX 时 `add_long_path_prefix_for_win` 会把 `\\\\?\\` 拼到 POSIX 路径上, 于是
    `os.path.isdir` 恒为 False —— 被测的是"平台分支逻辑"而不是"真在 Windows 上跑", 所以前缀
    在这里置成恒等(前缀本身的正确性由 `test_add_long_path_prefix_*` 三条单独覆盖)。
    """
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(utils, "add_long_path_prefix_for_win", lambda p: p)


def test_open_path_select_file_per_platform(tmp_path, monkeypatch):
    """open_path(select=True) 跨平台(R10-10): PIDL 不可用时 win explorer /select, · mac open -R · linux 退化父目录

    平台行为必须 monkeypatch sys.platform(CI 跑 Linux 而本项目以 Windows 为主);
    Windows 分支还要 patch `_win_shell_open`(PIDL 路线, 真调会弹资源管理器)与 `os.startfile`
    —— 后者在非 Windows 解释器上不存在, 故用 create=True。
    非文件目标 / 不存在目标一律退化为普通打开(动作类工具容错优先, 不抛错)。
    """
    f = tmp_path / "a.mkv"
    f.write_bytes(b"x")
    missing = tmp_path / "nope.mkv"

    # Windows: PIDL 路线不可用时退回 explorer /select,(打开父目录并选中该文件, 不是打开文件本身)
    # 置前调度一并 stub: 真跑会起后台线程去枚举/推前台真实窗口(测试期不得碰)
    _fake_windows(monkeypatch)
    with mock.patch.object(utils, "_win_shell_open", return_value=False), \
            mock.patch.object(utils, "_win_shell_enter", return_value=False), \
            mock.patch.object(utils, "_win_foreground_explorer_async"), \
            mock.patch.object(utils.os, "startfile", create=True) as sfile, \
            mock.patch.object(utils.subprocess, "run") as run:
        utils.open_path(str(f), select=True)
        assert sfile.call_count == 0
        run.assert_called_once_with(["explorer", "/select,", os.path.normpath(str(f))], check=False)
        # 目标不是文件(目录) -> 进入该目录(两个 PIDL 入口都不可用时退字符串路线)
        run.reset_mock()
        utils.open_path(str(tmp_path), select=True)
        assert run.call_count == 0
        sfile.assert_called_once_with(os.path.normpath(str(tmp_path)))
        # 目标文件不存在 -> 退化为普通打开(避免"点了没反应"还报错)
        sfile.reset_mock()
        utils.open_path(str(missing), select=True)
        sfile.assert_called_once_with(os.path.normpath(str(missing)))

    # macOS: open -R(Reveal in Finder)
    monkeypatch.setattr(sys, "platform", "darwin")
    with mock.patch.object(utils.subprocess, "run") as run:
        utils.open_path(str(f), select=True)
        run.assert_called_once_with(["open", "-R", str(f)], check=False)
        # 不带 select 时仍是普通打开
        run.reset_mock()
        utils.open_path(str(f))
        run.assert_called_once_with(["open", str(f)], check=False)

    # Linux: 无通用"选中"语义 -> 退化为打开父目录(明确降级优于静默失败)
    monkeypatch.setattr(sys, "platform", "linux")
    with mock.patch.object(utils.subprocess, "run") as run:
        utils.open_path(str(f), select=True)
        run.assert_called_once_with(["xdg-open", os.path.dirname(str(f))], check=False)


def test_open_path_windows_long_path_uses_shell_pidl(tmp_path, monkeypatch):
    """Windows 长路径: **进入目录** / 定位选中都走 Shell PIDL, **绝不触达** os.startfile 与 explorer

    本次修复的核心断言 —— 实测超长路径下 `os.startfile` 抛 `FileNotFoundError`、
    `explorer /select,` **静默打开"桌面"**, 所以这两条路径对长路径必须完全不被触达。
    目录目标是"进入"语义(`_win_shell_enter`), 它不可用时才退"定位选中"(`_win_shell_open`)。
    存在性判定与两个 PIDL 入口都 mock 掉(真调会弹资源管理器; 长路径在 POSIX 宿主上也不成立)。
    """
    _fake_windows(monkeypatch)
    long_dir = str(tmp_path) + "/" + "d" * 150 + "/" + "e" * 150
    long_file = long_dir + "/a.mkv"
    assert len(long_dir) >= utils.WIN_MAX_PATH, "用例前提: 目标确实是超长路径"

    with mock.patch.object(utils, "_win_shell_enter", return_value=True) as enter, \
            mock.patch.object(utils, "_win_shell_open") as pidl, \
            mock.patch.object(utils, "_exists_dir", return_value=True), \
            mock.patch.object(utils, "_win_foreground_explorer_async"), \
            mock.patch.object(utils.os, "startfile", create=True) as sfile, \
            mock.patch.object(utils.subprocess, "run") as run:
        utils.open_path(long_dir)  # 目录 -> 进入该目录
        enter.assert_called_once_with(long_dir)
        assert pidl.call_count == 0, "enter 成功即不再退'定位选中'"
        assert sfile.call_count == 0, "长路径目录不得退回 os.startfile"
        assert run.call_count == 0, "长路径目录不得退回 explorer"

    # enter 不可用 -> 退"定位选中"(目录 pidl), 仍不得落字符串路线
    with mock.patch.object(utils, "_win_shell_enter", return_value=False), \
            mock.patch.object(utils, "_win_shell_open", return_value=True) as pidl, \
            mock.patch.object(utils, "_exists_dir", return_value=True), \
            mock.patch.object(utils, "_win_foreground_explorer_async"), \
            mock.patch.object(utils.os, "startfile", create=True) as sfile, \
            mock.patch.object(utils.subprocess, "run") as run:
        utils.open_path(long_dir)
        pidl.assert_called_once_with(long_dir)
        assert sfile.call_count == 0
        assert run.call_count == 0

    with mock.patch.object(utils, "_win_shell_open", return_value=True) as pidl, \
            mock.patch.object(utils, "_win_foreground_explorer_async"), \
            mock.patch.object(utils, "_exists_file", return_value=True), \
            mock.patch.object(utils.os, "startfile", create=True) as sfile, \
            mock.patch.object(utils.subprocess, "run") as run:
        utils.open_path(long_file, select=True)  # 单文件种子 -> 打开父目录并选中
        pidl.assert_called_once_with(long_file)
        assert sfile.call_count == 0
        assert run.call_count == 0


def test_open_path_windows_falls_back_to_string_route(tmp_path, monkeypatch):
    """PIDL 路线返回 False 时, Windows 退回字符串路线 —— 不能静默什么都不做"""
    _fake_windows(monkeypatch)
    d = str(tmp_path)
    with mock.patch.object(utils, "_win_shell_open", return_value=False), \
            mock.patch.object(utils, "_win_shell_enter", return_value=False), \
            mock.patch.object(utils, "_exists_dir", return_value=True), \
            mock.patch.object(utils, "_win_foreground_explorer_async"), \
            mock.patch.object(utils, "_win_string_open") as fallback:
        utils.open_path(d)
        fallback.assert_called_once_with(d, select=False)
    with mock.patch.object(utils, "_win_shell_open", return_value=False), \
            mock.patch.object(utils, "_exists_file", return_value=True), \
            mock.patch.object(utils, "_win_foreground_explorer_async"), \
            mock.patch.object(utils, "_win_string_open") as fallback:
        utils.open_path(d + "/a.mkv", select=True)
        fallback.assert_called_once_with(d + "/a.mkv", select=True)


def test_open_path_non_windows_never_calls_shell_pidl(tmp_path, monkeypatch):
    """非 Windows 平台绝不触达 PIDL 路线

    守阵意义: 测试期副作用记账器把 `_win_shell_open` **整体计入 LAUNCH**(放行清单为空) ——
    若 POSIX 分支也去调它(哪怕它自己空转返回 False), 每次 `open_path` 都会记一条假阳性越界。
    """
    f = tmp_path / "a.mkv"
    f.write_bytes(b"x")
    for plat in ("linux", "darwin"):
        monkeypatch.setattr(sys, "platform", plat)
        with mock.patch.object(utils, "_win_shell_open") as pidl, \
                mock.patch.object(utils, "_win_shell_enter") as enter, \
                mock.patch.object(utils.subprocess, "run"):
            utils.open_path(str(f))
            utils.open_path(str(tmp_path), select=True)
            assert pidl.call_count == 0, f"{plat} 不得触达 PIDL 路线"
            assert enter.call_count == 0, f"{plat} 不得触达 PIDL 路线(进入目录)"


def test_open_path_windows_schedules_foreground_bringup(tmp_path, monkeypatch):
    """Windows 打开后调度后台置前: 参数 = (打开前窗口快照, 目录名); 非 Windows 不调度

    用户报"打开目标文件夹有概率不弹出至顶层": 根因是后台进程调用 Shell 时新窗口被前台锁压住。
    open_path 负责快照 + 调度, 具体置前逻辑由 _win_foreground_new_explorer 单独覆盖。
    """
    _fake_windows(monkeypatch)
    f = tmp_path / "a.mkv"
    f.write_bytes(b"x")
    with mock.patch.object(utils, "_win_explorer_hwnds", return_value={7, 8}), \
            mock.patch.object(utils, "_win_shell_open", return_value=True), \
            mock.patch.object(utils, "_exists_file", return_value=True), \
            mock.patch.object(utils, "_win_foreground_explorer_async") as fg:
        utils.open_path(str(f), select=True)
        fg.assert_called_once_with({7, 8}, os.path.normpath(str(f)))
    # 目录目标同样调度(且走"进入目录"的 PIDL 入口)
    with mock.patch.object(utils, "_win_explorer_hwnds", return_value=set()), \
            mock.patch.object(utils, "_win_shell_enter", return_value=True) as enter, \
            mock.patch.object(utils, "_win_shell_open", return_value=True), \
            mock.patch.object(utils, "_exists_dir", return_value=True), \
            mock.patch.object(utils, "_win_foreground_explorer_async") as fg:
        utils.open_path(str(tmp_path))
        enter.assert_called_once_with(str(tmp_path))
        fg.assert_called_once_with(set(), os.path.normpath(str(tmp_path)))
    # 非 Windows: 不调度(也不做快照)
    for plat in ("linux", "darwin"):
        monkeypatch.setattr(sys, "platform", plat)
        with mock.patch.object(utils, "_win_explorer_hwnds") as snap, \
                mock.patch.object(utils, "_win_foreground_explorer_async") as fg, \
                mock.patch.object(utils.subprocess, "run"):
            utils.open_path(str(f))
            assert snap.call_count == 0
            assert fg.call_count == 0


def test_win_foreground_new_explorer_new_window(monkeypatch):
    """快照差集命中新窗口 -> 立即抬到顶层(不空等超时)

    轮询超时压到极短: 本用例只验证"命中新窗口"这一条路径, 命中与否与超时长度无关。
    """
    monkeypatch.setattr(utils, "_EXPLORER_FG_TIMEOUT", 0.05)
    monkeypatch.setattr(utils, "_EXPLORER_FG_POLL", 0.01)
    before = {1, 2}
    seq = [before, before | {42}]
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: seq.pop(0) if seq else before | {42})
    monkeypatch.setattr(utils, "_win_window_text", lambda h: "")
    fg = mock.MagicMock(return_value=True)
    monkeypatch.setattr(utils, "_win_force_foreground", fg)
    assert utils._win_foreground_new_explorer(before, "dir") is True
    fg.assert_called_once_with(42)


def test_win_foreground_new_explorer_reused_window_title_match(monkeypatch):
    """无新窗口(Explorer 复用已有窗口导航) -> 按窗口标题匹配抬到顶层; 匹配不上不置前

    实测 SHOpenFolderAndSelectItems 打开的是**父窗口**并选中目标, 所以候选名含父目录名;
    Win11 标题带 " - 文件资源管理器" 后缀, 用 `名字 + " - "` 前缀匹配。
    """
    monkeypatch.setattr(utils, "_EXPLORER_FG_TIMEOUT", 0.05)
    monkeypatch.setattr(utils, "_EXPLORER_FG_POLL", 0.01)
    before = {5, 6}
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: before)
    # 目标 X:/downloads/f1.mkv: 窗口停在父目录 downloads(标题带本地化后缀) -> 命中
    texts = {5: "其它目录", 6: "downloads - 文件资源管理器"}
    monkeypatch.setattr(utils, "_win_window_text", lambda h: texts.get(h, ""))
    fg = mock.MagicMock(return_value=True)
    monkeypatch.setattr(utils, "_win_force_foreground", fg)
    assert utils._win_foreground_new_explorer(before, os.path.join("X:", "downloads", "f1.mkv")) is True
    fg.assert_called_once_with(6)
    # 标题对不上 -> 静默放弃, 绝不误推无关窗口
    fg.reset_mock()
    texts[6] = "别的 - 文件资源管理器"
    monkeypatch.setattr(utils, "_win_window_text", lambda h: texts.get(h, ""))
    assert utils._win_foreground_new_explorer(before, os.path.join("X:", "downloads", "f1.mkv")) is False
    assert fg.call_count == 0


class _FakeUser32:
    """user32 替身: 记录全部调用, 且**前台结果可控** —— 取焦被拒/成功的两条分支都能钉住

    为何要替身: 置前链路的 bug("有概率不弹到顶层")恰恰出在"某个 API 调用被系统静默拒绝"上,
    真调 user32 根本测不出这种分支(且会把开发机的窗口摆弄乱)。
    """
    def __init__(self, hwnd=42, fg=7, focus_after=None, switch_after=None, alive=(42, ), iconic=(), invisible=()):
        self.hwnd = hwnd
        self.fg = fg  # 当前前台窗口
        self.focus_after = focus_after  # SetForegroundWindow 之后的前台(None = 不变)
        self.switch_after = switch_after  # SwitchToThisWindow 之后的前台
        self.alive = set(alive)
        self.iconic = set(iconic)
        self.invisible = set(invisible)
        self.calls = []

    # ---- 查询 ----
    def IsWindow(self, h):
        return h in self.alive

    def IsIconic(self, h):
        return h in self.iconic

    def IsWindowVisible(self, h):
        return h not in self.invisible

    def GetForegroundWindow(self):
        return self.fg

    def GetWindowThreadProcessId(self, h, _lp):
        return 100

    # ---- 动作 ----
    def ShowWindow(self, h, cmd):
        self.calls.append(("ShowWindow", h, cmd))

    def SetWindowPos(self, h, insert, x, y, w, hh, flags):
        self.calls.append(("SetWindowPos", insert, flags))

    def AttachThreadInput(self, a, b, on):
        self.calls.append(("AttachThreadInput", a, b, on))
        return True

    def SetForegroundWindow(self, h):
        self.calls.append(("SetForegroundWindow", h))
        if self.focus_after is not None:
            self.fg = self.focus_after

    def SwitchToThisWindow(self, h, _alt):
        self.calls.append(("SwitchToThisWindow", h))
        if self.switch_after is not None:
            self.fg = self.switch_after

    def BringWindowToTop(self, h):
        self.calls.append(("BringWindowToTop", h))


def _install_fake_win(monkeypatch, **kw):
    """装上假 user32 / kernel32(只替换 `_win_user32` / `_win_kernel32`, 不碰 ctypes)"""
    monkeypatch.setattr(sys, "platform", "win32")
    u32 = _FakeUser32(**kw)
    monkeypatch.setattr(utils, "_win_user32", lambda: u32)

    class _K32:
        def GetCurrentThreadId(self):
            return 999

    monkeypatch.setattr(utils, "_win_kernel32", lambda: _K32())
    return u32


def test_win_wait_explorer_prefers_new_window_over_title_match(monkeypatch):
    """新窗口优先于标题匹配的复用窗口; 两条策略都落空 -> None(超时即放弃, 不无限等)

    旧实现把"复用/复用标题匹配"放在 2s 超时之后才做一次, 慢于 2s 的复用导航整个漏掉 ——
    这是本轮修复的核心回归面: 两条策略必须**每轮都试**。
    """
    monkeypatch.setattr(utils, "_EXPLORER_FG_TIMEOUT", 0.05)
    monkeypatch.setattr(utils, "_EXPLORER_FG_POLL", 0.01)
    before = {5, 6}
    # 既有新窗口 42, 也有标题匹配的旧窗口 6 -> 取新窗口
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: {5, 6, 42})
    monkeypatch.setattr(utils, "_win_window_text", lambda h: "downloads - 文件资源管理器" if h == 6 else "")
    target = os.path.join("X:", "downloads", "f1.mkv")
    assert utils._win_wait_explorer(before, target) == 42
    # 没有新窗口 -> 退到标题匹配的复用窗口
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: {5, 6})
    assert utils._win_wait_explorer(before, target) == 6
    # 两条都落空 -> 超时 None
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: {5, 6})
    monkeypatch.setattr(utils, "_win_window_text", lambda h: "无关窗口")
    assert utils._win_wait_explorer(before, target) is None


def test_win_topmost_once_toggles_and_clears(monkeypatch):
    """TOPMOST 挂一下立刻摘掉 + `SWP_NOACTIVATE`(只动 Z 序, 不抢焦点)

    摘是必须的: 留着 topmost 会让资源管理器长期钉在所有窗口之上, 比原来的 bug 更烦人;
    NOACTIVATE 是它能被后台进程受理的原因 —— 不受前台锁约束。
    """
    u32 = _install_fake_win(monkeypatch)
    utils._win_topmost_once(42)
    pos = [c for c in u32.calls if c[0] == "SetWindowPos"]
    assert pos == [("SetWindowPos", -1, 0x53), ("SetWindowPos", -2, 0x53)], "必须是 TOPMOST -> NOTOPMOST 成对调用"
    assert pos[0][2] & 0x0010, "必须带 SWP_NOACTIVATE: 靠它绕开前台锁"


def test_win_force_foreground_zorder_raised_even_when_focus_denied(monkeypatch):
    """前台锁拒绝取焦时, **Z 序提升照做** + 走 SwitchToThisWindow 兜底

    这是用户报障"有概率不弹出至顶层"的根因面: 后台进程 SetForegroundWindow 被静默拒绝 =>
    资源管理器留在浏览器后面。Window allows后台进程改 Z 序, 所以"看得见"必须与"抢得到焦点"解耦,
    且抬到顶层**不能**依赖任何一层成功。
    """
    u32 = _install_fake_win(monkeypatch, hwnd=42, fg=7, focus_after=7, switch_after=7)
    assert utils._win_force_foreground(42) is False
    kinds = [c[0] for c in u32.calls]
    assert "SetWindowPos" in kinds, "取焦失败也必须把窗口抬到顶层(Z 序)"
    assert "SetForegroundWindow" in kinds
    assert "SwitchToThisWindow" in kinds, "兜底硬切必须走到"
    # 连带效果: AttachThreadInput 必须成对(借了前台权限要还回去)
    attach = [c for c in u32.calls if c[0] == "AttachThreadInput"]
    assert [a[-1] for a in attach] == [True, False]


def test_win_force_foreground_true_when_focus_taken(monkeypatch):
    """抢到焦点即返回 True, 且不再多此一举走兜底硬切"""
    u32 = _install_fake_win(monkeypatch, hwnd=42, fg=7, focus_after=42)
    assert utils._win_force_foreground(42) is True
    kinds = [c[0] for c in u32.calls]
    assert "SwitchToThisWindow" not in kinds
    assert "BringWindowToTop" not in kinds


def test_win_force_foreground_dead_hwnd_silent(monkeypatch):
    """句柄已失效 -> 一个 user32 调用都不发, 返回 False(窗口可能早被关了)"""
    u32 = _install_fake_win(monkeypatch, hwnd=42, alive=())
    assert utils._win_force_foreground(42) is False
    assert u32.calls == []


def test_win_force_foreground_retries_until_focus(monkeypatch):
    """单次被拒后有**封顶**重试(前台锁是概率性的), 全部失败也返回 False 且不抛错"""
    monkeypatch.setattr(utils, "_EXPLORER_FG_RETRY_GAP", 0.0)
    monkeypatch.setattr(utils, "_win_wait_explorer", lambda before, target: 42)
    attempts = iter([False, False, True])
    monkeypatch.setattr(utils, "_win_force_foreground", lambda h: next(attempts))
    assert utils._win_foreground_new_explorer(set(), "dir") is True
    # 全部被拒: 不抛错, 只返回 False(置前是锦上添花)
    monkeypatch.setattr(utils, "_win_force_foreground", lambda h: False)
    assert utils._win_foreground_new_explorer(set(), "dir") is False


def test_win_user32_binds_signatures(monkeypatch):
    """`_win_user32` 必须给每个 API 绑死 argtypes(x64 ABI 陷阱的守阵)

    不绑时 ctypes 把 HWND 按 **32 位 int** 传, 指针宽度参数的高 32 位是寄存器残留:
    `SetWindowPos(hwnd, HWND_TOPMOST=0xFFFFFFFFFFFFFFFF, ...)` 收到畸形值 -> **返回 0 且
    GetLastError 仍为 0**(静默无效果)。2026-09-30 实测: 同一窗口同一时刻, 未绑 ret=0 Z 序不动,
    绑了 ret=1 立刻抬到顶层。这就是"有概率不弹到顶层"的真根因 —— 所以这一条不许退化。
    Windows 上跑真验收: 签名表里的函数必须全部绑上。
    """
    monkeypatch.setattr(sys, "platform", "win32")
    u32 = utils._win_user32()
    if u32 is None:  # POSIX 宿主: 早退本身由另一条覆盖, 这里只跳过真验收
        pytest.skip("非 Windows 宿主, 跳过签名绑定验收")
    for name, argtypes, _ in utils._WIN_USER32_SIGNATURES():
        fn = getattr(u32, name, None)
        assert fn is not None, f"{name} 在 user32 里不存在"
        assert fn.argtypes == list(argtypes), f"{name} 的 argtypes 没绑或绑错了(x64 传参会静默失效)"
    k32 = utils._win_kernel32()
    assert k32.GetCurrentThreadId.argtypes == []


def test_win_user32_kernel32_non_windows_none(monkeypatch):
    """非 Windows 上 user32 / kernel32 句柄取用返回 None(早退, 不靠"恰好抛异常")

    不为别的: `ctypes.windll` 在 POSIX 上不存在 —— 让行为依赖 AttributeError 会让 Linux CI
    变成偶然通过(本坑另有守阵 `test_win_shell_open_non_windows_returns_false`)。
    """
    for plat in ("linux", "darwin"):
        monkeypatch.setattr(sys, "platform", plat)
        assert utils._win_user32() is None
        assert utils._win_kernel32() is None
        assert utils._win_force_foreground(42) is False
        assert utils._win_window_text(42) == ""


def test_win_dll_missing_windll_returns_none(monkeypatch):
    """平台伪装成 win32 但 ctypes 无 `windll` / `WINFUNCTYPE` 门面(POSIX 实况) -> 返回 None, 不抛错

    守阵(2026-10-13 Linux CI 4 条红): 签名表构造会碰 `ctypes.WINFUNCTYPE`(POSIX 不存在) ——
    它若在**实参位**被求值, 就发生在 `ctypes.windll` 探测**之前**, "取不到 -> 返回 None"
    这层安全网被绕过, POSIX 上抛 `AttributeError`(与 is_windows 早退那条是两回事: 这条
    `sys.platform` 已是 win32, 早退不生效)。本用例在**两平台**造出 Linux CI 的等价形态:
    删掉 `windll` + `WINFUNCTYPE` 后断言返回 None。
    红验: 调用点退回 `_win_dll("user32", _WIN_USER32_SIGNATURES())` 即红(实参求值早于探测)。
    """
    import ctypes

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(utils, "_bound_user32", None)
    monkeypatch.setattr(utils, "_bound_kernel32", None)
    monkeypatch.delattr(ctypes, "windll", raising=False)
    monkeypatch.delattr(ctypes, "WINFUNCTYPE", raising=False)
    assert utils._win_user32() is None
    assert utils._win_kernel32() is None


def test_win_explorer_hwnds_non_windows_empty(monkeypatch):
    """非 Windows 上窗口快照恒空集, 不碰 ctypes(windll 在 POSIX 不存在)"""
    monkeypatch.setattr(sys, "platform", "linux")
    assert utils._win_explorer_hwnds() == set()


def test_win_shell_open_non_windows_returns_false(monkeypatch):
    """非 Windows 上 `_win_shell_open` / `_win_shell_enter` 前置返回 False

    必须靠 `is_windows()` 早返回, 而不是靠捕获 `AttributeError` —— `ctypes.windll` 在 POSIX 上
    根本不存在, 让行为依赖"恰好抛了异常"会让 Linux CI 变成偶然通过。两个入口都要覆盖:
    它们各自被 sidefx 计成 LAUNCH, 少了任一条"非 Windows 空转"就少了对应的假阳性守阵。
    """
    for plat in ("linux", "darwin"):
        monkeypatch.setattr(sys, "platform", plat)
        assert utils._win_shell_open("/tmp/whatever") is False
        assert utils._win_shell_enter("/tmp/whatever") is False


def test_win_string_open_degrades_long_path_to_ancestor(monkeypatch):
    """字符串路线遇超长路径上溯到最近的可达祖先

    否则 `os.startfile` 对超长路径必抛 `FileNotFoundError`(即使目录确实存在) —— 上溯后长度
    < `WIN_MAX_PATH`, 故判定用裸路径即可(无需前缀)。
    """
    monkeypatch.setattr(sys, "platform", "win32")
    long_path = "C:/" + "/".join(["d" * 40] * 8)
    assert len(os.path.normpath(long_path)) >= utils.WIN_MAX_PATH, "用例前提: 入参超长"
    with mock.patch.object(utils.os, "startfile", create=True) as sfile:
        utils._win_string_open(long_path, select=False)
        opened = sfile.call_args.args[0]
        assert len(opened) < utils.WIN_MAX_PATH, "必须上溯到长度 < MAX_PATH 的祖先"
        assert os.path.normpath(long_path).startswith(opened), "上溯结果必须是原路径的祖先"


def test_win_shell_open_not_windows(monkeypatch):
    """非 Windows 恒 False(不进入 ctypes 路线)"""
    monkeypatch.setattr(utils, "is_windows", lambda: False)
    assert utils._win_shell_open("D:/x") is False


def _fake_shell(
    parse_result=0, open_result=0, parse_sets_pidl=False, coinit_raises=False, exec_result=1, has_exec=True
):
    """假 shell32/ole32 替身(记录调用, 不碰真 Shell)

    `exec_result` / `has_exec` 只服务 `_win_shell_enter`(ShellExecuteExW 的成功/失败分支与
    "该导出不存在"的降级); `exec` 记的是**解引用后的结构体对象**(CArgObject._obj), 供用例
    直接断言 fMask/lpVerb/lpIDList 等字段。
    """
    import ctypes
    calls = {"parse": [], "open": [], "ilfree": 0, "couninit": 0, "exec": []}

    def parse(target, _none, byref_pidl, _flags, _byref_sfgao):
        calls["parse"].append(target)
        if parse_sets_pidl:
            byref_pidl._obj.value = 0x1234
        return parse_result

    def open_items(pidl, _n, _ref, _flags):
        calls["open"].append(pidl)
        return open_result

    def exec_ex(byref_info):
        calls["exec"].append(byref_info._obj)
        return exec_result

    def coinit(_reserved, _mode):
        if coinit_raises:
            raise AttributeError("no COM")
        return 1  # S_FALSE

    shell32 = SimpleNamespace(
        SHParseDisplayName=parse,
        SHOpenFolderAndSelectItems=open_items,
        ILFree=lambda pidl: calls.__setitem__("ilfree", calls["ilfree"] + 1),
    )
    if has_exec:
        shell32.ShellExecuteExW = exec_ex
    ole32 = SimpleNamespace(
        CoInitializeEx=coinit,
        CoUninitialize=lambda: calls.__setitem__("couninit", calls["couninit"] + 1),
    )
    return shell32, ole32, calls


def _unwrapped_shell_open(monkeypatch):
    """取回被 sidefx 记账包装前的原 _win_shell_open(仅本测试内直调)

    本测试把 shell32/ole32 全部换成假替身, 不可能产生真实打开 —— 而 sidefx 对该入口的
    记账包装包在函数外层, 不区分真假, 直调会按 LAUNCH 记成越界假阳性(sidefx.py 自述
    「没有真实副作用就不该记」)。借记账器自己的 _saved 快照把原函数临时装回去, 测后
    monkeypatch 自动恢复包装, 守阵对其余用例的拦截力不变。
    """
    import sidefx

    for container, name, original in list(getattr(sidefx.SESSION, "_saved", ())):
        if container is utils and name == "_win_shell_open":
            monkeypatch.setattr(utils, "_win_shell_open", original)
            return
    raise AssertionError("sidefx 未包装 _win_shell_open: 前置条件变化, 请复核本辅助")


def _unwrapped_shell_enter(monkeypatch):
    """取回被 sidefx 记账包装前的原 _win_shell_enter(仅本测试内直调)

    理由与 `_unwrapped_shell_open` 逐条相同: 本测试把 shell32/ole32 全换成假替身, 不可能产生
    真实打开, 而 sidefx 的记账包装包在函数外层不区分真假 —— 直调会按 LAUNCH 记成越界假阳性。
    """
    import sidefx

    for container, name, original in list(getattr(sidefx.SESSION, "_saved", ())):
        if container is utils and name == "_win_shell_enter":
            monkeypatch.setattr(utils, "_win_shell_enter", original)
            return
    raise AssertionError("sidefx 未包装 _win_shell_enter: 前置条件变化, 请复核本辅助")


def _shim_posix_ctypes(monkeypatch):
    """POSIX 上补齐 ctypes 的 Windows 专属门面(`windll` / `WINFUNCTYPE`), 让 Windows 分支用例
    在 Linux CI 上也能跑 —— 用例注入的都是假替身, 不碰真窗口。

    Windows 宿主不装: 走真门面, 行为与改动前逐字一致。缺这两样是 POSIX 的既有事实
    (`ctypes.windll` / `ctypes.WINFUNCTYPE` 在 Linux 上不存在), 不是被测代码的缺陷 ——
    生产入口(`_win_user32` / `_win_shell_open` 等)靠 `is_windows()` 早退, 用例则靠本 shim
    把门面补上。`ctypes.wintypes` 两平台都有, 无需补。
    """
    import ctypes

    if not hasattr(ctypes, "windll"):
        monkeypatch.setattr(ctypes, "windll", SimpleNamespace(), raising=False)
    if not hasattr(ctypes, "WINFUNCTYPE"):
        # WINFUNCTYPE(BOOL, HWND, LPARAM) 是回调工厂; 假 user32 下真实调用约定无意义,
        # 直接返回原函数即可(`_win_explorer_hwnds` 只把它当"把 _on_window 包成 proc"用)
        monkeypatch.setattr(ctypes, "WINFUNCTYPE", lambda *a: (lambda f: f), raising=False)


def test_win_shell_open_pidl_routes(monkeypatch):
    """_win_shell_open PIDL 路线三分支: 解析失败 / 打开失败 / 成功; 前缀剥离与 COM 配对

    Windows 分支用例 ⇒ 固定平台 + 补 ctypes 门面(POSIX 无 `windll`), 假 shell32/ole32
    全程替身, 不碰真 Shell。
    """
    import ctypes

    import auto_qb.infra.utils as u

    _shim_posix_ctypes(monkeypatch)
    monkeypatch.setattr(sys, "platform", "win32")
    _unwrapped_shell_open(monkeypatch)
    # 成功: parse 0 + open 0 -> True; pidl 置位 -> ILFree; CoUninitialize 配对
    shell32, ole32, calls = _fake_shell(parse_sets_pidl=True)
    monkeypatch.setattr(ctypes.windll, "shell32", shell32, raising=False)
    monkeypatch.setattr(ctypes.windll, "ole32", ole32, raising=False)
    assert u._win_shell_open("\\\\?\\D:/长路径目录") is True
    assert calls["ilfree"] == 1 and calls["couninit"] == 1
    assert calls["parse"] and not calls["parse"][0].startswith("\\\\?\\"), "前缀与 PIDL 路线互斥, 已剥离"
    # 解析失败 -> False(退回字符串路线)
    shell32, ole32, calls = _fake_shell(parse_result=1)
    monkeypatch.setattr(ctypes.windll, "shell32", shell32, raising=False)
    monkeypatch.setattr(ctypes.windll, "ole32", ole32, raising=False)
    assert u._win_shell_open("D:/nope") is False
    assert calls["ilfree"] == 0, "pidl 未置位不释放"
    # 打开失败 -> False
    shell32, ole32, calls = _fake_shell(parse_result=0, open_result=5)
    monkeypatch.setattr(ctypes.windll, "shell32", shell32, raising=False)
    monkeypatch.setattr(ctypes.windll, "ole32", ole32, raising=False)
    assert u._win_shell_open("D:/nope") is False
    # CoInitializeEx 异常 -> False(防御, 绝不抛)
    shell32, ole32, calls = _fake_shell(coinit_raises=True)
    monkeypatch.setattr(ctypes.windll, "shell32", shell32, raising=False)
    monkeypatch.setattr(ctypes.windll, "ole32", ole32, raising=False)
    assert u._win_shell_open("D:/nope") is False


def test_win_shell_enter_pidl_routes(monkeypatch):
    """`_win_shell_enter`(进入目录) PIDL 路线: ShellExecuteExW + `open` 动词 + PIDL, 长路径安全

    本函数与 `_win_shell_open`(SHOpenFolderAndSelectItems: 打开**父**窗口并选中该条目)是两件事 ——
    用例钉住结构体装填(fMask 含 IDLIST / 动词 / PIDL / nShow / cbSize 等于真实大小)、成功与
    失败分支、以及"该导出不存在"时的降级(绝不抛)。全程假 shell32/ole32 替身, 不碰真 Shell。
    """
    import ctypes

    import auto_qb.infra.utils as u

    _shim_posix_ctypes(monkeypatch)
    monkeypatch.setattr(sys, "platform", "win32")
    _unwrapped_shell_enter(monkeypatch)
    # 成功: 结构体按 ShellExecuteEx 契约装填; 前缀剥离; pidl 释放 + COM 配对卸载
    shell32, ole32, calls = _fake_shell(parse_sets_pidl=True)
    monkeypatch.setattr(ctypes.windll, "shell32", shell32, raising=False)
    monkeypatch.setattr(ctypes.windll, "ole32", ole32, raising=False)
    assert u._win_shell_enter("\\\\?\\D:/长路径目录") is True
    info = calls["exec"][0]
    assert info.lpVerb == "open" and info.fMask == u._SEE_MASK_INVOKEIDLIST
    assert info.lpIDList == 0x1234, "必须把 PIDL 直接交给 Shell(字符串路线对长路径不可靠)"
    assert info.nShow == u._SW_SHOWNORMAL
    assert info.cbSize == ctypes.sizeof(type(info)), "cbSize 必须等于结构体真实大小, 否则 Shell 直接失败"
    assert calls["parse"] and not calls["parse"][0].startswith("\\\\?\\"), "前缀与 PIDL 路线互斥, 已剥离"
    assert calls["ilfree"] == 1 and calls["couninit"] == 1
    # ShellExecuteExW 返回 0 -> False(调用方降级), 但 pidl 仍要释放
    shell32, ole32, calls = _fake_shell(parse_sets_pidl=True, exec_result=0)
    monkeypatch.setattr(ctypes.windll, "shell32", shell32, raising=False)
    monkeypatch.setattr(ctypes.windll, "ole32", ole32, raising=False)
    assert u._win_shell_enter("D:/nope") is False and calls["ilfree"] == 1
    # 解析失败 -> False 且不释放未置位的 pidl
    shell32, ole32, calls = _fake_shell(parse_result=1)
    monkeypatch.setattr(ctypes.windll, "shell32", shell32, raising=False)
    monkeypatch.setattr(ctypes.windll, "ole32", ole32, raising=False)
    assert u._win_shell_enter("D:/nope") is False and calls["ilfree"] == 0 and not calls["exec"]
    # 无 ShellExecuteExW 导出 -> False(防御分支, 由字符串路线兜住)
    shell32, ole32, calls = _fake_shell(parse_sets_pidl=True, has_exec=False)
    monkeypatch.setattr(ctypes.windll, "shell32", shell32, raising=False)
    monkeypatch.setattr(ctypes.windll, "ole32", ole32, raising=False)
    assert u._win_shell_enter("D:/nope") is False and not calls["exec"]


def test_win_user32_and_kernel32_bind_signatures(monkeypatch):
    """user32/kernel32 惰性句柄: 首次取用绑死 x64 签名(测试重置缓存后真绑定一次, 不调任何 API)

    Windows 分支用例 ⇒ 固定平台 + 假 `ctypes.windll`(句柄对象为空替身, 属性取不到时
    `_win_bind` 自行吞掉), 于是本用例在两平台都跑 —— 不靠"恰好抛 AttributeError"。
    """
    import ctypes

    import auto_qb.infra.utils as u

    _shim_posix_ctypes(monkeypatch)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(user32=SimpleNamespace(), kernel32=SimpleNamespace()), raising=False
    )
    monkeypatch.setattr(u, "_bound_user32", None)
    monkeypatch.setattr(u, "_bound_kernel32", None)
    user32 = u._win_user32()
    assert user32 is not None and u._win_user32() is user32, "缓存复用同一句柄"
    kernel32 = u._win_kernel32()
    assert kernel32 is not None and u._win_kernel32() is kernel32


class _P1FakeUser32:
    """可编程 user32 替身: 按脚本回答各 API(不碰真窗口)"""
    def __init__(self, *, is_window=True, iconic=False, visible=True, fg=None, thread_id=7, fg_thread=99):
        self.scripts = []
        self.calls = []
        self._is_window = is_window
        self._iconic = iconic
        self._visible = visible
        self._fg = fg
        self._thread_id = thread_id
        self._fg_thread = fg_thread

    def IsWindow(self, hwnd):
        return self._is_window

    def IsIconic(self, hwnd):
        return self._iconic

    def IsWindowVisible(self, hwnd):
        return self._visible

    def GetForegroundWindow(self):
        self._fg_seq = getattr(self, "_fg_seq", 0) + 1
        return self._fg(self._fg_seq) if callable(self._fg) else self._fg

    def SetForegroundWindow(self, hwnd):
        self.calls.append("SetForegroundWindow")
        return True

    def BringWindowToTop(self, hwnd):
        self.calls.append("BringWindowToTop")
        return True

    def SwitchToThisWindow(self, hwnd, toggle):
        self.calls.append("SwitchToThisWindow")

    def ShowWindow(self, hwnd, cmd):
        self.calls.append(f"ShowWindow:{cmd}")
        return True

    def SetWindowPos(self, hwnd, after, x, y, cx, cy, flags):
        self.calls.append(f"SetWindowPos:{after}")
        return True

    def GetWindowThreadProcessId(self, hwnd, out):
        return self._fg_thread

    def AttachThreadInput(self, a, b, attach):
        self.calls.append("AttachThreadInput" if attach else "DetachThreadInput")
        return True

    def GetClassNameW(self, hwnd, buf, n):
        buf.value = "CabinetWClass"
        return len(buf.value)

    def GetWindowTextW(self, hwnd, buf, n):
        buf.value = "目标 - 文件资源管理器"
        return len(buf.value)

    def EnumWindows(self, proc, lparam):
        proc(101, 0)
        proc(202, 0)
        return True


class _P1FakeKernel32:
    def GetCurrentThreadId(self):
        return 7


def test_win_explorer_hwnds_and_topmost_and_switch(monkeypatch):
    """Explorer 枚举按类名过滤 / TOPMOST 开关式提升 / SwitchToThisWindow 兜底 + 各失败静默

    `_win_explorer_hwnds` 内部要 `ctypes.WINFUNCTYPE`(POSIX 无) ⇒ 补门面; user32 仍是假替身。
    """
    _shim_posix_ctypes(monkeypatch)
    fake = _P1FakeUser32()
    monkeypatch.setattr(utils, "_win_user32", lambda: fake)
    monkeypatch.setattr(utils, "_win_kernel32", lambda: _P1FakeKernel32())
    hwnds = utils._win_explorer_hwnds()
    assert hwnds == {101, 202}, "类名 CabinetWClass 的窗口都进集合"
    utils._win_topmost_once(101)
    assert "SetWindowPos:-1" in fake.calls and "SetWindowPos:-2" in fake.calls, "TOPMOST 挂一下立刻摘"
    assert utils._win_switch_to_this_window(101) is True
    # 失败静默: user32 缺席 / API 缺失
    monkeypatch.setattr(utils, "_win_user32", lambda: None)
    assert utils._win_explorer_hwnds() == set()
    assert utils._win_switch_to_this_window(1) is False

    class _Broken(_P1FakeUser32):
        def SetWindowPos(self, *a):
            raise OSError("无窗口")

    monkeypatch.setattr(utils, "_win_user32", lambda: _Broken())
    utils._win_topmost_once(1)  # 异常吞掉不外抛
    monkeypatch.setattr(utils, "_win_user32", lambda: None)
    utils._win_topmost_once(1)  # user32 缺席早退
    assert utils._win_window_text(1) == "", "user32 缺席标题为空"
    monkeypatch.setattr(utils, "_win_user32", lambda: _P1FakeUser32())
    assert utils._win_window_text(1) == "目标 - 文件资源管理器"


def test_win_force_foreground_matrix(monkeypatch):
    """三层升级矩阵: 不可还原 / 最小化先还原 / 隐藏先显示 / 焦点成功 / 借线程失败硬切 / 异常 False"""
    monkeypatch.setattr(utils, "_win_kernel32", lambda: _P1FakeKernel32())
    # 1) 焦点直接成功
    fake = _P1FakeUser32(fg=lambda seq: 101 if seq >= 2 else 202)
    monkeypatch.setattr(utils, "_win_user32", lambda: fake)
    assert utils._win_force_foreground(101) is True
    assert "AttachThreadInput" in fake.calls and "DetachThreadInput" in fake.calls, "借前台线程权限并归还"
    # 2) 最小化: 先 SW_RESTORE(9)
    fake = _P1FakeUser32(iconic=True, fg=101)
    monkeypatch.setattr(utils, "_win_user32", lambda: fake)
    assert utils._win_force_foreground(101) is True
    assert "ShowWindow:9" in fake.calls
    # 3) 隐藏: 先 SW_SHOW(5)
    fake = _P1FakeUser32(visible=False, fg=101)
    monkeypatch.setattr(utils, "_win_user32", lambda: fake)
    assert utils._win_force_foreground(101) is True
    assert "ShowWindow:5" in fake.calls
    # 4) 焦点拿不到: 硬切 + BringWindowToTop, 仍失败如实 False
    fake = _P1FakeUser32(fg=lambda seq: 202)  # 前台永远是别人
    monkeypatch.setattr(utils, "_win_user32", lambda: fake)
    assert utils._win_force_foreground(101) is False
    assert "SwitchToThisWindow" in fake.calls and "BringWindowToTop" in fake.calls
    # 5) 窗口已不存在 -> False
    monkeypatch.setattr(utils, "_win_user32", lambda: _P1FakeUser32(is_window=False))
    assert utils._win_force_foreground(101) is False
    # 6) user32/kernel32 缺席 -> False
    monkeypatch.setattr(utils, "_win_user32", lambda: None)
    assert utils._win_force_foreground(101) is False


def test_win_reuse_and_wait_explorer(monkeypatch):
    """复用窗口按标题匹配(含本地化后缀); 差集新窗口优先; 超时 None; 置前重试封顶

    `_win_reuse_title_candidates` 用 `os.path` 拆**Windows 形态**的 target(调用点只在 Windows)
    ⇒ 按 pitfalls/testing/patching.md 4 固定语义: 只把 utils 模块内的 `os` 换成 `ntpath`
    (纯字符串模块, 两平台同语义), 不动全局 os.path。否则 POSIX 上反斜杠不是分隔符, 盘根断言必红。
    """
    monkeypatch.setattr(utils, "os", SimpleNamespace(path=ntpath))
    monkeypatch.setattr(utils, "_win_user32", lambda: _P1FakeUser32())
    monkeypatch.setattr(utils, "_win_kernel32", lambda: _P1FakeKernel32())
    # 标题候选: 目标名 + 父目录名
    names = utils._win_reuse_title_candidates("R:/Media/Show")
    assert names == {"Show", "Media"}
    assert utils._win_reuse_title_candidates("R:\\") == set(), "盘根无候选, 跳过复用兜底"
    # 复用匹配: 只在打开前就存在的窗口里找, 标题带本地化后缀也算
    hit = utils._win_match_reused_explorer({101, 202}, before={202}, names={"目标"})
    assert hit == 202
    assert utils._win_match_reused_explorer({101, 202}, before={202}, names={"无关"}) is None
    # 等待: 差集新窗口立刻返回
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: {999})
    assert utils._win_wait_explorer({202}, "R:/Media/Show") == 999
    # 等待: 无新窗口但旧窗口标题命中 -> 复用
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: {202})
    assert utils._win_wait_explorer({202}, "R:/Media/目标") == 202
    # 等待: 超时(上限拨负) -> None; 名字为空跳过复用匹配
    monkeypatch.setattr(utils, "_EXPLORER_FG_TIMEOUT", -1.0)
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: set())
    assert utils._win_wait_explorer(set(), "R:/Media/Show") is None
    assert utils._win_wait_explorer(set(), "") is None
    # 置前编排: 找不到窗口 -> False(静默); 重试耗尽 -> False(封顶, 不执念)
    assert utils._win_foreground_new_explorer(set(), "R:/x") is False
    monkeypatch.setattr(utils, "_EXPLORER_FG_RETRY", 1)
    monkeypatch.setattr(utils, "_EXPLORER_FG_RETRY_GAP", 0.0)
    monkeypatch.setattr(utils, "_win_wait_explorer", lambda before, target: 101)
    monkeypatch.setattr(utils, "_win_force_foreground", lambda hwnd: False)
    assert utils._win_foreground_new_explorer(set(), "R:/x") is False
    monkeypatch.setattr(utils, "_win_force_foreground", lambda hwnd: True)
    assert utils._win_foreground_new_explorer(set(), "R:/x") is True


def test_win_shell_with_pidl_missing_windll_returns_false(monkeypatch):
    """PIDL 路线在 ctypes 无 windll 门面时 -> False 降级, 不抛 ImportError/AttributeError

    打开路径是用户点出来的操作: 探测失败只许「换降级路线」, 绝不许把异常冒到端点。
    """
    import ctypes

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delattr(ctypes, "windll", raising=False)
    assert utils._win_shell_with_pidl("C:/x", lambda *a: True) is False


def test_win_api_missing_attribute_silent(monkeypatch):
    """四个 Windows 入口在「导出缺失」时一律静默降级(置前是锦上添花, 不许影响打开本体)

    `_win_explorer_hwnds` 缺 `ctypes.WINFUNCTYPE` -> 空集(快照失败 = 跳过置前, 行为退化到修复前);
    `_win_switch_to_this_window` / `_win_window_text` / `_win_force_foreground` 缺对应导出 ->
    False / "" / False。user32 替身刻意只给空对象, 让第一次属性访问就抛 AttributeError。
    """
    import ctypes

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(utils, "_win_user32", lambda: SimpleNamespace())
    monkeypatch.setattr(utils, "_win_kernel32", lambda: SimpleNamespace())
    monkeypatch.delattr(ctypes, "WINFUNCTYPE", raising=False)
    assert utils._win_explorer_hwnds() == set()
    assert utils._win_switch_to_this_window(1) is False
    assert utils._win_window_text(1) == ""
    assert utils._win_force_foreground(1) is False


def test_win_force_foreground_skips_attach_when_no_foreground(monkeypatch):
    """没有前台窗口时**不借线程权限**(`bool(fg)` 短路), 但仍照常 SetForegroundWindow

    前台窗口为 0(桌面切换中/锁屏刚恢复)时 AttachThreadInput 无对象可借, 硬借会拿 0 当线程 id
    去挂 —— 这里钉住「没前台就不 attach」, 同时保证取焦动作照发(一次就拿到焦点)。
    """
    u32 = _install_fake_win(monkeypatch, hwnd=42, fg=0, focus_after=42)
    assert utils._win_force_foreground(42) is True
    assert [c for c in u32.calls if c[0] == "AttachThreadInput"] == [], "无前台窗口不借线程权限"
    assert ("SetForegroundWindow", 42) in u32.calls


def test_win_wait_explorer_no_title_candidates_skips_match(monkeypatch):
    """目标算不出复用标题候选时(空集)整段跳过标题匹配, 只等新窗口差集, 超时即 None

    对应「目标路径的末段/父目录都不可用作窗口标题」的形态(如根目录、驱动器根) —— 此时去枚举
    旧窗口标题纯属空转, 必须走 `if names:` 假弧直接进超时判定。
    """
    monkeypatch.setattr(utils, "_EXPLORER_FG_TIMEOUT", 0.01)
    monkeypatch.setattr(utils, "_EXPLORER_FG_POLL", 0.005)
    monkeypatch.setattr(utils, "_win_reuse_title_candidates", lambda target: set())
    monkeypatch.setattr(utils, "_win_explorer_hwnds", lambda: set())
    matched = mock.MagicMock(return_value=7)
    monkeypatch.setattr(utils, "_win_match_reused_explorer", matched)
    assert utils._win_wait_explorer({1, 2}, "C:/") is None
    assert matched.call_count == 0, "无候选名不该去匹配旧窗口"


def test_win_foreground_explorer_async_spawns_daemon_thread(monkeypatch):
    """置前后台化: 调用方(WebUI 端点/托盘菜单)立刻返回, 找窗口在 daemon 线程里做

    用 Event 等线程真跑完 —— 不断言「线程对象已创建」, 否则线程根本没启动也全绿(假绿)。
    """
    done = threading.Event()
    seen = []

    def _fake(before, target):
        seen.append((before, target))
        done.set()
        return True

    monkeypatch.setattr(utils, "_win_foreground_new_explorer", _fake)
    utils._win_foreground_explorer_async({1}, "dir")
    assert done.wait(2.0), "后台线程必须真的执行置前动作"
    assert seen == [({1}, "dir")]
