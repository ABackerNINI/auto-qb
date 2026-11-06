"""提交闸门的评审留痕检查 —— 「这一批要不要评、评过没有、声明与实算是否一致」。

挂点: `.commands/my-commit-flow/.my-commit-flow.toml` 的 [[gates]] (每次提交跑, 无待评改动即静默)。
设计口径单点: `.agents/skills/code-review/SKILL.md` ①(触发) / ②(批次与容量) / ⑦(留痕)。

## 为什么是"锚点法"而不是"自报 base"
批次范围 = **最近一条带 `Review:` / `Review-Skip:` 的提交 → 当前工作树**。锚点从 git 历史现算,
agent 不用填 hash(填错就是假账), 且天然"连坐": 谁漏评, 那笔提交就滚进下一批, 由下一批被迫覆盖
——「不留免评节点」是这条规则的全部意义。冷启动(历史里一条都没有)时起点退化为 HEAD, 只算工作树。

## 判据(顺序即优先级)
1. 批内改动 0 行(仅记账类/生成物) → 通过(静默)
2. 实算 < 50 行且未触安全敏感面/红线 → 通过(低于下限, 机械闸门兜住)
3. 实算 < 50 行但触安全敏感面/红线 → 失败(不论行数都要评)
4. 提交信息有 `Review:` 行 → 校验: `<N> 行` 必须等于实算(±0); blocker/修/入池 三个数字齐;
   实算 > 400 行时必须带 `· 分面`(否则应先拆批)
5. 提交信息有 `Review-Skip: <理由>`(理由 ≥4 字) → 通过(豁免进 git log, 可审计)
6. 其余 → 失败, 一行原因 + 下一步
7. 旁路(不判红): `Review:` 行的 `· 齐平 <8hex>` 字段只查格式(计划 26-11-07-0201 落点 3) —— 缺失不问、
   真值不验; 格式异常打一行 `[warn]` 但 rc=0 放行(R4: 弱字段, 与「行数 ±0」的强校验刻意区分)

> 下限排在 trailer 校验之前: 5 行的小改正文里写一句「Review: 见报告」不该被硬拦「缺 `<N> 行` 声明」
> —— 低于下限的批本来就没有 trailer 义务(2026-11-06 评审实测)。

## 计数面
- 计入: 代码 + 事实性文档(计划/报告/约定/坑档/README/AGENTS.md)
- 不计入: **记账类**(`memory-bank/tasks/` `activeContext/` `testing/baselines/`) 与 **生成物**
  (`gen_all.py --list` 的权威清单; 取不到时退回 `_index*.md` 兜底, 不静默失效成"索引重排也算改动")

## 安全敏感面
`red_lines`(读 my-commit-flow 的闸门配置) ∪ 路径标记词(`state` `credential` `auth` `token`
`secret` `password`, 与 review_pack 同源)。命中即"不论行数必须评"。

退出码: 0 通过(含无需评审) · 1 未过(一行原因 + 下一步) · 2 用法/环境错误
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

FLOOR = 50  # 下限: 低于它不要求评审(未实测, 保守推断; 见 reports/26-11-06-0723)
CEILING = 400  # 建议上限: 超过要拆批, 或分面档并在 trailer 记 `· 分面`

REVIEW_LINE_RE = re.compile(r"^Review:\s*(.+)$", re.M)
SKIP_LINE_RE = re.compile(r"^Review-Skip:\s*(.+)$", re.M)
LINES_RE = re.compile(r"(\d+)\s*行")
COUNT_FIELDS = (
    ("blocker", re.compile(r"blocker\s*(\d+)")), ("修", re.compile(r"修\s*(\d+)")), ("入池", re.compile(r"入池\s*(\d+)"))
)

# 记账类: 结构由 check_doc_templates / check_status_drift / gen_active_recent 三道守卫管,
# 它们的内容不进评审面(否则每笔收尾都会被自己的记账逼出一轮评审)。
BOOKKEEPING_PREFIXES = ("memory-bank/tasks/", "memory-bank/activeContext/", "memory-bank/testing/baselines/")

# 安全敏感面路径标记词 —— 与 .commands/review/scripts/review_pack.py 同源(改一处要改两处, 见该文件同名常量)
SENSITIVE_PATH_MARKERS = ("state", "credential", "auth", "token", "secret", "password")

GATE_CONFIG_REL = ".commands/my-commit-flow/.my-commit-flow.toml"

# commit.py 在**合流复跑**那一次之前写下的标记(内容 = 当时的目标 sha, 只作凭据不作判据);
# 本脚本读到即跳过, 并顺手消费掉(一次性)。见 main() 里为什么不能用环境变量。
POST_MARKER = ".git/review_trace_post"

# 齐平字段(计划 26-11-07-0201 落点 3, D6): trailer 末尾可选的 `· 齐平 <8hex>`(评审时点的远端 tip
# 前 8 位, 与评审记录交叉可验)。弱校验(R4): 不强制存在、不验 hash 真值 —— 只查格式, 异常打一行
# [warn] 但 rc=0 放行, 绝不因它判红; 与「行数 ±0」的强校验刻意区分。
FLUSH_PRESENT_RE = re.compile(r"·\s*齐平")
FLUSH_RE = re.compile(r"·\s*齐平\s+([0-9a-f]{8})(?![0-9a-f])")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def find_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise SystemExit(2)  # 不在 git 仓库: 闸门不适用, 不冒充通过
    return Path(proc.stdout.strip()).resolve()


def generated_paths(root: Path) -> set[str]:
    """生成物权威清单(`gen_all.py --list`); 取不到时退回 `_index` 兜底, 不静默失效成"索引重排也算改动"。"""
    script = root / ".agents/skills/memory-bank/scripts/gen_all.py"
    if script.exists():
        proc = subprocess.run(
            [sys.executable, str(script), "--list"],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        if proc.returncode == 0:
            return {line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()}
    return set()  # 兜底由 _is_generated 的 _index 规则承担


def _is_generated(path: str, gen: set[str]) -> bool:
    if path in gen:
        return True
    name = path.rsplit("/", 1)[-1]
    return name.startswith("_index") and name.endswith(".md")


def _counted(path: str, gen: set[str]) -> bool:
    if _is_generated(path, gen):
        return False
    return not any(path.startswith(p) for p in BOOKKEEPING_PREFIXES)


def _numstat(root: Path, base: str, gen: set[str]) -> tuple[int, list[str]]:
    """`base` → 工作树 的改动行数(增+删)与被计数的路径清单。

    `--no-renames`: numstat 默认把改名写成 `a/{b => c}/d` 合成串, 既不是真实路径、也不匹配任何
    前缀 —— 移进记账目录的改名会被当普通改动计入, 生成物的 `{_index.md => _index-1.md}` 也绕开
    排除。改成删+增: 行数偏大(同一内容计两次), 但宁可多算不漏算。
    `core.quotepath=off`: 默认 ON 时非 ASCII 路径被八进制转义加引号, `root / path` 不存在 →
    整批漏计(与 _pipeline.changed_files 同款坑)。
    """
    proc = _git(root, "-c", "core.quotepath=off", "diff", "--numstat", "--no-renames", base)
    if proc.returncode != 0:
        raise SystemExit(2)
    total, files = 0, []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        add, delete, path = parts[0], parts[1], parts[2].strip()
        if not _counted(path, gen):
            continue
        files.append(path)
        if add == "-" or delete == "-":  # 二进制
            continue
        total += int(add) + int(delete)
    return total, files


def _untracked(root: Path, gen: set[str]) -> tuple[int, list[str]]:
    proc = _git(root, "-c", "core.quotepath=off", "ls-files", "--others", "--exclude-standard")
    total, files = 0, []
    for rel in (p.strip() for p in proc.stdout.splitlines()):
        if not rel or not _counted(rel, gen):
            continue
        files.append(rel)
        try:
            raw = (root / rel).read_bytes()
        except OSError:
            continue  # 读不到按 0 行计: 不让一个坏文件把整道闸门卡死
        if b"\x00" in raw[:8192]:
            continue  # 二进制: 随机 0x0A 会被数成上千行, 按 0 计(但仍进 files 供敏感面判定)
        total += len(raw.decode("utf-8", "replace").splitlines())
    return total, files


def red_lines(root: Path) -> list[str]:
    """红线清单与 my-commit-flow 闸门同源; 读不到返回空(不猜)。"""
    cfg = root / GATE_CONFIG_REL
    try:
        import tomllib
        data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return list(data.get("red_lines", []))


def sensitive_hit(files: list[str], reds: list[str]) -> list[str]:
    hits = []
    for f in files:
        low = f.lower()
        if any(r in f for r in reds) or any(m in low for m in SENSITIVE_PATH_MARKERS):
            hits.append(f)
    return hits


def message_text(root: Path, explicit: str | None) -> str:
    """提交信息: 显式参数 → 环境变量(commit.py 注入) → 约定文件 → HEAD 消息。

    闸门在一次提交里会跑两次: 提交前读消息文件; 提交后(合流复跑)文件已消费, 那时 HEAD 就是本次提交
    —— 退到 HEAD 消息正好命中同一份文本。**复跑不靠这个函数区分**(显式 --message-file 的文件不会被
    消费, 按"文件在不在"判会误判), 改由 commit.py 显式注入阶段标记(见 `PHASE_ENV`)。
    """
    for cand in (explicit, os.environ.get("COMMIT_FLOW_MSG_FILE")):
        if cand and Path(cand).exists():
            return Path(cand).read_text(encoding="utf-8", errors="replace")
    default = root / ".git" / "COMMIT_MSG_AI.txt"
    if default.exists():
        return default.read_text(encoding="utf-8", errors="replace")
    proc = _git(root, "log", "-1", "--format=%B")
    return proc.stdout if proc.returncode == 0 else ""


def anchor_commit(root: Path) -> str:
    """最近一条带 `Review:` / `Review-Skip:` 的提交; 一条都没有时退回 HEAD(冷启动只算工作树)。

    ❗**不设扫描窗口**: 曾经用 `-200` 提速, 结果"上一条 trailer 在第 201 笔"时静默退回 HEAD ——
    整段累计批被丢弃且无任何提示, 正好与"漏评提交滚进下一批"的连坐机制相反(2026-11-06 评审实测)。
    几千笔提交的 message 全量解析也就几百 KB, 不值得为它换一个静默失效点。
    """
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    if not head:
        return ""
    proc = _git(root, "log", "--format=%H%x1f%B%x1e")
    for rec in proc.stdout.split("\x1e"):
        if "\x1f" not in rec:
            continue
        sha, _, body = rec.partition("\x1f")
        if REVIEW_LINE_RE.search(body) or SKIP_LINE_RE.search(body):
            return sha.strip()
    return head


def decide(count: int, sensitive: list[str], message: str) -> tuple[bool, str]:
    """纯判定: (是否通过, 失败原因/通过说明)。顺序即优先级, 见模块头「判据」。

    下限/安全面排在 trailer 校验**之前**: 5 行的小改正文里写一句「Review: 见报告」不该被硬拦
    「缺 `<N> 行` 声明」—— 低于下限的批本来就没有 trailer 义务。
    """
    if count == 0 and not sensitive:
        return True, "仅记账类/生成物改动"

    if count < FLOOR:
        if sensitive:
            return False, (f"触碰安全敏感面: {'、'.join(sensitive[:3])} —— 不论行数都要评"
                           "(code-review skill ①)")
        return True, f"低于下限 {FLOOR} 行({count} 行)"

    review = REVIEW_LINE_RE.search(message)
    if review:
        line = review.group(1)
        if count > CEILING and "分面" not in line:
            return False, (f"本批实算 {count} 行 > 建议上限 {CEILING} —— 先拆批(按可独立编译/测试的文件组); "
                           "确实不可拆才走分面档并在 trailer 记 `· 分面`")
        declared = LINES_RE.search(line)
        if not declared:
            return False, f"`Review:` 行缺 `<N> 行` 声明(实算 {count} 行) —— 按 code-review skill ⑦ 的格式补齐"
        if int(declared.group(1)) != count:
            return False, (f"`Review:` 声明 {declared.group(1)} 行 ≠ 实算 {count} 行 —— "
                           "数字必须是提交那一刻实测的, 改对再提交")
        missing = [name for name, rx in COUNT_FIELDS if not rx.search(line)]
        if missing:
            return False, f"`Review:` 行缺字段: {'/'.join(missing)} —— 按 skill ⑦ 的格式补齐"
        return True, f"已评审 {count} 行"

    skip = SKIP_LINE_RE.search(message)
    if skip:
        reason = skip.group(1).strip()
        if len(reason) < 4:
            return False, "`Review-Skip:` 的理由为空或过短 —— 写清为什么这批不用评(≥4 字), 理由会进 git log"
        return True, f"豁免: {reason}"

    return False, (
        f"本批累计 {count} 行待评未留痕 —— 先跑 code-review skill(批次 base = 最近一条 `Review:` 提交), "
        "再在提交信息里写 `Review: <范围> · <N> 行 · blocker N · 修 N · 入池 N`; "
        "确属免评写 `Review-Skip: <理由>`"
    )


def flush_field_warn(message: str) -> str | None:
    """齐平字段的弱校验(计划 26-11-07-0201 落点 3) —— 返回 warn 文案或 None(静默)。

    与 decide() 分开成纯函数: 齐平不参与判红(R4), warn 是 v3「全过即静默」的唯一让步, 只在字段被
    写坏时出现。判定面: `Review:` 行里出现 `· 齐平` 才查; 带合法 8 位小写 hex → None; 出现了但格式
    不符(缺 hash / 非 8 位 / 大写 / 缺空格)→ 一行 warn。范围文本里撞到「齐平」二字但前面不是 · 的
    不算字段, 不误报。
    """
    for body in REVIEW_LINE_RE.findall(message):
        if not FLUSH_PRESENT_RE.search(body):
            continue
        if FLUSH_RE.search(body):
            continue
        return ("[warn] `Review:` 行齐平字段格式异常 —— 应为 `· 齐平 <8位hex>`"
                "(远端 tip 前 8 位; 弱校验仅提示不拦提交)")
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=None, help="仓库根(缺省由 git 探测)")
    parser.add_argument("--message-file", default=None, help="提交信息文件(缺省: env → .git/COMMIT_MSG_AI.txt → HEAD)")
    args = parser.parse_args(argv)

    root = find_root(args.root)
    # 合流复跑(commit.py 步骤 6b)跳过: 那次验的是"合并后的树", 消息已落库、行数已对过, 再算一遍
    # 只会把 rebase 进来的远端提交算成本批 → 假红。
    # ! **用文件标记, 不用环境变量**: 闸门里会跑 pytest, 子进程继承 env —— 实测 `COMMIT_FLOW_GATE_PHASE`
    #   传下去后, 包测试里"跑闸门脚本并断言它判红"的用例全部拿到 0, 3 条自测在复跑轮齐红(2026-11-06)。
    #   标记由 commit.py 在复跑前写下、跑完 finally 删; 这里读到即消费(一次性), 残留最多漏检一次。
    marker = root / POST_MARKER
    if marker.exists():
        marker.unlink(missing_ok=True)
        return 0

    msg = message_text(root, args.message_file)

    gen = generated_paths(root)
    base = anchor_commit(root)
    if not base:
        print("评审留痕检查: 仓库还没有任何提交 —— 无批可言, 跳过")
        return 0

    tracked_lines, tracked_files = _numstat(root, base, gen)
    untracked_lines, untracked_files = _untracked(root, gen)
    count = tracked_lines + untracked_lines
    files = tracked_files + untracked_files
    sensitive = sensitive_hit(files, red_lines(root))

    ok, why = decide(count, sensitive, msg)
    warn = flush_field_warn(msg)
    if warn:
        # 弱校验的让步输出(计划 26-11-07-0201 落点 3): 不改判定, 只提醒字段写坏了 —— 判定仍由 decide 独立给
        print(warn)
    if ok:
        return 0  # v3 契约: 全过即静默(仅记账/生成物这类"本来就没批"的情形也静默; warn 是唯一让步)
    print(f"评审留痕: {why}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
