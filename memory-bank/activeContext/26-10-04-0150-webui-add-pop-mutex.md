# 添加种子三浮层互斥补双向(issue 26-10-04-0130 认领, 方向二)

> 摘要: 用户指派认领 issue 26-10-04-0130(上一轮走查发现的计划外既有缺口), 按建议方向二实施:
> 抽 `closeAddPopsExcept(kind)` 三浮层互斥单点, 三开层各调一次; 守阵补「互斥双向」静态断言。
> 复验锚点仍复现(01:30 取证的互斥单向缺口原样); 修复后 Playwright 走查 6/6, 终态全部单浮层。
> 最后活动: 2026-10-04 01:50

## 已完成 (2026-10-04)

- **认领与复验**: 重跑锚点 —— `add_torrent.js` 三开层方法互斥写法与 issue 取证逐行一致, 缺口
  仍复现(openAddPathPop 收 cat/tag; openAddCatMenu 只关 addTagMenu、openAddTagMenu 只关
  addCatMenu, 均不关 addPathPop)。
- **修复(方向二)**: 新增 `closeAddPopsExcept(kind)`(kind = 保留的浮层; 收层带 Hi 复位, 与
  Esc 退栈/失焦收层同款); `openAddCatMenu`/`openAddTagMenu`/`openAddPathPop` 三处开层各调一次,
  各自保留 Hi 复位与悬停门限坐标复位。模板无改动(三个开层方法就是全部开层入口, 走查已核)。
- **守阵**: `test_web.py::test_frontend_add_combo_blur_close_and_fit` 补第 6 组「互斥双向」
  静态断言(closeAddPopsExcept 单点存在 + 三分支覆盖 + 三开层各调一次), 文件头「测试计划」同步。
- **验证**: ①`commands run test.full` 2419 passed + 3 skipped / 32.46s / 覆盖率 99%(合并远端
  4805f5f5 后重测); ②Playwright
  走查(scripts/ui_harness.py 桩后端, DOM 判浮层显隐): 6/6 —— 路径开→focus 分类、分类开→focus
  标签、标签开→focus 路径(修复前反向缺口)、点标签 label 转发、Tab 迁移, 终态全部单浮层;
  走查同时实测复现了 issue 记录的面板拦截现象(click 迁移被 `subtree intercepts` 拦, 属面板
  几何覆盖, 焦点迁移路径不受影响)。
- **收尾**: issue 档案状态 Open→Done(复验 + 修复后补充 + 日志两行) + issues/_index.md 重建
  (kb.index); progress/implemented-webui.md 新条目; 上一轮切片的「待办」条目迁出; 基线切片
  [testing/baselines/26-10-04-0150](../testing/baselines/26-10-04-0150-webui-add-pop-mutex.md)。

## 待办 / 观察

- 真机(真实 qB + 真实数据)走查仍待用户执行。
- 本轮未 commit —— 等用户显式「提交」。
