# test-legacy-review4-scripts-fix

> 摘要: R4 scripts 修复批收尾: test.full/test.pkg 全绿入基线切片(见 kb.baseline), 立档 tasks/26-11-07-test-legacy-review4-scripts-fix.md, 坑档双向处置(console-encoding 复发+1 / 新立 inproc-server-conn-abort), 回写判断=零回写; 待办: issues/_index 超预算待清理 + 4 件 26-11-07-1216 issue 待认领
> 最后活动: 2026-11-07 12:46
**Refs:** memory-bank/tasks/26-11-07-test-legacy-review4-scripts-fix.md, memory-bank/testing/baselines/26-11-07-1248-test-legacy-review4-scripts-fix.md

**R0(2026-11-07 12:46):** R4 scripts 修复批收尾: test.full/test.pkg 全绿入基线切片(见 kb.baseline), 立档 tasks/26-11-07-test-legacy-review4-scripts-fix.md, 坑档双向处置(console-encoding 复发+1 / 新立 inproc-server-conn-abort), 回写判断=零回写; 待办: issues/_index 超预算待清理 + 4 件 26-11-07-1216 issue 待认领

## 关键事实

- 本切片只记**收尾轮**: 修复/评审/收编/合流由修复批会话完成(八提交 ddf6acca..c9e13890, 24 条 17 文件, 决策与改道全录档案); 实测数字单点在基线切片(见 Refs)。
- 坑档双向: `pitfalls/ops/console-encoding.md`「反向」条 复发 +1 —— 批内新增测试 text=True 缺 encoding/errors, 守阵(test_platform_tolerance_guards)当场抓住; 为什么没命中: 任务书按 issue 条目派发未列该坑、路由未到坑档。新立 `pitfalls/testing/inproc-server-conn-abort.md` —— 收尾轮 test.full 首跑红: 对照组真流量 10053 连接中止(零请求主断言已过), 单跑绿、复跑全量绿, 定性并行负载 flake。
- 回写判断 = 零回写: 根 README 与 memory-bank/conventions 对本批 17 个 scripts 工具行为(port_kill 核验/--yes/--dry)无既有陈述; AGENTS.md taskkill 豁免已在批内落档(c73bad87)。

## 待办

- `memory-bank/issues/_index.md` 8,192 > 8,000 字符预算(doc.caps [债务] 行, 不拦提交)—— 需另开会话清理, 本轮未处置。
- 4 件新入池 issue 待认领: memory-bank/issues/26-11-07-1216-bug-port-kill-subprocess-encoding.html / memory-bank/issues/26-11-07-1216-bug-check-kb-structure-glyph.html / memory-bank/issues/26-11-07-1216-docs-hr-ext-stub-port-kill-yes-doc.html / memory-bank/issues/26-11-07-1216-bug-check-context-caps-porcelain-quote.html
