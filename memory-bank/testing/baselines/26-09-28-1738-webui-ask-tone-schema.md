# 1820 passed / 3 skipped —— 「?」语调接 schema tone 字段(删标两遗漏字段补红)

> 摘要: 用户报上轮「?」语调色修复(eb57595)有遗漏 —— 站点「删除标签格式」与自动化「彻底删除标签」仍是中性灰。根因: 语调取值只查前端 HUB_TONE 静态表, 带 risk 的动态路径字段进不去表。修法: schema `Field` 加 `tone` 属性(破坏性字段显式声明, 与 risk 文案解耦 —— "需重启"类 risk 不标), `hubToneOf` 优先读 `field.tone` 回落静态表; 两个删标字段标 `tone="danger"`。CSS 零改动复用上轮 `.hb-ask.danger` 变体。附带: 两字段行条纹由 warn 黄转红(hubRowClass 判 danger 后)。验证: 桩服务 + 真浏览器量测(两行静息红描边/on 态全红/普通行中性灰/password 静态表老键回落正常)。
> 基线时间: 2026-09-28 17:38
> 档案: tasks/26-09-27-webui-curve-chart.md(追加)

- test.full: **1820 passed / 3 skipped**, TOTAL **91%**(12429 语句 / 915 未覆盖 / 4222 分支 / 388 partial), 耗时 22.66s, 与前基线(26-09-28-1558)持平零回归。
