# 7009 passed, 6 skipped, TOTAL 31412/108/11190/93 99% —— 尾锚视口观察项修复批后基线

> 摘要: 推送时自动 rebase 吸收汇入 19 笔(relocate 收尾簇/kb.nav/cap 债务清理)+ 汇入 1dcf83b2(relocate_foreign 覆盖清偿)+1 后, 观察项修复批(dev.webui data_dir 钉 temp/S2 死逃生分支收紧/S20b 与 chart 注释如实)落地后的 develop 终态基线
> 基线时间: 2026-11-22 22:52
> 档案: memory-bank/tasks/26-11-22-webui-traffic-anchor-viewport.md

## 验收数字

`commands run test.full` 实测(test.quick 同树 7012 passed, 2 skipped):

```
TOTAL                                                31412    108  11190     93    99%
7009 passed, 6 skipped, 8 warnings in 149.58s
```

## 增量构成

- 相对 26-11-22-2211(6988P @ 5990f41b): +20 用例来自推送时汇入的 19 笔(kb.nav 守阵等), +1 用例来自汇入 1dcf83b2(relocate_foreign 覆盖清偿); 本分支观察项修复批(315cfaa1)零新增用例, S2 断言收紧不改计数。
- 本分支七笔在推送时经 ship.push 自动 rebase 换代: 4233aa3d/0abd9954/684d667e/c92eca0c/5645d935/4aab7f14/a5326fd5(映射详见任务档案 R4)。
- e2e 流量系七 spec 69P(收口态实测); 接缝终审(远端交叉面)零 blocker/major。
