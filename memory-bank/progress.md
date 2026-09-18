# Progress — 路线图与项目状态

> 来源: `想法.md` (设计草稿, 权威) + `README.md` 功能状态标注 + 源码 TODO + git log (截至 2026-09-12, commit d987015)。回答"XX 做了吗/计划怎么做"以此为准; 当前焦点与进行中事项见 [activeContext.md](activeContext.md)。

## 已实现 (✅, 有单测覆盖)

> 注意区分: 下表部分功能作者在 README 中标注 🚧 = "已实现但未严格测试(实盘验证)", 如规则引擎的条件/动作/checking/去重语义等 — 有单测但作者尚不认为经过严格验证; 此类 🚧 ≠ 未实现, 勿移除 (语义详见 pitfalls.md)。
- WEB UI 错误种子显示具体原因 (2026-09-18): 状态列不再只显示笼统「错误」—— `missingFiles` → 「文件丢失」(零 API, 状态自明), `error` → tracker 报错原文(如 `torrent not registered with this tracker`, 过长省略 + `title` 全文)。**前提核实**: qB `torrents/info` **不含**任何错误文本字段, 原因只在 `/torrents/trackers` 的 `msg` ⇒ 只能派生或另取。实现: 后端 `WebviewMixin.refresh_error_reasons` 在**主循环**按 TTL(300s)+单轮预算(5 条)预取, 写进 `TorrentRecord` 的**非快照**缓存槽 `tracker_error_msg`/`tracker_error_ts`(不进 `_SNAPSHOT_FIELDS`/`_raw`), 视图组装**只读缓存**(视图可能每 tick 重建, 不得发 API); 原因非快照字段 ⇒ 变化时由预取方**显式置 `_group_view_dirty`**; `missingFiles` 排除在拉取分支外(原因自明, 且"成片文件丢失"正是最需保住预算的场景); 预取与视图重建/搜索索引同门控(网页关掉不发请求); 断连时保持现值不清空。原因文本**取数单点** `_error_reason`, 视图透出 `error_reason`, 前端 `stateText(m)` 仅错误态采用(双 UI 共用逻辑层, 一处改两套生效; 模板各 4 处状态格 + 两套 CSS 省略规则)。基线 1001 → **1006 passed**(+5 项: tracker msg 提取/缺失文件零 API/预算与 TTL/恢复清空/断连跳过), 假 qB 服务(真实 `create_app`+uvicorn)双 UI DOM 与截图实测; 档案 [tasks/TASK015](tasks/TASK015-webui-error-reason.md); **已入库 `9723a76`**
- WEB UI 第十一轮修复 (2026-09-17): 7 项 (`想法.md` 待办)。①图标语义色补齐: 导航「追剧」(新挂 `ico-tv`)与「添加种子」(新挂 `ico-add`)、状态栏「空间剩余」(`.ico-disk` 原继承 `--fg-dim` 观感无色 -> indigo)与两处「限制速度」仪表盘(-> `--limit-hit`, "不限速"只弱化数值); ②状态栏历史入口**去文字只留图标**(图标改取 today-up 族色, 否则只剩灰点); ③**明细表接入点击排序** —— 明细与三视图正交, 故新增独立 `detailSortKey/detailSortDir` + `setSort(key,'detail')` scope 分支(表头右键排序项同源), 明细列模型补 `sortable` 标记到 14 列(Hash 除外), 行序由 `sortedMembers(list)` 派生(空键=后端原序, 标签为数组故先 join 再比); ④**保存路径列迁移**: 辅种表新增(组级取首位成员值 = 路径筛选器同口径), 明细表删除(组内成员路径本就一致); ⑤**横向滚动条(三项根因, 两轮才定位)**: `.group-head` 脱离滚动容器 => 表头比 `.content` 宽时把整页撑宽(实测表头写 3000px, `documentElement.scrollWidth` 1872→3012) -> `.content { overflow-x: clip }`(clip 不建滚动容器, sticky 与表头 transform 跟随不受影响); `.detail` 自带 `overflow-x: auto` => 与外层各滚各的 -> 去掉内层滚动; **"列没溢出却常驻横滚条"的真因是单元格自动最小尺寸**(表格层 `white-space: nowrap` + 单元格 `min-width: auto` = 文本全长, 13 列累加把行 `min-content` 顶到容器之上) -> 行内单元格统一 `min-width: 0`, 行/表头保持 `fit-content`(**底色跟内容**); 中途曾用"行定宽 100%"治假滚动条, 但那会让**溢出段没有行底色/边框**(用户实测反馈"滚动后右边无背景条"), 已回退。 ⑥**标签/分类芯片改状态色**(原"分类恒蓝/标签恒灰"无语义且蓝色与"下载中"撞色), 跟随所在行状态语义色, HR 标签用 `:not()` 排除保住橙/青语义。基线 999 passed(**不变**, 前端改动由静态守阵 + 双 UI 浏览器冒烟覆盖), 档案 [tasks/TASK013](tasks/TASK013-webui-fix-round11.md)
- WEB UI 第十轮修复 (2026-09-17): 16 项 (R10-01~R10-16) 按成因归 7 类实施, 计划 [docs/plans/26-09-17-0901-webui-fix-plan-round10.html](../docs/plans/26-09-17-0901-webui-fix-plan-round10.html)。三条硬 bug: ①**状态栏限速读了不存在的字段名**(前端读 `server_state.dl_limit/up_limit`, qB 真键是 `dl_rate_limit/up_rate_limit`; 该字段还兼作速度染色分母 ⇒ 色阶从未生效) -> `speedLimitBytes` 取数单点, 状态栏与染色分母同源; ②**星图点一次限速开两个窗口**(`.speed-pop` 与 SPD-04 旧模态共用 `speedOpen`, 第九轮漏删星图) -> 删旧模态 + 静态断言; ③**本机免鉴权仍被弹回密钥页**(前端把"有身份"绑死"密钥串非空") -> `authMode`/`authOk` 单点判据 + 不带空 Bearer。结构性: **列对齐进列模型**(`align` + `colAlignCss` 按可见列生成 `:nth-child` 规则注入 `<head>`, `data-table` 标记表头与值, 一处改两套生效; `:where()` 压特异性以保留既有"0 值居中")与**列偏好不再重置**(跨版本迁移 `LEGACY_COLS_KEYS` + 不再用升版本应对列集变更 + 写盘容错; origin 隔离作为限制入 pitfalls)。服务端新增能力: `/api/fs/dirs`(只列目录, 允许根白名单 + realpath 边界 + 符号链接逃逸防护) 与 `/api/fs/mkdir`(单层名字 + 幂等 + 同名文件 409), `open-path` 对单文件种子改为**定位选中**; 前端新增服务端目录浏览器对话框替代自绘下拉。其余: 状态栏底色专用令牌 `--statusbar-bg` + 去文字标签 + 历史入口并入今日流量组、选中态令牌族 `--sel-*`(五主题靖蓝族, 与做种绿分家)、文本列(站数/保存路径/hash/tracker)加入行状态色、弹窗尺寸令牌族(窄/标准/表单/宽/超宽; 添加窗口两 UI 统一 860px)、值行"单行省略 + title + 复制按钮"、菜单「高级能力」→「更多操作」、抽屉目录/文件分色、删除详情行由 `_deleteDetails` 由目标集合统一派生(四入口同构); 基线 996 → **999 passed**(+open_path 平台用例 + `/api/fs/dirs` + `/api/fs/mkdir`); 双 UI 浏览器冒烟逐项实测通过(假 qB + 临时 data_dir, 完事清理)
- WEB UI 第九轮修复 (2026-09-17): 25 项 (FX-01~FX-25) 按成因归 8 类实施, 计划 [docs/plans/26-09-17-0847-webui-fix-plan-round9.html](../docs/plans/26-09-17-0847-webui-fix-plan-round9.html)。三条公共底座: ①**单元格口径单点化**(做种时长/分享率/用户·做种三列此前在模板里各写三份 -> `cellSeedingTime`/`cellRatio`/`cellPeers`, 两套 UI 共用); ②**浮层锚定契约**(`.add-dialog-pathrow` 缺定位祖先导致面板渲染到视口之外 = "点了没反应"; 退役原生 `<datalist>`; 面板锚点下沉到 `.add-input-row`); ③**暂停态中性令牌族**(五个主题各补 `--paused/--paused-soft/--paused-line`, D8=方案B 无色相)。结构性重构: **选择模型**改"互斥 + 单一权威 + 派生集合"(`selHashSet` 三视图打通 + 半选态 + 追剧页修饰键选择), **删除链**四条入口统一到 `_deleteFlow`(汇报前置 + 等待聚合回执 + 收尾清选择)。其它: 启动鉴权首帧(`bootstrapping` 初值 = 未知)、底部状态栏重排(今日流量 + 复活历史流量入口 + 速度·限速配对 + 无遮罩就近浮层)、右键菜单分层(flyout, 一级只留 PT 高频)、追剧页整剧菜单、添加窗口 760px + 选项胶囊化 + 警告行常驻占位、抽屉常规页重构(分组卡片化 + 图标色调 + 长值块行 + 行内值操作)、列头拖动虚影、文案"分组"→"辅种"(`L10N_GROUP` 单点)。新增后端只读端点 `POST /api/open-path`(路径一律服务端派生, 不接受客户端传路径)。基线 995 → **996 passed**; 浏览器冒烟 25 项全过、0 控制台错误
- Memory Bank 触发机制修复 (2026-09-17): 补建真正的 skill 载体 `.agents/skills/memory-bank/SKILL.md` (会话开始 3 步 / 收尾 DoD 5 步 / 立档阈值 4 条 / 档案规范 / 反模式; 先建于 `.github/skills/`, 同日按仓库技能根惯例搬入 `.agents/skills/`), always-on 入口 (`AGENTS.md` + `.github/copilot-instructions.md` + `ai-lib.md`) 声明**可判定阈值**并指向 skill, `memory-bank.instructions.md` 顶部标注"本文件不负责触发 (applyTo 限定 memory-bank/**)"; 按**专题粒度**回填 `tasks/TASK001`~`TASK010` (30 条历史会话纪要原文按专题归档) 并重写 `_index.md`; `activeContext.md` 68 行 → 26 行 (恢复易变层定位); 新增守卫 `tests/test_memory_bank.py` (6 项, 红绿验证: 幽灵任务与纪要回流两类违例均被拦截); 基线 989 → **995 passed**
- WEB UI 替代 qB 界面 · 波次三 (2026-09-17 收口完成): 32 工作项 (FIX7/TBL8/DLG4/CTX3/SPD4/NAV3/RFB2/PRS1) 全部落地, **星图(atlas)与棱镜(prism)双 UI 同构**。后端: peers 端点修复(`sync_torrent_peers`)/`/api/paths` 已知目录聚合/bulk 组键模式/成员与单种透出 num_seeds·num_leechs·num_complete·num_incomplete/SPD-01 末档 clamp 回归锁定/SPD-03 `global_speed_limit_curve.enabled` 全管线(models+validation+loaders+设置页开关)。前端: 表格层(空值留白与"不限速"文案退役、状态底与七列三档数值色阶、去名称状态图标、列拖动重排+右键列选择器、补列、全宽布局、rail 退役改底部状态栏、批量段并入筛选行)、弹窗(删除确认框加宽+计数语义、添加种子改版与位置选择)、右键(彩色图标集/触发源强调/原生右键屏蔽)、限速(预览末档压缩、点击弹窗修改)、导航 IA(分组/种子/追剧升一级导航、设置右移、统计入状态栏、日志并入设置页、动态 logo)、详情抽屉纯展示重构、设置页重构(栅格令牌化/宽度放开/文案用户化/风险注记统一)。计划 [docs/plans/26-09-16-1128-webui-qb-replace-wave3-plan.html](../docs/plans/26-09-16-1128-webui-qb-replace-wave3-plan.html) + 派工契约 `.cluster/webui-w3/` + 交接 [docs/plans/26-09-17-0346-webui-qb-replace-wave3-handover.md](../docs/plans/26-09-17-0346-webui-qb-replace-wave3-handover.md); 基线 971→**988 passed**; 待人工: 浏览器 CDP 双 UI 走查 + 真机 dry-run。- tracker 分组·站点 groups 字段 + tracker_group 条件 (2026-09-15): 站点段新增可选 groups(字符串列表, 配置层声明不写种子, 组名自由命名无需预定义), 规则条件新增 tracker_group(镜像 TrackersCondition, 或关系, regex:/ignore_case, 无 tracker_conf 恒 False); 校验经 _check_str_list(非列表/纯空白项报错; 空串项被 _strip_none 统一视为未配置剔除, 项目既有约定), spec 校验走 _validate_pattern_list_spec; schema 双登记(TRACKER_FIELDS str_list + CONDITION_PLUGINS, 守卫自动 15→16); 热重载 groups=LEVEL_L2(S0 核实: record.tracker_conf 仅 added 流程绑定一次, L2 reset_runtime 置空重匹配才见新值, 与 domains/rules 同级; L0 会读到旧 conf 对象); Web UI 设置页借 str_list 控件零前端改动即可编辑保存; 测试 +4(test_conditions 条件 2 + test_config 校验/加载 2, helpers.FakeTracker 加 groups 参数), 基线 884 passed; 真机 dry-run 冒烟通过(119 种子同步/规则加载/决策链, 动作被 dry_run 抑制); 计划 docs/tracker-group-plan.html(D1=方案 B 站点字段/D2=tracker_group 已拍板); 后续阶段 2/3 前端: 设置页 groups 下拉快捷追加 + 辅种管理页按组筛选; README(5 处 15→16 种)/docs/configuration.md(示例+条件表)/memory-bank(rule-system 16 条件+config-reference+testing 基线)/想法.md 回写; 已随本提交入库
- TorrentRecord 全字段缓存 (2026-09-15): 快照 21 → 70 字段(必需 21 + 重加升格 6 + 可选扩展 43, 字段定稿参照用户提供的真机 TorrentDictionary 样例 + 真机冒烟补 4 字段), 为 WebUI 后续功能供数; D1-D5 决策见 [docs/plans/26-09-15-1302-record-full-fields-plan.html](../docs/plans/26-09-15-1302-record-full-fields-plan.html): slots 全量声明(_raw 降为前向兼容兜底)/RE_ADD_FIELDS 升格进快照(变化开始计入变化集)/新字段全可选(默认值取 qB 哨兵 -1/-2/8640000, REQUIRED 校验面不变)/缓存≠展示(新字段不进 _VIEW_FIELDS, 视图重建成本零变化, 测试锁死)/哨兵原样透传; 新增 `to_dict()` 全字段导出; 真机只读冒烟(119 种子)响应字段全声明 _raw 无残留; 测试 +9 净 +7, 基线 879 passed; 视图/规则/HR/分组消费字段全在旧集合内零行为变化
- WEB UI 双界面命名与目录化 (2026-09-15): 旧 UI 迁 `atlas/`(星图)、`newui/` 改名 `prism/`(棱镜), 共享逻辑层三件套+vendor+icon 收进 `static/shared/` 单一来源; web.py 加 `/`→307 `/atlas/`(默认 UI)与 `/newui/*`→307 `/prism/*` 书签兼容, 鉴权范围显式限定 `/api/*`(require_token 加 Request 路径判断, 行为等价 —— 原静态免鉴权靠 StaticFiles 不经依赖系统的副作用, 重定向真实路由后必须显式放行); atlas 顶栏切换器类 `.newui-entry`→`.ui-switch`, 互切链接文案改「星图/棱镜」; test_web 静态缓存测试路径更新 + 新增 test_ui_root_and_legacy_newui_redirect; 命名原则沉淀(身份名不代际名/目录名=URL 英文小写/中文两字/成组不撞车); 计划 docs/webui-naming-plan.html
- 依赖管理现代化 (2026-09-15): pyproject.toml(PEP 621 + hatchling, 12 直接依赖 == 锁死含 filelock 3.32.6 / uvicorn 0.53.0 最新, dev 走 PEP 735 依赖组, entry point `auto-qb = auto_qb.cli:main`) + uv.lock 全量锁 41 包 + `uv sync` editable 安装(清除旧壳 venv 与约 20 个无关包); CI 切 astral-sh/setup-uv@v10(enable-cache) + checkout@v6 + setup-python@v7 + uv sync/uv run; `uv build` sdist/wheel 打包就绪; 前置调研 docs/dependency-lock-report.md; requirements-dev.txt 已被 pyproject 取代(随提交删除); README/AGENTS/testing/techContext 同步, 基线 872 passed (uv 环境)
- WEB UI 旧版第八轮优化 (2026-09-15): 吸顶贴合(批量条/表头零缝堆叠, --bulk-h 剔除 margin)、筛选器幽灵空位消除(清除chip 常驻可见降透明)、删除确认框修复+扩容(`_findGroup` 优先查 decoratedGroups 修保存路径恒"—"; 批量删除补成员明细含路径; wide 560→720)、H&R 筛选(达标/未达标)、单种子视图(TORRENT_COLUMNS + 后端 `_build_singles_view` 未归组种子与 groups 同快照同版本门控)、信息栏双模式(左栏↔顶栏紧凑双排条持久化)、令牌中性化视觉刷新; 冒烟 10/10(修复包/筛选/视图/双模式全断言)+ pytest 872 全绿; 计划 docs/webui-optimization-plan-v3.html; 详见 pitfalls 第八轮条目
- WEB UI 新版界面与多主题 (2026-09-15): `newui/` 独立目录并存可切换(`/newui/` 零后端路由, 旧 UI 原样保留仅顶栏 +1 链接, 共享逻辑层单一来源)；令牌化五主题(深海机房/暗夜星云/极地晨霜/麦秋/品牌轨道, data-theme + localStorage + 系统明暗跟随, theme.js 首帧前同步防 FOUC)；Edge headless CDP 冒烟 34/34(双 UI 功能等价/主题切换持久化/五主题 WCAG 对比度全达标/移动宽/无控制台错误), pytest 871 全绿；设计计划见 docs/webui-redesign-plan.html；详见 pitfalls 新版 UI 条目
- 标签/分类管理: 站点标签加/删、相似标签清理、`delete_tags`/`delete_tags_if_has_no_torrents` 全局清理、集数标签
- HR 管理: 触发标签/分类 + satisfied 标签/分类, 站点覆盖全局
- 辅种分组: 增量归组、大小一致性、缺文件事件驱动扫描 (删除/上传转暂停/路径变化)、下载冲突检查
- 规则引擎: interval 触发 + 15 条件 + 12 动作 + execute_once/cooldown 去重 + 断点续跑 + stop_following_rules_if; 事件触发 (interval/on_* 四值 trigger + 事件分派引擎 + rule-event 断点续跑 + on_torrent_deleted 动作白名单 `print_torrent_details`, 2026-09-12 落地, 设计细节见下"事件触发(规则)规划")
- checking 动作: filelist/piecehashes/custom 三种参考判定 + full-checking (异步轮询) + skip-checking (导出→删除→重加, 同日去重+备份)
- tracker 单种限速 (奇数保护)
- 全局限速曲线: Traffic Monitor 数据源, DAY/MONTH/ND 聚合, 全程分档覆盖, 取最严 (2026-09 最近的大功能, commit ee88bc8..20481f3)
- 托盘常驻 UI (2026-09-12, --tray): `ui.py` —— CustomTkinter 深色窗口(状态卡片/最近日志/暂停恢复/通知热切换/开机自启)+ pystray 托盘(6 项菜单, 勾选态实时); 运行时暂停/恢复 = pause_event 完全旁观, 恢复后增量 diff 补上; 双开唤起 = 单实例锁 + localhost IPC(ui.port, 第二实例静默退出 0); 托管模式主循环移入后台线程(单一写线程约束保持), 首连失败重试常驻; GUI 栈仅 tray 分支加载; 通知开关支持从未配置状态热挂载(setup_notify force, 会话级); toast 点击激活唤起窗口(launch_arguments 经 AUMID 快捷方式 Arguments); 窗口图标 CTk iconbitmap 防 CTk 默认覆盖(assets/icon.ico); 打开日志目录前绝对化路径并确保目录存在, 托盘事件单点失败不中断 UI 轮询链; 新依赖 pystray/Pillow/customtkinter
- 主动通知 (2026-09-12): `notify.py` 零第三方依赖 —— NotifyHandler 挂 `auto_qb` logger 复用日志规范, PlatformChannel 按平台分派(win32=PowerShell WinRT toast / linux=notify-send / darwin=osascript), quiet_hours 免打扰(与 date_time 共用 utils.time_in_range) + 每小时上限 + 同键去重窗(内存态); CLI 致命退出补发 notify_fatal; dry-run 不挂载; toast 来源显示 "AutoQB" —— 首次运行幂等注册开始菜单快捷方式 AutoQB.lnk(%APPDATA% Programs 目录, 隐式 AppUserModelID), 注册失败回退 PowerShell 来源
- 任务队列: 单 heapq 队列 + `add_task(keep_progress=...)` 断点语义 + check 轮询在途去重 (12f3b46 重构完成)
- 数据层: TorrentStore 快照+惰性缓存+分组索引; QbApi Facade写后同步
- YAML 导出 (`--export-yaml`, `--only-missing`), qB 5.0 API 适配
- fail-fast 全量配置校验 (2026-09-05): `config.validate_config` 聚合校验未知键/必填项/值格式/规则 spec/引用存在性; 留空(空串/None)走默认值; Rule 构造报错带规则名上下文; `load_*` 解析函数已剥离全部检查(先验证再解析, 解析假定配置正确)
- 单实例锁 (2026-09-05): 基于第三方 `filelock`, 锁文件 `<state_file 去扩展名>.lock` + 伴生 `.meta.json`; 仅正常 `run()` 模式持锁, `--export-yaml` 等只读模式通过 `no_lock=True` 跳过; 失败抛 `SingleInstanceLockError(AutoQbError)`, CLI 单点捕获 AutoQbError 体系干净退出 (退出码 1, stderr 无堆栈); 陈旧锁不接管 (OS 句柄随进程退出自动释放, 必要时手动删除)
- 测试: 基线数字单点维护于 [testing.md](testing.md) 顶部 (2026-09-14 起, 此处不再手抄; ui.py GUI 本体真机冒烟)

