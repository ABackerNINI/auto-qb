# .py 注释/docstring 里的带圈数字撞 ASCII 符号守卫(评审快照后修必触发复评轮)

> 摘要: 写 .py 文件(代码注释/测试 docstring)时从计划/文档顺手抄 ①②③ 类带圈数字, test_ascii_symbol_guard 即红(冻结表只拦新增, circled 类冻结 0); 若发生在评审快照之后, 修复本身构成新 diff, 强制多走一轮复评
> 触发: 计划编号带圈数字, S4③, 注释抄计划, 带圈数字, circled, test_ascii_symbol_guard 红, 评审快照后修守卫红, docstring 测试计划

### 写 .py 注释前把计划节号改写成 ASCII 形态 —— 评审派发前先跑会拦新增符号的守卫

- **触发**: 给 .py 文件写注释/docstring(尤其测试文件头部「## 测试计划」清单同步)时, 从计划/issue HTML 里照抄编号与符号 —— 计划文档里合法的 ①②③(HTML 交付物可用图形符号)进 .py 就是违规(代码/配置禁 emoji 与图形符号, 冻结表对 circled 类冻结 0)。
- **判别**: `commands run test.quick`(或 test.full)红在 `tests/unit/test_ascii_symbol_guard.py`, 报文给出行与符号类(如「circled 实测 2 > 冻结 0」); 单独写新 .py 时也常见于提交闸门 test.quick 预跑。注意与坑档 `frozen-allowlist-baseline-drift` 的「预存判红」区分: 那是别批提交引入未登记符号导致的无关判红, 本坑是自己刚写的符号被正常拦截。
- **处置**: 注释里的节号一律写 ASCII 形态(如 `S4-3` 代替 `S4③`), 语义不变; **时序纪律**(2026-11-14 dt-live-update 轮已留痕, 本轮复发实证): 凡要派评审的批次, 派发**前**先跑会拦新增符号的守卫 —— 评审快照后再修守卫红, 修复增量照 code-review skill ⑤ 扳机强制复评一轮, 平白多花一轮评审成本。
- **复发**: 1 (2026-11-14, 计划 26-11-14-0001 T1): 测试 docstring 写「S4③」被拦, 改「S4-3」复跑绿。**为何没命中**: dt-live-update 轮的教训只写在 active-context 切片(26-11-14-0006)里, 没有立坑档, 检索路由不到 —— 本次立档补上。同日 T4 再次命中(docstring ①②), 改 S4-1/S4-2 形态后绿, 证明切片留痕不足以内化成动作, 坑档+派发前预跑才是根治。
- **复发**: 2 (2026-11-18, 计划 26-11-18-0259 S2 守阵批): `scripts/ui_harness.py` docstring 写自拟列举序号 ①② 被拦, 改 (a)/(b) 复跑绿(证据: 档案 `tasks/26-11-18-webui-boot-first-data.md` R3; 现文 _FileEntry docstring 即 (a)/(b) 形态)。**为何没命中**: 把坑面窄化成「抄计划的节号 S4③」—— 这轮写的是自拟列举序号, 没意识到「.py 内禁一切图形符号」对自拟序号同样生效; 「派发前先预跑守卫」的时序纪律也没执行, 守阵跑时才拦下(批内改绿, 侥幸未进评审快照, 免了一轮复评)。
- **复发**: 3 (2026-11-20, relocate 探测异步化第二批 T3): 实施子代理把计划里的圈号抄进 .py 注释, `test_ascii_symbol_guard` 批内拦下, 改 ASCII 形态后绿(证据: 提交 8f129b47 产物 `tests/unit/test_relocate_probe_consume.py` docstring 现文列举序号即 (1)(2)(3)(4) 形态); 批内拦截未进评审快照, 未产生复评成本。**为何没命中**: 实施子代理扫了 pitfalls/_index 但没打开该条目再动笔, 守卫批内拦截。
