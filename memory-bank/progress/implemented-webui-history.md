# 已实现 · WEB UI 历史轮次(外迁流水)

> 摘要: implemented-webui.md 超 cap 后外迁的早期长条目(2026-09-15 三条 + 2026-09-17 第 9/10/11 轮修复 + 2026-09-18/19 四条 + 2026-09-24/25 五条 + 2026-09-26 四条 + **2026-10-03 续迁 2026-09-26~10-02 十六条** + **2026-10-05 续迁 2026-10-02~10-04 十三条**) —— 冷库流水; implemented-webui.md 再超 cap 时最老条目续迁至此, 新条目仍回 implemented-webui.md。
> 触发: 第九轮, 第十轮, 第十一轮, FX-01, R10-16, 历史流水, 外迁, 键盘快捷键, 前端文件拆分, 搜索语法, 设置页分组合并

- WEB UI 第十一轮修复 (2026-09-17): 7 项 (`想法.md` 待办)。①图标语义色补齐: 导航「追剧」(新挂 `ico-tv`)与「添加种子」(新挂 `ico-add`)、状态栏「空间剩余」(`.ico-disk` 原继承 `--fg-dim` 观感无色 -> indigo)与两处「限制速度」仪表盘(-> `--limit-hit`, "不限速"只弱化数值); ②状态栏历史入口**去文字只留图标**(图标改取 today-up 族色, 否则只剩灰点); ③**明细表接入点击排序** —— 明细与三视图正交, 故新增独立 `detailSortKey/detailSortDir` + `setSort(key,'detail')` scope 分支(表头右键排序项同源), 明细列模型补 `sortable` 标记到 14 列(Hash 除外), 行序由 `sortedMembers(list)` 派生(空键=后端原序, 标签为数组故先 join 再比); ④**保存路径列迁移**: 辅种表新增(组级取首位成员值 = 路径筛选器同口径), 明细表删除(组内成员路径本就一致); ⑤**横向滚动条(三项根因, 两轮才定位)**: `.group-head` 脱离滚动容器 => 表头比 `.content` 宽时把整页撑宽(实测表头写 3000px, `documentElement.scrollWidth` 1872→3012) -> `.content { overflow-x: clip }`(clip 不建滚动容器, sticky 与表头 transform 跟随不受影响); `.detail` 自带 `overflow-x: auto` => 与外层各滚各的 -> 去掉内层滚动; **"列没溢出却常驻横滚条"的真因是单元格自动最小尺寸**(表格层 `white-space: nowrap` + 单元格 `min-width: auto` = 文本全长, 13 列累加把行 `min-content` 顶到容器之上) -> 行内单元格统一 `min-width: 0`, 行/表头保持 `fit-content`(**底色跟内容**); 中途曾用"行定宽 100%"治假滚动条, 但那会让**溢出段没有行底色/边框**(用户实测反馈"滚动后右边无背景条"), 已回退。 ⑥**标签/分类芯片改状态色**(原"分类恒蓝/标签恒灰"无语义且蓝色与"下载中"撞色), 跟随所在行状态语义色, HR 标签用 `:not()` 排除保住橙/青语义。基线 999 passed(**不变**, 前端改动由静态守阵 + 双 UI 浏览器冒烟覆盖), 档案 [tasks/TASK013](../tasks/26-09-17-webui-fix-round11.md)
- WEB UI 第十轮修复 (2026-09-17): 16 项 (R10-01~R10-16) 按成因归 7 类实施, 计划 [memory-bank/plans/26-09-17-0901-webui-fix-plan-round10.html](../plans/26-09-17-0901-webui-fix-plan-round10.html)。三条硬 bug: ①**状态栏限速读了不存在的字段名**(前端读 `server_state.dl_limit/up_limit`, qB 真键是 `dl_rate_limit/up_rate_limit`; 该字段还兼作速度染色分母 ⇒ 色阶从未生效) -> `speedLimitBytes` 取数单点, 状态栏与染色分母同源; ②**星图点一次限速开两个窗口**(`.speed-pop` 与 SPD-04 旧模态共用 `speedOpen`, 第九轮漏删星图) -> 删旧模态 + 静态断言; ③**本机免鉴权仍被弹回密钥页**(前端把"有身份"绑死"密钥串非空") -> `authMode`/`authOk` 单点判据 + 不带空 Bearer。结构性: **列对齐进列模型**(`align` + `colAlignCss` 按可见列生成 `:nth-child` 规则注入 `<head>`, `data-table` 标记表头与值, 一处改两套生效; `:where()` 压特异性以保留既有"0 值居中")与**列偏好不再重置**(跨版本迁移 `LEGACY_COLS_KEYS` + 不再用升版本应对列集变更 + 写盘容错; origin 隔离作为限制入 pitfalls)。服务端新增能力: `/api/fs/dirs`(只列目录, 允许根白名单 + realpath 边界 + 符号链接逃逸防护) 与 `/api/fs/mkdir`(单层名字 + 幂等 + 同名文件 409), `open-path` 对单文件种子改为**定位选中**; 前端新增服务端目录浏览器对话框替代自绘下拉。其余: 状态栏底色专用令牌 `--statusbar-bg` + 去文字标签 + 历史入口并入今日流量组、选中态令牌族 `--sel-*`(五主题靖蓝族, 与做种绿分家)、文本列(站数/保存路径/hash/tracker)加入行状态色、弹窗尺寸令牌族(窄/标准/表单/宽/超宽; 添加窗口两 UI 统一 860px)、值行"单行省略 + title + 复制按钮"、菜单「高级能力」→「更多操作」、抽屉目录/文件分色、删除详情行由 `_deleteDetails` 由目标集合统一派生(四入口同构); 基线 996 → **999 passed**(+open_path 平台用例 + `/api/fs/dirs` + `/api/fs/mkdir`); 双 UI 浏览器冒烟逐项实测通过(假 qB + 临时 data_dir, 完事清理)
- WEB UI 第九轮修复 (2026-09-17): 25 项 (FX-01~FX-25) 按成因归 8 类实施, 计划 [memory-bank/plans/26-09-17-0847-webui-fix-plan-round9.html](../plans/26-09-17-0847-webui-fix-plan-round9.html)。三条公共底座: ①**单元格口径单点化**(做种时长/分享率/用户·做种三列此前在模板里各写三份 -> `cellSeedingTime`/`cellRatio`/`cellPeers`, 两套 UI 共用); ②**浮层锚定契约**(`.add-dialog-pathrow` 缺定位祖先导致面板渲染到视口之外 = "点了没反应"; 退役原生 `<datalist>`; 面板锚点下沉到 `.add-input-row`); ③**暂停态中性令牌族**(五个主题各补 `--paused/--paused-soft/--paused-line`, D8=方案B 无色相)。结构性重构: **选择模型**改"互斥 + 单一权威 + 派生集合"(`selHashSet` 三视图打通 + 半选态 + 追剧页修饰键选择), **删除链**四条入口统一到 `_deleteFlow`(汇报前置 + 等待聚合回执 + 收尾清选择)。其它: 启动鉴权首帧(`bootstrapping` 初值 = 未知)、底部状态栏重排(今日流量 + 复活历史流量入口 + 速度·限速配对 + 无遮罩就近浮层)、右键菜单分层(flyout, 一级只留 PT 高频)、追剧页整剧菜单、添加窗口 760px + 选项胶囊化 + 警告行常驻占位、抽屉常规页重构(分组卡片化 + 图标色调 + 长值块行 + 行内值操作)、列头拖动虚影、文案"分组"→"辅种"(`L10N_GROUP` 单点)。新增后端只读端点 `POST /api/open-path`(路径一律服务端派生, 不接受客户端传路径)。基线 995 → **996 passed**; 浏览器冒烟 25 项全过、0 控制台错误
- WEB UI 双界面命名与目录化 (2026-09-15): 旧 UI 迁 `atlas/`(星图)、`newui/` 改名 `prism/`(棱镜), 共享逻辑层三件套+vendor+icon 收进 `static/shared/` 单一来源; web.py 加 `/`→307 `/atlas/`(默认 UI)与 `/newui/*`→307 `/prism/*` 书签兼容, 鉴权范围显式限定 `/api/*`(require_token 加 Request 路径判断, 行为等价 —— 原静态免鉴权靠 StaticFiles 不经依赖系统的副作用, 重定向真实路由后必须显式放行); atlas 顶栏切换器类 `.newui-entry`→`.ui-switch`, 互切链接文案改「星图/棱镜」; test_web 静态缓存测试路径更新 + 新增 test_ui_root_and_legacy_newui_redirect; 命名原则沉淀(身份名不代际名/目录名=URL 英文小写/中文两字/成组不撞车); 计划 memory-bank/plans/26-09-15-1241-webui-naming-plan.html
- WEB UI 旧版第八轮优化 (2026-09-15): 吸顶贴合(批量条/表头零缝堆叠, --bulk-h 剔除 margin)、筛选器幽灵空位消除(清除chip 常驻可见降透明)、删除确认框修复+扩容(`_findGroup` 优先查 decoratedGroups 修保存路径恒"—"; 批量删除补成员明细含路径; wide 560→720)、H&R 筛选(达标/未达标)、单种子视图(TORRENT_COLUMNS + 后端 `_build_singles_view` 未归组种子与 groups 同快照同版本门控)、信息栏双模式(左栏↔顶栏紧凑双排条持久化)、令牌中性化视觉刷新; 冒烟 10/10(修复包/筛选/视图/双模式全断言)+ pytest 872 全绿; 计划 memory-bank/plans/26-09-15-1042-webui-optimization-plan-v3.html; 详见 pitfalls 第八轮条目
- WEB UI 新版界面与多主题 (2026-09-15): `newui/` 独立目录并存可切换(`/newui/` 零后端路由, 旧 UI 原样保留仅顶栏 +1 链接, 共享逻辑层单一来源)；令牌化五主题(深海机房/暗夜星云/极地晨霜/麦秋/品牌轨道, data-theme + localStorage + 系统明暗跟随, theme.js 首帧前同步防 FOUC)；Edge headless CDP 冒烟 34/34(双 UI 功能等价/主题切换持久化/五主题 WCAG 对比度全达标/移动宽/无控制台错误), pytest 871 全绿；设计计划见 memory-bank/plans/26-09-15-0956-webui-redesign-plan.html；详见 pitfalls 新版 UI 条目

