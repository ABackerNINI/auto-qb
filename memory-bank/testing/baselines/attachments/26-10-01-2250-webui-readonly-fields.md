# 基线 · 1929 passed + 3 skipped / 91% —— WEBUI 设置页只读字段(issue 2135 清偿)

> 摘要: issue 26-09-28-2135(Field 只读标志 + 前端禁用渲染 + 写盘防线)实施完成的收官基线。
> 档案: [tasks/26-10-01-webui-readonly-fields.md](../../tasks/26-10-01-webui-readonly-fields.md)。
> 基线时间: 2026-10-01 23:00, develop @ 433f9549 (与远端合流后的新基线上复测; 工作树含本笔改动与收尾回写, 未提交)。

TOTAL **1929 passed + 3 skipped / 91%**(13326 语句 / 1030 未覆盖 / 4432 分支 / 435 partial,
test.full 26.28s @ 015727b5 / 28.10s @ 433f9549 两采样, **0 warnings**, rc=0)。相对上一基线
(1916+3 @ f3564847, 26-10-01-2125)的
+13 中, 本笔守阵 **+5**(test_config_writer 3: readonly 段回退/磁盘未配置删键/高版本精确错;
test_config_schema 1: readonly 点位清单断言; test_web 1: 前端 readonly 接线静态守阵),
其余 +8 来自同步合流的既有提交(W2 token atomic 守阵 +3 等)。test.quick 单跑全绿
(1929+3, 21.80s); 迭代期首跑 2 failed 均为本笔新测试夹具问题(路径不合法 / FsConfig 断言口径), 修正后绿。

## 本笔改动面 (守阵增量明细)

- `config/schema`: `Field.readonly` 标志 + 四点位打标(schema_version/data_dir/state_file/fs 段与叶子 path_map)
  + `readonly_config_paths()`; 守阵 test_readonly_fields_are_program_managed 钉住点位清单与 R 级段⊆readonly。
- `config/writer.py`: `_fallback_readonly_fields`(schema_version 豁免 —— 盖章承担其只读, 回退会吞
  「高于本程序支持」精确错, 守阵 test_write_tree_rejects_version_higher_than_program 钉住)。
- WebUI 前端: hub-field 只读摘要分支 + 全控件 :disabled + 「程序维护」徽标 + settings-detail 块级开关收口;
  静态守阵 test_frontend_hub_field_renders_readonly_fields(三皮肤聚合断言)。
- 浏览器冒烟: harness 桩 + ui_smoke.cjs 96 项, 1 项 flaky(P0-3 前行乐观时序, 首跑 PASS, 与本改动无关);
  定向验证(临时脚本)徽标/禁用/只读摘要逐项符合设计。
