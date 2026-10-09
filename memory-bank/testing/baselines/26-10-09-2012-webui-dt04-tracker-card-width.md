# 2871 —— WEBUI Tracker 状态卡片栅格宽度统一(虚拟卡去 sp2)基线

> 摘要: 用户报「WEBUI种子详情Tracker页的状态卡片栅格: 启用 tracker 卡片半宽, 未启用的虚拟条目全宽, 需统一」—— 根因 = 变体 04 双列 grid 里虚拟合并卡沿用设计稿 `sp2` 类(`grid-column:1 / -1`)跨全宽, 与实体卡(各占一格半宽)不一致; 用户拍板「虚拟卡改半宽」(与实体卡对齐, 改动最小) —— 删 `.dt04-card.sp2` CSS 规则与类引用, 虚拟卡与实体卡同占一格; 与设计稿的差异点在 `virtualCardHtml` 注释标明。1 个源文件, 不命中立档阈值, 切片沿用 26-10-06-0751(同专题追加)。
> 基线时间: 2026-10-09 20:12

**Refs:** memory-bank/activeContext/26-10-06-0751-webui-detail-panel-design.md

## test.full 实测

- 分支: `develop`(HEAD `e9fe4a9d`, 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2871 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- **收集面未变**: 本轮仅改 1 个静态变体 JS 的 CSS 数组与注释(纯字符串, 无新用例无新文件) ⇒ pytest 收集数不变。skip 与上基线差 1 的成因: `test_commands_engine.py:226` 的 PYTHONUTF8 环境条件用例本轮被跳(上基线那轮实跑), 与本轮改动无关(该用例 skip 消息自带条件说明)。
- 增量明细(本轮真正新增): 无新文件 —— `src/auto_qb/webui/static/shared/drawer_tpl/04-trackers-status-cards-tall.js` 为原文件修改; 回写件 `progress/implemented-webui.md` 新条目、切片 26-10-06-0751 追加; 本基线切片。