- WEB UI 追剧页 剧/集右键「打开目标文件夹」报"种子不存在" (2026-09-19, 已入库 `c888fba`): 用户报追剧页**剧右键与集右键**失败, 种子右键正常。**真因**: 后端 shows 视图的 `members` 是 **hash 数组**, 前端 `decoratedShows` 把它换成**成员对象**, 而 `openShowEpMenu`/`openShowMenu` 直接把 members 当 hash 用 ⇒ 拼进 URL/JSON 时字符串化成 `[object Object]` ⇒ 后端 404。**同一根因还让整集/整剧的开始/暂停/强制汇报报 Not Found、删除静默无反应**(用户尚未察觉)。**修法**: `shared/app.js` 新增 `memberHashesOf(list)`(两种形态都收)统一取 hash, 菜单与选中态(`_showHashes`/`_epUnits`/`epSelState`)一律走它; 双 UI 共用该文件 ⇒ 一次修两处。**验证**: 用 node 桩掉 `Vue.createApp`/`window`/`document` 直接加载**真 app.js** 断言产出是字符串 hash —— 新版 9/9 通过, 旧版挂 5 项(**红绿双验**); 守阵固化进 `tests/test_web.py::test_frontend_static_bundle_health` 第 7 项; 端到端冒烟(桩服务 + 无头浏览器)同样红绿验证。基线 1041 不变。

- 追剧视图 (tvshows) (2026-09-15, 已合入 develop): 剧/季/集解析 + 缺集计算 + atlas 三态视图。遗留: **prism 模板欠账**(棱镜侧追剧模板未做)。

- WEB UI 视图重建范围收口 · 种子速度刷新滞后修复 (2026-09-18): 用户报"WEBUI 种子的下载/上传速度更新慢, 但状态栏速度更新正常"。**根因(探针确定性复现)**: `qbmanager._tick` 与 `web_view.ensure_group_view` 是两条重建路径, 共享同一个 `_group_view_dirty`, 但主循环**只**重建 `_group_view` 就把标记清掉 ⇒ `_singles_view`/`_shows_view`/`_flat_view`(种子页数据源)长期拿不到重建, 版本号却每 tick 自增 ⇒ 前端把陈旧数组整表换上去; 状态栏"速度合计"取 groups 求和故一直新鲜。**同源第二坑**: 置脏语句在 `if grouping.enabled` 块内而 `consume_view_changed()` 在块外 ⇒ 分组关闭时标记被吞(版本号不再变化 ⇒ 前端退避轮询)。**实施**: ①新增 `WebviewMixin.rebuild_views()` 作**唯一重建入口**(四视图 + 版本号 + 清标记一次完成), 主循环与 Web 线程都只调它; ②置脏移出 grouping 门控(脏标记服务全部视图); ③前端 `currentPollMs()` 取消 `idlePolls` 无变化退避(只留失败退避), 并把 `store.server_state` 作为 `status.server` 并入 `/api/state` ⇒ 状态栏与行数据**同源同轮**, 每轮仍 1 条请求。**测试**: 改写 2 条把缺陷固化成预期的用例 + 新增 3 条(含端到端 `test_flat_view_refreshed_by_main_loop_tick`: 主循环 tick 后 Web 请求必须拿到新速度), 全部**红绿验证**; 基线 1018 → **1021 passed / 0 failed**。计划 [memory-bank/plans/26-09-18-1743-webui-speed-refresh-fix-plan.html](../plans/26-09-18-1743-webui-speed-refresh-fix-plan.html); 档案 [tasks/TASK017](../tasks/26-09-18-webui-view-rebuild-scope.md); **已入库 `6c98c63`**

- WEB UI 错误种子显示具体原因 (2026-09-18): 状态列不再只显示笼统「错误」—— `missingFiles` → 「文件丢失」(零 API, 状态自明), `error` → tracker 报错原文(如 `torrent not registered with this tracker`, 过长省略 + `title` 全文)。**前提核实**: qB `torrents/info` **不含**任何错误文本字段, 原因只在 `/torrents/trackers` 的 `msg` ⇒ 只能派生或另取。实现: 后端 `WebviewMixin.refresh_error_reasons` 在**主循环**按 TTL(300s)+单轮预算(5 条)预取, 写进 `TorrentRecord` 的**非快照**缓存槽 `tracker_error_msg`/`tracker_error_ts`(不进 `_SNAPSHOT_FIELDS`/`_raw`), 视图组装**只读缓存**(视图可能每 tick 重建, 不得发 API); 原因非快照字段 ⇒ 变化时由预取方**显式置 `_group_view_dirty`**; `missingFiles` 排除在拉取分支外(原因自明, 且"成片文件丢失"正是最需保住预算的场景); 预取与视图重建/搜索索引同门控(网页关掉不发请求); 断连时保持现值不清空。原因文本**取数单点** `_error_reason`, 视图透出 `error_reason`, 前端 `stateText(m)` 仅错误态采用(双 UI 共用逻辑层, 一处改两套生效; 模板各 4 处状态格 + 两套 CSS 省略规则)。基线 1001 → **1006 passed**(+5 项: tracker msg 提取/缺失文件零 API/预算与 TTL/恢复清空/断连跳过), 假 qB 服务(真实 `create_app`+uvicorn)双 UI DOM 与截图实测; 档案 [tasks/TASK015](../tasks/26-09-18-webui-error-reason.md); **已入库 `9723a76`**

- WEB UI 设置页 **新版(Console Hub)** 落地 (2026-09-21, ~~与经典页并存~~ 2026-09-25 起成为唯一设置页, 见上条): 样张 `resources/settings-page-templates/05-console-hub.html` 的原样复刻 —— 首页卡片总览(分段 LED 三态 + 等宽读数 + 按配置项名搜索直跳) → 二级页「块 → 行」两层级 + 行尾 `?` 就近说明浮窗; 站点/规则/限速/日志 四个专段。
  · ~~**不替换经典页**: 两套共用同一棵 YAML 树与全部 `cfg*` 读写(零重复编辑逻辑), 由 `localStorage autoqb.settings.hub` 切换, 入口为经典页页头「新版界面」与新版页的「经典界面」。~~(切换已随经典页移除, 共树共读写的设计保留)
  · 新增 `shared/config_hub.js`(`window.CONFIG_HUB` mixin + `window.HUB_FIELD_COMPONENT`, 后者继承 `ce-field` 全部读写仅换模板) + `shared/console_hub.css`(626 行, 两套 UI 共用)。
  · **版式硬知识**(写进 CSS 头部注释, 别改回去): 派生变量必须声明在使用 `--tone` 的那一层元素上(写进 `:root` 会被固化 → danger 档描边青/发光青); 发光用负 spread(正 spread 让边缘更亮, 实测 76% vs 18%); 切角与发光是死敌,`clip-path` 会整圈裁掉 `box-shadow`, 故切角只留大面。
  · 验证: 无浏览器环境下的替代手段 —— 用 vendored Vue 编译器 + 假 DOM(含浏览器实体解码器)把 hub 主区 / `tpl-hub-field` / 两套 UI 整页 `#app` 全部编译通过; 再用 `scripts/ui_harness.py` + playwright-core / chromium-1243 真机截图(prism/atlas 各 4 张), 0 console 错误。单测 **1098 passed** 不退化。
  · ⚠ 计划外发现(未修): 经典页 `setUnitNum` 调 `this.unitParts()` 而 `unitParts` 是 computed 拿到对象非函数 → 改「数值+单位」字段的数字会 throw; 新版已直接调 `ce.cfgSetUnit(path, num, unit)` 绕开, ~~经典页带病~~(该隐患已随经典页移除, 2026-09-25)。

- WEB UI **站点接入数据白屏修复**(2026-09-25): 用户报「webui 无任何显示」, 定位为 441ffe4(HR 安全档位呈现)踩中 `hr.js::hrSiteLine` 三处**裸调用** `fmtDuration`/`fmtSize`(format.js 的 methods, 漏 `this.`)—— 该雷被三重条件掩盖: 分支有数据门槛(未接入站点恒提前返回)、冒烟替身 `FakeTorrent.hr_judgement` 恒 None(站点命中形态从未渲染)、站点接入(BTSchool)后 `hrDurTitle` 把它提升到列表每行 title 绑定 ⇒ 生产首屏渲染 ReferenceError, Vue 3 卸掉整棵组件树 = **全页白屏**(viewMode 持久化, 刷新也白)。修复 = 三处补 `this.`; 桩服务新增 `--hr-site` 注入开关(真实 HrJudgement 轮转全分支, 含 judged=None 回落), 修复前冒烟 10 项即崩(双 UI 同死「切种子视图」), 修复后 **96 项全绿 + 三视图轮切 0 console 错误**; pytest 1607 passed + 1 skipped(与基线一致)。坑回写: pitfalls/web-ui/vue-reactivity.md(第四类静默白屏)+ pitfalls/testing/stubs-sim.md(替身恒默认分支盲区)。**未提交**
- WEB UI HR 删除安全档位呈现 (2026-09-25): 做种时长列(两套 UI 各 3 处)按**删除安全档位**着色(不能删=橙/可删=青/未核实=灰, 站点结论优先于本地 —— v3.0 档位即结论) + **来源 2 字徽标**(在线/本地/策略/未核, 结论来自优先级链哪一档) + 悬停全文(依据原文+站点侧值); 删除确认框点名「M 个仍在 HR 管束」(四入口同构); H&R 筛选两档→四档(不能删/可删/未核实) + **HR 来源副筛选**(在线核实/本地兜底/策略); 批量条「⚠ 含 N 个不能删」。后端单点 `hr/resolve.py::safety_display`(4 安全档 × 8 来源 token, 只转译既有判定不新造) + `views.py::_hr_view_fields` 透出 `hr_safety`/`hr_safety_text`/`hr_safety_src`(退役二值 `hr_satisfied_src`); 前端 token 映射表被守阵钉死与后端常量逐字一致。+4 测试, 全量 **1606 passed + 1 skipped**(TOTAL 91%), 双 UI 冒烟 94 项全过; 计划 [memory-bank/plans/26-09-25-1823-plan-webui-hr-safety-display.html](../plans/26-09-25-1823-plan-webui-hr-safety-display.html); 档案 [tasks/26-09-25-webui-hr-safety-display](../tasks/26-09-25-webui-hr-safety-display.md); **已入库 `441ffe4`**
- WEB UI 设置页**控件两处打磨**(2026-09-25, 已入库 `c4fcc0c`; 成因 / 逐项实测数字见切片 `26-09-25-1743-webui-settings-control-polish`): 均收口在 `shared/console_hub.css` —— ①规则引用下拉被 `.hb-ct .hb-select{flex:0 1 250px}` 的**后代**选择器串进 column 方向 `.hb-list`(flex-basis 变高度, 实测 460×250 竖条)⇒ 加 `.hb-list > .hb-select{flex:none}`; ②启用开关整族收 0.86(44×24/18/20 → 38×21/15/17), 静息底由 `--tone-line`(与选中态 accent 同色相, 只能靠滑块位置分辨)改中性 `--border-strong`。
- WEB UI **设置页合一: 移除经典设置页 + HR 站点状态并入「HR 在线核实」** (2026-09-25, 已入库 `7fcdc9c`; 明细见 activeContext 切片 `26-09-25-0845-webui-settings-unify`): ①经典页整块删除(`hub.mode`/`hubSetMode`/localStorage 切换一并移除, `page==='settings'` 只渲染 hub)。②「HR 站点状态」不再单列卡片: 只读状态块并入「HR 在线核实」分区页尾, 两套 UI 成对改。③顺带清掉只被旧页引用的死代码(JS 16 成员含级联 + 两主题 ce-* 旧页选择器与媒体查询残留; 既有死代码按范围守恒不动)。④机检: HR 字段锚点四入口 → 两入口(`hub.view === 'hr_check'` 唯一性)。**验证**: 全量 1597 passed + 1 skipped(与新基线一致; 曾恒红的 2 条 GBK 假红已随远端 a760da0 修复) + 双主题真浏览器冒烟(真实 create_app + 假 manager): 卡片/分区/搜索直达/运行日志/HR 状态块(含熔断·过期异常态)渲染正常, `main.ce-page` 恰 1 个、无「经典」按钮。

