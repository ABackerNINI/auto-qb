# 26-10-07-webui-detail-panel-followups — 详情面板 followups 四修轮

**Status:** Done
**Added:** 2026-10-07
**Updated:** 2026-10-07 11:42
**Topics:** webui-detail-panel-followups
**Summary:** 用户点名 4 个详情面板缺陷的修复轮: 单会话单分支(fix/webui-detail-panel-followups)4 笔提交(`039ea285`→`8677a415`), 每项独立提交、红验守阵, 最后统一浏览器实测(真机 qB 116 种子, Playwright 桩)四项全 PASS、零 console 错误。改动纯 WebUI 静态层(drawer_templates.js / state.js / drawer.js / ui_feedback.js)与 test_web.py 守阵, Python 产品代码零改动; 逐笔 test.quick 2714→2717 全绿, 收口 test.full **2717 passed + 4 skipped / TOTAL 99% / 42.08s**(基线 26-10-07-1142), 新增守阵 4 个测试函数。
**Refs:** memory-bank/tasks/26-10-06-webui-detail-panel.md,memory-bank/tasks/26-10-07-webui-detail-panel-audit-fixes.md,memory-bank/testing/baselines/26-10-07-1142-webui-detail-panel-followups.md,memory-bank/pitfalls/web-ui/drawer-switch-flicker.md,memory-bank/pitfalls/web-ui/aq-tip-position-clamp.md,memory-bank/pitfalls/web-ui/vif-host-node-stale.md

## 原始请求

用户点名的 4 个详情面板缺陷: ①模板选择器宽度随页签变化跳动, 带动同排元素; ②切设置页返回详情面板整幅空白; ③显式换种子闪"空态→加载态→数据"三连; ④tooltip 锚点被轮询重建/移位后错位(含键盘路径)。

## 思考过程与决策

- 延续前史拍板形态(独立修复轮独立档案、与前史档案互引), slug `webui-detail-panel-followups` 查重(本 clone + 跨工作区)无同名 → 新建。
- 每项独立提交并配红验守阵(先红后绿), 四项全绿后统一真机浏览器验证, 避免逐项起桩开销。
- 三项坑档回写: ②新建 `vif-host-node-stale.md`(v-if 拆建后宿主节点失效是清单外新坑); ①并坑 `drawer-switch-flicker.md`(显式换种子重入 = 「打开类入口重入语义」判别第三案); ④并坑 `aq-tip-position-clamp.md`(显示期锚定保活是同坑新路径)。

## 实现计划

四项串行: 每项先写失败守阵(红验)→ 修 → 守阵转绿 → test.quick 全绿 → 提交; 全部完成后起桩(`commands run dev.webui`)Playwright 真机 qB 116 种子统一实测四项 + console 零错误。

## 子任务状态表

| # | 提交 | 缺陷 | 改动 | 守阵 | 状态 |
|---|------|------|------|------|------|
| 1 | `039ea285` | 模板选择器宽度随页签跳动 | `.dt-select` 定宽 240px(+`.dt-summary` flex-basis 240px): 原生 select 自动最小宽=最宽 option, `dtTplOptions` 按页签变化导致宽度跳动(shared/drawer_templates.js) | `test_drawer_tpl_select_fixed_width_tab_independent` | Done |
| 2 | `195e1299` | 切设置页返回详情面板空白 | aside 被 v-if 拆掉重建后变体宿主换节点而 `_dtMounted` 持旧宿主, general/content 页签无通知源永不自愈; watch(drawerVisible) 种子支路进场补 `$nextTick(_dtSync)` 重挂(shared/state.js) | `test_drawer_seed_reentry_variant_remount` | Done |
| 3 | `199d0737` | 显式换种子闪空态 | openTorrentDrawer 整体重建清列表产生三连闪; 已开换目标改交棒 `_switchDrawerTarget` 软切换单点(旧数据撑几何+160ms 延迟遮罩), 同目标重入短路零副作用; 冷启动重建 trackers/files/peers loading 按 initialTab 同帧置位(shared/drawer.js) | `test_frontend_drawer_open_switch_no_empty_flash` | Done |
| 4 | `8677a415` | tooltip 锚定漂移 | place() 定位单点 + reacquire() 语义重解析(data-aq-tip 同文案新节点按视口中心距旧矩形最近) + watch()/tick() rAF 帧环(断链重解析、四轴漂移>1px 重定位、可见期每帧仅 1 次 getBoundingClientRect); 键盘 focusin NaN 坐标路径由矩形基准兜住(shared/ui_feedback.js) | `test_aq_tip_anchor_watch_and_reacquire_wired` | Done |

## 实测汇总

- 逐笔 test.quick 全绿: 2714→2715→2716→**2717** passed(各笔 4 skipped)。
- 收口 test.full: **2717 passed + 4 skipped / 覆盖率 TOTAL 99%(16061 语句 / 166 未覆盖 / 5496 分支 / 144 partial)/ 42.08s** —— 基线切片 `26-10-07-1142-webui-detail-panel-followups`(相对上基线 26-10-07-1003: passed +4 = 本轮 4 个新守阵函数, 与逐笔递增吻合)。
- 浏览器实测: 真机 qB 116 种子, Playwright 桩, 四项全 PASS、零 console 错误(截图存临时目录, 不作长期证据)。

## 进度日志

- 2026-10-07: 4 个子任务串行完成 4 笔提交(逐笔内容见上表), 每步红验守阵 + test.quick 全绿; 随后真机浏览器实测四项全 PASS。
- 2026-10-07 11:42: 收尾 DoD —— test.full 实测记基线切片 `26-10-07-1142`; 本档案独立立档(与前史两档案互引); activeContext 切片 26-10-06-0751 补 followups 轮; progress 沉淀一条; 坑档三处回写; kb.index 重建。
