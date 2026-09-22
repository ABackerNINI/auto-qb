# Conventions — 编码规范与项目约定

> 文内带日期条目为增量更新; **若代码与本文冲突, 以代码为准并回写**; 最新易变状态见 [activeContext.md](activeContext.md)。

## 协作约定 (用户明示)

- **必须全程使用中文**： 本项目中 AI 的所有交流、注释、文档、提交信息等一律使用中文, 除非用户显式要求使用其它语言。
- **提交 / push 口径以 `AGENTS.md`「提交 / PR」为单点定义** (2026-09-19 用户重新指定): **用户说"提交" = commit + 自动推送** —— ①先 commit 让工作区干净 ②`git pull --rebase <远端> develop` ③推 Gitee 主线 (协作主线, 必须成功) ④再**尝试一次** GitHub 直连 (失败只如实报告一次, 不重试) ⑤提交后核对 `HEAD` == `refs/heads/<分支>`。本节只留指针, 不复述细则 (避免两处各自演化)。
  - 历史沿革**不在本文件复述**(2026-09-10 曾规定"绝对不要 push", 已作废) —— 口径与沿革的单点定义都在 `AGENTS.md`「提交 / PR」。
- **多 AI 在各自独立 clone 上并行工作** (2026-09-20 改: **弃用 git worktree**; 原 2026-09-10 定的"共享同一个 `.git` 的多 worktree"模式已作废): 每个 AI 实例用**一份完整克隆**(独立 `.git`)隔离工作区, 分支名带 AI 标识 (如 `agentTrae/*`)。历史 worktree 目录已打包存档于 `D:/Projects/_archive/auto-qb-worktrees-2026-09-20/` (2026-09-20)。协作事项:
  - **只在自己的 clone 内改文件**, 不动别人的工作区; 各 clone 的 `.git` 互相独立 —— 提交/分支**不再**互相可见, 要看到别人的进展只能走远端 (这是与 worktree 模式最大的区别)。**跨仓库操作已升级为硬禁令、须用户显式说「授权」—— 完整定义见本文「🔴 跨仓库操作」节。**
  - **同步与汇合一律走远端主线**: 开工先 `git pull --rebase origin develop`; 交付按 `AGENTS.md`「提交 / PR」推 Gitee `develop`。**不自行 merge/rebase 其他 AI 的分支, 不擅自删除分支**, 分支汇合与旧工作区清理由用户统一协调; 任何合并前先确认自己工作区干净 (脏工作区会导致 merge 失败, 有前科)。
  - 多 AI 并行可能改到同一文件: 提交前在自己 clone 内跑全量测试保证自身改动自洽; 合并冲突交用户主导解决, 不擅自丢弃或覆盖他人改动。
  - 未被要求时**不主动 commit**; 被要求"提交"时按 `AGENTS.md`「提交 / PR」一次走完 (含推送), 不再把 commit 与 push 当成两次指令。