- WEB UI **做种时长悬停弹窗(T3 进度仪表)**(2026-09-26): 原生 `title` 一大段文字换悬停弹窗, T3 定稿零冗余落码(档案 `26-09-26-webui-hr-popup`)。`shared/hr.js` 单点: `hrPopData` 数据组装(只消费后端 hr_safety*/hr_site_* 字段零重算; 无时长要求→盾徽记; 考察中→还需 X; 本地兜底→已超出/还需 X; 终态未达标→考核期已过无站点轨; 数值条仅站点侧值; 终态「已结束」章) + hrPop* 调度(enter 120ms / leave 160ms / 移入弹窗不隐藏 / ESC·滚动·缩放即关) + fixed 定位(上翻下翻/视口夹取); `hrDurTitle` 删除。6 处绑定换 mouseenter/mouseleave; 弹窗单例 `<teleport to="body">`(prism 五主题令牌自动继承免改); 两套 CSS 成对(z-index 140); 守阵第②③段就地改写。全量 **1665 passed + 1 skipped**(TOTAL 92%); 冒烟 8 档位内容矩阵 + 交互 + 五主题跟随 0 报错; 档案 [tasks/26-09-26-webui-hr-popup](../tasks/26-09-26-webui-hr-popup.md); **随本提交入库**


- WEB UI **一键导入缺失站点**(2026-09-26): 对齐 CLI `--export-yaml --only-missing` —— 设置页「站点」pill 行「⤓ 导入缺失站点」→ `GET /api/sites/missing`(新路由模块 `routes/sites.py`, 只读)复用 `core/exporter.py` 同一套构件(域名双向包含匹配 + 默认条目: 自动标签 / `0KiB/s` 占位限速 / hr 示例值)扫描 qB 全部种子找未配置站点 → 确认框列出站点名(域名) → **填入编辑器待审**(不自动保存, 保守默认: 示例值不未经审阅生效) → 既有「保存」走校验/备份/热重载。`exporter.py` 提取 `gen_tracker_name`(既有占用/批内同名 → `_N` 后缀, taken 就地登记)供 CLI 与 webui 共用; 前端合并跳过同名键防待生效热重载竞态; 断连 503 / 扫描失败 502; atlas / prism 按钮成对。+7 测试, 全量 **1623 passed + 1 skipped**(TOTAL 92%), 金清单 61→62; 档案 [tasks/26-09-26-webui-sites-import](../tasks/26-09-26-webui-sites-import.md); **已入库 `e3fb35d`**(合流远端 9 笔后经合并提交 `8bacfae` 推送, 合并树重测 1636 collected / TOTAL 92%; 真机走查待真实 qB)


- WEB UI **做种时长悬停弹窗(T3 进度仪表)**(2026-09-26): 原生 `title` 一大段文字换悬停弹窗, T3 定稿零冗余落码(档案 `26-09-26-webui-hr-popup`)。`shared/hr.js` 单点: `hrPopData` 数据组装(只消费后端 hr_safety*/hr_site_* 字段零重算; 无时长要求→盾徽记; 考察中→还需 X; 本地兜底→已超出/还需 X; 终态未达标→考核期已过无站点轨; 数值条仅站点侧值; 终态「已结束」章) + hrPop* 调度(enter 120ms / leave 160ms / 移入弹窗不隐藏 / ESC·滚动·缩放即关) + fixed 定位(上翻下翻/视口夹取); `hrDurTitle` 删除。6 处绑定换 mouseenter/mouseleave; 弹窗单例 `<teleport to="body">`(prism 五主题令牌自动继承免改); 两套 CSS 成对(z-index 140); 守阵第②③段就地改写。全量 **1665 passed + 1 skipped**(TOTAL 92%); 冒烟 8 档位内容矩阵 + 交互 + 五主题跟随 0 报错; 档案 [tasks/26-09-26-webui-hr-popup](../tasks/26-09-26-webui-hr-popup.md); **随本提交入库**

- WEB UI **一键导入缺失站点**(2026-09-26): 对齐 CLI `--export-yaml --only-missing` —— 设置页「站点」pill 行「⤓ 导入缺失站点」→ `GET /api/sites/missing`(新路由模块 `routes/sites.py`, 只读)复用 `core/exporter.py` 同一套构件(域名双向包含匹配 + 默认条目: 自动标签 / `0KiB/s` 占位限速 / hr 示例值)扫描 qB 全部种子找未配置站点 → 确认框列出站点名(域名) → **填入编辑器待审**(不自动保存, 保守默认: 示例值不未经审阅生效) → 既有「保存」走校验/备份/热重载。`exporter.py` 提取 `gen_tracker_name`(既有占用/批内同名 → `_N` 后缀, taken 就地登记)供 CLI 与 webui 共用; 前端合并跳过同名键防待生效热重载竞态; 断连 503 / 扫描失败 502; atlas / prism 按钮成对。+7 测试, 全量 **1623 passed + 1 skipped**(TOTAL 92%), 金清单 61→62; 档案 [tasks/26-09-26-webui-sites-import](../tasks/26-09-26-webui-sites-import.md); **已入库 `e3fb35d`**(合流远端 9 笔后经合并提交 `8bacfae` 推送, 合并树重测 1636 collected / TOTAL 92%; 真机走查待真实 qB)

- WEB UI **多选右键菜单作用于整个选中集合**(2026-09-24, 已入库 `907890b`): 判据 = 范围比较(`selScope != anchorScope` 且 anchor ∈ selScope), 非"选中数>1"; 四入口(`menu.js::_ctxMulti`)写 `menu.multi`, 双 UI 批量分支复用批量浮条链路; 批量菜单只放批量有意义的动作。守阵 `test_frontend_ctx_menu_multi_select_targets_selection` 红验两处; 冒烟 +12 条 CTX-03。判据全文 [pitfalls/web-ui/overlays.md](../pitfalls/web-ui/overlays.md); 档案 [tasks/26-09-24-webui-ctx-menu-multi-select](../tasks/26-09-24-webui-ctx-menu-multi-select.md)

- WEB UI **右键次级菜单三修**(2026-09-25, 已入库 `3a8dabd`): ①图标 hover 变灰 = `.ctx-item:where(:hover) > .ico`(`>` 限直接子级 + `:where()` 压特异性, 缺一不可); ②移出不消失 = 收起只挂**父项** `mouseleave` 延迟 180ms(跨 4px 缝隙; 挂面板上会在回切时误收); ③「复制」并入「更多操作」, 一级 `has-sub` 收敛到 1 个。守阵 `test_frontend_ctx_submenu_single_entry_and_hover_close` + 冒烟 8 条。档案 [tasks/26-09-24-webui-ctx-submenu](../tasks/26-09-24-webui-ctx-submenu.md)

- WEB UI **搜索负词种子级定案: 任一候选行含负词 ⇒ 整种子排除**(2026-09-26/27): 两轮实机报障收口 —— ①「cat and -11」: E11 单文件的种子名行含 "11" 被行级作废, 却被不含 "11" 的**保存路径行**("D:/TV/The.Cat.and.the.Dragon.S01", "cat and" 齐)整颗捞回; ②「-mteam」站点行负词拦不住名字行正词命中。拍板(27): 负词优先级高于正词, 按**单个种子**统一计算 —— 任一候选行(名字/站点/分类/路径/标签/文件行, 季包文件统一计算)含负词 ⇒ 整颗排除; 多种子集合(辅种组/追剧)**每个种子单独计算**, 组/剧不连带。`search_torrents` 收敛为单轮逐种子判定(building 窗口内文件行负词未生效, 就位后收敛)。守阵 `test_search_torrents_negative_torrent_veto`(名字/路径/站点行否决 + 文件轮同受约束) + negative_term/facet_rows 改种子级断言(季包统一计算/标签行否决); 全量 **1685 passed + 1 skipped / 0 failed**(TOTAL 92%, views.py 98%, 基线 26-09-27-0045); 坑回写 [pitfalls/web-ui/search-views.md](../pitfalls/web-ui/search-views.md); **未提交**

