# 2872 —— dt07/dt09 peers 吸顶同族清偿 + e2e 守阵基线

> 摘要: 用户授权「修同族疑似」—— dt07(增强仪表盘)/dt09(密度表) 的 `.dt0x-head` 与 dt11 同族(同滚动容器、同 top:0), 同法负 inset 抵消(top:-14px); 探针实测中途滚动 gap 归零。dt10 的 `.dt10-right` 查证为侧栏卡(兄弟列无内容从其下滚过), 内缩只是观感偏移非漏字, 不修。新增守阵 `e2e/drawer-peers-sticky-flush.spec.mjs`(2 变体 × 双皮肤, 桩 peers 端点 40 行, 红验 4/4 红); 坑档同族条目已更新为清偿态。机理单点: pitfalls/web-ui/sticky-scrollpad-inset.md。
> 基线时间: 2026-10-09 20:52

**Refs:** memory-bank/activeContext/26-10-09-2040-webui-dt11-sticky-scrollpad.md,memory-bank/pitfalls/web-ui/sticky-scrollpad-inset.md

## test.full 实测

- 分支: `develop`(HEAD `e9fe4a9d`, 会话开工快进所得; 工作树含 dt11 + dt07/09 两轮修复 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2872 passed + 3 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标; 42.7s —— 与上基线 25.5s 同树同收集面, 差值为机器负载噪声区间)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- 增量明细(本轮真正新增): `src/` 改动仅 dt07/dt09 两条 sticky inset 与注释(零语义面变化); `e2e/` +1 守阵(peers 轨, 不进 pytest 收集面, pytest 数字与上基线同); 知识库回写件 2 份(activeContext 切片更新 / 本切片)+ 坑档同族条目更新 + `_index.md` 重建。
- e2e 门禁: `npm run test:e2e:fast` **38 passed**(dt11 轮 34 + 本轮 peers 守阵 4; 红验时旧值 4 failed, 恢复修复后复绿)。
