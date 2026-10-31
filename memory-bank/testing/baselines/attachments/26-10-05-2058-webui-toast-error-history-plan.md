# 2622 —— WEBUI 错误历史实施计划(认领 26-10-05-2013 + 三可交互模板)

> 摘要: 纯文档轮基线。认领 issue 26-10-05-2013(Open → In Progress, doc-refs 双向 + 复验六锚点全复现),
> 出分步实施计划 26-10-05-2026(完整方案 + 收 error 口径, S1-S6 每步一笔提交, 守阵 5 条规划),
> 附 3 个可交互入口模板(T1/T2/T3, 演示含触发→入史→徽标→面板复制/清空/模拟重连)供 D1 拍板。
> 用户报「演示控制点击无反应」已修(mount 根选择器未盖住卡片级兄弟 .demo-ctl), 内置浏览器全链走查通过。
> 本轮 src / tests 零改动, 基线用途 = 记录纯文档轮的 test.full 真值, 供实施轮(拍板后)对比。
> 基线时间: 2026-10-05 20:58

**Refs:** memory-bank/activeContext/26-10-05-2026-webui-toast-error-history-plan.md

- 分支: develop @ 2130450c(会话开工 sync 所得; 工作树含本轮改动: 计划 HTML + issue HTML +
  activeContext 切片 + 11 份 `_index.md` 生成物 + 本切片, 未提交)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2622 passed + 4 skipped, 29.78s, 覆盖率 TOTAL 99%**
  (15815 语句 / 166 未覆盖 / 5400 分支 / 139 partial; 门槛 98% 达标)
  同树二次采样(写完本切片 + `kb.index` 后的终态树): **2622 + 4 / 99% / 30.45s** —— 耗时区间
  **29.78 ~ 30.45s**, 用例与覆盖率五项逐字相同。
- 相对上一条基线 [26-10-05-2015](26-10-05-2015-webui-open-path-fallback.md)
  (2621 passed + 4 skipped @ 80f48bc7, 15815/169/5400/140): passed **+1** / 未覆盖 **-3** ——
  均为区间内 sync 合流(80f48bc7 → 2130450c)带入的其它会话提交(如 toast 停留下限轮的守阵);
  **本轮纯文档, src / tests 零改动, 对用例与覆盖率的贡献为零**。
- 靶向验证: `commands run test.one -- tests/test_docs_forms.py` 11 passed(计划 meta 完整性 / 命名 /
  dark 主题 / 状态词表 / 索引一致守阵); `commands run kb.check` 主键纪律 OK(419 文档 / 247 专题)+
  认领链 OK(计划 doc-refs ↔ issue doc-refs 双向闭环)。
- 浏览器走查: 内置浏览器 + 临时 HTTP 服务全链交互通过(触发→入史→徽标→面板→复制→清空→连发→
  模拟重连→T3→拍板标记; 连发定时器在后台页有节流延迟, 前台不受影响), 服务与标签页已清理。
- 改动面: `memory-bank/plans/26-10-05-2026-plan-webui-toast-error-history.html`(新) ·
  `memory-bank/issues/26-10-05-2013-feat-webui-toast-error-history.html`(新, 上轮入池未提交, 本轮置
  In Progress) · `memory-bank/activeContext/26-10-05-2026-webui-toast-error-history-plan.md`(新) ·
  11 份 `_index.md`(kb.index 生成物) · 本切片。
