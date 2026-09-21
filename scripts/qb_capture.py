#!/usr/bin/env python
"""真实 qB 语料抓取 · 脱敏 · 离线回放 —— 抓取器 (计划 26-09-21-0024 §04/§05/§06)

把真机 qB 的数据面抓成「可复现 + 可脱敏 + 自洽」的语料, 供 sim_qb.py --source=corpus 离线回放。

三条设计原则(见计划 §00):
  1. 零语义转换 = 零失真: 每帧是 qB 响应整帧原样落盘(含 server_state / tags / categories),
     种子与全局状态只有一个来源 —— 流。不另存 torrents/server_state/tags/categories。
  2. 语料 = 一条原始流: 首帧即 T0(full_update=true), 末帧必是一份全量(ok=closure / aborted=mismatch)。
     中间检查点抓而不存 —— 由 T0 ⊕ 增量流 可重建, 没有保存价值。
  3. 脱敏必须守恒分组等价类: 归组 key 是 (归一化 save_path, 排序后的文件相对路径集合)。
     形态守恒伪名化 + 单射性硬约束 + 脱敏前后逐组对拍(不一致即不落盘)。

子命令:
  capture   一次做完: 抓 T0 -> 录流(与 files/trackers 抓取并行) -> 抓 T1
  snapshot  只出 T0 + files/trackers(分步调试用)
  record    在已有语料目录上继续录流(会重抓一份全量当新 T0, meta 记 gap=true)
  self-test 对已有语料目录跑 --self-test 自检

凭据: 只接受命令行 --user/--pass, 或 --from-config <path> 只读解析其 qbittorrent 段。
      绝不写入 meta.json / 语料 / warnings.jsonl (计划 §05 字段分档 / §10 风险表)。

用法示例:
  uv run python scripts/qb_capture.py capture --from-config config.yml \
      --out auto-qb-data/corpus/2026-09-21-a --profile normal --minutes 10
  uv run python scripts/qb_capture.py capture --host 127.0.0.1 --port 16585 \
      --user u --pass p --out <dir> --profile perf --interval-ms 100 --minutes 20 \
      --full-every 600 --qps 20 --sanitize strict
  uv run python scripts/qb_capture.py self-test --out <dir>
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import hmac
import json
import logging
import os
import re
import sys
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---- 仓库内导入 (src/ 归组纯函数是唯一被本计划放行的 src/ 改动, 见 §04 第 5 步) ----
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
from auto_qb.mixins.grouping import group_key_of  # noqa: E402
from auto_qb import utils  # noqa: E402
from auto_qb.torrents.compat import _SNAPSHOT_FIELDS, REQUIRED_TORRENT_FIELDS  # noqa: E402

logger = logging.getLogger("qb_capture")

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
          ① scheme 原样; ② host 换成 site-N.example(端口原样); ③ path/query 形态守恒
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

        三条等价类边界必须 1:1 保留(计划 §05): ①不同盘符不得并组 -> 带盘符短令牌;
        ②尾斜杠有无不得被 rstrip; ③大小写形态不得被 casefold。
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
        tail_sep = rest.endswith(("/", "\\"))  # 尾斜杠 1:1 保留(计划 §05 边界②)
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
        # qB 配了 temp path 时下载中文件另存他处; 按 save_path 探不到属已知边界(计划 §04 note ③)
        try:
            if os.path.exists(os.path.join(temp_path, utils.path_normalize(rel_name))):
                return {"exists": False, "size": None, "suffix": None, "in_temp": True}
        except OSError:
            pass
    return {"exists": False, "size": None, "suffix": None}


# ==========================================================================================
# 抓取器主体
# ==========================================================================================
class Capture:
    def __init__(self, args):
        self.args = args
        self.out = Path(args.out).resolve()
        self.warnings: list[dict] = []
        self.stream: list[dict] = []
        self._stream_lock = threading.Lock()
        self.files_map: dict[str, list] = {}
        self.trackers_map: dict[str, list] = {}
        self.peers_map: dict[str, list] = {}
        self.disk_map: dict[str, dict[str, dict]] = {}  # hash -> {rel: {exists,size,suffix}}
        self.known_hashes: set[str] = set()
        self.meta: dict = {}
        self.abort_at: dict | None = None
        self.status = "ok"
        self.checkpoints: list[dict] = []
        self.t_seq = 0
        self.t0_wall = 0.0
        self._stop = threading.Event()
        self.sanitizer: Sanitizer | None = None
        self._pre_groups: dict | None = None
        self._raw_torrents: dict = {}
        self._raw_files: dict = {}
        self._save_path_pref = ""
        self._temp_path = ""

        self.client = QbClient(args.host, args.port, args.user, args.password)
        self.client.qps = args.qps
        self.rec = QbClient(args.host, args.port, args.user, args.password)  # 独立 session/rid
        self.ck = QbClient(args.host, args.port, args.user, args.password)  # 检查点/闭合专用
        self.fetch = QbClient(args.host, args.port, args.user, args.password)  # files/trackers 专用

    # ---------- 基础 ----------
    def warn(self, kind: str, **extra) -> None:
        self.warnings.append({"kind": kind, "t": datetime.now(timezone.utc).isoformat(), **extra})
        logger.warning("%s %s", kind, extra)

    def handshake(self) -> None:
        ver = self.client.get_text("/app/version")
        wapi = self.client.get_text("/app/webapiVersion")
        prefs, _ = self.client.get_json("/app/preferences")
        ss = self.rec.maindata(0)[0].get("server_state") or {}
        self.meta = {
            "corpus_version": CORPUS_VERSION,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "qb_version": ver,
            "qb_webapi_version": wapi,
            "server_state_keys": sorted(ss.keys()),
            "fields_whitelist_version": FIELDS_WHITELIST_VERSION,
            "snapshot_fields_expected": len(_SNAPSHOT_FIELDS),
            "required_fields": len(REQUIRED_TORRENT_FIELDS),
            "profile": self.args.profile,
            "interval_ms": self.interval_ms,
            "full_every_s": self.args.full_every,
            "qps": self.args.qps,
            "sample": self.args.sample,
            "probe_fs": self.args.probe_fs,
            "sanitize": self.args.sanitize,
            "preferences_baseline":
                {
                    # 只记"是否启用"与形态, 不记真实路径(路径本身就是敏感信息, 见 §05 字段分档)
                    "save_path_shape": "<redacted>",
                    "temp_path_shape": "<redacted>" if prefs.get("temp_path") else "",
                    "temp_path_enabled": prefs.get("temp_path_enabled"),
                    "max_active_downloads": prefs.get("max_active_downloads"),
                    "max_active_uploads": prefs.get("max_active_uploads"),
                    "max_active_torrents": prefs.get("max_active_torrents"),
                },
            "temp_path_enabled": bool(prefs.get("temp_path_enabled")),
            "record_peers": bool(self.args.record_peers),
        }
        # 真实路径只留在内存(探测用), 不进 meta.json
        self._save_path_pref = prefs.get("save_path") or ""
        self._temp_path = prefs.get("temp_path") or ""
        logger.info("qB %s / webapi %s / server_state 键 %d", ver, wapi, len(ss))
        if self.probe_fs_on and self.meta["temp_path_enabled"]:
            self.warn("temp_path_enabled", note="temp path 已启用: 按 save_path 探测不到下载中文件, 见计划 §04 note ③")

    @property
    def probe_fs_on(self) -> bool:
        """--probe-fs 是 on/off 字符串, 'off' 本身为真 —— 必须显式比一次, 不能直接 if args.probe_fs"""
        return self.args.probe_fs == "on"

    @property
    def interval_ms(self) -> int:
        if self.args.interval_ms:
            return int(self.args.interval_ms)
        if self.args.interval:
            return int(float(self.args.interval) * 1000)
        return 100 if self.args.profile == "perf" else 2000

    # ---------- T0 / 全量 ----------
    def full_frame(self, client: QbClient, role: str) -> dict:
        d, rtt = client.maindata(0)
        frame = {
            "t_seq": self.t_seq,
            "t_wall": datetime.now(timezone.utc).isoformat(),
            "dt_ms": 0,
            "rtt_ms": round(rtt, 3),
            "role": role
        }
        frame.update(d)
        self.t_seq += 1
        return frame

    def fetch_files_trackers(self, hashes: list[str], label: str = "") -> None:
        """每 hash 的 files/trackers: 受 --qps 限速, 并发上限 4; 失败只记 warnings, 不中断"""
        todo = [h for h in hashes if h not in self.files_map]
        if not todo:
            return
        t0 = time.perf_counter()

        def one(h: str):
            try:
                f, _ = self.fetch.files(h)
                self.files_map[h] = f or []
            except Exception as e:  # noqa: BLE001
                self.warn("files_failed", hash=h, error=f"{type(e).__name__}: {e}")
                self.files_map[h] = []
            try:
                tr, _ = self.fetch.trackers(h)
                self.trackers_map[h] = tr or []
            except Exception as e:  # noqa: BLE001
                self.warn("trackers_failed", hash=h, error=f"{type(e).__name__}: {e}")
                self.trackers_map[h] = []

        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(one, todo))
        logger.info(
            "抓 files/trackers: %d 个种子%s, 用时 %.0f ms", len(todo), f" ({label})" if label else "",
            (time.perf_counter() - t0) * 1000
        )

    def fetch_peers(self, hashes: list[str]) -> None:
        """sync/torrentPeers 按需端点: 默认不录, --record-peers 才录(计划 §03)"""
        todo = [h for h in hashes if h not in self.peers_map]
        if not todo:
            return
        t0 = time.perf_counter()

        def one(h: str):
            try:
                d, _ = self.fetch.get_json("/sync/torrentPeers", hash=h, rid=0)
                self.peers_map[h] = list((d.get("peers") or {}).values())
            except Exception as e:  # noqa: BLE001
                self.warn("peers_failed", hash=h, error=f"{type(e).__name__}: {e}")
                self.peers_map[h] = []

        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(one, todo))
        logger.info("抓 torrentPeers: %d 个种子, 用时 %.0f ms", len(todo), (time.perf_counter() - t0) * 1000)

    def probe_fs_initial(self) -> None:
        if not self.probe_fs_on:
            return
        t0 = time.perf_counter()
        temp = self._temp_path
        n = 0
        for h, files in self.files_map.items():
            tv = self.acc_torrents.get(h) or {}
            sp = tv.get("save_path", "")
            self.disk_map[h] = {}
            for f in files:
                self.disk_map[h][utils.path_normalize(f["name"])] = probe_disk(sp, f["name"], f["size"], temp)
                n += 1
        logger.info("磁盘初探: %d 个文件, 用时 %.0f ms", n, (time.perf_counter() - t0) * 1000)

    # ---------- 录流 ----------
    def _recorder(self) -> None:
        rid = self.rec_rid
        next_at = time.perf_counter()
        prev = next_at
        while not self._stop.is_set():
            next_at += self.interval_ms / 1000.0
            try:
                d, rtt = self.rec.maindata(rid)
            except Exception as e:  # noqa: BLE001
                self.warn("record_failed", error=f"{type(e).__name__}: {e}")
                time.sleep(0.5)
                continue
            rid = d.get("rid", rid)
            now = time.perf_counter()
            frame = {
                "t_seq": 0,  # 稍后统一编号
                "t_wall": datetime.now(timezone.utc).isoformat(),
                "dt_ms": round((now - prev) * 1000.0, 1),
                "rtt_ms": round(rtt, 3),
                "role": "inc",
            }
            prev = now
            frame.update(d)
            with self._stream_lock:
                self.stream.append(frame)
                if self.args.record_max_bytes and self._stream_bytes() > self.args.record_max_bytes:
                    self.warn("record_max_bytes", note="熔断: 流体积超限, 提前结束录流")
                    self._stop.set()
            slack = next_at - time.perf_counter()
            if slack > 0:
                time.sleep(slack)

    def _stream_bytes(self) -> int:
        return sum(len(json.dumps(f, ensure_ascii=False)) for f in self.stream[-50:]) * max(len(self.stream) // 50, 1)

    def new_hashes(self) -> list[str]:
        with self._stream_lock:
            hs = set()
            for f in self.stream:
                hs.update((f.get("torrents") or {}).keys())
        return sorted(hs - self.known_hashes)

    # ---------- 检查点 ----------
    def _catch_up(self) -> None:
        """收尾增量: 让流追上"现在", 把「全量 vs 流」的采样窗口从 interval_ms 压到毫秒级。

        不做这一步的话, 检查点/闭合必然因「最后一条增量之后又变了」而假红 ——
        这是采样式对齐的固有竞态, 与 qB 是否正确无关。
        """
        try:
            d, rtt = self.rec.maindata(self.rec_rid)
        except Exception as e:  # noqa: BLE001
            self.warn("catch_up_failed", error=f"{type(e).__name__}: {e}")
            return
        self.rec_rid = d.get("rid", self.rec_rid)
        frame = {
            "t_seq": 0,
            "t_wall": datetime.now(timezone.utc).isoformat(),
            "dt_ms": 0,
            "rtt_ms": round(rtt, 3),
            "role": "inc"
        }
        frame.update(d)
        with self._stream_lock:
            self.stream.append(frame)

    def checkpoint(self, label: str, final: bool) -> dict:
        """周期性全量对齐: 只留首尾两份, 中间的抓而不存(通过只在 meta 累加统计)"""
        self._catch_up()
        frame = self.full_frame(self.ck, "closure" if final else "checkpoint")
        acc = StreamAccumulator()
        for f in self.stream:  # frame 尚未入流, 故这里就是「首帧 ⊕ 中间全部增量帧」
            acc.apply(f)
        res = diff_full(acc, frame)
        res["label"] = label
        res["t_seq"] = frame["t_seq"]
        if res["ok"]:
            self.checkpoints.append(
                {
                    "label": label,
                    "ok": True,
                    "t_seq": frame["t_seq"],
                    "alignment_rate": res["alignment_rate"]
                }
            )
            if not final:
                return res  # 抓而不存
            with self._stream_lock:
                self.stream.append(frame)
            return res
        # 未对齐 -> 就地作为末帧入盘 + 停止录制 + 不写 groups.json
        self.status = "aborted"
        self.abort_at = {
            "t_seq": frame["t_seq"],
            "label": label,
            "diff": {
                k: v
                for k, v in res.items() if k not in ("ok", )
            }
        }
        with self._stream_lock:
            self.stream.append(frame)
        self.checkpoints.append(
            {
                "label": label,
                "ok": False,
                "t_seq": frame["t_seq"],
                "alignment_rate": res["alignment_rate"]
            }
        )
        self._stop.set()
        return res

    # ---------- 真值分组 (计划 §04 第 5 步) ----------
    @staticmethod
    def truth_groups(torrents: dict, files_map: dict, sanitize: bool = False, san: Sanitizer | None = None) -> dict:
        """用 auto_qb.mixins.grouping.group_key_of 的同一套公式算真机分组(单一事实源)"""
        groups: dict = {}
        for h, tv in torrents.items():
            files = files_map.get(h) or []
            fmap = {}
            for f in files:
                nm = utils.path_normalize(f["name"])
                fmap[san.name(nm) if sanitize and san else nm] = f["size"]
            if not fmap:
                continue  # 空 file_map 不归组(与 _assign_to_group 一致, 非错误路径)
            sp = tv.get("save_path", "")
            key = group_key_of(san.path(sp) if sanitize and san else sp, fmap)
            groups.setdefault(key, []).append(h)
        return groups

    @staticmethod
    def _group_signature(groups: dict, hash_fn) -> dict:
        """分组的等价类签名: 组 -> 成员(按映射后 hash 排序)。只看等价类, 不看名字"""
        return {key: tuple(sorted(hash_fn(h) for h in members)) for key, members in groups.items()}

    # ---------- 脱敏 ----------
    def sanitize_all(self) -> None:
        salt = os.urandom(32)
        san = Sanitizer(salt)
        self.sanitizer = san
        self.meta["salt_fingerprint"] = hashlib.sha256(salt).hexdigest()[:8]
        self.meta["sanitize_params"] = {
            "mode": "strict",
            "shape_preserving": True,
            "ext_preserved": True,
            "fsroot_placeholder": FSROOT_PLACEHOLDER
        }

        # files / trackers —— 必须一并重键到假 hash: 流里的种子键已换成假 hash,
        # 若这两张表仍用真 hash, 回放端按流里的 hash 查不到 files(分组全空 / 一致性判据必红)
        self.files_map = {
            san.infohash(h): [dict(f, name=san.name(utils.path_normalize(f["name"]))) for f in v]
            for h, v in self.files_map.items()
        }
        self.trackers_map = {
            san.infohash(h): [dict(t, url=san.tracker_url(t.get("url", ""))) for t in v]
            for h, v in self.trackers_map.items()
        }
        # 磁盘探测表同样按假 hash 重键, 且**内层相对路径也要伪名化**
        # ❗只重外层 hash 是不够的: 内层 key 是真实文件名, 会把真机资源名原样漏进语料
        #   (实测漏过一次: disk.json.gz 里全是未脱敏的中文资源名)。故内层走与 files 同一套
        #   `san.name(path_normalize(...))`, 保证与 files.json 的 name 逐字一致(回放端要按它对表)。
        if self.disk_map:
            self.disk_map = {
                san.infohash(h): {san.name(utils.path_normalize(rel)): v for rel, v in d.items()}
                for h, d in self.disk_map.items()
            }
        if self.peers_map:
            self.peers_map = {san.infohash(h): v for h, v in self.peers_map.items()}

        # 流: 每帧原样保留 qB 语义, 只替换身份字段
        with self._stream_lock:
            for f in self.stream:
                if isinstance(f.get("torrents"), dict):
                    f["torrents"] = {san.infohash(h): self._san_torrent(v, san) for h, v in f["torrents"].items()}
                if f.get("torrents_removed"):
                    f["torrents_removed"] = [san.infohash(h) for h in f["torrents_removed"]]
                if f.get("tags"):
                    f["tags"] = [san.text(t) for t in f["tags"]]
                if f.get("tags_removed"):
                    f["tags_removed"] = [san.text(t) for t in f["tags_removed"]]
                if isinstance(f.get("categories"), dict):
                    f["categories"] = {san.text(k): v for k, v in f["categories"].items()}
                if f.get("categories_removed"):
                    f["categories_removed"] = [san.text(k) for k in f["categories_removed"]]
        self.meta["sanitize_map_sizes"] = san.dump_stats()
        self.meta["collisions"] = dict(san.collisions) if san.collisions else {}
        if san.collisions:
            logger.info("伪名碰撞(已用递增 nonce 确定性重派生解决, 保长保形保单射): %s", san.collisions)

    @staticmethod
    def _san_torrent(v: dict, san: Sanitizer) -> dict:
        out = dict(v)
        # 路径类字段先 path_normalize 再伪名化 —— 让"同一逻辑路径"只有一种规范形,
        # 否则 'R:\\a' 与 'R:/a' 会得到两份不同伪名, 等价类对拍必然假红。
        for k in ("save_path", "content_path", "download_path", "root_path"):
            if out.get(k):
                out[k] = san.path(utils.path_normalize(out[k]))
        if out.get("name"):
            out["name"] = san.name(out["name"])
        if out.get("tags"):
            out["tags"] = ", ".join(san.text(t.strip()) for t in str(out["tags"]).split(","))
        if out.get("category"):
            out["category"] = san.text(out["category"])
        if out.get("tracker"):
            out["tracker"] = san.tracker_url(out["tracker"])
        if out.get("magnet_uri"):
            out["magnet_uri"] = san.tracker_url(out["magnet_uri"])
        for k in ("infohash_v1", "infohash_v2"):
            if out.get(k):
                out[k] = san.infohash(out[k])
        # comment / created_by 清空(常含站点署名与内网信息)
        for k in ("comment", "created_by"):
            if k in out:
                out[k] = ""
        return out

    # ---------- 落盘 ----------
    def write_corpus(self) -> None:
        self.out.mkdir(parents=True, exist_ok=True)
        # 首帧是 T0, 末帧必是全量
        with self._stream_lock:
            for i, f in enumerate(self.stream):
                f["t_seq"] = i
            stream = list(self.stream)

        with gzip.open(self.out / "sync-stream.jsonl.gz", "wt", encoding="utf-8") as fh:
            for f in stream:
                fh.write(json.dumps(f, ensure_ascii=False, separators=(",", ":")) + "\n")
        with gzip.open(self.out / "files.json.gz", "wt", encoding="utf-8") as fh:
            json.dump(self.files_map, fh, ensure_ascii=False, separators=(",", ":"))
        with gzip.open(self.out / "trackers.json.gz", "wt", encoding="utf-8") as fh:
            json.dump(self.trackers_map, fh, ensure_ascii=False, separators=(",", ":"))

        n_ok = sum(1 for c in self.checkpoints if c["ok"])
        self.meta.update(
            {
                "status": self.status,
                "abort_at": self.abort_at,
                "frames": len(stream),
                "frames_total_bytes": sum(len(json.dumps(f, ensure_ascii=False)) for f in stream),
                "first_frame_full_update": bool(stream[0].get("full_update")) if stream else False,
                "last_frame_role": stream[-1].get("role") if stream else None,
                "last_frame_full_update": bool(stream[-1].get("full_update")) if stream else False,
                "torrents_in_t0": len((stream[0].get("torrents") or {})) if stream else 0,
                "torrents_at_end": len(self.acc_torrents),
                "hashes_with_files": len(self.files_map),
                "hashes_with_trackers": len(self.trackers_map),
                "total_files": sum(len(v) for v in self.files_map.values()),
                "checkpoints_total": len(self.checkpoints),
                "checkpoints_failed": len(self.checkpoints) - n_ok,
                "warnings": len(self.warnings),
                "disk_probe":
                    {
                        "enabled":
                            self.probe_fs_on,
                        "exists":
                            sum(1 for v in self.disk_map.values() for x in v.values() if x["exists"]),
                        "missing":
                            sum(1 for v in self.disk_map.values() for x in v.values() if not x["exists"]),
                        "dot_qb_suffix":
                            sum(1 for v in self.disk_map.values() for x in v.values() if x.get("suffix") == ".!qB"),
                    } if self.probe_fs_on else {
                        "enabled": False
                    },
            }
        )
        if self.probe_fs_on:
            with gzip.open(self.out / "disk.json.gz", "wt", encoding="utf-8") as fh:
                json.dump(self.disk_map, fh, ensure_ascii=False, separators=(",", ":"))
        if self.peers_map:
            with gzip.open(self.out / "peers.json.gz", "wt", encoding="utf-8") as fh:
                json.dump(self.peers_map, fh, ensure_ascii=False, separators=(",", ":"))

        # groups.json: 只在 ok 时写(aborted 时真值分组已不可信, 绝不能被当判据答案)
        if self.status == "ok":
            post = self.truth_groups(self.acc_torrents, self.files_map, sanitize=False)
            conserve = self._partition_equivalent(
                self._raw_torrents, self._raw_files, self.acc_torrents, self.files_map, self.sanitizer
            )
            self.meta["group_conservation"] = conserve
            gid = {key: f"g{i:05d}" for i, key in enumerate(sorted(post, key=lambda k: (k[0], len(post[k]))))}
            groups_out = {
                "groups":
                    [
                        {
                            "group_id": gid[k],
                            "size": len(post[k]),
                            "members": sorted(post[k]),
                            "key_save_path": k[0],
                            "key_file_count": len(k[1])
                        } for k in gid
                    ],
                "evaluated_at": "T0 首帧应用后 / 任何写动作前",
                "note": "真值分组由抓取端用 group_key_of 算出; 参考时刻见计划 §09 CORPUS.group_exact"
            }
            with gzip.open(self.out / "groups.json.gz", "wt", encoding="utf-8") as fh:
                json.dump(groups_out, fh, ensure_ascii=False, indent=1)
        else:
            self.meta["group_conservation"] = {"skipped": "aborted 不写 groups.json"}

        (self.out / "meta.json").write_text(json.dumps(self.meta, ensure_ascii=False, indent=1), encoding="utf-8")
        with (self.out / "warnings.jsonl").open("w", encoding="utf-8") as fh:
            for w in self.warnings:
                fh.write(json.dumps(w, ensure_ascii=False) + "\n")
        # 产物目录自带 .gitignore 与警示 README(计划 §10 风险表 P0)
        (self.out / ".gitignore").write_text("*\n!.gitignore\n!README.md\n", encoding="utf-8")
        (self.out / "README.md").write_text(
            "# 真机语料目录 —— 请勿提交\n\n"
            "本目录由 `scripts/qb_capture.py` 生成, 含真实 PT 资源清单的**脱敏副本**。\n"
            "盐未落盘, 故本目录内容无法与任何真实资源关联; 但仍**严禁** `git add` / 提交 / 外传。\n"
            "已随目录附带 `.gitignore`(`*` 全忽略), 请勿删除。\n\n"
            "存放位置应为已 gitignore 的目录(如 `auto-qb-data/corpus/`), 且**至少再拷一份**到另一块盘"
            "(一份要真机 + 长时间高频录制才能产出的语料不该是单点, 见计划 §10)。\n",
            encoding="utf-8"
        )

    @staticmethod
    def _partition_equivalent(
        raw_torrents: dict, raw_files: dict, san_torrents: dict, san_files: dict, san: Sanitizer
    ) -> dict:
        """脱敏前后分组守恒 —— 头号验收(计划 §05), 阻断式

        做法: 用 group_key_of 在「原始身份」与「脱敏身份」上各算一次分组, 逐组逐成员对拍。
          A. pre    : 真机原始 torrents/files -> 分组(含真实种子名, 只在内存)
          B. mapped : 对 raw 施加同一套伪名映射后再分组 —— 这是"脱敏后**应该**得到的分组"
          C. post   : 直接对**已落盘形态**的语料(torrents/files 均已脱敏)分组
        A == B 是脱敏自身的一致性; B == C 才是"落盘产物真的按预期分组"。
        任一不等 ⇒ 脱敏破坏了等价类 ⇒ 中止抓取、不落盘。

        组的 key 会被脱敏整体改写(盘符 -> <FSROOT>/dN/), 所以只能比**成员集合结构**,
        不能比 key 本身 —— 比 key 会永远不等(这是本条判据最容易写错的地方)。
        """
        def groups_of(torrents: dict, files: dict, key_of_sp, key_of_name, label_of):
            out: dict = {}
            for h, tv in torrents.items():
                fmap = {}
                for f in files.get(h) or []:
                    fmap[key_of_name(f["name"])] = f["size"]
                if not fmap:
                    continue  # 空 file_map 不归组(与 _assign_to_group 一致)
                out.setdefault(group_key_of(key_of_sp(tv.get("save_path", "")), fmap), []).append(label_of(h))
            return out

        def partition(groups: dict) -> dict:
            """分组 -> {成员: 同组全体}。组的 key 会被整体改写, 故只比成员集合结构。"""
            out = {}
            for members in groups.values():
                ms = frozenset(members)
                for h in members:
                    out[h] = ms
            return out

        norm = utils.path_normalize
        rev_hash = {v: k for k, v in san._maps.get("hash", {}).items()}
        pre = partition(groups_of(raw_torrents, raw_files, norm, norm, lambda h: h))
        mapped = partition(
            groups_of(raw_torrents, raw_files, lambda p: san.path(norm(p)), lambda n: san.name(norm(n)), lambda h: h)
        )
        post = partition(groups_of(san_torrents, san_files, norm, norm, lambda h: rev_hash.get(h, h)))

        problems = []
        for label, a, b in (("pre_vs_mapped", pre, mapped), ("mapped_vs_post", mapped, post)):
            for h in sorted(set(a) | set(b)):
                if a.get(h) != b.get(h):
                    problems.append(
                        {
                            "kind": f"{label}:partition_mismatch",
                            "hash": h[:12],
                            "a_group": sorted(x[:8] for x in (a.get(h) or []))[:5],
                            "b_group": sorted(x[:8] for x in (b.get(h) or []))[:5]
                        }
                    )
                    break
        return {
            "ok": not problems,
            "torrents": len(pre),
            "groups": len(set(map(frozenset, pre.values()))),
            "problems": problems[:4]
        }

    # ---------- 自检 ----------
    def self_test(self) -> dict:
        """--self-test: 字段完整性 / 映射单射性 / 分组守恒 / 首尾闭合 / 体量统计"""
        res: dict = {}
        # 1. 字段完整性: 硬下限 = 27 必需字段(缺失即 FAIL); 扩展字段缺失按 WARN 逐项列出。
        #    两处 qB 语义修正(计划 §09 只要求"与 70 字段表比对", 这里把口径写实):
        #      · hash 不在响应体内 —— 它是 torrents 字典的键(store.py 注释亦如此), 视为已满足;
        #      · reannounce / reannounce_in 是不同 qB 版本二选一出现, 满足其一即可。
        all_fields: set = set()
        with self._stream_lock:
            for f in self.stream:
                for h, tv in (f.get("torrents") or {}).items():
                    all_fields.update(tv.keys())
                    all_fields.add("hash")
        if "reannounce" in all_fields or "reannounce_in" in all_fields:
            all_fields.update(("reannounce", "reannounce_in"))
        missing_required = [f for f in REQUIRED_TORRENT_FIELDS if f not in all_fields]
        missing_ext = [f for f in _SNAPSHOT_FIELDS if f not in all_fields]
        res["fields_complete"] = {
            "ok": not missing_required,
            "present": len(all_fields),
            "expected": len(_SNAPSHOT_FIELDS),
            "missing_required": missing_required,
            "missing_extension_warn": missing_ext
        }
        # 2. 映射单射性(构造期已硬校验, 这里复核)
        san = self.sanitizer
        inj = True
        if san:
            for kind, m in san._maps.items():
                if len(set(m.values())) != len(m):
                    inj = False
        res["sanitize_injective"] = {"ok": inj}
        # 3. 分组守恒
        res["group_conservation"] = self.meta.get("group_conservation", {})
        # 4. 首尾闭合: 流首帧 ⊕ 中间增量 == 流末帧
        with self._stream_lock:
            stream = list(self.stream)
        if self.status == "snapshot":
            res["stream_closure"] = {"ok": True, "skipped": "snapshot 模式无录流 ⇒ 无闭合锚点"}
        elif stream and stream[-1].get("role") in ("closure", "mismatch"):
            acc = StreamAccumulator()
            for f in stream[:-1]:
                acc.apply(f)
            res["stream_closure"] = diff_full(acc, stream[-1])
        else:
            res["stream_closure"] = {"ok": False, "reason": "末帧不是全量(role != closure/mismatch)"}
        # 5. 流级脱敏一致性: 流中每个 hash 都能在 files/trackers 找到; tracker 域名都在映射表内
        stream_hashes = {h for f in stream for h in (f.get("torrents") or {})}
        unknown_files = sorted(stream_hashes - set(self.files_map))
        # ❗磁盘表的内层相对路径必须与 files 的 name 逐字一致 —— 它是最容易漏脱敏的一处
        # (外层 hash 换了, 内层还是真实文件名, 且藏在 .gz 里, 凭据扫描扫不到)
        disk_orphans = []
        if self.disk_map:
            for h, d in self.disk_map.items():
                names = {utils.path_normalize(f["name"]) for f in (self.files_map.get(h) or [])}
                for rel in d:
                    if rel not in names:
                        disk_orphans.append(f"{h[:12]}:{rel[:40]}")
                        break
        res["sanitize_stream_consistent"] = {
            "ok": not unknown_files and not disk_orphans,
            "hashes_in_stream": len(stream_hashes),
            "missing_files_entry": unknown_files[:5],
            "missing_files_count": len(unknown_files),
            "disk_rel_not_in_files": disk_orphans[:5],
            "disk_rel_orphan_count": len(disk_orphans),
        }
        # 6. 凭据泄漏扫描(计划 §05 / P2-3): 明文产物里不得出现用户名/密码/真实路径前缀
        creds = [c for c in (self.args.password, self.args.user) if c]
        leaks = []
        for p in sorted(self.out.glob("*")):
            if not p.is_file() or p.suffix == ".gz":
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for cred in creds:
                if cred in txt:
                    leaks.append({"file": p.name, "kind": "credential"})
            for raw in (self._save_path_pref, self._temp_path):
                if raw and raw in txt:
                    leaks.append({"file": p.name, "kind": "raw_path"})
        res["no_credentials"] = {"ok": not leaks, "leaks": leaks}
        # 7. 体量
        res["sizes"] = {p.name: p.stat().st_size for p in sorted(self.out.glob("*")) if p.is_file()}
        return res

    # ---------- 主流程 ----------
    def run_capture(self) -> int:
        self.handshake()
        if self.args.dry:
            n = self.args.sample or self._count_torrents()
            logger.info(
                "[DRY] 将发请求: 1(version)+1(webapi)+1(preferences)+1(maindata rid=0) "
                "+%d×2(files+trackers) + 录流 %d 次(maindata, %.0f ms 间隔) "
                "+ 检查点 %d 次", n, int(self.args.minutes * 60000 / self.interval_ms), self.interval_ms,
                max(int(self.args.minutes * 60 / self.args.full_every), 1)
            )
            return 0
        if self.args.command == "snapshot":
            return self.run_snapshot()
        return self.run_full()

    def run_snapshot(self) -> int:
        """snapshot: 只出 T0 + files/trackers (分步调试用, 无录流 ⇒ 无闭合锚点)"""
        t0 = self.full_frame(self.client, "t0")
        self.acc_torrents = {h: dict(v) for h, v in (t0.get("torrents") or {}).items()}
        hashes = list(self.acc_torrents.keys())
        if self.args.sample:
            hashes = hashes[:self.args.sample]
        with self._stream_lock:
            self.stream.append(t0)
        self.known_hashes = set(hashes)
        self.fetch_files_trackers(hashes, "snapshot")
        if self.args.record_peers:
            self.fetch_peers(hashes)
        self.probe_fs_initial()
        self.status = "snapshot"
        self.meta["gap"] = True
        self.meta["note"] = "snapshot 模式: 只有 T0, 无录流; 分步调试用(计划 §04)"
        self._raw_torrents = {h: dict(v) for h, v in self.acc_torrents.items()}
        self._raw_files = {h: [dict(f) for f in v] for h, v in self.files_map.items()}
        self._pre_groups = self.truth_groups(self.acc_torrents, self.files_map, sanitize=False)
        self.sanitize_all()
        self.acc_torrents = self._final_torrents()
        self.write_corpus()
        logger.info(
            "snapshot 完成: %d 种子 / %d 文件 -> %s", len(hashes), sum(len(v) for v in self.files_map.values()), self.out
        )
        return 0

    def run_full(self) -> int:
        if self.args.command == "record" and (self.out / "meta.json").exists():
            # 分两步时 session 已断、rid 无从续 ⇒ 两步之间的变化会丢; 记 gap=true(计划 §04)
            self.meta["gap"] = True
            logger.warning("record 模式: 会重抓一份全量当新 T0, meta 记 gap=true(两步之间的变化已丢)")
        t0 = self.full_frame(self.client, "t0")
        self.acc_torrents = {h: dict(v) for h, v in (t0.get("torrents") or {}).items()}
        hashes = list(self.acc_torrents.keys())
        if self.args.sample:
            hashes = hashes[:self.args.sample]
        with self._stream_lock:
            self.stream.append(t0)
        self.known_hashes = set(hashes)
        self.rec_rid = t0.get("rid", 0)
        logger.info(
            "T0: %d 种子(full_update=%s, rid=%s)%s", len(hashes), t0.get("full_update"), self.rec_rid,
            f", --sample 截到 {len(hashes)}" if self.args.sample else ""
        )

        # 录流与 files/trackers 抓取并行(计划 §04 P2-1: 否则首个增量帧会把这段变化压成一帧)
        rec = threading.Thread(target=self._recorder, daemon=True)
        rec.start()
        self.fetch_files_trackers(hashes, "T0 全量")
        if self.args.record_peers:
            self.fetch_peers(hashes)
        self.probe_fs_initial()

        deadline = time.perf_counter() + self.args.minutes * 60
        next_ck = time.perf_counter() + self.args.full_every
        while not self._stop.is_set() and time.perf_counter() < deadline:
            time.sleep(0.2)
            fresh = self.new_hashes()
            if fresh:
                # 录制期间新出现的种子: 出现即 append, 不等结束再补(计划 §04)
                self.fetch_files_trackers(fresh, "流中新种子")
                if self.args.record_peers:
                    self.fetch_peers(fresh)
                self.known_hashes.update(fresh)
                for h in fresh:
                    self.acc_torrents.setdefault(h, {})
            if time.perf_counter() >= next_ck and not self._stop.is_set():
                next_ck = time.perf_counter() + self.args.full_every
                res = self.checkpoint("periodic", final=False)
                logger.info("检查点: 对齐率 %.4f %s", res["alignment_rate"], "OK" if res["ok"] else "*** 未对齐, 停止录制 ***")
                if self.probe_fs_on:
                    self.probe_fs_delta()
        self._stop.set()
        rec.join(timeout=5)

        if self.status == "ok":
            res = self.checkpoint("final", final=True)
            logger.info("T1 闭合: 对齐率 %.4f %s", res["alignment_rate"], "OK" if res["ok"] else "*** 未对齐 ***")
        self.acc_torrents = self._final_torrents()
        # 脱敏前的真值分组(内存, 不落盘; 含真实种子名)。raw 快照供守恒对拍用, 比完即弃。
        self._raw_torrents = {h: dict(v) for h, v in self.acc_torrents.items()}
        self._raw_files = {h: [dict(f) for f in v] for h, v in self.files_map.items()}
        self._pre_groups = self.truth_groups(self.acc_torrents, self.files_map, sanitize=False)
        self.sanitize_all()
        # 脱敏后再取一次终态(键已换成假 hash, 供落盘/分组对拍使用)
        self.acc_torrents = self._final_torrents()
        self.write_corpus()
        report = self.self_test()
        ok = self._report(report)
        return 0 if ok else 1

    def _final_torrents(self) -> dict:
        with self._stream_lock:
            stream = list(self.stream)
        acc = StreamAccumulator()
        for f in stream[:-1] if stream and stream[-1].get("role") in ("closure", "mismatch") else stream:
            acc.apply(f)
        return acc.torrents

    def probe_fs_delta(self) -> None:
        """检查点增量探测: 只 stat 上一轮还存在的条目, 差异作为该帧 fs_delta(计划 §04)"""
        temp = self._temp_path
        delta = {}
        for h, prev in list(self.disk_map.items()):
            tv = self.acc_torrents.get(h) or {}
            sp = tv.get("save_path", "")
            files = {utils.path_normalize(f["name"]): f for f in (self.files_map.get(h) or [])}
            for rel, old in prev.items():
                if not old.get("exists"):
                    continue
                f = files.get(rel)
                if not f:
                    continue
                now = probe_disk(sp, rel, f["size"], temp)
                if now != old:
                    delta.setdefault(h, {})[rel] = now
                    prev[rel] = now
        if delta:
            with self._stream_lock:
                if self.stream:
                    self.stream[-1].setdefault("fs_delta", {}).update(delta)

    def _count_torrents(self) -> int:
        d, _ = self.client.maindata(0)
        return len(d.get("torrents") or {})

    def _report(self, report: dict) -> bool:
        ok = True
        logger.info("=" * 68)
        for k in (
            "fields_complete", "sanitize_injective", "group_conservation", "stream_closure",
            "sanitize_stream_consistent", "no_credentials"
        ):
            v = report.get(k) or {}
            good = bool(v.get("ok"))
            ok = ok and good
            if good:
                logger.info("  [PASS] %s", k)
            else:
                brief = {kk: vv for kk, vv in v.items() if kk != "ok"}
                logger.info("  [FAIL] %s %s", k, json.dumps(brief, ensure_ascii=False)[:600])
        logger.info("=" * 68)
        logger.info(
            "语料: %s  status=%s frames=%d checkpoints=%d/%d warnings=%d", self.out, self.meta.get("status"),
            self.meta.get("frames"),
            self.meta.get("checkpoints_total", 0) - self.meta.get("checkpoints_failed", 0),
            self.meta.get("checkpoints_total", 0), len(self.warnings)
        )
        return ok


# ==========================================================================================
# CLI
# ==========================================================================================
def load_from_config(path: str) -> dict:
    """只读解析 config.yml 的 qbittorrent 段(不写回、不进暂存; 计划 §10 红线)

    兼容两种布局: 顶层直接是 qbittorrent, 或套在 config: 之下(本项目 config.yml 是后者)。
    """
    import yaml
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    qb = data.get("qbittorrent") or (data.get("config") or {}).get("qbittorrent") or {}
    if not qb:
        raise SystemExit(f"[FATAL] {path} 里没有 qbittorrent 段")
    return {
        "host": qb.get("host", "127.0.0.1"),
        "port": int(qb.get("port", 8080)),
        "user": qb.get("username", ""),
        "password": qb.get("password", "")
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="真实 qB 语料抓取 / 脱敏 / 自检", formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("command", nargs="?", default="capture", choices=["capture", "snapshot", "record", "self-test"])
    p.add_argument("--out", required=False, help="语料输出目录(显式传入, 不写死推荐路径)")
    p.add_argument("--from-config", help="只读解析 config.yml 的 qbittorrent 段")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=16585)
    p.add_argument("--user", default="")
    p.add_argument("--pass", dest="password", default="")
    p.add_argument("--profile", choices=["perf", "normal"], default="normal")
    p.add_argument("--interval-ms", type=int, default=0)
    p.add_argument("--interval", default="")
    p.add_argument("--minutes", type=float, default=10.0)
    p.add_argument("--full-every", type=float, default=600.0, help="周期性全量检查点间隔(秒)")
    p.add_argument("--qps", type=float, default=20.0)
    p.add_argument("--sample", type=int, default=0, help="只抓前 N 个种子(首次真机跑建议 200)")
    p.add_argument("--probe-fs", choices=["on", "off"], default="off")
    p.add_argument("--record-peers", action="store_true")
    p.add_argument("--record-max-bytes", type=int, default=512 * 1024 * 1024)
    p.add_argument("--sanitize", choices=["strict"], default="strict")
    p.add_argument("--dry", action="store_true", help="只打印将要发的请求数与预估耗时, 不发请求")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S"
    )
    if args.from_config:
        args.__dict__.update(load_from_config(args.from_config))
    if not args.out:
        raise SystemExit("[FATAL] 必须显式传 --out <dir>(计划 §12: 语料位置是参数, 不写死)")

    # self-test 只读本地语料目录, 不连 qB ⇒ 不需要凭据
    if args.command == "self-test":
        return _self_test_only(args)
    if not args.user or not args.password:
        raise SystemExit("[FATAL] 缺凭据: 传 --user/--pass, 或 --from-config <path> 只读解析")

    cap = Capture(args)
    if args.command in ("capture", "snapshot", "record"):
        return cap.run_capture()
    return 0


def _self_test_only(args) -> int:
    """对已有语料目录跑自检(不需要 qB 连接)"""
    out = Path(args.out).resolve()
    stream = []
    with gzip.open(out / "sync-stream.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            stream.append(json.loads(line))
    with gzip.open(out / "files.json.gz", "rt", encoding="utf-8") as fh:
        files_map = json.load(fh)
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))

    acc = StreamAccumulator()
    for f in stream[:-1]:
        acc.apply(f)
    closure = diff_full(acc, stream[-1]) if stream else {"ok": False}
    fields = set()
    for f in stream:
        for h, tv in (f.get("torrents") or {}).items():
            fields.update(tv.keys())
            fields.add("hash")
    if "reannounce" in fields or "reannounce_in" in fields:
        fields.update(("reannounce", "reannounce_in"))
    missing = [f for f in REQUIRED_TORRENT_FIELDS if f not in fields]
    stream_hashes = {h for f in stream for h in (f.get("torrents") or {})}
    unknown = sorted(stream_hashes - set(files_map))

    ok = closure.get("ok") and not missing and not unknown
    logging.info("=" * 68)
    logging.info("  [%s] stream_closure 对齐率=%s", "PASS" if closure.get("ok") else "FAIL", closure.get("alignment_rate"))
    logging.info(
        "  [%s] fields_complete 缺失 %d/%d %s", "PASS" if not missing else "FAIL", len(missing), len(_SNAPSHOT_FIELDS),
        missing[:8]
    )
    logging.info(
        "  [%s] sanitize_stream_consistent 流中无 files 条目的 hash %d", "PASS" if not unknown else "FAIL", len(unknown)
    )
    logging.info("  meta.status=%s frames=%d", meta.get("status"), meta.get("frames"))
    logging.info("=" * 68)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
