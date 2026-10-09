# webui dt11 树表批量吸顶吸底 padding 内缩缝

> 摘要: 用户报「树表批量的文件列表标题栏在上滑时未到顶导致顶部漏出文字, 统计栏没到底也会在底部漏出文字」→ 修复 dt11 后用户授权「修同族疑似」→ dt07/dt09 同法清偿。根因与修复见坑档(单点), 本切片只留会话滚动状态。
> 最后活动: 2026-10-09 20:52

**Refs:** memory-bank/pitfalls/web-ui/sticky-scrollpad-inset.md,memory-bank/testing/baselines/26-10-09-2040-webui-dt11-sticky-scrollpad.md

## 已完成

- 复现取证: 起桩(8241, 60 种子) + page.route 喂 90 个合成文件 + 三档 scrollTop 量几何 —— 吸顶态 headTop 比 body 顶缘恒低 14px(=padding-top)、吸底态 footBottom 比 body 底缘恒高 20px(=padding-bottom), 缝隙带采样到行名元素; 两档极端不露缝。探针脚本 `.openclaw/tmp/probe-dt11.mjs`(划痕, 不入库)。
- 修复: `11-content-treegrid-batch-low.js` 两条 sticky inset 负值抵消(top:-14px / bottom:-20px) + 机理注释; dt11 之外零接触。识图目检双皮肤: 表头/统计条贴齐可视缘, 统计条上方 8px 静置间隙无可辨碎片(该间隙不动)。
- 守阵: `e2e/drawer-content-dt11-sticky.spec.mjs`(@fast, 双皮肤) —— 已红验(旧值即红); `npm run test:e2e:fast` 34 passed。
- 回写: 坑档 `pitfalls/web-ui/sticky-scrollpad-inset.md` + 基线切片(2872+3, TOTAL 99%, 见 kb.baseline)+ 本切片; `kb.index` 已重建。
- 同族清偿(用户授权「修同族疑似」): dt07/dt09 的 `.dt0x-head` 同缝确认, 同法 top:-14px; 探针实测中途滚动 gap 归零(prism, 双变体); 新守阵 `e2e/drawer-peers-sticky-flush.spec.mjs`(2 变体 × 双皮肤, 红验 4/4); dt10 的 `.dt10-right` 查证为侧栏卡非漏字面, 不修。fast 门禁 38 passed; 基线第二切片(2872+3, TOTAL 99%, 见 kb.baseline)。

## 正在进行

- (无 —— 两轮修复与回写已收口, 随本专题入库; 用户未下「提交」指令, 工作树保持未提交改动现状)

## 下一步(候选, 未认领)

- (同族已清偿, 无遗留; 若后续改皮肤 `.drawer-body` padding, 按坑档判据连带核三变体负 inset)
