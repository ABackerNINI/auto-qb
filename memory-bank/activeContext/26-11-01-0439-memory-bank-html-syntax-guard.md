# memory-bank-html-syntax-guard

> 摘要: 守卫落地: scripts/check_html.py(L1 行级正则 + L2 stdlib 解析器残缺标签名双网, script/style 遮蔽) 挂进 kb.check 与提交闸门; v.Nu 增量闸门行(changed:GLOB 只查本次改动) + kb.html-audit 全库巡检任务; 守阵四条 test_html_guard_* 入阵, test.quick 全绿(数字口径见 kb.baseline); 坑档 pitfalls/docs/html-endtag-missing-gt.md 复发 2; 存量基线 L1+L2 零命中, v.Nu 全库 320 条 error 留巡检清理
> 最后活动: 2026-11-01 09:38
**Refs:**

**R0(2026-11-01 04:39):** 守卫落地: scripts/check_html.py(L1 行级正则 + L2 stdlib 解析器残缺标签名双网, script/style 遮蔽) 挂进 kb.check 与提交闸门; v.Nu 增量闸门行(changed:GLOB 只查本次改动) + kb.html-audit 全库巡检任务; 守阵四条 test_html_guard_* 入阵, test.quick 全绿(数字口径见 kb.baseline); 坑档 pitfalls/docs/html-endtag-missing-gt.md 复发 2; 存量基线 L1+L2 零命中, v.Nu 全库 320 条 error 留巡检清理

**R1(2026-11-01 09:38):** 闸门扩面: v.Nu 增量面放开到全仓改动 HTML(match=.html + changed:**/*.html), 守阵/坑档/docstring 同步, 全量绿见基线切片 26-11-01-0938
