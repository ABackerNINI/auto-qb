"""fastresume 双键改写编辑器(计划 26-11-05-0808 §3.2, S2 一期)。

单一职责: 把 BT_backup 里的 .fastresume 指向新保存根路径 —— 定位/解码/双键前缀替换/
往返自校验/.bak 备份/原子写。无状态、不碰 qB API、不碰 state.json;调用时机(qB 下线
窗口)与账本(journal)由回收 daemon(S3)负责, 本模块只提供逐成员的纯编辑能力。

机制依据(计划 §2.2 机制表, qB 8182ae071 + N 系列实测):
- 双键: qB 账面 = qBt-savePath(空 = AutoTMM), libtorrent 实际 = save_path, 加载各取
  各键 —— 必须双键同改, 只改其一 = 半效编辑; qBt-downloadPath 在场时一并改(未完成种
  的下载目录, 与 save_path 可不同值), 同样按前缀替换语义独立处理, 绝不抄 save_path 的新值。
- 键分隔符风味(N1 实测字节): lt 键反斜杠、qBt 键正斜杠, 两键不一致 —— 逐键在原串上做
  前缀替换保住各自风味, 禁止重推导路径串; 同一根路径两种分隔符写法都可能出现在键值里
  (实验脚手架 fr.py _variants 思路), 新值按命中变体的风味转写。
- 前缀边界: 命中必须落在路径分量边界(等值或后随分隔符), 防 R:\\data 误吞 R:\\database。
- 相对路径纪律(N10, E2c 修定 —— issue 26-11-07-2336): qB 便携 profile 部署(application.cpp:
  portableModeEnabled 恒开, 或 --relative-fastresume-paths 显式开启)把与 profile basePath
  同盘符的三路径键写成**basePath 相对形态**(bencoderesumedatastorage 三键统一过
  Profile::toPortablePath; Windows 只对与 basePath 同盘符的绝对路径相对化, profile_p.cpp)。
  只认绝对形态时同盘部署整条收尾链静默失效(改写跳过 -> 成员滞留旧根 -> job 恒 rewritten)。
  修定口径: base 由 bt_backup 单点推导(profile_base_of, qB 源码 CustomProfile 布局
  BT_backup = basePath/data/BT_backup => basePath = 上两级), 相对键解析出绝对形态后进
  既有前缀管道; **解析失败/不命中旧新根仍原样跳过** —— 保守纪律不破(不指鹿为马),
  base 推导错位只造成「照旧跳过」, 不产生错改写(产物恒为新根绝对形态, 不依赖 base)。
  装版 qB(DefaultProfile)相对化不开启(NoConvertConverter), 绝对形态走既有管道。
- 拒载形态(N6): 坏 bencode 落盘 = 重启后种子静默消失(仅一行 INFO)—— 往返自校验不过
  绝不落盘, 这是保命而不是健壮性。
- 写盘原子性: 与 qB 侧 QSaveFile 同规格 tmp+replace+fsync。
- 备份(D7): 同目录 <hash>.fastresume.bak —— qB 扫描只认 *.fastresume 后缀, .bak/.aqtmp
  天然被忽略; 回滚 = 覆盖回原名(restore_backup)。
- 文件名: v1 种子 = <infohash_v1>.fastresume, 与 .torrent 成对(N 系列实测); 混合/v2
  形态用 .torrent 对现算 infohash 匹配, 不猜命名规则。

bencode: 解码复用 hr.bencode(同一套畸形拒绝口径, infohash 计算同源); 编码模块内实现
(仓库现无编码器, 键序排序等行为口径参照实验区 tests-real/lib/bencode.py —— 但只收
bdecode 闭包内的类型, 不收 str: 解码域只有 bytes, 收 str 会造成「编码后解码 != 原值」,
打破往返自校验这个保命不变量; 禁止 import 实验区)。
"""
import contextlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from auto_qb.hr.bencode import BValue, bdecode, compute_infohashes