## 规划中 (🚧, 尚未实现)

(以下 WEB UI 核心已于 2026-09-13 实现, 见 productContext.md/modules.md; **2026-09-14 已补图形化配置编辑** —— 设置页每项配置均可增删改, 含站点/规则集(15 条件 + 12 动作)/限速曲线的结构化编辑与只读 YAML 预览, 直接编辑模式已移除; 剩余: WebSocket 推送/多用户)

### 规则系统
- ~~触发时机: `on_torrent_added` / `on_torrent_deleted` / `on_torrent_state_enum_changed`~~ — 已实现 (2026-09-12, 落地现状见下"事件触发(规则)规划": 事件分派引擎/断点续跑/测试全部完成)。**注**: 设计已把 `on_torrent_state_changed` 收敛为 `on_torrent_state_enum_changed` (与 `TorrentState` 枚举命名对齐)。
- 条件取反 (`!` / 非 logic) — `:ignore_case` 支持已完成 (2026-09-12, 见 08 TODO 段)
- tracker 分组 (规则按组筛选)

#### 事件触发(规则)规划 (2026-09-12 设计定论, 已实现)

**核心原则** — 区分"触发(瞬时)"与"结果(异步/状态式)"两种调度, 事件两者都要支持:

| 环节 | 触发方式 | 依据 |
|------|---------|------|
| 事件检测 + 事件规则动作入口 | 同步即时 (当拍快照, 不排队) | 事件是对瞬时状态转移的反应, 延后失真 |
| checking 动作的提交判断 (execute 决策链) | 同步即时 (随事件入口执行) | 判断"该不该校验"读瞬时状态 |
| checking 动作的结果轮询/组内等待 | 走队列 (现状 check / check-wait) | 轮询异步终态, 延后无害 |
| 校验成功后事件规则断点续跑 | 走队列 (`add_task(origin, keep_progress=True)`) | 复用现有 origin 恢复机制 |

