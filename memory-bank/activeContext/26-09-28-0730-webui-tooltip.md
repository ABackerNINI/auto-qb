# WEBUI tooltip 自绘发光浮层

> 摘要: 原生 title 全局替换为自绘单例 .aq-tip(设置页发光按钮配方, 三皮肤令牌自适应), 已验证并建基线。
> 最后活动: 2026-09-28 07:44

## 已完成

- 调度层: shared/ui_feedback.js 尾部纯 DOM 委托(mouseover/focusin 摘 title 压原生气泡 + 350ms 延迟弹 .aq-tip; mouseout/focusout/mousedown/scroll/blur 收起并还原 title, 还原前 hasAttribute 探测保 Vue :title 绑定)。
- 样式层: shared/console_hub.css `.aq-tip` 段 —— accent-line 描边 + 负 spread 微光(同 .hb-card 静息配方) + bg-elev 底/fg 字 + radius-sm 圆角; 发光在浮层本层用 --accent 现算(hub 控件的 --glow-soft 继承不到, 硬知识③)。
- 验证: Playwright 截图实测星图/控制台/棱镜 frost 三皮肤 + 右缘夹回/贴顶下翻/长文本折行/多行/title 还原; test.full 1820 passed / 3 skipped(基线 26-09-28-0744)。
- 事实回写: conventions/webui.md 新增「WEB UI 悬浮提示 .aq-tip」节。

## 进行中 / 待办

- 无 —— 等待用户说「提交」。
