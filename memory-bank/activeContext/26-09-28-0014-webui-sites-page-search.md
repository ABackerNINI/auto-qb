# 站点页搜索实施(webui-sites-page-search)

> 摘要: 计划 26-09-27-1852 已实施完成 —— trackers 二级页搜索(全字段匹配 + 命中 chip + 左右分栏)落地四文件 + 守阵 1 条, test.full 1812 passed 全绿; 待提交入库。
> 最后活动: 2026-09-28 00:14

## 已完成

- 四文件落地: settings.html(搜索行/命中列表/左右分栏/pill 去键数徽标) · config_hub.js(norm/parse/rows 单点 + computed 索引命中 + Esc·离开分区双清空 + 单命中自动选中) · config_editor.js(trackerQuery state) · console_hub.css(hb-tr-* 皮肤令牌样式)。
- 守阵 `test_frontend_tracker_search_wiring`; `CAP_POLICY["index-auto"]` 12000→12100(专题入册超 cap) + SKILL.md 表同步。
- 收尾五件套齐: 任务档案 26-09-28-webui-sites-page-search.md / 基线切片 26-09-28-0014 / 新坑 pitfalls/web-ui/cjk-regex-norm.md / 计划文档回写 Done / kb.index。

## 正在进行

- 提交入库(用户说「提交」即走 my-commit-flow; 收尾回写件随主提交一并暂存)。
