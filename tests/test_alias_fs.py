"""test_alias_fs 测试计划: infra/alias_fs 链接能力探测(plan 26-10-18-1604 实施期 P0)

## 测试计划(每个测试函数一条)
- test_probe_symlink_file_ok: 真建文件符号链接 -> 可见 + 穿透读一致〔无 symlink 建链能力的环境 skip〕
- test_probe_symlink_dir_ok: 真建目录符号链接 -> 可穿透列目录〔无 symlink 建链能力的环境 skip〕
- test_probe_symlink_injected_permission_error: 注入 `OSError(winerror=1314)`(§8.6 唯一注入点)
  -> 判「需提权」, 走的是生产分支
- test_probe_symlink_injected_invisible: 注入「调用成功但没建出链接」的替身 -> 判不可用(返回成功不算数)
- test_probe_hardlink_ok: 真建硬链接 -> 同 inode + nlink>=2
- test_probe_hardlink_injected_failure: 注入失败 -> 判不可用
- test_probe_junction_platform: Windows 真建 junction 成功; 非 Windows 明确「仅 Windows」而不是静默 False
- test_probe_leaves_no_residue: 四次探测跑完, work_dir 里不留探测临时目录
- test_probe_symlink_penetration_failures: 建出来但读不到(悬空 / 内容不符 / 目录缺探测文件)三种都判不可用〔无 symlink 建链能力的环境 skip〕
- test_probe_junction_injected: 注入建 junction 失败与「什么都没建」两种替身, 各自给出正确原因(仅 Windows)
- test_probe_hardlink_not_same_inode: 调用不报错但建的是副本(部分网络盘/FUSE) -> 判不可用
- test_classify_link_failure_order: 1314 二义性 —— 先按路径长度(>=260 判长路径), 再按错误码判提权
- test_capability_ladder: 形态阶梯(junction->symlink; Windows 同卷硬链接优先 / POSIX symlink 优先)
- test_capability_blocks_when_link_invisible: link_visible_to_host=False 时两种形态都不可用(跨 OS 反例)
- test_platform_verdict_rows: §3.3 七行能力矩阵逐行落位(row/supported)
- test_platform_verdict_unsupported_reason: 全不可用时 supported=False 且原因里带上各探测错误
- test_same_volume_and_free: 同卷 True / 不可读 None(不可判定, 不是 False); 剩余空间可读与不可读
- test_is_unc: UNC 判定(含 `\\\\?\\` 与 `\\\\.\\` 设备前缀不算 UNC)
- test_container_evidence: 环境变量 / 哨兵文件 / cgroup 三路证据(含 `container=0` 不算)
- test_is_wsl: env 与 /proc/version 两路判定
- test_mount_info_and_windows_backed: /proc/mounts 解析(最长前缀 + 八进制转义)与 Windows 共享挂载识别
  (drvfs 标记 / WSL 的 /mnt/<盘符>; 非盘符挂载不算)
- test_alias_primitives: create_file_alias 硬链接 + alias_kind_of/alias_target 对普通文件/缺失路径的判定 + 形态错配 ValueError(不依赖建链能力, 任何环境都跑)
- test_alias_primitives_symlink: create_dir_alias/create_file_alias 的 symlink 形态往返(建/识/穿透读/删)〔无 symlink 建链能力的环境 skip〕
- test_junction_roundtrip: Windows 真建 junction -> 形态识别 + 穿透读 + 删链接不动目标(非 Windows 跳过)
- test_remove_alias_does_not_follow_target: 删别名只删链接本身, 目标数据原封不动〔无 symlink 建链能力的环境 skip〕
- test_capability_cache_and_refresh: 缓存命中同一对象; refresh / reset 各自生效
- test_probe_capability_never_raises: 探测目录建不出来 -> 降级为不可用, 不抛异常(不炸启动)
- test_as_dict_shape: 界面用的扁平字典键齐全且可 JSON 序列化
- test_process_os_mapping: 进程 OS 映射(windows/linux/darwin/posix 四支, 走 utils.is_* 单点)
- test_read_text_missing_returns_empty: 小文本读取(读得到取内容 / 读不到空串, 不抛)
- test_probe_hardlink_unreadable_after_create: 建出来但 stat 不到(悬空) -> 判不可用〔无 symlink 建链能力的环境 skip〕
- test_probe_junction_unreadable: junction 目标里没有探测文件 -> 判不可用(仅 Windows)
- test_probe_capability_notes_foreign_mount: 整机探测在 WSL-on-NTFS 现场 -> 宿主/进程 OS 不一致、
  链接宿主读不了、verdict 落 container_cross_os
- test_probe_capability_degrades_on_probe_crash: 探测抛异常 -> 四项全判不可用, 不炸启动
- test_probe_capability_uac_note: 文件级 symlink 需提权时备注写明提权通道可用性
- test_uac_available_swallows_error: 提权通道探测: 非 Windows 恒 False; 取窗口站抛错 -> False

## 环境能力 skip(2026-10-18, issue 26-10-18-2030)

真实建符号链接类用例依赖**宿主建链能力**: Windows 非特权进程(非管理员且未开开发者模式)缺
SeCreateSymbolicLinkPrivilege, `os.symlink` 抛 WinError 1314; 少数重定向层还会"假成功"(不抛异常
但建不出链接)。按 file-conventions.md「测试不得依赖宿主环境能力」, 这类用例在无能力环境
**skip 而非 fail**(准入标记 `_SYMLINK_REQUIRED`; 判据同 `test_file_access._dir_symlink_or_skip`:
试建 + 复核 islink + 穿透读, 只 catch 异常不够)。注入替身(`try_create=...`)的用例不碰真实建链,
任何环境照常跑; 有建链能力的环境(管理员/开发者模式/Linux/macOS)全部真实执行, 覆盖不缩水。
"""
import json
import os
import tempfile

