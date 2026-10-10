# 基线: WEBUI 选中×触发一致性 S5(e2e 参数化矩阵, 三张网闭合)

- 主题: [../../activeContext/26-10-10-2103-webui-selection-trigger-parity.md](../../activeContext/26-10-10-2103-webui-selection-trigger-parity.md) · 计划 26-10-10-2001(S5, R5)
- 本笔只动 `e2e/`(新增 `trigger-scope.spec.mjs` + `lib/scope_ring.mjs` + `lib/gestures.mjs`; 上移 menus.spec 本地手势), **不改任何生产代码** —— pytest 覆盖面与 S4 基线(26-10-10-2306, 3112 passed / TOTAL 99%)逐位一致, 不另起 pytest 数字。
- **e2e 实测 (Windows, 单次采样)**:
  - `npm run test:e2e:fast`: **64 passed**(50+14, 1.6m) —— 新矩阵 14 条全进 @fast;
  - `commands run dev.e2e` 全量: **150 passed + 10 skipped, 0 failed**(3.7m) —— 136 既有 + 14 新增, 无回归;
  - menus.spec 手势上移后单独复跑: 20 passed / 6 skipped(on 模式默认轮)。
- 矩阵断言三层(计划 §5.4): 下发载荷拦截比对 / 审计环净(`scope_ring.expectScopeRingClean`) / 文案明示(toast countText + 菜单变体)。S4 完成判据「审计模式造不一致→环里出现记录」以 T-7 真机红验落地。
- 实施期纠偏两条(首跑即红即改): ① T-4 初版预设「选中 1 组右键该组→批量菜单」为误 —— C2 口径下集合==锚点范围渲染**单组支**, 已拆 T-4a(单组支)/T-4b(两组→bulk); ② 登记表页面暴露形态是 `window.AQB_TRIGGERS.methods.triggerDefs()`(methods 包装层), 非直接挂函数。
