# 6193 —— relocate 恢复确认账生命周期收口批全量基线

> 摘要: relocate 恢复确认账生命周期收口批全量基线
> 基线时间: 2026-11-15 13:18

## 验收数字

`commands run test.full` 实测(2026-11-15 13:18, Windows 开发机):

```text
TOTAL                                                27477     73   9664     78    99%
6193 passed, 2 skipped in 148.28s (0:02:28)
```

- 汇总: 6193 passed / 2 skipped, 覆盖率 99%(实测表尾 99% 由 pytest-cov 出)。
- 配套面: `commands run test.quick` 同数字(6193 passed, 2 skipped); relocate 受影响面定向(exec 五件 + resume_confirm + units + web_relocate + webui 三件)352 passed; e2e 面: 本机无 docker, `test.linux-env`/`test.linux-e2e` 起不了容器, 改跑 Windows 侧 `dev.e2e` 全量 —— 610 passed / 6 failed / 22 skipped(33.0m), **6 failed 全部与本分支无关**: 4 例 views/数据契约(300 vs 301)为 search-refresh 探针合成种子跨 spec 串扰(隔离复跑全绿), 2 例 flux(chip HR 语义 strict mode 双 chip / site-chip .f-on 辉光)在分支基座 46649c3f 临时 worktree 复跑同样复现(既有失败, 非本批引入); relocate-pop-terminal 新 spec 与 relocate-pair-filter(注释回写后)均 passed。

## 本改动面

计划 26-11-15-0914(relocate 恢复确认账五件联合修)S1-S4 四笔 + S5 收口:

- `src/auto_qb/core/modules/relocate_exec.py`(7ccc2a1b): S1 job_id 复用结转 —— `_carry_prev_state` 扩面, 旧账余量并入新账 resume_hashes(issue 0344, D14 锚 `_start_job`); 测试 `test_relocate_exec_jobs.py` / `test_relocate_resume_confirm.py` / `test_relocate_tag_mirror.py`。
- `src/auto_qb/core/modules/relocate_lifecycle.py` + `relocate_mod.py`(604b52b3): S2 已删成员闭账三态(常量 `_DELETED_CONFIRM_TICKS = 3`) + S4 stop() 停机计数摘要一行(issues 0345-deleted / 0345-feat, D9/D12/D13); 测试 `test_relocate_resume_confirm.py`(S2 七用例 + S4 两用例 `test_stop_logs_failure_counters_zero/nonzero`)。
- `src/auto_qb/webui/static/shared/relocate_pop.js` + `row_lang.css`(9a41204d): S3 终态(done/cancelled)浮窗窄放行 + 中性 tone 替身 view(issue 0345-popover, D11); 测试 `test_webui_relocate_pop.py`、新 e2e spec `relocate-pop-terminal.spec.mjs`、e2e 桩 `scripts/ui_harness.py`(4→5 粒)。
- S5 收口: e2e `relocate-pair-filter.spec.mjs` 两处注释漂移回写(ui_harness 桩改 5 粒后的口径校准, 零代码语义); D7 复核 `_RESUME_RETRY_MAX` 借用面不变(views_relocate.py 唯一消费方)、`_DELETED_CONFIRM_TICKS` 无配置化/第二消费方。
