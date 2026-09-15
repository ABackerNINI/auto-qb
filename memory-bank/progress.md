# Progress — 路线图与项目状态

> 来源: `想法.md` (设计草稿, 权威) + `README.md` 功能状态标注 + 源码 TODO + git log (截至 2026-09-12, commit d987015)。回答"XX 做了吗/计划怎么做"以此为准; 当前焦点与进行中事项见 [activeContext.md](activeContext.md)。

## 已实现 (✅, 有单测覆盖)

> 注意区分: 下表部分功能作者在 README 中标注 🚧 = "已实现但未严格测试(实盘验证)", 如规则引擎的条件/动作/checking/去重语义等 — 有单测但作者尚不认为经过严格验证; 此类 🚧 ≠ 未实现, 勿移除 (语义详见 pitfalls.md)。

- tracker 分组·站点 groups 字段 + tracker_group 条件 (2026-09-15): 站点段新增可选 groups(字符串列表, 配置层声明不写种子, 组名自由命名无需预定义), 规则条件新增 tracker_group(镜像 TrackersCondition, 或关系, regex:/ignore_case, 无 tracker_conf 恒 False); 校验经 _check_str_list(非列表/纯空白项报错; 空串项被 _strip_none 统一视为未配置剔除, 项目既有约定), spec 校验走 _validate_pattern_list_spec; schema 双登记(TRACKER_FIELDS str_list + CONDITION_PLUGINS, 守卫自动 15→16); 热重载 groups=LEVEL_L2(S0 核实: record.tracker_conf 仅 added 流程绑定一次, L2 reset_runtime 置空重匹配才见新值, 与 domains/rules 同级; L0 会读到旧 conf 对象); Web UI 设置页借 str_list 控件零前端改动即可编辑保存; 测试 +4(test_conditions 条件 2 + test_config 校验/加载 2, helpers.FakeTracker 加 groups 参数), 基线 884 passed; 真机 dry-run 冒烟通过(119 种子同步/规则加载/决策链, 动作被 dry_run 抑制); 计划 docs/tracker-group-plan.html(D1=方案 B 站点字段/D2=tracker_group 已拍板); 后续阶段 2/3 前端: 设置页 groups 下拉快捷追加 + 辅种管理页按组筛选; README(5 处 15→16 种)/docs/configuration.md(示例+条件表)/memory-bank(rule-system 16 条件+config-reference+testing 基线)/想法.md 回写; 已随本提交入库
- TorrentRecord 鍏ㄥ瓧娈电紦瀛?(2026-09-15): 蹇収 21 鈫?70 瀛楁(蹇呴渶 21 + 閲嶅姞鍗囨牸 6 + 鍙€夋墿灞?43, 瀛楁瀹氱鍙傜収鐢ㄦ埛鎻愪緵鐨勭湡鏈?TorrentDictionary 鏍蜂緥 + 鐪熸満鍐掔儫琛?4 瀛楁), 涓?WebUI 鍚庣画鍔熻兘渚涙暟; D1-D5 鍐崇瓥瑙?[docs/record-full-fields-plan.html](../docs/record-full-fields-plan.html): slots 鍏ㄩ噺澹版槑(_raw 闄嶄负鍓嶅悜鍏煎鍏滃簳)/RE_ADD_FIELDS 鍗囨牸杩涘揩鐓?鍙樺寲寮€濮嬭鍏ュ彉鍖栭泦)/鏂板瓧娈靛叏鍙€?榛樿鍊煎彇 qB 鍝ㄥ叺 -1/-2/8640000, REQUIRED 鏍￠獙闈笉鍙?/缂撳瓨鈮犲睍绀?鏂板瓧娈典笉杩?_VIEW_FIELDS, 瑙嗗浘閲嶅缓鎴愭湰闆跺彉鍖? 娴嬭瘯閿佹)/鍝ㄥ叺鍘熸牱閫忎紶; 鏂板 `to_dict()` 鍏ㄥ瓧娈靛鍑? 鐪熸満鍙鍐掔儫(119 绉嶅瓙)鍝嶅簲瀛楁鍏ㄥ０鏄?_raw 鏃犳畫鐣? 娴嬭瘯 +9 鍑€ +7, 鍩虹嚎 879 passed; 瑙嗗浘/瑙勫垯/HR/鍒嗙粍娑堣垂瀛楁鍏ㄥ湪鏃ч泦鍚堝唴闆惰涓哄彉鍖?- 渚濊禆绠＄悊鐜颁唬鍖?(2026-09-15): pyproject.toml(PEP 621 + hatchling, 12 鐩存帴渚濊禆 == 閿佹鍚?filelock 3.32.6 / uvicorn 0.53.0 鏈€鏂? dev 璧?PEP 735 渚濊禆缁? entry point `auto-qb = auto_qb.cli:main`) + uv.lock 鍏ㄩ噺閿?41 鍖?+ `uv sync` editable 瀹夎(娓呴櫎鏃у３ venv 涓庣害 20 涓棤鍏冲寘); CI 鍒?astral-sh/setup-uv@v10(enable-cache) + checkout@v6 + setup-python@v7 + uv sync/uv run; `uv build` sdist/wheel 鎵撳寘灏辩华; 鍓嶇疆璋冪爺 docs/dependency-lock-report.md; requirements-dev.txt 宸茶 pyproject 鍙栦唬(闅忔彁浜ゅ垹闄?; README/AGENTS/testing/techContext 鍚屾, 鍩虹嚎 872 passed (uv 鐜)
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
