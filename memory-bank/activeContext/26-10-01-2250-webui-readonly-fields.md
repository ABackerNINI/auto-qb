# webui-readonly-fields — issue 2135 实施完成(待提交)

> 摘要: 认领实施 issues/26-09-28-2135(WEBUI 设置页只读字段)已全部完成, 待 ship.commit 入库。
> 触发: 只读字段, 程序托管, readonly, issue 2135, 设置页

- **2026-10-01 22:55 收尾态**: 认领实施 issues/26-09-28-2135(WEBUI 设置页只读字段)已全部完成 —— ①schema `Field.readonly` + 四点位打标(schema_version/data_dir/state_file/fs 段与叶子 path_map) + `readonly_config_paths()`; ②前端 CE_FIELD_BASE 三 computed + tpl-hub-field 只读摘要分支/全控件 :disabled/「程序维护」徽标 + settings-detail 块级开关收口 + console_hub.css; ③cfgSave 反馈口径改「程序托管字段, 仅能在配置文件中修改, 本次未写入」; ④writer `_fallback_readonly_fields`(schema_version 豁免, 守阵钉住); ⑤守阵 +5。test.full **1929 passed + 3 skipped / 91%**(26.28s, 0 warnings, 基线 baselines/26-10-01-2250); 浏览器冒烟 96 项 1 flaky(P0-3 前行乐观, 与本改动无关), 定向验证全符合设计。档案 [tasks/26-10-01-webui-readonly-fields.md](../tasks/26-10-01-webui-readonly-fields.md)(已完成, 待 ship.commit 入库后本切片迁出)。
- **范围外发现(只记不修)**: 冒烟 flaky「P0-3 前行乐观(剧行 is-pending)」首跑 PASS/复跑 FAIL —— 轮询时序类, 建议归入 ui_smoke 时序容错专项。