- **改完先留在工作区, 不自行提交**： AI 完成代码/文档改动后留在工作区由用户逐项审核; 用户说"提交"后才提交 —— 届时按 `AGENTS.md` 一次走完 (commit + 推 Gitee + 尝试 GitHub)。AI 不主动 `git commit` / `git push` 这一点不变, 变的是"提交"这两个字**包含**推送。
- **列计划时务必不要修改文件**： 用户在"先列计划/先给方案"阶段, AI 只输出方案文本(可含代码片段作为示例), **不修改任何工作区文件**, 必须等用户明确"实施/开始/按计划做"等指令才动文件。
- **更新代码/文档后同步更新知识库**： 每次功能新增/行为变更/重构完成后, 在同一次工作中同步更新 `memory-bank/` 知识库对应条目 (模块表 modules / 架构 systemPatterns / 规则系统 rule-system / 配置参考 config-reference / 陷阱 pitfalls / 路线图 progress / 测试基线 testing 与 README 速览), 不等用户单独提醒。
- **git 提交信息需规范详细**： 提交信息需完整描述改动内容与原因 (做什么 + 为什么/影响), 不用模糊短语 (如仅"修复"/"更新"); 多个逻辑改动拆分为独立提交, 每个提交自包含可回溯 —— **例外: 同一改动的知识库回写随主提交一并提交, 不单独成笔** (2026-09-22 定: 先回写再提交, 免得走两次流水线; 已推送不能 amend 强推, 事后只能补交)。**2026-09-22 起首行带一个 gitmoji 标意图** (格式见 `AGENTS.md`「提交 / PR」, emoji 全表见 `gitmoji skill` 的 `references/gitmoji-reference.md`)。
- **`skills/` 与 `instructions/` 是通用资产, 除显式指定外一律不改** (2026-09-20 用户指定):
  - **范围**: `.agents/skills/`(项目级技能事实源, 由 `scripts/sync_agent_skills.py` junction 到 `.codebuddy/skills` 供 IDE 扫描)、`.codebuddy/skills/`(链接层, 改了会被脚本覆盖)、`.github/instructions/`(Copilot 通用指令)、`.github/agents/`(子 agent 定义), 以及用户级 `~/.workbuddy-ai/skills/`。
  - **理由**: 这些是**跨项目复用**的通用技能/指令。往里写本仓库专属的事实(主线远端名、分支名、某个文件的字符上限、"该去读哪个配置文件")会让它们失真, 换个仓库就不可用。
  - **判别法**: 动笔前先问「这一行是本仓库的**事实**, 还是**通用机制**?」—— 事实一律留在项目侧(项目脚本 / `.commit-flow.toml` / `memory-bank/` / `AGENTS.md`), skill 与 instructions 只承载机制。**连"为本仓库新增的读取机制"也不该进 skill。**
  - **实例(同一天被纠正两次)**: 给"AGENTS.md 8000 字符上限"做提交闸门时, 先把 `{"AGENTS.md": 8000}` 硬编码进 skill 的 `_ship_config.py`; 改成"skill 去读外置 JSON"仍被否。最终闸门落在项目侧 —— 执行体 `scripts/check_context_caps.py`(上限写死), 触发挂 `.commit-flow.toml` 的 `[[gates]]`。
  - **例外**: 用户显式点名要改某个 skill / instruction 时照做; 新增**全新**的通用 skill 不在此限(但仍不得夹带本项目专属值)。

## 🔴 跨仓库操作: 绝对禁止 (2026-09-21 用户指定)

> **本条是跨仓库操作的完整定义**; `AGENTS.md`「🔴 跨仓库操作」节只留精简版与指针。背景: 工作区模式是**多 clone 并行**, 每个 clone 是一份**独立克隆**(各有自己的 `.git`)。

- **除当前这一个工作 clone 外, 对其它 clone 的任何写操作一律绝对禁止** —— 包括但不限于: 改文件、`git apply`、复制/覆盖文件、在它里面跑任何 git 命令(含 `git pull` / `git rebase` / `git checkout`)。
- **授权指令只认一个词: `授权`**, 且必须由用户**显式**说出。以下**一律不算授权**:
  「继续 / 接着做 / ok / 你看着办 / 提交 / 修复 / 同步一下 / 帮我弄好」。
  ⚠️ **「提交」只授权 commit + push 到远端, 不授权动别的 clone** —— 两者不要混为一谈。
- **未授权时的正确做法: 停下来问, 不要自己动手。** 典型场景: 发现"改动在那个 clone 上不生效"
  (比如用户的服务跑在另一个 clone 上) ⇒ 该如实报告并交由用户决定 —— 让用户自己 `pull`, 或等用户说出「授权」。
  **不能因为"不改就修不好"就自己 `git apply` / 复制文件过去。**
- **跨工作区同步一律走 Gitee `develop`**: 只动自己这个 clone → 提交推送 → 让对方 clone 自己拉取。**没有第二种路径。**
- **为什么是硬禁止**(2026-09-21 事故实证, 不是推演): 一次未经授权的跨仓库同步, 连带在对方 clone 里跑了
  `git pull --rebase` ⇒ 工具 shell 的 rebase 毁掉它的 `.git`(refs 目录消失 + 对象丢失,
  详见 [pitfalls](pitfalls.md)「`git rebase` 会毁 `.git`」条); 又因 rebase 被 SIGTERM 中断、
  工作区被 checkout 到中间状态, 事后留下 **13 个文件 / 648 行的残缺状态**需要清理。
  而同样的修复走 Gitee 只需一次提交。⇒ **代价不对称**: 走 Gitee 是零成本, 越界操作是"修一个问题、制造两个事故"。
