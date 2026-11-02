"""小容量目标路径的显式入口与安全守卫(issue 26-11-02-1208 复验)。

入口只认用户显式设置的环境变量, 且对路径做硬校验: 必须带盘符、非系统卷、
卷标不得为 Recovery/System/EFI、路径各级不得带 hidden/system 属性或 reparse point、
st_dev 必须与盘符根一致。**绝不自动枚举、自动挂接任何隐藏卷/系统卷。**
"""
from __future__ import annotations

import ctypes
import os
import re
import shutil
import stat
from pathlib import Path

SMALL_TARGET_ENV = "QBT_REAL_SMALL_TARGET"
_FORBIDDEN_LABEL_KEYS = ("recovery", "system", "efi", "恢复", "系统")
_INVALID_ATTR = 0xFFFFFFFF


def _get_attrs(path: str) -> int:
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
    k32.GetFileAttributesW.restype = ctypes.c_uint32
    return int(k32.GetFileAttributesW(path))


def _is_link(p: Path) -> bool:
    try:
        st = os.lstat(p)
    except OSError:
        return False
    return bool(getattr(st, "st_reparse_tag", 0)) or stat.S_ISLNK(st.st_mode)


def _volume_label(root: str) -> str:
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetVolumeInformationW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_wchar_p,
        ctypes.c_uint32,
    ]
    k32.GetVolumeInformationW.restype = ctypes.c_int
    buf = ctypes.create_unicode_buffer(64)
    ok = k32.GetVolumeInformationW(root, buf, len(buf), None, None, None, None, 0)
    assert ok, f"读取卷标失败(拒绝继续): {root}"
    return buf.value


def label_forbidden(label: str) -> bool:
    low = label.strip().lower()
    return any(k in low for k in _FORBIDDEN_LABEL_KEYS)


def assert_safe_target(raw: str) -> Path:
    """硬守卫: 不满足即 AssertionError(带原因), 绝不自动修正/挂接。"""
    text = str(raw or "").strip()
    assert text, "目标路径为空"
    assert not text.startswith("\\\\"), f"拒绝 UNC / 卷 GUID 路径: {text}"
    raw_path = Path(text)
    assert raw_path.is_absolute(), f"目标必须是绝对路径: {text}"
    assert re.fullmatch(r"[A-Za-z]:", raw_path.drive or ""), f"目标必须带盘符: {text}"
    p = Path(os.path.abspath(text))
    assert p.is_dir(), f"目标必须是已存在的目录(测试不替你创建): {p}"
    drive = p.drive
    root = drive + "\\"
    sysdrive = (os.environ.get("SystemDrive") or "C:").rstrip("\\")
    assert drive.upper() != sysdrive.upper(), f"拒绝对系统卷执行: {drive}"
    label = _volume_label(root)
    assert not label_forbidden(label), f"拒绝 Recovery/System/EFI 类卷标: {label!r} @ {root}"
    bits = stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM
    attrs = _get_attrs(root)
    assert attrs != _INVALID_ATTR, f"读取卷根属性失败(拒绝继续): {root}"
    # 盘符根在 Windows 上恒带 HIDDEN|SYSTEM(实测 C:/D:/E: 均为 0x36), 不能据此判隐藏卷;
    # 隐藏/系统卷由「无盘符」(上面已拒) + 卷标关键词 + SystemDrive 比对共同拦截。
    # 真正要查 hidden/system 的是目标路径各级(下面逐级检查), 防止经隐藏目录/挂载点绕进别的卷。
    cur = Path(root)
    for part in p.relative_to(Path(root)).parts:
        cur = cur / part
        assert not _is_link(cur), f"拒绝 reparse point(junction/symlink/mount point): {cur}"
        a = _get_attrs(str(cur))
        assert a != _INVALID_ATTR, f"读取路径属性失败: {cur}"
        assert not (a & bits), f"路径含 hidden/system 属性: {cur}"
    st_p = os.stat(str(p))
    st_root = os.stat(root)
    assert st_p.st_dev == st_root.st_dev, (f"目标 st_dev={st_p.st_dev} 与 {drive} 根={st_root.st_dev} 不一致: 路径跨卷/经挂载点")
    return p


def require_small_target(needed: int) -> tuple[Path, int]:
    """读显式入口 + 安全守卫 + 前置成立(0 < free < needed), 返回 (路径, 剩余字节)。"""
    raw = os.environ.get(SMALL_TARGET_ENV, "")
    assert raw.strip(), (
        f"未设置 {SMALL_TARGET_ENV}: L490「跨卷 + 空间不足」负向对照需要你自行准备小容量目标。\n"
        f"唯一指定方式 = 手动挂载 ImDisk 内存盘(管理员, 非破坏性, 用完卸载):\n"
        f"  imdisk -a -s 96M -t vm -o fix -m Y: -p \"/fs:ntfs /q /y\"\n"
        f"  New-Item -ItemType Directory Y:\\small_target\n"
        f"  设 {SMALL_TARGET_ENV}=Y:\\small_target (容量须 < {needed} 字节, 96M 盘实测 free 约 80MiB)\n"
        f"详见 memory-bank/testing/real-machine.md §2.9; 不提供其它备选路径, "
        f"守卫会硬拒无盘符/系统卷/Recovery-System-EFI 卷标/reparse point 目标。"
    )
    p = assert_safe_target(raw)
    free = shutil.disk_usage(str(p)).free
    assert 0 < free < needed, (
        f"目标剩余 {free} 字节不小于 needed {needed}: L490 前置不满足。\n"
        f"请把 {SMALL_TARGET_ENV} 指向手动挂载的 ImDisk 小容量内存盘下的空目录"
        f"(容量 < {needed} 字节); 测试不会自动枚举、自动挂载任何卷。"
    )
    return p, free
