"""文件访问层: 下载数据目录的全部本地文件访问单点包装(plan 26-09-27-1407)

背景(docker 兼容, 依据 reports/26-09-27-1352): 程序读的是 qB 报回的宿主保存路径
(**逻辑空间**, 如 `D:/Downloads/x`), 容器里看不见那块盘 —— 把下载数据目录挂进容器后,
用映射表(config.fs.path_map)把逻辑路径在本层内部的 **syscall 边界**译成容器挂载路径
(**容器空间**, 如 `/mnt/downloads/x`), 译回逻辑空间再返回。

两条硬约束(报告 §04/§05, 违反即复刻历史事故):
1. **逻辑路径进 → 逻辑路径出**: 映射只发生在本层内部, 所有返回值/entry 仍是逻辑空间
   —— 组 key / 回传 qB 的动作(set_location/edit_category)/ 跳检备份元数据消费的
   字符串永不经过映射, 零污染。
2. **映射 miss 一律「不可判定」, 绝不判「不存在」**: 缺文件扫描把 exists == False
   翻译成暂停整组 + MISSING 标签(真实写 qB); 映射配错时若照常返回 False 会重演
   误暂停事故 —— 故 miss 时存在性语义返回 UNDETERMINED 哨兵、取值语义抛
   FileAccessError, 让功能显式退化为报错/跳过(显式报错优于静默假值)。
3. **容器侧挂载根逃逸校验(SEC-1)**: 映射命中的容器路径经 realpath 解析后必须仍落在
   挂载根的真实路径内, 逃逸按 miss 处理 —— 下载目录内的符号链接指向挂载外时,
   存在性探测/读取/新建/目录列举一概触达不了挂载外(Local 实现的 realpath 逃逸
   防护在容器侧的等价补齐)。

包装范围口径: 只收编**下载数据目录**访问(qB save_path/content_path 派生);
派生自 data_dir 的路径(state/锁/日志/token/HR/跳检备份/配置 .bak)在容器里本就落
/data /config, 不进本层。Windows 长路径前缀(`\\\\?\\`)收编进 Local 实现单点,
调用点只交逻辑路径(原先散在 grouping/checking/fs 各处的
add_long_path_prefix_for_win 调用随之删除)。

热重载级别: fs 段为 R 级(与 data_dir 同档, 见 config/impact.py) —— 单例在
QbManager 构造时经 init_file_access 按配置构建一次, 运行期不切换。
"""
import errno
import logging
import os
import shutil
from dataclasses import dataclass
from typing import List, NamedTuple, Optional, Tuple

from . import utils

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- 哨兵与异常


