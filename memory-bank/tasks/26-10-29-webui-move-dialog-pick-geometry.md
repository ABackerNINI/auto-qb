# 26-10-29-webui-move-dialog-pick-geometry — 设定位置对话框八修: 点选只回填 + 几何基线/过渡 + 增长只朝下 + 滚动条开关挂事实 + 面板非交互区不抢焦点 + 落点归属 + 高亮滚动跟随不碰祖先

**Status:** Done
**Added:** 2026-10-29
**Updated:** 2026-10-29
**Summary:** 「设定位置」对话框八轮修: ①点选候选只回填(移动只由按钮/手输回车发起); ②收层态基线 243→360px, 开层预留从 0↔272 硬切改为 200ms 过渡, 打开不再自动展开; ③开层增长只朝下(遮罩改 flex-start + margin-top 复刻居中偏移), 治「点下拉框, 下拉框出现后自动弹回」; ④⑤滚动条开关挂「面板是否存在」(`:has(.add-pop)`)而非开合状态, 治「下拉出现/消失时闪一下滚动条」; ⑥面板内非交互区(`.pop-head`/`.pop-empty`)不许抢焦点 —— 焦点纪律挂在共享模板的面板根, 治「点面板头面板就收了」; ⑦**落点归属** —— 组件根挂 `@click.stop`, 治「按下与抬起落在不同元素时 click 目标是公共祖先、冒泡到 window 兜底把面板关掉」; ⑧**高亮滚动跟随不许碰祖先** —— `_hiScroll` 弃 `scrollIntoView` 改手动差值调 `scrollTop` 并以菜单根为界, 治「选中过路径后再点下拉, 弹窗文案从上往下滑一次」。
**Topics:** webui-move-dialog-pick-geometry
**Refs:** memory-bank/plans/26-10-29-0041-plan-webui-move-dialog-pick-geometry.html, memory-bank/pitfalls/web-ui/dialog-geometry-jump.md, memory-bank/pitfalls/web-ui/combobox-focusout-close.md, memory-bank/testing/baselines/26-10-29-0149-webui-move-dialog-pick-geometry.md, memory-bank/testing/baselines/26-10-29-0224-webui-move-dialog-pick-geometry.md, memory-bank/testing/baselines/26-10-29-0249-webui-move-dialog-pick-geometry.md, memory-bank/testing/baselines/26-10-29-0314-webui-move-dialog-pick-geometry.md, memory-bank/testing/baselines/26-10-29-0348-webui-move-dialog-pick-geometry.md, memory-bank/testing/baselines/26-10-29-0412-webui-move-dialog-pick-geometry.md

## 原始请求

1. 「WEBUI 种子设定位置窗口点击下拉框中的选项就触发移动, 需要改成点击『设定位置』按钮后移动」
2. 「WEBUI 种子设定位置窗口太小, 点击下拉框高度跳变」
3. grilling 定稿后的补充口径: 「Q5 窗口再大气一点 / Q6 设计要简洁明了, 明显的交互逻辑不必写 / Q7 不自动展开」+「另外窗口不能『跳变』, 要用动画自然过渡」
4. 三修报障: 「WEBUI种子设定位置窗口点击下拉框, 下拉框出现后自动弹回」
5. 五修报障: 「下拉框消失时弹窗仍会有一瞬间出现滚动条」
6. 「缺陷一并修复」(指排查三修时顺带报给用户的既有缺陷: 点面板头「选择保存位置」面板就收了)
7. 「『无焦点时点下拉, 面板出现即弹回』回归了 / prism 正常, atlas 异常」→ 复核实为旧桩进程(验错对象), 但排查中复现到**落点错位收层**这个独立缺陷, 用户确认后一并修
8. 「选中新路径后再次点击下拉框, 弹窗中的元素会从上往下滑动出现一次; 输入框中无文字时正常」

## 思考过程与决策

计划全文与 D1–D7 拍板见 `memory-bank/plans/26-10-29-0041-plan-webui-move-dialog-pick-geometry.html`。要点:

- 两条报障同源: ①`moveApplyPath` 回填后直调 `submitMoveDialog`(点选即移动); ②19 日首修为「开层时给 body 预留 272px」, 条件类一切换 = 高度 ±272px 硬跳, 收层态又是 243px 小个子。
- 三条硬取舍:
  1. **点选只回填, 手输回车仍提交** —— 回车是明确确认手势, 不该逼用户再挪鼠标; 用 `comboKeydown` 的可选 `ctx.onEnter` 钩子分开两条路, 其余四个下拉不传(零变化)。
  2. **不选「高度恒定 + 常驻预留」** —— 打开不自动展开后, 恒定高会在第一眼露出 ~270px 空箱, 而用户要求不写说明文案填它; 改「基线抬升 + padding 过渡」, 大气/不跳/有动画三条同时满足。
  3. **body 不能 `flex:1`** —— 全局 `* { box-sizing: border-box }`, padding 会长在固定高度里, 内容反被挤成滚动条; 高度增长只能靠 body 的 auto 高度随 padding 走, 动作条用 `margin-top:auto` 钉底。
- 实施时纠正初稿一处: 面板入场**不需要**新增 `.pop-enter-*` 规则 —— `.pop-menu` 自带 `animation: drop-in .12s`, 再加 transition 是死规则且与动画争同一组属性。

## 实现计划

1. **S1 行为收口**: `moveApplyPath` 去提交; `openMoveDialog` 置 `moveSuppressOpen`; `openMovePathMenu` 首行消费 + 触发 settle; 模板按钮空态置灰。
2. **S2 共享单点**: `comboKeydown` 回退分支 `(ctx.onEnter || ctx.onPick)(v)` + 头注 ctx 清单补一行。
3. **S3 几何**: 三皮肤成对(基线 min-height 360 / 动作条钉底 / padding 200ms 过渡 / reduced-motion 关) + `MOVE_POP_SETTLE_MS=240` 与 `_movePopSettle`。
4. **S4 守阵**: 静态 8 条新断言(点选不提交 / onEnter / 置灰 / 抑制标志 / settle 常量 / 三皮肤 CSS)。
5. **S5 e2e**: 收层态基线 + ResizeObserver 过渡采样 + Esc 回落 + 点选零写请求 + 按钮一次写请求。
6. **S6 收尾**: 全量测试 → 基线切片 → 坑档 → 回写。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 行为收口(点选只回填 / 不自动展开 / 空态置灰) | Done(2026-10-29) |
| S2 | `comboKeydown` 加 `ctx.onEnter` 钩子 | Done(2026-10-29) |
| S3 | 三皮肤几何: 基线 360 + padding 过渡 + settle 重测 | Done(2026-10-29) |
| S4 | 静态守阵改写 + 扩容 | Done(2026-10-29) |
| S5 | e2e 重写(几何/过渡/点选不移动) | Done(2026-10-29) |
| S6 | 全量测试 + 基线切片 + 坑档 + 回写 | Done(2026-10-29) |
| S7 | 三修: 开层增长只朝下(遮罩 flex-start + margin-top 补偿) | Done(2026-10-29) |
| S8 | 三修守阵: 静态三皮肤成对 + e2e 几何不变量/连点两次 | Done(2026-10-29) |
| S9 | 四修: 开层期 body 关滚动(overflow:hidden), 治过渡期闪滚动条 | Done(2026-10-29) |
| S10 | 四修守阵: 静态成对断言 + e2e 逐帧滚动条采样 | Done(2026-10-29) |
| S11 | 五修: 滚动条开关改挂「面板是否存在」(`:has(.add-pop)`), 覆盖离场淡出 | Done(2026-10-29) |
| S12 | 五修守阵: 静态断言改 `:has` + e2e 收层全过程逐帧采样 | Done(2026-10-29) |
| S13 | 六修: 焦点纪律挂面板根(`@mousedown.prevent`), 治点面板头/空态就收面板 | Done(2026-10-29) |
| S14 | 六修守阵: 静态面板根断言 + e2e 两条配对(头点击 / 空态点击) | Done(2026-10-29) |
| S15 | 七修: 组件根挂 `@click.stop`, 治按下/抬起落点不同时 click 目标=公共祖先 → window 兜底收层 | Done(2026-10-29) |
| S16 | 七修守阵: 静态输入行根断言 + e2e 两变体 + 反向守门(点组件外仍收层) | Done(2026-10-29) |
| S17 | 八修: `_hiScroll` 弃 `scrollIntoView`, 手动差值调 `scrollTop` 并以菜单根为界 | Done(2026-10-29) |
| S18 | 八修守阵: 静态 `_hiScroll` 禁令断言 + e2e 逐帧 body 滚动/文案位移 + 高亮可见反向守门 | Done(2026-10-29) |

