"""按项目纪律提交并推送 —— 缺省**全量提交本次改动**(逐路径 add, 禁 -A) + 核 ref + 自动续推。

用法(**不要写死包的安装路径**, `<包>` = 本包目录(`<仓库根>/.commands/my-commit-flow`)):
    python <包>/scripts/commit.py [--message-file <文件>] [路径...] [--skip-preflight] [--no-push]

零参数 = 提交**全部改动**: 清单来自 `changed_files()`(与预检同一权威单点, 不让调用方手抄),
红线照拦、暂存清单显式打印。传路径 = 子集提交(会提示"未纳入"数量, 治「漏传文件静默不提交」)。
消息文件缺省读约定路径 `<root>/.git/COMMIT_MSG_AI.txt` —— .git 内永不入库(不触红线)、
多 clone 各自隔离、路径跨平台恒定; 调用方只剩「写消息 → 跑一条命令」两个动作。
**消费即删**: 提交落稳(ref 三处核对通过)后脚本自动删除约定路径的消息文件 ——
文件存在 = 有待提交的消息, 提交后不残留旧消息(固定路径 + 跨提交残留会让回看者把
旧消息当现状), 下次提交前必须重写; 显式 --message-file 指向非约定路径的文件归调用方管, 不删。

流程:
  1. 跑 preflight(**--phase commit**: 落后主线即 STOP —— 先合并远端, 收尾回写也要落在合并后的新基线上)
  2. 逐路径 `git add`(拒绝 -A / . / *)
  3. `git commit -F <消息文件>`(中文首行 + 空行 + 细节; 规模数字要提交那一刻实测)
  4. verify_ref 核对 ref 三处, 不一致给处置步骤; 通过后**删除消息文件**(消费即删)
  5. **同进程续跑 push 全流程**(--no-auto 预检 → 推主线 → 核对远端 → 一次镜像; `--no-push` 停在提交);
     推送未通过 ≠ 提交失败 —— RESULT: PARTIAL, 补跑 ship.push 即可, 别重新提交
  6. 末行按输出契约收尾(RESULT: / WHY: / NEXT:) —— 引擎保证协议行不被摘要截掉

退出码: 0 提交成功(推送未完成为 RESULT: PARTIAL, 退出码仍 0 —— 补推即可) · 1 预检 STOP ·
4 拒绝(红线 / 批量 / 消息缺失 / 无改动) · 5 git 失败 · 2/3 透传 verify_ref
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
from _ship_config import ConfigMissing, find_root, load_config  # noqa: E402
from preflight import changed_files  # noqa: E402

BULK = {"-A", "--all", ".", "*", "-u", "--update"}
DEFAULT_MESSAGE_REL = Path(".git") / "COMMIT_MSG_AI.txt"


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


def default_message_path(root: Path) -> Path:
    """消息文件的约定单点 —— <root>/.git/COMMIT_MSG_AI.txt(永不入库, 多 clone 隔离)。"""
    return root / DEFAULT_MESSAGE_REL


def consume_message_file(msg_file: Path, root: Path) -> None:
    """消费即删 —— 提交落稳后删除约定路径的消息文件, 防旧消息残留被回看者当现状。

    只删约定路径: 显式 --message-file 指向别处的文件归调用方管。删除失败只警告
    不影响退出码 —— 提交已成功, 别让收尾环节的失败骗执行者重跑(同 stdout 编码兜底的教训)。
    """
    if msg_file != default_message_path(root):
        return
    try:
        msg_file.unlink()
        print(f"消息文件已消费删除: {msg_file}(下次提交前必须重写)")
    except OSError as exc:
        print(f"⚠ 消息文件删除失败({exc}); 请手动删除 {msg_file}, 避免下次提交误读旧消息")


def resolve_stage_plan(paths: list[str], red_lines: list[str]) -> tuple[list[str], list[str], str | None]:
    """算暂存计划, 返回 (to_stage, omitted, refuse); refuse 非 None 即拒绝执行。

    paths 为空 → 全量改动(权威单点 changed_files); 传路径 → 子集, omitted = 改动了
    但没被纳入的文件(把"漏传"从静默变成可见)。红线按既有的子串口径匹配。
    """
    bulk = [p for p in paths if p in BULK]
    if bulk:
        return [], [], f"拒绝批量暂存: {' '.join(bulk)}"
    staged, unstaged = changed_files()
    all_changed = staged + unstaged
    if paths:
        to_stage = list(paths)
        omitted = [p for p in all_changed if p not in set(paths)]
    else:
        to_stage = all_changed
        omitted = []
    if not to_stage:
        return [], [], "没有可提交的改动(staged 0 / unstaged 0)"
    red = [p for p in to_stage if any(r in p for r in red_lines)]
    if red:
        return [], [], f"红线文件不得提交: {' '.join(red)}"
    return to_stage, omitted, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="要暂存的路径(缺省 = 全部改动); 传了即子集提交")
    parser.add_argument(
        "--message-file", default=None, help=f"提交消息文件(缺省 <root>/{DEFAULT_MESSAGE_REL}; 提交落稳后约定路径的会被自动删除)"
    )
    parser.add_argument("--skip-preflight", action="store_true", help="跳过预检(已跑过时用)")
    parser.add_argument("--no-push", action="store_true", help="只提交不推送(补推: commands run ship.push)")
    parser.add_argument("--config", default=None, help="指定配置文件(默认 <包>/.my-commit-flow.toml)")
    args = parser.parse_args(argv)

    try:  # 外置配置缺失 → 停手引导, 不猜默认值
        cfg, _src = load_config(explicit=args.config)
    except ConfigMissing as exc:
        print(exc)
        return 1
    RED_LINES = cfg["red_lines"]
    root = find_root()

    to_stage, omitted, refuse = resolve_stage_plan(args.paths, RED_LINES)
    if refuse:
        if refuse.startswith("拒绝批量"):
            sys.stderr.write(
                f"RESULT: FAIL {refuse}\n"
                "WHY: 项目纪律是逐路径 git add, 禁 add -A / . / *(防误交红线与在途改动)\n"
                "NEXT: 用显式路径重跑, 或零参数跑(缺省全量改动, 红线照拦): commands run ship.commit\n"
            )
        elif refuse.startswith("没有可提交"):
            sys.stderr.write(
                f"RESULT: STOP {refuse}\n"
                "WHY: 工作区是干净的 —— 改动可能在别的 clone 或未保存\n"
                "NEXT: 确认改动位置; 若确有改动, 在正确的工作树里重跑 commands run ship.commit\n"
            )
        else:  # 红线
            sys.stderr.write(
                f"RESULT: FAIL {refuse}\n"
                "WHY: 红线是生产文件(见 AGENTS.md「红线」节), 一行都不许进提交\n"
                "NEXT: 把它们移出提交范围后重跑 commands run ship.commit\n"
            )
        return 4

    msg_file = Path(args.message_file) if args.message_file else default_message_path(root)
    if not msg_file.exists():
        sys.stderr.write(
            f"RESULT: FAIL 提交消息文件不存在: {msg_file}\n"
            "WHY: 提交消息是必需要素; 约定文件消费即删(上次提交落稳后已删除), 每次提交前都要重写\n"
            f"NEXT: 把提交消息(中文首行 + 空行 + 动机/取舍/影响面/实测数字)写入 {msg_file} 后重跑 commands run ship.commit\n"
        )
        return 4

    if not args.skip_preflight:
        from preflight import main as preflight_main  # noqa: E402

        print("=== 预检 ===")
        # commit 阶段: 落后主线是 STOP(先合并远端, 收尾回写落在合并后的新基线上), 其余红线照旧拦
        if preflight_main(["--phase", "commit"]) != 0:
            sys.stderr.write(
                "RESULT: STOP 预检有 STOP, 未提交\n"
                "WHY: 见上方检查表的 STOP 行\n"
                "NEXT: 按检查表处理(落后先按「同步路径」合并远端)后重跑 commands run ship.commit\n"
            )
            return 1

    print("\n=== 暂存(逐路径) ===")
    for path in to_stage:
        proc = git("add", "--", path)
        if proc.returncode != 0:
            sys.stderr.write(
                f"RESULT: FAIL git add 失败: {path}\n"
                f"WHY: {proc.stderr.strip() or 'git 非 0(明细见上)'}\n"
                "NEXT: 核对路径(已删除? 大小写?)后重跑 commands run ship.commit\n"
            )
            return 5
        print(f"  + {path}")
    if omitted:
        shown = "、".join(omitted[:3]) + ("…" if len(omitted) > 3 else "")
        print(f"  …(子集提交: 另有 {len(omitted)} 个改动未纳入({shown}) —— 确认这是有意的)")

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
        detail = (proc.stdout + proc.stderr).strip().splitlines()
        sys.stderr.write(
            "RESULT: FAIL git commit 失败\n"
            f"WHY: {detail[-1] if detail else 'git 非 0(明细见上)'}\n"
            "NEXT: 按明细处理后重跑 commands run ship.commit\n"
        )
        return 5
    print(proc.stdout.strip())
    sha = git("rev-parse", "--short", "HEAD").stdout.strip()

    print("\n=== ref 核对 ===")
    from verify_ref import main as verify_main  # noqa: E402

    rc = verify_main([])
    if rc != 0:
        sys.stderr.write(
            "RESULT: FAIL ref 三处不一致 —— 提交可能没落稳\n"
            "WHY: verify_ref 的判据与处置步骤见上方输出\n"
            "NEXT: 确认无他人操作 .git 后按处置步骤处理; 复核: commands run my-commit-flow.verify-ref\n"
        )
        return rc

    consume_message_file(msg_file, root)

    if args.no_push:
        print(f"\nRESULT: OK {sha} 已提交({len(staged)} 个文件, --no-push 未推送); 下一步: commands run ship.push")
        return 0

    print("\n=== 推送(自动续跑) ===")
    from push import main as push_main  # noqa: E402

    if push_main([], emit_result=False) != 0:
        sys.stderr.write(
            f"RESULT: PARTIAL {sha} 已提交({len(staged)} 个文件), 推送未完成\n"
            "WHY: 推送阶段未通过(落后 / 取不到远端 / 推送失败 —— 原因见上方推送段)\n"
            "NEXT: commands run ship.push  (提交已落, 只需补推; 落后先按「同步路径」合并远端)\n"
        )
        return 0
    print(f"\nRESULT: OK {sha} 已提交({len(staged)} 个文件)并推送; 远端与本地一致; 镜像结果见上")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
