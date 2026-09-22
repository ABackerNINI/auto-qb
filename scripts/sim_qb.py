"""qBittorrent WebUI 仿真客户端 (独立安全/性能测试用)

讲 qB WebUI 协议子集的**独立 HTTP 服务**: auto-qb 用真实 `qbittorrent-api` 连上来,
因此 JSON 序列化 / HTTP 往返 / rid 增量语义 / Session 行为全部是真机成本 —— 这些在
进程内替身上根本测不到(实测: 增量 3.3 ms vs 全量 205 ms, 差 62 倍)。

用法:
    python scripts/sim_qb.py --n 5000 --beat 1.5 --active 0.10      # 起服务(前台)
    python scripts/sim_qb.py --n 50 --duration 20 --self-test       # 自检(含真机往返实测)

产物全部落在 `--root` 指定的工作根下(默认 R:\\auto-qb-sim), 按运行 ID 分目录:
    <root>/runs/<时间戳-场景ID>/{fs,config.yml,data,trace.jsonl,writes.jsonl,
                                sim-events.jsonl,fs-before.txt,fs-after.txt,summary.json}

❗R 盘即真实下载盘: 删除动作只在 <run>/fs/ 内生效, 受 B1-B4 四道边界校验约束,
  任一不过即拒绝(越界删除是不可逆的真实数据损失)。

设计要点见 docs/plans/26-09-19-1433-sim-client-5000-plan.html 第 06/07/08 节。
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import random
import shutil
import string
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

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

    ❗语义必须与 store 自己对齐, 否则 D 系列(删除 / 重复投递 / 幂等)判据会因**合并错误**而假红或假绿,
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
    # ❗必须**按序**推进, 不能只做集合运算: 先增后删与先删后加的结果完全不同
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

        ❗**必须以 disk.json.gz 为准**(抓取时刻的磁盘三态), 不能拿 files.json 的"逻辑大小"当"存在"。
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


# ---------- 仿真主体 ----------


class SimQb:
    def __init__(self, args):
        self.args = args
        self.rng = random.Random(args.seed)
        self.lock = threading.RLock()
        self.torrents: dict[str, dict] = {}
        self.dirty: dict[str, dict] = {}
        self.rid = 1
        self.tags: set[str] = set()
        self.categories: set[str] = set()
        self.violations: list[str] = []
        self.writes: list[dict] = []
        self.stats = {"sync_rounds": 0, "sync_full_rounds": 0, "requests": 0, "endpoint_hits": {}}
        self.groups: list[list[str]] = []  # 辅种组(hash 列表)
        self.beat_no = 0
        self.stop_at = None
        self._abort = False
        self._abort_done = False
        self._abort_until = 0.0
        self._materialized = 0
        self.latency_ms = float(getattr(args, "latency_ms", 0) or 0)  # 每个请求的人为延迟(模拟真机负载)
        self.expected_removals: set[str] = set()  # B4 核账: 预期删除清单
        # ❗外部删除必须经 sync/maindata 的 torrents_removed 报出去, 否则 auto-qb 永远看不
        # 到"种子没了" —— 快照里残留幽灵种子, D1/D2/D5 会全测成绿的假象(曾硬编码 [])。
        self.removed: list[str] = []  # 待上报的删除队列(sync 增量轮消费)
        self.removed_all: set[str] = set()  # 累计删除(判据用)
        self.manual_limits: dict[str, int] = {}  # S8: 手设单种限速(奇数 KiB/s), 收尾核对是否被改写
        self._ordered: list[dict] = []  # 全部种子(按生成序); --ramp 时按拍逐步暴露
        self._visible = 0
        self.events: list[dict] = []
        self._ev_lock = threading.Lock()

        self.run_dir = args.run_dir
        # 磁盘事实来源(计划 §07): 语料档默认 <root>/runs/<run-id>/fs, 可用 --fs-root 显式覆盖;
        # mock 档不物化任何文件, 合成档沿用 <run>/fs 真建树。
        self.fs_root = getattr(args, "fs_root", "") or os.path.join(self.run_dir, "fs")
        os.makedirs(self.fs_root, exist_ok=True)

        src = getattr(args, "source", "synthetic") or "synthetic"
        self.corpus_mode = src.startswith("corpus:")
        self.corpus = None
        # getattr 的默认值只在属性**缺失**时生效, 而 argparse 给的默认是空串 -> 必须显式兜底
        self.fs_mode = args.fs_mode or ("mock" if self.corpus_mode else "real")
        # 两层状态模型(计划 §07, 按 W0 真机实测修订):
        #   --command-latency-ms 命令效果对**两个端点**都延后(真机实测 ~733 ms, 两端共享)
        #   --maindata-lag-ms    maindata 相对 torrents/info 的**额外**滞后(真机实测 ≈0)
        # 计划原文假设"info 比 maindata 新", W0 实测 Δ=+1 ms 推翻了它; 拆成两个旋钮后
        # 默认档忠实复现真机, 而把 --maindata-lag-ms 调大即可做"直查更快"的受控实验(红验落点)。
        self.cmd_latency_s = float(getattr(args, "command_latency_ms", 0) or 0) / 1000.0
        self.md_lag_s = float(getattr(args, "maindata_lag_ms", 0) or 0) / 1000.0
        self.overlay: dict[str, dict] = {}  # hash -> {field: (value, t_info, t_md)}
        self.overlay_promoted: set[str] = set()
        self._md_emitted: dict[tuple, bool] = {}  # (hash, field) 是否已随增量轮报出去过

        if self.corpus_mode:
            self._load_corpus(src.split(":", 1)[1])
            self._write_fsmock_state()
        else:
            self._build_torrents()
            self._materialize()
        self._snapshot("fs-before.txt")

    def _write_fsmock_state(self) -> None:
        """把初始磁盘状态落成文件, 供 FS mock **启动即用**(消除"首轮早于首次轮询"的竞态)。

        时间源仍归播放器: 这个文件只是初值, 之后 mock 按秒拉 `GET /_fsmock/state` 覆盖它
        (计划 §07 硬条件③)。不给初值的话, auto-qb 的首轮会在空表上跑 —— 所有文件都被当成缺失。
        """
        p = os.path.join(self.run_dir, "fs-state.json")
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self.fsmock_state(), f, ensure_ascii=False)
            self.fsmock_state_file = p
        except OSError as e:  # pragma: no cover
            self.fsmock_state_file = ""
            print(f"[WARN] 写 fs-state.json 失败: {e}", file=sys.stderr)

    # ---------- 语料加载 ----------

    def _load_corpus(self, path: str):
        """从语料加载种子与元数据 —— 计划 §07 的切口: 只替换"造数层", HTTP 外壳/rid 语义/写端点记账全复用"""
        self.corpus = CorpusSource(path, self.fs_root)
        t0 = self.corpus.t0
        self.torrents = {}
        for h, tv in (t0.get("torrents") or {}).items():
            t = dict(tv)
            fl = self.corpus.files_of(h)
            t["_rel_files"] = [f.get("name", "") for f in fl]
            t["_file_size"] = (fl[0].get("size") if fl else 0)
            t["_files_raw"] = fl
            t["_trackers_raw"] = self.corpus.trackers_of(h)
            self.torrents[h] = t
        self.tags = set(t0.get("tags") or [])
        self.categories = set((t0.get("categories") or {}).keys())
        self._corpus_ss = dict(t0.get("server_state") or {})
        # 真值分组(groups.json) —— D4 取"真机上磁盘就有问题的组"时的样本来源
        self.groups = [list(g.get("members") or []) for g in (self.corpus.groups.get("groups") or [])]
        # ---- 录播时间轴(计划 §08) ----
        # 帧自带**实测 dt_ms**, 累积成时间轴; 回放按墙钟 × 倍速推进游标。
        # ❗末帧(closure/mismatch)是校验锚点, **不吐给客户端**(吐了客户端会按全量轮重置一次)。
        allf = self.corpus.frames
        self.replay_data = allf[:-1] if (allf and allf[-1].get("role") in ("closure", "mismatch")) else list(allf)
        # 帧的"可交付时刻" = 它**完成**时的累积时间(sum(dt))。用完成时刻而不是开始时刻:
        # dt_ms 记的是"距上一帧的实测间隔", 所以第 i 帧在 sum(dt[0..i]) 时才拿到手。
        self.replay_times: list[float] = []
        acc = 0.0
        for f in self.replay_data:
            acc += float(f.get("dt_ms") or 0)
            self.replay_times.append(acc)
        self.replay_total_ms = acc
        self.replay_pos = 0
        self.replay_speed = float(getattr(self.args, "replay_speed", 1.0) or 0.0)
        self.replay_started = time.time()
        self._disk_override: dict[str, dict] = {}
        self._last_rtt_ms = 0.0
        self.replay_stats = {
            "windows": 0,
            "frames_consumed": 0,
            "consumed_until_ms": 0.0,
            "max_drift_ms": 0.0,
            "ended": False,
            "rtt_samples": []
        }
        self._ordered = list(self.torrents.values())
        self._visible = len(self._ordered)
        print(
            f"[corpus] {path}: {len(self.torrents)} 种子 / {len(self.corpus.frames)} 帧"
            f"(可回放 {len(self.replay_data)}, 时间轴 {self.replay_total_ms / 1000:.1f}s) / "
            f"{len(self.groups)} 组 / fs-mode={self.fs_mode} / replay-speed={self.replay_speed} "
            f"latency={getattr(self.args, 'latency_mode', 'recorded')} / "
            f"cmd-latency={self.cmd_latency_s * 1000:.0f}ms md-lag={self.md_lag_s * 1000:.0f}ms",
            file=sys.stderr
        )

    # ---------- 录播游标(计划 §08) ----------

    def replay_cursor_ms(self) -> float:
        """回放游标(录制时间轴上的毫秒位置) = 墙钟已过 × 倍速。speed<=0 => 静态回放(不推进)"""
        if self.replay_speed <= 0:
            return 0.0
        return (time.time() - self.replay_started) * 1000.0 * self.replay_speed

    def _apply_fs_delta(self, frame: dict) -> None:
        """把该帧的 fs_delta 叠到磁盘状态上 —— 录制期真发生过的删/增/去后缀在这里重演"""
        delta = frame.get("fs_delta")
        if not isinstance(delta, dict):
            return
        for h, rels in delta.items():
            sp = (self.torrents.get(h) or {}).get("save_path", "")
            for rel, rec in (rels or {}).items():
                full = (sp.rstrip("/") + "/" + str(rel).lstrip("/")) if sp else str(rel)
                self._disk_override[full] = {"exists": bool(rec.get("exists")), "size": rec.get("size")}

    def consume_replay(self, cursor_ms: float | None = None) -> dict:
        """把游标推进到 cursor_ms, 把这段时间内落过的采样帧**合并成一拍**(计划 §08)。

        ⚠ 顺序: 先合并窗口(本函数) → 再由 `_snapshot_view` 叠 overlay。反了会让滞后边界落在错误的 t_seq 上。
        """
        if cursor_ms is None:
            cursor_ms = self.replay_cursor_ms()
        win: list[dict] = []
        while self.replay_pos < len(self.replay_data) and self.replay_times[self.replay_pos] <= cursor_ms:
            f = self.replay_data[self.replay_pos]
            win.append(f)
            self._apply_fs_delta(f)
            self.replay_pos += 1
        if not win:
            # 流已吐完: 记录"超出末帧多久"(判据 replay_stream_consumed / replay_timeline_aligned 用)
            if self.replay_pos >= len(self.replay_data):
                self.replay_stats["ended"] = True
                self.replay_stats["overrun_ms"] = cursor_ms - self.replay_total_ms
            return {}
        merged = merge_window(win)
        self.replay_stats["windows"] += 1
        self.replay_stats["frames_consumed"] += len(win)
        self.replay_stats["consumed_until_ms"] = self.replay_times[self.replay_pos - 1]
        drift = cursor_ms - self.replay_stats["consumed_until_ms"]
        self.replay_stats["max_drift_ms"] = max(self.replay_stats["max_drift_ms"], drift)
        rtts = [float(f.get("rtt_ms") or 0) for f in win]
        self.replay_stats["rtt_samples"].extend(rtts)
        self._last_rtt_ms = sum(rtts) / len(rtts)

        for h, patch in (merged.get("torrents") or {}).items():
            self.torrents.setdefault(h, {}).update(patch)
            self.dirty.setdefault(h, {}).update(patch)
        for h in merged.get("torrents_removed") or []:
            self.torrents.pop(h, None)
            self.removed.append(h)
        for t in merged.get("tags") or []:
            self.tags.add(t)
        for t in merged.get("tags_removed") or []:
            self.tags.discard(t)
        for k, v in (merged.get("categories") or {}).items():
            self.categories.add(k)
        for k in merged.get("categories_removed") or []:
            self.categories.discard(k)
        ss = merged.get("server_state") or {}
        if ss:
            self._corpus_ss = {**self._corpus_ss, **ss}
        return merged

    def replay_latency_ms(self) -> float:
        """按 --latency-mode 注入延迟: recorded(用录到的真实 rtt) / p50 / p95 / const:N

        计划 §07: 不用 `--latency-ms` 常数近似 —— 它既不是真机那种随载荷变化的延迟
        (全量 205 ms / 增量 3.3 ms), 也还原不了"变化在一个 tick 内部怎么分布"。
        """
        mode = getattr(self.args, "latency_mode", "recorded") or "recorded"
        if mode == "const":
            return self.latency_ms
        samples = sorted(self.replay_stats.get("rtt_samples") or [])
        if mode == "p50" and samples:
            return samples[len(samples) // 2]
        if mode == "p95" and samples:
            return samples[min(len(samples) - 1, int(len(samples) * 0.95))]
        return self._last_rtt_ms

    def sleep_replay_latency(self) -> None:
        ms = self.replay_latency_ms()
        if ms > 0:
            time.sleep(ms / 1000.0)

    # ---------- 两层状态(流状态 vs 实况状态) ----------

    def _visible_fields(self, h: str, now: float, layer: str) -> dict:
        ov = self.overlay.get(h)
        if not ov:
            return {}
        idx = 1 if layer == "info" else 2
        return {f: tup[0] for f, tup in ov.items() if tup[idx] <= now}

    def _live(self, h: str, now: float | None = None) -> dict:
        """实况状态 = 流状态 ⊕ 已到期的 overlay(立即生效侧)"""
        t = self.torrents.get(h)
        if t is None:
            return {}
        out = self._public(t)
        out.update(self._visible_fields(h, now if now is not None else time.time(), "info"))
        return out

    def _snapshot_view(self, h: str, now: float | None = None) -> dict:
        """流状态(snapshot view) = 流状态 ⊕ 已过 md 滞后线的 overlay"""
        t = self.torrents.get(h)
        if t is None:
            return {}
        out = self._public(t)
        out.update(self._visible_fields(h, now if now is not None else time.time(), "maindata"))
        return out

    def _promote_overlays(self) -> None:
        """把刚跨过 maindata 可见线的 overlay 字段登记进脏集合 —— 否则增量轮永远不带它们"""
        now = time.time()
        for h, ov in self.overlay.items():
            due = {f: tup[0] for f, tup in ov.items() if tup[2] <= now}
            if not due:
                continue
            prev = {f for f in due if self._md_emitted.get((h, f), False)}
            fresh = {f: v for f, v in due.items() if f not in prev}
            if fresh:
                self.dirty.setdefault(h, {}).update(fresh)
                for f in fresh:
                    self._md_emitted[(h, f)] = True
                self.overlay_promoted.add(h)

    # ---------- 构建 ----------

    def _build_torrents(self):
        """按固定 seed 分层生成种子: 站点含未配置站点 / 状态含少量异常 / 约 15% 构成辅种组"""
        a = self.args
        n = a.n
        rng = self.rng
        tracker_urls = [
            "https://ptfans.cc/announce",
            "https://tracker.hhanclub.net/announce",
            "https://example.unconfigured-tracker.org/announce",  # 未配置站点 -> 跳过分支
        ]
        # 辅种组: 前 15% 的种子, 每 group_size 个一组(共享 save_path 与文件相对路径)
        group_size = 4
        n_grouped = int(n * 0.15)
        n_grouped -= n_grouped % group_size
        grouped = set(range(n_grouped))

        for i in range(n):
            # 辅种组成员一律用**已配置**站点: 未配置站点的种子会被 auto-qb 跳过(不归组),
            # 会让"组内成员"在 sim 侧与 auto-qb 侧不一致, D4 的停止率判据随之失真。
            # 未配置站点的覆盖交给非辅种种子(仍然会走"未匹配 -> 警告并跳过"分支)。
            site = (i % 2) if i in grouped else (i % 3)
            show = i % 40
            ep = (i % 24) + 1
            if i in grouped:
                # ❗组内成员必须共享 save_path 与**完全相同的文件相对路径**, 否则归不成组
                # (曾按种子序号算 ep -> 同组文件名各不相同 -> 辅种组形同虚设)
                gi = i // group_size
                gep = (gi % 24) + 1
                save_path = os.path.join(self.fs_root, "shows", f"grp{gi:04d}")
                shared = f"Some.Show.S01E{gep:02d}.1080p.WEB-DL-GRP"
                rel = [f"{shared}\\{shared}.mkv"]
                name = f"{shared}[{site}]"  # 组内成员种子名不同, 但文件列表相同
            else:
                save_path = os.path.join(self.fs_root, "shows", f"Show{show:02d}")
                base = f"Show{show:02d}.S01E{ep:02d}.1080p.WEB-DL-GRP{i}"
                rel = [f"{base}\\{base}.mkv"]
                name = base
            # 少量异常状态: 触发错误原因预取与缺文件扫描路径
            if i % 500 == 7:
                state = "missingFiles"
            elif i % 500 == 13:
                state = "error"  # 合法 qB 状态名(写成 "errored" 会被解析成 UNKNOWN)
            elif i % 97 == 5:
                state = "downloading"
            else:
                state = "stalledUP"
            t = make_torrent(rng, i, self.fs_root, tracker_urls[site], save_path, rel, a.fs_file_size, name, state)
            # S8 限速保护: 约 10% 的种子带**手设单种限速**。
            # ❗必须造**奇数 KiB/s** —— 项目约定 `utils.is_manual_speed_limit` 判定为
            # `(bytes // 1024) % 2 == 1`, 奇数值才被当作"用户手设、本程序不覆盖"。
            # 造偶数(初版写成 i*7+1, i 恒为奇数 ⇒ KiB 恒为偶数)会被正常覆盖 -> 假红。
            if i % 10 == 3:
                t["up_limit"] = (i * 8 + 1) * 1024  # KiB = i*8+1 恒为奇数
                self.manual_limits[t["hash"]] = t["up_limit"]
            self._ordered.append(t)

        # 辅种组按**生成序**切分(与 --ramp 的逐步暴露一致: 组内成员逐个到位)
        hashes = [t["hash"] for t in self._ordered]
        for gi in range(n_grouped // group_size):
            self.groups.append(hashes[gi * group_size:(gi + 1) * group_size])

        # 首轮暴露: --ramp 0(默认) = 一次性全量; >0 = 先只给 ramp 个, 由 pump 按拍追加
        k = a.ramp if a.ramp > 0 else len(self._ordered)
        self._expose(min(k, len(self._ordered)))

    def _expose(self, target: int) -> int:
        """把生成序里的前 target 个种子暴露给 auto-qb(P2 渐进灌入用)

        ❗新暴露的种子必须整条进脏集合: 增量轮只回 `dirty`, 不这么做的话 auto-qb 永远
        看不到新种子(ramp 场景会静默少一半数据)。
        """
        added = 0
        while len(self.torrents) < target and self._visible < len(self._ordered):
            t = self._ordered[self._visible]
            self._visible += 1
            self.torrents[t["hash"]] = t
            if self.args.fs_materialize != 0:
                self._materialize_one(t)
            self.dirty[t["hash"]] = self._public(t)
            added += 1
        return added

    def _materialize(self):
        """物化当前已暴露的种子(--ramp 时新暴露的由 _expose 逐个物化)"""
        if self.args.fs_materialize == 0:
            return
        self._materialized = len(self.torrents)

    def _materialize_one(self, t: dict) -> bool:
        for rel in t["_rel_files"]:
            p = os.path.normpath(os.path.join(t["save_path"], rel.replace("\\", os.sep)))
            if os.path.exists(p) and os.path.getsize(p) == t["_file_size"]:
                continue  # 辅种组共享同一份, 已建过
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(b"\0" * t["_file_size"])
        return True

    def file_paths_of(self, t: dict) -> list[str]:
        return [os.path.normpath(os.path.join(t["save_path"], rel.replace("\\", os.sep))) for rel in t["_rel_files"]]

    # ---------- 文件树快照与核账 ----------

    def _walk(self):
        out = {}
        for dirpath, _, files in os.walk(self.fs_root):
            for fn in files:
                p = os.path.join(dirpath, fn)
                try:
                    out[os.path.relpath(p, self.fs_root)] = os.path.getsize(p)
                except OSError:
                    pass
        return out

    def _snapshot(self, name: str) -> dict:
        snap = self._walk()
        with open(os.path.join(self.run_dir, name), "w", encoding="utf-8") as f:
            for k in sorted(snap):
                f.write(f"{k}\t{snap[k]}\n")
        return snap

    def reconcile(self) -> dict:
        """B4 收尾核账: 只允许出现预期删除"""
        before = {}
        p = os.path.join(self.run_dir, "fs-before.txt")
        if os.path.exists(p):
            for line in open(p, encoding="utf-8"):
                if "\t" in line:
                    k, v = line.rstrip("\n").split("\t", 1)
                    before[k] = int(v)
        after = self._snapshot("fs-after.txt")
        removed = sorted(set(before) - set(after))
        unexpected = [r for r in removed if r not in self.expected_removals]
        if unexpected:
            self.violations.append(f"B4: unexpected_removals={len(unexpected)} e.g. {unexpected[:3]}")
        return {
            "files_before": len(before),
            "files_after": len(after),
            "removed": removed,
            "unexpected_removals": unexpected,
        }

    # ---------- 删除: B2/B3 ----------

    def safe_delete_files(self, paths: list[str], declared: int) -> int:
        if declared is not None and len(paths) > declared * 2:
            self.violations.append(f"B3: bulk delete {len(paths)} > declared {declared}*2")
            raise BoundaryViolation("B3 单次删除数量超限")
        ok = 0
        for p in paths:
            if not is_within(p, self.fs_root):
                self.violations.append(f"B2: FS_ESCAPE {p}")
                raise BoundaryViolation(f"B2 路径逃逸: {p}")
        for p in paths:
            try:
                os.remove(p)
                rel = os.path.relpath(p, self.fs_root)
                self.expected_removals.add(rel)
                ok += 1
            except FileNotFoundError:
                pass
            except OSError as e:
                self.violations.append(f"B2: remove failed {p}: {e}")
        return ok

    def delete_group_files(self, gi: int) -> int:
        """D4: 删掉整个辅种组的文件, 并让组内一个成员进入 errored

        只删文件 + 报 errored(模拟 qB 校验/读写失败发现异常), **不**把其它成员的 state
        改成 missingFiles —— 文件到底丢没丢, 必须由 auto-qb 自己扫磁盘判定, 而不是由
        仿真端把答案告诉它。
        """
        if gi >= len(self.groups):
            return 0
        paths = []
        for h in self.groups[gi]:
            t = self.torrents.get(h)
            if t:
                paths.extend(self.file_paths_of(t))
        paths = list(dict.fromkeys(paths))
        n = self.safe_delete_files(paths, len(paths))
        members = [h for h in self.groups[gi] if h in self.torrents]
        if members:  # 触发 _handle_state_transitions 的 "进入 errored" 分支
            # ❗状态名必须是 qB 的 "error"(写成 "errored" 会被解析成 UNKNOWN -> is_errored 为假)
            t = self.torrents[members[0]]
            t["state"] = "error"
            self.dirty.setdefault(members[0], {})["state"] = "error"
        return n

    def delete_torrents(self, count: int, with_files: bool) -> int:
        with self.lock:
            victims = list(self.torrents)[:count]
            paths = []
            if with_files:
                for h in victims:
                    paths.extend(self.file_paths_of(self.torrents[h]))
                paths = list(dict.fromkeys(paths))
                self.safe_delete_files(paths, len(paths))
            for h in victims:
                self.torrents.pop(h, None)
                self.dirty.pop(h, None)
                self.removed.append(h)  # 待上报 -> sync 增量轮的 torrents_removed
                self.removed_all.add(h)
                for g in self.groups:
                    if h in g:
                        g.remove(h)
            return len(victims)

    # ---------- 负载引擎 ----------

    def pump(self):
        """一拍: 变异 active 比例的种子, 登记脏集合"""
        a = self.args
        with self.lock:
            self.beat_no += 1
            n_active = max(1, int(len(self.torrents) * a.active))
            pool = list(self.torrents)
            if not pool:
                return
            if a.mode == "steady":
                if not hasattr(self, "_steady_pool"):
                    self._steady_pool = self.rng.sample(pool, min(n_active, len(pool)))
                target = self._steady_pool
            else:
                target = self.rng.sample(pool, min(n_active, len(pool)))
            now = int(time.time())
            for h in target:
                t = self.torrents.get(h)
                if t is None:
                    continue
                patch = {
                    "upspeed": self.rng.randrange(0, 8 * 1024**2),
                    "dlspeed": 0,
                    "uploaded": t["uploaded"] + self.rng.randrange(1, 4 * 1024**2),
                    "seeding_time": t["seeding_time"] + 1,
                    "ratio": round(t["ratio"] + 0.001, 3),
                    "state": self.rng.choice(STATES_ACTIVE),
                    "last_activity": now,
                    "time_active": t["time_active"] + 1,
                }
                t.update(patch)
                self.dirty.setdefault(h, {}).update({k: patch[k] for k in MUTATE_FIELDS})
            # P2 渐进灌入: 每拍追加 ramp 个种子(首轮成本被打散, 看是否有单 tick 尖峰)
            if a.ramp > 0 and self._visible < len(self._ordered):
                k = self._expose(len(self.torrents) + a.ramp)
                if k:
                    self._event("ramp", {"added": k, "total": len(self.torrents)})
            # 定时注入
            for spec in (a.delete_torrents or []):
                beat, cnt, wf = spec
                if self.beat_no == beat:
                    self.delete_torrents(cnt, wf)
                    self._event("delete_torrents", {"count": cnt, "with_files": wf})
            for spec in (a.delete_files or []):
                beat, gi = spec
                if self.beat_no == beat:
                    self.delete_group_files(gi)
                    self._event("delete_files", {"group": gi})
            # D5b 幂等: 重复投递同一批 torrents_removed(真实 qB 在 rid 错乱时会重放)
            if getattr(a, "redeliver_removed", 0) and self.beat_no == a.redeliver_removed:
                dup = sorted(self.removed_all)
                self.removed.extend(dup)
                self._event("redeliver_removed", {"count": len(dup)})

    def _event(self, kind: str, extra: dict):
        rec = {"ts": time.time(), "beat": self.beat_no, "kind": kind}
        rec.update(extra)
        self.events.append(rec)
        with self._ev_lock:
            with open(os.path.join(self.run_dir, "sim-events.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---------- sync/maindata ----------

    def sync_maindata(self, rid: int) -> dict:
        if self.corpus_mode:
            return self._sync_corpus(rid)
        with self.lock:
            self.stats["sync_rounds"] += 1
            if rid != self.rid:
                out = {
                    "rid": self.rid,
                    "full_update": True,
                    "torrents": {
                        h: self._public(t)
                        for h, t in self.torrents.items()
                    },
                    # 全量轮: 快照本身即权威, 删掉的种子只需不在 torrents 里
                    "torrents_removed": [],
                    "server_state": self.server_state(),
                }
                self.dirty.clear()
                self.removed.clear()
                self.stats["sync_full_rounds"] += 1
            else:
                out = {
                    "rid": self.rid + 1,
                    "full_update": False,
                    "torrents": {
                        h: dict(p)
                        for h, p in self.dirty.items()
                    },
                    "torrents_removed": list(self.removed),
                    "server_state": self.server_state(),
                }
                self.rid += 1
                self.dirty.clear()
                self.removed.clear()
            return out

    def _sync_corpus(self, rid: int) -> dict:
        """语料档的 sync/maindata —— 流状态视图(计划 §07 两层状态)。

        ⚠ 顺序: 先合并窗口(§08) → **再**按滞后规则叠 overlay。反了会让滞后边界落在错误的 t_seq 上。
        静态回放时流不推进(帧已全量加载, 由 W4 的游标按时间轴吐), 所以这里只处理 overlay。
        """
        with self.lock:
            self.stats["sync_rounds"] += 1
            # ⚠ 顺序: 先合并窗口(§08) → 再叠 overlay 的可见性(§07)。
            # 反了会让滞后边界落在错误的 t_seq 上 —— 故刻意写成两个独立调用, 不揉在一起。
            self.consume_replay()
            self._promote_overlays()
            if rid != self.rid:
                out = {
                    "rid": self.rid,
                    "full_update": True,
                    "torrents": {
                        h: self._snapshot_view(h)
                        for h in self.torrents
                    },
                    "torrents_removed": [],
                    "server_state": self.server_state(),
                }
                self.stats["sync_full_rounds"] += 1
            else:
                out = {
                    "rid": self.rid + 1,
                    "full_update": False,
                    "torrents": {
                        h: dict(p)
                        for h, p in self.dirty.items()
                    },
                    "torrents_removed": list(self.removed),
                    "server_state": self.server_state(),
                }
                self.rid += 1
            self.dirty.clear()
            self.removed.clear()
            return out

    def fsmock_state(self) -> dict:
        """给 FS mock 的"当前磁盘状态"(计划 §07 硬条件③: 时间源归播放器)。

        语料档 = files.json 的 disk 初值(按 t_seq 变化的部分由 W4 的 fs_delta 叠加);
        合成档 = 真树现算(只在 --fs-mode=mock 时才会被拉)。
        """
        if self.corpus_mode and self.corpus:
            files = self.corpus.disk_table()
            # 录制期的磁盘变化(fs_delta)按 t_seq 重演 —— 覆盖在初值之上
            for k, v in self._disk_override.items():
                files[k] = v
        else:
            files = {}
            for h, t in self.torrents.items():
                for rel in (t.get("_rel_files") or []):
                    full = os.path.join(t.get("save_path", ""), rel.replace("/", os.sep))
                    try:
                        files[full] = {"exists": os.path.exists(full), "size": os.path.getsize(full)}
                    except OSError:
                        files[full] = {"exists": False, "size": None}
        ss = self.server_state() or {}
        free = int(ss.get("free_space_on_disk") or 0)
        return {
            "files": files,
            "free_space": free,
            "total_space": int(ss.get("total_space") or 0) or max(free, 1),
            "t_seq": getattr(self, "replay_cursor", 0)
        }

    def _public(self, t: dict) -> dict:
        return {k: v for k, v in t.items() if not k.startswith("_")}

    def server_state(self) -> dict:
        if self.corpus_mode:
            # 语料档: 全局状态**只有一个来源** —— 流的首帧(计划 §06/§08)。
            # 原样透传而不是自己稀疏化: qB 的 server_state 是 merge 语义(store.py:111-118),
            # 自己挑键就要自己猜"某键缺失时该怎么办"。
            return dict(getattr(self, "_corpus_ss", {}) or {})
        up = sum(t["upspeed"] for t in self.torrents.values())
        return {
            "all_time_dl": 0,
            "all_time_ul": 0,
            "dl_info_data": 0,
            "dl_info_speed": 0,
            "dl_rate_limit": 0,
            "up_info_data": sum(t["uploaded"] for t in self.torrents.values()),
            "up_info_speed": up,
            "up_rate_limit": 0,
            "connection_status": "connected",
            "dht_nodes": 0,
            "queued_io_jobs": 0,
            "read_cache_hits": 0,
            "total_buffers_size": 0,
            "use_alt_speed_limits": False,
            "refresh_interval": 1500,
        }

    # ---------- 写端点 ----------

    def apply_write(self, endpoint: str, params: dict) -> None:
        """写端点: 全部记账; --read-only 时抛错(由 handler 转 403), 不改变状态"""
        self.writes.append({"ts": time.time(), "endpoint": endpoint, "params": params})
        with open(os.path.join(self.run_dir, "writes.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "endpoint": endpoint, "params": params}, ensure_ascii=False) + "\n")
        if self.args.read_only:
            return
        if self.corpus_mode:
            self._apply_write_corpus(endpoint, params)
            return
        self._apply_write_state(endpoint, params)

    def _apply_write_corpus(self, endpoint: str, params: dict) -> None:
        """语料档的写端点: 命令效果先进 **overlay**, 由两层状态模型决定何时对两个端点可见(计划 §07)。

        为什么不能直接改 self.torrents: `self.torrents` 是**流状态**(只由录制流推进), 而
        auto-qb 自己发的命令不在录制流里。若直接改它, "info 比 maindata 新"就无从表达 ——
        那正是 issue 26-09-20-2145 要复现的东西。
        """
        hashes = self._parse_hashes(params.get("hashes"))
        before = {h: dict(self.torrents[h]) for h in hashes if h in self.torrents}
        self._apply_write_state(endpoint, params)
        now = time.time()
        t_info = now + self.cmd_latency_s
        t_md = t_info + self.md_lag_s
        for h, b in before.items():
            after = self.torrents.get(h)
            if after is None:
                continue
            diff = {k: v for k, v in after.items() if not k.startswith("_") and b.get(k) != v}
            if diff:
                slot = self.overlay.setdefault(h, {})
                for k, v in diff.items():
                    slot[k] = (v, t_info, t_md)
            self.torrents[h] = b  # 回滚: base 只由录制流推进

    def _apply_write_state(self, endpoint: str, params: dict) -> None:
        hashes = self._parse_hashes(params.get("hashes"))
        if endpoint == "torrents/addTags":
            self._tag(hashes, params.get("tags", ""), add=True)
        elif endpoint == "torrents/removeTags":
            self._tag(hashes, params.get("tags", ""), add=False)
        elif endpoint == "torrents/createTags":
            for x in (params.get("tags") or "").split(","):
                if x:
                    self.tags.add(x)
        elif endpoint == "torrents/deleteTags":
            for x in (params.get("tags") or "").split(","):
                self.tags.discard(x)
        elif endpoint == "torrents/setCategory":
            cat = params.get("category", "")
            for h in hashes:
                t = self.torrents.get(h)
                if t is not None:
                    t["category"] = cat
                    self._mark(h, {"category": cat})
            if cat:
                self.categories.add(cat)
        elif endpoint == "torrents/createCategory":
            self.categories.add(params.get("category", ""))
        elif endpoint == "torrents/stop":
            self._set_state(hashes, "pausedUP")
        elif endpoint == "torrents/start":
            self._set_state(hashes, "stalledUP")
        elif endpoint == "torrents/pause":
            self._set_state(hashes, "pausedUP")
        elif endpoint == "torrents/resume":
            self._set_state(hashes, "stalledUP")
        elif endpoint == "torrents/setLocation":
            loc = params.get("location", "")
            for h in hashes:
                t = self.torrents.get(h)
                if t is not None:
                    t["save_path"] = loc
                    self._mark(h, {"save_path": loc})
        elif endpoint in ("torrents/setUploadLimit", "torrents/setDownloadLimit"):
            key = "up_limit" if endpoint.endswith("UploadLimit") else "dl_limit"
            val = int(params.get("limit") or 0)
            for h in hashes:
                t = self.torrents.get(h)
                if t is not None:
                    t[key] = val
                    self._mark(h, {key: val})
        elif endpoint == "torrents/delete":
            with_files = str(params.get("deleteFiles", "false")).lower() in ("true", "1", "yes")
            for h in hashes:
                t = self.torrents.get(h)
                if t is None:
                    continue
                if with_files:
                    self.safe_delete_files(self.file_paths_of(t), 1)
                self.torrents.pop(h, None)
                self.dirty.pop(h, None)
                self.removed.append(h)  # 同上: 必须上报, 否则 auto-qb 快照留幽灵
                self.removed_all.add(h)
                for g in self.groups:
                    if h in g:
                        g.remove(h)

    def _parse_hashes(self, raw) -> list[str]:
        if not raw:
            return []
        if raw == "all":
            return list(self.torrents)
        return [x for x in str(raw).replace(",", "|").split("|") if x]

    def _mark(self, h: str, patch: dict):
        t = self.torrents.get(h)
        if t is None:
            return
        self.dirty.setdefault(h, {}).update(patch)

    def _tag(self, hashes: list[str], tags: str, add: bool):
        for h in hashes:
            t = self.torrents.get(h)
            if t is None:
                continue
            cur = [x for x in (t["tags"] or "").split(",") if x]
            for x in (tags or "").split(","):
                x = x.strip()
                if not x:
                    continue
                if add and x not in cur:
                    cur.append(x)
                elif not add and x in cur:
                    cur.remove(x)
            t["tags"] = ",".join(cur)
            self._mark(h, {"tags": t["tags"]})

    def _set_state(self, hashes: list[str], state: str):
        for h in hashes:
            t = self.torrents.get(h)
            if t is not None:
                t["state"] = state
                self._mark(h, {"state": state})

    # ---------- summary ----------

    def summary(self, extra: dict | None = None) -> dict:
        fs = self.reconcile()
        risky = {e: self.stats["endpoint_hits"].get(e, 0) for e in sorted(RISK_ENDPOINTS)}
        s = {
            "scenario":
                {
                    "n": self.args.n,
                    "beat": self.args.beat,
                    "active": self.args.active,
                    "mode": self.args.mode,
                    "seed": self.args.seed,
                    "read_only": self.args.read_only,
                    "beat_reached": self.beat_no,
                },
            "sync": {
                "rounds": self.stats["sync_rounds"],
                "full_rounds": self.stats["sync_full_rounds"],
            },
            "writes":
                {
                    "total": len(self.writes),
                    "by_endpoint": dict(sorted(self.stats["endpoint_hits"].items())),
                    "risky": risky,
                },
            "fs": fs,
            "violations": self.violations,
            "root": self.args.root,
            "run_dir": self.run_dir,
        }
        if self.corpus_mode:
            rs = dict(self.replay_stats)
            rs["replayable_frames"] = len(self.replay_data)
            rs["consumed_frames"] = self.replay_pos
            rs["stream_consumed"] = self.replay_pos >= len(self.replay_data)
            rs["timeline_ms"] = self.replay_total_ms
            rs["speed"] = self.replay_speed
            rs["latency_mode"] = getattr(self.args, "latency_mode", "recorded")
            s["replay"] = rs
            s["corpus"] = {
                "path": getattr(self.args, "source", ""),
                "torrents": len(self.torrents),
                "groups": len(self.groups),
                "fs_mode": self.fs_mode
            }
        if extra:
            s.update(extra)
        s["verdict"] = "FAIL" if self.violations else "OK"
        return s


# ---------- HTTP ----------


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "SimQb/1.0"

    def log_message(self, *a):
        pass

    # 参数合并: POST 的 rid/hashes 等常在 body(form), GET 在 query —— 只解析 query 会恒得 rid=0
    def _params(self) -> dict:
        raw = self.path or ""
        if self.command in ("POST", "PUT"):
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                try:
                    body = self.rfile.read(n).decode("utf-8", "replace")
                except Exception:
                    body = ""
                raw = raw + ("&" if "?" in raw else "?") + body
        query = urlparse(raw).query
        if not query and "?" in raw:
            query = raw.split("?", 1)[-1]
        return {k: v[0] for k, v in parse_qs(query).items()}

    def _route(self) -> str:
        p = urlparse(self.path).path
        return p.strip("/").replace("api/v2/", "")

    def _json(self, obj, status=200):
        b = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _text(self, s: str, status=200):
        b = s.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _trace(self, route, params, status, size):
        sim = self.server.sim
        sim.stats["requests"] += 1
        sim.stats["endpoint_hits"][route] = sim.stats["endpoint_hits"].get(route, 0) + 1
        try:
            with open(os.path.join(sim.run_dir, "trace.jsonl"), "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "ts": time.time(),
                            "m": self.command,
                            "e": route,
                            "p": {
                                k: (v[:120] if isinstance(v, str) else v)
                                for k, v in params.items()
                            },
                            "s": status,
                            "b": size,
                        },
                        ensure_ascii=False
                    ) + "\n"
                )
        except OSError:
            pass

    def do_HEAD(self):
        if self.server.sim._abort:
            self.close_connection = True
            return
        self._text("")

    def do_GET(self):
        self._dispatch()

    def do_POST(self):
        self._dispatch()

    def _dispatch(self):
        sim = self.server.sim
        if sim._abort:
            self.close_connection = True
            return
        # 人为延迟(默认 0): 让假 qB 表现得像**真机上有负载的 qB**。
        # 没有它, 本地每个请求 ~0.5ms ⇒ `_build_search_index` 一轮 500 次文件 API 只要 250ms,
        # 主循环永远不饱和 ⇒ "命令排队 wait_ms" 恒为 0 ⇒ 真机上"点了要等 2-4s"这类缺陷
        # **在本地永远复现不出来**(与「桩服务是瞬时的 ⇒ 顺序型缺陷测不出」同一类, 但在后端)。
        if sim.latency_ms:
            time.sleep(sim.latency_ms / 1000.0)
        route = self._route()
        params = self._params()

        if route == "auth/login":
            self._trace(route, {}, 200, 3)
            return self._text("Ok.")
        if route in ("app/webapiVersion", "app/version", "app/preferences"):
            v = {"app/webapiVersion": "2.11", "app/version": "v5.2.3", "app/preferences": {}}[route]
            self._trace(route, params, 200, len(str(v)))
            return self._text(v) if isinstance(v, str) else self._json(v)

        if route in WRITE_ENDPOINTS:
            if sim.args.read_only:
                sim.apply_write(route, params)  # 记账但不改变状态
                self._trace(route, params, 403, 0)
                return self._json({"error": "read-only sim"}, status=403)
            try:
                sim.apply_write(route, params)
            except BoundaryViolation as e:
                self._trace(route, params, 403, 0)
                return self._json({"error": str(e)}, status=403)
            self._trace(route, params, 200, 2)
            return self._text("Ok.")

        # 读端点
        if route == "sync/maindata":
            # 录播档: 按 --latency-mode 注入延迟(recorded = 用录到的真实 rtt), 替代 --latency-ms 常数近似
            if sim.corpus_mode:
                sim.sleep_replay_latency()
            out = sim.sync_maindata(int(params.get("rid") or 0))
            b = json.dumps(out).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            self._trace(route, {"rid": params.get("rid")}, 200, len(b))
            return
        if route == "torrents/info":
            self._trace(route, params, 200, 0)
            # 语料档: 走**实况状态**(流状态 ⊕ 已到期 overlay)。它与 sync/maindata 的差异正是
            # issue 26-09-20-2145 要复现的"真值尚未落地"。合成档沿用原样(无 overlay)。
            if sim.corpus_mode:
                return self._json([sim._live(h) for h in sim.torrents])
            return self._json([sim._public(t) for t in sim.torrents.values()])
        if route == "torrents/files":
            t = sim.torrents.get(params.get("hash"))
            if sim.corpus_mode:
                # 语料档: 用**录下来的** files —— 归组 key 与缺文件扫描的唯一来源, 不再现场合成
                out = [dict(f) for f in (t.get("_files_raw") or [])] if t else []
                self._trace(route, params, 200, 0)
                return self._json(out)
            out = (
                [
                    {
                        "index": i,
                        "name": r,
                        "size": t["_file_size"],
                        "progress": 1.0,
                        "priority": 0,
                        "is_seed": True,
                    } for i, r in enumerate(t["_rel_files"])
                ] if t else []
            )
            self._trace(route, params, 200, 0)
            return self._json(out)
        if route == "torrents/trackers":
            t = sim.torrents.get(params.get("hash"))
            if sim.corpus_mode:
                out = [dict(x) for x in (t.get("_trackers_raw") or [])] if t else []
                self._trace(route, params, 200, 0)
                return self._json(out)
            out = (
                [
                    {
                        "url": t["tracker"],
                        "status": 2,
                        "tier": 0,
                        "num_peers": 0,
                        "num_seeds": 0,
                        "num_leeches": 0,
                        "num_downloaded": 0,
                        "msg": "",
                    }
                ] if t else []
            )
            self._trace(route, params, 200, 0)
            return self._json(out)
        # ---- 计划 §09 补齐的三个路由: 语料档必须实现, 否则 auto-qb 走到的路径会 404 ----
        if route == "sync/torrentPeers":
            h = params.get("hash")
            peers = (sim.corpus.peers.get(h, []) if (sim.corpus_mode and sim.corpus) else [])
            self._trace(route, params, 200, 0)
            return self._json({"rid": 0, "peers": {str(i): p for i, p in enumerate(peers)}, "peers_removed": {}})
        if route == "torrents/pieceHashes":
            # ! 严格模式(rules/actions/checking.py:145-154)把候选与目标的 piece hash **逐项比对**;
            # 按内容集合(排序后的 相对路径+大小)确定性派生, 同组成员天然共享同一列表, 与真机语义一致。
            # 若按 hash 各自随机, 同组成员互不相等 => 严格模式判据恒假(比不测更糟)。
            t = sim.torrents.get(params.get("hash"))
            if t is None:
                self._trace(route, params, 200, 0)
                return self._json([])
            pairs = [(str(f.get("name", "")), int(f.get("size") or 0)) for f in (t.get("_files_raw") or [])]
            if not pairs:
                pairs = [(r, int(t.get("_file_size") or 0)) for r in (t.get("_rel_files") or [])]
            out = piece_hashes_of(pairs)
            self._trace(route, params, 200, 0)
            return self._json(out)
        if route == "torrents/export":
            t = sim.torrents.get(params.get("hash"))
            if t is None:
                self._trace(route, params, 404, 0)
                return self._json({"error": "torrent not found"}, status=404)
            blob = minimal_bencode(str(t.get("name", "x")), int(t.get("size") or 0))
            self.send_response(200)
            self.send_header("Content-Type", "application/x-bittorrent")
            self.send_header("Content-Length", str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)
            self._trace(route, params, 200, len(blob))
            return
        if route == "_fsmock/state":
            # FS mock 的时间源(计划 §07 硬条件③): 由播放器给出"当前磁盘状态", mock 按秒拉取
            payload = sim.fsmock_state()
            self._trace(route, params, 200, 0)
            return self._json(payload)
        if route == "torrents/tags":
            self._trace(route, params, 200, 0)
            return self._json(sorted(sim.tags))
        if route == "torrents/categories":
            self._trace(route, params, 200, 0)
            return self._json({c: {"name": c, "savePath": ""} for c in sorted(sim.categories)})
        if route in ("transfer/info", "transfer/uploadLimit", "transfer/downloadLimit"):
            v = {"transfer/info": sim.server_state(), "transfer/uploadLimit": 0, "transfer/downloadLimit": 0}[route]
            self._trace(route, params, 200, 0)
            return self._json(v)

        self._trace(route, params, 404, 0)
        return self._json({"error": f"unknown endpoint: {route}"}, status=404)


class SimServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, sim):
        self.sim = sim
        super().__init__(addr, Handler)

    def handle_error(self, request, client_address):
        """auto-qb 被终止时连接会被重置 —— 这是预期收尾, 不打栈回溯(否则淹没统计层)"""
        import socket
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, BrokenPipeError, socket.timeout)):
            return
        super().handle_error(request, client_address)


# ---------- B1: 工作根校验 ----------


def prepare_root(root: str) -> tuple[str, str | None]:
    """校验/准备工作根; 返回 (实际 root, fallback 原因或 None)

    B1: 不得是盘根目录; 必须是新建空目录, 或含哨兵 .auto-qb-sim-root 的既有目录。
    """
    drive = os.path.splitdrive(os.path.abspath(root))[0]
    if not drive or os.path.abspath(root) == drive + os.sep:
        raise BoundaryViolation(f"B1: --root 不得是盘根目录: {root}")
    if os.path.exists(root):
        if not os.path.isdir(root):
            raise BoundaryViolation(f"B1: --root 不是目录: {root}")
        if os.listdir(root) and not os.path.exists(os.path.join(root, SENTINEL)):
            raise BoundaryViolation(f"B1: --root 已存在且非空, 但缺哨兵 {SENTINEL} —— 拒绝在非仿真目录上跑删除场景: {root}")
    else:
        try:
            os.makedirs(root, exist_ok=True)
        except OSError as e:
            return None, f"root 不可创建({e}), 回退临时目录"
        with open(os.path.join(root, SENTINEL), "w", encoding="utf-8") as f:
            f.write("auto-qb sim root\n")
    return root, None


def fallback_root() -> str:
    import tempfile
    d = os.path.join(tempfile.gettempdir(), "auto-qb-sim")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, SENTINEL), "w", encoding="utf-8") as f:
        f.write("auto-qb sim root (fallback)\n")
    return d


# ---------- CLI ----------


def parse_spec(s: list[str] | None, arity: int) -> list[tuple]:
    """--delete-torrents 'K:N[:with-files]' / --delete-files 'K:G'"""
    out = []
    for item in (s or []):
        parts = str(item).split(":")
        if len(parts) < arity:
            raise SystemExit(f"格式错误: {item}")
        if arity == 3:
            out.append((int(parts[0]), int(parts[1]), str(parts[2]).lower() in ("1", "true", "yes")))
        else:
            out.append((int(parts[0]), int(parts[1])))
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="qBittorrent WebUI 仿真客户端")
    p.add_argument("--root", default=os.environ.get("AUTOQB_SIM_ROOT") or DEFAULT_ROOT)
    p.add_argument("--run-id", default="")
    p.add_argument("--n", type=int, default=5000)
    p.add_argument("--beat", type=float, default=1.5)
    p.add_argument("--active", type=float, default=0.10)
    p.add_argument("--mode", choices=("churn", "steady"), default="churn")
    p.add_argument("--ramp", type=int, default=0, help="每拍新增种子数; 0=首轮全量")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=0, help="0=随机端口")
    p.add_argument("--duration", type=float, default=0, help="运行秒数; 0=不限")
    p.add_argument("--read-only", action="store_true", help="写端点回 403 但仍记账(dry-run 硬断言)")
    p.add_argument("--abort-after", type=float, default=0, help="N 秒后断连(测重连自愈)")
    p.add_argument("--abort-duration", type=float, default=0, help="断连持续秒数; 0=一直断。到点自动恢复并把 rid 断层(逼客户端走全量自愈)")
    p.add_argument("--delete-torrents", nargs="*", default=[], help="'K:N[:with-files]'")
    p.add_argument("--delete-files", nargs="*", default=[], help="'K:G' 第 K 拍删第 G 个辅种组文件")
    p.add_argument(
        "--redeliver-removed", type=int, default=0, help="第 K 拍把已删 hash 重新投递一次(测幂等: 重复 torrents_removed 不得炸)"
    )
    p.add_argument(
        "--latency-ms",
        type=float,
        default=0,
        help="每个请求的人为延迟(模拟真机上有负载的 qB)。默认 0 —— 本地请求 ~0.5ms 时主循环永远"
        "不饱和, '命令排队 wait_ms' 恒为 0, 真机上'点了要等 2-4s'这类缺陷复现不出来",
    )
    p.add_argument("--fs-materialize", type=int, default=-1, help="-1=全量(默认); 0=不建树")
    p.add_argument("--fs-file-size", type=int, default=4096)
    p.add_argument("--keep-last", type=int, default=10)
    p.add_argument("--emit-config", action="store_true", help="在 run 目录生成匹配的 config.yml")
    # ---- 语料回放(计划 26-09-21-0024 §07/§12: 语料位置与回放 root 全部参数化, 不写死) ----
    p.add_argument(
        "--source",
        default="synthetic",
        help="synthetic(默认, 保留为对照档) | corpus:<dir>(语料目录; 位置显式传入, 不写死)",
    )
    p.add_argument(
        "--fs-mode",
        choices=("mock", "real"),
        default="",
        help="磁盘事实来源: mock(默认, 进程内 FS mock, 不物化任何文件) | real(真建文件树, 仅用于复核 mock)",
    )
    p.add_argument("--fs-root", default="", help="mock 层根目录; 默认 <root>/runs/<run-id>/fs")
    p.add_argument(
        "--command-latency-ms",
        type=float,
        default=750.0,
        help="命令效果对**两个端点**都延后的毫秒数。默认 750 = W0 真机实测(mean 733 / median 751, n=12); "
        "真机实测 Δ(torrents/info − sync/maindata) = +1 ms, 即滞后是 qB 命令处理延迟、两端共享",
    )
    p.add_argument(
        "--maindata-lag-ms",
        type=float,
        default=0.0,
        help="sync/maindata 相对 torrents/info 的**额外**滞后(默认 0 = W0 实测)。"
        "计划原文默认 1500 并假设 info 更快, W0 实测推翻了该前提; 调大它可做'直查更快'的受控实验(红验落点)",
    )
    p.add_argument("--replay-speed", type=float, default=1.0, help="录播回放倍速(W4)")
    p.add_argument(
        "--latency-mode",
        choices=("recorded", "p50", "p95", "const"),
        default="recorded",
        help="延迟注入方式: recorded(默认, 用录到的真实 rtt) | p50/p95 | const:N(--latency-ms)",
    )
    p.add_argument("--self-test", action="store_true", help="跑内置自检(真实 qbittorrent-api 往返)")
    return p


def make_run_dir(root: str, run_id: str) -> str:
    if not run_id:
        run_id = time.strftime("%Y%m%d-%H%M%S") + "-run"
    d = os.path.join(root, "runs", run_id)
    os.makedirs(d, exist_ok=True)
    return d


def prune_runs(root: str, keep: int) -> int:
    runs = os.path.join(root, "runs")
    if not os.path.isdir(runs) or keep <= 0:
        return 0
    items = sorted(os.listdir(runs))
    removed = 0
    for name in items[:-keep]:
        p = os.path.join(runs, name)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
            removed += 1
    return removed


CONFIG_TMPL = """---
config:
    interval: {interval}S
    main_tick: {tick}S
    max_tasks_per_tick: {max_tasks}
    state_file: "{state_file}"
    remove_similar_tags: false
    skip_checking_tag: {skip_checking_tag}
    hr:
        add_tag: ""
        add_category: "!!HR${{required_seeding_time}}!!"
        overwrite_category: false
        add_tag_for_satisfied: ""
        add_category_for_satisfied: --HR${{required_seeding_time}}--
        overwrite_category_for_satisfied: false
    grouping:
        enabled: true
        missing_tag: {missing_tag}
        check_missing_files: true
    qbittorrent:
        host: "{host}"
        port: "{port}"
        username: "{user}"
        password: "{password}"
    log:
        level: INFO
        file: "{log_file}"
        max_bytes: 50MiB
{web}{rules}    trackers:
{trackers}
"""

WEB_TMPL = """    web:
        enabled: true
        host: "127.0.0.1"
        port: {web_port}
        token: "sim-token"
        skip_local_verify: true
