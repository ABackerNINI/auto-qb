"""sim_qb 仿真主体: class SimQb(从 sim_qb.py 原样搬迁)"""
from __future__ import annotations

import json
import os
import random
import sys
import threading
import time

from sim_qb_core import *  # noqa: F401,F403

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
        # !外部删除必须经 sync/maindata 的 torrents_removed 报出去, 否则 auto-qb 永远看不
        # 到"种子没了" —— 快照里残留幽灵种子, D1/D2/D5 会全测成绿的假象(曾硬编码 [])。
        self.removed: list[str] = []  # 待上报的删除队列(sync 增量轮消费)
        self.removed_all: set[str] = set()  # 累计删除(判据用)
        self.manual_limits: dict[str, int] = {}  # S8: 手设单种限速(奇数 KiB/s), 收尾核对是否被改写
        self._ordered: list[dict] = []  # 全部种子(按生成序); --ramp 时按拍逐步暴露
        self._visible = 0
        # alltime 计数器先给零值: 语料档透传 _corpus_ss 用不到它们, 但 pump 的累加路径
        # 两档共用, 不先初始化的话语料档首拍就 AttributeError(真值由 _build_torrents 覆写)
        self._alltime_base_dl = 0
        self._alltime_base_ul = 0
        self._alltime_extra_ul = 0
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
        (计划 §07 硬条件3.)。不给初值的话, auto-qb 的首轮会在空表上跑 —— 所有文件都被当成缺失。
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
        # 帧自带**实测 dt_ms**, 累积成时间轴; 回放按墙钟 x 倍速推进游标。
        # !末帧(closure/mismatch)是校验锚点, **不吐给客户端**(吐了客户端会按全量轮重置一次)。
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
        """回放游标(录制时间轴上的毫秒位置) = 墙钟已过 x 倍速。speed<=0 => 静态回放(不推进)"""
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

        WARN: 顺序: 先合并窗口(本函数) -> 再由 `_snapshot_view` 叠 overlay。反了会让滞后边界落在错误的 t_seq 上。
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
        """实况状态 = 流状态 + 已到期的 overlay(立即生效侧)"""
        t = self.torrents.get(h)
        if t is None:
            return {}
        out = self._public(t)
        out.update(self._visible_fields(h, now if now is not None else time.time(), "info"))
        return out

    def _snapshot_view(self, h: str, now: float | None = None) -> dict:
        """流状态(snapshot view) = 流状态 + 已过 md 滞后线的 overlay"""
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
                # !组内成员必须共享 save_path 与**完全相同的文件相对路径**, 否则归不成组
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
            # !必须造**奇数 KiB/s** —— 项目约定 `utils.is_manual_speed_limit` 判定为
            # `(bytes // 1024) % 2 == 1`, 奇数值才被当作"用户手设、本程序不覆盖"。
            # 造偶数(初版写成 i*7+1, i 恒为奇数 => KiB 恒为偶数)会被正常覆盖 -> 假红。
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

        # alltime 计数器基值(P6 桩验证对齐真 qB server_state 键名 alltime_dl/alltime_ul):
        # 初值 = 建库时的历史量, 此后只增不减(种子删除不回退, 对齐真 qB alltime 语义);
        # 仿真库纯做种不下载 -> dl 恒定。进程重启(新 run)计数器从基值重新起步 —— auto-qb
        # 看到的就是"qB 重启 alltime 回退", 供采样器回落判重置路径做桩验证。
        self._alltime_base_dl = sum(t["downloaded"] for t in self._ordered)
        self._alltime_base_ul = sum(t["uploaded"] for t in self._ordered)
        self._alltime_extra_ul = 0

    def _expose(self, target: int) -> int:
        """把生成序里的前 target 个种子暴露给 auto-qb(P2 渐进灌入用)

        !新暴露的种子必须整条进脏集合: 增量轮只回 `dirty`, 不这么做的话 auto-qb 永远
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
            # !状态名必须是 qB 的 "error"(写成 "errored" 会被解析成 UNKNOWN -> is_errored 为假)
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
                up_gain = self.rng.randrange(1, 4 * 1024**2)
                patch = {
                    "upspeed": self.rng.randrange(0, 8 * 1024**2),
                    "dlspeed": 0,
                    "uploaded": t["uploaded"] + up_gain,
                    "seeding_time": t["seeding_time"] + 1,
                    "ratio": round(t["ratio"] + 0.001, 3),
                    "state": self.rng.choice(STATES_ACTIVE),
                    "last_activity": now,
                    "time_active": t["time_active"] + 1,
                }
                t.update(patch)
                self._alltime_extra_ul += up_gain  # alltime 只增不减(与种子删除解耦)
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

        WARN: 顺序: 先合并窗口(§08) -> **再**按滞后规则叠 overlay。反了会让滞后边界落在错误的 t_seq 上。
        静态回放时流不推进(帧已全量加载, 由 W4 的游标按时间轴吐), 所以这里只处理 overlay。
        """
        with self.lock:
            self.stats["sync_rounds"] += 1
            # WARN: 顺序: 先合并窗口(§08) -> 再叠 overlay 的可见性(§07)。
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
        """给 FS mock 的"当前磁盘状态"(计划 §07 硬条件3.: 时间源归播放器)。

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
            # 键名对齐真 qB server_state(alltime_dl/alltime_ul): auto-qb 采样器(plan
            # 26-10-03-0946 §03.2)按真键名读, 旧名 all_time_* 会让全局系列恒 null。
            # dl 恒定(纯做种), ul 随 pump 单调增长; 进程重启回退到基值 -> 回落判重置可验。
            "alltime_dl": self._alltime_base_dl,
            "alltime_ul": self._alltime_base_ul + self._alltime_extra_ul,
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
                    # B3 按「一次命令」核账: 本命令声明的目标文件数 = 它要删的文件数
                    # (与 delete_torrents 同口径; 写死 1 会让 >2 文件的种子必被拒成 403 假红)
                    paths = self.file_paths_of(t)
                    self.safe_delete_files(paths, len(paths))
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
