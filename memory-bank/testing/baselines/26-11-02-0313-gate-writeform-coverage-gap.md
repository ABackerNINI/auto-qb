# 4820 passed + 2 skipped(根) —— 提交闸门双红清零(旧档 CRLF+LF 混排 + 覆盖率缺口补测)

> 摘要: 4820 passed + 2 skipped(根) — 提交闸门双红清零(旧档 CRLF+LF 混排 + 覆盖率缺口补测)
> 基线时间: 2026-11-02 03:13
**Refs:** memory-bank/testing/baselines/26-11-02-0245-core-w8-relocate-mutation-guard-cleanup.md

## 验收数字

- **目标**: 全量 pytest(`tests/` 全量 + `src/` 覆盖率报表), 测于提交闸门双红修复后的工作树(HEAD `a0469b80` + 上轮 W8 未提交改动 + 本轮闸门修复)
- `commands run test.full` 实测(wrapper 墙 168.1s, 2026-11-02 03:13, Windows 本机):
  - 汇总行: `4820 passed, 2 skipped in 165.88s (0:02:45)`
  - TOTAL 表: `TOTAL  22511  138  7722  131  99%`(stmts / miss / branch / partial / 覆盖率显示值)
  - 覆盖率闸: `Required test coverage of 99.0% reached. Total coverage: 99.08%`(带明细轮实测)
- **环境 / 工具**: Windows 本机(win32)· Python 3.13 · pytest-xdist 8 workers · `TMPDIR` 由 `test.full` 包内内置(不手工加前缀)
- **两处闸门红根因与修法**:
  - ① `test_md_no_mixed_line_endings`: 10 个 2026-09 旧 task `.md` 在工作树内 `CRLF xN + LF x1` 混排(HEAD blob 为纯 LF、`git diff` 为空); 按仓库 `.gitattributes` 的 `eol=lf` 口径做字节级归一 `read_bytes().replace(b"\r\n", b"\n")`, 零内容改动; 修后 4 条写盘形态守卫全过。
  - ② 覆盖率 98.96% → 99.08%: 真实缺口在 `src/auto_qb/transfer/adapters/qb.py` 的 orchestrator 扩展点(`find_torrent` / `pause_torrent`, 此前完全无测试)与六条错误分支; 在 `tests/test_transfer_adapters.py` 新增 11 条守阵(每条在文件头「测试计划」登记), 非凑数断言。既非统计口径失真也非生成物导致, 不删测试。
- 相对上基线逐位对比不写, 看差值 `commands run kb.baseline -n 2`

## 本改动面

- `tests/test_transfer_adapters.py`: 新增 11 条守阵 —— `test_qb_test_connection_unexpected_error`、`test_qb_add_text_rejected_result`、`test_qb_add_metadata_zero_counts_failed`、`test_qb_add_login_failed_result`、`test_qb_hash_exists_query_failure`、`test_qb_add_super_seeding_apply_failure`、`test_qb_find_torrent_mapping_record`、`test_qb_find_torrent_absent`、`test_qb_find_torrent_query_failure_returns_none`、`test_qb_find_torrent_non_mapping_record`、`test_qb_pause_torrent_success_and_failure`; 另 `test_normalize_tags` 补标量兜底一条断言。
- `memory-bank/tasks/26-09-*.md`(10 件): 工作树行尾归一 LF(内容零改动, HEAD blob 无差异)。
- 知识库: 本基线切片; `kb.index` 重建生成物。
- **零 `src/` 改动**; `config.yml` / `auto-qb-data/` 红线未触碰。
