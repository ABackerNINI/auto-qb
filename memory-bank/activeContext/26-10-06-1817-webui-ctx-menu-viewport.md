# 浮层菜单视口钳位修复 (issue 26-10-06-1717 认领轮)

> 摘要: 用户指派「认领issue并修复: memory-bank/issues/26-10-06-1717-bug-webui-batch-menu-viewport-overflow.html」。
> 根因 = `ui_feedback.js::_menuPos` 用**常量** `h=222` 估算菜单高度做视口钳位, 而菜单真实高度随分支变
> (批量菜单实测 **393px**, 双皮肤一致) ⇒ 锚点落在视口下部时菜单底越出下缘最多 **171px**(实测
> `y+height=1063` / 限值 `892`), 底部项(标签分类/导出/批量删除)真实点击不可达 —— 旧冒烟 W4 组选中导出段
> 的存量 30s 超时即此, 当年被当 flaky。
> 修法 = 钳位拆两跳: `_menuPos` 只出光标处**初值**; 新增 `_menuFit`(按 `offsetWidth/offsetHeight` 实测
> 重钳位 + 极矮视口退化分支限高可滚)与 `_menuFitRefit`(watcher 出口, 现读现取 + 守 visible);
> `state.js` 挂 `menu`/`headMenu`/`filePrio` 三个**开层 watcher** —— 判据是**对象替换**(`this.X = {…}`)
> 而不是 `visible` 翻转: 开层入口六处直挂必漏, 且"菜单开着又右键另一行"右击不触发 window click 收层,
> 只有换对象才每次都响。`tpl/ctx-menus.html` 三处补 `ref`。
> 验证: ①新 e2e 回归 `e2e/menus.spec.mjs`「CTX-fit 视口下部行的批量菜单整份落在视口内(底部项可点)」
> —— 挑视口下半带的行开批量菜单, 断言菜单盒整体在视口内 + 真实点击底部项; **修复前双皮肤红 / 修复后绿**;
> ②新静态守阵 `test_frontend_ctx_menu_refit_by_measured_size`(钉 ref↔watcher↔实测算接线, 摘 ref 红验过);
> ③全量 e2e **82 passed + 10 skipped / 0 failed**(2.9m); ④`test.full` 数字见基线切片。
> 未采用建议修法的第二方案(无脑 `max-height + overflow-y`)作常态解: `overflow` 非 visible 的盒子会裁掉
> `position:absolute` 的 flyout 次级面板(「更多操作」) —— 只作极矮视口的退化兜底, 且每次开层先复位。
> **未 commit**(用户未说「提交」)。
> 最后活动: 2026-10-06 18:25

**Refs:** memory-bank/tasks/26-10-06-webui-ctx-menu-viewport.md, memory-bank/testing/baselines/26-10-06-1830-webui-ctx-menu-viewport.md

## 现状

- 改动面: `src/auto_qb/webui/static/shared/ui_feedback.js`(`_menuFit` / `_menuFitRefit` + `_menuPos` 注释) ·
  `shared/state.js`(三个开层 watcher) · `shared/tpl/ctx-menus.html`(三个 `.ctx-menu` 补 ref) ·
  `tests/test_web.py`(新守阵 + 头部测试计划补登) · `e2e/menus.spec.mjs`(新 CTX-fit 用例 + 两处注释同步) ·
  `memory-bank/`(issue 置 Done / 任务档案 / 坑档 `pitfalls/web-ui/overlays.md` 新条目 / `testing/guards.md` 登记)。
- 覆盖面: 走 `menu` watcher 的**六处**开层入口全受益(组右键 / 成员右键 / 表头右键 / 整集 / 整剧 / 文件优先级),
  没有逐个入口改代码 —— 单点在 watcher。
- 开工第一步: 会话协议同步 `779cf088`(远端领先 13 笔)。issue 文件是**同步后**才在本 clone 出现的。

## 未闭环 / 下次注意

- **未提交**: 改动与知识库回写在树上, 等用户显式「提交」。
- 本任务**未**动 e2e 里那条"挑上部行"的 arrange(W4 组选中导出)—— 修复后它不再必要, 但保留不影响结论,
  只把注释改成"已修 + 指向 CTX-fit"; 若后续要收窄对账面再动。
- 同批入池的姊妹件未认领: `26-10-06-1717-question-webui-wide-row-click-landing`(宽行落点, 待拍板)与
  `26-10-06-1717-docs-docs-ui-smoke-comment-residue`(注释残留引用已退役脚本)。
