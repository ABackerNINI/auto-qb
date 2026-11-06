"""别名文件系统层: 链接能力探测与链接原语(plan 26-10-18-1604 §3.2/§3.3, 实施期 P0)

本模块只回答两个问题, 不含任何迁移决策:
1. **这台机器上, 此刻能不能在 qB 看得见的那块盘上建出 qB 能读的链接**(能力探测);
2. **建/读/删一条链接**的原语(探测自己要用, P3 的建链接与 C 的删链接也走这里)。

决策面(形态分流 `plan()`、闸门、相位机)在 P2/P3 的 `core/modules/relocate_*`, 不在这里 ——
本模块只输出事实, 不输出结论。唯一的例外是 `platform_verdict()`: 它把 §3.3 那张
「环境组合 -> 目录别名/文件别名/结论」的**能力矩阵**编码成纯函数, 供 P2 的闸门调用,
免得矩阵在探测侧与闸门侧各写一遍(verdict-scope-parity)。

## 为什么探测必须真建真删(而不是查平台/查版本)

§2.4 的实测把「按平台推断」这条路否掉了三次:
- 本机开发者模式开着, `os.symlink` 目录与文件都成功 —— 但用户环境未必开(需要 UAC);
- WSL 里 `ln -s` 到 `/mnt/h/...` **成功**, 而 Windows 侧 `open()` 报 `Errno 22`、
  `os.path.islink` 为 False —— 建出来的东西在**对端**读不了, 建链成功不等于可用;
- 文件级 `os.symlink` 在 259 字符可用、260 起一律 `WinError 1314`; ctypes 直调
  `CreateSymbolicLinkW` 返回成功但链接**不可见**。

所以每个探测都是「建 -> 校验可见 -> 校验可穿透读 -> 删」四步, 任一步不成立即判不可用;
`create` 的返回值不作数, 只有**现场可观测的链接**才算数。

## 沙盒口径(§2.4 末行)

以上全部是工具 shell 内实测, 真实部署(服务化/无交互桌面/容器)可能不同 ⇒ 本模块的结果
是**运行期探测结果**, 不是编译期结论; 探测在 `work_dir` 所在的卷上做, 目标卷不同时
(P3 跨卷迁移)由闸门按目标卷复探 —— 见 `probe_capability()` 的 `work_dir` 说明。

## 测试替身口径(§8.6)

允许注入的只有「尝试创建」这一个单点: `probe_symlink(try_create=...)` /
`probe_hardlink(try_create=...)` / `probe_junction(try_create=...)`, 默认值都是真实现。
**不得**给分支本身留开关(配置键/环境变量/`_force_windows` 一律不加) —— 分支要真跑。
"""
import errno
import itertools
import logging
import os
import posixpath
import re
import shutil
import stat
import struct
import tempfile
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from . import utils
from .clock import SYSTEM_CLOCK

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- 常量

# 链接形态(与 plan §3.2「链接能力阶梯」一一对应; 字符串进 state/界面, 不随代码改名)
KIND_JUNCTION = "junction"
KIND_SYMLINK = "symlink"
KIND_HARDLINK = "hardlink"
# 非链接节点的形态(路径链逐跳探测用, 与上面三种同属「事实」而非「结论」)
KIND_DIR = "dir"
KIND_FILE = "file"
KIND_MOUNT = "mount"
KIND_OTHER = "other"

# Windows 重解析点标签(区分 junction 与符号链接的唯一可靠依据 —— islink 对两者都为真)
IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003
IO_REPARSE_TAG_SYMLINK = 0xA000000C

# Windows 路径长度硬上限: 实测 259 可建、260 起一律 WinError 1314(带 \\?\ 前缀同样失败)
WIN_MAX_PATH = 260

# 权限类错误: 1314 与 EPERM/EACCES 都可能出现在建链失败上(1314 有二义性, 见 classify_link_failure)
ERROR_PRIVILEGE_NOT_HELD = 1314

# 探测临时目录名前缀(每次探测独立子目录, 用完删净)
_PROBE_PREFIX = ".auto-qb-alias-probe-"

_probe_seq = itertools.count(1)

# ---------------------------------------------------------------- 结果类型


@dataclass(frozen=True)
class LinkProbe:
    """单项链接能力的探测结果(ok=False 时 error 是给人看的原因, 直接进界面/回执)"""

    ok: bool
    detail: str = ""
    error: str = ""


@dataclass(frozen=True)
class PathInspection:
    """单个路径的只读探测事实(路径链逐跳展示用, §P2-1)

    `status` 是探测本身的结果(ok/missing/permission/unknown); 判不了的一律 unknown,
    **不猜**类型 —— 界面按原因文案显示「未确认」。
    """

    status: str
    kind: str = ""
    target: str = ""  # 链接的原始目标(未归一; 归一由调用方做)
    nlink: int = 0
    is_mount: bool = False
    error: str = ""


