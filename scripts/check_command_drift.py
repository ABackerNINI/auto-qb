"""反漂移闸门: 文档里**手抄**了已收录的命令 → 判红。

为什么必须有它: 命令一旦在包里有了单点定义, 文档里再抄一份就是副本 ——
而"哪一份才是生效的那份"并不写在命令旁边(§01 现场证据: 5 种写法里 4 种不满足项目约定,
其中 POSIX 前缀那一条看起来最正常, 实测 rc=1)。不做这一步, 整套东西只是第 9 处副本。

匹配按"命令骨架"而非逐字: 忽略引号风格 / 空格 / 路径差异 / 环境前缀, 只看关键 token 序列 ——
否则改个空格就绕过。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / ".agents/skills/commands/scripts"
sys.path.insert(0, str(ENGINE))

import _config as C  # noqa: E402

# 扫哪些文档 —— 都是**决策点**: 执行者真的会来这里找命令
# `.agents/skills/**/*.md`(不只 SKILL.md): skill 的 references/ 之类也是决策点, 而且
# SKILL.md 为省 token 会把细节搬过去 —— 只扫 SKILL.md 等于给搬出去的内容留一块盲区。
SCAN_GLOBS = (
    "AGENTS.md",
    "README.md",
    "CLAUDE.md",
    "TODO.md",
    "memory-bank/**/*.md",
    ".github/**/*.md",
    ".agents/skills/**/*.md",
)

# 显式豁免 —— 每一条都要说得出理由, 不加"先跑起来再说"的口子
EXEMPT = (
    ".github/workflows/",  # 另一条独立执行路径(CI), 不归本项目会话管
    "memory-bank/plans/",  # 历史快照: 计划定稿那一刻的样子, 不回改
    "memory-bank/reports/",  # 同上
    "memory-bank/issues/",  # 同上
    "memory-bank/tasks/",  # 档案纪要: 记的是"当时做了什么", 不是"现在该跑什么"
    "docs/plans/",
    "resources/",
    ".commands/",  # 配置层: 命令的单点定义就在这里
    "scripts/",  # 机检脚本自身
    ".workbuddy-ai/",
    # —— 下面两条是**逐文件**豁免, 都得说得出理由 ——
    "memory-bank/pitfalls/testing/tmpdir.md",  # 该条记的是 TMPDIR 陷阱本身: 哪几种写法不生效
    #   (POSIX 前缀 / 引号省略 / 换目录)**就是判据**, 把命令换成 task id 这条陷阱就没法读了
    "memory-bank/pitfalls/testing/patching.md",  # WSL 是另一条执行路径: 命令被 `wsl -- bash -c` 包裹
    #   且带 `-p 3.12/3.13` 变体, 不是本项目会话里"照着抄就能跑"的形态
)

# 已经写成"调 task"的写法 —— 这才是文档里该出现的形态
SANCTIONED = re.compile(r"commands\s+run\s+[\w.\-]+|run\.py\s+run\s+[\w.\-]+")

ENV_PREFIX = re.compile(r'^\s*(?:set\s+"?[A-Za-z_]\w*=[^"]*"?|[A-Za-z_]\w*=\S+)\s*$')
TOKEN_RE = re.compile(r'"[^"]*"|\S+')


def skeleton(cmd: str) -> list[str]:
    """命令 → 归一化 token 序列(去环境前缀 / 引号 / 路径只留文件名)。"""
    parts = [p.strip() for p in cmd.split("&&")]
    kept = [p for p in parts if p and not ENV_PREFIX.match(p)]
    text = " ".join(kept) if kept else cmd
    out: list[str] = []
    for raw in TOKEN_RE.findall(text):
        tok = raw.strip('"').strip("'")
        if not tok or tok in ("&&", ):
            continue
        if "/" in tok or "\\" in tok:
            tok = re.split(r"[\\/]", tok)[-1]  # 路径差异不算差异
        out.append(tok)
    return out


def line_tokens(line: str) -> list[str]:
    text = line.replace("`", " ")
    text = re.sub(r"^\s*[\-\*\|>»]+\s*", " ", text)
    return skeleton(text)


def find_skeletons() -> list[tuple[str, str, list[str]]]:
    """[(task id, 原始命令, 骨架)] —— 太短的骨架(单 token)匹配面过宽, 不收。"""
    tree = C.load_tree()
    out = []
    for task in tree.tasks.values():
        for cmd in C.task_commands(task, tree.root, strict=False):
            sk = skeleton(cmd)
            if len(sk) >= 2:
                out.append((task.id, cmd, sk))
    return out


def scan() -> list[tuple[str, int, str, str]]:
    """[(文件, 行号, 命中的原文, 该改成哪个 task)]"""
    skels = find_skeletons()
    if not skels:
        return []
    hits: list[tuple[str, int, str, str]] = []
    files: list[Path] = []
    for pat in SCAN_GLOBS:
        files += [p for p in ROOT.glob(pat) if p.is_file()]
    for path in sorted(set(files)):
        rel = path.relative_to(ROOT).as_posix()
        if any(rel.startswith(e) for e in EXEMPT):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for no, line in enumerate(lines, 1):
            if SANCTIONED.search(line):
                continue
            toks = line_tokens(line)
            if not toks:
                continue
            for tid, cmd, sk in skels:
                if _contains(toks, sk):
                    hits.append((rel, no, line.strip()[:110], tid))
                    break
    return hits


def _contains(line: list[str], sk: list[str]) -> bool:
    n = len(sk)
    return any(line[i:i + n] == sk for i in range(len(line) - n + 1))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查文档里有没有手抄已收录的命令")
    parser.add_argument("--list", action="store_true", help="只列出正在盯的命令骨架")
    args = parser.parse_args(argv)

    if args.list:
        for tid, cmd, sk in find_skeletons():
            print(f"{tid.ljust(28)}{' '.join(sk)}")
        return 0

    hits = scan()
    if not hits:
        print("命令漂移检查: 无手抄(0 处)")
        return 0
    print(f"命令漂移检查: {len(hits)} 处手抄 —— 命令只应在包里定义一份, 文档里写 task id")
    for rel, no, text, tid in hits:
        print(f"  [DRIFT] {rel}:{no}  → commands run {tid}")
        print(f"          {text}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
