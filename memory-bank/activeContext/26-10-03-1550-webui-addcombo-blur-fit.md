# 添加种子三下拉「失焦即收 + 限高不出窗」修复

> 摘要: 用户报添加种子窗口三下拉(保存路径/分类/标签)两类故障, 已按根因修复并三皮肤真机验证 12/12 × 3。
> 最后活动: 2026-10-03 15:50

## 已完成 (2026-10-03)

- **故障①(点窗口其它位置下拉不收/闪烁重现)**: 收层判据原来只有 window click(lifecycle.js)一路;
  点字段 label(`for=` 转发激活)时浏览器先 blur 再把焦点转回输入框(记录器实测 focusout → ~2ms
  focusin), click 关层 + 转发 click 重开 = 关了又开, leave 过渡被打断 = 用户看到的闪烁, 且时序
  依赖浏览器任务派发方式 ⇒ 概率发生。修法 = 收层主判据改 `@focusout`(三输入框挂
  `addPopBlurClose`)+ **40ms 合帧守卫**(同步收仍会被回焦打断), 三个开层方法先
  `_addPopBlurCancel()`; window click 降级为兜底。
- **故障②(选项过长把窗口撑变形)**: `.pop-menu` 基础 max-height:330px 只保证菜单自身可滚;
  菜单绝对定位锚在输入行下方, 输入行贴近窗口底沿时整条伸出窗外(滚动条跟着出窗), 且溢出把
  `.add-dialog-body` scrollHeight 撑大(实测 449→591)。修法 = 开层 watcher 单点
  (`watch` 块, 开层入口有四处直挂必漏)`_fitAddPop` 量「输入行→滚动容器可见底沿」净空,
  把可滚内层限进去(限前复位旧值, 下限 120px); 候选异步到位(loadAddOptions)开着时重限。
- **守阵**: `test_web.py::test_frontend_add_combo_blur_close_and_fit` 五组断言(focusout 挂点/
  合帧守卫/开层撤销/watcher 限高/候选重限), 文件头测试计划同步登记。
- **验证**: 三皮肤(atlas/prism/console)真浏览器 Playwright 走查 12/12 × 3 —— 点空白三菜单全收+
  失焦 / label 点击菜单保持且零过渡重放 / 切字段旧收新开 / 40 项长菜单不出窗 + body 零新增滚动 +
  菜单内滚动条生效 / Esc 只收下拉 / Tab 失焦收 / 选项行选中回归。
  探针与验证脚本: `.workbuddy-ai/tmp/verify-fix.cjs`(临时件, 不入库)。
- **收尾**: 基线切片 [baselines/26-10-03-1550](../testing/baselines/26-10-03-1550-webui-addcombo-blur-fit-done.md)
  (2391 passed + 3 skipped / 99% @ 4978a717 工作区, +1 = 本单守阵); 新坑
  [pitfalls/web-ui/combobox-focusout-close.md](../pitfalls/web-ui/combobox-focusout-close.md);
  smoke.md 残留桩条目复发 +1(本轮开工直接复用 8099 残留服务, 验的是别的 clone 的旧代码 → 假 PASS,
  判据 = fetch 静态 JS 比对特征串; 处置 = 改代码验证一律自己起桩)。progress 已迁出。
- 不满足立档阈值(单轮两文件 + 一测试文件); issue 未入池(用户当轮直接报障, 无入池指令)。

## 状态

实施与收尾完成, **工作树未提交** —— 等用户提交指令。
