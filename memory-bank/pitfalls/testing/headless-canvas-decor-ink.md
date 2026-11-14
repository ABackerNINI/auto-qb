# headless 软件光栅读不到 canvas 装饰墨: 像素探针恒 0 假阴性

> 摘要: 本机(Windows 无 testbed)Playwright headless 用软件光栅, rAF 渲染间读画布像素读不到**装饰层墨** —— 读数恒 0, 探针「通过」其实是假阴性(装饰根本没显形也过); 真 0 判据面与像素强度判据面在此环境都不可落地。降级判据: 装饰的**机制面**改运行时记账(包 drawAxes 钩子 + ctx.rect 只读包装), **调度器面**改 anim/fx 在场断言 —— 钉「代码改的那件事本身」而不是「像素结果」。
> 触发: canvas 像素探针, getImageData, 装饰墨, 软件光栅, headless, 假阴性, 右缘装饰带, 像素量, 帧采样, e2e 画布读数恒 0, traffic fx, A6, 像素强度

**Refs:** memory-bank/plans/26-11-14-1313-plan-webui-traffic-beat-fidelity.html, memory-bank/tasks/26-11-15-webui-traffic-beat-fidelity.md, memory-bank/testing/baselines/26-11-15-0432-webui-traffic-beat-fidelity.md

### 像素强度/装饰可见性判据在本环境不可落地

- **触发**: `e2e/traffic-fx-frames.spec.mjs` 的 A6 用例(计划验收判据「有流量时环/粒子/菱形无右缘裁切」按像素探针判)与 A1 量法(「拍窗内右缘装饰带像素量 >> 拍间基线」)首跑(2026-11-14, 计划 26-11-14-1313 B5 批)。
- **判别**: 在 rAF 回调/渲染间隙对 canvas `getImageData` 读右缘装饰带 —— 实测读数恒 0, 无论真滚窗拍还是预览拍、无论装饰是否该在场。取证三步: ①同一段代码在**有**装饰的帧(预览拍逐帧 spawn)与**无**装饰帧读数完全一致(全 0), 探针不具备区分度; ②换成**机制记账**(包 drawAxes 钩子 + ctx.rect 包装)后, 同场景逐渲染都能读到 fx 段 clip 实参与 spawn —— 装饰确实在画, 只是墨落不到可读的位图; ③结论 = **装饰墨只在渲染管线内可观测**, headless 软件光栅下渲染间读位图不回放装饰层。别把它误判成「动效没跑」—— 调度器/anim 状态面是活的, 死的只是像素读取面。
- **处置**: 量具降级, 不降判据: ①裁剪/几何类判据改**渲染对齐记账**(运行时包装钩子, 只读不改生产逻辑)直接钉改动本身 —— clip 实参 `rect(L,T,max(W,canvasW-L),H)` 逐渲染断言(与电池 G0 同契约); 近底环钳制/粒子镜像这类纯函数面由 node 电池(G11/G12)钉; ②「每拍都有反馈」类判据改**调度器在场断言**(每滚窗拍 `anim.fx` 在场且 lv>=1, 等级门回潮即整段缺席); ③写回计划/档案时把「像素量 >> 基线」量法偏差**如实记档**(S3b 回写 webui-traffic-beat.md), 不留「验收已按计划量法过」的假账。真像素级验收只能等 Linux testbed 真光栅或真机轨, 别在本环境硬凑。
- **守阵**: `e2e/traffic-fx-frames.spec.mjs` 裁剪面机制探针(C 段)与 A1 调度器面用例 —— 文件头注记录取证与降级理由, 回潮(有人再把像素探针请回来)会在同一段注释前红出来。
