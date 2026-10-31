# 基线 · 1768 passed + 2 skipped —— WEBUI 挂件点击即筛选轮(站点/标签/分类/路径 chip → 筛选器)

> 摘要: 表格里点 站点/标签/分类/路径 挂件直接切换对应筛选值(filters.js::filterFromChip 单点, toggle 语义再点取消), 三皮肤 CSS f-on/f-cell 交互态成对; 不挂原生 :title(遵 hr-tooltip-overlap 短文本列口径); 15 处挂件覆盖组级/明细/种子页/追剧。真浏览器冒烟(桩数据)14/14 + 三皮肤挂载 3/3, pageerror=0。
> 基线时间: 2026-09-30 00:20 (develop @ 58d72e0a + 本轮未提交改动; 开工 sync 至 1d711660, 提交前 stash/ff/pop 合入远端三提交)
> 档案: tasks/26-09-29-webui-chip-click-filter.md

TOTAL 1768 passed + 2 skipped / 91%(12506 语句 / 999 未覆盖, test.full 34.4s, rc=0) —— 0 failed。
较上轮切片 26-09-29-2316(1760 / 12480)+8 passed / +26 语句: +8 来自并入远端 58d72e0a 三提交(tooltip 扫描守阵改造 + 抽屉记住页签), 本轮零新增守阵; 途中红过两次均已转绿 —— test_frontend_template_split_wiring(atlas components.css 顶格 700 行, 新规则挪 views.css 后回 700)、test_doc_topics_complete(新任务档案漏 **Topics:** 行)。
改动面: shared/filters.js + shared/tpl/{groups,torrents,shows}.html + atlas css/views.css + prism css/views.css + console css/components.css + README.md + memory-bank 回写件(任务档案/切片/基线/契约/_index), 共 13 个文件, 零后端。
真浏览器冒烟工装(.openclaw/tmp/, 不入仓库): stub_ui_server.py(3 种子 2 组桩数据, 端口 8201 —— 8127 是运行中的生产实例勿占)+ chip-filter-drive.cjs 14/14 + skins-mount-drive.cjs 3/3。