# 改写的三个路径键(机制表「save path 双键」行; AutoTMM 成员没有后两个 qBt 键, N8 实测)
KEY_SAVE_PATH = b"save_path"
KEY_QBT_SAVE = b"qBt-savePath"
KEY_QBT_DOWNLOAD = b"qBt-downloadPath"
_PATH_KEYS = (KEY_SAVE_PATH, KEY_QBT_SAVE, KEY_QBT_DOWNLOAD)

# 原子写临时文件后缀: 挂在原名之后, 不以 .fastresume 结尾 => qB 目录扫描不会误认
_TMP_SUFFIX = ".aqtmp"
_BAK_SUFFIX = ".bak"


class FastresumeError(Exception):
    """fastresume 读/写失败(坏 bencode / 往返自校验不过 / 形态不符)。调用方只该记日志与跳过, 绝不重试落盘。"""


# ---------------------------------------------------------------------------
# bencode 编码(解码用 hr.bencode)
# ---------------------------------------------------------------------------


def bencode(value: BValue) -> bytes:
    """最小 bencode 编码, 只收 bdecode 闭包内的类型: bytes/int/list|tuple/dict(键 bytes)。

    键按字节序排序, 与 hr.bencode 解码域对称 => 「编码产物解码后与原值逐键一致」由构造
    保证, 是往返自校验的不变量底盘。排序等行为口径参照实验区 tests-real/lib/bencode.py
    (N2 实测该口径重编码的 fastresume qB 原生加载无损); str/float/None 等解码域外类型
    一律 TypeError(调用方编码前显式 encode, 不做隐式转换)。
    """
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        return b"%d:%s" % (len(raw), raw)
    if isinstance(value, int):  # bool 是 int 子类, 但解码产物里不可能出现 bool, 不设防
        return b"i%de" % value
    if isinstance(value, (list, tuple)):
        return b"l" + b"".join(bencode(v) for v in value) + b"e"
    if isinstance(value, dict):
        items: List[Tuple[bytes, BValue]] = []
        for k, v in value.items():
            if not isinstance(k, bytes):
                raise TypeError(f"bencode 字典键必须是 bytes: {type(k)!r}")
            items.append((k, v))
        items.sort(key=lambda kv: kv[0])
        return b"d" + b"".join(bencode(k) + bencode(v) for k, v in items) + b"e"
    raise TypeError(f"bencode 不支持的类型: {type(value)!r}")


# ---------------------------------------------------------------------------
# 定位
# ---------------------------------------------------------------------------


def locate_fastresume(backup_dir: Union[str, Path], hash_v1: str = "", hash_v2: str = "") -> Optional[Path]:
    """BT_backup 目录 + 种子身份 -> .fastresume 路径; 找不到返回 None(不猜命名)。

    命中顺序: <v1>.fastresume / <v2>.fastresume 直查(v1 种子 = <infohash_v1>.fastresume,
    与 .torrent 成对, N 系列实测) -> 直查都未中(混合/v2 命名不定的形态)扫 *.torrent
    现算 infohash 匹配(计划 §2.2「fastresume 文件名」行: 用 .torrent 对现算, 不猜命名
    规则)。兜底扫描才做全目录遍历, 命中即返回, 成本可接受。
    """
    h1 = (hash_v1 or "").strip().lower()
    h2 = (hash_v2 or "").strip().lower()
    if not backup_dir or not (h1 or h2):
        return None
    d = Path(backup_dir)
    if not d.is_dir():
        return None
    for h in (h1, h2):
        if h:
            cand = d / f"{h}.fastresume"
            if cand.is_file():
                return cand
    for tp in sorted(d.glob("*.torrent")):
        try:
            v1, v2, _ = compute_infohashes(tp.read_bytes())
        except (OSError, ValueError):
            continue  # 坏 .torrent 不属于目标种子, 跳过不挡匹配
        if (h1 and v1 == h1) or (h2 and v2 == h2):
            cand = tp.with_name(tp.stem + ".fastresume")
            if cand.is_file():
                return cand
    return None


