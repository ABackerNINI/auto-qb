"""BT_backup 自动探测后端(计划 26-11-11-0259 S3): 候选推导 / 资格判定 / hash 自证 / 五态裁决

纯函数模块, 供设置页「自动探测」按钮的端点(routes 层, S4)包装 —— 按钮显式触发是唯一入口
(D3 读法2), 运行面零隐式探测(G4)。四步组合口径:

    scan = candidates(platform)                            # §2.3 矩阵推导候选
    quals = [qualify(c.path) for c in scan.candidates]     # ^40hex\\.fastresume$ 或 queue 才合格
    matches = verify(torrent_id_set(pairs), quals)         # TorrentID 交集(v1 与 v2 截断双算, R2)
    result = verdict(scan, qualifications=quals, matches=matches,
                      manual_set=..., storage_type=..., online=...)   # §3.2 五态

硬约束:
- 零网络零 qB 客户端依赖: qB 事实(infohashes / resume_data_storage_type / 在线与否)由调用方以
  原语传入; 本模块不读 config 层、不起 qB 会话(黄金法则 5 单一写线程不受影响)。
- 只读探测: 零写盘零 state 零缓存(黄金法则 1/3/5), 每次调用现算。
- 拒不猜测(D5): 歧义/未命中/离线一律不猜不写, 只产证据(ProbeResult / CandidateReport 供端点序列化)。
- 判定顺序短路(§3.2): unusable-sqlite 先于 manual-set —— 已手动配置但存储后端非 Legacy 仍须示警
  「不可用」, 不被「仅供核对」吞掉。
- 不抛栈(R5): exe 定位失败 / 目录不可读 / 平台不支持一律降级为证据行; PowerShell 子进程钉
  UTF-8 + 超时守护(R6, issue 26-11-07-1216 口径: encoding/errors 两项必填), 命令串为编译期
  常量, 不拼接任何调用方输入(无注入面)。

候选推导依据(qB/libtorrent 源码取证, 计划 §2.2/§2.3): BT_backup 构造唯一(sessionimpl.cpp:1476,
无任何 ini 键可改道, WebAPI 无路径端点); Data 目录解析 profile_p.cpp:87-109 —— Windows =
%LOCALAPPDATA%\\qBittorrent[_<name>](无 data 中间层), Linux = $XDG_DATA_HOME|~/.local/share 且
≤4.2.x 带 .../data/ legacy 回退, macOS = ~/Library/Application Support; 便携 = <exeDir>/profile/
qBittorrent[_<name>]/data/BT_backup(application.cpp:333 须 exe 旁 profile/ 存在); --configuration
后缀经配置目录 qBittorrent* 枚举佐证, 新旧并存全部列为候选、歧义交 hash 自证消歧(R4); --profile
与 QBT_PROFILE 自定义 profile 及远程 qB(跨机)不可静态探测 → 不产生候选, 手动键兜底。

fastresume 文件命名与 TorrentID(bencoderesumedatastorage.cpp + infohash.cpp get_best()):
文件名 = ^40hex\\.fastresume$(伴生 <id>.torrent); <id> 4.5.0 起 = hybrid/v2 取 sha256 截断前
20 字节(= infohash_v2 前 40 hex), 否则 v1 sha1; 4.4.x hybrid 用 v1 命名 —— 自证集合按
{v1, v2trunc} 双算两种命名世代一并命中(见 torrent_ids_from_infohashes)。queue 文件(每行一个
40hex)是强结构标记, 单独构成资格。ResumeDataStorageType=SQLite 时 torrents.db 在 Data 根,
BT_backup 只剩迁移残留 → fastresume 改写无效(R1), verdict = unusable-sqlite。

依赖纪律: infra 只被依赖 —— 本模块只 import 标准库与 .utils(host_platform 平台判定走 utils.is_* 单点)。
"""
from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .utils import is_linux, is_mac, is_windows

# ---- 平台与来源常量(platform 实参取值; 测试按常量合成三平台场景) ----
PLATFORM_WINDOWS = "windows"
PLATFORM_LINUX = "linux"
PLATFORM_MAC = "mac"

