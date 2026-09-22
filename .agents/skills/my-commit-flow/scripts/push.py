"""推送 —— **顺序固定**: 先推主线远端(必须成功), 再尝试一次镜像直连(失败只报一次)。

用法:
    python <skill-dir>/scripts/push.py [--skip-mirror] [--skip-preflight]

流程:
  0. **先跑一次预检(`--phase push --no-auto`)** —— 原先是让人在推送前手动跑一遍, 现收进脚本:
     本脚本自己会 fetch + 判落后, 但**不查**工作区脏 / 上游 / 红线又被改出来 / 镜像远端是否存在,
     这四项靠预检补上。闸门不重复跑(它们刚在提交前跑过, 且会改工作区), 故固定 `--no-auto`。
  1. 再 `git fetch` 看是否落后 —— 落后就 STOP(不自动 rebase, 那是红线区)
  2. `git push <main> <branch>`; 失败原样输出并退出(主线瞬时 reset 可重试一次)
  3. 核对远端 ref == 本地 HEAD(`git ls-remote`);`git status -sb` 不应再有 ahead
  4. 镜像: `git <禁用 per-URL 代理的 -c> push <mirror> <branch>` —— **只尝试一次**,
     失败如实报告一次, 不重试 / 不换代理 / 不改走 SSH / 不回滚主线上已完成的推送

主线 / 镜像 / 分支 / 代理 **全部运行期探测**(见 `_ship_config.py`), 不写死任何 URL。

退出码: 0 主线推送成功(镜像失败不影响) · 1 落后主线 / 预检有 STOP · 5 主线推送失败 · 6 核对取不到远端 ref
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Windows GBK 控制台兑底(与 commit.py 同根): git push 的远端输出/ls-remote 结果含 emoji 时,
# GBK 编不出来会让 print 直接 UnicodeEncodeError —— 推送明明已成功, 脚本却崩在打印,
# 执行者会被骗去重推。强制 stdout/stderr 走 UTF-8, 编不出时降级 replace 显示。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ship_config import (  # noqa: E402
    KEY_DEFAULTS,
    load_config,
    proxy_disable_args,
    resolve_branch,
    resolve_main_remote,
    resolve_mirror_remote,
)


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


def resolve(cfg: dict):
    """(分支, 主线名, 主线 URL, 镜像名, 镜像 URL)"""
    branch = resolve_branch(cfg)
    main, main_url = resolve_main_remote(cfg)
    mirror, mirror_url = resolve_mirror_remote(cfg)
    return branch, main, main_url, mirror, mirror_url


# 缺配置时先记下错误, 到 main 里打印引导再退出 —— 别在 import 阶段抛栈
try:
    _CFG, _SRC = load_config()
    _ERR = None
except Exception as exc:  # ConfigMissing / tomllib 缺失
    _CFG, _SRC, _ERR = dict(KEY_DEFAULTS), None, str(exc)

BRANCH, MAIN, MAIN_URL, MIRROR, MIRROR_URL_NOW = resolve(_CFG)


def remote_sha_with_retry(name: str, branch: str) -> str:
    """取远端 ref —— **主线瞬时失败可重试一次**(网络抖动常见, 见项目 pitfalls 的对应条目)。

    取不到(空)与"取到了但不一致"必须区分: 前者是网络, 后者才是推送没落。
    """
    for attempt in range(2):
        proc = git("ls-remote", name, branch)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.split()[0]
        if attempt == 0:
            time.sleep(1)
    return ""


def remotes() -> dict[str, str]:
    out: dict[str, str] = {}
    proc = git("remote", "-v")
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "(push)":
            out[parts[0]] = parts[1]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-mirror", action="store_true", help="不尝试镜像远端")
    parser.add_argument("--skip-preflight", action="store_true", help="跳过推送前的预检(与 commit.py 同名开关对齐)")
    parser.add_argument("--config", default=None, help="指定配置文件(默认 <仓库根>/.commit-flow.toml)")
    args = parser.parse_args(argv)

    global BRANCH, MAIN, MAIN_URL, MIRROR, MIRROR_URL_NOW, _ERR
    if args.config:  # 允许临时换一份配置
        _CFG2, _ = load_config(explicit=args.config)
        BRANCH, MAIN, MAIN_URL, MIRROR, MIRROR_URL_NOW = resolve(_CFG2)
        _ERR = None
    if _ERR:
        print(_ERR)
        return 1

    if not args.skip_preflight:
        from preflight import main as preflight_main  # noqa: E402

        print("=== 预检(--phase push --no-auto: 闸门已在提交前跑过, 这里只核状态) ===")
        # 保留手动那一遍的价值(脏 / 上游 / 红线 / 镜像), 但不再重复跑闸门 ——
        # 闸门会改工作区, 而且刚在 commit 阶段跑过, 这里再跑一遍只会把全量测试做两遍。
        if preflight_main(["--phase", "push", "--no-auto"]) != 0:
            sys.stderr.write("预检有 STOP, 未推送。\n")
            return 1

    print("=== 推送前再 fetch 一次(status -sb 的 ahead/behind 是上次 fetch 的快照) ===")
    git("fetch", MAIN, BRANCH)
    behind_ahead = git("rev-list", "--left-right", "--count", f"{MAIN}/{BRANCH}...HEAD").stdout.split()
    if len(behind_ahead) == 2 and int(behind_ahead[0]) > 0:
        sys.stderr.write(f"落后主线 {behind_ahead[0]} 个提交 —— 先 rebase(工作区必须干净), 不推。\n")
        return 1
    print(f"  与主线齐平(本地领先 {behind_ahead[1] if len(behind_ahead) == 2 else '?'} 个)")

    head = git("rev-parse", "HEAD").stdout.strip()
    print(f"\n=== 推主线 {MAIN}/{BRANCH} ===")
    # 主线瞬时连接失败(Recv failure / reset)可重试一次;
    # 镜像不重试(旧规: 尝试一次, 失败只报一次)
    for attempt in range(2):
        proc = git("push", MAIN, BRANCH)
        if proc.returncode == 0:
            break
        if attempt == 0 and ("Recv failure" in proc.stderr or "Connection was reset" in proc.stderr):
            print("  主线瞬时连接失败, 重试一次 …")
            time.sleep(1)
    print((proc.stdout + proc.stderr).strip())
    if proc.returncode != 0:
        sys.stderr.write("主线推送失败 —— 镜像不再尝试, 先解决主线。\n")
        return 5

    print("\n=== 核对远端 ===")
    remote_sha = remote_sha_with_retry(MAIN, BRANCH)
    if not remote_sha:
        # 取不到 ≠ 推送失败: 别把网络抖动报成"不一致", 那会让执行者重复推或惊慌
        print(f"  **取不到远端 ref**(ls-remote 两次都空/失败) —— 推送命令本身已成功, 请手工确认:")
        print(f"     git ls-remote {MAIN} {BRANCH}   # 期望看到 {head}")
        print(f"  {git('status', '-sb').stdout.splitlines()[0]}")
        return 6
    ok = remote_sha == head
    print(f"  远端 {remote_sha}\n  本地 {head}  →  {'一致' if ok else '**不一致**'}")
    print(f"  {git('status', '-sb').stdout.splitlines()[0]}")

    if args.skip_mirror:
        return 0 if ok else 5

    print(f"\n=== 尝试一次镜像直连({MIRROR or '未找到镜像远端'}) ===")
    if not MIRROR:
        # 注意变量名是 MIRROR_URL_NOW(解析出的镜像 URL); 早年这里写成 MIRROR_URL,
        # 而它从未定义 —— 只有走到"没找到镜像远端"这个分支才会 NameError(主线推送失败时
        # 提前返回, 平时碰不到)。改回正确名字, 并由 test_preflight.py 的静态检查兜住。
        hint = f"git remote add <名字> {MIRROR_URL_NOW}" if MIRROR_URL_NOW else "补一个镜像远端即可(镜像允许滞后)"
        print(f"  没找到镜像远端; 需要时: {hint}")
        return 0 if ok else 5
    # 代理禁用参数从 git config 读, 不写死 key/端口; 没配代理则为空
    proc = git(*proxy_disable_args(MIRROR_URL_NOW), "push", MIRROR, BRANCH)
    out = (proc.stdout + proc.stderr).strip()
    if proc.returncode == 0:
        print(f"  镜像已推: {out.splitlines()[-1] if out else 'ok'}")
    else:
        # 只如实报告一次: 不重试 / 不换代理 / 不改 SSH / 不回滚主线
        print(f"  镜像直连失败(不重试, 镜像允许滞后): {out.splitlines()[-1] if out else '无输出'}")

    return 0 if ok else 5


if __name__ == "__main__":
    raise SystemExit(main())