def backup_path_of(path: Union[str, Path]) -> Path:
    """编辑备份路径: 同目录 <hash>.fastresume.bak(D7 拍板, qB 扫描天然忽略)。"""
    p = Path(path)
    return p.with_name(p.name + _BAK_SUFFIX)


# ---------------------------------------------------------------------------
# 读
# ---------------------------------------------------------------------------


def load_fastresume(path: Union[str, Path]) -> Dict[bytes, BValue]:
    """读并解码 .fastresume; 顶层必须是字典且解码必须消费全部字节(尾部残留 = 坏文件)。

    任何形态不符抛 FastresumeError —— N6: 坏文件绝不能进编辑链, 更不能被回写。
    """
    p = Path(path)
    raw = p.read_bytes()
    try:
        val, pos = bdecode(raw)
    except ValueError as e:
        raise FastresumeError(f"{p.name}: bdecode 失败: {e}") from e
    if pos != len(raw):
        raise FastresumeError(f"{p.name}: 解码后尾部残留 {len(raw) - pos}B, 按坏文件拒收(N6)")
    if not isinstance(val, dict):
        raise FastresumeError(f"{p.name}: 顶层不是字典, 按坏文件拒收")
    return val


# ---------------------------------------------------------------------------
# 双键改写
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RewriteOutcome:
    """逐键改写结果(三态互斥; 键缺席的(AutoTMM 的 qBt 两键)不进任何一档)。"""

    rewritten: Tuple[str, ...] = ()
    already: Tuple[str, ...] = ()  # 已是目标值, 幂等跳过(黄金法则 1)
    unmatched: Tuple[str, ...] = ()  # 前缀不命中(含相对形态解析失败/解析后不命中旧新根), 原样保留


def _flip_seps(p: str) -> str:
    """路径串分隔符风味对调(反斜杠 <-> 正斜杠; 无分隔符时原样返回)。"""
    return p.replace("\\", "/") if "\\" in p else p.replace("/", "\\")


def _prefix_match(value: bytes, prefix: bytes) -> bool:
    """value 以 prefix 开头且命中在分量边界(等值或后随分隔符), 防 R:\\data 误吞 R:\\database。"""
    if not value.startswith(prefix):
        return False
    return len(value) == len(prefix) or value[len(prefix):len(prefix) + 1] in (b"\\", b"/")


# ---------------------------------------------------------------------------
# 相对形态解析(qB 便携 profile 口径, issue 26-11-07-2336; 全纯字符串跨平台 ——
# 测试在 Linux CI 上以 Windows 形态路径为字节样本, 禁用 os.path)
# ---------------------------------------------------------------------------


def _split_absolute(p: str) -> Optional[Tuple[str, str, List[str]]]:
    """绝对路径 -> (根头不含尾分隔符, 根分隔符, 根下分量表); 非绝对/无法解析 -> None。

    三种根形态: 盘符(D:, 分隔符 \\)/UNC(\\\\host\\share, 分隔符 \\)/POSIX 根("", 分隔符 /)。
    分量切分: 盘符/UNC 根按两种分隔符统一切(混合风味 tolerated); POSIX 根只按 / 切
    (反斜杠是 POSIX 合法文件名字符, 原样保留在分量里), 空段(重复/尾部分隔符)一律丢弃。
    """
    if not p:
        return None
    if p.startswith("\\\\"):  # UNC: \\host\share\... (share 不可少, 少于两段判无法解析)
        segs = [s for s in p[2:].replace("/", "\\").split("\\") if s]
        if len(segs) < 2:
            return None
        return ("\\\\" + segs[0] + "\\" + segs[1], "\\", segs[2:])
    if len(p) >= 2 and p[1] == ":" and p[0].isascii() and p[0].isalpha():  # 盘符头
        return (p[:2], "\\", [s for s in p[2:].replace("/", "\\").split("\\") if s])
    if p.startswith("/"):  # POSIX 绝对
        return ("", "/", [s for s in p.split("/") if s])
    return None