## 进度日志

### R0 · 立档 (2026-10-29)

六步全部落地。几何实测: 收层态 H0 = 360、开层终值 H1 = 515(prism)/513(atlas), ResizeObserver 抓到 12 帧、其中 6 帧落在中间 → 高度确为过渡; 列表 210px 未被限高截断; 下拉底缘在 body 客户区内(-12px)。e2e 双皮肤全绿; 全量测试零失败, 覆盖率门槛达标(数字见基线切片 `26-10-29-0053`, 按口径不在此手抄)。坑档新增 `pitfalls/web-ui/dialog-geometry-jump.md`(条件类切高度必须带 transition + 过渡期量净空必重测)。

- 2026-10-29 01:07 设定位置对话框二修: 点选只回填/基线 360/200ms 过渡/不自动展开; e2e 双皮肤全绿, 全量零失败

### R1 · 三修: 增长只朝下 (2026-10-29)

用户报「点击下拉框, 下拉框出现后自动弹回」。探针(Playwright + 事件埋点, 三皮肤)结论: 面板**没有**被代码收层 —— 是二修把增长交给 padding 过渡后, 遮罩 `align-items:center` 让增高**上下对半扩**, 输入行连同刚展开的面板整体**上移 77px**(实测 rowTop 413→335), 面板顶到光标**原来的位置**上; 用户再点一下(双击第二次 / 以为没点中的补点)就命中候选(`@mousedown.prevent` 直取 = 回填 + 收层)或面板头(blur 收层) ⇒ 观感是"面板自己弹回"。合成零延迟点击不触发, `delay>=120ms` 连点同一屏幕坐标才稳定复现。

- 处置: 遮罩挂 `.move-dialog-mask` 改 `align-items:flex-start`, 弹窗 `margin-top: clamp(0px, calc((100vh - 360px) / 2 - 20px), calc(100vh - 560px))` 复刻收层态居中偏移(20 = 遮罩 padding; 上限扣开层总高 515 与下沿余量)⇒ 收层态屏位与居中逐像素相同(900 视口 top 仍 270), 开层只向下长。三皮肤成对改, 几何数字全在 CSS 单点。
- 实测(1440x900, 桩 300): prism 开层 rowTop 413→413 / dlgTop 270→270 / H 360→515 / 面板 top 450 ≥ 输入框 bottom 446 / 下缘 785 < 900; atlas 411→411 / 270→270 / 360→513 / 448 ≥ 444 / 783。连点两次: 面板仍在、输入框仍为空。
- 守阵: 静态 `test_frontend_move_dialog_combobox_wiring` 补 4d(模板 mask-class)+ 三皮肤 flex-start/margin-top 断言; e2e `move-dialog-fit.spec.mjs` 补几何不变量(输入行屏坐标不动 ≤2px / 上缘不动 / 面板 top ≥ 输入框 bottom / 下缘不溢出)+ 新测「同一屏幕点连点两次 · 面板不弹回」。红验: 摘掉模板 `mask-class` 一行 ⇒ 静态 1 红、e2e 4 红(连点两次那条直接 element not found)。
- 坑档: `pitfalls/web-ui/dialog-geometry-jump.md` 新增条目「条件类切高度: 增长方向必须朝下」(与上一条"必须带 transition"并列 —— 平滑的上移更坏)。

- 2026-10-29 01:36 设定位置对话框三修: 遮罩 flex-start + margin-top 居中补偿, 开层增长只朝下; 静态与 e2e 红绿双验通过

### R2 · 四修: 开层期关掉 body 滚动 (2026-10-29)

用户报「下拉框出现时弹窗有一瞬间出现滚动条」。探针(逐帧采样 scrollHeight/overflowY)结论: 预留 padding 走 200ms 过渡、面板却是瞬间挂载的 ⇒ 开层头 ~110ms 面板(256px)伸出 `.add-dialog-body` 的 padding 盒(实测溢出 256→173→108→37→7→0), body 是 `overflow-y:auto` 的滚动容器 ⇒ 闪一条滚动条, 经典滚动条还占 15px 宽 ⇒ 内容横向挤一下(无头 Chromium 是覆盖式滚动条, 占位宽恒 0, 判据只能看计算值)。

