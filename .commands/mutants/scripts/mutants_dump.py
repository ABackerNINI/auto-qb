"""把镜像里 mutmut 的结果导出成「可读清单 + 分类汇总」—— 在镜像仓里由 `.venv/bin/python` 执行。

**为什么要有它**: `mutmut results` 只回 `id: status`, 既没有文件:行, 也没有变异内容 ——
要三分类(真洞 / 等价 / 假存活)就必须拿到每条变异的 diff。状态存在
`mutants/<path>.meta` 的 `exit_code_by_key`, 变异内容由 mutmut 的 `diff_apply` 现场重放;
两者都只在镜像里, 所以本脚本也在镜像里跑。

用法::

    python mutants_dump.py [--status survived,no tests,timeout] [--limit N] [--target-glob G]

输出(stdout): 每条

    @@@ <mutant_id> :: <status>
    --- <file>
    +++ <file>
    <unified diff>

汇总(stderr, 供调用方转述): 按状态计数 + 按模块计数。

**状态 emoji 对照**(mutmut `stats.emoji_by_status`): 🎉 killed · 🫥 no tests · 🙁 survived ·
⏰ timeout · 🤔 suspicious · 🔇 skipped。注意 `no tests`(无覆盖) 与 `survived`(有覆盖没杀掉)
是**两类**, 分母不同, 别混着比。
"""

from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

DEFAULT_STATUSES = ("survived", "no tests", "timeout", "suspicious", "segfault")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--status", default=",".join(DEFAULT_STATUSES), help="要导出的状态(逗号分隔)")
    p.add_argument("--limit", type=int, default=0, help="最多导出多少条(0 = 不限)")
    p.add_argument("--target-glob", default="", help="只看某目标(仅用于汇总标注, 不影响筛选)")
    args = p.parse_args(argv)

    want = {s.strip() for s in args.status.split(",") if s.strip()}

    from mutmut.mutation.data import SourceFileMutationData
    from mutmut.mutation.diff_apply import find_mutant, get_diff_for_mutant
    from mutmut.stats import status_by_exit_code

    root = Path("mutants")
    if not root.is_dir():
        sys.stderr.write("[FAIL] 找不到 mutants/ —— 先在镜像里跑一轮 mutants.run\n")
        return 3

    by_status: collections.Counter = collections.Counter()
    by_module: collections.Counter = collections.Counter()
    n = 0
    for meta in sorted(root.rglob("*.meta")):
        rel = str(meta)[len("mutants/"):-len(".meta")]
        if not rel.endswith(".py"):
            continue
        data = SourceFileMutationData(path=rel)
        data.load()
        for mid, code in data.exit_code_by_key.items():
            status = status_by_exit_code[code]
            if status not in want:
                continue
            if args.limit and n >= args.limit:
                break
            n += 1
            by_status[status] += 1
            by_module[rel.rsplit("/", 1)[0].replace("/", ".")] += 1
            print(f"@@@ {mid} :: {status}")
            try:
                mutant = find_mutant(mid)
                print(get_diff_for_mutant(mid, path=mutant.path))
            except Exception as exc:  # 单条失败不拖垮整轮
                print(f"  <无法重放该变异: {exc}>")

    sys.stderr.write(f"[汇总] 导出 {n} 条 · 按状态 {dict(by_status)}\n")
    for mod, cnt in by_module.most_common():
        sys.stderr.write(f"[汇总]   {cnt:5d}  {mod}\n")
    if args.target_glob:
        sys.stderr.write(f"[汇总] 目标 glob: {args.target_glob}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
