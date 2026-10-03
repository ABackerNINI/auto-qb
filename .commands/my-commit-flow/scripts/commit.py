"""零参数全量提交 + 闸门 + 推送 —— 编排合一, 输出契约 v3(计划 26-09-28-0157)「沉默即成功」。

  成功           → 提交成功 <hash>
  推送未完成     → 提交成功 <hash> ＋ 推送未完成: <原因> —— 补推: commands run ship.push
                   (提交这个主目标已达成, 别重新提交; 退出码仍 0)
  失败           → 提交失败: <原因> —— <下一步>(闸门红附失败闸门名 + 输出末 20 行)

流程(全部静默, 检查项一个不删 —— 保全清单见计划 §04):
  1. 内部同步(run_sync): 齐平才继续; 落后自动快进 / 分叉自动 rebase —— 「先同步后提交」不再靠人记得
  2. 闸门(auto = true 真跑, 全过即静默; 失败给闸门名 + 末 20 行)
  3. 暂存计划: 缺省 = changed_files() 全量; 红线拦; 拒 -A / . / *(逐路径纪律)
  4. 逐路径 add —— 工作区已不存在的路径: 在索引里走 `rm --cached`, 都不在(已暂存的删除)则无事可做
     (修 issue 26-09-28-0128: 逐路径 add 撞「已暂存删除」的 pathspec 落空)
  5. git commit -F <消息文件>; 消息缺省读 <root>/.git/COMMIT_MSG_AI.txt, 落稳后**消费即删**
  6. ref 三处核对(静默; 不一致给处置步骤)
  7. 内联推送(run_push): 落后自动同步 / 瞬时失败重试一次 / 镜像全程静默
消息文件不删的时机: commit 或 ref 核对失败 —— 修好重跑还能用同一份消息。

用法: python <包>/scripts/commit.py [路径...] [--message-file <文件>] [--no-push]
退出码: 0 成功(含推送未完成) · 1 失败(输出自带原因, 不存在需要查的码表)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Windows GBK 控制台兑底(与包内其它脚本同根): gitmoji 首行含 emoji, GBK 编不出来会让 print 崩掉。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _pipeline import (  # noqa: E402
    changed_files,
    config_stops,
    gates_for,
    git_run,
    hit,
    run_gates,
    staged_overflow,
)
from _ship_config import ConfigMissing, find_root as _find_root, load_config  # noqa: E402
from verify_ref import check_refs  # noqa: E402

BULK = {"-A", "--all", ".", "*", "-u", "--update"}
DEFAULT_MESSAGE_REL = Path(".git") / "COMMIT_MSG_AI.txt"


def find_root() -> Path:  # noqa: F811  — 包一层, 测试替身钉这里
    return _find_root()


def default_message_path(root: Path) -> Path:
    """消息文件的约定单点 —— <root>/.git/COMMIT_MSG_AI.txt(永不入库, 多 clone 隔离)。"""
    return root / DEFAULT_MESSAGE_REL


def consume_message_file(msg_file: Path, root: Path) -> None:
    """消费即删 —— 提交落稳后删除约定路径的消息文件, 防旧消息残留被回看者当现状。

    只删约定路径: 显式 --message-file 指向别处的文件归调用方管。删除失败只提示
    不影响退出码 —— 提交已成功, 别让收尾环节的失败骗执行者重跑。
    """
    if msg_file != default_message_path(root):
        return
    try:
        msg_file.unlink()
    except OSError as exc:
        print(f"⚠ 消息文件删除失败({exc}); 请手动删除 {msg_file}, 避免下次提交误读旧消息")


def resolve_stage_plan(paths: list[str], red_lines: list[str], staged: list[str],
                       unstaged: list[str]) -> tuple[list[str], list[str], str | None]:
    """算暂存计划, 返回 (to_stage, omitted, refuse); refuse 非 None 即拒绝执行。

    paths 为空 → 全量改动(权威单点 changed_files); 传路径 → 子集, omitted = 改动了
    但没被纳入的文件(把"漏传"从静默变成可见)。红线按既有的子串口径匹配。
    """
    bulk = [p for p in paths if p in BULK]
    if bulk:
        return [], [], f"拒绝批量暂存 {' '.join(bulk)} —— 项目纪律是逐路径 add; 零参数 = 全量提交"
    all_changed = staged + unstaged
    if paths:
        to_stage = list(paths)
        omitted = [p for p in all_changed if p not in set(paths)]
    else:
        to_stage = all_changed
        omitted = []
    if not to_stage:
        return [], [], "没有可提交的改动 —— 工作区干净(改动在别的 clone 或未保存?)"
    red = [p for p in to_stage if any(r in p for r in red_lines)]
    if red:
        return [], [], f"红线文件不得提交: {' '.join(red)} —— 移出提交范围后重跑(见 AGENTS.md「红线」节)"
    return to_stage, omitted, None


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="要暂存的路径(缺省 = 全部改动); 传了即子集提交")
    parser.add_argument("--message-file", default=None, help=f"提交消息文件(缺省 <root>/{DEFAULT_MESSAGE_REL}; 约定路径落稳后自动删除)")
    parser.add_argument("--no-push", action="store_true", help="只提交不推送(补推: commands run ship.push)")
    args = parser.parse_args(argv)

    try:  # 外置配置缺失 → 停手引导, 不猜默认值
        cfg, _src = load_config()
    except ConfigMissing as exc:
        print(exc)
        return 1
    stops = config_stops(cfg, _src)
    if stops:  # 未知键 / timeout 非法 → 闸门可能静默失效, 必须停(不降级)
        print(f"提交失败: 配置错误 —— {stops[0]}")
        return 1
    root = find_root()

    staged, unstaged = changed_files()
    overflow = staged_overflow(staged, cfg["staged_panic"])
    if overflow:
        print(f"提交失败: {overflow}")
        return 1
    to_stage, omitted, refuse = resolve_stage_plan(args.paths, cfg["red_lines"], staged, unstaged)
    if refuse:
        print(f"提交失败: {refuse}")
        return 1
    warn_files = hit(staged + unstaged, cfg["warn_lines"])

    msg_file = Path(args.message_file).expanduser() if args.message_file else default_message_path(root)
    if not msg_file.exists():
        print(f"提交失败: 提交消息文件不存在 {msg_file} —— 把消息(中文首行 + 空行 + 动机/取舍/影响面/实测数字)"
              f"写入后重跑; 约定文件消费即删, 每次提交前都要重写")
        return 1

    # 1 内部同步: 落后自动快进 / 分叉自动 rebase; 失败即停(回写件必须落在合并后的新基线上)
    from sync import is_dirty_block, run_sync  # noqa: E402  (延后 import: 测试替身要能覆盖)

    ok, sync_line = run_sync()
    if not ok:
        print("提交失败: 未与主线同步 —— 处置后重跑 commands run ship.commit")
        print(f"  同步失败: {sync_line}")
        if is_dirty_block(sync_line):
            # 死锁护栏(2026-10-03): 「先跑 sync 后重跑」在树脏场景是死循环 —— 上面那条 sync
            # 就是本命令内部这一步, 单独重跑必撞同一处; 配方在 sync 失败行里, 这里不重复。
            print("  注意: 上面这条同步是本命令内部那一步 —— 单独重跑 sync、或「先提交」都解不开"
                  "(提交入口第一步还是它); 按失败行的「解锁」走")
        return 1

    # 2 闸门(在暂存前: fmt 类闸门会改文件)。改动清单以同步后的磁盘为准重算。
    staged, unstaged = changed_files()
    changed = staged + unstaged
    present = [p for p in changed if (root / p).exists()]
    ctx = {"root": root, "changed": present, "each_limit": cfg.get("each_limit", 99)}
    failures, manual, _ran = run_gates(gates_for(present, cfg["gates"]), ctx)
    if failures:
        note, cmd, rc, secs, tail = failures[0]
        print(f"提交失败: 闸门「{note}」未过 (rc={rc}, {secs:.1f}s) —— 处理后重跑 commands run ship.commit")
        print(f"  $ {cmd}")
        for line in tail.splitlines():
            print(f"    {line}")
        return 1
    if manual:
        print("人工闸门(未自动执行, 需自行跑): " + " ; ".join(manual))

    # 3 逐路径暂存 —— 工作区已不存在的路径: 索引里还有 → rm --cached; 都不在(已暂存的删除)→ 无事可做
    for path in to_stage:
        exists = (root / path).exists()
        if not exists:
            in_index = git_run("ls-files", "--", path).stdout.strip()
            if in_index:
                proc = git_run("rm", "--cached", "--", path)
            else:
                continue  # 已暂存的删除: 索引与工作区都没有, add 本就无处匹配(issue 26-09-28-0128)
        else:
            proc = git_run("add", "--", path)
        if proc.returncode != 0:
            err = (proc.stderr or "").strip().splitlines()
            print(f"提交失败: git {'add' if exists else 'rm --cached'} 失败 {path} —— "
                  f"{err[-1] if err else 'git 非 0'}")
            return 1
    if omitted:
        shown = "、".join(omitted[:3]) + ("…" if len(omitted) > 3 else "")
        print(f"…(子集提交: 另有 {len(omitted)} 个改动未纳入({shown}) —— 确认这是有意的)")

    # 4 提交
    proc = git_run("commit", "-F", str(msg_file))
    if proc.returncode != 0:
        detail = [l.strip() for l in ((proc.stdout or "") + (proc.stderr or "")).splitlines() if l.strip()]
        print(f"提交失败: git commit 未通过 —— {detail[-1] if detail else 'git 非 0(明细: git status)'}")
        return 1  # 消息文件保留: 修好重跑还能用同一份
    sha = git_run("rev-parse", "HEAD").stdout.strip()[:8]  # 8 位, 与 sync.py 的 <hash> 口径一致

    # 5 ref 三处核对 —— 提交命令成功 ≠ ref 落稳(本环境 ref 写入会被静默丢弃)
    ok, detail = check_refs()
    if not ok:
        print("提交失败: ref 三处不一致 —— 提交可能没落稳; 确认无他人操作 .git 后按下方步骤处置")
        for line in detail:
            print(line)
        return 1  # 消息文件保留: 现场未定, 别急着消费

    consume_message_file(msg_file, root)

    if args.no_push:
        print(f"提交成功 {sha}(未推送 —— 补推: commands run ship.push)")
        if warn_files:
            print(f"⚠ 已包含: {'、'.join(warn_files)} —— 确认是有意的")
        return 0

    # 6 内联推送(run_push 内含同步核对 / 瞬时重试 / 静默镜像); 推送未完成 ≠ 提交失败
    from push import run_push  # noqa: E402

    pushed, push_line = run_push()
    if not pushed:
        print(f"提交成功 {sha}(未推送)")
        print(f"推送未完成: {push_line} —— 补推: commands run ship.push")
    else:
        print(f"提交成功 {sha}")
    if warn_files:
        print(f"⚠ 已包含: {'、'.join(warn_files)} —— 确认是有意的")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
