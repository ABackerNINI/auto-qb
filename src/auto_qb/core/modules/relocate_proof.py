"""relocate_proof: 同机判据的路径级证据(D 目录元数据比对 + B′ 元数据降级)

计划 26-11-04-0055 §03.1/§04 P3 前半; 判据设计见报告 26-11-03-2306 §06.1。
把 relocate_plan 里 proved 的来源从 free-space 代理(same_volume_proof)换成
「qB 侧目录证据」, 三态:
- positive: 证明 qB 与 auto-qb 共享同一命名空间(同机同盘);
- negative: 确定性不共享(证据判负, 优先于其它结论, 调用方强制 proved=False);
- unavailable: 端点/权限/不可读导致不可判定 —— 调用方降级或按「未证明」处理。

两级证据(报告 §06.1-4):
- D 级(首选): qB `app/getDirectoryContent`(qbittorrent-api `app_get_directory_content`,
  WebAPI 2.11 ≈ qB 5.0 引入)带 withMetadata 列 qB 视角目录, 条目 name/size/
  last_modification_date 与本机 os.scandir 的 name→(size, int(mtime)) 比对:
  目录非空且至少一个代表文件 size+mtime 完全相等 => positive; 非空但抽中文件全不等
  => negative; 404/端点不存在/权限/纯字符串列表(无 metadata) => unavailable。
  实测坑(报告 §8.1): withMetadata 参数必须是**字符串** "true" —— True/"1"/false
  qB 都当作未开启, 返回纯路径字符串数组。探测目录取本组 content_root 粒度
  (flat 布局 content_root 本就是 save_path, 无法再下沉; 抽样使成本有界),
  不主动去列更大的范围。
- B′ 级(降级): D unavailable 时, 用本组成员种子的 torrents/files(qB 元数据 size,
  全版本可用)与本机同路径 stat 比 size: 任一文件相等 => positive(弱, 注明来自 B′);
  stat 成功但全不等 => negative; 一个都读不到/无文件清单 => unavailable。
  它证不了「qB 现在读得到」(size 来自种子元数据而非实时 FS), 但严格优于已退役的
  free-space 代理(修掉「比错盘」与「不同盘剩余巧合」两类病)。

dst 侧只要求「qB 看得见」: visibility_only=True 时列目录成功(哪怕空目录/纯字符串
列表)即算 positive; 目标叶子未创建是迁移正常输入, 由调用方先经
`nearest_existing_ancestor` 上溯最近存在祖先(与 relocate_common._volume_free_resolved
同一上溯机制)再取证。

路径口径: 入参双路径 —— qb_dir 是 qB 视角(逻辑空间, 即 qB 报回的 save_path 派生),
local_dir 是本机 syscall 路径(调用方经 file_access.map_to_container 既有单点换算,
即 relocate_plan._syscall 同款); 本模块不做翻译, 只在两侧行内比对。只读: 一个 qB
读 API + 本机 scandir/stat, 零写副作用。
"""
import os
from dataclasses import dataclass

from ...infra import file_access, utils
from .relocate_common import logger

# ---------- 常量单点 ----------

# 证据三态(稳定字符串: 调用方按它分支, 改文案不改值)
POSITIVE = "positive"  # 证明共享
NEGATIVE = "negative"  # 确定性不共享
UNAVAILABLE = "unavailable"  # 不可判定(端点/权限/不可读)

# 证据级别(D 首选 / B′ 降级; 进 note 供用户分辨证据强度)
LEVEL_D = "D"
LEVEL_BPRIME = "B'"  # ASCII 撇号, 进日志与 note 不经转义

# D 级列目录的 withMetadata 取值: 必须是字符串 "true"(实测坑, 报告 §8.1 ——
# 布尔 True 会被 requests 折成 "True"、"1" 与 false qB 都当作未开启)
WITH_METADATA = "true"

# D 级比对抽样: qB 条目数超过该值时按均匀步长抽这么多代表条目(确定性, 可测)
PROOF_SAMPLE_K = 3

# B′ 级 stat 的文件数上限(成员文件表可能上千; 比对是逐文件 os.stat, 有界即够)
BPRIME_MAX_FILES = 32

# 上溯祖先的层数上限(与 relocate_common._volume_free_resolved 同口径: 防御病态路径)
_ANCESTOR_MAX_DEPTH = 64


@dataclass(frozen=True)
class Evidence:
    """路径级证据结论(status 三态 + level 证据级 + detail 人读文案)"""

    status: str  # POSITIVE / NEGATIVE / UNAVAILABLE
    level: str  # LEVEL_D / LEVEL_BPRIME / ""(连证据级都拿不到, 如客户端缺失)
    detail: str = ""


# ---------- 内部小件 ----------


