# webui 一键导入缺失站点

> 摘要: 设置页「站点」新增一键导入(对齐 CLI --export-yaml --only-missing): 只读扫描端点 + 填入编辑器待审。
> 最后活动: 2026-09-26 02:34

## 本轮状态

- **已完成**(单会话一次落地, 明细见 [tasks/26-09-26-webui-sites-import](../tasks/26-09-26-webui-sites-import.md)):
  `GET /api/sites/missing` 只读扫描 + `config_hub.js::hubImportSites()` + 两套 UI 按钮 + `gen_tracker_name` 提取; 全量 1623 passed + 1 skipped(TOTAL 92%), 金清单 61→62。
- **正在进行**: 无 —— **已提交推送**: 功能提交 `e3fb35d` 经合并提交 `8bacfae`(合流远端 9 笔, 冲突 4 处手工解决 + 合并树重测 1636 collected)推 Gitee, ls-remote 核对一致。
- **遗留**: 真机走查待真实 qB(本会话无真机, 浏览器冒烟未做): 导入按钮 → 确认框 → 填入编辑器 → 保存热重载全链。

## 完成条目去向

- 已完成事实 → progress/implemented-webui.md(置顶条) + testing/baseline.md(顶部基线)。