def _relative_form(v: str) -> bool:
    """相对形态判定(qB Path::isAbsolute 的反向口径): 无盘符头且不以分隔符开头。"""
    if not v:
        return False
    if len(v) >= 2 and v[1] == ":" and v[0].isascii() and v[0].isalpha():
        return False
    return v[0] not in "\\/"


def _resolve_relative(rel: str, base: str) -> str:
    """把相对形态键按 base(qB profile basePath)解析成绝对形态; 无法解析返回 ""。

    语义对齐 qB fromPortablePath(basePath / rel, profile_p.cpp): rel 逐段解释, "."/空段
    丢弃, ".." 上弹; 上弹越过 base 根(盘符/UNC 头/POSIX 根)判无法解析 -> ""。产物分隔符
    = base 根分隔符(盘符/UNC -> 反斜杠, POSIX -> 正斜杠), 即部署平台语义分隔符 —— rel
    自身风味只进切段(两种分隔符统一切), 不进产物(Qt 双风味都收, 产物须能与旧根变体
    纯字节前缀匹配); POSIX 上反斜杠是合法文件名字符, 误判成上弹时解析结果不命中旧根 ->
    调用方照旧跳过, 保守面不破。
    """
    root, root_sep, base_segs = _split_absolute(base) or (None, None, None)
    if root is None:
        return ""
    out = list(base_segs)
    for seg in rel.replace("\\", "/").split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if not out:
                return ""  # 越出根: 无法解析(保守跳过)
            out.pop()
            continue
        out.append(seg)
    return root + root_sep + root_sep.join(out) if out else root + root_sep


def profile_base_of(backup_dir: str) -> str:
    """BT_backup 目录 -> qB profile basePath; 形态不足/非绝对 -> ""(相对键照旧跳过)。

    qB 源码 CustomProfile 布局(profile_p.cpp): basePath = <root>/qBittorrent,
    dataLocation = basePath/data, BT_backup = basePath/data/BT_backup —— 即 basePath 恒为
    BT_backup 上两级(--profile 与 portable 同构)。DefaultProfile(装版)相对化不开启,
    本推导不会被用到; 用户配错 BT_backup 时推导出的 base 解析不命中旧根, 照旧跳过。
    """
    root, _root_sep, segs = _split_absolute(str(backup_dir or "")) or (None, None, None)
    if root is None or len(segs) < 2:
        return ""
    sep = "/" if root == "" else "\\"
    return root + sep + sep.join(segs[:-2]) if segs[:-2] else root


def _rewrite_pairs(old: str, new: str) -> List[Tuple[bytes, bytes]]:
    """(旧根变体, 新根同风味转写) 对, 覆盖反斜杠/正斜杠两种键值写法; 等值对剔除。

    新根一律按命中旧变体的分隔符风味转写(新旧根各自的记录风味不参与配对), 防止
    「旧根反斜杠 + 新根恰好记成正斜杠」时把 lt 键改出混合风味串。
    """
    pairs: List[Tuple[bytes, bytes]] = []
    seen = set()
    for ov in (old, _flip_seps(old)):
        if ov in seen:
            continue
        seen.add(ov)
        nv = new.replace("/", "\\") if "\\" in ov else new.replace("\\", "/")
        if ov != nv:
            pairs.append((ov.encode("utf-8"), nv.encode("utf-8")))
    return pairs


