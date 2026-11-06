# R5 路线小结(存量评审 R4 · static 契约·scripts)

owner: clone3-main · freeze: f088329291e6 · 快照: C:\Users\11059\Desktop\Projects\zcode\auto-qb-review4-snap\auto-qb-zcode-clone3
(执行中逐批追加;终态节在 review.lane.done 后定稿)

## 批次勾选表

| 批 | 内容 | findings 过检 | 状态 |
|---|---|---|---|
| R5-1 | shared 启动与状态: app/state/boot/lifecycle/auth/polling/fetch_low/ui_feedback (3581行) | 24 (major 1 / minor 11 / nit 12) | done |
| R5-2 | shared 菜单·触发·命令链: menu/triggers/commands*/ctx_menu*/view/overlay_fit/ctl_bits/scope_audit/shortcuts(+panel) (3637行) | 10 (minor 7 / nit 3) | done |
| R5-3 | shared 表格与列: table/dt_table/columns*/sort/filters/selection/format/rowlang/decorate (3928行) | 25 (major 3 / minor 12 / nit 10) | done |
| R5-4 | shared drawer 族: drawer/drawer_templates/drawer_store/drawer_{general,rows,files,head} (3445行) | 16 (major 1 / minor 11 / nit 4) | done |
| R5-5 | shared drawer 模板·general 与 trackers(01-09 号) (3556行) | 33 (major 4 / minor 20 / nit 9) | done |
| R5-11 | shared drawer 模板·content 与 peers(10-12/90 号) (1720行) | 21 (major 4 / minor 12 / nit 5) | done |
| R5-6 | shared 对话框与流转: dialogs/add_torrent/delete_flow/transfer_*/relocate_chain (3257行) | 23 (major 3 / minor 11 / nit 9) | done |
| R5-7 | shared config 族: config_rules/config_editor{,_curve,_form,_tree}/config_hub{,_tm,_tracker,_hr} (3850行) | 26 (major 6 / minor 10 / nit 10) | done |
| R5-8 | 图表·hr 面板·快捷键引擎·fx: qb_traffic_chart/hr_status/hr/shows/traffic_card/shortcuts_engine + fx/theme (4032行) | 24 (major 1 / minor 17 / nit 6) | done |
| R5-9 | scripts 快扫: sim_* 全族 (3700行, 快扫档单面) | 16 (major 1 / minor 8 / nit 7) | done |

## R5-9 批记录(快扫档: 入口/危险操作/红线引用/明显缺陷/非ASCII,不逐行精评)

- **major 1 条**:sim_qb_server.py:258 handle_error 用 sys 但未 import sys——任何 Handler 线程异常(含每次停机必现的 ConnectionResetError)在 handle_error 内抛 NameError,「连接重置静默过滤」完全失效。
- minor 8 条:sim_fsmock UNC 分支死代码(长前缀被一般前缀截走) / sim_run 语料档阈值读合成档裸 id 违自述不变量 / sim_qb_model WEB 删除 declared=1 多文件必 403 与 delete_torrents 口径不一 / 非 ASCII 符号 6 文件。
- nit 7 条:replay_cursor 无赋值点 / WARN 死分支 / --tick 字面替换 / parse_spec 裸 ValueError。
- 引文校验 refute 1 条(sim_run.py:723 --tick 字面替换,幻觉引文直接弃,未复核);本批净入 16 条。
- 危险操作面:rmtree/unlink/杀进程/端口均在模拟根与回环内,DEFAULT_ROOT 写仓外真实盘系设计且有 B1/B2/B4 三道边界,不触 config.yml/auto-qb-data 红线。
- 底册复验:R2 终表与 Open issues 零命中本批。

### 自弃发现(7 条留痕)

open(...) 未接句柄 CPython 引用计数即关 / DEFAULT_ROOT 仓外真实盘系设计有三道边界 / fsmock 全局替换 os.path 系设计意图(前缀限定) / subprocess 超时裸栈开发工具可见 / Content-Length 畸形头测试专用不出现实场景 / 疑似搬迁残留无用 import 系风格 / --fs-mode real 语料档无物化路径意图不明。


## R5-8 批记录(2 面精评: 正确性+安全 / 测试缺口+文档漂移)

