# 26-10-15-backend-store-recover-lock-dedup — hr 恢复链与文件锁跨包收口(issue hr-store-recover-lock-family-dup 认领与修复)

**Status:** Done
**Added:** 2026-10-15
**Updated:** 2026-10-21
**Summary:** 用户指令「认领并修复 memory-bank/issues/26-10-11-0240-refactor-hr-store-recover-lock-family-dup.html」—— dup-code-audit infra 轮(R18)对 R6/R2/R3 三轮暂缓跨包件的合并考量收口。口径沿用前修复轮保守纪律(行为逐位不变, 仅编排/构造收口): ① `infra/store_recovery.py` 新增「读坏→(挪走)留证→读 `.bak`」编排单点 `recover_corrupt_file`(回调式 read_backup + 可选 quarantine, 不传 = 原地保留)与 `quarantine_bad_file` 时间戳留证单点, hr `HrLockSession._recover` 与 state `StateService.load()` 损坏分支两处调用 —— 语义差异(hr 挪走留证/schema 迁移/read_error 消息 vs state 原地保留/_CORRUPT 三态/分级日志/立即自愈写回)全部保留在调用方; ② `infra/locking.py` 新增 `open_file_lock`/`release_file_lock` 构造/释放单点, hr 站点锁与 SingleInstanceLock 同族收口(hr/store 不再裸 import filelock); ③ 新守阵 tests/test_store_recovery.py 十条(静态两判据均过红验)。测试数字唯一权威在基线切片(见 **Refs:**)。
**Topics:** dup-code-audit

**Refs:** memory-bank/issues/26-10-11-0240-refactor-hr-store-recover-lock-family-dup.html, memory-bank/testing/baselines/26-10-15-0540-backend-store-recover-lock-dedup.md
## 原始请求

> 用户(2026-10-15): 「认领并修复 memory-bank/issues/26-10-11-0240-refactor-hr-store-recover-lock-family-dup.html」

## 思考过程与决策

- **请求边界判定**: 执行任务(改代码 + 认领 issue)。用户显式「认领并修复」= 指派 + 修复双授权(create-issue skill「Agent 不得自行认领」以用户指派为前提, 本条满足); 未含 commit/push 授权, 收尾不做提交。
- **复验(防过期原则 5)**: 锚点仍在 —— hr/store.py 裸 `FileLock`(import + 构造各一处)、恢复链两套同族(`_recover` ↔ `load()` 损坏分支); 相对入池取证的 2026-10-11 02:39 行号有漂移(轮次间文件长短变化), 按符号 + grep 重定位。
- **回调式单点 vs 内置编排(改道点)**: 首版把「先留证」做进 infra 内部(按 path 直接挪), hr 两条例行 seam(`store.quarantine = lambda: ""` 模拟挪不动)被绕过, 首跑 test.one 双红 —— 说明**处置动作必须经调用方回调**: 单点只保留编排顺序纪律与兜底实现(`quarantine_bad_file`), hr 的 `store.quarantine` 方法保留为公开面 + seam。改道后双红即绿。
- **语义差异保留判据**(issue 建议点名的两处 + 实测第三处): hr 有 schema 迁移/版本回退即拒(recoverable=False 不挪也不从备份猜)、坏文件挪走留证、结论拼 `read_error`; state 有 `_CORRUPT` 三态、future 版本 fail-fast(不算损坏)、原地保留、立即自愈写回且失败不阻断启动。单点只收「顺序纪律 + 挪文件 + (数据, 原因) 契约」, 消息/日志/迁移/写回全部留调用方。
- **不合并的第三处差异**: state 的 `_write_back_recovered`(立即自愈写回, OSError 只告警)与 hr 的 commit 期 `keep_backup=not recovered_from_backup` —— 时机/载荷/异常口径都不同; 且 `test_load_state_recovered_writeback_failure_is_nonfatal` 按 `qb_state.utils.atomic_write` 打补丁(模块属性), 抽走会把补丁面打穿。只各保留 + 在 infra/store_recovery docstring 以第 3 条纪律互指。
- **锁收口的粒度**: 不做「锁类统一」—— SingleInstanceLock 有 meta 伴生/固定超时 0/CLI 错误通道, hr 有 per-site 路径/可配超时/HrLockBusy 领域异常, 强并类会改错误语义; 只收 filelock 依赖与构造/释放纪律(`open_file_lock` / `release_file_lock`), Timeout→领域异常的翻译留各自调用方。
- **filelock 版本事实**: 本仓锁定 3.32.6, `BaseFileLock` 已无 `_lock_file` 属性(句柄由库内 fd 生命周期自理), 旧 `_lock_file.close()` 仅作旧版兜底(AttributeError 静默跳过) —— `release_file_lock` 内保留兜底并注明, 行为与改前等价(改前该方法同样静默跳过)。