- WEB UI **搜索匹配收敛服务端单点: 三页(辅种/种子/追剧)统一消费 searchHits**(2026-09-26 晚): 治"同一语义修三遍" —— 统一前查询语法有三份实现(服务端 `_parse_query`+行级匹配 / 种子页 filters.js 客户端行过滤 / 追剧页剧名整句 includes), 恶女10·季包"cat 12"两轮报障各修一处即再漏别处。单点 = `views.py::search_torrents` 行级匹配, 候选行从「名字/文件」扩到「+站点/分类/保存路径/每标签」(只读 store 即时, 与名字行同轮; 文件行仍走索引 building 渐进) —— 顺带治了"搜站点名/标签在分组·追剧页搜不到"的跨页不一致; 剧名不单设候选行(展示名 = `tvshows.parse_release` 从成员种子名解析的标题, 名字行天然覆盖)。前端删第二/第三实现: filters.js 四函数(`_searchNorm`/`_parseSearchQuery`/`_torrentTextMatch`/`_torrentSearchPass`)与 `filteredTorrents` 改走 `hits.has(hash)`(输入新词到响应返回间沿用上一查询命中集, 与组视图同节奏)、shows.js 剧名 includes 删除(剧行高亮 = 全部集保留代理)、app.js `searchHitsQ` 陈旧守卫随之删除。守阵 `test_frontend_search_syntax_wiring` 改写为**反漂移**(前端复活任何"函数名+括号"匹配实现即红; node 对账脚本随客户端解析器一起删除), 新增 `test_search_torrents_facet_rows`(站点/分类/标签/路径行 + by 定位 + 行级负词不整种子误杀)。全量 **1684 passed + 1 skipped / 0 failed**(TOTAL 91%, 实测 16.4s); 坑回写 [pitfalls/web-ui/search-views.md](../pitfalls/web-ui/search-views.md)(三处实现收敛单点条目); **未提交**

---

## 2026-10-03 cap 轮转外迁 (自 implemented-webui.md, 原文逐字未改)

- WEB UI **搜索查询语法强化: 词 AND + `-排除` + `"短语"`(行级语义)**(2026-09-26): 修复「恶女 10」搜不到单文件发布物(旧口径整句归一后连续子串, 两词不连续必不中)+ 新增排除能力。后端 `views.py` 新增 `_parse_query` 纯函数(websearch 宽容词法: 空格分词隐式 AND / 词首 `-` 排除 / `"…"` 短语连续子串 / 孤立 `-`·未闭合引号·纯标点宽容降级, 词法判定在原始查询上进行与归一互不干扰), `search_torrents` 改**行级匹配** —— 候选行 = 归一种子名或单个归一文件名, 行通过 ⇔ 含全部正词且无负词, 种子命中 ⇔ 任一行通过(负词按行作废, 合集包非 DV 行不误杀; 跨行 AND 不命中是与种子级的分界, 26-09-26 拍板); 仅负词查询返回空 + `negative_only` 标记(与 Google 一致, 无正判据无从起搜)。响应加 `negative_only` 键(向后兼容)。前端: 两主题 placeholder 提示语法 + 5 处空态「只有排除词」提示(app.js `searchNegativeOnly` 状态单点)。**真机回访双修(同日)**: ①种子页 `filteredTorrents` 客户端过滤同步升级同语法 —— filters.js `_parseSearchQuery`/`_searchNorm`/`_torrentTextMatch` 单点(字段行级语义: 名称/站点/分类/路径/每标签各为一候选行; 仅负词返回空), hr.js 旧整句版删除, 守阵 test_frontend_search_syntax_wiring 以 vm 沙箱与 views.py **行为级对账**(当场抓到 `_` 折叠漂移; `\W` 会折叠掉 CJK 一并钉死); ②清除钮 `@mousedown.prevent` 两主题成对(focus 宽度过渡把按钮移出光标, 焦点态 click 落空)。+7 测试累计, 全量 **1680 passed + 1 skipped**(TOTAL 91%, 基线 26-09-26-2121); 调研与设计定稿见报告 [reports/26-09-26-1918-report-webui-search-query-syntax.html](../reports/26-09-26-1918-report-webui-search-query-syntax.html); 档案 [tasks/26-09-26-webui-search-query-syntax](../tasks/26-09-26-webui-search-query-syntax.md)

- WEB UI **设置页分组合并: 日志/界面(WebUI)/通知/运行日志 并入「常规」**(2026-09-26): 设置首页 10 张卡 → 6 张(常规/自动化/HR 在线核实/限速/站点/规则)。单点改动在 schema `groups.py`(log/web/notify 三段整段搬进 basic 组, 三个独立分组删除), 两套 UI 首页卡/搜索/富说明经 schema 派生自动跟随; config_hub.js 删 `__logs` 特制卡与分支(运行日志块移入常规分区页尾, 打开分区拉一次不轮询; 存量浏览器偏好 `__logs` 由 hubRestore 映射进 basic; web.host 暴露警示 LED 挪到常规卡; HUB_HELP 交叉引用「界面 →/通知 →」改「常规 →」); atlas/prism 模板成对改(`__logs` v-else-if 分支删除, v-if 链保持合法); web 段 label「WEB UI」→「WebUI」; `validate_config` 键集合不动(test_config_schema 守卫对齐)。守阵 test_web::test_config_schema_endpoint 同步新分组表 + 钉 log/web/notify 并入 basic 尾部。全量 **1665 passed + 1 skipped**(TOTAL 92%, 合并工作树重测, 含并行入库的 versioning/button 测试); 档案 [tasks/26-09-26-webui-settings-group-merge](../tasks/26-09-26-webui-settings-group-merge.md); **未提交**

- WEB UI **种子级标签/分类即时编辑**(2026-09-26): 补上"对种子加/删标签、设置分类"的用户能力 —— `/api/torrents/bulk` 动作表扩 `add_tags`/`remove_tags`/`set_category`(载荷加 `tags`/`category` 键, **提供才透传**, 空串分类=qB"清除分类"语义; `_BULK_ACTIONS` lambda 统一 4 参带 `extra`, 既有 4 动作忽略它; `bulk_torrents` 本就在 RESYNC/延迟回执两名单, 新动作零白名单改动自动继承补刷新与聚合回执), QbApi 侧三个方法早已就绪且同步 store 快照。前端「标签/分类」**即时编辑对话框**(shared/dialogs.js): 目标集合打开时锁定(批量 = `_bulkTargets()` 整个选中集合 / 单种子 = menu.hash), 全部标签以 `.opt-pill` 切换胶囊展示(亮 = 选中种子**共同拥有**, 点击即投递一条 bulk 命令), 分类 combobox 现有分类选择 + 自由输入(新分类/新标签**先建后设**, create 失败不阻断, 主循环 FIFO 保证顺序); 共同标签取交集但**不过滤站点同名标签**(那条是组级展示口径, 编辑场景要能移除它们)。三处入口双 UI 成对: 批量浮条按钮 / 批量右键菜单(CTX-03 链路 ctxMeta) / 单种子右键菜单(一级, 与限速/移动/重命名同级); `.opt-pill` 组件 atlas 首次引入(照 prism 同源搬入)。+3 测试, 全量 **1638 passed + 1 skipped**(TOTAL 92%); 双 UI 浏览器冒烟通过(harness 桩); 档案 [tasks/26-09-26-webui-torrent-meta-edit](../tasks/26-09-26-webui-torrent-meta-edit.md); **未提交**

- WEB UI **前端大文件拆分 + 单一语义模板收敛 + 内核续拆**(2026-09-27, plans/26-09-26-2233 五波全落地): ①模板: 两套 index.html(2555/2613 行)→ shell(166/177 行)+`shared/tpl/*.html` 14 分片**单一语义源** + `shared/boot.js` 按清单 fetch 注入(失败显式占位+停止); 双模板副本消灭, 模板级 UI 差异唯一入口 = `v-if="ui === 'atlas'|'prism'"` 条件块 + `ui-diff:` 注释(守阵收集为活差异清单, 现存 1 条: 棱镜主题切换器) ②样式: atlas style.css 1720 → 令牌+基线留根 200 + `css/{components,views,dialogs}.css`(全 ≤700, 连续字节切片级联序不变) ③内核: app.js 1281→411(常量单点+接线), `state.js`(data/computed/watch)/`lifecycle.js`(生命周期)经 `...window.X` 展开进**根组件选项**(不许 app.mixin —— 波及 hub-field 实例), `auth.js`/`polling.js`/`view.js` 走全局 mixin 方法域 ④守阵: 13 处直读改聚合读法 + 新增分片接线/差异口注册表/双 shell 清单一致性/整包成员查找 + JS 接线形态④。等价证明 = 切割聚合字节自验 + 真 API stub 冒烟改造前后渲染 DOM 双 UI 逐字节一致; 全量 **1688 passed + 1 skipped**(TOTAL 91%, 基线 [testing/baselines/26-09-27-1305-webui-kernel-split](../testing/baselines/26-09-27-1305-webui-kernel-split.md)); 计划 [plans/26-09-26-2233](../plans/26-09-26-2233-plan-webui-frontend-file-split.html); 档案 [tasks/26-09-26-webui-frontend-file-split](../tasks/26-09-26-webui-frontend-file-split.md); **已入库 `6fd1331`(三层拆分)/`aeca1fb`(收敛), 内核拆分随本批提交入库**

- WEB UI **自绘悬浮提示 .aq-tip**(2026-09-28): 原生 title 全局替换为自绘单例 —— `ui_feedback.js` 纯 DOM 委托(摘 title/350ms 延迟弹/收起还原, hasAttribute 探测保 Vue :title 绑定) + `console_hub.css` 发光按钮配方(三皮肤令牌自适应)。机制与配方**事实单点 = conventions/webui.md「WEB UI 悬浮提示 .aq-tip」节**。test.full 1820/3(基线 26-09-28-0744); **已入库 `c64b836f`**(切片 26-09-28-0730 蒸馏至此删除)

- WEB UI **设置页分类回归修复: 「常规/日志」成块 + 运行日志默认折叠**(2026-09-28): 治 26-09-26 分组合并(1905d6d)的回归 —— log/web/notify 三段因 `open=True` 被 cfgFlatten 平铺成无标题同级字段, 全部落进「常规/常规」。修复: 三段去 `open=True` 恢复成块展示(hubBlocks 自动渲染带标题且**永远展开**的块, 分类显性与 2026-09-15 平铺诉求同时满足), label 恢复合并前分组名 日志/WebUI/通知 + 补回旧分组一行 help; 运行日志块默认折叠、首次展开才拉 /api/log(`hubLogsToggle`/`hubLogsLoad`, 折叠态动等级/行数/刷新自动展开再拉), hubGo 去预取; hubHits/hubFieldCount 改递归进块(块内字段不再是展开顶层项); `open` 字段保留为通用能力(现仅 hr_check optional 段在用)。守阵 `test_config_schema_endpoint` 钉尾三段 kind=object 且不声明 open(防 open 平铺回归)。**三套 UI(atlas/prism/console)零成对改**: 设置页同吃 shared/tpl + config_hub.js, console 纯 CSS 换肤, manifest 一致性守阵钉住。全量 **1815 passed + 3 skipped**(TOTAL 91.39%, 基线 [testing/baselines/26-09-28-0212-webui-settings-categorize-logs](../testing/baselines/26-09-28-0212-webui-settings-categorize-logs.md)); 档案 [tasks/26-09-28-webui-settings-categorize-logs](../tasks/26-09-28-webui-settings-categorize-logs.md); **随本提交入库**

