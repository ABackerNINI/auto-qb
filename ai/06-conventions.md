# 06 编码规范与项目约定

## 协作约定 (用户明示)

- **修改完不要直接提交**： AI 完成代码/文档改动后留在工作区，由用户逐项审核，确认后再由用户或显式要求时再提交。AI 不主动 `git commit` / `git push`。
- **列计划时务必不要修改文件**： 用户在"先列计划/先给方案"阶段, AI 只输出方案文本(可含代码片段作为示例), **不修改任何工作区文件**, 必须等用户明确"实施/开始/按计划做"等指令才动文件。
- **更新代码/文档后同步更新知识库**： 每次功能新增/行为变更/重构完成后, 在同一次工作中同步更新 `ai/` 知识库对应条目 (模块表 03 / 架构 02 / 规则系统 04 / 配置参考 05 / 陷阱 08 / 路线图 09 / 测试基线 07 与 README 速览), 不等用户单独提醒。
- **git 提交信息需规范详细**： 提交信息需完整描述改动内容与原因 (做什么 + 为什么/影响), 不用模糊短语 (如仅"修复"/"更新"); 多个逻辑改动拆分为独立提交, 每个提交自包含可回溯。

## 函数设计原则 (用户明示)

- **非必要不要过度设计函数默认参数**： 优先遵循调用点语义, 默认参数应反映最常见用法 (例如"全部参数无默认值, 调用方显式传"也是合法选择)。避免为追求"通用"而给所有参数加默认值, 反而隐藏调用语义、增加误用风险。

## 命名规范 (想法.md 明文规定, 代码严格遵守)

| 名字 | 含义 |
|------|------|
| `tor` | qbittorrentapi 的 `TorrentDictionary` 对象 (原始客户端对象) |
| `torrent` | 本项目 `TorrentRecord` 对象 (快照记录) |
| `hash` | 种子 hash 字符串 (不是 `torrent_hash`/`infohash`) |

其它惯用: `tq` = task_queue, `conf` = 配置对象, `ctx` = RuleContext, `task`/`origin` = 队列任务 (origin 指触发校验的规则任务), `tors` = TorrentDictionary 列表, `rec` = TorrentRecord, `handled`/`stop` = process 返回值, `_` 前缀 = QbManager 内部方法 (mixin 方法一律 `_` 开头)。

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

- 分支: `develop` 开发, `master` 主干 (PR 目标)。
- 提交信息: 中文单行, 动词开头描述行为 (如 "修复跳检动作删除种子导致该种子后续动作/任务报错"、"补充 cov 缺口测试: ...")。
- 格式化可单独成提交 ("格式化代码"/"格式化测试代码")。
- 用户未要求时不主动 commit/push。

## 其它工程约定

- `pytest.ini` 的 addopts 自带 `--cov=src --cov-report=term-missing --cov-branch`: 直接 `pytest` 即带覆盖率。
- `.gitignore` 覆盖: config 类 (test.yml/torrents.txt)、日志、覆盖率、`skip-check-backup/`、`.github/instructions/`; `logs/auto-qb-state.json` 及其锁文件 `*.lock`/`*.lock.meta.json` 也在 gitignore 内。
- 包内 `logging.py` 与 stdlib 同名: 包内一律 `from .logging import setup_logging`, stdlib 用绝对 `import logging` (Python3 绝对导入默认, 无冲突, 但不要改成相对导入写法)。
- Windows 兼容: 文件操作过 `utils.add_long_path_prefix_for_win` (支持 >260 字符路径); 路径正斜杠化。
