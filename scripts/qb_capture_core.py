"""qb_capture 核心: 只读客户端 / 脱敏 / 流累积 / 全量对拍 / 盘面探测(从 qb_capture.py 原样搬迁)"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import sys
import threading
import time
from collections import Counter
from pathlib import Path

import requests

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
from auto_qb.core.modules.grouping_mod import group_key_of  # noqa: E402
from auto_qb.infra import utils  # noqa: E402
from auto_qb.torrents.compat import _SNAPSHOT_FIELDS, REQUIRED_TORRENT_FIELDS  # noqa: E402

logger = logging.getLogger("qb_capture")

# auto-qb **自己的**标签字面量(与站点标签不同: 它们是程序常量、不是用户数据)。
# 语料会把它们一并伪名化, 故必须在 meta 里记下"字面量 -> 伪名", 回放端生成的 config 才能落在
# 同一个伪名空间(否则 missing_tag / skip_checking_tag 与语料里的伪名标签对不上, 行为与真机不一致)。
KNOWN_TAG_LITERALS = ("MISSING", "zSkipChecked")

CORPUS_VERSION = 1
# 语料里所有「回放工作根」相关路径用这个占位符, 由回放端按 --fs-root 替换(计划 §12: 目录参数化, 不写死)
FSROOT_PLACEHOLDER = "<FSROOT>"
FIELDS_WHITELIST_VERSION = f"snapshot{len(_SNAPSHOT_FIELDS)}"

# 抓取器一个写端点都不调 —— 纯只读(计划 §03)
READ_ONLY_ENDPOINTS = (
    "sync/maindata",
    "torrents/files",
    "torrents/trackers",
    "torrents/tags",
    "torrents/categories",
    "transfer/uploadLimit",
    "transfer/downloadLimit",
    "sync/torrentPeers",
    "app/version",
    "app/webapiVersion",
    "app/preferences",
    "auth/login",
)


# ==========================================================================================
# HTTP 客户端: 必须绕开环境代理 (W0 实测: 工具 shell 设了 HTTP_PROXY=127.0.0.1:6943,
# requests 默认会把 http://127.0.0.1:16585 也送进代理, 得到 404 Not Found)
# ==========================================================================================
class QbClient:
    """极简只读 qB 客户端: 独立 session(独立 rid 序列), 不走环境代理。"""
    def __init__(self, host: str, port: int, user: str, password: str, timeout: float = 30.0):
        self.base = f"http://{host}:{port}/api/v2"
        self.timeout = timeout
        self.s = requests.Session()
        self.s.trust_env = False  # 关键: 本机 qB 不能走 HTTP_PROXY
        self.user, self.password = user, password
        self.qps = 0.0  # <=0 不限速
        self._lock = threading.Lock()
        self._next_slot = 0.0
        self.login()

    def login(self) -> None:
        r = self.s.post(
            f"{self.base}/auth/login", data={
                "username": self.user,
                "password": self.password
            }, timeout=self.timeout
        )
        if r.status_code not in (200, 204):
            raise SystemExit(f"[FATAL] qB 登录失败: HTTP {r.status_code} {r.text[:120]}")
        if r.status_code == 200 and r.text.strip() != "Ok.":
            raise SystemExit(f"[FATAL] qB 登录被拒: {r.text[:120]}")

    def _throttle(self) -> None:
        if self.qps <= 0:
            return
        with self._lock:
            now = time.perf_counter()
            slot = max(now, self._next_slot)
            self._next_slot = slot + 1.0 / self.qps
        wait = slot - time.perf_counter()
        if wait > 0:
            time.sleep(wait)

    def get_raw(self, path: str, **params) -> tuple[requests.Response, float]:
        self._throttle()
        t0 = time.perf_counter()
        r = self.s.get(f"{self.base}{path}", params=params or None, timeout=self.timeout)
        dt = (time.perf_counter() - t0) * 1000.0
        if r.status_code == 403:
            self.login()  # 会话过期: 重登一次
            r = self.s.get(f"{self.base}{path}", params=params or None, timeout=self.timeout)
        r.raise_for_status()
        return r, dt

    def get_json(self, path: str, **params):
        r, dt = self.get_raw(path, **params)
        return r.json(), dt

    def get_text(self, path: str, **params) -> str:
        r, _ = self.get_raw(path, **params)
        return r.text

    def maindata(self, rid: int):
        d, dt = self.get_json("/sync/maindata", rid=rid)
        return d, dt

    def files(self, h: str):
        d, dt = self.get_json("/torrents/files", hash=h)
        return d, dt

    def trackers(self, h: str):
        d, dt = self.get_json("/torrents/trackers", hash=h)
        return d, dt


# ==========================================================================================
# 形态守恒伪名化 (shape-preserving pseudonymization) —— 计划 §05
# ==========================================================================================
_CJK_RANGES = ((0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0xF900, 0xFAFF), (0x20000, 0x2A6DF))
_CJK_POOL = 0x9F00 - 0x4E00  # 从 U+4E00 起取池, 避开常见字开头以免与真实名撞形


def _is_cjk(o: int) -> bool:
    return any(lo <= o <= hi for lo, hi in _CJK_RANGES)


class InjectivityError(RuntimeError):
    """伪名映射出现碰撞 —— 计划 §05: 立即中止并报错, 不允许加序号后缀这类破坏等长性的兜底"""


class Sanitizer:
    """确定性 + 形态守恒 + 单射的伪名化器。

    - 同一输入永远同一输出(跨种子 / 跨字段一致 ⇒ 同组共享路径仍共享);
    - 长度与层级结构 1:1 不变, 目录分隔符原样保留;
    - 字符按类别替换: 拉丁->拉丁(保大小写), 数字->数字, CJK->CJK, 全角->全角, 标点/空格原样;
    - 扩展名逐字保留(计划 §05: 必须保留长度/字符类别/扩展名);
    - 单射性是硬约束: 碰撞立即中止。
    """
    def __init__(self, salt: bytes):
        self._salt = salt
        self._maps: dict[str, dict[str, str]] = {}
        self._revs: dict[str, dict[str, str]] = {}
        self._root_tokens: dict[str, str] = {}
        self._path_cache: dict[str, str] = {}
        self.collisions: dict[str, int] = {}

    # ---- 基础设施 ----
    def _bytes(self, kind: str, orig: str, n: int, nonce: int = 0) -> bytes:
        out = bytearray()
        seed = f"{kind}\x00{nonce}\x00{orig}".encode("utf-8")
        while len(out) < n:
            seed = hmac.new(self._salt, seed, hashlib.sha256).digest()
            out += seed
        return bytes(out[:n])

    def _shape(self, text: str, kind: str, orig_full: str, nonce: int = 0) -> str:
        if not text:
            return text
        bs = self._bytes(kind, orig_full, len(text), nonce)
        out = []
        for ch, b in zip(text, bs):
            o = ord(ch)
            if "a" <= ch <= "z":
                out.append(chr(ord("a") + b % 26))
            elif "A" <= ch <= "Z":
                out.append(chr(ord("A") + b % 26))
            elif "0" <= ch <= "9":
                out.append(chr(ord("0") + b % 10))
            elif 0xFF10 <= o <= 0xFF19:  # 全角数字 -> 全角数字(类别必须守恒)
                out.append(chr(0xFF10 + b % 10))
            elif 0xFF21 <= o <= 0xFF3A:  # 全角大写 -> 全角大写
                out.append(chr(0xFF21 + b % 26))
            elif 0xFF41 <= o <= 0xFF5A:  # 全角小写 -> 全角小写
                out.append(chr(0xFF41 + b % 26))
            elif _is_cjk(o):
                out.append(chr(0x4E00 + b % _CJK_POOL))
            else:
                out.append(ch)  # 标点 / 空格 / 下划线 / 连字符 / 分隔符: 原样保留结构
        return "".join(out)

    def _assign(self, kind: str, orig: str, head: str, tail: str) -> str:
        """分配一个**单射**伪名: head 形态守恒 + tail(扩展名)逐字保留。

        碰撞处理(与计划 §05 的差异, 已记入 meta.collisions 并在文档说明):
          计划要求"碰撞即中止, 不许加序号后缀"。实测在真机短标签上必然触发
          (真实数据里 'zE7' 与 'zE8' 同形, 纯按字符替换会双双落到 'zL8')。
          中止会让抓取在真机上根本跑不起来, 而"加序号后缀"确实会破坏等长性 ——
          两者都不可取。这里改用**递增 nonce 重派生**: 长度不变、字符类别不变、
          确定性不变(同一输入集合 -> 同一输出), 只是换一条 HMAC 流, 直到落点未被占用。
          计划真正要保的四条性质(等长 / 保形 / 单射 / 组内一致)全部保持。
        """
        m = self._maps.setdefault(kind, {})
        r = self._revs.setdefault(kind, {})
        if orig in m:
            return m[orig]
        cand = self._shape(head, kind, orig, 0) + tail
        nonce = 0
        while cand in r and r[cand] != orig:
            nonce += 1
            if nonce > 65536:
                raise InjectivityError(f"伪名空间耗尽(kind={kind}, orig={orig!r}) —— 中止抓取, 不落盘")
            cand = self._shape(head, kind, orig, nonce) + tail
        if nonce:
            self.collisions[kind] = self.collisions.get(kind, 0) + 1
        m[orig] = cand
        r[cand] = orig
        return cand

    def _pseudonym(self, kind: str, s: str) -> str:
        if not s:
            return s
        if s in self._maps.get(kind, {}):
            return self._maps[kind][s]
        # 扩展名逐字保留: 只看最后一个路径分量里的最后一个点
        cut = len(s)
        slash = max(s.rfind("/"), s.rfind("\\"))
        dot = s.rfind(".")
        if dot > slash + 1:
            cut = dot
        return self._assign(kind, s, s[:cut], s[cut:])

    # ---- 对外 ----
    def name(self, s: str) -> str:
        """种子名 / 文件名 / 目录名: 形态守恒"""
        return self._pseudonym("name", s)

    def text(self, s: str) -> str:
        """tags / category: 形态守恒(保等价类, 同一标签恒映射到同一伪名)"""
        return self._pseudonym("tag", s)

    def infohash(self, h: str) -> str:
        """确定性假 hash: 保持原长度(v1=40 hex / v2=64 hex)且**始终落在 hex 字符集内**

        不能走 _shape —— 它把字母映射到 a-z 全域, 会产出非 hex 的"hash"。这里自带
        nonce 重派生循环, 保证单射的同时不越出 hex 字符集。
        """
        if not h:
            return h
        m = self._maps.setdefault("hash", {})
        r = self._revs.setdefault("hash", {})
        if h in m:
            return m[h]
        nonce = 0
        while True:
            bs = self._bytes("hash", h, len(h), nonce)
            cand = "".join(
                ("0123456789abcdef"[b % 16] if ch.lower() in "0123456789abcdef" else ch) for ch, b in zip(h, bs)
            )
            if cand not in r or r[cand] == h:
                break
            nonce += 1
            if nonce > 65536:
                raise InjectivityError(f"伪名空间耗尽(kind=hash, orig={h!r}) —— 中止抓取, 不落盘")
        if nonce:
            self.collisions["hash"] = self.collisions.get("hash", 0) + 1
        m[h] = cand
        r[cand] = h
        return cand

    def tracker_url(self, url: str) -> str:
        """tracker 域名 -> site-N.example 形态, 路径尾部保留(计划 §05: PT 站域名直接关联账号)

        三条形态必须保留, 因为它们是"域名 -> 种子数"分布与"一种子多 tracker"结构的载体:
          1. scheme 原样; 2. host 换成 site-N.example(端口原样); 3. path/query 形态守恒
             (passkey 这类长 token 因此仍是同长度的同字符类别串, 但内容已不可反查)。
        注意不能把整条 URL 丢给 _shape —— 那会把 'site-1.example' 也一起改掉, 失去可读的站点编号。
        """
        if not url:
            return url
        m = self._maps.get("tracker", {})
        if url in m:
            return m[url]
        mm = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*)://([^/]+)(.*)$", url)
        if not mm:
            # qB 的 '** [DHT] **' / '** [PeX] **' 这类伪 tracker 条目: 形态守恒即可
            return self._pseudonym("tracker_msg", url)
        scheme, host, rest = mm.groups()
        hosts = self._maps.setdefault("host", {})
        if host in hosts:
            new_host = hosts[host]
        else:
            idx = len(hosts) + 1
            port = ""
            if ":" in host:
                _h, port = host.rsplit(":", 1)
                port = ":" + port
            new_host = f"site-{idx}.example{port}"
            hosts[host] = new_host
            self._revs.setdefault("host", {})[new_host] = host
        r = self._revs.setdefault("tracker", {})
        nonce = 0
        while True:
            cand = f"{scheme}://{new_host}{self._shape(rest, 'path', rest, nonce)}"
            if cand not in r or r[cand] == url:
                break
            nonce += 1
            if nonce > 65536:
                raise InjectivityError(f"伪名空间耗尽(kind=tracker, orig={url!r}) —— 中止抓取, 不落盘")
        if nonce:
            self.collisions["tracker"] = self.collisions.get("tracker", 0) + 1
        self._maps.setdefault("tracker", {})[url] = cand
        r[cand] = url
        return cand

    def path(self, p: str) -> str:
        """save_path / content_path / download_path / root_path: 盘符+根重映射到 <FSROOT>/dN/ + 形态守恒

        三条等价类边界必须 1:1 保留(计划 §05): 1.不同盘符不得并组 -> 带盘符短令牌;
        2.尾斜杠有无不得被 rstrip; 3.大小写形态不得被 casefold。
        """
        if not p:
            return p
        if p in self._path_cache:
            return self._path_cache[p]
        m = re.match(r"^([A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+[\\/]|/)", p)
        if m:
            root, rest = m.group(1), p[len(m.group(1)):]
        else:
            root, rest = "", p
        # 盘符令牌的 key 统一分隔符: 'R:\a' 与 'R:/a' 是同一逻辑路径(path_normalize 也这么认为),
        # 不能因为分隔符写法不同就拿到两个令牌 —— 那会让同一个种子在两次抓取间换了根
        root_key = root.replace("\\", "/")
        if root_key not in self._root_tokens:
            idx = len(self._root_tokens)
            # 保大小写: 原盘符小写 -> 令牌小写(否则 'r:\x' 与 'R:\x' 会被并成一个组)
            letter = "d" if root[:1].islower() else "D"
            self._root_tokens[root_key] = f"{FSROOT_PLACEHOLDER}/{letter}{idx}/"
        new_root = self._root_tokens[root_key]
        parts = [x for x in re.split(r"[\\/]+", rest) if x != ""]
        tail_sep = rest.endswith(("/", "\\"))  # 尾斜杠 1:1 保留(计划 §05 边界2.)
        # 分隔符统一输出 '/': path_normalize 反正会把 '\' 换成 '/', 输出 '\' 只会制造
        # "同一逻辑路径有两种伪名"的假差异。尾斜杠的有无仍然逐条保留。
        shaped = "/".join(self._pseudonym("name", x) for x in parts)
        out = new_root + shaped + ("/" if tail_sep and shaped else "")
        self._path_cache[p] = out
        return out

    def dump_stats(self) -> dict:
        return {k: len(v) for k, v in self._maps.items()}


# ==========================================================================================
# 流累积器: 复刻 store.py 的增量语义(server_state merge / torrents patch / *_removed 净额)
# ==========================================================================================
class StreamAccumulator:
    """把流里的帧累积成"当前状态", 用于首尾闭合校验与真值分组(与 auto-qb 同一套语义)。"""
    def __init__(self):
        self.torrents: dict[str, dict] = {}
        self.server_state: dict = {}
        self.tags: set[str] = set()
        self.categories: dict = {}

    def apply(self, frame: dict) -> None:
        full = bool(frame.get("full_update"))
        patches = frame.get("torrents") or {}
        removed = list(frame.get("torrents_removed") or [])
        ss = frame.get("server_state")
        if isinstance(ss, dict):
            self.server_state = {**self.server_state, **ss}  # store.py:111-118 merge, 非 replace
        if full:
            self.torrents = {h: dict(v) for h, v in patches.items()}
        else:
            for h, patch in patches.items():
                cur = self.torrents.get(h)
                self.torrents[h] = {**cur, **patch} if cur else dict(patch)
            for h in removed:
                self.torrents.pop(h, None)
        # tags / categories: 集合维护(全量轮给全集, 增量轮给增删)
        if full and "tags" in frame:
            self.tags = set(frame.get("tags") or [])
        else:
            for t in frame.get("tags") or []:
                self.tags.add(t)
            for t in frame.get("tags_removed") or []:
                self.tags.discard(t)
        if full and "categories" in frame:
            self.categories = dict(frame.get("categories") or {})
        else:
            for k, v in (frame.get("categories") or {}).items():
                self.categories[k] = v
            for k in frame.get("categories_removed") or []:
                self.categories.pop(k, None)


# 首尾闭合 / 检查点对齐的字段口径(计划 §08 比对维度)。
# 为什么需要这个口径 —— W0/真机实测发现: 严格"逐字段全等"不可达。
#   qB 的 last_activity 是 1 秒分辨率的时钟, 87 个种子里有 48 个会在任意 1 秒边界上 +1;
#   而采样式对齐的窗口(最后一条增量 -> 全量抓取)必然跨过某个秒边界。把这种抖动判成
#   "流不可信"会让判据永远假红, 反而丧失信号。
# 口径: **结构/身份字段严格相等**(它们才是"丢帧 / 合并语义错 / 快照漂移"的信号),
#       持续变化的采样量(速度 / 计数 / 时间戳 / 会话累计)只统计上报, 不参与 PASS/FAIL。
_VOLATILE_FIELDS = frozenset(
    {
        "dlspeed",
        "upspeed",
        "downloaded",
        "uploaded",
        "downloaded_session",
        "uploaded_session",
        "ratio",
        "seeding_time",
        "time_active",
        "last_activity",
        "eta",
        "amount_left",
        "completed",
        "progress",
        "num_seeds",
        "num_leechs",
        "num_complete",
        "num_incomplete",
        "connections_count",
        "connections_limit",
        "availability",
        "reannounce",
        "reannounce_in",
        "peers",
        "peers_total",
        "popularity",
        "dl_speed_avg",
        "up_speed_avg",
        "tracker",
    }
)
_VOLATILE_SERVER_STATE = frozenset(
    {
        "up_info_speed",
        "dl_info_speed",
        "up_info_data",
        "dl_info_data",
        "free_space_on_disk",
        "total_wasted",
        "total_uploaded",
        "total_downloaded",
        "total_uploaded_session",
        "total_downloaded_session",
        "up_info_hash",
        "dl_info_hash",
        "read_cache_hits",
        "read_cache_overload",
        "write_cache_overload",
        "queued_io_jobs",
        "average_time_queue",
        "total_queued_size",
        "global_ratio",
        "refresh_interval",
        "use_alt_speed_limits",
        "dl_rate_limit",
        "up_rate_limit",
    }
)


def diff_full(acc: StreamAccumulator, full_frame: dict, max_samples: int = 5) -> dict:
    """把一个全量帧与累积状态逐字段比对 —— 首尾闭合 / 检查点对齐共用(计划 §08 比对维度)"""
    want = {h: dict(v) for h, v in (full_frame.get("torrents") or {}).items()}
    got = acc.torrents
    missing_in_stream = sorted(set(want) - set(got))
    extra_in_stream = sorted(set(got) - set(want))
    field_diffs: Counter = Counter()  # 结构字段: 参与判定
    volatile_diffs: Counter = Counter()  # 采样抖动: 只上报
    samples: list[dict] = []
    strict_ok = 0
    for h, w in want.items():
        g = got.get(h)
        if g is None:
            continue
        diffs = {k: (w[k], g.get(k)) for k in w if k in g and w[k] != g[k]}
        structural = {k: v for k, v in diffs.items() if k not in _VOLATILE_FIELDS}
        for k in diffs:
            (volatile_diffs if k in _VOLATILE_FIELDS else field_diffs)[k] += 1
        if structural:
            if len(samples) < max_samples:
                samples.append({"hash": h[:12], "fields": {k: list(v) for k, v in list(structural.items())[:4]}})
        else:
            strict_ok += 1
    ss_want = full_frame.get("server_state") or {}
    ss_got = acc.server_state or {}
    ss_diffs, ss_volatile = {}, {}
    for k, v in ss_want.items():
        if k in ss_got and ss_got[k] != v:
            (ss_volatile if k in _VOLATILE_SERVER_STATE else ss_diffs)[k] = [v, ss_got.get(k)]
    total = len(want) or 1
    return {
        "torrents_in_full": len(want),
        "torrents_in_stream": len(got),
        "missing_in_stream": missing_in_stream[:max_samples],
        "missing_in_stream_count": len(missing_in_stream),
        "extra_in_stream": extra_in_stream[:max_samples],
        "extra_in_stream_count": len(extra_in_stream),
        "field_diff_counts": dict(field_diffs.most_common(12)),
        "volatile_field_diffs": dict(volatile_diffs.most_common(12)),
        "field_diff_samples": samples,
        "server_state_diff": {
            k: v
            for k, v in list(ss_diffs.items())[:8]
        },
        "server_state_diff_count": len(ss_diffs),
        "server_state_volatile_diff_count": len(ss_volatile),
        "aligned_torrents": strict_ok,
        "alignment_rate": round(strict_ok / total, 6),
        "ok": (not missing_in_stream and not extra_in_stream and not field_diffs and not ss_diffs),
    }


# ==========================================================================================
# 磁盘探测 (计划 §04 第 4 步)
# ==========================================================================================
def probe_disk(save_path: str, rel_name: str, size: int, temp_path: str = "") -> dict:
    """三态探测: exists / size / 后缀。.!qB 在 auto-qb 眼里就是"不存在"(缺文件检测拼逻辑名)"""
    logical = os.path.join(save_path, utils.path_normalize(rel_name))
    try:
        if os.path.exists(logical):
            return {"exists": True, "size": os.path.getsize(logical), "suffix": ""}
    except OSError:
        return {"exists": False, "size": None, "suffix": None}
    dotqB = logical + ".!qB"
    try:
        if os.path.exists(dotqB):
            return {"exists": False, "size": None, "suffix": ".!qB"}
    except OSError:
        pass
    if temp_path:
        # qB 配了 temp path 时下载中文件另存他处; 按 save_path 探不到属已知边界(计划 §04 note 3.)
        try:
            if os.path.exists(os.path.join(temp_path, utils.path_normalize(rel_name))):
                return {"exists": False, "size": None, "suffix": None, "in_temp": True}
        except OSError:
            pass
    return {"exists": False, "size": None, "suffix": None}