def rewrite_save_paths(val: Dict[bytes, BValue],
                       old_root: str,
                       new_root: str,
                       *,
                       profile_base: str = "") -> Tuple[Dict[bytes, BValue], RewriteOutcome]:
    """双键前缀替换: save_path + qBt-savePath(+qBt-downloadPath 在场时), 逐键在原串上做。

    - 纯函数: 不改入参, 返回浅拷贝改写(只换顶层 bytes 值, 嵌套值共享不动)。
    - 幂等与嵌套方向裁决: 先算旧根命中与改写产物 —— 产物==原值, 或值同时命中新旧根且
      旧根是新根前缀(嵌套 old<new, 值已在新根内) => already 跳过, 杜绝二次改写; 若
      新根是旧根前缀(嵌套 new<old, 目标=源祖先), 值虽也命中新根前缀但那是旧根命中的
      必然推论, 旧根命中优先 => 产物!=原值必改写(否则旧根键值被 already 误判永不改写,
      daemon 记 already 出账后核验永不过, journal 永久悬挂, 违反 D10)。
    - 相对形态(profile_base 在场且值非绝对): 先按 qB 便携口径解析成绝对形态再进管道
      (E2c 修定, 见模块 docstring「相对路径纪律」); 解析失败/解析结果不命中旧新根 =>
      原样跳过(unmatched), 绝不重推导指鹿为马。profile_base 空 = 相对键一律跳过
      (N10 原口径, 旧链调用面行为不变)。
    - 不匹配即跳过(unmatched): 原样保留。
    - old/new 为空或等值(字节面) => ValueError(fail-fast, 调用方契约错误); 仅分隔符风味
      不同的新旧根视为同一路径, 全键 unmatched 原样返回(无差异可改)。
    """
    if not old_root or not new_root:
        raise ValueError("old_root/new_root 不能为空")
    if str(old_root) == str(new_root):
        raise ValueError("old_root == new_root, 无改写差异")
    pairs = _rewrite_pairs(str(old_root), str(new_root))
    new_prefixes = tuple(nv for _, nv in pairs)
    out = dict(val)
    rewritten: List[str] = []
    already: List[str] = []
    unmatched: List[str] = []
    for key in _PATH_KEYS:
        v = out.get(key)
        if not isinstance(v, bytes):
            continue
        if profile_base:
            v_str = v.decode("utf-8", "replace")
            if _relative_form(v_str):
                resolved = _resolve_relative(v_str, profile_base)
                if resolved:
                    # 解析成功: 以绝对形态进入下方管道 —— 命中旧根走改写, 命中新根判
                    # already, 都不命中落 unmatched(与绝对形态不命中同口径)。out 只在
                    # rewritten 分支写回, unmatched/already 保持原相对值零触碰。
                    v = resolved.encode("utf-8")
        new_hit = any(_prefix_match(v, np) for np in new_prefixes)
        old_hit = None
        for ov, nv in pairs:
            if _prefix_match(v, ov):
                old_hit = (ov, nv)
                break
        if old_hit is not None:
            ov, nv = old_hit
            product = nv + v[len(ov):]
            # already 只在改写确为无操作时判: 产物==原值, 或嵌套 old<new(旧根是新根
            # 前缀, 值同时命中两根 => 值已在新根内, 改写只会二次加深)。嵌套 new<old
            # 时新根前缀命中是旧根命中的推论, 必须改写(嵌套裁决见函数 docstring)。
            if product == v or (new_hit and _prefix_match(nv, ov)):
                already.append(key.decode("utf-8", "replace"))
                continue
            out[key] = product
            rewritten.append(key.decode("utf-8", "replace"))
            continue
        if new_hit:
            already.append(key.decode("utf-8", "replace"))
            continue
        unmatched.append(key.decode("utf-8", "replace"))
    return out, RewriteOutcome(tuple(rewritten), tuple(already), tuple(unmatched))


# ---------------------------------------------------------------------------
# 写(安全三件套: 往返自校验 -> .bak -> 原子写)
# ---------------------------------------------------------------------------


