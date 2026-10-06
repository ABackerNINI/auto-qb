# WEBUI 种子详情面板重构 · 设计模板轮 (零代码)

> 摘要: 用户命题 —— 详情面板抽屉改下方面板后: ①常规页竖排右边空一大块 ②Tracker/用户/内容三页平铺没设计感 ③收起状态疑似无用需论证。本轮纯设计: 产出 `resources/detail-panel-templates/` 15 份可交互单文件模板(五页 general/trackers/peers/content/traffic × 高·矮·收起三方向, prism ocean 令牌, dark 主题, 每份内置收起/矮/高三档高度切换) + `_brief.md` 调研简报; 汇总报告 `26-10-06-0723-report-webui-detail-panel-redesign.html`(已登记 reports/_index.md), 内含收起态论证 —— **收起有实际作用**(回收约 44px 头部空间)但反馈弱, 附三条补强点(持久化只写不回读→回读 / 收起态点页签→自动展开 / 收起态头部→摘要化)与逐页推荐「供拍板」。质检: Playwright 真实浏览器逐份三档+交互全过; 过程中修 01-12 号模板缺 `[hidden]` 规则共 12 行(`[hidden]` 会被显式 display 规则压掉)。**未 commit, 等用户指令**。
> 最后活动: 2026-10-06 07:51

**Refs:** memory-bank/tasks/26-10-06-webui-detail-panel.md, memory-bank/reports/26-10-06-0723-report-webui-detail-panel-redesign.html

## 立档与闸门口径

- **立档: 已立** `memory-bank/tasks/26-10-06-webui-detail-panel.md`(Topics: webui-detail-panel-redesign, Status: In Progress)。依据: 命中 skill 立档阈值 #4(本轮已产出 `reports/` HTML 报告制品)与 #3(「设计模板轮/实施轮」波次表述)。后续实施会话按「一个专题一个档案」在**该档案追加**, 不另新建。
- **test.full: 豁免** —— 本轮零代码改动(未动 `src/` / `config`), 现役基线 `26-10-06-0713` 不变, 不新建基线切片; 改跑 `test.one tests/test_memory_bank.py` 验 KB 守卫(本轮新增档案/切片/索引是该守卫的输入)。
- **开工同步**: `my-commit-flow.sync` 成功 376dda34(远端有新提交, 自 5f321099 快进; 自动重跑生成物 1 处)。

## 下一步

1. 用户按报告逐页推荐选型(可整页采纳或指定吸收组合)。
2. 选型后**另立 plan** 实施落地: `drawer.html` / `drawer.js` / 三皮肤 CSS, 收起态三条补强点一并纳入取舍。
