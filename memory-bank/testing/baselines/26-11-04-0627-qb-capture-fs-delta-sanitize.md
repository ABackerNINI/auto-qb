# 5126 passed + 10 skipped; 覆盖率 99%; test.full 248.0s —— 全量测试基线 · fs_delta 脱敏修复后(2026-11-04)

> 摘要: 全量测试基线 · fs_delta 脱敏修复后(2026-11-04)
> 基线时间: 2026-11-04 06:27
**Refs:** memory-bank/issues/26-11-03-1144-bug-qb-capture-fs-delta-sanitize.html, memory-bank/activeContext/26-11-04-0628-qb-capture-fs-delta-sanitize.md

## 验收数字

- 汇总行: `5126 passed, 10 skipped in 245.32s (0:04:05)`(2026-11-04 本机 Windows 实测, `commands run test.full` 总耗时 248.0s)
- 覆盖率 TOTAL: `23933 stmts / 229 miss / 8184 branch / 171 partial / 99%`
- 口径注记: 本机 Windows 走 `commands run test.full`(内部已带 TMPDIR 自举); 上基线 26-11-04 05:31 为 `5121 passed` / `23896 stmts / 230 miss / 8158 branch / 173 partial / 98.69%`, 本切片 +5 passed(3 条新用例 + 2 条既有用例扩形态), miss -1, partial -2
- 定向口径: `commands run test.one -- tests/test_qb_capture.py tests/test_sim_corpus.py` 51 passed(5.9s), 其中修复前同命令为 4 failed / 47 passed(红验证据)

## 本改动面

- `scripts/qb_capture.py`: `sanitize_all` 增逐帧 `fs_delta` 分支; 新增 `_san_fs_delta`(外层 `san.infohash` + 内层 `san.name(utils.path_normalize(rel))`, 与 files_map/disk_map 同源; 对不上 files 的行丢弃并 WARN `fs_delta_unsanitized`, 取样只写伪值); `sanitize_stream_consistent` 增 fs_delta 判据(`fs_delta_hash_not_in_files` / `fs_delta_rel_not_in_files` / `fs_delta_orphan_count`)
- `tests/test_qb_capture.py`: 新增 3 条(同源派生 / 未知行丢弃且不泄漏 / 自检红转绿); `test_write_corpus_end_to_end_minimal` 扩 fs_delta 落盘后 .gz 明文零泄漏断言; 头部「## 测试计划」同步
- `tests/test_sim_corpus.py`: `test_timeline_applies_fs_delta` 扩四形态(出现 / 删除 / 改名 / .!qB 后缀), 夹具 files/disk/fs_delta 同步; 头部「## 测试计划」同步
- `memory-bank/issues/26-11-03-1144-*.html`: 状态 In Progress→Done, 修复后补充回写, 正文「静默丢增量」口径订正为「叠到错误完整路径」
- 真机 `--probe-fs` 抽样终验未跑(本机无真机轨), 留待下次真机轮
