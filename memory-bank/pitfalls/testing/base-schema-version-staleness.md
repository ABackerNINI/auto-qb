# tests-real 基座写死 schema_version 字面量: 产品 bump 后静默过期

> 摘要: tests-real 各片基座(write_cfg/CONFIG_TEMPLATE)写死 `schema_version: <当时现行版>` 避免迁移改写 —— 产品 config schema 一 bump, 该字面量立即过期, 启动物化(materialize_schema_migration)开始改写落盘+留 `<名>.v<m>.bak` 搅浑用例临时目录, 而现有「缺 N 拒跑」断言只查写入前文本所以恒绿。守卫 = `tests/test_real_schema_version_guard.py` 扫字面量断言 == `CURRENT_VERSIONS["config"]`。
> 触发: schema_version, 基座, 版本字串, 迁移改写, config.yml.v5.bak, 版本备份, CURRENT_VERSIONS, 启动物化, materialize_schema_migration, v5→v6, 版本过期, 测试基座

**Refs:** memory-bank/issues/26-11-08-0044-test-tests-real-rm08-schema-version-stale.html · tests/test_real_schema_version_guard.py

## 坑

「必写当前版本避免迁移改写」是一条**会过期的口径**: 写死的版本字串只在产品 schema 未 bump 时成立。产品 v6 上线(退役 `relocate.finalize_timeout`)后, tests-real 13 处基座字面量(lib/app.py + RM02~RM10)写 5 → 每个用例实例启动都走 v5→v6 迁移改写 + 留 `config.yml.v5.bak`(带 token 的 auth 实例连凭据一起进备份文件); 「缺 5 拒跑」断言查的是**写入前的模板文本**, 字面量自洽恒绿, 副作用完全静默(issue 26-11-08-0044, 2026-11-10 清偿)。同构陷阱: 同名字段可能属于别的域(rm09 的 WebUI keys 模板包 `schema_version: 1/2`), 机械扫描要按 (文件, 值) 显式豁免, 不能一刀切。

## 动作

- **产品 config schema bump 时, `tests/test_real_schema_version_guard.py` 会红** —— 红了照它指的文件把基座字面量抬到新现行版(字面量形: YAML 模板 `schema_version: N` 与 dict `"schema_version": N` 两种, docstring 措辞一并改), 不要只改模板不改断言/docstring。
- **给基座加字面量时优先想守卫**: 新片基座写 `schema_version: <现行版>`(别从旧片抄旧值); 新增同名字段但非 config schema 的域(keys 类), 必须同步更新守卫的 `_OTHER_DOMAIN` 豁免表并在表注写明域语义。
- **断言面别只查写入前文本**: 「配置缺 N 拒跑」防的是手滑删键, 防不了「N 过期」—— 过期防线只在守卫测试一处, 别在各片复制粘贴第二份版本号口径。

## 复发

- (0)
