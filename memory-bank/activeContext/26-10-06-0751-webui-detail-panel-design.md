# WEBUI 种子详情面板重构 · 设计模板轮 + 实施计划

> 摘要: 用户命题 —— 详情面板抽屉改下方面板后: ①常规页竖排右边空一大块 ②Tracker/用户/内容三页平铺没设计感 ③收起状态疑似无用需论证。设计轮已闭环: `resources/detail-panel-templates/` 15 份可交互单文件模板(五页 × 高·矮·收起三方向, prism ocean 令牌, 每份内置三档高度切换) + `_brief.md` 简报 + 汇总报告 26-10-06-0723(收起态论证 + 三条补强 + 逐页推荐)。**用户已拍板(26-10-06): 15 套全量实施可切换(试用期取代逐页选型)、每套挂载点尽量少、选择存 localStorage** —— 实施计划 [26-10-06-0838](../plans/26-10-06-0838-plan-webui-detail-panel-redesign.html) 已出(doc-status **Open 待拍板**): 注册表 + 宿主 + 经典版兜底架构(数据管线零改动, 三皮肤 CSS 零改动, 锁步面收窄到三份 index.html manifest), 每变体 = 1 文件 + 3 行清单, S0-S7 分步, 拍板点 P-01…P-06 各带推荐案; 补强二(收起态点页签自动展开)/补强三(收起态头部摘要化)纳入 S1, 补强一(开合态回读)因 D1 拍板在案入非目标。**未 commit, 等用户指令**。
> 最后活动: 2026-10-06 16:4x(实施轮 S1-S7 全部完成, 本切片已收口归档 —— 实施结论与试用期使用说明见任务档案; 基线 26-10-06-1620)

**Refs:** memory-bank/tasks/26-10-06-webui-detail-panel.md, memory-bank/reports/26-10-06-0723-report-webui-detail-panel-redesign.html, memory-bank/plans/26-10-06-0838-plan-webui-detail-panel-redesign.html

## 立档与闸门口径

- **立档: 已立** `memory-bank/tasks/26-10-06-webui-detail-panel.md`(Topics: webui-detail-panel-redesign, Status: In Progress)。依据: 命中 skill 立档阈值 #4(本轮已产出 `reports/` HTML 报告制品)与 #3(「设计模板轮/实施轮」波次表述)。后续实施会话按「一个专题一个档案」在**该档案追加**, 不另新建。
- **test.full: 豁免** —— 设计轮与计划轮均零代码改动(未动 `src/` / `config`), 现役基线 `26-10-06-0713` 不变, 不新建基线切片; 改跑 `test.one tests/test_memory_bank.py` 验 KB 守卫(本轮新增档案/切片/索引是该守卫的输入)。
- **开工同步**: 计划轮 sync 成功 b0767903(与设计轮收尾提交同点, 已是最新)。

## 下一步

1. ~~用户对计划 P-01…P-06 拍板点定案~~ 已拍板(2026-10-06, 按推荐案全收)。
2. ~~拍板后转 In Progress, 按 S0-S7 开工~~ 已完成(2026-10-06): S1-S7 七笔提交在
   `feature/webui-drawer-templates`(S1-S6 hash 见任务档案), S7 收口全矩阵巡检 283 断言全过 +
   删变体演示 + test.full 基线 2678+4(切片 26-10-06-1620); 计划 doc-status Done, 档案 Done。
3. 试用期使用(切换器位置 / 增删变体 = 1 文件 + 3 行 manifest)见任务档案「试用期使用说明」。