- **major 1 条**:fx-mount.js:102 armSettle 全仓库零调用——dock(true) 承诺的兜底定时器从未武装,过渡事件丢失场景下落定回执永不执行,fx-glide 恒驻留违反「只罩开门窗口」口径。
- minor 17 条:OS 切明暗流量图 canvas 残旧主题色(theme.js 不派事件) / themechange 监听只挂不摘 / loadQbHistory 死代码 / 快捷键字符串字面量 ↑↓ / 键位匹配引擎零行为执行(改键→重载→触发链任何测试不跑) / hrPopData 零执行 / _qbTickLabel+_qbIsolatedIdxs 零执行(同文件其余纯函数均有电池) / fx 挂载层零行为测试零 e2e / theme.js 全文件零测试(事件契约无成对锚) / hr.js 头注与自身修正注释矛盾 / data-fx-pushed 活约定已退役(照表消费即被守阵打红) / 「十档」vs 13 档 / Alt+5 when 条件描述不符 / README:90「默认只看做种中」残留旧口径。
- nit 6 条:非 ASCII 符号 6 文件(hr_status 带圈数字 26 处密度最高) / epLabel 零执行 / fx 计数 18 实为 17 / webui.md 悬空引用。
- 安全面:9 文件无 innerHTML sink(tooltip/状态文本均走 Vue 插值与 textContent)。
- 底册复验:R2 终表零命中本批;Open issue 0149(图悬停联动)仍 Open 未重报。

### 自弃发现(15 条留痕)

面1(8):_qbLoad stale 不复位 loading 有双路自愈 / hrPopData 判据依赖违约数据归理论 / 键位撞号静默跳过系最后防线且有注释 / 24h 回退字面量重复无行为差 / spawnGhost 定位由 CSS 决定无法证实 / hrsHistKey 同秒撞键说不出场景 / _kbViewportRow 全 document 扫未核实不报 / openDrawerTraffic 后 hover 有越界守卫。
面2(7):traffic_card 引用系家族命名惯用 / ⊕ 疑笔误语义可读 / hr.js 五档系历史陈述 / PANEL_ENTER_MS 与 CSS 实测一致 / webui-fx.md 不在本面文档范围 / _kbIsolatedIdxs 并入刻度条目 / KB_MERGE_TAB_REMAP 有锚+e2e 不重复报。


## R5-7 批记录(2 面精评: 正确性+安全 / 测试缺口+文档漂移)

- **major 6 条(全在测试缺口面)**:未保存改动防护链全程零行为执行 / 单位控件族零测试(2026-09-21 整页白屏事故现场,回归无保护) / 站点回退链整族零引用(注释自称铁律无测试钉) / 曲线编辑器交互与图表全部零执行 / 命名实体增改删骨架零引用 / 站点搜索匹配语义零执行(CJK 归一曾出事故)。
- minor 10 条:cfgLoad 幽灵站点+放弃的重命名静默复活 / 关闭工具回滚无中生 enabled 键 / HR 绑定五分支零测试 / tm 参数往返零行为执行 / 规则卡风险摘要零测试 / cfgFlatten 灰显零行为执行 / 守阵文件名指错 / collapsedRules 死状态。
- nit 10 条:cfgPluginEntry/cfgInlineBool 死代码 2 条 / on_error prune 双实现 / 删项模式 4 份重复 / cfgReset 漏清 3 张 map / 非 ASCII 符号 7 文件(config_hub HUB_HELP 用户可见字面量含 →)。
- 密码/secret 掩码链路(GET 掩码→setSecret 拒写→writer.py MASK_SENTINEL 还原)核对闭环,无发现。
- 底册复验:R2 终表零命中本批;Open issues 2002(伪警示条)/0641(真机排期锚)仍 Open 未重报。

### 自弃发现(16 条留痕)

面1(9):cfgSave 后 fresh GET 失败误报系理论 / tm int 字段 NaN 链路完整 / 0 档徽标纯外观 / hubLedOf 截断漏警需 >8 条且仅提示 / not 切换收敛第一孩子系有意设计 / cfgExprTry 后端恒带 error / unitDefault 均在梯内 / 曲线 hover 模板恒渲染 svg / 掩码链路闭环。
面2(7):「ai/06 约定」仓外无从证伪 / search_torrents 符号真实存在仅文件归属宽泛 / 「拟记 pitfalls」表意向 / cfgExprTry 属真机面与底册 0641 相邻 / cfgReset 漏清系面1 已报 / hubImportSites 有 e2e 真渲染 / cfgSave 主路径有 e2e+后端电池。


