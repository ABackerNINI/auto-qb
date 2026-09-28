# 站点页搜索实施(webui-sites-page-search)

> 摘要: 计划 26-09-27-1852 已实施完成(全字段匹配 + 命中 chip); 下拉浮层形态的「覆盖详情且不消失」报障已修 —— 跳转器交互(点命中/点外即收即清词)落地三文件, test.full 1831 passed 全绿。
> 最后活动: 2026-09-28 23:34

## 已完成

- 搜索本体: config_hub.js(norm/parse/rows 单点 + computed 索引命中 + 单命中自动选中) · settings.html(搜索行/命中下拉/pill 去键数徽标) · config_editor.js(trackerQuery state) · console_hub.css(hb-tr-* 皮肤令牌样式)。
- 跳转器交互(2026-09-28 深夜): hubTrackerPick(点命中=选中+清词收层) + hubOnDocClick 点外即收(豁免 .hb-tr-search 行内点击); 原 Q5「保留搜索」随下拉形态退役; 守阵四条收起路径断言; 基线 26-09-28-2334。
- 档案与坑: tasks/26-09-28-webui-sites-page-search.md(子任务 7 条) + pitfalls/web-ui/overlays.md「形态切换要连交互一起重新评审」。

## 正在进行

- 提交入库(用户已说「提交」, 随 my-commit-flow 一次走完)。