import pytest

from auto_qb.infra import alias_fs, utils
from auto_qb.infra.alias_fs import (
    KIND_HARDLINK,
    KIND_JUNCTION,
    KIND_SYMLINK,
    AliasCapability,
    LinkProbe,
    probe_capability,
    probe_hardlink,
    probe_junction,
    probe_symlink,
)

_WIN_ONLY = pytest.mark.skipif(not utils.is_windows(), reason="junction 仅 Windows")


def _probe_symlink_capability() -> bool:
    """本进程能否真建符号链接并穿透读: 试建 -> 复核 islink -> 读回内容, 用完清理

    Windows 非特权进程缺 SeCreateSymbolicLinkPrivilege 时 `os.symlink` 抛 WinError 1314;
    少数重定向层还会"假成功"(不抛异常但建不出链接)。判据与
    `test_file_access._dir_symlink_or_skip` 同源 —— 只 catch 异常不够, 必须复核 islink
    (file-conventions.md「测试不得依赖宿主环境能力」, issue 26-10-18-2030)。
    """
    with tempfile.TemporaryDirectory(prefix="auto-qb-symlink-probe-") as tmp:
        target = os.path.join(tmp, "target")
        link = os.path.join(tmp, "link")
        with open(target, "w", encoding="utf-8") as f:
            f.write("auto-qb")
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError, AttributeError):
            return False
        try:
            with open(link, encoding="utf-8") as f:
                return os.path.islink(link) and f.read() == "auto-qb"
        except OSError:
            return False


# 真实建链类用例的准入: 宿主无 symlink 能力时 skip 而非 fail(环境能力缺失不是代码缺陷)
_SYMLINK_REQUIRED = pytest.mark.skipif(
    not _probe_symlink_capability(),
    reason="本进程建不出符号链接(如 Windows 非特权缺 SeCreateSymbolicLinkPrivilege, os.symlink 报 WinError 1314): "
    "真实建链覆盖需以管理员身份运行或开开发者模式; 注入替身覆盖不受影响",
)


def _win_error(code: int, message: str = "denied") -> OSError:
    """造一个带 winerror 的 OSError(ctypes.WinError 只在 Windows 可用, 测试要跨平台)"""
    err = OSError(message)
    err.winerror = code
    return err