- 处置: `.modal.move-dialog.pop-open .add-dialog-body` 增 `overflow: hidden`(三皮肤成对, 只 1 条声明)。安全性: 开层期 body 溢出的**只有预留空白**(真内容在输入行上方), 裁剪位置与 auto 完全相同(都是 padding 盒底沿)⇒ 观感不变, 只是没有滚动条/横向挤压; 收层态仍 `auto`(矮视口兜底滚动不受影响), 列表自身仍可滚。
- 实测: 开层全过程 8 帧有溢出但 0 帧有滚动条占位、overflowY 恒 hidden; 终态面板底缘 -12px(未被裁)。
- 守阵: 静态补三皮肤「同一条规则里既有 padding-bottom:272px 又有 overflow:hidden」; e2e 加逐帧采样器(只从面板挂载那帧开始记)断言 overflowY 恒 hidden + 占位宽 0, 另断言收层态仍 auto。红验: 摘掉 `overflow:hidden` ⇒ 双皮肤该条立刻红。

- 2026-10-29 02:24 设定位置对话框四修: 开层期 body overflow:hidden, 滚动条不再闪; 静态与 e2e 红绿双验通过

- 2026-10-29 01:45 三修: 开层增长只朝下(遮罩 .move-dialog-mask 改 flex-start + margin-top 复刻居中偏移), 治「点下拉框, 下拉框出现后自动弹回」; 静态 4d + 三皮肤断言, e2e 几何不变量与连点两次用例, 红绿双验通过

- 2026-10-29 02:24 四修: 开层期 body overflow:hidden, 治「下拉出现时闪一下滚动条」(预留过渡期面板伸出滚动容器); 静态成对断言 + e2e 逐帧滚动条采样, 红绿双验通过; 全量 4006 passed 零失败

### R3 · 五修: 滚动条开关挂「事实」而不是「状态」 (2026-10-29)

用户报「下拉框消失时弹窗仍会有一瞬间出现滚动条」。逐帧采样(收层全过程)结论: 面板**并不立刻离场** —— `<transition name="pop">` 的淡出(`--dur-fast` ~120ms)期间它仍在 DOM 里、高度仍是 256px, 而 `.pop-open` 已摘 ⇒ 四修挂的 `overflow: hidden` 随之失效(回到 `auto`), 同时 padding 在 200ms 里往回缩 ⇒ 溢出从 0 一路涨到 **254px**(实测 0→73→139→184→212→229→241→249→254)→ 收层端又闪一次滚动条。四修只覆盖了开层那一段。

- 处置: 开关从「状态」改挂「事实」—— `.modal.move-dialog:has(.add-pop) .add-dialog-body { overflow: hidden }`(三皮肤成对)。`:has()` 在离场淡出期仍命中, 开层/离场两段一起覆盖; 面板真被移除后自动回到 `auto`(矮视口兜底滚动不受影响)。
- 守阵: 静态断言改为 `:has(.add-pop)` 规则; e2e 的逐帧采样器改成**只记面板存在的帧**(离场后回到 auto 是正确状态, 混进来会假红), 并在 ③ Esc 收层段也跑一遍, 断言收层全过程 `overflowY` 恒 hidden + 占位宽 0、收完回到 auto。红验: 把开关退回 `.pop-open` 口径 ⇒ 双皮肤「收层全过程」那条立刻红(Received 38 帧 auto)。
- 坑档: `dialog-geometry-jump.md` 同条条目改写 —— 处置改按「浮层是否存在」判, 教训补两条: ①修开层端忘收层端(离场动画让浮层多活 ~120ms); ②开关挂状态 vs 挂事实。

- 2026-10-29 02:44 设定位置对话框五修: 滚动条开关改 `:has(.add-pop)`, 收层端不再闪; 静态与 e2e 红绿双验通过

- 2026-10-29 02:41 五修: 滚动条开关从 .pop-open(状态)改挂 :has(.add-pop)(事实), 覆盖面板离场淡出那 ~120ms, 治「下拉消失时闪一下滚动条」; 静态断言改 :has + e2e 收层全过程逐帧采样, 红绿双验通过

### R4 · 六修: 面板内非交互区不许抢焦点 (2026-10-29)

