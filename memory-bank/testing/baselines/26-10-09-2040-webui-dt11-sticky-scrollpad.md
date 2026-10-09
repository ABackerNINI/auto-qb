# 2872 —— dt11 树表批量吸顶吸底 padding 内缩缝修复 + e2e 几何守阵基线

> 摘要: 用户报「WEBUI 种子详情内容页树表批量的文件列表标题栏在上滑时未到顶导致顶部漏出文字, 统计栏没到底也会在底部漏出文字」。根因 = sticky 视矩形被滚动容器 `.drawer-body` 自身 padding 内缩 —— `top:0` 实际停在 padding-top(14px)之下、`bottom:0` 实际停在 padding-bottom(20px)之上, 中途滚动时数据行文字从两条缝里漏出(实测 headTop 比 body 顶缘恒低 14 / footBottom 比 body 底缘恒高 20)。修复 = 负 inset 抵消(top:-14px / bottom:-20px, 见 11-content-treegrid-batch-low.js 内注释); 新增 e2e 几何守阵 `e2e/drawer-content-dt11-sticky.spec.mjs`(双皮肤两档滚动断言齐平, 已红验); 坑档 `pitfalls/web-ui/sticky-scrollpad-inset.md` 入册。
> 基线时间: 2026-10-09 20:40

**Refs:** memory-bank/activeContext/26-10-09-2040-webui-dt11-sticky-scrollpad.md,memory-bank/pitfalls/web-ui/sticky-scrollpad-inset.md

## test.full 实测

- 分支: `develop`(HEAD `e9fe4a9d`, 会话开工快进所得; 工作树含本轮修复 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2872 passed + 3 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标; 25.5s)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- 增量明细(本轮真正新增): `e2e/` +1 几何守阵(playwright 轨, 不进 pytest 收集面); `src/` 改动仅 dt11 变体两条 sticky inset 与注释(零语义面变化); 知识库回写件 3 份(activeContext 切片 / pitfalls 坑档 / 本切片)+ `_index.md` 重建。pytest 收集面本轮零改动, passed/skip 位移来自会话开工快进带入的上会话提交(`9860ce11`/`e9fe4a9d`), 非本轮。
- e2e 门禁: `npm run test:e2e:fast` **34 passed**(含新守阵双皮肤 2 条; 红验时旧值双皮肤 2 failed, 恢复修复后复绿)。
