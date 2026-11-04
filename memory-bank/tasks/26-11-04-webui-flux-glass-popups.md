# 26-11-04-webui-flux-glass-popups — flux全浮层玻璃化: 预算4→16+遮罩浓度修复

**Status:** Done
**Added:** 2026-11-04
**Updated:** 2026-11-05
**Summary:** flux 全浮层玻璃化落地: 12 处浮层改半透明底+blur(预算 4→16)+三遮罩降浓(.72/.62→.5), 守阵清单反转+遮罩浓度钉, 弹窗/右键菜单玻璃肉眼可见
**Topics:** webui-flux-glass-popups
**Refs:** memory-bank/pitfalls/web-ui/glass-visibility-mask-stacking.md

## 原始请求

1. 用户: 「WEBUI的flux毛玻璃效果没做好, 特别是经过两轮的修改, 添加种子/右键菜单等弹窗的毛玻璃效果近乎没有, 需要调整」。
2. 范围问询(AskUserQuestion)用户拍板: **全部浮层玻璃化**(右键菜单 + 列选择器/筛选器下拉 + 限速浮层/悬停卡/设置页浮窗等全部 --bg-pop 浮层都挂 blur)。

## 思考过程与决策

- 诊断两个独立根因: ① `.modal` blur(14px) 声明一直在, 但 `.modal-mask` 遮罩 `rgba(4,10,22,.72)` × 弹窗底 .82 → 有效透视仅 ~5%, 数学上不可见(11-03 轮只修了面板底没动遮罩); ② `.ctx-menu`/`.ctx-sub` 按设计就没挂 blur —— 26-11-02「透正文」修复把无 blur 浮层全部改成不透明 `--bg-pop`, 本轮经用户拍板反转该口径。
- 关键取舍: 26-11-02「透正文」的根因是半透明底**无 blur**, 挂上 blur 后半透明即毛玻璃, 不再透可读正文 —— 两轮口径不矛盾, 是同一根因的两个阶段。预算显式档 4→16(用户拍板全量玻璃化), 唯一保留不透明底的浮层 = `.col-ghost`(拖动虚影, 每帧移动挂 blur = 逐帧回读)。
- 约束兑现: `flux/css/components.css` 恰 700 行卡满(css-file-line-cap 坑), 该文件内全部新声明**内联进现有行零净增行**; shared 层(`.relc-pop` 等)本体不动, flux 侧 `html[data-fx-preset]` 前缀覆盖(四皮肤隔离)。

## 实现计划

总体思路: CSS 玻璃化 → 守阵同步(预算+清单反转+遮罩浓度钉) → 红绿双验 → 桩服务真浏览器截图验收 → 文档回写。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | flux 三件 CSS 12 处浮层玻璃化 + 三遮罩降浓 | Done(2026-11-04) |
| 2 | 守阵同步: 预算 4→16 + `_scan_flux_modal_frost` ④ 反转 + ⑥ 遮罩钉 | Done(2026-11-04) |
| 3 | 红绿双验(预算回拨红验 + test.quick 全绿) | Done(2026-11-04) |
| 4 | 桩服务真机截图验收(弹窗/右键菜单/下拉三面) | Done(2026-11-04) |
| 5 | 文档回写(webui.md + 新坑档 + 任务档案) | Done(2026-11-04) |
| 6 | 分面评审修 3(major×2 守阵洞 + minor×1) + 探针红验 | Done(2026-11-05) |
| 7 | test.full 全绿 + 基线切片 + 提交 | Done(2026-11-05) |

## 进度日志

### R0 · 立档 (2026-11-04)

- CSS: flux 三件(components/views/dialogs)12 处浮层玻璃化(`--bg-pop`→`--bg-card`+blur, 大面 14px / tip 10px / 共用层 12px); 遮罩三处降浓(`.modal-mask`/`.hr-full-mask` .72→.5、`.add-drop-mask` .62→.5)。
- 守阵: `_FLUX_BACKDROP_BUDGET` 4→16; `_scan_flux_modal_frost` ④ 清单反转(玻璃化浮层族正钉 + `.col-ghost` 反向钉 + 共用层覆盖正则钉) + 新增 ⑥ 遮罩 alpha ≤ .6 钉; `test_webui_relocate_chain.py` 补 flux 覆盖断言。
- 红绿双验: 预算回拨 4 守阵真红 → 还原 16 全绿(test.quick, 数字见 kb.baseline)。
- 截图验收(桩服务 127.0.0.1 + Playwright): 添加种子弹窗/右键菜单/标签下拉三面均透出真实模糊玻璃层, 主页面基线不变。覆盖口径: 三面代表三种材质族(遮罩叠乘弹窗 / fixed 菜单 / 锚定下拉); 其余玻璃化面(speed-pop/hr-full-modal/add-drop-box/aq-tip 等)与三面同一套 CSS 机制, 未逐面截图(评审面② minor, 按「记明口径」处置)。
- 收口评审(分面档, 2 只读子代理: 正确性+安全 / 测试缺口): blocker 清零; 修 3 —— major×2(守阵 ④ blur 子串判断挡不住「只删无前缀留 -webkit-」→ 改负向环视+双份钉; ⑥ 遮罩浓度钉扩到 .modal-mask/.hr-full-mask/.add-drop-mask 三处) + minor×1(:is() 组 7 成员逐个锚定); 三处修复均经内存变异探针验证真红; 入池 0, 弃 2(引文幻觉, review.check REFUTE); 全量测试复核全绿。

**R1(2026-11-05 00:23):** 收尾: test.full 全绿(见 kb.baseline 26-11-05-0023) + 基线切片落盘 + kb.wrap; 档案 Done。