"""

# D5 幂等用: execute_once=once 的规则 + 无副作用的 print_torrent_details 动作。
# 它会在 state.json 的 exec_history 里给每个命中种子留一条记录 —— 第二相(新进程)必须
# 靠这条记录跳过, 一个都不许重跑。state 若没落盘, 第二相就会全部重跑 -> 判据立刻变红。
# ❗规则块必须落在 config: **之内**且键名以 _rules 结尾 —— validate_config 的
# rules_config = {k: v for k, v in cfg.items() if k.endswith("_rules")}; 根节点只认 config。
# (test_stop.yml 里那种顶层写法是旧格式, 现在会被判"根节点未知键")
RULES_TMPL = """    sim_once_rules:
        rule:
            enabled: true
            trigger: interval
            interval: 15S
            execute_once: once
            cooldown: 0S
            conditions:
                - trackers:
                      - ptfans_cc
            actions:
                - print_torrent_details: true
            stop_following_rules_if:
                never
"""

TRACKER_RULES_TMPL = """            rules:
                - "@sim_once_rules.rule"
"""

SYNTHETIC_TRACKERS = """        ptfans_cc:
            domains:
                - ptfans.cc
            tags:
                - PTFans
{rules}        hhanclub:
            domains:
                - tracker.hhanclub.net
            tags:
                - HHan
