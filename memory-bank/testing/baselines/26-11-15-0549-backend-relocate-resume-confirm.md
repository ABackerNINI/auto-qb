# 6161 passed + 2 skipped —— fuse 让路收窄账窗口与穷尽文案两修批全量绿

> 摘要: fuse 让路收窄账窗口与穷尽文案两修批全量绿
> 基线时间: 2026-11-15 05:49
> 档案: memory-bank/tasks/26-11-15-backend-relocate-resume-confirm.md

## 验收数字

`commands run test.full` 实测(2026-11-15 05:49, Windows 本机, 本分支最终代码态 f617cad7+4dea136e):

```
TOTAL                                                27412     72   9632     77    99%
6161 passed, 2 skipped in 164.66s (0:02:44)
```

覆盖率 99%。缺口净额 +2(上片 miss+partial=71+76=147 → 本片 72+77=149; 分母语句 27397→27412 / 分支 9624→9632, 测试改造带入), 未超 +15 无点名。已知噪声源: `test_hr_discovery.py::test_start_all_busy_returns_false_and_retries` 计时敏感 flaky(issue 26-11-15-0546 入池), 本轮全量未命中。

## 本改动面

- `src/auto_qb/core/modules/fuse_mod.py`: to_pause 三支让路谓词 relocating→resuming(getattr 单点口径不变), 注释随口径重写 —— 让路窗口从「relocating 登记生命周期(非终态 job 并集)」收窄为「恢复确认账在走(store.resuming_hashes 并集)」
- `src/auto_qb/core/modules/relocate_lifecycle.py`: 新登记 resuming_hashes 生产面 —— `_note_resume_state` 落账单点直呼重算(账开/闭合/穷尽收敛零滞后, 该点不走 _set_job) + `_sync_relocating` 漏斗末尾附带刷新(job 变更/启动加载/热启用; 终态挂账 job 也进登记)
- `src/auto_qb/core/modules/relocate_mod.py`: resuming 登记随 resume 出口接线
- `src/auto_qb/torrents/store.py`: 新登记 `resuming_hashes`(账窗口=resume_pending 非空并集, 非 job 窗口, 纯内存)
- `src/auto_qb/webui/static/shared/decorate.js`: `relocateResumeText` 穷尽分支文案「补发穷尽, 需手动恢复」→「不再补发」(不对是否需手动恢复做时点承诺)
- `src/auto_qb/webui/views_relocate.py`: 注释/docstring 口径随文案同步(投影字段与判定零改动)
- `tests/test_fuse_mod.py` 改造 3 例+新增 4 例(全链 restreak/即时重算不滞后/终态+穷尽保留/启动重建); `tests/test_relocate_resume_confirm.py` +4; `tests/test_webui_relocate_pop.py`/`tests/test_webui_relocate_visibility.py` 断言钉扎随文案
- `memory-bank/`: issue 26-11-15-0441 两件翻 Done + flaky 用例入池(26-11-15-0546) + 任务档案与切片回写
