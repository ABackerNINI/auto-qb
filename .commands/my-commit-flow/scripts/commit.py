"""零参数全量提交 + 闸门 + 同步 + 推送 —— 编排合一, 承接 v3(计划 26-09-28-0157)「沉默即成功」并升级到 v3.1。

  结果行      → 提交成功 <hash>
  步骤行(上面) → 本次"真发生了"的 HEAD 改写, 相邻两步首尾相接 **旧hash→新hash**:
                同步: 远端领先 1 笔 · 本地领先 1 笔(分叉) → rebase 重放本地 1 笔 aa11bb22→bb22cc33
                闸门复跑: 合流后闸门改了 2 个文件 → amend bb22cc33→cc33dd44
                (非改写类: 合流后上游改动了本包时留一行「本次仍按启动版本运行, 重跑以采用新版本」)
  推送未完成  → 提交成功 <hash>(未推送) ＋ 推送未完成: <原因> —— 补推: commands run ship.push
                 (提交这个主目标已达成, 别重新提交; 退出码仍 0)
  失败        → 提交失败: <原因> —— <下一步>(闸门红附失败闸门名 + 输出末 20 行)

一次 ship.commit 里 HEAD 最多被改写三次 —— 提交自身、内部同步的 rebase、闸门复跑后的 amend
(补推前 run_push 内部还可能再同步一次)。结果行只给终值, 前两段若不登记就成了黑箱 —— 这正是 v3.1
要补的漏洞(2026-10-06 用户指出「输出过于精简, rebase 后 hash 变了会让人去查原因」)。
登记纪律见 `_pipeline.py`「步骤登记」段; 结果行的唯一出口是 `emit()`。

流程(2026-10-04 起**提交先行** —— 提交后树必然干净, 分叉 rebase 恒可自动, stash 解锁舞蹈自提交路径退役;
全部静默, 检查项一个不删 —— 保全清单见计划 §04):
  1. 闸门(auto = true 真跑, 全过即静默; 失败给闸门名 + 末 20 行) —— 按本地改动清单
  2. 暂存计划: 缺省 = changed_files() 全量; 红线拦; 拒 -A / . / *(逐路径纪律)
  3. 逐路径 add —— 工作区已不存在的路径: 在索引里走 `rm --cached`, 都不在(已暂存的删除)则无事可做
     (修 issue 26-09-28-0128: 逐路径 add 撞「已暂存删除」的 pathspec 落空)
  4. git commit -F <消息文件>; 消息缺省读 <root>/.git/COMMIT_MSG_AI.txt
  5. ref 三处核对(提交命令成功 ≠ ref 落稳 —— 本环境 ref 写入会被静默丢弃, 必须赶在同步前拦下:
     同步拿 HEAD 当真值, ref 丢了会把旧 tip 当成本地提交) → 落稳即消费消息文件
  6. 内部同步(run_sync): 齐平即 no-op; 分叉自动 rebase 保线性 —— 冲突 / 断网自动回滚后按
     「推送未完成」停下要人
  7. rebase 真合入了远端提交(HEAD 改写) → 按**同一份清单**复跑一轮(合并后的树才算数); fmt 类闸门若又
     改了文件 → 逐路径 add + commit --amend 折进未推送的 tip(与 sync.py 生成物收尾同款)。规则仍是
     **启动版本那份** —— 快照语义下不重取配置(那正是撕裂的来源); 合流若改动了本包, 登记一行提示重跑
  8. 内联推送(run_push): 自带同步核对(竞态窗口兜底) / 推主线 20s×3 次(见 `_pipeline.run_git`) / 镜像 attempts=1 全程静默
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
    emit_steps,
    gates_for,
    git_run,
    hit,
    pack_touched,
    run_gates,
    staged_overflow,
    step,
)
from _ship_config import ConfigMissing, find_root as _find_root, load_config  # noqa: E402
from verify_ref import check_refs  # noqa: E402

BULK = {"-A", "--all", ".", "*", "-u", "--update"}
DEFAULT_MESSAGE_REL = Path(".git") / "COMMIT_MSG_AI.txt"


def emit(steps: list[str], line: str) -> None:
    """打结果行 —— 步骤行永远排在它上面。**所有**结果行都从这里出(别处 print 结果行会让步骤行掉队)。

    为什么必须集中: 一次提交里 HEAD 最多被改写三次(自身 → 内部 rebase → 闸门改后 amend);
    只要有一个出口绕开这里, 那个 hash 变化就成了无人解释的黑箱 —— 正是 v3.1 要补的洞。
    """
    emit_steps(steps)
    print(line)


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
    parser.add_argument("--no-push", action="store_true", help="只提交不推送(不同步, 离线可用; 补推: commands run ship.push)")
    args = parser.parse_args(argv)
    steps: list[str] = []  # 步骤登记簿由入口持有(见 _pipeline.py「步骤登记」段的三条纪律)

    try:  # 外置配置缺失 → 停手引导, 不猜默认值
        cfg, _src = load_config()
    except ConfigMissing as exc:
        emit(steps, str(exc))
        return 1
    stops = config_stops(cfg, _src)
    if stops:  # 未知键 / timeout 非法 → 闸门可能静默失效, 必须停(不降级)
        emit(steps, f"提交失败: 配置错误 —— {stops[0]}")
        return 1
    root = find_root()

    staged, unstaged = changed_files()
    overflow = staged_overflow(staged, cfg["staged_panic"])
    if overflow:
        emit(steps, f"提交失败: {overflow}")
        return 1
    to_stage, omitted, refuse = resolve_stage_plan(args.paths, cfg["red_lines"], staged, unstaged)
    if refuse:
        emit(steps, f"提交失败: {refuse}")
        return 1
    warn_files = hit(staged + unstaged, cfg["warn_lines"])

    msg_file = Path(args.message_file).expanduser() if args.message_file else default_message_path(root)
    if not msg_file.exists():
        emit(steps, f"提交失败: 提交消息文件不存在 {msg_file} —— 把消息(中文首行 + 空行 + 动机/取舍/影响面/实测数字)"
             f"写入后重跑; 约定文件消费即删, 每次提交前都要重写")
        return 1

    # 1 闸门(在暂存前: fmt 类闸门会改文件)。按本地改动清单跑; 合流后的树在步骤 6 复跑。
    changed = staged + unstaged
    present = [p for p in changed if (root / p).exists()]
    ctx = {"root": root, "changed": present, "each_limit": cfg.get("each_limit", 99)}
    failures, manual, _ran = run_gates(gates_for(present, cfg["gates"]), ctx)
    if failures:
        note, cmd, rc, secs, tail = failures[0]
        emit(steps, f"提交失败: 闸门「{note}」未过 (rc={rc}, {secs:.1f}s) —— 处理后重跑 commands run ship.commit")
        print(f"  $ {cmd}")
        for line in tail.splitlines():
            print(f"    {line}")
        return 1
    if manual:
        print("人工闸门(未自动执行, 需自行跑): " + " ; ".join(manual))

    # 2 逐路径暂存 —— 工作区已不存在的路径: 索引里还有 → rm --cached; 都不在(已暂存的删除)→ 无事可做
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
            emit(
                steps, f"提交失败: git {'add' if exists else 'rm --cached'} 失败 {path} —— "
                f"{err[-1] if err else 'git 非 0'}"
            )
            return 1
    if omitted:
        shown = "、".join(omitted[:3]) + ("…" if len(omitted) > 3 else "")
        print(f"…(子集提交: 另有 {len(omitted)} 个改动未纳入({shown}) —— 确认这是有意的)")

    # 3 提交
    proc = git_run("commit", "-F", str(msg_file))
    if proc.returncode != 0:
        detail = [l.strip() for l in ((proc.stdout or "") + (proc.stderr or "")).splitlines() if l.strip()]
        emit(steps, f"提交失败: git commit 未通过 —— {detail[-1] if detail else 'git 非 0(明细: git status)'}")
        return 1  # 消息文件保留: 修好重跑还能用同一份
    sha_full = git_run("rev-parse", "HEAD").stdout.strip()
    sha = sha_full[:8]  # 8 位, 与 sync.py 的 <hash> 口径一致

    # 4 ref 三处核对 —— 提交命令成功 ≠ ref 落稳(本环境 ref 写入会被静默丢弃); 必须赶在同步前拦下:
    #   同步拿 HEAD 当真值, ref 丢了会把旧 tip 当成本地提交推出去
    ok, detail = check_refs()
    if not ok:
        emit(steps, "提交失败: ref 三处不一致 —— 提交可能没落稳; 确认无他人操作 .git 后按下方步骤处置")
        for line in detail:
            print(line)
        return 1  # 消息文件保留: 现场未定, 别急着消费

    consume_message_file(msg_file, root)

    if args.no_push:  # 纯本地提交: 不同步不推送(离线可用), 合流留给补推时的 ship.push
        emit(steps, f"提交成功 {sha}(未推送 —— 补推: commands run ship.push)")
        if warn_files:
            print(f"⚠ 已包含: {'、'.join(warn_files)} —— 确认是有意的")
        return 0

    # 5 内部同步(提交先行, 2026-10-04): 树已净 —— 齐平 no-op / 分叉自动 rebase 恒可自动;
    #   冲突 / 断网自动回滚后停下要人 —— 提交已落稳, 按「推送未完成」处理, 别重新提交
    from sync import run_sync  # noqa: E402  (延后 import: 测试替身要能覆盖)

    ok, sync_line = run_sync(steps)
    if not ok:
        sep = "" if sync_line.startswith("需解决") else ": "
        emit(steps, f"提交成功 {sha}(未推送)")
        print(f"推送未完成: 同步失败{sep}{sync_line} —— 补推: commands run ship.push")
        if warn_files:
            print(f"⚠ 已包含: {'、'.join(warn_files)} —— 确认是有意的")
        return 0

    # 6 rebase 真合入了远端提交(HEAD 改写) → 闸门按同一份清单复跑一轮 —— 合并后的树才算数(检查项一个不删);
    #   fmt 类闸门若又改了文件, 逐路径 add 后折进未推送的 tip(rebase 后 tip 未推送, amend 安全)
    head_now = git_run("rev-parse", "HEAD").stdout.strip()
    if head_now != sha_full:
        # 6a 快照语义(一次调用 = 一个版本): 本进程从启动起就跑在**仓库之外的副本**上(`_snapshot`),
        #    内部同步的 rebase 把远端新版**本包**写进工作区, 对本进程不可见 —— 新版本从下一次调用生效。
        #    这里只把"上游改过本包"如实登记一行: 静默会让人以为已经用上新版本(这正是撕裂要换来的东西)。
        if pack_touched(sha_full, head_now):
            step(steps, "快照: 上游改动了本包 → 本次仍按启动版本运行, 重跑以采用新版本")
        # 6b 复跑闸门: 规则仍是**启动版本那份** cfg —— 快照语义下不重取配置(那正是撕裂的来源);
        #    复跑要验的只是"合并后的树", 改动清单也不变(仍是本次提交的那批)。
        failures_r, _manual_r, _ran_r = run_gates(gates_for(present, cfg["gates"]), ctx)
        if failures_r:
            note, cmd, rc, secs, tail = failures_r[0]
            emit(steps, f"提交成功 {head_now[:8]}(未推送)")
            print(
                f"推送未完成: 闸门「{note}」未过(合并远端后复跑, rc={rc}, {secs:.1f}s) —— "
                f"修复后重跑 commands run ship.commit(修复将作为新提交入库)"
            )
            print(f"  $ {cmd}")
            for line in tail.splitlines():
                print(f"    {line}")
            if warn_files:
                print(f"⚠ 已包含: {'、'.join(warn_files)} —— 确认是有意的")
            return 0
        st_r, un_r = changed_files()
        dirty_r = [p for p in st_r + un_r if (root / p).exists()]
        for path in dirty_r:
            proc = git_run("add", "--", path)
            if proc.returncode != 0:
                err = (proc.stderr or "").strip().splitlines()
                emit(steps, f"提交成功 {head_now[:8]}(未推送)")
                print(f"推送未完成: git add 失败 {path} —— {err[-1] if err else 'git 非 0'} —— 补推: commands run ship.push")
                if warn_files:
                    print(f"⚠ 已包含: {'、'.join(warn_files)} —— 确认是有意的")
                return 0
        if dirty_r:
            before = head_now
            amend = git_run("commit", "--amend", "--no-edit")
            if amend.returncode != 0:
                detail = [l.strip() for l in ((amend.stdout or "") + (amend.stderr or "")).splitlines() if l.strip()]
                emit(steps, f"提交成功 {head_now[:8]}(未推送)")
                print(f"推送未完成: 闸门改动 amend 失败 —— {detail[-1] if detail else 'git 非 0'} —— 补推: commands run ship.push")
                if warn_files:
                    print(f"⚠ 已包含: {'、'.join(warn_files)} —— 确认是有意的")
                return 0
            head_now = git_run("rev-parse", "HEAD").stdout.strip()
            # 闸门复跑改了文件 → amend 又挪了一次 tip: 不登记的话, 成功行的 hash 第三次失真
            step(steps, f"闸门复跑: 合流后闸门改了 {len(dirty_r)} 个文件 → amend {before[:8]}→{head_now[:8]}")
            ok, detail = check_refs()  # amend 又是一次 ref 写入 —— 复核
            if not ok:
                emit(steps, "提交失败: ref 三处不一致(amend 后) —— 提交可能没落稳; 确认无他人操作 .git 后按下方步骤处置")
                for line in detail:
                    print(line)
                return 1
    sha = head_now[:8]

    # 7 内联推送(run_push 内含同步核对 / 推主线 20s×3 重试 / attempts=1 静默镜像); 推送未完成 ≠ 提交失败
    from push import run_push  # noqa: E402

    pushed, push_line = run_push(steps)
    if not pushed:
        emit(steps, f"提交成功 {sha}(未推送)")
        print(f"推送未完成: {push_line} —— 补推: commands run ship.push")
    else:
        # run_push 内部同步可能又 rebase(竞态) → 以终值为准; 中间那次改写由它自己登记在步骤行里
        sha = git_run("rev-parse", "HEAD").stdout.strip()[:8]
        emit(steps, f"提交成功 {sha}")
    if warn_files:
        print(f"⚠ 已包含: {'、'.join(warn_files)} —— 确认是有意的")
    return 0


if __name__ == "__main__":
    from _snapshot import maybe_respawn  # noqa: E402  (快照自举: 一次调用 = 一个版本)

    _rc = maybe_respawn(__file__)  # 未在快照里 → 复制整包到仓库之外并重入
    if _rc is not None:
        raise SystemExit(_rc)  # 已由子进程(副本)接管
    raise SystemExit(main())
