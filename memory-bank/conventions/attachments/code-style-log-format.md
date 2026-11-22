# 代码风格细则: 日志规范与格式化

> 摘要: `conventions/code-style.md` 的日志规范(骨架 · 等级 · 通知联动 · 种子标识)与格式化(yapf)细则 —— 整节逐字外迁, 本节是该主题的现行权威。
> 触发: 日志, 日志骨架, 日志等级, 通知联动, 种子标识, yapf, 格式化, dev.fmt

## 日志规范 (2026-09-05 统一)

**骨架: `[上下文] {主体} | 事件: 详情`** —— 上下文与事件之间 ` | `,详情不含种子标识 (上下文已含):

| 类别 | 模板 | 使用处 |
|------|------|--------|
| 规则动作结果 | `规则[{name}] {log_repr} \| 动作[{action}] 成功/失败/等待异步/跳过: {详情}` | Rule.process 单通道输出 (动作不打自己的 INFO) |
| 内置维护 | `维护 {log_repr} \| {事件}: {详情}` | MaintenanceModule/TrackerModule(维护与限速, plan P3) |
| 任务调度 | `任务[{task.log_tag}] \| {事件}: {详情}` | qbmanager/taskqueue/rule_engine (log_tag = `kind:name[#hash8]`) |
| 分组事件 | `辅种组({n}个) \| {事件}: {详情}` | GroupingModule |
| 系统级 | `{事件}: {详情}` (无前缀) | 启动/连接/曲线/导出/全局标签清理 |

- **种子标识唯一入口** = `torrent.log_repr` (`'name' [站点] (hash8)`); 仅种子已从客户端消失时退化为 `hash[:8]`
- **ActionResult.message = 纯详情** (不含动词与 log_repr, 例: `['HHan', 'seed-3D']`), 动作名由管线日志统一携带
- **等级** (2026-09-27 收窄, 单点口径): DEBUG=例行检查 + skipped 动作; INFO=动作成功/状态变化 + **用户操作审计/生命周期告知**; WARNING=**纯排障** (可自愈降级/重试中/保护性动作/性能细节 —— 值得 grep 不值得弹窗); ERROR=**真正危险** (数据丢失/状态写盘失败/任务停摆需人工/认证失败/未预期异常 —— `exc_info=True` 保留, 运行期 bug 需要堆栈; 配置错误走 ConfigError 无堆栈)。判别口诀「弹窗测试」: 这条出现时用户需立刻放下手头的事 → ERROR; 只是排查问题时想 grep 到 → WARNING; 事后审计想留痕 → INFO。定级单点: `memory-bank/plans/26-09-27-1126-plan-log-level-notify-error.html` 表 A–D。
- **全中文**; 默认 `log.format` 含 `%(name)s` (来源模块): `%(asctime)s [%(levelname)s] %(name)s: %(message)s`

> 已外迁: 凭据脱敏(越界即脱敏 · 日志/外发两个单点 · R1/R6 铁律 · 守阵①~⑤) → [code-style-examples.md](code-style-examples.md)

- **通知联动** (2026-09-12; 2026-09-27 默认改 ERROR): `notify.enabled` 时 NotifyHandler 挂在 `auto_qb` logger 上, 达到 `notify.min_level` 的日志自动推送平台原生通知 —— 因此**日志级别/骨架即通知语义**, 新增 ERROR 日志点无需单独接入通知; **min_level 默认 ERROR**, 即默认只有真正危险才弹窗, WARNING 仅排障 (想看时把 min_level 调低); 免打扰时段与节流在 notify.py 过滤, 消息内容直接复用日志消息(遵守本骨架); `--tray` 模式下 UiLogHandler 同样直挂 `auto_qb` logger, 窗口日志视图实时跟随本骨架输出

## 格式化 (yapf, .style.yapf)
- based_on_style=facebook, indent=4, column_limit=**120**, spaces_before_comment=2, split_before_logical_operator=false, allow_split_before_default_or_named_assigns=false
- 提交前对改动文件跑 `commands run dev.fmt -- <file>`

