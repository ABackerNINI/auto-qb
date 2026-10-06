# 日期靠手写 + 守卫只查形状: 约定写了等于没写

> 摘要: 「时间戳用命令取当前值」这条约定写了两处, 但那条命令**根本不存在** —— 日期实际全是 agent 按会话上下文手敲的(未来时间与错体例由此而来); 而守卫只查文件名的**形状**, 不查**值**。
> 触发: 日期不准, 未来日期, 时间戳, 文件名日期, 最后活动, doc-added, 时间体例, 取时命令

**Refs:** memory-bank/tasks/26-09-30-memory-bank-timekit.md

## 约定写了但不可执行 = 没写

### 「用命令取当前值」的约定下, 那条命令并不存在

- **触发**: 文档/约定里反复写「时间戳用命令取当前值」, 但没人真去跑那条命令 —— 去 `.commands/` 全包 grep 取时命令, **0 命中**。
- **判别**: 一条约定若**没有可执行的落点**(真命令 / task id), agent 只能回退到"按上下文推算" —— 系统提示里的日期、记忆、推断, 哪个都能写进去, 于是文件名与正文出现未来时间、体例各写各的。判据: 约定里的动词(取/跑/执行)**能不能一字不差地照做**; 不能 ⇒ 这条约定是空话。
- **处置**: 把约定落成**真命令** —— `timekit.py`(UTC+8 钉死) + 收录 task `commands run kb.time`(date / time / stamp); 约定文案改写成「一律取自 `commands run kb.time` 的输出」, 并在会话开始 / 收尾 / 档案规范三处挂钩(决策点上触达)。时区必须**与机器无关**(`datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)`, naive UTC+8 墙钟 —— 全库既有解析是 naive, 别混 aware), 否则换台非 +08 的机器就产出错值。
- **守阵**: `tests/test_memory_bank.py::test_timekit_now_is_utc_plus_8_naive`

### 守卫只查形状不查值 ⇒ 坏值永远不红

- **触发**: `tests/test_memory_bank.py` 校验文件名的**形状**、章节结构、索引一致性, 但**不校验任何日期值**; `gen_active_recent.parse_last_active` 对格式坏的「最后活动」`strptime` 失败后**静默回退**文件名时间。
- **判别**: 判据分两层 —— ①**形状**(定宽前缀、三字段) 与 ②**值**(合法日期、不晚于当前、体例统一)。只守①时, 坏值被吞掉: 排序键静默换成创建时间、错体例一路进库, 而守卫全程绿。
- **处置**: `timekit.py check` 三层守卫 —— 文件名(tasks `YY-MM-DD` / 切片与 HTML 制品 `YY-MM-DD-HHMM`)与元数据(`Added` / `Updated` / `最后活动` / `doc-added` / `doc-updated`)查「合法 + 非未来」, 正文只查体例(规范 token 不查未来, 可合法引用未来日程); 挂 `kb.check` 与提交闸门。`gen_active_recent` 区分「缺失」(按设计回退)与「存在但格式坏」(报红)。
- **判据**: **过去日期的错值兜不住**(无真值可比), 只能靠「只从 kb.time 取」的流程规避; 正文的机器数据(路径 / 代码块里的 8 位数字)用边界与代码上下文跳过 —— 别把 `audit-20260921/` 这类目录名当日期 token。
- **守阵**: `tests/test_memory_bank.py::test_timekit_guards_catch_three_layers` / `test_timekit_body_ignores_code_and_paths` / `test_timekit_check_is_green_on_current_kb`