ORIGIN_DEFAULT = "default-profile"
ORIGIN_PORTABLE = "portable"

# ---- verdict 五态(§3.2; 判定顺序: unusable-sqlite > manual-set > 命中裁决) ----
VERDICT_HIT = "hit"
VERDICT_AMBIGUOUS = "ambiguous"
VERDICT_MISS = "miss"
VERDICT_UNUSABLE_SQLITE = "unusable-sqlite"
VERDICT_MANUAL_SET = "manual-set"

#: 便携 exe 定位的 Windows 一次性 CIM 查询硬超时(启动开销大, 参照 port_owner 给富余)
WIN_EXE_TIMEOUT_S = 3.0
#: POSIX 便携 exe 定位的 /proc 根(模块常量: 测试可注入)
PROC_DIR = "/proc"

#: fastresume 文件名(qB 只写小写 hex, 判定放宽大小写后归一); \\Z 而非 $ 防尾部换行的怪名误配
FASTRESUME_RE = re.compile(r"^([0-9a-fA-F]{40})\.fastresume\Z")
#: 强结构标记文件(qB 每行一个 40hex 的队列账本)
QUEUE_FILENAME = "queue"

#: Windows/Linux 配置目录条目 -> configuration 后缀("qBittorrent" -> "", "qBittorrent_x" -> "_x")
QB_DIR_RE = re.compile(r"^qBittorrent(_.+)?\Z")
#: macOS 配置形态是 ~/Library/Preferences/qBittorrent[_<name>].ini 文件
QB_INI_RE = re.compile(r"^qBittorrent(_.+)?\.ini\Z")

#: TorrentID 合法形态: v1 sha1 全 40 hex / v2 sha256 全 64 hex(截断前校验)
HEX40_RE = re.compile(r"^[0-9a-fA-F]{40}\Z")
HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}\Z")

#: resume_data_storage_type 原语口径(对齐 relocate_plan.is_legacy_resume_storage):
#: qB 4.6+ WebAPI 返回整数 0 = Legacy 文件 / 1 = SQLite; 容错接受字符串字样;
#: 空/None = SQLite 选项出现之前的 qB(只有文件后端), 按 Legacy 处理。
_SQLITE_TOKENS = ("1", "sqlite")
_LEGACY_TOKENS = ("0", "legacy", "")

_REASON_SQLITE = ("qB resume 数据存储为 SQLite: BT_backup 非主存储, fastresume 改写无效, 探测结果不可用"
                  "(需在 qB 设置改回 Legacy 文件后端)")
_REASON_MANUAL_SET = "relocate.bt_backup 已手动配置(显式 > 推断): 探测仅供核对, 配置一字不改(D5)"
_COVERAGE_NOTE = (
    "探测覆盖面 = 默认 profile / --configuration 后缀 / 便携(exe 旁 profile/): --profile 与 "
    "QBT_PROFILE 自定义 profile 及远程 qB(跨机)不可静态探测, 未产生候选, 手动键兜底"
)


def host_platform() -> str:
    """宿主平台常量(candidates 的 platform 实参生产取值); 未知平台返回空串(候选推导降级)。"""
    if is_windows():
        return PLATFORM_WINDOWS
    if is_linux():
        return PLATFORM_LINUX
    if is_mac():
        return PLATFORM_MAC
    return ""


# ---- 证据结构体(全部 frozen dataclass, 端点 asdict 后直接序列化) ----


@dataclass(frozen=True, slots=True)
class Candidate:
    """一个 BT_backup 候选目录 + 推导依据"""

    path: str
    origin: str
    suffix: str
    note: str = ""


