# 分类: src/auto_qb/rules/actions/full_checking.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__actions__full_checking.py.txt`
- 机器实测: 40 条全部真存活(池抓不住)
- 计数: 40 条 = 真洞 4 / 等价 36 / 假存活 0

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `xǁFullCheckingMixinǁ_execute_full_checking__mutmut_10` | _execute_full_checking | 删 `source="rule"` 实参 | 等价 | ops.recheck 的 `source` 形参默认值即 `"rule"`(ops_mod.py:183) ⇒ 逐字同义, 冷却/保护策略分支不变 |
| 2 | `xǁFullCheckingMixinǁ_execute_full_checking__mutmut_22` | _execute_full_checking | `getattr(ctx, "task", None)` → `getattr(ctx, "task", )` | 等价 | `task` 是 RuleContext 的 dataclass 字段(base.py:106, 默认 None)⇒ 属性恒存在, 两参 getattr 不会抛, 取到的值与三参式相同 |
| 3 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_20` | _wait_for_group_checking | `getattr(ctx, "task", None)` → `getattr(ctx, "task", )` | 等价 | 同 #2(dataclass 字段恒存在) |
| 4 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_24` | _wait_for_group_checking | 无任务驱动 `skip(文案)` → `skip(None)` | 等价 | 仍 skip, `origin is None` 判定与不建等待任务的行为不变, 仅文案空 |
| 5 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_25` | _wait_for_group_checking | 同 #4 文案包 `XX…XX` | 等价 | 纯文案 |
| 6 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_27` | _wait_for_group_checking | `rule_name = ctx.rule_name` → `None` | 等价 | rule_name 只进 4 条 logger 前缀, 不参与任何分支/入队/判定 |
| 7 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_32` | _wait_for_group_checking | 自身已删 `logger.warning(f"…")` → `warning(None)` | 等价 | 仅日志; `tq.add_task(origin)` + FINISHED 的语义未变 |
| 8 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_33` | _wait_for_group_checking | 同上日志 `hash[:8]` → `[:9]` | 等价 | 仅日志截断长度 |
| 9 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_34` | _wait_for_group_checking | 自身已删分支 `tq.add_task(origin)` → `add_task(None)` | 等价 | None.resume_index 抛 AttributeError, 但该行在 wait_poll 的 `try` 内, 被 `except Exception` 捕获 → `revive()`(即 add_task(origin)) → FINISHED; 终态与原路径逐位一致, 只多一条 error 日志 |
| 10 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_36` | _wait_for_group_checking | `> GROUP_CHECK_WAIT_LIMIT` → `>=` | 等价 | 连续浮点计时差恰等于 7200.0 的概率为 0 ⇒ 离散边界不可达(等价类: 计时上限 `>`/`>=`) |
| 11 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_37` | _wait_for_group_checking | 等待超时 `logger.warning(f"…")` → `warning(None)` | 等价 | 仅日志; 超时仍 revive()+FINISHED |
| 12 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_38` | _wait_for_group_checking | 同上日志 `hash[:8]` → `[:9]` | 等价 | 仅日志截断长度 |
| 13 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_39` | _wait_for_group_checking | 组内已清 `logger.debug(f"…")` → `debug(None)` | 等价 | 仅日志 |
| 14 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_40` | _wait_for_group_checking | 同上日志 `hash[:8]` → `[:9]` | 等价 | 仅日志截断长度 |
| 15 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_41` | _wait_for_group_checking | 异常 `logger.error(f"…")` → `error(None)` | 等价 | 仅日志; 异常仍 revive()+FINISHED |
| 16 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_42` | _wait_for_group_checking | 同上日志 `hash[:8]` → `[:9]` | 等价 | 仅日志截断长度 |
| 17 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_44` | _wait_for_group_checking | Task `kind="check-wait"` → `None` | 等价 | kind 的唯一分支判定是 `task.kind == "check"`(add_task 在途登记, taskqueue.py:144): None 同样不登记 ⇒ 不占用 `_active_checks` 的语义保持; 其余只进 uid/log_tag |
| 18 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_45` | _wait_for_group_checking | Task `name="check-group-wait"` → `None` | 等价 | name 只进 uid/log_tag; 该任务无 has_task(kind,name,hash) 幂等查询 |
| 19 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_46` | _wait_for_group_checking | Task `hash=hash` → `None` | 等价 | handler(wait_poll)用闭包 hash, 不读 task.hash; task.hash 只进 log_tag/uid/has_task, 本任务无后者 |
| 20 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_47` | _wait_for_group_checking | Task `store=manager.store` → `None` | 等价 | `_store` 唯一读点是 `Task.torrent` 属性(taskqueue.py:102), wait_poll 不读 ⇒ 无读点字段 |
| 21 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_52` | _wait_for_group_checking | 删 `hash=hash` 实参(缺省 `""`) | 等价 | 同 #19, 空 hash 与 None 同为 falsy, 无读点差异 |
| 22 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_53` | _wait_for_group_checking | 删 `store=manager.store` 实参 | 等价 | 同 #20(缺省 None, 无读点) |
| 23 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_54` | _wait_for_group_checking | 删 `interval=CHECK_RESULT_INTERVAL`(缺省 0→归一 1s) | 等价 | 只改轮询节拍(2s→1s); wait_poll 判定只用 `time.time()-start` 与 `others_checking()`, 更密的轮询不改变任何终局分支 |
| 24 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_56` | _wait_for_group_checking | kind → `"XXcheck-waitXX"` | 等价 | 同 #17: 只要不等于 `"check"` 即不登记在途; 仅 uid/log_tag 变 |
| 25 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_57` | _wait_for_group_checking | kind → `"CHECK-WAIT"` | 等价 | 同 #17(大小写不影响 `== "check"` 判定) |
| 26 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_58` | _wait_for_group_checking | name → `"XXcheck-group-waitXX"` | 等价 | 同 #18, 仅日志标识 |
| 27 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_61` | _wait_for_group_checking | 推迟等待 `logger.debug(f"…")` → `debug(None)` | 等价 | 仅日志; 仍返回 `pending("等待同组种子校验完成")` |
| 28 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_62` | _wait_for_group_checking | `pending(文案)` → `pending(None)` | 等价 | 仍 pending(规则断点/本轮不重入队), 等待任务已入队, 仅断点理由文案空 |
| 29 | `xǁFullCheckingMixinǁ_wait_for_group_checking__mutmut_63` | _wait_for_group_checking | `pending(文案)` 包 `XX…XX` | 等价 | 同 #28, 纯文案 |
| 30 | `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_14` | _skip_on_group_check_failed | 守卫 `h == hash or count <= 0` → `and` | 真洞 | 自身(h==hash)不再被跳过: 一旦自身当日失败计数>0, 循环里 `rec=自己`、`sizes.get(自身)==mine` 恒真 ⇒ 种子把自己判成"同组种子校验失败"直接 skip, 失败一次即永久拒检(且当日计数再无从清零)。**建议守阵**: 自身 recheck_fails>0 时 `_skip_on_group_check_failed` 必须返回 None |
| 31 | `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_20` | _skip_on_group_check_failed | `count <= 0` → `count < 0` | 真洞 | 计数恒 ≥0 ⇒ 条件恒假: **无失败记录**的兄弟成员也过闸, 同 size 即被推断为"校验失败" ⇒ 本种子假跳过校验(失败推断闸门从"有证据"退化为"同组即跳过"), 校验层整体被旁路。**建议守阵**: 兄弟 count==0 时返回 None(不 skip) |
| 32 | `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_22` | _skip_on_group_check_failed | 守卫分支 `continue` → `break` | 真洞 | members 首位常是自身(group_members 含 hash 自身)⇒ 首轮即 break, 循环体永不执行: 决策链 1.6 失败推断整体失效, 已判败的同组种子不再拦截, 重复全量校验(且 #146 的假失败自愈也不再发生)。**建议守阵**: 兄弟当日失败且 size 一致时返回 skipped |
| 33 | `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_31` | _skip_on_group_check_failed | `pop(h, None)` → `pop(h)` | 等价 | 能过 `count>0` 守卫的 h 必在今日 recheck_fails 中(recheck_fail_count 只对今日记录返非 0, 且 `manager.state` 就是 `ctx.state.data`, qbmanager.py:324 同一 dict)⇒ 缺省值不可达, 不会 KeyError |
| 34 | `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_33` | _skip_on_group_check_failed | `.get("recheck_fails", {})` → `.get(…, None)` | 等价 | 同 #33: count>0 ⇒ `recheck_fails` 键必然存在, None 兜底不可达 |
| 35 | `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_35` | _skip_on_group_check_failed | `.get("recheck_fails", )` | 等价 | 同 #33/#34, 缺省 None 不可达 |
| 36 | `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_38` | _skip_on_group_check_failed | 自愈分支 `continue` → `break` | 真洞 | 假失败自愈清掉一条陈旧记录(成员已完成/已删除)后即中断遍历 ⇒ 其后**真失败**成员漏判, 本种子照常 recheck: 重复校验 + 2026-09-25 那类"陈旧记录毒化"只解一半。**建议守阵**: members=[陈旧记录成员, 真失败同 size 成员] 时仍返回 skipped |
| 37 | `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_41` | _skip_on_group_check_failed | 推断命中 `logger.info(f"…")` → `info(None)` | 等价 | 仅日志(该条 INFO 是排障可见性, 但返回的 skip 与文案未变) |
| 38 | `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_42` | _skip_on_group_check_failed | 同上日志 `h[:8]` → `h[:9]` | 等价 | 仅日志截断长度 |
| 39 | `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_43` | _skip_on_group_check_failed | 推断命中 `skip(f"…{h[:8]}…")` → `skip(None)` | 等价 | 仍 skipped(拒检结论与分支不变), 仅丢推断理由文案 |
| 40 | `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_44` | _skip_on_group_check_failed | skip 文案 `h[:8]` → `h[:9]` | 等价 | 仅文案截断长度 |

## 真洞归并(1 个根因, 4 条)

全部落在决策链 1.6 失败推断闸门(`_skip_on_group_check_failed`), 同一处循环/守卫的四种错法:
- #30 `or`→`and`: 自身参与推断 ⇒ 失败一次后永久拒检。
- #31 `<=0`→`<0`: 零失败成员被当成失败 ⇒ 假推断旁路校验层。
- #32 守卫 `continue`→`break`: 闸门整体失效(重复校验)。
- #36 自愈分支 `continue`→`break`: 自愈后漏判后续真失败(重复校验 + 记录残留)。
