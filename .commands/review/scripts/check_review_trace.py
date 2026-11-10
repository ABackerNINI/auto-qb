"""提交闸门的评审留痕检查 —— 「这一批要不要评、评过没有、声明与实算是否一致」。

挂点: `.commands/my-commit-flow/.my-commit-flow.toml` 的 [[gates]] (每次提交跑, 无待评改动即静默)。
设计口径单点: `.agents/skills/code-review/SKILL.md` 1)(触发) / 2)(批次与容量) / 7)(留痕)。

## 为什么是"锚点法"而不是"自报 base"
批次范围 = **最近一条带 `Review:` / `Review-Skip:` 的提交 → 当前工作树**。锚点从 git 历史现算,
agent 不用填 hash(填错就是假账), 且天然"连坐": 谁漏评, 那笔提交就滚进下一批, 由下一批被迫覆盖
——「不留免评节点」是这条规则的全部意义。冷启动(历史里一条都没有)时起点退化为 HEAD, 只算工作树。
锚点与计数都**走主线(first-parent)**、批次行数**逐笔累计**(合并提交取对第一父母的差): 合并拓扑下
树差 ≠ 新增提交, 侧分支 trailer 也不遮蔽主线 —— 实现单点已收编进 review_content
(anchor_commit / numstat_batch 的 docstring 与 issue 26-11-08-0903)。

## 判据(顺序即优先级)
1. 批内改动 0 行且未触安全敏感面且消息无 `Review:` trailer(仅记账类/生成物, 及 0 行二进制改动
   —— numstat 对二进制计 0 行) → 通过(静默); 带 trailer 的 0 行批**不短路**, 照走判据 2 全链
   校验(含 `· 基` 比对 —— issue 26-11-08-1701: 二进制改动实算恒 0, 基比对是它唯一的机检面)
2. 提交信息有 `Review:` 行 → 校验(计划 26-11-07-0441): `<N> 行` 必须等于实算(±0); blocker/修/入池 数字齐;
   `检 P/T` 必填且 0 ≤ P ≤ T、P ≥ 修 + 入池 —— 修/入池/检 为**全轮累计**口径(修复循环首轮 + 各修复轮
   累加申报, 计划 26-11-08-1240 D7; T=送检发现数, P=引文逐字通过数; 修/入池 只数过检且未被 REFUTE 的
   发现, 判定式对累计数照旧成立); `· 基 <12hex>` 必填(D6): 值与闸门用 review_content.batch_base_hash
   重算的当前批(锚点→工作树)整批过滤 diff 哈希比对, 不一致 = 评审后有新改动 → 判红, 出路 = 重跑
   review.pack 取新基并补一轮复评; `· 轮 <R>` 可缺省(缺省 1 = 修复循环轮数, D7), 出现时必须整数 ≥ 1;
   实算 > 400 行时必须带 `· 派发 <K>` 且 K ≥ 2(先拆批, `· 分面` 不再是超限通路; 派发 K = **首轮**拓扑
   派遣, 修复轮不计入 —— 累计会稀释容量下界); 超限无派发/缺字段(含缺检缺基)/行数不符 三类失败行尾附
   可粘贴整行骨架(行数位填实算, `?` 直贴必再判红)
3. 提交信息有 `Review-Skip:` → 失败(计划 26-11-08-1240 D8: 豁免已退役, 理由长短不再重要) —— 历史
   trailer 在锚点 walk 与侧分支计数里照旧识别(不追溯重判), 新提交没有免评通道
4. 其余 → 失败(计划 26-11-08-1240 D9: 50 行下限退役, 可评行数 >0 即必须有 `Review:` trailer,
   实算恒 0 才静默): 触安全敏感面给敏感面原因(不论行数都要评), 否则给未留痕原因 + 下一步
5. 旁路(不判红): `· 齐平 <8hex>` 字段只查格式(计划 26-11-07-0201 落点 3) —— 缺失不问、真值不验;
   格式异常打一行 `[warn]` 但 rc=0 放行(R4: 弱字段, 与「行数 ±0」的强校验刻意区分); `· 分面` 同为
   信息字段(0441 D8) —— 任何档位都不判红, 也不再放行超限

> 下限(50 行)已随 26-11-08-1240 D9 退役: 「5 行小改正文写一句 Review: 见报告」不再是无 trailer 义务
> 的通路 —— 可评行数 >0 就得写全字段 trailer(小提交与修复增量两条政策缝一并闭合, 2026-11-08 拍板)。

## 计数面
- 计入: 代码 + 事实性文档(计划/报告/约定/坑档/README/AGENTS.md)
- 不计入: **记账类**(`memory-bank/tasks/` `active-context/` `testing/baselines/`, 以及
  `reports/attachments/legacy-review4/` 整目录 —— R4 存量评审的 findings/manifest/路线小结是被评代码
  的产物, 0441 落点 3/D3) 与 **生成物**(`gen_all.py --list` 的权威清单; 取不到时退回 `_index*.md`
  兜底, 不静默失效成"索引重排也算改动")
- 判定与实算实现单点在 review_content.py: 排除面(_counted/generated_paths)、锚点(anchor_commit)、
  逐笔行数实算(numstat_batch/untracked_batch)与基哈希(batch_base_hash)与 review.pack 共用同一份
  实现(计划 26-11-08-1240 §03 3.3; 2026-11-11 起 pack 评审规模也走同一实算, 与 trailer `<N> 行`
  恒同源) —— 本脚本只消费, 不复写判据

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
# 同目录共享模块: 锚点/可评路径判定/逐笔行数实算/基哈希, 与 review_pack 单点同源
from review_content import (  # noqa: E402
    REVIEW_LINE_RE,
    SKIP_LINE_RE,
    anchor_commit,
    batch_base_hash,
    generated_paths,
    numstat_batch,
    untracked_batch,
)

CEILING = 400  # 建议上限: 超过先拆批; 确实不可拆的残余批须 `· 派发 <K>` 且 K ≥ 2(计划 26-11-07-0441 D1)

LINES_RE = re.compile(r"(\d+)\s*行")
COUNT_FIELDS = (
    ("blocker", re.compile(r"blocker\s*(\d+)")), ("修", re.compile(r"修\s*(\d+)")), ("入池", re.compile(r"入池\s*(\d+)"))
)
# 修/入池为全轮累计口径(计划 26-11-08-1240 D7): 修复循环首轮 + 各修复轮的修复/入池数累加后申报,
# 判定式(P ≥ 修 + 入池)对累计数照旧成立 —— 本处正则只管取数, 不区分轮次。
# 检 P/T(0441 落点 2): T = 送检发现数, P = 引文逐字通过数(review.check 判过的条目), 同为全轮累计。
# 值正则取斜杠形式; `·` 锚定的在场正则只用来区分「缺字段」与「写了但形状不对」(直贴骨架的
# `检 ?/?` 不许静默通过)。
CHECK_RE = re.compile(r"检\s*(\d+)\s*/\s*(\d+)")
CHECK_PRESENT_RE = re.compile(r"·\s*检")
# 派发 K(0441 落点 1): 值正则锚定 `·` 前缀(D10: 防正文散文「派发 2 个子代理」过采), 缺省 1;
# 在场正则同锚 —— 直贴骨架的 `派发 ?` 落「形状不对」判红, 不会按缺省静默通过。
# 派发 K = **首轮**拓扑派遣数, 修复轮不计入(D7/F4): 修复轮若计入 K, 会掩盖 >400 行批「首轮只派
# 1 次」的违规、稀释容量下界(发现数 ∝ 派发次数); 修复轮深度由 `· 轮 R` 与累计 检 P/T 反映。
DISPATCH_RE = re.compile(r"·\s*派发\s*(\d+)")
DISPATCH_PRESENT_RE = re.compile(r"·\s*派发")
# 轮 R(计划 26-11-08-1240 D7): 修复循环轮数, 缺省 1; 出现时必须整数 ≥ 1 —— 形状校验同 派发 风格,
# 直贴骨架的 `轮 ?` / 非数字不许静默通过。
ROUND_RE = re.compile(r"·\s*轮\s*(\d+)")
ROUND_PRESENT_RE = re.compile(r"·\s*轮")
# 基 hash(计划 26-11-08-1240 D6): 整批过滤 diff 哈希(review_content.batch_base_hash 输出的 12 位
# 小写 hex), 必填; 值与闸门重算的当前批哈希比对, 不一致判红(评审后有新改动 → 重跑 pack 取新基复评)。
BASE_RE = re.compile(r"·\s*基\s+([0-9a-f]{12})(?![0-9a-f])")
BASE_PRESENT_RE = re.compile(r"·\s*基")

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


def _skeleton(count: int) -> str:
    """失败行尾附的可粘贴整行骨架(计划 26-11-07-0441 落点 4/D4)。

    行数位直接填实算值, 其余位是 `?` —— `?` 不是数字/hash, 直接粘贴会被 decide() 的形状校验再判红
    (blocker/修/入池/检 走原正则, 检/派发/基 另有形状校验), 失败方向安全。
    """
    return (f"可粘贴整行(把 ? 逐一换成实数/hash): Review: <范围> · {count} 行 · blocker ? · 修 ? · "
            "入池 ? · 检 ?/? · 基 ? · 派发 ?")


def decide(count: int, sensitive: list[str], message: str, base_hash: str | None = None) -> tuple[bool, str]:
    """纯判定: (是否通过, 失败原因/通过说明)。顺序即优先级, 见模块头「判据」。

    全轮累计口径(计划 26-11-08-1240 D7): trailer 里的 修/入池/检 P/T 申报的是**本批修复循环所有
    轮次的累计数**(首轮 + 各修复轮), 判定式不变 —— 下界 P ≥ 修 + 入池 与 0 ≤ P ≤ T 对累计数照旧
    成立; `· 派发 K` 是**首轮**拓扑派遣数, 修复轮不计入(累计会稀释 >400 行批的容量下界); `· 轮 R`
    = 修复循环轮数, 缺省 1。
    base_hash: 闸门按同一套过滤实现(review_content.batch_base_hash)重算的当前批(锚点→工作树)基
    哈希; 消息带 `Review:` trailer 时 main 恒传入, trailer 的 `· 基` 与它比对, 不一致判红(D6: 评审
    后有新改动)。None = 不比对(消息无 trailer 的调用面; 单测直调 decide 时不传即跳过比对, 生产
    面不存在 —— batch_base_hash 算不了会直接 SystemExit(2), 不会静默变 None)。
    50 行下限已退役(D9): 可评行数 >0 即须 trailer, 实算恒 0(纯记账类/生成物, 及 0 行二进制改动
    —— numstat 对二进制计 0)且消息无 `Review:` trailer 才静默; 带 trailer 的 0 行批不短路, 照走
    全链校验, `· 基` 比对可达(issue 26-11-08-1701: 二进制改动的实算恒 0, 基比对是它唯一的机检面)。
    """
    # 0 行静默短路仅对无 trailer 的批生效(issue 26-11-08-1701, 方案 A): 二进制改动经 numstat 实算
    # 恒 0, 带 `Review:` trailer 的批若在此短路, D6 基比对对它们不可达 —— 评审后替换/新增二进制
    # 可评文件会静默放行。带 trailer 的 0 行批照走下方全链校验(含 `· 基` 与闸门重算哈希比对)。
    if count == 0 and not sensitive and not REVIEW_LINE_RE.search(message):
        return True, "可评 0 行(记账类/生成物或纯二进制)改动"

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
                f"`Review:` 行缺 `<N> 行` 声明(实算 {count} 行) —— 按 code-review skill 第 7 步的格式补齐"
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
        declared_base = BASE_RE.search(line)
        if declared_base is None:
            # 基是必填(26-11-08-1240 D6): 缺了判红; 写了但不是 12 位小写 hex(直贴骨架的 `基 ?`)同样判红。
            missing.append("基(形状不对, 应为 `· 基 <12位hash>`)" if BASE_PRESENT_RE.search(line) else "基")
        if missing:
            return False, (
                f"`Review:` 行缺字段: {'/'.join(missing)} —— 按 skill 第 7 步的格式补齐; "
                "检 P/T: T=送检发现数, P=引文逐字通过数(全轮累计); `· 基 <hash>` = review.pack 输出的"
                "基哈希 —— " + _skeleton(count)
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
        round_field = ROUND_RE.search(line)
        if ROUND_PRESENT_RE.search(line) and (round_field is None or int(round_field.group(1)) < 1):
            # 轮 R(26-11-08-1240 D7): 缺省 1, 写了就必须是整数 ≥ 1 —— 直贴骨架的 `轮 ?` 不许静默通过。
            return False, ("`轮` 字段形状不对(应为 `· 轮 <R>`, R 为整数 ≥ 1, 缺省 1) —— " + _skeleton(count))
        if base_hash is not None and declared_base.group(1) != base_hash:
            # 基哈希比对(26-11-08-1240 D6): 闸门重算的当前批哈希与申报不一致 = 评审后工作树又有新改动
            # —— 补一轮复评, 不许拿旧基蒙混过关。
            return False, (
                f"`· 基 {declared_base.group(1)}` ≠ 闸门重算的整批过滤 diff 哈希 {base_hash} —— "
                "评审后有新改动 —— 重跑 commands run review.pack 取新基并补一轮复评"
            )
        return True, f"已评审 {count} 行"

    skip = SKIP_LINE_RE.search(message)
    if skip:
        # Review-Skip 已退役(26-11-08-1240 D8): 理由长短不再看, 一律判红 —— 历史 trailer 只在锚点
        # walk / 侧分支计数里照旧识别(anchor_commit / numstat_batch), 不追溯重判。
        return False, "Review-Skip: 豁免已退役 —— 没有免评通道, 写 `Review:` 走正常评审(code-review skill)"

    if sensitive:
        return False, (f"触碰安全敏感面: {'、'.join(sensitive[:3])} —— 不论行数都要评"
                       "(code-review skill 第 1 步)")

    return False, (
        f"本批累计 {count} 行待评未留痕 —— 先跑 code-review skill(批次 base = 最近一条 `Review:` 提交), "
        "再在提交信息里写 `Review: <范围> · <N> 行 · blocker N · 修 N · 入池 N · 检 P/T · 基 <hash>`"
        "(检 P/T 全轮累计: T=送检发现数, P=引文逐字通过数; 基 = review.pack 输出的基哈希; "
        "超 400 行须 `· 派发 2` 起; 50 行下限已退役, 可评行数 >0 一律要评)"
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

    tracked_lines, tracked_files = numstat_batch(root, base, gen)
    untracked_lines, untracked_files, _ = untracked_batch(root, gen)
    count = tracked_lines + untracked_lines
    files = tracked_files + untracked_files
    sensitive = sensitive_hit(files, red_lines(root))

    if msg_source == "HEAD":
        # 无消息文件可读、退到 HEAD 消息(0441 落点 4): 手工预览不再静默假装 —— 上一笔是 Skip 时按 HEAD
        # 判会直接报 ok, 至少把实算行数亮出来; 判定不变(仍按 HEAD 的 trailer 判), 复跑轮在更早处已被拦。
        print(f"未给消息文件, 按 HEAD 判, 实算 {count} 行")
        if count == 0 and not sensitive:
            # HEAD 消息的 0 行批保持静默(issue 26-11-08-1701 复评轮补): HEAD 上的 trailer 描述的是
            # **已入库的上一批**, 锚点已推进到它、本批实算恒 0 —— 拿「声明行数/基 ≠ 实算 0」去校验
            # 历史 trailer 是假红。真正的提交面消息恒来自 file/default(commit.py 经 env 递入),
            # 带 trailer 的 0 行批在提交面照走全链校验, 本让步不开旁路。
            return 0
    # 基哈希机检(计划 26-11-08-1240 D6): 消息带 `Review:` trailer 时, 用与 review.pack 同源的过滤实现
    # 重算当前批(锚点→工作树)哈希, 供 decide 与 trailer 的 `· 基` 比对; 无 trailer 的调用面不算(省一次
    # git diff) —— 无 trailer 的 0 行静默短路与 Skip/未留痕分支用不到它; 0 行带 trailer 的批仍要
    # 算(issue 26-11-08-1701: 此类批不走短路, 基比对必须可达)。
    batch_hash = batch_base_hash(root, base) if REVIEW_LINE_RE.search(msg) else None
    ok, why = decide(count, sensitive, msg, base_hash=batch_hash)
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
