# WEBUI 快捷键「改为切换语义」适配性分析 → 「适合」6 条实施

> 摘要: 用户命题「分析快捷键中哪些适合改为切换类型(如 qB 流量图 —— 按一下打开、再按一下关闭), 写报告含适合/不适合表格」→ 报告 `reports/26-10-09-1731-report-webui-shortcuts-toggle-suitability.html` 判定注册表 59 条中 **6 适合 / 4 有条件 / 49 不适合**(准则 C1 界面显隐 / C2 关闭无副作用 / C3 键位语义单一 / C4 重复按下期望明确 / C5 有开关基础)。**2026-10-10 用户下令「实施适合的 6 条, 其余待定, 完成后状态置为 in progress」** —— 6 条**已落地**: 流量图 `Ctrl+\` / 统计 `\` / 历史 `Shift+\` / 详情面板 `I` / 帮助 `Shift+/` / 列选择器 `K` 由「只打开」升级为「开/关双态」。实现要点: **只改键盘 `run` 路径**(鼠标入口 —— 状态栏按钮/右键菜单/双击 —— 保持原语义); 抽屉类(流量图/详情)不在浮层屏蔽名单、第二按直达; 浮层类(统计/历史/帮助/列选择器)靠新增自切换白名单 `KB_SELF_TOGGLE_OVERLAY` 放行第二次按键(报告 §07.1)。4 条「有条件」与 49 条「不适合」**待定未实施**。
> 最后活动: 2026-10-10 08:56

## 状态

- 已完成: 6 条「适合」条目切换语义实施(`src/auto_qb/webui/static/shared/shortcuts.js`); 守阵 `tests/test_web_shortcuts.py` 新增 `test_shortcut_toggle_semantics` 并更新 3 处旧断言与「## 测试计划」清单; 全量测试绿(数字见 `commands run kb.baseline`); 任务档案 `tasks/26-09-28-webui-keyboard-shortcuts.md` 状态 `Done` -> `In Progress`。
- 未做: 4 条「有条件」(详情页签 `Alt+1~5` / `Enter` / 限速 `L` / 设置 `Ctrl+,`)与 49 条「不适合」按用户「其余待定」维持原状; 真机实弹走查(逐键实测)留给用户。
- 下一步(待用户拍板): 是否推进 4 条「有条件」条目 —— 详情页签 `Alt+1~5` 可补「同页签再按 ⇒ 关」升级为完整切换; `Enter` / `L` / `Ctrl+,` 报告建议保持现状(语义漂移 / 关闭丢输入 / 页面导航无关闭态)。

**Refs:** memory-bank/reports/26-10-09-1731-report-webui-shortcuts-toggle-suitability.html,memory-bank/tasks/26-09-28-webui-keyboard-shortcuts.md,memory-bank/testing/baselines/26-10-09-1759-webui-shortcuts-toggle-suitability.md,memory-bank/testing/baselines/26-10-10-0856-webui-shortcuts-toggle-suitability.md
