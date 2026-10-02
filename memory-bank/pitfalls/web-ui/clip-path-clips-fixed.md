# clip-path 祖先会裁剪 fixed 后代 (覆盖层必须是块盒的兄弟)

> 摘要: 祖先带 `clip-path`(console/atlas 皮肤的 `.hb-cut` 切角)时, 其内 `position: fixed` 后代的绘制被裁剪进该祖先的块盒 —— 症状是「全屏层只剩与块重叠的部分可点/可见」, 看着像 z-index 或事件绑定 bug, 实为绘制裁剪。覆盖式全屏层一律写成块盒的**兄弟节点**(或确保祖先链无 clip-path/transform/filter), 不靠 z-index 救。
> 触发: fixed 全屏不显示, 覆盖层只显示一部分, 弹窗被裁剪, 全屏遮罩点不到, clip-path, 切角, hb-cut, z-index 调不动, fixed 后代, 设置页覆盖层, 全屏层错位
**Refs:** memory-bank/tasks/26-10-02-webui-hr-status-display.md

### clip-path 裁剪 fixed 后代: 机制与修法 (2026-10-02 实测)

- **触发**: 在带切角皮肤的卡片/块盒(`.hb-blk` 等, console/atlas 用 `.hb-cut` + `clip-path: polygon(...)` 实现)**内部**放 `position: fixed` 的覆盖式全屏层(遮罩 + 弹窗), 想让它铺满视口。
- **判别**: 真浏览器目检(桩数据起盘)发现全屏层**只剩与块盒重叠的部分**可点/可见, 超出块盒的部分像不存在 —— `z-index` 调多高都没用, DOM 检查器里元素坐标是对的。根因: CSS 规范里 `clip-path`(同族还有 `transform` / `filter` / `will-change` 等生成 containing block 的属性)会使该元素成为 fixed 后代的**裁剪/包含上下文**, fixed 的「相对视口」语义在绘制层被截断为「相对该祖先」。静态守阵与代码审查都发现不了(坐标与类名全对), 必须真浏览器目检。
- **处置**: 覆盖层写成块盒的**兄弟节点**而非子节点(HR 站点状态全屏层: 覆盖层是 `.hb-blk` 的兄弟, 单节点 `v-show` 显隐, 状态在组件 state 天然随行, 零 DOM 搬迁); 同理给这类皮肤写新弹层前先确认祖先链无 clip-path/transform。若确需在裁剪祖先内做浮层, 只能放弃 fixed 改用祖先内绝对定位(即放弃"全屏"语义)。
- **守阵**: 阶段 2 提交在 settings-detail.html 模板注释里钉了「覆盖层是 .hb-blk 的兄弟而非子节点」的原因(含本坑一句话); `tests/test_web.py::test_frontend_hr_full_modal_wiring` 钉三套 UI CSS 成对与接线。