@dataclass(frozen=True, slots=True)
class CandidateScan:
    """candidates() 结果: 候选集 + 证据行(后缀枚举来源 / 定位失败 / 覆盖面说明)"""

    candidates: tuple[Candidate, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Qualification:
    """qualify() 结果: 单候选资格判定(资格依据 / 不资格原因都在 reason 里)"""

    path: str
    qualified: bool
    reason: str
    fastresume_ids: frozenset[str]
    has_queue: bool


@dataclass(frozen=True, slots=True)
class HashMatch:
    """verify() 结果: 单候选与 TorrentID 集合的交集"""

    path: str
    matched_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class CandidateReport:
    """逐候选证据(候选路径 / 资格依据 / hash 交集, 按路径把三步记录联接后的形态)"""

    path: str
    origin: str
    suffix: str
    qualified: bool
    qualification_reason: str
    fastresume_count: int
    has_queue: bool
    hash_matched: bool
    matched_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """五态裁决 + 全量证据(供端点序列化; 配置一字不改由调用方保证, 本模块零写盘)"""

    state: str
    reason: str
    candidates: tuple[CandidateReport, ...]
    notes: tuple[str, ...]


# ---- 候选推导(candidates) ----


def candidates(
    platform: str,
    *,
    env: Mapping[str, str] | None = None,
    home: str | Path | None = None,
    exe_locator: Callable[[], tuple[tuple[str, ...], tuple[str, ...]]] | None = None,
) -> CandidateScan:
    """按 §2.3 可探测性矩阵推导 BT_backup 候选目录; 永不抛栈, 失败降级为证据行。

    platform 显式注入(生产传 host_platform(), 测试合成三平台场景); env / home / exe_locator
    同为注入面(默认 os.environ / Path.home() / 按平台选真实定位器)。只读: 扫配置目录枚举
    configuration 后缀(qBittorrent*, 新旧并存全部列为候选, 歧义交 hash 自证消歧), 便携候选
    须 exe 旁 profile/ 存在(application.cpp:333 的便携触发条件)。--profile 与 QBT_PROFILE
    自定义及远程 qB 不产生候选, 只留覆盖面证据行(手动键兜底)。
    """
    env_map: Mapping[str, str] = os.environ if env is None else env
    home_dir = Path.home() if home is None else Path(home)
    evidence: list[str] = []
    cands: list[Candidate] = []

    if platform == PLATFORM_WINDOWS:
        data_root = _env_path(env_map, "LOCALAPPDATA", home_dir / "AppData" / "Local")
        config_root = _env_path(env_map, "APPDATA", home_dir / "AppData" / "Roaming")
        suffixes, note = _scan_suffixes(config_root, QB_DIR_RE, want_dir=True)
        evidence.append(note)
        cands.extend(
            Candidate(
                str(data_root / f"qBittorrent{s}" / "BT_backup"),
                ORIGIN_DEFAULT,
                s,
                "Windows 默认 profile(Qt AppLocalDataLocation, 无 data 中间层)",
            ) for s in _ordered_suffixes(suffixes)
        )
    elif platform == PLATFORM_LINUX:
        data_root = _env_path(env_map, "XDG_DATA_HOME", home_dir / ".local" / "share")
        config_root = _env_path(env_map, "XDG_CONFIG_HOME", home_dir / ".config")
        suffixes, note = _scan_suffixes(config_root, QB_DIR_RE, want_dir=True)
        evidence.append(note)
        for s in _ordered_suffixes(suffixes):
            cands.append(
                Candidate(
                    str(data_root / f"qBittorrent{s}" / "BT_backup"),
                    ORIGIN_DEFAULT,
                    s,
                    "Linux 默认 profile(4.3.0+ 布局)",
                )
            )
            cands.append(
                Candidate(
                    str(data_root / "data" / f"qBittorrent{s}" / "BT_backup"),
                    ORIGIN_DEFAULT,
                    s,
                    "Linux legacy 布局(4.2.x 及更早: data/ 中间层)",
                )
            )
    elif platform == PLATFORM_MAC:
        data_root = home_dir / "Library" / "Application Support"
        config_root = home_dir / "Library" / "Preferences"
        suffixes, note = _scan_suffixes(config_root, QB_INI_RE, want_dir=False)
        evidence.append(note)
        cands.extend(
            Candidate(
                str(data_root / f"qBittorrent{s}" / "BT_backup"),
                ORIGIN_DEFAULT,
                s,
                "macOS 默认 profile(~/Library/Application Support)",
            ) for s in _ordered_suffixes(suffixes)
        )
    else:
        evidence.append(f"不支持的平台({platform!r}): 未产生候选")

    locator = exe_locator if exe_locator is not None else _DEFAULT_EXE_LOCATORS.get(platform)
    if locator is not None:
        cands.extend(_portable_candidates(locator, evidence))

    return CandidateScan(_dedupe(cands), tuple(evidence) + (_COVERAGE_NOTE, ))


def _env_path(env: Mapping[str, str], key: str, fallback: Path) -> Path:
    """环境变量目录取值; 缺失/空白回退到 home 派生路径(不猜更深的形态)。

    判空与转 Path 用同一 strip 归一值: 非空但带首尾空白的值(如 "C:\\bt ")原样转 Path 会让
    qualify 恒判「目录不存在」造成误 miss —— 归一后进候选。
    """
    raw = env.get(key, "").strip()
    return Path(raw) if raw else fallback


def _scan_suffixes(root: Path, pattern: re.Pattern[str], *, want_dir: bool) -> tuple[frozenset[str], str]:
    """扫配置目录派生 configuration 后缀集合; 恒含默认 "" 后缀, 失败降级 + 证据行。"""
    try:
        entries = list(os.scandir(root))
    except OSError as exc:
        return frozenset({""}), f"配置目录不可扫({root}): {exc}; 后缀枚举降级为仅默认实例"
    suffixes = {""}
    for entry in entries:
        try:
            if not (entry.is_dir() if want_dir else entry.is_file()):
                continue
        except OSError:
            continue
        m = pattern.match(entry.name)
        if m:
            suffixes.add(m.group(1) or "")
    extra = sorted(s for s in suffixes if s)
    if extra:
        return frozenset(suffixes), f"configuration 后缀枚举: {', '.join(extra)}(配置目录: {root})"
    return frozenset({""}), f"配置目录仅默认实例(无 _<name> 后缀): {root}"


def _ordered_suffixes(suffixes: Iterable[str]) -> tuple[str, ...]:
    """确定性排序: 默认 "" 后缀最先, 其余按字典序(候选顺序稳定, 便于测试与展示)。"""
    return tuple(sorted(suffixes, key=lambda s: (s != "", s)))


def _portable_candidates(
    locator: Callable[[], tuple[tuple[str, ...], tuple[str, ...]]],
    evidence: list[str],
) -> list[Candidate]:
    """便携候选: exe 旁 profile/ 存在才推导(application.cpp:333 口径), 后缀在便携配置目录枚举。

    locator 返回 (exe 所在目录集, 证据行集); 定位失败/无进程都是证据行, 不影响默认 profile 候选。
    """
    exe_dirs, loc_evidence = locator()
    evidence.extend(loc_evidence)
    out: list[Candidate] = []
    for exe_dir in exe_dirs:
        profile_root = Path(exe_dir) / "profile"
        if not profile_root.is_dir():
            evidence.append(f"便携 exe {exe_dir} 无 profile/ 目录(非便携安装), 未产生便携候选")
            continue
        suffixes, note = _scan_suffixes(profile_root, QB_DIR_RE, want_dir=True)
        evidence.append(note)
        out.extend(
            Candidate(
                str(profile_root / f"qBittorrent{s}" / "data" / "BT_backup"),
                ORIGIN_PORTABLE,
                s,
                f"便携 profile(exe: {exe_dir})",
            ) for s in _ordered_suffixes(suffixes)
        )
    return out


def _dedupe(cands: list[Candidate]) -> tuple[Candidate, ...]:
    """按路径字符串去重保序(同 exe 多进程 / 双布局撞路径时不产重复候选)。"""
    seen: dict[str, Candidate] = {}
    for c in cands:
        seen.setdefault(c.path, c)
    return tuple(seen.values())


# ---- 便携 exe 定位(真实实现; 测试经 exe_locator 注入替身, 不触这两条) ----

#: Windows 一次性 CIM 查询: 编译期常量, 按进程名过滤(WQL LIKE 大小写不敏感, 覆盖增强版分支),
#: 不拼接任何调用方输入 -> 无注入面。走 PowerShell CIM 而非 wmic(R5: wmic 已从新版 Win11 移除)。
_WIN_EXE_SCRIPT = (
    "try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }; "
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "Get-CimInstance Win32_Process -Filter \"Name LIKE 'qbittorrent%'\" | "
    "ForEach-Object { $_.ExecutablePath }"
)

#: 平台 -> 真实 exe 定位器(便携候选默认注入点; mac 无 /proc, 天然降级为证据行)
_DEFAULT_EXE_LOCATORS: dict[str, Callable[[], tuple[tuple[str, ...], tuple[str, ...]]]] = {
    PLATFORM_WINDOWS: lambda: _win_portable_dirs(),
    PLATFORM_LINUX: lambda: _posix_portable_dirs(),
    PLATFORM_MAC: lambda: _posix_portable_dirs(),
}


def _run_powershell_exe_query() -> tuple[tuple[str, ...], str]:
    """单次 PowerShell CIM 查询 qBittorrent 进程 exe 路径; 返回 (路径集, 失败原因)。永不抛出。

    R6 口径(issue 26-11-07-1216): 文本子进程 encoding="utf-8" + errors="replace" 两项必填
    (英文 runner cp1252 打死读线程的前科), timeout 超时守护由 subprocess.run 杀子进程。
    """
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _WIN_EXE_SCRIPT],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=WIN_EXE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return (), f"PowerShell CIM 查询超时(>{WIN_EXE_TIMEOUT_S:g}s)"
    except OSError as exc:
        return (), f"PowerShell 不可用: {exc}"
    if proc.returncode != 0:
        first = (proc.stderr or proc.stdout or "").strip().splitlines()
        detail = f": {first[0].strip()[:200]}" if first else ""
        return (), f"PowerShell 退出码 {proc.returncode}{detail}"
    paths = tuple(sorted({line.strip() for line in (proc.stdout or "").splitlines() if line.strip()}))
    return paths, ""


