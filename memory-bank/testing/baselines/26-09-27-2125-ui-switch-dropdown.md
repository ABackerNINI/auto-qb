# 1744 passed + 3 skipped —— 界面切换改顶栏下拉直选(替代环形互切)

> 摘要: 顶栏右半部互切链接(`<a class="ui-link">` 环形 atlas→prism→console→atlas)改为**下拉直选**:
> 按钮显示当前 UI 名 + ▾, 点开列三套 UI(图标 + 名称 + 一句话描述, 当前项「当前」+ ✓), 点任意一套直达;
> 当前项点击 preventDefault 仅收起。面板/行复用既有弹层族 `.pop-menu`/`.pop-item`(flip-x 静态右对齐,
> 锚点恒在顶栏右缘无需测量), 三套 CSS **净增 0 行**(atlas components.css 恰好 700 行上限, 靠原位改写
> .ui-tools/.ui-link 规则消化); 选项表单点 `state.js UI_HOME`, computed `uiCurrent`/`uiOptions` 替代
> `uiSwitchTarget`; 开合挂 lifecycle.js 既有「window 点空白关闭链 + Esc 退栈」。评审模板:
> resources/navbar-right-template.html(三皮肤令牌面板, 可交互)。设计源模板评审 + 三套皮肤真机截图
> (星图/棱镜/控制台)全部通过; 棱镜主题引擎(theme.js)零影响, 控制台无主题按钮不变。
> 基线时间: 2026-09-27 21:25(取落库提交时间 3d0d1d2)。

- **测试**: 1752 passed + 3 skipped(远端 b080086 合入 HR 绑定映射制后在新基线复测; 本次改动零新增测试
  —— 守阵 `test_frontend_template_split_wiring`(分片体量/差异口/聚合配平)、`test_frontend_static_bundle_health`
  (CSS 括号/挂件类)、`_UI_ALL` 成对断言全绿即覆盖本次改动面); test.full 18.52s。
  附: 切片数 49 超 activeContext 上限 48, 按守卫口径蒸馏 `26-09-22-2318-deps-version-management`
  (纯指针件, 实体在 tasks/26-09-22-deps-version-management.md)后删除, test_memory_bank 24 passed。
- **改动面**: `shared/tpl/topbar.html`(链接 → 按钮+菜单) / `shared/state.js`(UI_HOME + uiCurrent/uiOptions
  + uiMenuOpen) / `shared/lifecycle.js`(点空白 + Esc 两处挂 uiMenuOpen) / 三套 `css/components.css`
  (.ui-tools 加 position:relative、.ui-link 加 font:inherit 与 .open 态、.pop-item 加 text-decoration:none) /
  README.md(「环形互切」→「顶栏下拉直选」)。后端零改动。
- **浏览器冒烟**: qB 未运行 → 按 testing/ui-preview-harness.md 口径自建临时 stub(静态挂载 +
  /api/config/public + /api/state + /api/events + no-cache 中间件), Playwright 实测三皮肤:
  免鉴权直进 / 菜单开合 / 当前行 preventDefault / 外点收起 / Esc 收起 / 三套互跳全链路 ✓。
  ⚠ IAB 测试面板 rAF/animation 冻结(遮挡节流)会卡住 Vue 过渡类, 属环境伪象 —— 状态机经
  二次探针证验(菜单 DOM 滞留时 Vue 状态已关)。
- **覆盖率**: TOTAL 91%(11730 语句 / 849 未覆盖 / 3940 分支 / 351 partial; 取自合并远端 b080086
  之后的树; 1 采样)。