class _UndeterminedType:
    """「不可判定」哨兵: 映射 miss 时存在性未知 —— 与「不存在」严格区分(报告 §05 红线)

    ❗不可作布尔值: 判定代码必须显式 `result is UNDETERMINED` 走三态分支。
    若放行隐式真值判断(falsy), `if not fa.exists(p)` 会把「不可判定」当成「不存在」
    —— 恰是本层要防的误暂停事故, 故直接抛错让写法暴露。
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "UNDETERMINED"

    def __bool__(self) -> bool:
        raise TypeError("UNDETERMINED 不可作布尔值 —— 必须显式 `is UNDETERMINED` 走三态分支")


UNDETERMINED = _UndeterminedType()


class FileAccessError(OSError):
    """包装层错误: 本次访问无法完成(典型: 映射 miss 时做取值类访问)

    继承 OSError 让既有 `except OSError` 兜底(缺文件扫描的 getsize 分支等)按
    「文件无法读取」降级, 不会以未捕获异常炸穿主循环; 取值方需要区分「不可判定」
    与真实 I/O 失败时, 先捕获本类即可。
    """


class NotSupported(RuntimeError):
    """当前 FileAccess 实现不支持该语义(容器: open_path —— 缺 xdg-open 更缺文件管理器,
    B/C 类根因与挂载无关, 显式降级优于两层根因的 404/500)"""


@dataclass(frozen=True)
class DirEntry:
    """scandir 条目(逻辑空间): name + 逻辑路径 + 目录判定(scandir 时一次性判定)"""

    name: str
    path: str  # 逻辑空间路径(与父目录入参同空间)
    is_dir: bool


class DiskUsage(NamedTuple):
    """磁盘用量(与 shutil.disk_usage 的字段同形)"""

    total: int
    used: int
    free: int


# ---------------------------------------------------------------- 路径归一


def _strip_win_prefix(p: str) -> str:
    """剥掉 Windows 扩展长度前缀 `\\\\?\\`(`\\\\?\\UNC\\` 还原成 `\\\\`), 其余原样返回

    前缀让同一路径有两种写法, 而比较与映射只认一种(语义与 webui/server/routes/fs.py
    的 _bare 一致 —— 该处保留同名薄委托, 供既有测试钉住)。path_normalize 更危险:
    它先折叠 `\\` ⇒ `\\\\?\\H:\\a` 会折坏成 `/?/H:/a`, 所以必须**先剥再规范化**。
    """
    if p.startswith("\\\\?\\UNC\\"):
        return "\\\\" + p[8:]
    return p[4:] if p.startswith("\\\\?\\") else p


def _norm_logical(p: str) -> str:
    """逻辑路径归一: 剥前缀 + 折叠分隔符(`\\`→`/`)+ 压缩重复斜杠(映射匹配的统一口径)"""
    return utils.path_normalize(_strip_win_prefix(p))


def _fold_prefix_len(lp: str, folded_prefix: str) -> int:
    """原串 lp 中折叠后恰等于 folded_prefix 的前缀的**码点长度**; 不命中返回 -1

    casefold 是逐码点映射却可能变长(ß→ss、İ→i̇), 折叠串与原串长度不对齐 —— 拿折叠
    前缀的长度硬切原串会切错位(容器路径丢字符 → exists 误判「不存在」→ 重演误暂停
    事故, 报告 §05 红线)。故沿原串逐码点累加折叠定位边界: 累加折叠长度严格单调递增,
    与目标等值至多命中一次; 累加结果不再是目标前缀时提前退出(后续只会更长)。
    """
    acc = ""
    for i, ch in enumerate(lp):
        acc += ch.casefold()
        if acc == folded_prefix:
            return i + 1
        if not folded_prefix.startswith(acc):
            return -1
    return -1


# ---------------------------------------------------------------- 抽象基座


class FileAccess:
    """文件访问抽象: 全部方法 **逻辑路径进 → 逻辑路径出**

    存在性语义(exists/isdir/isfile)可能返回 UNDETERMINED; 取值语义(getsize/
    disk_usage/scandir/mkdir)失败抛 FileAccessError(子类可另有 NotSupported)。
    """
    def exists(self, path: str) -> bool:
        raise NotImplementedError

    def isdir(self, path: str) -> bool:
        raise NotImplementedError

    def isfile(self, path: str) -> bool:
        raise NotImplementedError

    def getsize(self, path: str) -> int:
        """文件大小(字节); 不存在/不可判定抛 FileAccessError"""
        raise NotImplementedError

    def disk_usage(self, path: str) -> DiskUsage:
        """路径所在盘的 (total, used, free); 不可用/不可判定抛 FileAccessError"""
        raise NotImplementedError

    def scandir(self, path: str) -> List[DirEntry]:
        """列目录(仅一层, 不读文件内容); entry.path 已译回逻辑空间"""
        raise NotImplementedError

    def mkdir(self, path: str) -> None:
        """新建单层目录(全项目对下载目录唯一的本地写, 语义见 MappedFileAccess)"""
        raise NotImplementedError

    def realpath_lexical(self, path: str) -> str:
        """规范化到可比较的绝对形式(白名单/父目录比较用; 见各实现的能力差异说明)"""
        raise NotImplementedError

    def open_path(self, path: str, select: bool = False) -> None:
        """用系统默认方式打开文件/目录(容器实现显式不支持, 见 NotSupported)"""
        raise NotImplementedError


class LocalFileAccess(FileAccess):
    """宿主直跑实现: 直通 syscall + Windows 长路径前缀单点收编(行为与收编前等价)

    realpath_lexical = normcase + realpath: 路径真实存在时可解析符号链接(目录浏览的
    逃逸防护依赖它); >MAX_PATH 路径 realpath 静默退化 abspath —— 既有已知限制, 口径不变。
    Local 永远不产生 UNDETERMINED(三态只属于映射 miss)。
    """
    def _pref(self, path: str) -> str:
        """本地 syscall 用路径: 剥前缀(幂等)后统一加 Windows 长路径前缀(非 Windows 空操作)"""
        return utils.add_long_path_prefix_for_win(_strip_win_prefix(path))

    def exists(self, path: str) -> bool:
        return os.path.exists(self._pref(path))

    def isdir(self, path: str) -> bool:
        return os.path.isdir(self._pref(path))

    def isfile(self, path: str) -> bool:
        return os.path.isfile(self._pref(path))

    def getsize(self, path: str) -> int:
        return os.path.getsize(self._pref(path))

    def disk_usage(self, path: str) -> DiskUsage:
        return shutil.disk_usage(self._pref(path))

    def scandir(self, path: str) -> List[DirEntry]:
        lp = _norm_logical(path)
        with os.scandir(self._pref(lp)) as it:
            return [DirEntry(name=e.name, path=f"{lp}/{e.name}", is_dir=e.is_dir()) for e in it]

    def mkdir(self, path: str) -> None:
        os.mkdir(self._pref(path))

    def realpath_lexical(self, path: str) -> str:
        return os.path.normcase(os.path.realpath(_strip_win_prefix(path)))

    def open_path(self, path: str, select: bool = False) -> None:
        utils.open_path(path, select=select)  # 前缀语义由 utils 内部分支自理


class MappedFileAccess(FileAccess):
    """容器实现: 按映射表把逻辑路径译成容器挂载路径再做 syscall

    - 匹配口径: 入参先 _norm_logical(折叠分隔符 + 剥前缀), 源前缀 casefold 比较,
      强制 `/` 边界(`D:/Downloads` 不得命中 `D:/Downloads2`), 尾斜杠归一后匹配;
    - miss: 存在性 → UNDETERMINED; 取值 → FileAccessError —— 绝不返回「不存在」;
    - 逃逸加固(SEC-1): 命中映射的容器路径经容器侧 realpath 解析后必须仍落在挂载根的
      真实路径内(下载目录内的符号链接指向挂载外 → 按 miss 处理) —— Local 的
      realpath 逃逸防护在容器侧等价补齐, fs.py 目录浏览不再「词法退化」;
    - mkdir: **真实执行**(挂载点可写即成功); 只读挂载由 OS 的 EROFS/EACCES 冒泡,
      调用方语义化拒绝; miss 抛 FileAccessError;
    - open_path: NotSupported(恒) —— 容器缺 xdg-open 更缺文件管理器, 与挂载无关;
    - realpath_lexical: 纯词法(normcase + normpath) —— 逻辑路径在容器里不真实存在,
      realpath 只会把它拼坏; 逻辑空间白名单比较保持词法, 符号链接逃逸防护由本层的
      挂载根校验承担(见上)。
    """
    def __init__(self, path_map: Tuple):
        # entries 保留原始声明(自检/展示用); _table 为匹配用折叠表(源/目标都去尾斜杠 + casefold)
        self.entries: Tuple = tuple(path_map)
        self._table: List[Tuple[str, str]] = [
            (_norm_logical(e.src).rstrip("/").casefold(), _norm_logical(e.dst).rstrip("/")) for e in self.entries
        ]
        # 挂载根真实路径缓存(dst → realpath+normcase): 映射/挂载根 R 级运行期不切换(与
        # 单例同生命周期), 根解析结果稳定可缓存; 惰性填充, 首次访问才做 syscall
        self._root_real = {}

    def _root_contained(self, dst: str, cp: str) -> bool:
        """容器路径 cp 经 realpath 解析后是否仍落在挂载根 dst 的真实路径内(SEC-1 判定单点)

        根与目标**都**取 realpath: 挂载根本身经符号链接到达(如 /mnt/downloads → /srv/data)
        时按解析后的共同基准比较, 不会误伤; 下载目录内的符号链接指到挂载外时解析结果跳出
        根前缀 → False(逃逸)。normcase 使 Windows 宿主测试的大小写差异不误判(POSIX 恒等)。
        """
        root = self._root_real.get(dst)
        if root is None:
            root = os.path.normcase(os.path.realpath(dst))
            self._root_real[dst] = root
        rp = os.path.normcase(os.path.realpath(cp))
        if rp == root:
            return True
        prefix = root if root.endswith(os.sep) else root + os.sep
        return rp.startswith(prefix)

    def _match(self, path: str) -> Optional[Tuple[str, str]]:
        """映射匹配核心: 返回 (挂载根, 容器路径); **None = miss(含逃逸)** —— fail-safe 判定点

        匹配在 casefold 空间进行, 边界定位回原串: 前缀余量必须按**原串**码点切割
        (casefold 可能变长, 折叠长度 ≠ 原串长度, 见 _fold_prefix_len)。命中后过挂载根
        逃逸校验, 逃逸与未命中同样返回 None —— 调用方据此统一走三态。
        """
        lp = _norm_logical(path)
        for src_folded, dst in self._table:
            n = _fold_prefix_len(lp, src_folded)
            if n < 0:
                continue
            if n == len(lp):
                return dst, dst  # 根本身命中(目录浏览首屏允许根 = save_path 本身), 恒在根内
            if lp[n] == "/":  # `/` 边界(D:/Downloads 不得命中 D:/Downloads2)
                cp = dst + lp[n:]
                if not self._root_contained(dst, cp):
                    logger.debug(f"fs.path_map 逃逸拦截 | '{path}' -> '{cp}' 经 realpath 解析落在挂载根 '{dst}' 之外, 按 miss 处理")
                    return None
                return dst, cp
        return None

    def map_to_container(self, path: str) -> Optional[str]:
        """逻辑路径 → 容器路径; **None = miss 或逃逸**(fail-safe 判定点, 调用方据此走三态)

        匹配见 _match; 逃逸(映射命中但容器侧 realpath 跳出挂载根)与未命中同判 None。
        """
        m = self._match(path)
        return None if m is None else m[1]

    def _require_mapped(self, path: str) -> str:
        cp = self.map_to_container(path)
        if cp is None:
            raise FileAccessError(f"路径不可判定(未命中 fs.path_map 映射): '{path}'")
        return cp

    def exists(self, path: str) -> bool:
        cp = self.map_to_container(path)
        return UNDETERMINED if cp is None else os.path.exists(cp)

    def isdir(self, path: str) -> bool:
        cp = self.map_to_container(path)
        return UNDETERMINED if cp is None else os.path.isdir(cp)

    def isfile(self, path: str) -> bool:
        cp = self.map_to_container(path)
        return UNDETERMINED if cp is None else os.path.isfile(cp)

    def getsize(self, path: str) -> int:
        return os.path.getsize(self._require_mapped(path))

    def disk_usage(self, path: str) -> DiskUsage:
        return shutil.disk_usage(self._require_mapped(path))

    def scandir(self, path: str) -> List[DirEntry]:
        """列目录(仅一层, 不读文件内容); entry.path 已译回逻辑空间

        逃逸条目(容器内符号链接解析后跳出挂载根)**剔除**而非报错: 一个坏链接不该让
        整个目录浏览 404, 而挂载外的目标也不该出现在列表里(与 exists/取值的逃逸=miss
        口径一致, fs.py 逐条白名单因此无需自行做容器侧 realpath)。
        """
        lp = _norm_logical(path)
        m = self._match(lp)
        if m is None:
            raise FileAccessError(f"路径不可判定(未命中 fs.path_map 映射): '{path}'")
        dst, cp = m
        out: List[DirEntry] = []
        with os.scandir(cp) as it:
            for e in it:
                ecp = f"{cp}/{e.name}"
                if not self._root_contained(dst, ecp):
                    logger.debug(f"fs.path_map 逃逸剔除 | '{lp}/{e.name}' -> '{ecp}' 落在挂载根 '{dst}' 之外, 不进目录列表")
                    continue
                out.append(DirEntry(name=e.name, path=f"{lp}/{e.name}", is_dir=e.is_dir()))
        return out

    def mkdir(self, path: str) -> None:
        os.mkdir(self._require_mapped(path))

    def realpath_lexical(self, path: str) -> str:
        return os.path.normcase(os.path.normpath(_norm_logical(path)))

    def open_path(self, path: str, select: bool = False) -> None:
        raise NotSupported("容器环境不支持打开文件夹(无桌面会话与文件管理器), 请使用「复制路径」")


# ---------------------------------------------------------------- 单例

_instance: FileAccess = LocalFileAccess()  # 默认直跑实现(init_file_access 之前/未配置映射时)


def init_file_access(config) -> FileAccess:
    """按配置构建单例(QbManager 构造时调用一次; fs 段 R 级热重载, 运行期不切换)"""
    global _instance
    mapping = getattr(getattr(config, "fs", None), "path_map", ()) or ()
    _instance = MappedFileAccess(mapping) if mapping else LocalFileAccess()
    return _instance


def get_file_access() -> FileAccess:
    """当前文件访问实现(调用点只认本入口, 不感知 Local/Mapped 差异)"""
    return _instance


# ---------------------------------------------------------------- 启动自检


def path_map_selfcheck(save_paths: List[str]) -> None:
    """映射自检(非 fail-fast, 只记日志不阻塞启动): 结果是预告, 运行期以真实 syscall 为准

    ① 每条挂载点(to)在容器内 isdir 存在 —— 不存在提示查 compose volumes;
    ② 现存种子 save_path 对映射源前缀命中率 0% —— 提示映射表可能写错(盘符/大小写/分隔符);
    ③ 每条挂载点做可写探测(建删临时目录), 只读结果记 INFO(「新建文件夹」需 :rw 挂载)。
    """
    fa = get_file_access()
    if not isinstance(fa, MappedFileAccess) or not fa._table:
        return
    mounts = sorted({dst for _src, dst in fa._table})
    for dst in mounts:
        if not os.path.isdir(dst):
            logger.warning(f"fs.path_map 自检 | 挂载点不存在: '{dst}' —— 检查 compose volumes 是否漏挂或路径写错")
            continue
        try:
            probe = os.path.join(dst, ".auto-qb-write-probe")
            os.mkdir(probe)
            os.rmdir(probe)
        except OSError as e:
            if e.errno in (errno.EACCES, errno.EPERM, errno.EROFS):
                logger.info(f"fs.path_map 自检 | 挂载点只读: '{dst}' —— 新建文件夹(mkdir)将不可用, 需要 :rw 挂载")
            else:
                logger.info(f"fs.path_map 自检 | 挂载点可写探测失败: '{dst}': {e} —— 运行期以真实 syscall 结果为准")
    paths = [p for p in save_paths if p]
    if paths and all(fa.map_to_container(p) is None for p in paths):
        logger.warning("fs.path_map 自检 | 现存种子的 save_path 无一命中映射源前缀 —— 映射表可能写错(检查盘符/大小写/分隔符/尾斜杠)")
