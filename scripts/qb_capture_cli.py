"""qb_capture CLI 共享 helper: 配置解析 / 参数构造 / 离线自检。

CLI 入口( main + __main__ )只在 qb_capture.py —— 本文件不再有 main,
勿在此构造 Capture(符号在 qb_capture.py, 引用即 NameError)。
"""
from __future__ import annotations

import argparse
import gzip
import json
import logging
from pathlib import Path

from qb_capture_core import *  # noqa: F401,F403
from qb_capture_core import _SNAPSHOT_FIELDS, REQUIRED_TORRENT_FIELDS  # noqa: F401


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
