# 前端重复代码审查 · Phase 2 轮 20–23 收口（sharded JS / 抽屉族 / 三皮肤 CSS / 模板层）

> 摘要: 用户「执行重复代码审查计划 PHASE2: 26-10-10-2333-plan-dup-code-audit.html」→ 按计划 §07 拆 **15 个子轮**跑完 Phase 2 前端全部四个面（R20 shared/*.js 17449 行/35 文件 · R21 shared/drawer*/drawer_tpl* 8234 行/17 文件 · R22 三皮肤 CSS 8109 行/19 文件 · R23 shared/tpl 20 件 3967 行 + 三 index.html 632 行）。**纯审查零源码改动**，取证基线 `4eef60fe`。产出：**166 项发现（A71/B15/C48/D32）**，与 Phase 1 合并后**全局累计 322 项（A129/B30/C88/D75）**；滚动报告 `26-10-11-0033` 追加 §26–§30 五小节；入池 **17 条 issue（16 refactor + 1 test，族级合并）**。Phase 2 全部完成，主线剩 Phase 3（测试与横切 轮 24–25）+ Phase 4（汇总 轮 26）。
> 最后活动: 2026-10-22 03:26
**Refs:** memory-bank/tasks/26-10-20-frontend-dup-code-audit.md,memory-bank/reports/26-10-11-0033-report-dup-code-audit.html

## 已完成(单会话收口)

- **15 个子轮全部 Done**：R20-A~F（六面 69 项）/ R21-A~C（抽屉 34 项）/ R22-A~C（CSS 20 项）/ R23-A~C（模板 43 项）= **166 项**。
- **机器提名实测**：jscpd 5.4.1 `-f "javascript,css,markup"`（**该版本无 html 格式**，模板层只能靠结构线索 + 精读）全前端 **121 克隆 / 2525 重复行(6.56%)** = css 74(18.55%) / javascript 44 / markup 3。**CSS 是唯一被 jscpd 有效覆盖的面**（18.55% 全定位到三皮肤 views/dialogs 互克隆）；JS 字面克隆仅 3 处（全部落 R20-A），**其余 163 项 100% 来自结构线索 grep + 精读** —— 这个比例本身是本轮方法论的核心结论：单靠 jscpd 只能抓到 Phase 2 的 1.8%。
- **滚动报告** `26-10-11-0033` 已追加 §26(R20 六面) / §27(R21 抽屉族) / §28(R22 三皮肤 CSS) / §29(R23 模板层) / §30(Phase 2 汇总: 分类计数 + 主战果 + 30.2 A 类分布特征对比 + 30.3 候选排序 18 行 + 30.4 入池 issue 表 + 30.5 五条结论)；覆盖表补 R20–R23 五行；§2.1 补 jscpd 前端实测与格式可用性两行；§25 变更记录追加 `26-10-20-2232`。
- **17 条 issue 入池**（`create-issue`, type=refactor×16 + test×1, topic=dup-code-audit, 全部 Open 未认领），与 Phase 1 的「逐轮拆分 46 条/156 项」不同，**Phase 2 走族级合并（17 条/71 A 类项）**，便于一次改到底：
  - combobox 族 1 条（R20-B-05 + R20-C-12 + R21-A-04 + R23-A-01，JS 逻辑 5 处 + 模板骨架 5 处 + 设置页第 6 变体，`2230-refactor-fe-combobox-family-dup`）
  - 台账/骨架族 4 条：`config-default-ladder-dup`（三份"schema→默认值梯"互相嵌套）/ `config-entity-crud-dup` / `dialogs-js-boilerplate-dup`（mgr CRUD 5 + 面板加载 5 + POST+waitCmd 4）/ `dialog-shell-template-dup`（mask 手势 10 + title 头 11 + actions 栏 11）
  - 抽屉族 2 条：`drawer-fetcher-boilerplate-dup`（drawer_store 四 fetcher 同骨架）/ `drawer-variant-renderer-dup`（**dt07 与 dt08 除 CSS 前缀外逐字同** + peers 判据四件 3 份）
  - 模板族 4 条：`tpl-cell-fragment-dup` / `tpl-ctx-item-branch-dup`（`.ctx-item` 骨架 5 份）/ `tpl-list-row-empty-dup`（`.empty` 11 处）/ `tpl-switch-fold-seg-dup`（`.hb-switch` 7 处 + `hb-sub-toggle` 5 处）
  - CSS 族 2 条：`css-rule-family-dup` / `css-skin-token-layer-dup`（含 **R22-C-08 + R23-C-03 合并**：prism 无 dialogs.css 的同一事实两投影）
  - 横切 2 条：`overlay-geometry-dup`（浮层定位几何五处手写）/ `polling-family-dup`（长驻轮询启停第二份，抽屉侧缺 qb 侧已修的悬挂兜底）/ `single-point-bypass-dup`（单点已存在但被旁路的族）
  - 守阵 1 条（唯一 type=test）：**`2231-test-fe-tpl-shell-parity-guard`** —— 三 shell 的 sprite 段(80 行/67 symbol)与 login 段逐字相等目前**无守阵**，补两条断言即可让 CI 兜住，是本轮**唯一"只改测试不改源码"就能落地**的收益。
