# 4006 passed + 2 skipped(根) —— 设定位置对话框二修: 点选只回填 + 基线 360 + 高度过渡

> 摘要: 设定位置对话框二修(点选候选只回填 / 手输回车仍提交 / 收层态基线 360px / 开层高度走 200ms 过渡)后全量基线
> 基线时间: 2026-10-29 00:53
**Refs:** memory-bank/plans/26-10-29-0041-plan-webui-move-dialog-pick-geometry.html

## 验收数字

`commands run test.full` 实测输出:

- 汇总行: **4006 passed, 2 skipped in 144.97s (0:02:24)**
- TOTAL 表: `20981  98   7088   100    99%`(语句 / missed / 分支 / partial / 覆盖率)
- 覆盖率门槛 99% 达标, 无 FAIL 行; 零失败零回归
- e2e 单跑(`commands run dev.e2e` 传 spec 名, 双皮肤 × 2 用例): **4 passed (14.2s)**
  - 几何实测(1440x900): 收层态 **H0 = 360**(prism) / **360**(atlas); 开层终值 **H1 = 515**(prism) / **513**(atlas)
  - 过渡采样: ResizeObserver 抓到 **12 帧**, 其中 **6 帧**严格落在 (H0, H1) 之间 = 高度确为过渡而非瞬跳
  - 列表 `maxHeight` 未被限高截断(**210px**), 输入行下方预留 **272px**, 下拉底缘在 body 客户区内(-12px)

口径注记: passed/skipped/覆盖率数字由 agent 从本次实测输出誊写; 相对上基线的逐位对比不写(看差值 `commands run kb.baseline -n 2`)。

## 本改动面

用户两条报障(点选下拉选项即移动 / 窗口太小且点下拉高度跳变)的落点, 7 个源文件 + 2 个测试件:

- `src/auto_qb/webui/static/shared/drawer.js` —— `moveApplyPath` 去掉 `submitMoveDialog()`(点选只回填); `onMovePathKeydown` 增 `onEnter`(手输回车仍提交); `openMoveDialog` 置 `moveSuppressOpen`(打开只聚焦不展开); `openMovePathMenu` 首行消费抑制标志 + 触发 `_movePopSettle`(过渡后重测限高); 新增文件级常量 `MOVE_POP_SETTLE_MS = 240` 与方法 `_movePopSettle`
- `src/auto_qb/webui/static/shared/add_torrent.js` —— `comboKeydown` 回退分支改 `(ctx.onEnter || ctx.onPick)(v)`(可选钩子, 缺省回落), 头注 ctx 清单补一行; 其余四个下拉不传, 行为零变化
- `src/auto_qb/webui/static/shared/state.js` —— 新增根数据 `moveSuppressOpen`
- `src/auto_qb/webui/static/shared/tpl/move-dialog.html` —— 按钮 `:disabled="moveBusy || !movePathInput.trim()"` + 头注补二修口径
- `src/auto_qb/webui/static/{atlas,console,prism}/css/dialogs.css` —— 三皮肤成对: 收层态 `min-height: min(360px, calc(100vh - 120px))`、动作条 `margin-top: auto` 钉底、`padding-bottom` 200ms 过渡、`prefers-reduced-motion` 关过渡
- `tests/test_webui_static_dom_panel.py` —— move 用例补 8 条断言(点选不提交 / `ctx.onEnter` / 按钮置灰 / 抑制标志与消费 / settle 常量 / 三皮肤 min-height+transition+动作条钉底)
- `e2e/move-dialog-fit.spec.mjs` —— 重写: 收层态基线 + ResizeObserver 过渡采样 + Esc 回落 + 点选零写请求 + 点按钮一次写请求(route 计数 + cmd 回执桩)
