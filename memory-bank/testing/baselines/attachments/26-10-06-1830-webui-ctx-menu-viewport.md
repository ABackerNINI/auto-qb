# 2678 —— 浮层菜单开层实测钳位: 批量菜单视口溢出修复 (issue 26-10-06-1717)

> 摘要: 认领并修复 issue 26-10-06-1717 —— `ui_feedback.js::_menuPos` 用**常量** `h=222` 估算菜单高度做视口钳位,
> 而菜单真实高度随分支变(批量菜单实测 **393px**, 双皮肤一致, skip-check on): 锚点落在视口下部时菜单底越出下缘
> 最多 **171px**(e2e 实测菜单盒 `y+height = 1063` / 限值 `892`), 底部项(标签分类/导出/批量删除)真实点击不可达。
> 修法 = 钳位拆两跳: `_menuPos` 只出光标处初值; 新增 `ui_feedback.js::_menuFit`(按 `offsetWidth/offsetHeight`
> 实测重钳位 + 极矮视口退化分支限高可滚)与 `_menuFitRefit`(watcher 出口, 现读现取 + 守 visible); `state.js` 挂
> `menu`/`headMenu`/`filePrio` 三个开层 watcher(判据 = **对象替换**而非 visible 翻转, 覆盖"菜单开着又右键另一行";
> 开层入口共六处, 直挂方法必漏); `tpl/ctx-menus.html` 三处补 `ref`。新增静态守卫 1 条(**摘 ref 红验已过**) +
> e2e 回归 1 条(修复前双皮肤红 / 修复后双皮肤绿)。零 Python 生产代码改动。
> 基线时间: 2026-10-06 18:30

**Refs:** memory-bank/tasks/26-10-06-webui-ctx-menu-viewport.md, memory-bank/activeContext/26-10-06-1817-webui-ctx-menu-viewport.md

- 分支: develop @ **779cf088**(工作树含本轮改动未提交)
- 命令: `commands run test.full`(Windows —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2678 passed + 4 skipped, 覆盖率 TOTAL 99%**
  - 语句 **16021** / 未覆盖 **163** / 分支 **5472** / partial **143**。
  - 耗时: 两次采样 **58.17s** / **51.46s** ⇒ 区间约 **51~59s**(机器同期跑过 e2e, 偏慢; 上一条基线 45~48s)。
- 相对上一条基线 [26-10-06-1102](26-10-06-1102-check-kb-structure-debt-count.md)(2677 + 4 / 16021 / 163 / 5472 / 143):
  passed **+1** —— 新增守卫 `test_frontend_ctx_menu_refit_by_measured_size`; 语句 / 未覆盖 / 分支 / partial 逐位相同。
- **红验**: ①静态守阵 —— 把 `ref="ctxMenu"` 改名 ⇒ 立刻 FAIL(`ctx-menus.html 缺 ref="ctxMenu"`), 还原后绿;
  ②e2e 回归 —— 修复前同一条用例双皮肤 FAIL(几何断言 `菜单底 1063 ≤ 893`), 修复后双皮肤 pass。
- e2e: `commands run dev.e2e` **82 passed + 10 skipped / 0 failed / 2.9m**(含本轮新增 2 条 CTX-fit);
  `--grep CTX-fit` 单文件修复后 **2 passed** / 修复前 **2 failed**。
- 守卫: `kb.check` 绿(463 文档 · 251 专题, 主键 + 认领链 OK) · `doc.links` 绿 · `kb.active --check` 绿 ·
  `commands run doc.caps` **无 cap 债务**。
- 改动面:
  - `src/auto_qb/webui/static/shared/ui_feedback.js` —— 新增 `_menuFit(el, x, y)` 与 `_menuFitRefit(stateKey, refName)`;
    `_menuPos` 注释改为"只出光标处初值"(常量不再是钳位依据)。
  - `src/auto_qb/webui/static/shared/state.js` —— `watch` 新增 `menu` / `headMenu` / `filePrio` 三个开层 watcher。
  - `src/auto_qb/webui/static/shared/tpl/ctx-menus.html` —— 三个 `.ctx-menu` 各补 `ref`。
  - `tests/test_web.py` —— 新增 `test_frontend_ctx_menu_refit_by_measured_size` + 头部「测试计划」补登。
  - `e2e/menus.spec.mjs` —— 新增 CTX-fit 回归用例; 头注「计划外发现」段与 W4 arrange 注释同步为"已修"。
  - `memory-bank/` —— issue 26-10-06-1717 置 **Done**(复验 / 实际修法 / 验证方式 / 测试数字) · 新任务档案
    `tasks/26-10-06-webui-ctx-menu-viewport.md` · `pitfalls/web-ui/overlays.md` 新条目「浮层钳位不能用常量估算高度」
    (三行头摘要/触发同步扩词) · `testing/guards.md` 前端段登记 · 本切片 · activeContext 切片。
  - 生成物 `_index.md` / `_doc-map.md` 族(20 个重建)。
- 行尾: 本切片与改动面全为 **LF**(仓库 2026-10-02 起 `text=auto eol=lf`)。
- **未入库**: 等用户显式「提交」。