def _fsync_dir(d: Path) -> None:
    """尽力 fsync 目录(POSIX 持久化 rename; Windows 打不开目录句柄, 交给 NTFS 日志 ——
    qB 侧 QSaveFile 同样只做文件级 fsync)。"""
    try:
        fd = os.open(str(d), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _write_bytes_durable(path: Path, data: bytes) -> None:
    """tmp + fsync + replace 原子写(与 qB 侧 QSaveFile 同规格); 失败清理临时文件。"""
    tmp = path.with_name(path.name + _TMP_SUFFIX)
    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise
    _fsync_dir(path.parent)


def _assert_roundtrip(val: Dict[bytes, BValue], payload: bytes) -> None:
    """bdecode 往返自校验: 编辑后的 dict 重编码再解码必须逐键一致 —— 不过绝不落盘(N6 保命)。"""
    try:
        back, pos = bdecode(payload)
    except ValueError as e:
        raise FastresumeError(f"往返自校验失败(重编码不可解码): {e}") from e
    if pos != len(payload):
        raise FastresumeError("往返自校验失败: 重编码后解码有尾部残留")
    if back == val:
        return
    if not isinstance(back, dict) or set(back.keys()) != set(val.keys()):
        raise FastresumeError("往返自校验失败: 键集不一致, 拒绝落盘")
    for k in val:
        if back.get(k) != val[k]:
            raise FastresumeError(f"往返自校验失败: 键 {k!r} 值不一致, 拒绝落盘")
    raise FastresumeError("往返自校验失败: 拒绝落盘")


def save_fastresume(path: Union[str, Path], val: Dict[bytes, BValue]) -> None:
    """安全三件套落盘: 往返自校验 -> 现存文件先备 .bak(改写前内容) -> 原子写。

    校验不过抛 FastresumeError 且磁盘零触碰; 目标文件不存在时不建 .bak(编辑链不会走到,
    防御直接误用)。
    """
    payload = bencode(val)
    _assert_roundtrip(val, payload)
    p = Path(path)
    if p.is_file():
        _write_bytes_durable(backup_path_of(p), p.read_bytes())
    _write_bytes_durable(p, payload)


def restore_backup(path: Union[str, Path]) -> bool:
    """回滚 = .bak 覆盖回原名(D7)。有 .bak 并已恢复返回 True; 无 .bak 返回 False。"""
    p = Path(path)
    bak = backup_path_of(p)
    if not bak.is_file():
        return False
    _write_bytes_durable(p, bak.read_bytes())
    return True


# ---------------------------------------------------------------------------
# 逐成员一步到位(S3 daemon 的单成员入口)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetargetReport:
    """单成员改写回执。status: written(已改写落盘) / unchanged(无键改写, 未落盘) / not_found。"""

    status: str
    path: Optional[str] = None
    rewritten: Tuple[str, ...] = ()
    already: Tuple[str, ...] = ()
    unmatched: Tuple[str, ...] = ()


def retarget(backup_dir: Union[str, Path], hash_v1: str, hash_v2: str, old_root: str, new_root: str) -> RetargetReport:
    """定位 -> 读 -> 双键改写 -> 落盘, 单成员一步到位。

    - 定位不到 -> not_found(不抛, 逐成员记账是调用方的事)。
    - 双键无一改写(全部 already/unmatched)-> unchanged, 不落盘不建 .bak(黄金法则 1,
      幂等重放零副作用)。
    - 坏样本 -> FastresumeError 上抛(绝不落盘, N6); 调用方记日志并保留 .bak 供回滚。
    - 相对形态键: profile base 由 backup_dir 单点推导(profile_base_of, qB 便携布局
      basePath = BT_backup 上两级)后按 E2c 修定口径解析改写; 推导不出(base 空)时相对键
      照旧跳过(N10 原口径)。
    """
    fr = locate_fastresume(backup_dir, hash_v1, hash_v2)
    if fr is None:
        return RetargetReport("not_found")
    val = load_fastresume(fr)
    new_val, outcome = rewrite_save_paths(val, old_root, new_root, profile_base=profile_base_of(str(backup_dir)))
    if not outcome.rewritten:
        return RetargetReport("unchanged", str(fr), (), outcome.already, outcome.unmatched)
    save_fastresume(fr, new_val)
    return RetargetReport("written", str(fr), outcome.rewritten, outcome.already, outcome.unmatched)
