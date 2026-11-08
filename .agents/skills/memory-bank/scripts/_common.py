"""memory-bank 脚本族共用的常量与工具 (gen_kb_index / check_kb_structure 等)。

**与具体项目无关**: 不出现项目名、不假定 skill 的安装深度、不硬编码 memory-bank 路径 ——
换一个项目直接装上就能跑; 项目专属值 (如 AGENTS.md 的 8000 字符上限) 留在项目脚本里。

单点定义 (守卫 import 这里, 不手抄):
- `CAP_POLICY`: 角色 → 字符上限 (方案 §03「cap 分级」); 改 cap 只改这里
- `PITFALL_CLASSES`: pitfalls 的类枚举 (扩类须三处同步: 本常量 / 新建目录 / README 细路由)
- `DOC_STATUSES` / `TERMINAL_DOC_STATUSES`: 计划 / 报告 / issue 共用的 5 词表与其完结子集
  (gen_doc_map 校验 / flip_status 词表 / check_doc_templates 都 import 这里)
- `TASK_STATUSES` / `TASK_DOMAINS` / `TASK_FILE_RE`: 任务档案的 4 词表 / 领域枚举 / 命名正则
  (`kb.new` / `check_doc_templates` 同源)
- `FAMILIES`: 文档族注册表 (plan/task/slice + P3 二期 pitfall/report/baseline +
  2026-11-07 收编的 issue → 命名/模板/词表/索引动作) —— `kb.new` / `kb.wrap` /
  `check_doc_templates` 与模板的同一份注册表 (计划 26-10-17-0527 P1/P3; issue 收编见 26-11-07-0549 D4;
  2026-11-08 重构 W3: progress 族注册删除, 各族的索引重建只保留 pitfalls 一路)
- `detect_doc_kind` / `DOC_KIND_*`: 载体探测 (**改面**: plans|reports HTML · tasks · slices · issues) ——
  `kb.status` / `kb.bump` 的同一份; 与建面的 `FAMILIES` 分工 (那边管「建」, 这里管「改」)
- `html_meta` / `set_html_meta` / `md_field` / `set_md_field` / `set_last_active`: 元数据行读写单点
  (doc-* meta 与 `**字段:**` / `> 最后活动:` 行; 缺目标行返回 None, 由调用方 fail-fast)
- `sync_body_meta`: 正文 `.meta` 镜像行与 head meta 同改 (计划族模板的展示行; 缺即无操作) ——
  派生面不跟着抬 = 渲染页显示过期值
- `html_set_refs` / `md_set_refs`: 认领链声明 (doc-refs meta / `**Refs:**` 行) 的插入/合并单点
  (D4 反向补链; 值 = 仓库根相对路径, 英文逗号; md 只动**首个** `**Refs:**` 行; 幂等)
- `rebuild_index`: 改后重建受影响索引的共同落点 —— 2026-11-08 重构 W3 起只服务 pitfalls 索引
  (gen_kb_index; `kb.new pitfall` 的建后落点; 与 `gen_all` 的集合单点同一 build 实现)
- `TYPES` / `TIERS` / `TIER_BY_TYPE` / `SLUG_RE` / `ISSUE_FILE_RE`: issue 族常量
  (2026-11-07 起 create-issue 的脚本与模板物理并入本 skill ——
  计划 26-11-07-0549 W1; 原两侧各一份的 5 词表合一为 `DOC_STATUSES`, 取时走 timekit 单点, 不另设;
  同日 W3 起 `kb.new issue` 收编建件, 档位→模板映射搬进 `FAMILIES["issue"].template_by_tier`,
  原 `TIER_TEMPLATE` 退役)
- `find_root()`: 仓库根探测 (向上找 `.git`, 而非按 skill 安装深度反推 `parents[n]`)
- `resolve_mb_dir()`: memory-bank 目录探测 (`--mb-dir` 显式指定优先)
- `read_meta()`: 主题文件三行头元数据 (`# 标题` / `> 摘要:` / `> 触发:`)
- `role_of()`: 仓库相对路径 → 角色 (决定套哪档 cap)
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent

# --------------------------------------------------------------------------- cap 策略

# 角色 → 字符上限 (首个匹配生效, 口径同项目脚本 check_context_caps.py: 按**字符**数)。
# 2026-11-05 用户重定调: 存量 tasks 一律不动(排障才读, 改造收益低), task cap 收紧到 8,000 且只约束
# 此后新建的档案(存量整类豁免, 见 CAP_TASK_FREEZE); log/evergreen/pitfall/index-auto 四类存量清零到
# 8,000 且 cap 同步收紧。旧值(task/log 48,000·evergreen 20,000·pitfall 12,000·index-auto 25,200)作废。
# 唯一例外 `agents`: AGENTS.md 的 8000 是 IDE 注入 `slice(0, 8000)` 的硬约束, 放大 = 守卫失效 + 尾部静默截断。
CAP_POLICY: dict[str, int] = {
    "index": 6000,  # `<doc>/_index.md` 与 memory-bank/README.md —— 手写路由/索引
    # 自动生成、行数随档案/issue 数增长的目录索引。2026-11-05 起与 pitfall 同档, 存量由生成器
    # (摘要截断/分卷)清零到 8,000; 手改无效, 只改生成器。
    "index-auto": 8000,
    "pitfall": 8000,  # pitfalls/* 条目集 —— 读法是「扫描找一条」, 比通读更贵
    "evergreen": 8000,  # 常青主题 (叙述型) —— 2026-11-05 收紧, 超 8K 即债务
    # reference 角色已随 2026-11-08 重构 W5 删除 (config-reference/ · rule-system/ 主体先亡,
    # src/ 侧 check_context_caps 无消费面, grep 实证) —— 命中不到的路径落 evergreen。
    "volatile": 24000,  # 易变层 (2026-11-08 重构: 顶层易变件已删, 角色保留为历史占位)
    "slice": 12000,  # active-context/ 会话切片 —— per-会话 / per-专题, 天然比整份易变层小
    # testing/baselines/ 基线切片 —— 不可变的一次性快照, 单条本就该短; 超了说明把逐轮流水又堆回来了
    # (明细下沉对应任务档案, 不是调 cap)。
    "baseline-slice": 8000,
    "task": 8000,  # 任务档案(新建); 2026-11-05 之前的存量整类豁免, 见 CAP_TASK_FREEZE
    # append-only 历史流水 (如 `*-history.md`) —— **只增不改**, 每次改动追一条。
    # 2026-11-05 起 cap 收紧到 8,000, 存量同样清零; 触顶动作见 `check_kb_structure.trim_hint`。
    "log": 8000,
    "agents": 8000,  # 项目引导 (AGENTS.md; IDE 注入硬约束, 不随任何一轮翻倍, 见上)
}

# 整类豁免 (2026-11-05 用户定调): 文件名前缀日期 < 此值的 task 档案不参与 cap 检查 ——
# 存量 tasks 只在排障时读, 改造收益低, 一律不动。此值之后新建的 task 必须 ≤ 8,000。
# 个案豁免不写在这里: 必须在文档头写明理由, 并经用户逐件确认(计划里的"待审"才可落地)。
CAP_TASK_FREEZE = "26-11-05"

# 下限建议: **只 WARN** —— 主题文件过小会让「读三个文件」取代「读一节」, 反而更贵
CAP_MIN_WARN = 1500

# 陈旧度软提示阈值 (2026-11-05 计划 26-11-05-1049 §07 P4; **只提示不拦截**):
# volatile(会话切片)= 会话级, 取 14 天; reference 类主题 = 90 天;
# plan / report 出厂即冻结, 不参与老化提示。消费方: gen_active_recent.py / nav_data.py。
STALE_DAYS_VOLATILE = 14
STALE_DAYS_REFERENCE = 90

# `active-context/` 切片数上限 —— 切片无界增长是这个方案的已知代价, 给个可判定的收口线。
# 2026-09-30 起它是**债务**而不是判红项(D2 拍板, 计划 26-09-30-2112): 违反它只是"该蒸馏没蒸馏",
# 与尺寸债同属一场清理会话的活, 而留红会逼出"为了过守卫而违规归档"。
# **只告警、不拦**: 达到上限时 `kb.active` / `kb.check` 打债务行, 退出码仍 0, 不阻断 kb.wrap 与提交。
# 120 = 14 天蒸馏窗口 × 日均 ~8.5 篇(2026-11-03 用户定调 70→120: 多 clone 并行日常态实测可达
# 15 片/日, 原 70 反复触顶; 旧校准 48→56→70 见 git 历史)
SLICE_COUNT_LIMIT = 120

# 触顶后的**处置目标**(2026-11-03 用户定调): 一次清理要降到 80 条以内 —— 与尺寸 cap 的
# 固定动作同思路, 留足追加余量, 否则刚处理完又立刻超限。提示文案必须带上这个落点,
# 不能只写"请清理"(活跃切片多时无从判断清到哪算完)。
SLICE_COUNT_TARGET = 80

# --------------------------------------------------------------------------- 文档形态状态词

# 计划 / 报告 (`doc-status`) 与 issue (`issue-status`) 共用的 5 词表 —— **单点定义**
# (gen_doc_map 校验 / flip_status 词表 / check_doc_templates 都 import 这里, 不手抄)。
# ⚠ 表外值 (如 `Draft`) 会让 `gen_doc_map --check` (提交闸门) 判红 —— 校验单点在
#   `gen_doc_map.check_status_vocabulary` (见 pitfalls/kb/doc-status-meta.md)。
# ⚠ 与 tasks/ 档案的 4 词表 (`**Status:**` = In Progress/Open/Done/Dropped) **不同**, 别互相套用。
DOC_STATUSES = ("In Progress", "Open", "Done", "Dropped", "Superseded")

# 完结态 (`DOC_STATUSES` 子集): gen_doc_map 轮转用 —— 专题「有未完结件」才算活跃。
TERMINAL_DOC_STATUSES = frozenset({"Done", "Dropped", "Superseded"})

# --------------------------------------------------------------------------- issue 族
# (2026-11-07 起 create-issue 的脚本与模板物理并入本 skill (计划 26-11-07-0549 W1), 常量随之
# 单点化: 原先 create-issue `_common.py` 里另设的 5 词表并入上方 `DOC_STATUSES`, issue 专属枚举
# 落在本节 —— 增删类型/档位只改这里。同日 W3 起 `kb.new issue` 收编建件 (D4, new_issue.py 退役),
# 枚举的消费方 = FAMILIES["issue"] (type_enum / naming_re / template_by_tier 全从本节拼出)。
# 取时不用本文件: 走 timekit 单点(UTC+8 naive 墙钟), 不引入第二套时间实现。)

# 问题类型枚举 —— 增删类型只改这一处 (文件名、meta、索引、脚本校验全部读它)
TYPES = ("bug", "perf", "docs", "test", "refactor", "feat", "chore", "question")

# 类型 → 默认档位; --tier 可覆盖 (如 test 的失败用例用 --tier standard)
TIER_BY_TYPE = {
    "bug": "standard",
    "perf": "standard",
    "feat": "standard",
    "docs": "light",
    "test": "light",
    "refactor": "light",
    "chore": "light",
    "question": "light",
}
TIERS = ("light", "standard")

# slug: 小写英文短横线, 允许单段 (<领域>-<专题> 只是建议, 分类职责已交给 type)
# (与下方 TOPIC_FILE_RE 同款正则 —— 那份带 .md 后缀管主题文件名, 这份用于 slug 的裸校验)
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# issue 报告文件名: <时间>-<类型>-<slug>.html —— 类型固定在第二段, 扫描目录即可按类型聚合。
# 带 `.html$` 的**完整文件名**正则 (同 PLAN_FILE_RE 等族注册表口径; W3 起 kb.new 的派生名守卫
# 与 FAMILIES.naming_re 都按完整文件名匹配)。
# 中段**从 TYPES 单点拼出** (W3: 不手抄第二份枚举) —— 扩类型只改 TYPES, 命名正则/
# CLI 枚举全部跟着走; 枚举外类型在这里就匹配不上 (建件端正则与守卫端正则同一份)。
ISSUE_FILE_RE = re.compile(
    r"^(?P<stamp>\d{2}-\d{2}-\d{2}-\d{4})-(?P<type>" + "|".join(TYPES) + r")-(?P<slug>[a-z0-9-]+)\.html$"
)

# issues 目录 = `<mb>/issues`(`FAMILIES["issue"].spec.dir` 单点落点) —— 建件 (kb.new) 走这一处。
# 原 create-issue 独立工具时代的三候选探测
# (`memory-bank/issues` → `issues` → `docs/issues`, resolve_issues_dir/ISSUES_CANDIDATE_DIRS)
# 已随 new_issue.py 一并退役 (2026-11-07, 计划 26-11-07-0549 D2; 评审裁定: 无任何生产语义
# 依赖候选 2/3, 留着只会让「目录在哪」出现两套口径)。

# --------------------------------------------------------------------------- 结构枚举

# pitfalls 的类枚举。**扩类须三处同步**: 本常量 / 新建 `<class>/_about.md` / memory-bank/README.md 细路由。
PITFALL_CLASSES = ("git", "web-ui", "backend", "testing", "ops", "kb", "docs")

# 主题文件名: 小写英文与数字, 短横线分段 (同款裸名正则见上方 issue 族的 SLUG_RE)
TOPIC_FILE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

# 会话切片文件名: 定宽 `YY-MM-DD-HHMM-<slug>` —— 前缀定宽才能保证**字典序 == 时间序**
# (写成 `26-9-3-34` 立刻乱序)。⚠ 与 tasks/ 档案「不带时分、同天同专题必撞同路径」的故意设计
# **意图相反**: 那边靠撞名暴露重复, 这边靠带时分避撞名 —— 所以两者必须分目录, 别混。
SLICE_FILE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

# 切片头部的「最后活动」字段 —— 阅读器的排序键; 缺失则回退文件名时间戳 (= 创建时间)
LAST_ACTIVE_RE = re.compile(r"^>\s*最后活动:\s*(\S.*?)\s*$", re.MULTILINE)
# 会话滚动状态切片所在目录 (`memory-bank/active-context/`; 2026-11-08 重构定名)
SLICE_DIR = "active-context"

# --------------------------------------------------------------------------- 文档族注册表
# (`kb.new` / `kb.wrap` / `check_doc_templates` 与模板的**同一份**注册表 —— 命名/模板/词表/
# 索引动作只在这里定义一次, 命令与守卫都 import 它, 不造第二套规范)。
#
# 模板落点: skill 的 `templates/<spec.template>` (分级族按 `template_by_tier` 选); 状态词表
# import 既有单点 (HTML 制品 5 词 `DOC_STATUSES` / 档案 4 词 `TASK_STATUSES`); 建后由命令按
# `index_script` 重建**该族受影响的那份索引**(与 `gen_all` 的集合单点同一实现, 不另建)。
# 2026-11-08 重构 W3 (D4/D5): 索引生态收缩为 pitfalls 一家 —— plan/task/issue/report 族的
# `index_script` 让位为空串 (它们的 `_index.md` 已随低价值层移除退役, kb.new/kb.status/kb.bump
# **不得**再重建), 只有 pitfall 族仍指向 gen_kb_index; progress 族注册删除 (progress/ 目录全灭,
# D9), `kb.new progress` 不再是合法族。
# P3 扩族 (计划 §04/§07): pitfall (子目录选类) / report (出厂即 Done) / baseline
# (`--total` 誊写, 无索引)。W3 收编 issue 族 (计划 26-11-07-0549 D4):
# 模板按档位选 + 文件名中段从 TYPES 拼 (new_issue.py 退役, 26-10-17-0527 D2 正式翻案)。

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


# 任务档案 4 词表 —— **单点**: `kb.status` / `check_doc_templates` 都 import 这里。
# ⚠ 与 HTML 制品的 5 词表 (`DOC_STATUSES`) **不同**, 别互相套用 (doc-forms 状态词节同款警告)。
TASK_STATUSES = ("In Progress", "Open", "Done", "Dropped")

# 命名正则 (单点: `new_doc` 建件 / `check_doc_templates` 判新增面都 import 这里, 不手抄)。
# ⚠ 切片用的 `SLICE_FILE_RE` 已在上方 (带时分避撞名); 档案用 `TASK_FILE_RE` (不带时分、
# 同天同专题必撞同路径 = 靠撞名暴露重复)。两者意图相反, 必须分目录, 别混。
# 基线切片与切片同款命名 (带时分), 所以直接用 `SLICE_FILE_RE` —— 同一份正则两种载体,
# 目录不同 (testing/baselines/ vs active-context/) 即不混。
PLAN_FILE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-\d{4}-plan-[a-z0-9]+(?:-[a-z0-9]+)*\.html$")
REPORT_FILE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-\d{4}-report-[a-z0-9]+(?:-[a-z0-9]+)*\.html$")
TASK_FILE_RE = re.compile(r"^\d{2}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")

# 模板里的填空标记 (`new_doc` 建后据此打印 SLOT 清单; `check_doc_templates` 判「无残留」)
SLOT_RE = re.compile(r"<!--\s*SLOT:\s*(.*?)\s*-->", re.DOTALL)


@dataclass(frozen=True)
class FamilySpec:
    """一族文档的命名 / 模板 / 词表 / 索引动作 —— 命令与守卫的同一份注册表。"""

    name: str
    dir: str  # memory-bank 下的子目录 (切片族是 `active-context`; 可多段如 `testing/baselines`)
    ext: str  # ".html" | ".md"
    template: str  # skill `templates/` 下的文件名 (issue 族为空串 —— 模板按档位选, 见下)
    statuses: tuple  # 状态词表 (切片族无状态, 空元组)
    default_status: str  # 出厂状态
    index_script: str  # 建后重建哪个生成器 (2026-11-08 W3 起仅 pitfall 族 = gen_kb_index; 其余族空串)
    naming_re: object  # 文件名正则 (从上面的单点来)
    domain_first: bool  # `--topic` 领域段须 ∈ `TASK_DOMAINS` (最长前缀匹配, 仅档案族)
    subdir_flag: str = ""  # 第二段子目录的 CLI 参数名 (坑档 = `class`; 其余族空)
    subdir_values: tuple = ()  # 子目录允许值 (坑档 = `PITFALL_CLASSES`; 其余族空)
    # 档位选模板 (W3, 计划 26-11-07-0549): 非空时模板按 `--tier` 从这里选 (issue 族), `template`
    # 让位为空串; 空 dict = 该族不分级, 模板恒 `template` (既有七族零影响)。
    template_by_tier: dict = field(default_factory=dict)
    # 文件名中段的类型枚举 (issue 族 = `TYPES` 单点, 同 `subdir_values` 的 import 纪律);
    # 空元组 = 该族文件名无类型段 (CLI 据此决定是否收 `--type`)。
    type_enum: tuple = ()


FAMILIES: dict[str, FamilySpec] = {
    "plan":
        FamilySpec(
            name="plan",
            dir="plans",
            ext=".html",
            template="plan.html",
            statuses=DOC_STATUSES,
            default_status="Open",
            index_script="",  # plans/_index.md 已随 2026-11-08 重构退役 (D4/D5), 建后不再重建
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
            index_script="",  # tasks/_index.md 已随 2026-11-08 重构退役 (D4/D5), 建后不再重建
            naming_re=TASK_FILE_RE,
            domain_first=True,
        ),
    # ---- W3 建件收编 (计划 26-11-07-0549 D4, 翻案 26-10-17-0527 D2): issue 族入列,
    # new_issue.py 退役 —— 命名/模板/词表动作收进本注册表, 不造第二套。
    "issue":
        FamilySpec(
            name="issue",
            dir="issues",
            ext=".html",
            template="",  # 模板按档位选 (template_by_tier), `template` 让位为空串
            statuses=DOC_STATUSES,  # issue-status 与 doc-* 制品同一 5 词表 (gen_doc_map / flip_status 同源)
            default_status="Open",  # 出厂恒 Open; 翻状态 W4 收编后走 kb.status (CLI 不设 --status)
            index_script="",  # issues/_index.md 已随 2026-11-08 重构退役 (D4/D5), 建后不再重建
            naming_re=ISSUE_FILE_RE,  # 文件名中段从 TYPES 单点拼出 (见上方 issue 族节)
            domain_first=False,
            template_by_tier={
                "light": "issue-light.html",
                "standard": "issue-standard.html"
            },
            type_enum=TYPES,  # `--type` 枚举 (文件名中段; 单点 TYPES, 同 subdir_values 的 import 纪律)
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
    # ---- P3 二期族 (计划 §04/§07): 模板/命名/索引动作都在这里单点定义
    "pitfall":
        FamilySpec(
            name="pitfall",
            dir="pitfalls",
            ext=".md",
            template="pitfall.md",
            statuses=(),
            default_status="",
            index_script="gen_kb_index",  # pitfalls/<class>/_index.md + pitfalls/_index.md 类指针 (唯一幸存索引面)
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
            index_script="",  # reports/_index.md 已随 2026-11-08 重构退役 (D4/D5), 建后不再重建
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
    # progress 族注册已随 2026-11-08 重构删除 (D9: progress/ 目录全灭) —— `kb.new progress` 不再合法。
}

# --------------------------------------------------------------------------- 改面载体探测
# (`kb.status` / `kb.bump` 的同一份; 与建面 `FAMILIES` 分工 —— 那边管「建」, 这里管「改」)。
# 探测 = memory-bank 相对路径的目录前缀 + 扩展名, 收集口径与 `gen_doc_map.collect()` 同源
# (plans/reports/tasks/issues 四形态), 外加 active-context 切片 (切片不进 docmap, 但 kb.bump 抬它)。
# ⚠ 只认 memory-bank 下的文件 —— 别处的路径一律 "" (防命令改错文件, 调用方拒绝并指路)。

DOC_KIND_PLAN = "plan"  # plans|reports/*.html —— 5 词表 (`doc-status`), 翻转抬 doc-updated
DOC_KIND_TASK = "task"  # tasks/*.md —— 4 词表 (`**Status:**`), 翻转抬 **Updated:**
DOC_KIND_SLICE = "slice"  # active-context/*.md —— **无状态**: kb.status 拒绝并指路 kb.wrap 迁出
DOC_KIND_ISSUE = "issue"  # issues/*.html —— 建件已收编进 FAMILIES (W3, `kb.new issue`), 词表
# 单点同在本文件 (DOC_STATUSES); 翻状态 W4 起收编进 kb.status (计划 26-11-07-0549
# D5: 徽标 + issue-status meta 两处一次改 + 状态变更日志追加一行); 改版仍不在 kb.bump 范围 (直编辑);
# 但**可以是 refs 目标** (doc-refs meta)

# 词表 (单点: 翻转只查这张表, 不在命令里分叉 if-else)。
# (2026-11-08 重构 W3: 原配套的 DOC_KIND_INDEX_SCRIPT 索引动作表已退役 —— 改面四族的
# `_index.md` 全部随低价值层移除, kb.status / kb.bump 不再重建任何索引。)
DOC_KIND_STATUSES = {DOC_KIND_PLAN: DOC_STATUSES, DOC_KIND_TASK: TASK_STATUSES, DOC_KIND_ISSUE: DOC_STATUSES}
DOC_KIND_CN = {DOC_KIND_PLAN: "计划/报告", DOC_KIND_TASK: "任务档案", DOC_KIND_SLICE: "会话切片", DOC_KIND_ISSUE: "issue"}

# 索引/元数据文件名: `_` 开头, 不参与「主题文件」计数
INDEX_NAME = "_index.md"
# 分卷页 (`_index-1.md` …): 主索引装不下主题表时的同族生成物, 与主索引同档 cap/同套守卫
INDEX_VOLUME_RE = re.compile(r"_index-\d+\.md$")
ABOUT_NAME = "_about.md"

# 三行头元数据 —— 条目型与叙述型共用同一套 (这是「全库一套机制」的关键)
TITLE_RE = re.compile(r"^#\s+(\S.*?)\s*$", re.MULTILINE)
SUMMARY_RE = re.compile(r"^>\s*摘要:\s*(\S.*?)\s*$", re.MULTILINE)
TRIGGER_RE = re.compile(r"^>\s*触发:\s*(\S.*?)\s*$", re.MULTILINE)

# pitfalls 条目的三个必填字段 (条目以 `### ` 起头, 字段是 `- **触发**: …` 这样的行)
ENTRY_HEADING_RE = re.compile(r"^###\s+(\S.*?)\s*$", re.MULTILINE)
REQUIRED_FIELDS = ("触发", "判别", "处置")

# --------------------------------------------------------------------------- 目录遍历排除

# 不参与 gen_kb_index「索引目录」自发现的目录 (放进 `EXCLUDED_DIRS` 后不会被当成「索引目录」)。
# `active-context` 用 `gen_active_recent.py`(打印而非生成): 若让它自发现, gen_kb_index 会造出一个
# 随切片数增长的 `_index.md`, 终将撞 index 档 —— 而时间戳文件名本身已是索引, 不需要它。
# `plans` / `reports`(2026-09-23 由 docs/ 迁入): 内容是 HTML 制品, 由 `doc-*` meta 维护,
# 没有三行头元数据可扫 (其 `_index.md` 已随 2026-11-08 重构退役)。
# `conventions` / `testing`(2026-11-08 重构): 生成索引 `_index.md` 已随低价值层移除退役 ——
# 这两层的路由走 memory-bank/README.md 极简路由, 不再走 `_index` 生态 (D5: pitfalls 8 个
# `_index` 是唯一例外)。
EXCLUDED_DIRS = ("tasks", "issues", "attachments", "active-context", "plans", "reports", "conventions", "testing")

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

    接受三种形态, 按序解析 (跨形态视图输出的是 mb 相对链接, 用户照抄最自然):
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
# ❗必须写"真的能重建 / 校验这个脚本产出"的那条 —— 指错命令比不给提示更费时间(照做一遍还是红的;
#   2026-09-24 实测过"报错文案指向跑完仍红的命令"的缺陷形态)。
# 2026-11-08 重构 W3: 生成集合收缩为 pitfalls 索引一家(D5), 表里只留幸存的重建/校验入口。
# 守阵: `tests/test_memory_bank_structure.py::test_gen_cmd_hints_name_real_tasks` —— 钉住
#   "每个调用点的脚本都在表里" + "每个 task id 在 .commands/ 里真实存在"。
GEN_CMD_BY_SCRIPT = {
    "gen_kb_index.py": "commands run kb.index",
    # 生成物集合的单点: kb.index 调它。
    "gen_all.py": "commands run kb.index",
    # 只校验/查询不写文件的脚本 —— 它的"重跑"是校验或查询命令, 不是重建命令。
    "gen_active_recent.py": "commands run kb.active --check",
    "gen_baseline_recent.py": "commands run kb.baseline --check",
}


def gen_cmd(root: Path, script: str) -> str:
    """生成物头部 / 报错文案里该写的**重建方式** —— 写 task id, 不写命令本体。

    命令只有一处定义(在 `.commands/kb/` 这个包里); 生成物、文档里再抄一份就是副本,
    而"哪一份才是生效的那份"并不写在命令旁边 —— 见 `scripts/check_command_drift.py`
    (那条机检会把手抄形态直接判红)。

    ❗按脚本查表(`GEN_CMD_BY_SCRIPT`), **不要**退化成"所有脚本返回同一句":
    脚本产出不同 ⇒ 修它的命令就不同。未知脚本退回 `kb.index`(它是"重建全部生成物"的总入口,
    至少不会指到一条无用的命令)。
    """
    return GEN_CMD_BY_SCRIPT.get(script, "commands run kb.index")


def rebuild_index(root: Path, mb: Path, script: str) -> list[Path]:
    """改后重建受影响的索引 (2026-11-08 重构 W3 收口: 只服务 pitfalls 索引面)。

    `script` = `FAMILIES[...].index_script` 的值: 仅 pitfall 族仍是 `gen_kb_index`, 其余族
    空串 → 空表 (D4/D5: tasks/plans/reports/issues 的 `_index.md` 已随低价值层移除退役,
    `kb.new` / `kb.status` / `kb.bump` **不得**再重建它们)。`gen_kb_index` 走全量 build_all
    (与 `commands run kb.index` 同一实现, 确定性幂等) —— 不是"只重建受影响目录",
    集合单点不按调用点分裂。索引文件一律 LF (`newline="\\n"`, 同生成器口径)。
    """
    if not script:
        return []
    module = __import__(script)
    written: list[Path] = []
    if script == "gen_kb_index":
        targets = module.build_all(root, mb)
        for path, text in targets.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            written.append(path)
        # 分卷页是生成物: 主题变少/改名后不再需要的卷页同批删除 (否则 --check 恒红)。
        for stale in module.stale_volume_pages(mb, targets):
            stale.unlink()
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
    """读 HTML meta 值 (`doc-*` / `issue-*`; 与 gen_doc_map 的读取正则同款)。"""
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
    (存量件可能留有模板旧版自带的 `**Refs:**` 空 placeholder, 模板已不再输出, 2026-11-06 起) ——
    原位并值, 绝不另插一行 (复发 8 的 md 形态: 另插一行让空值/旧值赢过新值)。
    插入锚点链 (与存量形态一致): 已有 `**Refs:**` → 并值; 有
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
    """仓库相对路径 → cap 角色 (首个匹配生效, 顺序即优先级)。

    (2026-11-08 重构 W5: 原 index-auto 精确路径表 tasks/issues/plans/reports 的 `_index.md`
    已随低价值层移除删除 —— 四族索引退役后全是死路径; 自动索引角色由下方通配分支继续服务
    幸存的 pitfalls `_index`。)
    """
    rel = rel.replace("\\", "/")
    if rel == "AGENTS.md":
        return "agents"
    if rel == "memory-bank/README.md":
        return "index"
    # 目录级 _index.md 全部是生成物(check_index_regenerated 逐目录守卫"索引 == 生成结果"),
    # 行数随主题文档数增长且一行一条已是极简 —— 与 tasks/issues 同性质, 同属 index-auto。
    # (2026-09-27 校准: pitfalls/testing/_index 3,147 字符在 3,000 档常红, 15 个主题无收缩路径)
    if rel.endswith(INDEX_NAME) or INDEX_VOLUME_RE.search(rel.rsplit("/", 1)[-1]):
        return "index-auto"
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
    # 2026-11-08 重构: config-reference/ · rule-system/ 目录与同名顶层件已删, reference 角色
    # 同批删除 (W5, CAP_POLICY 行一并退役); 命中不到的路径落 evergreen。
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
    ⚠ 排除按 **mb 相对路径的首段**判(2026-11-08): `EXCLUDED_DIRS` 里有 `testing`/`conventions`
    这类与 pitfalls 子类同名的顶层目录 —— 按 `directory.name` 判会把 `pitfalls/testing/`
    这类**嵌套类目录**误排掉(实测: 其分卷页当场被判「过期」)。`attachments` 例外: 它是
    约定俗成的证据链目录名, 任一层级出现都排除(至今无一带 `_about.md`, 纯防御)。
    """
    out: list[Path] = []
    for path in sorted(mb.rglob(ABOUT_NAME)):
        directory = path.parent
        if directory == mb:
            continue
        rel_parts = directory.relative_to(mb).parts
        if rel_parts[0] in EXCLUDED_DIRS or "attachments" in rel_parts:
            continue
        out.append(directory)
    return out


def iter_index_files(mb: Path) -> list[Path]:
    """全部生成索引 (`_index.md` + 分卷页 `_index-<n>.md`)。"""
    return sorted(mb.rglob("_index*.md"))


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
