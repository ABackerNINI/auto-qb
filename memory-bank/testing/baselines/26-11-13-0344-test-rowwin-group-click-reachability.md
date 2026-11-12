# 6084 passed + 2 skipped(根) —— e2e rowWin 组行点击可达性修复批次

> 摘要: e2e group-hash-ref test4 挑组窗口化可达性修复(issue 26-11-13-0130)
> 基线时间: 2026-11-13 03:44

## 验收数字

```text
TOTAL                                                27113     65   9480     69    99%
6084 passed, 2 skipped in 193.64s (0:03:13)
```

(实测时点: 修复 + 评审 4 轮 2 发现全修后收尾 `commands run test.full` 2026-11-13; 2 skipped 为存量 skip; pytest 面零改动 —— 本批只动 e2e spec 与文档, 数字与上一切片 26-11-13-0232 一致; e2e 面数字在本专题 issue 档案, 不入基线)

## 本改动面

- **`e2e/group-hash-ref.spec.mjs`**: test4 挑组从 `vm.groups.find`(服务端插入序首组 = 排序后最末, @3000 矩阵轮 rowWin 窗外不渲染致点击超时)改为沿已渲染组行 `.group-row[data-table="group"][data-key]` 的 DOM 序取**最顶**第一个含非暂停成员的组再反查 vm.groups —— 顶部行在任何窗口状态下都在场(滚动顶部 start 恒钳 0), 尾缘行随行高实测收敛重算进出; 红绿双验 + 矩阵轮 repeat-each 3 全绿(e2e 数字见 issue 26-11-13-0130 修复后补充)。
- **文档面**: issue 26-11-13-0130 翻 Done(复验 + 修复后补充); 新坑档 `memory-bank/pitfalls/testing/rowwin-target-row-from-dom.md` + `kb.index` 再生; 会话切片 26-11-13-0343。
