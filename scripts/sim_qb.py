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
        self.fs_root = os.path.join(self.run_dir, "fs")
        os.makedirs(self.fs_root, exist_ok=True)

        self._build_torrents()
        self._materialize()
        self._snapshot("fs-before.txt")

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

    def _public(self, t: dict) -> dict:
        return {k: v for k, v in t.items() if not k.startswith("_")}

    def server_state(self) -> dict:
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
            return self._json([sim._public(t) for t in sim.torrents.values()])
        if route == "torrents/files":
            t = sim.torrents.get(params.get("hash"))
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
    p.add_argument("--fs-materialize", type=int, default=-1, help="-1=全量(默认); 0=不建树")
    p.add_argument("--fs-file-size", type=int, default=4096)
    p.add_argument("--keep-last", type=int, default=10)
    p.add_argument("--emit-config", action="store_true", help="在 run 目录生成匹配的 config.yml")
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
    skip_checking_tag: zSkipChecked
    hr:
        add_tag: ""
        add_category: "!!HR${{required_seeding_time}}!!"
        overwrite_category: false
        add_tag_for_satisfied: ""
        add_category_for_satisfied: --HR${{required_seeding_time}}--
        overwrite_category_for_satisfied: false
    grouping:
        enabled: true
        missing_tag: MISSING
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
        ptfans_cc:
            domains:
                - ptfans.cc
            tags:
                - PTFans
{tracker_rules}        hhanclub:
            domains:
                - tracker.hhanclub.net
            tags:
                - HHan
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
                tracker_rules=TRACKER_RULES_TMPL if with_rules else ""
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
        pruned = prune_runs(root, args.keep_last)
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

    # B2 逃逸: 目标在 fs_root 之外必须被拒
    outside = os.path.join(os.path.dirname(sim.fs_root), "outside.txt")
    with open(outside, "w") as f:
        f.write("x")
    try:
        sim.safe_delete_files([outside], 1)
        print("[自检] B2 逃逸拦截      : 未拦截 ✗")
        ok = False
    except BoundaryViolation:
        print("[自检] B2 逃逸拦截      : 已拦截 ✓")
    os.remove(outside)

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