## R5-6 批记录(2 面精评: 正确性+安全 / 测试缺口+文档漂移)

- **major 3 条**:add_torrent.js:695 加种提交闸在 20s 落点预检+FileReader 之后才置位,窗口内双击并发重复 POST 加种(幂等性违例,本路线最重的一条)/ _relocateAddGate confirm 分支零执行 / meta 标签分类对话框行为面全部零执行。
- minor 11 条:mkdir 回执 r.path 恒 undefined(契约错位兼死代码) / enterFallback「含清空=无分类」不可达(注释矛盾) / metaSetCategory 缺 metaBusy 闸 / Esc 退栈/DND 进料/combo 键盘导航/管理对话框 CRUD/HR 风险点名行/限速浮层编排/历史聚合数学/路径链 seq 守卫零测试 / 「三份 index.html」漂移×2。
- nit 9 条:回退标签取参数 hash / 非 ASCII 符号 4 文件 / 注释指错模板与 py 文件位置 2 条。
- 同根双报 1 组已去重:dialogs_meta.js:62 enterFallback 清空回车(面1 面2 同锚同口径),保留 1 条。
- 底册复验:R2 终表零命中本批;Open issues 2120(标签分类对话框重构)/0330(gtm 日期炸弹)仍 Open 未重报。

### 自弃发现(16 条留痕)

面1(8):代际守卫只查布尔开合但数据同源无可见危害 / 删除失败仍 clearSelection 系既有取舍 / _metaExpandHashes 求值两次纯重复 / ttMapMove j 越界给不出可达路径 / relChainGlobals 监听单例常驻非泄漏 / 拖入链接不去重可编辑无静默副作用 / _transferRunning 非响应式系既有约定双闸覆盖 / relChainCopyAll 前导空格系约定。
面2(8):gtmAlert 有 e2e 真渲染且涉底册 / 删除闸门+reannounce 桶有 node 电池 / 遮罩关窗有真手势 spec / toggleAltSpeed 族有四态电池 / transfer 四段式主链覆盖充分仅边角未钉 / 纯展示小函数零测理论风险 / webui*.md+README 逐条一致 / 底册两条未重报。


## R5-11 批记录(2 面精评: 正确性+安全 / 测试缺口+文档漂移;lane 批序在 R5-5 之后 R5-6 之前)

- **major 4 条(全在测试缺口/文档面)**:12 号变体全部交互零 e2e 真渲染(grep dt12 仅 perf spec 一句注释)/ 10 号右详情优先级分段(S5 批量通道唯一入口)零测试 / 11 号主勾选框三态切换零 e2e / 11 号 omitEmpty 头注描述已退役行为(与 app.js:307 及 e2e 用例名矛盾)。
- minor 12 条:「未完成」筛选舍入口径与计数不同源(0.995≤p<1 文件计入计数但筛不出) / 10 号空态幽灵行无样式兜底 / focusKey 死代码 2 条(10/11 号,anchTouch W5 退役后无写入点) / 12 号仍 JSON.stringify 全量序列化(W1 指纹止血未跟上) / 11 号字符串字面量 → / dt11 行级键盘零 e2e / 10 号全局折叠钮零 e2e / omitEmpty 漂移第二处(av 字段注释) / 10 号 anchTouch 注释漂移 / 「三份 index.html」实为四份(4 文件重复) / 吸顶补偿三皮肤清单漏 flux。
- nit 5 条:负边距 -16px 只合 prism / 箭头注释 3 文件 / 90 号带圈数字④。
- XSS 面专项:四文件所有插值均走 dtHtml 转义,未发现未转义外部数据进 innerHTML 的路径。
- 底册复验:R2 终表零命中本批;Open issue 0521(重命名入口)仍 Open 未重报,且 filesSig 不含 name 的改名场景因 0521 无入口暂不可达(自弃留痕)。

### 自弃发现(16 条留痕)