- **配套纪律(越界已发生时的止损)**: rebase 中断后**工作区不可信**, 不要想当然用 `reset --mixed` 保留它 ——
  那会把残缺状态固定下来。正确做法是 `reset --hard <远端 tip>`(前提: 改动已入库或有仓库外备份)。

## 函数设计原则 (用户明示)

- **非必要不要过度设计函数默认参数**： 优先遵循调用点语义, 默认参数应反映最常见用法 (例如"全部参数无默认值, 调用方显式传"也是合法选择)。避免为追求"通用"而给所有参数加默认值, 反而隐藏调用语义、增加误用风险。
- **问题提早暴露， 禁用防御性掩盖** (2026-09-06): 数值/关键字段的 `x or 默认`、不可能为 None 的对象的 `is None` 守卫、恒有值属性的 `getattr(x, "attr", 默认)` —— 都会把上游 bug 静默转化为"合法语义", 且方向可能朝危险侧 (如 progress=None → 视为全新辅种 → 放行跳检)。规则:
  - 类型契约/初始化顺序已保证的字段 **直接访问**, 不加守卫 (异常早暴露调用路径错误)
  - `or 默认` 仅用于: 空串/空容器归一化 (category/tags/API 边界)、除零防护 (方向保守)、配置留空语义
  - **例外**方向判别: 掩盖后行为是"放行高风险动作"→ 必须删; "跳过可选动作"→ 可留

## 可测试性原则 (用户明示)

- **可以设计易测试的代码, 但不能为测试专门留通道** (2026-09-06): 依赖注入/必传参数等"易测试设计"必须由生产路径真实使用, 不得为测试保留生产不可达的可选形态。实例: QbApi 的 `store=None` 透明透传 —— 生产 QbManager 恒持有 store, 该形态只为让测试免建数据层而存在, 已移除 (store 改必传, 15 处 `if self.store is not None` 守卫删除, "无 store"系列测试删除, 测试改走生产同路径如 `make_manager` 的真实 store)。判别: 某分支/默认值在生产调用图中不可达、仅服务于测试绕过构建成本 → 删。
- **不要为了测试通过而修改生产代码!!** (2026-09-07): 测试失败时, 先判断是测试期望有误还是代码有 bug。若代码是有意为之 (如禁用某匹配模式), 则改测试适应代码, 而非改代码迁就测试。实例: `episodes.py` 的 bare number 匹配曾被有意注释禁用("可能会导致误判"), AI 为让测试通过而取消注释 —— 这是错误方向, 应改测试期望或与用户确认需求后再动代码。判别: 代码注释/docstring 说明了意图, 而测试期望与之冲突 → 改测试, 不改代码。

## 模块职责约定 (用户明示)

- **所有配置校验集中在 config 校验阶段 fail-fast, 插件类不再自查** (2026-09-06): conditions/actions 等插件假定配置正确 (`_validate_plugin_entry` 保证名称已注册 + `_PLUGIN_SPEC_VALIDATORS` 做 spec 深度校验), 构造函数只解析、不加正确性检查 (曾把 state 属性名校验写进 StateCondition, 违背该原则已迁移)。对应测试放 test_config.py (load_config 级), 不在插件测试里构造非法 spec。
- **新条件字段一律先进 `rules/expr/env.py`, 不再新增固定条件插件** (2026-09-20): 表达式条件 `expr` 落地后, 想按新的种子字段/额外值做判断, 在 `env.py` 的取值面加一个表项即可(名字 + 取值器 + 静态类型 + 昂贵标记), **不要**再走「新条件插件 + 校验 + schema + 前端」那套四处接线。旧 16 个条件冻结保留, 只修 bug 不加能力。取值面是单一事实源, schema/前端/文档都从它派生。

## 命名规范 (想法.md 明文规定, 代码严格遵守)

| 名字 | 含义 |
|------|------|
| `tor` | qbittorrentapi 的 `TorrentDictionary` 对象 (原始客户端对象) |
| `torrent` | 本项目 `TorrentRecord` 对象 (快照记录) |
| `hash` | 种子 hash 字符串 (不是 `torrent_hash`/`infohash`) |

其它惯用: `tq` = task_queue, `conf` = 配置对象, `ctx` = RuleContext, `task`/`origin` = 队列任务 (origin 指触发校验的规则任务), `tors` = TorrentDictionary 列表, `rec` = TorrentRecord, `handled`/`stop` = process 返回值, `_` 前缀 = QbManager 内部方法 (mixin 方法一律 `_` 开头)。

