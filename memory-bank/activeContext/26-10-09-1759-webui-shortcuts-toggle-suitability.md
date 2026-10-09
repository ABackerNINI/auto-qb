# WEBUI 快捷键「改为切换语义」适配性分析

> 摘要: 用户命题「分析快捷键中哪些适合改为切换类型(如 qB 流量图 —— 按一下打开、再按一下关闭), 写报告含适合/不适合表格」。产出报告 `reports/26-10-09-1731-report-webui-shortcuts-toggle-suitability.html`。**结论**: 注册表 59 条中 **6 条适合**(流量图 `Ctrl+\` / 统计 `\` / 历史 `Shift+\` / 详情面板 `I` / 帮助 `Shift+/` / 列选择器 `K`)、**4 条有条件**(详情页签 `Alt+1~5` / `Enter` / 限速 `L` / 设置 `Ctrl+,`)、**49 条不适合**(导航·命令·移动选择·已成对开关·多档循环)。判定用 5 准则: C1 界面显隐 / C2 关闭无副作用 / C3 键位语义单一 / C4 重复按下期望明确 / C5 有开关基础。**关键实现约束**: 浮层屏蔽闸门(`_kbOverlayBusy`)会吞掉「第二次按键」—— 抽屉类(流量图/详情)已不在名单、第二按可直达; 浮层类(统计/历史/帮助/列选择器)需额外放行。**零 `src/` / `tests/` 改动**。
> 最后活动: 2026-10-09 17:59

## 状态

- 已完成: 报告产出并入库(`reports/_index.md` 重建); 与本专题任务档案 `tasks/26-09-28-webui-keyboard-shortcuts.md` 建立双向 `doc-refs` 认领链。
- 未做: 无代码改动; 未拍板是否实施切换化改造。
- 下一步(待用户拍板): 是否按报告 §03/§04 推进「适合」6 条(优先流量图 + 详情面板 —— 抽屉不在屏蔽名单、改造零障碍)与「有条件」条目; 实施需另立计划(涉 `shortcuts.js` 的 `run` 分支「已开 ⇒ 关」+ 浮层自切换放行白名单, 不改注册表结构、不动键表)。

**Refs:** memory-bank/reports/26-10-09-1731-report-webui-shortcuts-toggle-suitability.html,memory-bank/tasks/26-09-28-webui-keyboard-shortcuts.md,memory-bank/testing/baselines/26-10-09-1759-webui-shortcuts-toggle-suitability.md
