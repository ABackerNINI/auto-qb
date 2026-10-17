# activeContext · memory-bank-doc-pipeline(26-10-17-0527)

> 摘要: memory-bank 文档统一模板 + 命令化创建/更新改造计划。用户目标有二:①统一风格 ②尽量减少 agent 修改步骤;首版设计缺②被用户纠正后按「一次逻辑动作 = 一条命令 + 一次填空,派生面零手写」重设计。产出计划 `memory-bank/plans/26-10-17-0527-plan-memory-bank-doc-pipeline.html`(doc-status Open):命令面 `kb.new` / `kb.status` / `kb.bump` / `kb.wrap`(脚本落 memory-bank skill scripts/,模板落 skill templates/,词表/时间/cap 全部 import 既有单点)+ SLOT 填空模板(一期 plan/task/slice 三族)+ 守卫只拦新增(冻结线豁免存量)+ 步数对照(新专题开工含立档 16→4、翻状态 4→1、收尾 6→1)。R1: D1–D6 已拍板锁定;§05 增剩余人工步骤量化与裁定(机械剩余恒 0 收录断言,边界裁定 A1–A7)。
> 最后活动: 2026-10-17 07:53

**用户诉求**: memory-bank 下各文档风格不一 → 要统一模板与统一的创建/更新方式;初步设想「命令+模板自动搭骨架,agent 仅填内容,留余地;状态/时间等自动填写;常用固定操作(如翻转文档状态)也写成命令」。grilling 两轮:第一轮 Q1–Q6 因询问工具展示不全改为文本列出;用户未逐项作答,给出方向性纠正——「设计目的一是统一风格,二是尽量减少 agent 的修改步骤,当前设计只着重第一点,重新设计」。

**本轮过程**: 开工同步快进 6d9bb9e7→ab2e8e30 → 读 doc-forms / webui / kb-structure / commands skill / kb 包 config + 抽样五族现行头部(切片/档案/计划 HTML/坑档/基线)→ grilling(第一轮 6 问文本)→ 按用户纠正重设计 → 落计划。

**关键事实**:
- kb 包既有模式 = `.commands/kb/config.toml` 挂 task id 调 skill scripts/ 里 python ⇒ 新命令落点 skill scripts/ + templates/,规范字段 import `_common`(DOC_STATUSES 5 词表/CAP_POLICY)+ timekit,不造第二套规范。
- 防漂移先例 = 守卫只拦新增(doc-forms 51 份旧命名豁免、check_wording FROZEN 常数)——模板必须配守卫才闭环。
- 切片头部两种形态并存(YAML vs 三行头);状态词表两张(HTML 5 词/档案 4 词)已于 26-10-16 单点化 fail-fast。
- cap 债务(本会话不动手,另开清理会话): 切片 132>70;26-10-15-0728(19,037)与 26-10-16-0541(13,905)超 12,000。

**产出**: 计划 26-10-17-0527(doc-status Open,§08 六项待拍板默认按推荐:D1 机器面强制+骨架可裁 / D2 一期三族 / D3 存量冻结 / D4 反向认领自动补链 / D5 切片去 YAML 归一三行头 / D6 kb.wrap 只做机械面)。

**R0(2026-10-17 05:27)**: 计划初版落盘;纯文档轮无代码事实变更。立档动作未执行(阈值 #3/#4 命中;按请求边界新建文件须用户逐项显式确认,确认后随本专题入库)。

**R1(2026-10-17 06:07)**: 用户拍板「这些按推荐」⇒ D1–D6 锁定;另三项拍板:命令粒度 = 单职责四条(否决工作流复合)、`kb.new` 不预建切片、`kb.wrap` 并入 P1。用户新增裁定问题「剩余人工步骤具体是多少」⇒ 计划 §05 增量化:口径(步 = 命令调用或文件编辑;进命令三判据)、对照修正(R0 漏计档案填空,新专题开工含立档 16→4 = 2 命令+2 填空)、输出契约(三分类清单 + 「机械 0」收录断言)、边界裁定 A1–A7(Summary 预填/初次填空不强制 bump/后补 Refs 留人工/基线数字不自动化/进度日志日期 wrap 派生/切片摘要 --did 即合法/坑档触发词二期)。

**R2(2026-10-17 07:14)**: 用户指令「写入文档中」⇒ 对账发现 R1 答复的逐命令剩余步骤表(命令步/判断/条件/机械四列)未进文档 ⇒ 补录计划 §5.3(原 5.3/5.4 顺延),并声明该表为「机械 0」收录断言的数据源;doc-updated 抬至 26-10-17-0714。

**R3(2026-10-17 07:52)**: P1 骨架实施落地并验收全绿: 族登记表 `_common.FAMILIES`(三族单点, 词表/时间/命名全 import 既有单点, gen_tasks_index 本地 4 词表副本删除) · 三族模板(templates/plan.html·task.md·slice.md, SLOT 填空) · `kb.new` + `kb.wrap` 脚本经 add 协议落 .commands/kb(占位符解析实测通过) · `check_doc_templates.py` 守卫(冻结线 26-10-17-0736, 存量豁免)双处接线(kb.check + commit 门禁) · 守阵测试 7 条全绿(三突变红绿双验/冻结线精确到件/族登记与模板对账)。冒烟: 三族各真建一件(plan 10 处 SLOT 判红=守卫拦没填完, task 5 处 SLOT 判红, slice 零 SLOT 即过), 输出均含「机械 0」断言行; 冒烟落 /tmp 未提交已删。收口: test.full 全绿(数字只誊写进基线切片 `memory-bank/testing/baselines/26-10-17-0752-memory-bank-doc-pipeline-p1.md`, 裁定 A4); kb.check 全绿。计划 HTML 状态 Open→In Progress + §09 记 R3。范围守恒: P2/P3 未动(--refs 判拒留位); 任务档案未建(§08 待用户显式确认); cap 债务 3 项转告。踩坑: MSYS2 heredoc 反斜杠吞转(候选坑档, 触发词二期)。

**R4(2026-10-17 07:53):** 收尾: 计划 HTML 回写(status In Progress + §10 R3 + §07 P1 行标验收) · 基线切片落盘 · kb.index 重建 · kb.check 复绿(含回写守卫); 全部改动未提交, 等用户授权入库
