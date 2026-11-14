# 6157 passed + 2 skipped —— relocate fuse 让路与恢复确认批全量绿

> 摘要: relocate fuse 让路与恢复确认批全量绿
> 基线时间: 2026-11-15 03:51
> 档案: memory-bank/tasks/26-11-15-backend-relocate-resume-confirm.md

## 验收数字

`commands run test.full` 实测(2026-11-15 03:57, Windows 本机, 收尾回写完成后的本批工作树; 03:49 实施树首轮同数字):

```
TOTAL                                                27397     71   9624     76    99%
6157 passed, 2 skipped in 172.81s (0:02:52)
```

覆盖率 99%。

## 本改动面

- `src/auto_qb/core/modules/fuse_mod.py`: to_pause 三支收集点(_scan_unmanaged 监控支/_advance armed 支/_advance triggered 分支)各加 relocating_hashes 让路(getattr 单点); 窗口拍不计连击(confirm_count/_streak 清零)
- `src/auto_qb/core/modules/relocate_lifecycle.py`: _reconcile_resume_pending/_resume_reissue/_member_stopped/_resume_retries_of/_note_resume_state + _RESUME_RETRY_SECONDS=30.0/_RESUME_RETRY_MAX=3; 四出口开账; resume_pending/resume_retries 序列化进 job_to_dict/job_from_dict; _finish_direct 次序改 done 落账后再恢复
- `src/auto_qb/webui/views_relocate.py`: member_relocate 投影 +4 字段(resume_pending_count/resume_pending_hashes/resume_retries/resume_exhausted)
- `src/auto_qb/webui/static/shared/decorate.js`: relocateResumeText 文案单点(空账零噪音; 穷尽/在途区分位只认后端)
- `src/auto_qb/webui/static/shared/drawer_rows.js`: 抽屉两条件行(待恢复成员/待恢复哈希)
- `src/auto_qb/webui/static/shared/relocate_pop.js`: 悬停浮窗 kv 行(待恢复成员)
- `tests/test_fuse_mod.py` +3 例; 新 `tests/test_relocate_resume_confirm.py` 14 用例(全 FakeClock); `tests/test_webui_relocate_visibility.py` +3 例; `tests/test_webui_relocate_pop.py` 探针扩段
- `memory-bank/`: issue 26-11-14-1744 两件翻 Done + 邻接面 5 条入池 + 任务档案与切片