**计划外问题报告文件名** (create-issue skill, 2026-09-20): `<YY-MM-DD-HHMM>-<type>-<slug>.html` —— type 在文件名第二段, 取值 `bug` / `perf` / `docs` / `test` / `refactor` / `feat` / `chore` / `question`(枚举单点定义在 `.agents/skills/create-issue/scripts/_common.py` 的 `TYPES`)。档位由类型定: 便签档 `light`(docs / refactor / chore / question / test 缺口)只写现象+位置, 标准档 `standard`(bug / perf / feat / test 失败)才取证; 根因与建议修法一律可选, 默认"待查"。

## 类型注解 (来自 .github/instructions/py-type-lint.instructions.md)

1. 非必要不使用 `Any`。
2. 复合类型尽量精确 (`List[Task]`, `Dict[str, int]`, `Optional[X]`, tuple 字面量如 `("dlratio", 0.8)`)。
- 现状: 核心模块类型注解完善; 例外是 `RuleContext.manager: Any` 与 curves 的鸭子类型 points (有意为之, 避免循环导入/模块依赖, 保留注释说明)。
- Python 3.12 语法可用 (`X | Y` 联合, dataclass slots)。

## 性能约定 (来自 .github/instructions/perf.instructions.md)

先设计框架 (数据结构/算法) → 优化框架 → 再写代码 → 最后优化代码性能。**不在非热路径上过度优化**, 可读性与性能平衡。热路径 (每 tick/每种子执行): `_refresh_torrents`、条件 `match`、store 查询 — 这些地方用索引 (member_to_key O(1))、缓存 (惰性)、避免重复 API 调用; 冷路径 (配置加载、日志) 从简。

## 注释与文档字符串风格

- 全中文注释; docstring 常包含**设计动机/决策链/风险说明** (如 CheckAction 的 docstring 写完整决策链 0-4 步) — 这是本项目最重要的注释传统: 解释"为什么这样设计", 而非复述代码。
- 模块级 docstring 声明职责与依赖 (mixin 文件头声明依赖宿主的实例属性)。
- 关键不变量写在 docstring (如 "先登记成功再让位(顺序保证: 失败绝不 defer, 杜绝原任务永久让位)")。
## 日志规范 (2026-09-05 统一)

**骨架: `[上下文] {主体} | 事件: 详情`** —— 上下文与事件之间 ` | `,详情不含种子标识 (上下文已含):

| 类别 | 模板 | 使用处 |
|------|------|--------|
| 规则动作结果 | `规则[{name}] {log_repr} \| 动作[{action}] 成功/失败/等待异步/跳过: {详情}` | Rule.process 单通道输出 (动作不打自己的 INFO) |
| 内置维护 | `维护 {log_repr} \| {事件}: {详情}` | TagsMixin/tracker 限速 (_add_tags 等) |
| 任务调度 | `任务[{task.log_tag}] \| {事件}: {详情}` | qbmanager/taskqueue/rule_engine (log_tag = `kind:name[#hash8]`) |
| 分组事件 | `辅种组({n}个) \| {事件}: {详情}` | GroupingMixin |
| 系统级 | `{事件}: {详情}` (无前缀) | 启动/连接/曲线/导出/全局标签清理 |

