# webui-tooltip-declutter — WEBUI tooltip 去冗与锚定修复

> 摘要: tooltip 专题。首轮(26-10-04)全站复述型移除 67 处已闭环; 二轮(26-10-07)详情面板去冗 45 处 + 容器级 title 锚定下放 6 组(修用户报 tracker 状态卡片栅格错位)完成, 档案 tasks/26-10-04-webui-tooltip-declutter.md Done。
> 最后活动: 2026-10-07 23:13

## 已完成(详情见档案, 不在此复述)

- 首轮 67 处 + 守卫 `test_removed_redundant_tooltips_stay_removed`(2026-10-04)。
- 二轮去冗 45 处(`94013201`)+ 锚定下放 6 组(`99fa6eef`), 分支 webui-tooltip-fix2 并入本地 develop;
  test.full 2757+4 / e2e fast 6 passed / 真浏览器悬浮 12/12 PASS(基线 [26-10-07-2313](../testing/baselines/26-10-07-2313-webui-tooltip-declutter-r2.md))。
- 计划外发现 ui_harness `FakeClient.peers_map` 恒空 → 已入池 [issue 26-10-07-2309](../issues/26-10-07-2309-test-webui-peers-harness.html)(Open, 待用户指派认领)。

## 正在进行

- 无 —— 二轮已收口, 本切片只剩未决项。

## 未决项

- issue 26-10-07-2309: ui_harness peers 数据缺失(e2e 零覆盖 peers 页签内容渲染), Open。
- `.zcode-tmp/` 下 9 张验证截图属临时证据, 看完可删, 勿入库。
