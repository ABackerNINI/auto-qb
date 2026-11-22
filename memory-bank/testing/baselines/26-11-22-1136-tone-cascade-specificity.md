# 6790 —— 6790 passed, 6 skipped —— issue 26-11-20-0404 tone 级联修复收尾基线(webui-column-style)

> 摘要: 6790 passed, 6 skipped —— issue 26-11-20-0404 tone 级联修复收尾基线(webui-column-style)
> 基线时间: 2026-11-22 11:36
**Refs:** memory-bank/tasks/26-11-20-webui-column-style.md

## 验收数字

`commands run test.full` 实测(2026-11-22 11:32–11:36, Windows, 3m56s, 树 = 8ff76f0b, 分支 develop, 工作树含本批未提交改动):

```
TOTAL                                                30681     85  10942     87    99%
6790 passed, 6 skipped, 8 warnings in 236.88s (0:03:56)
```

覆盖率闸门通过(99% 线 rc=0)。与上基线(26-11-22-0821, 6789P/6S)相比 passed +1(新增静态守阵用例 `test_frontend_tone_cascade_beats_state_color`), skipped 持平; TOTAL 表四项与上片逐位一致(30681/85/10942/87), 覆盖率同为 99% 无回退。

## 本改动面

本轮 = issue 26-11-20-0404 收尾: 四皮肤 tone 规则用 `:is()` 举齐 7 状态/7 成员 kind 从 (0,3,0) 提到 (0,4,0) 后置胜出, 修复状态文字色压制数值色阶; 新增静态级联守阵 + 四皮肤计算色 e2e。事实与验证细节见 issue 26-11-20-0404 的 §07; 浏览器计算色由真浏览器 e2e 覆盖(整份 `e2e/colstyle.spec.mjs` 28/28 通过)。按计划 26-11-20-0009 D14 本专题为纯前端展示面、免真机轨。
