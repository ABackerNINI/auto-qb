# 26-10-01-webui-readonly-fields — issue 2135 清偿: WEBUI 设置页支持只读字段(程序托管/R 级)

**Status:** Done
**Added:** 2026-10-01
**Updated:** 2026-10-01 22:55
**Summary:** 实施 issue 26-09-28-2135 建议修法全部五条: ①schema `Field` 加 `readonly: bool = False`, 四点位打标(schema_version/data_dir/state_file/fs 段 + 叶子 fs.path_map); ②前端 CE_FIELD_BASE 加 readonly/readonlyComplex/readonlySummary 三 computed, hub-field 模板只读摘要分支 + 全控件 `:disabled` + 「程序维护」徽标, settings-detail 块级 section 开关对 readonly 段换徽标(fs.path_map 的 `[object Object]` 控件随之消失); ③保存反馈口径改为「程序托管字段, 仅能在配置文件中修改, 本次未写入」(不再谎报「需重启才生效」); ④writer `_prepare` 加 `_fallback_readonly_fields` 键面回退防线(schema_version 刻意豁免 —— 盖章承担其只读, 回退会吞掉「高于本程序支持」的精确校验错); ⑤守阵 +5(writer 3 / schema 1 / web 静态 1)。验证: test.full **1929 passed + 3 skipped / 91%**(26.28s, 0 warnings, rc=0), 真浏览器定向验证徽标/禁用/只读摘要全符合预期。
**Topics:** webui-readonly-fields
**Refs:** memory-bank/issues/26-09-28-2135-feat-webui-readonly-fields.html

## 原始请求

用户显式授权认领并实施 issue `26-09-28-2135-feat-webui-readonly-fields`: 设置页支持只读字段 —— 程序托管 / R 级字段改为只读展示。需求单唯一来源为该 issue 报告, 以报告内「建议修法」与验收口径为准(摸排注提示三段: Field 只读标志 + 前端禁用渲染 + 写盘防线, 三段都要落地)。若报告含开放决策点, 按报告建议方向选保守默认实施; W3 同页另两件 bug(26-09-25-1702 未保存丢改动 / 26-09-22-2002 伪警示条)明确不在本次范围。完成后按项目协议提交推送(授权已覆盖立档 / 改 issue 状态 / commit+push)。

## 思考过程与决策