- **种子标识唯一入口** = `torrent.log_repr` (`'name' [站点] (hash8)`); 仅种子已从客户端消失时退化为 `hash[:8]`
- **ActionResult.message = 纯详情** (不含动词与 log_repr, 例: `['HHan', 'seed-3D']`), 动作名由管线日志统一携带
- **等级**: DEBUG=例行检查 + skipped 动作; INFO=动作成功/状态变化; WARNING=回退/风险/数据异常; ERROR=未预期异常 (`exc_info=True` 保留, 运行期 bug 需要堆栈; 配置错误走 ConfigError 无堆栈)
- **全中文**; 默认 `log.format` 含 `%(name)s` (来源模块): `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- **凭据脱敏** (2026-09-22, issue 26-09-21-1408): 任何**可能内嵌凭据的 URL**(首当其冲是 tracker announce URL)进日志前必须过 `utils.sanitize_tracker_url()`, 只留主地址 `scheme://host[:port]`; **不按参数名黑名单剥** —— 私站凭据参数名是任意的(passkey 只是最常见的一种, 还有 authkey/token/uid 等), 黑名单每漏一个名字就漏一个站, 所以 path/query/fragment 整段丢弃。日志会落盘(含轮转备份)、可经 `/api/log` 读回, 且经通知联动(下条)直推系统通知, 泄露面远不止"读一次"
- **通知联动** (2026-09-12): `notify.enabled` 时 NotifyHandler 挂在 `auto_qb` logger 上, 达到 `notify.min_level` 的日志自动推送平台原生通知 —— 因此**日志级别/骨架即通知语义**, 新增 WARNING/ERROR 日志点无需单独接入通知; 免打扰时段与节流在 notify.py 过滤, 消息内容直接复用日志消息(遵守本骨架); `--tray` 模式下 UiLogHandler 同样直挂 `auto_qb` logger, 窗口日志视图实时跟随本骨架输出

## WEB UI 菜单/入口分层原则 (2026-09-17 用户明确要求记入)

右键菜单(及同类动作入口)按**使用频率**分两层, 不是按功能族平铺:

- **一级 = PT 日常高频动作**: 开始 / 暂停 / 强制汇报 / 详细信息 / 限速 / 移动 / 重命名 / 重新校验 / 导出 .torrent / 打开目标文件夹 / 删除。
- **次级菜单(flyout) = qB 通用低频能力**: 队列(置顶·上移·下移·置底) · 自动种子管理 · 超级做种 · 强制开始 · 分享率限制 → 「**更多操作**」(R10-14 由「高级能力」改名: 这些是 qB **常规**种子控制, 文案不该评价能力高低; 「更多操作」只表达层级, 后续增删子项也不会失准); 复制名称/哈希/magnet → 「复制」。
- **判据**: 该动作是否"每天都要点" —— 不是则下沉。菜单项数增长时**先问能否归入既有次级菜单**, 不要直接往一级追加。
- 实现: `.ctx-item.has-sub` + `.ctx-sub`(锚在父项右缘, 靠右时 `.flip-x` 向左翻); hover 与点击都能展开; 状态的唯一权威是 `app.js` 的 `subMenu`(随 `menu.visible` 关闭一并复位)。

## WEB UI 令牌分工 (2026-09-17 第十轮)

同名语义只允许有一个令牌族, 新增值先找族再考虑加令牌:

- **状态色族**(`--green/--blue/--error/--warn` + `--paused-*`): 表达**种子/行状态**。只染有语义的状态; 0 值/
  "—"占位不染; 芯片(站点/标签/分类)保持自身语义色不跟随行色(决策 D6-A —— 芯片表达**成员级**语义, 跟随行色会抹平这层信息)。
  `--paused` 是唯一"无色相"的成员, 取值 = `--fg-muted`(中性中间调), 配 `--paused-soft: transparent` + `--paused-line: var(--border-strong)`
  —— **暂停/其它一律"不铺底 + 中性描边"**, 不许落回 `--surface-2`(暗底 = 白 6%, 读作"太白/没颜色")。该族**两套 UI 各声明一处**
  (星图 `:root` / 棱镜 `themes/*.css` 五主题), 改值必须两处同改。
- **选中态族**(`--sel-bg/--sel-line/--sel-bar`, 五主题均取**非绿**的靖蓝族): 只用于"用户选中"语义; **不得**再引用
  `--accent`/`--accent-soft` —— 品牌主题(orbit)下 `--accent` 与做种 `--green` 同族且明度接近, 用户分不出"选中"与"做种"。
- **表面/底色族**: 状态栏用专用 `--statusbar-bg`(与页底形成可见层级); **不要改 `--glass`** —— 它同时管顶栏,
  改它会连带改顶栏。
- **尺寸族**: 弹窗宽度取 `--modal-w-narrow/base/form/add`/`--modal-wide-w`(两套 UI 同值同族); 新增弹窗只选档,
  不写新数字(这正是此前"第 N 次调大"的成因)。
- **单点口径原则(通用)**: 同一数据/口径在两个以上地方出现时, 收成 computed/method 单点(如 `speedLimitBytes`
  限速取数、`cellSeedingTime/cellRatio/cellPeers/cellAvailability/cellTime` 单元格口径、`_deleteDetails` 删除详情行、`colAlignCss` 列对齐),
  模板里只引用不重算。新增展示口径时先问"它是否已被别处实现"。

