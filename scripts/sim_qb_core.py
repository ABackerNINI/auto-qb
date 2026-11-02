"""sim_qb 核心: 常量 / 边界 / 种子 / 语料回放(从 sim_qb.py 原样搬迁)"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import random
import string
import time

# ---------- 常量 ----------

SENTINEL = ".auto-qb-sim-root"
DEFAULT_ROOT = r"R:\auto-qb-sim"

# 写端点(全部记账): 安全断言的证据源
WRITE_ENDPOINTS = frozenset(
    {
        "torrents/addTags",
        "torrents/removeTags",
        "torrents/createTags",
        "torrents/deleteTags",
        "torrents/createCategory",
        "torrents/removeCategories",
        "torrents/setCategory",
        "torrents/start",
        "torrents/stop",
        "torrents/pause",
        "torrents/resume",
        "torrents/delete",
        "torrents/recheck",
        "torrents/reannounce",
        "torrents/setLocation",
        "torrents/setUploadLimit",
        "torrents/setDownloadLimit",
        "torrents/add",
        "torrents/addTrackers",
        "torrents/removeTrackers",
        "torrents/renameFile",
        "torrents/setShareLimits",
        "transfer/setUploadLimit",
        "transfer/setDownloadLimit",
    }
)

# 高风险端点(默认配置下必须 0 命中)
RISK_ENDPOINTS = frozenset(
    {
        "torrents/delete",
        "torrents/setLocation",
        "torrents/reannounce",
        "torrents/recheck",
        "torrents/add",
        "torrents/removeTrackers",
    }
)

# 外壳**已实现**的端点集(读 + 写)。判据 CORPUS.endpoints_covered 拿它比对"语料里出现过的端点":
# 语料档的覆盖范围 = 现有外壳已实现的端点集 —— 把这条写出来, 才不会让"合成数据从未覆盖的路径
# 会被语料覆盖"这句承诺落空(计划 §03: sync/torrentPeers / torrents/export / torrents/pieceHashes
# 三个路由原本根本不存在, 落到 unknown endpoint 404, W3 已补齐)。
IMPLEMENTED_ENDPOINTS = frozenset(
    {
        "auth/login",
        "app/version",
        "app/webapiVersion",
        "app/preferences",
        "sync/maindata",
        "sync/torrentPeers",
        "torrents/info",
        "torrents/files",
        "torrents/trackers",
        "torrents/tags",
        "torrents/categories",
        "torrents/pieceHashes",
        "torrents/export",
        "transfer/info",
        "transfer/uploadLimit",
        "transfer/downloadLimit",
        "_fsmock/state",
    }
) | WRITE_ENDPOINTS

# 变异字段: 全部落在 _VIEW_FIELDS 内, 必然驱动视图置脏(有意的, WEB UI 是已知昂贵路径)
MUTATE_FIELDS = ("upspeed", "dlspeed", "uploaded", "seeding_time", "ratio", "state", "last_activity", "time_active")

STATES_ACTIVE = ("uploading", "stalledUP")


class BoundaryViolation(Exception):
    """边界校验未通过(B1-B4); 一律拒绝执行, 不静默放宽"""


# ---------- B2: 路径逃逸判定 ----------


def _norm(p: str) -> str:
    """归一: 剥 \\\\?\\ 长路径前缀 + realpath + normcase(Windows 大小写不敏感)"""
    if p.startswith("\\\\?\\"):
        p = p[4:]
    return os.path.normcase(os.path.realpath(os.path.abspath(p)))


def is_within(path: str, root: str) -> bool:
    """path 是否位于 root 之下(B2 核心判定)"""
    p, r = _norm(path), _norm(root)
    return p == r or p.startswith(r + os.sep)


# ---------- 种子生成 ----------


def _rand_hash(rng: random.Random) -> str:
    return "".join(rng.choice(string.hexdigits[:16].lower()) for _ in range(40))


def make_torrent(
    rng: random.Random, idx: int, fs_root: str, tracker_url: str, save_path: str, rel_files: list[str], file_size: int,
    name: str, state: str
) -> dict:
    """构造一个种子(字段集与 qB torrents/info 一致, 含全部 REQUIRED_TORRENT_FIELDS)"""
    h = _rand_hash(rng)
    now = int(time.time())
    seeding = rng.randrange(0, 200 * 3600)
    up = rng.randrange(0, 50 * 1024**3)
    return {
        "hash": h,
        "name": name,
        "save_path": save_path,
        "content_path": os.path.join(save_path, rel_files[0].split("\\")[0]) if rel_files else save_path,
        "size": file_size * len(rel_files),
        "total_size": file_size * len(rel_files),
        "tags": "",
        "category": "",
        "state": state,
        "downloaded": file_size * len(rel_files),
        "uploaded": up,
        "dlspeed": 0,
        "upspeed": 0,
        "seeding_time": seeding,
        "ratio": round(up / max(1, file_size * len(rel_files)), 3),
        "amount_left": 0,
        "completed": file_size * len(rel_files),
        "progress": 1.0,
        "dl_limit": 0,
        "up_limit": 0,
        "added_on": now - rng.randrange(0, 90 * 86400),
        "seq_dl": False,
        "f_l_piece_prio": False,
        "ratio_limit": -2,
        "seeding_time_limit": -2,
        "inactive_seeding_time_limit": -2,
        "share_limit_action": -1,
        "downloaded_session": 0,
        "uploaded_session": 0,
        "eta": 8640000,
        "time_active": seeding,
        "last_activity": now,
        "availability": -1,
        "num_seeds": 0,
        "num_leechs": 0,
        "num_complete": -1,
        "num_incomplete": -1,
        "tracker": tracker_url,
        "trackers_count": 1,
        "connections_count": 0,
        "connections_limit": 500,
        "reannounce_in": 1800,
        "reannounce": 0,
        "max_ratio": -1,
        "max_seeding_time": -1,
        "max_inactive_seeding_time": -1,
        "magnet_uri": f"magnet:?xt=urn:btih:{h}",
        "infohash_v1": h,
        "infohash_v2": "",
        "private": False,
        "comment": "",
        "created_by": "mktorrent 1.1",
        "creation_date": now - 86400,
        "has_metadata": True,
        "piece_size": 4 * 1024**2,
        "pieces_have": 1024,
        "pieces_num": 1024,
        "auto_tmm": False,
        "download_path": "",
        "root_path": "",
        "force_start": False,
        "super_seeding": False,
        "priority": 0,
        "completion_on": now - 3600,
        "seen_complete": now - 3600,
        "total_wasted": 0,
        "popularity": 0.0,
        "has_tracker_error": False,
        "has_tracker_warning": False,
        "has_other_announce_error": False,
        # 以下非快照字段, 供仿真端内部使用(不进 qB 响应语义)
        "_rel_files": rel_files,
        "_file_size": file_size,
    }


# ---------- 语料回放 (计划 26-09-21-0024 §06/§07/§08) ----------
#
# 语料 = 一条原始流(首帧即 T0 / 末帧必是一份全量) + 流里没有的按 hash 元数据(files/trackers)
#        + 真值分组(groups.json)。回放端退化成"按时间轴吐帧的播放器": 每帧都是 qB 响应整帧原样,
#        不重建响应、不自己维护脏集合 ⇒ 零语义转换 = 零失真。

FSROOT_PLACEHOLDER = "<FSROOT>"


def resolve_fsroot(text, fs_root: str) -> str:
    """把语料里的 `<FSROOT>` 占位符换成真实的 --fs-root(计划 §12: 目录参数化, 不写死路径)"""
    if not isinstance(text, str) or FSROOT_PLACEHOLDER not in text:
        return text
    return text.replace(FSROOT_PLACEHOLDER, fs_root.replace("\\", "/"))


def piece_hashes_of(rel_sizes: list[tuple[str, int]], pieces: int = 8) -> list[str]:
    """由「排序后的(相对路径 + 大小)集合」**确定性派生** piece hash(计划 §09 修订)。

    为什么不能按 hash 各自随机合成: `rules/actions/checking.py:145-154` 的严格模式是把候选与目标的
    piece hash 列表**逐项比对**; 真实世界里辅种组成员的 piece hash 必须相同(同文件、同大小、同分块)。
    若各自随机, 同组成员会互不相等 ⇒ 严格模式判据**恒假**(比不测更糟: 会给出"没有候选通过"的错误结论)。
    按内容集合派生则同组成员天然共享同一列表, 与真机语义一致。
    """
    seed = repr(sorted(rel_sizes)).encode("utf-8")
    out = []
    for i in range(pieces):
        h = hashlib.sha1(seed + i.to_bytes(4, "big")).hexdigest()
        out.append(h[:40])
    return out


def minimal_bencode(name: str, size: int) -> bytes:
    """torrents/export 的最小合法 bencode(单文件 info dict + announce)"""
    info = f"d6:lengthi{size}e4:name{len(name)}:{name}12:piece lengthi262144ee".encode("utf-8")
    return b"d8:announce26:http://site-1.example/ann4:info" + info + b"e"


def merge_window(frames: list[dict]) -> dict:
    """把窗口内的多帧合并成"这一拍的状态"(计划 §08 窗口合并语义)。

    !语义必须与 store 自己对齐, 否则 D 系列(删除 / 重复投递 / 幂等)判据会因**合并错误**而假红或假绿,
    且极难归因(看起来像 auto-qb 的 bug)。规则:
      · torrents          —— 逐 hash **后写覆盖**(窗口内先改再改回, 取末值)
      · torrents_removed  —— 与 torrents 做**净额判定**(以窗口末态为准: 先删后加 => 净额是"加")
      · categories/tags   —— 同理(增删净额)
      · server_state      —— 仍是 **merge**(与 store.py:111-118 同款)
    """
    out: dict = {
        "torrents": {},
        "torrents_removed": [],
        "tags": [],
        "tags_removed": [],
        "categories": {},
        "categories_removed": [],
        "server_state": {}
    }
    if not frames:
        return out
    # !必须**按序**推进, 不能只做集合运算: 先增后删与先删后加的结果完全不同
    state: dict[str, dict] = {}
    removed_seq: list[str] = []
    tag_add: list[str] = []
    tag_del: list[str] = []
    cat_set: dict = {}
    cat_del: list[str] = []
    for f in frames:
        if f.get("full_update"):
            # 全量轮 = 基线重置: 之前的增删序列不再有参考意义(客户端会整包替换)
            state = {h: dict(v) for h, v in (f.get("torrents") or {}).items()}
            removed_seq = []
            tag_add, tag_del = [], []
            cat_set, cat_del = dict(f.get("categories") or {}), []
        else:
            for h, patch in (f.get("torrents") or {}).items():
                state[h] = {**state.get(h, {}), **patch}
            for h in f.get("torrents_removed") or []:
                state.pop(h, None)  # 按序: 删除即刻生效, 之后若再被新增会重新进 state
                removed_seq.append(h)
            tag_add.extend(f.get("tags") or [])
            tag_del.extend(f.get("tags_removed") or [])
            cat_set.update(f.get("categories") or {})
            cat_del.extend(f.get("categories_removed") or [])
        ss = f.get("server_state")
        if isinstance(ss, dict):
            out["server_state"] = {**out["server_state"], **ss}
    out["torrents"] = state
    # 净额: 只在"删了且末态确实不在"时才报 removed(先删后加 => 不报, 否则客户端会误删)
    out["torrents_removed"] = [h for h in dict.fromkeys(removed_seq) if h not in state]
    # tags/categories 同样按序: **最后一次事件为准**(先加后删 => 报 removed; 先删后加 => 报 add)。
    # 不这么做的话"窗口内加了又删"的标签会既不报 add 也不报 removed, 而客户端可能本来就持有它
    # => 该删的没删掉(欠报比过报危险: 过报一个 removed 对客户端只是 discard 不存在的键, 无副作用)。
    out["tags"] = [t for t, ev in _last_event(frames, "tags", "tags_removed").items() if ev == "add"]
    out["tags_removed"] = [t for t, ev in _last_event(frames, "tags", "tags_removed").items() if ev == "del"]
    cat_last = _last_event(frames, "categories", "categories_removed")
    out["categories"] = {k: cat_set.get(k, {}) for k, ev in cat_last.items() if ev == "add"}
    out["categories_removed"] = [k for k, ev in cat_last.items() if ev == "del"]
    return out


def _last_event(frames: list[dict], add_key: str, del_key: str) -> dict[str, str]:
    """窗口内每个 tag/category 的**最后一次事件**(add/del); 全量轮重置基线"""
    last: dict[str, str] = {}
    for f in frames:
        if f.get("full_update"):
            last = {k: "add" for k in (f.get(add_key) or [])}
            continue
        if add_key == "categories":
            for k in (f.get(add_key) or {}):
                last[k] = "add"
        else:
            for k in (f.get(add_key) or []):
                last[k] = "add"
        for k in (f.get(del_key) or []):
            last[k] = "del"
    return last


class CorpusSource:
    """加载一个语料目录(计划 §06 的格式)。只读, 不改语料。"""
    def __init__(self, path: str, fs_root: str):
        self.path = path
        self.fs_root = fs_root.replace("\\", "/")
        meta_p = os.path.join(path, "meta.json")
        if not os.path.isfile(meta_p):
            raise SystemExit(f"[FATAL] 语料目录里没有 meta.json: {path}")
        with open(meta_p, encoding="utf-8") as f:
            self.meta = json.load(f)
        if self.meta.get("status") == "aborted":
            raise SystemExit(
                f"[FATAL] 该语料 status=aborted(检查点未对齐), 按计划 §08 不可回放 —— "
                f"abort_at={self.meta.get('abort_at')}"
            )
        self.frames = self._read_jsonl_gz("sync-stream.jsonl.gz")
        if not self.frames:
            raise SystemExit(f"[FATAL] 语料流为空: {path}")
        self.files = self._read_json_gz("files.json.gz") or {}
        self.trackers = self._read_json_gz("trackers.json.gz") or {}
        self.disk = self._read_json_gz("disk.json.gz") or {}
        self.peers = self._read_json_gz("peers.json.gz") or {}
        self.groups = self._read_json_gz("groups.json.gz") or {}
        self._resolve_fsroot()

    # ---- IO ----
    def _read_json_gz(self, name: str):
        p = os.path.join(self.path, name)
        if not os.path.isfile(p):
            return None
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)

    def _read_jsonl_gz(self, name: str) -> list[dict]:
        p = os.path.join(self.path, name)
        if not os.path.isfile(p):
            return []
        out = []
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def _resolve_fsroot(self) -> None:
        """把语料里的 <FSROOT> 占位符解析成真实的 --fs-root(只改内存副本, 不动语料文件)"""
        fr = self.fs_root
        for f in self.frames:
            for tv in (f.get("torrents") or {}).values():
                for k in ("save_path", "content_path", "download_path", "root_path"):
                    if tv.get(k):
                        tv[k] = resolve_fsroot(tv[k], fr)

    # ---- 便捷访问 ----
    @property
    def t0(self) -> dict:
        return self.frames[0]

    @property
    def closure(self) -> dict | None:
        last = self.frames[-1]
        return last if last.get("role") in ("closure", "mismatch") else None

    def files_of(self, h: str) -> list:
        return self.files.get(h) or []

    def trackers_of(self, h: str) -> list:
        return self.trackers.get(h) or []

    def disk_table(self) -> dict:
        """拼出 mock 用的磁盘状态表: {全路径: {exists,size}}。

        !**必须以 disk.json.gz 为准**(抓取时刻的磁盘三态), 不能拿 files.json 的"逻辑大小"当"存在"。
        两者是不同的东西: files.json 是 qB 报的文件清单(逻辑上该有哪些文件、多大),
        disk.json 是抓取时**磁盘上真实是什么样**(存在性 + 实际大小 + `.!qB` 后缀)。
        W0 真机实测: 11457 个文件里 **9673 个不存在**(R 盘上 progress=0 的 stoppedDL 等) ——
        若这里退化成"全部存在", D4 的天然样本会全部消失, 缺文件检测永远不触发(假绿)。
        """
        table: dict = {}
        save_paths = {h: (tv.get("save_path") or "") for h, tv in (self.t0.get("torrents") or {}).items()}
        for h, fl in self.files.items():
            sp = save_paths.get(h, "")
            for f in fl:
                rel = str(f.get("name", "")).replace("\\", "/")
                full = (sp.rstrip("/") + "/" + rel.lstrip("/")) if sp else rel
                rec = (self.disk.get(h) or {}).get(rel)
                if isinstance(rec, dict):
                    # suffix=".!qB" 时 exists 已是 false —— auto-qb 拼的是**逻辑名**, 带后缀的文件在它眼里
                    # 就是"不存在"; 这正是真机行为, 回放必须还原, 否则下载中的组会被误判成"文件齐全"。
                    table[full] = {"exists": bool(rec.get("exists")), "size": rec.get("size")}
                else:
                    table[full] = {"exists": True, "size": f.get("size")}
        return table