- `memory-bank/issues/_index.md` 已由 `gen_issues_index.py` 重建，`fe-` 前缀计数 17。
- **零改动确认**：`git status --porcelain` 只含 `memory-bank/` 路径，`src/` 与 `tests/` 为空。

## 关键结论(供后续执行参考)

- **①模板侧的重复要「守阵化」而非「合并」** —— 三 shell 的 manifest(74 行)已被守阵钉死 `diff` 相等，而 sprite(80 行/67 symbol) 与 login 段(31 行，仅差 1 行注释)未钉。合并唯一路径是后端渲染注入，会**破坏 `index.html` 静态直开能力**（能力回退），不可取。重复本身不可怕，无守阵的重复才可怕 → 全部建议改为「补齐守阵」。
- **②抽组件有 DOM 结构硬边界** —— cells 渲染器是多根片段、单元格必须是行容器**直接子元素**（grid 靠 `:nth-child` 列对齐 + `data-table` 双依赖），故 `m-dur`/`m-progress`/`tag-chip` 那几族**不能组件化**（会多包一层 wrapper 破坏列对齐），只能做「注释合一 + 纯 JS 算式抽单点」。Vue in-DOM `<template is>` 不支持片段复用，加剧了这一约束。
- **③R23-B 是 Phase 2 A 类密度最高的一段(9/23)** —— 原因是模板层此前已做过两轮大收敛（P1/P2/P3 表壳与 cells、W3/W4 抽屉头与流量控件），**残留同构件最集中**：收敛做过的面再复扫，命中率反而升高，说明"收敛完就该补守阵"，否则下一轮还会长回来。
- **④发现 4 处非风格重复的实质缺陷面**（价值高于纯重复）：
  - `R23-B-09` torrent 行 `.site-chip` 缺 `search-hit`，`torrents.html:8` 行级同缺 → **"种子页搜索时命中行不高亮"的跨文件功能遗漏**；
  - `R23-B-10` `aq-table` thead/grid 双分支**排序箭头口径相反**（每列都有箭头 vs 仅当前列），无注释；
  - `R23-B-13` drawer 四页签宿主的**合并态已数据驱动、非合并态仍硬编码字面量** → W4 收敛只做了一半的直接证据；
  - `R23-B-12` `hrGroupTitle` 单点已存在，但 ep 行**内联手写四层三元绕过它**。
- **⑤三皮肤 CSS 的结构性偏差**：atlas/console = `style.css → components → views → dialogs`；**prism 无 dialogs.css**（弹窗族被拆散进 components/views）→ **级联序与另两皮肤相反**。这不是遗漏而是历史选择，但它是 R22-C-08 / R23-C-03 至今反复被重新发现的根因 —— 入池时已合并成一条。
- **⑥CSS 是 jscpd 唯一高命中面，但收益最低** —— 74 克隆/18.55% 里绝大多数是三皮肤同源规则的必然投影（换肤本来就要求三份），真正可动的是「同一皮肤内部的规则族重复」，故筛选后 A 类只留 10 项（R22 全轮 20 项中）。

## 后续候选(未开工)