def _cap(**over) -> AliasCapability:
    """造一份能力事实(纯逻辑测试用; 不跑任何 syscall)"""
    base = dict(
        process_os="windows",
        host_os="windows",
        container=False,
        wsl=False,
        path_style="windows",
        foreign_fs=None,
        link_visible_to_host=True,
        junction=LinkProbe(True, detail="junction"),
        dir_symlink=LinkProbe(True, detail="dir symlink"),
        file_symlink=LinkProbe(True, detail="file symlink"),
        hardlink=LinkProbe(True, detail="hardlink"),
        uac_available=True,
        probe_root="C:/Temp",
        probed_at=0.0,
        notes=(),
    )
    base.update(over)
    return AliasCapability(**base)


# ---------------------------------------------------------------- 单项探测


@_SYMLINK_REQUIRED
def test_probe_symlink_file_ok(tmp_path):
    probe = probe_symlink(str(tmp_path), target_is_directory=False)
    assert probe.ok, probe.error
    assert "符号链接" in probe.detail


@_SYMLINK_REQUIRED
def test_probe_symlink_dir_ok(tmp_path):
    probe = probe_symlink(str(tmp_path), target_is_directory=True)
    assert probe.ok, probe.error


def test_probe_symlink_injected_permission_error(tmp_path):
    def deny(*args, **kwargs):
        raise _win_error(alias_fs.ERROR_PRIVILEGE_NOT_HELD)

    probe = probe_symlink(str(tmp_path), target_is_directory=False, try_create=deny)
    assert not probe.ok
    assert "提权" in probe.error


def test_probe_symlink_injected_invisible(tmp_path):
    def pretend(*args, **kwargs):
        return None  # 调用「成功」但什么都没建出来(实测 ctypes 直调就是这种表现)

    probe = probe_symlink(str(tmp_path), target_is_directory=False, try_create=pretend)
    assert not probe.ok
    assert "不可见" in probe.error


def test_probe_hardlink_ok(tmp_path):
    probe = probe_hardlink(str(tmp_path))
    assert probe.ok, probe.error
    assert "硬链接" in probe.detail


def test_probe_hardlink_injected_failure(tmp_path):
    def deny(*args, **kwargs):
        raise OSError("cross device")

    probe = probe_hardlink(str(tmp_path), try_create=deny)
    assert not probe.ok
    assert probe.error


def test_probe_junction_platform(tmp_path):
    probe = probe_junction(str(tmp_path))
    if utils.is_windows():
        assert probe.ok, probe.error
        assert "junction" in probe.detail
    else:
        assert not probe.ok
        assert "仅 Windows" in probe.error


def test_probe_leaves_no_residue(tmp_path):
    probe_junction(str(tmp_path))
    probe_symlink(str(tmp_path), target_is_directory=True)
    probe_symlink(str(tmp_path), target_is_directory=False)
    probe_hardlink(str(tmp_path))
    left = [n for n in os.listdir(tmp_path) if n.startswith(".auto-qb-alias-probe-")]
    assert left == []


@_SYMLINK_REQUIRED
def test_probe_symlink_penetration_failures(tmp_path):
    """建出来了但读不到: 悬空链接 / 内容不符 / 目录里没有探测文件 —— 三种都判不可用"""
    def dangling(target, link, target_is_directory=False):
        os.symlink(target + "-missing", link, target_is_directory=target_is_directory)

    probe = probe_symlink(str(tmp_path), target_is_directory=False, try_create=dangling)
    assert not probe.ok and "穿透读取" in probe.error

    def wrong_content(target, link, target_is_directory=False):
        other = os.path.join(os.path.dirname(link), "other.txt")
        with open(other, "w", encoding="utf-8") as f:
            f.write("not auto-qb")
        os.symlink(other, link)

    probe = probe_symlink(str(tmp_path), target_is_directory=False, try_create=wrong_content)
    assert not probe.ok and "内容不符" in probe.error

    def empty_dir(target, link, target_is_directory=False):
        other = os.path.join(os.path.dirname(link), "other-dir")
        os.mkdir(other)
        os.symlink(other, link, target_is_directory=True)

    probe = probe_symlink(str(tmp_path), target_is_directory=True, try_create=empty_dir)
    assert not probe.ok and "穿透读取" in probe.error


