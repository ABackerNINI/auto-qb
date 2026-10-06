"""补推 / 单独推送 —— 顺序固定: 先同步核对 → 推主线 → 核对远端 → 镜像(全程静默)。

输出契约 v3.1(承接 v3 计划 26-09-28-0157): 结果行仍是「推送成功 <hash>」/「推送失败: <原因> —— <下一步>」,
逐个**步骤**行打在它上面(见 `_pipeline.py`「步骤登记」段)。本任务的步骤来自内部 run_sync 的快进 / rebase。
ship.commit 成功后默认**同进程内联续推**(run_push, 输出由 commit 统一编排), 本任务是补推 / 重验入口。

- 先跑一次 sync(run_sync): 齐平则无事发生; 落后自动快进; 分叉自动 rebase(树净才动) ——
  刚提交完的树通常干净, 不给「先手动同步」这道手工步骤。
- 推主线瞬时连接失败(Recv failure / Connection was reset)自动重试**一次**;
  不重试第二次 / 不换代理 / 不改走 SSH。
- 推送核对只用 ls-remote 现查远端真值(refs/remotes 快照在本环境不可信); 取不到 ≠ 推送失败,
  如实说「无法核实」, 别把网络抖动报成不一致。
- 镜像(github)仍自动尝试一次, 但**成功失败都不提**(26-09-28 用户定调: 允许滞后, 提了纯属噪音);
  失败不重试 / 不回滚主线上已完成的推送。

用法: python <包>/scripts/push.py   (无旗标)
退出码: 0 推送成功 · 1 失败(输出自带原因)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Windows GBK 控制台兑底(与包内其它脚本同根)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _pipeline import emit_steps, git, git_run  # noqa: E402
from _ship_config import ConfigMissing, load_config, proxy_disable_args, resolve_branch, resolve_main_remote, resolve_mirror_remote  # noqa: E402
from sync import remote_sha_with_retry, run_sync  # noqa: E402


def _git_reason(proc) -> str:
    lines = [l.strip() for l in (proc.stderr or "").splitlines() if l.strip() and not l.startswith("hint:")]
    return lines[-1] if lines else "git 非 0"


def run_push(steps: list[str] | None = None) -> tuple[bool, str]:
    """核心动作。返回 (ok, line): 成功时 line = 「推送成功 <hash>」;
    失败时 line 是「推送失败」的**后缀**(同步类失败沿用 sync 的后缀, 含冲突模板)。

    `steps` 由入口持有并在结果行前打印(见 `_pipeline.step` 的三条纪律); 内部的 run_sync
    可能 rebase 改写 HEAD —— 那一行在这里登记, 推送结果行的 hash 才追得上源头。
    """
    ok, line = run_sync(steps)
    if not ok:
        return False, line

    try:
        cfg, _src = load_config()
    except ConfigMissing as exc:
        return False, str(exc)
    branch = resolve_branch(cfg)
    main, _url = resolve_main_remote(cfg)
    if not main:
        return False, "找不到主线远端 —— git remote -v 核对后改配置"

    head = git("rev-parse", "HEAD")
    proc = None
    for attempt in range(2):
        proc = git_run("push", main, branch)
        if proc.returncode == 0:
            break
        err = proc.stderr or ""
        if attempt == 0 and ("Recv failure" in err or "Connection was reset" in err):
            time.sleep(1)  # 主线瞬时连接失败, 重试一次
            continue
    if proc.returncode != 0:
        return False, f"主线推送未通过 —— {_git_reason(proc)}; 联网后重跑"

    remote_sha = remote_sha_with_retry(main, branch)
    if not remote_sha:
        # 取不到 ≠ 推送失败: 别把网络抖动报成「不一致」, 那会让执行者重复推
        return False, (f"推送命令已执行但取不到远端 ref, 无法核实 —— 稍后手工核对 "
                       f"git ls-remote {main} {branch} (期望 {head[:8]})")
    if remote_sha != head:
        return False, f"远端 ref 与本地不一致 (远端{remote_sha[:8]} 本地{head[:8]}) —— 核对链路后重跑"

    # 镜像: 只尝试一次, 全程静默(D2) —— 成功失败都不提, 允许滞后
    mirror, mirror_url = resolve_mirror_remote(cfg)
    if mirror:
        git_run(*proxy_disable_args(mirror_url), "push", mirror, branch)
    return True, f"推送成功 {head[:8]}"


def main(argv: list[str] | None = None) -> int:
    import argparse

    # ❗参数入口的判据(2026-10-03, 与 sync.py 同源):
    #   `argv is None` = CLI 直跑 → 吃真实 sys.argv; 显式空表([]) = 测试裸调的动作入口。
    #   旧 `argv or []` 把 CLI 的 sys.argv 整个丢掉, `push.py --help` 会**真的推一次**。
    # (教训链: verify_ref.py 2026-09-22 → sync.py 2026-09-28 → 2026-10-03 定性为
    #  「argv or [] 吃参数」这一类; 冒烟侧过滤见 .my-commit-flow.toml 的 |--with-safety 节。)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safety", action="store_true", help="回答「无参跑我是否即真动作」(冒烟安全过滤用)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.safety:  # 冒烟安全过滤的探针: 只答常量, 不碰 git / 网络
        print("push.py: action-without-args")
        return 0
    steps: list[str] = []
    ok, line = run_push(steps)
    emit_steps(steps)  # 步骤行永远在结果行**上面**(结果行才是要贴进回复 / 档案的那个值)
    print(line if ok or line.startswith("[STOP]") else f"推送失败: {line}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
