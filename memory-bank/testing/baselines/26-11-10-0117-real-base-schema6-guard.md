# 5879 passed, 2 skipped (139.41s), 覆盖率 99% (26152 stmts / 41 miss) —— tests-real 基座 schema 6 对齐 + 守卫批全量绿

> 摘要: tests-real 基座 schema 6 对齐 + 守卫批全量绿
> 基线时间: 2026-11-10 01:17
**Refs:** memory-bank/issues/26-11-08-0044-test-tests-real-rm08-schema-version-stale.html

## 验收数字

```text
TOTAL                                                26152     41   9102     53    99%
5879 passed, 2 skipped in 139.41s (0:02:19)
```

(实测时点: HEAD 5529b9f8 + 本批工作树改动, `commands run test.full` 2026-11-10 01:15)

## 本改动面

- **修 issue 26-11-08-0044**: tests-real 13 文件基座字面量/拒跑断言/docstring `schema_version: 5→6`(lib/app.py + RM02~RM10, 用户拍板全 tests-real 一次改净)—— 产品 config 现行 v6, 写 5 会走启动物化 v5→v6 迁移改写+留 `config.yml.v5.bak`(auth 实例连 token 一起进备份), 写 6 零 IO。产品单点实测: v5 → desc=`v5→v6`+备份, v6 → `""`; v6 配置过 load_config 全量校验。
- **新守卫** `tests/test_real_schema_version_guard.py`(2 用例): 扫 tests-real 基座字面量断言 == `CURRENT_VERSIONS["config"]`(rm09 keys 域 (文件,值) 豁免)+ 守卫活性自检; 反证改回 5 即红。全量 +2 例(5876→5879)。
- **回写**: issue 翻 Done + 修复后补充; 坑档 pitfalls/testing/base-schema-version-staleness.md(索引 kb.index 重建); memory-bank/testing/real-machine.md 口径行回写(含 dry-run 限定语)。
- 评审: 分面 2+修复轮 2 次(轮 3), 全部发现当场修毕, 零 actionable 收口。