@_WIN_ONLY
def test_probe_junction_injected(tmp_path):
    def deny(link, target):
        raise OSError(5, "denied")

    probe = probe_junction(str(tmp_path), try_create=deny)
    assert not probe.ok and "建链失败" in probe.error

    def nothing(link, target):
        return None

    probe = probe_junction(str(tmp_path), try_create=nothing)
    assert not probe.ok and "不是 junction" in probe.error


def test_probe_hardlink_not_same_inode(tmp_path):
    """调用没报错但建的是副本(部分网络盘/FUSE 就是这样): 必须判不可用, 不能当真链接"""
    def copy_instead(src, dst):
        with open(src, "rb") as f:
            data = f.read()
        with open(dst, "wb") as f:
            f.write(data)

    probe = probe_hardlink(str(tmp_path), try_create=copy_instead)
    assert not probe.ok and "inode" in probe.error


# ---------------------------------------------------------------- 失败归因


def test_classify_link_failure_order(tmp_path):
    long_path = os.path.join(str(tmp_path), "x" * 300)
    long_message = alias_fs.classify_link_failure(long_path, _win_error(alias_fs.ERROR_PRIVILEGE_NOT_HELD))
    short_message = alias_fs.classify_link_failure(os.path.join(str(tmp_path), "short"), _win_error(1314))
    if utils.is_windows():
        # 1314 二义性: 长路径必须先判长路径, 否则用户提权后依旧失败
        assert "路径过长" in long_message
    else:
        assert "提权" in long_message
    assert "提权" in short_message
    assert "提权" in alias_fs.classify_link_failure(os.path.join(str(tmp_path), "short"), OSError(1, "denied"))
    assert "建链失败" in alias_fs.classify_link_failure(os.path.join(str(tmp_path), "short"), OSError(5, "other"))


# ---------------------------------------------------------------- 形态阶梯与能力矩阵


def test_capability_ladder():
    win = _cap()
    assert win.dir_alias_kind == KIND_JUNCTION
    assert win.file_alias_kind(True) == KIND_HARDLINK
    assert win.file_alias_kind(False) == KIND_SYMLINK

    no_junction = _cap(junction=LinkProbe(False, error="junction 不可建"))
    assert no_junction.dir_alias_kind == KIND_SYMLINK

    nothing = _cap(junction=LinkProbe(False, error="x"), dir_symlink=LinkProbe(False, error="x"))
    assert nothing.dir_alias_kind is None

    posix = _cap(process_os="linux", host_os="linux", path_style="posix", junction=LinkProbe(False, error="x"))
    assert posix.dir_alias_kind == KIND_SYMLINK
    assert posix.file_alias_kind(True) == KIND_SYMLINK  # POSIX 先 symlink
    assert posix.file_alias_kind(False) == KIND_SYMLINK

    posix_no_symlink = _cap(
        process_os="linux",
        host_os="linux",
        path_style="posix",
        junction=LinkProbe(False, error="x"),
        dir_symlink=LinkProbe(False, error="x"),
        file_symlink=LinkProbe(False, error="x")
    )
    assert posix_no_symlink.file_alias_kind(True) == KIND_HARDLINK
    assert posix_no_symlink.file_alias_kind(False) is None


def test_capability_blocks_when_link_invisible():
    cap = _cap(process_os="linux", host_os="windows", container=True, foreign_fs="drvfs", link_visible_to_host=False)
    assert cap.dir_alias_kind is None
    assert cap.file_alias_kind(True) is None
    assert cap.file_alias_kind(False) is None


def test_platform_verdict_rows():
    rows = [
        (_cap(), {}, "windows_local", True),
        (_cap(), {
            "target_is_unc": True
        }, "windows_unc", True),
        (
            _cap(process_os="linux", host_os="linux", path_style="posix",
                 junction=LinkProbe(False, error="x")), {}, "linux", True
        ),
        (
            _cap(process_os="darwin", host_os="darwin", path_style="posix",
                 junction=LinkProbe(False, error="x")), {}, "darwin", True
        ),
        (_cap(container=True), {}, "container_same_os", True),
        (
            _cap(process_os="linux", host_os="windows", container=True, foreign_fs="drvfs",
                 link_visible_to_host=False), {}, "container_cross_os", False
        ),
        (_cap(process_os="linux", host_os="linux"), {
            "remote": True
        }, "remote_no_shared_fs", False),
        (_cap(process_os="freebsd", host_os="freebsd", path_style="posix"), {}, "unknown", True),
    ]
    for cap, kwargs, row, supported in rows:
        verdict = alias_fs.platform_verdict(cap, **kwargs)
        assert verdict.row == row, (row, verdict)
        assert verdict.supported is supported, (row, verdict)
        assert verdict.reason


