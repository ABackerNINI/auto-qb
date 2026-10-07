"""补推 / 单独推送 —— 顺序固定: 先同步核对 → 推主线 → 核对远端 → 镜像(全程静默)。

输出契约 v3.1(承接 v3 计划 26-09-28-0157): 结果行仍是「推送成功 <hash>」/「推送失败: <原因> —— <下一步>」,
逐个**步骤**行打在它上面(见 `_pipeline.py`「步骤登记」段)。本任务的步骤来自内部 run_sync 的快进 / rebase。
ship.commit 成功后默认**同进程内联续推**(run_push, 输出由 commit 统一编排), 本任务是补推 / 重验入口。

- 先跑一次 sync(run_sync): 齐平则无事发生; 落后自动快进; 分叉自动 rebase(树净才动) ——
  刚提交完的树通常干净, 不给「先手动同步」这道手工步骤。
- 推主线**单次超时 20s + 有界重试 3 次**(`_pipeline.run_git` 统一提供, 全部失败才判失败) ——
  远端会间歇性卡住, 重试层就是为它加的; 不换代理 / 不改走 SSH。主线 = `origin`(存在即主线),
  镜像由主线主机决定 —— 解析单点在 `_ship_config.resolve_main_remote` / `resolve_mirror_remote`。
- 推送核对只用 ls-remote 现查远端真值(refs/remotes 快照在本环境不可信); 取不到 ≠ 推送失败,
  如实说「无法核实」, 别把网络抖动报成不一致。
- 镜像**只给超时, 不给重试**(attempts=1)且**成功失败都不提**(26-09-28 用户定调: 允许滞后,
  提了纯属噪音); 是谁由**主线主机决定** —— origin 是 gitee 则镜像 github, 反之亦然, 只配
  origin 则无镜像。失败不回滚主线上已完成的推送。

用法: python <包>/scripts/push.py   (无旗标)
退出码: 0 推送成功 · 1 失败(输出自带原因)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Windows GBK 控制台兑底(与包内其它脚本同根)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _pipeline import emit_steps, git, git_run, retry_note  # noqa: E402
from _ship_config import ConfigMissing, load_config, proxy_disable_args, resolve_branch, resolve_main_remote, resolve_mirror_remote  # noqa: E402
from sync import remote_sha, run_sync  # noqa: E402


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
    # 主线推送: 单次超时 20s + 有界重试 3 次全在 run_git 层 —— 这里**不再自己重试**
    # (两层各重试 = 最多 6 次尝试, 且「重试了几次」会拆成两处口径, 失败行说不清)。
    proc = git_run("push", main, branch)
    if proc.returncode != 0:
        return False, f"主线推送未通过{retry_note(proc)} —— {_git_reason(proc)}; 联网后重跑"

    remote_sha_now = remote_sha(main, branch)
    if not remote_sha_now:
        # 取不到 ≠ 推送失败: 别把网络抖动报成「不一致」, 那会让执行者重复推
        return False, (f"推送命令已执行但取不到远端 ref, 无法核实 —— 稍后手工核对 "
                       f"git ls-remote {main} {branch} (期望 {head[:8]})")
    if remote_sha_now != head:
        return False, f"远端 ref 与本地不一致 (远端{remote_sha_now[:8]} 本地{head[:8]}) —— 核对链路后重跑"

    # 镜像: **只给超时, 不给重试**(attempts=1), 全程静默(D2) —— 成功失败都不提, 允许滞后
    mirror, mirror_url = resolve_mirror_remote(cfg)
    if mirror:
        git_run(*proxy_disable_args(mirror_url), "push", mirror, branch, attempts=1)
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
    from _snapshot import maybe_respawn  # noqa: E402  (快照自举: 一次调用 = 一个版本)

    _rc = maybe_respawn(__file__)  # 未在快照里 → 复制整包到仓库之外并重入
    if _rc is not None:
        raise SystemExit(_rc)  # 已由子进程(副本)接管
    raise SystemExit(main())