- WEB UI **搜索框语法帮助入口: 框内幽灵「?」+ 锚定浮卡(方案A)**(2026-09-28): 3 版交互式提案(计划 26-09-28-0201)用户拍板 A + 占位符简化为「搜索种子或文件名...」。实施: `topbar.html` 「?」恒显于清空钮左侧 + 浮卡(词 AND/`-词`/`"短语"`/`-"短语"` 四行 + 容错提示, 示例行点击回填即搜 `doSearch` + 焦点还输入框); 挂件样式入三 UI 共用层 `shared/console_hub.css`(mono 用 `var(--font-mono, 内联栈)` longhand —— 星图无该令牌, shorthand 遇未定义令牌整条失效), 皮肤差异只留 atlas pill 钮圆与 input 右内边距 52px; `searchHelpOpen` 状态 + `toggleSearchHelp`/`searchHelpFill`(view.js), 收起 = 点空白/Esc(lifecycle 既有链)+ goView/openSettings 导航收起; 守阵 `test_frontend_search_help_wiring`。实机 dev.harness+Playwright 三套 UI 全交互通过(示例 `"web dl"` 真实后端命中 35/60); 全量 **1815 passed + 3 skipped**(TOTAL 91%, 基线 26-09-28-0250); 档案 [tasks/26-09-26-webui-search-query-syntax](../tasks/26-09-26-webui-search-query-syntax.md); **未提交**

- WEB UI **做种时长列/弹窗的「要求」显示修复**(2026-09-29): 用户实报未核/在线行不显示要求时间、只剩孤立的「未核」芯片。定位为两处**渲染门**(纯前端, 判定与字段未动): ①三份模板 `.req` 只在 `hr_triggered` 为真时渲染 ⇒ 未触发行连配置事实(要求时长)一起被藏; ②`hr.js` 弹窗把 `unverified` 与真放行/免罪同类收起成「无时长要求」徽记(而它 `hr_req_time=115200s` 确有要求)。修复: 要求门只认「已做种非空 + `hr_req_time`」; 收起条件只留 `site_released`/`site_exempt`(义务已了), 未核实改画本地轨。**现象属「上游修好后才被点亮」** —— 前几轮修好 HR 视图发布后 `hr_safety` 从空变有值, 此前不可达的芯片/弹窗分支第一次上线(教训入 [pitfalls/web-ui/contract-api.md](../pitfalls/web-ui/contract-api.md))。守阵 `test_frontend_hr_safety_wiring` 增两条断言(回退即红)。全量 **1747 passed + 4 skipped**(TOTAL 91%, 基线 [testing/baselines/26-09-29-1920-webui-hr-duration-req](../testing/baselines/26-09-29-1920-webui-hr-duration-req.md)); 档案 [tasks/26-09-29-webui-hr-duration-req](../tasks/26-09-29-webui-hr-duration-req.md); **未提交**

- WEB UI **标签列全量展开, 移除「+1/+2」折叠**(2026-09-30): 用户要求标签不再折叠。4 处模板(种子明细 / 组级+组内成员 / 追剧集行)去 `tagSlice(...,3)`/`slice(0,3)` 截断与 `+N` 徽标, 改 `v-for` 全量渲染; 三皮肤 `.g-tags, .m-tags` 加 `flex-wrap: wrap`(行高逐行实测的虚拟滚动承接变高行), 清 `.tag-more` 死样式; `decorate.js` 删 `tagSlice()`。单个超长标签仍 ellipsis(完整值在悬浮)。纯前端改动, 无 Python 源改动; 档案 [tasks/26-09-30-webui-tags-unfold](../tasks/26-09-30-webui-tags-unfold.md); **随本提交入库**

- WEB UI **键盘快捷键全量落地(可自定义)**(2026-09-30, plans/26-09-28-0354 W1-W7 两波): ①引擎 `shared/shortcuts.js` 注册表单一事实源 55 条(e.code+固定修饰序归一化 / IME isComposing+229 双保险 / 输入元素+模态层屏蔽 / repeat+纯修饰键+defaultPrevented 前置 / 浏览器保留键黑名单 Ctrl+W/T/N/Q 族; 适配器 `window.AQB_KEYS` 单一存储出口) ②光标模型 kbCursor 按身份不按下标(滚动进视口走 getBoundingClientRect 差值+`_rowPre` 前缀和, **禁 scrollIntoView**; 26-09-30 方案 B 键鼠衔接追加: selection.js 五个点击入口按所在行回写 kbCursor —— 落光标≠选中, 无光标回落改**视口就近行** `_kbViewportRow`, 明细成员行补 kb-cursor 视觉, 守阵 test_click_lands_cursor_and_viewport_fallback) ③`commands._actCore` 统一动作出口(act/actTorrent/bulkAct/actEpisode 四入口收敛) ④默认键位 A-I 组(§08 v4 危险档一律二键组合: 删除 Shift+D/重新校验 Shift+Y/强制汇报 Shift+A + 确认框默认「确定」Enter 确认; Delete 键额外删除入口直连 `_deleteFlow` 注册表外; E 组 Shift 族/F 组队列开关/G 组局部作用域 Alt+1-4+设置页 Ctrl+S inputSafe/H 组帮助浮层 Shift+Slash) ⑤作用域五值(global/list/drawer/settings/modal)全量生效, 模态白名单分流 ⑥后端持久化: `routes/keys.py` GET/PUT `/api/keys`(存储 `auto-qb-data/webui-keys.json` 与 web.token 同寻址, 读时兜底链 主文件→.bak→默认表, PUT 结构校验 422, 金清单 +2; 存储定案=后端独立文件, 决策点⑥) ⑦自定义面板: 设置页「快捷键」分区(按下即录录制器捕获段监听/纯修饰键拒收/黑名单拒绑/冲突三选一 交换-覆盖对方置空-取消/单条全部重置/空串=显式禁用/保存失败本地回滚/离开未保存先确认)+ 帮助浮层只读速查。守阵 test_web_shortcuts.py 16 条 + test_web.py keys 后端 5 条; 探针 28 项全过。全量 **1813 passed + 3 skipped**(TOTAL 91%, 基线 [26-09-30-0555 W1-W4](../testing/baselines/26-09-30-0555-webui-keyboard-w1w4.md) / [26-09-30-0702 W5-W7](../testing/baselines/26-09-30-0702-webui-keyboard-w5w7.md)); 档案 [tasks/26-09-28-webui-keyboard-shortcuts](../tasks/26-09-28-webui-keyboard-shortcuts.md); W1-W4 **已入库 `38ffec5`**, W5-W7 **未提交**

- WEB UI **HR 在线核实详情两张表**(2026-10-01/02, 清偿 issue
  [26-10-01-2137-feat-webui-hr-detail-table](../issues/26-10-01-2137-feat-webui-hr-detail-table.html),
  计划 [plans/26-10-01-2216](../plans/26-10-01-2216-plan-webui-hr-detail-table.html) 拍板六项全按推荐):
  ①后端导出单点 `hr/status.py` `EntryDetail`/`entry_details()`(P0+P1 全集, 人话字段后端算好,
  档位·下载量排序含失踪行)+ 只读端点 `GET /api/hr/sites/{site}/entries`(未启用 400 / 未接入 404 /
  线程未启动 409; f5ce07bd); ②站点卡片**表① 全量详情表**(打开分区/手动刷新各拉一次不轮询,
  档位筛选 chips 本地过滤, 「数据截至」时间戳, 「上次核实(放行判定)」独立口径, 单元格不挂原生 title;
  d3d4d987); ③**表② 排障视图**(站点级 kv 行 `hrsKvRows` 拼行单点 + 各档波次明细, 原生 `<details>`
  默认收起, 数据全来自 /api/hr/status 零新请求, 展开态不持久化; b2b1e96d); `.hr-detail-table` 等
  三套 UI CSS 成对。阶段4 契约守阵 `test_frontend_hr_contract_keys_match_backend`(前端消费键 ⊆
  后端 to_dict 键集)钉两表字段面; 基线数字见 `commands run kb.baseline`;
  档案 [tasks/26-10-01-webui-hr-detail-table](../tasks/26-10-01-webui-hr-detail-table.md); **随本提交入库**

- WEB UI **设置页只读字段(程序托管/R 级)**(2026-10-01, 清偿 issue
  [26-09-28-2135-feat-webui-readonly-fields](../issues/26-09-28-2135-feat-webui-readonly-fields.html)):
  schema_version/data_dir/state_file/fs 段此前渲染为可编辑但保存必然被盖章/回退, 反馈还谎报「需重启才生效」。
  修法五条: ①`Field` 加 `readonly` 标志 + 四点位打标(fs 段与叶子 path_map 双标, 前端叶子只认自身标)
  + `readonly_config_paths()`; ②CE_FIELD_BASE 三 computed(readonly/readonlyComplex/readonlySummary),
  hub-field 只读摘要分支(fs.path_map 渲染「from: … · to: …」映射对, 替换 `[object Object]` text 控件)
  + 全控件 `:disabled` + 「程序维护」徽标 + settings-detail 块级 section 开关收口; ③cfgSave 反馈口径改
  「程序托管字段, 仅能在配置文件中修改, 本次未写入」; ④writer `_fallback_readonly_fields` 键面防线
  (schema_version 豁免 —— 盖章承担其只读, 回退会吞「高于本程序支持」精确错); ⑤守阵 +5(writer 3 /
  schema 1 / web 静态 1)。真浏览器定向验证徽标/禁用/摘要全符合设计。test.full **1929 passed + 3 skipped / 91%**
  (基线 [testing/baselines/26-10-01-2250](../testing/baselines/26-10-01-2250-webui-readonly-fields.md));
  档案 [tasks/26-10-01-webui-readonly-fields](../tasks/26-10-01-webui-readonly-fields.md); **随本提交入库**

- WEB UI **web.token 生成改走 atomic_write**(2026-10-01, 清偿 issue
  [26-09-21-1347-bug-web-token-non-atomic-write](../issues/26-09-21-1347-bug-web-token-non-atomic-write.html)):
  ensure_web_token 原用 O_TRUNC 直写, 生成瞬间非优雅终止会留下非空半截 token 被持久化 ⇒ 已存浏览器密钥 401。
  修法 = 改走 utils.atomic_write 单点(mkstemp 默认 0600, 落盘字节逐字节等价), 读取侧零改动;
  守阵暂不并入 O_TRUNC 静态扫描(hr/channel.py:104 同族直写未清, 待一并收)。守阵 +3(test_web:
  生成可读回 / 已有 token 不漂移 / 写一半中断自愈)。**已入库 `5965cc07`**(W2 清偿 1/3)

