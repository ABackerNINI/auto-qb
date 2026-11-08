"""提交闸门的评审留痕检查 —— 「这一批要不要评、评过没有、声明与实算是否一致」。

挂点: `.commands/my-commit-flow/.my-commit-flow.toml` 的 [[gates]] (每次提交跑, 无待评改动即静默)。
设计口径单点: `.agents/skills/code-review/SKILL.md` ①(触发) / ②(批次与容量) / ⑦(留痕)。

## 为什么是"锚点法"而不是"自报 base"
批次范围 = **最近一条带 `Review:` / `Review-Skip:` 的提交 → 当前工作树**。锚点从 git 历史现算,
agent 不用填 hash(填错就是假账), 且天然"连坐": 谁漏评, 那笔提交就滚进下一批, 由下一批被迫覆盖
——「不留免评节点」是这条规则的全部意义。冷启动(历史里一条都没有)时起点退化为 HEAD, 只算工作树。
锚点与计数都**走主线(first-parent)**、批次行数**逐笔累计**(合并提交取对第一父母的差): 合并拓扑下
树差 ≠ 新增提交, 侧分支 trailer 也不遮蔽主线 —— 详见 anchor_commit / _numstat 的 docstring 与
issue 26-11-08-0903。

## 判据(顺序即优先级)
1. 批内改动 0 行(仅记账类/生成物) → 通过(静默)
2. 实算 < 50 行且未触安全敏感面/红线 → 通过(低于下限, 机械闸门兜住)
3. 实算 < 50 行但触安全敏感面/红线 → 失败(不论行数都要评)
4. 提交信息有 `Review:` 行 → 校验(计划 26-11-07-0441): `<N> 行` 必须等于实算(±0); blocker/修/入池 数字齐;
   `检 P/T` 必填且 0 ≤ P ≤ T、P ≥ 修 + 入池(T=送检发现数, P=引文逐字通过数; 修/入池 只数过检且未被
   REFUTE 的发现); 实算 > 400 行时必须带 `· 派发 <K>` 且 K ≥ 2(先拆批, `· 分面` 不再是超限通路);
   超限无派发/缺字段(含缺检)/行数不符 三类失败行尾附可粘贴整行骨架(行数位填实算, `?` 直贴必再判红)
5. 提交信息有 `Review-Skip: <理由>`(理由 ≥4 字) → 通过(豁免进 git log, 可审计)
6. 其余 → 失败, 一行原因 + 下一步
7. 旁路(不判红): `· 齐平 <8hex>` 字段只查格式(计划 26-11-07-0201 落点 3) —— 缺失不问、真值不验;
   格式异常打一行 `[warn]` 但 rc=0 放行(R4: 弱字段, 与「行数 ±0」的强校验刻意区分); `· 分面` 同为
   信息字段(0441 D8) —— 任何档位都不判红, 也不再放行超限

> 下限排在 trailer 校验之前: 5 行的小改正文里写一句「Review: 见报告」不该被硬拦「缺 `<N> 行` 声明」
> —— 低于下限的批本来就没有 trailer 义务(2026-11-06 评审实测)。

## 计数面
- 计入: 代码 + 事实性文档(计划/报告/约定/坑档/README/AGENTS.md)
- 不计入: **记账类**(`memory-bank/tasks/` `activeContext/` `testing/baselines/`, 以及
  `reports/attachments/legacy-review4/` 整目录 —— R4 存量评审的 findings/manifest/路线小结是被评代码
  的产物, 0441 落点 3/D3) 与 **生成物**(`gen_all.py --list` 的权威清单; 取不到时退回 `_index*.md`
  兜底, 不静默失效成"索引重排也算改动")
- 判定实现单点在 review_content.py(与 review.pack 的基哈希共用同一份排除面, 计划 26-11-08-1240
  §03 3.3) —— 本脚本只消费, 不复写判据

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_content import _counted, generated_paths  # noqa: E402  (同目录共享模块: 可评路径判定与基哈希, 与 review_pack 单点同源)

FLOOR = 50  # 下限: 低于它不要求评审(未实测, 保守推断; 见 reports/26-11-06-0723)
CEILING = 400  # 建议上限: 超过先拆批; 确实不可拆的残余批须 `· 派发 <K>` 且 K ≥ 2(计划 26-11-07-0441 D1)

REVIEW_LINE_RE = re.compile(r"^Review:\s*(.+)$", re.M)
SKIP_LINE_RE = re.compile(r"^Review-Skip:\s*(.+)$", re.M)
LINES_RE = re.compile(r"(\d+)\s*行")
COUNT_FIELDS = (
    ("blocker", re.compile(r"blocker\s*(\d+)")), ("修", re.compile(r"修\s*(\d+)")), ("入池", re.compile(r"入池\s*(\d+)"))
)
# 检 P/T(0441 落点 2): T = 送检发现数, P = 引文逐字通过数(review.check 判过的条目)。值正则取斜杠形式;
# `·` 锚定的在场正则只用来区分「缺字段」与「写了但形状不对」(直贴骨架的 `检 ?/?` 不许静默通过)。
CHECK_RE = re.compile(r"检\s*(\d+)\s*/\s*(\d+)")
CHECK_PRESENT_RE = re.compile(r"·\s*检")
# 派发 K(0441 落点 1): 值正则锚定 `·` 前缀(D10: 防正文散文「派发 2 个子代理」过采), 缺省 1;
# 在场正则同锚 —— 直贴骨架的 `派发 ?` 落「形状不对」判红, 不会按缺省静默通过。
DISPATCH_RE = re.compile(r"·\s*派发\s*(\d+)")
DISPATCH_PRESENT_RE = re.compile(r"·\s*派发")

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


def _count_numstat(root: Path, git_args: list[str], gen: set[str], total: int,
                   files: list[str]) -> tuple[int, list[str]]:
    """跑一条 numstat 类 git 命令并把结果累计进 (total, files)。

    `--no-renames`: numstat 默认把改名写成 `a/{b => c}/d` 合成串, 既不是真实路径、也不匹配任何
    前缀 —— 移进记账目录的改名会被当普通改动计入, 生成物的 `{_index.md => _index-1.md}` 也绕开
    排除。改成删+增: 行数偏大(同一内容计两次), 但宁可多算不漏算。
    `core.quotepath=off`: 默认 ON 时非 ASCII 路径被八进制转义加引号, `root / path` 不存在 →
    整批漏计(与 _pipeline.changed_files 同款坑)。
    """
    proc = _git(root, "-c", "core.quotepath=off", *git_args)
    if proc.returncode != 0:
        raise SystemExit(2)
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


def _numstat(root: Path, base: str, gen: set[str]) -> tuple[int, list[str]]:
    """`base` 之后的主线提交逐笔 + 侧分支无 trailer 提交 + 工作树 的改动行数(增+删)与路径清单。

    为什么逐笔不整段树差: base..HEAD 之间含合并提交时(跨 clone 分支流合流的常态), 树差
    `git diff base` 量的是「两棵树的差」而不是「新增了哪些提交」—— 被合并分支的已评内容
    会整支算进本批(2026-11-08 实证, 详见 issue 26-11-08-0903)。逐笔口径:
      普通提交 = `git diff <sha>^ <sha>`(自身改动);
      合并提交 = `git show --remerge-diff`(自动合并结果 vs 实际合并结果 = 纯冲突解决面 ——
                 分支侧内容已随分支自己的 trailer 评过, 第一父母树差/combined diff 都会把它们
                 重复计入; 实证 0469bf0c: 第一父母差 53 文件, remerge 只剩 2 个生成物);
                 remerge 失败(旧 git / 特殊提交)按 0 计。
      侧分支提交 = base..HEAD 全集里不在 first-parent 路径上的那部分: 带 Review/Review-Skip
                 trailer 的(已评)排除; **无 trailer 的按自身 diff 计入** —— 连坐承诺(漏评滚进
                 下一批)对侧分支同样成立: 裸 git commit / 漏写 trailer 的提交落在侧分支再被
                 干净合并, 若只算主线+remerge 会整类漏计(评审二轮 major, 假绿通路)。
    工作树部分 = `git diff HEAD`(已暂存未提交 + 未暂存)。
    """
    total, files = 0, []
    mainline = _git(root, "rev-list", "--first-parent", f"{base}..HEAD").stdout.split()
    seen = set(mainline)
    side = [s for s in _git(root, "rev-list", f"{base}..HEAD").stdout.split() if s not in seen]
    for sha in mainline:
        total, files = _commit_numstat(root, sha, gen, total, files)
    for sha in side:
        body = _git(root, "log", "-1", "--format=%B", sha).stdout
        if REVIEW_LINE_RE.search(body) or SKIP_LINE_RE.search(body):
            continue  # 侧分支自带 trailer = 已评, 不计入
        total, files = _commit_numstat(root, sha, gen, total, files)
    return _count_numstat(root, ["diff", "--numstat", "--no-renames", "HEAD"], gen, total, files)


def _commit_numstat(root: Path, sha: str, gen: set[str], total: int, files: list[str]) -> tuple[int, list[str]]:
    """单笔提交的改动行数: 普通提交 = 与父母的差; 合并提交 = remerge(冲突解决面, 失败按 0 计)。"""
    parents = _git(root, "rev-list", "--parents", "-1", sha).stdout.split()
    if len(parents) > 2:  # 合并提交(sha + ≥2 父母)
        args = ["show", "--remerge-diff", "--numstat", "--format=", "--no-renames", sha]
    else:
        args = ["diff", "--numstat", "--no-renames", f"{sha}^", sha]
    try:
        return _count_numstat(root, args, gen, total, files)
    except SystemExit:
        if len(parents) > 2:
            return total, files  # remerge 失败的合并提交按 0 计(见 _numstat docstring)
        raise


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


def message_text(root: Path, explicit: str | None) -> tuple[str, str]:
    """提交信息: 显式参数 → 环境变量(commit.py 注入) → 约定文件 → HEAD 消息。

    返回 (文本, 来源), 来源取值 "file" / "default" / "HEAD" —— 来源为 HEAD 时 main() 会打一行
    「未给消息文件, 按 HEAD 判, 实算 N 行」(0441 落点 4): 手工预览没给文件不再静默假装, 上一笔是
    Skip 时按 HEAD 判会直接报 ok, 至少把实算行数亮出来; 判定语义不变, 仍按 HEAD 的 trailer 判。

    闸门在一次提交里会跑两次: 提交前读消息文件; 提交后(合流复跑)文件已消费, 那时 HEAD 就是本次提交
    —— 退到 HEAD 消息正好命中同一份文本。**复跑不靠这个函数区分**(显式 --message-file 的文件不会被
    消费, 按"文件在不在"判会误判), 改由 commit.py 写 POST_MARKER 文件标记且 main() 在调用本函数之前
    就消费它 —— 走到 HEAD 来源的只剩"手工预览没给文件"一种情形。
    """
    for cand in (explicit, os.environ.get("COMMIT_FLOW_MSG_FILE")):
        if cand and Path(cand).exists():
            return Path(cand).read_text(encoding="utf-8", errors="replace"), "file"
    default = root / ".git" / "COMMIT_MSG_AI.txt"
    if default.exists():
        return default.read_text(encoding="utf-8", errors="replace"), "default"
    proc = _git(root, "log", "-1", "--format=%B")
    return (proc.stdout if proc.returncode == 0 else ""), "HEAD"


def anchor_commit(root: Path) -> str:
    """主线(first-parent 路径)上最近一条带 `Review:` / `Review-Skip:` 的提交; 一条都没有时退回
    HEAD(冷启动只算工作树)。

    ❗不设扫描窗口: 曾经用 `-200` 提速, 结果"上一条 trailer 在第 201 笔"时静默退回 HEAD ——
    整段累计批被丢弃且无任何提示, 正好与"漏评提交滚进下一批"的连坐机制相反(2026-11-06 评审实测)。
    几千笔提交的 message 全量解析也就几百 KB, 不值得为它换一个静默失效点。
    ❗必须 --first-parent: 侧分支 tip 自带 trailer 时(跨 clone 分支流的常态), 平铺 log 按提交时间
    会取到它 —— 而侧分支常从旧基线切出, 配合 _numstat 的树差会把主线在分支切出之后的全部已评
    工作整支算进「本批」(2026-11-08 实证: config-infra 分支 tip 80df0b9a 遮蔽主线锚点 70bba719,
    实算虚增 ~9600 行, 提交被死锁; 详见 issue 26-11-08-0903)。侧分支的提交已随它自己的 trailer
    评审过, 不该由主线锚点承担。
    """
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    if not head:
        return ""
    proc = _git(root, "log", "--first-parent", "--format=%H%x1f%B%x1e")
    for rec in proc.stdout.split("\x1e"):
        if "\x1f" not in rec:
            continue
        sha, _, body = rec.partition("\x1f")
        if REVIEW_LINE_RE.search(body) or SKIP_LINE_RE.search(body):
            return sha.strip()
    return head


def _skeleton(count: int) -> str:
    """失败行尾附的可粘贴整行骨架(计划 26-11-07-0441 落点 4/D4)。

    行数位直接填实算值, 其余位是 `?` —— `?` 不是数字, 直接粘贴会被 decide() 的数字正则再判红
    (blocker/修/入池/检 走原正则, 检/派发 另有形状校验), 失败方向安全。
    """
    return f"可粘贴整行(把 ? 逐一换成实数): Review: <范围> · {count} 行 · blocker ? · 修 ? · 入池 ? · 检 ?/? · 派发 ?"


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
        if count > CEILING:
            # 超限判据只认派发(0441 D1): `· 分面` 降级为信息字段(D8), 不再是合法通路 —— 原「分面」条件已删。
            dispatch = DISPATCH_RE.search(line)
            if not dispatch or int(dispatch.group(1)) < 2:
                return False, (
                    f"本批实算 {count} 行 > 建议上限 {CEILING} —— 先拆批(按可独立编译/测试的文件组); "
                    "确实不可拆的残余批须多派一轮: trailer 记 `· 派发 <K>`(要求 派发 ≥ 2; `· 分面` 只是"
                    "信息字段) —— " + _skeleton(count)
                )
        declared = LINES_RE.search(line)
        if not declared:
            return False, (
                f"`Review:` 行缺 `<N> 行` 声明(实算 {count} 行) —— 按 code-review skill ⑦ 的格式补齐"
                " —— " + _skeleton(count)
            )
        if int(declared.group(1)) != count:
            return False, (
                f"`Review:` 声明 {declared.group(1)} 行 ≠ 实算 {count} 行 —— "
                "数字必须是提交那一刻实测的, 改对再提交 —— " + _skeleton(count)
            )
        fixed: dict[str, int] = {}
        missing = []
        for name, rx in COUNT_FIELDS:
            m = rx.search(line)
            if m:
                fixed[name] = int(m.group(1))
            else:
                missing.append(name)
        check = CHECK_RE.search(line)
        if check is None:
            # 检是必填(0441 落点 2): 缺了判红; 写了但不是合法斜杠数字形状(直贴骨架的 `检 ?/?`)同样判红,
            # 在场正则只用来把措辞说准 —— 两个方向都是红, 不存在静默通过。
            missing.append("检(形状不对, 应为 `检 P/T`)" if CHECK_PRESENT_RE.search(line) else "检")
        if missing:
            return False, (
                f"`Review:` 行缺字段: {'/'.join(missing)} —— 按 skill ⑦ 的格式补齐; "
                "检 P/T: T=送检发现数, P=引文逐字通过数(review.check 判过的条目) —— " + _skeleton(count)
            )
        passed, total = int(check.group(1)), int(check.group(2))
        if passed > total:
            return False, (f"`检 {passed}/{total}`: P(过检数) > T(送检数) —— 通过的条目不可能多于送检的, "
                           "数字写反了 —— " + _skeleton(count))
        lower = fixed["修"] + fixed["入池"]
        if passed < lower:
            return False, (
                f"`检 {passed}/{total}`: P(过检数) {passed} < 修 {fixed['修']} + 入池 {fixed['入池']}"
                f" = {lower} —— 修/入池 只数过检且未被 REFUTE 的发现(自发顺手修、被 REFUTE 弃掉的"
                "条目不进这两个数), 口径对不上就改数 —— " + _skeleton(count)
            )
        if DISPATCH_PRESENT_RE.search(line) and not DISPATCH_RE.search(line):
            # ≤ CEILING 不校验派发数值, 但写了 `派发` 字样就必须是数字形状 —— 否则直贴骨架的 `派发 ?`
            # 会按缺省静默通过(0441 落点 4)。> CEILING 时上面已保证派发合法且 ≥ 2, 走不到这里。
            return False, ("`派发` 字段形状不对(应为 `· 派发 <K>`, K 为数字) —— 骨架里的 `?` 要换成实数 —— " + _skeleton(count))
        return True, f"已评审 {count} 行"

    skip = SKIP_LINE_RE.search(message)
    if skip:
        reason = skip.group(1).strip()
        if len(reason) < 4:
            return False, "`Review-Skip:` 的理由为空或过短 —— 写清为什么这批不用评(≥4 字), 理由会进 git log"
        return True, f"豁免: {reason}"

    return False, (
        f"本批累计 {count} 行待评未留痕 —— 先跑 code-review skill(批次 base = 最近一条 `Review:` 提交), "
        "再在提交信息里写 `Review: <范围> · <N> 行 · blocker N · 修 N · 入池 N · 检 P/T · 派发 K`"
        "(检 P/T: T=送检发现数, P=引文逐字通过数; 超 400 行须 `· 派发 2` 起); "
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

    msg, msg_source = message_text(root, args.message_file)

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

    if msg_source == "HEAD":
        # 无消息文件可读、退到 HEAD 消息(0441 落点 4): 手工预览不再静默假装 —— 上一笔是 Skip 时按 HEAD
        # 判会直接报 ok, 至少把实算行数亮出来; 判定不变(仍按 HEAD 的 trailer 判), 复跑轮在更早处已被拦。
        print(f"未给消息文件, 按 HEAD 判, 实算 {count} 行")
    ok, why = decide(count, sensitive, msg)
    warn = flush_field_warn(msg)
    if warn:
        # 弱校验的让步输出(计划 26-11-07-0201 落点 3): 不改判定, 只提醒字段写坏了 —— 判定仍由 decide 独立给
        print(warn)
    if ok:
        # v3 契约: 全过即静默(仅记账/生成物这类"本来就没批"的情形也静默; warn 与「未给消息文件」提示是仅有的两处让步)
        return 0
    print(f"评审留痕: {why}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