"""

# 非站点标签(自动生成的通用标签), 派生"站点标签"时要排除掉
_GENERIC_TAG_HINTS = ("MISSING", "zSkipChecked", "辅种", "R")


def corpus_tracker_section(sim: SimQb) -> str:
    """按语料里的真实数据派生 tracker 段(计划 §12 / W3)

    为什么必须派生: 语料里的 tracker 域名已被脱敏成 `site-N.example`、标签也已伪名化。
    若沿用合成档写死的 `ptfans.cc` / `hhanclub`, auto-qb 的站点匹配会全部落空 ⇒
    `tracker_name` 解析不出来 ⇒ 依赖站点的规则与日志全是空转。

    站点标签的推断 —— 取"**对该 host 最专有**"的那个标签: score = 该站出现次数 / 全局出现次数。
    真机上站点标签几乎只出现在本站的种子上(score→1), 而通用标签(MISSING / zSkipChecked / 辅种)
    散布在全库(score 很小)。⇒ 不能按"出现最多"挑, 那会被通用标签抢走。
    (⚠ 标签在语料里已伪名化, 所以**不能**用原始字面量 "MISSING" 之类去排除 —— 只能靠这个统计判据。)

    ⚠ 首选 `meta.sanitize_map.tracker_tags`: 抓取端拿用户 config 的 trackers 段算出来的**权威**
    伪域名 ↔ 伪标签映射; 取不到才退回上面的统计派生。两者都只产出**已脱敏**的两侧。
    """
    # ❗`or {}`: 老语料 / 无映射时 `.get()` 返回 None, 后面再 .get() 会直接 AttributeError
    _corpus = getattr(sim, "corpus", None)
    smap = ((_corpus.meta.get("sanitize_map") or {}) if _corpus else {}) or {}
    auth = smap.get("tracker_tags") or {}
    host_tags: dict[str, dict[str, int]] = {}
    tag_global: dict[str, int] = {}
    for h, t in sim.torrents.items():
        tags = [x.strip() for x in str(t.get("tags") or "").split(",") if x.strip()]
        for tag in tags:
            tag_global[tag] = tag_global.get(tag, 0) + 1
        for tr in (t.get("_trackers_raw") or []):
            url = str(tr.get("url") or "")
            if "://" not in url:
                continue
            host = url.split("://", 1)[1].split("/", 1)[0].split(":", 1)[0]
            if not host:
                continue
            slot = host_tags.setdefault(host, {})
            for tag in tags:
                slot[tag] = slot.get(tag, 0) + 1

    # ---- 输出: 权威映射优先, 覆盖不到的域名退回统计派生, 且只输出语料里真出现过的域名 ----
    # ❗**不能只信权威映射**: 用户 config 的 `domains:` 字面量与 tracker URL 的 **host 不一定相等**
    #   (auto-qb 的站点匹配是**后缀**匹配, 而这里按 host 精确对表)。实测该映射漏掉了语料里最大的
    #   站点(35 个种子) ⇒ 那些种子因"未匹配 tracker 配置"被 `continue` 跳过(qbmanager.py:685-690),
    #   **连带不参与归组** ⇒ 头号判据 group_exact 从 0 变成 34(真值 63 组只分出 29 组)。
    # ❗也**不能只信统计**: 站点混用标签时统计会挑错。故**两者合并**: 有权威就用, 没有才统计。
    stat_tag: dict[str, str] = {}
    for host in host_tags:
        counts = host_tags[host]
        best, best_score = None, -1.0
        for tag, n in sorted(counts.items()):
            score = n / max(tag_global.get(tag, 1), 1)
            if score > best_score or (score == best_score and best is not None and n > counts.get(best, 0)):
                best, best_score = tag, score
        if best:
            stat_tag[host] = best
    if not stat_tag and not auth:
        return SYNTHETIC_TRACKERS.format(rules="")
    lines = []
    for host in sorted(stat_tag):
        tag = None
        if host in auth:
            cand = [t for t in (auth[host] or []) if t]
            if cand:
                tag = cand[0]
        if tag is None:
            tag = stat_tag[host]
        key = host.replace(".", "_").replace("-", "_")
        lines.append(
            f"""        {key}:
            domains:
                - {host}
            tags:
                - {tag}