## 实现计划

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 开工同步 + issue 复验 + 置 `In Progress` + kb.index | Done |
| S2 | `infra/store_recovery.py` 编排单点(回调式) + `quarantine_bad_file` | Done |
| S3 | `infra/locking.py` 构造/释放单点 + SingleInstanceLock 委托 | Done |
| S4 | `hr/store.py`: 锁走单点 / quarantine 委托 / `_recover` 走编排 | Done |
| S5 | `core/state.py`: `load()` 损坏分支走编排 + `_read_backup_dict` | Done |
| S6 | 守阵 `tests/test_store_recovery.py`(静态 2 + 行为 8) + 红验 | Done |
| S7 | test.full 全量 + 基线切片 | Done |
| S8 | 收尾: issue 置 `Done`(doc-refs) / 档案 / 切片 / kb.index / kb.check | Done |

## 子任务状态表

| 子任务 | 状态 | 说明 |
| --- | --- | --- |
| 恢复链编排单点 | Done | `recover_corrupt_file`(回调式) + `quarantine_bad_file`; hr/state 两处调用 |
| 语义差异保留 | Done | hr 迁移/read_error/挪走留证 vs state 三态/分级日志/原地保留/立即自愈 |
| 文件锁单点 | Done | `open_file_lock` / `release_file_lock`; hr 站点锁与 SingleInstanceLock 共用 |
| 守阵与红验 | Done | 静态两判据(`.bad-` 字面量分布 / `from filelock import` 分布)均红验; 行为用例 8 条 |
| 认领链 | Done | issue `doc-refs` ↔ 本档案 `**Refs:**` 双向; 会话切片反向声明 |
| 收尾(测试/索引/基线) | Done | 基线切片 `26-10-15-0540-backend-store-recover-lock-dedup`; kb.index / kb.check |

## 进度日志

### 2026-10-15 — 单会话收口(R12)

- **开工同步**: `commands run my-commit-flow.sync` → 已同步 `5f5689c5`。
- **复验**: 锚点均在(hr/store.py 裸 FileLock; `_recover` 与 `load()` 损坏分支同族); 置 `In Progress` + `kb.index`。
- **改道记录(首跑双红 → 回调式改道)**: 首版 infra 内置按 path 挪文件, 绕过 hr 例行的 `store.quarantine` seam(`test_repeated_read_failure_does_not_rewarn` / `test_store_recover_unmovable_keeps_backup` 双红) → 处置改回调注入, 单点只留编排纪律。教训: 单点化时所有「调用方可能打桩的既有方法」都是 seam, 要么保留在调用链上, 要么显式接受并同步改测试。
- **改动**: 如子任务表; 全部过 `dev.fmt`(yapf 顺带规范化 locking.py 两处既有未格式化行, fmt 闸门对 `src/` 生效, 保留其结果)。
- **行为等价审计**: `read_error` 四段消息逐字重组(坏文件已挪走 / 未能挪走 / 已从备份恢复 / 备份不可用); state 的 WARNING/INFO/ERROR 三条日志与自愈写回路径不变; hr 锁的 acquire / Timeout→HrLockBusy / release 纪律不变(唯一微差: 释放失败 debug 文案「释放站点锁失败: {path}」→「释放站点锁 {path} 失败: ...」, 无守阵钉该文案)。
- **验证**: 定向 6 文件全绿(hr_store / locking / rule_engine / hr_status / hr_service / store_recovery); test.full 全绿, 数字唯一权威在基线切片(见 **Refs:**), 此处不手抄。
- **零改动确认**: 未触碰 `config.yml` / `auto-qb-data/`; webui/torrents 零改动; 既有测试文件零修改(仅新增 `tests/test_store_recovery.py`)。

- 2026-10-21 02:26 认领并修复 issue 26-10-20-2231(test-fe-tpl-shell-parity-guard): tests/test_webui_static_skins.py 新增 test_frontend_shell_sprite_login_parity —— 三份 shell sprite 段逐字相等 + #app+login 段注释归一后相等, 零源码改动; 红验三类突变(sprite 漂移红/login 标记漂移红/login 仅注释漂移绿)后精确还原, 三份 shell git diff 零改动; issue 置 Done, test.full 3966 passed + 10 skipped / TOTAL 99%(数字见基线切片 26-10-21-0225-dup-code-audit)