def test_platform_verdict_unsupported_reason():
    cap = _cap(
        junction=LinkProbe(False, error="junction 不可建"),
        dir_symlink=LinkProbe(False, error="目录链接不可建"),
        file_symlink=LinkProbe(False, error="文件链接不可建"),
        hardlink=LinkProbe(False, error="硬链接不可建")
    )
    verdict = alias_fs.platform_verdict(cap, same_volume=True)
    assert not verdict.supported
    assert verdict.dir_alias is None and verdict.file_alias is None
    for fragment in ("junction 不可建", "目录链接不可建", "文件链接不可建"):
        assert fragment in verdict.reason


# ---------------------------------------------------------------- 平台事实


def test_same_volume_and_free(tmp_path):
    assert alias_fs.same_volume(str(tmp_path), str(tmp_path)) is True
    assert alias_fs.same_volume(str(tmp_path), str(tmp_path / "missing")) is None  # 不可判定 != 不同卷
    assert alias_fs.volume_free(str(tmp_path)) > 0
    assert alias_fs.volume_free(str(tmp_path / "missing")) is None


def test_is_unc():
    assert alias_fs.is_unc(r"\\nas\share\movie")
    assert alias_fs.is_unc("//nas/share/movie")
    assert not alias_fs.is_unc(r"C:\Download")
    assert not alias_fs.is_unc("/mnt/downloads")
    assert not alias_fs.is_unc(r"\\?\C:\Download")
    assert not alias_fs.is_unc(r"\\.\PhysicalDrive0")


def test_container_evidence():
    assert alias_fs.container_evidence(env={}, exists=lambda p: False, read_text=lambda p: "") == ()
    env_hit = alias_fs.container_evidence(env={"container": "docker"}, exists=lambda p: False, read_text=lambda p: "")
    assert env_hit and "container" in env_hit[0]
    assert alias_fs.container_evidence(env={"container": "0"}, exists=lambda p: False, read_text=lambda p: "") == ()
    sentinel = alias_fs.container_evidence(env={}, exists=lambda p: p == "/.dockerenv", read_text=lambda p: "")
    assert any("dockerenv" in item for item in sentinel)
    cgroup = alias_fs.container_evidence(
        env={}, exists=lambda p: False, read_text=lambda p: "12:pids:/kubepods/burstable/pod1\n"
    )
    assert any("kubepods" in item for item in cgroup)


def test_is_wsl():
    assert alias_fs.is_wsl(env={"WSL_DISTRO_NAME": "Ubuntu-26.04"})
    assert alias_fs.is_wsl(env={"WSL_INTEROP": "/run/WSL/1_interop"})
    assert alias_fs.is_wsl(env={}, proc_version="Linux version 6.18.33.2-microsoft-standard-WSL2")
    assert not alias_fs.is_wsl(env={}, proc_version="Linux version 6.8.0-generic")


_MOUNTS = (
    "none /mnt/wsl tmpfs rw,relatime 0 0\n"
    "/dev/sde / ext4 rw,relatime 0 0\n"
    "C:\\134 /mnt/c 9p rw,noatime,aname=drvfs;path=C:\\;uid=1000 0 0\n"
    "Z: /mnt/z drvfs rw,noatime 0 0\n"
    "//nas/share /mnt/y 9p rw 0 0\n"
    "dev /mnt/my\\040disk ext4 rw 0 0\n"
    "malformed-line\n"
)


