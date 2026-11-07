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

!R 盘即真实下载盘: 删除动作只在 <run>/fs/ 内生效, 受 B1-B4 四道边界校验约束,
  任一不过即拒绝(越界删除是不可逆的真实数据损失)。

设计要点见 memory-bank/plans/26-09-19-1433-sim-client-5000-plan.html 第 06/07/08 节。
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

from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from sim_qb_core import *  # noqa: F401,F403
from sim_qb_core import _last_event, _norm, _rand_hash  # noqa: F401
from sim_qb_model import SimQb  # noqa: F401
from sim_qb_server import Handler, SimServer, fallback_root, prepare_root  # noqa: F401
from sim_qb_cli import (  # noqa: F401
    CONFIG_TMPL, RULES_TMPL, SYNTHETIC_TRACKERS, TRACKER_RULES_TMPL, WEB_TMPL, _GENERIC_TAG_HINTS, build_parser,
    corpus_tracker_section, create_sim, emit_config, make_run_dir, parse_spec, prune_runs, run_load_engine
)


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
    # (本自检要真起 HTTP + 真装 qbittorrentapi, CI 从不执行 => 交给 pytest 验, 覆盖两平台)

    # B3 数量上限 / D4 删组文件: 均已**下沉**进 tests/test_sim_corpus.py ——
    #   test_safe_delete_rejects_bulk_over_declared(B3, 钉"超 2 倍要拒"与"恰好 2 倍不拒"两侧)
    #   test_delete_group_files_removes_them_from_disk(D4, 走**合成档**: 语料档 mock 模式磁盘上
    #   没文件, `_walk()` 前后都是 0 => 判据恒假, 故该用例显式断言 before > 0)
    # 本自检要真起 HTTP + 真装 qbittorrentapi, CI 从不执行 => 交给 pytest 验, 覆盖两平台。

    srv.shutdown()
    print("[自检] " + ("全部通过 [x]" if ok else "存在失败 x"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
