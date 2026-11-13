# .py 注释/docstring 里的带圈数字撞 ASCII 符号守卫(评审快照后修必触发复评轮)

> 摘要: 写 .py 文件(代码注释/测试 docstring)时从计划/文档顺手抄 ①②③ 类带圈数字, test_ascii_symbol_guard 即红(冻结表只拦新增, circled 类冻结 0); 若发生在评审快照之后, 修复本身构成新 diff, 强制多走一轮复评
> 触发: 计划编号带圈数字, S4③, 注释抄计划, 带圈数字, circled, test_ascii_symbol_guard 红, 评审快照后修守卫红, docstring 测试计划

### 写 .py 注释前把计划节号改写成 ASCII 形态 —— 评审派发前先跑会拦新增符号的守卫

- **触发**: 给 .py 文件写注释/docstring(尤其测试文件头部「## 测试计划」清单同步)时, 从计划/issue HTML 里照抄编号与符号 —— 计划文档里合法的 ①②③(HTML 交付物可用图形符号)进 .py 就是违规(代码/配置禁 emoji 与图形符号, 冻结表对 circled 类冻结 0)。
- **判别**: `commands run test.quick`(或 test.full)红在 `tests/test_ascii_symbol_guard.py`, 报文给出行与符号类(如「circled 实测 2 > 冻结 0」); 单独写新 .py 时也常见于提交闸门 test.quick 预跑。注意与坑档 `frozen-allowlist-baseline-drift` 的「预存判红」区分: 那是别批提交引入未登记符号导致的无关判红, 本坑是自己刚写的符号被正常拦截。
- **处置**: 注释里的节号一律写 ASCII 形态(如 `S4-3` 代替 `S4③`), 语义不变; **时序纪律**(2026-11-14 dt-live-update 轮已留痕, 本轮复发实证): 凡要派评审的批次, 派发**前**先跑会拦新增符号的守卫 —— 评审快照后再修守卫红, 修复增量照 code-review skill ⑤ 扳机强制复评一轮, 平白多花一轮评审成本。
- **复发**: 1 (2026-11-14, 计划 26-11-14-0001 T1): 测试 docstring 写「S4③」被拦, 改「S4-3」复跑绿。**为何没命中**: dt-live-update 轮的教训只写在 active-context 切片(26-11-14-0006)里, 没有立坑档, 检索路由不到 —— 本次立档补上。同日 T4 再次命中(docstring ①②), 改 S4-1/S4-2 形态后绿, 证明切片留痕不足以内化成动作, 坑档+派发前预跑才是根治。
