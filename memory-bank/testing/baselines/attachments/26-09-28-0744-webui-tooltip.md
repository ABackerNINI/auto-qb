# 1820 passed / 3 skipped —— WEBUI tooltip 换自绘发光浮层

> 摘要: 原生 title 提示全局替换为自绘单例 .aq-tip: 调度单点在 shared/ui_feedback.js 尾部(document 级委托, hover/聚焦摘除 title 压原生气泡 + 350ms 延迟, 离开还原; 点击/滚动/失焦即收), 样式单点在 shared/console_hub.css .aq-tip 段(设置页发光按钮配方: accent-line 描边 + 负 spread 微光 + bg-elev 底 + radius-sm 圆角, 三皮肤令牌自适应)。模板 130+ 处 title/:title 零改动受益, 新增 0 测试。
> 基线时间: 2026-09-28 07:44

- test.full 一次通过(无 throttle 假红): **1820 passed / 3 skipped**, 20.25s, TOTAL **91%**(12542 语句 / 915 未覆盖 / 4222 分支 / 388 partial); 与 26-09-28-0724 同数字 —— 本轮纯前端静态资源改动, 增 0 测试。
- test.quick 全绿 1820 passed(17.4s)。
- 真浏览器验证(临时脚手架借真实皮肤 CSS, Playwright 截图): 星图/控制台/棱镜 frost 三皮肤视觉正确(圆角随 --radius-sm, 控制台自动方角); 右缘夹回 / 贴顶下翻 / 360px 长文本折行 / \n 多行 / 离开还原 title 均实测通过。