def _syscall(path: str) -> str:
    """逻辑路径 -> 本机 syscall 路径(复用 file_access.map_to_container 既有单点;
    与 relocate_plan._syscall 同款 —— 未命中/无映射/查询失败时原样返回)"""
    try:
        fa = file_access.get_file_access()
        return fa.map_to_container(path) or path
    except Exception:  # noqa: BLE001 - 映射查询失败按原路径(比对随后自行降级)
        return path


def _prefixed(path: str) -> str:
    """本机 syscall 前缀(Windows 长路径; 与 relocate_plan 的 lstat 先例同款)"""
    return utils.add_long_path_prefix_for_win(path)


def _local_listing(local_dir: str) -> dict:
    """本机目录 listing: {name: (size, int(mtime), is_dir)}(lstat 语义, 不穿链接)

    OSError 直接冒泡给调用方按 unavailable 处理(本机目录读不了 => 无法比对)。
    is_dir 记录用于剔除目录条目 —— qB 对目录上报的 size 语义未实测(可能是 0 或
    汇总值), 拿它比对会造出假阴性; 文件条目才有确定的 size/mtime 语义。
    """
    out = {}
    with os.scandir(_prefixed(_syscall(local_dir))) as it:
        for e in it:
            st = e.stat(follow_symlinks=False)
            out[e.name] = (st.st_size, int(st.st_mtime), e.is_dir(follow_symlinks=False))
    return out


def _sample(items, k: int) -> list:
    """确定性均匀抽样(条目多时抽 k 个代表; k<=1 取首个; 覆盖首中尾, 比截前 k 个
    更不容易整段踩进同一种局部状态)"""
    n = len(items)
    if n <= k:
        return list(items)
    if k <= 1:
        return [items[0]]
    step = (n - 1) / (k - 1)
    return [items[round(i * step)] for i in range(k)]


def _client_of(ctx):
    """ctx -> qB 原始客户端(缺失返回 None, 调用方按 unavailable 处理)"""
    api = getattr(ctx, "api", None)
    return getattr(api, "client", None) if api is not None else None


def _unavailable(detail: str) -> Evidence:
    return Evidence(UNAVAILABLE, "", detail)


# ---------- D 级: qB 列目录元数据比对 ----------


def _d_evidence(client, qb_dir: str, local_dir: str, visibility_only: bool, sample_k: int) -> Evidence:
    """D 级证据: qB app/getDirectoryContent + withMetadata, 与本机 scandir 比对

    visibility_only(dst 侧): 列目录成功即 positive(哪怕空目录/纯字符串列表) ——
    只证明「qB 看得见该目录」, 不做内容比对。
    """
    try:
        entries = client.app_get_directory_content(directory_path=qb_dir, with_metadata=WITH_METADATA)
    except Exception as e:  # noqa: BLE001 - 404/端点不存在(qB<5.0)/权限/网络都按不可判定降级
        return _unavailable(f"qB 列目录不可用({type(e).__name__}: {e})")
    if not isinstance(entries, (list, tuple)):
        return _unavailable(f"qB 列目录响应形态异常({type(entries).__name__})")
    if visibility_only:
        return Evidence(POSITIVE, LEVEL_D, f"qB 列目录成功({len(entries)} 条), qB 看得见该目录")
    # 元数据未生效(qB<5.0 忽略 withMetadata 回纯字符串, 或参数被未来版本改名) => 无法比对
    if entries and not all(isinstance(e, dict) for e in entries):
        return _unavailable("qB 返回纯路径列表(withMetadata 未生效), 无 size/mtime 可比对")
    try:
        local = _local_listing(local_dir)
    except OSError as e:
        return _unavailable(f"本机目录不可读({e}), 无法与 qB 视角比对")
    if not entries:
        return _unavailable("qB 侧目录为空, 无可比条目")
    # 只比文件条目: 本机侧是目录的剔除(qB 对目录的 size 语义未实测, 比对会造假阴性);
    # qB 独有名字(本机没有)保留比对 —— 同一命名空间下不该出现单侧独有的条目
    comparable = [
        e for e in entries if "dir" not in str(e.get("type", "")).lower() and
        "folder" not in str(e.get("type", "")).lower() and not local.get(e.get("name"), (0, 0, False))[2]
    ]
    if not comparable:
        return _unavailable("qB 条目剔除目录后无可比文件, 无法判定")
    checked = 0
    for e in _sample(comparable, sample_k):
        name = e.get("name")
        size, mtime = e.get("size"), e.get("last_modification_date")
        hit = local.get(name)
        checked += 1
        if hit is not None and hit[0] == size and hit[1] == int(mtime):
            return Evidence(POSITIVE, LEVEL_D, f"代表文件 {name} 的 size+mtime 与本机完全相等")
    detail = "; ".join(str(e.get("name")) for e in _sample(comparable, sample_k)[:3])
    return Evidence(NEGATIVE, LEVEL_D, f"抽中的 {checked} 个代表文件 size/mtime 与本机全不等({detail})")


