"""生成物集合的**唯一声明处** —— 一次跑齐全部索引生成器, 并对外声明它们负责哪些文件。

三个用途(计划 memory-bank/plans/26-10-03-1544-plan-sync-generated-index-autoresolve.html):
    无参       依次重建全部生成物(等价于 `commands run kb.index`)
    --list     打印全部生成物路径(仓库相对 posix, 一行一个) —— **sync 自动化解白名单的唯一来源**
    --check    全部自证: 磁盘内容 == 生成结果; 漂移即 rc=1 并逐条报路径
    --safety   回答「无参跑我是否即真动作」—— 冒烟闸门用它决定要不要给本脚本加 `--help`

为什么要有它: `_index.md` 这类生成物的合并冲突解法是「任取一侧 + 重跑」, 而「哪些文件可重跑」
必须只有**一处声明**。sync 从 `--list` 取白名单, 提交闸门与重建入口也调它 —— 若各处再抄一份清单,
迟早各自演化, 而「哪份才生效」不写在清单旁边(见 scripts/check_command_drift.py)。

数据源与生成器完全一致(它是纯函数: 只读工作树里的手写文件, 不读 git / 时间戳 / 环境),
所以「任取一侧 + 重跑」必然收敛, 不需要任何文本合并。

用法(从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/gen_all.py                     重建全部生成物
    python <skill-dir>/scripts/gen_all.py --list              只打印路径, 不写文件
    python <skill-dir>/scripts/gen_all.py --check             只比对, 不一致则退出码 1
    python <skill-dir>/scripts/gen_all.py --safety            只回答冒烟安全性, 不碰文件
    python <skill-dir>/scripts/gen_all.py --root <dir> --mb-dir <dir>   覆盖探测
退出码: 0 成功 / 1 校验漂移
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import find_root, gen_cmd, rel_posix, resolve_mb_dir  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent

# 生成器脚本 → 所属 skill 名。**集合的唯一声明处** —— 新增一个生成器只改这里。
# (2026-11-08 重构 W3: 生成集合收缩为 gen_kb_index 一家, 只服务 pitfalls 的 8 个 `_index`
# —— tasks/plans/reports/issues 的索引与归档清单已随低价值层移除退役, D4/D5,
# 三个生成器脚本本体与其调用点同批退役; 见 `_common.rebuild_index` 同款收口。)
GENERATORS = (("memory-bank", "gen_kb_index.py"), )

# 「无参即真动作」的生成器 —— **同步的生成物自动化解只准碰这一类**。
# 判据是"无参即真动作"(碰巧当前也是"纯确定性"): 这类脚本的默认动作就是重建全部生成物,
# 所以「任取一侧 + 重跑 + 自证」在构造上收敛(生成器是纯函数, 只读工作树里的手写文件)。
# ! 新增一个无参即重建的生成器却忘了登记 → 它的冲突**不会被自动化解**, 表现是与现状一致的
#   失败行(保守侧, 不猜不丢内容); 多登记一个非无参即动作的 → 冲突时**静默丢手写内容**,
#   这才是危险方向, 所以登记前先问「无参跑一次, 它是不是把全部生成物都写了一遍」。
PARAMETERLESS_ACTION_GENERATORS = frozenset({"gen_all.py"})


def _mb_module(name: str):
    """载入 memory-bank skill 自身的生成器(与本脚本共用同一份 `_common`)。"""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    return __import__(name)


def _stale_volume_pages(mb: Path, outputs: dict[Path, str]) -> list[Path]:
    """磁盘上残留、生成结果已不需要的分卷页 (`_index-<n>.md`) —— 主题变少/改名后的残留。

    只认 `_index-<n>.md`(`_common.INDEX_VOLUME_RE`); 手写 `_index-notes.md` 之类不在删除范围。
    """
    vol_re = _mb_module("_common").INDEX_VOLUME_RE
    return [p for p in mb.rglob("_index-*.md") if vol_re.search(p.name) and p not in outputs]


def collect(root: Path, mb: Path) -> dict[Path, str]:
    """{生成物绝对路径: 应写内容} —— 重建 / `--list` / `--check` 三条路径**共用同一实现**。

    这样 `--list` 声明的集合与真正写出的集合在构造上恒等; 若两者能各自演化, 白名单就可能
    列出一个其实不是生成物的路径, sync 会据此静默丢弃手写内容 —— 这是本设计最不能出的错。

    2026-11-08 重构(W3): tasks/plans/reports/issues 的主索引与归档清单已随低价值层移除
    (D4/D5, git 历史即冷库), 生成集合收缩为 gen_kb_index 一家(conventions/testing 亦无
    `_index` 生态, 见 `_common.EXCLUDED_DIRS`), 三个生成器脚本本体与其调用点已同批退役。
    """
    out: dict[Path, str] = {}

    out.update(_mb_module("gen_kb_index").build_all(root, mb))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="打印全部生成物路径(一行一个), 不写文件")
    parser.add_argument("--check", action="store_true", help="只比对, 不写文件 (不一致则退出码 1)")
    parser.add_argument("--safety", action="store_true", help="回答「无参跑我是否即真动作」(冒烟过滤用; 不读文件不写文件)")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args(argv)

    # ! 必须在任何动作之前: 冒烟闸门会给脚本加 `--help` 探活, 而"无参即真动作"的脚本若
    #   把陌生参数当无参处理, 就会**真的重建一遍**(闸门在只读检查阶段写文件)。
    #   本脚本自己就是这一类, 这里的 --safety / --help 答案只来自常量, 不碰文件系统。
    if args.safety:
        kind = "action-without-args" if Path(__file__).name in PARAMETERLESS_ACTION_GENERATORS else "read-only-default"
        print(f"{Path(__file__).name}: {kind}")
        return 0

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)

    outputs = collect(root, mb)

    if args.list:
        for path in sorted(outputs, key=lambda p: rel_posix(p, root)):
            print(rel_posix(path, root))
        return 0

    if args.check:
        drifted = [p for p, want in outputs.items() if (p.read_text(encoding="utf-8") if p.exists() else "") != want]
        stale = _stale_volume_pages(mb, outputs)
        if drifted or stale:
            for path in sorted(drifted, key=lambda p: rel_posix(p, root)):
                sys.stderr.write(f"{rel_posix(path, root)} 与生成结果不一致\n")
            for path in sorted(stale, key=lambda p: rel_posix(p, root)):
                sys.stderr.write(f"{rel_posix(path, root)} 是过期分卷页 (生成结果已不需要)\n")
            sys.stderr.write(f"请运行 {gen_cmd(root, 'gen_all.py')} 重建\n")
            return 1
        return 0

    # ! newline="\n" 必须显式给: write_text 的 newline 默认 None ⇒ 按 os.linesep 翻换行, Windows 上把
    #   `\n` 写成 CRLF —— 生成物落进仓库就是一批"纯行尾噪音"的 modified(坑档 pitfalls/git/editing-traps.md)。
    #   本脚本的立身前提是"生成器是纯函数、不读环境", 落盘这一下读 os.linesep 就把前提破坏了。
    for path, want in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(want, encoding="utf-8", newline="\n")
    # 分卷页是生成物: 主题表缩回一份后, 旧卷页不该留在库里 (否则 --check 恒红)。
    for stale in _stale_volume_pages(mb, outputs):
        stale.unlink()
    print(f"已生成 {len(outputs)} 个生成物")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