- WEB UI **HR 排除辅种补悬停弹窗**(2026-10-02): 2026-09-29 做种时长列非文字化清理撤原生 title
  「已排除」提示后弹窗侧未接盘 —— 命中 HR 排除表(exclude_categories/exclude_tags)的辅种 hover
  完全真空(排除态 hr_safety 组装层短路空串, hrPopData 对空档位一律不弹)。后端 record.py 排除
  匹配收敛单点 `_hr_exclusion_hits`((标签命中, 分类命中)), 新增 `hr_excluded_by()` 来源 token
  (tag/category/tag+category, 与 hr_excluded 同单点恒一致), `hr_view_fields` 双分支透出
  `hr_excluded_by`; 前端 hrPopData 排除行分支 —— 「已排除出 HR 管理」+ 依据行「命中 HR 排除表的
  分类规则/标签规则/标签与分类规则」(`HR_EXCLUDED_BY_TEXT` 映射, 前端不重算匹配纪律不变),
  无轨道/站点值(排除行本就无, 画要求轨反误导为仍受管束); 三主题 CSS 成对新增
  `.hp-dot/.hp-verdict.excluded` 中性灰档(--fg-muted, 不占四档安全色); 种子页/辅种组成员行/
  追剧集行共用弹窗单点一处修三处生效。守阵: testhr_view_fields_excluded 扩展三命中形态 + 空配置
  键集; record 排除三测补 token 断言; 接线守阵 CSS 成对清单 +2; FakeTorrent 鸭子兼容补
  hr_excluded_by(裸替身直喂 _build_group_view 两场景全量暴露)。test.full **2292 passed +
  3 skipped / 99%**(27.5s @ f0c0f0ed, 基线 26-10-02-1956); 档案
  [tasks/26-10-02-webui-hr-excluded-hover-pop](../tasks/26-10-02-webui-hr-excluded-hover-pop.md)

- WEB UI **ESC 兜底清全部面筛**(2026-10-02, 清偿 question issue
  [26-10-01-2108](../issues/26-10-01-2108-question-webui-esc-clear-filter.html), 计划
  [plans/26-10-02-1632](../plans/26-10-02-1632-plan-webui-esc-clear-filters.html) 拍板方案 A):
  ESC 不进引擎键表(方案 B 双触发 + fixed 语义崩坏, 已否决), 接 lifecycle.js 退栈链**终端兜底**
  —— 16 层浮层 pop 与既有 4 兜底全部走完仍无层可退, 且门五件套(`authOk` / `page === "groups"` /
  无 hrPop 卡 / 非输入态 inInput / `facetsActive`)全过时清全部面筛 + toast 点名「已清除全部筛选
  (搜索词保留)」; filters.js 新增 computed `facetsActive`(与 clearFilters 字段清单同源,
  **不含 searchQuery** —— filtersActive 含搜索词不能当门); 键表零改动, `clear-filters` 保持空位
  供自定义, `clear-esc` label 补「清筛选」, shortcuts.js 三处文案。守阵 test_web_shortcuts.py
  新增 `test_esc_chain_clear_filters_fallback`(链序 / 门条件五件套 / Escape 唯一默认绑定 /
  facetsActive 纯度); 桩服务走查 8/8 项 / 34 断言通过(IME 组合态 CDP 真实组词态验证);
  档案 [tasks/26-10-02-webui-esc-clear-filters](../tasks/26-10-02-webui-esc-clear-filters.md);
  **已入库 `0d286cc5`**

- WEB UI **Shift 连选起点与键鼠联动统一**(2026-10-02, 计划
  [plans/26-10-02-0608](../plans/26-10-02-0608-plan-webui-shift-anchor.html) 方案 B, 用户指令
  「按推荐实施计划」直接拍板 + 4 决策点按建议案): 修「鼠标点过第 5 行, 按 Shift+↓ 却从**列表第一行**
  起选」—— 根因是方案 B 只统一了**光标**(`kbCursor`), 区间**起点**(`selAnchor*`)仍是另一套状态机
  (仅 Ctrl/⌘ 点击与展开写入), 为空时四处消费者一律兜底 `list[0]`。修法四条: ①起点解析/写入单点
  `_selAnchor(kind, list)` / `_selSetAnchor(kind, id)`(`selection.js`), 兜底链 **显式锚点 → 当前光标
  → [group: 展开的组] → 列表首行**, `shiftGroupSel`/`shiftMemberSel`/`shiftTorrentSel`/`_extendUnit`
  四处改调用, 消掉「四处各写一遍 `list[0]`」的口径漂移源; ②五个点击入口普通/Ctrl 路径补落起点,
  **`!event.shiftKey` 守卫排除 Shift**(法则 2: 起点在扩展期间不动, 否则 Shift+点击只选目标单行);
  ③`shortcuts.js` 新增 `_selSeedAnchorFromCursor`, `_kbExtend` 在 `_kbMove` **之前**以当前光标落
  「手势原点」(已有有效起点则不动); ④追剧页起点缺失改走 `_selAnchor("unit", units)` 形成区间, 不再
  退化为单单元切换。**行为口径未变**: 普通点击仍不选中(只写 `selAnchor*`) / 滚动仍只在键盘路径 /
  禁 `scrollIntoView` / FX-11 互斥清理不变 / 无 Python src·配置键·后端改动。守阵
  `test_web_shortcuts.py` 18 → 19(`test_shift_anchor_unified`); test.full **2290 passed + 3 skipped /
  99%**(基线 [testing/baselines/26-10-02-0635](../testing/baselines/26-10-02-0635-webui-shift-anchor.md));
  档案 [tasks/26-09-28-webui-keyboard-shortcuts](../tasks/26-09-28-webui-keyboard-shortcuts.md); **已入库 `fa79d526`**


<!-- 2026-10-05 cap 轮转追加 (implemented-webui.md 收缩到 ≤50%) -->

- **WEB UI HR 拉取历史详情表**(2026-10-04, 计划
  [plans/26-10-04-0312](../plans/26-10-04-0312-plan-webui-hr-fetch-history.html) S1-S6 全落地, 提交链
  `49da6d06`(拍板落定: ⑤=2000条/站点+6个月, 余推荐A)→`0227f25c`(S1 `HrHistoryEvent` +
  `HrSiteData.history` 环形留痕, 不抬 hr_site 版本链)→`4c88e8e2`(S2 波次/拦截(含 force-defer)/对账三类
  事件写入点, poll 跳过零写盘)→`2923ffa4`(S3 `history_rows()` 只读口径 + `GET /api/hr/history`)→
  `85a22f8a`(S4 全屏弹层表③: 懒加载/站点chips/仅看异常/行展开档位明细)→`ec697a08`(S5 ui_harness 桩
  五形态 + 表③断言与三皮肤目检), 分支 webui-hr-fetch-history 待并回): 「什么时间拉取了什么站点/解析
  结果」可考 —— 参照扩展选项页取数明细表且更细; 已知限制: 新旧版本混跑窗口期旧程序写盘丢 history 键
  (业务字段无损, 不做双写兼容)。test.full 2442 passed + 3 skipped / 30.93s / 99%(基线
  [26-10-04-0632](../testing/baselines/26-10-04-0632-webui-hr-fetch-history.md)); 三皮肤冒烟 207/207 +
  15 张截图目检; 档案 [tasks/26-10-04-webui-hr-fetch-history](../tasks/26-10-04-webui-hr-fetch-history.md)(Done)。

- **WEB UI 添加种子三下拉 label 闪烁「第四轮」(JS 收层守卫单点加固)**(2026-10-04): 用户报 594e247f
  三修后真机仍稳定复现。本轮探针自校验(摘掉 `@mousedown.prevent` → delay=150 完整闪烁链复现)证明
  三修代码在 Chromium 人手时序下干净(三皮肤 × 四场景 24/24 零翻转), 用户症状 = 浏览器跑的还是旧
  模板 —— SPA 的模板/JS 以页面加载时刻为准, 长开页签不刷新服务端更新到不了。代码侧加固 = 收层不再
  依赖「模板与 JS 同代到达」: `addPopBlurClose`/`metaCatBlurClose` 的 40ms 定时器收层前问
  `_popBlurShouldHold`(mounted 挂 mousedown capture 记录器, unmounted 对称移除) —— 焦点已回本族
  输入框或本族 label 转发 click 仍在途(350ms 新鲜度)→ 跳过收层; 模板修饰符在 = 纯 no-op, 缺位 =
  独立根除闪烁, 任何代际混合都安全。守卫 vs 旧模板 4/4(点空白/Tab/过期 blur 三条正常收层路径零误伤);
  守阵 combo 第 7 组 + 拖拽守阵 mounted 断言改子集语义; 用户侧验收 = 服务重启后整页强刷再走查。
  基线 [testing/baselines/26-10-04-0240](../testing/baselines/26-10-04-0240-webui-addcombo-label-round4.md)
  (2419 passed + 3 skipped / 31.86s / 99%, stash→sync 合并 2b10581a 后重测)。

