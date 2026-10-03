# WEBUI qB 流量图三挂点并入底部详情抽屉 (待用户提交)

> 摘要: 用户要求「qb流量图复用种子流量(详情)的模式/样式/高度, 特别是高度跟随详情窗, 替换当前的弹出窗口」。
> 四项拍板: ①并入详情抽屉 ②与详情抽屉**共用高度**(drawerHeightPx) ③**全部三挂点** ④抽屉**提升为全局**(任意页可开)。
> 落地: 删除 `tpl/qb-traffic.html` 两个模态弹层(全局/分组) -> 抽屉新增 `kind === "traffic"` 形态(`drawer.scope`
> 记挂点 global/group), 与种子详情的「流量」页签**共用同一段正文块**(`qbTrafficActive` -> `qbCur*`, 建图落点统一
> `ref="qbChartHost"`); `.drawer-dock` 落点自 `tpl/torrents.html` 上提为 app 级分片 `tpl/dock.html`(三清单同步),
> 可见性改由 `drawer.js::drawerVisible` 把守(种子详情限种子页 / 流量图全局)。图高改量 `host.clientHeight` 并让
> ResizeObserver **宽高双观察** -> 拖拽抽屉顶缘调高, 图实时跟着长(实测 378px 抽屉 -> 图 194px; 拉到 620px -> 图 436px)。
> 去掉 `qbHistOpen` / `qbGroupOpen` 两个独立开合字段(统一 `drawer.open + kind + scope`), Esc 退栈/escBusy/登出清理
> 归一到 `closeDrawer` + `_qbTeardown`。三主题 CSS 成对改。**test.full 2423 passed + 3 skipped / 99%**;
> 浏览器冒烟(Playwright + ui_harness)三形态实测: 全局流量图渲染 + 高度跟随 + 种子详情流量页签 + 默认页布局未坏, 零 pageerror。
> 未验证面: 真机(真实 qB 数据/24h 与 30d 换窗/轮询续拉)待用户走查; 原「弹窗滚轮穿透」报告里的 12 遮罩模态现为 10。

> 最后活动: 2026-10-04 04:20

**正在进行**: 无 —— 实现 + 测试 + 浏览器冒烟均完成, **已提交 `659eada8`(Gitee develop, 已推)**。
提交前远端已推进到 800ccba2(另一 clone 的 .modal-members 死类移除, 同改 atlas/console views.css),
按 sync 失败行配方 stash -u -> sync -> stash pop 合流(无冲突), 改动落在 800ccba2 之上; 合并后复跑
test.full 2423 passed + 3 skipped / 99%。

**待办**: ①用户真机走查(高度跟随 / 三形态 / Esc / 切页后流量图仍在); ②原弹窗滚轮穿透报告(26-10-04-0128)的遮罩计数
与弹窗清单需随之更新(该报告停在拍板, 未开工, 实施时一并核对); ③主 issue 26-09-27-1248 真机观察期后收口;
④`kb.check` 报的切片数债务(91 > 70)待另开会话清理; ⑤`scripts/ui_smoke.cjs` 头注的 NODE_PATH
(`.workbuddy-ai/binaries/node/workspace/node_modules`)在本 clone 不存在, 属文档漂移, 未顺手改(范围守恒)。
