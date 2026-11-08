"""收口评审的机械面: 评审包生成(review.pack)与发现引文校验(review.check)。

code-review skill 的配套脚本(八节规程见 .agents/skills/code-review/SKILL.md):
- pack:  基线与 HEAD hash / diff 统计与分档提示(>400 行或安全敏感面命中 -> 分面) /
         基哈希(「base -> 工作树」过滤后 diff 的确定性哈希, 过滤面与提交闸门共用
         review_content.py 单点, 记账类/生成物变更不影响) /
         文件清单 / 红线与安全敏感面预警。红线清单与 my-commit-flow 闸门同源(读
         .commands/my-commit-flow/.my-commit-flow.toml 的 red_lines / warn_lines),
         这里只做提示, 拦截仍归提交闸门; 闸门配置读不到/解析失败给可见警告并降级。
- check: 对 reviewer 产出的 findings JSON 逐条校验 —— 字段齐全、severity/relevance 枚举、
         quote 与源码逐字比对(单行内连续片段, 行号允许 +-window 邻近; file 越出仓库根
         一律 REFUTE; 非 UTF-8 文件按字节序兜底比对并在原因行注明)。
         REFUTE 的发现直接弃, 不复核(幻觉引文是 LLM 评审的头号失效模式)。

用法:
  python review_pack.py pack  --base <rev> [--root DIR]
  python review_pack.py check --findings <json文件|-> [--root DIR] [--window N]

退出码: check 0=全部通过 1=存在 REFUTE; 两命令 2=用法/环境/输入错误(缺 --base / 非 git
仓库 / findings 非 UTF-8 或非法 JSON 等)。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_content import batch_base_hash  # noqa: E402  (同目录共享模块: 基哈希的过滤判定与提交闸门单点同源)

SEVERITIES = ("blocker", "major", "minor", "nit")
RELEVANCES = ("相关", "不相关")
REQUIRED_FIELDS = ("file", "line", "quote", "severity", "claim", "relevance", "fix")
MIN_QUOTE = 4  # 过短引文无法定位, 视同无效证据
TIER_LIMIT = 400  # 单次评审 diff 行数上限(SmartBear/Cisco 检出率衰减点)
DEFAULT_WINDOW = 3  # quote 实际行与声称行允许的邻近偏差

GATE_CONFIG = ".commands/my-commit-flow/.my-commit-flow.toml"

# 安全敏感面提示词(凭据/网络/状态写入): 新增行命中正则, 或路径含标记词 —— 是提示不是闸门
SENSITIVE_LINE_RE = re.compile(r"(?i)(password|passwd|secret|token|credential|api[_-]?key)")
SENSITIVE_PATH_MARKERS = ("state", "credential", "auth", "token", "secret", "password")


def _die(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(2)


def _flat(value) -> str:
    """不受信字段进输出前单行化: 控制字符(含换行)替换为空格, 堵输出行注入。"""
    return "".join(ch if ch.isprintable() else " " for ch in str(value))


def _git(root: Path, *args: str) -> str:
    # 固定 quotepath=off: 仓库有成百上千个非 ASCII 路径, 依赖机器级 git 配置会让清单/归因在别的 clone
    # 或 CI 上静默失真(同包 _pipeline.py 同类事故的处置口径)。
    cmd = ["git", "-c", "core.quotepath=off", *args]
    try:
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as exc:
        _die(f"git 启动失败: {exc}")
    if proc.returncode != 0:
        _die(f"git {' '.join(args)} 失败: {proc.stderr.strip()}")
    return proc.stdout


def _resolve_root(explicit: str | None, require_git: bool = True) -> Path:
    # require_git=False: check 支持 --root 指向 git archive 导出的快照(非 git 只读树),
    # 引文校验只按 root/file 读文件, 不需要 git; pack 要做 diff 归因, 保持强校验。
    if explicit:
        root = Path(explicit).resolve()
        if require_git and not (root / ".git").exists():
            _die(f"--root {root} 不是 git 仓库(缺 .git)")
        return root
    proc = None
    try:
        proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, encoding="utf-8")
    except OSError as exc:
        _die(f"git 启动失败: {exc}")
    if proc.returncode != 0:
        _die("当前目录不在 git 仓库内(也没有 --root)")
    return Path(proc.stdout.strip()).resolve()


def _load_gate_lines(root: Path) -> tuple[list[str], list[str]]:
    """红线/警告清单与提交闸门同源; 读不到或解析失败给可见警告并降级为空(不静默)。"""
    path = root / GATE_CONFIG
    if not path.exists():
        print(f"[warn] 读不到 {GATE_CONFIG}, 红线预警不可用(提交闸门不受影响)")
        return [], []
    try:
        cfg = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, OSError) as exc:
        print(f"[warn] {GATE_CONFIG} 解析失败({exc}), 红线预警不可用(提交闸门不受影响)")
        return [], []
    return list(cfg.get("red_lines", [])), list(cfg.get("warn_lines", []))


def _match_rule(path: str, pattern: str) -> bool:
    # 与提交闸门同口径: commit.py 按子串匹配(any(r in p)), 这里保持同源, 避免嵌套路径下预警漏报
    return pattern in path


def _hit_rules(paths: list[str], rules: list[str]) -> list[str]:
    return sorted({f"{p} (命中 {r})" for p in paths for r in rules if _match_rule(p, r)})


def _count_lines(path: Path) -> int:
    try:
        data = path.read_bytes()
    except OSError:
        return -1  # 不可读(独占锁/坏链接), 调用处降级为 [不可读] 不崩
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


# --------------------------------------------------------------------------- pack


def cmd_pack(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    base = _git(root, "rev-parse", "--verify", args.base).strip()
    head = _git(root, "rev-parse", "HEAD").strip()

    shortstat = _git(root, "diff", "--shortstat", base).strip()
    m = re.search(r"(\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?", shortstat)
    files_n = int(m.group(1)) if m else 0
    ins = int(m.group(2)) if m and m.group(2) else 0
    dele = int(m.group(3)) if m and m.group(3) else 0

    changed: list[str] = []
    deleted: list[str] = []
    for row in _git(root, "diff", "--name-status", base).splitlines():
        parts = row.split("\t")
        if not parts or not parts[0]:
            continue
        status, path = parts[0][0], parts[-1]
        changed.append(path)
        if status == "D":
            deleted.append(path)

    untracked = [p for p in _git(root, "ls-files", "--others", "--exclude-standard").splitlines() if p]
    untracked_lines: dict[str, int] = {}
    for p in untracked:
        n = _count_lines(root / p)
        if n < 0:
            print(f"[warn] 未跟踪文件不可读, 按 0 行计: {p}")
            n = 0
        untracked_lines[p] = n

    # 按文件归因的新增行: 只认 hunk 内的 '+' 行(+++ 头在 hunk 外, 内容以 ++ 开头也不会被误当元数据);
    # 新路径取 +++ b/<path> 头, 不再从 diff --git 行 rsplit(新旧路径本身含 " b/" 都能正确归属)。
    current: str | None = None
    in_hunk = False
    per_file_added: dict[str, list[str]] = {}
    for line in _git(root, "diff", "-U0", base).splitlines():
        if line.startswith("diff --git "):
            current = None
            in_hunk = False
        elif line.startswith("@@"):
            in_hunk = True
        elif not in_hunk and line.startswith("+++ b/"):
            # git 对含空格的路径在 +++ 头末尾补一个 TAB —— 必须剥掉, 否则归因键带尾随 TAB 且与 name-status 重名
            current = line[len("+++ b/"):].rstrip("\t")
        elif not in_hunk and line.startswith("+++ /dev/null"):
            current = None
        elif in_hunk and line.startswith("+") and current:
            per_file_added.setdefault(current, []).append(line[1:])
    sensitive_hits = {p for p in changed + untracked if any(mark in p.lower() for mark in SENSITIVE_PATH_MARKERS)}
    sensitive_hits |= {
        p
        for p, added in per_file_added.items() if any(SENSITIVE_LINE_RE.search(line) for line in added)
    }
    for p in untracked:
        if p in sensitive_hits:
            continue
        try:
            content = (root / p).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(SENSITIVE_LINE_RE.search(line) for line in content.splitlines()):
            sensitive_hits.add(p)
    sensitive_hits = sorted(sensitive_hits)

    all_paths = changed + untracked
    red_rules, warn_rules = _load_gate_lines(root)
    red_hits = _hit_rules(all_paths, red_rules)
    warn_hits = _hit_rules(all_paths, warn_rules)

    total = ins + dele + sum(untracked_lines.values())
    # 分档两判据与 skill ③/D14 一致: 行数超限 或 触安全敏感面 -> 分面
    tier = "分面 (2-3 个: 正确性 / 安全 / 测试缺口)" if total > TIER_LIMIT or sensitive_hits else "全能 (1 个子代理)"

    print(f"基线: {base}")
    print(f"HEAD: {head}" + (" (== 基线, 只有未提交改动)" if head == base else ""))
    print(
        f"diff 统计: {files_n} 个已跟踪文件变更, +{ins}/-{dele}" +
        (f", 另有 {len(untracked)} 个未跟踪文件共 {sum(untracked_lines.values())} 行" if untracked else "")
    )
    # 基哈希(计划 26-11-08-1240 §03 3.3): 「base -> 工作树」过滤后 diff 的确定性哈希 —— 过滤判定与
    # 提交闸门共用 review_content 单点, 末轮评审后补写记账类/生成物不影响它(不误红, D6/R4)。
    print(f"基哈希: {batch_base_hash(root, base)}")
    print(f"评审规模: {total} 行 -> 分档: {tier}")
    print(f"安全敏感面: {'; '.join(sensitive_hits) if sensitive_hits else '无'}")
    print(f"红线预警: {'; '.join(red_hits) if red_hits else '无'}" + ("  <-- 出现即停, 移出评审范围并回滚" if red_hits else ""))
    if warn_hits:
        print(f"警告清单: {'; '.join(warn_hits)}")
    if deleted:
        print(f"删除文件(引文校验将不可用): {'; '.join(deleted)}")
    print("文件清单:")
    for p in changed:
        mark = " [已删除]" if p in deleted else ""
        print(f"  {p}{mark}")
    for p, n in untracked_lines.items():
        print(f"  {p} [未跟踪 +{n} 行]")
    return 0


# --------------------------------------------------------------------------- check


def _verify(finding: dict, root: Path, window: int) -> tuple[bool, str]:
    missing = [k for k in REQUIRED_FIELDS if k not in finding]
    if missing:
        return False, f"字段缺失: {', '.join(missing)}"
    if finding["severity"] not in SEVERITIES:
        return False, f"severity 非法: {finding['severity']!r} (合法: {'|'.join(SEVERITIES)})"
    if finding["relevance"] not in RELEVANCES:
        return False, f"relevance 非法: {finding['relevance']!r} (合法: {'|'.join(RELEVANCES)})"
    quote = finding["quote"]
    if not isinstance(quote, str) or len(quote) < MIN_QUOTE:
        return False, f"quote 过短(<{MIN_QUOTE} 字符), 无法作为证据"
    if not isinstance(finding["line"], int) or finding["line"] < 1:
        return False, "line 必须是正整数(1 起)"
    if not isinstance(finding["file"], str) or not finding["file"]:
        return False, "file 必须是非空字符串(仓库相对路径)"
    resolved = (root / finding["file"]).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return False, "file 越出仓库根(绝对路径/.. 穿越, 拒绝)"
    if not resolved.is_file():
        return False, f"文件不存在或已删除: {_flat(finding['file'])}"
    try:
        text = resolved.read_text(encoding="utf-8")
        enc_note = ""
    except UnicodeDecodeError:
        text = resolved.read_bytes().decode("latin-1")  # 1:1 字节映射, ASCII 引文仍可逐字命中
        enc_note = "(文件非 UTF-8, 按字节序比对)"
    except OSError as exc:
        return False, f"文件读取失败: {exc}"
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    found = [i + 1 for i, line in enumerate(lines) if quote in line]
    if not found:
        return False, f"引文不在文件中(幻觉引文, 直接弃){enc_note}"
    drift = min(abs(found_at - finding["line"]) for found_at in found)
    if drift > window:
        shown = ", ".join(str(x) for x in found[:5])
        return False, f"行号偏移 {drift} 行(>{window}), 引文实际在: {shown}{enc_note}"
    return True, f"实际行 {min(found, key=lambda x: abs(x - finding['line']))}{enc_note}"


def cmd_check(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root, require_git=False)  # --root 允许指向快照目录(非 git 树), 见 _resolve_root 注释
    if args.findings == "-":
        try:
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")  # 裸 python 可能按 locale(cp936)解码
        except (AttributeError, OSError):
            pass
        raw = sys.stdin.read()
    else:
        fpath = Path(args.findings)
        if not fpath.is_file():
            _die(f"--findings 文件不存在: {args.findings}")
        try:
            raw = fpath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            _die(f"--findings 读取失败(需 UTF-8 文本): {exc}")
    try:
        findings = json.loads(raw)
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        _die(f"findings 不是合法 JSON: {exc}")
    if not isinstance(findings, list):
        _die("findings 必须是 JSON 数组(skill ④ schema)")

    passed: dict[str, int] = dict.fromkeys(SEVERITIES, 0)
    refuted = 0
    for idx, finding in enumerate(findings, 1):
        if not isinstance(finding, dict):
            print(f"[REFUTE] #{idx} 不是 JSON 对象")
            refuted += 1
            continue
        ok, reason = _verify(finding, root, args.window)
        label = f"#{idx} {_flat(finding.get('file', '?'))}:{_flat(finding.get('line', '?'))} [{_flat(finding.get('severity', '?'))}]"
        print(f"[{'PASS' if ok else 'REFUTE'}] {label} {reason}")
        if ok:
            passed[finding["severity"]] += 1
        else:
            refuted += 1

    total_ok = sum(passed.values())
    print(
        f"汇总: {len(findings)} 条 / 通过 {total_ok} / 弃 {refuted}" +
        f" (blocker {passed['blocker']} / major {passed['major']} / minor {passed['minor']} / nit {passed['nit']})"
    )
    if refuted:
        print("被弃条目不进入裁决; 引文约定的单行连续片段与 ±%d 行邻近窗口见 code-review skill ④" % args.window)
    return 1 if refuted else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="收口评审机械面: pack=评审包生成, check=发现引文校验")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pack = sub.add_parser("pack", help="评审包: 基线/分档/文件清单/红线预警")
    p_pack.add_argument("--base", required=True, help="任务起点 rev(任务第一个 commit 的 parent / 上次收口 commit)")
    p_pack.add_argument("--root", help="仓库根(默认取 cwd 所在仓库)")

    p_check = sub.add_parser("check", help="findings 引文逐字校验")
    p_check.add_argument("--findings", required=True, help="findings JSON 文件路径, '-' 读 stdin")
    p_check.add_argument("--root", help="仓库根(默认取 cwd 所在仓库)")
    p_check.add_argument("--window", type=int, default=DEFAULT_WINDOW, help=f"行号邻近窗口(默认 {DEFAULT_WINDOW})")

    args = parser.parse_args()
    return cmd_pack(args) if args.cmd == "pack" else cmd_check(args)


if __name__ == "__main__":
    raise SystemExit(main())
