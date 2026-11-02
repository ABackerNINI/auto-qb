# 4823 —— toast 进行中→结果统一两段式(5 条链路)后全量

> 摘要: toast 进行中→结果统一两段式(5 条链路)后全量
> 基线时间: 2026-11-02 09:47
**Refs:** memory-bank/testing/baselines/26-11-02-0911-webui-flux-message-surface.md

## 验收数字

`commands run test.full` 实测(2026-11-02 09:47, 十轮「统一收」: 五条链路并进两段式):

```text
TOTAL                                                22521    152   7726    135    99%
4823 passed, 10 skipped in 217.27s (0:03:37)
```

- 口径注记: 10 skipped 为既有跳过面(平台条件跳过, 与本轮改动无关); 覆盖率 99%。
- 守阵 `tests/test_webui_static_skins.py` 26 passed: 第 20 项把九轮那三条换成「统一收」三判据 ——
  ① 全 `shared/*.js` 里 `{ sticky: true }` 只允许出现在统一工厂 `_runningToast` 体内(手搓即红);
  ② 归档条文案不许含「进行中/正在/等待 tracker/确认中」(剥注释后只查字面量);
  ③ `_settleRunningToast(` 全 shared 汇总调用点 ≥10(当前 12)。
  红验三种破坏形态各精确报红、还原后绿(手搓 sticky / 文案改进行时 / 转移整条退回原位改字)。
- 实测(桩服务 + Playwright, 1440×950, 真实右键手势, 逐帧采样"上条底 - 下条顶"):
  - 导出: 峰值 2 条、双条帧 109、**重叠帧 0**; 文案 `导出已开始 / 已导出`。
  - 批量跳检: 峰值 2 条、双条帧 94、**重叠帧 0**; `批量跳检已提交` + `已执行 批量跳检(2 个目标)`。
  - 删除(前置汇报+删除): 峰值 **3 条**(已投递 → 汇报完成·开始删除 → 已删除)、**重叠帧 0**。
  - 转移: 桩服务未配置转移目标(子菜单显示「未配置目标, 去设置」), **未端到端实测**;
    改动与其余三条同构(同一工厂 + 三处 `_settleRunningToast`), 由 node 探针覆盖结算分型。

## 本改动面

- `shared/commands.js`: 新增统一原语 `_runningToast(text)`(唯一 sticky 工厂, 返回 `{tid,text,at}`)
  与 `_settleRunningToast(ref, kind, text, ms, minShow=900)`(归档成 info 留队列 4s + 结果另起一条),
  取代只服务强制汇报的 `_settleDeliveredToast`。强制汇报 / 导出两条链路改走它; 强制汇报投递文案
  去掉「tracker 确认中」(归档后不成立), 导出改「导出已开始: N 个 .torrent 文件」(去省略号)。
- `shared/delete_flow.js`: `_reannounceAll` 的进行中条改「强制重新汇报已投递」(原「进行中…等待
  tracker 确认」归档后不成立), 失败/成功两处结算改 `_settleRunningToast`(成功时 await 使删除动作
  最多推迟 900ms, 只在桩服务级快回执时发生)。
- `shared/drawer.js`: 批量跳检进行中条改「批量跳检已提交」, 结算改两段式。
- `shared/transfer_flow.js`: 转移进行中条改「转移已开始」, 三处结算(失败/跳过/全成)改两段式;
  投递抛错仍原位落失败(没有「已投递」可归档)。
- `tests/test_webui_static_skins.py`: 第 20 项三判据替换 + 文档串同步。
- `tests/test_transfer_flow_confirm.py`: node 探针补 `_runningToast`/`_settleRunningToast` 桩,
  `vm.toasts[0]` → `lastToast()`(结果条现在是最后一条, 归档条排在它前面)。
- `tests/test_webui_static_dom_panel.py`: 删除链电池的 `RA_BASE` 补两个空桩。
- `memory-bank`: `conventions/webui.md` 新增「进行中 → 结果 = 统一两段式(十轮)」段(含两条硬口径、
  5 条链路清单、投递抛错的例外)。

## e2e 同步

- `commands run dev.e2e -- e2e/menus.spec.mjs -g "W4 多选导出|W2 批量限速|块E"` → **12 passed**
  (prism/atlas 各 6: 导出回执 / 限速回执 / 非活跃置灰 / 混选放行 / 删除确认框两例)。
- 九轮那条 `e2e/site-alerts.spec.mjs -g "命令结果图标"` 本轮未再改(回执文案与结构未动)。
