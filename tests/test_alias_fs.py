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
- test_same_volume: 同卷 True / 不可读 None(不可判定, 不是 False); volume_free 死导出已删(R2#32,
  同一职责由 relocate_common._volume_free_resolved 单点承担)
- test_is_unc: UNC 判定(含 `\\\\?\\` 与 `\\\\.\\` 设备前缀不算 UNC)
- test_is_remote_path: 远端判定 = UNC(含设备前缀 UNC); 本机固定盘/相对路径/非 Windows 为 False
- test_is_remote_path_drive_type: 盘符映射网络盘(DRIVE_REMOTE)判远端, 本机固定盘判本地
- test_drive_type_failure_degrades: GetDriveTypeW 不可用返回 DRIVE_UNKNOWN(按本地处理), 不抛
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

P1-T1.4 守卫与容错簇(计划 26-10-20-2101, 覆盖率缺口清偿):
- test_mount_info_reads_proc_mounts_when_not_injected: mounts_text 未注入 -> 走真实读取单点
  (非 Linux 平台读不到 = None, 不抛); 注入文本时按最长前缀命中
- test_remove_tree_tolerates_failures: 探测清理容错面 —— 目录不存在(scandir 抛 OSError)静默
  返回 / 子项删不掉记 DEBUG 继续 / 收尾 rmdir 因残留失败同样只记 DEBUG(不半途抛)
- test_probe_junction_non_windows: 非 Windows 恒不可用且原因写明「仅 Windows」(不做任何探测)
- test_alias_kind_of_symlink_without_reparse_tag: 形态判定兜底支 —— st_reparse_tag 缺省时
  按 S_ISLNK 判符号链接(POSIX 口径; Windows 上 reparse tag 先命中)
- test_win_interactive_session_station_failures: 窗口站探测两条保守出口(ctypes 桩)——
  拿不到窗口站句柄 / 取 UOI_FLAGS 失败 -> False(服务/SSH 会话弹不出 UAC)
- test_win_create_junction_kernel_failure_cleans_up: junction 内核原语失败(ctypes 桩)——
  CreateFileW 返回 INVALID_HANDLE / DeviceIoControl 失败 -> 抛 OSError 且删掉刚建的空目录;
  清理时 rmdir 再失败也不掩盖主因

S5 重定向原语簇(计划 26-11-05-0808 S5, D15: 0247 S6③ 设想从零实现):
- test_retarget_alias_dir_forms: 目录别名(Windows junction / POSIX 目录 symlink)改指 -> 读旧目标
  删旧建新 + 穿透读 + 幂等重放 skipped
- test_retarget_alias_hardlink_and_idempotent: 硬链接改指(换 inode)+ 重放 skipped(同 inode 幂等)
- test_retarget_alias_missing_link_rebuilds: 链接缺失(经别名搬迁被改名带走形态)-> 按 kind 重建
  〔无 symlink 建链能力的环境 skip〕
- test_retarget_alias_hardlink_cross_volume_falls_back_to_symlink: hardlink 形态改指跨卷目标 ->
  删旧前回落 symlink(评审 #2, 不进 os.link EXDEV 死循环)/ 卷位判不了(None)保守回落 /
  同卷对照不回落保 hardlink〔无 symlink 建链能力的环境 skip〕
- test_retarget_alias_refuses_when_target_missing: 新目标不存在 -> 拒绝且旧链接原样(绝不做删了建不回)
- test_retarget_alias_refuses_nonempty_real_dir: 链接位置被非空真目录占据 -> 拒绝不动数据
- test_probe_alias_rebuild_busy: 句柄占用探测(DELETE 权限独占打开 = 「此刻真删也会成功」的忠实预言)——
  Windows 文件型链接被无共享删除句柄占用时检出、释放/带共享删除放行、junction 持句柄放行
  (现代 Windows 链接本体删除对读句柄稳健, 实测口径)/ 路径缺失放行; POSIX 恒 None

覆盖率缺口清偿(26-11-07, test.full 99.31% -> 99.5% 闸):
- test_inspect_path_junction_kind: inspect_path 对 junction 报 KIND_JUNCTION(重解析标签先判)
- test_alias_points_to_hardlink_stat_failure_is_false: 硬链接比对 stat 炸 => False 不猜
- test_alias_points_to_unreadable_link_target_is_false: readlink 判不了 => False 走重建
- test_probe_alias_rebuild_busy_posix_is_none: 非 Windows 恒 None
- test_probe_alias_rebuild_busy_isdir_oserror_is_none: 存在性判不了(isdir 炸)=> None 不拦
- test_probe_alias_rebuild_busy_unclassifiable_error_is_none: 其它 CreateFileW 错误(非法路径字符)
  => None 不拦
- test_retarget_alias_infers_kind_when_link_and_kind_absent: 无链接无 kind 防御支(目录/文件目标
  两路推断)〔无 symlink 建链能力的环境 skip〕
- test_retarget_alias_consumes_empty_real_dir_at_link_position: 空真目录占位 -> 挪掉照常重建
- test_retarget_alias_unsupported_form_raises_valueerror: 形态不支持 => ValueError
- test_retarget_alias_dir_penetration_failure_leaves_error: 目录别名建后不可穿透 => RuntimeError
  带旧指诊断
- test_retarget_alias_file_penetration_failures: 文件别名穿透双闸(isfile 为假/尺寸不符)

CI 红修复(POSIX 口径, 26-11-07):
- test_alias_kind_of_real_dir_is_none: 真目录(含子目录, POSIX nlink>=2)不被 nlink 判据认成
  硬链接 —— 缺了它「非空真目录占据链接位」拒绝分支在 Linux 上会拿目录去 unlink

真文件占位保护(issue 26-11-07-0748, 26-11-07):
- test_retarget_alias_refuses_real_file_at_link_position: 链接位被真文件占据 -> 拒绝不动数据
  (形态非 hardlink / 无 kind 防御支 / hardlink 形态但与新目标尺寸不一致三路, 文件原样保留)
- test_retarget_alias_refuses_foreign_reparse_tag_real_file: 非链接重解析标签的真体(OneDrive
  云占位符形态, lstat 桩)同样进真文件保护支 —— 链接标签豁免只认 MOUNT_POINT/SYMLINK
- test_retarget_alias_allows_hardlink_twin_residue: hardlink 孪生残名(qB 搬移删另一名字后
  nlink 收敛 1 的真文件)与新目标同尺寸 -> 放行删除照常重建(同卷保 hardlink 形态)
- test_retarget_alias_twin_residue_cross_volume_falls_back_to_symlink: 孪生残名占位且跨卷 ->
  放行删除后回落 symlink(N10 生产形态, 不进 EXDEV 死循环)〔无 symlink 建链能力的环境 skip〕

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
import stat
import tempfile
from types import SimpleNamespace

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

_WIN_ONLY = pytest.mark.skipif(not utils.is_windows(), reason="junction 仅 Windows")  # owner: abacker


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
)  # owner: abacker


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


