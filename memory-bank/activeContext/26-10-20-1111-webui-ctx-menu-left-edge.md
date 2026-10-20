# webui-ctx-menu-left-edge

> 摘要: 认领并修复 issue 26-10-20-0148(用户指派): e2e/menus.spec.mjs 横轴拆出 CTX-fit 右缘(真实右键贴滚动容器右缘, clientX≈1426, 断言右缘≤vw-8)与 CTX-fit 左缘(clientX=2 合成 contextmenu 走真实 handler 链, 断言左缘≥8; 真实手势结构不可达——容器左缘被 .layout 12px padding 钉死)两支; 移除垂直 CTX-fit 里恒真的顺带右缘断言; 双皮肤绿 + 两类突变(左/右缘两级 clamp 全拆)各自判红不误红, ui_feedback.js 零改动; 新坑档 pitfalls/web-ui/ctx-menu-edge-clamp.md; 全量测试数字见基线切片
> 最后活动: 2026-10-20 11:30

**R0(2026-10-20 11:11):** 认领并修复 issue 26-10-20-0148(用户指派): e2e/menus.spec.mjs 横轴拆出 CTX-fit 右缘(真实右键贴滚动容器右缘, clientX≈1426, 断言右缘≤vw-8)与 CTX-fit 左缘(clientX=2 合成 contextmenu 走真实 handler 链, 断言左缘≥8; 真实手势结构不可达——容器左缘被 .layout 12px padding 钉死)两支; 移除垂直 CTX-fit 里恒真的顺带右缘断言; 双皮肤绿 + 两类突变(左/右缘两级 clamp 全拆)各自判红不误红, ui_feedback.js 零改动; 新坑档 pitfalls/web-ui/ctx-menu-edge-clamp.md; 全量测试数字见基线切片

**R1(2026-10-20 11:30):** ship.commit 被命令漂移闸门拦一次: 基线切片里手抄了 npx playwright test(已收录为 dev.e2e), 改成 task id 形态 commands run dev.e2e -- menus.spec.mjs 后过; 为什么没命中 —— 写基线时没走 commands skill 的收录协议(凭习惯写裸命令), 该坑 2026-10-06 首次记录在 tasks/26-10-06-test-playwright-e2e.md, 无独立坑档条目
