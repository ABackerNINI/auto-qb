# 6002 —— 全量绿基线: e2e 既有红修复批收尾 + 远端合流测试面扩容后重测(ctx-custom 断言对齐 + traffic-gap-zones 竞态闭合)

> 摘要: 全量绿基线: e2e 既有红修复批收尾 + 远端合流测试面扩容后重测(ctx-custom 断言对齐 + traffic-gap-zones 竞态闭合)
> 基线时间: 2026-11-11 06:58

## 验收数字

`commands run test.full` 实测(2026-11-11, pytest 179.41s; 远端 develop 合入 11 笔后的组合树):

- TOTAL: 26747 statements / 55 missed / 9362 branches / 66 partial / **99%**
- 汇总: **6002 passed, 2 skipped**(179.41s)

相对上一基线 [26-11-11-0346](26-11-11-0346-webui-pinned-matrix-guard.md)(5945 passed / TOTAL 26307 / 50 missed)的增量来自**远端合流带来的测试面扩容** —— 远端 develop 合入 11 笔(含规则页条件树修复与 e2e 回归、闸门预跑)新增测试; 本会话改动面本身为测试修复与文档面, 不新增用例。

## 本改动面

- e2e `ctx-custom` 既有红修复: 断言漂移对齐(右键菜单四支用户布局期望项数 13 → 12)。
- e2e traffic-gap-zones 既有红修复: Ctrl+\ 与 `loadWebFlags()` 竞态闭合(既有红, 与生产行为变更建议分案 —— 后者入池 issue `26-11-11-0633-bug-webui-flags-boot-resilience.html`, 只记不修)。
- 2 条对应 issue 结档; `memory-bank/testing/flaky-ledger.md` 台账改判 async-wait/时序类目。
- 收尾面: active-context 切片 `26-11-11-0635-e2e-red-ctx-custom-traffic-gap.md` + 本基线切片; 新坑档 `memory-bank/pitfalls/kb/review-check-findings-placeholder.md`(review.check findings 内联 JSON 尖括号被当占位符)。
- 本切片为合流前置闸门复检重测: 本会话曾按 rebase 前旧树实测(5948 passed / TOTAL 26307)建过一版同专题切片, 因基线切片是**不可变的一次性快照**(testing/baseline.md「切片写完不改」)、旧数字已不能代表当前树, 按口径删除重建为本件(时间戳取重建时刻)。

