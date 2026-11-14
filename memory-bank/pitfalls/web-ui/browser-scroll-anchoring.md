# 浏览器 CSS scroll anchoring: 根滚动器锚补让 scrollY 无 JS 调用地跳变

> 摘要: Chromium/Firefox 的 CSS scroll anchoring 会在滚动容器内容生长时自动补偿 scrollY —— 本意是防视口内容被推走, 但停靠面板 enter 首帧生长也被当成锚事件补跳: scrollY 无任何 JS scrollBy 调用地 +286(== 面板首帧生长量), 把本不该动的行推出视口顶。它不是 JS 滚动竞速族, 滚动写入者登记/竞速排查全扑空; zoom=1 整数布局探针几乎必绿, zoom≠1 分数布局才确定性复现。
> 触发: scrollY 无故跳变, 没调 scrollBy 却滚动了, 开抽屉行被推出视口顶, 面板打开页面跳动, scroll anchoring, overflow-anchor, 锚补, 锚定补偿, 根滚动器, 分数布局, zoom 0.9, DPR 1.25, 文档底, dock 生长, 首帧缓动
**Refs:** memory-bank/tasks/26-11-12-webui-drawer-reopen-reveal.md

### 面板 enter 首帧生长被根滚动器锚补, 邻近的未覆盖行被推出视口 (2026-11-14, T8, 已修)

- **触发**: 文档底点余量 439~570px 的邻近行开抽屉 —— 面板 42vh enter 首帧缓动生长(≈285px), Chromium 对根滚动器(文档流)做锚补, scrollY 无 JS 调用地 +286, 行被推出视口顶净上移 171px。zoom≠1 分数布局(html zoom 0.9 / 浏览器缩放 / DPR 1.25)确定性复现; zoom=1 整数布局难复现(探针里近乎必绿, 症状被布局取整掩盖)。
- **判别**: 指纹三件套, 三件齐全即锚补而非自家代码竞速: ①scrollY 跳变量 == dock 同帧生长量, 且跳变帧无任何 JS 滚动调用; ②滚动写入者登记空表 —— 包装全部五个滚动原语(scrollTo/scrollBy/scrollIntoView/scrollLeft/top 赋值等)逐帧登记 + `isTrusted` 排除 JS 合成事件, 仍见无来源跳变; ③逐帧采样: scrollY 跳变帧与 dock 高度生长帧逐帧对齐。竞速族(见 frame-swap-scroll-reset / drawer-switch-flicker)的特征是"写入者互相重启", 本坑特征是"零写入者也跳"。
- **处置**: 四皮肤根样式 `html{overflow-anchor:none}` 根级禁锚(红验 `5c04d0e7`)。注意 overflow-anchor **不可继承**, 只需禁根滚动器, 内层滚动器(抽屉内表格体等)锚定零波及 —— 别全站 `*{overflow-anchor:none}`。禁锚后要自查「依赖浏览器帮忙稳住视口」的隐性语义: settle 期 pad 重算吃掉停车余量这类依赖在禁锚后会裸露(同族现案: issue 26-11-14-0844, zoom≠1 下行窗口化渲染窗错位此前被锚补掩盖)。红验必要条件 = zoom≠1 分数布局构造, zoom=1 用例对本坑无红验力。
