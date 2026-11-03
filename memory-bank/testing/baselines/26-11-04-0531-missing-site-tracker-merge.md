# 5121 passed, 10 skipped in 182.72s (0:03:02); TOTAL 23896 stmts / 230 miss / 8158 branch / 173 partial / 98.69% —— 缺失站点扫描 fresh 直查旁路 tracker 惰性缓存全量测试基线

> 摘要: 缺失站点扫描 fresh 直查旁路 tracker 惰性缓存全量测试基线
> 基线时间: 2026-11-04 05:31
**Refs:** memory-bank/issues/26-11-04-0228-bug-sites-missing-stale-tracker-cache.html

## 验收数字

- 汇总行: `5121 passed, 10 skipped in 182.72s (0:03:02)`(2026-11-04 本机 Windows 实测)
- 覆盖率 TOTAL: `23896 stmts / 230 miss / 8158 branch / 173 partial / 98.69%`
- 口径注记: pytest 直接全量跑(等价 test.full 展开; 本机 shell 外部 TMPDIR 需 `env -u TMPDIR` 前缀, 坑档 testing/tmpdir)
- ⚠覆盖率低于 99% 阈值(FAIL): 缺口 45 条 miss 系同机证明代码(e80d9f8e, stmts 23370→23896)在无真机条件下 8 条测试 skip 所致 —— 非本改动引入(改动面三文件 0 miss); 对照 02:45/02:53 入库前切片 23370 stmts / 167-185 miss / 99%(其中 02:53 为真机在位 2 skipped 口径)
- 首轮全量 1 failed(test_qbmanager_w6::test_w6_flush_fallback_once_per_round, 主循环 tick 时序 flaky, 同域既有 issue 26-09-20-0952), 单独/整文件复跑均绿后全量重跑如上, 一次性绿

## 本改动面

- `src/auto_qb/core/qbapi.py`: 新增 `torrents_trackers_fresh(torrent_hash)` —— 旁路 store 记录级惰性缓存的 tracker 直查, 脱敏同口径(mask 过 Facade); 常规 `torrents_trackers` 读路径不动(issue 26-11-04-0228)
- `src/auto_qb/core/exporter.py`: `collect_torrent_tracker_hostnames` 优先走 fresh 直查(getattr 探测, 非 facade 兼容客户端/测试桩回退普通读); CLI 与 WEBUI 扫描同一入口一并覆盖
- `tests/test_exporter.py`: 两条新回归 —— prefers_fresh_bypass(有 fresh 方法逐种直查) + fresh_bypass_facade_cache(红验: 记录级缓存吃 qB 侧旧值时扫描读到新值且不回填污染); 头部测试计划清单同步
- `memory-bank/issues/26-11-04-0228-*.html`: 状态 Open→Done, 复验行/修复后补充/影响面核实结论回写; `memory-bank/issues/_index.md` kb.index 重建
- 真机红验件 tests-real RM08-12 本机未跑(无真机轨), 待下次真机轮自然复验