## 格式化 (yapf, .style.yapf)
- based_on_style=facebook, indent=4, column_limit=**120**, spaces_before_comment=2, split_before_logical_operator=false, allow_split_before_default_or_named_assigns=false
- 提交前对改动文件跑 `yapf -i <file>` (git 历史有独立的"格式化代码"提交)

## dataclass / 架构模式约定

- 配置项一律 dataclass (`@dataclass` + 类型注解), 常量默认值集中在 `config.py` 顶部 `DEFAULT_*`。
- 插件注册: 类级 `name` 属性 + `@register_condition`/`@register_action` 装饰器, `registry.py` 按名创建; 未知名抛 ValueError。
- 跨模块避免循环导入: `rules/base.py` 不 import QbManager (manager 以 `Any` 传入); `curves.py`/`episodes.py` 无项目内依赖。
- Facade模式: 业务代码**只**调 `self.api` (QbApi), 不直接用 raw client (例外: 数据层惰性缓存内部与测试)。
- 写后同步: 任何通过 QbApi 的写操作同步更新 store 快照; 新增写方法必须照此模式 (否则同 tick 内读到旧值)。

## dry_run 约定

- `dry_run` 逐层传递 (task.handler(task, dry_run) → execute(ctx.dry_run) → 各调用点)。
- 判定在**调用点**: `if not dry_run: api.xxx(...)`; QbApi Facade不感知 dry_run。
- dry-run 下动作仍返回 ActionResult (ok/skip), 但**不写** `record_execution` (条件: `not ctx.dry_run and ok_action`)。
- 分组/曲线等内置功能同样 dry_run 只打日志 (曲线 dry_run 还会跳过读当前值)。

## 幂等与去重约定 (设计原则 #1)

- 动作天然幂等: 先查后做 (标签已存在→skip, 状态相同→skip, 限速相同→skip)。
- 窗口语义 (每天一次) → `record_execution`/`get_exec_record` (state_file), 键 `{rule}:{hash}`。
- **不能**用 run_count/循环次数表达窗口语义。

## Git 约定 (观察自 git log)

- **开工前先同步分支 (2026-09-19 用户指定)**: 会话第一步必为 `git pull --rebase <远端> develop` (**分支名必须写**, 只给远端名会只 fetch 不合并), `git status -sb` 确认不落后才动手; **禁止在落后的分支上改代码**; 拉取前先把工作区弄干净 (脏工作区 + rebase 触发 stash 会损坏对象库)。细则见 `AGENTS.md`「会话协议 · 开始」与「提交 / PR」—— 该规则共有 4 处入口 (`AGENTS.md` / `.github/copilot-instructions.md` / `.agents/skills/memory-bank/SKILL.md` / `.github/instructions/ai-lib.md`), **改规则必须一次改全**, 本文件只留指针不复述。
- **push 口径单点定义在 `AGENTS.md`「提交 / PR」** (2026-09-19 起: "提交" = commit + 推送)。本文件不复述, 免得第三次漂移。
- 分支: `develop` 开发 (协作主线, 统一以 Gitee 的 `develop` 为准), `master` 主干。
- 提交信息: **格式单点定义在 `AGENTS.md`「提交 / PR」**(2026-09-22 起为 **gitmoji + 中文**: 首行 `<gitmoji> <中文一句话概述>` + 空行 + 详细描述); 本文件不复述。选 emoji 走 [gitmoji skill](.agents/skills/gitmoji/SKILL.md)。
- 格式化可单独成提交 ("格式化代码"/"格式化测试代码")。
- 用户未要求时不主动 commit; 要求"提交"时按 `AGENTS.md` 一次走完 (含推送)。

## 提交闸门自动执行 (2026-09-22 实施)