- **复验(2026-10-01 22:0x)**: 按报告锚点重跑 —— `_stamp_schema_version`(writer.py 无条件盖章) / `_reject_stale_version` / `_fallback_restart_fields`(R 级回退) / `SECTION_LEVELS` 退役后的 R 闸 `impact.RESTART_SECTIONS`(state_file/data_dir/fs) / `groups.py` 四点位 / `config_editor.js` 的 `CE_FIELD_BASE`(grep readonly 零命中) / `routes/config.py::api_config_put`, **全部仍复现**; 入池锚点行号有漂移(CE_FIELD_BASE 现 967 附近, R 级三段在 impact.py:17 的 `RESTART_SECTIONS`), 符号与 grep 关键词均可命中。
- **readonly 打标粒度**: fs 段**与其叶子 path_map 都打标** —— 前端叶子分支只认自身 `Field.readonly`(嵌套组件经 inject 拿不到祖先的 readonly 态, 显式双标优于发明继承机制); writer 回退按段路径生效(`readonly_config_paths()` 对 readonly 段不再展开子树, 段整体回退已覆盖子树)。
- **写盘防线的位置**: 放 `_prepare` 尾部(R 级回退之后、盖章之前), 与 R 级回退同语义(旧值存在则覆盖 / 不存在则删键走默认)。两道防线覆盖面有交集无冲突(都回退到同一磁盘旧值), 任一失效另一道仍兜住 —— R 级回退只认「本次变更命中 R 闸的段」, readonly 防线按 schema 键面全量兜底, 防未来新增点位漏配时重演「可编辑但不生效」。
- **schema_version 豁免(报告红线)**: 它的只读由 `_stamp_schema_version` 盖章承担; 若 readonly 回退也碰它, 提交树里「比程序新的版本」会被抹平成磁盘旧值静默保存, 吞掉校验层本该报的精确错(「高于本程序支持」, 用户排障的唯一线索)。守阵 `test_write_tree_rejects_version_higher_than_program` 钉住该行为。
- **反馈口径**: R 级回退 = 值没写进去, 重启也不会生效 —— toast 改「`<paths>` 为程序托管字段, 仅能在配置文件中修改, 本次未写入」, 保留 timeout 型(琥珀色, 恰合「已保存但有未写入项」的中间态)。UI 只读化后正常操作不再触发该 toast(只剩陈旧页签 / 直调 API 路径), 属兜底反馈。
- **fs.path_map 控件形态**: 采报告建议改**只读摘要** —— 模板控件链首支加 `readonlyComplex` 分支(readonly 且值为列表/对象时), 每个映射对渲染一行 `from: … · to: …`(`readonlySummary` computed, 对象平铺 k: v、嵌套值 JSON 化), 替换原 text 控件(列表值 String 化出 `[object Object]`, 编辑产出必挂校验)。
- **验证手法**: pytest 守阵之外, 真浏览器(harness 桩 + Playwright 1.63.0, NODE_PATH 挂 npx 缓存)定向验证 —— schema_version/data_dir/state_file 三行 disabled=true + hb-readonly 类 + 徽标; fs 块头「程序维护」徽标且启用/关闭开关不渲染; 注入已配置 fs 段后 path_map 行渲染两条映射摘要行、无输入控件。全量冒烟 96 项仅 1 项失败(P0-3 剧行乐观时序, 首跑过/复跑未过 = flaky, 与设置页无关)。
- **范围纪律**: W3 另两件 bug(未保存丢改动 / 伪警示条)未触碰; 未顺手重构设置页其它逻辑。

## 实现计划

- schema: `fields.py` Field 加 `readonly` 字段(docstring 说明职责边界: 只标「后端机制会覆盖/回退用户输入」的字段); `groups.py` 四点位打标; `__init__.py` 加 `readonly_config_paths()`(点路径收集, readonly 段不展开)。
- writer: `_fallback_readonly_fields` + `_prepare` 接线(schema_version 豁免, 注释写明理由)。
- 前端: `config_editor.js` CE_FIELD_BASE 三 computed + cfgSave toast 口径; `tpl/xtpl.html` 只读摘要分支 + 全控件 `:disabled` + 徽标 + section 分支开关换徽标; `tpl/settings-detail.html` 块级 section 开关收口; `console_hub.css` 禁用态与摘要行样式。
- 守阵 +5: writer 3(readonly 段回退 / 磁盘未配置删键 / 高版本精确错) + schema 1(readonly 点位清单 == 4 点位 ∧ R 级段全打标 ∧ path_map 打标) + web 静态 1(CE_FIELD_BASE 三成员 / 摘要分支链首 / `:disabled` >= 7 / 徽标 / settings-detail 收口)。
- 收尾: 本档案 + issue 报告 Done(双向认领链) + 基线切片 + activeContext/progress 回写 + kb.index + gen_issues_index.py + ship.commit。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| 同步 (my-commit-flow.sync) | ✅ 完成 | 同步成功 015727b5, 工作树净 |
| 复验(重跑报告锚点) | ✅ 完成 | 四点位机制全部仍在, 行号漂移已记录 |
| schema 三件(Field/groups/__init__) | ✅ 完成 | readonly 标 + readonly_config_paths() |
| writer 写盘防线 | ✅ 完成 | _fallback_readonly_fields + schema_version 豁免 |
| 前端只读渲染 + 反馈口径 | ✅ 完成 | xtpl/settings-detail/config_editor.js/console_hub.css |
| 守阵 +5 与 test.quick 迭代 | ✅ 完成 | 首轮 2 failed(夹具路径不合法/断言口径), 修正后全绿 |
| 真浏览器冒烟 + 定向验证 | ✅ 完成 | 96 项 1 flaky(与设置页无关); 定向验证全符合预期 |
| test.full + 基线切片 | ✅ 完成 | 1929+3 / 91%; baselines/26-10-01-2250 |
| 认领链(本档案 + issue Done) | ✅ 完成 | 双向 doc-refs; kb.index + gen_issues_index.py |
| ship.commit | ✅ 完成 | hash 以本仓库 git log 为准(提交无法携带自身 hash) |