# ---------- B′ 级: 种子元数据 size 比对(降级) ----------


def _bprime_evidence(local_dir: str, files) -> Evidence:
    """B′ 级证据: 成员种子元数据 size vs 本机同路径 stat(size 单项, 弱证据)

    files: (相对 local_dir 的路径, qB 元数据 size) 序列 —— 调用方从 torrents/files
    换算到探测目录粒度。任一 stat 成功且 size 相等 => positive; stat 成功过但全不等
    => negative; 一个都读不到/无清单 => unavailable。
    """
    files = [(str(rel), int(size)) for rel, size in (files or ())][:BPRIME_MAX_FILES]
    if not files:
        return _unavailable("无文件清单可做 B′ 元数据比对")
    tried = 0
    for rel, size in files:
        try:
            st = os.stat(_prefixed(_syscall(os.path.join(local_dir, *str(rel).replace("\\", "/").split("/")))))
        except OSError:
            continue  # 本机缺文件/不可读: 不算不等, 换下一个代表
        tried += 1
        if st.st_size == size:
            return Evidence(POSITIVE, LEVEL_BPRIME, f"本机 {rel} 的 size 与 qB 元数据相等(弱证据: 仅元数据, 非实时 FS)")
    if tried == 0:
        return _unavailable("本机文件一个都读不到, B′ 比对不可判定")
    return Evidence(NEGATIVE, LEVEL_BPRIME, f"本机 {tried} 个文件的 size 与 qB 元数据全不等")


# ---------- 公开入口 ----------


def path_evidence(
    ctx,
    qb_dir: str,
    local_dir: str,
    files=(),
    visibility_only: bool = False,
    sample_k: int = PROOF_SAMPLE_K
) -> Evidence:
    """路径级同机证据(三态): D 级列目录元数据比对, unavailable 时降级 B′

    ctx: AppContext 形态(消费 ctx.api.client); qb_dir 是 qB 视角路径(逻辑空间),
    local_dir 是本机 syscall 路径(调用方经 file_access.map_to_container 单点换算)。
    files 是 B′ 降级用的 (相对 local_dir 的路径, qB 元数据 size) 序列(src 侧传,
    dst 侧不传); visibility_only=True 为 dst 侧口径(列目录成功即可见)。
    """
    client = _client_of(ctx)
    if client is None:
        d_ev = _unavailable("qB 客户端不可用, 无法取 qB 侧路径证据")
    else:
        d_ev = _d_evidence(client, qb_dir, local_dir, visibility_only, sample_k)
    # B′ 降级只对 src 侧内容比对有意义(dst 没有「成员文件的元数据 size」可拿);
    # 客户端缺失也照走 B′ —— files 是调用方已取回的种子元数据, 不依赖此刻的客户端
    if d_ev.status != UNAVAILABLE or visibility_only:
        return d_ev
    b_ev = _bprime_evidence(local_dir, files)
    if b_ev.status != UNAVAILABLE:
        return b_ev
    # 两级都不可判定: 保留 D 级的失败原因(更根本), detail 注明已尝试降级
    return Evidence(UNAVAILABLE, "", d_ev.detail + "(B′ 降级同样不可判定)")


def nearest_existing_ancestor(fa, path: str):
    """最近存在祖先(逻辑路径): 与 relocate_common._volume_free_resolved 同一上溯机制
    (disk_usage 逐层试到第一个可用层), 但返回**路径本身**供 qB 侧列目录用。

    目标叶子未创建是迁移正常输入 —— qB 要列的是「数据将落在的那层」。全链不可用
    (盘不存在/未就绪/UNC 不可达/映射 miss) => None, 调用方按 unavailable 处理。
    返回形态: 首层可用原样返回(调用方传入的 qB 视角写法不动); 上溯命中的祖先经
    normpath 回本机分隔符(qB 侧 dirPath 实测按 Windows 反斜杠口径)。
    """
    original = str(path or "").strip()
    cur = original.replace("\\", "/")
    for depth in range(_ANCESTOR_MAX_DEPTH):
        if not cur:
            return None
        try:
            fa.disk_usage(cur)
            return original if depth == 0 else os.path.normpath(cur)
        except Exception:  # noqa: BLE001 - 本层不可用(不存在/盘未就绪/不可达): 上溯
            pass
        parent = os.path.dirname(cur)
        if parent == cur:
            return None  # 卷根已失败 => 整链不可判定
        cur = parent
    return None