- **WEB UI qB 口径流量图三图**(2026-10-04 实施完成, 方案C): 全局弹层 / 单种抽屉「流量」页签 / 分组弹层三挂点 (uPlot vendor 单文件, 三主题登记, 低频轮询); 后端采样管线 (core/modules/traffic_sample_mod.py, 全局恒采 + 单种活跃过滤) + dat 存储层 (core/traffic_store.py, `<data_dir>/qb-traffic/` global.dat + torrents/&lt;infohash&gt;.dat, 小时封口 catch-up 补封 + 半行容错/损坏隔离 + index/reconcile + 删种冻结/重加解冻/按龄淘汰) + 三 GET API (webui/server/traffic_qb.py, 栅格离散 null 断线 + 组读侧聚合, 金清单 75); 配置键 `qb_traffic`(enabled 缺省 false = 零开销)。P6 十条桩验证 10/10 过 (桩验证替代真机); 真机遗留: fastresume 单种 all-time 持久性 / alltime 回退幅度待观察。实施权威 = [计划 26-10-03-0946](../plans/26-10-03-0946-plan-qb-traffic-charts-c.html) + [档案 26-10-03-webui-qb-traffic-charts](../tasks/26-10-03-webui-qb-traffic-charts.md) (P6 验证记录节); test.full 2418 passed / 99%。**2026-10-04 跟进: 三挂点并入底部详情抽屉**(删两个模态弹层, 与种子详情「流量」页签共用同一段正文块与同一拖拽高度, `.drawer-dock` 落点上提 app 级 `tpl/dock.html` = 入口任意页可达, 图高改量宿主 clientHeight 并宽高双观察 -> 拖拽调高图实时跟随; 见 [activeContext 26-10-04-0405](../activeContext/26-10-04-0405-webui-qb-traffic-drawer-merge.md))。**2026-10-06 面板加页面守卫**: 面板只在主内容页 (`page === "groups"`) 渲染 (`drawerVisible` 单点, 状态位不随切页翻 —— 回主内容页连数据与窗口选择一起回来), 修「qB 全局流量图错误地出现在设置页」; 连带三处 —— 三挂点 `active` 同款守卫(隐藏期不发请求)、`watch(drawerVisible)` 退场销毁图 / 进场补拉重画(v-if 拆装换宿主, uPlot 不自愈)、Esc 两处名单改判 `drawerVisible`(看不见的面板不吃 Esc); 坑见 [pitfalls/web-ui/dock-panel.md](../pitfalls/web-ui/dock-panel.md)。。**2026-10-05 补完 (UX)**: 窗口档位(13 档)选择落 localStorage(全局单独 `autoqb.ui.qbWinGlobal` / 组与种子共用 `autoqb.ui.qbWinShared`) + 档位清单单点 `QB_WINDOW_NAMES`(展示/切换/校验三处同源, 与后端逐字一致) + 三快捷键(打开全局图 `Ctrl+Backslash` / 流量页签 `Alt+5` / 窗口前后切换 `[` `]`, 后两条走新增引擎 `when` 条件绑定)。见 [activeContext 26-10-05-1759](../activeContext/26-10-05-1759-webui-qb-traffic-window-persist-shortcuts.md)。

- **WEB UI 添加种子三浮层互斥补双向(closeAddPopsExcept 单点)**(2026-10-04): issue 26-10-04-0130
  认领, 按建议方向二实施。原互斥矩阵单向(openAddPathPop 收 cat/tag, 反向 openAddCatMenu/
  openAddTagMenu 不收 addPathPop), 路径面板与下拉可同悬且面板盖住相邻字段 label 的点击(Playwright
  实测 "subtree intercepts pointer events"); 失焦合帧兜不住 —— 新字段 @focus 先 _addPopBlurCancel
  撤掉定时器。修法 = 抽 `closeAddPopsExcept(kind)` 三浮层互斥单点(收层带 Hi 复位), 三开层各调一次,
  后续加第四个浮层单点补分支即可; 守阵 `test_frontend_add_combo_blur_close_and_fit` 补第 6 组
  「互斥双向」静态断言。Playwright 走查 6/6(focus 迁移焦点避开面板几何拦截, 修复前反向缺口终态
  双开、修复后单浮层); 基线 [testing/baselines/26-10-04-0150](../testing/baselines/26-10-04-0150-webui-add-pop-mutex.md)
  (2419 passed + 3 skipped / 99%, 合并 4805f5f5 后重测)。

- **WEB UI 添加种子三下拉 label 闪烁「第三轮」(上轮修法未修住)**(2026-10-04): 用户报 a7ebbe14 后
  「点字段 label 稳定复现下拉闪烁」依旧。真浏览器事件埋点定位: 第二轮两个判断是错的 —— label 的
  **mousedown** 默认动作就会 blur 已聚焦的输入框(focusout related=null 实测在),"回焦 ~2ms"只是
  零延迟合成点击的假象, 真人按下到抬起隔 **80~150ms** ⇒ addPopBlurClose 的 40ms 合帧定时器在
  **按住期间**先收层, 松手 label click 默认动作回焦重开 = 每次必闪; 第二轮走查 39/39 全绿是因为
  Playwright 默认点击 down/up 只隔 ~2ms, 撞不上 40ms 窗。修法 = 四个字段 label(添加窗口三字段 +
  meta 分类)一律 `@mousedown.prevent`(mousedown 不产生 blur ⇒ 收层定时器不武装, 竞态从根上消失;
  @click.stop 保留挡 window 收层, 缺一即回归; 关闭态点 label 仍正常聚焦+开菜单, 实测)。守阵第 1 组
  扩为双断言; 坑档 [combobox-focusout-close(复发+1, 第三轮)](../pitfalls/web-ui/combobox-focusout-close.md)
  —— 教训: 合成零延迟点击验证不了按住时序竞态, 走查必须 `delay>=120ms`。基线
  [testing/baselines/26-10-04-0054](../testing/baselines/26-10-04-0054-webui-addcombo-label-round3.md)
  (2418 passed + 3 skipped / 99%, 合并 30143bda 后重测); 三皮肤 24/24(delay=150ms 人手时序)。

- **WEB UI 抽屉出入过渡动画** (2026-10-04): 用户报「抽屉出现与消失时很生硬」 —— 停靠面板占文档流,
  open 翻转时列表底部一帧被面板撑开/收回, 面板本体滑淡治不了布局跳变; JS 过渡钩子驱动 `.drawer-dock`
  槽位高度插值(drawer.js 出入过渡块 + drawer.html `<transition>` 接线), 收场同步收面板自身高 +
  dock 跟随, 动画期几何登记 `_drawerAnimTop` 供 `_kbViewBottom` 单点消费(行让位不读中间插值);
  seq 代际闸管快速往返, reduced-motion 与 D3 全屏态双豁免。守阵 `test_drawer_transition_dock_anim`;
  真浏览器探针三皮肤各 9/9; 基线 [testing/baselines/26-10-04-0015](../testing/baselines/26-10-04-0015-webui-drawer-transition-anim-done.md)
  (**2418 passed + 3 skipped / 99%**); 档案 [tasks/26-10-03-webui-drawer-redesign](../tasks/26-10-03-webui-drawer-redesign.md)

- **WEB UI 添加种子三下拉「第二轮遗留四项」**(2026-10-03): ①点字段 label **稳定**复现下拉闪烁 ——
  输入框已聚焦时点 label 不 blur(@focusout 不参与), 真链条是「label click 冒泡到 window 收层名单 →
  label 默认动作转发 click 给 for= 输入框 → 重开」⇒ 四个 combo 的字段 label 一律 `@click.stop`;
  ②三个 combobox 内嵌清空 x(`@mousedown.prevent` 保焦点 + `@click.stop` 挡 window 收层, 双修饰符
  缺一即"清完下拉没了"), 三皮肤 CSS 成对; ③拖选文字终点落在遮罩上抬手把窗口关了 —— click 的 target
  是 mousedown/mouseup 的**公共祖先**(= 遮罩), `@click.self` 误判 ⇒ 全仓 11 处遮罩统一改
  「mousedown 记臂位 + mouseup.self 才关」(dialogs.js 单点, 零残留); ④选中分类后逐字删除撑变形 ——
  开层限高按当时候选量算, 删字涨回全量时旧限高不更新 ⇒ 三个输入值各挂 watcher 重限(meta 侧同族);
  另排查出第 4 个 combo(meta 分类下拉)既无 @focusout 也不在 window click 名单 = 点别处悬着不收,
  一并补齐。守阵 `test_frontend_add_combo_label_clear_mask_and_refit`; 坑档
  [combobox-focusout-close(补第二轮)](../pitfalls/web-ui/combobox-focusout-close.md) +
  [modal-mask-click-self-drag(新)](../pitfalls/web-ui/modal-mask-click-self-drag.md);
  基线 [testing/baselines/26-10-03-2130](../testing/baselines/26-10-03-2130-webui-addcombo-round2.md)
  (2415 passed + 3 skipped / 99%); 三皮肤真机走查 39/39。

- **WEB UI 添加种子三下拉「失焦即收 + 限高不出窗」**(2026-10-03): 收层主判据 window click → `@focusout`
  + 40ms 合帧守卫(治点字段 label 转发回焦导致的「下拉闪烁再次出现/未失焦」, 概率性), 开层方法先撤销
  挂起收层; 开层 watcher `_fitAddPop` 量「输入行→滚动容器可见底沿」净空限高 + 候选异步重限(治菜单
  伸出窗口外把 `.add-dialog-body` 撑变形, 滚动条进窗)。守阵 `test_frontend_add_combo_blur_close_and_fit`;
  坑档 [pitfalls/web-ui/combobox-focusout-close.md](../pitfalls/web-ui/combobox-focusout-close.md);
  基线 [testing/baselines/26-10-03-1550](../testing/baselines/26-10-03-1550-webui-addcombo-blur-fit-done.md)
  (2391 passed + 3 skipped / 99%); 三皮肤真机走查 12/12 × 3。**未提交(等用户指令)**。

- **WEB UI 种子详情抽屉重设计: 浮层 → 底部停靠属性面板 (方案A)**(2026-10-03, 计划
  [plans/26-10-03-0917](../plans/26-10-03-0917-plan-webui-drawer-redesign.html) 五波, 提交链 `f994ce20`/`9c594e1e`/`b81a1ee4`/`a0b5d73f`,
  清偿 issue [26-10-01-2119-feat-webui-drawer-redesign](../issues/26-10-01-2119-feat-webui-drawer-redesign.html) +
  [26-10-01-2108-feat-webui-shortcuts-drawer-nav](../issues/26-10-01-2108-feat-webui-shortcuts-drawer-nav.html) +
  [26-10-01-2108-feat-webui-shortcuts-drawer-open](../issues/26-10-01-2108-feat-webui-shortcuts-drawer-open.html)):
  用户硬约束「抽屉打开时模糊列表、键盘切换看不清当前行」结构性消除 —— W1 浮层改列表下方全宽停靠面板
  (`.drawer-dock` sticky 吸底, boot.js "into" 支持选择器落点, 三皮肤 drawer 族 CSS 重写 + 下滑淡入),
  遮罩与 `backdrop-filter` 摘除 = **PERF-01 全站归零收尾**; W2 键盘跟随流: scope 存活(`_kbOverlayBusy` 摘 drawer.open,
  面板开着列表键位不灭)+ drawer-tab-* 四条 list scope 双态(Alt+1~4 关态开面板定位页签/开态切页)+
  详情防抖跟随单点 `_kbFollowDrawer`(200ms + seq 代际 + hash 短路, 挂 `_kbApplyCursor` 尾部)+
  D2 Enter 已开仅跟随不关; W3 高度治理: 拖拽调高夹取 [240px, 70vh] + 收起/展开钮 + 高度持久化 `autoqb.ui.drawerHeight`,
  D1 首屏默认收起(`drawerOpen` 只写不回读), tracker/peers 宽表全宽利用 ~97%; W4: D3 ≤900px 转全屏覆盖(纯 CSS)+
  计划内修复两处(停靠面板 sticky 吸底遮蔽以 `window.innerHeight` 为下界的滚动几何 → `_kbViewBottom` 单点下界让位面板顶缘;
  隐藏面板 5s 轮询收口 → 种子视图可见性守卫)+ kb-cursor 复检后未增强(三皮肤可辨, 与既有拍板打架)。
  坑: 模板 `_` 前缀裸标识符为已记坑复发(波及 drawer.html/popovers.html 复制钮, drawer.js 注释钉原因)。
  全量 **2329 passed + 3 skipped / 99%**(基线 [testing/baselines/26-10-03-1335](../testing/baselines/26-10-03-1335-webui-drawer-redesign-w4-done.md));
  冒烟走查单 24 项 × 三皮肤全过; 档案 [tasks/26-10-03-webui-drawer-redesign](../tasks/26-10-03-webui-drawer-redesign.md)

