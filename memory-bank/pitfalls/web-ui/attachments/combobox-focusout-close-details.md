# 自绘 combobox 收层第六、七轮的完整判据与实测证据 — 外迁详情(原 `pitfalls/web-ui/combobox-focusout-close.md` 段落原文)

> 摘要: `pitfalls/web-ui/combobox-focusout-close.md` 的详细处置/实测证据原文外迁(主档为控 cap 原位留指针); 判据与实测证据原样保留。
> 触发: 同主档 `pitfalls/web-ui/combobox-focusout-close.md` 的触发词(完整列表见主档头部)。

> 本文件是**外迁存档**: 主档该段原文一字未改搬来 (仅相对链接整体下移一层 —— 本文件在 `pitfalls/web-ui/attachments/`); 本目录不计 cap, 主档原位留指针。
## 第六/七轮: 面板内非交互区(区域级焦点纪律)与落点归属(click target 公共祖先)

- **触发**(2026-10-29 第六轮, 用户「缺陷一并修复」: 点面板头「选择保存位置 N」, 面板就收了): combobox 面板里除候选行/预置行之外还有**非交互区** —— `.pop-head`(标题+计数)与 `.pop-empty`(空态文案)。它们点了什么都不该发生, 但同样吃 mousedown 默认动作的 blur。
- **判别**: 前五轮修的都是面板内**可点**元素(label / 清空 x / 候选行)的焦点纪律, 非交互区没人管 —— mousedown 落在 `.pop-head` 上时焦点从输入框掉到 body, `@focusout` 照常触发, 40ms 合帧后 `_popBlurShouldHold` 判「焦点不在本族输入框、也没有本族 label 转发在途」⇒ 收层。它在事件链上与「点窗口空白」完全同形, 所以只能在模板层拦, JS 守卫分不出来。面板头紧贴输入行下沿、候选行正上方, 误触概率极高(与三修「面板被顶到光标底下」是同一片热区)。
- **处置**: 焦点纪律挂**面板根** —— `shared/tpl/combo-input.html` 的 `.pop-menu.add-pop` 加 `@mousedown.prevent`(与 `@click.stop` 并列), 一处覆盖现有全部非交互子元素, 将来往面板里加展示性节点也自动免疫; 5 个调用点(添加种子三下拉 / meta 分类 / 设定位置)零改动。与候选行自带的 `@mousedown.prevent` 不冲突(同一事件先到目标行再到根, 重复 prevent 无害), 行上那份保留。不影响滚轮与滚动条(滚动是合成器/原生滚动条行为, 不经 mousedown 默认动作)。
- **守阵**: 静态 `test_webui_static_dom_panel_dialogs.py::test_frontend_add_combo_label_clear_mask_and_refit` 第 6 节 —— 面板根必须同时带 `@mousedown.prevent`(焦点纪律)与 `@click.stop`(挡 window click 收层); e2e **两条配对**: `move-dialog-fit.spec.mjs`「点面板头/空态不收起」(面板仍在 + 输入框未改写 + **随后点候选仍能回填并收起**, 防「修成冻住」), `add-options-recent-order.spec.mjs` 空态段(分类按输入过滤到 0 候选, 点 `.pop-empty` 不许收)。红验三段: ①摘掉根级修饰符 ⇒ 静态 1 红 + e2e 双皮肤红; ②把修复收窄成「只给 `.pop-head` 挂 prevent」⇒ **头点击仍绿、空态双皮肤红**; ③恢复根级 ⇒ 全绿。
- **教训**: ①「面板内点击」不是一类**元素**, 是一块**区域** —— 焦点纪律要按区域(根)设; 按元素逐个设, 就会随新增元素静默复发(与 issue 26-10-20-2230 把五处骨架收敛成单点的同一条道理)。②只覆盖一个可点位置的断言拦不住半截修法: 区域级不变量至少要两条落在**不同位置**(头 + 空态)的断言配对, 红验也要按「收窄版」跑一遍才算验过。③非交互区在真人手里不是「点了没事」, 而是「点了会消失」 —— 凡是紧贴高频操作热区(输入行下沿)的区域, 任何「点了会消失」的行为都会被放大成「面板自己弹回」。

- **触发**(2026-10-29 第七轮, 排查「无焦点点下拉即弹回」时复现到的独立缺陷): 按下在输入框、抬起落在**别处**(行内留白 / 面板 / 整行)时, 面板"点一下就关"。
- **判别**: 浏览器把 `click` 的 target 定成 mousedown 与 mouseup 两个落点的**公共祖先** —— 按在 `input`、抬到行内留白或面板里, click 的 target 就是 `.add-input-row`, 那一层没有 `@click.stop`, 事件照常冒泡到 lifecycle 的 window 收层名单 ⇒ `movePathMenu = false`。实测(prism, 无焦点): 抬到输入框下 6px → click target `div.add-input-row` → 面板关; 抬到候选行 → 同样关; 抬到上方说明文案 → target `div.add-dialog-body` → 关(这一路**应当**关, 属"点组件外")。无焦点时最易踩的原因: 面板是在**按住期间**才挂载的(`@focus` → 开层), DOM 在按下与抬起之间变化, 抬起落点被改写的机会就在那一段; 有焦点时面板早已在, 落点不变。**皮肤差异的由来**: 两皮肤输入行屏位差 2px(prism 413–445 / atlas 411–443), 而面板入场 `drop-in` 从 `translateY(-4px)` 起、面板顶 = 输入框底 +4 ⇒ 入场头 ~120ms 面板顶正好压在输入框下沿那 1–2px 上, 落点是否被改写就取决于这 2px 与点击高度的组合。
- **处置**: 组件**根**(`shared/tpl/combo-input.html` 的 `.add-input-row`)挂 `@click.stop` —— 落点在本组合框内部的一切点击(输入框 / 行内留白 / 面板 / 被改写成公共祖先的点击)都不再冒泡到 window 兜底; 收层主判据仍是 `@focusout`(点窗口别处照常收), window click 退回"真点到组件外"的兜底。**只许挂组件根**: 挂到对话框层会把"点对话框别处收层"一起废掉。
- **守阵**: 静态 `test_frontend_add_combo_label_clear_mask_and_refit` 第 7 节(输入行根必须带 `@click.stop`, 并注明只许挂组件根); e2e `move-dialog-fit.spec.mjs`「按下与抬起落在不同元素 · 面板不收起」—— 变体 A(抬到行内留白)/ 变体 B(抬到候选行)面板都必须还在且不回填, 末尾**反向守门**: 真点到组件外(上方说明文案)仍必须收层。红验: 摘掉根级 `@click.stop` ⇒ 静态 1 红 + e2e 双皮肤红(element not found); 恢复 ⇒ 全绿。
- **教训**: ①"点空白收层"这条兜底只该管**组件外**的点击; 组件内部的任何落点都归组件自己判 —— 用 `@click.stop` 划清边界, 比在 window 处理器里加特判稳。②`click` 的 target 不是"用户点的那个元素", 是 down/up 的公共祖先 —— 凡是用 window click 做兜底的地方都要想到这一条(拖选、按住期间 DOM 变化都会改写落点)。③"无焦点才复现"这类条件, 往往指向**按住期间 DOM 变化**(开层/关层/高度过渡), 而不是焦点本身。
