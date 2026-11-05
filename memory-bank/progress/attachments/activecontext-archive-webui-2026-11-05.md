# activeContext 切片归档 · WEB UI 界面与交互

> 摘要: 2026-11-05 activeContext 蒸馏轮逐字外迁的 25 条切片原文(2026-10-09~11-03, 详情面板/对话框单点化/flux 视觉/乐观 UI/e2e 修复)。
> 触发: WEB UI, 详情面板, flux, fx, 乐观 UI, e2e 修复, 切片归档
> 本文件为逐字归档(attachments 不计 cap); 蒸馏结论与指针写在各 progress 主题文件。
> 归档说明: 原文中的相对链接已因换目录统一补一级 ../, 其余逐字未改。
> 归档说明之二: 仅**行首的 Refs 声明行**改题为「切片原文」以免被知识库认领链解析误读(正文中的 `doc-refs`/`Refs` 键名保持原样); 链接路径已补一级 ../; 其余逐字未改。

---

<!-- slice: 26-10-09-1759-webui-shortcuts-toggle-suitability.md; 最后活动: 2026-10-10 08:56 -->

# WEBUI 快捷键「改为切换语义」适配性分析 → 「适合」6 条实施

> 摘要: 用户命题「分析快捷键中哪些适合改为切换类型(如 qB 流量图 —— 按一下打开、再按一下关闭), 写报告含适合/不适合表格」→ 报告 `reports/26-10-09-1731-report-webui-shortcuts-toggle-suitability.html` 判定注册表 59 条中 **6 适合 / 4 有条件 / 49 不适合**(准则 C1 界面显隐 / C2 关闭无副作用 / C3 键位语义单一 / C4 重复按下期望明确 / C5 有开关基础)。**2026-10-10 用户下令「实施适合的 6 条, 其余待定, 完成后状态置为 in progress」** —— 6 条**已落地**: 流量图 `Ctrl+\` / 统计 `\` / 历史 `Shift+\` / 详情面板 `I` / 帮助 `Shift+/` / 列选择器 `K` 由「只打开」升级为「开/关双态」。实现要点: **只改键盘 `run` 路径**(鼠标入口 —— 状态栏按钮/右键菜单/双击 —— 保持原语义); 抽屉类(流量图/详情)不在浮层屏蔽名单、第二按直达; 浮层类(统计/历史/帮助/列选择器)靠新增自切换白名单 `KB_SELF_TOGGLE_OVERLAY` 放行第二次按键(报告 §07.1)。4 条「有条件」与 49 条「不适合」**待定未实施**。
> 最后活动: 2026-10-10 08:56

## 状态

- 已完成: 6 条「适合」条目切换语义实施(`src/auto_qb/webui/static/shared/shortcuts.js`); 守阵 `tests/test_web_shortcuts.py` 新增 `test_shortcut_toggle_semantics` 并更新 3 处旧断言与「## 测试计划」清单; 全量测试绿(数字见 `commands run kb.baseline`); 任务档案 `tasks/26-09-28-webui-keyboard-shortcuts.md` 状态 `Done` -> `In Progress`。
- 未做: 4 条「有条件」(详情页签 `Alt+1~5` / `Enter` / 限速 `L` / 设置 `Ctrl+,`)与 49 条「不适合」按用户「其余待定」维持原状; 真机实弹走查(逐键实测)留给用户。
- 下一步(待用户拍板): 是否推进 4 条「有条件」条目 —— 详情页签 `Alt+1~5` 可补「同页签再按 ⇒ 关」升级为完整切换; `Enter` / `L` / `Ctrl+,` 报告建议保持现状(语义漂移 / 关闭丢输入 / 页面导航无关闭态)。

**Refs（切片原文）:** memory-bank/reports/26-10-09-1731-report-webui-shortcuts-toggle-suitability.html,memory-bank/tasks/26-09-28-webui-keyboard-shortcuts.md,memory-bank/testing/baselines/attachments/26-10-09-1759-webui-shortcuts-toggle-suitability.md,memory-bank/testing/baselines/attachments/26-10-10-0856-webui-shortcuts-toggle-suitability.md

---

<!-- slice: 26-10-10-2103-webui-selection-trigger-parity.md; 最后活动: 2026-10-10 22:45 -->

# WEBUI 选中 × 触发 一致性(作用域契约 + 触发点登记表 + 静态守阵)

> 摘要: 用户动议「WEBUI 加强选中与触发不一致的测试/守阵/运行时检查, 可以重构底层使其更易被检查, 后续添加的功能可以自动停靠, 而不是添加新的检查」, 举例「选中 A 触发 B / 无选中触发 C / 选中 A 触发全部」; 明确**暂时没发现相关 BUG**, 先出计划。计划 26-10-10-2001(专题 `webui-selection-trigger-parity`)已出并拍板(采纳推荐: C5 取口径甲 / S1+S2 先行 / S3 单独一轮 / S6 延后 / 审计开关不同步进 flags)。**S1+S2 已落地并提交(e4282642)**; **S3 已落地**: descriptor 单点 `selection.js::_scopeResolve`(R1–R7 + V1 全部收编, R1/R2 两套选中展开收敛为同一 descriptor 的 `keys/hashes` 与 `closure` 两字段) + M3 拆借道(`menu.hash` 写入点清零, `actTorrent/exportTorrent/torrentCmd/copyTorrentInfo/delTorrent` 增显式 hash 形参缺省回落菜单)。**实施期修正**: 出口重签名(3 个 `_dispatch*`)降级为保留既有出口形状 —— 载荷已是 descriptor 投影, 重签名与「e2e 逐位一致」约束冲突, 见计划 §9 R3。实测: test.full 3111 passed / 4 skipped / TOTAL 99%(基线 26-10-10-2245); dev.e2e 全量 136 passed / 10 skipped 与改前逐位一致。
> 最后活动: 2026-10-10 22:45

## 正在进行

- **S3+S4+S5 已完成**(S3: descriptor 单点 + M3 拆借道; S4: 运行时审计环 `scope_audit.js` + T6 守阵 + 三出口接线; S5: e2e 参数化矩阵 `trigger-scope.spec.mjs` + 读环辅助 `scope_ring.mjs` + 手势上移 `gestures.mjs`)。**三张网闭合**: 静态守阵 T1–T6 / 运行时审计(默认关, e2e 断言环净) / 真浏览器矩阵(`test:e2e:fast` 64 passed)。剩余: S6 菜单项集声明化(§8 拍板延后, 待评估); S1–S5 随本专题入库。
- e2e 矩阵(S5, 用户列的四类场景参数化)与 S4 是剩余两张网; S6 菜单项集声明化延后(§8 拍板)。

## 关键结论(供后续触发点/动作入口改动参考)

- **现状把「动谁」拆在 7 个目标解析点 + 7 个动作出口 + 1 个平行变体判定上**(计划 §1 两张取证表), 互不引用 —— 这是口径漂移的结构性原因, 不是某个函数写错。四条机制: ①两套判定并行(菜单变体由 `_ctxMulti`/`_ctxScopeKey` 判, 动作目标由 `_bulkTargets`/`_groupTargets`/`menu.*` 算); ②优先级相反(鼠标锚点优先 vs 键盘选中优先, 同一屏同一选中集合给出不同答案且都不提示); ③**借道菜单状态**(键盘把解析出的 hash 写进 `this.menu.hash` 再调菜单绑定方法, 二者耦合); ④两套「选中展开」(`_bulkTargets` 组 key 优先覆盖成员 vs `selHashSet` 全量展开, 「N 个目标」含义不同)。
- **C5(本轮拍板的口径)**: **仅当选中集合为空时, 锚点与光标才有资格当目标**。选中非空时锚点只能**改变选中**, 不能静默改变作用对象 —— 除非该触发点在登记表里显式声明 `scope: 'anchor'`。取「口径甲」(保持既有「选中 N 项右键 = 对全部生效」语义, 但菜单上明示作用范围), 不动已拍板的 CTX-03。
- **登记表的两张表分工**(`shared/triggers.js`): `ui` 描述**触发点**(id/ui/variant/entry/scope/dispatch), `calls` 描述**投递调用点**(file/fn/ep/scope/why)。**豁免也登记**(`scope: "none"` 必须写 why) —— 白名单会越长越宽直到失去意义, 而每行都要写理由的表加宽成本可见。
- **T1 的判据必须是 `method: "POST"` 而不是端点字符串**(本轮实施期修正): reannounce 的逐目标投递端点是拼接变量, 只认字面量会留盲区; 改判动词后覆盖面从 11 处扩到 30 处。**连带坑**: 登记表自己的文件头注释就含这个词, 不把 `triggers.js` 排除出扫描面会把自己扫成表外项(首次跑就命中了)。
- **T4 只能按「动作族」比对, 不能按「逐项集合」**: 四支项集本就按形态允许不同(整集支没有限速/移动/导出), 逐项比对恒红。归族后判据 = 四支都必须有基线四族(开始/暂停/汇报/删除), multi/member/group 还必须各有扩展六族(重新校验/跳检/限速/移动/标签分类/导出) —— 正好覆盖 2026-10-09「单组右键菜单缺选项」那类回归(红验③复现即判红)。
- **登记表落成 mixin 片段而非裸数据**: 现有守阵要求 `shared/` 下每个片段都被清单引用, 且定义了 `window.X` 的必须被注入(`app.mixin`) ⇒ 表经 `window.AQB_TRIGGERS.triggerDefs()` 暴露。**prism 的 shell 已在 210 行硬顶**, 加一行须先从别处腾一行(本轮去掉一处多余空行)。
- **上游同域改动 `727b72e2`(非活跃种子禁强制汇报)是 C4「出口自检」的先例**: 其 `_guardReannounce`(判「允不允许」) 与 `reannouncePlan`(判「发给谁」) 是刻意分开的两层, 不可互相替代; 且它实证了「**详情面板不经 `_actCore`**」这条旁路(机制 3 的活例) —— 已登记为 `panel.cmd` / `drawer.js::torrentCmd`, 并在口径文档 §6 引用。
- **e2e 断言多目标动作要按 hash 落, 不要数请求条数**(上游同域结论, 与本专题同源): 选中行可能同属一组而被展开为整组成员(桩 300 种子/150 组, 两行必同组), 条数随分组形态变。计划 S5 的矩阵沿用这一口径。

## 后续候选(未开工, 已识别)

- `rules/actions/transfer.py::ReannounceAction` 只跳 `is_stopped`(不跳排队/校验中/错误), 与 qB 口径不一致 —— 见上游档案「后续候选」, 属另一入口, 不在本专题范围。
- 计划 §8 的 Q1/Q2: descriptor 是否序列化进日志(暂不做)、选中集合是否需要上限或二次确认(不属本轮, 由用户决定是否入池)。

---

<!-- slice: 26-10-14-0204-webui-detail-classic-removal.md; 最后活动: 2026-10-14 02:44 -->

# 26-10-14-0204-webui-detail-classic-removal — 四内容页签经典 UI 与流量页签变体移除

> 摘要: 用户令「移除种子详情面板除『流量』页的 4 个经典 UI, 以及『流量』页的除经典外的 UI, 以及 qb 流量页的除经典外的 UI」; 二次确认选定**彻底删除经典渲染**档。终态 = 四内容页签(常规/Tracker/用户/内容)**变体独档**(缺省 = 该页签首个变体), 流量页签(含 qB 全局/分组挂点)**经典独档**。删除面: `drawer_tabs.js` 四组件 + `tpl/drawer-tabs.html` + 三个经典单元格渲染器 + 经典三表注册(drawerTracker/drawerPeer/drawerFile)/六个 columns computed/六个 state 排序字段/`drawerTrackerRows`/`fileRowSelect`/`renameFileRow`/`drawerSelPath` + 流量变体 13/14/15 + 图前/图后双宿主 + 注册表 `slot`; 档制判据收成 `CLASSIC_TABS/defaultSel/choices` 单点(全层无 `|| CLASSIC` 字面量), 渲染失败兜底改回该页签缺省档, 流量页签模板菜单因候选 < 2 不再弹; 三皮肤死 CSS 清 ~144 条。守阵 6 个 pytest 函数 + 7 份 e2e spec 同轮改写。代价(用户拍板接受): 内容页「重命名…」随经典消失; 兜底不再有第二实现。档案 [26-10-14-webui-detail-classic-removal](../../tasks/26-10-14-webui-detail-classic-removal.md); 基线 [26-10-14-0244](../../testing/baselines/attachments/26-10-14-0244-webui-detail-classic-removal.md)。
> 最后活动: 2026-10-14 02:44

**Refs（切片原文）:** memory-bank/tasks/26-10-14-webui-detail-classic-removal.md,memory-bank/testing/baselines/attachments/26-10-14-0244-webui-detail-classic-removal.md,memory-bank/activeContext/26-10-06-0751-webui-detail-panel-design.md

> ⚠ 末项 `memory-bank/activeContext/26-10-06-0751-webui-detail-panel-design.md` 已于 2026-10-19 随 activeContext 清理删除(已归档), 原文见本归档对应小节; 未改指到不存在的文件。

## 下一步

1. 无强制后续。可选: 变体 10/11/12 侧补「重命名」入口(内容页功能回补, 单独立项)。
2. 旧存值自愈已验证(`readSel` 白名单): 四页签存 `"classic"`、流量页签存 `13/14/15` 一律回落缺省档。

---

<!-- slice: 26-10-19-2020-webui-site-alerts.md; 最后活动: 2026-10-19 22:44 -->

# webui-site-alerts

> 摘要: 站点健康 + 逐目标回执已落地(计划 S0-S7 Done); 观感返工也已完成 —— 站点问题改走 chip 底色、图标只留命令结果(26-10-19-2206 计划 Done), 两槽方案作废
> 最后活动: 2026-10-19 22:44

**Refs（切片原文）:** memory-bank/plans/26-10-19-2007-plan-webui-site-alerts.html, memory-bank/tasks/26-10-19-webui-site-alerts.md, memory-bank/plans/26-10-19-2206-plan-webui-site-chip-color.html

**R0(2026-10-19 20:20):** grilling 四轮收口(11 项拍板), 落地站点列提醒与逐目标汇报回执的实施计划 S0-S7

**R1(2026-10-19 21:24):** S0-S7 实施完成: 统一 tracker 健康取数器 + 站点 chip 两槽图标 + 逐目标回执; 计划转 Done, 已立档

**R2(2026-10-19 22:08):** 站点 chip 观感返工: grilling 15 问收口, 出改色表达计划 26-10-19-2206(Open, 未实施)

## 本轮结论

- 四条 WEBUI 待办(种子出错 / tracker 报错 / 缺站点配置 / 汇报部分失败不可定位)收敛到**一个锚点**: 站点 chip 内两个图标槽 —— 左槽持久健康(`site_alert`: `no_site_conf` / `tracker_error`), 右槽临时命令结果(`alertIcons`: pending / ok / warn / error)。判定与取数全在后端单点, 前端只消费字符串与符号。
- **取数统一**: `refresh_error_reasons` 改造为 `refresh_tracker_health` —— 一次 `/trackers` 调用同时喂 `tracker_error_msg`(状态列原因)与 `tracker_health_msg`(站点健康), `ERROR_REASON_BUDGET` 退役; 预算 20/轮 + 四档 TTL(600 / 30 / 60 / 300)+ 墙钟去抖 30s。
- **S0 真机标定**: 生产 qB 5.2.3 / 151 种子库, 单连接 keep-alive 连发 50 次 → 均值 0.38ms / P95 0.53ms; 20 条/轮 ≈ 7.5ms = 1.5s tick 的 0.5%, 远低于 R2 的 5% 触发线 ⇒ 预算与 TTL 按计划原值定死, **不触发线程化**。
- **回执**: `check_pending` 聚合带出 `truth.results`(逐 hash 结论), 前端按它把结果落到行上; truth 缺失统一落 warn, 不谎称成功。聚合 toast 文案逐字不变。

## 下一步

- **站点 chip 改色返工已完成**(计划 `plans/26-10-19-2206-plan-webui-site-chip-color.html` Done): 站点问题走 chip 底色(缺配置橙+虚线 / 报错红), 图标只留命令结果并固定放文字后; 档案 `tasks/26-10-19-webui-site-chip-color.md`。
- 第一阶段已收口; **第二阶段**(全局汇总徽章: 顶栏/状态栏「N 个问题种子」+ 点击切筛选; 缺配置 chip 跳转站点页)按 D11 另立计划件, 尚未排期。
- 真机走查(可选): 在生产实例观察一轮真实 tracker 报错 → chip 变色/恢复即灭的节奏是否与 30s/60s 口径一致。

**R3(2026-10-19 22:44):** 站点 chip 改色返工实施完成(S0-S5): 站点问题走 chip 底色(缺配置橙+虚线/报错红), 图标只留命令结果且固定放站点名后; 守阵与 e2e 重写并双向红验, 全量测试见 kb.baseline

---

<!-- slice: 26-10-20-1224-webui-pinned-first-cell-selected.md; 最后活动: 2026-10-20 13:27 -->

# webui-pinned-first-cell-selected

> 摘要: 修 WEBUI 三主表选中行必显列异色竖带: 选中态用半透明 tint 替换了行底(承光层变页底 --bg), 与吸左首格按 --bg-row 合成分家(真浏览器逐像素 Δ9/255 atlas、5/255 prism, 未选中行 Δ0); 三皮肤改为「同色 linear-gradient 叠 --bg-row」与首格同一表达式, 成员行拆出保持裸柔底; 静态 + e2e 双守阵(修后 Δ0/1), 全量 pytest 与 e2e @fast 全绿
> 最后活动: 2026-10-20 13:27

**R0(2026-10-20 12:24):** 修 WEBUI 三主表选中行必显列异色竖带: 选中态用半透明 tint 替换了行底(承光层变页底 --bg), 与吸左首格按 --bg-row 合成分家(真浏览器逐像素 Δ9/255 atlas、5/255 prism, 未选中行 Δ0); 三皮肤改为「同色 linear-gradient 叠 --bg-row」与首格同一表达式, 成员行拆出保持裸柔底; 静态 + e2e 双守阵(修后 Δ0/1), 全量 pytest 与 e2e @fast 全绿

## 用户诉求

上一轮(切片 webui-pinned-first-cell-hover)修完悬停闪竖带后遗留的一条: 「选中的行必显列背景与其它列不一致」。
修完后用户又追加「group 一同修」—— 把同族最后一条半透明状态(组行展开)也收掉。

## 本轮过程

1. 开工同步: `commands run my-commit-flow.sync` 快进 `5ce3e295 → 4eef60fe`。
2. 真浏览器像素探针(Playwright 截图 + PIL 取色, 脚本 `tmp-analysis/probe-selected.mjs`): 三主表 × 双皮肤 ×
   四态(plain / expanded / selected / selected-hover), 首格与相邻格取**同相对位置**的像素。
3. 反解承光层: 相邻列可见底 ≈ `--bg`(atlas #0e1218 / frost #f2f6fb), 首格 ≈ 局部 `--bg-row` ⇒
   选中态两侧合成基色分家。
4. 三皮肤 views.css 把 `.group-row.selected/.partial` 从「裸半透明 tint(替换行底)」改为「tint 叠
   `--bg-row`(层叠)」—— 与首格镜像同一个表达式; `.member-row` 拆出保持裸柔底(无吸左首格、底由
   `.detail` 的 `--bg-sunken` 承光)。
5. 守阵: 静态 `test_frontend_pinned_first_cell_selected_row_keeps_base`(三皮肤/两态/末层 --bg-row/同 tint
   字面) + e2e `main-table-pinned-selected.spec.mjs`(三主表 × 双皮肤, 真手势 Ctrl+click 后行板 backgroundColor
   不透明 + 行板与首格 color/image 逐字相等, 含悬停); 两者均红绿双验。
6. 顺带修订既有守阵 `test_sel_visual_parity_and_site_cell`: 它钉的是「成员行与组行**同一条规则文本**」,
   与「组行要合成、成员行不要」的新结构冲突 —— 改钉「同一 tint 令牌 + 同吃左色条规则」。

## 关键事实

- 主表行板的真实承光底是**页底 `--bg`**, 不是 `--bg-row`: 行底被状态规则替换后, 露出的就是页底。
- 残差量级: 选中行 atlas Δ9/255、prism Δ5/255(整列高, 可辨); 未选中行 Δ0。修后 prism Δ0、atlas ≤1(取整)。
- 同族残差: expanded 原本 Δ5(atlas)/2(prism)(低于可辨阈, R0 未动) —— **R1 已同口径收掉**, 修后 Δ0;
  console 另有 `.group-row.expanded:hover` 覆盖, 同样要叠底(否则悬停展开行那一下又分家)。
- 选中瞬间不会错拍: 行板 `transition: background` 看似把 image 层纳进过渡, 实测两侧 `background-image`
  同帧出现(36/38ms, 0 帧不一致, 探针 `tmp-analysis/probe-select-transient.mjs`)。
- 抽屉变体面用 `.sel/.is-chk/.bad/.err`、不用 `.selected` ⇒ 本次主表规则不影响按面重锚(dt_table.css)。

## 产出

- `src/auto_qb/webui/static/{prism,atlas,console}/css/views.css`(三皮肤同改)
- `tests/test_webui_static_skins.py`(新守阵 + 模块测试计划清单)、`tests/test_web_shortcuts.py`(口径修订)
- `e2e/main-table-pinned-selected.spec.mjs`(新 e2e, 6 例)
- `memory-bank/pitfalls/web-ui/frozen-column.md` ⑩(半透明状态底是叠加不是替换)

**R1(2026-10-20 13:27):** 用户「group 一同修」⇒ 收掉同族最后一条半透明状态: 组行展开 .group-row.expanded 原本裸用 --bg-sunken(下沉底替换行底), 辅种页实测 Δ5/255 atlas、2/255 prism; 三皮肤改「同色 linear-gradient 叠 --bg-row」(prism views.css / atlas·console components.css), console 独享的 .group-row.expanded:hover 同款; 新增静态守阵 test_frontend_pinned_first_cell_expanded_row_keeps_base + e2e 展开行用例(辅种/追剧 × 双皮肤), 两侧红绿双验; 途中撞 CSS 700 行 cap(atlas components.css 702 行) —— 行数测量用 PowerShell Get-Content 少计 51 行所致, 已用行内注记把文件拉回 700 并给坑档记复发

---

<!-- slice: 26-10-21-0341-webui-css-rule-family-shared.md; 最后活动: 2026-10-21 03:41 -->

# webui-css-rule-family-shared

> 摘要: 认领并修复 issue 26-10-20-2231: 三皮肤逐字节相同的四族 CSS 规则(35 条)收敛进 shared/console_hub.css 单点(三皮肤合计 −324 行), 三皮肤真差异(drawer-tabs 激活态令牌/HR 徽章底形/副行字体)按口径留皮肤内并原位注明; 守阵新增 _ui_css_effective 改量生效面 + 底形族反向断言(两支红验); 等价性=生效规则表 59 条逐条同; test.full 与 dev.e2e 双绿
> 最后活动: 2026-10-21 03:41

**R0(2026-10-21 03:41):** 认领并修复 issue 26-10-20-2231: 三皮肤逐字节相同的四族 CSS 规则(35 条)收敛进 shared/console_hub.css 单点(三皮肤合计 −324 行), 三皮肤真差异(drawer-tabs 激活态令牌/HR 徽章底形/副行字体)按口径留皮肤内并原位注明; 守阵新增 _ui_css_effective 改量生效面 + 底形族反向断言(两支红验); 等价性=生效规则表 59 条逐条同; test.full 与 dev.e2e 双绿

---

<!-- slice: 26-10-21-0607-webui-busy-skeleton.md; 最后活动: 2026-10-21 06:07 -->

# webui-busy-skeleton

> 摘要: 认领修复 issue 26-10-20-2231 完成: dialogs/config_hub 手抄 19 处 busy 骨架收敛为 dialogs.js 三单点(_mgrRun/_panelLoad/_postWaitCmd), tmShutdownTool 特例保留; triggers.js calls 表四处 POST 旧登记并为统一出口一行; 新守阵 busy_skeleton_single_point 两支红验; test.full 与 dev.e2e 双绿, 数字见基线切片 26-10-21-0605
> 最后活动: 2026-10-21 06:07
**Refs（切片原文）:** memory-bank/tasks/26-10-21-webui-busy-skeleton.md

**R0(2026-10-21 06:07):** 认领修复 issue 26-10-20-2231 完成: dialogs/config_hub 手抄 19 处 busy 骨架收敛为 dialogs.js 三单点(_mgrRun/_panelLoad/_postWaitCmd), tmShutdownTool 特例保留; triggers.js calls 表四处 POST 旧登记并为统一出口一行; 新守阵 busy_skeleton_single_point 两支红验; test.full 与 dev.e2e 双绿, 数字见基线切片 26-10-21-0605

---

<!-- slice: 26-10-21-1410-webui-dialog-shell-single-point.md; 最后活动: 2026-10-21 14:10 -->

# webui-dialog-shell-single-point

> 摘要: 修复落地: 三段式外壳收敛 aq-modal/aq-modal-head + 管理对话框 mgrDef 合并 + modalDetailRows 并一(复制钮 value===0 边界修复); 守阵单点化+红验三类; test.full 3978+2 全绿(基线切片 26-10-21-1408) + e2e 336+10 全绿; issue 置 Done
> 最后活动: 2026-10-21 14:10

**R0(2026-10-21 14:10):** 修复落地: 三段式外壳收敛 aq-modal/aq-modal-head + 管理对话框 mgrDef 合并 + modalDetailRows 并一(复制钮 value===0 边界修复); 守阵单点化+红验三类; test.full 3978+2 全绿(基线切片 26-10-21-1408) + e2e 336+10 全绿; issue 置 Done

---

<!-- slice: 26-10-30-0630-webui-optimistic-ui.md; 最后活动: 2026-10-30 07:48 -->

# webui-optimistic-ui

> 摘要: 专题完结: 乐观 UI 扩面(rename 乐观补丁+速度切预翻转)实施收口并置 Done(计划 26-10-30-0610 / issue 26-10-01-2137); 真机复测两链延迟阻塞(测试实例不可达); SSE 断轮询延迟已独立入池 26-10-30-0626(暂不修)
> 最后活动: 2026-10-30 07:48

**R0(2026-10-30 06:30):** grilling 两轮+真机实测定稿: 认领 issue 26-10-01-2137(复验分岔: add ~34ms 已覆盖不改码; rename ~1.7s 与主备速度切 0~1.5s 立项); 追加实测 SSE 断退回轮询 ~1.19s 归因用户观察, 独立入池 26-10-30-0626-perf-webui-sse-down-poll-latency(暂不修)

**R1(2026-10-30 07:48):** S1/S2/S4/S5 实施收口: 4 提交落地 rename 乐观补丁+速度切预翻转, 全量实测见 kb.baseline 最新一条(切片 26-10-30-0746); 计划 26-10-30-0610 与 issue 26-10-01-2137 均置 Done; 真机复测两链延迟阻塞(测试实例 @36595 不可达, 记录于计划 §10 R2)

---

<!-- slice: 26-10-31-0331-webui-rename-rollback-drawer-detail.md; 最后活动: 2026-10-31 03:31 -->

# webui-rename-rollback-drawer-detail

> 摘要: 认领并修复 issue 26-10-30-0818: commands.js 新增 _syncDrawerRollback 两条回滚出口对称覆盖 drawer.detail + editRename 回填 op.prev 兜行不在视图; rename 四态电池加 7 断言(25/25), test.full 全绿(基线 26-10-31-0331); issue 置 Done
> 最后活动: 2026-10-31 03:31

**R0(2026-10-31 03:31):** 认领并修复 issue 26-10-30-0818: commands.js 新增 _syncDrawerRollback 两条回滚出口对称覆盖 drawer.detail + editRename 回填 op.prev 兜行不在视图; rename 四态电池加 7 断言(25/25), test.full 全绿(基线 26-10-31-0331); issue 置 Done

---

<!-- slice: 26-11-02-0342-webui-fx-r6-check-relocation.md; 最后活动: 2026-11-02 03:42 -->

# webui-fx-r6-check-relocation

> 摘要: 精修轮 R6(F7f): D4-6 快勾误归类纠正 -- 行首勾标退役, 转落真实 checkbox(flux 全部可见面 CSS-only, hb-switch 排除) + showcase 归位 D5(makeCtl); Playwright 18/18; test.full 4806 全绿切片 26-11-02-0340
> 最后活动: 2026-11-02 03:42
**Refs（切片原文）:**

**R0(2026-11-02 03:42):** 精修轮 R6(F7f): D4-6 快勾误归类纠正 -- 行首勾标退役, 转落真实 checkbox(flux 全部可见面 CSS-only, hb-switch 排除) + showcase 归位 D5(makeCtl); Playwright 18/18; test.full 4806 全绿切片 26-11-02-0340

**R1(2026-11-02 03:42):** 精修轮 R6(F7f): D4-6 快勾误归类纠正

---

<!-- slice: 26-11-02-0451-webui-relocate-free-space-race.md; 最后活动: 2026-11-02 04:51 -->

# webui-relocate-free-space-race

> 摘要: 认领修复 issue 26-11-02-0413: test_relocate_volume_free_ancestor_fallback 桩 disk_usage(存在回固定free/不存在抛FileNotFoundError)消两次采样断言竞态; 定向2过+整文件31过, 全量见 kb.baseline; issue 置 Done
> 最后活动: 2026-11-02 04:51
**Refs（切片原文）:**

**R0(2026-11-02 04:51):** 认领修复 issue 26-11-02-0413: test_relocate_volume_free_ancestor_fallback 桩 disk_usage(存在回固定free/不存在抛FileNotFoundError)消两次采样断言竞态; 定向2过+整文件31过; issue 置 Done

**R1(2026-11-02 06:20):** 全量直跑 4812过/11红(1519s, 机载~15x): 8 junction族(本shell junction Target被改写落沙箱, 直接探针实证环境性)+2端口(他agent harness占口)+1耗时预算; 与本改动零因果(零src改动); 全量未绿不产新基线; 未提交(用户: 不推远端, ship.commit无免推路径)

---

<!-- slice: 26-11-02-0525-webui-state-color-progress-bar.md; 最后活动: 2026-11-02 05:25 -->

# webui-state-color-progress-bar

> 摘要: 种子状态色拆分 + 进度条改为行状态色: 四皮肤新增 --st/--st-soft 令牌段(7 kind, 校验中 --warn/移动中 --violet), 图例/芯片/行文字/进度条 18 处消费点改读变量; 新增静态守阵第 19 项 + e2e 进度条计算色断言; 数字见 kb.baseline
> 最后活动: 2026-11-02 05:25
**Refs（切片原文）:**

**R0(2026-11-02 05:25):** 种子状态色拆分 + 进度条改为行状态色: 四皮肤新增 --st/--st-soft 令牌段(7 kind, 校验中 --warn/移动中 --violet), 图例/芯片/行文字/进度条 18 处消费点改读变量; 新增静态守阵第 19 项 + e2e 进度条计算色断言; 数字见 kb.baseline, 基线切片 26-11-02-0524

**R1(2026-11-02 05:25):** 见基线切片

---

<!-- slice: 26-11-02-0553-webui-flux-message-surface.md; 最后活动: 2026-11-02 10:31 -->

# webui-flux-message-surface

> 摘要: flux 消息弹窗统一(用户报「强制汇报投递与确认框样式不一致」): 把提示条从 console fork 的平面方角老配方改到弹窗同一套 glass 语言 —— 切角(--hb-cut 10/14 同族) + 同一 --msg-surface 单点 + 语义档 --msg-tone/--msg-line 变量表; 顺手补上 warn 档(21 处调用点此前整档没有样式, 与 info 同貌)与 .modal.tone-warn/error 描边染色; 新增守阵 _scan_message_surface_parity 扫模板图标映射+JS 调用点求 kind 全集(红验四形态), test.full 见 kb.baseline 最新切片。后续十轮把提示条收敛成「两行排版 + 队列重排 + 两段式事件消息」, 十一轮修倒计时条按 id 归属(失败回执条进度条走完却不消失)
> 最后活动: 2026-11-02 10:31
**Refs（切片原文）:**

**R0(2026-11-02 05:53):** flux 消息弹窗统一(用户报「强制汇报投递与确认框样式不一致」): 把提示条从 console fork 的平面方角老配方改到弹窗同一套 glass 语言 —— 切角(--hb-cut 10/14 同族) + 同一 --msg-surface 单点 + 语义档 --msg-tone/--msg-line 变量表; 顺手补上 warn 档(21 处调用点此前整档没有样式, 与 info 同貌)与 .modal.tone-warn/error 描边染色; 新增守阵 _scan_message_surface_parity 扫模板图标映射+JS 调用点求 kind 全集(红验四形态), test.full 见 kb.baseline 最新切片

**R1(2026-11-02 06:27):** 二轮: 用户否决「消息通知切角」—— .toast 去掉 clip-path 回方角(材质/语义档不动, 弹窗仍保留 14px 切角), 守阵第 20 项由「要求切角」改「禁止切角」反向钉(红验一次); 另开 showcase D9「消息通知形状/边标」挑选区(6 候选: 切角否决对照/方角纯描边/左侧 3px 色条/顶部 2px 通栏/色条+淡底/微圆角 2px, 每卡 ok·warn·error 三档, 复用演示·选定·导出), 桩服务 8452 已起; test.full 见 kb.baseline 最新切片, 形状最终档待用户选定

**R2(2026-11-02 06:45):** 三轮: 用户暂定 D9-1(方角纯描边 = 生产现状)并指定复刻 showcase D6 的图标样式 —— 提示条图标改成「圈内字形族」(18px 圆环 + 圈内单形 / stroke 2 / 一档一形), 落 flux/css/views.css 的 @supports(mask) 段: color:transparent 藏旧 sprite 字形 + mask 画形 + background-color 取 --msg-tone(不碰四皮肤共享的模板/sprite, 不支持 mask 时降级保留原字形); 守阵第 20 项追加每档 --msg-ico 断言(漏一张 = 实心色块, 红验一次); 挑选台 D9 样例图标同步成同族并标注 D9-1 暂定选定; test.full 见 kb.baseline 最新切片

**R3(2026-11-02 07:01):** 四轮: 用户指定「文字内容排版样式也用 showcase D6-2 倒计时进度条例子的样式」—— 生产提示条改成标题+明细两行排版(13/600 标题 + 12/--fg-muted/400 明细, 图标 flex-start 顶对齐, 固定宽 340): components.css 的 .toast 基座(顶对齐/600/宽高padding/overflow) + views.css 的 .toast-txt/.toast-t/.toast-s(components 卡 700 行 cap) + 新增 flux/fx-mount.js::shapeToastText 在挂载层把模板那一条 span 按纯结构规则拆两段(动作短语≤14字 : 剩余≥6字, 不满足即单行, 单行靠 600 字重读作标题), 共享模板零改动; 守阵第20项追加三组排版断言+拆段器 JS 断言(红验四形态); 挑选台 D9 六卡样例同步排版; test.full 见 kb.baseline 最新切片

**R4(2026-11-02 07:24):** 五轮: 用户指出『The torrent file is already in the list』要用中文 + 都改主标题+说明 —— ①挑选台 D9 六卡 18 条样例全改中文并统一两行(row(tone,icon,head,sub): 已强制汇报/3 个种子·tracker 已受理、部分目标已受理/2 个推迟到最小间隔后重报、添加种子失败/该种子已在列表中); ②生产拆段器分隔符集 [：:] → [：:，,] —— 生产里『状态, 补充』句式占大头, 只认冒号会让这批条停单行; ③约定文档同步; test.full 见 kb.baseline 最新切片

**R5(2026-11-02 07:51):** 七轮: 用户选「改文案」—— 把生产 58 处提示条文案统一成「主标题: 说明」(14 个 shared/*.js; 无分隔符的回执都补说明句, 例如 已导出 .torrent → 已导出: .torrent 文件已保存 / 未作修改 → 未作修改: 输入与当前值一致 / 限速需为非负数字(KiB/s) → 限速值无效: 需为非负数字(KiB/s)); TOAST_SPLIT 说明门槛 6→2 字(文案统一后说明常是名字/计数); 新增守阵第21项 _scan_toast_copy_two_part 扫 toast( 与 _finishToast( 两个入口(终态文案在第3参); 三条既有断言随文案同步(test_web_shortcuts x2 / test_webui_static_dom_panel x1 / e2e menus W4 导出回执), e2e 实跑通过(prism/atlas 两皮肤); test.full 见 kb.baseline 最新切片

**R6(2026-11-02 08:21):** 八轮: 用户报「强制汇报的两个窗口(已投递/回执)没有统一且互相重叠, 按 D6-3 队列重排 FLIP 做」+「通知挡住了状态栏, 上移」—— ①两态统一: 等待/已投递文案压成标题+一行说明(76px→59px), 措辞统一到菜单名「强制重新汇报」, 删除前置汇报的等待/完成同步措辞; ②队列重排 FLIP: fx-mount.js 新增 flipStack(), toastSync/toastDrop 双钩, 视口坐标测位置(先 cancel 自己的 WAAPI 动画), 邻居进出补 transform、自身高度变化补 height; RM 降级; ③位置: .toast-wrap bottom 20px → calc(var(--statusbar-h)+12px), 与 .err-panel 同族; 守阵第 20 项加两条(状态栏令牌 / flipStack 至少两处), 红验通过; e2e site-alerts 命令结果图标 2 皮肤通过; test.full 见 kb.baseline 最新切片

**R7(2026-11-02 09:12):** 九轮: 用户报「强制汇报第一个消息窗口被第二个顶掉, 仅显示不到1秒, 没有做到队列重排」—— 时间线取证坐实: 八轮把回执做成同一条原位改字, 投递条只活 531ms 就被换内容, 队列里从头到尾 n=1。改法: ① 拆两条事件消息(投递条 busy 起步 → 回执到来归档成 info「已投递」留在队列 4s, 回执另起 toast; reToast 句柄提到 try 外 + _settleDeliveredToast 900ms 最短展示, catch 也收口; 投递文案不写「等待中」); ② 队列推入不叠画: 新增 fx-toast-queue-in 关键帧 + [data-fx-queue] 规则(从下方一整格起步 + 90ms 延迟 backwards), 栈内新条由 toastSync 盖章 —— 否则 FLIP 反成重叠来源(逐帧实测重叠 5 帧/49px → 0 帧); ③ toastSync 加 settleId 与模板 :data-id, 结算条的倒计时按 id 精确补挂; 守阵第20项 +5 条(红验五形态); 约定文档「提示条栈」段整段改写 + 新坑档 toast-queue-pushin-overlap; e2e site-alerts 回执断言改 expect.poll 等回执条落定; test.full 见 kb.baseline 最新切片

**R8(2026-11-02 09:47):** 十轮「统一收」: 把九轮只做在强制汇报上的两段式推广到全部常驻等待条 —— 新增统一工厂 _runningToast + 结算 _settleRunningToast(归档成 info 留队列 4s + 结果另起一条), 覆盖 5 条链路(强制汇报/删除前置汇报/导出/批量跳检/转移), 取代 _settleDeliveredToast; 归档条文案统一改为归档后仍成立(已投递/已开始/已提交, 去掉进行中/正在/等待 tracker 确认); 投递本身抛错不拆(原位落失败); 守阵第20项三判据(sticky 只许出现在工厂体内/归档文案禁进行时/settle 调用点下限10), 红验三形态; 两条探针补桩(转移 vm 的 _runningToast+lastToast 取结果条, 删除链 RA_BASE 空桩); e2e menus 12 passed(导出/限速/删除确认框); 转移链路因桩服务无目标未端到端实测; test.full 见 kb.baseline 最新切片

**R9(2026-11-02 10:31):** 十一轮: 用户报「强制重新汇报失败的窗口时间指示条到了但没消失」—— 时间线取证(桩 8137 + Playwright): 结果条 --fx-life=4000(应 12000), 动画 t=5106ms finished, 节点 t=13013ms 才移除, 中间 8s 干挂。根因 = toastSync 的 **stamp 分支**用整栈共用 ttl 给新节点挂 data-fx-cd: _settleRunningToast 同 tick 先发归档条 4000、再推结果条 12000, 两份 $nextTick 按注册序执行 ⇒ 4000 落到结果条上; 结果条自己那次调用已 stamp ⇒ 只走补挂分支, 而补挂只认 settleId(本次没传)。九轮修了"补挂"一侧, stamp 一侧是同一类错的另一半。改法: toastSync(ttl, id) 先算 own=data-id===id(缺 id 退化栈尾兜底), stamp 与补挂合并成唯一一处 `if (own && ttl > 0)`; toast() 补传第二参 id(此前漏传)。守阵第20项 +3 判据(own 守卫存在 / data-fx-cd 全文件唯一 / ui_feedback 两处 toastSync 都带 id), 红验一次; 约定文档 ⑤ 整条改写 + 新坑档 toast-countdown-ttl-misattributed; 浏览器复验 5 场景(两段式 error/ok、单条 error、sticky、真实 _actCore 链路); test.full 见 kb.baseline(26-11-02-1031 切片)

---

<!-- slice: 26-11-03-0033-webui-ctx-src-target-marker.md; 最后活动: 2026-11-03 00:33 -->

# webui-ctx-src-target-marker

> 摘要: 右键目标行标识改四皮肤静态实心 outline 框(绕过 row_lang box-shadow 归零/左条与选中条同色), 新增静态守阵与基线切片
> 最后活动: 2026-11-03 00:33
**Refs（切片原文）:**

**R0(2026-11-03 00:33):** 右键目标行标识改四皮肤静态实心 outline 框(绕过 row_lang box-shadow 归零/左条与选中条同色), 新增静态守阵与基线切片

---

<!-- slice: 26-11-02-2033-webui-flux-overlay-opacity.md; 最后活动: 2026-11-03 01:01 -->

# webui-flux-overlay-opacity

> 摘要: 新增 --bg-pop 不透明浮层底: flux 自有 12 处浮层换值 + shared 7 处 html[data-fx-preset] 覆盖, 另三皮肤补惰性别名; 根因=flux 表面令牌带 alpha 且毛玻璃预算仅 4 处; 口径回写 webui.md 与 overlays.md
> 最后活动: 2026-11-03 01:01
**Refs（切片原文）:** memory-bank/tasks/26-11-02-webui-flux-overlay-opacity.md

**R0(2026-11-02 20:33):** 新增 --bg-pop 不透明浮层底: flux 自有 12 处浮层换值 + shared 7 处 html[data-fx-preset] 覆盖, 另三皮肤补惰性别名; 根因=flux 表面令牌带 alpha 且毛玻璃预算仅 4 处; 口径回写 webui.md 与 overlays.md

**R1(2026-11-03 01:01):** 找回 flux 弹窗毛玻璃(回归): 根因=26-11-02 消息面统一把 .modal 底从 --bg-card(.82) 换成 --bg-elev(.92), blur(14px) 声明仍在但仅剩 8% 透视; 修法=--msg-surface 拆角色底 --msg-base(.modal-mask 回落 --bg-card/提示条仍 --bg-elev) + .modal 补 -webkit- 前缀; 守阵新增 _scan_flux_modal_frost(双向钉弹窗 blur+半透明底 / --bg-pop 不透明 + 八类无 blur 浮层); 口径回写 webui.md 与 overlays.md

---

<!-- slice: 26-11-03-0102-webui-remove-row-hover-bar-and-fx-flash.md; 最后活动: 2026-11-03 01:02 -->

# webui-remove-row-hover-bar-and-fx-flash

> 摘要: 移除四皮肤 hover 行左条与 flux fx-row-flash; test.full 4900 passed/10 skipped/99%
> 最后活动: 2026-11-03 01:02
**Refs（切片原文）:**

**R0(2026-11-03 01:02):** 移除四皮肤 hover 行左条与 flux fx-row-flash; test.full 4900 passed/10 skipped/99%

---

<!-- slice: 26-11-03-0227-webui-dur-pad-rowheight.md; 最后活动: 2026-11-03 02:53 -->

# webui-dur-pad-rowheight

> 摘要: 修做种时间格 padding 撑高整行并扩到四皮肤守阵: 四皮肤去 padding 改线偏移 + 静态/几何双守阵(SKINS_ALL 四皮肤) + 真机复验 + 全量基线切片
> 最后活动: 2026-11-03 02:53
**Refs（切片原文）:** memory-bank/testing/baselines/26-11-03-0252-e2e-skins-all-geometry.md, memory-bank/pitfalls/web-ui/dur-cell-padding-rowheight.md

**R0(2026-11-03 02:27):** 修做种时间格 6px padding 撑高整行: 四皮肤去 padding 改线偏移 + 静态/几何双守阵 + 真机四皮肤复验 + 全量基线切片

**R1(2026-11-03 02:53):** e2e 行高几何守阵扩到四皮肤: harness.mjs 新增 SKINS_ALL, views.spec 几何 describe 改数据驱动遍历四皮肤; 定向 e2e 4 皮肤全绿; 全量 test.full 实测 4908 passed/10 skipped; 新建基线切片 26-11-03-0252; 同步 smoke.md/browser-env.md 的 harness 口径

---

<!-- slice: 26-11-03-0821-webui-ctx-menu-e2e-existing-red.md; 最后活动: 2026-11-03 08:21 -->

# webui-ctx-menu-e2e-existing-red

> 摘要: 修复 e2e 右键菜单既有红：按产品注册表与 data-item 改正三条过时 spec(定制块 20 行/两个 has-sub/hover 锁定静态更多操作)；产品零改动，定向 e2e 全绿
> 最后活动: 2026-11-03 08:21
**Refs（切片原文）:**

**R0(2026-11-03 08:21):** 修复 e2e 右键菜单既有红：按产品注册表与 data-item 改正三条过时 spec(定制块 20 行/两个 has-sub/hover 锁定静态更多操作)；产品零改动，定向 e2e 全绿

---

<!-- slice: 26-11-03-0821-webui-drawer-window-firstbeat-converge.md; 最后活动: 2026-11-03 08:21 -->

# webui-drawer-window-firstbeat-converge

> 摘要: 修复 e2e 大表既有红：窗口引擎三处接线修正(容器 vh/抽屉 gap 首拍收敛/行高实测过滤与补拍) + dt11 过时期望改正；定向 e2e 全绿，全量测试通过
> 最后活动: 2026-11-03 08:21
**Refs（切片原文）:**

**R0(2026-11-03 08:21):** 修复 e2e 大表既有红：窗口引擎三处接线修正(容器 vh/抽屉 gap 首拍收敛/行高实测过滤与补拍) + dt11 过时期望改正；定向 e2e 全绿，全量测试通过

---

<!-- slice: 26-11-03-0852-webui-drawer-rowafter-dead-hook.md; 最后活动: 2026-11-03 09:24 -->

# webui-drawer-rowafter-dead-hook

> 摘要: 认领并修复 issue 26-11-03-0802: 桥表 @vue:mounted 改传页签 key(tab)给 dtRowAfter, 与 dtBridgeDef 契约对齐; 新增静态+node 双面回归守阵, 定向测试与全量测试全绿
> 最后活动: 2026-11-03 09:24
**Refs（切片原文）:** memory-bank/issues/26-11-03-0802-bug-drawer-rowafter-dead-hook.html, memory-bank/testing/baselines/26-11-03-0910-webui-drawer-rowafter-dead-hook.md

**R0(2026-11-03 08:52):** 认领并修复 issue 26-11-03-0802: 桥表 @vue:mounted 改传页签 key(tab)给 dtRowAfter, 与 dtBridgeDef 契约对齐; 新增静态+node 双面回归守阵, 定向测试与全量测试全绿

**R1(2026-11-03 09:24):** 验证收口: 定向抽屉/布局/表格与知识库守卫全绿, test.full 通过(数字见基线 26-11-03-0910), issue 置 Done 并重建索引

---

<!-- slice: 26-11-03-0454-webui-search-uncovered-dedup.md; 最后活动: 2026-11-03 11:42 -->

# webui-search-uncovered-dedup

> 摘要: 修复 issue 26-11-03-0254: filteredGroups 渲染期用未过滤 this.groups 现算 groupedNow + 「不在命中集 / 已归组」两道闸(排 facet/push 之前); 静态守阵按语义位置 + 三皮肤 4 场景 e2e; 全量见 kb.baseline; issue 置 Done
> 最后活动: 2026-11-03 11:42
**Refs（切片原文）:**

**R0(2026-11-03 04:54):** 修复 issue 26-11-03-0254: filteredGroups 渲染期用未过滤 this.groups 现算 groupedNow + 「不在命中集 / 已归组」两道闸(排 facet/push 之前); 静态守阵按语义位置 + 三皮肤 4 场景 e2e; 全量见 kb.baseline; issue 置 Done

**R1(2026-11-03 10:54):** 补住 CI 收集期 BASE_URL 导出缺失: spec 改 baseUrl() + 新增 e2e 回潮守阵; test.full 4936 passed/2 skipped, e2e 定向 18/18

**R2(2026-11-03 11:42):** 同轮抬 e2e 预算(dev.e2e 2700s / playwright job 40m)并补坑档; site-alerts 全量顺序污染入池 test/standard Open

---

<!-- slice: 26-11-01-0026-webui-write-side.md; 最后活动: 2026-11-01 00:26 -->

# webui-write-side

> 摘要: 修复完成: _verdict_reannounce 消解等待模型(②废除/③″新增/④′扩{4,5,6}), 单测矩阵语义重写, 真机 RM09-04 四态全验+RM09 整片 10/10, test.full 全绿(见 kb.baseline, 基线切片 26-11-01-0025); 回写 effect-confirmation(复发+1)/real-machine §2.14/issue Done
> 最后活动: 2026-11-01 00:26

**R0(2026-11-01 00:26):** 修复完成: _verdict_reannounce 消解等待模型(②废除/③″新增/④′扩{4,5,6}), 单测矩阵语义重写, 真机 RM09-04 四态全验+RM09 整片 10/10, test.full 全绿(见 kb.baseline, 基线切片 26-11-01-0025); 回写 effect-confirmation(复发+1)/real-machine §2.14/issue Done

---

<!-- slice: 26-11-01-0910-webui-add-torrents-sync-lag.md; 最后活动: 2026-11-01 09:10 -->

# webui-add-torrents-sync-lag

> 摘要: 认领修复 issue 26-10-30-0626: 归因由「SSE 掉线/轮询」改为「qB add 是四跳异步管线 + 命令后补刷新太早(距 add 返回 0.5~0.8ms)」, 按候选 A 落地 store 有界追平(80ms × ≤3 次, TTL 3s) + 命令线登记回执 hash + 主循环提前同步线; 真机 N=6/N=12 零 1.5s 簇(24~129ms, 修复前 22%/44%), 全量测试见 kb.baseline; issue 置 Done
> 最后活动: 2026-11-01 09:10
**Refs（切片原文）:** memory-bank/issues/26-10-30-0626-perf-webui-sse-down-poll-latency.html,memory-bank/testing/baselines/26-11-01-0910-webui-add-torrents-sync-lag.md

**R0(2026-11-01 09:10):** 认领修复 issue 26-10-30-0626: 归因由「SSE 掉线/轮询」改为「qB add 是四跳异步管线 + 命令后补刷新太早(距 add 返回 0.5~0.8ms)」, 按候选 A 落地 store 有界追平(80ms × ≤3 次, TTL 3s) + 命令线登记回执 hash + 主循环提前同步线; 真机 N=6/N=12 零 1.5s 簇(24~129ms, 修复前 22%/44%), 全量测试见 kb.baseline; issue 置 Done

---

<!-- slice: 26-11-02-0345-webui-large-filelist-perf.md; 最后活动: 2026-11-02 23:54 -->

# webui-large-filelist-perf

> 摘要: 调研取证: 抽屉 content 变体/引擎桥/后端 files 端点/主表现状走读 + 外部方案调研, 报告落盘 26-11-02-0339
> 最后活动: 2026-11-02 23:54
**Refs（切片原文）:**

**R0(2026-11-02 03:45):** 调研取证: 抽屉 content 变体/引擎桥/后端 files 端点/主表现状走读 + 外部方案调研, 报告落盘 26-11-02-0339

**R1(2026-11-02 03:46):** 调研取证: 抽屉 content 变体/引擎桥/后端 files 端点/主表现状走读 + 外部方案调研, 报告落盘 26-11-02-0339

**R2(2026-11-02 07:08):** 报告 26-11-02-0339 + 计划 26-11-02-0351 + W1-W5 串行实施(千级 DOM 1001→45-48, longtask 归零, 主表 3000 种子复测全绿) + 基线 26-11-02-0707(4824 过/99.00%); 遗留: W6/D1/D3 待拍板、真机轨待 token; 工作区未提交(用户未授权)

**R3(2026-11-02 08:29):** 用户验收轮(3000 种子桩): 切标签页/关抽屉后卡死数秒且能滚不能点 —— 根因=columns.js _measureRowH 行高签名混入 viewMode(切页全表作废退全量量齐)+_winCtnSync 抽屉离场过渡期宽度假 bump(作废主表行高); 两守卫修复后 8.4s/5.6s longtask→0(主线程饿死假象, 非遮罩); 新守阵 e2e/window-invalidation 6 条+静态 1 条, 三皮肤千级 e2e 28/28

**R4(2026-11-02 11:25):** 认领并修复 issue 26-11-02-0902: 千级首访估算开窗+渐进量齐(ROW_WIN_EST_MIN 1000 / _rowHAvgOf 全局均值), 3000 行首访 longtask 8432ms→97ms、gBR 3310→55 次; perf.spec 千级档判据分档(粗界/不塌陷), 3000 档 10 passed; 新增坑档 est-cold-start-vs-absolute-threshold; 工作区未入库(用户未授权)

**R5(2026-11-02 12:51):** 阈值二轮调优 1000→200(拐点实测 250ms 线落 150~200 之间, 与 ROW_WIN_MIN 合并); 空档1 首访路径指纹用例+空档2 单测边界断言补齐并双负向验证; 滚到底估算档改按比例禁塌陷; e2e 199/200/300 三档+test.full 全绿, 基线 26-11-02-1248

**R6(2026-11-02 21:28):** 复测 drawer-tab-switch-lag: 同步 e8d6279c, 对照对方 5e351c4b 首访估算开窗, 同桩同路径不复现(31-77ms/0 longtask), issue 置 Done

**R7(2026-11-02 22:47):** W6 测量先行: W6a 现状 142-153ms→乐观写 16.5-19.6ms(建议做), W6b payload 127911B/裁剪省≈1.3ms(建议 Dropped), D1/D2/D3 已回填计划 §06, 真机轨待 QBT_TEST_* token; 服务端/前端代码零改动, 计划与档案保持 In Progress

**R8(2026-11-02 23:54):** W6a 实施+验收(单测2+e2e6); W6b 拍板 Dropped; 真机环境1 RM08-09 千文件; 全量 4896 passed