## 进度日志

- **2026-10-01 22:05** 同步成功 015727b5(工作树净)。读 issue 报告全文与 pitfalls 索引: web-ui 类(frontend-split 找模板口径: 聚合读 `_ui_aggregate`, 模板单点在 shared/tpl/xtpl.html; search-views 的 schema 单点口径)、backend 类(schema-stamp-writeback 盖章语义)、testing 类(tmpdir/sandbox-full-run/smoke)。定位源码: schema 四件 + writer + impact + routes/config.py + config_editor.js + config_hub.js + tpl/xtpl.html + tpl/settings-detail.html + console_hub.css。实施三段落地(方案见「思考过程与决策」)。
- **2026-10-01 22:20** test.quick 首轮 2 failed —— 均为本笔新测试的夹具问题: ①fs.path_map 夹具路径 `d/new` 不满足校验「必须是绝对路径」; ②`load_config(path).fs is None` 断言口径错(默认是空 FsConfig 不是 None)。修正后 test.quick **1929 passed, 3 skipped**(21.80s)全绿; dev.fmt 七个改动 .py 全跑。
- **2026-10-01 22:40** 真浏览器冒烟: harness 桩(200 种子, 端口 8123)+ ui_smoke.cjs 96 项, 仅「P0-3 剧行乐观(剧行 is-pending)」1 项 flaky(首跑 PASS/复跑 FAIL, 轮询时序类, 与设置页改动无关); 「无 console.error / pageerror」与设置页全部断言 PASS。定向验证(一次性脚本, 临时目录产物不入仓库): schema_version/data_dir/state_file 行 disabled=true + 「程序维护」徽标 + hb-readonly 类; fs 块头徽标且开关不渲染; 注入已配置 fs 段后 path_map 渲染「from: D:/Downloads · to: /mnt/downloads」式摘要行、无输入控件 —— 与设计逐项吻合。桩服务按 pitfalls/testing/smoke.md 口径(PowerShell 按端口)清理。
- **2026-10-01 22:48** test.full **1929 passed + 3 skipped / 91%**(26.28s, 0 warnings, rc=0; 13326 语句 / 1030 未覆盖 / 4432 分支 / 435 partial), 基线切片 baselines/26-10-01-2250-webui-readonly-fields.md。相对上一基线(1916+3 @ f3564847)的 +13 中, 本笔守阵 +5(writer 3 / schema 1 / web 1), 其余 +8 来自同步合流的既有提交(W2 token 守阵 +3 等)。
- **2026-10-01 22:55** 收尾回写: 本档案 + issue 报告 Done(徽标/kicker/meta/doc-refs/复验/修复后补充/状态日志) + activeContext 切片 + progress/implemented-webui.md 条目 + kb.index + gen_issues_index.py; test.quick 复跑确认认领链守阵(test_docs_forms::test_claim_chain_is_bidirectional)绿。
- **2026-10-01 23:00** 合流: ship.commit 首跑因远端新提交(433f9549, 全为文档/索引回写)与本地重叠被拒 —— 按 failure 行指引 stash(-u) 移出 → sync 快进 433f9549 → pop 自动合并(唯一冲突 issues/_index.md, 生成物) → gen_issues_index.py + kb.index 在新基线重建 → test.full 复测 **1929 passed + 3 skipped / 91%**(28.10s, 与合流前 26.28s 同数字) → 基线切片改记合流后基线 → 重跑 ship.commit。
