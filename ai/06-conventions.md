# 06 编码规范与项目约定

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
- 日志: 中文 + `{torrent.log_repr}` (格式 `'{name}' [{tracker_name}] ({hash前8位})`), f-string, 级别: DEBUG=每轮常规检查, INFO=动作/状态变化, WARNING=风险/异常回退, ERROR=任务异常 (带 `exc_info=True`)。

## 格式化 (yapf, .style.yapf)

- based_on_style=facebook, indent=4, column_limit=**120**, spaces_before_comment=2, split_before_logical_operator=false, allow_split_before_default_or_named_assigns=false
- 提交前对改动文件跑 `yapf -i <file>` (git 历史有独立的"格式化代码"提交)

## dataclass / 架构模式约定

- 配置项一律 dataclass (`@dataclass` + 类型注解), 常量默认值集中在 `config.py` 顶部 `DEFAULT_*`。
- 插件注册: 类级 `name` 属性 + `@register_condition`/`@register_action` 装饰器, `registry.py` 按名创建; 未知名抛 ValueError。
- 跨模块避免循环导入: `rules/base.py` 不 import QbManager (manager 以 `Any` 传入); `curves.py`/`episodes.py` 无项目内依赖。
- 门面模式: 业务代码**只**调 `self.api` (QbApi), 不直接用 raw client (例外: 数据层惰性缓存内部与测试)。
- 写后同步: 任何通过 QbApi 的写操作同步更新 store 快照; 新增写方法必须照此模式 (否则同 tick 内读到旧值)。

## dry_run 约定

- `dry_run` 逐层传递 (task.handler(task, dry_run) → execute(ctx.dry_run) → 各调用点)。
- 判定在**调用点**: `if not dry_run: api.xxx(...)`; QbApi 门面不感知 dry_run。
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
- `.gitignore` 覆盖: config 类 (test.yml/torrents.txt/auto-qb-state.json)、日志、覆盖率、`skip-check-backup/`、`.github/instructions/`。
- 包内 `logging.py` 与 stdlib 同名: 包内一律 `from .logging import setup_logging`, stdlib 用绝对 `import logging` (Python3 绝对导入默认, 无冲突, 但不要改成相对导入写法)。
- Windows 兼容: 文件操作过 `utils.add_long_path_prefix_for_win` (支持 >260 字符路径); 路径正斜杠化。
