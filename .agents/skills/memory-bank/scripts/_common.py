"""memory-bank 脚本族共用的常量与工具 (gen_tasks_index / gen_kb_index / check_kb_structure)。

**与具体项目无关**: 不出现项目名、不假定 skill 的安装深度、不硬编码 memory-bank 路径 ——
换一个项目直接装上就能跑; 项目专属值 (如 AGENTS.md 的 8000 字符上限) 留在项目脚本里。

单点定义 (守卫 import 这里, 不手抄):
- `CAP_POLICY`: 角色 → 字符上限 (方案 §03「cap 分级」); 改 cap 只改这里
- `PITFALL_CLASSES`: pitfalls 的类枚举 (扩类须三处同步: 本常量 / 新建目录 / README 细路由)
- `DOC_STATUSES` / `TERMINAL_DOC_STATUSES`: 计划 / 报告 / issue 共用的 5 词表与其完结子集
  (gen_docs_index 分区 / gen_doc_map 轮转 / test_docs_forms 校验都 import 这里); `StatusVocabularyError`
  是生成器遇表外值时的 fail-fast 异常 (见 pitfalls/kb/doc-status-meta.md)
- `TASK_STATUSES` / `TASK_DOMAINS` / `TASK_FILE_RE`: 任务档案的 4 词表 / 领域枚举 / 命名正则
  (`gen_tasks_index` 与 `kb.new` / `check_doc_templates` 同源)
- `FAMILIES`: 文档族注册表 (plan/task/slice + P3 二期 pitfall/report/baseline/progress →
  命名/模板/词表/索引动作) —— `kb.new` / `kb.wrap` / `check_doc_templates` 与模板的同一份注册表
  (计划 26-10-17-0527 P1/P3)
- `detect_doc_kind` / `DOC_KIND_*`: 载体探测 (**改面**: plans|reports HTML · tasks · slices · issues) ——
  `kb.status` / `kb.bump` 的同一份; 与建面的 `FAMILIES` 分工 (那边管「建」, 这里管「改」)
- `html_meta` / `set_html_meta` / `md_field` / `set_md_field` / `set_last_active`: 元数据行读写单点
  (doc-* meta 与 `**字段:**` / `> 最后活动:` 行; 缺目标行返回 None, 由调用方 fail-fast)
- `sync_body_meta`: 正文 `.meta` 镜像行与 head meta 同改 (计划族模板的展示行; 缺即无操作) ——
  派生面不跟着抬 = 渲染页显示过期值
- `html_set_refs` / `md_set_refs`: 认领链声明 (doc-refs meta / `**Refs:**` 行) 的插入/合并单点
  (D4 反向补链; 值 = 仓库根相对路径, 英文逗号; md 只动**首个** `**Refs:**` 行; 幂等)
- `rebuild_index`: 改后重建受影响索引的共同落点 —— `kb.new` / `kb.status` / `kb.bump` 共用
  (与 `gen_all` 的集合单点同一 build 实现)
- `find_root()`: 仓库根探测 (向上找 `.git`, 而非按 skill 安装深度反推 `parents[n]`)
- `resolve_mb_dir()`: memory-bank 目录探测 (`--mb-dir` 显式指定优先)
- `read_meta()`: 主题文件三行头元数据 (`# 标题` / `> 摘要:` / `> 触发:`)
- `role_of()`: 仓库相对路径 → 角色 (决定套哪档 cap)
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent

# --------------------------------------------------------------------------- cap 策略

# 角色 → 字符上限 (首个匹配生效, 口径同项目脚本 check_context_caps.py: 按**字符**数)。
# 2026-09-29 用户定调: **全表翻倍** —— 旧值频繁触顶, 每次触顶都逼出一轮"压文案/外迁"返工,
# 返工轮次的 token 成本远大于文件变长的阅读成本; 触顶处置统一为"收缩到最大值的 50%"(见 TRIM_KEEP)。
# 唯一例外 `agents`: AGENTS.md 的 8000 是 IDE 注入 `slice(0, 8000)` 的硬约束, 放大 = 守卫失效 + 尾部静默截断。
CAP_POLICY: dict[str, int] = {
    "index": 6000,  # `<doc>/_index.md` 与 memory-bank/README.md —— 手写路由/索引
    # `tasks/_index.md` / `issues/_index.md` 与各目录 `_index.md` 是**自动生成、行数随档案/issue
    # 数增长**的索引: 一行一条已是最简, 没有可行的收缩路径 —— 单列一档, 有守卫防无限膨胀,
    # 但不假装它们是一屏索引。
    "index-auto": 25200,
    "pitfall": 12000,  # pitfalls/* 条目集 —— 读法是「扫描找一条」, 比通读更贵
    "evergreen": 20000,  # 常青主题 (叙述型) —— 一次通读可接受
    "reference": 24000,  # 参考速查 (config-reference / rule-system) —— 查表不是通读
    "volatile": 24000,  # 易变层 (activeContext.md) —— 会话开始必读, 硬顶
    "slice": 12000,  # activeContext/ 会话切片 —— per-会话 / per-专题, 天然比整份易变层小
    # testing/baselines/ 基线切片 —— 不可变的一次性快照, 单条本就该短; 超了说明把逐轮流水又堆回来了
    # (明细下沉对应任务档案, 不是调 cap)。
    "baseline-slice": 8000,
    "task": 48000,  # 任务档案
    # append-only 历史流水 (如 `*-history.md`) —— **只增不改**, 每次改动追一条。
    # 与任务档案同档: 它按设计就会一直长, 给一个"涨到多少该轮转"的上限, 而不是假装它是一屏文档。
    # 触顶策略见下方 `TRIM_KEEP` —— 按它切, 不要只搬"最老的一条"。
    "log": 48000,
    "agents": 8000,  # 项目引导 (AGENTS.md; IDE 注入硬约束, 不随 2026-09-29 翻倍, 见上)
}

# 下限建议: **只 WARN** —— 主题文件过小会让「读三个文件」取代「读一节」, 反而更贵
CAP_MIN_WARN = 1500

# 触顶后的统一收缩比例 (2026-09-29 用户定调): **任何**文件超 cap, 处置都是"精简/外迁到 cap 的
# 50%", 一次留足追加余量 —— 而不是削到刚好贴线, 下次追加立刻再触顶。
# ❌ 只搬"最老的一条"是错的: 最老条目大小不受控, 可能只有几百字符, 下次追加立刻又触顶;
#    2026-09-23 实测 `testing/baseline-history.md` 触顶时只剩 170 字符余量 —— 也就是说**任何**一次
#    追加都会越线, 而按"搬一条"处置等于每次新增都要迁移一次。
# 落点: 同目录 `attachments/`(`iter_topic_files` 是非递归 glob + 该目录在 EXCLUDED_DIRS 里 ⇒ 不计 cap),
# 原位留一行指针; 搬运用脚本按原换行风格切分原样写回, 不手抄。
TRIM_KEEP = 1 / 2

# `activeContext/` 切片数上限 —— 切片无界增长是这个方案的已知代价, 给个可判定的收口线。
# 2026-09-30 起它是**债务**而不是判红项(D2 拍板, 计划 26-09-30-2112): 违反它只是"该蒸馏没蒸馏",
# 与尺寸债同属一场清理会话的活, 而留红会逼出"为了过守卫而违规归档"。
# 70 = 14 天蒸馏窗口 × 日均 ~5 篇(2026-09-29 二次校准: 56 打满且窗口内 57/57 全部活跃;
# 实测 14 天 57 篇 ≈ 4.1/天, 取整 5/天留余量; 首次校准 48→56 见 git 历史)
SLICE_COUNT_LIMIT = 70

# --------------------------------------------------------------------------- 文档形态状态词

# 计划 / 报告 (`doc-status`) 与 issue (`issue-status`) 共用的 5 词表 —— **单点定义**
# (gen_docs_index 分区 / gen_doc_map 轮转 / test_docs_forms 校验都 import 这里, 不手抄)。
# ⚠ 表外值 (如 `Draft`) 会让 gen_docs_index 不落任何分区 ⇒ 索引**静默漏收**该件 —— 仍打印
#   「已生成 N 个生成物」、零警告, 且 kb.check / kb.docmap --check / doc.links 全绿, 只有
#   test.full 才红 (见 pitfalls/kb/doc-status-meta.md)。故生成器遇表外值 **fail-fast**
#   (`StatusVocabularyError`), 提交闸门 (`gen_doc_map --check`) 也挂同源校验。
# ⚠ 与 tasks/ 档案的 4 词表 (`**Status:**` = In Progress/Open/Done/Dropped) **不同**, 别互相套用。
DOC_STATUSES = ("In Progress", "Open", "Done", "Dropped", "Superseded")

# 完结态 (`DOC_STATUSES` 子集): gen_doc_map 轮转用 —— 专题「有未完结件」才算活跃。
TERMINAL_DOC_STATUSES = frozenset({"Done", "Dropped", "Superseded"})


class StatusVocabularyError(ValueError):
    """`doc-status` / `issue-status` 不在 5 词表 —— 生成器会静默漏收, 故 fail-fast。

    由 `gen_docs_index.build()` 抛出 (聚合两份制品目录的全部表外值); `gen_docs_index` 与
    `gen_all` 的 CLI 入口捕获后打印干净报错并 rc=1。这样 kb.index / kb.check / 提交闸门 /
    pytest 全在**同一处**判红 (根因单点, 见 pitfalls/kb/doc-status-meta.md)。
    """


# --------------------------------------------------------------------------- CLOSED_KEEP 出口
# (计划 memory-bank/plans/26-10-31-0534-plan-kb-cleanup-tiers.html R3/D5/D14: tasks/ 与 plans/
# 补齐 issues/ 已有的那条防线 —— 主索引的**已完结**分区只渲染最近 N 条, 全量清单另落归档索引。)

# 主索引的已完结分区只保留最近 `CLOSED_KEEP` 条(控 index-auto cap): 档案/制品**原地不动**,
# 只是不出主索引 —— 索引大小由常量钉住, 不再随完结条目数线性涨(issues 侧 2026-10-11 实测:
# 243 条时无摘要口径已达 cap 108%, 砍摘要救不回来, 搬文件又打坏 `**Refs:**` 认领链)。
# 语义与 create-issue 的 `gen_issues_index.CLOSED_KEEP` 同值同款(60); 跨 skill 不 import
# (单点纪律, 见 gen_all._load_isolated) —— 两边各有一份常量, 由守阵
# test_closed_keep_constants_match_issues 等值钉住, 不许漂移。
CLOSED_KEEP = 60

# 归档清单文件名: 故意**不叫 `_index.md`** —— 那会被 role_of 套成 index-auto(25,200 cap),
# 全量清单必然超(计划 §07 风险表); `_archive.md` 不在任何 cap 扫描面。
ARCHIVE_NAME = "_archive.md"

# 归档清单相对所在目录的落点(与 create-issue 的 gen_issues_index.ARCHIVE_REL 同值)。
# `<dir>/attachments/` 在 EXCLUDED_DIRS, 不计 cap。
ARCHIVE_REL = f"attachments/{ARCHIVE_NAME}"


def keep_closed_window(ordered: list, status: str, terminal: frozenset, keep: int = CLOSED_KEEP) -> tuple[list, int]:
    """CLOSED_KEEP 出口的裁剪单点(gen_tasks_index / gen_docs_index 共用, 不各写一遍)。

    `ordered` 须已按时间**倒序**(各生成器自己的排序键); 已完结状态(`status` ∈ `terminal`)
    只保留最近 `keep` 条, 返回 (保留条目, 隐藏条数)。在办状态不受影响 —— 条数再多也原样返回。
    """
    if status not in terminal or len(ordered) <= keep:
        return ordered, 0
    return ordered[:keep], len(ordered) - keep


def closed_hidden_note(hidden: int, dir_name: str, noun: str) -> str:
    """主索引里「更早 N 条已出本索引」提示行 —— 形态与 gen_issues_index.render 同款。"""
    return (f"> 更早的 **{hidden}** 条已出本索引 —— {noun}仍在 `{dir_name}/` 目录(未搬动), "
            f"全量清单见 [{ARCHIVE_REL}]({ARCHIVE_REL}).")


# --------------------------------------------------------------------------- 结构枚举

# pitfalls 的类枚举。**扩类须三处同步**: 本常量 / 新建 `<class>/_about.md` / memory-bank/README.md 细路由。
PITFALL_CLASSES = ("git", "web-ui", "backend", "testing", "ops", "kb", "docs")

# 主题文件名: 小写英文与数字, 短横线分段 (与 create-issue 的 SLUG_RE 同款)
TOPIC_FILE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

# activeContext 会话切片文件名: 定宽 `YY-MM-DD-HHMM-<slug>` —— 前缀定宽才能保证**字典序 == 时间序**
# (写成 `26-9-3-34` 立刻乱序)。⚠ 与 tasks/ 档案「不带时分、同天同专题必撞同路径」的故意设计
# **意图相反**: 那边靠撞名暴露重复, 这边靠带时分避撞名 —— 所以两者必须分目录, 别混。
SLICE_FILE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

# 切片头部的「最后活动」字段 —— 阅读器的排序键; 缺失则回退文件名时间戳 (= 创建时间)
LAST_ACTIVE_RE = re.compile(r"^>\s*最后活动:\s*(\S.*?)\s*$", re.MULTILINE)
# 会话滚动状态切片所在目录 (目录化后 `memory-bank/activeContext/`)
SLICE_DIR = "activeContext"

# --------------------------------------------------------------------------- 文档族注册表
# (`kb.new` / `kb.wrap` / `check_doc_templates` 与模板的**同一份**注册表 —— 命名/模板/词表/
# 索引动作只在这里定义一次, 命令与守卫都 import 它, 不造第二套规范)。
#
# 模板落点: skill 的 `templates/<spec.template>`; 状态词表 import 既有单点
# (HTML 制品 5 词 `DOC_STATUSES` / 档案 4 词 `TASK_STATUSES`); 建后由命令按
# `index_script` 重建**该族受影响的那份索引**(与 `gen_all` 的集合单点同一实现, 不另建)。
# P3 扩四族 (计划 §04/§07): pitfall (子目录选类) / report (出厂即 Done) / baseline
# (`--total` 誊写, 无索引) / progress (三行头)。

# 任务档案的领域枚举 (文件名首段; 不足用先扩枚举再建档 —— 口径见 SKILL.md「任务档案规范」)
TASK_DOMAINS = ("webui", "backend", "rule", "memory-bank", "docs", "test", "deps", "config")


def match_domain(topic: str) -> str | None:
    """`--topic` 的领域段 = **最长前缀匹配**的枚举项 (枚举自身可含短横线, 如 `memory-bank`)。

    ⚠ P1 缺陷 (P2 补, 26-10-17): 旧实现 `topic.split("-", 1)[0]` 把 `memory-bank-xxx`
    的首段切出 `memory` —— 枚举里的 `memory-bank` 永远不可达。领域段自定最长, 匹配规则
    只能最长前缀 (`d + "-"` 或 topic == d, 保留 P1 的裸领域照收行为), 不能首段切分。
    """
    for d in sorted(TASK_DOMAINS, key=len, reverse=True):
        if topic == d or topic.startswith(d + "-"):
            return d
    return None


# 任务档案 4 词表 —— **单点**: `gen_tasks_index` 与 `check_doc_templates` 都 import 这里。
# ⚠ 与 HTML 制品的 5 词表 (`DOC_STATUSES`) **不同**, 别互相套用 (doc-forms 状态词节同款警告)。
TASK_STATUSES = ("In Progress", "Open", "Done", "Dropped")

# 任务档案的完结态 (`TASK_STATUSES` 子集): gen_tasks_index 的 CLOSED_KEEP 出口用 ——
# 与 `TERMINAL_DOC_STATUSES` 分开定义, 因为 4 词表里没有 `Superseded`, 别拿 5 词表硬套。
TERMINAL_TASK_STATUSES = frozenset({"Done", "Dropped"})

# 命名正则 (单点: `new_doc` 建件 / `check_doc_templates` 判新增面都 import 这里, 不手抄)。
# ⚠ 切片用的 `SLICE_FILE_RE` 已在上方 (带时分避撞名); 档案用 `TASK_FILE_RE` (不带时分、
# 同天同专题必撞同路径 = 靠撞名暴露重复)。两者意图相反, 必须分目录, 别混。
# 基线切片与切片同款命名 (带时分), 所以直接用 `SLICE_FILE_RE` —— 同一份正则两种载体,
# 目录不同 (testing/baselines/ vs activeContext/) 即不混。
PLAN_FILE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-\d{4}-plan-[a-z0-9]+(?:-[a-z0-9]+)*\.html$")
REPORT_FILE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-\d{4}-report-[a-z0-9]+(?:-[a-z0-9]+)*\.html$")
TASK_FILE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

# 模板里的填空标记 (`new_doc` 建后据此打印 SLOT 清单; `check_doc_templates` 判「无残留」)
SLOT_RE = re.compile(r"<!--\s*SLOT:\s*(.*?)\s*-->", re.DOTALL)


@dataclass(frozen=True)
class FamilySpec:
    """一族文档的命名 / 模板 / 词表 / 索引动作 —— 命令与守卫的同一份注册表。"""

    name: str
    dir: str  # memory-bank 下的子目录 (切片族是 `activeContext`; 可多段如 `testing/baselines`)
    ext: str  # ".html" | ".md"
    template: str  # skill `templates/` 下的文件名
    statuses: tuple  # 状态词表 (切片族无状态, 空元组)
    default_status: str  # 出厂状态
    index_script: str  # 建后重建哪个生成器 (切片族无索引, 空串)
    naming_re: object  # 文件名正则 (从上面的单点来)
    domain_first: bool  # `--topic` 领域段须 ∈ `TASK_DOMAINS` (最长前缀匹配, 仅档案族)
    subdir_flag: str = ""  # 第二段子目录的 CLI 参数名 (坑档 = `class`; 其余族空)
    subdir_values: tuple = ()  # 子目录允许值 (坑档 = `PITFALL_CLASSES`; 其余族空)


FAMILIES: dict[str, FamilySpec] = {
    "plan":
        FamilySpec(
            name="plan",
            dir="plans",
            ext=".html",
            template="plan.html",
            statuses=DOC_STATUSES,
            default_status="Open",
            index_script="gen_docs_index",
            naming_re=PLAN_FILE_RE,
            domain_first=False,
        ),
    "task":
        FamilySpec(
            name="task",
            dir="tasks",
            ext=".md",
            template="task.md",
            statuses=TASK_STATUSES,
            default_status="In Progress",
            index_script="gen_tasks_index",
            naming_re=TASK_FILE_RE,
            domain_first=True,
        ),
    "slice":
        FamilySpec(
            name="slice",
            dir=SLICE_DIR,
            ext=".md",
            template="slice.md",
            statuses=(),
            default_status="",
            index_script="",
            naming_re=SLICE_FILE_RE,
            domain_first=False,
        ),
    # ---- P3 二期四族 (计划 §04/§07): 模板/命名/索引动作都在这里单点定义
    "pitfall":
        FamilySpec(
            name="pitfall",
            dir="pitfalls",
            ext=".md",
            template="pitfall.md",
            statuses=(),
            default_status="",
            index_script="gen_kb_index",  # pitfalls/<class>/_index.md + pitfalls/_index.md 类指针
            naming_re=TOPIC_FILE_RE,
            domain_first=False,
            subdir_flag="class",  # `--class` 选 7 类之一 (单点 PITFALL_CLASSES)
            subdir_values=PITFALL_CLASSES,
        ),
    "report":
        FamilySpec(
            name="report",
            dir="reports",
            ext=".html",
            template="report.html",
            statuses=DOC_STATUSES,
            default_status="Done",  # 出厂即终态: 快照完成即冻结 (doc-forms 状态词节同款口径)
            index_script="gen_docs_index",
            naming_re=REPORT_FILE_RE,
            domain_first=False,
        ),
    "baseline":
        FamilySpec(
            name="baseline",
            dir="testing/baselines",
            ext=".md",
            template="baseline.md",
            statuses=(),
            default_status="",
            index_script="",  # 基线切片无索引 (时间戳文件名即索引, 口径见 gen_baseline_recent)
            naming_re=SLICE_FILE_RE,  # 与切片同款带时分命名 (目录不同即不混, 见上)
            domain_first=False,
        ),
    "progress":
        FamilySpec(
            name="progress",
            dir="progress",
            ext=".md",
            template="progress.md",
            statuses=(),
            default_status="",
            index_script="gen_kb_index",  # progress/_index.md
            naming_re=TOPIC_FILE_RE,
            domain_first=False,
        ),
}

# --------------------------------------------------------------------------- 改面载体探测
# (`kb.status` / `kb.bump` 的同一份; 与建面 `FAMILIES` 分工 —— 那边管「建」, 这里管「改」)。
# 探测 = memory-bank 相对路径的目录前缀 + 扩展名, 收集口径与 `gen_doc_map.collect()` 同源
# (plans/reports/tasks/issues 四形态), 外加 activeContext 切片 (切片不进 docmap, 但 kb.bump 抬它)。
# ⚠ 只认 memory-bank 下的文件 —— 别处的路径一律 "" (防命令改错文件, 调用方拒绝并指路)。

DOC_KIND_PLAN = "plan"  # plans|reports/*.html —— 5 词表 (`doc-status`), 翻转抬 doc-updated
DOC_KIND_TASK = "task"  # tasks/*.md —— 4 词表 (`**Status:**`), 翻转抬 **Updated:**
DOC_KIND_SLICE = "slice"  # activeContext/*.md —— **无状态**: kb.status 拒绝并指路 kb.wrap 迁出
DOC_KIND_ISSUE = "issue"  # issues/*.html —— 自己的词表/索引在 create-issue skill (跨 skill 不 import,
# 单点纪律), kb.status/kb.bump 拒绝并指路; 但**可以是 refs 目标** (doc-refs meta)

# 词表与索引动作 (单点: 翻转与重建都查这两张表, 不在命令里分叉 if-else)
DOC_KIND_STATUSES = {DOC_KIND_PLAN: DOC_STATUSES, DOC_KIND_TASK: TASK_STATUSES}
DOC_KIND_INDEX_SCRIPT = {DOC_KIND_PLAN: "gen_docs_index", DOC_KIND_TASK: "gen_tasks_index"}
DOC_KIND_CN = {DOC_KIND_PLAN: "计划/报告", DOC_KIND_TASK: "任务档案", DOC_KIND_SLICE: "会话切片", DOC_KIND_ISSUE: "issue"}

# 索引/元数据文件名: `_` 开头, 不参与「主题文件」计数
INDEX_NAME = "_index.md"
ABOUT_NAME = "_about.md"

# 三行头元数据 —— 条目型与叙述型共用同一套 (这是「全库一套机制」的关键)
TITLE_RE = re.compile(r"^#\s+(\S.*?)\s*$", re.MULTILINE)
SUMMARY_RE = re.compile(r"^>\s*摘要:\s*(\S.*?)\s*$", re.MULTILINE)
TRIGGER_RE = re.compile(r"^>\s*触发:\s*(\S.*?)\s*$", re.MULTILINE)

# pitfalls 条目的三个必填字段 (条目以 `### ` 起头, 字段是 `- **触发**: …` 这样的行)
ENTRY_HEADING_RE = re.compile(r"^###\s+(\S.*?)\s*$", re.MULTILINE)
REQUIRED_FIELDS = ("触发", "判别", "处置")

# --------------------------------------------------------------------------- 存根

STUB_MARK = "已迁至"
STUB_CAP = 2000  # 2026-09-29 随全表翻倍 (原 1,000) —— 存根只要是个小指针, 不是精确预算

# 需要存根保护的顶层文档: 拆成同名目录后, 原路径必须降级为 ≤1 KB 存根
# (引用面统计见方案 §08 —— testing.md 132 处 / pitfalls.md 113 处, 大量在历史计划与 issue 报告里)
STUB_CANDIDATES = (
    "pitfalls.md",
    "testing.md",
    "progress.md",
    "systemPatterns.md",
    "modules.md",
    "conventions.md",
    "config-reference.md",
    "rule-system.md",
    "activeContext.md",  # 2026-09-23: 滚动状态迁 activeContext/ 切片目录, 原路径降级为存根
)

# 有独立生成器、不走 gen_kb_index 的目录 (放进 `EXCLUDED_DIRS` 后不会被当成「索引目录」)
# `activeContext` 用 `gen_active_recent.py`(打印而非生成): 若让它自发现, gen_kb_index 会造出一个
# 随切片数增长的 `_index.md`, 终将撞 index 档 —— 而时间戳文件名本身已是索引, 不需要它。
# `plans` / `reports`(2026-09-23 由 docs/ 迁入)用 `gen_docs_index.py`: 内容是 HTML 制品,
# 由 `doc-*` meta 与生成器维护, 没有三行头元数据可扫。
EXCLUDED_DIRS = ("tasks", "issues", "attachments", "activeContext", "plans", "reports")

# --------------------------------------------------------------------------- 探测


def find_root(start: Path | None = None) -> Path:
    """仓库根: 从 start(默认脚本目录)向上找 `.git`(目录或 worktree 的 `.git` 文件)。

    **不按 skill 的安装深度反推** —— `parents[n]` 只在 `.agents/skills/<name>/scripts/`
    这一种布局下成立 (这条坑已在 KB 里记过)。探测不到时退回 `parents[4]` 兜底,
    并允许调用方用 `--root` 覆盖。
    """
    cur = (start or SCRIPTS_DIR).resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists():
            return parent
    return Path(__file__).resolve().parents[4]


def resolve_mb_dir(root: Path, dir_arg: str | None = None) -> Path:
    """memory-bank 目录: `--mb-dir` 显式指定优先, 否则 `<root>/memory-bank`。"""
    if dir_arg:
        cand = Path(dir_arg)
        return (cand if cand.is_absolute() else root / cand).resolve()
    return (root / "memory-bank").resolve()


def resolve_doc_path(raw: str, root: Path, mb: Path) -> Path:
    """用户传入的文档路径 → 绝对路径 (`kb.status` / `kb.bump` / `kb.new --refs` 共用)。

    接受三种形态, 按序解析 (`kb.docmap` 输出的是 mb 相对链接, 用户照抄最自然):
    ① 绝对路径 (原样); ② 仓库根相对 (`memory-bank/plans/...`); ③ mb 相对 (`plans/...`)。
    三种都不存在时退回 ② 的解析 —— 报错文案按仓库根相对展示, 与其它命令一致。
    """
    cand = Path(raw)
    if cand.is_absolute():
        return cand.resolve()
    for base in (root, mb):
        probe = (base / cand).resolve()
        if probe.is_file():
            return probe
    return (root / cand).resolve()


def detect_doc_kind(path: Path, mb: Path) -> str:
    """路径 → 改面载体 (`kb.status` / `kb.bump` / `kb.new --refs` 目标校验共用)。

    返回 `DOC_KIND_*` 之一; `""` = 不在改面范围 (调用方拒绝并给指路, **不猜载体**)。
    """
    try:
        rel = path.resolve().relative_to(mb.resolve()).as_posix()
    except ValueError:
        return ""
    if path.name.startswith("_") or rel.startswith("attachments/"):
        return ""
    if rel.startswith(("plans/", "reports/")) and rel.endswith(".html"):
        return DOC_KIND_PLAN
    if rel.startswith("tasks/") and rel.endswith(".md"):
        return DOC_KIND_TASK
    if rel.startswith(f"{SLICE_DIR}/") and rel.endswith(".md"):
        return DOC_KIND_SLICE
    if rel.startswith("issues/") and rel.endswith(".html"):
        return DOC_KIND_ISSUE
    return ""


def rel_posix(path: Path, root: Path) -> str:
    """相对仓库根的 posix 路径 (markdown 链接里 `\\` 是错的)。跨盘时返回绝对路径。"""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def rel_link(from_dir: Path, target: Path) -> str:
    """从 from_dir 指向 target 的相对链接 (posix)。"""
    return Path(os.path.relpath(str(target.resolve()), str(from_dir.resolve()))).as_posix()


def char_count(path: Path) -> int:
    """字符数 —— 与 IDE 注入口径一致。

    用 `read_bytes().decode()` 而不是 `read_text()`: 后者走 universal newlines 会把 CRLF
    折成 LF, 每行少算一个字符。卡在临界值时会误判放行。
    """
    return len(path.read_bytes().decode("utf-8"))


# 各生成脚本对应的**重建/校验**命令(task id 单点定义在 `.commands/kb/` 包里)。
# ❗必须写"真的能重建 / 校验这个脚本产出"的那条: 2026-09-24 实测 —— 原先无论传什么都返回
#   `kb.index`, 而 `kb.index` 当时只跑 gen_tasks_index + gen_kb_index ⇒ `_doc-map.md` /
#   `plans|reports/_index.md` 的报错文案把用户指向一条**跑完仍然红**的命令(而提交闸门
#   早就把这两条 `--check` 挂上了, 于是"闸门能红、却没有一条能修的命令")。
# 守阵: `tests/test_memory_bank.py::test_gen_cmd_hints_name_real_tasks` —— 钉住
#   "每个调用点的脚本都在表里" + "每个 task id 在 .commands/ 里真实存在"。
GEN_CMD_BY_SCRIPT = {
    "gen_tasks_index.py": "commands run kb.index",
    "gen_kb_index.py": "commands run kb.index",
    "gen_docs_index.py": "commands run kb.index",
    # 生成物集合的单点: kb.index 调它, 由它覆盖上面三条 + create-issue 的 gen_issues_index。
    "gen_all.py": "commands run kb.index",
    # 只校验/查询不写文件的脚本 —— 它的"重跑"是校验或查询命令, 不是重建命令
    # (gen_doc_map.py 同类: 2026-09-29 起 _doc-map.md 物化退役, 改查询 `commands run kb.docmap`)
    "gen_active_recent.py": "commands run kb.active --check",
    "gen_baseline_recent.py": "commands run kb.baseline --check",
}


def gen_cmd(root: Path, script: str) -> str:
    """生成物头部 / 报错文案里该写的**重建方式** —— 写 task id, 不写命令本体。

    命令只有一处定义(在 `.commands/kb/` 这个包里); 生成物、文档里再抄一份就是副本,
    而"哪一份才是生效的那份"并不写在命令旁边 —— 见 `scripts/check_command_drift.py`
    (那条机检会把手抄形态直接判红)。

    ❗按脚本查表(`GEN_CMD_BY_SCRIPT`), **不要**退化成"所有脚本返回同一句":
    脚本产出不同 ⇒ 修它的命令就不同, 指错命令比不给提示更费时间(照做一遍还是红的)。
    未知脚本退回 `kb.index`(它是"重建全部生成物"的总入口, 至少不会指到一条无用的命令)。
    """
    return GEN_CMD_BY_SCRIPT.get(script, "commands run kb.index")


def rebuild_index(root: Path, mb: Path, script: str) -> list[Path]:
    """改后重建受影响的索引 (`kb.new` / `kb.status` / `kb.bump` 共用一份, 不各写一遍)。

    按 `DOC_KIND_INDEX_SCRIPT` 的值调对应生成器的 `build()` —— 与 `gen_all` 的集合单点
    同一实现; 空串 (切片族无索引) → 空表。索引文件一律 LF (`newline="\\n"`, 同生成器口径)。
    `gen_kb_index` 走全量 build_all (坑档/进展件入索引; 与 `commands run kb.index` 同一实现,
    确定性幂等) —— 不是"只重建受影响目录", 集合单点不按调用点分裂。
    tasks/plans 的归档索引 (`attachments/_archive.md`, CLOSED_KEEP 出口) 与主索引**同批**写,
    缺了它 `gen_all --check` 恒红 —— 同 `gen_issues_index` 的同批纪律。
    """
    if not script:
        return []
    module = __import__(script)
    written: list[Path] = []
    if script == "gen_docs_index":
        for kind, text in module.build(root, mb).items():
            path = mb / kind / "_index.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            written.append(path)
        # 归档索引与主索引**同批**生成 (CLOSED_KEEP 出口; 缺它 gen_all --check 恒红)。
        for path, text in module.build_archives(root, mb).items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            written.append(path)
    elif script == "gen_tasks_index":
        path = mb / "tasks" / "_index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(module.build(root, mb), encoding="utf-8", newline="\n")
        written.append(path)
        # 归档索引与主索引**同批**生成 (CLOSED_KEEP 出口; 缺它 gen_all --check 恒红)。
        archive = mb / "tasks" / ARCHIVE_REL
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_text(module.build_archive(root, mb), encoding="utf-8", newline="\n")
        written.append(archive)
    elif script == "gen_kb_index":
        for path, text in module.build_all(root, mb).items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            written.append(path)
    return written


# --------------------------------------------------------------------------- 元数据


@dataclass
class Meta:
    """主题文件的三行头元数据 (生成器的数据源)。"""

    title: str = ""
    summary: str = ""
    triggers: str = ""

    @property
    def has_summary(self) -> bool:
        return bool(self.summary)

    @property
    def has_triggers(self) -> bool:
        return bool(self.triggers)

    @property
    def complete(self) -> bool:
        return bool(self.title) and self.has_summary and self.has_triggers


def read_meta(path: Path) -> Meta:
    """读三行头元数据; 缺哪行就留空 (由守卫报红, 不在这里抛)。"""
    text = path.read_bytes().decode("utf-8")
    title = TITLE_RE.search(text)
    summary = SUMMARY_RE.search(text)
    triggers = TRIGGER_RE.search(text)
    return Meta(
        title=title.group(1) if title else "",
        summary=summary.group(1) if summary else "",
        triggers=triggers.group(1) if triggers else "",
    )


# --------------------------------------------------------------------------- 元数据行读写
# (`kb.status` / `kb.bump` / `kb.new --refs` 反向补链共用 —— **只动元数据行, 正文零触碰**)。
# ⚠ 缺目标行一律 fail-fast (返回 None), **不猜插入位置** —— 猜位置会静默改坏文件形态。

HTML_META_READ = '<meta name="{name}" content="([^"]*)">'


def html_meta(text: str, name: str) -> str | None:
    """读 HTML meta 值 (`doc-*` / `issue-*`; 与 gen_docs_index / gen_doc_map 的读取正则同款)。"""
    m = re.search(HTML_META_READ.format(name=re.escape(name)), text)
    return m.group(1) if m else None


def set_html_meta(text: str, name: str, value: str) -> str:
    """写 HTML meta: 存在则**原行替换值** (格式不动); 不存在则插在 `doc-updated` 行后
    (无则 `</head>` 前) —— 与既有制品的 meta 排列一致。lambda 替换绕开 `re.sub` 的
    替换串转义坑 (值里可能出现 `\\`)。"""
    pat = re.compile(r'(<meta name="%s" content=")([^"]*)(">)' % re.escape(name))
    if pat.search(text):
        return pat.sub(lambda m: m.group(1) + value + m.group(3), text, count=1)
    anchor = re.search(r'<meta name="doc-updated" content="[^"]*">\n', text)
    if anchor:
        return text.replace(anchor.group(0), anchor.group(0) + f'<meta name="{name}" content="{value}">\n', 1)
    return text.replace("</head>", f'<meta name="{name}" content="{value}">\n</head>', 1)


def sync_body_meta(text: str, name: str, value: str) -> str:
    """正文 `.meta` 展示行与 head meta 同改 (计划族模板的镜像行; 缺该行 = 原样返回)。

    镜像行是**派生面** (与 head 同源渲染, 报告族没有) —— 不跟着抬 = 渲染页显示过期值。
    状态词从词表单点 (`DOC_STATUSES`) 取, 只替换词本身; 词后的括号注记是 agent 的散文, 不碰。
    """
    if name == "doc-status":
        alternation = "|".join(re.escape(s) for s in DOC_STATUSES)
        pat = re.compile(r"(<b>doc-status</b> )(?:%s)" % alternation)
    else:
        pat = re.compile(r"(<b>%s</b> )\S+" % re.escape(name))
    if not pat.search(text):
        return text
    return pat.sub(lambda m: m.group(1) + value, text, count=1)


def md_field(text: str, field: str) -> str | None:
    """读 md 头部字段行 `**Field:** value` (Status/Added/Updated/Topics/Refs 同款); 缺返回 None。"""
    m = re.search(r"^\*\*%s:\*\*\s*(.+?)\s*$" % re.escape(field), text, re.MULTILINE)
    return m.group(1) if m else None


def set_md_field(text: str, field: str, value: str) -> str | None:
    """写 md 头部字段行 —— 存在则替换值 (格式不动); **不存在返回 None** (调用方 fail-fast)。"""
    pat = re.compile(r"^(\*\*%s:\*\*\s*).*$" % re.escape(field), re.MULTILINE)
    if not pat.search(text):
        return None
    return pat.sub(lambda m: m.group(1) + value, text, count=1)


def set_last_active(text: str, stamp: str) -> str:
    """抬切片 `> 最后活动:` 行 (严格 `YYYY-MM-DD HH:MM`, 同 `check_doc_templates` 的校验口径)。

    缺行则插在首个 `> 摘要:` 行后 —— 与 `wrap_session._touch_slice` 同口径 (模板切片摘要
    单行; 多行摘要的存量切片本就都带该行, 该分支近乎死代码)。
    """
    new_line = f"> 最后活动: {stamp}"
    if re.search(r"^>\s*最后活动:", text, re.MULTILINE):
        return re.sub(r"^>\s*最后活动:\s*\S.*$", new_line, text, count=1, flags=re.MULTILINE)
    return re.sub(r"^(> 摘要:.*)$", rf"\1\n{new_line}", text, count=1, flags=re.MULTILINE)


def split_refs(raw: str) -> list[str]:
    """refs 字符串 → 列表 (唯一合法分隔符 = 英文逗号; 视觉分隔符误用见 gen_doc_map 的报错提示)。"""
    return [p.strip() for p in raw.split(",") if p.strip()]


def html_set_refs(text: str, target_rel: str) -> str:
    """HTML 认领链: 在 `doc-refs` meta 里并入 target_rel (仓库根相对 posix)。

    只动元数据行 (D4); 已声明则**幂等**原样返回; 无 meta 则由 `set_html_meta` 插入。
    """
    existing = html_meta(text, "doc-refs")
    if existing is not None:
        refs = split_refs(existing)
        if target_rel in refs:
            return text
        return set_html_meta(text, "doc-refs", ", ".join([*refs, target_rel]))
    return set_html_meta(text, "doc-refs", target_rel)


def md_set_refs(text: str, target_rel: str) -> str:
    """md 认领链: 并入/插入 `**Refs:**` 行 (仓库根相对 posix, 英文逗号; 幂等)。

    只动元数据行; md 只认**首个** `**Refs:**` 行 (gen_doc_map 口径)。**空值占位行也算已有声明**
    (模板自带 `**Refs:**` 空 placeholder, 2026-10-31 起) —— 原位并值, 绝不另插一行 (复发 8 的 md 形态:
    另插一行让空值/旧值赢过新值)。插入锚点链 (与存量形态一致): 已有 `**Refs:**` → 并值; 有
    `**Topics:**` → 其后插 (档案形态); 三行头的最后一个 `>` 行后 (坑档/基线/切片形态); 都没有 →
    `# 标题` 行后。
    """
    m = re.search(r"^\*\*Refs:\*\*[ \t]*(.*?)[ \t]*$", text, re.MULTILINE)
    if m:
        refs = split_refs(m.group(1))
        if target_rel in refs:
            return text
        merged = ", ".join([*refs, target_rel])
        return re.sub(r"^\*\*Refs:\*\*[ \t]*.*?$", lambda mm: "**Refs:** " + merged, text, count=1, flags=re.MULTILINE)
    line = f"**Refs:** {target_rel}"
    anchor = re.search(r"^(\*\*Topics:\*\*\s*.+)$", text, re.MULTILINE)
    if anchor:
        return text.replace(anchor.group(1), anchor.group(1) + "\n" + line, 1)
    lines = text.split("\n")
    last_gt = -1
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            break
        if ln.startswith(">"):
            last_gt = i
    if last_gt >= 0:
        lines.insert(last_gt + 1, line)
        return "\n".join(lines)
    title = re.search(r"^(#\s+.+)$", text, re.MULTILINE)
    if title:
        return text.replace(title.group(1), title.group(1) + "\n" + line, 1)
    return line + "\n\n" + text


# --------------------------------------------------------------------------- 角色


def role_of(rel: str) -> str:
    """仓库相对路径 → cap 角色 (首个匹配生效, 顺序即优先级)。"""
    rel = rel.replace("\\", "/")
    if rel == "AGENTS.md":
        return "agents"
    if rel in (
        "memory-bank/tasks/_index.md", "memory-bank/issues/_index.md", "memory-bank/plans/_index.md",
        "memory-bank/reports/_index.md"
    ):
        return "index-auto"
    if rel == "memory-bank/README.md":
        return "index"
    # 目录级 _index.md 全部是生成物(check_index_regenerated 逐目录守卫"索引 == 生成结果"),
    # 行数随主题文档数增长且一行一条已是极简 —— 与 tasks/issues 同性质, 同属 index-auto。
    # (2026-09-27 校准: pitfalls/testing/_index 3,147 字符在 3,000 档常红, 15 个主题无收缩路径)
    if rel.endswith(INDEX_NAME):
        return "index-auto"
    if rel == "memory-bank/activeContext.md":
        return "volatile"
    if rel.startswith(f"memory-bank/{SLICE_DIR}/"):
        return "slice"
    if rel.startswith("memory-bank/testing/baselines/"):
        return "baseline-slice"
    if rel.startswith("memory-bank/tasks/"):
        return "task"
    if rel.endswith("-history.md"):
        return "log"
    if "/pitfalls/" in rel:
        return "pitfall"
    if rel.startswith(("memory-bank/config-reference/", "memory-bank/rule-system/")) or rel in (
        "memory-bank/config-reference.md",
        "memory-bank/rule-system.md",
    ):
        return "reference"
    return "evergreen"


def cap_of(rel: str) -> int:
    return CAP_POLICY[role_of(rel)]


# --------------------------------------------------------------------------- 目录遍历


def is_topic_file(path: Path) -> bool:
    """主题文件 = 不以 `_` 开头的 `.md` (`_index.md` / `_about.md` 不算)。"""
    return path.suffix == ".md" and not path.name.startswith("_")


def iter_topic_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.md") if is_topic_file(p))


def iter_indexed_dirs(mb: Path) -> list[Path]:
    """全部「索引目录」= 含 `_about.md` 的目录 (自发现, 新增目录自动纳入)。

    `tasks/` `issues/` 有自己的生成器, 且没有 `_about.md` —— 天然不在结果里;
    仍显式排除 `EXCLUDED_DIRS` 以免将来误加 `_about.md` 后冲突。
    """
    out: list[Path] = []
    for path in sorted(mb.rglob(ABOUT_NAME)):
        directory = path.parent
        if directory == mb or directory.name in EXCLUDED_DIRS:
            continue
        out.append(directory)
    return out


def iter_index_files(mb: Path) -> list[Path]:
    """全部 `_index.md` (含 tasks/ issues/ —— 它们也要被 README 引用, 否则是孤儿)。"""
    return sorted(mb.rglob(INDEX_NAME))


def split_pitfall_entries(text: str) -> list[tuple[str, str]]:
    """切出 pitfalls 条目: `### 标题` 起头, 到下一个 `###` / `##` / 文件尾。

    返回 [(标题, 块正文)]。
    """
    lines = text.split("\n")
    marks = [(i, line[4:].strip()) for i, line in enumerate(lines) if line.startswith("### ")]
    entries: list[tuple[str, str]] = []
    for idx, (start, title) in enumerate(marks):
        end = len(lines)
        for nxt in range(start + 1, len(lines)):
            if lines[nxt].startswith("## "):
                end = nxt
                break
        entries.append((title, "\n".join(lines[start:end])))
    return entries