- **Phase 3 = 测试与横切（轮 24–25）**：`tests/` fixture/hepler 重复、conftest 分片、`scripts/` 与 `src/` 的口径重复。
- **Phase 4 = 汇总（轮 26）**：全局 322 项的重构候选排序总表（报告 §30.3 已有 Phase 2 部分 18 行雏形）+ 跨层「同一事实」总账（Phase 1 后端 ↔ Phase 2 前端同名/同义常量的对账）+ 未入池候选按清偿顺序决定。
- **Phase 2 的 17 条 issue：8 条已 Done（`2230-refactor-fe-combobox-family-dup` combobox 族 · `2231-test-fe-tpl-shell-parity-guard` 守阵 · `2231-refactor-fe-config-entity-crud-dup` 三骨架收敛 · `2231-refactor-fe-config-default-ladder-dup` 默认值梯 · `2231-refactor-fe-tpl-list-row-empty-dup` 列表外壳两件套 · `2231-refactor-fe-tpl-switch-fold-seg-dup` 模板小控件三件套 · `2231-refactor-fe-css-rule-family-dup` CSS 四规则族 · `2231-refactor-fe-drawer-fetcher-boilerplate-dup` 四 fetcher 唯一骨架），余 9 条 Open 未认领** —— 建议起手顺序：守阵族（零源码风险）→ 按 §30.3 排序取 A 族；`config-entity-crud-dup` 已给出「先写等价性断言再改」的模板（见 R2）。

**R1(2026-10-21 02:26):** 认领并修复 issue 26-10-20-2231(test-fe-tpl-shell-parity-guard): tests/test_webui_static_skins.py 新增 test_frontend_shell_sprite_login_parity —— 三份 shell sprite 段逐字相等 + #app+login 段注释归一后相等, 零源码改动; 红验三类突变(sprite 漂移红/login 标记漂移红/login 仅注释漂移绿)后精确还原, 三份 shell git diff 零改动; issue 置 Done, test.full 3966 passed + 10 skipped / TOTAL 99%(数字见基线切片 26-10-21-0225-dup-code-audit)

**R2(2026-10-21 03:11):** 认领并修复 issue 26-10-20-2231(refactor-fe-config-entity-crud-dup): config_editor.js 抽 cfgEntityAdd/Rename/Remove 三骨架 + cfgTrackerDef/RuleGroupDef/RuleDef 三份差异清单, config_hub.js 三处 promptDialog 包装合并为 hubAddEntity(def), 九处入口收敛; 连带删中间态 newXName×3/addOpen/cfgAddCancel/cfgTracker(name); 50 项等价性 harness 对 HEAD 版与改后各跑一遍均全绿(开发中抓出 _rules 后缀回归并修), issue 置 Done

**R3(2026-10-21 03:24):** 认领并修复 issue 26-10-20-2230(前端 combobox 族重复): 模板骨架 5 处收敛为独立分片 tpl/combo-input.html 的 #tpl-combo-input + 五处一行 aq-combo-input 调用(差异全参数化), 键盘导航 _comboKeydown 提为 comboKeydown(ctx, ev) 单点并补 IME 守卫, 40ms 合帧收层收敛为 _popBlurArm/_popBlurCancel(删两份拷贝), 四个守阵同步; 全量 pytest 3959 passed + 10 skipped(TOTAL 99.29%), dev.e2e 336 passed + 10 skipped, 新坑档 component-ref-ownership, 基线切片 26-10-21-0258-fe-combobox-family-dup

**R4(2026-10-21 03:25):** 认领并修复 issue 26-10-20-2231(refactor-fe-config-default-ladder-dup): schema→默认值梯三处收敛为 cfgDefaultScalar/cfgDefaultForFields 单点 + 插件侧 cfgDefaultForPlugin 分派, 行为等价性实证(真实 schema 25 插件 + 18 段 diff 为空), 新增守阵 test_frontend_config_default_ladder_single_point(形态六查 + node 语义电池 11 项), 红验三类突变后精确还原, test.full 3967 passed + 10 skipped / TOTAL 99%(基线切片 26-10-21-0323-dup-code-audit)

