# 26-10-20-frontend-dup-code-audit — Phase 2 前端重复代码审查(执行档案)

**Status:** Done
  
**Added:** 2026-10-20
  
**Updated:** 2026-10-20
  
**Topics:** dup-code-audit
  
**Summary:** 重复代码审查计划(`plans/26-10-10-2333-plan-dup-code-audit.html`)的 **Phase 2 = 前端(轮 20–23)** 执行档案。Phase 1 后端已全完(156 项 A58/B15/C40/D43, 46 issue 入池, 见 `tasks/26-10-10-backend-dup-code-audit.md`)。Phase 2 实测规模(~~36.4k 行)远超单轮 4000 行硬上限, 按计划 §07 拆 **15 个子轮**: R20-A~~F(shared JS 六面) / R21-A~~C(抽屉族) / R22-A~~C(三皮肤 CSS) / R23-A~C(模板+index) +  consolidated S5 归档。取证基线 HEAD `4eef60fe`, 取证时间 `26-10-20-2108`, **全程纯审查零源码改动**。
  
**Refs:** memory-bank/reports/26-10-11-0033-report-dup-code-audit.html,memory-bank/activeContext/26-10-20-2233-dup-code-audit.md,memory-bank/issues/26-10-20-2230-refactor-fe-combobox-family-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-config-default-ladder-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-config-entity-crud-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-css-rule-family-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-css-skin-token-layer-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-dialog-shell-template-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-dialogs-js-boilerplate-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-drawer-fetcher-boilerplate-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-drawer-variant-renderer-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-overlay-geometry-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-polling-family-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-single-point-bypass-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-tpl-cell-fragment-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-tpl-ctx-item-branch-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-tpl-list-row-empty-dup.html,memory-bank/issues/26-10-20-2231-refactor-fe-tpl-switch-fold-seg-dup.html,memory-bank/issues/26-10-20-2231-test-fe-tpl-shell-parity-guard.html

> **收口(26-10-20-2233)**: 15 子轮 + S5 归档全部完成 —— Phase 2 **166 项 A71/B15/C48/D32**, 与 Phase 1 后端 156 项合并后**全局累计 322 项 A129/B30/C88/D75**; 17 条 issue 入池(16 refactor + 1 test, 族级合并)均 Open 待认领; 全程纯审查零源码改动(`src/` 与 `tests/` 空), 取证基线 `4eef60fe`。续跑看计划 §Phase 3(轮 24–25)→ Phase 4(轮 26)。

## 子轮切分(按 §07 拆轮)

| 子轮    | 面                         | 文件(行数)                                                                                                                                                              | 状态               |
| ----- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| R20-A | 表格视图面                     | table·dt_table·columns·view·sort·shows·filters·decorate·selection                                                                                                   | Done             |
| R20-B | 交互控件面                     | dialogs·menu·ctx_menu·ctx_menu_custom·ui_feedback·triggers·delete_flow·add_torrent                                                                                  | Done             |
| R20-C | 配置编辑面                     | config_editor(1405)·config_hub(1456)·config_rules(315)                                                                                                              | Done             |
| R20-D | 运行时骨架面                    | app(954)·state(561)·boot(133)·lifecycle(380)·polling(271)·commands(980)                                                                                             | Done             |
| R20-E | 领域页面                      | hr(358)·hr_status(677)·qb_traffic_chart(1094)                                                                                                                       | Done             |
| R20-F | 横切支撑                      | auth·shortcuts·fetch_low·scope_audit·traffic_card·format                                                                                                            | Done(随 R20-C 补核) |
| R21-A | 抽屉底座                      | drawer(1500)·drawer_head(35)·drawer_store(359)·drawer_templates(885)                                                                                                | Done             |
| R21-B | 抽屉页面 general+trackers     | drawer_tpl/01–05(2028)                                                                                                                                              | Done             |
| R21-C | 抽屉页面 peers+content+bridge | drawer_tpl/06–12·90(2953)                                                                                                                                           | Done             |
| R22-A | CSS 令牌与主题层                | tokens·base·themes·style.css·theme.js                                                                                                                               | Done             |
| R22-B | CSS 组件层                   | 三套 components.css                                                                                                                                                   | Done             |
| R22-C | CSS 视图与对话框层               | 三套 views.css + dialogs.css                                                                                                                                          | Done             |
| R23-A | 模板上半                      | dialogs(137)·dialogs-mgr(284)·move-dialog(62)·popovers(367)·ctx-menus(178)·topbar(235)·statusbar(81)·dock(10)·groups(63)·torrents(29)·shows(90)·overlays(49) = 1585 | Done             |
| R23-B | 模板下半 | settings-detail(520)·xtpl(381)·xtpl-cells(356)·traffic-card(317)·settings(317)·drawer(242)·xtpl-cells-dt(192)·drawer-head(59) = 2384 | Done |
| R23-C | 三套 index.html 骨架          | atlas(208)·console(212)·prism(212) = 632                                                                                                                            | Done             |
| S5    | 归档                        | 滚动报告追加 s26+ · issue 入池 · 档案/切片回写 · kb.index                                                                                                                         | Open             |

机器提名基线(jscpd 5.4.1, `-f "javascript,css,markup"`, 全前端): **121 克隆 / 2525 重复行(6.56%)**; css 74 克隆(18.55%, 主战场=三皮肤互克隆), javascript 44 克隆(字面重复极低, 仅 3 处 —— 与后端同结论: 主战场在结构线索+精读), markup 3 克隆。

## 发现台账(七字段: 位置 / 类别 / 重复对象 / 分歧点 / 维护风险 / 建议收敛形态 / 预估收益风险)

### R20-A 表格视图面(6 项: A3/C2/D1)

**R20-A-01** · 排序比较器两份逐字同

- 位置: `shared/sort.js:161-169`(`sortedGroups` 内 sort) ↔ `shared/filters.js:254-262`(`filteredTorrents` 内 sort)
- 类别: A
- 重复对象: 组排序比较器(同名 key 提取 + 大小比较 + 0 兜底)逐字相同
- 分歧点: 无(逐字同)
- 维护风险: 改排序口径(如加"置顶组优先")必改两处, 漏一处则筛选视图与主表顺序不一致
- 建议收敛形态: sort.js 暴露 `compareGroups(a,b)` 单点, filters.js 删除内联份改调用
- 预估收益/风险: 收益中(消 1 维护点); 风险低(纯函数, 有既有视图测试可守)

**R20-A-02** · 面筛谓词 7 支逐字同

- 位置: `shared/filters.js:204-211`(未归组分支) ↔ `shared/hr.js:270-279`(`_memberPass`)
- 类别: A
- 重复对象: 七个"成员是否通过当前面筛"的谓词(逐条件同口径)
- 分歧点: 无(逐字同)
- 维护风险: 新增筛选项(如按 HR 状态筛)要同步两处; HR 视图与主表筛结果不一致属用户可见 bug
- 建议收敛形态: 收敛为 `memberPasses(member, filters)` 单点(hr.js 或 filters.js 任一), 两侧 import
- 预估收益/风险: 收益中高; 风险低-中(两侧调用方上下文不同, 收敛时需回归两视图)

**R20-A-03** · 面筛字段清单三处

- 位置: `shared/filters.js` `clearFilters` / `filtersActive` / `facetsActive` 三函数内各列一遍筛选项键
- 类别: C
- 重复对象: "当前有哪些面筛键"这一事实的三份表示
- 分歧点: 三处清单目前一致, 但无单点约束
- 维护风险: 加/改筛选项漏一处 → 清除不净/激活态错算/facets 计数漂移
- 建议收敛形态: 提 `FILTER_KEYS` 常量数组单点, 三处改引用
- 预估收益/风险: 收益中; 风险低(数据驱动)

**R20-A-04** · REANNOUNCE_BLOCKED_STATES 跨层常量

- 位置: `shared/decorate.js`(`REANNOUNCE_BLOCKED_STATES`) + 后端同族
- 类别: C
- 重复对象: "哪些状态禁止重新做种"这一事实的前端表示(后端已登记 R16-C03)
- 分歧点: 前后端各持一份(当前值一致)
- 维护风险: 后端加状态忘改前端 → 前端放行后端拒绝(或反之)
- 建议收敛形态: 登记待轮 25 跨层总账收口; 前端可考虑从 schema/常量接口取
- 预估收益/风险: 收益中(跨层); 风险中(涉及接口改动, 需单独拍板)

**R20-A-05** · Shift 连选两份逐字同

- 位置: `shared/selection.js:353-363`(`shiftMemberSel`) ↔ `shared/selection.js:390-400`(`shiftTorrentSel`)
- 类别: A
- 重复对象: 11 行 shift 区间选择逻辑(锚点→当前项→区间全选)逐字相同, 仅 list 来源不同
- 分歧点: 无(逐字同)
- 维护风险: 修 shift 边界 bug(如空列表/锚点失效)要改两处
- 建议收敛形态: 提 `shiftSelect(list, anchorIdx, curIdx, selSet)` 纯函数, 两处传不同 list
- 预估收益/风险: 收益中; 风险低(同文件内收敛, 调用点清晰)

**R20-A-06** · 表格族既有收敛轮产物

- 位置: `shared/table.js`·`dt_table.js`·`columns.js`
- 类别: D
- 重复对象: 三文件形状相似(列模型/渲染助手)
- 为何不动: 已有两轮收敛(计划 26-10-11-1722 / 26-10-13-0811)处理过, 当前残留是刻意分层(主表/明细表/列模型), 合并反而模糊边界
- 预估收益/风险: 不动

### R20-B 交互控件面(12 项: A5/C3/D4)

**R20-B-01** · mgr CRUD busy+try+toast+finally 骨架 5 处

- 位置: `shared/dialogs.js` `submitMgrCategory:112`·`submitMgrTags:132`·`mgrEditCatPath:149`·`mgrDeleteCategory:169`·`mgrDeleteTag:183`
- 类别: A(族)
- 重复对象: `if (mgrBusy) return` → `mgrBusy=true` → try{api+toast(ok)+loadMgr()} → catch{!e.auth toast(error)} → finally{mgrBusy=false}, 五处同构
- 分歧点: 各处 payload/文案/确认框不同, 骨架相同
- 维护风险: 改回执等待期语义(如加超时/取消)要五处同改; `!e.auth` 过滤逻辑漏一处则 401 时弹错 toast
- 建议收敛形态: 提 `mgrSubmit(fn, {okMsg, errMsg})` 包装器吞掉骨架
- 预估收益/风险: 收益中高(5 处); 风险低-中(包装器要保留各处差异参数)

**R20-B-02** · 面板加载骨架 5 处

- 位置: `shared/dialogs.js` `loadStats:25`·`loadMgr:91`·`loadLogs:414`·`loadSpeedMode:435`·`loadHistory:602`
- 类别: A(族)
- 重复对象: `xLoading=true; xError=""; try{api+装配} catch{!e.auth xError=...} finally{xLoading=false}` 五处同构
- 分歧点: 各面板数据装配不同; loadSpeedMode 带 force 参数
- 维护风险: 加载态/错误态口径漂移(如某处忘记 finally 复位 → 面板永久转圈)
- 建议收敛形态: 提 `panelLoad(key, loader)` 或统一 `withLoading(state, fn)` 助手
- 预估收益/风险: 收益中高; 风险低

**R20-B-03** · POST+waitCmd+三态 toast 骨架 4 处

- 位置: `shared/dialogs.js` `_metaBulk:282`·`submitSpeedOverride:452`·`toggleAltSpeed:555`·`submitAltLimits:573`
- 类别: A(族)
- 重复对象: POST 命令 → 轮询/等待回执 → 成功/失败/超时三态 toast + busy 管理, 与后端族 `webui-route-cmd-boilerplate-dup` / `webui-bulk-receipt-boilerplate-dup` 同族
- 分歧点: 各命令 payload 与成功判据不同
- 维护风险: 回执等待超时值/取消语义四份; 改三态文案口径要四处同改
- 建议收敛形态: 提 `postCmdAndAwait(path, body, {onOk,onErr,onTimeout})` 单点(与后端收敛 issue 对齐命名)
- 预估收益/风险: 收益高(前后端各一半); 风险中(回执时序敏感, 需回归三条命令路径)

**R20-B-04** · Esc 关闭链两处同步

- 位置: `shared/dialogs.js:531`(`escBusy`) ↔ `shared/lifecycle.js`(Esc 链)
- 类别: C
- 重复对象: "当前有弹窗/忙态时 Esc 归属"这一事实的两处表示(注释已声明需同步)
- 分歧点: 无(注释声明同口径)
- 维护风险: 加新弹窗层忘同步 → Esc 关错层或双关
- 建议收敛形态: Esc 优先级链提为数据表(层名→优先级)单点
- 预估收益/风险: 收益中; 风险中(键盘路径回归面大)

**R20-B-05** · combobox 键盘导航三处同骨架

- 位置: `shared/add_torrent.js:271-294`(`_comboKeydown`)·`shared/add_torrent.js:447-465`(`onAddPathKeydown`)·`shared/dialogs.js:391-410`(`onMetaCatKeydown`)
- 类别: A(族)
- 重复对象: IME 守卫 → ↑↓ 移动 activeIdx(取模环绕) → Enter 选中 preventDefault → Esc 关闭, 三处同构
- 分歧点: 各 combobox 数据源与关闭语义不同
- 维护风险: 键盘可访问性口径(如 IME 守卫漏一处 → 中文输入法下误触发)三处
- 建议收敛形态: 提 `comboKeydown(getCtx, ev)` 通用键盘导航助手(消费方注入 items/activeIdx/onPick/onClose)
- 预估收益/风险: 收益中高; 风险低-中(纯交互, 可手工回归)

**R20-B-06** · 40ms 合帧失焦收层两份

- 位置: `shared/add_torrent.js:403-413`(`addPopBlurClose`) ↔ `shared/dialogs.js:368-374`(`metaCatBlurClose`)
- 类别: A
- 重复对象: blur 后 setTimeout 40ms 再关层(给 mousedown 抢先机会), 两份同构
- 分歧点: 无实质分歧(关闭的目标层不同)
- 维护风险: 合帧时延值两份; 改策略(如改 60ms / 用 pointerdown)要两处同改
- 建议收敛形态: 提 `blurCloseLayer(closeFn, delay=40)` 单点
- 预估收益/风险: 收益小-中; 风险低

**R20-B-07** · comboHoverIdx kind→键映射两份

- 位置: `shared/add_torrent.js`(`comboHoverIdx` 及同类助手)
- 类别: C
- 重复对象: "kind(域名/路径/标签…)→ 数据键名"映射表两份表示
- 分歧点: 两处当前一致
- 维护风险: 加新 kind 漏一份 → 悬停高亮取错数据
- 建议收敛形态: 提 `COMBO_KEYS` 常量单点
- 预估收益/风险: 收益小; 风险低

**R20-B-08** · 视口边距字面量 6 处

- 位置: `shared/ui_feedback.js`(toast/确认框/菜单定位, 8px 边距 6 处)
- 类别: C
- 重复对象: "浮层距视口边缘留 8px"这一事实的 6 份字面量
- 分歧点: 无(值相同)
- 维护风险: 调整浮层贴边策略要数 6 处; 漏一处浮层会贴边/出界
- 建议收敛形态: 提 `VIEWPORT_MARGIN = 8` 常量(同族延伸: `config_hub.js:709-745` hubAsk 用 12px —— 见 R20-C-14)
- 预估收益/风险: 收益小; 风险低

**R20-B-09** · 两级溢出判定注释分歧

- 位置: `shared/menu.js`(`_subOverflowsRight` ↔ `_menuOverflowsRight`)
- 类别: D
- 重复对象: 两个"是否溢出右缘"判定形状相似
- 为何不动: 源码注释已声明两处**故意**不同(子菜单与主菜单的翻转基准不同), 属记录在案的分歧, 非疏漏
- 预估收益/风险: 不动(注释即文档)

**R20-B-10** · 开层惯用式 5 处

- 位置: `shared/menu.js` 及 ctx 菜单族(开层前关他层 + 状态置位序列)
- 类别: D
- 为何不动: 五处开层序列各自治管不同层集合, 抽公共函数要传 4+ 参数才能表达差异, 合并后可读性下降; 且已有 Esc 链统一收敛路径
- 预估收益/风险: 不动(防过度抽象)

**R20-B-11** · 注册表/登记表数据声明

- 位置: `shared/ctx_menu.js`·`ctx_menu_custom.js`·`triggers.js`
- 类别: D
- 为何不动: 三者是声明式数据(菜单定义/触发器登记), 形状相似属数据范式非代码重复; 合并成一张大表反而丢可读性
- 预估收益/风险: 不动

**R20-B-12** · bulkDelete 内联成员展开 ↔ \_deleteMembers

- 位置: `shared/delete_flow.js:54-65`(`bulkDelete` 内联) ↔ `shared/delete_flow.js:93-106`(`_deleteMembers`)
- 类别: A
- 重复对象: 12 行"展开选中集合为成员 hash 列表(含去重/跳过空)"近逐字同
- 分歧点: 无实质分歧
- 维护风险: 改成员展开口径(如含/不含暂停种)两处; 内联份在 bulkDelete 里容易被后来者再抄一遍
- 建议收敛形态: bulkDelete 删内联份, 直接调 `_deleteMembers`
- 预估收益/风险: 收益中; 风险低(同文件, 输入输出已同形)

### R20-F 横切支撑面(6 项: A1/C3/D2)

**R20-F-01** · 401/错误转换块 11 行逐字同

- 位置: `shared/auth.js:49-61`(`_request` 内) ↔ `shared/commands.js:915-926`(`_exportDownload` 内)
- 类别: A
- 重复对象: fetch 响应 401→抛 `e.auth`、其它非 2xx→抛带 message 的错误对象, 11 行逐字同
- 分歧点: 无(逐字同)
- 维护风险: 改鉴权失败语义(如加 403 刷新令牌)两处; `_exportDownload` 绕过 `_request` 单点是当初为下载流手写的, 后来漂移出第二份
- 建议收敛形态: 让 `_exportDownload` 改走 `_request`(或抽出 `raiseForStatus(resp)` 单点)
- 预估收益/风险: 收益中高; 风险中(下载流路径要回归: 401 时不能吞掉响应体)

**R20-F-02** · fetch 超时常量同值两实现

- 位置: `shared/auth.js`(`AQB_FETCH_TIMEOUT_S`/`_MS`) ↔ `shared/fetch_low.js`(`AQB_FETCH_LOW_TIMEOUT_S`)
- 类别: C
- 重复对象: "前端请求超时时长"同一事实的两份常量(当前同值)
- 分歧点: 无(同值)
- 维护风险: 调超时忘一处 → 两条路径行为不一致; 守阵 `test_frontend_raw_fetch_timeout_single_point` 已钉住不许多 third 份
- 建议收敛形态: 超时值提为单一常量(如 `window.AQB_FETCH_TIMEOUT_S`), 两实现引用
- 预估收益/风险: 收益中; 风险低(常量合并, 守阵可验)

**R20-F-03** · boot 第三份超时内联

- 位置: `shared/boot.js`(`BOOT_PART_TIMEOUT_MS = 10000`)
- 类别: C
- 重复对象: 同一"超时"事实的第三份表示(启动分片超时)
- 分歧点: 值不同(10s vs 请求超时), 但概念同族; 注释已声明理由(启动分片独立节奏)
- 维护风险: 低(有意独立); 风险在"超时治理无总账", 轮 25 收口
- 建议收敛形态: 登记轮 25 跨层总账; 本轮不动
- 预估收益/风险: 收益小; 风险低

**R20-F-04** · Bearer 头惯用式 4 处