def _win_portable_dirs() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Windows 便携 exe 定位: CIM 进程名枚举 -> exe 所在目录集 + 证据行。"""
    exes, err = _run_powershell_exe_query()
    if err:
        return (), (f"便携 exe 定位失败: {err}(降级: 便携候选不参与, 手动键兜底)", )
    if not exes:
        return (), ("未发现运行中的 qBittorrent 进程, 便携候选不适用", )
    dirs: set[str] = set()
    notes: list[str] = []
    for exe in exes:
        p = Path(exe)
        if not p.is_absolute():
            notes.append(f"便携 exe 定位收到非绝对路径({exe}), 跳过")
            continue
        dirs.add(str(p.parent))
        notes.append(f"便携 qBittorrent 进程 exe: {exe}")
    return tuple(sorted(dirs)), tuple(notes)


def _posix_portable_dirs() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """POSIX 便携 exe 定位: /proc/<pid>/exe readlink 扫描(无 psutil 依赖), 永不抛出。

    readlink 需同 uid 或 root; 权限不足/进程已退出逐条静默跳过(逐条记证据噪音过大)。
    """
    try:
        pids = [name for name in os.listdir(PROC_DIR) if name.isdigit()]
    except OSError as exc:
        return (), (f"/proc 枚举失败: {exc}(降级: 便携候选不参与, 手动键兜底)", )
    exes: set[str] = set()
    for pid in pids:
        try:
            target = os.readlink(f"{PROC_DIR}/{pid}/exe")
        except OSError:
            continue
        if os.path.basename(target).lower().startswith("qbittorrent"):
            exes.add(target)
    if not exes:
        return (), ("未发现运行中的 qBittorrent 进程(/proc exe 扫描), 便携候选不适用", )
    ordered = tuple(sorted(exes))
    return tuple(os.path.dirname(e) for e in ordered), tuple(f"便携 qBittorrent 进程 exe: {e}" for e in ordered)


# ---- 资格判定(qualify) ----


def qualify(directory: str | Path) -> Qualification:
    """候选目录资格判定(§3.2): 含 ^40hex\\.fastresume$ 文件或 queue 文件才算合格, 空目录不资格。

    只读 scandir 零写入; 目录不存在/不可读 = 不资格 + 原因(证据行), 永不抛栈。40hex 大小写
    不敏感, 归一为小写参与后续 hash 交集。
    """
    d = Path(directory)
    path_str = str(d)
    if not d.is_dir():
        return Qualification(path_str, False, "目录不存在", frozenset(), False)
    try:
        entries = list(os.scandir(d))
    except OSError as exc:
        return Qualification(path_str, False, f"目录不可读: {exc}", frozenset(), False)
    ids: set[str] = set()
    has_queue = False
    for entry in entries:
        try:
            if not entry.is_file():
                continue
        except OSError:
            continue
        if entry.name == QUEUE_FILENAME:
            has_queue = True
            continue
        m = FASTRESUME_RE.match(entry.name)
        if m:
            ids.add(m.group(1).lower())
    if ids or has_queue:
        parts = []
        if ids:
            parts.append(f"fastresume x{len(ids)}")
        if has_queue:
            parts.append("queue")
        return Qualification(path_str, True, " + ".join(parts), frozenset(ids), has_queue)
    return Qualification(path_str, False, "无 .fastresume 与 queue 文件(空目录或非 BT_backup 形态)", frozenset(), False)


# ---- hash 自证(verify) ----


def torrent_ids_from_infohashes(infohash_v1: str = "", infohash_v2: str = "") -> frozenset[str]:
    """单种子 -> TorrentID 候选集(get_best() 双算, R2 兜 4.4.x hybrid 命名差异)。

    qB 4.5.0 起 fastresume 按 libtorrent get_best() 命名: hybrid/v2 取 infohash_v2(sha256)
    截断前 20 字节 = 前 40 hex; 4.4.x hybrid 与 v1-only 用 v1(sha1) 命名。双算 {v1, v2trunc}
    两种命名世代一并命中。空/畸形输入跳过不猜。
    """
    out: set[str] = set()
    v1 = (infohash_v1 or "").strip().lower()
    if HEX40_RE.match(v1):
        out.add(v1)
    v2 = (infohash_v2 or "").strip().lower()
    if HEX64_RE.match(v2):
        out.add(v2[:40])
    return frozenset(out)


def torrent_id_set(pairs: Iterable[tuple[str, str]]) -> frozenset[str]:
    """/torrents/info 的 (infohash_v1, infohash_v2) 对序列 -> TorrentID 全集(verify 的输入)。"""
    out: set[str] = set()
    for v1, v2 in pairs:
        out |= torrent_ids_from_infohashes(v1, v2)
    return frozenset(out)


def verify(torrent_ids: Iterable[str], qualifications: Iterable[Qualification]) -> tuple[HashMatch, ...]:
    """hash 自证(§3.2): TorrentID 集合与各候选 ^40hex\\.fastresume$ 文件名求交。

    torrent_ids 由调用方按 torrent_id_set() 双算规则得出; 纯集合运算, 零 FS 零网络。
    """
    ids = {t.strip().lower() for t in torrent_ids if t and t.strip()}
    return tuple(HashMatch(q.path, frozenset(q.fastresume_ids & ids)) for q in qualifications)


# ---- 五态裁决(verdict) ----


def verdict(
    scan: CandidateScan,
    *,
    qualifications: Sequence[Qualification] = (),
    matches: Sequence[HashMatch] = (),
    manual_set: bool = False,
    storage_type: object = "",
    online: bool = False,
) -> ProbeResult:
    """五态裁决(§3.2), 判定顺序短路: unusable-sqlite -> manual-set -> 命中裁决(hit/ambiguous/miss)。

    qB 事实由调用方以原语传入: manual_set = relocate.bt_backup 非空(strip 后); storage_type =
    app/preferences 的 resume_data_storage_type 原语(整数 0/1 或字符串, 口径对齐运行面
    is_legacy_resume_storage); online = 是否拿到 /torrents/info。matches 仅在 online 时参与
    裁决(离线一律机械忽略 —— 「离线未自证」的机械保证, 防调用方矛盾输入误消歧)。
    命中裁决: 零合格 = miss; 恰一个合格 = hit(hash 交集是加分自证, 离线标注未自证); 多候选
    合格时按 hash 交集消歧, 恰一候选命中 = hit, 多候选命中或全零 = ambiguous(拒不猜测, D5)。
    """
    effective_matches = matches if online else ()
    matched_by_path = {m.path: m.matched_ids for m in effective_matches if m.matched_ids}
    qual_by_path = {q.path: q for q in qualifications}

    reports: list[CandidateReport] = []
    for c in scan.candidates:
        q = qual_by_path.get(c.path)
        mids = matched_by_path.get(c.path, frozenset())
        reports.append(
            CandidateReport(
                path=c.path,
                origin=c.origin,
                suffix=c.suffix,
                qualified=bool(q and q.qualified),
                qualification_reason=q.reason if q is not None else "未判定(调用方未提供该候选的资格结果)",
                fastresume_count=len(q.fastresume_ids) if q is not None else 0,
                has_queue=bool(q and q.has_queue),
                hash_matched=bool(mids),
                matched_ids=tuple(sorted(mids)),
            )
        )
    qualified = [r for r in reports if r.qualified]
    matched_paths = [r.path for r in qualified if r.hash_matched]
    notes: list[str] = list(scan.evidence)

    st = str(storage_type).strip().lower() if storage_type is not None else ""
    if st in _SQLITE_TOKENS:
        return ProbeResult(VERDICT_UNUSABLE_SQLITE, _REASON_SQLITE, tuple(reports), tuple(notes))
    if st and st not in _LEGACY_TOKENS:
        notes.append(
            f"qB resume_data_storage_type={storage_type!r} 非 Legacy 已知值: BT_backup 是否主存储存疑, "
            "运行面预检将 fail-closed 拦截"
        )
    if manual_set:
        return ProbeResult(VERDICT_MANUAL_SET, _REASON_MANUAL_SET, tuple(reports), tuple(notes))
    if not online:
        notes.append("离线未自证: qB 离线或 hashes 不可得, hash 交集未参与裁决")
        notes.append("qB 离线: resume_data_storage_type 未知, SQLite 存储模式未排除(运行面预检仍会拦截)")

    if not qualified:
        return ProbeResult(VERDICT_MISS, f"零合格候选(共扫描 {len(reports)} 个)", tuple(reports), tuple(notes))
    if len(qualified) == 1:
        r = qualified[0]
        if online and r.hash_matched:
            reason = f"唯一合格候选且 hash 自证通过(交集 {len(r.matched_ids)} 个 TorrentID)"
        elif online:
            reason = "唯一合格候选; qB 在线但 hash 交集为 0(候选可能属于其他实例), 未自证"
        else:
            reason = "唯一合格候选(qB 离线, 未自证)"
        return ProbeResult(VERDICT_HIT, reason, tuple(reports), tuple(notes))
    if len(matched_paths) == 1:
        return ProbeResult(
            VERDICT_HIT,
            f"{len(qualified)} 个候选合格, hash 自证消歧命中唯一: {matched_paths[0]}",
            tuple(reports),
            tuple(notes),
        )
    if len(matched_paths) >= 2:
        return ProbeResult(
            VERDICT_AMBIGUOUS,
            f"{len(qualified)} 个候选合格且其中 {len(matched_paths)} 个 hash 命中, 无法消歧; 拒不猜测(D5), 手动键兜底",
            tuple(reports),
            tuple(notes),
        )
    return ProbeResult(
        VERDICT_AMBIGUOUS,
        f"{len(qualified)} 个候选合格且 hash 自证不能消歧(全靠结构自证); 拒不猜测(D5), 手动键兜底",
        tuple(reports),
        tuple(notes),
    )