- **WEB UI 站点级「显式空 = 覆盖为空」三态 + 「跟随全局」删键: 删除类标签全局/站点作用域混淆修复**(2026-10-03, issue 26-10-01-2129 方案 B 完整形态, 三阶段提交 `18bde39c`/`42d3d90a`/`9c6bc499`): 根因三层(config 层 `_strip_none` 使 str/list「显式空=未定义」坍缩 / bool 开关恒写值从不删键单向锁死 / 回填用 schema 默认非全局生效值), 用户拍板 B 完整形态 + 配置版本升级。config 层: `Field.tri_state` 属性 + 4 站点 str 键标三态(hr.add_tag / add_category / add_tag_for_satisfied / add_category_for_satisfied)+ `_strip_none` 站点段豁免保 '' + validate 放行 + **配置 v3→v4 迁移**(经 infra.versioning 新增 migrate_with_notes 汇聚)清存量 '' 并逐键 WARNING, ruamel round-trip 保 '' 实测无损; keys.md / docs/configuration.md 同步。显示层: config_editor.js `SITE_FALLBACK_GLOBAL` 7 键回退链表 + cfgSiteFallbackPath/cfgFallbackValue 生效值回填 + siteBadge「站点/全局」来源徽标(站点 '' 原样显示)+ cfgIsDefault 链上键抑制「默认」矛盾徽标; 三皮肤零成对改。交互层: 「跟随全局」按钮接线死代码 cfgResetField/cfgDelPath(confirm danger + toast), str「清空保存=覆盖为空」与「跟随全局=删键」两动作区分, 9 键 help 三态文案(schema/trackers.py), 内联开关 tooltip risk+help 并接修复。守阵: config 层 v3→v4 迁移用例; 冒烟 118/118(atlas/prism/console, bool 三态走全 / str 覆盖为空 vs 删键 / 徽标回退链)。全量 **2325 passed + 3 skipped / 99%**(基线 [testing/baselines/26-10-03-0913](../testing/baselines/26-10-03-0913-webui-delete-tag-scope-confusion-done.md)); 档案 [tasks/26-10-03-webui-delete-tag-scope-confusion](../tasks/26-10-03-webui-delete-tag-scope-confusion.md); 报告 [reports/26-10-03-0504](../reports/26-10-03-0504-report-webui-site-scope-confusion.html); **随实施提交已入库**

- **WEB UI HR 判定新鲜度置脏 (2026-10-03, 计划
  [plans/26-10-03-0436](../plans/26-10-03-0436-plan-hr-hotreload-webui-stale-display.html) P2, `e4df1fc0`)**:
  HR 判定结果非 store 快照字段 —— 取数线程发布新视图(`HrViewPublisher.revision` 自增)无任何置脏消费方,
  WebUI 快照挂在旧值(热重载接入 HR 后恒显「本地·达标」的辅因; 独立缺陷: 运行期判定一变 UI 都要等别的原因
  碰巧置脏)。修法仿「错误原因」先例: `WebUIRuntime` 重建完成时记基线 `_hr_rev_at_build`(挂
  `_publish_locked` 末尾, 判空防御), `flush_views` 比对当前 `hr.revision` 与基线不等即 `mark_dirty()` ——
  基线随重建前移, 无循环置脏。守阵 test_web.py 两用例(直推 publisher 抬 revision → flush 置位
  group_view_dirty / 重建后基线前移不再置脏, 红验过)。坑档
  [pitfalls/backend/hot-reload-stale-bindings-derived-views.md](../pitfalls/backend/hot-reload-stale-bindings-derived-views.md);
  档案 [tasks/26-10-03-backend-hr-hotreload-stale-display](../tasks/26-10-03-backend-hr-hotreload-stale-display.md)

- WEB UI **多选右键菜单四项(限速/移动/跳检/导出 .torrent)+ 跳检菜单开关 `web.skip_check_menu`**
  (2026-10-02/03, 计划 [plans/26-10-02-1955](../plans/26-10-02-1955-plan-webui-multi-ctx-actions.html),
  五波六提交; 拍板 D1=A 前端循环(推翻推荐的后端 zip, 归档端点未建) / D2=是 fail-closed / D3=留空不改):
  W1 配置键全链路(models/loaders/validate/GUI schema/minimal.yml/keys.md/键面 fixture, `b71e1291`)+
  `GET /api/webui/flags` 端点、skip-check 端点 403 gate(只放 web 入口, rule 源零改动)、前端 flags
  显隐门控(v-if 对 undefined 静默隐藏)(`dff534b6`); W2 批量限速/移动(bulk 扩 limits/location,
  qbapi 原生收 hash 列表单次调用, 对话框前置不做乐观贴片, 留空方向不进载荷, `a4bfabbf`); W3 批量跳检
  (bulk 扩 skip_check 走 ops 逐 hash 串行聚合回执, danger 确认框, 复用跳检开关, `f5f62726`); W4 多选导出
  (`exportMulti` 按 selHashSet 全量展开含组选中, 前端循环逐个下载, 零后端改动, `4c0c6f66`); W5 冒烟走查
  汇总(`ui_harness.py` 跳检开关两态参数化 `--skip-check-menu` + `ui_smoke.cjs` 补多选四项齐/单选跳检项/
  确认后提交 bulk(action=skip_check)/限速与导出成功回执 toast/off 态 fail-closed 精简轮, on/off 双皮肤
  实跑, `9f1e2a32`)。test.full **2309 passed + 3 skipped / 99%**(32.13s, 基线
  [26-10-03-0542](../testing/baselines/26-10-03-0542-webui-multi-ctx-actions-done.md));
  档案 [tasks/26-10-02-webui-multi-ctx-actions](../tasks/26-10-02-webui-multi-ctx-actions.md);
  真机走查(用户自配 `web.skip_check_menu: true` 后)待用户执行

- WEB UI **HR 站点状态区展示二轮改造**(2026-10-02/03, 计划
  [plans/26-10-02-1936](../plans/26-10-02-1936-plan-webui-hr-status-display-rework.html),
  5 决策点拍板: ①用户改判「展开即覆盖式全屏, 不另设全屏钮」(原推荐覆盖式机制保留),
  ②a③a④a⑤a 按推荐): ①后端明细行只读标记 `local_present` —— `webui/server/routes/hr.py::
  mark_local_present` 单点(响应层 join `manager.store.by_hash`, infohash v1→v2 顺序 casefold
  探测; 本地存在含暂停 = 做种中, 不存在 = 老旧; 不落盘不进轮询载荷), 「毕业」用户可见 4 处
  改「已达标」(status.py:51,66 / resolve.py:234,350 / events.py:109), 注释按拍板②保留
  (`b50c2873`); ②站点状态块默认折叠(头部摘要行, hubGo 打开分区不再自动拉数只复位折叠态)
  + 「展开」即 fixed 覆盖式全屏弹窗(`.hr-full-mask`/`.hr-full-modal` 三套 UI CSS 成对, 让出
  顶栏/状态栏, 单节点 v-show 不搬 DOM, ESC/✕/遮罩三路关闭 —— ESC 挂 lifecycle 退栈链对话框
  层级、先于 26-10-02-1632「清全部面筛」兜底, dialogs.js escBusy 名单同步; 首次展开才拉数,
  折叠态点立即拉取/刷新 = 顺手展开再拉)(`888a0e29`); ③表① 前端老旧过滤(默认只看做种中,
  与档位 chips AND, 空态文案区分两口径)+ 十列三态排序(对齐 shared/sort.js 范式, 模块级纯
  函数比较器, 空值恒末位, 箭头复用 sprite 双图标)+ 三列重组(档位徽章 / 核实结论徽章 +
  「来源人话 · 时刻」副行 / 在列「在列 | 失踪 N 波」徽章 + 「观察期 · 最近被见到」副行,
  0 哨兵纪律不变)(`8cb2da59`); ④守阵复核 5 项(全屏 CSS 成对 / 默认折叠 / 毕业文案零残留 /
  三态比较器 / 无原生 title)零缺口(`ca77ff23`)。阶段 2/3 各做三套 UI 真浏览器目检(桩数据);
  atlas `.hb-cut` clip-path 裁剪 fixed 后代坑独立入档
  [pitfalls/web-ui/clip-path-clips-fixed](../pitfalls/web-ui/clip-path-clips-fixed.md)。
  test.full **2309 passed + 3 skipped / 99%**(34.59s, 基线
  [26-10-03-0440](../testing/baselines/26-10-03-0440-webui-hr-status-display-rework-done.md));
  档案 [tasks/26-10-02-webui-hr-status-display](../tasks/26-10-02-webui-hr-status-display.md);
  真机走查(真实 qB + HR 数据)待用户执行。
  **文案两轮修订**(2026-10-03): ①「显示老旧种子」→「显示未做种」(回应取证报告 B1);
  ②用户二次驳回「未做种/只看做种中」——「未做种」实为**本地已删除**(非"没在做种"),
  「做种中」反向态**含暂停/异常**, 定为「显示已删除种子 (N) / 只看本地仍在列 (M)」(空态
  文案与注释/守阵标签同步换词, 内部标识符 `oldOn` 族保留; 守阵加旧措辞零残留断言);
  test.full 2416 passed + 3 skipped / 99%(基线 [26-10-03-2335](../testing/baselines/26-10-03-2335-webui-hr-deleted-label.md))。

