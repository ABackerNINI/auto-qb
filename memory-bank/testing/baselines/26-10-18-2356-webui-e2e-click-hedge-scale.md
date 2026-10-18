# 3637 passed + 10 skipped(根), 覆盖率 98% —— clickRow 对冲清偿(3000 规模高行落点)后全量基线

> 摘要: clickRow 对冲清偿(3000 规模高行落点)后全量基线
> 基线时间: 2026-10-18 23:56

## 验收数字

`commands run test.full` 实测誊写(2026-10-18 23:57 跑, 文档回写完成后复跑一次, 数字与 23:51 那次一致):

```text
TOTAL                                                18691    306   6338    208    98%
3637 passed, 10 skipped in 37.03s
```

口径注记:

- 上表是 pytest 全量口径(含覆盖率门槛 98%); 相对上基线的逐位对比不写 —— 看差值 `commands run kb.baseline -n 2`。
- **e2e 侧不进本表**(另一条链路, 不在 pytest 收集面内), 实测数字落在 issue 报告 §07 与本切片「本改动面」的注记里: 3000 档定点 `multiselect-shows.spec.mjs` 修复前 12 passed / 4 failed → 修复后 **16 passed / 0 failed**; 默认 300 档全量 `dev.e2e` **290 passed / 10 skipped / 0 failed**。
- 裸数字只写基线切片这一处; 档案与报告正文引它而不抄(守卫 `check_wording.py` 判据族 B)。

## 本改动面

- `e2e/lib/gestures.mjs` · `e2e/multiselect-shows.spec.mjs` · `e2e/optimistic.spec.mjs` · `e2e/delta-sync.spec.mjs` —— 4 份同构 `clickRow` 对冲同步改三处: ①拦截面由「`querySelector('.sticky-head')` 头一个」改为「所有 `.sticky-head` 下沿最大值」; ②行高 > 可用视口时 `scrollIntoView` 由 `block:'center'` 改 `'start'`; ③落点由「行盒 `top+8`」改为钳进「行盒 ∩ (视口 − 拦截面)」(`lo > hi` 即本拍作废)。
- `e2e/multiselect-shows.spec.mjs` 文件头新增「第二形态」归因段(高行居中 ⇒ 落点出视口)。
- `memory-bank/pitfalls/testing/smoke.md` 新增条目「行高于视口时 scrollIntoView(center) 把落点推出视口」+ 三行头触发词补新词。
- `memory-bank/issues/26-10-18-2226-test-click-hedge-shows-scale-3000.html` 置 Done(复验 / 根因 / 实际修法 / 改道说明 / 测试数字)。
- 新建: 本切片 + 任务档案 `memory-bank/tasks/26-10-18-webui-e2e-click-hedge-scale.md`。
- 排障脚本 `tmp-analysis/clickrow-probe.mjs` / `clickrow-probe2.mjs`(仪器化几何探针)—— 该目录已在 `.gitignore:84`, 不进提交。
