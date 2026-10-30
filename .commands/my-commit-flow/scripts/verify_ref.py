"""提交后核对分支 ref 三处一致 —— 某些环境下 ref 更新会静默丢失(提交命令照样打印成功),
**不要只看 commit 输出**。ship.commit 已内置这一核对(静默通过); 本任务是排障 / 手工复核入口。

用法: python <包>/scripts/verify_ref.py [期望的 sha 前缀]

判据: HEAD == refs/heads/<branch> == loose ref; packed-refs 不再是独立判据(见 v5)。

输出契约 v5(2026-10-31, packed-refs 陈旧形态从「停手指引」升级为「自动修复 + 放行」):
通过一行「ref 一致 <hash>」(自动修复发生时, 上方附一行修复记录); 不一致保留完整处置步骤
(它本来就是排障工具, 细节是它的价值)。
- packed-refs 陈旧(HEAD==refs/heads==loose 三处一致, 仅 packed 落后): **不再停** —— git 解析
  ref 时 loose 优先于 packed, packed 旧值读不到, 提交确定落稳。自动跑 `git pack-refs --all`
  顺带刷新 packed(只重写 packed-refs 一个文件, 对象零风险), 刷不动也放行(附一行说明)。
  本仓提交后 packed 不自动刷新, 该形态每笔提交都会再现 —— 手工处置已复发 7 次
  (pitfalls「packed-refs 陈旧会导致核 ref 假红」), 故收进脚本。
- 分支指针被回退/丢失(HEAD 与 refs/heads/loose 不一致)或 staged 暴增: **仍停**, 送「分支 ref
  被回退」条目 —— 这才是核对存在的意义, 绝不自动修。
退出码: 0 一致(含 packed 陈旧已自动修复) · 1 不一致 / staged 暴增(输出自带处置步骤)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Windows GBK 控制台兑底(与包内其它脚本同根)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _pipeline import git, git_run  # noqa: E402
from _ship_config import KEY_DEFAULTS, find_root, load_config, resolve_branch  # noqa: E402

REPO = find_root()  # 向上找 .git, 不按 skill 安装深度反推
try:
    _CFG, _ = load_config(REPO)
except Exception:  # 校验工具不因缺配置停摆: 用内置兜底值
    _CFG = dict(KEY_DEFAULTS)
BRANCH = resolve_branch(_CFG)
STAGED_PANIC = _CFG["staged_panic"]
# 分支指针被回退/丢失形态的处置(HEAD 与 refs/heads/loose 不一致, 或 staged 暴增)
BRANCH_ROLLBACK_HINT = """处置(按 pitfalls「分支 ref 被回退」条目):
  1. 先确认没有别的会话正在操作同一个 .git
  2. 留底:  git format-patch -1 <sha> --stdout > 备份.patch
  3. 建锚点防 GC:  git update-ref refs/heads/tmp-<名字> <sha>
  4. 等对方结束后:  git reset --soft <sha>   (工作区/索引无需变动)
  **不要**用 git add -A / 全量提交去"解决"那批 staged —— 那是别人的在途改动。"""


# 仅 packed-refs 陈旧形态的自动修复(HEAD==refs/heads==loose, 只是 packed 落后; 提交已落稳)。
# v5(2026-10-31)起该形态不再停手 —— 手工照配方跑 pack-refs 已复发 7 次, 收进脚本自动做:
# 放行判据(B): git 解析 ref 时 loose 优先于 packed, packed 旧值读不到, 三处本地真值一致
# 即落稳; pack-refs --all(A)是顺带刷新, 刷不动也不影响放行。
def _autoheal_packed_stale(head: str, packed: str) -> list[str]:
    """跑 `git pack-refs --all` 顺带刷新 packed-refs; 返回信息行(放行, 不失败)。"""
    proc = git_run("pack-refs", "--all")
    now = packed_ref(BRANCH)
    if proc.returncode == 0 and now == head:
        return [
            f"packed-refs 陈旧已自动修复: git pack-refs --all({packed[:8]} → {head[:8]})"
            " —— 提交已落稳(loose 优先, packed 落后不拦)"
        ]
    return [
        f"packed-refs 自动修复未生效(rc={proc.returncode}, 现值 {now or '(无)'}) —— 已放行:"
        " HEAD==refs/heads==loose 为准, packed 落后仅是噪音"
    ]


def classify_form(head: str, branch_ref: str, loose: str, packed: str) -> str:
    """不一致的形态: 'packed_stale' 或 'branch_rollback'。

    三处本地真值(HEAD / refs/heads / loose)已一致、仅 packed-refs 落后 → 'packed_stale'
    (提交已落稳, v5 起自动修复 + 放行); 否则是分支指针被回退/丢失 → 'branch_rollback'(仍停)。
    """
    if head and head == branch_ref == loose and packed and packed != head:
        return "packed_stale"
    return "branch_rollback"


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
            BRANCH_ROLLBACK_HINT,
        ]

    values = {v for v in (head, branch_ref, loose) if v}
    ok = bool(head) and len(values) == 1 and (not packed or packed == head)
    if expect:
        ok = ok and head.startswith(expect)
    if ok:
        return True, []

    form = classify_form(head, branch_ref, loose, packed)
    if form == "packed_stale":
        # HEAD/refs/heads/loose 已一致, 只 packed 落后 —— v5 起自动修复 + 放行, 不再停手
        # (手工照配方跑 pack-refs 已复发 7 次; 若 expect 也不匹配则另算, 不在放行之列)
        if not expect or head.startswith(expect):
            return True, _autoheal_packed_stale(head, packed)
        return False, [f"[STOP] HEAD {head} 与期望 {expect} 不一致。"]
    detail = [
        f"  HEAD         {head}",
        f"  refs/heads/{BRANCH}".ljust(28) + branch_ref,
        f"  loose ref    {loose or '(无 loose 文件)'}",
        f"  packed-refs  {packed or '(未 pack)'}",
        "",
        "[STOP] ref 不一致 —— 提交可能没落稳。",
        BRANCH_ROLLBACK_HINT,
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
    for line in detail:
        print(line)  # 信息行(packed 陈旧自动修复记录)即使 ok 也要打印; 干净通过时 detail 为空
    if ok:
        print(f"ref 一致 {git('rev-parse', 'HEAD')[:8]}")
        return 0
    return 1


if __name__ == "__main__":
    from _snapshot import maybe_respawn  # noqa: E402  (快照自举: 一次调用 = 一个版本)

    _rc = maybe_respawn(__file__)  # 未在快照里 → 复制整包到仓库之外并重入
    if _rc is not None:
        raise SystemExit(_rc)  # 已由子进程(副本)接管
    raise SystemExit(main())