def test_mount_info_and_windows_backed():
    info = alias_fs.mount_info_for_path("/mnt/c/Download", _MOUNTS)
    assert info is not None and info.fstype == "9p" and info.mount_point == "/mnt/c"
    # 最长前缀: /mnt/wslg 未被匹配时落到 /mnt/wsl 的兄弟挂载上, 不能串到 /
    assert alias_fs.mount_info_for_path("/mnt/wsl/x", _MOUNTS).mount_point == "/mnt/wsl"
    # 八进制转义: 路径带空格也要匹配得上
    assert alias_fs.mount_info_for_path("/mnt/my disk/x", _MOUNTS).mount_point == "/mnt/my disk"
    # 无匹配时落到根挂载; 挂载表读不到时返回 None(不可判定)
    assert alias_fs.mount_info_for_path("/nope/x", _MOUNTS).mount_point == "/"
    assert alias_fs.mount_info_for_path("/nope/x", "") is None

    # WSL 的 Windows 盘: 9p + aname=drvfs 与 /mnt/<盘符> 两条判据都要认
    assert alias_fs.windows_backed_mount("/mnt/c/Download", _MOUNTS, wsl=True).is_drvfs
    assert alias_fs.windows_backed_mount("/mnt/z/x", _MOUNTS, wsl=True) is not None
    # 非盘符挂载(/mnt/wsl)不是 Windows 盘; 非 WSL 环境不按盘符猜
    assert alias_fs.windows_backed_mount("/mnt/wsl/x", _MOUNTS, wsl=True) is None
    assert alias_fs.windows_backed_mount("/mnt/c/Download", _MOUNTS, wsl=False).is_drvfs  # drvfs 标记仍成立
    # drvfs 标记本身就是结论(不依赖 wsl 探测); 无标记的 9p 只在 WSL 的 /mnt/<盘符> 上才认
    assert alias_fs.windows_backed_mount("/mnt/z/x", _MOUNTS, wsl=False).is_drvfs
    assert alias_fs.windows_backed_mount("/mnt/y/x", _MOUNTS, wsl=True) is not None
    assert alias_fs.windows_backed_mount("/mnt/y/x", _MOUNTS, wsl=False) is None

    # 宿主推断与链接可见性: WSL 的 Windows 盘 = Linux 进程 + Windows 宿主 + 链接宿主读不了
    drvfs = alias_fs.windows_backed_mount("/mnt/c/x", _MOUNTS, wsl=True)
    assert alias_fs._host_os("linux", True, drvfs) == "windows"
    assert alias_fs._host_os("linux", False, None) == "linux"
    assert alias_fs._host_os("windows", False, None) == "windows"
    assert alias_fs._link_visible_to_host("linux", drvfs) is False
    assert alias_fs._link_visible_to_host("linux", None) is True
    assert alias_fs._link_visible_to_host("windows", drvfs) is True


# ---------------------------------------------------------------- 链接原语


@_SYMLINK_REQUIRED
def test_alias_primitives_symlink(tmp_path):
    """链接原语 symlink 形态往返: 目录链接穿透读 + 文件链接读目标, 删链接不动数据"""
    target = tmp_path / "target"
    target.mkdir()
    (target / "a.txt").write_text("auto-qb", encoding="utf-8")
    link = tmp_path / "link"

    alias_fs.create_dir_alias(str(link), str(target), KIND_SYMLINK)
    assert alias_fs.alias_kind_of(str(link)) == KIND_SYMLINK
    assert os.path.realpath(str(link)) == os.path.realpath(str(target))
    assert (link / "a.txt").read_text(encoding="utf-8") == "auto-qb"
    alias_fs.remove_alias(str(link))
    assert not link.exists()

    file_target = tmp_path / "file.bin"
    file_target.write_text("data", encoding="utf-8")
    sym = tmp_path / "sym.bin"
    alias_fs.create_file_alias(str(sym), str(file_target), KIND_SYMLINK)
    assert alias_fs.alias_kind_of(str(sym)) == KIND_SYMLINK
    assert alias_fs.alias_target(str(sym)) is not None
    alias_fs.remove_alias(str(sym))


