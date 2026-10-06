"""提交后核对分支 ref 三处一致 —— 某些环境下 ref 更新会静默丢失(提交命令照样打印成功),
**不要只看 commit 输出**。ship.commit 已内置这一核对(静默通过); 本任务是排障 / 手工复核入口。

用法: python <包>/scripts/verify_ref.py [期望的 sha 前缀]

判据(三者必须一致): HEAD == refs/heads/<branch> == loose ref / packed-refs

输出契约 v3(计划 26-09-28-0157): 通过一行「ref 一致 <hash>」; 不一致保留完整处置步骤
(它本来就是排障工具, 细节是它的价值)。staged 数量暴增 = 分支 ref 被回退的信号, 同样停。
退出码: 0 一致 · 1 不一致 / staged 暴增(输出自带处置步骤)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Windows GBK 控制台兑底(与包内其它脚本同根)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _pipeline import git  # noqa: E402
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


def check_refs(expect: str = "") -> tuple[bool, list[str]]:
    """核对三处; 返回 (ok, 失败时的明细行)。成功只给一行结论, 失败给全量处置细节。"""
    head = git("rev-parse", "HEAD")
    branch_ref = git("rev-parse", f"refs/heads/{BRANCH}")
    loose = loose_ref(BRANCH)
    packed = packed_ref(BRANCH)

    staged = [l for l in git("status", "--porcelain").splitlines() if l[:1] not in (" ", "?", "")]
    if len(staged) > STAGED_PANIC:
        return False, [
            f"[STOP] staged {len(staged)} 个(阈值 {STAGED_PANIC}) —— 分支 ref 可能被别的会话回退。",
            FIX_HINT,
        ]

    values = {v for v in (head, branch_ref, loose) if v}
    ok = bool(head) and len(values) == 1 and (not packed or packed == head)
    if expect:
        ok = ok and head.startswith(expect)
    if ok:
        return True, []

    detail = [
        f"  HEAD         {head}",
        f"  refs/heads/{BRANCH}".ljust(28) + branch_ref,
        f"  loose ref    {loose or '(无 loose 文件)'}",
        f"  packed-refs  {packed or '(未 pack)'}",
        "",
        "[STOP] ref 不一致 —— 提交可能没落稳。",
        FIX_HINT,
        f"\n强制写回(确认无他人操作后):  git update-ref refs/heads/{BRANCH} {head or '<sha>'}",
    ]
    return False, detail


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # 闸门自检契约(.my-commit-flow.toml): `verify_ref.py --help` 期望 rc=0; 手工解析下
    # 不拦的话 --help 会被当成期望 sha, 退出码非 0 让闸门假红(实测 2026-09-22)。
    if "--help" in argv or "-h" in argv:
        print(__doc__.strip())
        return 0
    expect = argv[0] if argv else ""
    ok, detail = check_refs(expect)
    if ok:
        print(f"ref 一致 {git('rev-parse', 'HEAD')[:8]}")
        return 0
    for line in detail:
        print(line)
    return 1


if __name__ == "__main__":
    from _snapshot import maybe_respawn  # noqa: E402  (快照自举: 一次调用 = 一个版本)

    _rc = maybe_respawn(__file__)  # 未在快照里 → 复制整包到仓库之外并重入
    if _rc is not None:
        raise SystemExit(_rc)  # 已由子进程(副本)接管
    raise SystemExit(main())
