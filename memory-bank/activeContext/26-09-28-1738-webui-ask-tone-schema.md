# WEBUI「?」语调色补漏: schema tone 字段单点

> 摘要: 用户报删标两字段(站点「删除标签格式」/自动化「彻底删除标签」)的「?」按钮仍中性灰 —— 已修(语调源接 schema `Field.tone`)并入库建档, 详见 tasks/26-09-27-webui-curve-chart.md 09-28 二次追加段与基线 26-09-28-1738。
> 最后活动: 2026-09-28 17:38

## 已完成

- schema `Field` 加 `tone` 属性("danger"/"important"): 破坏性字段的语义单点, 与 `risk` 文案解耦(带 risk 不全是危险 —— "需重启"类只写文案不标 tone)。
- `hubToneOf` 改为 `field.tone` 优先、`HUB_TONE` 静态表回落 —— 动态路径字段(如 `trackers.<站点>.remove_tags`)进不去静态表, 这是静态表盖不住它们的结构性原因。
- 两个删标字段标 `tone="danger"`; CSS 零改动复用 eb57595 的 `.hb-ask.danger` 变体。附带: 两字段行条纹由 warn 黄转红(`hubRowClass` 按 tone 判 danger)。
- 验证: 桩服务 + 真浏览器量测 —— 两行静息描边红 45% / on 态字+底+发光全红; 普通行(域名)中性灰不变; 静态表老键(qbittorrent.password)回落正常。test.full 1820 passed / 3 skipped(基线 26-09-28-1738)。

## 进行中 / 待办

- 无 —— 等待用户下一条反馈。