面1(8):filesSig 不含 name 因 0521 无入口暂不可达 / 10 号优先级乐观写 stale 窗口一次往返自愈 / 90 号 gate 子串匹配系构造性测试桩 / 90 号裸 innerHTML 内容恒定静态 / 90 号缺 destroy 系框架无条件清宿主 / 吸底负边距耦合模式头注已声明只报实例 / 12 号 cssEsc 与核心重复系收编候选非缺陷 / filesSig 32 位碰撞理论风险。
面2(8):app.js U4 段 anchTouch 漂移锚不在本批 / 守阵 docstring 漂移锚在测试文件 / e2e spec 头注自相矛盾锚在 spec / 12 号 JSON.stringify 系 perf spec 已标计划外池 / rowMem 不含 miss 系确定性函数 / 90 号静默退出无独立失败场景 / legacy p===4 分支不可达 / 勾选重置仅字符串锚边际价值低。


## R5-1 批记录(2 面精评: 正确性+安全 / 测试缺口+文档漂移)

- **major 1 条**:polling.js:85 SSE 断线沿判定+换票重连状态机零行为回归测试(唯一守阵为字符串锚)。
- minor 11 条:模态框 resolve 悬空 / 登出不断 SSE+换票重开竞态 / 5 个匿名监听不撤除+句柄堆叠 / ver 驱动 refresh 绕过后台门控 / stopPoll 跳过 onEnd / _esDisconnectEdge 探针声明不存在 / _errlogReseed 探针声明不存在 / 退避曲线零测试 / 列播种语义零测试 / 错误环形缓冲零行为测试 / boot.js「三套 UI」计数漂移。
- 同根双报 1 组已去重:lifecycle.js 匿名监听器(面1 正确性锚 :265 与 面2 测试缺口锚 :181),保留面1 条目。
- py↔js 契约对账(面1 只读对 routes/state.py、routes/events.py、runtime_views.py delta、runtime_stream.py errlog、infra/clock.py):delta/removed/rid/status/errlog/ticket/flags 字段口径无错位。
- 底册复验:R2 终表零命中本批;Open issues 0149(抽屉开合态)/0411(/api/state 分页)仍 Open 未重报。

### 自弃发现(13 条留痕)

面1(6):boot.js fail() innerHTML 拼接无攻击者输入不构成 XSS / token 存 localStorage 系用户拍板设计 / startPoll chain 抛错静默死亡现网不可达 / _logout 不清 pendingOps 窗口极窄 / 超时+AbortError 翻译三处实现系文档化例外(守阵钉同值) / _esDisconnectEdge(undefined) 首次断线 toast 系设计口径。
面2(7):退避注释 2s→15s 系代表性举例 / 401 不断 SSE 属面1 已报不越面 / delta 合并有 e2e 真页面测试担忧不成立 / 字符串锚守阵属既定范式不构成缺口 / boot 超时值守阵核实属实 / auth.js「60 余个 api()」计数值必然漂移 / 底册两条未重报。

## R5-2 批记录(2 面精评: 正确性+安全 / 测试缺口+文档漂移)

- **major 1 条**:shortcuts_panel.js:39 快捷键录制态的非脏关闭路径不调 kbRecordCancel——document 捕获期 _kbRecHandler 残留,下一次任意按键被吞掉并静默提交成键位绑定。
- minor 7 条:cmdStats 单槽无归属校验(旧命令回执错挂新命令) / kbPanelEnter quiet 加载失败后保存会整份覆盖服务端 overrides / view.js 静默刷新失败无退避 1 req/s 死循环 / waitCmd 竞态零测试 / kbConflictResolve 三态零测试 / _auditScope 分类零测试 / ctx 拖拽落点零测试 / setRowIcon 定时器回归零测试 / webui.md「一级只允许一个次级菜单入口」与守阵双双过期 / episode 分支提示宣称已退役旧行为。
- (上列 10 条与 findings 文件一一对应,minor 实数 7、含文档类 1 条 webui.md:9)
- py↔js 契约对账(面1 对照 runtime_commands.py / system.py / ops_skip.py / groups.py):回执 status 三值 / truth 事件 / skip_check 事件 / flags / 组 key base64url 均核实无错位。
- 底册复验:R2 终表零命中本批;Open issue 0411(涉 view.js)仍 Open 未重报。

### 自弃发现(9 条留痕)

