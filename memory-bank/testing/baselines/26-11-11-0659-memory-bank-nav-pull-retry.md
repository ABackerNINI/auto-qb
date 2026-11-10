# 6007 passed, 2 skipped —— kb.nav 拉取重试批次全量基线

> 摘要: 6007 passed, 2 skipped (185.45s), 覆盖率 99% (26747 stmts / 55 miss / 9362 br / 66 partial) —— kb.nav 拉取按钮 git 层有界重试批次(任务 26-11-11-memory-bank-nav-pull-retry)收尾全量绿
> 基线时间: 2026-11-11 06:59

## 验收数字

- 汇总行: `6007 passed, 2 skipped in 185.45s (0:03:05)`(commands run test.full 实测誊写)
- 覆盖率 TOTAL 表: `26747 stmts / 55 miss / 9362 br / 66 partial -> 99%`
- 与上一切片 [26-11-11-0504](26-11-11-0504-ship-gate-prerun.md)(6002/2)差值: +5 passed —— 本批新增面(tests/test_kb_nav_server.py 补 5 条重试测试)

## 本改动面

- 修改 `.agents/skills/memory-bank/scripts/nav_server.py`(_git 层有界重试: _git_once Popen+看门狗+_kill_tree / _retryable 三档判据 / retry_note; pull_ff_only 失败行接重试备注)
- 修改 `tests/test_kb_nav_server.py`(补 5 条: 三档判据 / 抖动自愈 / 三次全败带备注 / merge 零重试 / rc=-1 映射)
- 修改 `.commands/kb/config.toml`(kb.nav note 补重试口径一句)
- 真机: 本地起 nav 服务 POST /api/pull 实跑 Gitee(「已是最新 90764579」)+ 跨源 403 护栏, 通过
