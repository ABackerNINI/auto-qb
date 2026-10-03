# 添加种子三下拉 label 闪烁「第四轮」修复(JS 收层守卫单点加固)

> 摘要: 用户报 594e247f(第三轮 mousedown.prevent)仍未修住「点字段 label 稳定复现下拉闪烁(保存路径/分类/标签)」。
> 本轮真浏览器探针(Playwright + ui_harness 桩, delay=150ms 人手时序, 全事件埋点 + rAF 菜单时间线)把两件事拆开:
> ①**探针自校验** —— 把四个 label 的 `@mousedown.prevent` 临时摘掉(回到第二轮状态), delay=150 稳定复现完整
> 闪烁链(mousedown→blur→按住期 65ms 收层→松手回焦重开), 证明探针能抓到该 bug, "当前代码干净"的阴性结果可信;
> ②**当前代码四场景全干净** —— 菜单开/关 × 聚焦/未聚焦, 三皮肤 24/24 零翻转。用户症状与「浏览器跑的还是
> 第三轮修复之前的模板」逐特征一致: SPA 长开页签的模板/JS 以**页面加载时刻**为准, 服务端更新到不了不刷新的页签。
> 加固 = 收层改 **JS 单点自洽**: `addPopBlurClose`/`metaCatBlurClose` 的 40ms 定时器收层前问
> `_popBlurShouldHold`(mounted 挂 mousedown capture 记录器) —— 焦点已回本族输入框或本族 label 转发 click
> 仍在途 → 跳过收层。模板修饰符在 = 纯 no-op; 缺位 = 独立根除闪烁, 任何模板/JS 代际混合都安全。
> 最后活动: 2026-10-04 02:40

## 已完成 (2026-10-04)

- **探针自校验(关键方法步)**: `sed` 摘掉 `dialogs-mgr.html` 三 label 的 `@mousedown.prevent` →
  probe_label5 复现完整闪烁链(focusout@mousedown+0.2ms → menu=false@+65ms → menu=true@回焦) ——
  与第三轮埋点一致, 排除"探针测不出"的可能; 随即 `git checkout` 还原。
- **根因面结论**: 第三轮修法本身有效; 用户侧仍闪 = 资源代际未到达(长开页签不刷新)。第四轮不再
  依赖「模板与 JS 同代到达浏览器」: 收层在 JS 层单点闭环。
- **修复**: ①`add_torrent.js` mounted 挂 `window.addEventListener("mousedown", recorder, {capture:true})`
  记录最近落点是否 `label[for]`(unmounted 对称移除); 新增 `_popBlurShouldHold(ids)`(activeElement ∈
  本族 id → true; 记录 350ms 内且 forId ∈ 本族 → true); `addPopBlurClose` 定时器体首行接守卫
  (三字段 id 名单)。②`dialogs.js::metaCatBlurClose` 同款接守卫(`["meta-category"]`)。
- **验证**: ①守卫 vs 旧模板(修饰符摘掉态): T1 按住 150ms 点 label **零翻转**焦点落位, T2 点空白照常收,
  T3 Tab 照常收(focus 开下一字段, mutex 收本字段), T4 记录 600ms 过期后 blur 照常收 —— 4/4。
  ②真实状态全量回归: 三皮肤 × 8 项(三字段开着点/关着点/未聚焦点/点空白/互斥/meta 同款)= 24/24。
- **守阵**: `test_frontend_add_combo_label_clear_mask_and_refit` 新增第 7 组(记录器挂/撤对称 + 守卫双判据
  + 350ms 上界 + add/meta 两侧定时器接守卫); `test_frontend_add_torrent_drag_drop_wiring` 第 1 组改子集
  语义(mounted 合法新增 mousedown 记录器, 不再断言"恰好等于四件套", 对称性仍由 removed == added 兜住)。
- **实测**: `commands run test.full` **2419 passed + 3 skipped / 31.86s / 覆盖率 99%**(提交前 stash→sync
  合并远端 2b10581a 后于新基线重测, 与 908fbf28 首测同数)。
- **收尾**: 坑档 `combobox-focusout-close.md` 第四轮条目(复发:2, 教训 = 修完要区分"源码修好"与"用户侧
  生效", SPA 静态资源以页面加载时刻为准; 前端行为修复尽量 JS 单点自洽); 基线切片 26-10-04-0240;
  progress 条目; kb.index 重建。

## 待办 / 观察

- **用户侧验证动作**: 服务重启后**浏览器整页强刷一次**(Ctrl+F5)再走查 —— 长开页签不刷新永远跑旧模板/JS。
  若强刷后仍闪, 请报浏览器名与版本(本轮 Chromium 实测干净, 剩余差异面只剩引擎)。
- 无新增入池项; 第三轮发现的互斥不对称已在 26-10-04-0150 修毕(本轮 U7 复验互斥双向仍正确)。