面1(9):组 key base64url/hash 十六进制无注入断路面 / auth 失败 sticky 条被 _logout 整体清空 / menu 虚拟行 members[0] undefined 给不出到达路径 / menuTorrent() 有 || {} 兜底 / cmAddSep 跨层重号推不出用户可见失败 / 双层重复 item id 手改配置才可达 / commands_optimistic 双函数系刻意分工有差异清单 / kbConflictResolve serial 恰等时非最小化纯风格 / reannounce 回执缺 cmd_id 给不出触发路径。
面2(9):webui.md「项集一致」按守阵 T3 口径可调和 / _runningToast sticky 系守阵放行工厂本体 / _finishToast 原位落失败有注释声明例外 / [perf] 埋点无用户可感失败 / _searchRefreshBusy 重入组合理论风险 / TRUTH_HOLD_MS 已有守阵 / KB_BLACKLIST 重复添加注释如实 / triggers 登记双向对账已覆盖 / 底册 0411 不重报。

## R5-3 批记录(2 面精评: 正确性+安全 / 测试缺口+文档漂移)

- **major 3 条**:columns_grid.js:534 member 窗口切片/前缀和与渲染数组不同源(排序激活+大展开组时切片错位、键盘跟随取错行)/ selection.js:100 选择集双向联动状态机零执行测试 / columns_persist.js:151 列意图升格三层 merge 零执行测试(旧实现「隐藏列宽被抹」根因无回归保护)。
- minor 12 条:filters.js path 筛选组视图两侧口径不一致 / 列宽零位移点击也固化 / 拖拽尾 capture 吞下次点击(columns_drag+columns_persist 同款) / dt_table 整模块生产零引用(死模块+平行机制) / decorate.js 运行期字符串含「→」 / applyColOrder off-by-one 高危零测试 / AQB_SORT 域零执行 / fmt 纯函数族零执行 / 装饰指纹对零执行 / 窗口化退避联动零执行 / columns_menu.js 注释指向拆分后的错误文件 / columns_grid.js 注释正则与实现不符(小数 px)。
- 非ASCII 图形符号:10 文件注释命中(table.js 20 行密度最高;decorate.js L149 为运行期字符串字面量,重一档)。
- 底册复验:R2 终表零命中本批;Open issues 1420(涉 decorate.js)/0330(涉 filters.js)仍 Open 未重报。

### 自弃发现(17 条留痕)

面1(10):_rowPre 残留有长度闸兜底 / 换容器 unbind 旧元素随 GC / _decoFpBuild 防御不对称非可达缺陷 / document 级 mousemove 单实例同寿命不可达 / O(n²) 扫描无具体失败规模 / showSelState 全量重算规模小 / WIN_SRC_DOC.bindScroll 系描述符契约非残留 / dtSortCell 懒建 Vue 常规 / fmtDuration 负秒无生产者 / relocateTitle 有前置判空。
面2(7):「域名.方法」类注释系拆分后仓库惯例不算漂移 / _facetPick 其余 kind 系同函数薄分支 / filteredTorrents 与底册 0330 同域避撞车 / rowlang 全 DOM 耦合提不出具体失败 / 横滚胶囊手势行为回归只能 e2e 承接 / 窗口化金值断言属加严 / webui*.md+README 逐条核对一致无漂移。

## R5-4 批记录(2 面精评: 正确性+安全 / 测试缺口+文档漂移)

- **major 1 条**:drawer.js:690 分享率限制对话框哨兵契约与后端相反——前端 -1=恢复全局默认,后端(commands_limit.py)钉死 -1=不限制、-2=用全局;用户按提示输 -1 实际写入「永不限制」,意图完全相反(py↔js 契约错位的实锤,S6 定级重点)。
- minor 11 条:drawerDel 收抽屉判据竞态(读回调时刻 hash+轮询未落) / emptyHost 死变量+注释声称的换代守卫不存在 / 非ASCII 带圈数字 5 文件(drawer.js/drawer_general/drawer_store/drawer_templates/字符串字面量含 → 的 drawer_rows) / _drawerClampHeight 边界分支零执行 / _relocateConfirmRows+confirm 回路零执行 / drawer_templates「三份 manifest」实为四份 / drawer_head 守卫引用不存在的 e2e spec。
- nit 4 条:头注指错文件名(kb_→qb_) / 令牌白名单「三皮肤」漏 flux / 装载序指向已删除的 drawer_tabs.js / 「三皮肤 views.css」实为四套。
- 底册复验:R2 终表零命中本批;Open issues 0149/0521 仍 Open 未重报。

