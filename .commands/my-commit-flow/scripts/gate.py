"""ship.gate —— 提交闸门单独预跑(计划 26-11-11-0408)。

为什么存在: 小失误此前只在 ship.commit 闸门一刻暴露, 回路是「小失误 → review → 提交被拦 →
修改 → 重 review → 再提交」—— 多花的是评审派发。预跑把 commit 将要跑的同一套闸门在
review 之前原样演一遍, 让 review 评到的树已经是闸门绿的。

行为表(与计划 §03 逐条对应):
  0. 配置体检(未知键 STOP) —— 与 commit 同一份 .my-commit-flow.toml, 清单单点不另抄。
  1. 树净 → 一行「树净, 无闸门可跑」(rc 0; 提交闸门照旧在 ship.commit 兜底)。
  2. 红线 / warn 命中 → 只打 WARN 信息行。拦截语义属于 commit 的暂存计划, 预跑不拦。
  3. 闸门: changed = staged + unstaged 中工作区仍存在的路径(与 commit 同口径);
     gates_for 命中 → run_gates 原样执行(并发池 / 分片 / 聚合语义一字不改)。
  4. `when_message` 闸门(配在 review.trace 上): 消息文件(<root>/.git/COMMIT_MSG_AI.txt)
     不存在 → 打略过行不执行 —— 评审批次 pack 前评审尚未发生, 照跑必红; 文件存在 → 照跑:
     trailer 已写但与实算不符(基漂移/行数错/Skip)在这时提前暴露。commit 侧不受该键影响:
     commit 在闸门之前就因消息缺失拒跑。
  5. review.trace 的「待评审」(批内有待评内容而消息尚无任何评审主张; 契约单点见
     check_review_trace.py 模块头「rc=3 待评审」节)→ 降级为待办行**不计入失败** —— 预跑时刻
     评审必然尚未发生, trailer 必然不存在, 与真违规不可分的红会让「消息文件先写」的预跑必红,
     与第 4 条的略过路径自相矛盾(2026-11-19 收口)。机器面 = 输出行首标记
     `评审留痕[待评审]:`(脚本 rc 恒 3, 但引擎 run.py 把任务失败归一成 rc=1, rc 到不了闸门);
     其余失败照旧; 待评审项在明细里单列, 全绿结果行缀「另: 评审留痕待评审」。commit 侧不受
     影响: rc!=0 照拦(评审未做不许提交)。
  6. 输出: 成功一行(「闸门全绿: ...」, 贴进评审记录); 失败 = 一行结果 + 全量逐条明细
     (预跑是诊断面, 与 commit 取 failures[0] 不同 —— 一次看全, 一轮修完)。

双跑是有意设计(拍板 D3): commit 闸门照旧全跑, 不做绿结果缓存 —— 缓存失效的静默红面
与「闸门静默失效比报错坏」哲学冲突。

用法: commands run ship.gate   (无参数; --safety 是冒烟闸门的探针)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Windows GBK 控制台兜底(与包内其它脚本同根)。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _pipeline import (  # noqa: E402
    changed_files, config_stops, gates_for, hit, run_gates,
)
from _ship_config import (  # noqa: E402
    ConfigMissing, find_root, load_config,
)

DEFAULT_MESSAGE_REL = Path(".git") / "COMMIT_MSG_AI.txt"
# review.trace 的「待评审」机器标记(契约单点: check_review_trace.py 模块头「rc=3 待评审」节):
# 脚本退出码恒 rc=3, 但引擎 run.py 把任务失败统一归一成 rc=1 —— rc=3 到不了闸门, 待评审态由
# 输出行首标记承载。gate 持同值字面量, 由 test_gate 的跨包钉面防漂移。
PENDING_TRACE_PREFIX = "评审留痕[待评审]:"


def _is_pending_failure(tail: str) -> bool:
    """失败输出尾里是否含 review.trace 的待评审标记行(2026-11-19 鸡生蛋收口)。"""
    return any(row.strip().startswith(PENDING_TRACE_PREFIX) for row in tail.splitlines())


def run_gate_prerun(steps: list[str]) -> tuple[bool, str, list[str]]:
    """预跑主体: 返回 (是否全绿, 结果行, 失败明细行)。

    明细行由入口打在**结果行之后**(commit.py 同序: 可执行的结论先行, 证据垫底)。
    `steps` 是步骤登记簿位(gate 不改写 HEAD, 现在恒空; 保留入口形状与 sync/commit 一致,
    以后加可追溯步骤时不必改调用面)。
    """
    cfg, _src = load_config()
    stops = config_stops(cfg, _src)
    if stops:  # 未知键 / timeout 非法 → 闸门可能静默失效, 必须停(不降级), 与 commit 同判据
        return False, f"预跑失败: 配置错误 —— {stops[0]}", []

    root = find_root()
    staged, unstaged = changed_files()
    changed = staged + unstaged
    if not changed:
        # 树净不是失败 —— 纯记账/生成物提交本就无预跑点(拍板 D7), 一行说明即可。
        return True, "树净, 无闸门可跑 —— 提交闸门照旧在 ship.commit 兜底", []

    # 红线 / warn: 只提示不拦(拍板 D6)。拦截语义属于 commit 的暂存计划(resolve_stage_plan)。
    for p in hit(changed, cfg["red_lines"]):
        print(f"WARN: 红线命中(仅提示, 拦截在 ship.commit 暂存计划): {p}")
    for p in hit(changed, cfg["warn_lines"]):
        print(f"WARN: 人工确认项(提交时需说明): {p}")

    present = [p for p in changed if (root / p).exists()]
    hits = gates_for(present, cfg["gates"])

    # when_message 过滤(拍板 D6): 消息文件不存在 → 消息依赖闸门打略过行后摘除。
    # 文件存在 → 原样保留, 并照 commit.py:515 同款把生效路径经环境变量递下去(review.trace 是
    # shell 子进程, 拿不到本进程的 Path; 不设它, ambient 里的旧值会让判定偏离 exists() 校验过的这份)。
    skipped: list[dict] = []
    msg_file = root / DEFAULT_MESSAGE_REL
    if not msg_file.exists():
        skipped = [g for g in hits if g.get("when_message")]
        if skipped:
            hits = [g for g in hits if not g.get("when_message")]
            print(
                f"[预跑] 略过 {len(skipped)} 条消息依赖闸门(消息文件不存在, 评审尚未发生): " +
                " ; ".join(g.get("note", "(无 note)") for g in skipped)
            )
    else:
        os.environ["COMMIT_FLOW_MSG_FILE"] = str(msg_file)

    if not hits:
        return True, "无闸门命中(略过面见上) —— 本次改动没有可预跑的自动闸门, commit 照旧兜底", []

    ctx = {"root": root, "changed": present, "each_limit": cfg.get("each_limit", 99)}
    t0 = time.monotonic()
    failures, manual, ran = run_gates(hits, ctx)
    secs = time.monotonic() - t0

    if manual:  # 本仓库配置里没有 auto=false 的闸门, 纯兜底提示(与 commit.py 同款)
        print("人工闸门(未自动执行, 需自行跑): " + " ; ".join(manual))

    # 待评审降级(2026-11-19 鸡生蛋收口, 契约单点见 check_review_trace.py 模块头): 预跑时刻
    # 评审必然尚未发生 → 「待评未留痕」是流程位置不是缺陷。按行首标记识别(引擎 run.py 把任务
    # 失败统一归一成 rc=1, 脚本的 rc=3 到不了这里), 降级为待办行不计入失败, 与 when_message
    # 的略过路径对齐(同一棵树不因消息文件先写而判红); commit 侧 rc!=0 照拦。
    pendings = [f for f in failures if _is_pending_failure(f[4])]
    failures = [f for f in failures if not _is_pending_failure(f[4])]

    if failures:
        detail: list[str] = []
        for note, cmd, rc, secs_i, tail in failures:
            detail.append(f"  - 「{note}」 (rc={rc}, {secs_i:.1f}s)")
            detail.append(f"    $ {cmd}")
            detail.extend(f"      {row}" for row in tail.splitlines())
        for _note, _cmd, _rc, _secs, tail in pendings:
            detail.append("  - 待评审(预跑不拦, 评审后闭合; commit 照拦):")
            detail.extend(f"      {row}" for row in tail.splitlines())
        line = (f"闸门预跑失败: {len(failures)} 条未过 —— 逐条处理完重跑 commands run ship.gate; "
                "绿了再 pack/评审")
        return False, line, detail
    if pendings:
        detail = []
        for _note, _cmd, _rc, _secs, tail in pendings:
            detail.append("  - 待评审(评审后闭合, commit 照拦) —— 按流程继续: review.pack → 评审 → 写 trailer:")
            detail.extend(f"      {row}" for row in tail.splitlines())
        return True, (
            f"闸门全绿: 命中 {len(hits)} 条, 执行 {ran} 条命令, 总耗时 {secs:.1f}s"
            f"(略过 {len(skipped)} 条); 另: 评审留痕待评审(评审后闭合) —— 结果行贴进评审记录"
        ), detail
    return True, (f"闸门全绿: 命中 {len(hits)} 条, 执行 {ran} 条命令, 总耗时 {secs:.1f}s"
                  f"(略过 {len(skipped)} 条) —— 结果行贴进评审记录"), []


def main(argv: list[str] | None = None) -> int:
    import argparse

    # ! 参数入口的判据照 sync.py(2026-10-03 定性): `argv is None` = CLI 直跑, 必须吃真实
    #   sys.argv, 否则 --help / --safety 被当"无参", 直接下沉到 run_gate_prerun() 真跑全套闸门
    #   (fmt 会真改文件)。显式空表([]) = 测试里裸调的动作入口。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safety", action="store_true", help="回答「无参跑我是否即真动作」(冒烟安全过滤用)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.safety:  # 冒烟安全过滤的探针: 只答常量, 不碰 git
        # 无参 = 真动作(fmt 真格式化 / test 真跑全套) —— 自认后冒烟闸门摘除本脚本。
        print("gate.py: action-without-args")
        return 0

    steps: list[str] = []
    try:
        ok, line, detail = run_gate_prerun(steps)
    except ConfigMissing as exc:
        ok, line, detail = False, str(exc), []
    print(line)
    for row in detail:
        print(row)
    return 0 if ok else 1


if __name__ == "__main__":
    from _snapshot import maybe_respawn  # noqa: E402  (快照自举: 一次调用 = 一个版本)

    _rc = maybe_respawn(__file__)  # 未在快照里 → 复制整包到仓库之外并重入
    if _rc is not None:
        raise SystemExit(_rc)  # 已由子进程(副本)接管
    raise SystemExit(main())
