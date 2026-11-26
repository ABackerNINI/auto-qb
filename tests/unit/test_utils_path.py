"""test_utils_path 测试计划: utils 工具函数

## 测试计划(每个测试函数一条)
- test_add_long_path_prefix_for_win: Windows 长路径前缀
- test_atomic_write_creates_file: 原子写生成目标文件且不残留临时文件
- test_atomic_write_rejects_empty_path: 空路径直接 ValueError(否则临时文件落到 CWD 的父目录)
- test_atomic_write_failure_keeps_old_content: 写盘回调抛异常时旧内容不变(直写 open("w") 会先 truncate 成半截文件), 临时文件被清理
- test_atomic_write_replace_retries_transient_denial: 换名被瞬时拒绝(WinError 5, 读者/杀软持句柄)时退避重试可穿过, 到成功即止
- test_atomic_write_replace_retry_exhausted_raises_and_keeps_old: 重试耗尽仍抛不吞(次数按单点常量), 旧内容完好 + 临时文件清理
- test_atomic_write_replace_only_retries_permission_error: 只重试 PermissionError, 其它 OSError(磁盘满)一次即抛不白等
- test_atomic_write_keep_backup: keep_backup=True 写盘前复制 .bak; 无旧文件时不凭空造备份
- test_add_long_path_prefix_unc: UNC 路径 -> \\?\\UNC 前缀
- test_add_long_path_prefix_already_prefixed: 已加前缀 -> 原样返回
- test_path_normalize_empty: 空路径 -> 原样返回
- test_path_normalize_keeps_unc_boundary: UNC 开头双斜杠豁免压缩(R2#30), 其余重复斜杠照常压缩

### P1 覆盖率提升轮: infra 长尾
- test_atomic_write_backup_failure_continues: 备份失败只 WARNING, 写盘照常
- test_atomic_write_failure_cleans_temp_and_reraises: 写盘中途失败清理临时文件并上抛
- test_long_path_prefix_relative_path: 相对路径先转绝对再加前缀
- test_exists_dir_file_apply_long_path_prefix: _exists_dir/_exists_file 对判定过长路径前缀 helper
- test_atomic_write_failure_cleanup_arcs: 失败清理两边缘(临时文件已不在则不删 / 删临时文件失败只吞掉, 原始异常照抛)
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


def test_add_long_path_prefix_for_win(monkeypatch):
    """Windows 平台: 超长/短路径均加 \\\\?\\ 前缀 (monkeypatch 模拟 win32, 与 CI Linux 平台无关)"""
    monkeypatch.setattr(sys, "platform", "win32")
    long_path = r"C:\a" + "\\" + "x" * 300
    prefixed = utils.add_long_path_prefix_for_win(long_path)
    assert prefixed.startswith("\\\\?\\"), f"超长路径应加前缀: {prefixed}"
    short_path = r"C:\short"
    assert utils.add_long_path_prefix_for_win(short_path).startswith("\\\\?\\"), "短路径也加前缀"


def test_add_long_path_prefix_unc(monkeypatch):
    """Windows 平台: UNC 路径 -> \\?\\UNC 前缀 (monkeypatch 模拟 win32)"""
    monkeypatch.setattr(sys, "platform", "win32")
    p = r"\\server\share\file"
    result = utils.add_long_path_prefix_for_win(p)
    assert result == r"\\?\UNC\server\share\file"


def test_add_long_path_prefix_already_prefixed(monkeypatch):
    """Windows 平台: 已加 \\?\\ 前缀 -> 原样返回 (monkeypatch 模拟 win32)"""
    monkeypatch.setattr(sys, "platform", "win32")
    p = r"\\?\C:\x"
    assert utils.add_long_path_prefix_for_win(p) == p


def test_path_normalize_empty():
    """空路径 -> 原样返回"""
    assert utils.path_normalize("") == ""


def test_path_normalize_keeps_unc_boundary():
    """UNC 开头双斜杠豁免压缩(R2#30): `\\\\NAS\\share` 折成 `//NAS/share` 后必须保留 `//` 根边界

    旧实现 `re.sub(r'/{2,}', '/', ...)` 把开头双斜杠也压掉 -> `/NAS/share/dl` 在 Windows
    宿主侧被当相对路径拼到 cwd 所在盘根下, POSIX 侧本就是绝对路径不发生拼接 —— 两种宿主
    都触达不了 UNC 目标本体。其余位置的重复斜杠与三斜杠以上开头(收敛到两个, 保持 UNC
    形状)照常归一。
    """
    assert utils.path_normalize(r"\\NAS\share\dl") == "//NAS/share/dl"
    assert utils.path_normalize("//NAS//share//dl") == "//NAS/share/dl"
    assert utils.path_normalize("///NAS/share") == "//NAS/share"
    assert utils.path_normalize("////NAS") == "//NAS"
    assert utils.path_normalize("//") == "//"
    # 非 UNC 形状的既有行为不变(盘符 / POSIX 绝对 / 中段压缩 / 首尾斜杠保留)
    assert utils.path_normalize("R://Seeds///A") == "R:/Seeds/A"
    assert utils.path_normalize("/mnt//media/") == "/mnt/media/"
    assert utils.path_normalize("a//b///c") == "a/b/c"


def test_exists_dir_file_apply_long_path_prefix(tmp_path, monkeypatch):
    """`_exists_dir` / `_exists_file` 的判定必须过 `add_long_path_prefix_for_win`

    长路径判定不前缀化会恒为 False(实测 `isdir` 给假) ⇒ 端点误报 404。这里用 spy 钉住
    "确实调了前缀 helper", 而不是断言真实 Windows 行为(CI 跑在 Linux)。
    """
    spy = mock.Mock(side_effect=lambda p: p)
    monkeypatch.setattr(utils, "add_long_path_prefix_for_win", spy)
    assert utils._exists_dir(str(tmp_path)) is True
    assert utils._exists_file(str(tmp_path / "x")) is False
    assert spy.call_args_list == [mock.call(str(tmp_path)), mock.call(str(tmp_path / "x"))]


def test_atomic_write_creates_file(tmp_path):
    """原子写: 内容落到目标路径, 且同目录不残留临时文件"""
    from auto_qb.infra.utils import atomic_write

    p = tmp_path / "state.json"
    atomic_write(str(p), lambda f: f.write('{"a": 1}'))
    assert p.read_text(encoding="utf-8") == '{"a": 1}'
    assert sorted(c.name for c in tmp_path.iterdir()) == ["state.json"], "临时文件必须已被替换/清理"


def test_atomic_write_failure_keeps_old_content(tmp_path):
    """写盘回调抛异常时旧内容保持不变 —— 这是原子写存在的全部理由

    直接 `open(path, "w")` 会先 truncate: 写盘途中被杀/磁盘满/序列化异常都会留下**半截文件**,
    而 state.json 没有备份 ⇒ 执行历史与去重记录全丢, 重启后规则重放。
    """
    from auto_qb.infra.utils import atomic_write

    def _boom(_f):
        raise RuntimeError("simulated write failure")

    p = tmp_path / "state.json"
    p.write_text("OLD", encoding="utf-8")
    with pytest.raises(RuntimeError):
        atomic_write(str(p), _boom)
    assert p.read_text(encoding="utf-8") == "OLD", "失败时旧内容必须完好"
    assert sorted(c.name for c in tmp_path.iterdir()) == ["state.json"], "失败的临时文件必须清理"


def test_atomic_write_replace_retries_transient_denial(tmp_path, monkeypatch):
    """换名被**瞬时拒绝**时退避重试 —— Windows 上读者持目标文件即抛 WinError 5

    坑档 `pitfalls/backend/platform-fs.md`「Windows 原子写与并发读者的双向瞬时拒绝」: 读者
    (含杀软/索引器/另一进程)开-读-关的微秒~毫秒窗口内 `MoveFileEx` 拒绝替换, 不是持久故障。
    2026-10-16 用户实报 HR 实例注册表心跳一次性失败(`instances.json.o7e7o6ed.tmp` ->
    `instances.json`)即此坑的写侧 —— 主仓当时的 `atomic_write` 没有这层重试(gtm 工具侧已有)。

    S3 monkeypatch 收敛(2026-11-05): sleep 桩解包, 退避(50ms × 2)真实发生 —— utils.time
    是 stdlib time 模块对象, 经它 patch 即进程级改写(第一半「真实退避」先例同款)。
    """
    attempts = []
    real_replace = os.replace

    def flaky_replace(src, dst):
        attempts.append(1)
        if len(attempts) <= 2:
            raise PermissionError(13, "拒绝访问", dst)
        return real_replace(src, dst)

    monkeypatch.setattr(utils.os, "replace", flaky_replace)

    p = tmp_path / "state.json"
    utils.atomic_write(str(p), lambda f: f.write("NEW"))
    assert p.read_text(encoding="utf-8") == "NEW", "两次被拒后第三次必须落地"
    assert len(attempts) == 3, "重试到成功即止(不白跑满次数)"


def test_atomic_write_replace_retry_exhausted_raises_and_keeps_old(tmp_path, monkeypatch):
    """重试耗尽仍抛 PermissionError(不吞)、旧内容不变、临时文件清理 —— 容错口径留给调用方

    S3 monkeypatch 收敛(2026-11-05): sleep 桩解包, 退避(50ms × 4)真实发生 —— utils.time
    是 stdlib time 模块对象, 经它 patch 即进程级改写(第一半「真实退避」先例同款)。
    """
    attempts = []

    def always_denied(src, dst):
        attempts.append(1)
        raise PermissionError(13, "拒绝访问", dst)

    monkeypatch.setattr(utils.os, "replace", always_denied)

    p = tmp_path / "state.json"
    p.write_text("OLD", encoding="utf-8")
    with pytest.raises(PermissionError):
        utils.atomic_write(str(p), lambda f: f.write("NEW"))
    assert len(attempts) == utils.REPLACE_RETRY_ATTEMPTS, "重试次数按单点常量(改常量即改行为)"
    assert p.read_text(encoding="utf-8") == "OLD", "失败时旧内容必须完好(半截文件是原子写存在的全部理由)"
    assert sorted(c.name for c in tmp_path.iterdir()) == ["state.json"], "耗尽后临时文件必须清理"


def test_atomic_write_replace_only_retries_permission_error(tmp_path, monkeypatch):
    """只重试 PermissionError: 其它 OSError(磁盘满/路径非法)重试不解决, 一次即抛(不白等退避)

    S3 monkeypatch 收敛(2026-11-05): `utils.time.sleep` 的 pytest.fail 桩解包 —— utils.time
    是 stdlib time 模块对象, 经它 patch 即进程级改写; 「非 PermissionError 不退避」由下方
    `len(attempts) == 1` 结构性证明(退避只在两次重试之间, 一次即抛则零退避)。
    """
    attempts = []

    def other_oserror(src, dst):
        attempts.append(1)
        raise OSError(28, "磁盘空间不足")

    monkeypatch.setattr(utils.os, "replace", other_oserror)
    with pytest.raises(OSError):
        utils.atomic_write(str(tmp_path / "state.json"), lambda f: f.write("x"))
    assert len(attempts) == 1, "非瞬时错误必须早抛"


def test_atomic_write_rejects_empty_path():
    """空路径直接 ValueError: 否则临时文件会落到 **CWD 的父目录**(仓库外)

    回归点(2026-09-19): `abspath("")` 是 CWD, 再 `dirname` 就是它的父目录 —— 空路径不会
    "什么都不写", 而是往仓库外面丢 `.xxxxxxxx.tmp`, 然后 `os.replace(tmp, "")` 失败再删掉,
    表现为"偶发、无害"的噪音(长期被误当成 IDE/工具产生的临时文件), 实为调用方漏传路径。
    """
    from auto_qb.infra.utils import atomic_write

    with pytest.raises(ValueError):
        atomic_write("", lambda f: f.write("x"))


def test_atomic_write_keep_backup(tmp_path):
    """keep_backup=True: 写盘前把当前文件复制为 .bak; 无旧文件时不凭空造备份

    备份路径一律按 `path + utils.BACKUP_SUFFIX` 断言(不写字面量): 后缀是写侧与 state 恢复侧
    共用的单点常量, 一旦有人在 atomic_write 里改回字面量, 这条就红 —— 否则两边命名漂移,
    备份写出去没人按同名读回来(issue 26-09-21-1347)。
    """
    from auto_qb.infra.utils import atomic_write

    p = tmp_path / "state.json"
    bak = tmp_path / ("state.json" + utils.BACKUP_SUFFIX)
    atomic_write(str(p), lambda f: f.write("NEW"), keep_backup=True)
    assert not bak.exists(), "无旧文件不应产生备份"

    atomic_write(str(p), lambda f: f.write("NEWER"), keep_backup=True)
    assert bak.read_text(encoding="utf-8") == "NEW"
    assert p.read_text(encoding="utf-8") == "NEWER"


def test_atomic_write_backup_failure_continues(tmp_path, monkeypatch):
    """keep_backup 时备份失败(如权限) -> 只 WARNING, 写盘照常进行(不因备份失败丢新数据)"""
    target = tmp_path / "state.json"
    target.write_text("old", encoding="utf-8")

    def boom(src, dst):
        raise OSError(13, "拒绝访问")

    monkeypatch.setattr(utils.shutil, "copy2", boom)
    utils.atomic_write(str(target), lambda f: f.write("new"), keep_backup=True)
    assert target.read_text(encoding="utf-8") == "new"


def test_atomic_write_failure_cleans_temp_and_reraises(tmp_path):
    """写盘中途失败 -> 临时文件清理 + 原异常上抛(不留半截文件)"""
    target = tmp_path / "state.json"

    def bad_write(f):
        raise ValueError("序列化炸了")

    with pytest.raises(ValueError):
        utils.atomic_write(str(target), bad_write)
    assert list(tmp_path.iterdir()) == [], "临时文件已清理"
    assert not target.exists()


def test_long_path_prefix_relative_path(tmp_path, monkeypatch):
    """相对路径 -> 先转绝对再加前缀(与已绝对路径不同径)

    相对分支只在 `is_windows()` 为真时可达 ⇒ 必须 monkeypatch 平台 ——
    否则在 Linux CI 上函数原样返回入参, 前缀断言必红(见 testing/file-conventions.md)。
    """
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.chdir(tmp_path)
    out = utils.add_long_path_prefix_for_win("sub/dir/file.bin")
    assert out.startswith("\\\\?\\") and "sub/dir" in out.replace("\\", "/")


def test_atomic_write_failure_cleanup_arcs(tmp_path, monkeypatch):
    """atomic_write 失败清理的两条边缘: 1. 临时文件已不在时不删(少一次无谓 IO);
    2. 删临时文件本身失败(占用/权限)只吞掉, **绝不掩盖原始异常**

    1. 对应 `os.replace` 已成功后的形态; 2. 对应 Windows 上杀毒/索引器短暂占用临时文件的形态 ——
    清理是尽力而为, 调用方要看到的永远是「写盘中断」这个真原因。
    """
    target = str(tmp_path / "out.txt")

    def _boom(f):
        raise RuntimeError("写盘中断")

    # 1. exists 恒假 -> `if os.path.exists(tmp_path)` 假弧, 直接 re-raise
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    with pytest.raises(RuntimeError, match="写盘中断"):
        utils.atomic_write(target, _boom)
    monkeypatch.undo()

    # 2. 删不掉 -> OSError 吞掉, 原始异常照抛
    def _remove_boom(p):
        raise OSError(13, "locked")

    monkeypatch.setattr(os, "remove", _remove_boom)
    with pytest.raises(RuntimeError, match="写盘中断"):
        utils.atomic_write(target, _boom)
    monkeypatch.undo()

    for leaked in tmp_path.iterdir():  # 2. 故意删不掉, 手工清残骸
        leaked.unlink()
