# 1831 passed / 3 skipped —— WEBUI 设置页「?」说明全面核对与改写(纯文案 27 行)

> 摘要: 按 [plans/26-09-29-0003](../../plans/26-09-29-0003-plan-webui-settings-help-rewrite.html) 实施六文件纯文案改动 —— schema help/risk(P1 与实现相反 5 行 / P2 过时架空 2 行 / P3 边界补齐 17 行 / P4 补缺 help 3 行) + config_hub.js 富文案数据源改写并删死键 rules.overview + settings-detail.html 补 ND 滚动窗口句; 另修 KB 守卫三处存量红(gen_doc_map 渲染口径收口 / 认领链双向 / 切片上限重校 56→70)。键集合零改动, 守卫基线不受影响。
> 基线时间: 2026-09-29 00:44

- test.full 一次通过: **1831 passed / 3 skipped**, 21.58s, TOTAL **91%**(12462 语句 / 917 未覆盖 / 4246 分支 / 390 partial); 较 26-09-28-2334 基线 passed 数持平, 本轮增 0 测试(纯文案 + KB 守卫校准)。
- 初跑 3 failed 均为 KB 一致性存量(非代码): 认领链单向 / _doc-map 超 cap 28 字符 / 切片数 57>56, 处置后全绿。