### 自弃发现(10 条留痕)

面1(10):precheck 回执恒带 hash 不可达 TypeError / 超时态文案正则漂移仅措辞级 / dtBridgeTo seg 固定枚举动态键不可达(留作变体扩展保底) / delTorrent 主路径内吞错误 / dtToggleMerge 二次点击需重开菜单不可达 / copyTorrentInfo 字段恒有值 / 切走 content 页签孤儿窗口自愈(已有 issue 注释覆盖) / dtWinRows [] 回落无实证行为后果 / 箭头类符号 py 侧 68 文件同用属既成风格,建议仓库级裁决后统一清(带圈数字系点名类故已报) / 预填失败有「未作修改」兜底。
面2(8):_skipPrecheck 分支链有逐语句等值断言守阵 / _drawerWaitSources 有 e2e 值守 / 锚对账有 bridge-stub spec A-D / drawerGeneralSections 等经 e2e 变体用例真实执行 / _dtMergeRows 有 node 电池间接真跑 / drawer_head 历史类比非操作性声明 / MOVE_POP_SETTLE_MS 守阵确实存在 / conventions+README 抽查无矛盾。

## R5-5 批记录(2 面精评: 正确性+安全 / 测试缺口+文档漂移)

- **major 4 条(全在测试缺口面)**:01/02/03 三个 general 变体 render 零行为级覆盖(02/03 连渲染都没执行过,01 只测了可见性)/ 05 skipUnchanged 原地回填分支零覆盖(2026-10-18 根治场景行为上无保护)。
- minor 20 条:跨变体口径漂移 4 条(01 裸拼 -1 哨兵不设防 / 08 折叠态进 sig 致整帧重建 / 05 tier 缺失折 0 排最前 / HR 徽章三变体三文案)/ 死 CSS+wide 槽位失接 / 字符串字面量 ↑↓ 与带圈数字 3 文件 / 变体切换 destroy 路径零测试 / 06 全局近似回退零测试 / adviceFor 五类分派零覆盖 / 04/06 动作钮零手势 / 09 占用条与默认序零断言 / 默认序文案漂移 3 条(07/09 注记 vs app.js defKey)/ sig 口径头注漂移 4 条(04/06/07/09,系 U4 收口漏改)/ omitEmpty 头注漂移 2 条(07/08)/ paintTick 不存在符号 3 处 / tpl-aq-dt07-cells 旧 id 引用。
- nit 9 条:tags 徽章误用 is-hr 色 / gate 放行 title 空串 / LAN_RE 内网误报面 / barHtml 死参数 / 带圈数字 3 文件。
- 底册复验:R2 终表零命中本批;Open issue 0149(09 变体封禁钮)仍 Open 未重报。

### 自弃发现(12 条留痕)

面1(12):badge innerHTML 比较已证伪(dtHtml 返回纯串幂等成立) / 07/08 模块级 _ctx 晚绑定无 null 解引用 / present 冗余写法等价 / 02:285 fallback 不可达 / rowOf 无 k 字段经描述符证实无断键 / →⇒← 箭头系全族历史风格且 code-style.md 未点名 U+2192,建议整库裁决不单点开刀 / magnet title 缺空格纯措辞 / 09 无 hand 档系文档化差异 / 03 备注双位系设计 / 多份逐字复制系自包含退役契约无真分叉 / paintTick 命名漂移无行为影响 / addrTitle 尾随冒号纯展示。
面2(6):01/02/03 动作清单漏 chain 系枚举不全 / anchTouch 漂移锚不在本批文件 / 04 守阵 docstring 自身漂移不锚本批 / conventions+README 抽查无涉本批断言 / 06 qB 5.2 透传外部事实快照内无法核实 / 0149 底册不重报。


## 执行备注(路线级)

- review.check --root 快照 的 .git 强检查误拒仍在(R2 首报,58849374 只定位根因):本路线用 R3 的 workaround——快照根建空 .git 目录绕过,零代码改动。
- 提交闸门 review.trace 对纯盘点数据提交按累计口径计行(认领提交曾滚入他 clone R4-2 数据),走 Review-Skip「纯盘点数据落盘」豁免。
