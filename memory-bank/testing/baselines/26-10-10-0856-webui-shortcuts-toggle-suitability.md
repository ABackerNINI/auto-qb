# 2871 —— WEBUI 快捷键「适合」6 条切换语义实施基线

> 摘要: 用户下令「实施适合的 6 条(切换语义), 其余待定, 完成后状态置为 in progress」。按报告 `reports/26-10-09-1731-report-webui-shortcuts-toggle-suitability.html` §03/§04 落地 6 条「适合」条目(流量图 `Ctrl+\` / 统计 `\` / 历史 `Shift+\` / 详情面板 `I` / 帮助 `Shift+/` / 列选择器 `K`)由「只打开」升级为「开/关双态」: **只改键盘 `run` 路径**(鼠标入口不变), 抽屉类第二按直达、浮层类靠自切换白名单 `KB_SELF_TOGGLE_OVERLAY` 放行; 4 条「有条件」与 49 条「不适合」维持原状。1 源文件(`shortcuts.js`)+ 1 守阵(`test_web_shortcuts.py` 新增 1 用例)。
> 基线时间: 2026-10-10 08:56

**Refs:** memory-bank/activeContext/26-10-09-1759-webui-shortcuts-toggle-suitability.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 同步 `19175361`, 工作树含本轮改动时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2871 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标)
- 增量: passed `2870 -> 2871`(**+1**, 新增守阵 `test_shortcut_toggle_semantics`); 语句 / 未覆盖 /
  分支 / partial **未变**(改动全在 `src/**/*.js` 前端, 不进 Python 覆盖口径)。
- 增量明细(本轮真正新增/改动):
  - `src/auto_qb/webui/static/shared/shortcuts.js`: 注册表 4 条 `run` 改指 `_kbToggle*`
    (open-stats / open-history / open-qb-traffic / help-panel); 详情面板 `_kbOpenDrawer` 补
    「已开同目标 ⇒ closeDrawer」切换分支; 新增 4 个切换方法(`_kbToggleStats` / `_kbToggleHistory` /
    `_kbToggleKbHelp` / `_kbToggleQbTraffic`); 新增 `KB_SELF_TOGGLE_OVERLAY` 自切换白名单 +
    引擎 `_kbOverlayBusy` 闸门放行分支。
  - `tests/test_web_shortcuts.py`: 新增 `test_shortcut_toggle_semantics`; 更新 3 处旧断言
    (`test_qb_traffic_shortcuts` ① / `test_help_overlay_wiring`)与 docstring「## 测试计划」清单。
  - 回写 `memory-bank/tasks/26-09-28-webui-keyboard-shortcuts.md`(Status `Done` -> `In Progress`)、
    `memory-bank/activeContext/26-10-09-1759-webui-shortcuts-toggle-suitability.md`。

## 对照判据(后续沿用)

- 以本切片(`2871+4` / `16567` / `167` / `5716` / `143`)为对照点: 预期 passed 只升不降、
  未覆盖 / partial 不升。
- 剩 4 条「有条件」(详情页签 `Alt+1~5` / `Enter` / 限速 `L` / 设置 `Ctrl+,`)与 49 条「不适合」
  **待定, 未实施**; 若后续推进, 数字变化另立基线切片。