def test_same_volume(tmp_path):
    assert alias_fs.same_volume(str(tmp_path), str(tmp_path)) is True
    assert alias_fs.same_volume(str(tmp_path), str(tmp_path / "missing")) is None  # 不可判定 != 不同卷


def test_is_unc():
    assert alias_fs.is_unc(r"\\nas\share\movie")
    assert alias_fs.is_unc("//nas/share/movie")
    assert not alias_fs.is_unc(r"C:\Download")
    assert not alias_fs.is_unc("/mnt/downloads")
    assert not alias_fs.is_unc(r"\\?\C:\Download")
    assert not alias_fs.is_unc(r"\\.\PhysicalDrive0")


def test_is_remote_path(monkeypatch):
    assert alias_fs.is_remote_path(r"\\nas\share\movie")
    assert alias_fs.is_remote_path("//nas/share/movie")
    assert alias_fs.is_remote_path(r"\\?\UNC\nas\share\movie"), "设备前缀 UNC 仍是远端"
    assert not alias_fs.is_remote_path(r"C:\Download")
    assert not alias_fs.is_remote_path("/mnt/downloads")
    assert not alias_fs.is_remote_path("")
    assert not alias_fs.is_remote_path(r"..\relative")

    # 非 Windows 不做盘符判定(保持旧行为)
    monkeypatch.setattr(alias_fs.utils, "is_windows", lambda: False)
    assert not alias_fs.is_remote_path(r"Z:\movie")


def test_is_remote_path_drive_type(monkeypatch):
    # 核心分支: 盘符映射网络盘(DRIVE_REMOTE=4)必须判远端; 本机固定盘(3)判本地
    monkeypatch.setattr(alias_fs.utils, "is_windows", lambda: True)
    monkeypatch.setattr(alias_fs, "_drive_type", lambda root: 4 if root == "Z:\\" else 3)
    assert alias_fs.is_remote_path(r"Z:\movie")
    assert not alias_fs.is_remote_path(r"C:\Download")


def test_drive_type_failure_degrades(monkeypatch):
    # GetDriveTypeW 不可用 => 0(DRIVE_UNKNOWN), 调用方按本地处理, 不抛
    import ctypes

    def _boom(*args, **kwargs):
        raise OSError("no kernel32")

    monkeypatch.setattr(ctypes, "WinDLL", _boom, raising=False)
    assert alias_fs._drive_type("C:\\") == 0


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


def test_alias_kind_of_real_dir_is_none(tmp_path):
    """真目录恒判「不是链接」: POSIX 目录 nlink 天生 >= 2, 不得被 nlink 判据认成硬链接

    !Linux CI 实测红: POSIX 目录 st_nlink = 2 + 子目录数(自己的 `.`、父目录里指向它的那个条目、
    每个子目录的 `..`), 空目录就已经是 2, 旧写法一律返回 KIND_HARDLINK -> 重定向「非空真目录占据
    链接位」拒绝分支的前置条件(existing is None)不成立, retarget_alias 拿目录本体去 os.unlink,
    抛 IsADirectoryError 而不是按设计拒绝。Windows 目录 nlink 常为 1, 本地永远走不到那条路,
    只有 POSIX 才暴露 —— 故必须有这条守卫。
    """
    plain_dir = tmp_path / "plain_dir"
    (plain_dir / "sub").mkdir(parents=True)  # 子目录把 nlink 抬上去(POSIX 口径)
    assert alias_fs.alias_kind_of(str(plain_dir)) is None


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


# ---------- P1-T1.4 守卫与容错簇(计划 26-10-20-2101) ----------


def test_mount_info_reads_proc_mounts_when_not_injected(monkeypatch):
    """mounts_text 未注入 -> 走真实 /proc/mounts 读取单点(_read_text); 读不到 = None(非 Linux
    平台的常态, 不抛); 注入文本时按最长前缀命中(挂载表解析逻辑本身由既有用例钉住)"""
    monkeypatch.setattr(alias_fs, "_read_text", lambda path: "")
    assert alias_fs.mount_info_for_path("/mnt/c/x") is None  # 读不到: 不抛不猜
    monkeypatch.setattr(
        alias_fs, "_read_text", lambda path: "/dev/sda1 / ext4 rw 0 0\n/mnt/c /mnt/c 9p rw,aname=drvfs 0 0\n"
    )
    info = alias_fs.mount_info_for_path("/mnt/c/Users/x")
    assert info is not None and info.mount_point == "/mnt/c" and info.is_drvfs