- 位置: `shared/auth.js:34`(单点, 注释声明) · `shared/shortcuts.js:397,410` · `shared/commands.js:916`
- 类别: C
- 重复对象: `if (token) headers.Authorization = \`Bearer ${token}\`\` 一行惯用式 4 份
- 分歧点: 无(逐字同)
- 维护风险: 改鉴权头形态(如加 X-Token 双头/前缀大小写)要数 4 处
- 建议收敛形态: 提 `authHeaders(token)` 助手单点(shortcuts 的 keys 适配器与 commands 下载路径消费)
- 预估收益/风险: 收益小-中; 风险低

**R20-F-05** · KiB↔bytes 换算前端半

- 位置: `shared/format.js:149`(`fmtLimit` 内 `this.fmtSpeed(kib * 1024)`)
- 类别: C
- 重复对象: "后端 KiB/s ↔ 前端 bytes/s"单位事实的前端半(后端已登记 R06-A02)


- 分歧点: 无
- 维护风险: 后端改限速单位口径, 前端乘 1024 的点要跟着改; 同类延伸见 R20-C-09(\_fmtSpeed/\_fmtBytes 第二份单位梯)
- 建议收敛形态: 轮 25 跨层总账收口; 单位梯合并见 R20-C-09
- 预估收益/风险: 收益中(跨层); 风险中

**R20-F-06** · 单点件参照

- 位置: `shared/scope_audit.js`·`shared/traffic_card.js`
- 类别: D
- 为何不动: 两文件自身即收敛产物(单点件), 无内部重复; 留作后续轮对照基准
- 预估收益/风险: 不动


### R20-C 配置编辑面(22 项: A13/B1/C4/D4)

**R20-C-01** · 增命名实体三处同骨架

- 位置: `shared/config_editor.js` `cfgTrackerAdd:672-687`·`cfgRuleAddGroup:744-756`·`cfgRuleAdd:770-782`
- 类别: A(族)
- 重复对象: trim→空名 return→查重 toast(error)→按 schema 造初始值 cfgSetPath→复位 newXName→cfgAddCancel, 三处同构
- 分歧点: 实体初始值构造不同(站点 str_list 空数组 / 规则集空对象 / 规则 conditions+actions)
- 维护风险: 增实体口径(如加名称长度校验/保留字)三处
- 建议收敛形态: 提 `cfgAddNamed(kind, {initial})` 或 `cfgAddEntity(name, path, initial)` 单点
- 预估收益/风险: 收益中; 风险低

**R20-C-02** · hub 侧 promptDialog 包装三处

- 位置: `shared/config_hub.js` `hubAddTracker:951-963`·`hubAddRuleGroup:1003-1010`·`hubAddRule:1011-1018`
- 类别: A(族)
- 重复对象: promptDialog→null/undefined 双判→trim→空判→`this.cfg.newXName = n`→委托 cfg*Add, 三处近逐字同
- 分歧点: 标题/占位/okText 不同
- 维护风险: 改命名交互(如加二次确认/长度提示)三处
- 建议收敛形态: 与 R20-C-01 合并设计: `hubAddEntity(title, cfgAdd)` 一参数化包装
- 预估收益/风险: 收益中; 风险低

**R20-C-03** · 重命名两处同骨架

- 位置: `shared/config_editor.js` `cfgTrackerRename:688-702` ↔ `cfgRuleRename:790-803`
- 类别: A
- 重复对象: promptDialog→null→trim→同名 return→查重 toast→Object.entries 重建对象改名→cfgSetPath→同步选中键, 14 行同构
- 分歧点: 路径深度不同(站点在 trackers 下两层 / 规则在 group 下)
- 维护风险: 改重命名语义(如禁止大小写变形重名)两处
- 建议收敛形态: 提 `cfgRenameKey(parentPath, oldKey, title)` 单点
- 预估收益/风险: 收益中; 风险低

**R20-C-04** · 删实体四处同骨架

- 位置: `shared/config_editor.js` `cfgTrackerRemove:703-716`·`cfgRuleRemoveGroup:757-765`·`cfgRuleRemove:783-789`·`cfgCurveDisable:821-827`
- 类别: A(族)
- 重复对象: confirmDialog(danger)→!ok return→cfgDelPath→复位选中键到剩余首项, 四处同构
- 分歧点: 确认框文案/删除目标不同; 规则集删除连带全部规则(文案声明)
- 维护风险: 改破坏性动作惯例(如加"删除前自动备份")四处
- 建议收敛形态: 提 `cfgRemoveEntity(path, {title, body, selKey})` 单点
- 预估收益/风险: 收益中; 风险低-中(确认框是用户可见面, 收敛时保留文案参数)

**R20-C-05** · schema→默认值梯三处同构

- 位置: `shared/config_editor.js:634-644`(`cfgDefaultForField`) ↔ `shared/config_rules.js:181-200`(`cfgPluginDefaultSpec`)·`201-208`(`cfgPluginDefaultSection`)
- 类别: A(族)
- 重复对象: 遍历 schema 字段造初始值: enum→options[0] / bool→"false" / object→递归段 / else→placeholder||default, 三处同构(config_rules 两份还互相嵌套)
- 分歧点: cfgDefaultForField 只处理 required 字段; cfgPluginDefaultSpec 分 spec_kind 前置分支(list→[]/bool→"true"/enum→options[0])
- 维护风险: 加新字段 kind(如 tri_state)的默认值规则要三处同改; 漏一处则新条目过不了后端校验或写出非法空值
- 建议收敛形态: 提 `cfgDefaultForFields(fields, {requiredOnly})` + `cfgDefaultForPlugin(meta)` 两个单点, 当前三处改调用
- 预估收益/风险: 收益高(3 处且互相缠绕); 风险中(默认值直接影响保存合法性, 需回归"新增条目→保存"路径)

**R20-C-06** · cfgBool 真值惯用式内联三份

- 位置: 单点 `shared/config_editor.js:359-363`(`cfgBool`); 内联份 `shared/config_rules.js:108-112`(`cfgSpecBool`)·`shared/config_hub.js:616-621`(`hrSiteEnabled`)·`shared/config_hub.js:541-545`(`hubReadout` hr_check 分支)
- 类别: A(族)
- 重复对象: `["true","1","yes","on"].includes(String(v).trim().toLowerCase())` 四处(1 单点 + 3 内联)
- 分歧点: cfgSpecBool 对 undefined 先兜 "false"; hrSiteEnabled 先判 typeof boolean —— 细节差异, 口径相同
- 维护风险: 加真值词(如 "y")要数 4 处; YAML BaseLoader 全字符串口径下这是高频判断
- 建议收敛形态: 三处内联改调 `cfgBool`(路径可达时)或提 `truthy(v)` 纯函数
- 预估收益/风险: 收益中; 风险低

**R20-C-07** · 空列表处理与既定规则分歧

- 位置: `shared/config_rules.js:97-102`(`cfgSpecListItemRemove` 空列表写 `[]`) vs 既定规则 `shared/config_editor.js:433-438`(`cfgItemRemove`)·`shared/config_rules.js:47-53`(`cfgPluginRemove`)·`shared/config_editor.js:891-896`(`cfgCurvePointRemove`)·`shared/config_editor.js:1390-1394`(`toggleKey` 注释: 空列表≠缺键, 脏标记误判 + 后端校验必败)
- 类别: B
- 重复对象: "列表删空"骨架四处一致, 仅空态处理不同(三处删键 vs 一处写 [])
- 分歧点: **删键 vs 写空表**。写 [] 的后果按 toggleKey 注释: ①全树对比脏标记认它改动("勾选再取消"仍提示未保存); ②部分键(notify.channels 类)空表过不了后端校验。但规则 conditions/actions 空表是合法形状(cfgRuleAdd 就建 `{conditions:[],actions:[]}`)—— 该分歧需人裁定, 不在本轮给合并结论
- 维护风险: 同一文件内两种空态口径, 后来者抄错边的风险
- 建议收敛形态: 登记; 后续轮裁定"哪些列表允许空表合法存在", 按裁定统一或显式注释豁免
- 预估收益/风险: 只登记(计划 §07: B 类不给直接合并结论)

**R20-C-08** · 列表规整两种兜底

- 位置: `shared/config_rules.js:82-86`(`cfgSpecList` 标量归一为单元素列表) vs `shared/config_editor.js:420-423`(`cfgList` 非数组即 `[]`)
- 类别: D
- 重复对象: "取列表值"助手形状相同
- 为何不动: cfgSpecList 的标量归一是**注释声明的故意设计**(YAML 单值亦归一为数组, 与插件解析一致); cfgList 面向通用字段。语义不同, 非重复
- 预估收益/风险: 不动

**R20-C-09** · 单位梯第二份表示

- 位置: `shared/config_editor.js:1095-1106`(`_fmtBytes`/`_fmtSpeed`) vs `shared/format.js:12-26`(`fmtSpeed`/`fmtSize`)
- 类别: C
- 重复对象: "bytes/s → KiB/s·MiB/s·GiB/s 人话"与 "bytes → KiB·MiB·GiB 人话"两个单位梯的第二份表示(曲线图专用)
- 分歧点: 曲线图用 toFixed(1)+Math.round 兜底+梯顶 TiB; format.js 用 toFixed(2)+原样兜底+梯顶 PiB —— 图轴标签要短, 表格要精, **精度分歧是当前设计**
- 维护风险: 改单位档位(如加 PiB 档)两处; 与 R06-A02(KiB↔bytes)/R20-F-05 同族
- 建议收敛形态: 保留两份但抽 `UNIT_LADDER` 数据表(档位+精度可配)单点; 或轮 25 总账登记
- 预估收益/风险: 收益小-中; 风险低(显示层)

**R20-C-10** · directionKey 三元内联

- 位置: `shared/config_editor.js:885`(`cfgCurvePointAdd` 内联 `direction === "upload_curve" ? "upload_speed_limit" : "download_speed_limit"`) ↔ `shared/config_editor.js:897-899`(`cfgCurveDirectionKey`)
- 类别: A(小项)
- 重复对象: 同文件同映射两份(一份是助手, 一份内联)
- 分歧点: 无
- 维护风险: 加第三方向(如双向曲线)漏内联份
- 建议收敛形态: 内联份改调 `cfgCurveDirectionKey(direction)`
- 预估收益/风险: 收益小; 风险极低

**R20-C-11** · used-set 查重惯用式两份

- 位置: `shared/config_editor.js:1232-1238`(`refOptions` computed) ↔ `shared/config_editor.js:1380-1385`(`refPick`)
- 类别: A(小项)
- 重复对象: `new Set(list().map((it) => String(...).trim()))` 查重集合构造两份(注释声明"双保险")
- 分歧点: 无
- 维护风险: 改归一口径(如大小写不敏感)两份
- 建议收敛形态: 提 `cfgRefUsedSet()` 小助手
- 预估收益/风险: 收益小; 风险低

**R20-C-12** · combobox 键盘导航第 4 处

- 位置: `shared/config_hub.js:870-887`(`hubTrackerKeydown`)
- 类别: A(族延伸)
- 重复对象: 与 R20-B-05 三处同骨架(IME 守卫→↑↓ 取模→Enter pick→preventDefault), 本处多 $nextTick 滚动跟随
- 分歧点: 活动项索引存 `hub.trackerHitIdx`(全局 hub 态), 非局部 ref; 带 hover 接管互斥
- 维护风险: 键盘导航口径第 4 份; 与 R20-B-05 合并设计时要把"索引存放位置"参数化
- 建议收敛形态: 并入 R20-B-05 的 `comboKeydown` 助手设计(索引 getter/setter 注入)
- 预估收益/风险: 收益中(4 处合并); 风险低-中

**R20-C-13** · hubGo/hubBack 共用前置序列

- 位置: `shared/config_hub.js:423-447`(`hubGo`)·`448-454`(`hubBack`)
- 类别: A(小项)
- 重复对象: `kbGuardLeave`→`hubCloseHelp`→`hubTrackerStageClose(false)`→置 view→`window.scrollTo({top:0})` 前置序列两份
- 分歧点: hubGo 有 per-key 初始化(trackers/rules 选中项/懒加载), hubBack 无
- 维护风险: 加新前置(如离开时 flush 草稿)两处
- 建议收敛形态: 提 `hubNavigate(key)` 内聚前置+分发
- 预估收益/风险: 收益小; 风险低

**R20-C-14** · hubAsk 视口边距 12px

- 位置: `shared/config_hub.js:709-745`(`hubAsk` 定位计算)
- 类别: C(族延伸)
- 重复对象: 浮层贴视口定位逻辑(右缘/左缘/上下钳制)是 R20-B-08 视口边距族的第 7 处, 边距值 12(与 ui_feedback 的 8 不同)
- 分歧点: 边距值 12 vs 8 —— 帮助浮窗与 toast/菜单的有意差或疏漏, 未声明
- 维护风险: 浮层定位逻辑散落(menu/ui_feedback/config_hub 三处), 改钳制策略各处为战
- 建议收敛形态: 与 R20-B-08 合并考虑: 提 `placeFloater(rect, {margin, prefer})` 通用定位助手
- 预估收益/风险: 收益中; 风险中(定位是视觉敏感面, 需逐浮层回归)

**R20-C-15** · tm 面板 busy+try+finally 骨架 5 处

- 位置: `shared/config_hub.js` `hubImportSites:964-1002`·`tmLoad:1117-1150`·`tmSave:1285-1301`·`tmAutostart:1303-1321`·`tmPickLoad:1334-1348`
- 类别: A(族延伸)
- 重复对象: `xBusy=true`(或 importing)→清消息→try{api+装配}→catch{err/toast}→finally{复位}, 与 R20-B-01/B-02 同骨架第 6–10 处
- 分歧点: 各面板消息槽(saveMsg/saveErr/autoMsg/autoErr)与回滚语义不同(tmAutostart 失败回滚勾选态)
- 维护风险: 与 dialogs 五处同风险; 另注意 tmShutdownTool(1187-1222) 是"保存失败回滚内存态"的特例, 收敛时不可吞
- 建议收敛形态: 并入 R20-B-01/B-02 的包装器设计(消息槽名参数化)
- 预估收益/风险: 收益中高(与 dialogs 5 处合计 10 处); 风险低-中

**R20-C-16** · 有界轮询+pollGen 代际守卫两份

- 位置: `shared/config_hub.js:1167-1178`(`tmPollSettle`)·`1225-1234`(`tmPollShutdown`)
- 类别: A(对)
- 重复对象: `const gen = ++pollGen; setTimeout(async () => { if (gen !== pollGen) return; await reload(); if (条件 && n < 上限) 递归; }, 间隔)`, 两份同构(仅间隔 2s/1s、上限 15/10、收敛条件不同)
- 分歧点: 间隔/上限/条件参数不同
- 维护风险: 代际守卫模式第 2 份(第 1 份在 polling.js, R20-D 核); 漏 gen 检查会导致两条轮询链叠加双请求
- 建议收敛形态: 提 `boundedPoll({interval, max, until, reload})` 单点; 与 R20-D polling.js 代际守卫统一设计
- 预估收益/风险: 收益中; 风险低-中(轮询时序, 需回归 launching→ready 观察链)

**R20-C-17** · cfgFlatten 树遍历三处同构

- 位置: `shared/config_hub.js:501-513`(`hubFieldCount`)·`348-360`(`hubHits` collect)·`585-601`(`hubCollectRisk`)
- 类别: A(小项族)
- 重复对象: `for (const it of items||[]) { if (it.type !== "field") 递归(it.items); else 计件/收集 }` 遍历 cfgFlatten 产出树, 三处同构
- 分歧点: 叶子处理不同(计数/命中收集/风险收集); hubHits 带上限 10 提前返回
- 维护风险: cfgFlatten 项类型契约(type/items/path/field)散落三处消费, 改契约要三处
- 建议收敛形态: 提 `walkCfgItems(items, onField)` 单点(含上限参数)
- 预估收益/风险: 收益小-中; 风险低

**R20-C-18** · path→key 单点 vs 内联 join

- 位置: 单点 `shared/config_hub.js:491-493`(`hubKey`); 内联 `shared/config_rules.js:257,260`(`cfgRulePath(...).join(".")`)
- 类别: C(小项)
- 重复对象: "路径数组→点分键"事实: 一处有助手, 两处内联
- 分歧点: 无
- 维护风险: 改键格式(如加前缀防碰撞)漏内联份
- 建议收敛形态: config_rules 两处改调 hubKey(或提共享 `pathKey`)
- 预估收益/风险: 收益小; 风险极低

**R20-C-19** · 对象→人话三种实现

- 位置: `shared/config_hub.js:793-818`(`trackerRows` walk)·`shared/config_editor.js:1189-1201`(`readonlySummary` one)·`shared/config_hub.js:929-944`(`hubPluginText`)
- 类别: D
- 重复对象: 三个"把配置对象拍平成人话文本"的遍历形状相似
- 为何不动: 三者输出结构与用途完全不同(搜索行/只读摘要/插件步骤文案), 合并要传 3+ 策略参数, 可读性反而降
- 预估收益/风险: 不动(防过度抽象)

**R20-C-20** · IME 组词守卫 6 处

- 位置: `shared/shortcuts.js:8`(文档化单点说明)·`shortcuts.js:482,1363`·`config_editor.js:299`·`config_hub.js:765,871`
- 类别: C
- 重复对象: `if (e.isComposing || e.keyCode === 229) return;` 一行守卫 5 处执行 + 1 处文档
- 分歧点: 无(逐字同)
- 维护风险: 键盘入口新增处漏守卫 → 中文输入法组词中 Esc/Enter 被业务劫持(用户可见 bug, 且难复现)
- 建议收敛形态: 提 `imeGuard(e)` 助手或 keydown 包装(`onKeyGuard(fn)`); 文档单点在 shortcuts 保持
- 预估收益/风险: 收益中; 风险低

**R20-C-21** · tmFmtBytes 委托 fmtSize(正例)

- 位置: `shared/config_hub.js:1322-1323`
- 类别: D
- 为何不动: 这是"复用单点"的正例(工具卡字节格式化委托 format.js fmtSize), 与 R20-C-09 的两份单位梯对照; 记录以正样本留存
- 预估收益/风险: 不动

**R20-C-22** · 规则摘要两种粒度

- 位置: `shared/config_rules.js:219-223`(`cfgRuleSummary`)·`264-279`(`cfgRuleMetaSummary`)
- 类别: D
- 重复对象: 都拼"触发时机 · 若干项"摘要串
- 为何不动: 卡头摘要(一行概览)与折叠段摘要(详细节奏)粒度与消费场景不同, 属同一事实的两个**正当**表示层面
- 预估收益/风险: 不动

### R20-D 运行时骨架面(13 项: A3/C7/D3)

**R20-D-01** · localStorage 白名单初值函数 7 处同构

- 位置: `shared/app.js` `initialViewMode:785`·`initialPage:801`·`initialDrawerTab:813`·`initialDrawerHeight:827`·`initialDrawerTpl:841`·`initialDrawerMerge:852` + `shared/config_hub.js:160`(`initialHubView`)
- 类别: A(族)
- 重复对象: `try { const saved = localStorage.getItem(KEY); return <白名单校验> ? saved : DEFAULT; } catch { return DEFAULT; }` 七处同构(注释互称"同口径")
- 分歧点: 白名单校验各异(等值 / 数组 includes / 数字范围 / JSON 双形态迁移); initialDrawerTpl 多一层 `reg.readSel()` 合并; initialHubView 多旧值别名映射
- 维护风险: 新增偏好项再抄一遍骨架; 漏 try/catch 的变体在隐私模式下会断启动路径
- 建议收敛形态: 提 `readLsChoice(key, isValid, fallback)` 单点(校验器注入), 七处改调用
- 预估收益/风险: 收益中(7 处, 且是启动路径); 风险低(冒烟可验)

**R20-D-02** · localStorage JSON 读入健壮性不一

- 位置: `shared/app.js:413`(`loadTimeFmt` `|| "{}"`)·`app.js:712`(`readColStateRaw` 裸 parse+循环 try)`·`app.js:854`(`|| '"off"'`)·`shared/drawer_templates.js:405`(`|| "{}"`)·`shared/lifecycle.js:209\`(裸 getItem 无 try/catch)
- 类别: C
- 重复对象: "读 localStorage + JSON.parse + 坏数据兜底" 同一事实五种写法
- 分歧点: 兜底形态三种 + 一种无兜底; lifecycle 的 token 读取无 try/catch(隐私模式抛错会断 mounted)
- 维护风险: 坏 JSON / 存储被禁时各路径行为不一致, 且无总账
- 建议收敛形态: 提 `readLsJson(key, fallback)` 单点; token 读取补 try/catch
- 预估收益/风险: 收益小-中; 风险低-中(token 读在启动路径, 需回归登录两条链)

**R20-D-03** · 浮层关闭撤强调 watcher 三处同构

- 位置: `shared/state.js:520`(`"menu.visible"`)·`527`(`"headMenu.visible"`)·`530`(`"filePrio.visible"`)
- 类别: A(小项族)
- 重复对象: `if (!v) this._clearCtxSource();` 三处(注释声明 CTX-02 同一口径)
- 分歧点: menu.visible 多 keepSub/subMenu 复位(FX-15)
- 维护风险: 新浮层漏挂 → 关闭后触发源强调残留(CTX-02 复发)
- 建议收敛形态: 浮层注册表驱动(关层回调表), 与 R20-D-11 合并设计
- 预估收益/风险: 收益小; 风险低

**R20-D-04** · \_menuFitRefit watcher 四处同构

- 位置: `shared/state.js:541`(`menu`)·`544`(`headMenu`)·`547`(`filePrio`)·`551`(`drawerMenu`)
- 类别: A(小项族)
- 重复对象: `this.$nextTick(() => this._menuFitRefit("X", "YEl"));` 四处, 仅 (浮层名, ref 名) 对不同
- 分歧点: 无
- 维护风险: 新浮层漏挂重钳位 → 锚点在下视口时菜单底项点击不可达(issue 26-10-06-1717 复发)


- 建议收敛形态: `FIT_MENUS = [["menu","ctxMenu"],...]` 表 + 循环注册(或 watch 多路径)
- 预估收益/风险: 收益小; 风险低

**R20-D-05** · 有界轮询三样式

- 位置: `shared/commands.js:211-228`(`_pollCmd` 退避曲线 while + stop 标志) ↔ `shared/config_hub.js:1167-1178`(`tmPollSettle`)·`1225-1234`(`tmPollShutdown`)(定间隔 setTimeout 递归 + pollGen 代际守卫) ↔ `shared/polling.js:106-111`(`scheduleNext` setTimeout 链)
- 类别: C
- 重复对象: "有界等待外部状态收敛" 同一事实三种实现
- 分歧点: 退避曲线 vs 定间隔; 代际守卫 vs stop 标志 vs 链式 clearTimeout; 上限 40s/15 轮/10 轮/无
- 维护风险: 轮询叠加/泄漏的防护模式三套, 后来者各学一套
- 建议收敛形态: 登记轮 25 总账; 收敛候选 `boundedPoll({interval|backoff, max, genGuard})`
- 预估收益/风险: 收益中; 风险中(时序敏感, 需回归三条等待链)

**R20-D-06** · busy 守卫惯用式 14+ 处

- 位置: `auth.js:147`·`add_torrent.js:94,343,675`·`dialogs.js:88,113,133,231,309,322,453,556`·`drawer.js:667,741`·`view.js:51`(另有 polling.js `_esBusy:22`·config_hub `relaunching/shutting/importing` 族同语义)
- 类别: C
- 重复对象: "在途防重入/防误关" `if (this.xBusy) return;` 一行守卫 14+ 处
- 分歧点: 语义分两种(防重复投递 / 回执等待期防误关), 无成文区分规范
- 维护风险: 新在途操作漏守卫 → 重复投递或等待期误关丢回执
- 建议收敛形态: 与 R20-B-01/R20-C-15 包装器合并设计(守卫由包装器统一施加)
- 预估收益/风险: 收益中; 风险低-中

**R20-D-07** · tm 状态双表

- 位置: `shared/config_hub.js:1106-1111`(`tmStateText`) ↔ `shared/config_hub.js:1114-1116`(`tmStateClass`)
- 类别: C(小项)
- 重复对象: tm.state 五态的展示事实两张表(文案表 + LED 类名表), 键集一致
- 分歧点: 无(键集一致; 注释记过 ready→"on" 无样式类的历史坑)
- 维护风险: 加第六态漏一张表 → 文案显示"未知"或 LED 落灰
- 建议收敛形态: 合并为一张 `{ready: {text, cls}, ...}` 表
- 预估收益/风险: 收益小; 风险极低

**R20-D-08** · STATE_RANK 跨层双实现

- 位置: `shared/app.js:878-880`(`STATE_RANK` + `STATE_RANK_LAST`) ↔ 后端 `auto_qb/mixins/web_view.py::_SHOW_STATE_RANK`
- 类别: C
- 重复对象: "状态优先级" 同一事实的前后端两份实现
- 分歧点: 历史上有过两处分歧({downloading,checking} 与 {paused,seeding}), 已对齐; 守阵 `_scan_state_rank` 机械盯防(改一边必须改另一边)
- 维护风险: 再漂移则同批种子两页颜色不同 + 乐观 UI 弹回(注释有 2026-09-19/21 实史)
- 建议收敛形态: 登记轮 25 跨层总账; 接口化收敛需单独拍板
- 预估收益/风险: 收益中(跨层); 风险中

**R20-D-09** · 导出/复制家族正例

- 位置: `shared/commands.js` `exportTorrent:898`·`exportMulti:943`·`exportGroup:848`·`_exportHashes:952` 四入口收敛到 `_exportDownload:915` 单点; `_copyText:866` + `copyText:891` 模板别名(注释声明 Vue `_` 前缀不可达)
- 类别: D
- 为何不动: 下载核心/剪贴板降级均已单点化; 记录为正例(与 R20-F-01 的 `_exportDownload` 内联 401 块对照: 同一文件里"该单点的没单点")
- 预估收益/风险: 不动

**R20-D-10** · polling/lifecycle 单点件正例

- 位置: `shared/polling.js:142`(`applyStateRows` delta/full 单一合并入口)·`shared/lifecycle.js:308`(`_mergeBackendErrlog`)·`332`(`_pullErrlog` 合并/补拉单点)
- 类别: D
- 为何不动: 既有收敛产物, 注释声明单点语义与顺序安全事实
- 预估收益/风险: 不动

**R20-D-11** · 点空白收层名单 12 项

- 位置: `shared/lifecycle.js:75-96`(window click 监听内 12 个浮层 visible 复位)
- 类别: C
- 重复对象: "临时浮层清单"事实的又一种表示(与 R20-B-04 的 Esc 退栈链 20 项 + escBusy 同步并列)
- 分歧点: 与 Esc 链名单不完全一致(有意: Esc 有层级优先, click 无层级)
- 维护风险: 新浮层要进三张名单(click / Esc / escBusy), 漏一张症状各不同且都难复现
- 建议收敛形态: 浮层注册表单点(name → {visible, escOrder, closeOnBlank}), 与 R20-D-03 合并设计
- 预估收益/风险: 收益中; 风险中(鼠标+键盘两条路径都要回归)

**R20-D-12** · unmounted 幂等撤除惯用式 10 处

- 位置: `shared/lifecycle.js:236-288`(`_kbKeyDown`/`_cfgGuardKey`/`_winListening`/`_winRaf`/`_onColStore`/`_onTimeFmtStore`/`_clockTimer`/`_errPollTimer`/`_headObs`/`_headRaf` 十处 `if (this._x) { 撤除; this._x = 0/null; }`)
- 类别: D
- 重复对象: "句柄幂等撤除"形状十处
- 为何不动: 撤除动作各异(removeEventListener / clearInterval / clearTimeout / cancelAnimationFrame / observer.disconnect), 抽分发表的机械复杂度高于收益; 各处均带"防热重载堆叠"注释
- 预估收益/风险: 不动(防过度抽象)

**R20-D-13** · 2 位数补零助手两份

- 位置: `shared/format.js:38`(`fmtTime` 内 `p`) ↔ `shared/lifecycle.js:31`(`_errBackendClock` 内 `p`)
- 类别: C(小项)
- 重复对象: `const p = (n) => String(n).padStart(2, "0")` 两份逐字同
- 分歧点: 无
- 维护风险: 极低(但格式助手应单点)
- 建议收敛形态: 提 `pad2(n)` 单点
- 预估收益/风险: 收益很小; 风险极低

### R20-E 领域页面(10 项: A2/C5/D3)

**R20-E-01** · 浮层锚定定位几何五处手写

- 位置: `shared/hr.js:141-171`(`_hrPopPlace`)·`shared/ui_feedback.js:247-257`(右键菜单溢出探针+夹取)·`shared/ui_feedback.js:413-433`(面板定位)·`shared/menu.js:312-329`(`_menuFit` 类重钳位)·`shared/config_hub.js:716-736`(tracker 帮助浮层)
- 类别: C
- 重复对象: 「`getBoundingClientRect` + `window.innerWidth/innerHeight` + 边距夹取 + 溢出翻向」同一事实五种手写
- 分歧点: 边距 8 vs 12；翻向能力三档(只左右夹取 / 左右+上下 / 上优先翻下+尾部贴底)；箭头随向重定位仅 hr 一处；探针基准有 clientX 与 rect.left 两套
- 维护风险: 视口边界类缺陷(菜单底项不可达 issue 26-10-06-1717 已发过一次)要五处同修；R20-B 已把"8px 字面量 6 处"记为小项，本项把它升为独立条目(含几何算法而非只边距常量)
- 建议收敛形态: 先抽纯函数 `clampRect(rect, size, margin)` + `flipVertical(rect, size, {gap, margin, prefer})`；整体定位 API 留待各浮层语义稳定后再议
- 预估收益/风险: 收益中; 风险中(定位回归无自动化覆盖, 需逐浮层手工验)

**R20-E-02** · 长驻轮询启停骨架第二份

- 位置: `shared/drawer_store.js:69-81`(`_stopDrawerPoll`)·`82-108`(`_startDrawerPoll`) ↔ `shared/qb_traffic_chart.js:752-771`(`_qbPollStart`)·`773-780`(`_qbPollStop`)·`782-786`(`_qbPollResync`)
- 类别: C
- 重复对象: `stop → setInterval(守卫链 → 在途互斥 → 拉数) → stop(clearInterval+句柄置空)` 同一"长驻轮询生命周期"两份；**stop 半逐字同**(qb 侧显式注释"对齐 drawer.js \_startDrawerPoll 先例")
- 分歧点: 守卫链不同(`drawer.open` + `page!=="groups"` + `document.hidden` vs `def.active(this)` + `document.hidden`)；间隔来源不同(`currentPollMs()` 按种子量分档 vs `meta.interval_s` 夹取 [MIN,MAX])；**qb 侧有在途悬挂兜底(`_qbLoadStalled` 超时强制续拉 + 警告痕), 抽屉侧无** —— 同一类"loading 卡死永久挡拍"缺陷只修了一边
- 维护风险: 悬挂兜底缺口是**真缺陷面**(抽屉 trackers/peers 页签 loading 卡死 → 面板冻结到重开)；两份间隔策略改动易互相割裂
- 建议收敛形态: `startPoll(fn, {ms, guard, mutex, stallMs})` 返回句柄 + `stopPoll(handle)`; 与 R20-D-05(`boundedPoll`)并入轮 25 总账同一设计草案
- 预估收益/风险: 收益中高(兜底缺口为实质收益); 风险中(时序敏感, 需回归抽屉四页签 + 三作用域流量图)

**R20-E-03** · 「不可见/非活跃不拉数」守卫五表示

- 位置: `shared/polling.js:109`(`document.hidden || !this.authOk`)·`shared/lifecycle.js:191`(`document.hidden` 停主轮)·`shared/drawer_store.js:89-96`(open+hidden+page+合并对)·`shared/qb_traffic_chart.js:759-761`(active+hidden)·`shared/lifecycle.js:356`(`_errPollTimer` 无守卫)
- 类别: C
- 重复对象: 同一"后台不拉、离页不拉"纪律五种拼装
- 分歧点: 判据层数 1~4；错误日志轮询**完全没有**可见性守卫(后台标签仍每 `ERR_POLL_INTERVAL_MS` 拉一次)
- 维护风险: 新增轮询漏一层判据 → 后台标签持续打后端; `_errPollTimer` 是现存不一致点
- 建议收敛形态: `pollGate()` 单点(组合 hidden / 登录态 / 当前页 / 作用域活跃), 各轮询调用注入自己的活跃谓词
- 预估收益/风险: 收益小-中; 风险低(纯前端节流, 行为差异仅后台标签)

**R20-E-04** · 面板加载骨架扩员 5→8(R20-B-02 延伸)

- 位置: `shared/hr_status.js:181-202`(`loadHrStatus`)·`568-587`(`hrsHistLoad`, 与前者除端点/状态名外逐字同)·`210-245`(`loadHrSiteEntries`, 变体) + `shared/config_editor.js:168-184`(`cfgLoad`)·`193-221`(`cfgSave`)
- 类别: A(族延伸)
- 重复对象: 与 R20-B-02 同一骨架(`loading 守卫 → loading=true/error="" → try{api+装配} catch{!e.auth 落 error} finally{loading=false}`)；本轮新增两处逐字同(hr_status 两表)+ 两处 cfg 变体
- 分歧点: `loadHrSiteEntries` 用"对象整替"而非字段赋值(force 时 `keep` 保旧行, 三态重组 6 字段)；`cfgSave` 走 POST 后重载属"提交+回读"变体
- 维护风险: 家族实为 8 处(原估 5), 收敛收益被低估; 漏 finally 的症状(面板永久转圈)在 8 条路径都能复现
- 建议收敛形态: 并入 R20-B-02 的 `panelLoad(key, loader)`; `loadHrSiteEntries` 的 keep 语义作为选项(`{keepOnForce:true}`)而非第二实现
- 预估收益/风险: 收益中高(扩员后); 风险低

**R20-E-05** · 分享率两位小数八处散落

- 位置: `shared/format.js:109`(`cellRatio`)·`113-119`(`cellAvailability`)·`shared/hr_status.js:344`(`hrsRatio`)·`shared/hr.js:212`·`329`·`shared/drawer.js:1310`·`1316`·`1349`
- 类别: C
- 重复对象: `Number(v).toFixed(2)` 表示分享率/可用性 8 处
- 分歧点: 空值/边界守卫各异且**均有正当理由**(cellRatio 进度 0 时不显示; cellAvailability 吞负数 qB 哨兵; hrsRatio null→「—」; drawer 分享率限制 `<0`→「未设」) —— 守卫属各列展示语义, 不该合并
- 维护风险: 改"分享率小数位"要动 8 处; 各处 guard 已趋稳定, 漂移风险低
- 建议收敛形态: 只抽纯数字格式化 `fmtRatio2(v)`, guard 留调用方
- 预估收益/风险: 收益小; 风险极低

**R20-E-06** · 百分比换算两种精度

- 位置: `shared/hr_status.js:546`(`hrsPct`, `Math.round(v*100)`)·`shared/drawer.js:1312`(`toFixed(1)` 进度文案)·`1439`·`1460`(条宽 `Math.round`)·`1465`(相关度 `Math.round`)
- 类别: C(小项)
- 重复对象: `x * 100` 百分比文本/条宽 5 处
- 分歧点: 文案一位小数(进度 12.3%) vs 整数(条宽/相关度); 同一 drawer 文件内两种
- 维护风险: 低(纯显示)
- 建议收敛形态: `pctText(v, digits=0)` 单点


- 预估收益/风险: 收益小; 风险极低

**R20-E-07** · pad2 第三份 + `new Date(ts*1000)` 三处(R20-D-13 扩员)

- 位置: `shared/qb_traffic_chart.js:1056-1057`(`_qbTickLabel` 内 `new Date(ts*1000)` + `p`)·`shared/format.js:37-38`(`fmtTime`)·`shared/lifecycle.js:31`
- 类别: C(小项, R20-D-13 扩员)
- 重复对象: `const p = (n) => String(n).padStart(2,"0")` 三份逐字同; 秒→毫秒换算 `ts*1000` 三处
- 分歧点: `_qbTickLabel` 按窗口四族选刻度粒度(年月/日期/到秒/到分)属正当需求, 但 `p` 与 `*1000` 属同一事实
- 维护风险: 极低
- 建议收敛形态: `pad2(n)` + `secToDate(ts)` 单点; 刻度粒度留各自(或抽 `tickFmt(window, ts)`)
- 预估收益/风险: 收益很小; 风险极低

**R20-E-08** · 档位/来源类名映射两族

- 位置: `shared/hr.js:81-104`(`hrTimeClass`/`hrRatioClass`/`hrGroupClass`/`hrDurClass`/`hrSrcClass`) ↔ `shared/hr_status.js:337`(`hrsLaneCls`)·`380`(`hrsSrcCls`)·`452`(`hrsStateClass`)·`506`(`hrsLaneClass`)·`539`(`hrsHistResCls`)
- 类别: D
- 重复对象: 「后端 token → CSS 类名」映射函数两族(列表页行 vs 状态页徽章)，形状相似
- 为何不动: 两族消费不同后端载荷(种子行 hr\_* 字段 vs SiteStatus/LaneStatus)，token 集不重叠；多处注释明确"只映射不重算判定"，合并会把防伪边界抹平
- 预估收益/风险: 不动

**R20-E-09** · 图表纵轴取值链已单点

- 位置: `shared/qb_traffic_chart.js:587-605`(`_qbGlobalLimit`/`_qbYCapOf`)
- 类别: D
- 为何不动: 注释声明 `speedLimitBytes`(dialogs.js)为跨面单点(状态栏/速度染色/流量图同源)，本处只取上下行较大者 + 模式换算；`_qbYCapOf` 的三种模式分派是单点判据
- 预估收益/风险: 不动

**R20-E-10** · 三条时序曲线渲染栈

- 位置: `shared/qb_traffic_chart.js:787-1054`(uPlot 封装 + `_qbDrawGaps`/`_qbDrawLimits` 注解钩子) ↔ `shared/config_editor.js:940-1070`(SVG 手绘阶梯 + 悬停吸附 + 点编辑) ↔ `shared/dialogs.js:602-905`(`histGeom`/`histPaths` SVG 面积)
- 类别: D
- 重复对象: "画时序曲线"三条路径，表面高度相似
- 为何不动: 渲染栈与交互需求三分(实时轮询+缩放+注释层 / 阶梯+可编辑控制点+吸附提示 / 双系列面积+静态)；统一到一栈属大重构，不属重复代码审查范围；可抽的只有坐标刻度文案(见 R20-E-07)
- 预估收益/风险: 不动

## 分类计数


### R21-A 抽屉底座(12 项: A5/B1/C5/D1)

**R21-A-01** · 抽屉四 fetcher 同骨架 4 份

- 位置: `shared/drawer_store.js` `_fetchDrawerDetail:112-130`·`_fetchDrawerTrackers:131-152`·`_fetchDrawerFiles:153-173`·`_fetchDrawerPeers:174-197`
- 类别: A(族)
- 重复对象: `hash 快照 → loading 门 → try{api} → stale 守卫 → 合并/赋值 → 清 error} catch{!silent&&!e.auth toast → stale 守卫 → 落 error} finally{stale 守卫 → loading=false → _dtNotify → _drawerDone}` 四份同构(每份 ~22 行)
- 分歧点: 合并键(详情无合并 / tracker 按 url / file 按 index|name / peer 按 ip:port)、peer 多一道 `_drawerNormPeers` 键名适配、detail 多一条"种子不存在"error、detail 恒拉不带 seq
- 维护风险: 四份 stale 守卫 × 两处 = 8 个判点，漏一处即"旧响应覆盖新目标"或"遮罩挂死"；`_dtNotify` 与 `loading=false` 的**先后次序**是有意为之(注释三处重复解释)，复制时极易颠倒
- 建议收敛形态: `drawerFetch(src, {path, merge, norm, errText, toastText})` —— 骨架 1 份，四调用点只传差异项；stale/loading/notify/done 的四步次序由骨架固定
- 预估收益/风险: 收益高(4×22 行 + 8 个易错判点); 风险中(取数链路是抽屉全部数据面，需回归四页签 + 合并双列 + 软切换)

**R21-A-02** · 限速对话框双胞胎(单选/批量)

- 位置: `shared/drawer.js` `editLimits:562-592` ↔ `editLimitsMulti:766-795`
- 类别: A
- 重复对象: 字段表(`up`/`dl` 两输入，同 label/placeholder)、`for (const [k,key] of [["up","up_limit"],["dl","dl_limit"]])` 校验循环、`Math.round(n*1024)` 换算、"未作修改"短路、结尾投递 —— 除 title/body 文案、预填值、最后一行(`_editPost` vs `_bulkEditPost`)外**逐字同**
- 分歧点: 预填(单选拉 `_editDetail` 填当前值；批量恒空)、目标集合(单 hash vs `_bulkTargets`)
- 维护风险: 改限速口径(如允许小数 KiB)要两处同改；单边漏改 → 单选/批量行为不一致且都"看起来正常"
- 建议收敛形态: `_speedLimitDialog({title, body, prefill, submit})` —— 公共两输入 + 校验 + 换算收成一份，`submit` 注入 `_editPost`/`_bulkEditPost`
- 预估收益/风险: 收益中(2×30 行); 风险低(纯表单，可手工回归两条路径)

**R21-A-03** · 单位预填/回填换算惯用式

- 位置: `shared/drawer.js:566`(`kiB`: bytes→KiB 字符串, ≤0 留空)·`585`(`*1024` 回写)·`598`(`hrs`: 秒→小时两位小数, ≤0 留空)·`626`(`*3600`, -1 原样)·`788`(`*1024` 批量侧)·`913`(优先级文案表)·`1349`(`?? -1` 未设判据)
- 类别: C
- 重复对象: 「显示单位 ↔ 存储单位」换算 + 「≤0/-1 = 未设留空」哨兵惯用式，7 处手写
- 分歧点: 精度与哨兵各异(KiB 取整 / 小时两位 / 分享率 -1)；每个字段的哨兵语义是后端契约，不该统一
- 维护风险: 新增可编辑字段时单位方向(乘/除)与哨兵易弄反；与 R06-A02(KiB↔bytes)/R20-C-09(单位梯)同族
- 建议收敛形态: 只抽方向明确的小助手 `bytesToKiBText`/`kiBTextToBytes`/`secToHourText`/`hourTextToSec`，哨兵留调用方
- 预估收益/风险: 收益小; 风险低

**R21-A-04** · combobox 键盘导航第 5 处

- 位置: `shared/drawer.js:698-725`(`onMovePathKeydown`)
- 类别: A(族延伸)
- 重复对象: 与 R20-B-05 三处 + R20-C-12 一处同骨架(↑↓ 取模环绕 → Enter 选中 preventDefault → Esc 收层)
- 分歧点: **①层关时方向键先开层**(另四处只移高亮)；②Esc 只收面板且 `stopPropagation`(不关对话框)；③**无 IME 守卫**(`e.isComposing`/`keyCode===229` 缺失) —— 另四处均首行守卫
- 维护风险: 键盘口径第 5 份;③ 是**实际缺口**(输入法组词期间方向键/回车被劫持)，只因路径输入多为 ASCII 而未暴露
- 建议收敛形态: 并入 R20-B-05 的 `comboKeydown` 设计，把"层关时开层""Esc 只收面板""IME 守卫"作为选项显式化；③ 无论是否合并都应补守卫
- 预估收益/风险: 收益中(5 处合并); 风险低-中(键盘路径需逐下拉手工回归)

**R21-A-05** · 失焦收层 40ms 第 3 处

- 位置: `shared/drawer.js:729-736`(`movePathBlurClose`)+`737-739`(`_movePopBlurCancel`)
- 类别: A(族延伸)
- 重复对象: R20-B-06 的 40ms 合帧失焦收层第 3 份；**这处已部分收敛**(守卫走 `_popBlurShouldHold` 单点，add_torrent.js)，剩 `clearTimeout + setTimeout(40)` 壳与"撤挂起"成对方法
- 分歧点: 收层目标态不同(`movePathMenu/movePathHi` 双复位 vs 另一套)；撤挂起方法独立命名(`_movePopBlurCancel`)
- 维护风险: 新下拉再抄一份；40ms 魔数第三次出现
- 建议收敛形态: `popBlurClose(timerKey, close)` / `popBlurCancel(timerKey)` 两助手，40ms 常量化
- 预估收益/风险: 收益小; 风险极低

**R21-A-06** · 文件优先级文案表两份且键集不一致

- 位置: `shared/drawer.js:1424`(`drawerFileRows` 内 `prio`)`{0:"不下载",1:"正常",4:"高",6:"高",7:"最高"}` ↔ `shared/drawer.js:913`(`setFilePriority` 内 `label`)`{0:"不下载",1:"正常",6:"高",7:"最高"}`
- 类别: B
- 重复对象: qB `files[].priority` → 人话 同一张表，同一文件内两份
- 分歧点: **`4` 档只在行渲染侧存在**(映射到"高")，设置侧缺键 ⇒ `{p:4}` 时 `label` 落 `String(p)`，toast 显示 `优先级已设为「4」` 而表格行显示「高」。`drawerFileRows` 的 `prio` 注释写"4|6=高"、`setFilePriority` 注释只写"6=高" —— 两处注释已不同步
- 维护风险: 真实分歧而非纯重复；4 档由谁写入需人裁定(qB 文档里 4 是 legacy "high" 档，现网可能仍存)
- 建议收敛形态: 抽 `FILE_PRIO_TEXT` 单表(含 4)，两处消费；按计划 §07 B 类**只登记不给合并结论**
- 预估收益/风险: 只登记(但建议优先裁定 4 档归属，成本极低)

**R21-A-07** · `dur`/`size` 助手跨文件两份

- 位置: `shared/drawer.js:1302-1304`(`drawerGeneralSections` 内 `dur`/`size` 局部箭头函数) ↔ `shared/drawer_templates.js:151-155`(`HELPERS.dur`/`HELPERS.size`)
- 类别: A
- 重复对象: `dur = (v, dash) => (v===null||v===undefined||v<0) ? (dash||"未设") : fmtDuration(v)` 与 `size = (v) => fmtSizeOrDash(v) || "—"` **逐字同**(仅 `ctx.` / `this.` 之差)
- 分歧点: 无(语义完全一致)
- 维护风险: HELPERS 头注自称"01-12 十二份变体各自复刻的四类骨架代码收口成单点"，但**根实例侧仍留私有一份** —— 单点没覆盖到自己的第一消费者
- 建议收敛形态: `drawerGeneralSections` 改调 `window.AQB_DRAWER_TPL_REG.helpers.dur/size`，删本地两份
- 预估收益/风险: 收益小(2×3 行); 风险极低(同语义替换)

**R21-A-08** · 定时器撤销/防抖惯用式无助手

- 位置: `clearTimeout(` 全前端 **34 处**(本面集中: `drawer.js:108?(mergeResizeT)`·`730`(movePopBlurT)·`1063`(followDrawerTimer)·`drawer_store.js:302`(busyArmTimer)·`1173`(animRaf 除外)); 防抖四件套 `if (t) clearTimeout(t); t = setTimeout(...)` 见于 `view.js:7-15`·`53-54`·`filters.js:88`·`hr.js:117-139`·`add_torrent.js`/`dialogs.js`(40ms 族)
- 类别: C
- 重复对象: 「定时器句柄生命周期」(起 → 撤 → 置空 / 防抖重排)同一纪律 N 种手写；全仓无 `debounce`/`delayCall` 助手(grep 零命中)
- 分歧点: 有的撤后置 null、有的置 0、有的不置；防抖延迟 40/120/160/200/400/1000ms 六种(各有正当理由)
- 维护风险: 漏置空 → `if (t)` 判真却已触发过(重复撤销无害，但配合 unmounted 的"防热重载"语义会误导); 与 R20-D-12(unmounted 十处句柄撤除)为同一族的上游
- 建议收敛形态: 先加 `debounce(fn, ms)` + `timerCancel(handle)` 两个最小助手，新代码只许用助手(存量渐进)
- 预估收益/风险: 收益中低(34 处但每处 3 行); 风险低(纯机械替换，但需逐个确认置空语义)

**R21-A-09** · 偏好写侧吞异常 14 处

- 位置: `localStorage.setItem` 全前端 **14 处**: `drawer.js:232/1090/1151/1157`·`columns.js:424/452`·`config_hub.js:199`·`drawer_templates.js:726`·`menu.js:71`·`qb_traffic_chart.js:581/634`·`view.js:85/145`·`auth.js:166`
- 类别: C
- 重复对象: 「只落用户意图 + 写失败吞异常 + 不打断当前操作」同一纪律 14 份手写(try/catch 各一份)
- 分歧点: 异常处理形态三种(`catch {}` / `catch (e) { /* 注 */ }` / 裸写无 try —— `auth.js:166` 与 `columns.js:424` 在既有 try 块内)
- 维护风险: 隐私模式/配额满时的行为不统一(有的静默、有的在更大 try 里被吞)；与 R20-D-01/D-02(**读侧**)是同一事实的写侧，分开两轮登记但应同批收敛
- 建议收敛形态: `writeLs(key, value)` 单点(内部 try/catch)，14 处改调用
- 预估收益/风险: 收益小; 风险极低

**R21-A-10** · 浮层夹取几何第 6 处(R20-E-01 扩员)

- 位置: `shared/drawer.js:894-903`(`openFilePrio`)
- 类别: C(族延伸)
- 重复对象: 与 R20-E-01 五处同族(`Math.min(Math.max(8, rect.left), Math.max(8, innerWidth - w - 8))` 逐字同 ui_feedback.js:256-257)
- 分歧点: 尺寸硬编码 150×176(未量实际元素)；y 轴只有"下方优先"无翻转；`+4` 间距与别处 gap 8/10/12 均不同
- 维护风险: 菜单项增减后 150×176 失真 → 夹取偏移；六处已三种边距三种间距
- 建议收敛形态: 并入 R20-E-01 的 `clampRect`；尺寸改实测 `el.offsetWidth/Height`
- 预估收益/风险: 收益中(并入后共 6 处); 风险低

**R21-A-11** · `_fitAddPop` 三 watcher 同调

- 位置: `shared/drawer.js:1490-1498`(`movePathMenu`/`movePathInput`/`movePathOptions` 三条 watch 都只调 `this._fitAddPop("movePathList")`)
- 类别: C(小项, 与 R20-D-04 同族)
- 重复对象: "同一重限动作挂多个触发源"的第三条写法(R20-D-04 是 `_menuFitRefit` 四处 watcher)
- 分歧点: 本处三条 watch 的目标态完全一致(仅触发源不同)，可合成 `watch: { a,b,c }` 或单 watch 数组
- 维护风险: 低(漏一条 → 删字后候选涨回撑变形，注释已记)
- 建议收敛形态: 三 watch 合并为一条(或 `$watch([...])`)
- 预估收益/风险: 收益很小; 风险极低

**R21-A-12** · 抽屉层单点件正例

- 位置: `drawer.js:40-61`(`MERGE_PAIRS` + `AQB_DRAWER_MERGE` 跨文件单点, 注释记 R2 空列 bug 教训)·`97-115`(`drawerIsSeed`/`drawerIsTraffic`/`drawerMember` 形态判据, 守阵 `test_frontend_drawer_form_judge_single_point` 钉死)·`drawer_store.js:108-111`(`_drawerStale` 竞态单点)·`285-297`(`_drawerDone` 落定单点)·`326-338`(`_drawerNormPeers` 键名适配单点)·`drawer_templates.js`(`dtHtml`/`esc`/`HELPERS`/`KIT`/`TPL_REG` 五件)·`drawer.js:1389-1404`(`icoTone` 图标→色调派生表)
- 类别: D
- 为何不动: 均为既有收敛轮的产物，注释记录了"为何必须单点"的事故史(空列 bug / 形态判据散落 / 破折号表)；本层是全前端收敛度最高的区域之一
- 预估收益/风险: 不动

## 分类计数

### R21-B 抽屉变体 general+trackers(11 项: A6/B2/C2/D1)

**R21-B-01** · 变体三态空帧 + 整帧换帧骨架 12 份(横跨 R21-B/C)

- 位置: `drawer_tpl/01:277-292`·`02:211-294`·`03:245-347`·`04:292-335`·`05:332-408` + 06/07/08/09/10/11/12 同构
- 类别: A(族)
- 重复对象: `取数据 → 算结构 sig → H.skipUnchanged 短路 → if(loading&&!rows) 空帧 / if(err&&!rows) 空帧 / if(!rows.length) 空帧 → 拼 html → H.withScroll(replaceChildren + anchFill)` 十二份同构；**实测 `createContextualFragment` 计数**: general 三件各 1 次(只用整帧)、bridge 九件各 4 次(三态 + 整帧)
- 分歧点: 空态类名前缀(dt01-empty…dt12-empty，各变体自定，为 CSS 作用域)；文案各异(正在加载…/…加载失败请重试/暂无 tracker|文件|用户)；bridge 变体多一条"数据拍 paintHtml 原地回填"分支 + anchFill
- 维护风险: 十二份里"错误态先于空态"的次序、"失败不是真空"的语义(P3-5 报告 26-10-07-0542)靠注释各自复述 —— 新增变体抄漏一处即回到"失败当空态"的老 bug
- 建议收敛形态: 在 `reg.helpers` 增 `shell(host, ui, {loading, err, rows, texts, html, tableId})` —— 三态文案/次序/换帧/滚动/锚保活全由壳固定，变体只交 `html` 与 `texts`；KIT 的三态 (drawer_templates.js:287-296) 作为其文案默认值
- 预估收益/风险: 收益高(12 × ~25 行 + 十二处易错次序); 风险中(渲染主干，需逐变体比对首帧/空态/失败态三态截图)

**R21-B-02** · 变体状态文案表 3 份逐字同

- 位置: `drawer_tpl/01:25-33`·`02:25-33`·`03:27-35`(`STATE_TEXT` 20 键 + `SEEDING_STATES` 三元素)
- 类别: A
- 重复对象: qB 原始 `state` → 中文文案表两份常量(diff 实测**逐字节同**)
- 分歧点: 无。**注意**: 与 `decorate.js:151 stateText(m)` 不构成重复 —— 后者吃聚合 `kind`(6 值)，本表吃 qB 原始 state(20+ 值)，变体注释已声明"与经典链 stateText 的成员视图口径独立"
- 维护风险: qB 新增 state 值要三处同改；漏一处 → 同一状态在不同版式下文案不一致
- 建议收敛形态: 移入 `reg.helpers`(或 `reg.consts`)导出，三变体解构取用
- 预估收益/风险: 收益小(3×9 行); 风险极低

**R21-B-03** · 图标色调派生表 4 份

- 位置: `shared/drawer.js:1389-1404`(`icoTone` 方法) ↔ `drawer_tpl/01:128-141`·`02:120-133`·`03:143-156`(`ICO_TONE` 常量 + `icoTone` 箭头函数, 三份 diff 实测**逐字节同**，与 drawer.js 版仅"方法 vs 函数"之别)
- 类别: C
- 重复对象: sprite 图标名 → 色调类(`ico-t-io/cap/time/site/sw/id/path/state`)映射表 28 条，四份
- 分歧点: 无(表内容一致)。变体侧注释声明"自包含复制(变体不经 Vue, ctx 白名单无 icoTone)" —— 理由成立，但**收敛路径已存在**: 核心层 `reg.helpers` 已经是变体取公共物的正规通道(`dur`/`size`/`present` 就这么给的)，把表挂进 helpers 即可，无需动 ctx 白名单
- 维护风险: 新增图标(或改语义色)要改 4 处；漏一处 → 同一图标在常规页三种版式下颜色不同
- 建议收敛形态: `reg.helpers.icoTone(icon)` + 表随核心层发布；`drawer.js::icoTone` 改调同一份
- 预估收益/风险: 收益小-中; 风险极低(纯查表)

**R21-B-04** · HR 摘要三段式 3 份且能力已分叉

- 位置: `drawer_tpl/01:154-182`(`hrStrip`)·`02:184-209`(`hrBody`)·`03:209-232`(`hrLine`)
- 类别: B
- 重复对象: 种子详情 HR 摘要的**业务分支树**: `hr_excluded`→「已排除出 HR 管理」+`hr_safety_text` / `hr_triggered`→达标·未达标徽章 + `hr_req_ratio`·`hr_req_time`·`hr_state` 行 + `hr_site_need`·`hr_site_remain` 双判空
- 分歧点: **①文案三种**("H\&R 已达标"/"已触发 · 已达标"/"HR 已触发 · 已达标")；**②tone 值三套**(`is-info|is-done|is-pending` / `""|is-done|is-hr` / `is-info|is-done|""`)；**③能力已分叉**: 01 多 `hr_tag`/`hr_tag_done` chips，02 把 req 合成一行数组，**03 整段缺 `hr_state`**(`hr_safety_text`/`hr_reason` 两字段在 03 不展示) ⇒ 同一颗种子在 03 版式下少一行 HR 依据
- 维护风险: HR 文案/字段口径属业务话术，三份各自演化；③ 是**已存在的能力缺口**(非纯风格差异)
- 建议收敛形态: 抽业务数据层 `hrSummary(d)` 返回 `{tone, badgeText, reqLines:[], siteLines:[], tags:[]}`(纯数据，不含 HTML)，三个变体只负责排版；按 §07 B 类**只登记**，③ 的字段补齐需人裁定(可能是版式有意省略)
- 预估收益/风险: 只登记(建议优先裁定 ③)

**R21-B-05** · trackers 变体公共函数三件逐字同

- 位置: `drawer_tpl/04:162-171`(`bucketOf`) ↔ `05:163-172`(diff 实测**逐字节同**)；`04:179-186`(`hostOf` 函数声明) ↔ `05:195-201`(箭头函数, 函数体同)；`04:189`/`05:194`(`num` 谓词逐字同)
- 类别: A
- 重复对象: tracker 行装配的三个前置助手(bucket 分桶 / 从 URL 取 host / 非负数值谓词)
- 分歧点: `hostOf` 声明形态不同(语义等价)；`LAN_RE` 内网正则只在 04(05 无"内网"徽章，属版式差异)
- 维护风险: 分桶规则(`BUCKET` 表 + `bucketOf` 判据)改口径要两处同改；06 若也复制则三处
- 建议收敛形态: 移入 `reg.helpers`(`bucketOf` 需要 `BUCKET` 一并发布，或改成 `bucketOf(status)` 纯函数 + 表参数注入)
- 预估收益/风险: 收益小; 风险极低

**R21-B-06** · trackers 统计行"渐进省略"判据两套

- 位置: `drawer_tpl/04:203-204`(`b !== "off" || num(t.num_seeds)` / `b !== "off" || num(t.num_leeches)`) ↔ `05:212`(`num(t.num_seeds) || num(t.num_complete)`)·`05:215`(`num(t.num_leeches) || num(t.num_incomplete)`)
- 类别: B
- 重复对象: 「stats 行何时省略」同一展示事实两套谓词
- 分歧点: 04 按**分桶态**决定(off 桶且无种子数才省)；05 按**分量非零**决定(主值与副值任一非零即显示)。同一条 tracker 在两版式下的行数可能不同(如 off 桶带 num_seeds 时 04 显示、05 只在 num_seeds 非零时显示；num_complete 有值但 num_seeds 缺时 05 显示、04 显示"—")。另 04 第四项叫「完成下载」带 `suffix:"次"`，05 叫「完成」不带
- 维护风险: 同一数据两版式观感不一致；谓词口径无成文定义
- 建议收敛形态: 抽 `statsFor(t, bucket)` 单点(含省略谓词与文案)，两变体只决定"摆成卡还是摆成行"；按 B 类**只登记**，谓词归属需人裁定
- 预估收益/风险: 只登记

**R21-B-07** · 重报闸门行字段两份

- 位置: `drawer_tpl/04:225-226`·`05:229-230`(`gatedOk: rGate.ok, gatedTitle: rGate.ok ? "强制重新汇报" : rGate.title`)
- 类别: A(小项)
- 重复对象: 行对象上的闸门两字段赋值逐字同
- 分歧点: 无
- 维护风险: 极低
- 建议收敛形态: 随 R21-B-05 的 helpers 一并提供(如 `gateFields(rGate)`)
- 预估收益/风险: 收益很小

**R21-B-08** · 变体注册壳 12 份

- 位置: 每个 `drawer_tpl/*.js` 尾部 `const _render = render; reg.register({ id, tab, label, css, render(host, ctx){ wire(host); host.__dtCtx = ctx; _render(host, ctx); }, destroy })`(01:351-361·02:352-362·03:410-420·04:381-391·05:470-480·06–12 同形)
- 类别: A(族)
- 重复对象: 「注册 + 每次渲染前挂事件/存 ctx」的入口壳 12 份同构
- 分歧点: `tableId`/`rowsFn`/`rowAfterFn` 可选字段(桥变体才有)；05 的 ui 用 `Vue.reactive`
- 维护风险: 新增变体抄壳；`host.__dtCtx = ctx` 这行若漏 → 事件委托里 `h.__dtCtx` 为 undefined(静默失败，事件不响应)
- 建议收敛形态: 核心层加 `reg.define({...})` —— 内部即上述壳，变体只交 `{id, tab, label, css, render, destroy, tableId, rowsFn}`；`wire` 由核心层统一在首次渲染前调用一次(`wireEvents` 自带幂等守卫)
- 预估收益/风险: 收益中(12 处); 风险低

**R21-B-09** · KIT 三态 vs 变体自绘三态

- 位置: `shared/drawer_templates.js:286-308`(`KIT.loading/empty/error/table`) ↔ 9 个 bridge 变体各自手写 `dtNN-empty` 三态
- 类别: C
- 重复对象: 「加载/空/失败」三态 HTML 同一事实两套实现(核心 KIT 与变体自绘)
- 分歧点: KIT 产出 `class="empty"`(经典链类名)，变体需要 `.dtNN-empty` 作用域类(限宽/配色按变体走) ⇒ **不能直接复用**，需 KIT 支持类名前缀/变体覆盖参数
- 维护风险: 三态文案与图标口径两套(如 KIT.error 文案"加载失败"，变体是"…列表加载失败, 将在下次自动刷新时重试" —— 后者信息更全)
- 建议收敛形态: 并入 R21-B-01 的 `H.shell`：KIT 三态降级为其默认文案/图标，类名参数化。头注已声明"classic 四件全走这里, 变体可选迁移(本轮不强制)" —— **收不收敛属既定渐进计划，本轮只登记进度**
- 预估收益/风险: 收益中(与 B-01 同一动作); 风险低

**R21-B-10** · 折叠头键盘转发 3 份逐字同

- 位置: `drawer_tpl/01:337-343` ↔ `02:304-310`(diff 实测**逐字节同**)·`03:396-403`
- 类别: A(小项)
- 重复对象: `onKeyDown` —— Enter/Space → 跳过原生可点击元素 → `closest("[data-fold]")` → preventDefault + 转发 onClick
- 分歧点: 无
- 维护风险: P3-4 可访问性修正在三处各自复述；新增折叠版式再抄一份，漏"排除原生控件"那条会出现 Enter 双触发
- 建议收敛形态: 移入 `reg.helpers.foldKeydown(ev, onClick)`(或随 B-01 的 shell 提供)
- 预估收益/风险: 收益小; 风险极低

**R21-B-11** · 变体公共设施消费正例

- 位置: 12 变体全部消费 `H.skipUnchanged`(12/12)·`H.withScroll`(12/12)·`H.wireEvents/unwireEvents`(12/12)；9 个 bridge 变体消费 `H.anchFill`(9/9，12 与 90 无桥)；`reg.dtHtml/dtRaw` 全量转义(变体裸 `innerHTML` 零命中)
- 类别: D
- 为何不动: 报告 26-10-07-0845 的收口成果仍在生效，变体层没有绕过 helpers 自建实现；本轮的重复集中在 helpers **未覆盖**的面(三态壳/注册壳/ICO_TONE/STATE_TEXT/HR 摘要)，而非"已收口的又散回去"
- 预估收益/风险: 不动

## 分类计数

### R21-C 抽屉变体 peers+content+bridge(11 项: A5/B2/C3/D1)

**R21-C-01** · peers 双形态归一 5 处

- 位置: `shared/drawer_store.js:181-185`(`_fetchDrawerPeers` 落袋处)·`shared/drawer.js:1455`(`drawerPeerRows`)·`drawer_tpl/07:206-209`·`08:199-202`·`09:143-146`(`peerList`, 三份 diff 实测**逐字节同**)
- 类别: A
- 重复对象: `const p = (ctx.drawer && ctx.drawer.peers) || {}; return Array.isArray(p.peers) ? p.peers : Object.values(p.peers || {});` —— qB peers 可能是 dict 或数组，同一归一表达式五处
- 分歧点: 落袋处那份是对**原始响应**归一(注释"归一恒归数组形")，下游四处是对**已归一的 store 值**再判一次 —— 属防御式冗余；`drawer.js` 版无 `ctx.` 前缀
- 维护风险: 归一规则若变(如后端改为恒数组)，五处要一起改；下游再判让"落袋已归一"这个契约在阅读上失效
- 建议收敛形态: 落袋处归一即契约，下游统一走 `reg.helpers.peerList(ctx)`(读 store 不再判形态)；`drawer.js` 版同步改调
- 预估收益/风险: 收益中(5 处 + 契约澄清); 风险低

**R21-C-02** · peers 判据四件 3 份逐字同

- 位置: `drawer_tpl/07:211-237`·`08:204-227`·`09:148-171`(`flagTokens`/`isBad`/`bucketOf`/`isLanIp`；diff 三组比对**全部逐字节同**，08 仅少 `flagHas`)
- 类别: A
- 重复对象: peer 行的四项**业务判据**：`flags` 串切词、吸血嫌疑启发式(迅雷/XL)、flag→桶映射(u→choke / U→take / D→feed / 无→idle / ?→hand)、IPv4+IPv6 内网判定
- 分歧点: 无(08 无 `flagHas` 是因为无"标志筛选"交互)
- 维护风险: **这是判据不是版式** —— 吸血启发式规则调整(如新增 "Xunlei" 拼写)、flag 语义变化，必须三处同改；漏一处 → 同一 peer 在三种版式下分到不同桶(会出现"某版式显示为在传、另一版式显示为空闲")
- 建议收敛形态: `reg.helpers.peers = { tokens, isBad, bucket, isLan }` 随核心层发布；三变体解构取用
- 预估收益/风险: 收益中高(判据一致性); 风险低(纯函数，可加 node 单测锚定)

**R21-C-03** · FLAG_META 工具提示表 3 份逐字同

- 位置: `drawer_tpl/07:45-58`·`08:61-74`·`09:32-45`(10 个 flag → `{c: 类名, t: 说明}`；diff 实测**逐字节同**)
- 类别: A
- 重复对象: qB peer flags 图例表(类名 + 中文解释 10 条)
- 分歧点: 无
- 维护风险: 新增/修正 flag 说明要三处同改；说明文本是**用户可见话术**，三份漂移会让人在不同版式看到不同解释
- 建议收敛形态: 移入 `reg.consts.FLAG_META`(与 B-02 的 `STATE_TEXT`、B-03 的 `ICO_TONE` 同一动作)
- 预估收益/风险: 收益小; 风险极低

**R21-C-04** · content 变体公共件三件

- 位置: `drawer_tpl/10:158-160`·`11:147-149`·`12:118-120`(`fileList` 三份**逐字节同**)；`10:443-447`·`11:446-450`(`rowAfterFn`, 仅锚 key 差 `ui.selPath` vs `""`)；`10:252-260`·`11:210-218`(`prioBadgeClass`)
- 类别: A
- 重复对象: 取文件列表(`ctx.drawer.files || []`)、锚换代后 roving 恢复、优先级徽章类名派生
- 分歧点: `rowAfterFn` 的锚点(10 用选中行、11 用首行)；`prioBadgeClass` 细节未逐字比(两者均 p→类)
- 维护风险: 低-中(三件都短，但 `rowAfterFn` 漏 `H.rowRestore` 会让键盘用户每次重建后被甩回文档头 —— issue 26-10-07-0846 的复发面)
- 建议收敛形态: 前两件入 `reg.helpers`(`fileList`/`rovingRestore(el, key)`)，`prioBadgeClass` 随 C-08 的 PRIO 表一起
- 预估收益/风险: 收益小-中; 风险极低

**R21-C-05** · trackers 变体公共件三件第 3 份(R21-B-05 扩员)

- 位置: `drawer_tpl/06:143-151`(`bucketOf`)·`06:153`(`num`)·`06:154-160`(`hostOf`) —— 与 04/05 的同名件**逐字节同**，故 04/05/06 三份全同
- 类别: A(族延伸)
- 重复对象: 见 R21-B-05，本处确认 trackers 三变体**完整三份**
- 分歧点: 无
- 维护风险: 同 R21-B-05
- 建议收敛形态: 并入 R21-B-05 的 helpers 方案
- 预估收益/风险: 收益小

**R21-C-06** · content 目录树构建两份且聚合字段已分叉

- 位置: `drawer_tpl/10:161-216`(`newDir`/`buildTree`/`aggregate`/`findNode`) ↔ `12:121-174`(同四件)
- 类别: B
- 重复对象: 「qB `files[].name` 的 `/` 分隔路径 → 目录树 + 自底向上聚合」同一算法两份
- 分歧点: **节点模型已分叉** —— 10 的节点带 `dirs` 计数与 `hasAv`/`minAv` 布尔对(可用性"是否有值"靠显式标记)；12 无 `dirs`、改用局部 `avSet` 闭包变量 + `av` 字段。聚合结果语义相同(目录 = 子树最低可用性)，但**字段集不同** ⇒ 两份不能互换消费
- 维护风险: 树构建/聚合的口径修正(如大小重复计数、软链接、空目录)要两处同改；11 走 `derive`(扁平表 + path 前缀归并)是第三套算法 —— 三版式三实现
- 建议收敛形态: 抽 `buildFileTree(files, {withDirCount, withAv})` 纯函数(选项控制字段集)，三变体共享；按 B 类**只登记**，字段集统一需人裁定(12 的 treemap 可能真的不需要 dirs 计数)
- 预估收益/风险: 只登记(但建议至少把 `aggregate` 的可用性聚合统一，那是数据口径)

**R21-C-07** · trackers 分桶表两种形状

- 位置: `drawer_tpl/04:35-41`(`BUCKET`: `{err/warn/upd/ok/off}` → `{text, sev}`, 06:37-43 同) ↔ `05:42-50`(`GROUPS`: 同五键 → `{text, cnt}`)
- 类别: B
- 重复对象: tracker 五桶的**中文文案 + 附加值**同一张表两种形状
- 分歧点: 04/06 附 `sev`(排序权值: err0/warn1/upd2/ok3/off9)；05 附 `cnt`(分区副标题话术: "正在拖后腿 · 优先处理" 等)。同一桶的 `text` 五处完全一致 ⇒ 文案是同一事实，附加列是消费场景不同
- 维护风险: 新增第六桶(如 qB 未来加状态)要改两处形状；桶文案改动要三处(04/05/06)
- 建议收敛形态: 一张表 `{key: {text, sev, cnt}}`(全部列)，两处各取所需；按 B 类**只登记**
- 预估收益/风险: 只登记

**R21-C-08** · 文件优先级文案表 3 份(R21-A-06 佐证)

- 位置: `drawer_tpl/10:38`·`11:39`·`12:27`(`PRIO_LABEL` = `{0:"不下载",1:"正常",4:"高",6:"高",7:"最高"}`，三份 diff **逐字节同**)
- 类别: C
- 重复对象: 见 R21-A-06 —— 全仓该表共 **5 份**: `drawer.js:1424`(含 4)、`drawer_tpl/10·11·12`(含 4，三份同) → 四份一致；`drawer.js:913`(`setFilePriority`)是唯一**缺 4 档**的
- 分歧点: 4/5 含 4 档，1/5 不含 ⇒ R21-A-06 判 B 的依据在此加固：不是"两派势均力敌"，而是**一份孤立**
- 维护风险: 同 R21-A-06
- 建议收敛形态: 单表 `FILE_PRIO_TEXT` 五处消费(含 4)，`setFilePriority` 的 toast 顺带修正
- 预估收益/风险: 收益小; 风险极低

**R21-C-09** · 模块级 `_ctx` 间接层 5 处

- 位置: `drawer_tpl/10:249-250`(→`377` 赋值)·`11:207-208`(→`360`)·`12:249-250`(→`384`)·`07:402-403`·`08:239-241`
- 类别: C
- 重复对象: `let _ctx = null; const ctxOf = () => _ctx;` + render 期 `_ctx = ctx` —— "模板串里要用 ctx 但函数签名不带"的同一绕行写法五份(07/08 变体为 `fmtSizeOf`/`fmtSpeedOf` 两个具名包装)
- 分歧点: 命名(`ctxOf` vs `fmtSizeOf/fmtSpeedOf`)；07/08 注释明确"render 期只读引用, 动作链仍走 host._\_dtCtx"
- 维护风险: 模块级可变单例在"两个变体同时挂载"(合并双列)时的隔离性 —— 目前安全是因为每次 render 都重新赋值且同步用完，但这是**隐式时序契约**，无注释外的机械保证
- 建议收敛形态: 把 `ctx` 显式传进构建函数(多数函数已带 `ctx` 参数，`ctxOf` 只是给少数内联模板用的兜底)；或核心层提供 `H.setCtx(ctx)` 成对纪律
- 预估收益/风险: 收益小; 风险低-中(改动点分散在模板串附近，需逐点确认)

**R21-C-10** · content roving 键盘外层 3 份

- 位置: `drawer_tpl/10:517-529`·`11:517-525`·`12:497-512`(`onKeyDown`: 取 `[data-dt-key]` 行 → Enter/Space 切换选中 → `H.rowMove` 移焦 + preventDefault)
- 类别: A(族)
- 重复对象: roving 键盘的外层"取行/判目标/Enter 动作/移焦"四步 3 份；`H.roving/rowRestore/rowMove` 三件已是单点，但**外层胶水**仍各写
- 分歧点: Enter 的动作不同(10 切换选中并 rerender / 11 勾选 / 12 定位); 目标容器类名不同(`.dt10-list` 等)
- 维护风险: 与 R21-B-10 同类；`ev.target !== row` 那条"只认行容器自身持有焦点"的守卫漏一处 → 行内按钮的 Enter 被劫持
- 建议收敛形态: `H.rovingKeys(ev, {listSel, onActivate})` —— 守卫与移焦固定，动作注入
- 预估收益/风险: 收益小-中; 风险低

**R21-C-11** · 抽屉变体层正例(含 stub)

- 位置: `drawer_tpl/90-peers-stub-bridge.js`(测试专用 fixture: `?dtstub` 门控注册, 恒定 sig 保锚稳定不变量, 生产零观感)·九变体的 `H.anchFill`/`H.anchTouch` 桥锚纪律·`Vue.reactive` ui(04/07/08/09/10/11 六处，需要跨重渲染的嵌套态才用)·桥描述符 `rowsFn`/`rowAfterFn`(数据判据留变体、排序/列交互归引擎)
- 类别: D
- 为何不动: 90 是刻意最小化的验证件(注释即契约文档)；桥锚纪律与 rowsFn 分工是本项目最复杂的一处设计，当前"判据在变体、渲染归引擎"的切分经多次报障收敛而来
- 预估收益/风险: 不动

## 分类计数

### R22-A CSS 令牌与主题层(5 项: C2/D3)

**R22-A-01** · 令牌名集三份不同步

- 位置: `atlas/style.css`(:root **86** 令牌)·`console/style.css`(**89**)·`prism/css/tokens.css`+`prism/css/themes/*.css`(结构令牌 42 行 + 每主题 **68–73** 色令牌)
- 类别: C
- 重复对象: 同一份"设计令牌契约"在三个皮肤各声明一次(名集应完全一致，值才允许不同)
- 分歧点: **实测差集 = atlas 缺 `--font-ui`/`--font-display`/`--font-mono` 三个字体令牌**(console 89 与 prism 89 一致)。这正是 `drawer_templates.js:62` 头注写的"atlas 的 --font-ui/--font-display 不存在, 变体要写字体时用字面栈"的根因 —— 变体层因此被迫写 `var(--font-mono, ui-monospace, monospace)` 字面兜底
- 维护风险: 新增令牌要改 3 处(atlas/console 的 style.css + prism 的 tokens.css 或 5 个主题)；漏一处 → 该皮肤静默取 initial 值(颜色类令牌漏了会变成继承色，字体漏了变成默认字体，都不报错)；**当前已有 3 个令牌处于这种不对称状态**
- 建议收敛形态: ①短期加守阵测试断言"三皮肤令牌名集完全一致"(纯文本解析 `^\s*--[a-z0-9-]+:`，成本极低)；②中期把**结构令牌**(字体/几何/阴影/动效，与配色无关)收进 `/shared/tokens.css`，三皮肤继承 —— 与 R22-B/C 共用同一通道
- 预估收益/风险: 收益中(名集漂移已有实例); 风险低(纯声明层)

**R22-A-02** · 变体令牌白名单口径已过时

- 位置: `shared/drawer_templates.js:48-62` 头注「CSS 令牌白名单」—— 宣称 `--teal/--indigo/--cyan/--violet/--pink` **未入名单**(2026-10-06 求交集所得)，要求"未入名单的一律写字面值或 `var(--x, <字面 fallback>)`"
- 类别: C(文档契约 vs 代码事实的分歧)
- 重复对象: "哪些令牌可用"这一事实的两种表示 —— 头注白名单 vs 三皮肤实际声明
- 分歧点: **实测五主题 + atlas + console 全部声明了这 5 个令牌**(逐个 grep 计数=1)。白名单保守过度 ⇒ 变体 CSS 里出现 `color: var(--teal, #2dd4bf)` 这类"令牌 + 某皮肤色板字面兜底"的写法(01:105-111 共 6 处)，兜底值永不生效但会把特定皮肤的配色硬编码进变体
- 维护风险: 后续变体作者按白名单继续写字面色值 → 换肤不跟随；且字面兜底值给读者"这个令牌可能不存在"的错误信号
- 建议收敛形态: 更新头注(把 5 个令牌加入名单、删除字面兜底)；或反过来把白名单改成机械校验脚本(提取三皮肤令牌名集求交，与变体实际引用比对)
- 预估收益/风险: 收益小(文档纠正); 风险极低

**R22-A-03** · 五主题完整色表 5 份(主题机制本身)

- 位置: `prism/css/themes/{ocean,galaxy,frost,golden,orbit}.css`(68/68/72/73/68 令牌)
- 类别: D
- 重复对象: 五份几乎同构的令牌声明表(键集相同、值不同)
- 为何不动: **这就是主题机制的实现方式** —— 每主题一份完整色表，缺键时用 `var(--x)` 会静默回落 initial，所以"完整性"比"少写"重要。理论上可做 `base.css` + 差异覆盖，但会让"新增令牌只改一处"变成"新增令牌改一处 + 五个主题自动继承错值"(静默漂移)，权衡不划算
- 实测差异: 仅 3 处可选覆盖 —— `--font-display` 只 1/5 主题覆盖(注释声明"主题可覆盖 --font-display 换排版个性")、`--shadow-1/2/3` 只 2/5(亮色主题需不同阴影)。**无缺键**
- 预估收益/风险: 不动

**R22-A-04** · 共享 CSS 通道正例(收敛路径已存在)

- 位置: `/shared/console_hub.css`(1432 行，设置工作台，**三皮肤 index.html 均加载**)·`/shared/dt_table.css`(162 行，表格面背景/密度族单点，三皮肤均加载)
- 类别: D
- 为何不动: 这是本项目**已验证**的"结构规则共用、配色只走令牌"通道 —— R22-B/C 的重复规则收敛建议全部以它为模板(不需要新机制，只需把规则搬进同名 shared 文件并在三份 index.html 加一行 link)。记录为正例，避免收敛建议被当成"需要新建构建链"
- 预估收益/风险: 不动

**R22-A-05** · 主题引擎单点

- 位置: `prism/js/theme.js`(109 行，`THEMES` 注册表 + `resolve/apply/known` + `data-theme` 首帧同步 + 系统明暗跟随)
- 类别: D
- 为何不动: 单文件单职责，新增主题 = 加一个 css 文件 + 注册表一行；`stored()` 的 try/catch 与 `known()` 白名单校验是本项目偏好读取的标准式(与 R20-D-01 同族，未发散)
- 预估收益/风险: 不动

## 分类计数

### R22-B CSS 组件层(三套 components.css)(6 项: A4/C1/D1)

> 机器提名按行量: atlas↔console **81 行**、atlas↔prism **70 行**、console↔prism **11 行**，11 个克隆块，最大块 21 行。与 views/dialogs 层相比**单块更小、更分散** —— 组件层确实做了"每皮肤换视觉"，重复集中在**语义上必须一致**的族。

**R22-B-01** · 行状态色选择器族三份

- 位置: `atlas/css/components.css:312-390`·`console/css/components.css:276-345`·`prism/css/components.css`(同族) —— `.group-row.s-seeding …` / `.member-row.seeding …` 长选择器列表(每状态 ~8 个选择器)
- 类别: A
- 重复对象: 「行状态 → 整行子元素统一上色」的选择器族；值全走令牌(`var(--green)` 等)，故三皮肤**逐字相同**，仅落点行号不同(克隆块 13/15/18 行三处)
- 分歧点: 注释口径一致(`:not(.zero)` 排除空值占位、`:not(.hr-pending):not(.hr-done)` 排除 HR 标签)—— 这类排除条件正是"改一处漏一处"的高危面
- 维护风险: **这是后端 kind 枚举的第三份表示**(STATE_RANK 在前端 app.js、`_SHOW_STATE_RANK` 在后端, 见 R20-D-08) —— 新增状态要改: 后端 rank + 前端 rank + 三皮肤各一串选择器 + CSS 变量。漏改症状: 新状态行不上色(静默)
- 建议收敛形态: 移入 `/shared/`(如 `shared/row-state.css`)，三皮肤各加一行 link —— 与 `dt_table.css` 同一通道
- 预估收益/风险: 收益中(3 × ~80 行 + 一处高频改动点); 风险低-中(需确认三皮肤无后续覆盖规则，否则搬到更早的层会被覆盖)

**R22-B-02** · 右键菜单族三份

- 位置: `atlas/css/components.css:446-500`·`console/css/components.css:442-…`·`prism/css/components.css:190-…`(`.ctx-menu` 容器 + `.ctx-item` 项 + `.ctx-item .ico-*` 按操作族着色 + `.ctx-tick`/`.has-sub`)
- 类别: A
- 重复对象: 右键菜单的结构规则(定位 fixed / z-index / 最小宽 196 / 圆角 / shadow-3 / drop-in 动画 / 项 hover / 图标按族取色)
- 分歧点: 无(色值全令牌；克隆块 15/11 行)
- 维护风险: 菜单项增减或图标族扩充要三处同改；`min-width: 196px` 这类几何常量三份(与 `menu.js:313` 的 `202` 溢出阈值是同一族常量，见 R20-B)
- 建议收敛形态: 同 B-01，移入 shared
- 预估收益/风险: 收益中; 风险低

**R22-B-03** · 状态栏按钮/速度族三份

- 位置: `atlas/css/components.css:179-…`(`.sb-btn`)·`atlas/css/dialogs.css:435-…`(`.sb-sep/.sb-spd/.sb-spd .val/.spd-up/.spd-down`) ↔ console/prism 同名族
- 类别: A
- 重复对象: 状态栏三个控件族(按钮 / 分隔线 / 上下行速度胶囊 + 数字等宽 + 色义 today-up/down)
- 分歧点: **落层不一致** —— atlas 的 `.sb-btn` 在 components、`.sb-spd` 在 dialogs；prism 两者都在 views
- 维护风险: 同族规则跨文件分散，改速度胶囊颜色要先找在哪个文件(三皮肤答案不同)
- 建议收敛形态: 同 B-01(移入 shared)；落层不一致并入 C-08 处理
- 预估收益/风险: 收益小-中; 风险低

**R22-B-04** · 选项胶囊 `.opt-pill` 三份

- 位置: `atlas/css/components.css:679-700` ↔ `prism/css/components.css:362-…`(21 行克隆块，本层最大)
- 类别: A
- 重复对象: 删除/跳检对话框的选项胶囊(勾选点 / on 态 accent / danger 态 error / focus-visible / `.is-gated` 禁用语态)
- 分歧点: `.is-gated` 那条的注释记录了 issue 26-10-17-1703 的特异性教训(`:hover` 并集显式列出)，三皮肤同款
- 维护风险: 特异性修正在三处各自复述；新皮肤或新语态漏一条 → 置灰项 hover 又亮起来(该 issue 复发)
- 建议收敛形态: 移入 shared
- 预估收益/风险: 收益小-中; 风险低

**R22-B-05** · 组件层规则归属不一致(与 R22-C-08 同源)

- 位置: `modal.strip` 族 —— `atlas/console views.css` 各 7 处 ↔ `prism/components.css` 7 处；`hr-detail-table` —— `atlas/console dialogs.css` 各 26 处 ↔ `prism` **拆成 components 3 + views 23**
- 类别: C
- 重复对象: 同一批规则的"该放哪层"三皮肤答案不同
- 分歧点: 见上；prism 无 `dialogs.css`，把弹窗族分塞进 components 与 views
- 维护风险: ①找规则要试三个文件；②**级联顺序不同** —— prism 的 `modal.strip` 在 components 层(早于 views)，atlas/console 在 views/dialogs 层(晚于 components)，同名覆盖关系方向相反 ⇒ 同一个"后续覆盖"写法在三皮肤里生效结果可能不同
- 建议收敛形态: 统一为三文件分层(atlas 现状)，或统一把"语义规则"全移 shared、三皮肤只留配色；**不建议**在收敛规则时同时改分层(两个变量一起动无法定位回归)
- 预估收益/风险: 收益中; 风险中(级联顺序改动影响面大，需三皮肤逐页比对)

**R22-B-06** · 组件层"只换视觉"边界正例

- 位置: 三套 `components.css` 的头部注释与分区结构(按钮/输入/表格壳/菜单/状态栏…)，同名类在下游文件里以**令牌值差异**而非选择器差异实现换肤
- 类别: D
- 为何不动: 组件层是"三皮肤允许不同"的正常面 —— 圆角/间距/密度/字重本就该随设计语言变；重复的只是那些"语义必须一致"的族(已列 B-01~04)，其余差异是设计意图
- 预估收益/风险: 不动

## 分类计数

### R22-C CSS 视图与对话框层(9 项: A6/C2/D1)

> 机器提名全前端最高重复面集中在此: `atlas/views ↔ console/views` **272 行**、`atlas/views ↔ prism/views` **260 行**、`atlas/dialogs ↔ console/dialogs` **236 行**，合计约 990 行(占 css 克隆总量 1690 行的 59%)。**跨层错位匹配** `atlas/dialogs ↔ prism/views` 195 行、`atlas/dialogs ↔ prism/components` 121 行 —— 直接暴露 C-08 的分层不一致。

**R22-C-01** · qB 流量图控件族三份

- 位置: `atlas/css/views.css:473-530` ↔ `console/css/views.css:352-…`(67 行)·`prism/css/views.css:629-…`(59 行)
- 类别: A
- 重复对象: `.qb-tabs`(胶囊页签) `.qb-seg`(纵轴分段器) `.qb-tools`/`.qb-tools-label` `.qb-yaxis-input` `.qb-note/.qb-stale`(空态) `.qb-chart/.qb-chart-host` `.qb-statctl`(统计栏控件组)—— 点击/悬停/active/focus 全用令牌
- 分歧点: 无实质差异(克隆块差几行是因为注释行是否被计入)；`.hist-summary` 的 `align-items:center` 那条版式修正(2026-10-16 用户动议「统计栏未对齐」)三皮肤同步
- 维护风险: 流量图是本项目功能迭代最频繁的面之一，每轮 UI 调整要改三份；注释已多处写"三皮肤成对改"——**这是靠纪律维持的重复**
- 建议收敛形态: 移入 `/shared/`(如 `shared/qb-traffic.css`)；三皮肤各加一行 link，保留各自 `style.css` 里的令牌覆盖能力
- 预估收益/风险: 收益高(三份 × ~60 行 + 高频改动点); 风险低(纯结构规则，色值全令牌)

**R22-C-02** · 历史流量图 SVG 族三份

- 位置: `atlas/css/views.css:428-475`(39 行) ↔ `prism/css/views.css:591-…`；`.hist-summary/.hist-legend/.hist-tip/.hist-cross/.hist-dot`
- 类别: A
- 重复对象: 磁盘历史曲线(SVG)：十字虚线 / 圆点描边 / tooltip 定位(含 `.flip` 翻向) / 图例 / 摘要行
- 分歧点: 无
- 维护风险: 与 C-01 同一族(同一功能两块图)，收敛应同批做
- 建议收敛形态: 并入 C-01 的 shared 文件
- 预估收益/风险: 收益中; 风险低

**R22-C-03** · HR 明细表族三份(prism 内还拆两层)

- 位置: `atlas/css/dialogs.css:113-173`(60 行) ↔ `console/css/dialogs.css:109-…`(逐字节)；prism 同族被拆到 `prism/css/components.css:3 处` + `prism/css/views.css:23 处`
- 类别: A
- 重复对象: HR 状态页明细表：`.hr-sub`(副行等宽小字) `.hr-pres`(在列/退役徽章三态) `.sortable`(表头排序) `.arrow`(绝对定位箭头，含 2026-10-06 版式修正长注释)
- 分歧点: 仅落层(见 R22-B-05)
- 维护风险: 箭头绝对定位那条注释写着"别改回 inline-block，也别补内层 v-if(切换排序列时标题会左右跳)" —— 这类教训复述在三份里的两份，prism 那份被拆散后注释是否完整需核
- 建议收敛形态: 移入 shared
- 预估收益/风险: 收益中(60 行 ×2 + prism 26 处); 风险低

**R22-C-04** · HR 悬浮弹层族三份

- 位置: `atlas/css/dialogs.css:526-605`(79 行，本层最大块) ↔ `prism/css/views.css:1019-…`；`.hr-pop`/`.hp-arrow`(定位 + 上/下翻向)/`.hp-head/.hp-dot`(四态色)
- 类别: A
- 重复对象: HR 档位悬浮弹窗的结构与箭头几何(`bottom:-5.5px` 这类半像素值三份)
- 分歧点: 无
- 维护风险: 与 `hr.js::_hrPopPlace`(R20-E-01)是**同一浮层的 CSS/JS 两半** —— CSS 箭头位置改了三份、JS 夹取改了六份，一处视觉缺陷要动九处
- 建议收敛形态: 移入 shared(与 R20-E-01 的 JS 收敛作为同一个"浮层"议题排期)
- 预估收益/风险: 收益中; 风险低

**R22-C-05** · 弹窗语气/标题条族三份

- 位置: `atlas/css/views.css:333-370`(37 行) ↔ `console/css/views.css:230-…`、`prism/css/components.css`；`.modal.tone-error/.tone-warn`、`.modal.strip`、`.modal-detail-row.is-warn/.is-error/.d-label`
- 类别: A
- 重复对象: 弹窗语义配色(标题着色 / strip 左侧色条 `inset 3px 0 0` / 明细行 level 着色)
- 分歧点: 落层不一致(见 R22-B-05)
- 维护风险: 2026-10-19 新增的 `tone: "warn"` 语义(跳检降档，见 drawer.js `_skipCheckDialog`)要三皮肤同步；漏一处 → 跳检框在某个皮肤下仍是红色危险档
- 建议收敛形态: 移入 shared
- 预估收益/风险: 收益中; 风险低

**R22-C-06** · 抽屉壳族三份

- 位置: `atlas/css/dialogs.css:50-100`(28 行) ↔ `console/css/dialogs.css:50-…`、`prism/css/views.css`；`.drawer-close` `.drawer-tabs`(button 下划线页签) `.drawer-body` `.drawer-body.is-traffic`
- 类别: A
- 重复对象: 详情抽屉的外壳几何与页签态
- 分歧点: 无
- 维护风险: `.drawer-body` 的 `padding: 14px 18px 20px` 与 prism 的 `padding-bottom: 8px` 修正(2026-10-16 收紧统计栏)是同一轮改动同步到三皮肤
- 建议收敛形态: 移入 shared
- 预估收益/风险: 收益小-中; 风险低

**R22-C-07** · 主表行布局 + 站点 chip 状态族三份

- 位置: `atlas/css/views.css:250-294`(44 行，`.group-row > :first-child` 网格行布局)·`atlas/css/views.css:114-150`(37 行，`.site-chip.sa-*` / `.m-site.sa-*` / `.search-hit` / `.sx-pending` 动画)；console/prism 同名族
- 类别: A
- 重复对象: ①主表行的网格定位与四态(expanded/partial/search-hit)背景；②站点 chip 的三态色(no-conf 警告 / tracker 错误 / 搜索命中)与脉冲动画
- 分歧点: 无
- 维护风险: 行布局是列宽拖拽与 `gridStyle` 的耦合面(style.css 头注已警告"类名不得改名")，三份同改；`sa-*` 三态由后端站点审计字段驱动，新增态要三处加
- 建议收敛形态: 移入 shared
- 预估收益/风险: 收益中(81 行); 风险低-中(主表布局属高频视觉面，需三皮肤截图比对)

**R22-C-08** · 三皮肤分层结构不一致(prism 合并 dialogs)

- 位置: 加载链 —— `atlas/index.html:10-12`(components → views → dialogs)、`console/index.html:13-15`(同)、`prism/index.html:18-19`(components → views，**无 dialogs.css**)；文件规模 atlas 700+649+623、console 669+479+549、prism 728+1097(0)
- 类别: C
- 重复对象: "三层分层(组件/视图/对话框)"这一结构性事实，prism 用两层表达
- 分歧点: prism 的 dialogs 族被拆到 components(modal.strip 7 + hr-detail-table 3)与 views(其余)；**级联顺序因此不同** —— prism 的弹窗族比另两皮肤更早介入级联，同名规则的覆盖方向相反
- 维护风险: ①跨皮肤克隆出现大量"错位匹配"(atlas/dialogs↔prism/views 195 行)，机器提名把真重复淹没在错位块里；②"后续覆盖"写法在三皮肤生效结果可能不同(隐性行为差异)；③找规则要试三个文件
- 建议收敛形态: **先统一分层再谈收敛** —— 建议恢复 prism 的 dialogs.css(把 components/views 里的 dialogs 族迁回)，使三皮肤文件职责一致；这一步本身会消掉约 300 行"错位克隆"的机器噪音。属结构调整，需单独排期与三皮肤回归
- 预估收益/风险: 收益中-高(可读性与后续收敛的前提); 风险中(级联顺序重排，需逐页比对)

**R22-C-09** · 视图层注释契约正例

- 位置: 三套 `views.css` / `dialogs.css` 的段头注释大量记录"这些类名与 JS 耦合不得改名"(网格列数须与 rows 一致、`.search-hit`/`.ctx-menu` 供逻辑挂钩、`th .arrow` 不得回 inline-block、`.opt-pill.is-gated` 特异性)、以及每条版式修正的日期与用户动议出处
- 类别: D
- 为何不动: 这些注释是**防回退的唯一载体**(无视觉回归测试)，收敛搬家时必须整段随规则一起搬 —— 本轮建议里已逐条标注"注释随行"
- 预估收益/风险: 不动


### R23-A 模板上半(dialogs 族·dock·topbar·statusbar·ctx-menus·popovers·overlays)(15 项: A7/B3/C3/D2)

范围(实测 1585 行/12 件): `dialogs.html`(137)·`dialogs-mgr.html`(284)·`move-dialog.html`(62)·`popovers.html`(367)·`ctx-menus.html`(178)·`topbar.html`(235)·`statusbar.html`(81)·`dock.html`(10)·`groups.html`(63)·`torrents.html`(29)·`shows.html`(90)·`overlays.html`(49)。
机器提名对照: jscpd markup 仅 3 克隆(其中 `xtpl-cells.html` 内部 11 行归 R23-B), 本子轮的 15 项**全部来自结构线索 grep + 精读** —— 再次印证 markup 侧的字面克隆率对模板族几乎无效(模板骨架是"参数化后的同构", jscpd 的 token 阈值看不见)。

骨架族实测计数(`grep -c` in `tpl/`): `maskDownSelf` 10 / `class="modal-title"` 11 / `add-dialog-x` 9 / `modal-actions` 11 / `ce-placeholder` 8 / `class="pop-menu` 7 / `opt-pill` 8 / `add-input-row` 6 / `transition name="pop"` 13 / `ctx-item` 5 / `row-pad` 6 / `aq-table` 5。

**R23-A-01** · combobox 输入行 + 候选面板骨架 5 处逐字同
- 位置: `dialogs-mgr.html:56-84`(保存路径)·`96-115`(分类)·`120-141`(标签)·`move-dialog.html:34-54`(movePath)·`popovers.html:66-86`(metaCat)
- 类别: A
- 重复对象: 整段"`.add-input-row` + `<input>`(focus/click.stop/input/focusout/keydown 五绑) + `.add-pop-clear` 清空钮 + `<transition name="pop">` + `.pop-menu.add-pop` + `pop-item`(on/data-hi/mousedown.prevent/mousemove) + `pop-empty`"，约 **18-22 行 × 5 = ~100 行**
- 分歧点: 五个标识符族 —— v-model 名(`addSavePath`/`addCategory`/`addTags`/`movePathInput`/`metaCatInput`)、菜单开合(`addPathPop`/`addCatMenu`/`addTagMenu`/`movePathMenu`/`metaCatMenu`)、高亮索引(`*Hi`)、过滤产物(`addCatFiltered()`/`addTagFiltered()`/`metaCatFiltered()`/直用数组)、点选(`pickAddPath`/`pickAddCat`/`pickAddTag`/`moveApplyPath`/`metaSetCategory`)、`comboHoverIdx('path'|'cat'|'tag'|'move'|'meta', …)` 的 key 字面。另有细分歧: 保存路径与 move 有 `pop-head` 计数头, 分类/标签/meta 无; move 无 `has-clear` 清空钮; 图标有无(路径 folder-open / 标签 i-tag / 分类与 meta 无图标 / meta 多一个"无分类"预置行)
- 维护风险: **这是全项目 bug 最密集的一处**。`@mousedown.prevent` + `@click.stop` + `label` 双修饰符 + 40ms 合帧的"缺一即回归"注释在这 5 处**各写一遍**(同一段坑档 `pitfalls/web-ui/combobox-focusout-close` 的 5 份拷贝), 任何一次只在 4 处修 = 第 5 处静默复发; 而 `comboHoverIdx` 的 key 字面是**字符串**, 拼错不报错(只是悬停高亮失效)。另: 显隐分支有三种写法(`addPathPop` 布尔 / `addCatMenu` 布尔 / `@input` 内 `hi=-1; menu=true` 连写), 行为一致但收敛后必须逐一对齐
- 建议收敛形态: 抽**一层模板片段**而非组件 —— `tpl/xtpl.html` 已有 `<template id="tpl-*">` 分片先例, 建议加 `tpl-combo-input`, 参数 `{ model, menu, hi, options, onPick, comboKey, icon, emptyText, headText }`, 五处改为 `<aq-combo …>`(Vue 3 全局组件已有 `aq-table`/`aq-group-cells` 等 8 个先例, 注册表在 `table.js`/`app.js`)。**先决条件**: 状态层已单点(`comboHoverIdx` 按 key 分派即证据), 缺的只是模板层 —— 与 R21-A 的 `reg.helpers` 同模式, 风险低于外观
- 预估收益/风险: 收益高(~100 行 → ~25 行, 且消灭 5 份坑档拷贝与 5 个字符串 key); 风险中(五处交互热路径, 须逐处 delay>=120ms 走查 + 三皮肤各一遍)

**R23-A-02** · 对话框外壳三段式(mask 手势 / title 头 / actions 栏)11 处
- 位置: mask 双行 10 处 —— `dialogs-mgr.html:5-6`·`201-202`·`243-244`、`dialogs.html:3-4`、`move-dialog.html:14-15`、`popovers.html:2-3`·`48-49`·`114-115`·`205-206`·`339-340`; title 头 11 处 —— `dialogs-mgr.html:8-14`·`204-210`·`246-252`、`dialogs.html:6-12`·`70-76`、`move-dialog.html:18-24`、`popovers.html:5-11`·`51-57`·`121-126`·`208-219`·`342-348`; actions 栏 11 处 —— `dialogs-mgr.html:189-195`·`235-238`·`280-282`、`dialogs.html:55-60`·`125-133`、`move-dialog.html:57-60`、`popovers.html:39-41`·`109-111`·`188-200`·`362-365`
- 类别: A
- 重复对象: ①`<div class="modal-mask" @mousedown="maskDownSelf" @mouseup.self="maskCloseIfArmed(…)">` 双行 —— 10 处**除关窗方法名外逐字同**; ②`<div class="modal-title">` + `<svg class="ico ico-sm"><use href="#i-XXX">` + `<span>标题</span>` + `<button class="bt icon add-dialog-x">` + `#i-close` 五段 —— 11 处; ③`<div class="modal-actions">` + `ghost`/`primary` 双钮尾 —— 11 处
- 分歧点: ①的差异只有关窗方法(`closeStats`/`closeMove`/`closeMgr`/`closeMeta`/`resolveModal(false)`/`closeHistory`/`closeKbHelp`/`closeAddTorrent`/`closeDirBrowse`); ②的差异 = 图标 id + 标题文本 + 关闭方法, 另有 **3 处异形**: `hist-modal` 的 title 里插了 `ce-spacer` + `hist-tabs` 分段钮, `kb-help` 用 `<h3>` 而非 `<span>` 包标题(全文唯一), `speed-pop` 虽是 `.modal-title` 但无 mask(无遮罩浮层); ③的差异 = 钮数与语义(单"关闭"2 处 mgr / ghost+primary 5 处 / 带 extraText 三钮 1 处 / 带 spin 态 2 处)
- 维护风险: ①这是**2026-10-03 报障的修复载体**(`@click.self` 会把"输入框拖选文字、抬手落在遮罩"判成点空白关窗), 结论写在 `dialogs-mgr.html:2-4` 一处注释里, 另外 9 处只有代码没有出处 —— 后人改回 `@click.self` 只需动一处; ②`kb-help` 的 `<h3>` 让同一头骨架的标题元素有两种, 若日后给 `.modal-title > span` 加样式/断字规则, kb-help 不生效; ③`add-dialog-x` 在 `historyOpen` 与 `kb-help` 两处写成 `class="bt icon"`(缺 `add-dialog-x`), 意味着既有的"关闭钮样式单点"实际有 2 处漏网
- 建议收敛形态: 抽 `<aq-modal>` 组件(参数: `open`/`close`/`icon`/`title`/`width-class`/`body-class`/`actions` slot), 三段一并收。**先决**: ①③是纯机械收敛(10 处 mask + 11 处 actions), ②需为 hist-tabs / h3 保留 slot 口 —— 建议 `title` slot 默认为 `<span>{{title}}</span>`, hist/kb-help 走 slot 覆盖。Vue 3 全局组件注册点已存在(`table.js::AQ_TABLE_COMPONENT` 模式), 无需构建链
- 预估收益/风险: 收益高(三段共 ~90 行 → ~30 行, 且把"点空白关窗"的唯一正确写法固化成组件内部实现, 从"要记住"变成"写不出来"); 风险中(11 个对话框的关窗行为, 须逐个验证"拖选文字抬手套"场景 + Esc 退栈链名单同步)

**R23-A-03** · 管理对话框(标签 / 分类)两份同构
- 位置: `popovers.html:2-43`(mgrOpen==='tag', 42 行) ↔ `dialogs-mgr.html:243-284`(mgrOpen==='category', 42 行)
- 类别: A
- 重复对象: 完整对话框骨架 —— mask/title/`add-dialog-body`/`ce-placeholder` 双态(`mgrLoading` → `mgrError`+重试)/`mgr-list` + `mgr-row`(`mgr-name` + `mgr-acts` 删除钮)/`mgr-empty` 空态/`mgr-new` 新建行/actions 单"关闭"钮, 约 **40 行逐字同**
- 分歧点: ①分支值 `'tag'`/`'category'`; ②图标 `#i-tag`/`#i-folder` 与标题; ③数据源 `mgrTags`(string[]) vs `mgrCategories`(`{name, save_path}[]`); ④分类多一列 `mgr-sub`(保存路径 + `dim` 态)与一个"改路径…"钮; ⑤分类新建行多一个"保存路径(可空)"输入框; ⑥分类**无** `mgr-hint` 提示行(标签有"H&R/集数/MISSING 自动规则"那条); ⑦加载态文案"正在加载标签…"/"正在加载分类…"
- 维护风险: `mgrBusy`/`mgrLoading`/`mgrError`/`loadMgr()`/`closeMgr()` **五个状态与方法是共用的**(同一份 `dialogs.js` 逻辑层), 而模板是两份 —— 改共用逻辑时两处都要复查; ⑥的分歧无注释说明为何分类不需要提示行(可能只是漏了), 属无人值守的漂移
- 建议收敛形态: 合并为单份 + `mgrDef` 数据表(`{kind, icon, title, loadingText, loadText, rows: [{key,label,sub}] , newFields: [...], hint}`), 定义放 `dialogs.js` 单点(与 `filterDefs`/`tableDefs` 同模式); 模板留一份 `v-for`。若嫌重, 最低成本 = 把 ⑥ 补齐 + 在两处各加一行 `<!-- 与 X 同构, 改一处必须改另一处 -->` 交叉引用
- 预估收益/风险: 收益中(-40 行 + 消除 ⑥ 类静默漂移); 风险低(单次开窗 UI, 无热路径)

**R23-A-04** · `.ctx-item` 渲染骨架 5 份(注册表已单点"项集", 骨架未单点)
- 位置: `ctx-menus.html:38-40`(multi)·`48-50`(episode)·`79-81`(member)·`95-97`(group) —— 4 份 **逐字同**; `73-75`(member 子面板, 遍历变量 `sit` 而非 `it`)为第 5 份
- 类别: A
- 重复对象: `<div v-else class="ctx-item" :class="[it.cls, { 'is-gated': it.gated }]" :title="it.title" :data-item="it.id" @click="ctxRun(it)">` + `<svg class="ico ico-sm" :class="it.icon.cls" …><use :href="it.icon.use">` + `<span class="ctx-text">{{ it.label }} <span v-if="it.note" class="ctx-note">{{ it.note }}</span></span>`, 3 行 × 5
- 分歧点: 只有 `ctxItems('<支>')` 的支名(multi/episode/member/group)与遍历变量名(it/sit)不同
- 维护风险: **这正是模板注释自己警告的那件事**。`ctx-menus.html:5-15` 写着"项集/顺序/显隐/跨层全部由注册表驱动…改项集改注册表单点, 别回本模板逐项直写(直写 = 四支人肉奇偶, 复发路径即 pitfall ctx-menu-branch-parity)" —— 项集侧确实已收敛到 `window.AQB_CTX_MENU_REG`, 但**渲染骨架仍是四支各一份**。当下次给 `.ctx-item` 加属性(如 `:aria-disabled`、`:data-note`)或改图标类名时, 只改 3 处即出现"某一支的菜单项少一个属性"的同族缺陷, 症状与注释里记录的那次用户报障同类
- 建议收敛形态: 四支合一 —— `ctxMenuKind()` 已返回支名(`ctx-menus.html:3` 就绑了 `:data-kind`), 直接用 `ctxItems(ctxMenuKind())` 单一 `v-for`; `multi`/`episode`/`hash`/`else` 四条 `<template v-if>` 退化为一条。`submenu` 分支(`63-78`)保留独立判断(它是唯一带子面板的 kind)
- 预估收益/风险: 收益中高(-10 行, 但消灭"四支奇偶"这个**有前科**的复发面); 风险中(右键菜单是高频交互, 四支项集/顺序须逐一比对 e2e `menus.spec` 的 `data-kind`/`data-count` 断言)

**R23-A-05** · 窗口化行容器三明治 4 份 + 空态块 3 份
- 位置: 行容器 —— `groups.html:19/22-27/45`(group 行 + 上下 row-pad)·`groups.html:33-42`(member 明细)·`torrents.html:6-15`(torrent 行)·`shows.html:38-47`(ep 成员明细); 空态 `<div class="empty">` —— `groups.html:47-53`·`torrents.html:16-22`·`shows.html:74-80`
- 类别: A
- 重复对象: ①`<div v-if="XPadTop" class="row-pad" :style="{ height: XPadTop + 'px' }" aria-hidden="true">` 上下两道 + 中间 `v-for="m in visibleX"` 行 + 行内 `<aq-X-cells :cols="visibleXCols" :m>`; ②空态: `<div v-if="!filteredX.length" class="empty"><svg class="ico"><use href="#i-inbox"></svg><span>{{ searchQuery.trim() ? (searchNegativeOnly ? '只…' : (searchBuilding ? '正在构建…' : '无匹配…')) : (filtersActive ? '当前筛选下没有…' : '暂无…') }}</span></div>`
- 分歧点: ①每处 4 个标识符(`PadTop`/`PadBottom`/`visibleX`/`gridStyle('X')`) + 行类名与事件集不同(group/torrent 有 dblclick 开抽屉, show-ep 行无 dblclick); ②三分支文案的**末梢**不同(无匹配种子/剧集、暂无种子/l10nGroup/剧集可展示), 且 `groups` 的"正在构建文件索引…"分支在 `torrents` 缺失(shows 有)
- 维护风险: ①`row-pad` 的几何是 P1-2 行窗口化契约(占位撑总高), 四处手写意味着一处改了 `aria-hidden`/`px` 写法另三处不同步不会报错, 但会让滚动条长度算法在两视图间不一致; ②空态的四层嵌套三元是**用户可见文案**, 三份已经出现分支集合不同(torrents 少一个 searchBuilding 分支)—— 这属于"看起来一样所以没人核对"的典型
- 建议收敛形态: ①抽 `<aq-vlist :rows :pad-top :pad-bottom :row-class :cells="'aq-group-cells'" :cols>` 组件(窗口化热路径须注意"不引入逐行组件实例"的既有纪律 —— `groups.html:13` 注释明确"组件只包表壳, 窗口化热路径不引入逐行组件实例", 故此条**只能收敛 row-pad 与表壳, 不能收敛行本身**; 收敛范围收窄为 `<aq-row-pad :top :bottom>` 双层 + 复用 `aq-table` 的组合); ②空态抽 `<aq-empty :mode :filtered :building :negative :kind-label>` 单组件, 先把三分支集合对齐再收
- 预估收益/风险: 收益中(-25 行 + 消除空态文案分支漂移); 风险低-中(row-pad 是纯几何, 空态是纯展示; 但行窗口化有性能纪律, 收敛不得越界)

**R23-A-06** · `.opt-pill` 切换胶囊模板实例 8 处(单项版是多项版的退化特例)
- 位置: `dialogs-mgr.html:148-167`(添加种子选项区, **5 个逐字同的 opt-pill**)·`popovers.html:171-174`(单项 `modal.checkbox`)·`popovers.html:181-186`(多项 `modal.checks`)
- 类别: A
- 重复对象: `<button type="button" class="opt-pill" :class="{ on: X }" role="switch" :aria-checked="X" @click="X = !X"><span class="opt-dot"></span><span>文案</span></button>` —— 5 份在 dialogs-mgr 内**逐字同**(仅 `addStart`/`addSkipCheck`/`addSequential`/`addFirstLast`/`addTmm` 五个变量与文案不同, 其中 `addSkipCheck` 那份多 `danger` 类); `modal.checkbox`(`171-175`)是 `modal.checks`(`180-187`)的单元素退化 —— 同一 DOM 形状, checkbox 版少 `is-gated`/`:title`/`:aria-disabled`/`c.disabled ||` 短路
- 分歧点: 数据驱动 vs 硬编码(5 个按钮各写一遍) ;单项版 vs 多项版(前者是后者的特例, 但代码是两份)
- 维护风险: ①5 个硬编码胶囊的 `role="switch"`/`:aria-checked` 契约重复 5 遍 —— 若日后统一改 `aria-pressed`(更符合 toggle button 语义)要改 6 处(CSS 侧 `.opt-pill` 另见 R22-B-04); ②`modal.checkbox` 缺 `is-gated` 能力, 意味着"置灰真禁点击"这条已在 issue 26-10-17-1703 定案的规矩对单项选项**没有实现**, 哪天需要"置灰的单选项"就得现加一遍
- 建议收敛形态: ①五项改 `v-for="o in addOpts"` + 数据表(定义放 `add_torrent.js`, 与 `filterDefs` 同模式); ②`modal.checkbox` 并入 `modal.checks`(`_openModal` 里把 `checkbox` 归一成 `checks: [{key:'_one', label: checkbox, checked, disabled:false}]`), 模板只留 `181-187` 一份。②是纯逻辑归一, 无 UI 变化
- 预估收益/风险: 收益中(-12 行 + 消灭"单项无置灰能力"的能力缺口); 风险低(纯展示/单次开窗)

**R23-A-07** · `aq-table` 表壳调用 5 处 / `detailHead` 四行逐字同 2 份
- 位置: `<aq-table>` —— `torrents.html:2-3`·`groups.html:14-15`(groupHead)·`groups.html:31-32`(detailHead)·`shows.html:3-4`(showHead)·`shows.html:35-36`(detailHead); 其中两组 `detailHead` 逐字同: `ref="detailHead" table-id="detail" :cols="visibleDetailCols" :sort-key="detailSortKey" :sort-dir="detailSortDir" :drag="colDrag"`
- 类别: A
- 重复对象: 5 处 `<aq-table>` 属性串, 与 2 处完全相同的 detail 表壳
- 分歧点: 只有 `ref`/`table-id`/`cols`/`sortKey`/`sortDir` 的绑定名不同
- 维护风险: `aq-table` 是新抽出的单点(`table.js` + `tpl/xtpl.html#tpl-aq-table`, 计划 26-10-11-1722 P1/P2 的成果), 5 处属性串是它的**调用面**: 若组件加必填 prop(如 `:drag`)或改 `sortKey/sortDir` 打包形状, 5 处都要改; 但更值得注意的是 `detailHead` 在 `groups` 与 `shows` 两处 `ref` **同名** —— 两视图互斥渲染故不冲突, 但它是一个隐性前提(切视图时 ref 数组会短暂同时存在), 属需要有注释守住的不变量, 目前无注释
- 建议收敛形态: `detailHead` 两处抽成 `<aq-detail-head>`(仅 4 行, 收益低)—— 建议**不改**这 4 行, 改为在两处各加一行注释说明 ref 同名前提; 5 处属性串保持(它们已是单组件的调用, 收敛不到更少)
- 预估收益/风险: 收益低(4 行); 风险极低。列此项的目的是**给 S5 归档留判据**: `aq-table` 化已完成(5/5), 模板侧表壳重复已消, 本族不再列为待办

**R23-A-08** · `.modal-details` 行式键值两套(key 口径 / title 口径 / 复制钮有无)
- 位置: `popovers.html:135-141`(`modal.verdict`, 跳检预检区) ↔ `popovers.html:147-159`(`modal.details`, 删除确认目标区)
- 类别: B
- 重复对象: `<div class="modal-detail-row" :class="[d.tone && 'is-' + d.tone, { wide: d.wide }]">` + `<svg v-if="d.icon">` + `.d-label` + `.d-value` 四段同构
- 分歧点: ①`:key` 口径不同 —— verdict 用**索引** `:key="i"`, details 用**标签** `:key="d.label"`; ②`:title` 口径不同 —— verdict `String(d.value)`, details `d.hint || String(d.value)`; ③details 每行带 `d-copy` 复制钮(`String(d.value||'').length` 门控), verdict **无**复制钮; ④verdict 有 `wide` 之外无 `hint`
- 维护风险: **②是本项的真问题**: `d.hint`(2026-10-18 加的"实际占用"去重解释口径)只对 details 生效, verdict 的行若将来也带 hint 会被静默忽略(值正确、提示丢失, 不报错)。①的索引 key 在 `modal.verdict` 重新计算时会整段重建 DOM(无 `v-for` 复用损失, 但若 verdict 内将来加入输入控件会丢焦点)。③的门控表达式 `String(d.value || '').length` 与 `d.value` 为 `0` 时的边界(数字 0 → `String(0||'')` = `''` → 不出复制钮)**在 details 里是 bug 级边界**, verdict 因无此钮而不受影响 —— 即两份拷贝让这个边界只暴露在一半
- 建议收敛形态: 合一为一份 `v-for`, `d.copy !== false && String(d.value ?? '').length` 门控 + 统一 `:key="d.label || i"` + 统一 `d.hint ||`. 顺带修 `||` → `??` 的 0 值边界(与 Phase 1 后端的 `||`/`??` 族同源, 见 `26-10-10-backend-dup-code-audit.md`)
- 预估收益/风险: 收益中(-13 行 + 修一处 0 值边界 + 消灭 hint 半生效); 风险低(纯展示行)

**R23-A-09** · `.pop-item` 的可访问性契约三套(role / tabindex / 键盘 / aria)
- 位置: `topbar.html:76-84`(列选择器项: `role="button"` + `:tabindex` + `:aria-pressed` + `@keyup.enter`)·`topbar.html:207-215`(筛选器项: 同前 + `@keyup.space.prevent`)·`topbar.html:139-145`(UI 切换项: `<a href>` 无 `aria-pressed`, 靠 `:class="{on}"`)·`dialogs-mgr.html:74-79`/`107-111`/`131-135` 与 `move-dialog.html:44-49`/`popovers.html:74-82`(combobox 候选项: `<div>` 无 `role`/`tabindex`/`aria`, 键盘走 `@keydown` 自绘 + `:data-hi`)
- 类别: B
- 重复对象: "可点击的列表行"这一交互原语, 用 `.pop-item` / `.ctx-item` 同一套 CSS 类, 但可访问性契约分成三套
- 分歧点: ①列选择器/筛选器走**原生焦点 + 键盘**(tabindex + keyup); ②UI 切换走**链接语义**(可 Ctrl+点击新标签, 但无 pressed 态); ③combobox 走**自绘高亮**(`data-hi` + 容器 keydown, 项本身不可聚焦 —— 这是 ARIA combobox 的**正确**做法, 需配 `role="listbox"`/`role="option"`/`aria-activedescendant`, 目前都没有)
- 维护风险: ③是实际缺陷面 —— 自绘高亮的 combobox 若不标 `role="option"` + `aria-activedescendant`, 读屏用户听不到"当前高亮第几项"; 而 ①的实现方式(tabindex 进每个项)与 ③(项不可聚焦)是**互斥的两条路**, 现状是三套并存且无注释说明为何不同。日后统一键盘策略时会撞上"改 ① 影响 combobox 的 Tab 序"这类交叉
- 建议收敛形态: **先立契约再谈收敛** —— 按交互原语分三类并在 CSS 段头注释(+ 一处 conventions 记录)写清判据: (a) 菜单式(`.ctx-item`, 项可聚焦 + roving tabindex, 已有 `roving` helper 见 drawers)、(b) 选择式(`.pop-item` + `role="option"`, 自绘高亮 + `aria-activedescendant`)、(c) 导航式(`<a>`)。然后 combobox 五处统一补 `role="listbox"`/`option`/`aria-activedescendant`(可直接复用 R21-A 的 `reg.helpers.roving`)
- 预估收益/风险: 收益中(可访问性真实提升, 且给后续收敛立判据); 风险低-中(补 ARIA 不影响视觉, 但 `aria-activedescendant` 要求 id 稳定, 需给候选项生成 id)

**R23-A-10** · combobox 下拉"计数头"两套(有 pop-head / 无 pop-head)
- 位置: 有 `pop-head` —— `dialogs-mgr.html:72`(保存路径)·`move-dialog.html:42`(movePath); 无 —— `dialogs-mgr.html:106`(分类)·`130`(标签)·`popovers.html:73`(metaCat)
- 类别: B
- 重复对象: combobox 候选面板的顶部信息行(`<div class="pop-head"><span>选择保存位置</span><span class="pop-count">N</span></div>`)
- 分歧点: 2 有 / 3 无。**有头的是"路径"类候选(数量少、名字长、需要计数)**, 无头的是"分类/标签"类(数量多、带过滤); 但 `pop-empty` 文案五处都有, 说明"空态提示"是共识、"计数头"不是
- 维护风险: 低-中。这不是错误, 是**未写下的口径**: 日后新增第 6 个 combobox 时无从判断该不该带头; 若统一加头, 分类/标签的多行过滤面板会被头挤掉一行高度(这两处正是最容易溢出视口的)
- 建议收敛形态: 在 `tpl-combo-input`(见 R23-A-01)里把 `headText` 做成可选参数, 并在组件注释里写清判据("候选 = 有限的历史路径清单 → 带头计数; 候选 = 可过滤的全集 → 不带头"); 现状不动
- 预估收益/风险: 收益低(纯口径固化, 随 R23-A-01 一并完成); 风险无

**R23-A-11** · 浮层外壳 `.pop-menu` 4 种形状 / 7 处手写
- 位置: `topbar.html:73`(`col-menu` + `flip-x` + `:style="colMenuStyle()"`)·`topbar.html:138`(`pop-menu flip-x`, UI 切换)·`topbar.html:202`(`pop-menu` + 动态 `flip-x`)·`dialogs-mgr.html:71`/`106`/`130` 与 `move-dialog.html:41` 与 `popovers.html:73`(均 `.pop-menu.add-pop` + `@click.stop`); 另有 `.ctx-menu` 独立族 4 处(`ctx-menus.html:2`/`104`/`139`/`160`)
- 类别: C
- 重复对象: "锚定浮层容器"这一事实: `<transition name="pop">` + `<div v-if="XOpen" class="pop-menu …" :class="{ 'flip-x': … }" :style="…" @click.stop>` 组合, 共 13 个 `<transition name="pop">`、7 个 `.pop-menu`、4 个 `.ctx-menu`
- 分歧点: ①定位方式三套 —— CSS 锚定(combobox 的 `add-pop`, 靠父 `.add-input-row` 的 `position:relative`)、inline `:style` 计算(topbar 的 `col-menu`)、`flip-x` 静态类(UI 切换, 注释明说"锚点恒在顶栏右缘, 不需要测量翻转"); ②收层方式两套 —— `@click.stop` 内部吃掉(combobox/col-menu)vs **故意不挂**让冒泡到 `lifecycle` 的 window 收层链(UI 切换, `topbar.html:136-137` 有注释说明"与筛选器菜单语义相反, 别照抄")
- 维护风险: ②的"故意不挂"是有意为之且**已有注释**, 属正例; ①的三套定位方式是历史演进结果, 但组合起来后"新加一个浮层该抄哪个"没有单点答案(注释只在 UI 切换处写了一次"别照抄", 抄错的入口仍在)
- 建议收敛形态: 立判据而非合并 —— 在 `shared/ui_feedback.js` 或 `tpl/` 段头写一张浮层三分类表(锚定型 `add-pop` / 视口夹取型 `ctx-menu`(`_subFitViewport`/`openFilePrio` 等 6 处手写几何, 见 R21-A)/ 静态边缘型 `flip-x`), 并指明各自"收层该不该挂 @click.stop"。合并本身不建议(定位策略不同, 强行统一会把简单情形复杂化)
- 预估收益/风险: 收益低-中(纯文档化, 但能挡住"抄错入口"); 风险无

**R23-A-12** · `statusbar` 速度组下载/上传对称双份
- 位置: `statusbar.html:64-70`(下载) ↔ `72-78`(上传)
- 类别: C
- 重复对象: `<button class="sb-spd spd-down" :class="{ off: sbLimits.down === '不限' }" @click.stop="openSpeedAt($event, 'down')">` + 图标 + `.val` + `.slash` + `.lim` 五段
- 分歧点: 五处对称字面(`spd-down/up`、`ico-down/ico-up`、`i-download/i-upload`、`totalDl/totalUl`、`sbLimits.down/up`、`'down'/'up'`)
- 维护风险: 2 份、各 7 行, 属"对称双份"最低档 —— 风险仅在于"第三个方向"(若日后加"局域网速度")时才会复制成 3 份
- 建议收敛形态: `v-for="d in [['down','下载'],['up','上传']]"` 或数据表; 但 7 行 × 2 的收益不足以抵消"键名参数化后失去 `totalDl/totalUl` 的 computed 直读"。建议**不动**, 仅在两处之间加一行注释交叉引用
- 预估收益/风险: 收益低; 判定为"可接受的双份", 列此以免 S5 复核时再翻一遍

**R23-A-13** · `.ce-placeholder` 加载/错误/空态三态块 6 处(R23-A 范围内)
- 位置: `dialogs-mgr.html:13`+`16-17`(mgr 加载/错误)·`dialogs.html:16-22`(stats 错误 + 首开兜底 + 空态**三态合一**, 且带 `:class="{loading}"` 与 `FIX-04/FIX-04b` 防闪烁注释)·`popovers.html:13`+`14-17`(mgr 同前)·`popovers.html:220-224`(history: `hist-loading`/`error`/`hist-empty` **三套不同类名**)
- 类别: C
- 重复对象: "`ce-placeholder` 承载 loading/error+重试/空"的三态结构
- 分歧点: ①错误态的"重试"钮有无: stats 有(`dialogs.html:18`)、mgr 有(`loadMgr()`)、history 无(只有文本); ②空态类名: stats/mgr 用 `ce-placeholder` + `loading` 修饰, history 用 `hist-empty`(自带专属样式); ③**加载体与骨架的关系不同**: stats 是"骨架常驻仅值区降透明"(FIX-04b 防闪烁), mgr 是"`v-if` 整体替换"
- 维护风险: ③是**已定案的交互口径**(FIX-04b: 加载态不卸载字段列表), 但只在 stats 一处实现且注释只写在那里; mgr/history 整体替换的写法若被当作"标准"抄走, 会把 FIX-04b 的防闪烁固化为"没必要"。②的空态类名分裂让"统一空态样式"无法一次命中
- 建议收敛形态: 抽 `<aq-loading-state :loading :error :empty :retry>` 三态组件, 并把 FIX-04b 的"骨架常驻"做成组件默认行为(参数 `keep-mounted`); history 的 `hist-empty` 迁到统一类名 + 皮肤内覆盖。**范围注**: `settings.html` 另有 2 处 `ce-placeholder` 归 R23-B, 收敛时一并
- 预估收益/风险: 收益中(-20 行 + 把 FIX-04b 从"注释"变成"默认"); 风险低-中(加载态是用户第一眼看到的, 须逐框走查"首开无数据不崩" —— `dialogs.html:20-21` 注释明确记录了模板解引用 null 的崩溃史)

**R23-A-14** · `dock.html` 单点落点正例
- 位置: `dock.html:10` 单行 `<div class="drawer-dock"></div>`, 附 9 行注释说明"为何上提到 app 级"与"可见性由 `drawer.js::drawerVisible` 把守"
- 类别: D
- 为何不动: 这是"模板只留一个空落点、几何与可见性全在 JS/CSS"的正例; 注释里"落点 app 级 != 面板任意页可见"这条区分是防复发的关键, 收敛反而会把它打散
- 预估收益/风险: 不动

**R23-A-15** · 根层浮层与 `teleport` 正例
- 位置: `overlays.html:2-9`(toast 栈)·`19-43`(通知面板)·`47-49`(列头拖动虚影) 与 `popovers.html:295-335`(HR 悬停弹窗 `<teleport to="body">`)
- 类别: D
- 为何不动: 三处都带"必须挂在 `#app` 根层 / 必须 teleport"的成因注释(clip-path/transform 建包含块 → fixed 被裁剪, 与 `.speed-pop` 的溢出裁剪是同一族坑)。这些是**位置契约**而非重复代码, 收敛到组件里反而会隐藏"必须放在哪一层"的信息
- 预估收益/风险: 不动

### R23-B 模板下半(drawer·drawer-head·xtpl·xtpl-cells·xtpl-cells-dt·settings·settings-detail·traffic-card)(23 项: A9/B6/C5/D3)

范围(实测 2384 行/8 件): `settings-detail.html`(520)·`xtpl.html`(381)·`xtpl-cells.html`(356)·`traffic-card.html`(317)·`settings.html`(317)·`drawer.html`(242)·`xtpl-cells-dt.html`(192)·`drawer-head.html`(59)。
机器提名对照: markup 3 克隆中的 `xtpl-cells.html` site-chip 块(11 行)命中于此(R23-B-09); 其余 22 项均来自精读。**本子轮是 Phase 2 里 A 类密度最高的一段**(9/23) —— 原因是模板层已做过两轮大收敛(P1/P2/P3 表壳与 cells 渲染器、W3/W4 抽屉头与流量控件), 收敛后的**残留同构件**最集中, 而新收敛面(设置页 Console Hub / 抽屉变体)还没被同一把尺子量过。

骨架族实测计数(in 本 8 件): `hb-switch` 7 / `hb-blk-hd` 15 / `hb-sub-toggle` 5 / `empty` 8(其中 3 处无图标) / `site-chip` 3 / `m-progress` 4 / `hb-btn` 200+ / `drawer-table` 4 / 内联 `style="padding:12px 14px"` 4。

**R23-B-01** · `.hb-switch` 开关块 7 处(4 带文字 / 3 不带)
- 位置: `xtpl.html:18-22`(section 段开关)·`84-88`(bool 行)·`183-188`(inline 从属开关) · `settings.html:228-232`(规则启停) · `settings-detail.html:70-73`(跳检开关)·`171-175`(普通分区段开关) · `traffic-card.html:300-305`(流量图采样)
- 类别: A
- 重复对象: `<label class="hb-switch"><input type="checkbox" :checked="X" @change="Y"><span class="hb-sw-track"></span><span class="hb-sw-text">{{ X ? '启用' : '关闭' }}</span></label>`, 4-5 行 × 7
- 分歧点: ①**文字有无各半** —— xtpl 3 处 + traffic-card 1 处带 `.hb-sw-text`(显示"启用/关闭"), settings 1 + settings-detail 2 **不带**(只有滑轨); ②`hb-switch` 的 `:class="ce.hubToneOf(item)"` 色调绑定只有 xtpl 的 bool 行有; ③`title` 只有 settings-detail:70 的跳检开关有
- 维护风险: ①无判据 —— 同一控件在配置行里带字、在分区段头里不带字, 但 `settings-detail:171`(分区段开关)与 `xtpl:18`(section 段开关)**是同一位置同一语义却一个带一个不带**, 属纯漂移; ②色调/title 绑定散落意味着"给开关加一项能力"要改 7 处(且会漏)。另: 开关的 `aria` 全靠原生 checkbox 语义, 无 `role="switch"` —— 与 `.opt-pill` 的 `role="switch"`(R23-A-06)两套可访问性口径
- 建议收敛形态: 抽 `<hb-switch :checked :on-change :text :tone :title>` 组件(注册点与 `hub-field` 同处), 7 处改一行; `text` 缺省 = 不渲染文字, 但**必须在组件注释里写清"何时该带文字"**(建议: 状态语义不自明的场景带字, 段头开关统一不带)
- 预估收益/风险: 收益中(-30 行 + 7 处能力同步); 风险低(纯表单控件, 无热路径)

**R23-B-02** · `hb-sub-toggle` 可折叠段头 5 处逐字近同
- 位置: `traffic-card.html:34-42`(数据来源)·`146-154`(限速曲线)·`281-289`(流量图采样) · `xtpl.html:37-47`(group 段) · `settings.html:240-249`(规则 meta)
- 类别: A
- 重复对象: `<div class="hb-blk-hd hb-sub-toggle" role="button" tabindex="0" @click="T" @keyup.enter="T">` + `bh-t` 标题 + `bh-n` 说明 + `bh-r` 内的 `aria-expanded` 收起/展开钮 + `v-if` 折叠体
- 分歧点: traffic-card 三处的 toggle 参数是 `'source'`/`'curve'`/`'chart'`(字符串 key, 走 `$root.hubSubToggle(k)` + `$root.hubSubOpen(k)`); xtpl 用 `toggleGroup()`/`groupOpen`(组件方法); settings 用 `cfgRuleMetaToggle(g,r)`/`cfgRuleMetaOpen(g,r)`(双参数)。**三种签名**
- 维护风险: 折叠头的键盘契约(`role="button"` + `tabindex="0"` + `@keyup.enter`, 注意**没有** `@keyup.space` —— 与 R23-A-09 里 `.pop-item` 的"enter+space"口径不等)在这 5 处各写一遍; 改一次键盘策略要改 5 处。另: `@click` 与内层钮的 `@click.stop` 组合是"整行可点 + 钮不重复触发"的关键, 漏 `.stop` 会折叠两次(净效果 = 不动, 表现为"点了没反应")
- 建议收敛形态: 抽 `<hb-fold :open :on-toggle :title :note :tone>` + 默认插槽; 三种签名归一为"回调函数"入参(组件不关心 key 形状)。traffic-card 三处可直接 `v-for="sec in [{k:'source',...}]"` 再降一层
- 预估收益/风险: 收益中高(-35 行 + 折叠键盘契约单点); 风险低-中(折叠态是设置页主交互, 须走查"整行点/钮点/键盘"三条路径)

**R23-B-03** · 规则「条件 / 动作」两栏 `hb-step` 逐字同
- 位置: `settings.html:256-278`(条件栏) ↔ `279-302`(动作栏)
- 类别: A
- 重复对象: `hb-flow-grp` + `hb-flow-grp-hd`(标题 + `fg-hint`) + `v-for` 的 `hb-step`(序号 `st-n` + 文本 `st-t` + `st-r` 三钮 ↑↓✕) + `hub-field` 子项 + 空态 `hb-hp` + 底部 `<select>` 添加器, 约 **22 行 × 2**
- 分歧点: 前缀 `'conditions'`/`'actions'`; 标题"条件"/"动作"; `fg-hint` 文案"全部满足才执行"/"按顺序执行"; 动作栏 `hb-step` 多 `:class="hubStepClass(entry)"`; 空态文案两条; 添加器选项源 `cfgConditionOptions()`/`cfgActionOptions(g,r)` + 占位"＋ 添加条件…"/"＋ 添加动作…"
- 维护风险: 8 处差异里有 6 处是**文案**, 2 处是功能(stepClass / 选项源函数)。两栏的 `↑↓✕` 三钮走同一组 `cfgPluginMove`/`cfgPluginRemove`(已单点), 所以模板是纯骨架拷贝 —— 但"条件不可排序"这类未来需求会只改一边
- 建议收敛形态: `v-for="side in [{k:'conditions',t:'条件',hint:'全部满足才执行',...},{k:'actions',...}]"`, 选项源函数进 side 数据。约 44 行 → 24 行
- 预估收益/风险: 收益中(-20 行); 风险低(纯展示 + 已有单点方法)

**R23-B-04** · `hb-unit` 数值+单位控件 2 份(跨文件, 两套取数口径)
- 位置: `xtpl.html:136-144`(hub-field 的 `hasUnit` 分支) ↔ `traffic-card.html:120-128`(工具参数 `p.kind === 'time' || 'size'`)
- 类别: A
- 重复对象: `<div class="hb-unit"><input class="hb-input hb-mono hb-w-sm" type="text" :value="NUM" :placeholder="..." @input="set(NUM_PART, $event.target.value, UNIT)"><select class="hb-select" :value="UNIT" @change="set(NUM, $event.target.value)"><option v-for="u in OPTS" :value="u">{{ LBL(u) }}</option></select></div>`
- 分歧点: 取数函数两套 —— xtpl 走 `ce.cfgSetUnit(path, num, unit)` + `unitOptions`/`unitLabel(u)`(字段级 computed); traffic-card 走 `$root.tmSetUnitPart(p, num, unit)` + `$root.cfgUnitOptions(p.kind)`/`cfgUnitLabel(kind, u)`(参数级方法)。**traffic-card 的 `cfgUnitOptions(kind)` 说明单位梯已按 kind 单点**, 而 xtpl 的 `unitOptions` 是 hub-field 自己的另一份
- 维护风险: 单位梯(时间: 秒/分/时; 大小: KiB/MiB/GiB…)是**同一事实的两个来源**。改一处阶梯会导致"配置页显示 30MiB、工具参数页显示 30GiB"这类同值不同单位。另 `hb-mono` 两处都有但对 `kind === 'text'` 的行没有 —— 无判据
- 建议收敛形态: 把 `cfgUnitOptions/cfgUnitLabel` 作为**唯一**阶梯(它们已按 kind 参数化), hub-field 的 `unitOptions` 改为转发; 模板抽 `<hb-unit :num :unit :kind :on-change>`。或最小改动 = 让 hub-field 的 computed 直接调 `this.cfgUnitOptions(f.kind)`
- 预估收益/风险: 收益中(消除单位梯双源, 这是"静默错值"类风险而非样式); 风险低-中(单位语义错会写坏配置, 须比对现有 `cfgSetUnit` 的夹紧行为)

**R23-B-05** · 抽屉变体 peer 行渲染器 3 份(仅 CSS 前缀不同)
- 位置: `xtpl-cells.html:267-296`(dt07)·`298-327`(dt08)·`329-356`(dt09)
- 类别: A
- 重复对象: 10 个 `col.key` 分支(addr/client/flags/files/progress/upspeed/dlspeed/uploaded/downloaded/relevance), 每分支逐字同, **唯一差异是类名前缀 `dt07-` / `dt08-` / `dt09-`**(约 30 行 × 3)
- 分歧点: **dt07 与 dt08 除前缀外零差异**; dt09 有 1 处真差异 —— `upspeed` 分支改成 `dt09-occ`(带占比条 `<span class="track"><i :style="{width: p.occBar+'%'}">` + 更长 title, 语义是"条长 = 占当前上传合计比重"), `dlspeed` 改成 `dt09-dn` 且 `:class="{z:…}"` 直接挂外层。**注释已承认同源**("dt08 五区分组: 与 07 同判据同款单元格(dt08-* 类族), 差异只在版式(组体由外壳承载)")
- 维护风险: 这是"注释说同款、代码是三份"的典型。加一个 peer 列(如 `p.connected` 徽章)要改 3 处, 漏一处 = 该变体下该列空白且**无任何报错**(与 `tpl-aq-member-cells` 注释里记录的"漏改一处 = 该页该列空白"完全同型缺陷)。三份各 30 行 = 90 行, 收敛后约 35 行
- 建议收敛形态: 渲染器接 `prefix` prop(`:prefix="'dt07'"` → 类名 `:class="prefix + '-addr'"`), 由 `dtBridgeRowModel` 的同类机制传入; 或把三套类名统一为 `dt-peer-*` 并把三皮肤 CSS 的三组前缀规则合并(需同步 CSS, 归 R21-C 的 dt 族讨论)。**改类名会撞 `_scan_ui_diff_registry` 与三皮肤 CSS, 故建议走 prefix prop 而不改名**
- 预估收益/风险: 收益高(-55 行, 且关掉一类"某变体某列空白"的复发面); 风险中(dt09 的 occ 分支须保留特化, 5 个变体的渲染须逐一比对 e2e)

**R23-B-06** · `.empty` 空态块 8 处(其中 3 处无图标)
- 位置: 带图标 —— `drawer.html:102-105`(流量加载中)·`106-109`(流量错误)·`110-113`(流量空)·`200-203`(详情加载中)·`204-207`(详情错误); 不带图标 —— `settings-detail.html:293`·`294`·`322`(HR 表三态); 跨轮(已计 R23-A-05) —— `groups.html:47-53`·`torrents.html:16-22`·`shows.html:74-80`
- 类别: A
- 重复对象: `<div class="empty"><svg class="ico" viewBox="0 0 16 16"><use href="#i-X"></use></svg><span>{{ 文案 }}</span></div>`
- 分歧点: ①**图标有无** —— 8 处有、3 处(settings-detail HR 表)无; ②图标选择有语义分工(drawer: hourglass 加载中/warn 错误/inbox 空; groups/torrents/shows: 恒 inbox); ③settings-detail 的三处**连 `svg` 都不写**, 且 `322` 的文案走 `hrsEmptyText(s.site)` 函数
- 维护风险: ①是真实的视觉不一致 —— 同一"空态"在原表页有图标、在设置页 HR 表没有; 且 settings-detail 那三处是 `.empty` 类名但样式上下文不同(`.drawer-table` 兄弟), 三皮肤里 `.empty` 的 padding 未必适配。②`#i-X` 的选择没有判据文档
- 建议收敛形态: 抽 `<aq-empty :icon :text>`(icon 缺省 `#i-inbox`, 加载中/错误由调用方给 hourglass/warn), 11 处(含 R23-A-05 的 3 处)统一; 顺带把图标选择的口径写进组件注释(加载中 = hourglass / 错误 = warn / 空 = inbox)
- 预估收益/风险: 收益中高(-25 行 + 空态图标口径单点 + 消掉 3 处无图标); 风险低(纯展示; 但 `.empty` 类名被三皮肤 CSS 直接选择, 组件必须**保留同类名结构**)

**R23-B-07** · 单元格子件跨文件重复(`m-progress` / `m-dur` / `m-ratio` / `tag-chip` / `cat-chip`)
- 位置: `m-progress` 4 份 —— `xtpl-cells.html:37-40`(group)·`143-146`(torrent)·`223-226`(ep) + `xtpl.html:302-305`(member); `m-dur` 2 份 —— `xtpl-cells.html:163-171` + `xtpl.html:307-315`(**含 `.dur-body` 注释两份各写一遍**); `m-ratio` 2 份 —— `xtpl-cells.html:172-175` + `xtpl.html:316-319`; `tag-chip` 3 份 —— `xtpl-cells.html:46-48`·`138-140` + `xtpl.html:291-293`; `cat-chip` 3 份 —— `xtpl-cells.html:53-55`·`132-134` + `xtpl.html:297-299`
- 类别: A
- 重复对象: 五族"单元格内构件"的模板片段, 每族 2-4 份, 差 `g.`/`m.`/`e.` 三个行模型前缀与 `$root.` 取值
- 分歧点: `m-progress` 纯前缀差; `m-dur` 与 `m-ratio` **跨文件且夹注释**(注释内容逐字同: "`.dur-body` = **文字**包裹层…挂 `.m-dur` 上会随列宽"); `tag-chip` 的 group 版用 `g.commonTags.list` + `g.members[0]`(首个成员算 tagClass), member/torrent 版用 `$root.mTags(m)`; `cat-chip` 的 group 版有 `commonCategory.diff` 三态
- 维护风险: `m-dur`/`m-ratio` 是 **FX-02/03/04 口径单点化的产物**(整格线随文字宽、组进度 0 不显示), 注释是这两条口径的**唯一载体**而它有两份 —— 改口径时改了一份、另一份的注释会变成错的指引(比代码错更糟)。`m-progress` 的 `Math.min(100, X*100)` 三份手写, 若口径改成"四舍五入到 0.1"要改 4 处
- 建议收敛形态: 这五族**已在 `$root` 有取值单点**(`cellRatio`/`hrDurClass`/`mTags`/`tagClass`), 缺的只是模板壳。建议与 R23-A-05 的 `<aq-row-pad>` 同一批做成 `xtpl.html` 里的 `<template id="tpl-cell-dur">` 等具名片段, 由 cells 渲染器 `<template is=...>` 引用? **但注意** Vue 3 的 in-DOM 模板不支持 `<template is>` 的片段复用, 故实际可行形态 = 抽成**组件**(`<aq-cell-dur :m>`)——这与 `tpl-aq-member-cells` 的注释"单元格必须是行的直接子元素, 故不包 wrapper"冲突: 组件会多一层包裹。**结论: 本族只能收 BF(先统一行模型前缀)或不做** —— 详见风险段
- 预估收益/风险: 收益中(-40 行); **风险中高** —— 多根片段 + 直接子元素是 grid 列对齐的硬约束(`:nth-child` 与 `data-table` 双依赖), 抽组件会破坏它。**建议 S5 归档时把本项降级为"登记不动"**, 只做两件事: ①把 `m-dur` 的两份注释合并为一份并注明"另一处逐字同"; ②`m-progress` 的百分比口径抽成 `$root.progPct(v)` 单点(纯 JS, 零 DOM 风险)

**R23-B-08** · 变体表操作按钮对(`report` + `del`)4 处
- 位置: `xtpl-cells-dt.html:28-31`(dt04)·`49-53`(dt05 fail)·`77-80`(dt05 row)·`118-121`(dt06)
- 类别: A
- 重复对象: `<button type="button" class="dtXX-act" :class="{ 'is-gated': !p.gatedOk }" data-act="report" :data-url="p.url" :title="…"><svg class="ico ico-sm"><use href="#i-refresh"></use></svg></button>` + 同款 `data-act="del"` + `#i-trash`
- 分歧点: ①**report 钮的 title 两套** —— 3 处写 `p.gatedOk ? '强制重新汇报' : p.gatedTitle`, dt05 fail 那处写 `p.gatedOk ? '' : p.gatedTitle`(用空串走"清除提示"通道, 见 `ui_feedback` 口径); ②dt05 fail 的 report 钮**带文字**"强制重新汇报"(其余 3 处纯图标); ③dt05 的 del 钮 title 是"删除失效 tracker"(其余"删除 tracker")
- 维护风险: ①是**口径分叉且 dt05 那处更正确**(空串 title 是既有定案), 另 3 处重复冗余文案 = 用户悬停时看到的提示与 `is-gated` 态提示会闪变; ②同一操作在 4 个变体里三种视觉(纯图标 ×3 / 图标+文字 ×1), 无判据
- 建议收敛形态: 抽 `<dt-acts :row :prefix :with-text>`(数据 `p.url`/`p.gatedOk`/`p.gatedTitle` 已齐), title 口径统一取 dt05 的空串写法; 4 处改一行
- 预估收益/风险: 收益中(-15 行 + title 口径统一); 风险低(单按钮, e2e 按 `data-act` 断言, 属性不变)

**R23-B-09** · `.site-chip` 站点徽章 3 处(jscpd markup 第 3 处)
- 位置: `xtpl-cells.html:63-71`(group 行, `v-for="m in g.members"`)·`111-119`(torrent 行, 单值 `m`)·`231-239`(ep 行, `v-for="m in e.members"`)
- 类别: A
- 重复对象: `<span class="site-chip" :class="[m.kind, $root.siteAlertClass(m), { 'search-hit': m.hit, 'f-on': $root.isFilterOn('siteFilter', m.site) }]" :title="$root.chipAlertTip(m)" :aria-label="$root.siteAlertAria(m) || null" @click.stop="$root.filterFromChip('site', m.site)">{{ m.site }}<svg v-if="$root.rowIcon(m.hash)" class="ico sx" :class="'sx-' + $root.rowIcon(m.hash).kind"><use :href="$root.alertIconHref($root.rowIcon(m.hash).kind)"></use></svg></span>`
- 分歧点: **torrent 版缺 `'search-hit': m.hit`**(group/ep 版都有)。这条差异有实际后果: 种子页搜索结果里成员行/组行的站点 chip 会高亮, 种子页平铺行的 chip 不高亮 —— 且 `torrents.html:8` 的行级 class 里**也没有** `search-hit`(而 `groups.html:35` 的 member 行有、`shows.html:10` 的剧行有)
- 维护风险: ①`search-hit` 的缺失是**跨三个文件的同一遗漏**(chip 1 处 + 行级 1 处), 表现为"种子页搜索时不高亮命中行" —— 属功能缺陷而非纯重复; ②`.site-chip` 内嵌的 `rowIcon` 三连调用(`$root.rowIcon(m.hash)` 出现 3 次/处 × 3 处 = 9 次)是性能小项, 且若 `rowIcon` 改成有副作用就会炸; ③jscpd 抓到 11 行说明这三份已到了 token 阈值, 是 markup 侧少数能机器发现的真重复
- 建议收敛形态: 抽 `<aq-site-chip :m :with-hit>`(组件化在此**不违反**直接子元素约束 —— chip 本身是单元格内的元素, 不是行容器的直接子项); `with-hit` 缺省 true, torrent 行显式给 true 一并修复。`rowIcon` 三连调用改 computed 或 `v-for` 一次的局部变量
- 预估收益/风险: 收益中高(-18 行 + 修一处功能遗漏); 风险低-中(chip 是点击热区, filterFromChip 的 `.stop` 语义须逐处保)

**R23-B-10** · `aq-table` 的 thead / grid 双分支排序箭头口径相反
- 位置: `xtpl.html:220-228`(thead 模式) ↔ `229-252`(grid 模式)
- 类别: B
- 重复对象: `<span class="arrow">` + `<svg class="ico"><use :href="'#i-arrow-up' | '#i-arrow-down'">` 这一段排序指示器
- 分歧点: **可见性语义相反** —— thead 分支 `:class="{ on: sortKey === col.key }"` 且 `<svg>` **恒渲染**, `:href` 在非当前列回落到 `#i-arrow-down`(即"每列都有一个箭头"); grid 分支 `<span v-if="col.sortable" class="arrow"><svg v-if="sortKey === col.key">`(即"只有当前排序列、且只有可排序列才有箭头")。另 thead 分支无 `@mousedown`(拖宽)/`@contextmenu`(表头菜单)/`.resizer`
- 维护风险: ①**用户可见差异** —— 设置页 HR 详情表(thead 模式)表头每列都有箭头, 主表(grid 模式)只有排序列有。这不是缺陷, 但**没有任何注释说明为何不同**(`tpl-aq-table` 头注只写了"grid 分支一字未动"和"不挂拖宽/重排/右键", 没提箭头); ②`headAriaSort(col)` 两处都调(可访问性一致), 但视觉不一致会让读屏用户与明眼用户看到的"可排序性"不同; ③`col.sortable` 在 thead 分支**没有被用**(grid 用它门控箭头), 意味着 thead 模式下即使列不可排序也显示箭头 —— 若 HR 表传入不可排序列, 会出现"点了没反应"的箭头
- 建议收敛形态: **先定口径**。建议统一为 grid 口径(`v-if="col.sortable"` + 仅当前列显箭头), 因为它与 `col.sortable` 的实际能力一致; 若 thead 的"恒显箭头"是有意(如"降序/升序二态切换"提示), 则须在头注补一句说明并把 grid 也改成 `col.sortable` 门控 + 非当前列显淡箭头
- 预估收益/风险: 收益中(消掉一处用户可见不一致); 风险低(纯表头视觉, 无数据路径)但**需产品判断**

**R23-B-11** · 状态文案两套 `stateText` vs `kindText`
- 位置: `xtpl-cells.html:121-126`(torrent 行: `$root.stateText(m)`)·`217-222`(ep 行: `$root.kindText(e.state)`) ↔ `xtpl.html:272`(member 行: `$root.stateText(m)`)
- 类别: B
- 重复对象: "状态"列/单元格的文案来源
- 分歧点: 两个函数 —— `stateText(member)` 吃成员对象(可读 `error_reason` 等字段), `kindText(kind)` 吃状态枚举字符串。ep 行的状态是**聚合**出来的 `e.state`(无成员对象可传), 故它只能用 `kindText`; torrent/member 行有完整对象故用 `stateText`
- 维护风险: 两个函数若文案表不同(如 "做种中" vs "做种"), 同一状态在剧集行与种子行**显示不同词**。这是纯静默差异, 无测试会红。且 `kindText` 也在 `topbar.html:180` 用于筛选说明(`kindText(kindFilter)`), 那里与 ep 行共用一个函数
- 建议收敛形态: 确认 `stateText(m) === kindText(m.kind)` 恒成立(或 `stateText` = `kindText` + 错误态后缀), 然后在 `stateText` 里加注释指明"无成员对象时用 kindText, 两者共用同一文案表"; 若文案表是两份则合并
- 预估收益/风险: 收益中(消掉"同一状态两个词"的可能); 风险低(纯文案, 但须逐状态比对)

**R23-B-12** · HR 徽标的 title 口径 —— 单点函数 vs 内联手写三元
- 位置: `xtpl-cells.html:74`(group 行: `:title="$root.hrGroupTitle(g)"`) ↔ `244-245`(ep 行: `:title="e.hr_triggered ? (e.hr_pending ? e.hr_pending + '/' + e.hr_triggered + ' 未满足要求' : 'HR 已全部达标') : '该集无成员触发 HR'"`)
- 类别: B
- 重复对象: HR 徽章的悬停提示文案
- 分歧点: group 版走单点函数 `hrGroupTitle(g)`; ep 版在模板里内联手写四层三元。两者文案**不相同**: group 版的措辞未知(在 `hr_status.js`), ep 版是"未满足要求/已全部达标/无成员触发 HR"
- 维护风险: ①`hrGroupTitle` 这个单点**已存在**, ep 行却没用 —— 要么是 ep 的对象形状(有 `e.hr_triggered`/`e.hr_pending`, 与 group 同名字段)其实可以直接复用, 要么是刻意不同。**无论哪种, 现在都没有注释**, 后人改措辞只会改一处; ②内联四层三元是全文件最长的单行表达式, 违 `hb` 系列的"判据在 JS"纪律
- 建议收敛形态: 若字段同名(已实测同名: `hr_triggered`/`hr_pending`)则直接改调 `$root.hrGroupTitle(e)`(一行); 若口径确需不同, 则加 `hrEpTitle(e)` 到 JS 并把注释写在那
- 预估收益/风险: 收益中(消掉模板里最长内联表达式 + 单点被绕过); 风险低(纯 title)

**R23-B-13** · drawer 四页签宿主两套写法(数据驱动 vs 硬编码字面量)
- 位置: `drawer.html:217-225`(合并双列: `v-for="col in dtPairCols"` + `dtHostOn(col.tab)` + `aq-dt-bridge`) ↔ `228-238`(非合并: 4 个硬编码 `<div class="dt-host">` + `v-for="t in ['general','trackers','peers','content']"`)
- 类别: B
- 重复对象: "逐页签宿主 + 变体桥"这一结构
- 分歧点: 合并态**已数据驱动**(`dtPairCols` 来自 `MERGE_PAIRS` 单点, 注释明说"W4: 模板不再硬编码 gc/tp 两个 `<template>` 分支"); 非合并态**仍硬编码** 4 个宿主 div + 一个页面签名字面量数组
- 维护风险: **这是"同一次收敛只做了一半"的直接证据**。W4 的收敛目标写得很清楚(删掉硬编码分支), 但它只覆盖了合并态 —— 非合并态的四页签名字面量出现**两次**(4 个 `data-dt-host` + `['general','trackers','peers','content']`), 加第五个页签(如已存在的 `'traffic'`, 走的是另一条 `qbTrafficActive` 分支)时非合并态要改两处。且非合并态的四行 div 与桥的 `v-for` **本可以合成一个 v-for**(`v-for="t in DRAWER_TABS"` + `v-show="dtHostOn(t)"` + 桥)
- 建议收敛形态: 非合并态改为 `v-for="t in [$root.dtTabList]"`(新增单点, 值 = `['general','trackers','peers','content']`), 宿主 div 与桥同一个 v-for 内(桥要 `v-if="dtBridgeOn(t)"`)。与合并态的 `dtPairCols` 共用"页签列表来自单点"的同一范式
- 预估收益/风险: 收益中(-8 行 + 消灭第二处页签字面量); 风险低-中(宿主是 `_dtSync` 的挂载目标, `:key` 与显隐语义须保 `v-show`)

**R23-B-14** · 缺集标记两套类名(`dt10-miss` vs `dt11-meta is-miss`)
- 位置: `xtpl-cells-dt.html:144`(`<span v-if="p.missTxt" class="dt10-miss" :title="p.missTitle">缺 {{ p.missTxt }}</span>`) ↔ `181`(`<span v-if="p.missTxt" class="dt11-meta is-miss" :title="p.missTitle">缺 {{ p.missTxt }}</span>`)
- 类别: B
- 重复对象: 树行文件节点的"缺 N"标记(同一 `p.missTxt` / `p.missTitle` 字段来源, 同一文案模板)
- 分歧点: 类名两套 —— `dt10-miss`(专用类) vs `dt11-meta is-miss`(复用 meta 类 + 修饰类)
- 维护风险: 三皮肤 CSS 要为同一个视觉写两组规则(`.dt10-miss` 与 `.dt11-meta.is-miss`), 且 `is-miss` 的语义与 `dt11-meta` 的默认态(目录的"子树合计")叠加 —— 若 `.dt11-meta` 有 `margin-left` 等布局属性, `is-miss` 会继承。改"缺集"的颜色要改两处 CSS(×3 皮肤 = 6 处)
- 建议收敛形态: 统一为 `.dt-miss`(跨变体共用, 与 R21-C 的 dt 类族收敛同批), 或统一为 `dtXX-meta is-miss` 两种都行 —— **关键是二者取一**。属 CSS 侧改动, 与 R22 的 dt 族合并处理
- 预估收益/风险: 收益低-中(1 处类名); 风险低(仅样式)

**R23-B-15** · 设置页内联 SVG 图标 vs sprite symbol
- 位置: `settings.html:25`(搜索图标内联 `<circle cx="7" cy="7" r="4.6"/><path d="M10.6 10.6 14 14"/>`)·`107`(同款再写一遍)·`154`·`171`("＋"图标内联 `<path d="M8 3v10M3 8h10"/>`)·`174`(导入图标内联)·`82`(返回箭头内联)·`47`(警示三角, 在已注释掉的块里)
- 类别: B
- 重复对象: 图标的载体选择 —— sprite `<use href="#i-*">`(全项目其余所有地方) vs 内联 `<path>`
- 分歧点: 设置页用 `class="hb-ico"`(console_hub.css 的独立图标类)而非 `class="ico"`, 且**内联 path 而不引用 sprite**。sprite 里明明有 `#i-search`(atlas/index.html:20)、`#i-plus`、`#i-warn`
- 维护风险: ①**同一搜索图标在同一文件里内联了两遍**(25 与 107 各一份完整 path), 改图标要改两处; ②sprite 的 67 个 symbol 是 R23-C 说的"三份物理拷贝", 而设置页这 6 处内联让**图标来源分裂为二** —— 想统一换图标风格(如加粗 stroke)时会在设置页留一片旧样式; ③无注释说明为何不用 sprite。**推测原因**: `console_hub.css` 是三皮肤共用的 shared 通道, 若依赖各皮肤 `index.html` 的 sprite, 一旦某皮肤少一个 symbol 就静默丢图标(这正是 R23-C-01 的风险) —— **但这个理由没写下来**
- 建议收敛形态: **两条路, 择一并注释**: (a) 保持内联但抽成 `hub_icons.js` 的 SVG 字符串常量或 `tpl` 里的具名片段, 消掉同文件内两遍搜索图标; (b) 改用 sprite 并在 `test_webui_static_skins.py` 加"三皮肤 sprite 必含 `hb_ico` 所需 symbol 集合"断言。**推荐 (a)** —— 它不引入跨皮肤隐式依赖, 且与 `console_hub.css` 的"自带"定位一致
- 预估收益/风险: 收益低-中(消 1 处重复 + 明确图标来源纪律); 风险低

**R23-B-16** · 折叠交互 4 种实现并存
- 位置: ①原生 `<details>` —— `settings-detail.html:211-214`(站点微调)·`331-369`(排障视图)·`381-428`(拉取历史); ②`hb-sub-toggle` 可点段头 + `v-if` —— `traffic-card.html:34/146/281`、`xtpl.html:37`、`settings.html:240`; ③`v-show` + 钮 —— `settings-detail.html:462`(运行日志 `logs.open`); ④`aria-expanded` + `v-if` + 组件方法 —— `xtpl.html:23-24`(section `sectionOpen`)/`42-43`(group `groupOpen`)/`settings.html:246-250`(规则 meta)
- 类别: C
- 重复对象: "一段内容可收起/展开"这一交互事实
- 分歧点: ①`<details>` 免费获得键盘/读屏/无 JS 状态, 但样式受限于 `summary`; ②`hb-sub-toggle` 手动 `role="button"` + `tabindex="0"` + `@keyup.enter`(无 space), 状态在 `hub.sub`; ③`v-show` 无 `aria-expanded`、无 `tabindex`(钮本身可聚焦故可用), 状态在 `logs.open`; ④`aria-expanded` 绑在**另一个按钮**上而可点区域是整个标题栏
- 维护风险: 四种实现的可访问性不一: `<details>` 最好、②次之、③缺 `aria-expanded`、④的 `aria-expanded` 挂错层(挂在钮上但整栏可点, 读屏用户会以为只有钮能展开)。这是**真问题不是风格问题**。另: 折叠态持久化口径也不一(`<details>` 不持久化、`hub.sub` 不持久化"见 config_hub.js"、`logs.open` 也不持久化) —— 三者一致但都没写在一起
- 建议收敛形态: **立判据**: (a) 一次性排障/只读信息 → `<details>`(白拿可访问性); (b) 主内容区段(需自定义头样式/常驻钮) → `hb-sub-toggle`; (c) 禁用 `v-show` 折叠与"整栏可点但 aria 挂钮"两种写法。然后逐处归类改造(优先级: ③④ → 统一)
- 预估收益/风险: 收益中(可访问性真实提升 + 折叠口径单点); 风险低(折叠不涉及数据)

**R23-B-17** · 分段单选钮组 4 套
- 位置: `popovers.html:212-215`(`.hist-tabs`: `v-for="g in ['day','month','year']"` + 内联字面量映射 `{day:'天',…}[g]`)·`drawer-head.html:41-44`(`.qb-tabs`: `v-for="w in $root.qbWindowNames"` + `$root.qbWindowLabel(w)`)·`drawer-head.html:47-54`(`.qb-seg`: 硬编码 3 个钮) · `drawer.html:48-57`(`.drawer-tabs`: 合并态 `dtMergeTabList` 数据驱动 / 非合并态硬编码 4+1 钮)
- 类别: C
- 重复对象: `<div class="X"><button v-for=… :class="{ active: 当前 === 值 }" @click="设值">{{ 标签 }}</button></div>`
- 分歧点: ①数据源四种 —— 内联字面量数组 / `$root` 属性 + 标签方法 / 硬编码钮 / 注册表单点; ②激活判据两种 —— `:class="{active: X===v}"` vs `.on` 类(settings 的 `hb-pill` 用 `on`); ③**`.drawer-tabs` 的合并态与非合并态又是两种**(与 R23-B-13 同型的"收敛只做一半")
- 维护风险: ①`hist-tabs` 的内联映射 `{ day: '天', month: '月', year: '年' }[g]` 在 `popovers.html` 里出现了**两次**(`214` 标签与 `270` 汇总文案), 加一个粒度要改两处; ②四套里只有 `drawer-tabs` 走注册表, 其余三套加档位都是"改模板"; ③`.qb-seg` 硬编码 3 钮但 `qbYAxisMode` 有 auto/limit/manual 三值 —— 若加第四种纵轴模式, CSS 的 `.qb-seg > button` 均分布局会自动适配, 但模板要加钮
- 建议收敛形态: 抽 `<seg-group :items :value :on-pick :cls>`(items = `[{v, label}]`), 四套改数据表; 三皮肤 CSS 的 `.hist-tabs`/`.qb-tabs`/`.qb-seg`/`.drawer-tabs` 四组规则**保留**(视觉确实不同, 属 R22-C-06 已登记的"同一浮层的两半")
- 预估收益/风险: 收益中(-20 行 + 档位定义单点); 风险低(纯视觉切换钮)

**R23-B-18** · 手写 SVG 折线图模板两套
- 位置: `popovers.html:230-255`(历史流量, `.hist-*` 类族 + `histGeom.padL/padT/chartH`) ↔ `traffic-card.html:205-246`(限速曲线, `.ce-chart-*` 类族 + `ch.padL/padT/baseY`) ; 另有第三方 uPlot(`drawer.html:131-153` 的 `qb-chart-host`, 走 `_qbChartBuild`)
- 类别: C
- 重复对象: "SVG 折线图"的模板骨架 —— `<svg><g class="*-grid">line v-for yTicks</g><path class="*-area"><path class="*-line"><g v-if="hover"><line/><circle/></g><g class="*-axis"><text v-for/></g></svg>` + 悬停浮卡
- 分歧点: ①类名前缀 `hist-` / `ce-chart-`; ②几何变量名 `histGeom` / `ch`; ③**hist 有 area 双系列(up/down 两条 path)而 ce-chart 单系列(逐方向画两张图)**; ④浮卡定位: hist 用 `leftPct` 百分比、ce-chart 用 `leftPct+topPct` 双百分比、drawer 的 uPlot 版用 `left` px; ⑤ce-chart 有 `tierLines`(档位竖线)与 `legend` 块, hist 有 `hist-legend` 但结构不同
- 维护风险: ①**三种图表实现**(手写 hist / 手写 ce-chart / uPlot)意味着三套坐标换算、三套悬停、三套 tooltip; 改"悬停时显示当时限速"(已在 drawer 版实现)要分别在另两套重做; ②两套手写 SVG 都用 `v-bind="{ viewBox }"` 规避模板编译器小写坑(`popovers.html:228-229` 有注释解释), 这个坑的知识点在两处各写/各不写; ③`pathLength: 1000` 的 draw-in 动画只有 hist 有
- 建议收敛形态: **不合并**(三者数据形状与性能需求不同 —— uPlot 为万点时序, 两套手写为百点级), 但应立"图表实现选择判据"并写进 conventions: (a) >1000 点连续时序 → uPlot; (b) ≤100 点且需双系列叠加 → 手写; (c) 单系列分档 → 手写。同时把"`viewBox`/`pathLength` 必须 `v-bind`"的坑从两处注释合并到一处 pitfall 档
- 预估收益/风险: 收益低(判定为合理的三分, 与 R20-E 的"渲染栈三分"结论一致); 风险无 —— 列此项的价值是**给 S5 归档一个"已评估、不合并"的明确记录**, 防止下轮重审

**R23-B-19** · HR 三张表的表头三套
- 位置: `settings-detail.html:296-304`(表① 详情: `<tr is="vue:aq-table" mode="thead" table-id="hrDetail" :cols="hrsCols()" …>` 借壳)·`345-353`(表② 波次: `<tr><template v-for="c in hrsWaveCols()"><th v-if="c.num" class="num">` 手写)·`400-404`(表③ 历史: 10 个**硬编码** `<th>`)
- 类别: C
- 重复对象: `<thead><tr>` + 列头单元格
- 分歧点: ①来源三套 —— 表壳组件(`hrsCols()` 注册表)/ `v-for` 手写(`hrsWaveCols()` 注册表但自己渲染)/ 硬编码字面量(无注册表); ②`.num` 标记三套 —— `col.num`(组件内)/ `c.num` 双分支(注释解释"`:class="{num}"` 会渲空 `class=""`")/ 手写 `class="num"`; ③排序能力: 表① 可排(`@sort` emit)、表②③ 不可排
- 维护风险: ①表③的 10 个 `<th>` **完全脱离 `hrsCols` 注册表**, 加一列要同时改 `<thead>` 与 `<tbody>` 的 `<td>` 顺序, 两者错位即整表串列(表③ `colspan="10"` 也硬编码了列数); ②表②的"`v-if="c.num"` 双分支"与表③的"手写 class"是同一个坑的两种应对, 知识没合并; ③三表共用 `.hr-detail-table` 类(注释说"波次表同挂 .hr-detail-table 继承表① 徽章色义")但表头渲染路径不同
- 建议收敛形态: 表③改 `v-for="c in hrsHistCols()"`(新增注册表, 10 条), `colspan` 改 `:colspan="hrsHistCols().length"`; 表②保留(注释已解释为何不用表壳: 行数 ≤4 不接排序); 表①保留
- 预估收益/风险: 收益中(表③的列定义单点 + 消灭 colspan 硬编码 = 一类串列缺陷的预防); 风险低(纯表头, 但有 10 列顺序须逐列比对)

**R23-B-20** · 内联样式散落(几何数字不进 CSS 的例外区)
- 位置: `traffic-card.html` ~15 处 —— `63`(padding)·`91`(padding)·`94`(flex/gap)·`98`(margin-top)·`106`/`158`/`161`(padding)·`186`(width:110px)·`192`(margin-left:auto)·`198`(margin-top)·`266`/`272`/`293`/`313`(padding/margin) ; `settings-detail.html` 4 处 —— `15`/`195`/`250`/`462`(全为 `style="padding:12px 14px"` 字面量)·`205`(flex)·`206`(flex)·`211`(margin-top) ; `settings.html` 数处
- 类别: C
- 重复对象: 块内间距/布局的落点选择 —— CSS 类 vs 内联 style
- 分歧点: 项目其他模板普遍遵循"几何数字全在 CSS 单点"(如 `move-dialog.html:13` "模板只加类名绑定, 几何数字全在 CSS 单点"、`drawer.html:9` "高度/开合持久化") —— 但 `traffic-card` 与 `settings-detail` 大量内联。`padding:12px 14px` 这一**完全相同的字面量出现 5 次**(traffic 3 + detail 2), 说明它本该是一个类
- 维护风险: ①`padding:12px 14px` 五处手写 = 三皮肤下无法按皮肤调(而 console_hub.css 是三皮肤共用通道, 正是为这种场景设的); ②`width:110px`(traffic:186 的 period 输入框)与 `max-width:60ch`(traffic:73)这类具体数字更无法按皮肤适配; ③与 R22 里"三皮肤 views.css 有 `--` 令牌"的体系不合
- 建议收敛形态: 把 5 处 `padding:12px 14px` 提为 `.hb-blk-bd` 类(console_hub.css 单点); 其余一次性几何保留但集中在此处注释说明"本分片的内联几何是有意的一次性布局, 非可复用间距"。属 CSS 侧改动, 与 R22 合批
- 预估收益/风险: 收益低-中(皮肤可调性); 风险低(纯间距)

**R23-B-21** · 抽屉三件单点组件正例(`aq-drawer-head` / `aq-qb-ctl` / `aq-traffic-card`)
- 位置: `drawer-head.html:25-39`(`tpl-aq-drawer-head`)·`40-59`(`tpl-aq-qb-ctl`)·`traffic-card.html:16-317`(`tpl-aq-traffic-card`); 调用点 `drawer.html:34`·`40-66`·`183` 与 `settings.html:316`
- 类别: D
- 为何不动: 三处头注完整记录了**收敛动机与代价**: ①`aq-drawer-head` 把"两形态各写一份 `<header class="drawer-head">`"收成外壳 + 默认插槽, 且解释了"这不违『不共用头部』的语义"(两形态中部仍各自给), 并指出这正是坑档 `drawer-multi-form-hosts` 的根因预防; ②`aq-qb-ctl` 注明了"必须多根片段(不留 wrapper)"的原因(三皮肤 CSS 靠直接子选择器 `.qb-statctl > .qb-tabs`), 且说明"多包一层 div 会让规则全部静默落空, pytest 扫源码看不见、只有真浏览器量布局才现形, 故由 e2e 按直接子元素钉住"; ③`aq-traffic-card` 注明了抽组件的触发条件(单分片 400 行上限)与"去嵌套"的版式动因(三层同名标题)
- 预估收益/风险: 不动。**这是 S5 归档应引用的成功范式**: "单点 > 同源"这句话(`drawer-head.html:22-23`)是本轮所有 A 类建议的共同落点

**R23-B-22** · 位置契约与裁剪坑的正例三则
- 位置: ①`settings-detail.html:232-241`(HR 全屏覆盖层)**必须**是 `.hb-blk` 的兄弟而非子节点 —— atlas 的 `.hb-cut` 带 `clip-path` 会把 fixed 后代裁到块盒内; ②`settings-detail.html:486`(`hb-pop` 的就近说明浮窗, 箭头是**独立元素**否则被面板 `clip-path` 裁掉); ③`xtpl.html:353-357`(`dtBridgeTargetOn` —— 布局换代时 teleport 会挂到已消失目标上, Vue 生产版静默不挂子节点, 卸载时对 null 解构抛 TypeError 导致整次 patch 中断)
- 类别: D
- 为何不动: 三处都是**机制性约束**(浏览器渲染 / Vue patch 顺序), 注释即唯一防御。与 R23-A-15 的"根层浮层 / teleport 位置契约"同族, 同判 D
- 预估收益/风险: 不动

**R23-B-23** · cells 渲染器"每行模型单份"正例
- 位置: `xtpl-cells.html:1-12`(头注: 三类 group/torrent/show-ep 各一份, 替代此前"groups.html 49 条 / torrents.html 28 条 / shows.html 剧行+集行各 ~11 条"的内联分支链) + `xtpl.html:255-262`(`tpl-aq-member-cells`: 28 列只此一份, 替代 groups/shows 各一份逐字近似副本) + `xtpl.html:201-212`(`tpl-aq-table` 表壳, 替代"5 份逐字近似的表头块")
- 类别: D
- 为何不动: 这是 P1/P2/P3 计划已完成的收敛, 头注把"收敛前后数量 + 漏改后果 + 多根片段约束 + `$root` 取值纪律"四件事全写上, 并指出守阵 `_scan_column_cells_paired` 已同步改扫。**这正是 R23-B-05/07 建议收敛时应参照的模板**: 同一次收敛顺手加守阵, 否则三份拷贝还会长回来
- 预估收益/风险: 不动

### R23-C 三套 index.html 骨架(5 项: A2/C1/D2)

范围与实测(三份逐段 diff, 非抽样): `atlas/index.html` **208** 行 · `console/index.html` **212** 行 · `prism/index.html` **212** 行。结构切分(以 atlas 计): head 资源清单 `1-17` / sprite `19-98`(**80 行, 67 个 `<symbol>`**) / `#app` + login-mask `100-130` / `tpl-manifest` JSON `131-204` / tail `205-208`。

三份 diff 的**全部**内容(atlas↔console 5 个 hunk, console↔prism 7 个 hunk):
- `<html>` 属性: atlas 无 / console `data-theme="ocean"` / prism 无
- `<meta name="color-scheme">`: atlas 无 / console `dark` / prism `dark light`
- `<title>`: 星图 / 控制台 / 棱镜
- head 的 CSS 资源清单: atlas 4 链接(style+components+views+dialogs) / console 同 4(但 prism 风味注释) / prism **10 链接**(tokens+5 themes+base+components+views, **无 dialogs**)+ `theme.js` 前置脚本
- 3 处注释措辞差异 + 3 个空行

⇒ **除 head 资源清单外, 三份 shell 逐字同**: sprite 80 行 `diff` 空、`tpl-manifest` 74 行 `diff` 空、`#app`+login 段 31 行仅差 1 行注释 + 1 空行。逐字同的部分 ≈ **182 行 / 208 行 = 87.5%**。

这也印证了 jscpd 报的 markup 3 克隆里最大两块(`login-mask` 107 行 / `sprite` 85 行)的归属 —— 它们不是"某段代码巧合相同", 而是**ship 契约要求三份 shell 同构**。

**R23-C-01** · sprite 图标清单 80 行 / 67 symbol 三份逐字同
- 位置: `atlas/index.html:19-98` · `console/index.html:19-98`(行号同, 因 head 差异被注释吸收) · `prism/index.html:22-101`
- 类别: A
- 重复对象: 整个 `<svg class="icon-sprite" aria-hidden="true" focusable="false">` + 67 条 `<symbol id="i-*">` 块, **三份 `awk` 提取后 `diff` 输出为空**(逐字节同)
- 分歧点: 无 —— 唯一差异是块前那行注释的措辞(atlas/prism 写"use 引用, 无外部图标库依赖", console 写"与 atlas/prism 同一份清单(brand 仍用 i-orbit)"), 而 console 那句注释恰好**是错的**: 它说"与 atlas/prism 同一份", 但三份是物理拷贝而非共享源
- 维护风险: **加一个图标要改 3 个文件, 漏一个的表现是"某皮肤下该图标空白"**(`<use href="#i-new">` 指向不存在的 symbol → 静默不渲染, 无控制台报错)。这是最容易漏且最难发现的一类: 功能测试在开发用的那套皮肤上通过, 另两套坏。实测 67 个 symbol 里有多个带"第X轮新增"注释(`i-panel`/`i-history`/`i-select-all`/`i-spark` 等), 说明历史上已多次走"改三份"流程
- 建议收敛形态: **不合并, 改守阵**(理由见 R23-C-04)。具体 = 在 `tests/test_webui_static_skins.py` 加一条断言: 三份 shell 的 sprite 块 `awk` 提取后必须**逐字相等**, 附失败信息指明"改图标须三皮肤同步"。成本约 15 行测试, 收益 = 把"靠自觉"变成"CI 拦"。若日后想真合并, 唯一无损路径是后端渲染时注入(见 R23-C-02 的风险段), 但会破坏静态文件直开能力, 不建议
- 预估收益/风险: 收益中-高(消灭"三皮肤图标不同步"这一整类缺陷); 风险极低(只加测试, 不动源码)

**R23-C-02** · `#app` + login-mask 段三份逐字同(实差仅 1 行注释)
- 位置: `atlas/index.html:100-130` · `console/index.html:103-133` · `prism/index.html:106-132`
- 类别: A
- 重复对象: `<div id="app" v-cloak>` + `login-mask` 登录遮罩两态(`bootstrapping` 加载卡 → 密钥输入表单), 含 `login-card`/`brand`/`brand-img src="/shared/icon.png"`/`ico spin`+`#i-orbit`/`v-if="authRequired"` 判据链, 约 **28 行**
- 分歧点: 仅 console 多一行注释("—— 结构与 atlas/prism 同一份, 控制台皮肤只换视觉"), 与 1 个尾部空行。**结构零差异**
- 维护风险: ①`login-mask` 是**首屏第一眼**且在任何 JS 之前渲染(Vue 挂载前就要能显示加载态), 改错直接影响"打不开/白屏"; ②`bootstrapping` 这个防闪现判据(`修复刷新时闪现输入密钥界面`)只在一处注释里说明, 三份拷贝 = 三份可能被单独改坏的窗口; ③`/shared/icon.png` 是唯一跨皮肤共用资源, 若日后按皮肤分图, 三处都要改
- 建议收敛形态: 同 R23-C-01 —— **不合并, 加守阵**。同一断言函数可一并覆盖("shell 的 sprite 段与 login 段三份逐字相等")。**明确不选**"后端注入"路径的原因: `index.html` 现为可直接静态打开的文件(测试亦直接读盘), 引入服务端文本替换会让 `file://` 直开与静态托管失效, 属能力回退
- 预估收益/风险: 收益中-高; 风险极低(仅加测试)

**R23-C-03** · head 资源清单三套(prism 10 链接 vs 另两 4 链接, 且无 dialogs.css)
- 位置: `atlas/index.html:8-12` · `console/index.html:9-15` · `prism/index.html:9-19`
- 类别: C
- 重复对象: "一套皮肤 = style/tokens + 分层 components → views → dialogs + shared 两件"这一资源组装事实
- 分歧点: ①atlas/console 用"单 style.css 内联令牌 + 3 个分层文件"; prism 用"tokens.css + 5 个 themes/*.css + base.css + components + views"(**无 dialogs**), 即令牌载体与分层数两处不同; ②prism 多一个 `<script src="/prism/js/theme.js">` 且**必须在 head 同步执行**(首帧前定 `data-theme`, 防 FOUC —— 注释已写明); ③三份都挂 `/shared/console_hub.css` 与 `/shared/dt_table.css`(共用通道, 已有守阵钉"各挂载一次")
- 维护风险: 本项与 **R22-C-08 是同一事实的两个投影**(CSS 侧看是"prism 无 dialogs.css", markup 侧看是"链接少一条"), 入池时须合并为一个 issue, 否则会被当成两件事各修一遍。风险实体同 R22-C-08: prism 的弹窗族更早介入级联, 同名覆盖方向与另两皮肤相反
- 建议收敛形态: 同 R22-C-08(恢复 prism 的 dialogs.css 分层), 本项只作为"改动落点在 markup 侧"的补充指引 —— 改分层时三份 head 都要动, 且 `test_webui_static_skins.py` 的 CSS 链接序断言会在此处报红(这是好事, 说明守阵有效)
- 预估收益/风险: 与 R22-C-08 合并计; 单看本项收益低(链接顺序本身无害), 价值在于**定位改动落点**

**R23-C-04** · `tpl-manifest` 55 条 + 既有守阵 = shell 收敛的正确模板
- 位置: `atlas/index.html:131-204` · `console/index.html:135-208` · `prism/index.html:135-208`(三份 `sed` 提取后 `diff` **全同**); 守阵 `tests/test_webui_static_skins.py:1725-1860` 已钉 manifest 逐项相等 / CSS 链接序 / 700 行 CSS 上限 / 212 行 shell 上限 / 400·560 行分片上限 / 盘上孤儿分片 / `_scan_ui_diff_registry` 活跃差异清单
- 类别: D
- 为何不动: manifest 同样是三份物理拷贝(74 行), 但它与 sprite/login 的区别是 **`diff` 已被守阵强制相等** —— 抄漏一个分片 CI 即红。这正是 R23-C-01/02 建议的形态: 重复本身不可怕, 无守阵的重复才可怕。**现状是 shell 里三块拷贝(manifest 已守 / sprite 未守 / login 未守), 收敛只需把守阵覆盖补齐, 无需动源码**
- 预估收益/风险: 不动; 作为 R23-C-01/02 的实施方案样板

**R23-C-05** · head 分层约定注释正例
- 位置: `atlas/index.html:9`("W2 分层(26-09-26-2233): 令牌+基线留根 style.css, 链接顺序即级联序(components → views → dialogs)") · `console/index.html:9-12`(同 + "设置页继续吃 shared/console_hub.css(与另两套同源)" + "主题: V1 固定深海机房单主题…五主题切换仍属棱镜 ui-diff 口") · `prism/index.html:9`("主题引擎必须在 head 同步执行(首帧前定 data-theme, 无 FOUC)")
- 类别: D
- 为何不动: 三处注释各自记录了**该皮肤特有的约束**(级联序 / 单主题退化 / FOUC 同步), 是 R22-C-08 修复时的判断依据; 合并成一处会丢失"哪条约束属于哪套皮肤"
- 预估收益/风险: 不动

## 分类计数

| 子轮 | A | B | C | D | 小计 |
|---|---|---|---|---|---|
| R20-A | 3 | 0 | 2 | 1 | 6 |
| R20-B | 5 | 0 | 3 | 4 | 12 |
| R20-C | 13 | 1 | 4 | 4 | 22 |
| R20-F | 1 | 0 | 3 | 2 | 6 |
| R20-D | 3 | 0 | 7 | 3 | 13 |
| R20-E | 2 | 0 | 5 | 3 | 10 |
| R21-A | 5 | 1 | 5 | 1 | 12 |
| R21-B | 6 | 2 | 2 | 1 | 11 |
| R21-C | 5 | 2 | 3 | 1 | 11 |
| R22-A | 0 | 0 | 2 | 3 | 5 |
| R22-B | 4 | 0 | 1 | 1 | 6 |
| R22-C | 6 | 0 | 2 | 1 | 9 |
| R23-A | 7 | 3 | 3 | 2 | 15 |
| R23-B | 9 | 6 | 5 | 3 | 23 |
| R23-C | 2 | 0 | 1 | 2 | 5 |
| **R20–R23 已审合计** | **71** | **15** | **48** | **32** | **166** |
| Phase 1(后端) | 58 | 15 | 40 | 43 | 156 |
| **全局累计** | **129** | **30** | **88** | **75** | **322** |

注: R20-C-12/C-15/C-16/C-14 为跨轮族延伸(R20-B 族的第 4 处 / 第 6–10 处 / polling 对照 / 视口边距族第 7 处), 计 R20-C 名下但在入池时与 R20-B 同族 issue 合并讨论。

## 进度日志

### 2026-10-20-2108 R20 机器提名(S1/S2)

- jscpd 全前端 121 克隆/2525 重复行(6.56%): css 74(18.55%)/javascript 44/markup 3; JS 字面重复仅 3 处(均落入 R20-A), 证实主战场 = 结构线索 grep + 精读。
- 结构线索 grep: 格式化助手/escape/debounce/localStorage/JSON.parse+兜底/单位转换六路, 产出跨轮候选池(IME 守卫/Bearer/超时常量/单位梯四族已定性)。

### 2026-10-20 R20-A~F 六面精读与判定(S3/S4)

- R20-A: 表格视图面 6 项(A3/C2/D1); jscpd JS 3 处字面克隆全部命中(sort↔filters / filters↔hr / selection shift 对)。
- R20-B: 交互控件面 12 项(A5/C3/D4); dialogs.js 三骨架族(mgr CRUD 5/面板加载 5/POST+waitCmd 4)为主战果; menu 两级溢出分歧为注释声明正例。
- R20-C: 配置编辑面 22 项(A13/B1/C4/D4); 三份"schema→默认值梯"为最缠绕发现(互相嵌套); B 类 1 项(空列表删键 vs 写 [])待后续轮裁定。
- R20-D: 运行时骨架面 13 项(A3/C7/D3); localStorage 读入族(白名单 7 处同构 + JSON 五种兜底)与浮层 watcher 族为主战果; Esc 链(20 项)/click 收层(12 项)/escBusy 三张浮层名单确认并列, 收敛需注册表化。
- R20-F: 横切支撑 6 项(A1/C3/D2), 与 R20-C 补核同步完成(Bearer 4 处/IME 6 处计数已实测)。
- R20-E: 领域页面 10 项(A2/C5/D3); 主战果是**浮层定位几何五处手写**(R20-B 的 8px 小项升格)与**长驻轮询启停第二份**(抽屉侧缺 qb 侧已修的悬挂兜底 —— 实质缺陷面); 三条时序曲线渲染栈判 D(渲染栈三分, 不属重复)。
- R21-A: 抽屉底座 12 项(A5/B1/C5/D1); 主战果是 **drawer_store 四 fetcher 同骨架 4 份**(A, 建议收敛形态 1 份骨架 + 4 差异项)与**限速对话框双胞胎**(单选/批量 30 行逐字同); 唯一 B 类是**文件优先级文案表键集不一致**(4 档只在行渲染侧存在); combobox 键盘导航扩到 5 处且**本处缺 IME 守卫**; 抽屉层单点件(形态判据/竞态/落定/键名适配)判 D 正例。
- R21-B: 变体 general+trackers 11 项(A6/B2/C2/D1); 主战果是**三态空帧+整帧换帧骨架 12 份**(general 三件各 1 次 createContextualFragment、bridge 九件各 4 次 = 三态+整帧, 实测计数); B 类两项:**HR 摘要三段式已分叉**(03 版式整段缺 hr_state, 文案/tone 三套)与 trackers「渐进省略」判据两套; helpers 未覆盖的面(ICO_TONE 4 份/STATE_TEXT 3 份/注册壳 12 份)全部登记。
- R21-C: 变体 peers+content+bridge 11 项(A5/B2/C3/D1); 主战果是 **peers 判据四件 3 份逐字同**(吸血启发式/flag 分桶/内网判定 —— 判据漂移会让同一 peer 在三版式下分桶不同)与 **peers 双形态归一 5 处**; B 类两项: content 目录树两份且聚合字段已分叉、trackers 分桶表 BUCKET/GROUPS 两种形状; **PRIO_LABEL 三份含 4 档**加固了 R21-A-06 的 B 判定(5 份表里 setFilePriority 是唯一孤立缺档)。
- R23-A: 模板上半 15 项(A7/B3/C3/D2), 1585 行/12 件; 机器提名 markup 仅 3 克隆且全部不在此子轮, 本子轮 15 项 **100% 来自结构线索 + 精读**。主战果三项: ①**combobox 输入行+候选面板 5 处逐字同(~100 行)** —— 状态层已单点(`comboHoverIdx` 按 key 分派)、模板层仍是 5 份, 且 40ms 合帧坑档在 5 处各写一遍; ②**对话框外壳三段 11 处**(mask 手势 10 / title 头 11 / actions 栏 11), 其中"mousedown 记臂位 + mouseup.self 关窗"这个 2026-10-03 报障的修复只在一处有出处注释; ③**`.ctx-item` 渲染骨架 5 份** —— 注册表已把"项集"单点, 但骨架仍是四支各一份, 正是模板注释自己警告的"四支人肉奇偶"。B 类三项最有价值的是 **`modal-details` 行式键值两套**: `d.hint` 只对 details 生效(verdict 静默忽略), 且 `String(d.value || '')` 在 `value === 0` 时不出复制钮(0 值边界, 与后端 `||`/`??` 族同源)。
- R23-B: 模板下半 23 项(A9/B6/C5/D3), 2384 行/8 件; A 类密度为 Phase 2 最高(9/23)。主战果五项: ①**`.hb-switch` 开关 7 处**(4 带"启用/关闭"文字、3 不带, 且同位置的 section 段开关一个带一个不带 = 纯漂移); ②**`hb-sub-toggle` 折叠段头 5 处**且 toggle 签名三种(字符串 key / 组件方法 / 双参数); ③**抽屉 peer 渲染器 dt07/dt08 除 CSS 前缀外逐字同、dt09 仅 1 处特化** —— 注释已自认"同款单元格", 仍是三份拷贝(加一个 peer 列要改 3 处, 漏改 = 该变体该列空白且无报错); ④**`.empty` 空态 11 处**(含 R23-A-05 的 3 处)里 settings-detail HR 表 3 处**连图标都不写**; ⑤**`.site-chip` 3 份**且 torrent 版缺 `search-hit` —— 与 `torrents.html:8` 行级同缺, 构成"种子页搜索不高亮"的跨文件功能遗漏。B 类最有价值的三项: `aq-table` **thead/grid 双分支排序箭头口径相反**(每列都有箭头 vs 仅当前列, 无注释说明); `hrGroupTitle` 单点已存在但 ep 行**内联手写四层三元绕过它**; drawer 四页签宿主的**合并态已数据驱动、非合并态仍硬编码字面量**(W4 收敛只做了一半的直接证据)。
- R23-C: 三 index.html 5 项(A2/C1/D2), 632 行; 逐段 diff 实测结论 —— **除 head 资源清单外三份 shell 逐字同**(sprite 80 行 diff 空 / manifest 74 行 diff 空 / `#app`+login 31 行仅差 1 行注释), 逐字同部分 ≈ 87.5%。核心判断: shell 的三处物理拷贝里 **manifest 已被守阵钉死相等、sprite 与 login 未钉** —— 故本族建议一律是"**不合并, 补齐守阵**"(合并唯一路径是后端渲染注入, 会破坏 `index.html` 静态直开能力, 属能力回退), 并把 `R23-C-04` 的 manifest 守阵当作实施方案样板。C 类 1 项(prism 无 dialogs.css)与 **R22-C-08 同一事实**, 入池须合并成一个 issue。
- 全程零源码改动(git status 干净)。

### 2026-10-20-2233 S5 归档(六步 a–f)

- **a. 报告**: `reports/26-10-11-0033-report-dup-code-audit.html` 追加五小节 —— §26 R20 六面(69 项) / §27 R21 抽屉族(34 项) / §28 R22 三皮肤 CSS(20 项) / §29 R23 模板层(43 项) / §30 Phase 2 汇总(166 项 A71/B15/C48/D32; 全局 322 项 A129/B30/C88/D75)。§30 内含分类计数框 / 主战果表 / 三个 callout 方向性结论 / 30.2 A 类分布特征对比表 / 30.3 候选排序 18 行 / 30.4 入池 issue 表 / 30.5 五条结论。另: 覆盖表补 R20–R23 五行 + `Phase 2 —— 前端(webui/static/)轮 20–23` 分隔行; §2.1 补 jscpd 前端实测(121 克隆/2525 行/6.56%)与 `-f` 格式可用性(无 html)两行; §25 变更记录追加 `26-10-20-2232` 一行。
- **b. 入池**: 17 条 L1 issue(`create-issue`, type=refactor×16 + test×1, topic=`dup-code-audit`, 全部 Open 未认领), 按**族级合并**口径(与 Phase 1 的"逐轮拆分 46 条/156 项"相反, 便于一次改到底):
  - `2230-refactor-fe-combobox-family-dup` —— R20-B-05 + R20-C-12 + R21-A-04 + R23-A-01 四轮四处合并为一条(JS 逻辑 5 处 + 模板骨架 5 处 + 设置页第 6 变体; 状态层 `comboHoverIdx` 已单点, 模板层仍 5 份, 40ms 合帧坑档 5 处各写一遍)。
  - `2231-refactor-fe-` × 15: `config-default-ladder-dup`(三份 schema→默认值梯互相嵌套) / `config-entity-crud-dup` / `dialogs-js-boilerplate-dup`(mgr CRUD 5 + 面板加载 5 + POST+waitCmd 4) / `dialog-shell-template-dup`(mask 手势 10 + title 头 11 + actions 栏 11) / `drawer-fetcher-boilerplate-dup`(drawer_store 四 fetcher 同骨架) / `drawer-variant-renderer-dup`(dt07≡dt08 逐字同 + peers 判据四件 3 份) / `tpl-cell-fragment-dup` / `tpl-ctx-item-branch-dup`(.ctx-item 骨架 5 份) / `tpl-list-row-empty-dup`(.empty 11 处) / `tpl-switch-fold-seg-dup`(.hb-switch 7 处 + hb-sub-toggle 5 处, toggle 签名三种) / `css-rule-family-dup` / `css-skin-token-layer-dup`(**含 R22-C-08 + R23-C-03 合并**: prism 无 dialogs.css 的同一事实两投影) / `overlay-geometry-dup`(浮层定位几何五处手写) / `polling-family-dup`(长驻轮询启停第二份, 抽屉侧缺 qb 侧已修的悬挂兜底) / `single-point-bypass-dup`(单点已存在却被旁路的族: hrGroupTitle / 平台判定 / STATE_ATTRS 式)。
  - `2231-test-fe-tpl-shell-parity-guard` —— **唯一 type=test**: 三 shell 的 sprite 段(80 行/67 symbol)与 login 段(31 行, 仅差 1 行注释)目前**无守阵**, manifest(74 行)已被守阵钉死 `diff` 相等。补两条断言即让 CI 兜住 —— 本轮**唯一"只改测试不改源码"就能落地**的收益, 也是 R23-C "不合并, 补齐守阵"建议的实现样板。
  - `issues/_index.md` 由 `gen_issues_index.py` 重建, `fe-` 前缀计数 17。
- **c. activeContext**: 新建 `activeContext/26-10-20-2233-dup-code-audit.md`(slug 复用, dup-code-audit 时间线第 6 片), 载 Phase 2 全量结论与六条关键结论, 指向报告 §26–§30 + 17 条 issue。
- **d. 索引**: `kb.index` 重建。
- **e. 零改动**: `git status --porcelain` 仅 `memory-bank/` 路径(`issues/_index.md` + `issues/attachments/_archive.md` + 报告 M, 17 条新 issue + 本档 ??), **`src/` 与 `tests/` 为空** —— 纯审查纪律自 R20 开工至 S5 收口全程未破。
- **f. 遗留**: 本档无剩余项。Phase 2(轮 20–23)全部 Done; 主线续跑 Phase 3(轮 24–25 测试与横切)→ Phase 4(轮 26 汇总: 322 项总排序 + 跨层同一事实对账 + 未入池候选清偿顺序)。

## 待办

1. ~~R21-A~C 抽屉族~~ **Done**(A5/B1/C5/D1 · A6/B2/C2/D1 · A5/B2/C3/D1 = 34 项)
2. ~~R22-A~C CSS 三皮肤~~ **Done**(C2/D3 · A4/C1/D1 · A6/C2/D1 = 20 项; css 74 克隆/18.55% 已定位到三皮肤 views/dialogs 互克隆)
3. ~~R23-A~C 模板层~~ **Done**(A7/B3/C3/D2 · A9/B6/C5/D3 · A2/C1/D2 = 43 项; 20 件 tpl 实测 3967 行 + 三 index.html 632 行)
4. ~~consolidated **S5** 归档~~ **Done**(六步 a–f 全部落地, 见下方进度日志 `2026-10-20-2233 S5 归档`):
   a. ~~滚动报告追加 s26–s30~~ **Done** —— 实为五小节(比台账原写的 s26–s29 多一节 Phase 2 汇总), 按报告既有编号续排 §26/§27/§28/§29/§30。
   b. ~~A 族入池~~ **Done** —— 17 条(16 refactor + 1 test, 族级合并), 全部 `topic=dup-code-audit` / `doc-refs` 指本档 / 正文无 TODO 残留。
   c. ~~activeContext 切片回写~~ **Done** —— 新建 `activeContext/26-10-20-2233-dup-code-audit.md`(slug 复用, 同 dup-code-audit 时间线第 6 片), Phase 2 置 Done 并指向 S5 产出。
   d. ~~`kb.index` 重建~~ **Done** —— `issues/_index.md` 的 `fe-` 前缀计数 17 已核。
   e. ~~零改动确认~~ **Done** —— `git status --porcelain` 仅 `memory-bank/` 路径, `src/` 与 `tests/` 为空。
   f. ~~R23-C-01/02 守阵 issue~~ **Done** —— `26-10-20-2231-test-fe-tpl-shell-parity-guard.html`(本轮唯一 type=test, 也是唯一"只改测试不改源码"即可落地的收益)。

**本档无剩余项。** Phase 2 前端全部收口, 主线续跑见计划 `26-10-10-2333`: **Phase 3 = 测试与横切(轮 24–25)** → **Phase 4 = 汇总(轮 26)**。
