# 代码风格与设计约定

> 摘要: 函数设计 / 可测试性 / 模块职责 / 命名 / 类型注解 / 性能 / 注释 / 日志 / 格式化 / dataclass / 其它工程约定。
> 触发: 命名, 类型注解, 函数设计, 可测试性, 模块职责, 注释, 日志, 格式化, yapf, dataclass

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
- **通知联动** (2026-09-12): `notify.enabled` 时 NotifyHandler 挂在 `auto_qb` logger 上, 达到 `notify.min_level` 的日志自动推送平台原生通知 —— 因此**日志级别/骨架即通知语义**, 新增 WARNING/ERROR 日志点无需单独接入通知; 免打扰时段与节流在 notify.py 过滤, 消息内容直接复用日志消息(遵守本骨架); `--tray` 模式下 UiLogHandler 同样直挂 `auto_qb` logger, 窗口日志视图实时跟随本骨架输出

## 格式化 (yapf, .style.yapf)
- based_on_style=facebook, indent=4, column_limit=**120**, spaces_before_comment=2, split_before_logical_operator=false, allow_split_before_default_or_named_assigns=false
- 提交前对改动文件跑 `yapf -i <file>` (git 历史有独立的"格式化代码"提交)

## dataclass / 架构模式约定

- 配置项一律 dataclass (`@dataclass` + 类型注解), 常量默认值集中在 `config.py` 顶部 `DEFAULT_*`。
- 插件注册: 类级 `name` 属性 + `@register_condition`/`@register_action` 装饰器, `registry.py` 按名创建; 未知名抛 ValueError。
- 跨模块避免循环导入: `rules/base.py` 不 import QbManager (manager 以 `Any` 传入); `curves.py`/`episodes.py` 无项目内依赖。
- Facade模式: 业务代码**只**调 `self.api` (QbApi), 不直接用 raw client (例外: 数据层惰性缓存内部与测试)。
- 写后同步: 任何通过 QbApi 的写操作同步更新 store 快照; 新增写方法必须照此模式 (否则同 tick 内读到旧值)。

## 其它工程约定

- `pytest.ini` 的 addopts 自带 `--cov=src --cov-report=term-missing --cov-branch`: 直接 `pytest` 即带覆盖率。
- `.gitignore` 覆盖: config 类 (test.yml/torrents.txt)、覆盖率 (`.coverage` / `.coverage.*`); 运行时数据整目录 `auto-qb-data/` 忽略 (内含 `state.json` 状态、`state.lock`/`state.lock.meta.json` 单实例锁、`logs/auto-qb.log` 日志、`skip-check-backup/` 跳检备份)。**注意 `config.yml`/`minimal.yml` 受 git 跟踪且未忽略** —— config.yml 含真实站点凭据, 靠"勿改勿提交"约定保护 (见 08), 不是 gitignore。
- 包内 `logging.py` 与 stdlib 同名: 包内一律 `from .logging import setup_logging`, stdlib 用绝对 `import logging` (Python3 绝对导入默认, 无冲突, 但不要改成相对导入写法)。
- Windows 兼容: 文件操作过 `utils.add_long_path_prefix_for_win` (支持 >260 字符路径); 路径正斜杠化。