**为事件造"可恢复 origin" (关键机制)**: 事件触发时 `_apply_event_rule` 传入真正的 `Task` 对象 (kind="rule-event", 一次性任务) 作 `ctx.task`, 而非 None。这样 `_execute_full_checking` 的 `origin = ctx.task` 就是该 rule-event 任务: 校验成功 → `on_success()` + `tq.add_task(origin, keep_progress=True)` → 断点保留 → 下 tick `_handle_event_rule` 从断点续跑事件后续动作; 失败/删除 → `add_task(origin)` 默认重置重走完整决策链 (删除由事件 handler 的删除守卫判死)。

**rule-event 任务的可恢复但一次性双重性质**: 它从不被 `run_due` 主动弹出 (事件分派时**不 add_task**, 避免被当周期任务弹掉/占 max_tasks 计数); 只在两条路径出现 — (A) 事件分派即时执行: `_apply_event_rule` 拿到 process 返回后持有 Task 对象作 origin, 不接 `_fast`; (B) 断点续跑: 轮询子任务 `add_task(origin, keep_progress=True)` 把它入 `_fast`, 下 tick `_handle_event_rule` 执行并从断点续跑后**返回 FINISHED 消亡** (恒不自我周期循环, 除非再遇 pending)。

**落地现状** (2026-09-12): 全部实现 — `Rule.trigger` 解析、`RuleContext.snapshot` 快照回退 + `torrent` 属性、`TRIGGER_VALUES` 四值、`_validate_trigger_action_compat` 白名单 (`DELETED_TRIGGER_ALLOWED_ACTIONS = {"print_torrent_details"}`)、`print_torrent_details` 动作、事件分派引擎 (`_dispatch_events`/`_apply_event_rule`/`_handle_event_rule`/`_rules_by_trigger`/`_torrent_event_rules`)、`_refresh_torrents` 分派点接线 + 删除前快照捕获 (`removed_snapshots`)、`taskqueue` rule-event kind 语义、`tests/test_trigger_events.py` (13 个测试, 覆盖四触发器/checking 断点续跑三态/混用/白名单/dry_run)。

