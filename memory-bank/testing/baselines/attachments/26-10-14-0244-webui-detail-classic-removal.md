# 2026-10-14-0244 — 四内容页签经典 UI 与流量页签变体移除基线

> 基线时间: 2026-10-14 02:44

> 摘要: 用户令「移除种子详情面板除『流量』页的 4 个经典 UI, 以及『流量』页的除经典外的 UI, 以及 qb 流量页的除经典外的 UI」全量验证。终态 = 四内容页签(常规/Tracker/用户/内容)**变体独档**(缺省 = 该页签首个变体 01/04/07/10), 流量页签(含 qB 全局/分组挂点)**经典独档**(变体 13/14/15 已删); 「哪些页签还有经典」收成注册表单点 `CLASSIC_TABS`/`defaultSel`/`choices`, 渲染失败兜底由 classic 改为该页签缺省档。删除 5 个文件(3 流量变体 + drawer_tabs.js + drawer-tabs.html)+ 改 27 个源文件; 三皮肤死 CSS 清 144 条; 守阵改 6 个 pytest 函数 + 7 份 e2e spec。**另修一个被本变更暴露的既有潜伏 bug**: 变体表格体桥(Teleport)在「拆桥」与「拆它的锚」同帧发生时 Vue 运行期崩溃(`Cannot destructure property 'bum' of 'e' as it is null`, 合并开关/视口门跨越必现)——合并开关与视口门跨越改为先熄桥、下一拍再翻状态。档案见 Refs。

**Refs:** memory-bank/tasks/26-10-14-webui-detail-classic-removal.md, memory-bank/activeContext/26-10-14-0204-webui-detail-classic-removal.md

## 实测

| 项 | 结果 |
|---|---|
| `test.full` | **3197 passed / 4 skipped, 0 failed**(TOTAL 99%, 覆盖率 98.65%) |
| 前端静态守阵(skins + dom_panel + dom_page) | 全绿 |
| `dev.e2e` 真浏览器 | **236 passed / 10 skipped, 0 failed**(6.6m) |

## e2e 同轮改版(锚点全部重钉)

- 空态容器: 变体自带 `.dt07-empty`/`.dt04-empty`/`.dt10-load`(经典 `.empty` 已随经典链删除), `drawer-switch-no-flash` 按页签给选择器。
- 表 id: `drawerPeer/drawerTracker/drawerFile` → `drawerPeerV07/drawerTrackerV04/drawerTrackerV06/drawerContentV10`(几何/交互/列偏好用例改钉变体表)。
- 右键手势: 模板菜单的右键目标从「.drawer-body 中心」改为「**行**」——表头 `@contextmenu.stop` 独占右键, 点中心会命中表头弹列菜单; 且点完菜单项后须等 `.ctx-menu` **离场**(pop 过渡期间仍盖在原位, 会吃掉随后的拖宽/排序 mousedown)。
- 合并双列: 两列从「经典组件 + 变体宿主」改为同为变体宿主, 断言改钉 `.dt-host[data-dt-host=...]` + `.dt-tpl`; 列选择器恢复入口断言改钉「当前选中变体表」分组(经典三表分组已随经典表注册删除)。

## 坑与意外

- **既有潜伏 bug 被暴露**: `drawer_templates.js` 的桥在「v-if 翻转」与「所属 DOM 分支(v-if=dtSplitOn)翻转」同帧时, Vue 拆桥会撞上 Teleport 目标被同帧移除 → 运行期崩溃。经典渲染链在时四内容页签默认**不带桥**(classic 无 tableId), 故从不触发; 经典移除后默认就带桥, 100% 暴露。修法 = `_dtBridgesOff()` 先熄灯一帧, 再翻 `drawerMerge`/`dtWinW`。
- **变体排序与经典不同**: 07 默认按 upspeed 降序(经典 = 后端原序), `dt-live-update` 的「首行速度实时」断言必须按对端地址(10.0.0.0)定位行, 否则探到 upspeed 并列首行里 dl_speed 恒定的那一格, 两轮输入完全相同 → 误报。