def test_alias_primitives(tmp_path):
    """链接原语往返(不依赖建链能力): 硬链接同 inode / 普通文件与缺失路径返回 None / 形态错配 ValueError"""
    file_target = tmp_path / "file.bin"
    file_target.write_text("data", encoding="utf-8")
    hard = tmp_path / "hard.bin"
    alias_fs.create_file_alias(str(hard), str(file_target), KIND_HARDLINK)
    assert alias_fs.alias_kind_of(str(hard)) == KIND_HARDLINK
    assert alias_fs.alias_target(str(hard)) is None
    assert os.stat(str(hard)).st_ino == os.stat(str(file_target)).st_ino
    alias_fs.remove_alias(str(hard))
    assert file_target.exists()

    plain = tmp_path / "plain.txt"
    plain.write_text("x", encoding="utf-8")
    assert alias_fs.alias_kind_of(str(plain)) is None
    assert alias_fs.alias_kind_of(str(tmp_path / "absent")) is None
    assert alias_fs.alias_target(str(tmp_path / "absent")) is None
    assert alias_fs.alias_target(str(plain)) is None
    alias_fs.remove_alias(str(tmp_path / "absent"))  # 幂等

    with pytest.raises(ValueError):
        alias_fs.create_dir_alias(str(tmp_path / "x1"), str(tmp_path), KIND_HARDLINK)
    with pytest.raises(ValueError):
        alias_fs.create_file_alias(str(tmp_path / "x2"), str(file_target), KIND_JUNCTION)


@_WIN_ONLY
def test_junction_roundtrip(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "a.txt").write_text("auto-qb", encoding="utf-8")
    link = tmp_path / "junction"
    alias_fs.create_dir_alias(str(link), str(target), KIND_JUNCTION)
    try:
        assert alias_fs.alias_kind_of(str(link)) == KIND_JUNCTION
        assert (link / "a.txt").read_text(encoding="utf-8") == "auto-qb"
    finally:
        alias_fs.remove_alias(str(link))
    assert not link.exists()
    assert (target / "a.txt").exists()  # 删 junction 不动目标数据