**⚠️ 已修复的潜在缺陷 (2026-09-12)**: `_create_rule_task` 对非 interval 规则返回 `None`, 原 `_create_torrent_tasks` 直接 `tasks.append(...)` 并 `add_tasks` → 遇到 `trigger: on_*` 规则时 `add_task(None)` 会在 `None.resume_index` 处 AttributeError 崩溃。已修复: `_create_torrent_tasks` 过滤 None 条目后再入队。

**触发时机 × 动作白名单** (`_validate_trigger_action_compat`, config 阶段 fail-fast):

| trigger | 允许动作 | 特别说明 |
|---------|----------|---------|
| `interval` | 全部 12 | 现状 |
| `on_torrent_added` | 全部 12 含 checking | 事件入口 + origin 续跑 |
| `on_torrent_state_enum_changed` | 全部 12 含 checking | 事件入口 + origin 续跑 |
| `on_torrent_deleted` | **仅 `print_torrent_details`** | 删除后 store 无该种子, `ctx.torrent` 回退删除前快照副本; 需活种子的动作 (启停/校验/限速/移动/汇报) 都无意义 → 拒绝; 只读留档动作适用。**此即"唯一待确认"的答案**: 因新增 `print_torrent_details`, 原空集白名单放宽为只读动作集 |