def test_remove_tree_tolerates_failures(tmp_path, monkeypatch):
    """_remove_tree 容错面(探测临时目录清理): 目录不存在(scandir 抛 OSError)-> 静默返回;
    子项删不掉 -> 记 DEBUG 继续扫其它项(不半途抛); 收尾 rmdir 因残留失败同样只记 DEBUG
    —— 清理是尽力而为, 绝不让清理失败盖掉探测结论"""
    alias_fs._remove_tree(str(tmp_path / "absent"))  # scandir 抛 OSError: 零操作零异常
    root = tmp_path / "probe"
    root.mkdir()
    stuck = root / "stuck.txt"
    stuck.write_text("x", encoding="utf-8")
    real_unlink = os.unlink

    def _unlink_boom(path):
        if os.path.basename(str(path)) == "stuck.txt":
            raise OSError(13, "locked")
        return real_unlink(path)

    monkeypatch.setattr(alias_fs.os, "unlink", _unlink_boom)
    alias_fs._remove_tree(str(root))
    assert stuck.exists() and root.exists()  # 删不掉的留下, 别的照删, 全程不抛


def test_probe_junction_non_windows(monkeypatch):
    """非 Windows 平台: junction 恒不可用且原因写明「仅 Windows」(直接返回, 不做任何探测)"""
    monkeypatch.setattr(alias_fs, "utils", SimpleNamespace(is_windows=lambda: False))
    probe = alias_fs.probe_junction("whatever")
    assert not probe.ok and "仅 Windows" in probe.error


def test_alias_kind_of_symlink_without_reparse_tag(tmp_path, monkeypatch):
    """形态判定兜底支: st_reparse_tag 缺省(非 Windows 口径)时按 S_ISLNK 判符号链接 ——
    Windows 上 reparse tag 先命中, 这条兜底是 POSIX 与旧 stat 形态的唯一判据"""
    monkeypatch.setattr(alias_fs.os, "lstat", lambda path: SimpleNamespace(st_mode=stat.S_IFLNK | 0o777, st_nlink=1))
    assert alias_fs.alias_kind_of(str(tmp_path / "any")) == KIND_SYMLINK


@_WIN_ONLY
def test_win_interactive_session_station_failures(monkeypatch):
    """窗口站探测两条保守出口(ctypes 桩): 拿不到窗口站句柄 / 取 UOI_FLAGS 失败 -> False
    —— 无可见窗口站的会话(服务/SSH/计划任务)弹不出 UAC, 按「提权通道不可用」处理

    !平台准入: 用例靠 `ctypes.WinDLL` 桩住 user32, 而 Linux 上 `ctypes` **没有 WinDLL 属性**
    (monkeypatch.setattr 直接 AttributeError)。被测函数本身也只在 Windows 调用。"""
    import ctypes

    def _fake_dll(station, info_ok):
        def factory(name, use_errno=False, use_last_error=False):
            def get_station():
                return station

            def get_info(*args):
                return info_ok

            return SimpleNamespace(GetProcessWindowStation=get_station, GetUserObjectInformationW=get_info)

        return factory

    monkeypatch.setattr(ctypes, "WinDLL", _fake_dll(0, 1))
    assert alias_fs._win_interactive_session() is False  # 没有窗口站
    monkeypatch.setattr(ctypes, "WinDLL", _fake_dll(1234, 0))
    assert alias_fs._win_interactive_session() is False  # UOI_FLAGS 取不到


@_WIN_ONLY
def test_win_create_junction_kernel_failure_cleans_up(tmp_path, monkeypatch):
    """junction 内核原语失败路径(ctypes 桩): CreateFileW 返回 INVALID_HANDLE / DeviceIoControl
    失败 -> 抛 OSError 且删掉刚建的空目录(不留半截现场); 清理时 rmdir 再失败也不掩盖主因

    !平台准入同 `test_win_interactive_session_station_failures`: 桩的是 `ctypes.WinDLL`, Linux 无此属性。"""
    import ctypes
    from ctypes import wintypes

    link = str(tmp_path / "link")
    target = str(tmp_path / "target")
    os.makedirs(target)
    invalid = wintypes.HANDLE(-1).value

    def _fake_k32(handle, io_ok):
        def factory(name, use_errno=False, use_last_error=False):
            return SimpleNamespace(
                CreateFileW=lambda *args: handle,
                DeviceIoControl=lambda *args: io_ok,
                CloseHandle=lambda handle_: 1,
            )

        return factory

    monkeypatch.setattr(ctypes, "WinDLL", _fake_k32(invalid, 0))
    with pytest.raises(OSError):
        alias_fs._win_create_junction(link, target)
    assert not os.path.exists(link)  # 失败即清场
    monkeypatch.setattr(ctypes, "WinDLL", _fake_k32(1234, 0))  # 句柄有效但 FSCTL 失败
    with pytest.raises(OSError):
        alias_fs._win_create_junction(link, target)
    assert not os.path.exists(link)
    # 清理本身失败(rmdir 抛错): 被吞掉, 主因照抛 —— 空目录留下但不掩盖失败原因
    monkeypatch.setattr(alias_fs.os, "rmdir", lambda path: (_ for _ in ()).throw(OSError(13, "locked")))
    with pytest.raises(OSError):
        alias_fs._win_create_junction(link, target)
    assert os.path.isdir(link)
    monkeypatch.undo()
    os.rmdir(link)