@dataclass(frozen=True)
class AliasCapability:
    """一次能力探测的完整事实(不可变; 缓存后供界面与闸门共用)

    字段口径:
    - `process_os` / `host_os`: 进程所在 OS 与**宿主** OS。容器里两者可能不同
      (Linux 容器 + Windows 宿主 = Docker Desktop/WSL2), 这正是 §3.3 要拒绝的那一行。
    - `foreign_fs`: `work_dir` 所在挂载的文件系统类型(`drvfs` = WSL-on-NTFS, `9p`/`virtiofs`
      = Docker Desktop 共享挂载), None = 读不到 /proc/mounts 或本地盘。
    - `link_visible_to_host`: 本进程建出的链接**宿主**能否读到。WSL-on-NTFS 为 False
      (LX 重解析点, Windows 侧 Errno 22, 实测)。
    - `uac_available`: 提权通道是否可用(仅 Windows 有意义) —— 无可见窗口站的会话
      (服务/SSH/计划任务)弹不出 UAC, 此时「需提权的 symlink」等于不可用。
    """

    process_os: str
    host_os: str
    container: bool
    wsl: bool
    path_style: str
    foreign_fs: Optional[str]
    link_visible_to_host: bool
    junction: LinkProbe
    dir_symlink: LinkProbe
    file_symlink: LinkProbe
    hardlink: LinkProbe
    uac_available: bool
    probe_root: str
    probed_at: float
    notes: Tuple[str, ...] = field(default=())

    @property
    def dir_alias_kind(self) -> Optional[str]:
        """目录别名可用形态(§3.2 阶梯: junction -> POSIX/Windows 目录 symlink); None = 不可用"""
        if not self.link_visible_to_host:
            return None
        if self.junction.ok:
            return KIND_JUNCTION
        if self.dir_symlink.ok:
            return KIND_SYMLINK
        return None

    def file_alias_kind(self, same_volume: bool) -> Optional[str]:
        """逐文件别名可用形态; None = 不可用

        阶梯按平台分叉(§3.2): Windows 先同卷硬链接(免权限)再 symlink(可能要 UAC);
        POSIX 先 symlink(免权限)再同卷硬链接。`same_volume` 由调用方给出 —— 硬链接
        跨卷不可能, 探测本身只能证明「同卷硬链接可建」。
        """
        if not self.link_visible_to_host:
            return None
        if self.process_os == "windows":
            if same_volume and self.hardlink.ok:
                return KIND_HARDLINK
            return KIND_SYMLINK if self.file_symlink.ok else None
        if self.file_symlink.ok:
            return KIND_SYMLINK
        if same_volume and self.hardlink.ok:
            return KIND_HARDLINK
        return None

    def as_dict(self) -> Dict[str, object]:
        """扁平字典(界面/接口展示用; 不含 qB 侧事实, 那些由调用方拼)"""
        return {
            "process_os": self.process_os,
            "host_os": self.host_os,
            "container": self.container,
            "wsl": self.wsl,
            "path_style": self.path_style,
            "foreign_fs": self.foreign_fs,
            "link_visible_to_host": self.link_visible_to_host,
            "junction": {
                "ok": self.junction.ok,
                "detail": self.junction.detail,
                "error": self.junction.error
            },
            "dir_symlink":
                {
                    "ok": self.dir_symlink.ok,
                    "detail": self.dir_symlink.detail,
                    "error": self.dir_symlink.error
                },
            "file_symlink":
                {
                    "ok": self.file_symlink.ok,
                    "detail": self.file_symlink.detail,
                    "error": self.file_symlink.error
                },
            "hardlink": {
                "ok": self.hardlink.ok,
                "detail": self.hardlink.detail,
                "error": self.hardlink.error
            },
            "uac_available": self.uac_available,
            "dir_alias_kind": self.dir_alias_kind,
            "file_alias_kind_same_volume": self.file_alias_kind(True),
            "file_alias_kind_cross_volume": self.file_alias_kind(False),
            "probe_root": self.probe_root,
            "probed_at": self.probed_at,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class SupportVerdict:
    """§3.3 能力矩阵的一行(环境组合 -> 支持与否 + 原因)

    `row` 是矩阵的行名, 测试与日志按它断言(不是给人看的长句); `reason` 才进界面。
    """

    row: str
    dir_alias: Optional[str]
    file_alias: Optional[str]
    supported: bool
    reason: str


# ---------------------------------------------------------------- 平台事实


def _process_os() -> str:
    """进程所在 OS(平台判定走 utils.is_* 单点, 不另立 sys.platform 判据)"""
    if utils.is_windows():
        return "windows"
    if utils.is_linux():
        return "linux"
    if utils.is_mac():
        return "darwin"
    return "posix"


def _read_text(path: str) -> str:
    """读一个小文本文件(读不到返回空串; 只用于 /proc 下的只读探针)"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def is_wsl(env=None, proc_version: Optional[str] = None) -> bool:
    """是否运行在 WSL 里(env 优先; 否则看 /proc/version 的 microsoft 标记)"""
    env = os.environ if env is None else env
    if env.get("WSL_DISTRO_NAME") or env.get("WSL_INTEROP"):
        return True
    if proc_version is None:
        proc_version = _read_text("/proc/version")
    return "microsoft" in proc_version.lower()


def container_evidence(env=None, exists=None, read_text=None) -> Tuple[str, ...]:
    """容器判定证据(多条, 全部只读; 空元组 = 不在容器里)

    为什么用证据链而不是一个判据: `/.dockerenv` 在老版本/被裁剪的镜像里可能不存在,
    cgroup 在 cgroup v2 下可能只写 `0::/`; 任何单条都会漏判。证据也进 `notes`,
    用户看到「检测到容器」时能立刻知道我们凭什么这么判。
    """
    env = os.environ if env is None else env
    exists = os.path.exists if exists is None else exists
    read_text = _read_text if read_text is None else read_text
    out = []
    for key in ("container", "DOCKER_CONTAINER", "KUBERNETES_SERVICE_HOST", "POD_NAME"):
        value = env.get(key)
        if value and value != "0":
            out.append(f"env {key}={value}")
    for sentinel in ("/.dockerenv", "/run/.containerenv"):
        if exists(sentinel):
            out.append(f"存在 {sentinel}")
    cgroup = read_text("/proc/1/cgroup")
    for marker in ("docker", "kubepods", "lxc", "containerd", "garden"):
        if marker in cgroup:
            out.append(f"/proc/1/cgroup 含 {marker}")
            break
    return tuple(out)


def _unescape_mount(field_text: str) -> str:
    """还原 /proc/mounts 里的八进制转义(`\\040` = 空格; 路径带空格时不还原就匹配不上)"""
    return re.sub(r"\\[0-7]{3}", lambda m: chr(int(m.group(0)[1:], 8)), field_text)


@dataclass(frozen=True)
class MountInfo:
    """一条挂载(来自 /proc/mounts)

    `options` 不是装饰: WSL2 的 Windows 盘 fstype 是 `9p`, 而「这是 drvfs」这个事实只写在
    挂载选项里(`aname=drvfs;path=D:\\;...`)—— 只看 fstype 会把它当成普通 9p 共享,
    于是漏掉 §2.4 那条反例(实测: WSL 建链接成功, Windows 侧 Errno 22)。
    """

    mount_point: str
    fstype: str
    options: str

    @property
    def is_drvfs(self) -> bool:
        """Windows 盘经 WSL 挂进来(drvfs 驱动; 新版 WSL 报 9p + aname=drvfs)"""
        return self.fstype == "drvfs" or "drvfs" in self.options


def mount_info_for_path(path: str, mounts_text: Optional[str] = None) -> Optional[MountInfo]:
    """路径所在挂载(最长前缀匹配); 非 Linux / 读不到 => None

    `mounts_text` 可注入, 让解析逻辑在 Windows 开发机上也能测。
    """
    if mounts_text is None:
        mounts_text = _read_text("/proc/mounts")
        if not mounts_text:
            return None
    # 用 posixpath 而不是 os.path: 挂载表是 POSIX 口径, 在 Windows 上跑测试时
    # os.path.abspath("/mnt/c/x") 会拼成 "H:\\mnt\\c\\x", 与挂载点永远匹配不上。
    target = posixpath.normpath(path)
    best: Optional[MountInfo] = None
    best_len = -1
    for line in mounts_text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        info = MountInfo(mount_point=_unescape_mount(parts[1]), fstype=parts[2], options=" ".join(parts[3:]))
        mp = info.mount_point
        if mp == "/" or target == mp or target.startswith(mp.rstrip("/") + "/"):
            if len(mp) > best_len:  # 最长前缀 = 最具体的挂载
                best, best_len = info, len(mp)
    return best


def windows_backed_mount(path: str,
                         mounts_text: Optional[str] = None,
                         wsl: Optional[bool] = None) -> Optional[MountInfo]:
    """路径所在挂载是否由 **Windows 宿主** 提供(跨 OS 共享盘); None = 本地盘 / 不可判定

    判据(保守, 只认有实测支撑的形态):
    - 挂载带 drvfs 标记(WSL 的 /mnt/c 一类, 新旧内核分别报 `drvfs` 与 `9p+aname=drvfs`);
    - WSL 里挂在 `/mnt/<单个盘符>` 上的任何文件系统(WSL 的约定, 与 drvfs 标记互为兜底)。

    Docker Desktop 的 9p/virtiofs 共享挂载**不在此列**: 同一形态在 macOS 宿主上是可用的,
    仅凭容器内信息分不出宿主 OS —— 记为「未实测」而不是猜(见 plan §8.5 未覆盖项)。
    """
    info = mount_info_for_path(path, mounts_text)
    if info is None:
        return None
    if info.is_drvfs:
        return info
    if (wsl if wsl is not None else is_wsl()) and re.match(r"^/mnt/[A-Za-z]/?$", info.mount_point):
        return info
    return None


def _host_os(process_os: str, wsl: bool, foreign: Optional[MountInfo]) -> str:
    """宿主 OS 推断: WSL 与 Windows 共享挂载都意味着「Linux 进程 + Windows 宿主」"""
    if process_os == "windows":
        return "windows"
    if wsl or foreign is not None:
        return "windows"
    return process_os


def _link_visible_to_host(process_os: str, foreign: Optional[MountInfo]) -> bool:
    """本进程建出的链接, 宿主能否读到

    唯一被实测钉死的反例: Linux 进程在 NTFS 上 `ln -s` 成功, 但写的是 **LX 重解析点**,
    Windows 侧 `open()` 报 `Errno 22`、`os.path.islink` 为 False(§2.4)。其余组合没有反例,
    按「能读到」处理 —— 保守默认针对的是**不可判定**, 不是「没实测过就否定」。
    """
    if process_os == "windows":
        return True
    return foreign is None


def is_unc(path: str) -> bool:
    """Windows UNC 路径(`\\\\server\\share\\...`); 盘符/相对路径/设备前缀(`\\\\?\\` `\\\\.\\`)均 False"""
    p = path.replace("/", "\\")
    if p.startswith("\\\\?\\") or p.startswith("\\\\.\\"):
        return False
    return p.startswith("\\\\")


_DRIVE_REMOTE = 4


def is_remote_path(path: str) -> bool:
    """路径是否落在**远端存储**: UNC, 或 Windows 盘符映射的网络共享(GetDriveTypeW == DRIVE_REMOTE)

    仅 is_unc 不够: `Z:` 映射到 NAS 时语法上是盘符, 但 lstat/readlink 同样走网络, 共享离线
    时会长时间阻塞调用线程。路径链探测据此判「不做 syscall」; 判不了时按本地处理(保持原行为)。
    """
    logical = strip_device_prefix(path).replace("/", "\\")
    if is_unc(logical):
        return True
    if not utils.is_windows():
        return False
    match = re.match(r"([A-Za-z]):", logical)
    if not match:
        return False
    return _drive_type(f"{match.group(1).upper()}:\\") == _DRIVE_REMOTE


def _drive_type(root: str) -> int:
    """GetDriveTypeW; 取不到(非 Windows / 调用失败)返回 0(DRIVE_UNKNOWN), 调用方按本地处理"""
    try:
        import ctypes

        get_type = ctypes.WinDLL("kernel32", use_last_error=True).GetDriveTypeW
        get_type.argtypes = [ctypes.c_wchar_p]
        get_type.restype = ctypes.c_uint
        return int(get_type(root))
    except Exception:  # noqa: BLE001 - 不新增拒绝面
        return 0


def same_volume(a: str, b: str) -> Optional[bool]:
    """两个路径是否在同一卷(st_dev 相等); 任一侧不可读 => None(不可判定, 闸门按拒绝处理)"""
    try:
        dev_a = os.stat(utils.add_long_path_prefix_for_win(a)).st_dev
        dev_b = os.stat(utils.add_long_path_prefix_for_win(b)).st_dev
    except OSError:
        return None
    return dev_a == dev_b


def volume_free(path: str) -> Optional[int]:
    """路径所在卷的剩余字节; 不可读 => None(界面显示「不可判定」而不是 0)"""
    try:
        return shutil.disk_usage(utils.add_long_path_prefix_for_win(path)).free
    except OSError:
        return None


def classify_link_failure(path: str, exc: BaseException) -> str:
    """把建链失败翻译成给人看的原因(§3.2 能力校正)

    **判定顺序不能反**: `1314` 有二义性 —— 长路径与权限不足报同一个码, 所以先按路径长度
    分类(>=260 一律判长路径), 再按错误码分类(<260 且 1314/EPERM => 需提权)。顺序反了
    就会把长路径说成「请提权」, 用户提权后依然失败。
    """
    length = len(os.path.abspath(path))
    if utils.is_windows() and length >= WIN_MAX_PATH:
        return (f"路径过长({length} 字符 >= {WIN_MAX_PATH}): Windows 上文件级链接建不出来 "
                "—— 需改用目录别名, 或缩短路径")
    winerror = getattr(exc, "winerror", None)
    code = getattr(exc, "errno", None)
    if winerror == ERROR_PRIVILEGE_NOT_HELD or code in (errno.EPERM, errno.EACCES):
        return "权限不足(需提权/UAC): 以管理员身份运行 auto-qb, 或换同卷目标走硬链接"
    return f"建链失败: {exc}"


# ---------------------------------------------------------------- 探测临时目录


def _probe_dir(work_dir: str) -> Optional[str]:
    """在 work_dir 下开一个独立探测子目录(失败返回 None); 每次探测互不干扰"""
    try:
        os.makedirs(work_dir, exist_ok=True)
        path = os.path.join(work_dir, f"{_PROBE_PREFIX}{os.getpid()}-{next(_probe_seq)}")
        os.mkdir(utils.add_long_path_prefix_for_win(path))
        return path
    except OSError:
        return None


def _is_link_like(path: str) -> bool:
    """是不是一条链接(junction / 符号链接); 硬链接不算(它没有「链接对象」)"""
    try:
        st = os.lstat(utils.add_long_path_prefix_for_win(path))
    except OSError:
        return False
    if getattr(st, "st_reparse_tag", 0) == IO_REPARSE_TAG_MOUNT_POINT:
        return True
    return stat.S_ISLNK(st.st_mode)


def _remove_tree(path: str) -> None:
    """删掉探测临时目录: 逐条非递归, **绝不跟随链接**(目录别名只删链接本身)

    不用 `shutil.rmtree`: 它对 junction 的处理依赖版本, 而探测目录里恰好有链接。
    """
    try:
        entries = list(os.scandir(utils.add_long_path_prefix_for_win(path)))
    except OSError:
        return
    for entry in entries:
        child = os.path.join(path, entry.name)
        try:
            if _is_link_like(child):
                remove_alias(child)
            elif entry.is_dir(follow_symlinks=False):
                _remove_tree(child)
            else:
                os.unlink(utils.add_long_path_prefix_for_win(child))
        except OSError:
            logger.debug(f"alias_fs 探测清理失败: {child}")
    try:
        os.rmdir(utils.add_long_path_prefix_for_win(path))
    except OSError:
        logger.debug(f"alias_fs 探测目录删除失败: {path}")


# ---------------------------------------------------------------- 单项探测


def probe_symlink(work_dir: str, *, target_is_directory: bool, try_create=None) -> LinkProbe:
    """探测符号链接可建性(建 -> 可见 -> 穿透读 -> 删)

    `try_create` 是 §8.6 指定的唯一注入点(默认 `os.symlink`); 单测传一个抛
    `OSError(1314)` 的替身来走「需提权」分支 —— 被测分支仍是生产分支。
    """
    fn = os.symlink if try_create is None else try_create
    kind_text = "目录" if target_is_directory else "文件"
    root = _probe_dir(work_dir)
    if root is None:
        return LinkProbe(False, error=f"探测目录不可用: {work_dir}")
    target = os.path.join(root, "target")
    link = os.path.join(root, "link")
    try:
        if target_is_directory:
            os.mkdir(target)
            with open(os.path.join(target, "probe.txt"), "w", encoding="utf-8") as f:
                f.write("auto-qb")
        else:
            with open(target, "w", encoding="utf-8") as f:
                f.write("auto-qb")
        try:
            fn(target, link, target_is_directory=target_is_directory)
        except (OSError, NotImplementedError) as e:
            return LinkProbe(False, error=classify_link_failure(link, e))
        # 建链调用返回成功不算数: 实测 ctypes 直调可能「成功但链接不可见」
        if not _is_link_like(link):
            return LinkProbe(False, error="建链调用成功但链接不可见(路径过长或平台不支持)")
        if target_is_directory:
            if not os.path.isfile(os.path.join(link, "probe.txt")):
                return LinkProbe(False, error="链接存在但无法穿透读取(目录)")
        else:
            try:
                with open(link, encoding="utf-8") as f:
                    content = f.read()
            except OSError as e:
                return LinkProbe(False, error=f"链接存在但无法穿透读取: {e}")
            if content != "auto-qb":
                return LinkProbe(False, error="链接存在但读回内容不符")
        return LinkProbe(True, detail=f"{kind_text}符号链接可建({link} -> {target})")
    finally:
        _remove_tree(root)


def probe_hardlink(work_dir: str, *, try_create=None) -> LinkProbe:
    """探测硬链接可建性(同卷才可能; 校验同 inode + nlink>=2)

    `try_create` 默认 `os.link`(§8.6 注入点)。硬链接只证明「本卷可建」——
    跨卷是否可用由 `same_volume()` 在闸门处判定。
    """
    fn = os.link if try_create is None else try_create
    root = _probe_dir(work_dir)
    if root is None:
        return LinkProbe(False, error=f"探测目录不可用: {work_dir}")
    target = os.path.join(root, "target")
    link = os.path.join(root, "link")
    try:
        with open(target, "w", encoding="utf-8") as f:
            f.write("auto-qb")
        try:
            fn(target, link)
        except (OSError, NotImplementedError) as e:
            return LinkProbe(False, error=classify_link_failure(link, e))
        try:
            st_target = os.stat(utils.add_long_path_prefix_for_win(target))
            st_link = os.stat(utils.add_long_path_prefix_for_win(link))
        except OSError as e:
            return LinkProbe(False, error=f"硬链接建后不可读: {e}")
        if st_target.st_ino != st_link.st_ino or st_link.st_nlink < 2:
            return LinkProbe(False, error="建出的不是同一 inode(文件系统不支持硬链接)")
        return LinkProbe(True, detail=f"硬链接可建(同卷, nlink={st_link.st_nlink})")
    finally:
        _remove_tree(root)


def probe_junction(work_dir: str, *, try_create=None) -> LinkProbe:
    """探测 Windows junction 可建性(免管理员; 非 Windows 恒不可用)

    `try_create` 默认 `_win_create_junction`(§8.6 注入点)。
    """
    if not utils.is_windows():
        return LinkProbe(False, error="junction 仅 Windows 支持(本平台用目录符号链接)")
    fn = _win_create_junction if try_create is None else try_create
    root = _probe_dir(work_dir)
    if root is None:
        return LinkProbe(False, error=f"探测目录不可用: {work_dir}")
    target = os.path.join(root, "target")
    link = os.path.join(root, "link")
    try:
        os.mkdir(target)
        with open(os.path.join(target, "probe.txt"), "w", encoding="utf-8") as f:
            f.write("auto-qb")
        try:
            fn(link, target)
        except (OSError, NotImplementedError) as e:
            return LinkProbe(False, error=classify_link_failure(link, e))
        kind = alias_kind_of(link)
        if kind != KIND_JUNCTION:
            return LinkProbe(False, error=f"建出的不是 junction(实得 {kind or '非链接'})")
        if not os.path.isfile(os.path.join(link, "probe.txt")):
            return LinkProbe(False, error="junction 存在但无法穿透读取")
        return LinkProbe(True, detail=f"junction 可建({link} -> {target})")
    finally:
        _remove_tree(root)


# ---------------------------------------------------------------- 链接原语


def create_dir_alias(link: str, target: str, kind: str) -> None:
    """建一条目录别名(junction / 目录符号链接); 目标必须已存在"""
    if kind == KIND_JUNCTION:
        _win_create_junction(link, target)
    elif kind == KIND_SYMLINK:
        os.symlink(target, link, target_is_directory=True)
    else:
        raise ValueError(f"目录别名不支持形态: {kind}")


def create_file_alias(link: str, target: str, kind: str) -> None:
    """建一条逐文件别名(硬链接 / 文件符号链接)"""
    if kind == KIND_HARDLINK:
        os.link(target, link)
    elif kind == KIND_SYMLINK:
        os.symlink(target, link)
    else:
        raise ValueError(f"文件别名不支持形态: {kind}")


def alias_kind_of(path: str) -> Optional[str]:
    """识别一条链接的形态; None = 不是链接(或不可读)

    junction 与符号链接靠重解析点标签区分(`islink` 对两者都为真); 硬链接没有链接对象,
    只能按 `st_nlink > 1` 认出「这份数据还有别的名字」—— 是不是**我们要找的那个**名字
    由调用方比对 inode 判定。
    """
    try:
        st = os.lstat(utils.add_long_path_prefix_for_win(path))
    except OSError:
        return None
    tag = getattr(st, "st_reparse_tag", 0)
    if tag == IO_REPARSE_TAG_MOUNT_POINT:
        return KIND_JUNCTION
    if tag == IO_REPARSE_TAG_SYMLINK:
        return KIND_SYMLINK
    if stat.S_ISLNK(st.st_mode):
        return KIND_SYMLINK
    if st.st_nlink > 1:
        return KIND_HARDLINK
    return None


def alias_target(path: str) -> Optional[str]:
    """链接指向的目标(junction / 符号链接); 硬链接与非链接返回 None"""
    if alias_kind_of(path) == KIND_HARDLINK:
        return None
    try:
        return os.readlink(utils.add_long_path_prefix_for_win(path))
    except OSError:
        return None


#: Windows NT 设备前缀(junction 的 readlink 结果常见 `\??\H:\...`)
_DEVICE_PREFIX = "\\??\\"


def strip_device_prefix(path: str) -> str:
    """剥掉 NT/扩展长度前缀, 统一成逻辑路径(`\\??\\H:\\a` / `\\\\?\\H:\\a` -> `H:\\a`)"""
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[8:]
    if path.startswith("\\\\?\\"):
        return path[4:]
    if path.startswith(_DEVICE_PREFIX):
        return path[4:]
    return path


def resolve_link_target(raw: str, link_path: str) -> str:
    """把 readlink 的原始结果归一成**绝对逻辑路径**; 无法映射时返回空串

    - `\\??\\` / `\\\\?\\` 前缀剥掉(保留原目标只用于展示的出处, 这里给探测用);
    - 相对目标按链接所在目录拼接(POSIX 相对符号链接的常见形态);
    - 卷设备路径(`\\??\\Volume{...}`)无法映射到盘符, 返回空串让调用方标「未确认」。
    """
    target = strip_device_prefix((raw or "").strip())
    if not target:
        return ""
    if target.startswith("Volume{"):
        return ""
    is_abs = os.path.isabs(target) or bool(re.match(r"^[A-Za-z]:[\\/]", target))
    if not is_abs:
        parent = os.path.dirname(strip_device_prefix(link_path))
        target = os.path.join(parent, target)
    return os.path.normpath(target)


def _classify_probe_error(exc: OSError) -> Tuple[str, str]:
    """OSError -> (status, 人话原因); 判不了归 unknown, 不把权限不足说成不存在"""
    winerror = getattr(exc, "winerror", None)
    code = getattr(exc, "errno", None)
    if isinstance(exc, (FileNotFoundError, NotADirectoryError)) or winerror in (2, 3) \
            or code in (errno.ENOENT, errno.ENOTDIR):
        return "missing", "路径不存在"
    if isinstance(exc, PermissionError) or winerror in (5, 1314) \
            or code in (errno.EACCES, errno.EPERM):
        return "permission", "权限不足"
    return "unknown", f"无法读取: {exc}"


def _is_mount_point(logical: str, st: os.stat_result) -> bool:
    """目录是否挂载点(`st_dev` 与父目录不同); 根目录恒 False

    仅供 POSIX 风格的「挂载点」识别; Windows 的卷挂载点会被重解析点标签先识别成 junction。
    """
    absolute = os.path.abspath(strip_device_prefix(logical))
    parent = os.path.dirname(absolute)
    if parent == absolute:
        return False
    try:
        parent_st = os.lstat(utils.add_long_path_prefix_for_win(parent))
    except OSError:
        return False
    return parent_st.st_dev != st.st_dev


def inspect_path(path: str) -> PathInspection:
    """逐跳探测单个路径(lstat/readlink), 返回事实而非结论

    分类口径(§P2-1): 符号链接 / junction / 硬链接 / 普通目录 / 挂载点 / 其它;
    路径不存在、权限不足、类型未知分别给出可展示原因 —— **判不了就 unknown**。
    """
    logical = strip_device_prefix(path)
    probe = utils.add_long_path_prefix_for_win(logical)
    try:
        st = os.lstat(probe)
    except OSError as exc:
        status, reason = _classify_probe_error(exc)
        return PathInspection(status=status, error=reason)

    tag = getattr(st, "st_reparse_tag", 0)
    is_mount = False
    if tag == IO_REPARSE_TAG_MOUNT_POINT:
        kind = KIND_JUNCTION
    elif tag == IO_REPARSE_TAG_SYMLINK:
        kind = KIND_SYMLINK
    elif stat.S_ISLNK(st.st_mode):
        kind = KIND_SYMLINK
    elif stat.S_ISDIR(st.st_mode):
        is_mount = _is_mount_point(logical, st)
        kind = KIND_MOUNT if is_mount else KIND_DIR
    elif stat.S_ISREG(st.st_mode):
        kind = KIND_HARDLINK if st.st_nlink > 1 else KIND_FILE
    else:
        kind = KIND_OTHER

    target = ""
    if kind in (KIND_JUNCTION, KIND_SYMLINK):
        try:
            target = os.readlink(probe)
        except OSError as exc:
            status, reason = _classify_probe_error(exc)
            return PathInspection(status="unknown", kind=kind, nlink=st.st_nlink, error=reason)
    return PathInspection(status="ok", kind=kind, target=target, nlink=st.st_nlink, is_mount=is_mount)


def remove_alias(path: str) -> None:
    """删掉一条别名: **非递归**, 绝不跟随链接删目标内容(幂等, 已消失即返回)

    Windows 上目录别名(junction / 目录符号链接)只能用 `os.rmdir`, 文件链接用 `os.unlink`;
    POSIX 上符号链接一律 `os.unlink`(目录链接也是链接, `rmdir` 会 ENOTDIR)。
    """
    p = utils.add_long_path_prefix_for_win(path)
    try:
        st = os.lstat(p)
    except OSError:
        return
    tag = getattr(st, "st_reparse_tag", 0)
    if tag == IO_REPARSE_TAG_MOUNT_POINT:
        os.rmdir(p)
        return
    if stat.S_ISLNK(st.st_mode) and os.name == "nt" and os.path.isdir(p):
        os.rmdir(p)  # Windows 目录符号链接: RemoveDirectory 才删得掉链接本身
        return
    os.unlink(p)


# ---------------------------------------------------------------- 别名重定向(计划 26-11-05-0808 S5, D15: 0247 S6③ 设想从零实现)
# supersede 重定向的三个原语: 幂等判定(alias_points_to)/ 占用探测(probe_alias_rebuild_busy)/
# 重定向(retarget_alias: 读旧目标 -> 删旧链接(非递归绝不跟随) -> 按形态建新链接 -> 穿透校验)。
# 形态分流照 create_dir_alias/create_file_alias 口径: junction/目录 symlink 走目录别名,
# 硬链接/文件 symlink 走文件别名; 形态优先沿用**现存链接**的实际形态(qB 读的就是它),
# 链接缺失(搬移经别名时 qB 把链接改名带走等)才按调用方给的 kind / 目标类型重建。


def _norm_abs(path: str) -> str:
    """重定向指向比较用的归一形(绝对路径 + normcase; Windows 大小写不敏感语义)"""
    p = os.path.abspath(strip_device_prefix(path or ""))
    return os.path.normcase(p)


def alias_points_to(link: str, target: str) -> bool:
    """链接现指是否恰为目标(重定向幂等判定; 黄金法则 1: 已是目标指向则跳过)

    - junction / 符号链接: readlink 原始结果经 resolve_link_target 归一后与目标比
      (normcase + abspath, NT 设备前缀/相对目标都吃得下);
    - 硬链接: 没有链接对象, 比两侧 stat 的 inode(同 inode = 已指向同一份数据);
    - 不是链接或读不了: False(调用方按需重建/报错)。
    """
    kind = alias_kind_of(link)
    if kind == KIND_HARDLINK:
        try:
            return os.stat(utils.add_long_path_prefix_for_win(link)).st_ino == os.stat(
                utils.add_long_path_prefix_for_win(target)
            ).st_ino
        except OSError:
            return False
    if kind in (KIND_JUNCTION, KIND_SYMLINK):
        raw = alias_target(link)
        if not raw:
            return False
        return _norm_abs(resolve_link_target(raw, link)) == _norm_abs(target)
    return False


def probe_alias_rebuild_busy(link: str) -> Optional[str]:
    """别名重建可行性探测(S5 搬前预检加项, D20: 句柄占用类失败前移): 返回拒绝文案, None = 未检出占用

    原理(2026-11-06 Win32 实测定型): 重建要先删后建 —— 删除成败的忠实预言 = 以 **DELETE
    访问权 + 全共享模式**(FILE_SHARE_READ|WRITE|DELETE)打开链接本体: 打开成功 ⟺
    「此刻真删也会成功」(实测三元组逐一对照: 持有者 share=0 / R|W 时探测与 os.unlink
    同报 WinError 32; 持有者带 FILE_SHARE_DELETE 时两者都放行 —— POSIX 式延迟删除语义;
    共享检查是双向的, 探测自己必须开全共享, 冲突才精确落在「对方没给共享删除」这一种)。
    junction/重解析点的打开走 OPEN_REPARSE_POINT, 现代 Windows 上链接本体的删除对读
    句柄稳健(实测持句柄 rmdir 全部成功), 探测随之放行 —— 不假阳、不空拦。

    qB 做种不假阳的依据: libtorrent 自身要在做种中 rename/move 文件, 打开文件带
    FILE_SHARE_DELETE —— 做种句柄不会让 DELETE 探测失败(整组成员在搬前预检时点仍在
    做种, 这是探测面能覆盖文件级形态的前提)。

    保守边界: 探测异常(路径消失/权限/远端超时)一律 None —— 判不了**不拦**(漏报由搬后
    重试至收敛兜底, 误报会拦死正常迁移, 两害取其轻); 打开 DELETE 句柄后立即 CloseHandle,
    不置 disposition, 零删除副作用。
    """
    if not utils.is_windows():
        return None  # POSIX 删链接无句柄占用失败形态(目录可带打开句柄删除)
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = k32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
        wintypes.HANDLE
    ]
    create_file.restype = wintypes.HANDLE
    close_handle = k32.CloseHandle
    close_handle.restype = wintypes.BOOL
    p = utils.add_long_path_prefix_for_win(link)
    flags = _FILE_FLAG_OPEN_REPARSE_POINT
    try:
        if os.path.isdir(p):
            flags |= _FILE_FLAG_BACKUP_SEMANTICS  # 目录/目录链接本体必须带 BACKUP_SEMANTICS 才打得开
    except OSError:
        return None  # 存在性判不了: 不拦(与「其它探测异常」同口径)
    _DELETE_ACCESS = 0x00010000  # DELETE(NT 访问权); 打开本身零删除副作用(删除须再设 disposition)
    _SHARE_ALL = 0x1 | 0x2 | 0x4  # FILE_SHARE_READ|WRITE|DELETE: 冲突精确落在「对方未开共享删除」
    handle = create_file(p, _DELETE_ACCESS, _SHARE_ALL, None, _OPEN_EXISTING, flags, None)
    if handle != wintypes.HANDLE(-1).value:
        close_handle(handle)
        return None  # DELETE 独占打开成功 = 此刻真删也会成功
    err = ctypes.get_last_error()
    if err in (2, 3):  # ERROR_FILE_NOT_FOUND / PATH_NOT_FOUND: 链接本就不在, 重建无占用可言
        return None
    if err == 32:  # ERROR_SHARING_VIOLATION
        return ("链接本体被其它进程占用(WinError 32, 删除权限探测): 常见为杀毒/备份/同步工具握着文件且未开共享删除 —— "
                "关闭占用者后重试")
    return None  # 其余错误判不了占用与否: 不拦, 交搬后重试


def retarget_alias(link: str, target: str, kind: Optional[str] = None) -> str:
    """重定向一条别名到新目标(S5 supersede 单点; D15: 0247 S6③ 设想从零实现)

    步骤: 幂等判定 -> 读旧目标(留诊断) -> 删旧链接(remove_alias, 非递归绝不跟随) ->
    按形态建新链接(create_dir_alias/create_file_alias 同口径分流) -> 穿透校验(经新链接
    读得到目标内容)。链接缺失(搬移把链接改名带走/外部误删)时按 kind 重建 —— 重建即
    恢复服务, 与 rebuild-from-journal 同语义。

    形态取舍: 现存链接的实际形态**优先**(qB 正在读的就是它, 保有形态零惊扰); 缺失时用
    调用方给的 kind(job plan 的 link_kind); 再缺失按目标类型推断(目录= Windows junction
    /POSIX 目录 symlink; 文件= symlink —— 推断面只兜旧账无 kind 的防御支)。hardlink 形态
    遇跨卷新目标时回落 KIND_SYMLINK(os.link 跨卷必 EXDEV, 见建链段注释) —— 由搬前预检
    保证回落可行(symlink 能力在场), 否则应在搬前整体拒绝而不是搬后吊死 supersede。

    返回: "skipped"(已指向目标, 零动作) / "retargeted"(删旧建新) / "rebuilt"(缺失重建)。
    失败抛 OSError/RuntimeError(删失败=占用/权限; 建/穿透失败=环境) —— 调用方按 D20
    搬后「重试至收敛」处置, 本函数保证失败时不留半截链接(建失败即删, 见 create 侧)。
    """
    existing = alias_kind_of(link)
    if existing is not None and alias_points_to(link, target):
        return "skipped"
    was_dir = False
    if existing is not None:
        was_dir = os.path.isdir(utils.add_long_path_prefix_for_win(link))
    elif kind is None:
        # 防御支: 无现存链接也无 kind(旧账/直调) —— 按目标类型推断
        kind = KIND_JUNCTION if utils.is_windows() else KIND_SYMLINK
        if not os.path.isdir(utils.add_long_path_prefix_for_win(target)):
            kind = KIND_SYMLINK
    form = existing or kind
    old_target = alias_target(link) if existing in (KIND_JUNCTION, KIND_SYMLINK) else None
    # 目录形态判定(建新链接与穿透校验共用同一谓词): junction 恒目录; symlink 沿用现存
    # 链接的目录性(os.path.isdir 穿透判, 悬空时回落到目标侧判断)。
    dir_like = form == KIND_JUNCTION or (
        form == KIND_SYMLINK and (was_dir or os.path.isdir(utils.add_long_path_prefix_for_win(target)))
    )
    # 目标存在性前置闸: 新目标不在就绝不动旧链接(删了建不回 = 现存别名被毁;
    # 上游时序保证重定向只发生在搬移完成、目标数据落位之后 —— 这里是最后一道防线)。
    target_probe = utils.add_long_path_prefix_for_win(target)
    if not os.path.exists(target_probe):
        raise RuntimeError(f"重定向拒绝: 新目标不存在({target}) —— 保留旧链接原样, 不做删建")
    # 删旧链接前先处理「位置被真目录/真文件占着」的形态: 与 _build_links 目录支同口径,
    # 只挪**空**目录(qB 搬走文件后的残留); 非空 = 有真数据, 绝不动(不猜)。
    try:
        st = os.lstat(utils.add_long_path_prefix_for_win(link))
        is_real_dir = stat.S_ISDIR(st.st_mode) and existing is None and \
            getattr(st, "st_reparse_tag", 0) == 0
    except OSError:
        is_real_dir = False
    if is_real_dir:
        if os.listdir(utils.add_long_path_prefix_for_win(link)):
            raise RuntimeError(f"重定向失败: 链接位置被非空真目录占据({link}), 不猜测不动数据")
        os.rmdir(utils.add_long_path_prefix_for_win(link))
    else:
        remove_alias(link)
    # 建新链接: 目录别名(junction/目录 symlink) vs 文件别名(硬链接/文件 symlink)
    if dir_like:
        create_dir_alias(link, target, form)
    elif form in (KIND_HARDLINK, KIND_SYMLINK):
        # 跨卷回落(收口评审 #2): hardlink 形态且新链接位置与新目标跨卷 => os.link 必 EXDEV,
        # 而删旧链接已先行(旧孪生被 qB 跨卷搬移后 nlink 收敛 1, alias_kind_of 认不出, 删的
        # 正是前任成员的现存数据名), 之后每拍重试恒失败 = 前任永停 supersede stage(D20 无从
        # 收敛)。跨卷时回落 KIND_SYMLINK: 成员经符号链接照常读, 形态对 qB 透明; 卷位判不了
        # (st_dev 不可得)按跨卷保守处理 —— symlink 同/跨卷皆可建, 宁降级也不进 EXDEV 死循环;
        # 回落也失败 => 抛错交 D20 搬后重试路径(搬前预检应已拦掉 symlink 也不可用的组合)。
        # 卷位探的是新链接的父目录(os.link 的新名落点), 链接本体缺失(重建支)也判得准。
        if form == KIND_HARDLINK and same_volume(os.path.dirname(link) or ".", target) is not True:
            form = KIND_SYMLINK
        os.makedirs(os.path.dirname(link) or ".", exist_ok=True)  # 与 _build_links 文件支同口径
        create_file_alias(link, target, form)
    else:
        raise ValueError(f"重定向不支持形态: {form}(link={link})")
    # 穿透校验: 经新链接读得到目标内容(目录= 可列; 文件= 尺寸一致)
    try:
        if dir_like:
            if not os.path.isdir(utils.add_long_path_prefix_for_win(link)):
                raise RuntimeError("目录别名建后不可穿透(isdir 为假)")
            os.listdir(utils.add_long_path_prefix_for_win(link))
        else:
            if not os.path.isfile(utils.add_long_path_prefix_for_win(link)):
                raise RuntimeError("文件别名建后不可穿透(isfile 为假)")
            if os.path.getsize(utils.add_long_path_prefix_for_win(link)) != os.path.getsize(
                utils.add_long_path_prefix_for_win(target)
            ):
                raise RuntimeError("文件别名穿透尺寸与目标不一致")
    except (OSError, RuntimeError) as e:
        raise RuntimeError(f"重定向穿透校验失败({link} -> {target}, 旧指 {old_target}): {e}") from e
    return "retargeted" if existing is not None else "rebuilt"


# ---------------------------------------------------------------- 能力矩阵(§3.3)


def platform_verdict(
    cap: AliasCapability,
    *,
    target_is_unc: bool = False,
    remote: bool = False,
    same_volume: bool = False,
) -> SupportVerdict:
    """把能力探测结果落到 §3.3 的某一行, 给出「支持 / 拒绝 + 原因」

    这是矩阵的**单点定义**: P2 的闸门调它, 不自己再判一遍平台。参数里 `target_is_unc` /
    `remote` / `same_volume` 是探测拿不到的事实(qB 侧与目标侧), 由闸门传入。

    `same_volume` 默认 False(保守默认: 不假定同卷) —— 调用方必须在证明同卷后再传 True。
    """
    if remote:
        return SupportVerdict(
            "remote_no_shared_fs", None, None, False, "远程 qB 无共享文件系统: 本机建不出 qB 能读的链接 —— 只有独占情形可用(qB 自己搬, 不需要别名)"
        )
    if not cap.link_visible_to_host:
        return SupportVerdict(
            "container_cross_os", None, None, False,
            f"跨 OS 容器组合(进程 {cap.process_os} / 宿主 {cap.host_os}): 建出的是 LX 重解析点, "
            f"宿主侧读不了(实测 Errno 22) —— 只有独占情形可用"
        )
    dir_kind = cap.dir_alias_kind
    file_kind = cap.file_alias_kind(same_volume)
    if cap.container:
        row = "container_same_os"
    elif cap.process_os == "windows":
        row = "windows_unc" if target_is_unc else "windows_local"
    elif cap.process_os in ("linux", "darwin"):
        row = cap.process_os
    else:
        row = "unknown"
    if dir_kind or file_kind:
        return SupportVerdict(row, dir_kind, file_kind, True, "可建出 qB 能读的链接")
    reasons = [
        f"{name}: {probe.error}"
        for name, probe in (("junction", cap.junction), ("目录链接", cap.dir_symlink), ("文件链接", cap.file_symlink))
        if probe.error
    ]
    return SupportVerdict(row, None, None, False, "无法建出 qB 能读的链接 —— " + "; ".join(reasons))


# ---------------------------------------------------------------- 整机探测与缓存


def probe_capability(work_dir: Optional[str] = None) -> AliasCapability:
    """探测一台机器(一个卷)的链接能力; **不抛异常**, 探测失败即「不可用」

    `work_dir` 决定**在哪个卷上探测**: 缺省系统临时目录(= 进程级能力); P3 跨卷迁移时由
    闸门传目标卷的路径复探(卷相关差异: FAT32 无硬链接、UNC 目标 junction 不可用)。
    """
    root = os.path.abspath(work_dir or tempfile.gettempdir())
    process_os = _process_os()
    evidence = container_evidence()
    wsl = is_wsl()
    mount = mount_info_for_path(root)
    foreign = windows_backed_mount(root, wsl=wsl)
    foreign_fs = None if foreign is None else ("drvfs" if foreign.is_drvfs else foreign.fstype)
    host_os = _host_os(process_os, wsl, foreign)
    notes = list(evidence)
    if wsl:
        notes.append("检测到 WSL")
    if mount is not None:
        notes.append(f"探测目录所在挂载: {mount.fstype} @ {mount.mount_point}")
    if foreign is not None:
        notes.append("该挂载由 Windows 宿主提供: 本进程建出的链接宿主读不了")
    try:
        junction = probe_junction(root)
        dir_symlink = probe_symlink(root, target_is_directory=True)
        file_symlink = probe_symlink(root, target_is_directory=False)
        hardlink = probe_hardlink(root)
    except Exception as e:  # noqa: BLE001 - 探测边界: 任何异常都降级成「不可用」, 不炸启动
        logger.warning(f"alias_fs 能力探测异常, 按不可用处理: {e}")
        failed = LinkProbe(False, error=f"探测异常: {e}")
        junction = dir_symlink = file_symlink = hardlink = failed
    uac_available = _uac_available(process_os)
    if process_os == "windows" and not file_symlink.ok and "提权" in file_symlink.error:
        notes.append(f"文件级符号链接需提权, 提权通道{'可用' if uac_available else '不可用'}")
    if host_os != process_os:
        notes.append(f"宿主 OS 与进程 OS 不一致: {host_os} / {process_os}")
    notes.append(f"探测在 {root} 所在的卷上做; 目标卷不同时由闸门按目标卷复探")
    return AliasCapability(
        process_os=process_os,
        host_os=host_os,
        container=bool(evidence),
        wsl=wsl,
        path_style="windows" if process_os == "windows" else "posix",
        foreign_fs=foreign_fs,
        link_visible_to_host=_link_visible_to_host(process_os, foreign),
        junction=junction,
        dir_symlink=dir_symlink,
        file_symlink=file_symlink,
        hardlink=hardlink,
        uac_available=uac_available,
        probe_root=root,
        probed_at=SYSTEM_CLOCK.now(),  # 探测记录时间戳: 挂钟语义走取时单点(S2 时钟注入收编)
        notes=tuple(notes),
    )


_cache_lock = threading.Lock()
_cached: Optional[AliasCapability] = None


def get_capability(refresh: bool = False) -> AliasCapability:
    """进程级能力(缓存; `refresh=True` 强制重探 —— 启动一次 + 配置热重载时调这个)

    缓存的是**默认卷**(系统临时目录)上的能力; 目标卷的差异由闸门按目标路径复探。
    加锁只为防两个线程同时探测建出同名临时目录, 探测本身是毫秒级只读+建删。
    """
    global _cached
    with _cache_lock:
        if _cached is None or refresh:
            _cached = probe_capability()
        return _cached


def reset_capability_cache() -> None:
    """清缓存(单测用; 生产侧只走 `get_capability(refresh=True)`)"""
    global _cached
    with _cache_lock:
        _cached = None


# ---------------------------------------------------------------- Windows 原语(ctypes)


def _uac_available(process_os: str) -> bool:
    """提权通道是否可用: 无可见窗口站的会话(服务/SSH/计划任务)弹不出 UAC 同意框"""
    if process_os != "windows":
        return False
    try:
        return _win_interactive_session()
    except Exception as e:  # noqa: BLE001 - 拿不到就按「不可用」处理(保守默认)
        logger.debug(f"alias_fs 提权通道探测失败: {e}")
        return False


def _win_interactive_session() -> bool:
    """当前进程的窗口站是否可见(WSF_VISIBLE) —— 可见才可能弹 UAC

    !ctypes 必须绑死 argtypes/restype: 不绑时句柄按 32 位传, 高 32 位是寄存器残留,
    表现为「有概率失败且 GetLastError 为 0」(pitfalls/backend/ctypes-x64-argtypes.md)。
    """
    import ctypes
    from ctypes import wintypes

    class _UserObjectFlags(ctypes.Structure):
        """USEROBJECTFLAGS: GetUserObjectInformationW(UOI_FLAGS) 要求 12 字节, 只给 4 字节会 ERROR_INSUFFICIENT_BUFFER"""

        _fields_ = [("fInherit", wintypes.BOOL), ("fReserved", wintypes.BOOL), ("dwFlags", wintypes.DWORD)]

    u32 = ctypes.WinDLL("user32", use_last_error=True)
    get_station = u32.GetProcessWindowStation
    get_station.argtypes = []
    get_station.restype = wintypes.HANDLE
    get_info = u32.GetUserObjectInformationW
    get_info.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    get_info.restype = wintypes.BOOL
    station = get_station()
    if not station:
        return False
    flags = _UserObjectFlags()
    needed = wintypes.DWORD(0)
    if not get_info(station, 1, ctypes.byref(flags), ctypes.sizeof(flags), ctypes.byref(needed)):  # UOI_FLAGS = 1
        return False
    return bool(flags.dwFlags & 0x0001)  # WSF_VISIBLE


# FSCTL_SET_REPARSE_POINT / 打开标志 / 访问权限(避免依赖第三方库, 全部用数值常量)
_FSCTL_SET_REPARSE_POINT = 0x000900A4
_GENERIC_WRITE = 0x40000000
_OPEN_EXISTING = 3
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000


def _win_create_junction(link: str, target: str) -> None:
    """建 junction(免管理员): 空目录 + FSCTL_SET_REPARSE_POINT 挂载点重解析数据

    为什么不用 `mklink /J`: 那要起子进程(cmd.exe), 既是外部副作用, 又把 Unicode 路径
    塞进命令行 —— §3.3 明确要求 Unicode 路径不经命令行参数。这里直接进内核 API。

    失败时把刚建的空目录删掉(不留半截现场), 再抛 `OSError`(带 winerror)。
    """
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = k32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
        wintypes.HANDLE
    ]
    create_file.restype = wintypes.HANDLE
    device_io = k32.DeviceIoControl
    device_io.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
    ]
    device_io.restype = wintypes.BOOL
    close_handle = k32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    link_p = utils.add_long_path_prefix_for_win(link)
    target_abs = os.path.abspath(target)
    os.mkdir(link_p)
    try:
        # REPARSE_DATA_BUFFER: 8 字节头 + MountPointReparseBuffer(4 个 USHORT + PathBuffer)
        # 注意 mount point 的结构**没有** Flags 字段(那是 SymbolicLinkReparseBuffer 才有的),
        # 加上去会把 PathBuffer 的首 4 字节冲掉 => 内核拒绝或建出坏链接。
        substitute = ("\\??\\" + target_abs).encode("utf-16-le")
        printable = target_abs.encode("utf-16-le")
        path_buffer = substitute + b"\x00\x00" + printable + b"\x00\x00"
        data_len = 8 + len(path_buffer)
        total = 8 + data_len
        buf = ctypes.create_string_buffer(total)
        struct.pack_into("<IHH", buf, 0, IO_REPARSE_TAG_MOUNT_POINT, data_len, 0)
        struct.pack_into("<HHHH", buf, 8, 0, len(substitute), len(substitute) + 2, len(printable))
        buf[16:16 + len(path_buffer)] = path_buffer
        handle = create_file(
            link_p, _GENERIC_WRITE, 0, None, _OPEN_EXISTING,
            _FILE_FLAG_OPEN_REPARSE_POINT | _FILE_FLAG_BACKUP_SEMANTICS, None
        )
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            returned = wintypes.DWORD(0)
            ok = device_io(
                handle, _FSCTL_SET_REPARSE_POINT, ctypes.byref(buf), total, None, 0, ctypes.byref(returned), None
            )
            if not ok:
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            close_handle(handle)
    except OSError:
        try:
            os.rmdir(link_p)
        except OSError:
            pass
        raise