**触发点接线** (`qbmanager._refresh_torrents`): 在 `store.refresh` 之后、自有动作之前、`update_state_snapshot` 之前的分派点同步执行各事件规则 (即时), 遇 checking 内部建 rule-event origin → pending → 轮询子任务走队列 → 结果恢复续跑。

**性能与副作用**: 事件分派同步执行拉长单 tick (数千种子大库 + 大量事件时, 与 grouping 缺文件扫描同模式, 已被接受); `max_tasks_per_tick` 只约束队列里的轮询/恢复任务, 不约束事件即时分派。

### 其它功能
- 通知多渠道: webhook/邮件/Telegram 等(channels 配置结构已按列表预留, 与 traffic_source 同款演进路径); Windows 自定义图标(当前快捷方式图标为 Python 解释器图标, AUMID 来源名已实现); toast 交互按钮(需 winsdk)
- 插件系统: 直接支持自定义 Python plugin
- 根据流量接入更多数据源 (traffic_source 当前仅 traffic_monitor 单源, 代码已按列表预留)
- 与 PTD-cli 合作: 自动分析 HR 标签 / 暂停低分享率非免费种子 (想法.md 标注"需可行性验证")

## 已知 BUG (来自 想法.md)

- ~~新加的种子无法触发 skip-checking~~ (2026-09-06 已修复): 生产日志实锤 —— 跳检删除→重加同 hash 种子后, `store.remove_torrent` 保留 `_known_hashes` 导致重加种子**不进 added 列表**, 下轮 refresh 重建记录 `tracker_conf=None` 永久未匹配; `log_repr → tracker_name` 回退 `self.tor.client`(真实 TorrentDictionary 无此属性) AttributeError。修复: ①跳检重加成功后恢复删除前快照记录(tracker_conf/惰性缓存保留) ②tracker_name 无 conf 返回 "Unknown"(与 FakeTorrent 对齐, 不再回退 tor.client)
- 复杂限速规则 (tracker+时段组合等)
- 性能: 主循环拆分平滑占用、全面优化 (想法.md 标注) —— **2026-09-14 已修其中一处严重回归**: 非托管模式下主循环完全不节流(空转约 2800 tick/s, 详见 08 陷阱); 其余优化(如 `update_state_snapshot` 增量化)经评估风险大于收益, 暂不做

