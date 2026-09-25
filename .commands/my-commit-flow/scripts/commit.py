"""按项目纪律提交 —— 逐路径暂存(禁 -A) + 提交 + 提交后立即核对 ref 三处。

用法(**不要写死包的安装路径**, `<包>` = 本包目录(`<仓库根>/.commands/my-commit-flow`)):
    python <包>/scripts/commit.py --message-file <文件> <路径> [<路径>...]
        [--skip-preflight]   # 已跑过预检时用

流程:
  1. 跑 preflight(**用 --phase commit**: 落后主线即 STOP —— 提交前必须先合并远端
     (`merge --ff-only` 快进; 树脏走「移出→快进→施回」配方, 预检会打印「同步路径」),
     收尾回写文档也要落在合并后的新基线上, 否则合并时 baseline/切片必撞; 其余 STOP 照旧拦)
  2. `git add -- <你给的路径>` —— **逐路径**, 拒绝 `-A` / `.` / `*`
  3. `git commit -F <消息文件>`(中文首行 + 空行 + 细节; 规模数字要提交那一刻实测)
  4. 调 verify_ref 核对 ref 三处, 不一致 → 退出码 2 并给处置步骤
  5. 打印下一步: `commands run ship.push`(统一调用面, 不暴露裸脚本路径)

不替执行者做历史整合 / push —— 交给执行者按 `references/pipeline.md` 的判据手动跑。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Windows GBK 控制台兑底: git 输出含 emoji(gitmoji 提交首行)时, GBK 编不出来会让 print
# 直接 UnicodeEncodeError —— 提交明明已成功, 脚本却崩在打印、退出码非 0, 执行者会被骗去
# 重跑(实测 2026-09-22: 🐛 首行提交崩在 `print(proc.stdout.strip())`)。强制 stdout/stderr
# 走 UTF-8, 编不出时降级 replace 显示, 不再让输出编码中断流程。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ship_config import ConfigMissing, load_config  # noqa: E402

BULK = {"-A", "--all", ".", "*", "-u", "--update"}


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="要暂存的文件路径(逐路径写, 禁 -A / . / *)")
    parser.add_argument("--message-file", required=True, help="提交消息文件(UTF-8)")
    parser.add_argument("--skip-preflight", action="store_true", help="跳过预检(已跑过时用)")
    parser.add_argument("--config", default=None, help="指定配置文件(默认 <包>/.my-commit-flow.toml)")
    args = parser.parse_args(argv)

    try:  # 外置配置缺失 → 停手引导, 不猜默认值
        cfg, _src = load_config(explicit=args.config)
    except ConfigMissing as exc:
        print(exc)
        return 1
    RED_LINES = cfg["red_lines"]

    bulk = [p for p in args.paths if p in BULK]
    if bulk:
        sys.stderr.write(f"拒绝批量暂存: {' '.join(bulk)} —— 项目纪律是逐路径 git add, 禁 add -A\n")
        return 4

    msg_file = Path(args.message_file)
    if not msg_file.exists():
        sys.stderr.write(f"提交消息文件不存在: {msg_file}\n")
        return 4

    red = [p for p in args.paths if any(r in p for r in RED_LINES)]
    if red:
        sys.stderr.write(f"红线文件不得提交: {' '.join(red)}\n")
        return 4

    if not args.skip_preflight:
        from preflight import main as preflight_main  # noqa: E402

        print("=== 预检 ===")
        # commit 阶段: 落后主线不算 STOP(推送阶段再合流), 其余红线照旧拦
        if preflight_main(["--phase", "commit"]) != 0:
            sys.stderr.write("预检有 STOP, 未提交。\n")
            return 1

    print("\n=== 暂存(逐路径) ===")
    for path in args.paths:
        proc = git("add", "--", path)
        if proc.returncode != 0:
            sys.stderr.write(f"git add 失败: {path}\n{proc.stderr}\n")
            return 5
        print(f"  + {path}")

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout.split()
    print(f"\n暂存清单({len(staged)} 个):")
    for path in staged:
        print(f"  - {path}")

    print("\n=== 提交 ===")
    proc = git("commit", "-F", str(msg_file))
    if proc.returncode != 0:
        sys.stderr.write(f"git commit 失败:\n{proc.stdout}\n{proc.stderr}\n")
        return 5
    print(proc.stdout.strip())

    print("\n=== ref 核对 ===")
    from verify_ref import main as verify_main  # noqa: E402

    rc = verify_main([])
    if rc != 0:
        return rc

    print("\n下一步: commands run ship.push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
