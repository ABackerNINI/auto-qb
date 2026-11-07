"""生成物集合的**唯一声明处** —— 一次跑齐全部索引生成器, 并对外声明它们负责哪些文件。

三个用途(计划 memory-bank/plans/26-10-03-1544-plan-sync-generated-index-autoresolve.html):
    无参       依次重建全部生成物(等价于 `commands run kb.index` 原先跑的那四条)
    --list     打印全部生成物路径(仓库相对 posix, 一行一个) —— **sync 自动化解白名单的唯一来源**
    --check    全部自证: 磁盘内容 == 生成结果; 漂移即 rc=1 并逐条报路径
    --safety   回答「无参跑我是否即真动作」—— 冒烟闸门用它决定要不要给本脚本加 `--help`

为什么要有它: `_index.md` 这类生成物的合并冲突解法是「任取一侧 + 重跑」, 而「哪些文件可重跑」
必须只有**一处声明**。sync 从 `--list` 取白名单, 提交闸门与重建入口也调它 —— 若各处再抄一份清单,
迟早各自演化, 而「哪份才生效」不写在清单旁边(见 scripts/check_command_drift.py)。

数据源与四个生成器完全一致(它们是纯函数: 只读工作树里的手写文件, 不读 git / 时间戳 / 环境),
所以「任取一侧 + 重跑」必然收敛, 不需要任何文本合并。

用法(从仓库根; `<skill-dir>` = 加载 memory-bank skill 时它实际所在的目录):
    python <skill-dir>/scripts/gen_all.py                     重建全部生成物
    python <skill-dir>/scripts/gen_all.py --list              只打印路径, 不写文件
    python <skill-dir>/scripts/gen_all.py --check             只比对, 不一致则退出码 1
    python <skill-dir>/scripts/gen_all.py --safety            只回答冒烟安全性, 不碰文件
    python <skill-dir>/scripts/gen_all.py --root <dir> --mb-dir <dir>   覆盖探测
退出码: 0 成功 / 1 校验漂移或 `doc-status` 表外值
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import StatusVocabularyError, find_root, gen_cmd, rel_posix, resolve_mb_dir  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent

# 生成器脚本 → 所属 skill 名。**集合的唯一声明处** —— 新增一个生成器只改这里。
# (2026-11-07 W1 起 gen_issues_index 物理并入本 skill, 四个生成器同目录同一 `_common`,
# 计划 26-11-07-0549; 原先跨 skill 载入用的 find_skill_dir/_load_isolated 隔离机制随之退役。)
GENERATORS = (
    ("memory-bank", "gen_tasks_index.py"),
    ("memory-bank", "gen_kb_index.py"),
    ("memory-bank", "gen_docs_index.py"),
    ("memory-bank", "gen_issues_index.py"),
)

# 「无参即真动作」的生成器 —— **同步的生成物自动化解只准碰这一类**。
# 判据是"无参即真动作"(碰巧当前也是"纯确定性"): 这类脚本的默认动作就是重建全部生成物,
# 所以「任取一侧 + 重跑 + 自证」在构造上收敛(生成器是纯函数, 只读工作树里的手写文件)。
# ❗新增一个无参即重建的生成器却忘了登记 → 它的冲突**不会被自动化解**, 表现是与现状一致的
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
    """
    out: dict[Path, str] = {}

    out.update(_mb_module("gen_kb_index").build_all(root, mb))
    ti = _mb_module("gen_tasks_index")
    out[mb / "tasks" / "_index.md"] = ti.build(root, mb)
    # 归档索引: 主索引的已完结区只留最近 `CLOSED_KEEP` 条(控 cap), 全量清单另落这里 ——
    # 与主索引**同批**生成, 否则各生成器 `--check` 会因它缺席而恒红 (同 issues 侧纪律)。
    out[mb / "tasks" / ti.ARCHIVE_REL] = ti.build_archive(root, mb)
    docs = _mb_module("gen_docs_index")
    for kind, text in docs.build(root, mb).items():
        out[mb / kind / "_index.md"] = text
    for archive, text in docs.build_archives(root, mb).items():
        out[archive] = text

    issues_gen = _mb_module("gen_issues_index")
    # issues 目录恒 `<mb>/issues`(FAMILIES["issue"].spec.dir 单点落点) —— 与上面 tasks/plans/reports
    # 同用 `mb`; 原三候选探测(`resolve_issues_dir(root)`)随 new_issue.py 一并退役(2026-11-07),
    # 顺带修掉 `--mb-dir` 指向他处时 issues 落错树的隐患。
    issues_dir = mb / "issues"
    out[issues_dir / "_index.md"] = issues_gen.build(root, issues_dir)
    # 归档索引: 主索引的已关闭区只留最近 `CLOSED_KEEP` 条(控 cap), 全量清单另落这里 ——
    # 它必须与主索引**同批**生成, 否则 `gen_issues_index --check` 会因它缺席而恒红。
    out[issues_dir / issues_gen.ARCHIVE_REL] = issues_gen.build_archive(root, issues_dir)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="打印全部生成物路径(一行一个), 不写文件")
    parser.add_argument("--check", action="store_true", help="只比对, 不写文件 (不一致则退出码 1)")
    parser.add_argument("--safety", action="store_true", help="回答「无参跑我是否即真动作」(冒烟过滤用; 不读文件不写文件)")
    parser.add_argument("--root", help="仓库根 (默认向上找 .git)")
    parser.add_argument("--mb-dir", help="memory-bank 目录 (默认 <root>/memory-bank)")
    args = parser.parse_args(argv)

    # ❗必须在任何动作之前: 冒烟闸门会给脚本加 `--help` 探活, 而"无参即真动作"的脚本若
    #   把陌生参数当无参处理, 就会**真的重建一遍**(闸门在只读检查阶段写文件)。
    #   本脚本自己就是这一类, 这里的 --safety / --help 答案只来自常量, 不碰文件系统。
    if args.safety:
        kind = "action-without-args" if Path(__file__).name in PARAMETERLESS_ACTION_GENERATORS else "read-only-default"
        print(f"{Path(__file__).name}: {kind}")
        return 0

    root = Path(args.root).resolve() if args.root else find_root()
    mb = resolve_mb_dir(root, args.mb_dir)

    try:
        outputs = collect(root, mb)
    except StatusVocabularyError as exc:
        # gen_docs_index.build() 的表外状态 fail-fast —— 让它从"静默漏收"变成响亮报错,
        # kb.index / kb.check 两条入口都在这里接住 (见 pitfalls/kb/doc-status-meta.md)。
        sys.stderr.write(f"{exc}\n")
        return 1

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

    # ❗newline="\n" 必须显式给: write_text 的 newline 默认 None ⇒ 按 os.linesep 翻换行, Windows 上把
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