@_SYMLINK_REQUIRED
def test_remove_alias_does_not_follow_target(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep.txt").write_text("keep", encoding="utf-8")
    link = tmp_path / "link"
    alias_fs.create_dir_alias(str(link), str(target), KIND_SYMLINK)
    alias_fs.remove_alias(str(link))
    assert not link.exists()
    assert (target / "keep.txt").read_text(encoding="utf-8") == "keep"


# ---------------------------------------------------------------- 整机探测与缓存


def test_capability_cache_and_refresh():
    alias_fs.reset_capability_cache()
    first = alias_fs.get_capability()
    assert alias_fs.get_capability() is first
    refreshed = alias_fs.get_capability(refresh=True)
    assert refreshed is not first
    assert refreshed.probed_at >= first.probed_at
    alias_fs.reset_capability_cache()
    assert alias_fs.get_capability() is not refreshed
    alias_fs.reset_capability_cache()


def test_probe_capability_never_raises(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir", encoding="utf-8")
    cap = probe_capability(str(blocker / "sub"))
    assert isinstance(cap, AliasCapability)
    assert not cap.junction.ok and not cap.dir_symlink.ok and not cap.file_symlink.ok and not cap.hardlink.ok
    assert cap.dir_alias_kind is None
    assert cap.notes


def test_as_dict_shape():
    payload = _cap().as_dict()
    for key in ("process_os", "host_os", "container", "junction", "uac_available", "dir_alias_kind", "notes"):
        assert key in payload
    assert payload["dir_alias_kind"] == KIND_JUNCTION
    json.dumps(payload)  # 必须可序列化(界面/接口直接吃)


# ---------------------------------------------------------------- 平台分支与安全网


def test_process_os_mapping(monkeypatch):
    monkeypatch.setattr(alias_fs.utils, "is_windows", lambda: True)
    assert alias_fs._process_os() == "windows"
    monkeypatch.setattr(alias_fs.utils, "is_windows", lambda: False)
    monkeypatch.setattr(alias_fs.utils, "is_linux", lambda: True)
    assert alias_fs._process_os() == "linux"
    monkeypatch.setattr(alias_fs.utils, "is_linux", lambda: False)
    monkeypatch.setattr(alias_fs.utils, "is_mac", lambda: True)
    assert alias_fs._process_os() == "darwin"
    monkeypatch.setattr(alias_fs.utils, "is_mac", lambda: False)
    assert alias_fs._process_os() == "posix"


def test_read_text_missing_returns_empty(tmp_path):
    target = tmp_path / "a.txt"
    target.write_text("hello", encoding="utf-8")
    assert alias_fs._read_text(str(target)) == "hello"
    assert alias_fs._read_text(str(tmp_path / "absent")) == ""


@_SYMLINK_REQUIRED
def test_probe_hardlink_unreadable_after_create(tmp_path):
    """建出来了但 stat 不到(悬空链接): 判不可用而不是当成功"""
    def dangling(src, dst):
        os.symlink(src + "-missing", dst)

    probe = probe_hardlink(str(tmp_path), try_create=dangling)
    assert not probe.ok and "不可读" in probe.error


@_WIN_ONLY
def test_probe_junction_unreadable(tmp_path):
    """junction 建出来了但目标里没有探测文件: 判不可用"""
    def empty_target(link, target):
        empty = os.path.join(os.path.dirname(target), "empty")
        os.mkdir(empty)
        alias_fs._win_create_junction(link, empty)

    probe = probe_junction(str(tmp_path), try_create=empty_target)
    assert not probe.ok and "穿透读取" in probe.error


def test_probe_capability_notes_foreign_mount(monkeypatch, tmp_path):
    """WSL-on-NTFS 反例走整机探测: 宿主=windows / 进程=linux / 链接宿主读不了"""
    info = alias_fs.MountInfo("/mnt/c", "9p", "aname=drvfs")
    monkeypatch.setattr(alias_fs, "_process_os", lambda: "linux")
    monkeypatch.setattr(alias_fs, "is_wsl", lambda *a, **k: True)
    monkeypatch.setattr(alias_fs, "container_evidence", lambda *a, **k: ())
    monkeypatch.setattr(alias_fs, "mount_info_for_path", lambda *a, **k: info)
    monkeypatch.setattr(alias_fs, "windows_backed_mount", lambda *a, **k: info)
    cap = probe_capability(str(tmp_path))
    assert cap.process_os == "linux" and cap.host_os == "windows"
    assert cap.link_visible_to_host is False
    assert cap.foreign_fs == "drvfs"
    assert any("WSL" in n for n in cap.notes)
    assert any("Windows 宿主提供" in n for n in cap.notes)
    assert any("挂载" in n for n in cap.notes)
    assert any("宿主 OS 与进程 OS 不一致" in n for n in cap.notes)
    assert alias_fs.platform_verdict(cap).row == "container_cross_os"


def test_probe_capability_degrades_on_probe_crash(monkeypatch, tmp_path):
    def boom(*args, **kwargs):
        raise RuntimeError("ctypes 炸了")

    monkeypatch.setattr(alias_fs, "probe_junction", boom)
    cap = probe_capability(str(tmp_path))
    assert not cap.junction.ok and not cap.dir_symlink.ok
    assert "探测异常" in cap.junction.error


def test_probe_capability_uac_note(monkeypatch, tmp_path):
    """文件级 symlink 需提权时, 备注要写明提权通道是否可用(界面据此给出路)"""
    def symlink_probe(work_dir, *, target_is_directory, try_create=None):
        if target_is_directory:
            return LinkProbe(True, detail="dir ok")
        return LinkProbe(False, error="权限不足(需提权/UAC): 以管理员身份运行")

    monkeypatch.setattr(alias_fs, "probe_symlink", symlink_probe)
    monkeypatch.setattr(alias_fs, "_uac_available", lambda process_os: True)
    monkeypatch.setattr(alias_fs, "_process_os", lambda: "windows")
    monkeypatch.setattr(alias_fs, "is_wsl", lambda *a, **k: False)
    monkeypatch.setattr(alias_fs, "windows_backed_mount", lambda *a, **k: None)
    cap = probe_capability(str(tmp_path))
    assert any("提权通道可用" in n for n in cap.notes)


def test_uac_available_swallows_error(monkeypatch):
    assert alias_fs._uac_available("linux") is False

    def boom():
        raise RuntimeError("没有 window station")

    monkeypatch.setattr(alias_fs, "_win_interactive_session", boom)
    assert alias_fs._uac_available("windows") is False
