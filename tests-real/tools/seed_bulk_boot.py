"""S0/S3 批量假种子(计划 26-11-18-0259: 重启后 WebUI 首份数据取证)。

为什么不用 real.seed 逐个造: 210 枚 × 每枚一个短命进程(uv 启动 + guard 连接 + settle)
≈ 分钟级白耗; 本脚本单进程批量走同一套 lib(guard/instances/torrent), 安全边界与
real.seed 完全一致(real-fake 标签 / .work 落点白名单 / 真实种子先暂停)。

种子形状(对准用户报告「约 210 种子」的库形态):
  - 210 枚单文件假种子, 256K random, 每枚独立目录独立文件名(零数据互踩);
  - 名字按剧集形状造(Boot Show NNN S01E### 1080p.bin), 105 剧 × 每剧 2 集 ——
    shows 视图与 groups 视图(每枚单成员组)都有非空数据面;
  - announce 统一 http://127.0.0.1:1/announce(死端口, 连接即被拒, 零 DNS 零外连,
    RM08-14/RM10 同款先例)—— 派生配置的 trackers 段 domains=[127.0.0.1] 命中,
    否则 added 种子匹配不到 tracker conf 会被跳过, 归组管线(被测对象)整段不跑;
  - 无 announce 联系失败只在 qB 侧记 tracker 错误, 不进产品测量窗。

用法:
  uv run python tests-real/tools/seed_bulk_boot.py --count 210 --yes   # 默认副实例(空库草稿本)
  uv run python tests-real/tools/seed_bulk_boot.py --count 210          # 缺省 dry-run
种子留存口径(用户拍板): S0 造完留在实例里, S3 同批复测后才清 —— 本脚本不清场。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # tests-real/ —— 复用 lib 与 seed.py 的常量

from lib import guard, instances, torrent  # noqa: E402
from seed import SETTLED, TAG, parse_size  # noqa: E402 —— 标签/稳定态/大小解析单点

DATA_ROOT = HERE.parent / ".work" / "seeds" / "boot"  # 数据落点(.work 白名单内, gitignored)
ANNOUNCE = "http://127.0.0.1:1/announce"  # 死端口: 连接即拒, 零 DNS 零外连(RM10 同款口径)
SIZE = 256 * 1024  # 256K: KB 级够看状态, 与 real.seed 默认一致


def seed_name(idx: int) -> str:
    """第 idx 枚(0 基)的种子名: 105 剧 × 每剧 2 集(shows 视图非空的最小形状)。"""
    return f"Boot Show {idx // 2:03d} S01E{idx + 1:03d} 1080p.bin"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="S0/S3 批量假种子(210 枚剧集形状)")
    ap.add_argument("--count", type=int, default=210)
    ap.add_argument("--size", default="256K")
    ap.add_argument("--port", type=int, default=instances.SECONDARY, choices=list(guard.WHITELIST_PORTS))
    ap.add_argument("--yes", action="store_true", help="真造真加(默认 dry-run)")
    args = ap.parse_args(argv)

    size = parse_size(args.size)
    rep = guard.check_port(args.port)
    qb = instances.make(args.port)
    status = guard.check_online(qb)
    real = guard.snapshot(qb, skip_tags=(TAG, ))
    print(f"[guard] {args.port} pid={rep['pid']} {status} 真实种子 {len(real)} 个已暂停(全程不碰)")
    existing = [t for t in qb.torrents() if TAG in guard.tag_set(t)]
    print(f"[plan ] 目标 {args.count} 枚 × {args.size}, 已有自造 {len(existing)} 枚; 数据落 {DATA_ROOT}")
    if not args.yes:
        print("[dry-run] 加 --yes 才真造真加")
        return 0

    t0 = time.perf_counter()
    made = 0
    for idx in range(args.count):
        name = seed_name(idx)
        datadir = DATA_ROOT / f"e{idx + 1:03d}"
        datafile = datadir / name
        datafile.parent.mkdir(parents=True, exist_ok=True)
        torrent.write_file(str(datafile), size, "random", name)
        raw, ih = torrent.build_from_path(str(datafile), name, ANNOUNCE)
        cur = qb.torrent(ih)
        if cur:  # 幂等: 同名同内容同 infohash(重跑先清再建, real.seed 同款口径)
            qb.delete(ih, delete_files=False)
            time.sleep(0.1)
        qb.add_torrent(raw, savepath=str(datadir), tags=TAG, infohash_hint=None)
        made += 1
        if made % 30 == 0:
            print(f"[..] {made}/{args.count} ({time.perf_counter() - t0:.0f}s)")
    inject_s = time.perf_counter() - t0

    # 收尾核净: 全部 real-fake 种子到稳定态; stopped 的补一次 start(qB 5.2 加种子偶发 stoppedUP;
    # SETTLED 不含 qB 5.2 的 stoppedUP/stoppedDL 命名 —— stopped 集合与 unsettled 有交集, 先
    # resume 再继续等, 不能用「settled 全空」当 resume 前置)
    deadline = time.time() + 120
    while time.time() < deadline:
        fakes = [t for t in qb.torrents() if TAG in guard.tag_set(t)]
        unsettled = [t for t in fakes if t["state"] not in SETTLED]
        stopped = [t for t in fakes if t["state"].startswith("stopped")]
        if not unsettled and not stopped:
            break
        if stopped:
            qb.resume("|".join(t["hash"] for t in stopped))
        time.sleep(1.0)
    fakes = [t for t in qb.torrents() if TAG in guard.tag_set(t)]
    states: dict[str, int] = {}
    for t in fakes:
        states[t["state"]] = states.get(t["state"], 0) + 1
    print(f"[ok] 新造 {made} 枚, 实例内自造共 {len(fakes)} 枚, 注入耗时 {inject_s:.1f}s")
    print(f"[ok] 状态分布: {states}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
