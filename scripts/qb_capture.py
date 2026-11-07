#!/usr/bin/env python
"""真实 qB 语料抓取 - 脱敏 - 离线回放 —— 抓取器 (计划 26-09-21-0024 §04/§05/§06)

把真机 qB 的数据面抓成「可复现 + 可脱敏 + 自洽」的语料, 供 sim_qb.py --source=corpus 离线回放。

三条设计原则(见计划 §00):
  1. 零语义转换 = 零失真: 每帧是 qB 响应整帧原样落盘(含 server_state / tags / categories),
     种子与全局状态只有一个来源 —— 流。不另存 torrents/server_state/tags/categories。
  2. 语料 = 一条原始流: 首帧即 T0(full_update=true), 末帧必是一份全量(ok=closure / aborted=mismatch)。
     中间检查点抓而不存 —— 由 T0 + 增量流 可重建, 没有保存价值。
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
from auto_qb.core.modules.grouping_mod import group_key_of  # noqa: E402
from auto_qb.infra import utils  # noqa: E402
from auto_qb.torrents.compat import _SNAPSHOT_FIELDS, REQUIRED_TORRENT_FIELDS  # noqa: E402

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from qb_capture_core import *  # noqa: F401,F403
from qb_capture_core import _SNAPSHOT_FIELDS, REQUIRED_TORRENT_FIELDS, group_key_of, utils  # noqa: F401
from qb_capture_cli import _self_test_only, build_parser, load_from_config  # noqa: F401


# ==========================================================================================
# --dry 计划打印(真零请求口径: 判定必须发生在 Capture 构造之前, 见 _dry_plan)
# ==========================================================================================
def interval_ms_of(args) -> int:
    """录制间隔 ms 的纯参数计算(单点: Capture.interval_ms 与 _dry_plan 共用, 不另抄一份)"""
    if args.interval_ms:
        return int(args.interval_ms)
    if args.interval:
        return int(float(args.interval) * 1000)
    return 100 if args.profile == "perf" else 2000


def _dry_plan(args) -> int:
    """--dry: 只打印真跑将要发的请求计划, 本身零请求(评审 #11)。

    口径(help: 不发请求): 本函数由 main() 在 **Capture 构造之前**调用 —— QbClient 构造即
    POST /auth/login(Capture 一造就是 4 个独立 session), 旧实现在 run_capture 里先
    handshake 后判 dry, version/webapiVersion/preferences/maindata 4 个真实请求已经发出,
    缺 --sample 时计数请求(_count_torrents)再发 1 个, 与文案矛盾。现在不 login、不握手、
    不计数: 种子数取 --sample; 未给时全库计数本身要发请求, 与零请求矛盾, 计划里以"全库"
    占位不预查。真跑的请求序列见 run_capture -> handshake / run_full。
    """
    interval = interval_ms_of(args)
    per_torrent = (f"{args.sample}x2(files+trackers)" if args.sample else "全库种子数x2(files+trackers, 计数本身要发请求, 零请求模式不预查)")
    logger.info(
        "[DRY] 本次实际发出请求 0 个(未连接 qB: 不 login / 不握手 / 不计数)。真跑将发: "
        "1(version)+1(webapi)+1(preferences)+1(maindata rid=0) + %s + 录流 %d 次(maindata, %.0f ms 间隔)"
        " + 检查点 %d 次", per_torrent, int(args.minutes * 60000 / interval), interval,
        max(int(args.minutes * 60 / args.full_every), 1)
    )
    return 0


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
            self.warn("temp_path_enabled", note="temp path 已启用: 按 save_path 探测不到下载中文件, 见计划 §04 note 3.")

    @property
    def probe_fs_on(self) -> bool:
        """--probe-fs 是 on/off 字符串, 'off' 本身为真 —— 必须显式比一次, 不能直接 if args.probe_fs"""
        return self.args.probe_fs == "on"

    @property
    def interval_ms(self) -> int:
        return interval_ms_of(self.args)

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
        for f in self.stream:  # frame 尚未入流, 故这里就是「首帧 + 中间全部增量帧」
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
        """用 auto_qb.core.modules.grouping_mod.group_key_of 的同一套公式算真机分组(单一事实源)"""
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
        # !只重外层 hash 是不够的: 内层 key 是真实文件名, 会把真机资源名原样漏进语料
        #   (实测漏过一次: disk.json.gz 里全是未脱敏的中文资源名)。故内层走与 files 同一套
        #   `san.name(path_normalize(...))`, 保证与 files.json 的 name 逐字一致(回放端要按它对表)。
        if self.disk_map:
            self.disk_map = {
                san.infohash(h): {
                    san.name(utils.path_normalize(rel)): v
                    for rel, v in d.items()
                }
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
                if isinstance(f.get("fs_delta"), dict):
                    f["fs_delta"] = self._san_fs_delta(f["fs_delta"], san)
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

    def _san_fs_delta(self, delta: dict, san: Sanitizer) -> dict:
        """fs_delta 脱敏: 外层 hash 与内层相对名必须与 files_map/disk_map 同一套派生。

        !漏处理会把真实 infohash 与真实资源名原样写进 sync-stream.jsonl.gz(且凭据扫描跳过 .gz);
         回放端还会按伪 hash 查 save_path 落空, 把增量叠到错误的完整路径。
        对不上 files 的行**丢弃并 WARN**: 保留只能靠真名落盘(脱敏红线), 而伪名化一个 files 里
        不存在的名字又会让回放端无从对表。WARN 取样只写伪值, 不把真名带进 warnings.jsonl。
        """
        out: dict = {}
        dropped = []
        for h, rels in (delta or {}).items():
            ph = san.infohash(h)
            names = {utils.path_normalize(f["name"]) for f in (self.files_map.get(ph) or [])}
            keep = {}
            for rel, rec in (rels or {}).items():
                pn = san.name(utils.path_normalize(rel))
                if pn not in names:
                    dropped.append(f"{ph[:12]}:{pn[:40]}")
                    continue
                keep[pn] = rec
            if keep:
                out[ph] = keep
        if dropped:
            self.warn("fs_delta_unsanitized", dropped=len(dropped), samples=dropped[:5])
        return out

    # ---------- 落盘 ----------
    def _sanitize_mapping(self, seen: set[str] | None = None) -> dict:
        """脱敏后的「tracker 域名 <-> 站点标签」与「auto-qb 自有标签字面量」映射

        为什么必须记下来: 语料里的域名已换成 `site-N.example`、标签已伪名化, 而回放端生成的 config
        必须落在**同一个伪名空间**里, 否则:
          - tracker 规则按真域名写 => 站点匹配全落空 => `tracker_name` 解析不出来、依赖站点的规则空转;
          - `missing_tag` / `skip_checking_tag` 按真字面量写 => 与语料里的伪名标签对不上 =>
            跳检 / 缺文件的行为跟真机不一致(该跳的没跳、该打的标签打不上) —— 判据全绿也是假的。

        WARN: **只记已脱敏的两侧**(伪域名 <-> 伪标签)。站点标签的伪名**绝不**反向对应到真实站名
        —— 那等于把站点名原样写进语料。`MISSING` / `zSkipChecked` 是 auto-qb 自己的常量、非用户数据,
        记它们的伪名不构成泄露(这是本映射能成立的前提)。
        """
        san = self.sanitizer
        out: dict = {"tracker_tags": {}, "known_tags": {}}
        # 1) auto-qb 自有标签字面量 -> 伪名(只在真机上真出现过才记, 免得凭空造出不存在的标签)
        # !seen 是流内出现过的标签集合, 存的是**已脱敏**的伪名; 拿原始字面量 "MISSING" 去比对永远对不上。
        #   必须用反查表把伪名还原成原标签再比(san._revs[kind] = {伪名: 原文}, 同模块内取用)。
        #   调用方(write_corpus)把 StreamAccumulator 累积出的 tags 传进来。
        revs = san._revs.get("tag") or {}
        raw_seen = {revs.get(t, t) for t in (seen or set())}
        for lit in KNOWN_TAG_LITERALS:
            if lit in raw_seen:
                out["known_tags"][lit] = san.text(lit)
        # 2) tracker 域名 -> 站点标签(两侧都是伪名)。源是用户 config 的 trackers 段(权威),
        #    比"从数据里统计哪个标签最专有"可靠 —— 后者在站点混用标签时会挑错。
        cfg_path = getattr(getattr(self, "args", None), "from_config", "") or ""
        if cfg_path and os.path.isfile(cfg_path):
            try:
                import yaml
                data = yaml.safe_load(open(cfg_path, encoding="utf-8").read()) or {}
                trackers = (data.get("config") or {}).get("trackers") or data.get("trackers") or {}
                for _name, spec in (trackers or {}).items():
                    if not isinstance(spec, dict):
                        continue
                    for d in spec.get("domains") or []:
                        mm = re.match(
                            r"^[a-zA-Z][a-zA-Z0-9+.-]*://([^/]+)",
                            san.tracker_url(f"https://{d}/announce") or ""
                        )
                        if not mm:
                            continue
                        out["tracker_tags"][mm.group(1)] = [san.text(t) for t in (spec.get("tags") or [])]
            except Exception:  # noqa: BLE001  映射是增益信息, 取不到就退回统计派生
                pass
        return out

    def write_corpus(self) -> None:
        self.out.mkdir(parents=True, exist_ok=True)
        # 首帧是 T0, 末帧必是全量
        with self._stream_lock:
            for i, f in enumerate(self.stream):
                f["t_seq"] = i
            stream = list(self.stream)

        # 流终态标签集合(已脱敏伪名): 供 _sanitize_mapping 反查 auto-qb 自有标签是否真出现过
        acc = StreamAccumulator()
        for f in stream:
            acc.apply(f)

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
                "sanitize_map": self._sanitize_mapping(set(acc.tags)),
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
        任一不等 => 脱敏破坏了等价类 => 中止抓取、不落盘。

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
        #      - hash 不在响应体内 —— 它是 torrents 字典的键(store.py 注释亦如此), 视为已满足;
        #      - reannounce / reannounce_in 是不同 qB 版本二选一出现, 满足其一即可。
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
        # 4. 首尾闭合: 流首帧 + 中间增量 == 流末帧
        with self._stream_lock:
            stream = list(self.stream)
        if self.status == "snapshot":
            res["stream_closure"] = {"ok": True, "skipped": "snapshot 模式无录流 => 无闭合锚点"}
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
        # !磁盘表的内层相对路径必须与 files 的 name 逐字一致 —— 它是最容易漏脱敏的一处
        # (外层 hash 换了, 内层还是真实文件名, 且藏在 .gz 里, 凭据扫描扫不到)
        disk_orphans = []
        if self.disk_map:
            for h, d in self.disk_map.items():
                names = {utils.path_normalize(f["name"]) for f in (self.files_map.get(h) or [])}
                for rel in d:
                    if rel not in names:
                        disk_orphans.append(f"{h[:12]}:{rel[:40]}")
                        break
        # !fs_delta 也必须与 files 对表: 外层伪 hash 必须在 files_map, 内层伪相对名必须与
        #   对应 files 的 name 逐字一致(回放端按 save_path + 它拼全路径)。
        #   no_credentials 跳过 .gz, 漏脱敏只能由这条判据拦下(否则 self-test 恒假绿)。
        fs_hash_orphans: list[str] = []
        fs_rel_orphans: list[str] = []
        for f in stream:
            for h, rels in (f.get("fs_delta") or {}).items():
                names = {utils.path_normalize(x["name"]) for x in (self.files_map.get(h) or [])}
                if not names:
                    fs_hash_orphans.append(h[:12])
                    continue
                for rel in rels:
                    if rel not in names:
                        fs_rel_orphans.append(f"{h[:12]}:{rel[:40]}")
        res["sanitize_stream_consistent"] = {
            "ok": not unknown_files and not disk_orphans and not fs_hash_orphans and not fs_rel_orphans,
            "hashes_in_stream": len(stream_hashes),
            "missing_files_entry": unknown_files[:5],
            "missing_files_count": len(unknown_files),
            "disk_rel_not_in_files": disk_orphans[:5],
            "disk_rel_orphan_count": len(disk_orphans),
            "fs_delta_hash_not_in_files": fs_hash_orphans[:5],
            "fs_delta_rel_not_in_files": fs_rel_orphans[:5],
            "fs_delta_orphan_count": len(fs_hash_orphans) + len(fs_rel_orphans),
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
        # --dry 不在这里判: Capture 构造(QbClient login x4)与 handshake 都发真实请求,
        # 零请求口径要求 dry 在 main() 里、Capture 构造之前分流(见 _dry_plan, 评审 #11)。
        self.handshake()
        if self.args.command == "snapshot":
            return self.run_snapshot()
        return self.run_full()

    def run_snapshot(self) -> int:
        """snapshot: 只出 T0 + files/trackers (分步调试用, 无录流 => 无闭合锚点)"""
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
            # 分两步时 session 已断、rid 无从续 => 两步之间的变化会丢; 记 gap=true(计划 §04)
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

    # self-test 只读本地语料目录, 不连 qB => 不需要凭据
    if args.command == "self-test":
        return _self_test_only(args)
    if not args.user or not args.password:
        raise SystemExit("[FATAL] 缺凭据: 传 --user/--pass, 或 --from-config <path> 只读解析")

    # --dry 的判定必须早于 Capture 构造(QbClient 构造即 login x4, 见 _dry_plan) —— 旧实现
    # 在 run_capture 里先 handshake 后判 dry, 4 个握手请求(+1 个计数请求)已经发出(评审 #11)。
    if args.command in ("capture", "snapshot", "record") and args.dry:
        return _dry_plan(args)
    cap = Capture(args)
    if args.command in ("capture", "snapshot", "record"):
        return cap.run_capture()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
