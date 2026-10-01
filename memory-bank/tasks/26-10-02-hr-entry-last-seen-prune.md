# 26-10-02-hr-entry-last-seen-prune — HrEntry.last_seen 写入点与 INDEX_RETENTION 清理复活

**Status:** Done
**Added:** 2026-10-02
**Updated:** 2026-10-02
**Summary:** 清偿 issue 26-10-01-2335(W1 波阶段 2/3): `_merge_seen` 合并时刷新 `last_seen`(与 `first_seen` 同口对称, 时钟统一走 `now_fn`), 两处逐字重复的 `_prune_index` 合并为模块级单点, INDEX_RETENTION 过期清理分支复活; test.full 2219 passed + 3 skipped / 97.53%(基线 26-10-02-0412)。

**Refs:** memory-bank/issues/26-10-01-2335-bug-hr-entry-last-seen-dead-prune.html

**Topics:** hr-entry-last-seen-prune

## 原始请求

用户授权 W1 波(后端速赢)路线图实施, 本条为其阶段 2/3: 认领 issue [26-10-01-2335](../issues/26-10-01-2335-bug-hr-entry-last-seen-dead-prune.html), 单独提交推送。认领指令明确要求先定 `last_seen` 的正确写入时机(轻设计, 决策写进本档案)再让清理分支复活, 不发明大特性。

## 思考过程与决策

- **决策 1 —— last_seen 写入时机: `_merge_seen` 合并进索引的时刻**(service.py, 波内增量与波后收尾两个调用点共用该口)。
  - 语义: 「最近一次在站点清单里见到该条目」= 本波已见行合并进索引的时刻。`wave.seen` 里的行全部来自本波实际解析到的清单页, 合并时刻即见到时刻(页取数与合并间隔秒级, 不影响以天计的保留窗口)。
  - 与 INDEX_RETENTION 口径精确对齐: 过期 = 距 last_seen 超过 30 天。条目退役的三条路径(终态冻结 `_freeze_terminal` / 观察期出口 `_advance_observation` / 换 tid 接管 `_record_hit`)全部只作用于**不在本波 wave.seen 里**的条目 —— 退役后不再进入合并口, last_seen 自然冻结在最后一次见到的时刻, 正是保留窗口的计时起点。
  - 与 `first_seen` 写法对称(issue §6 建议方向), 不新增管道、不新增配置键 —— 复核确认 `INDEX_RETENTION` 是 `hr/service.py` 模块常量(30 天, `INDEX_RETENTION = 30 * 86400.0`), **不是**配置键, 无 config.validate_config / schema.py 改动面。
  - 时钟一致性: 写入值取调用方传入的 `now`(源自 `now_fn`, 生产 = `time.time`), 不在函数内直调 `time.time()` —— 假时钟测试才可断言保留窗口; `first_seen` 的兜底分支同函数内一并改用 `now`(生产行为不变, 测试确定性提升)。
- **决策 2 —— 两处逐字重复的 `_prune_index` 合并为单点**(issue §6 留给认领人定): 删除类内 `@staticmethod` 版(service.py:1108, 生产零调用, 仅一个测试引用), 保留模块级函数版(service.py:1409, 唯一生产调用点 service.py:1036), 测试改为只守模块级单点。理由: 复活的逻辑只留一份, 消除漂移面; 「方法版与模块版同口径」的守阵在合并后失去存在意义。
- **决策 3 —— 恒 0 存量条目的口径(保守)**: 清理条件保持 `not entry.active and entry.last_seen and ...` 原样。修复前入库存量的非活跃条目 last_seen=0.0(falsy)永不淘汰 —— 有界存量集、判定无害(非活跃条目不进反查表, 放行凭 data.verified 永续记录), 不加 first_seen 兜底(last_seen ≥ first_seen, 兜底会提前淘汰, 属发明新语义); 存量条目若被站点重新列出会经合并口重获 last_seen, 之后再退役即可正常淘汰。
- **耦合面核对**(任务档案 26-10-01-webui-hr-detail-table): 详情表导出契约 `EntryDetail.last_seen`/`status.py` 视图复制点是纯读透传, 字段面不变; 前端 `hr_status.js` 已按「0=未知不缀显示」实现, 修复后真实值直接点亮「最近被见到」, 契约守阵不受影响。前端注释里「last_seen 上游恒 0(issue 26-10-01-2335)」一句随修复过期, 同步改为「0=未知(存量条目)不缀」口径。

## 实现计划

1. `hr/service.py`: `_merge_seen(data, wave, now)` 增参刷新 last_seen; 两处调用点传 `self._now()`; 删除类内 `_prune_index` 静态方法。
2. `hr/model.py`: `last_seen` 字段补语义注释(写点单点 + 存量 0 语义)。
3. `webui/static/shared/hr_status.js`: 更新过期注释。
4. `tests/test_hr_service.py`: 新增两例(合并刷新 last_seen / 保留窗口全链: 见到→退役→超期清理→活跃存活→放行记录留存), 同步头部「测试计划」清单; 既有 prune 单元用例收敛到模块级单点。
5. 收尾: issue 状态 Done + 状态日志 / kb.index / activeContext 切片 / test.full 基线切片 / 提交。

## 子任务状态表

| 段 | 内容 | 状态 |
|----|------|------|
| 认领建档 | 本档案 + issue doc-refs 双向登记 | 完成(26-10-02) |
| 实施 | last_seen 写点 + _prune_index 合并单点 + 注释面 | 完成(26-10-02) |
| 测试 | 新增 2 例 + 既有用例收敛 + test.quick 迭代 | 完成(26-10-02) |
| 收尾 | issue Done / kb.index / 切片 / test.full 基线 | 完成(26-10-02) |
| 提交 | ship.commit 单独一笔 | 完成(26-10-02) |

## 进度日志

- **2026-10-02 开工**: sync PASS @ bc24631b; 摸排完成(HrEntry 读写面 / 两处清理分支 / INDEX_RETENTION 常量定位 / 详情表契约面 / 退役三路径核对); 三个决策落档(见「思考过程与决策」)。
- **2026-10-02 实施完成**: ①`_merge_seen(data, wave, now)` 增参刷新 last_seen, 两处调用点传 `self._now()`(波内增量 / 波后收尾); ②类内 `_prune_index` 静态方法删除, 模块级单点保留; ③model.py last_seen 字段注释 + js 过期注释更新。首轮 test.quick 抓出两处: 新测例回执断言行集算错(entries==2 应为 1, 本轮自改)+ memory-bank 三守阵红(新档案未登记), `kb.index` 重建后全绿(2219+3)。
- **2026-10-02 收尾**: issue 26-10-01-2335 翻 Done(封面徽标 / meta / 复验 / 修复后补充 / 状态日志五处); test.full **2219 passed + 3 skipped / 97.53%**(13,272 语句 / 298 未覆盖 / 4,438 分支 / 86 partial, 29.1s), 基线切片 26-10-02-0412; 已知 flaky(test_budget_unit_wait_and_caps)本轮未触发; 无新坑入池(无计划外改动)。
