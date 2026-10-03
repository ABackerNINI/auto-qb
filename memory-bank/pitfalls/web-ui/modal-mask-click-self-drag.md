# 遮罩关窗用 @click.self: 拖选文字/拖动的 mouseup 落在遮罩上会被判成"点空白关窗"

> 摘要: `.modal-mask` 上写 `@click.self="closeX"` 判的是 click 事件的 target, 而 click 由 mousedown 与 mouseup 的**公共祖先**派发(DOM 规范)—— 在对话框里的输入框按下左键拖选文字、鼠标终点落到遮罩上抬手, 公共祖先就是遮罩本身, 于是"拖选文字"被判成"点空白关窗"(用户原话: 选个标签文字, 抬手窗口没了)。修法 = 遮罩成对挂 `@mousedown="maskDownSelf"` + `@mouseup.self="maskCloseIfArmed(closeX)"`: 只在"这一笔 mousedown 也从遮罩起手"时才关; 任何落在对话框内部的 mousedown 都会把臂位清掉, 不会累积。
> 触发: 遮罩关窗, click.self, 拖选文字窗口消失, 拖选后弹窗自己关了, mouseup 公共祖先, 点空白关窗误判, mousedown 起手位置, 添加种子窗口消失, 弹窗误关, text selection, 拖拽抬手

## 条目

- **触发**: 给弹窗加"点遮罩空白处关闭"(`@click.self`), 或报障「在输入框里拖选文字, 鼠标松在窗口外面, 整个窗口就没了」「拖动一下弹窗就自己关了」。
- **判别**: click 事件的 target 不是 mouseup 所在的那个元素, 而是 mousedown 与 mouseup 的**公共祖先**(这是规范行为, 与冒泡无关)—— 起点在对话框内、终点在遮罩上 ⇒ target = 遮罩 ⇒ `.self` 命中。所以 `@click.self` 表达的是"这一笔交互的共同祖先是遮罩", 而不是"点在空白处"。拖选普通文本(不在输入框里也一样)同样会误关。静态守阵抓不到(模板语法正确 + 单测全绿), 真机一动鼠标就出。
- **处置**: 遮罩**成对**挂 `@mousedown="maskDownSelf"`(记 `e.target === e.currentTarget` 到 `_maskArmed`)与 `@mouseup.self="maskCloseIfArmed(closeX)"`(臂位为真才关, 关完复位)。`maskCloseIfArmed(closeFn, ...args)` 支持带参关闭(确认框 `resolveModal(false)`)。全仓 11 处遮罩统一换掉, 零残留 `@click.self`(守阵按 v-if + class="modal-mask" 扫全模板, 注释不算)。
- **关联**: 与 [combobox-focusout-close.md](combobox-focusout-close.md) 是同一条教训的两面 —— 前者是"label 转发的 click 让浮层关了又开", 本条是"click 的 target 不等于用户以为的那个元素"; 两处都靠"记录这一笔从哪起手"解决, 不靠改冒泡。