用户「缺陷一并修复」—— 指的是排查三修时顺带报上去的那个既有缺陷: **点面板头「选择保存位置 N」, 面板就收了**。机理与三修完全无关, 是 combobox 焦点纪律的一个漏洞: 面板里除候选行/预置行之外还有两处**非交互区** —— `.pop-head`(标题+计数)与 `.pop-empty`(空态文案)。它们点了什么都不该发生, 但 mousedown 的**默认动作**把焦点从输入框抢走 → `@focusout` → `movePathBlurClose` 的 40ms 合帧定时器收层 = 面板"点一下就消失"。光标本来就在候选行正上方(面板头紧贴输入框下沿), 误触概率极高。

- 处置: 焦点纪律挂在**共享模板的面板根** `shared/tpl/combo-input.html` 的 `.pop-menu.add-pop` 上(`@mousedown.prevent`)—— 一处覆盖现有全部非交互子元素, 将来往面板里加任何展示性节点也自动免疫。5 个调用点(添加种子三下拉 / meta 分类 / 设定位置)同点受益, 调用点零改动。与候选行自带的 `@mousedown.prevent` 不冲突(同一事件先到目标行再到根, 重复 prevent 无害), 行上那份保留: `onPick` 的"焦点不掉"不依赖根的挂载顺序。不影响滚轮/滚动条(滚动是合成器与原生滚动条行为, 不经 mousedown 默认动作)。
- 守阵: 静态 `test_frontend_add_combo_label_clear_mask_and_refit` 补第 6 节 —— 面板根必须同时带 `@mousedown.prevent`(焦点纪律)与 `@click.stop`(挡 window click 收层), 并注明"必须挂根, 逐个打补丁 = 新增一处展示节点就复发"; e2e 两条**配对**: `move-dialog-fit.spec.mjs` 新增「点面板头/空态不收起」(面板仍在 + 输入框未改写 + 面板没被冻住: 随后点候选仍能回填并收起), `add-options-recent-order.spec.mjs` 补空态段(分类按输入过滤到 0 候选, 点 `.pop-empty` 面板不许收)。
- 红验(三段): ①摘掉根级修饰符 ⇒ 静态 1 红 + e2e 头点击双皮肤红(element not found); ②把修复收窄成"只给 `.pop-head` 挂 prevent" ⇒ 头点击**仍绿**、空态双皮肤红 —— 证明两条断言配对才拦得住半截修法; ③恢复根级 ⇒ 全绿。
- 旁证(不改): 顶栏筛选弹层的 `.pop-head` 不是同一类 —— 它的收层走 window click(根有 `@click.stop`), 没有 focusout 驱动, 且头里那个「清除」是真按钮。

- 2026-10-29 03:00 设定位置对话框六修: 焦点纪律挂面板根(@mousedown.prevent), 点面板头/空态不再收起; 静态 + e2e 两条配对断言, 红绿三段验证通过

### R5 · 七修: 落点归属 —— click 的 target 是 down/up 的公共祖先 (2026-10-29)

用户报「无焦点点下拉, 面板出现即弹回」回归 + 「prism 正常, atlas 异常」。**先做对象核对**: 上一轮的 8099
桩进程已死(`curl` 连接被拒 000), 用户对着它测的是旧资源; 起新桩 + 两皮肤强刷后不复现。为排除"代码里真有一条
无焦点路径", 仍做了 12 条交互序列 × 5 种视口(1440x900 → 980x600)× headless/headed 的取证 —— 面板全程稳定。

取证中复现到**另一个真实缺陷**: 按下在输入框、抬起落在别处时, 浏览器把 `click` 的 target 定成两者的**公共
祖先**(`.add-input-row` / `.add-dialog-body`), 组件根没有 `@click.stop`, 事件冒泡到 lifecycle 的 window 收层
名单 ⇒ 面板点一下就关。实测: 抬到输入框下 6px / 抬到候选行 ⇒ target `div.add-input-row` ⇒ 面板 false;
抬到上方说明文案 ⇒ target `div.add-dialog-body` ⇒ false(**这一路应当关**, 属"点组件外")。

- 为什么"只有无焦点时": 无焦点那次点击, 面板是在**按住期间**才挂载的(`@focus` → 开层), DOM 在按下与抬起
  之间变化, 抬起落点被改写的机会就在那一段; 有焦点时面板早已在, 落点不变。
- 为什么"皮肤不同": 两皮肤输入行屏位差 2px(prism 413–445 / atlas 411–443), 面板入场 `drop-in` 从
  `translateY(-4px)` 起、面板顶 = 输入框底 +4 ⇒ 入场头 ~120ms 面板顶正好压在输入框下沿那 1–2px 上。
