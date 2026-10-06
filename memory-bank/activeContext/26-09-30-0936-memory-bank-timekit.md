# 26-09-30-0936-memory-bank-timekit — memory-bank 取时间标准化

> 摘要: 用户提出文档日期不准/体例漂移/文件名出现未来时间, 要求 UTC+8 脚本单点取时 + 守卫 + 守卫脚本随 skill 移植。**实施完成 (2026-10-06)**: `timekit.py` (date/time/stamp/check, UTC+8 naive 墙钟) + 三层日期守卫 (文件名/元数据/正文) + `commands run kb.time` 流程接入 (挂 kb.check 与提交闸门) + SKILL.md 时间口径节 + create-issue 钉 +08 + 存量清洗 + `gen_active_recent` 收口静默回退 + `check_doc_links.py` 迁入 skill + `references/PORTING.md`。**已入库 `c612082a`**。
> 最后活动: 2026-10-06 20:14

**Refs:** memory-bank/testing/baselines/26-10-06-1955-memory-bank-timekit.md

## 已完成(本轮)

- 计划 `plans/26-09-30-0931-plan-memory-bank-timekit.html` (实施后置 doc-status Done); 档案 `tasks/26-09-30-memory-bank-timekit.md` (Done, 子任务 9/9)。
- **时间单点**: `.agents/skills/memory-bank/scripts/timekit.py` —— `datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)` (naive UTC+8 墙钟, 与机器时区无关, TZ 无关性由测试钉住); 子命令 `date` / `time` / `stamp` / 无参三行 / `check`。
- **三层守卫** (`timekit.py check`, 挂 `kb.check` 与提交闸门): 文件名 (tasks `YY-MM-DD` / 切片与 HTML 制品 `YY-MM-DD-HHMM`) / 元数据 (`Added` / `Updated` / `最后活动` / `doc-added` / `doc-updated`) / 正文 (斜杠 / 不补零 / 中文 / 紧凑 8 位 / ISO-T; 规范 token 不查未来)。md 跳过围栏与行内代码, html 跳过 code/pre/script/style 与 URL 串, 行内 `<!-- time:allow -->` 豁免整行。
- **流程接入**: 新 task `commands run kb.time` (取时入口); `timekit.py --check` 挂进 `kb.check` 与提交闸门 (改 `memory-bank/` 即触发)。
- **约定落地**: SKILL.md 新增「时间口径与取时」节 + 会话开始第 5 步 / 收尾切片 / 档案规范三处挂钩; `conventions/doc-forms.md` / `webui.md` 的「用命令取」落到 `commands run kb.time stamp`。
- **钉时区**: create-issue 真源 `new_issue.py` 的 `datetime.now()` → `now_local()` (UTC+8 naive); `_common.stamp()` / `long_date()` 同口径 (本地内联常量, 不跨 skill import)。
- **存量清洗**: 7 处坏「最后活动」+ 2 处坏 `Updated` 规范化, 2 处缺行补齐; 紧凑 8 位 10 处按边界豁免 (8 处在代码块/路径, 非日期 token)。
- **收口静默回退**: `gen_active_recent.parse_last_active` 区分「缺失」与「存在但格式坏」, 后者 `--check` 报红。
- **守卫脚本随 skill**: `check_doc_links.py` 从根 `scripts/` 迁入 skill (`git mv`, 根探测改 `_common.find_root()`); 同步改提交闸门 / `doc.links` task / pytest 引用; 新件 `references/PORTING.md`。

## 待办

- (无 —— 实施闭环并已入库 `c612082a`)
