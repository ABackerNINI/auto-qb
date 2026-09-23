"""提交后核对分支 ref —— 某些环境下 ref 更新会静默丢失(提交命令照样打印成功), **不要只看 commit 输出**。

用法(**不要写死包的安装路径**, `<包>` = 本包目录(`<仓库根>/.commands/my-commit-flow`)):
    python <包>/scripts/verify_ref.py [期望的 sha]

判据(三者必须一致):
    HEAD == refs/heads/<branch> == loose ref / packed-refs

退出码: 0 一致 · 2 不一致(打印修复命令) · 3 出现「staged 数量暴增」(分支 ref 被回退的信号)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Windows GBK 控制台兑底(与 commit.py 同根): 打印含 emoji/非常用字符时 GBK 编不出来会
# UnicodeEncodeError, 核对结果被打印中断。强制 stdout/stderr 走 UTF-8, 编不出时降级 replace。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ship_config import KEY_DEFAULTS, find_root, load_config, resolve_branch  # noqa: E402

REPO = find_root()  # 向上找 .git, 不按 skill 安装深度反推
try:
    _CFG, _ = load_config(REPO)
except Exception:  # 校验工具不因缺配置停摆: 用内置兜底值
    _CFG = dict(KEY_DEFAULTS)
BRANCH = resolve_branch(_CFG)
STAGED_PANIC = _CFG["staged_panic"]
FIX_HINT = """处置(按 pitfalls「分支 ref 被回退」条目):
  1. 先确认没有别的会话正在操作同一个 .git
  2. 留底:  git format-patch -1 <sha> --stdout > 备份.patch
  3. 建锚点防 GC:  git update-ref refs/heads/tmp-<名字> <sha>
  4. 等对方结束后:  git reset --soft <sha>   (工作区/索引无需变动)
  **不要**用 git add -A / 全量提交去"解决"那批 staged —— 那是别人的在途改动。"""


def git(*args: str) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def packed_ref(branch: str) -> str:
    packed = REPO / ".git" / "packed-refs"
    if not packed.exists():
        return ""
    for line in packed.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.endswith(f"refs/heads/{branch}") and not line.startswith("#") and not line.startswith("^"):
            return line.split()[0]
    return ""


def loose_ref(branch: str) -> str:
    path = REPO / ".git" / "refs" / "heads" / branch
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # 闸门自检契约(.my-commit-flow.toml): `verify_ref.py --help` 期望 rc=0; 手工解析下
    # 不拦的话 --help 会被当成期望 sha, 退出码 2 让闸门假红(实测 2026-09-22)。
    if "--help" in argv or "-h" in argv:
        print(__doc__.strip())
        return 0
    expect = argv[0] if argv else ""
    head = git("rev-parse", "HEAD")
    branch_ref = git("rev-parse", f"refs/heads/{BRANCH}")
    loose = loose_ref(BRANCH)
    packed = packed_ref(BRANCH)

    print(f"  HEAD              {head}")
    print(f"  refs/heads/{BRANCH}".ljust(28) + branch_ref)
    print(f"  loose ref         {loose or '(无 loose 文件)'}")
    print(f"  packed-refs       {packed or '(未 pack)'}")

    staged = [l for l in git("status", "--porcelain").splitlines() if l[:1] not in (" ", "?", "")]
    if len(staged) > STAGED_PANIC:
        print(f"\n[STOP] staged {len(staged)} 个(阈值 {STAGED_PANIC}) —— 分支 ref 可能被别的会话回退。\n{FIX_HINT}")
        return 3

    values = {v for v in (head, branch_ref, loose) if v}
    ok = bool(head) and len(values) == 1 and (not packed or packed == head)
    if expect:
        ok = ok and head.startswith(expect)

    if ok:
        print("\n[PASS] ref 三处一致(未 pack 时以 loose 为准)。")
        return 0

    print(f"\n[STOP] ref 不一致 —— 提交可能没落稳。\n{FIX_HINT}")
    print(f"\n强制写回(确认无他人操作后):  git update-ref refs/heads/{BRANCH} {head or '<sha>'}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
