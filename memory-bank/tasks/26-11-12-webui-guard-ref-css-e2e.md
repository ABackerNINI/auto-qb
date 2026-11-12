# 26-11-12-webui-guard-ref-css-e2e — 过期守阵指称族 css/html/e2e 面 7 处修复

**Status:** Done
**Added:** 2026-11-12
**Updated:** 2026-11-12
**Summary:** 过期守阵指称族 css/html/e2e 面 7 处全部改指拆分后现行守阵定义点(含 700 行 cap 守阵一处改道), issue 26-11-12-0628 结档 Done, 分批评审零 actionable 出口, 全量回归全绿
**Topics:** webui-guard-ref-css-e2e
**Refs:** memory-bank/issues/26-11-12-0628-docs-webui-guard-ref-css-e2e.html, memory-bank/pitfalls/kb/doc-verify-completed-claim.md

## 本篇只回答

本轮**实际怎么改、验证到哪** —— 7 处注释改指现行定义点的改动面与复扫/全量结论; 「要不要修 / 什么时候修」在 issue 26-11-12-0628, 修法范式在 issue 26-11-12-0527 与 0d420c9d, 不复述。

## 原始请求

1. 「修复 memory-bank/issues/26-11-12-0628-docs-webui-guard-ref-css-e2e.html」

## 思考过程与决策

- 用户点名具体 issue 并要求修复 = 用户指派认领; 开工按 create-issue 防过期原则复验: 同口径词边界复扫 7 处仍全部复现, 行号与取证当时值一致。
- 修法照 0527 已修轮(逐符号 grep 现行定义点后改指), 只改注释; 零逻辑/断言改动, 零生产行为变更。
- **一处改道**: atlas/css/views.css:317 的「守阵见」紧邻「components.css 顶 700 行体量上限」, 位置表建议的 test_frontend_frozen_column_boundary_wiring 实钉 .is-hscrolled 吸左发丝线(非 700 行 cap); 逐符号复核(拆分前旧件 2322 行 static_bundle_health 体内含 700 行 cap 断言; 拆分后该断言落 skin 件 test_frontend_template_split_wiring 的 181-196 行)后改指 test_frontend_template_split_wiring, 建议原文与改道理由均留在 issue 修复后补充。评审轮 1 抓回首版误指 static_bundle_health(拆分后该函数只调 _scan_frontend_assets(), 无 cap 断言)并订正。
- 范围守恒: memory-bank/ 冻结历史件的同类旧指称不在 src/ e2e/ 扫描面, 一行未改; 未发现需入池的计划外缺陷。

## 实现计划

1. 词边界复扫 + 逐符号核对 7 处现行定义点(防过期复验)。
2. 改 3 处 src(atlas/views.css · settings-detail.html · xtpl-cells.html)与 4 处 e2e 头注释。
3. issue 认领(In Progress)→ 结档(Done), 补复验/实际修法/验证方式, 建档案并双向补认领链。
4. 分批评审(只读子代理 + 引文校验)与全量回归, 结论与基线切片随本专题入库。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 复扫 + 逐符号核对定义点 | Done(2026-11-12) |
| S2 | 7 处注释改指 | Done(2026-11-12) |
| S3 | issue 认领/结档 + 认领链 | Done(2026-11-12) |
| S4 | 分批评审 + 全量回归 + 基线切片 | Done(2026-11-12) |

## 进度日志

### R0 · 立档 (2026-11-12)

S1-S3 完成: 7 处旧指称改指拆分后现行定义点, 词边界复扫 src/ e2e/ 三后缀命中归零(仅剩 memory-bank/ 冻结历史件); issue 26-11-12-0628 翻 Done 并补复验/修法/改道理由, 档案与 issue 的认领链双向声明由 kb.new --refs 一次补齐。评审与全量回归结论由收尾行追加; 随本专题入库。

- 2026-11-12 08:27 过期守阵指称族 css/html/e2e 面 7 处改指现行守阵定义点, issue 26-11-12-0628 翻 Done 并补复验/改道理由, 分批评审 3 轮零 actionable 出口, 全量回归全绿(见 kb.baseline)

### R1 · 收尾 (2026-11-12)

- `review:` 分批评审 4 轮(全能档; 末轮远端快进 1 笔把锚点推到 `9dc0dcd1`, 收尾派生坑档入可评面共 44 行): 轮 1 二发现(major = 700 行 cap 守阵首版误指 `static_bundle_health`, minor = 结档补充段把错误落点写成改道成果)引文 2/2 过检全修; 轮 2 一 major(结档补充段把未执行的全量回归与未建的本专题基线切片写成完成式 + 悬空 `kb.baseline` 引用)过检当场修; 轮 3 零新增 actionable; 轮 4 收尾派生件复评零 actionable 出口。累计检 3/3 · 修 3 · 入池 0 · 轮 4, 末轮基哈希 `d6dfb354497a`; `ship.gate` 各轮全绿。
- 全量回归: `commands run test.full` 全绿(见 kb.baseline 与基线切片 `26-11-12-0826-webui-guard-ref-css-e2e`), 裸数字只写切片一处; 会话切片 `26-11-12-0827-webui-guard-ref-css-e2e` 由 `kb.wrap` 落。
- 坑档: 新立 `pitfalls/kb/doc-verify-completed-claim.md`(轮 2 陷阱, 双向认领链由 `kb.new --refs` 补齐); 踩到已记坑 `pitfalls/kb/subagent-survey-fact-verify.md` **复发 +1** —— 为什么没命中: 开工只读了 `pitfalls/_index.md`, 没按「源码注释 / 语义映射」触发词深入该条(文件没读), 改指时凭拆分前旧函数名落笔而未读拆分后函数体验证断言归属。
- 债务转告: `kb.check` 的切片数 cap 债务告警(见 kb.check 债务行, 已超上限 120 条)按范围守恒不在本会话清理, 另开会话处理。