"""
        )
    return "".join(lines) if lines else SYNTHETIC_TRACKERS.format(rules="")


def emit_config(
    run_dir: str, sim: SimQb, port: int, web_port: int = 0, with_rules: bool = False, interval: int = 60
) -> str:
    """生成与仿真端匹配的 auto-qb 配置

    web_port > 0 时开启 auto-qb 自带 WEB UI(D3: 测 auto-qb 主动删除的唯一真实路径;
    skip_local_verify=true 让 loopback 免密钥, 驱动器可直接投递命令)。默认不开 ——
    保持"默认配置不额外开面"的保守默认。

    with_rules 时注入一条 execute_once=once 的规则, 供 D5 验跨进程幂等(默认不注入,
    免得给性能场景掺进规则求值成本)。
    """
    data_dir = os.path.join(run_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    p = os.path.join(run_dir, "config.yml")
    # 语料档: tracker 段必须按语料里的实际域名/标签派生(域已脱敏成 site-N.example), 否则站点匹配全落空
    if getattr(sim, "corpus_mode", False):
        trackers = corpus_tracker_section(sim)
    else:
        trackers = SYNTHETIC_TRACKERS.format(rules=TRACKER_RULES_TMPL if with_rules else "")
    # 语料档: auto-qb 自有标签字面量(MISSING / zSkipChecked)在语料里**已被伪名化**,
    # 必须换成对应伪名 —— 否则跳检/缺文件的行为与真机不一致(该跳的没跳, 判据全绿也是假的)。
    known = {}
    if getattr(sim, "corpus_mode", False) and sim.corpus is not None:
        known = (sim.corpus.meta.get("sanitize_map") or {}).get("known_tags") or {}
    with open(p, "w", encoding="utf-8") as f:
        f.write(
            CONFIG_TMPL.format(
                interval=interval,
                tick=2,
                max_tasks=20,
                state_file=os.path.join(data_dir, "state.json").replace("\\", "/"),
                host=sim.args.host,
                port=port,
                user="sim",
                password="sim",
                log_file=os.path.join(data_dir, "autoqb.log").replace("\\", "/"),
                web=WEB_TMPL.format(web_port=web_port) if web_port else "",
                rules=RULES_TMPL if with_rules else "",
                trackers=trackers,
                skip_checking_tag=known.get("zSkipChecked", "zSkipChecked"),
                missing_tag=known.get("MISSING", "MISSING"),
            )
        )
    return p


def run_load_engine(sim: SimQb, stop: threading.Event):
    """按 beat 变异; abort-after 到点后置 _abort 断连"""
    start = time.time()
    while not stop.is_set():
        stop.wait(sim.args.beat)
        if stop.is_set():
            break
        sim.pump()
        a = sim.args
        if not a.abort_after:
            continue
        if not sim._abort and not sim._abort_done and time.time() - start >= a.abort_after:
            sim._abort = True
            sim._abort_done = True
            sim._abort_until = time.time() + (a.abort_duration or 1e9)
            sim._event("abort_start", {"duration_s": a.abort_duration})
        elif sim._abort and time.time() >= sim._abort_until:
            sim._abort = False
            # ❗恢复时把 rid 断层(模拟 qB 重启): 客户端手上的旧 rid 必然失配 -> 走全量自愈。
            # 不这么做的话 rid 只是暂停推进, 恢复后仍是增量, 测不到"全量重建"这条路径。
            sim.rid += 1000
            sim._event("abort_recover", {"rid": sim.rid})
    return


def create_sim(args) -> tuple[SimQb, SimServer]:
    """构造仿真端(供 sim_qb 主流程与 sim_run 驱动器共用)"""
    root, why = prepare_root(args.root)
    fallback = None
    if root is None:
        root = fallback_root()
        fallback = why
    args.root = root
    args.run_dir = make_run_dir(root, args.run_id)
    sim = SimQb(args)
    if fallback:
        sim.violations.append(f"ROOT_FALLBACK: {fallback}")
        print(f"[WARN] {fallback} -> {root}", file=sys.stderr)
    return sim, SimServer((args.host, args.port), sim)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    args.delete_torrents = parse_spec(args.delete_torrents, 3)  # K:N[:with-files]
    args.delete_files = parse_spec(args.delete_files, 2)  # K:G

    sim, srv = create_sim(args)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    print(
        f"[sim] 监听 {args.host}:{port} | 种子 {len(sim.torrents)} | 物化文件 "
        f"{sim._materialized} | 辅种组 {len(sim.groups)} | run={args.run_dir}"
    )

    cfg = emit_config(args.run_dir, sim, port) if args.emit_config else None
    if cfg:
        print(f"[sim] 配置已生成: {cfg}")

    if args.self_test:
        rc = self_test(sim, srv, port)
        srv.shutdown()
        return rc

    stop = threading.Event()
    t = threading.Thread(target=run_load_engine, args=(sim, stop), daemon=True)
    t.start()
    try:
        if args.duration:
            time.sleep(args.duration)
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        srv.shutdown()
        s = sim.summary()
        with open(os.path.join(args.run_dir, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
        print(json.dumps(s, ensure_ascii=False, indent=2))
        pruned = prune_runs(args.root, args.keep_last)
        if pruned:
            print(f"[sim] 清理旧运行目录 {pruned} 个")
    return 0


# ---------- 自检: 真实 qbittorrent-api 往返 ----------


def self_test(sim: SimQb, srv: SimServer, port: int) -> int:
    try:
        import qbittorrentapi
    except ImportError:
        print("[自检] 未安装 qbittorrentapi, 跳过")
        return 0
    cli = qbittorrentapi.Client(host=sim.args.host, port=port, username="sim", password="sim")
    ok = True

    t0 = time.perf_counter()
    d = cli.sync_maindata(rid=0)
    t_full = (time.perf_counter() - t0) * 1000
    got = len(d.get("torrents", {}))
    print(f"[自检] 全量  rid=0      : {t_full:7.1f} ms, {got} 种子 (期望 {len(sim.torrents)})")
    print(f"[自检] rid 往返         : 库收到 d['rid']={d.get('rid')!r}, 服务端 last_sent={sim.rid}")
    ok &= got == len(sim.torrents)

    # 缺字段校验: 首轮全量必须含全部 REQUIRED_TORRENT_FIELDS
    sample = next(iter(d["torrents"].values())) if got else {}
    need = (
        "hash name save_path content_path size total_size tags category state downloaded uploaded "
        "dlspeed upspeed seeding_time ratio amount_left completed progress dl_limit up_limit added_on "
        "seq_dl f_l_piece_prio ratio_limit seeding_time_limit inactive_seeding_time_limit "
        "share_limit_action"
    ).split()
    miss = [f for f in need if f not in sample]
    print(f"[自检] 必需字段         : 缺 {miss if miss else '无'}")
    ok &= not miss

    sim.pump()  # 制造一拍变化
    t0 = time.perf_counter()
    d2 = cli.sync_maindata(rid=d.get("rid") or 0)
    t_inc = (time.perf_counter() - t0) * 1000
    print(
        f"[自检] 增量  rid={d.get('rid')}     : {t_inc:7.1f} ms, {len(d2.get('torrents', {}))} 条 "
        f"(full_update={d2.get('full_update')})"
    )
    ok &= (len(d2.get("torrents", {})) > 0 and not d2.get("full_update"))

    # files: 单个请求 + 路径/大小必须与磁盘一致
    h0 = next(iter(sim.torrents))
    files = cli.torrents_files(hash=h0)
    p = os.path.normpath(os.path.join(sim.torrents[h0]["save_path"], files[0]["name"].replace("\\", os.sep)))
    exists = os.path.exists(p) and os.path.getsize(p) == files[0]["size"]
    print(f"[自检] files 与磁盘一致 : {exists} ({p})")
    ok &= exists

    # B2 逃逸: 已**下沉**进 tests/test_sim_corpus.py::test_safe_delete_rejects_path_outside_fs_root
    # (本自检要真起 HTTP + 真装 qbittorrentapi, CI 从不执行 ⇒ 交给 pytest 验, 覆盖两平台)

    # B3 数量上限
    try:
        sim.safe_delete_files(sim.file_paths_of(sim.torrents[h0]), 0)
        print("[自检] B3 数量上限      : 未拦截 ✗")
        ok = False
    except BoundaryViolation:
        print("[自检] B3 数量上限      : 已拦截 ✓")

    # 删除文件(D4 注入)后, 磁盘上确实消失
    if sim.groups:
        before = len(sim._walk())
        sim.delete_group_files(0)
        after = len(sim._walk())
        print(f"[自检] D4 删组文件      : {before} -> {after} ✓")
        ok &= after < before

    srv.shutdown()
    print("[自检] " + ("全部通过 ✓" if ok else "存在失败 ✗"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