### 代码内待办 (TODO 清单, 2026-09-09 核对; 位置用函数/方法名锚定, 行号易漂移)
| 位置 | 内容 |
|------|------|
| ~~qbmanager.py `_get_torrent`~~ | 兼容方法已删除, 统一用 `store.get(hash)` |
| ~~rules/base.py 多 tracker 匹配~~ | 已处理 2026-09-05: `_match_tracker_conf` 命中多个打 ERROR 用第一个 |
| ~~rules/base.py HR 判定迁移~~ | 已迁移 2026-09-05: check_hr_* 移至 TorrentRecord, replace_vars 移至 utils |
| ~~rules/conditions.py (tags/category/trackers 三处 `# TODO: 支持:ignore_case`)~~ | 已完成 2026-09-12: 三条件改走 `utils.match_value` 统一匹配, `:ignore_case` 全支持; config 阶段补 regex 可编译校验 |
| ~~recheck 失败冷却~~ | 已实现 2026-09-05: 连续失败3次当日冷却, recheck_fails |
| rules/actions/checking.py `CheckAction.execute` 闸门 0 上方 | 未完成且暂停的种子 recheck 后仍未完成, 下一轮会再次校验 (3 次失败冷却兜底, TODO 未销) |
| rules/actions/checking.py `_find_reference` 上方 | 优化为 `has_reference() -> bool` 提前返回 |
| rules/actions/checking.py 分段执行处 | 重新设计自定义 (custom) 校验流程 |
| ~~mixins/tags.py `_add_hr_tag_or_category`~~ | 已完成 2026-09-12 (commit d987015): HR 条件/satisfied 判定改委托 `TorrentRecord.check_hr_condition/check_hr_satisfied` 单点判定 |
| config/loaders.py `load_global_hr` / `load_tracker_hr` | 函数上方 `# TODO: optimize` |
| ~~reannounce 限频~~ | 已实现 2026-09-05: 运行时最小间隔10M + 加载告警 |
| ~~episodes.py 集数标签格式~~ | 已实现 2026-09-05: add_episode_tags 段 add_tag_single/add_tag_multi 模板 |