**R5(2026-10-21 04:46):** 认领并修复 issue 26-10-20-2231(refactor-fe-tpl-list-row-empty-dup, 台账 R23-A-05 + R23-B-06): 模板层两件套各收敛一份 —— 新增分片 tpl/list-shell.html 的 tpl-aq-row-pad / tpl-aq-empty + table.js 两组件 + app.js 注册 + 三 shell 清单挂载(aq-row-pad 落地为同组件挂两次, 占位须夹住 v-for 行; 行本身仍内联, 不碰逐行组件实例纪律), 四处三明治 8 个占位实例与十二处空态全部改挂(无图标的 4 处按语义补 hourglass/warn/inbox 且口径写进组件头注), 空态四层嵌套三元收敛为 filters.js::listEmptyText 单点 + 三视图 computed 薄壳并补回种子页缺失的索引构建分支; 新增守阵 test_frontend_list_row_pad_and_empty_single_point(形态查 + 活性探针 + node 语义电池 15 项), 红验 4/4 判红并修正活性探针被头注字样撑满的失效(计数前剥 HTML 注释); test.full 3968 passed + 10 skipped / TOTAL 99%

**R6(2026-10-21 05:05):** Phase 3 收口(轮 24-25): R24 tests/ 审查 25 项(A11/B5/C6/D3, 拆 A-D 四子轮, jscpd 112 克隆/1.30% + ast docstring 比对 56 文件漂移) + R25 跨层六主题面总账(全局累计 347 项); 入池 6 条(5 refactor+1 test); 零源码改动, 基线 cecbe4a9

**R7(2026-10-21 05:35):** 认领并修复 issue 26-10-20-2231(refactor-fe-css-skin-token-layer-dup): atlas :root 补 --font-ui/--font-display/--font-mono 三令牌(86→89, 与另两皮肤相等, 顺带修掉自己 4 处 var(--font-mono) 裸引用的静默失效); prism 新建 css/dialogs.css 把弹窗族从 components(313 行)/views(264 行) 按原全局序迁入, link 落 views 之后, 拆后 381/818/603 行; 守阵同轮对齐(单文件路径 5 处改聚合、inset:0 判据收窄、shell cap 214)+ 新增令牌名集相等与 prism 链接序两条守阵(均红验); 等价性静态赢家表 3526 条零变化 + 真浏览器 5 态像素 prism 全 0 差异 + test.full 3971 passed

**R8(2026-10-21 05:47):** 认领并修复 issue 26-10-20-2231(refactor-fe-drawer-fetcher-boilerplate-dup, 台账 R21-A-01): drawer_store 四份 fetcher 收敛为唯一骨架 _fetchDrawerSource + 顶层差异表 _DT_FETCH(端点/归一/目标状态键/空值形状 + loading 门/失败标记/通知时机), 四入口退化为单行薄壳, stale 判点 13→4; 等价性实证(37 项 node 电池对收敛前实现同绿) + 红验七类突变全红 + 抽屉域 11 份 e2e 64 绿; 新增守阵 test_drawer_fetcher_skeleton_single_point, 四处既有守阵同步到骨架/表; 数字见 kb.baseline

**R9(2026-10-22 01:49):** issue 26-10-20-2231-refactor-fe-tpl-ctx-item-branch-dup 认领并修复: ctx-menus.html 四支各一份 .ctx-item 骨架(5 份)合并为一条 ctxItems(ctxMenuKind()) v-for, 骨架 5 份→2 份; 三件守阵比对面搬到 ctxMenuKind() 单点; 全量 3994 passed/覆盖率 99.28%

**R10(2026-10-22 02:24):** 认领并修复 issue 26-10-20-2231(模板层单元格碎片): site-chip 3 份收敛为 #tpl-aq-site-chip 单点组件(三调用点, DOM 逐字同), torrent chip+torrents.html 行级补 search-hit(休眠绑定已取证), m-progress 四处抽 $root.progPct 单点, dur-body 注释跨文件互指; 全量与 e2e 实测数字见 kb.baseline(切片 26-10-22-0221-webui-site-chip-progpct-dup)

**R11(2026-10-22 03:26):** 认领并修复 issue 26-10-20-2231(fe-single-point-bypass-dup): 7 族单点绕过全部收敛 —— 提 cfgTruthy/aqbAuthHeaders/kibToBytes/bytesToKib/AQB_UNIT_LADDER/_fmtLadder/hrEpTitle 单点, 合并 cfgPathKey 第二份 path→key 单点, 11 处内联改调 + 单点处禁内联注释; 单位梯保留表格/图轴精度分歧(参数化), 阶梯核对无 KiB/KB 口径差; Bearer 取顶层函数护住 auth.js 单文件探针; test.full 与 e2e 三规格双绿(数字见基线切片 26-10-22-0324), 档案/契约/索引回写
