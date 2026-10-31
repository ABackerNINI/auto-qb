"""假种子命令行 —— 造 / 加 / 看 / 删, 供手工探索与排障(不参与用例验收)。

与用例里那套的区别: 用例由 pytest fixture 起一个**活到用例结束**的伪 tracker, 断言在用例里闭环;
这里是**短命进程**, 起不了常驻 tracker, 所以默认造出来的种子**不带 announce**(纯本地做种, 零流量)。
需要 announce 的场景请在用例里用 `FakeTracker`, 或自己起一个常驻 tracker 再用 `--tracker` 指过去。

安全边界(与用例同一套):
  - 端口只认白名单 36595/36596, 且镜像路径必须在 `D:\\Programs\\qBittorrent-testing*` 下(guard 核);
  - 加种子前先把**真实种子全部暂停**并核一遍;
  - 自造种子一律打 `real-fake` 标签 —— list / rm / clean 只认这个标签, 绝不碰真实种子;
  - 自造的数据与 .torrent 只能落在 `tests-real/.work/` 下(越界拒跑)。

用法示例:
  uv run python tests-real/seed.py add --yes                             # 默认 256K 伪随机, 加到 36596 并做种(零外连)
  uv run python tests-real/seed.py add --size 512K --pattern text --yes   # 可读文本行, 便于人眼看/手改
  uv run python tests-real/seed.py add --size 2G --pattern zeros --yes    # 大种子自动落 R:(内存盘, 免写盘代价)
  uv run python tests-real/seed.py add --size 3G --no-data --yes          # >2G 只造元数据: 不落盘就不拦
  uv run python tests-real/seed.py add --size 3G --allow-huge --reason "测限速曲线" --yes   # 真落盘要显式授权+原因
  uv run python tests-real/seed.py add --size 8M --no-data --yes          # 只有元数据, 不占磁盘
  uv run python tests-real/seed.py add --from D:/tmp/sample.bin --yes     # 拿现成文件造种子
  uv run python tests-real/seed.py list
  uv run python tests-real/seed.py rm --all --yes
  uv run python tests-real/seed.py clean --yes

落点口径: **默认 KB 级小种子**(256K), 落仓库内 `tests-real/.work/`(gitignore, 随用例一起清);
只有 ≥ 32M 的大种子才落 `R:/qbt-fake/` —— R 盘是内存盘, 写多少都不心疼, 但**重启即清空**,
所以大种子只当次会话有效(要长期留着就显式 `--dir` 指到磁盘)。
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lib import guard, instances, torrent  # noqa: E402

WORK = HERE / ".work" / "seeds"
RAM_ROOT = Path("R:/qbt-fake")  # R 盘是内存盘: 大种子写这里, 免写盘代价(重启即清空)
BIG_SIZE = 32 * 1024 * 1024  # ≥ 32M 才算"大种子", 默认落内存盘
HUGE_SIZE = 2 * 1024**3  # > 2G 原则上不许造: 要 --allow-huge + --reason 显式授权
DEFAULT_SIZE = "256K"  # 默认 KB 级: 造种子是为了看状态, 不是为了塞满盘
ALLOWED_ROOTS = (HERE / ".work", RAM_ROOT)
TAG = "real-fake"
DEFAULT_PORT = instances.SECONDARY  # 36596: 空库, 拿它当草稿本


# ---------------------------------------------------------------- 小工具
def parse_size(text: str) -> int:
    """`8M` / `1.5G` / `512k` / `1048576` → 字节数(1024 进制)。"""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kmgt]?)i?b?\s*", text, re.I)
    if not m:
        raise SystemExit(f"看不懂的大小 {text!r}; 例: 8M / 1.5G / 512k / 1048576")
    return int(float(m.group(1)) * {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3, "t": 1024**4}[m.group(2).lower()])


def fmt_size(n: float) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024 or unit == "T":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}B"


def _allowed(path: Path) -> Path:
    """落点白名单: 自造物只许进 `tests-real/.work/`(仓库内, gitignore) 或 `R:/qbt-fake/`(内存盘)。"""
    p = path.resolve()
    for root in ALLOWED_ROOTS:
        if str(p).lower().startswith(str(root.resolve()).lower()):
            return p
    raise SystemExit(f"拒绝: {p} 不在允许的落点之下 —— 只认 {[str(r) for r in ALLOWED_ROOTS]}")


def _ram_ready() -> bool:
    return RAM_ROOT.anchor != "" and Path(RAM_ROOT.anchor).exists()


def _free_bytes(path: Path) -> int:
    """目标盘剩余空间(路径还没建时往上找已存在的祖先)。"""
    p = path
    while not p.exists() and p.parent != p:
        p = p.parent
    try:
        return shutil.disk_usage(p).free
    except OSError:
        return 0


def _pick_dir(size: int, name: str) -> tuple[Path, str]:
    """按大小挑落点: 小种子进仓库, 大种子进内存盘。返回 (目录, 一句话理由)。"""
    stem = Path(name).stem
    if size >= BIG_SIZE and _ram_ready():
        return RAM_ROOT / stem, f"{fmt_size(size)} ≥ {fmt_size(BIG_SIZE)} ⇒ 落 R:(内存盘, 免写盘代价, 重启即清空)"
    if size >= BIG_SIZE:
        return WORK / stem, f"{fmt_size(size)} 偏大但 R: 不可用 ⇒ 退回仓库 .work(会真写盘)"
    return WORK / stem, f"{fmt_size(size)} 是小种子 ⇒ 落仓库 .work(gitignore, 随用例一起清)"


def _connect(port: int, pause_real: bool):
    rep = guard.check_port(port)
    qb = instances.make(port)
    status = guard.check_online(qb)
    # 只暂停/保护**真实**种子; 自造种子(real-fake)由本命令自己管, 不要顺手改它的状态
    real = guard.snapshot(qb, skip_tags=(TAG, )) if pause_real else {}
    return qb, rep, status, real


def _fakes(qb) -> list[dict]:
    # 成员判断走 guard.tag_set(strip 版): qB 多标签是「, 」连接, 裸 split(",") 会漏(issue 26-10-31-1215)
    return [t for t in qb.torrents() if TAG in guard.tag_set(t)]


SETTLED = {"stalledUP", "stalledDL", "pausedUP", "pausedDL", "missingFiles", "error", "uploading", "downloading"}


def _settle(qb, infohash: str, timeout: float = 20.0) -> dict:
    """等种子走完 check/alloc, 拿到稳定态再打印 —— 否则看到的是 checkingResumeData, 白等一场。"""
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        last = qb.torrent(infohash) or {}
        if last.get("state") in SETTLED:
            return last
        time.sleep(0.5)
    return last


def _match(qb, name: str | None, infohash: str | None, every: bool) -> list[dict]:
    fakes = _fakes(qb)
    if every:
        return fakes
    hits = [t for t in fakes if (name and t["name"] == name) or (infohash and t["hash"].startswith(infohash))]
    if not hits:
        raise SystemExit(f"没找到: name={name!r} hash={infohash!r}(用 list 看有哪些)")
    return hits


# ---------------------------------------------------------------- add
def cmd_add(args) -> int:
    if args.from_path:
        src = Path(args.from_path)
        if not src.is_file():
            raise SystemExit(f"--from 指向的文件不存在: {src}")
        name = args.name or src.name
        size = src.stat().st_size
        datadir = Path(args.dir).resolve() if args.dir else src.resolve().parent
        why = "沿用源文件所在目录(不动原文件)"
        pattern = "(已有文件)"
    else:
        size = parse_size(args.size)
        name = args.name or f"fake-{args.size.upper()}-{args.pattern}.bin"
        pattern = args.pattern
        if args.dir:
            datadir, why = _allowed(Path(args.dir)), "显式 --dir"
        else:
            datadir, why = _pick_dir(size, name)

    stem = Path(name).stem
    tpath = _allowed(Path(args.out) if args.out else WORK / f"{stem}.torrent")
    datafile = datadir / name
    salt = args.salt or name

    # > 2G 原则上不许造: 停下来要授权 + 原因(写文件前就拦, 不留半截垃圾)
    if size > HUGE_SIZE:
        if args.from_path:
            print(
                f"[warn] 源文件 {fmt_size(size)} 超过 {fmt_size(HUGE_SIZE)} —— 本次不创建文件, 只是给它造种子"
                f"(qB 校验会读满 {fmt_size(size)})"
            )
        elif args.no_data:
            print(f"[warn] 只造元数据(--no-data), 不写 {fmt_size(size)} 的数据文件")
        elif not args.allow_huge:
            raise SystemExit(
                f"暂停, 等待授权: 要创建 {fmt_size(size)}, 超过上限 {fmt_size(HUGE_SIZE)}。\n"
                f"  原则上不造这么大的文件 —— 占盘/占内存盘、qB 校验要读满一遍、清理最容易漏。\n"
                f"  先想清楚是否真需要:\n"
                f"    · 只想要一个「大尺寸」的种子看状态 ⇒ 用 --no-data(不落盘, 零代价)\n"
                f"    · 只是要测分块/进度条 ⇒ KB~MB 级就够, 默认 256K\n"
                f"  确实必须落盘, 请说明原因并显式授权: --allow-huge --reason \"<为什么要这么大的文件>\""
            )
        elif not args.reason.strip():
            raise SystemExit(
                f"暂停, 等待授权: --allow-huge 必须配 --reason \"<原因>\" —— 授权要留痕, 否则等于默认允许。\n"
                f"  例: --allow-huge --reason \"RM07 测 3G 单文件的限速曲线\""
            )
        else:
            print(f"[warn] 已授权创建 {fmt_size(size)} 的大文件(> {fmt_size(HUGE_SIZE)}): {args.reason.strip()}")
            print(f"[warn] 用完请 rm/clean; R: 重启即清空, 落磁盘的不会自己消失")

    print(f"[plan ] 大小 {fmt_size(size)}({size} B) · 生成方式 {pattern}" + (f" · salt={salt}" if not args.from_path else ""))
    print(f"[plan ] 落点 {datadir} —— {why}")
    print(f"[plan ] 数据 {datafile if not args.no_data else '(不落盘 --no-data ⇒ 永远下不完, 不占磁盘)'}")
    print(f"[plan ] 种子 {tpath}")
    print(f"[plan ] 加入 {args.port} {'暂停(零流量, 但进度停在 0)' if args.paused else '启动(默认, 做种态 stalledUP)'}"
          f" · 标签 {TAG}")
    if not args.no_data and not args.from_path:
        free = _free_bytes(datadir)
        if size > free * 0.9:
            raise SystemExit(f"拒绝: 要写 {fmt_size(size)}, 而 {datadir.drive} 只剩 {fmt_size(free)}(留 10% 余量)")
        print(f"[plan ] 目标盘剩余 {fmt_size(free)}")

    if not args.yes:
        print("[dry-run] 加 --yes 才真造真加(会写文件并改 qB 状态)")
        return 0

    qb = rep = status = None
    if not args.no_add:
        qb, rep, status, real = _connect(args.port, pause_real=True)
        print(f"[guard] {args.port} pid={rep['pid']} {status} 真实种子 {len(real)} 个已暂停(全程不会碰)")

    # 1) 内容
    if args.from_path:
        pass  # 用现成文件, 不动它
    elif args.no_data:
        datadir.mkdir(parents=True, exist_ok=True)  # savepath 得存在, 但文件不写 ⇒ missingFiles
    else:
        torrent.write_file(str(datafile), size, args.pattern, salt)

    # 2) 种子
    if args.no_data:
        raw, ih = torrent.build_stream(name, size, args.pattern, salt, args.tracker, args.piece_len)
    else:
        raw, ih = torrent.build_from_path(str(datafile), name, args.tracker, args.piece_len)
    tpath.parent.mkdir(parents=True, exist_ok=True)
    tpath.write_bytes(raw)
    print(f"[ok] infohash={ih}")
    print(f"[ok] .torrent → {tpath}")

    if args.no_add:
        print("[hint] --no-add: 只造了文件和 .torrent, 没有加入任何实例")
        return 0

    # 3) 入库(幂等: 同 salt ⇒ 同 infohash, 先清再建)
    try:
        if qb.torrent(ih):
            qb.delete(ih, delete_files=False)
        qb.add_torrent(raw, savepath=str(datadir), paused=args.paused, tags=TAG, infohash_hint=ih)
    except Exception as exc:
        raise SystemExit(f"加入失败: {exc}") from None

    t = _settle(qb, ih)
    print(
        f"[ok] state={t.get('state')} progress={t.get('progress')} "
        f"size={fmt_size(int(t.get('size') or 0))} save_path={t.get('save_path')}"
    )
    if args.no_data:
        print("[hint] --no-data: 只造了元数据, 没有数据文件 ⇒ 永远停在 progress 0(实测不会进 missingFiles)")
    elif not args.tracker and not args.paused:
        print("[hint] 没有 announce ⇒ 即使做种态也是零外连(upspeed 恒 0); 需要真流量请用 L2 用例那套")
    return 0


def cmd_list(args) -> int:
    qb, rep, status, _ = _connect(args.port, pause_real=False)
    fakes = _fakes(qb)
    all_t = qb.torrents()
    print(f"[{args.port}] pid={rep['pid']} {status} 共 {len(all_t)} 个种子, 其中自造 {len(fakes)} 个(标签 {TAG})")
    if not fakes:
        print("(没有自造种子; 用 add 造一个)")
        return 0
    print(f"{'infohash':<10}{'name':<30}{'size':>9}  {'progress':>8}  {'state':<14}save_path")
    for t in sorted(fakes, key=lambda x: x["name"]):
        print(
            f"{t['hash'][:8]:<10}{t['name'][:29]:<30}{fmt_size(t['size']):>9}  "
            f"{t['progress'] * 100:7.1f}%  {t['state']:<14}{t.get('save_path', '')}"
        )
    return 0


def cmd_rm(args) -> int:
    qb, rep, status, _ = _connect(args.port, pause_real=False)
    hits = _match(qb, args.name, args.hash, args.all)
    print(f"[{args.port}] pid={rep['pid']} {status}; 命中 {len(hits)} 个自造种子:")
    for t in hits:
        print(f"  - {t['hash'][:8]} {t['name']} {fmt_size(t['size'])} {t['state']}")
    if not hits:
        return 0
    if not args.yes:
        print("[dry-run] 加 --yes 才真删(默认连数据文件一起删; --keep-data 保留)")
        return 0
    for t in hits:
        qb.delete(t["hash"], delete_files=not args.keep_data)
        print(f"[ok] 删除 {t['hash'][:8]} {t['name']}{'' if args.keep_data else ' + 文件'}")
    return 0


def _clean_root(root: Path, yes: bool) -> int:
    if not root.exists():
        print(f"[skip] {root} 不存在")
        return 0
    files = [p for p in root.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    print(f"[plan ] {root}: {len(files)} 个文件, 共 {fmt_size(total)}")
    for p in files[:20]:
        print(f"  - {p.relative_to(root)}")
    if len(files) > 20:
        print(f"  ... 还有 {len(files) - 20} 个")
    if not yes:
        return 0
    for p in files:
        p.unlink()
    # 空目录也要收掉(rm 已经把文件删了的情况, 这里只剩壳子)
    for d in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda x: -len(x.parts)):
        try:
            d.rmdir()
        except OSError:
            pass
    print(f"[ok] 已清空 {root}")
    return 0


def cmd_clean(args) -> int:
    roots = [_allowed(Path(args.dir))] if args.dir else [r for r in ALLOWED_ROOTS if r.exists()]
    for root in roots:
        _clean_root(root, args.yes)
    if not args.yes:
        print("[dry-run] 加 --yes 才真删(只动 tests-real/.work/ 与 R:/qbt-fake/)")
    else:
        print("[hint] qB 里的种子条目请用 rm 删, clean 不碰 qB")
    return 0


# ---------------------------------------------------------------- 入口
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="real-seed", description="假种子: 造 / 加 / 看 / 删")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="造数据 + 造 .torrent + 加入实例")
    p.add_argument(
        "--size",
        default=DEFAULT_SIZE,
        help=f"大小, 支持 256K / 8M / 1.5G / 裸字节(默认 {DEFAULT_SIZE}, KB 级就够看状态); "
        f"给了 --from 就不用它; ≥{fmt_size(BIG_SIZE)} 默认落 R: 内存盘"
    )
    p.add_argument("--from", dest="from_path", default="", help="拿现成文件造种子(大小自动取文件, 不动原文件)")
    p.add_argument(
        "--pattern",
        default="random",
        choices=torrent.PATTERNS,
        help="数据生成方式: random(默认, 由 salt 播种的确定性伪随机) / zeros(全零) / text(可读文本行)"
    )
    p.add_argument("--salt", default="", help="混进数据的盐; 默认取文件名 ⇒ 同参数重跑得同 infohash(幂等)")
    p.add_argument("--name", default="", help="种子里的文件名(默认 fake-<size>-<pattern>.bin)")
    p.add_argument(
        "--dir", default="", help=f"数据落点(只认 {ALLOWED_ROOTS[0]} 与 {ALLOWED_ROOTS[1]}; "
        f"不给则小种子进 .work、大种子进 R:)"
    )
    p.add_argument("--out", default="", help=".torrent 落点(默认 tests-real/.work/seeds/<stem>.torrent)")
    p.add_argument("--tracker", default=None, help="announce URL; 不给则种子不带 announce(纯本地做种)")
    p.add_argument("--piece-len", type=int, default=torrent.PIECE_LEN, help=f"分块大小(默认 {torrent.PIECE_LEN})")
    p.add_argument("--no-data", action="store_true", help="只造种子不落数据(永远 progress 0, 不占磁盘) —— 用来试「缺数据」的界面/逻辑")
    p.add_argument("--no-add", action="store_true", help="只造文件和 .torrent, 不加入实例(不碰 qB)")
    p.add_argument(
        "--allow-huge", action="store_true", help=f"授权创建 > {fmt_size(HUGE_SIZE)} 的文件(必须同时给 --reason); 原则上不该用"
    )
    p.add_argument("--reason", default="", help="授权原因, 与 --allow-huge 配套, 会打印出来留痕")
    p.add_argument("--paused", action="store_true", help="加入后保持暂停(默认启动: 做种态 stalledUP; 无 announce ⇒ 仍是零流量)")
    p.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        choices=list(guard.WHITELIST_PORTS),
        help=f"加到哪个实例(默认 {DEFAULT_PORT})"
    )
    p.add_argument("--yes", action="store_true", help="真造真加(默认 dry-run)")
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("list", help="列出实例里的自造种子(标签 real-fake)")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, choices=list(guard.WHITELIST_PORTS))
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("rm", help="删掉自造种子(连数据一起)")
    p.add_argument("--name", default=None)
    p.add_argument("--hash", default=None, help="infohash 前缀即可")
    p.add_argument("--all", action="store_true", help="删掉全部 real-fake 种子")
    p.add_argument("--keep-data", action="store_true", help="保留数据文件")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, choices=list(guard.WHITELIST_PORTS))
    p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_rm)

    p = sub.add_parser("clean", help="清掉 tests-real/.work 与 R:/qbt-fake 下的数据与 .torrent(不碰 qB)")
    p.add_argument("--dir", default="", help="只清这一处(必须在允许的落点之下); 不给则两处都扫")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_clean)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