- 处置: 组件**根**(`.add-input-row`)挂 `@click.stop` —— 落点在本组合框内部的一切点击不再冒泡到 window 兜底;
  收层主判据仍是 `@focusout`, window click 退回"真点到组件外"的兜底。只许挂组件根(挂到对话框层会把
  "点对话框别处收层"一起废掉, e2e 有反向守门)。
- 守阵: 静态第 7 节(输入行根必须带 `@click.stop`); e2e「按下与抬起落在不同元素 · 面板不收起」(变体 A 抬到
  行内留白 / 变体 B 抬到候选行 面板都得在且不回填 + 反向守门: 点组件外仍收层)。红验: 摘掉根级 `@click.stop`
  ⇒ 静态 1 红 + e2e 双皮肤红(element not found); 恢复 ⇒ 全绿。
- 坑档: `web-ui/combobox-focusout-close` 第七轮条目(含"click target 是公共祖先"这条通识);
  `testing/smoke.md` 新增「回归的第一嫌疑是验错对象: 旧桩进程 / 旧页签」(复发 1) —— 旧桩用 `&` 脱离启动,
  shell 退出即被回收, 正是这次"假回归"的物理成因。

- 2026-10-29 03:37 设定位置对话框七修: 组件根 @click.stop(落点归属), 治"按下/抬起不同元素时面板被 window 兜底关掉"; 静态 + e2e 两变体 + 反向守门, 红绿双验通过

### R6 · 八修: 高亮滚动跟随不许碰祖先容器 (2026-10-29)

用户报「选中新路径后再次点击下拉框, 弹窗中的元素会从上往下滑动出现一次(『作用于 N 个种子』那两段文案在滑);
输入框中无文字时正常」。探针(逐帧采样 `body.scrollTop` + 文案 rect)结论: `_hiScroll` 用
`el.scrollIntoView({ block: "nearest" })` 把高亮项滚进视野 —— 而 `scrollIntoView` 会把**所有可滚祖先**
一起滚, `.add-dialog-body` 正是 overflow-y 容器, 开层过渡期它的 scrollHeight 比 clientHeight 大 166px,
于是整段文案被滚下去再弹回: 实测 `body.scrollTop` `0 → 166 → 83 → 18 → 0`、文案 top `352 → 186 → 269 → 334`;
空输入对照全程 0(与用户"无文字时正常"逐字吻合)。

- 为什么只有"选中过路径"才复现: 输入框空时 `hi = -1`、面板里没有 `[data-hi="1"]`, `_hiScroll` 查不到高亮项
  直接 return; 回填过候选后高亮项存在 ⇒ 才触发滚动跟随 ⇒ 才滚祖先。
- 处置: `_hiScroll` 改手动差值调 `scrollTop`(block:nearest 语义), 逐级向上**以菜单根为界**
  (`for (let n = el.parentElement; n && box.contains(n); ...)` + 到 `box` 即 break), 绝不碰 `.add-dialog-body`/页面。
  五个下拉(添加种子三处 / meta 分类 / 设定位置)共用此单点, 一并受益。
- 守阵: 静态 `test_frontend_combo_hiscroll_never_scrolls_ancestors`(剥注释后真代码内禁 `scrollIntoView`;
  必须 `scrollTop`+`getBoundingClientRect`; 必须有界); e2e「选中候选后再点下拉 · 弹窗文案不滑动」(逐帧
  `body.scrollTop` 恒 0 + 文案极差 ≤2px, 反向守门: 高亮项仍须在列表可视区内)。红验: 把循环退回
  `scrollIntoView` ⇒ 静态 1 红 + e2e 双皮肤红(断言原文见基线切片); 恢复 ⇒ 全绿。
- 坑档: `web-ui/hover-keynav-fight` 复发 1 —— 该条处置 ④ 早就写着「滚动跟随不用 scrollIntoView」, 只是
  `_hiScroll` 这个单点没落实; 教训补「禁令要按单点清点」「受害者常是弹窗自己的滚动容器」「状态相关复现先查
  那条路是不是直接 return」。

- 2026-10-29 04:03 设定位置对话框八修: `_hiScroll` 弃 scrollIntoView(逐层滚祖先会把弹窗文案滚走), 改手动差值 + 菜单根为界; 静态 + e2e 逐帧断言, 红绿双验通过