- **命令固定就标 `auto = true`** —— 由预检**真的执行**, 红了即 STOP(退出码 1); 只有需要人读输出做判断的才留 `auto = false`(只打印)。判据: 闸门存在的意义是不让步, 执行权留在记忆里等于没装。
- **占位符由预检展开**: `<root>` / `<skill-dir:NAME>` / `<changed:GLOB>` / `<each:GLOB>`; 展开不了即 **STOP, 不降级成打印**(降级 = "看起来跑过了")。自造占位符不会被猜。
- **未知键 / `timeout` 非法 → STOP**: 闸门很贵, 拼错键让它静默失效比报错坏得多。代价: 新增配置键必须先加进 `KEY_DEFAULTS` / `GATE_KEYS`。
- **测试跑两次, 不是一次**: ① 改完代码、**回写知识库之前** ② `commit.py` 内部提交前。第一次必须在回写之前 —— 测试带文档守卫(会读 `memory-bank/`), 回写后跑会分不清红的是代码还是文档。S6 推送前由 `push.py` 内嵌 `--no-auto` 只核状态(脏 / 上游 / 红线 / 镜像), 不跑闸门。
- **格式化类闸门必须在逐路径暂存之前**: 格式化会让已 staged 文件与 index 不一致, 必须重新 `add`。
- 字段与占位符的**机制**见 `my-commit-flow` skill 与其 `scripts/test_preflight.py`(23 用例); 本仓库的**取值**在 `.commit-flow.toml`; 设计取舍见 `docs/plans/26-09-22-0812-commit-gate-auto-run-plan.html`。

## 禁止用生产配置启动程序(2026-09-13, AI 越界实例)

- **🔴 绝对禁止以生产 `config.yml` 或生产 `auto-qb-data/` 启动程序**(含间接形式: 无参数启动 = 默认加载生产 config.yml)
- 违规后果: AI 启动的实例会在真实数据上执行管理动作(打标签/清理标签/HR 打标/限速), 占用单实例锁致用户无法启动, 并可能误杀用户实例
- **运行验证一律使用独立临时配置 + 独立 data_dir**(在 `R:/Temp/auto-qb/run-<名>/` 下自建 yml 与 data 目录, 用后清理 —— 临时目录统一走 R 盘, 见 [techContext.md](techContext.md)「临时目录 / 备份盘约定」)
- 生产环境的启动/停止/验证**仅由用户本人执行**; AI 需要用户提供日志或观察结果

## HTML 文档一律 dark 主题 (2026-09-20 用户指定)

- **适用**: 所有产出的单文件 HTML —— 计划文档 / issue 报告 / 交付物 / 演示页。**一律深色底 + 浅色字, 禁止浅底黑字**。
- **配色口径**: `--bg` / `--paper` 亮度 ≈ `#0f…`~`#18…`, `--ink` 亮度 ≥ `#d8…`; 样式里**必须**写 `color-scheme: dark` —— 缺这条, 浏览器原生滚动条与表单控件不会跟着变深。
- **存量**: `docs/plans/` 25 份与 `memory-bank/issues/` 9 份已全部深色; 新产出若不是深色即为违规。
- **例外**: `resources/`(ui-component-libraries 设计观摩稿 + settings-page-templates 候选稿)**不套用** —— 那批白底极简(kenya-hara / pentagram / muller-brockmann)是设计本体。⚠ 遇到"统一主题"类要求, 先分清**交付物 vs 参考素材**, 别一把梭。
- **命名**: 放 `docs/plans/` 时命名 `YY-MM-DD-HHMM-<slug>.html`, 日期时间**用命令取当前值**, 不靠记忆。

## 其它工程约定

- `pytest.ini` 的 addopts 自带 `--cov=src --cov-report=term-missing --cov-branch`: 直接 `pytest` 即带覆盖率。
- `.gitignore` 覆盖: config 类 (test.yml/torrents.txt)、覆盖率 (`.coverage` / `.coverage.*`); 运行时数据整目录 `auto-qb-data/` 忽略 (内含 `state.json` 状态、`state.lock`/`state.lock.meta.json` 单实例锁、`logs/auto-qb.log` 日志、`skip-check-backup/` 跳检备份)。**注意 `config.yml`/`minimal.yml` 受 git 跟踪且未忽略** —— config.yml 含真实站点凭据, 靠"勿改勿提交"约定保护 (见 08), 不是 gitignore。
- 包内 `logging.py` 与 stdlib 同名: 包内一律 `from .logging import setup_logging`, stdlib 用绝对 `import logging` (Python3 绝对导入默认, 无冲突, 但不要改成相对导入写法)。
- Windows 兼容: 文件操作过 `utils.add_long_path_prefix_for_win` (支持 >260 字符路径); 路径正斜杠化。