## 近期演进脉络 (git log 提炼, 有助于理解"为什么现在是这样")

1. 任务队列驱动重构 (12f3b46, 528 passed) — 双队列合并为单 heapq 队列, `add_task` 断点语义 (keep_progress 续跑/默认重置) 建立
2. 全局限速曲线落地 (ee88bc8 → 20481f3) — SpeedCurveMixin + curves 纯逻辑模块 + qB5.0 transfer 端点适配 (f402eaf)
3. 跳检稳健性 (5ab17c5, e5ea9e7) — 修复删除种子后访问属性/后续任务报错
4. 覆盖率补齐 (6f60a5a) — config/qbapi/qbmanager/logging/cli/tracker/speed_curve 缺口

## 给 AI 的实现建议 (基于现有架构的延伸方向)

- **新触发时机** (`on_torrent_added`): `_refresh_torrents` 的 added 循环已经是事件点; 按 09 事件触发规划, `_dispatch_events` 同步分派 added 事件规则 (不建周期任务), 复用 `_apply_event_rule` + rule-event origin 机制。
- **状态变化触发** (`on_torrent_state_enum_changed`): `store.state_snapshot` 已保存上一轮枚举状态, `_handle_state_transitions` 是现成的"状态转移检测"参考实现 (grouping 内部用); 事件分派用它对比上轮/本轮状态枚举筛选触发。
- **删除触发** (`on_torrent_deleted`): 用 `store.refresh` 返回的 removed 及其删除前快照副本触发; 白名单只允许 `print_torrent_details` 只读留档。
- **新流量源**: `curves.py` 保持无项目内依赖; 数据源解析独立成函数返回 `List[HistoryRow]` 即可复用 aggregate/curve_speed 全链路。
