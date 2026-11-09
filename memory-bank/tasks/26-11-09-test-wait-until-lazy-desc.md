# 26-11-09-test-wait-until-lazy-desc — wait_until 惰性 desc 基座改造(修复 issue 26-11-08-0044)

**Status:** In Progress
**Added:** 2026-11-09
**Updated:** 2026-11-09
**Summary:** tests-real 9 份 wait_until 基座 desc 加惰性 callable 支持 + 19 处活值 f-string desc 调用点改传 lambda, 超时报错不再显示等待前旧值
**Topics:** test-wait-until-lazy-desc
**Refs:** memory-bank/issues/26-11-08-0044-test-tests-clock-wait-until-desc-eager.html

## 本篇只回答

「tests-real 的 wait_until desc 为什么/怎么改成惰性求值, 改了哪些点」—— 单题档案, 不覆盖单测侧 tests/clock.py(无 desc 参数, 无此缺陷)。

## 原始请求

1. 用户: 「修复memory-bank/issues/26-11-08-0044-test-tests-clock-wait-until-desc-eager.html」—— issue 内容: wait_until 的 desc 调用期求值, 调用点拼 f-string 带「最后观测值」显示调用前旧值(RM07-11 首版踩过); 建议基座加惰性 desc(callable 支持)。

## 思考过程与决策

- **位置更正**: issue 原报位置 `tests/clock.py` 有误 —— 该文件 wait_until 无 desc 参数, 调用点消息由 assert 承载(assert 消息表达式失败时才求值, 天然惰性); 真实缺陷在 tests-real/rm*/ 下 9 份复制的 `wait_until(fn, timeout, desc: str, interval)`(8 标准 + rm06 异常容忍变体; rm04_relocate_visibility 经 `M.wait_until` 复用)。复验后已在 issue §02 更正。
- **修法与 issue 建议同向**: ① 9 份基座 `desc: str | Callable[[], str]`, 报错行 `{desc() if callable(desc) else desc}` —— str 调用点零漂移; ② 活值调用点(f-string 插值内嵌调用)改传 lambda。
- **扫描口径**: AST 全量 193 处调用点分类; 活值判别要**递归深扫**(f-string 内任意深度出现 Call), 首轮顶层判别漏列表推导 1 处(rm04:1735), 评审抓出后补转并深扫复查(仅剩刻意豁免点 rm10 `sorted(want)` 纯局部值)。
- **范围守恒**: 静态值 f-string(ih[:8]/path 等不可变量)不动; 既有 HEAD 超宽 assert 行不碰; rm10 纯值点豁免(转了也无害但不 churn)。
- **机械改写踩坑**: AST col_offset 切片在含 CJK 行错位(end_col_offset 偏一位) —— 回滚重做, 改用 `ast.get_source_segment` 定位; 已入坑档 `pitfalls/testing/ast-migration-fidelity.md` 第 4 条。

## 实现计划

总体思路(单批完成): 基座惰性化(9 份同款机械编辑, 严格匹配计数断言) → 活值调用点 lambda 化(AST 定位) → py_compile + 惰性行为自证 → issue 翻 Done 补修法 → 评审两轮 → 收尾回写。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 9 份 wait_until 基座加惰性 desc(callable 超时才求值) | Done(2026-11-09) |
| 2 | 19 处活值 f-string desc 调用点改传 lambda(含评审抓出的 rm04:1735) | Done(2026-11-09) |
| 3 | py_compile 9 文件 + 惰性行为自证(str/callable/快路径零求值三态) | Done(2026-11-09) |
| 4 | issue 0044 翻 Done + 位置更正 + 实际修法/验证方式 | Done(2026-11-09) |
| 5 | 评审两轮(基哈希 ba69820ed4d1 → 6fe51c1d557c, 修复轮零 actionable) | Done(2026-11-09) |
| 6 | 收尾回写(real-machine.md §09 约定 + 坑档第 4 条 + 基线切片) | Done(2026-11-09) |

## 进度日志

### R0 · 立档 (2026-11-09)

- 修复批全绿(数字单点见基线切片 `testing/baselines/26-11-09-2304-wait-until-lazy-desc.md`)。
- review: 批 168 行(基 f4221c14), 轮 2, 检 2/2, blocker 0, 修 1(rm04:1735 漏转), 入池 0。
- 待办: 提交待用户显式指令(AGENTS.md 提交口径)。

- 2026-11-09 23:08 修复 issue 26-11-08-0044: tests-real 9 份 wait_until 基座 desc 惰性 callable 支持 + 19 处活值调用点改 lambda; 评审两轮零 actionable; test.full 全绿(基线切片 26-11-09-2304); 收尾回写 real-machine.md/坑档/基线切片/任务档案齐
