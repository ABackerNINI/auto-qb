# 26-10-02-webui-unsaved-changes-guard — 设置页未保存改动防护(报告路线 U1-b: 自绘框 + 原生兜底)

**Status:** Done
**Added:** 2026-10-02
**Updated:** 2026-10-02 06:19
**Topics:** webui-settings-unsaved-changes
**Refs:** memory-bank/issues/26-09-25-1702-bug-webui-settings-unsaved-changes-lost.html, memory-bank/reports/26-10-02-0508-report-webui-unsaved-changes-guard.html
**Summary:** issue 26-09-25-1702 的实施档 —— 键盘刷新(F5/Ctrl+R)弹自绘三选一框(保存并刷新/放弃并刷新/留在此页), 其余真实导航靠原生 beforeunload 兜底(随 cfgDirty 挂摘), 刷新即清零不做草稿恢复; 静态守阵 +1, test.full 2289 passed / 99%

## 原始请求

- 2026-10-02 05:08: 用户指派认领 issue 26-09-25-1702(设置页有未保存改动时刷新会丢改动, 无任何提醒), 先出方案调研报告。
- 2026-10-02 05:5x: 「按推荐实施 26-10-02-0508-report-webui-unsaved-changes-guard.html, 做 U1-b 自绘框 + 原生兜底」——
  即: 报告 §7 的落地路径照做(判据/清零语义/挂载时机), 但框的形态由报告倾向的 U1-a(纯原生)换成 U1-b。

## 思考过程与决策

1. **为什么两条链缺一不可**: JS 取消不了真实导航, 唯一能取消导航的钩子是原生 `beforeunload`;
   而原生框文案由浏览器给(防钓鱼)、只有「留下/离开」两选项, 说不清"可以先保存"。
   ⇒ 键盘刷新走自绘(可定制 + 多「保存并刷新」这一支), 其余导航走原生兜底 —— 这是 U1-b 明知的代价(报告 §6"双框不一致")。
2. **判据不另立**: 沿用 `cfgDirty`(全树 JSON 对比 baseline), 与 actbar「有改动还没保存」同源单点, 零新增状态机。
3. **改动范围**: 三选一按钮是既有两钮 modal 没有的能力 —— 加 `extraText` 第三个钮(缺省不渲染)。
   与 `confirmDialog`(布尔)/ `promptDialog`(字符串)的契约分开, 老调用点零变化。
4. **挂载范围(唯一偏离报告 §8-3 的决定)**: 报告倾向「设置页且 dirty」, 实施为**只要 dirty** ——
   配置树内存常驻, 改完没保存切到辅种页那棵树仍是脏的, 按页收窄会在那条路径上留一个静默丢失的洞;
   dirty 只可能在设置页被造出来(保存/放弃/登出即清零), 判据本身已足够窄。
5. **去重**: 自绘框里点了任一「刷新」分支必须先 `cfgGuardRelease()` 再 `location.reload()`,
   否则紧接着的 reload 会再弹一次原生框(双框连击)。
6. **不做草稿恢复**(报告 §4 决定二): 配置树含 `qbittorrent.password`, 一律不进 Web Storage; 守阵里加了反向断言钉住。

## 实现计划

- [x] `ui_feedback.js`: `_modalInit` 加 `extraText`; 新增 `confirmThreeDialog`(返回 `true | "extra" | false`); `resolveModal(choice)` 认 `"extra"`
- [x] `tpl/popovers.html`: 第三个钮(`v-if="modal.extraText"` → `resolveModal('extra')`, 按破坏性分支渲染)
- [x] `config_editor.js`: `cfgGuardActive` / `cfgGuardSync` / `cfgGuardRelease` / `_cfgOnBeforeUnload` / `_cfgOnReloadKey` / `cfgReloadGuard`; `cfgSave` 改返回成败布尔
- [x] `lifecycle.js`: mounted 注册 `_cfgOnReloadKey`(排在快捷键引擎之后), unmounted 撤除 + `cfgGuardRelease()`
- [x] `state.js`: `watch.cfgDirty` → `cfgGuardSync(v)`(原生兜底随脏态挂摘)
- [x] `tests/test_web.py`: 新增 `test_frontend_unsaved_changes_guard_wiring`(六类不变量 + 反向断言), 同步头部测试计划清单
- [ ] 报告 §8-4 的 chromium 实弹走查(`commands run dev.harness`, 记 dialogs 计数)—— 本轮未做, 留给下次

## 子任务状态表

| # | 子任务 | 状态 | 备注 |
|---|---|---|---|
| 1 | 三选一框基础设施 | Done | ui_feedback.js + popovers.html, 老契约零变化 |
| 2 | 守卫逻辑(config_editor.js) | Done | 含 cfgSave 返回值改造 |
| 3 | 接线(lifecycle 监听 + state watcher) | Done | 注册序在快捷键引擎之后 |
| 4 | 静态守阵 + 全量测试 | Done | +1 守阵; test.full 2289 passed / 99% |
| 5 | 浏览器实弹走查 | Open | 待起真浏览器(F5 → 自绘框 1 次; 关标签 → 原生框 1 次) |

## 进度日志

- 2026-10-02 05:5x — 开工同步(develop @ 300f8aa5), 读报告 + 复验锚点(`config_editor.js` 的 `cfgDirty/cfgLoad/cfgSetTree` 与 `polling.js::startPolling` 的 `cfgLoad()`)。
- 2026-10-02 06:0x — 四处代码改完 + 守阵写就: `test.one -k unsaved_changes_guard` 1 passed; `test.quick` 2289 passed + 3 skipped(38.4s); `test.full` 2289 passed + 3 skipped / 99%(47.7s)。
- 2026-10-02 06:0x — 收尾回写: issue 26-09-25-1702 翻 Done(状态变更日志 + 修复后补充), 立本档, 建基线切片, 收录 pitfall `web-ui/unsaved-guard-reload-keys.md`, 重建索引。
