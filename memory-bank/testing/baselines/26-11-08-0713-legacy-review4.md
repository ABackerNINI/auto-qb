# 5753 —— test.full 5753+2: R4 config-infra 36 条收口合并树基线

> 摘要: test.full 5753+2: R4 config-infra 36 条收口合并树基线
> 基线时间: 2026-11-08 07:13

## 验收数字

TOTAL 表: 25635 语句, 12 miss, 8870 分支, 34 部分分支, **99%** 覆盖
汇总行: **5753 passed, 2 skipped, 7 warnings in 137.07s (0:02:17)** — 0 failed
口径: `commands run test.full`, develop @ 0469bf0c(远端 70bba719 + R4 config-infra 36 条认领分支 merge); 上一切片(远端 9daad745 记录 5651+2+1failed, 存量措辞守卫红)→ 本切片 5753+2+0failed: 合并树全绿, 远端记录的存量 failed 在本树已不存在

## 本改动面

- 存量评审 R4 config-infra 汇总件(memory-bank/issues/26-11-07-0527)36 条认领修复全落: 6 批次提交 f5edc616/fd08ebb6/64e0cc8c/2deebdb5/fa4ddeaf/dfb6384a(每批 Review trailer 见 git log; #26 复验已消失), 接缝终审零发现
- 代码面: infra/utils_paths.py+file_access.py+alias_fs.py+notify.py+utils.py+utils_parse.py+versioning.py、config/loaders.py+validation×3+schema/__init__.py+migrations.py+compat.py+writer.py、rules/conditions.py+expr×4+actions/__init__.py、webui add_torrent.js+fs.py+lifecycle.py+notify_mod.py; 新增测试散布 test_utils_path/test_file_access/test_conditions/test_config_misc/test_config_rules/test_config_writer_mask/test_config_writer_write/test_config_schema/test_alias_fs/test_webui_relocate_chain/test_notify/test_core_modules/test_utils_parse/test_expr_parse
- 文档面: issue 0527 置 Done+复验+逐批修法; 6 条计划外入池(26-11-08-0703 系列); modules/rules-and-deps.md 漂移修正
- 测试数字增量: 各批次 test.quick 5674→5676→5680→5683→5686→5690(本分支逐批), 合并远端后 test.full 5753+2
