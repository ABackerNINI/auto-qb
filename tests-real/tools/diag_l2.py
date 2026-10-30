"""L2 诊断脚本(非用例): 打印双实例互传时每一环的现场, 用来定位 RM00-05 卡在哪。

用法: uv run python tests-real/tools/diag_l2.py [秒数]
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from lib import instances, net, torrent  # noqa: E402
from lib.tracker import FakeTracker  # noqa: E402

SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 90
WORK = HERE / ".work" / "diag_l2"


def conns(port: int) -> str:
    """看该端口上有没有 TCP 连接(用 netstat, 中文输出用 gbk 解)。"""
    r = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, encoding="gbk", errors="replace")
    hits = [ln.strip() for ln in r.stdout.splitlines() if f":{port} " in ln and "LISTENING" not in ln]
    return "; ".join(hits) or "(无)"


def tracker_view(q, ih: str) -> list:
    return [{"url": x.get("url"), "status": x.get("status"), "msg": x.get("msg"),
             "peers": x.get("num_peers"), "seeds": x.get("num_seeds"),
             "leeches": x.get("num_leeches"), "next": x.get("next_announce")}
            for x in q.trackers(ih) if str(x.get("url")).startswith("http")]


def main() -> None:
    q1, q2 = instances.make(instances.PRIMARY), instances.make(instances.SECONDARY)
    seed_port = int(q1.prefs()["listen_port"])
    host = net.local_host()
    print(f"[net] local_host={host} seed_port={seed_port} "
          f"36595={q1.connection_status()} 36596={q2.connection_status()}")

    # 测试实例带 1 KiB/s 下载限速, 互传 512KB 会被限速卡住 —— 诊断期间临时解除
    saved = {q.port: {k: q.prefs()[k] for k in ("dl_limit", "up_limit")} for q in (q1, q2)}
    for q in (q1, q2):
        q.set_prefs(dl_limit=0, up_limit=0)
    print(f"[prefs] 已解除限速(原值 {saved})")

    tr = FakeTracker(interval=5).start()
    tr.peers = [(host, seed_port)]
    print(f"[tracker] {tr.url} peers={tr.peers}")

    data = torrent.payload(size=512 * 1024, seed=b"auto-qb-rm00-l2")
    raw, ih = torrent.build("rm00-l2.bin", data, tr.url)
    src, dst = WORK / "seed", WORK / "leech"
    torrent.write_payload(str(src), "rm00-l2.bin", data)
    dst.mkdir(parents=True, exist_ok=True)

    for q in (q1, q2):
        try:
            if q.torrent(ih):
                q.delete(ih, delete_files=True)
        except Exception:
            pass

    try:
        q1.add_torrent(raw, savepath=str(src), paused=False, infohash_hint=ih)
        q2.add_torrent(raw, savepath=str(dst), paused=False, infohash_hint=ih)
        print(f"[add] infohash={ih}")
        t0 = time.time()
        while time.time() - t0 < SECONDS:
            n = int(time.time() - t0)
            for label, q in (("seed", q1), ("leech", q2)):
                t = q.torrent(ih) or {}
                print(f"[{n:3d}s {label}] state={t.get('state')} prog={t.get('progress')} "
                      f"conn={t.get('connections_count')} up={t.get('upspeed')} dl={t.get('dlspeed')} "
                      f"avail={t.get('availability')} seeds={t.get('num_seeds')} "
                      f"tr={json.dumps(tracker_view(q, ih), ensure_ascii=False)}")
            print(f"[{n:3d}s tracker] count={tr.count(ih)} ports={[a.get('port') for a in tr.announces]}")
            print(f"[{n:3d}s tcp {seed_port}] {conns(seed_port)}")
            if (q2.torrent(ih) or {}).get("progress", 0) >= 1.0:
                print("[done] leech 完成")
                break
            time.sleep(5)
    finally:
        for q in (q1, q2):
            try:
                q.delete(ih, delete_files=True)
            except Exception:
                pass
            q.set_prefs(**saved[q.port])
        tr.stop()


if __name__ == "__main__":
    main()