# ---------------------------------------------------------------- S5 重定向原语(计划 26-11-05-0808 S5, D15)


def _mk_file(path, content=b"auto-qb"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return path


def _win():
    return alias_fs.utils.is_windows()


def test_retarget_alias_dir_forms(tmp_path):
    """目录别名改指: 读旧目标删旧建新 + 穿透读 + 幂等重放 skipped(Windows junction / POSIX 目录 symlink)"""
    root = str(tmp_path)
    b, c = os.path.join(root, "b"), os.path.join(root, "c")
    _mk_file(os.path.join(b, "e00.mkv"), b"B-data")
    _mk_file(os.path.join(c, "e00.mkv"), b"C-data")
    link = os.path.join(root, "alias")
    kind = alias_fs.KIND_JUNCTION if _win() else alias_fs.KIND_SYMLINK
    alias_fs.create_dir_alias(link, b, kind)
    assert alias_fs.retarget_alias(link, c, kind) == "retargeted"
    assert alias_fs.alias_points_to(link, c)
    with open(os.path.join(link, "e00.mkv"), "rb") as f:  # 穿透: 经新链接读到新目标内容
        assert f.read() == b"C-data"
    # 幂等(黄金法则 1): 已是目标指向 -> skipped, 零删建
    assert alias_fs.retarget_alias(link, c, kind) == "skipped"
    assert alias_fs.alias_kind_of(link) == kind
    # 删旧链接非递归绝不跟随: 旧目标数据原封不动
    with open(os.path.join(b, "e00.mkv"), "rb") as f:
        assert f.read() == b"B-data"


def test_retarget_alias_hardlink_and_idempotent(tmp_path):
    """硬链接改指: 换到新目标 inode; 重放同 inode -> skipped(幂等判定走 inode 比对)"""
    root = str(tmp_path)
    fb = _mk_file(os.path.join(root, "b", "e00.mkv"), b"x" * 64)
    fc = _mk_file(os.path.join(root, "c", "e00.mkv"), b"y" * 64)  # 同尺寸不同内容(穿透校验比尺寸)
    link = os.path.join(root, "a", "e00.mkv")
    os.makedirs(os.path.dirname(link), exist_ok=True)
    alias_fs.create_file_alias(link, fb, alias_fs.KIND_HARDLINK)
    assert alias_fs.retarget_alias(link, fc, alias_fs.KIND_HARDLINK) == "retargeted"
    assert alias_fs.alias_points_to(link, fc), "改指后与目标同 inode"
    assert os.stat(link).st_ino == os.stat(fc).st_ino
    assert alias_fs.retarget_alias(link, fc, alias_fs.KIND_HARDLINK) == "skipped"


@_SYMLINK_REQUIRED
def test_retarget_alias_missing_link_rebuilds(tmp_path):
    """链接缺失(经别名搬迁被 qB 改名带走 / 外部误删形态) -> 按 kind 重建, 返回 rebuilt"""
    root = str(tmp_path)
    fc = _mk_file(os.path.join(root, "c", "e00.mkv"), b"C-data")
    link = os.path.join(root, "a", "e00.mkv")  # 从不存在
    assert alias_fs.retarget_alias(link, fc, alias_fs.KIND_SYMLINK) == "rebuilt"
    assert alias_fs.alias_kind_of(link) == alias_fs.KIND_SYMLINK
    with open(link, "rb") as f:
        assert f.read() == b"C-data"


@_SYMLINK_REQUIRED
def test_retarget_alias_hardlink_cross_volume_falls_back_to_symlink(tmp_path, monkeypatch):
    """hardlink 形态改指跨卷目标 -> 删旧前先回落 KIND_SYMLINK(评审 #2)

    不修则 os.link 跨卷必 EXDEV: 删旧链接已先行(旧孪生被 qB 跨卷搬移后 nlink 收敛 1, 删的
    正是前任成员的现存数据名), 每拍重试恒失败 = 前任永停 supersede stage。回落 symlink 后
    成员经符号链接照常读(形态透明); 卷位判不了(None)按跨卷保守回落。同卷不回落保 hardlink。
    """
    root = str(tmp_path)
    real_same_volume = alias_fs.same_volume
    fb = _mk_file(os.path.join(root, "b", "e00.mkv"), b"x" * 64)
    fc = _mk_file(os.path.join(root, "c", "e00.mkv"), b"y" * 64)
    link = os.path.join(root, "a", "e00.mkv")
    os.makedirs(os.path.dirname(link), exist_ok=True)
    alias_fs.create_file_alias(link, fb, alias_fs.KIND_HARDLINK)
    # 跨卷注入: st_dev 判定恒 False(新目标在另一块卷)
    monkeypatch.setattr(alias_fs, "same_volume", lambda a, b: False)
    assert alias_fs.retarget_alias(link, fc, alias_fs.KIND_HARDLINK) == "retargeted"
    assert alias_fs.alias_kind_of(link) == alias_fs.KIND_SYMLINK, "跨卷必须回落 symlink, 不进 EXDEV"
    assert alias_fs.alias_points_to(link, fc)
    with open(link, "rb") as f:  # 穿透: 成员经 symlink 读到新目标内容
        assert f.read() == b"y" * 64
    # 卷位判不了(st_dev 不可得 => None)同样保守回落
    link_none = os.path.join(root, "a-none", "e00.mkv")
    os.makedirs(os.path.dirname(link_none), exist_ok=True)
    alias_fs.create_file_alias(link_none, fb, alias_fs.KIND_HARDLINK)
    monkeypatch.setattr(alias_fs, "same_volume", lambda a, b: None)
    assert alias_fs.retarget_alias(link_none, fc, alias_fs.KIND_HARDLINK) == "retargeted"
    assert alias_fs.alias_kind_of(link_none) == alias_fs.KIND_SYMLINK
    # 对照: 同卷(st_dev 实测相等, 恢复真函数解除注入)不回落, hardlink 原形态改道
    monkeypatch.setattr(alias_fs, "same_volume", real_same_volume)
    link_same = os.path.join(root, "a2", "e00.mkv")
    os.makedirs(os.path.dirname(link_same), exist_ok=True)
    alias_fs.create_file_alias(link_same, fb, alias_fs.KIND_HARDLINK)
    assert alias_fs.retarget_alias(link_same, fc, alias_fs.KIND_HARDLINK) == "retargeted"
    assert alias_fs.alias_kind_of(link_same) == alias_fs.KIND_HARDLINK
    assert os.stat(link_same).st_ino == os.stat(fc).st_ino


def test_retarget_alias_refuses_when_target_missing(tmp_path):
    """新目标不存在 -> 拒绝(RuntimeError)且旧链接原样 —— 绝不做「删了建不回」的自毁"""
    root = str(tmp_path)
    b = os.path.join(root, "b")
    _mk_file(os.path.join(b, "e00.mkv"))
    link = os.path.join(root, "alias")
    kind = alias_fs.KIND_JUNCTION if _win() else alias_fs.KIND_SYMLINK
    alias_fs.create_dir_alias(link, b, kind)
    with pytest.raises(RuntimeError):
        alias_fs.retarget_alias(link, os.path.join(root, "gone"), kind)
    assert alias_fs.alias_points_to(link, b), "旧链接必须原样保留"


def test_retarget_alias_refuses_nonempty_real_dir(tmp_path):
    """链接位置被非空真目录占据 -> 拒绝(不猜测不动数据); 空目录残留则照常重建"""
    root = str(tmp_path)
    fc = _mk_file(os.path.join(root, "c", "e00.mkv"))
    link = os.path.join(root, "a")
    os.makedirs(os.path.join(link, "junk"))
    with pytest.raises(RuntimeError):
        alias_fs.retarget_alias(link, fc, alias_fs.KIND_SYMLINK)
    assert os.path.isdir(link), "非空真目录必须原样保留"
    os.rmdir(os.path.join(link, "junk"))
    os.rmdir(link)  # 空目录(qB 搬走文件后的残留形态) -> 照常重建
    assert alias_fs.retarget_alias(
        link, os.path.dirname(fc), alias_fs.KIND_SYMLINK if not _win() else alias_fs.KIND_JUNCTION
    ) == "rebuilt"


def test_retarget_alias_refuses_real_file_at_link_position(tmp_path):
    """链接位置被真文件占据 -> 拒绝且文件原样(真目录支有非空拒绝, 文件支同口径; issue 26-11-07-0748)

    旧实现真文件位落到 remove_alias 的 os.unlink 静默删真数据: 形态非 hardlink(应持链接位
    出现真文件 = 外来物)或 hardlink 形态但与新目标尺寸不一致(不是搬移落位后的孪生残名)
    一律不动数据, 交 D20 重试路径留现场给人。
    """
    root = str(tmp_path)
    fc = _mk_file(os.path.join(root, "c", "e00.mkv"), b"target-data")
    link = os.path.join(root, "a", "e00.mkv")
    _mk_file(link, b"foreign-data")  # 真文件占位(nlink=1, 非链接非目录)
    with pytest.raises(RuntimeError):
        alias_fs.retarget_alias(link, fc, alias_fs.KIND_SYMLINK)
    with open(link, "rb") as f:
        assert f.read() == b"foreign-data", "真文件必须原样保留, 内容不变"
    # 无 kind(旧账/直调)防御支同样拒绝: 文件目标推断 symlink 形态, 真文件位不认
    with pytest.raises(RuntimeError):
        alias_fs.retarget_alias(link, fc)
    # hardlink 形态但尺寸与新目标不一致 = 不是搬移落位后的孪生残名, 同样不动
    with pytest.raises(RuntimeError):
        alias_fs.retarget_alias(link, fc, alias_fs.KIND_HARDLINK)
    assert os.path.isfile(link) and os.path.getsize(link) == len(b"foreign-data")
    assert alias_fs.alias_kind_of(link) is None, "占位真文件全程未被改写"


def test_retarget_alias_refuses_foreign_reparse_tag_real_file(tmp_path, monkeypatch):
    """带非链接重解析标签的真文件(OneDrive 云占位符形态)也进真文件保护支(评审 minor)

    链接标签豁免只认 MOUNT_POINT/SYMLINK 两个: 云族等非链接标签且 S_ISREG 的真体不再
    落 remove_alias 的 os.unlink, 与普通真文件同一拒绝口径(issue 26-11-07-0748)。
    """
    root = str(tmp_path)
    fc = _mk_file(os.path.join(root, "c", "e00.mkv"), b"target-data")
    link = _mk_file(os.path.join(root, "a", "e00.mkv"), b"cloud-placeholder")
    cloud_tag = 0x90000001  # IO_REPARSE_TAG_CLOUD 族(OneDrive); 非链接标签
    real_lstat = os.lstat

    def fake_lstat(p, *args, **kwargs):
        st = real_lstat(p, *args, **kwargs)
        if os.path.normcase(os.path.abspath(p)) == os.path.normcase(
            os.path.abspath(utils.add_long_path_prefix_for_win(link))
        ):
            # retarget_alias/alias_kind_of 对 lstat 结果只取属性: 桩带齐被读字段(st_mode/
            # st_reparse_tag/st_nlink), S_ISREG + tag=云族 + nlink=1 = 云占位符真体形态
            return SimpleNamespace(st_mode=stat.S_IFREG | 0o644, st_reparse_tag=cloud_tag, st_nlink=1)
        return st

    monkeypatch.setattr(alias_fs.os, "lstat", fake_lstat)
    with pytest.raises(RuntimeError):
        alias_fs.retarget_alias(link, fc, alias_fs.KIND_SYMLINK)
    assert os.path.isfile(link)
    with open(link, "rb") as f:
        assert f.read() == b"cloud-placeholder", "云占位符真体必须原样保留"


def test_retarget_alias_allows_hardlink_twin_residue(tmp_path):
    """hardlink 形态的合法真文件占位 = 孪生残名(nlink 收敛 1) -> 放行删除照常重建(同卷保 hardlink)

    qB 搬移删掉另一名字后别名位收敛成普通真文件(数据已随搬移落到新目标): 形态声明
    hardlink 且新目标同尺寸才放行 —— 这是注释里「删的正是前任成员的现存数据名」的
    有意路径, 与意外真文件的拒绝支(issue 26-11-07-0748)两分。
    """
    root = str(tmp_path)
    fb = _mk_file(os.path.join(root, "b", "e00.mkv"), b"x" * 64)
    fc = _mk_file(os.path.join(root, "c", "e00.mkv"), b"y" * 64)  # 同尺寸不同内容(穿透校验比尺寸)
    link = os.path.join(root, "a", "e00.mkv")
    os.makedirs(os.path.dirname(link), exist_ok=True)
    alias_fs.create_file_alias(link, fb, alias_fs.KIND_HARDLINK)
    os.unlink(fb)  # qB 搬移删掉另一名字: 别名位 nlink 收敛 1, 变成普通真文件
    assert alias_fs.alias_kind_of(link) is None and stat.S_ISREG(os.lstat(link).st_mode)
    assert alias_fs.retarget_alias(link, fc, alias_fs.KIND_HARDLINK) == "rebuilt"
    assert alias_fs.alias_kind_of(link) == alias_fs.KIND_HARDLINK, "同卷重建保 hardlink 形态"
    assert os.stat(link).st_ino == os.stat(fc).st_ino
    with open(link, "rb") as f:
        assert f.read() == b"y" * 64


@_SYMLINK_REQUIRED
def test_retarget_alias_twin_residue_cross_volume_falls_back_to_symlink(tmp_path, monkeypatch):
    """孪生残名占位 + 跨卷 -> 放行删除后回落 symlink(N10 生产形态, 不进 EXDEV 死循环)"""
    root = str(tmp_path)
    fb = _mk_file(os.path.join(root, "b", "e00.mkv"), b"x" * 64)
    fc = _mk_file(os.path.join(root, "c", "e00.mkv"), b"y" * 64)
    link = os.path.join(root, "a", "e00.mkv")
    os.makedirs(os.path.dirname(link), exist_ok=True)
    alias_fs.create_file_alias(link, fb, alias_fs.KIND_HARDLINK)
    os.unlink(fb)  # 别名位 nlink 收敛 1 -> 普通真文件(孪生残名)
    monkeypatch.setattr(alias_fs, "same_volume", lambda a, b: False)
    assert alias_fs.retarget_alias(link, fc, alias_fs.KIND_HARDLINK) == "rebuilt"
    assert alias_fs.alias_kind_of(link) == alias_fs.KIND_SYMLINK, "跨卷回落 symlink"
    assert alias_fs.alias_points_to(link, fc)
    with open(link, "rb") as f:
        assert f.read() == b"y" * 64


def test_probe_alias_rebuild_busy(tmp_path):
    """句柄占用探测: DELETE 权限独占打开 = 「此刻真删也会成功」的忠实预言(Win32 实测口径)

    - 文件型链接被「无 FILE_SHARE_DELETE」句柄握着 -> 检出(与 unlink 同报共享冲突);
    - 持有者带 FILE_SHARE_DELETE(libtorrent 做种形态)或释放后 -> 放行;
    - junction 持句柄 -> 放行(现代 Windows 链接本体删除对读句柄稳健, 探测随之不假阳);
    - 路径缺失放行; POSIX 恒 None。
    """
    if not _win():
        # POSIX 删链接无句柄占用失败形态: 任何路径(含不存在)恒 None
        assert alias_fs.probe_alias_rebuild_busy(str(tmp_path / "whatever")) is None
        pytest.skip("句柄占用探测为 Windows 面(POSIX 恒 None 已断言)")
    import ctypes

    GENERIC_READ, OPEN_EXISTING = 0x80000000, 3
    SHARE_RW, SHARE_RWD = 0x1 | 0x2, 0x1 | 0x2 | 0x4
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    root = str(tmp_path)
    t = _mk_file(os.path.join(root, "t.bin"), b"seed")
    # 文件型链接用硬链接(免提权, 任何 Windows 可建; 探测命中的是文件本体, 与 symlink 同判)
    hl = os.path.join(root, "hlink")
    alias_fs.create_file_alias(hl, t, alias_fs.KIND_HARDLINK)
    assert alias_fs.probe_alias_rebuild_busy(hl) is None, "无人占用时放行"
    hold = k32.CreateFileW(utils.add_long_path_prefix_for_win(hl), GENERIC_READ, SHARE_RW, None, OPEN_EXISTING, 0, None)
    assert hold != -1
    try:
        busy = alias_fs.probe_alias_rebuild_busy(hl)
        assert busy is not None and "占用" in busy, busy
    finally:
        k32.CloseHandle(hold)
    assert alias_fs.probe_alias_rebuild_busy(hl) is None, "释放后放行"
    # qB 做种形态: libtorrent 打开带 FILE_SHARE_DELETE -> 探测放行(不假阳)
    hold = k32.CreateFileW(
        utils.add_long_path_prefix_for_win(hl), GENERIC_READ, SHARE_RWD, None, OPEN_EXISTING, 0, None
    )
    assert hold != -1
    try:
        assert alias_fs.probe_alias_rebuild_busy(hl) is None, "带共享删除的做种句柄不构成重建障碍"
    finally:
        k32.CloseHandle(hold)
    # junction 持句柄(含独占) -> 放行: 现代 Windows 链接本体删除对读句柄稳健(实测 rmdir 全成)
    b = os.path.join(root, "b")
    _mk_file(os.path.join(b, "e00.mkv"))
    jlink = os.path.join(root, "jalias")
    alias_fs.create_dir_alias(jlink, b, alias_fs.KIND_JUNCTION)
    hold = k32.CreateFileW(
        utils.add_long_path_prefix_for_win(jlink), GENERIC_READ, 0, None, OPEN_EXISTING, 0x02000000, None
    )
    assert hold != -1
    try:
        assert alias_fs.probe_alias_rebuild_busy(jlink) is None
    finally:
        k32.CloseHandle(hold)
    # 路径缺失: 无占用可言
    assert alias_fs.probe_alias_rebuild_busy(os.path.join(root, "gone")) is None


# ---------------------------------------------------------------------------
# 覆盖率缺口清偿(26-11-07): 重定向失败支与平台遗留面
# ---------------------------------------------------------------------------


@_WIN_ONLY
def test_inspect_path_junction_kind(tmp_path):
    """inspect_path 对 junction 报 KIND_JUNCTION(重解析点标签先于 S_ISLNK 判定)"""
    target = tmp_path / "real"
    target.mkdir()
    link = str(tmp_path / "jalias")
    alias_fs.create_dir_alias(link, str(target), alias_fs.KIND_JUNCTION)
    info = alias_fs.inspect_path(link)
    assert info.status == "ok" and info.kind == alias_fs.KIND_JUNCTION
    assert alias_fs.strip_device_prefix(info.target).lower().endswith("real")


def test_alias_points_to_hardlink_stat_failure_is_false(tmp_path, monkeypatch):
    """硬链接比对两侧 stat 任一炸 => False(不猜指向)

    !桩必须**装在建链之后**: os.stat 是进程级单例, 装上就同时打死了 os.makedirs 的
    `exist_ok` 判据(POSIX 的 posixpath.isdir 先 stat, 炸 -> isdir False -> 已存在目录的
    FileExistsError 不再被吞), 于是建夹具那一步会以 FileExistsError 炸在 _mk_file 里,
    而不是走到被测分支(Windows 上 os.path.isdir/ exists 是 C 内建, 绕过 Python 层补丁,
    桩晚了也照绿 —— 本地全绿、Linux CI 全红的典型形态)。
    """
    fb = _mk_file(os.path.join(str(tmp_path), "b.bin"), b"x")
    link = os.path.join(str(tmp_path), "l.bin")
    alias_fs.create_file_alias(link, fb, alias_fs.KIND_HARDLINK)
    assert alias_fs.alias_kind_of(link) == alias_fs.KIND_HARDLINK

    def _boom(path, *a, **kw):
        raise OSError("stat denied")

    monkeypatch.setattr(alias_fs.os, "stat", _boom)
    assert alias_fs.alias_points_to(link, fb) is False


def test_alias_points_to_unreadable_link_target_is_false(tmp_path, monkeypatch):
    """junction/symlink readlink 失败(alias_target 判不了) => False, 走重建/报错路"""
    target = tmp_path / "real"
    target.mkdir()
    link = os.path.join(str(tmp_path), "jalias")
    kind = alias_fs.KIND_JUNCTION if _win() else alias_fs.KIND_SYMLINK
    alias_fs.create_dir_alias(link, str(target), kind)
    assert alias_fs.alias_points_to(link, str(target)) is True  # 前置: 可读时命中

    def _boom(path, *a, **kw):
        raise OSError("readlink denied")

    monkeypatch.setattr(alias_fs.os, "readlink", _boom)
    assert alias_fs.alias_points_to(link, str(target)) is False


def test_probe_alias_rebuild_busy_posix_is_none(monkeypatch, tmp_path):
    """非 Windows 恒 None(POSIX 删链接无句柄占用失败形态)"""
    monkeypatch.setattr(alias_fs.utils, "is_windows", lambda: False)
    assert alias_fs.probe_alias_rebuild_busy(str(tmp_path / "whatever")) is None


@_WIN_ONLY
def test_probe_alias_rebuild_busy_isdir_oserror_is_none(tmp_path, monkeypatch):
    """存在性判不了(isdir 炸) => None 不拦(保守默认)"""
    def _boom(path, *a, **kw):
        raise OSError("isdir denied")

    monkeypatch.setattr(alias_fs.os.path, "isdir", _boom)
    assert alias_fs.probe_alias_rebuild_busy(str(tmp_path / "x.bin")) is None


@_WIN_ONLY
def test_probe_alias_rebuild_busy_unclassifiable_error_is_none(tmp_path):
    """CreateFileW 其它错误(非法路径字符 -> ERROR_INVALID_NAME)判不了占用 => None 不拦"""
    assert alias_fs.probe_alias_rebuild_busy(str(tmp_path / "bad<>name.bin")) is None


@_SYMLINK_REQUIRED
def test_retarget_alias_infers_kind_when_link_and_kind_absent(tmp_path):
    """防御支: 无现存链接也无 kind(旧账/直调) -> 目录目标推断 junction(POSIX 目录 symlink),
    文件目标推断文件 symlink —— 重建即恢复服务"""
    root = str(tmp_path)
    # 目录目标: 推断目录别名(Windows junction 免提权 / POSIX 目录 symlink)
    b = os.path.join(root, "b")
    _mk_file(os.path.join(b, "e00.mkv"))
    link = os.path.join(root, "alias-none")
    assert alias_fs.retarget_alias(link, b) == "rebuilt"
    assert alias_fs.alias_kind_of(link) == (alias_fs.KIND_JUNCTION if _win() else alias_fs.KIND_SYMLINK)
    # 文件目标: 推断文件 symlink
    fc = _mk_file(os.path.join(root, "c.bin"), b"C")
    flink = os.path.join(root, "falias-none")
    assert alias_fs.retarget_alias(flink, fc) == "rebuilt"
    assert alias_fs.alias_kind_of(flink) == alias_fs.KIND_SYMLINK
    with open(flink, "rb") as f:
        assert f.read() == b"C"


def test_retarget_alias_consumes_empty_real_dir_at_link_position(tmp_path):
    """链接位置被**空**真目录占据(qB 搬走文件后的残留): 挪掉空目录照常重建(非空支已另测)"""
    root = str(tmp_path)
    b = os.path.join(root, "b")
    _mk_file(os.path.join(b, "e00.mkv"))
    link = os.path.join(root, "alias-empty")
    os.makedirs(link)  # 空真目录占位
    kind = alias_fs.KIND_JUNCTION if _win() else alias_fs.KIND_SYMLINK
    assert alias_fs.retarget_alias(link, b, kind) == "rebuilt"
    assert alias_fs.alias_kind_of(link) == kind  # 位置已由别名接管


def test_retarget_alias_unsupported_form_raises_valueerror(tmp_path):
    """形态不支持(既非 junction/symlink 也非 hardlink) => ValueError(直调防御面)"""
    fc = _mk_file(os.path.join(str(tmp_path), "c.bin"), b"C")
    with pytest.raises(ValueError, match="不支持形态"):
        alias_fs.retarget_alias(os.path.join(str(tmp_path), "l.bin"), fc, "bogus-kind")


def test_retarget_alias_dir_penetration_failure_leaves_error(tmp_path, monkeypatch):
    """目录别名建后不可穿透(建链替身什么都没建) => RuntimeError 包旧指诊断"""
    root = str(tmp_path)
    b = os.path.join(root, "b")
    _mk_file(os.path.join(b, "e00.mkv"), b"B")
    c2 = os.path.join(root, "c2")  # 新目标必须存在(目标存在性前置闸先行)
    _mk_file(os.path.join(c2, "e00.mkv"), b"C2")
    link = os.path.join(root, "alias")
    kind = alias_fs.KIND_JUNCTION if _win() else alias_fs.KIND_SYMLINK
    alias_fs.create_dir_alias(link, b, kind)
    monkeypatch.setattr(alias_fs, "create_dir_alias", lambda *a, **kw: None)  # 建链替身: 假成功
    with pytest.raises(RuntimeError, match="穿透校验失败") as ei:
        alias_fs.retarget_alias(link, c2, kind)
    assert "旧指" in str(ei.value)  # 诊断带旧目标


def test_retarget_alias_file_penetration_failures(tmp_path, monkeypatch):
    """文件别名穿透双闸: isfile 为假 / 尺寸与目标不一致 => RuntimeError(建失败不留半截指向)"""
    root = str(tmp_path)
    fb = _mk_file(os.path.join(root, "b.bin"), b"x" * 32)
    fc = _mk_file(os.path.join(root, "c.bin"), b"y" * 32)
    link = os.path.join(root, "l.bin")
    alias_fs.create_file_alias(link, fb, alias_fs.KIND_HARDLINK)
    # 1) 建链替身什么都没建 -> isfile 为假
    monkeypatch.setattr(alias_fs, "create_file_alias", lambda *a, **kw: None)
    with pytest.raises(RuntimeError, match="穿透校验失败"):
        alias_fs.retarget_alias(link, fc, alias_fs.KIND_HARDLINK)
    # 2) 建链替身建了个内容更长的副本 -> 尺寸不一致
    def _copy_with_extra(link_path, target_path, kind):
        with open(target_path, "rb") as f:
            data = f.read()
        with open(link_path, "wb") as f:
            f.write(data + b"extra")

    monkeypatch.setattr(alias_fs, "create_file_alias", _copy_with_extra)
    with pytest.raises(RuntimeError, match="尺寸与目标不一致"):
        alias_fs.retarget_alias(link, fc, alias_fs.KIND_HARDLINK)
