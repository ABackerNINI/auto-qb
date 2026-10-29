# 分类: src/auto_qb/rules/base.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__base.py.txt`
- 机器实测: 89 条全部真存活(16 文件池全绿)
- 计数: 89 条 = 真洞 36 / 等价 53 / 假存活 0

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `xǁActionResultǁ__init____mutmut_1` | ActionResult.__init__ | `status` 默认 `"success"`→`"XXsuccessXX"` | 等价 | 全仓无 `ActionResult()` 无参构造(只有 ok/fail/skip/pending 四个类方法且显式传 status), 默认值不可达 |
| 2 | `xǁActionResultǁ__init____mutmut_2` | ActionResult.__init__ | `status` 默认 `"SUCCESS"` | 等价 | 同上: 默认值无调用点 |
| 3 | `xǁActionResultǁ__init____mutmut_3` | ActionResult.__init__ | `message` 默认 `""`→`"XXXX"` | 等价 | 默认值不可达; 且 message 只进日志/ops job 展示文案, 无控制流 |
| 4 | `xǁActionResultǁok__mutmut_1` | ActionResult.ok | `message` 默认 `""`→`"XXXX"` | 等价 | 文案: message 读点仅 base.py:243-260 日志与 ops_mod.py:956 UI 载荷 |
| 5 | `xǁActionResultǁfail__mutmut_1` | ActionResult.fail | `message` 默认 `"XXXX"` | 等价 | 同上, 仅文案 |
| 6 | `xǁActionResultǁskip__mutmut_1` | ActionResult.skip | `message` 默认 `"XXXX"` | 等价 | 同上, 仅文案 |
| 7 | `xǁActionResultǁpending__mutmut_1` | ActionResult.pending | `message` 默认 `"XXXX"` | 等价 | 同上, 仅文案 |
| 8 | `xǁActionResultǁpending__mutmut_3` | ActionResult.pending | `return cls("pending", None)` | 等价 | message 变 None, 唯一读点是日志 f-string 与 UI 文案 ⇒ 文案差异 |
| 9 | `xǁActionResultǁpending__mutmut_5` | ActionResult.pending | `return cls("pending")` | 等价 | 丢掉调用方 message, 同上仅文案; 状态位仍为 pending |
| 10 | `xǁBaseActionǁ__init____mutmut_2` | BaseAction.__init__ | `self.spec = None` | 等价 | 无读点字段: 全仓 `self.spec` 只有 base.py:75/88/137 三处赋值, 无任何读取点 |
| 11 | `xǁRuleǁ__init____mutmut_2` | Rule.__init__ | `self.spec = None` | 等价 | 同上, `.spec` 无读点 |
| 12 | `xǁRuleǁ__init____mutmut_6` | Rule.__init__ | `spec.get(None, True)` 取 enabled | 真洞 | 键名变 None ⇒ 恒返回默认 True, 配置 `enabled: false` 的规则仍被启用并执行动作(禁用开关整体失效), rules_mod 的 enabled_rules 直接吃这个字段; 池内用例均不传 enabled。**建议守阵**: 断言 `Rule("g.x", {"enabled": False, "actions": []}, mgr).enabled is False` |
| 13 | `xǁRuleǁ__init____mutmut_10` | Rule.__init__ | `spec.get("XXenabledXX", True)` | 真洞 | 同 mutmut_6: 键名错位 ⇒ enabled 恒 True, 禁用规则照跑。**建议守阵**: 同上的 enabled=False 用例 |
| 14 | `xǁRuleǁ__init____mutmut_11` | Rule.__init__ | `spec.get("ENABLED", True)` | 真洞 | 同 mutmut_6/10, 大小写错位 ⇒ 禁用开关失效。**建议守阵**: 同上 |
| 15 | `xǁRuleǁ__init____mutmut_30` | Rule.__init__ | watch_fields 过滤条件 `str(f).strip()`→`str(None).strip()` | 等价 | `"None"` 恒真 ⇒ 只保留空白项; 而 config 校验 `_validate_watch_fields` 要求非空且取值限 tags/category, 空白项不可达; 且 "" 与任何真实字段名无交集(rules_mod:372 取交集) |
| 16 | `xǁRuleǁ__init____mutmut_41` | Rule.__init__ | interval 默认 `"0S"`→`"0s"` | 等价 | `_parse_quantity` 先 `str(raw).strip().upper()` 再匹配 ⇒ 大小写不可区分 |
| 17 | `xǁRuleǁ__init____mutmut_62` | Rule.__init__ | cooldown 默认 `"0S"`→`"0s"` | 等价 | 同 mutmut_41 |
| 18 | `xǁRuleǁ__init____mutmut_73` | Rule.__init__ | `_cond_err_key` 初值 `None`→`""` | 等价 | 该字段只作节流哨兵比较; key 形如 `"Type:msg"` 恒不等于 `""`, 与不等于 None 同效 |
| 19 | `xǁRuleǁ__init____mutmut_74` | Rule.__init__ | `_cond_err_ts` 初值 `0.0`→`None` | 等价 | 首报时 `key != self._cond_err_key` 恒真, `or` 短路使 `now - None` 不可达; 后续该字段已被写成 float |
| 20 | `xǁRuleǁ__init____mutmut_75` | Rule.__init__ | `_cond_err_ts` 初值 `0.0`→`1.0` | 等价 | 与 0.0 只差 epoch 后 1 秒, 在 300s 阈值下不可区分 |
| 21 | `xǁRuleǁ__init____mutmut_87` | Rule.__init__ | `ignore_next = None`(初值) | 等价 | None 与 False 同真值; create_action 第三参只在 base.py:257 `if not action.ignore_error` 按真值用 |
| 22 | `xǁRuleǁ__init____mutmut_88` | Rule.__init__ | `ignore_next = True`(初值) | 真洞 | 首条动作恒带 ignore_error=True ⇒ 规则第一个动作失败不再中断链, 后续动作照跑(错误隔离语义反向泄漏); 现测 test_rule_action_chain_ignore_continue 直接赋 rule.actions 绕过 __init__。**建议守阵**: 用 spec 构造 `[{"move_to": {"path": ""}}, {"add_tags": ["AFTER"]}]`, 断言 AFTER 未执行 |
| 23 | `xǁRuleǁ__init____mutmut_98` | Rule.__init__ | 标记分支 `ignore_next = None` | 真洞 | `ignore_next_action_error` 置位被吞 ⇒ 被标记的动作失败即断链, 配置项整体失效; 现测 test_rule_ignore_next_action_error 用 skip(非 fail)验证, 掩盖了失败分支。**建议守阵**: 标记后接必失败动作, 断言后续动作仍执行 |
| 24 | `xǁRuleǁ__init____mutmut_109` | Rule.__init__ | `create_action(name, value, None)` | 真洞 | 第三参恒 None ⇒ 所有动作 ignore_error 恒假, `ignore_next_action_error` 失效(同 mutmut_98)。**建议守阵**: 构造后断言 `rule.actions[1].ignore_error is True` |
| 25 | `xǁRuleǁ__init____mutmut_112` | Rule.__init__ | `create_action(name, value)` | 真洞 | 第三参缺省 False ⇒ 同上, 标志失效。**建议守阵**: 同上 |
| 26 | `xǁRuleǁ__init____mutmut_114` | Rule.__init__ | 消费后 `ignore_next = None` | 等价 | None 与 False 同真值, 下一条动作仍为不忽略 |
| 27 | `xǁRuleǁ__init____mutmut_115` | Rule.__init__ | 消费后 `ignore_next = True` | 真洞 | 标志不消费 ⇒ 一旦出现 ignore_next_action_error, 其后**所有**动作都忽略错误, 链永不中断(错误被成片吞掉)。**建议守阵**: 标记→动作A→动作B 两连失败, 断言 B 之后仍按不忽略中断 |
| 28 | `xǁRuleǁ__init____mutmut_126` | Rule.__init__ | reannounce 告警条件 `cooldown <= 0`→`<= 1` | 等价 | 只决定一条 ERROR 告警是否打印, 无控制流(仅日志) |
| 29 | `xǁRuleǁprocess__mutmut_2` | Rule.process | `ctx.torrent is None` → `(True, False)` | 等价 | 返回值 (handled, stop) 在产线无读点: 三个调用点(rules_mod:275/398/412)经 _run_rule 全部丢弃元组; 且早退位置一致, 动作执行与断点均不受影响 |
| 30 | `xǁRuleǁprocess__mutmut_3` | Rule.process | 同上 → `(False, True)` | 等价 | 同 mutmut_2: 仅 stop 值变, 无产线读点 |
| 31 | `xǁRuleǁprocess__mutmut_4` | Rule.process | `ctx.rule_name = None` | 等价 | rule_name 读点仅日志(full_checking.py:91-150、basic.py:182), 无状态键/无控制流 |
| 32 | `xǁRuleǁprocess__mutmut_15` | Rule.process | `_log_condition_error(ctx, None)` | 等价 | 仅日志文案与节流键退化(所有异常共用 "NoneType:None"); stop=True 分支不变 |
| 33 | `xǁRuleǁprocess__mutmut_28` | Rule.process | 去重拦截 → `(False, True)` | 等价 | 两版都在此早退、都不执行动作, 仅 stop 值不同 ⇒ 产线无读点(同 mutmut_2) |
| 34 | `xǁRuleǁprocess__mutmut_29` | Rule.process | `log_repr = None` | 等价 | 只进日志 f-string(仅日志) |
| 35 | `xǁRuleǁprocess__mutmut_32` | Rule.process | `start = 0 if (fresh) or True else resume_index` | 真洞 | 断点续跑失效: 续跑轮从 0 开始重放, 已成功的动作被**重复执行**(如重复 add_tags/reannounce/转移), 且 task.resume_index 会被清 ⇒ 断点契约(读/写/清)全断; 池内无 pending 续跑用例。**建议守阵**: 手工置 `task.resume_index = 1` 后 process, 断言 actions[0] 未再执行 |
| 36 | `xǁRuleǁprocess__mutmut_36` | Rule.process | `executed = None`(初值) | 等价 | 唯一读点 `return executed or ok_action` 按真值, None 与 False 同效 |
| 37 | `xǁRuleǁprocess__mutmut_38` | Rule.process | `failed = None`(初值) | 等价 | failed 只作真值传给 _should_stop / stop_if 判定, None 与 False 同效 |
| 38 | `xǁRuleǁprocess__mutmut_40` | Rule.process | `result = ""`(初值) | 等价 | 循环内每次迭代必先赋值再读 `result.is_pending`; actions 为空时该值不被读 |
| 39 | `xǁRuleǁprocess__mutmut_47` | Rule.process | 异常分支 `ActionResult.fail(None)` | 等价 | 仅异常文案(日志)丢失, 状态仍 failed ⇒ 断链逻辑不变 |
| 40 | `xǁRuleǁprocess__mutmut_52` | Rule.process | pending+task 分支 `logger.debug(None)` | 等价 | 仅日志 |
| 41 | `xǁRuleǁprocess__mutmut_53` | Rule.process | pending+task → `(False, True)` | 等价 | handled 值产线无读点(同 mutmut_2), 早退位置/断点写入一致 |
| 42 | `xǁRuleǁprocess__mutmut_54` | Rule.process | pending+task → `(True, False)` | 等价 | 仅 stop 值变, 产线无读点 |
| 43 | `xǁRuleǁprocess__mutmut_57` | Rule.process | 无 task 的 pending 分支 `executed = None` | 等价 | 该分支 ok_action 已置 True, `executed or ok_action` 结果不变 |
| 44 | `xǁRuleǁprocess__mutmut_58` | Rule.process | 无 task 的 pending 分支 `executed = False` | 等价 | 同 mutmut_57: executed 本就是初值 False, 终值由 ok_action 兜住 |
| 45 | `xǁRuleǁprocess__mutmut_59` | Rule.process | 同上分支 `logger.info(None)` | 等价 | 仅日志 |
| 46 | `xǁRuleǁprocess__mutmut_60` | Rule.process | 同上分支 `continue`→`break` | 等价 | 该分支要求 `ctx.task is None`, 而产线三个入口(rules_mod:275/398/412)恒传 task ⇒ 不可达防御分支 |
| 47 | `xǁRuleǁprocess__mutmut_63` | Rule.process | is_ok 分支 `executed = None` | 等价 | 同分支同时置 ok_action=True, 终值不变 |
| 48 | `xǁRuleǁprocess__mutmut_64` | Rule.process | is_ok 分支 `executed = False` | 等价 | 同上, ok_action 兜住终值 |
| 49 | `xǁRuleǁprocess__mutmut_65` | Rule.process | is_ok 分支 `logger.info(None)` | 等价 | 仅日志 |
| 50 | `xǁRuleǁprocess__mutmut_73` | Rule.process | is_skipped 分支 `logger.debug(None)` | 等价 | 仅日志 |
| 51 | `xǁRuleǁ_log_condition_error__mutmut_2` | Rule._log_condition_error | `key = None` | 等价 | 节流键恒等 ⇒ 不同错误原因在 5 分钟内合并节流, 只影响日志条数(仅日志) |
| 52 | `xǁRuleǁ_log_condition_error__mutmut_3` | Rule._log_condition_error | `key = f"{type(None).__name__}:{e}"` | 等价 | 异常类名从键里消失, 同文案不同异常合并节流 ⇒ 仅日志 |
| 53 | `xǁRuleǁ_log_condition_error__mutmut_4` | Rule._log_condition_error | 节流条件 `or`→`and` | 等价 | 换原因不再立即报(要同时超时), 仍只影响日志节流(仅日志) |
| 54 | `xǁRuleǁ_log_condition_error__mutmut_7` | Rule._log_condition_error | 节流边界 `>`→`>=` | 等价 | 300.0s 浮点等值边界, 离散不可观测 |
| 55 | `xǁRuleǁ_dedup_allowed__mutmut_2` | Rule._dedup_allowed | `execute_once != "never"` | 真洞 | 语义反转: once/daily/hourly 规则在 cooldown<=0 时直接放行 ⇒ execute_once 去重整体失效, 同一 seed 反复执行动作; 现测去重用例都用幂等 add_tags(重复执行被动作自己 skip, handled 仍 False)掩盖。**建议守阵**: 用非幂等动作(或直测 `_dedup_allowed`)断言第二次为 False |
| 56 | `xǁRuleǁ_dedup_allowed__mutmut_3` | Rule._dedup_allowed | `execute_once == "XXneverXX"` | 等价 | never 规则只是不走快路: 慢路径在 cooldown<=0 时对 once/daily/hourly 三判据均不成立, 仍 return True |
| 57 | `xǁRuleǁ_dedup_allowed__mutmut_4` | Rule._dedup_allowed | `execute_once == "NEVER"` | 等价 | 同 mutmut_3 |
| 58 | `xǁRuleǁ_dedup_allowed__mutmut_5` | Rule._dedup_allowed | `cooldown <= 0`→`< 0` | 等价 | cooldown 为 0 时慢路径同样 return True(三判据皆不成立), 与快路等价 |
| 59 | `xǁRuleǁ_dedup_allowed__mutmut_6` | Rule._dedup_allowed | `cooldown <= 0`→`<= 1` | 真洞 | 0<cooldown<=1 的 never 规则(cooldown 支持小数, 校验走 parse_time)冷却被整段跳过 ⇒ 亚秒冷却重复执行; 池内冷却值均 ≥1H。**建议守阵**: `cooldown: "0.5S"` 连跑两次, 断言第二次不执行 |
| 60 | `xǁRuleǁ_dedup_allowed__mutmut_15` | Rule._dedup_allowed | 冷却判定 `and`→`or` | 真洞 | 有执行记录且 cooldown>0 时恒 return False ⇒ 该规则对该 seed **永不执行**(冷却永不到期), 自动化静默停摆; 现测只断言冷却期内不执行, 掩盖了冷却后应放行。**建议守阵**: 断言记录 ts 早于 cooldown 窗口时 `_dedup_allowed` 为 True |
| 61 | `xǁRuleǁ_dedup_allowed__mutmut_16` | Rule._dedup_allowed | 冷却判定 `cooldown > 0`→`>= 0` | 等价 | 多出的 cooldown==0 分支需 `elapsed < 0`(ts 在未来)才拦, 正常时钟不可达 |
| 62 | `xǁRuleǁ_dedup_allowed__mutmut_17` | Rule._dedup_allowed | 冷却判定 `cooldown > 0`→`> 1` | 真洞 | 0<cooldown<=1 时冷却闸门被跳过 ⇒ 亚秒冷却重复执行(同 mutmut_6 的另一半)。**建议守阵**: `cooldown: "0.5S"` 连跑两次, 断言第二次不执行 |
| 63 | `xǁRuleǁ_dedup_allowed__mutmut_20` | Rule._dedup_allowed | `rec.get("ts", None)` | 等价 | record_execution(state.py:262)恒写 ts, 缺键形状不可由本仓产生 ⇒ 默认值无读点 |
| 64 | `xǁRuleǁ_dedup_allowed__mutmut_22` | Rule._dedup_allowed | `rec.get("ts", )` | 等价 | 同 mutmut_20 |
| 65 | `xǁRuleǁ_dedup_allowed__mutmut_25` | Rule._dedup_allowed | `rec.get("ts", 1)` | 等价 | 同 mutmut_20: 默认值不可达 |
| 66 | `xǁRuleǁ_dedup_allowed__mutmut_26` | Rule._dedup_allowed | 冷却窗口 `<`→`<=` | 等价 | 浮点时间等值边界, 离散不可观测 |
| 67 | `xǁRuleǁ_dedup_allowed__mutmut_29` | Rule._dedup_allowed | `execute_once == "XXonceXX"` | 真洞 | once 去重判据永不成立 ⇒ once 规则反复执行(实测复现: 变异后 `_dedup_allowed` 返回 True, 只因 add_tags 幂等才没被池抓住)。**建议守阵**: once 记录存在时断言 `_dedup_allowed` 为 False |
| 68 | `xǁRuleǁ_dedup_allowed__mutmut_30` | Rule._dedup_allowed | `execute_once == "ONCE"` | 真洞 | 同 mutmut_29, 大小写错位 ⇒ once 去重失效。**建议守阵**: 同上 |
| 69 | `xǁRuleǁ_dedup_allowed__mutmut_31` | Rule._dedup_allowed | once 分支 `return False`→`True` | 真洞 | once 规则永不去重 ⇒ 每次 tick 都执行动作(高频写 qB)。**建议守阵**: 同上 |
| 70 | `xǁRuleǁ_dedup_allowed__mutmut_32` | Rule._dedup_allowed | daily 判据 `and`→`or` | 真洞 | 记录 date 为今天时任何 execute_once 取值都 return False ⇒ 全规则当天只跑一次(daily 之外的类型被误拦), 自动化大面积停摆。**建议守阵**: once 规则记录 date=今天时断言仍允许执行 |
| 71 | `xǁRuleǁ_dedup_allowed__mutmut_33` | Rule._dedup_allowed | daily 判据 `==`→`!=` | 真洞 | daily 去重反转: 当天已跑过反而放行(重复执行), 昨天跑过的当天被拦(漏执行)。**建议守阵**: daily 当天记录 → False; 昨日记录 → True |
| 72 | `xǁRuleǁ_dedup_allowed__mutmut_34` | Rule._dedup_allowed | `execute_once == "XXdailyXX"` | 真洞 | daily 去重失效, 每次 tick 重复执行。**建议守阵**: daily 当天记录 → `_dedup_allowed` False |
| 73 | `xǁRuleǁ_dedup_allowed__mutmut_35` | Rule._dedup_allowed | `execute_once == "DAILY"` | 真洞 | 同 mutmut_34。**建议守阵**: 同上 |
| 74 | `xǁRuleǁ_dedup_allowed__mutmut_36` | Rule._dedup_allowed | daily 分支 `rec.get(None)` | 真洞 | 取不到 date ⇒ 判据恒假 ⇒ daily 去重失效。**建议守阵**: 同上 |
| 75 | `xǁRuleǁ_dedup_allowed__mutmut_37` | Rule._dedup_allowed | `rec.get("XXdateXX")` | 真洞 | 键名错位 ⇒ daily 去重失效。**建议守阵**: 同上 |
| 76 | `xǁRuleǁ_dedup_allowed__mutmut_38` | Rule._dedup_allowed | `rec.get("DATE")` | 真洞 | 大小写错位 ⇒ daily 去重失效。**建议守阵**: 同上 |
| 77 | `xǁRuleǁ_dedup_allowed__mutmut_39` | Rule._dedup_allowed | daily 日期比较 `==`→`!=` | 真洞 | 与 mutmut_33 同根因: 当天重复执行 / 隔天误拦。**建议守阵**: 同上 |
| 78 | `xǁRuleǁ_dedup_allowed__mutmut_40` | Rule._dedup_allowed | daily 分支 `return False`→`True` | 真洞 | daily 去重失效。**建议守阵**: 同上 |
| 79 | `xǁRuleǁ_dedup_allowed__mutmut_43` | Rule._dedup_allowed | hourly 判据 `==`→`!=` | 真洞 | hourly 去重反转: 同小时已跑过反放行, 跨小时反被拦。**建议守阵**: hourly 同小时记录 → False |
| 80 | `xǁRuleǁ_dedup_allowed__mutmut_44` | Rule._dedup_allowed | `execute_once == "XXhourlyXX"` | 真洞 | hourly 去重失效 ⇒ 每 tick 重复执行。**建议守阵**: 同上 |
| 81 | `xǁRuleǁ_dedup_allowed__mutmut_45` | Rule._dedup_allowed | `execute_once == "HOURLY"` | 真洞 | 同 mutmut_44。**建议守阵**: 同上 |
| 82 | `xǁRuleǁ_dedup_allowed__mutmut_46` | Rule._dedup_allowed | hourly 分支 `rec.get(None)`(date) | 真洞 | date 取不到 ⇒ hourly 去重失效。**建议守阵**: 同上 |
| 83 | `xǁRuleǁ_dedup_allowed__mutmut_47` | Rule._dedup_allowed | `rec.get("XXdateXX")`(hourly) | 真洞 | 键名错位 ⇒ hourly 去重失效。**建议守阵**: 同上 |
| 84 | `xǁRuleǁ_dedup_allowed__mutmut_48` | Rule._dedup_allowed | `rec.get("DATE")`(hourly) | 真洞 | 大小写错位 ⇒ hourly 去重失效。**建议守阵**: 同上 |
| 85 | `xǁRuleǁ_dedup_allowed__mutmut_50` | Rule._dedup_allowed | `rec.get(None)`(hour) | 真洞 | 小时取不到 ⇒ 同小时判据恒假 ⇒ hourly 去重失效。**建议守阵**: 同上 |
| 86 | `xǁRuleǁ_dedup_allowed__mutmut_51` | Rule._dedup_allowed | `rec.get("XXhourXX")` | 真洞 | 键名错位 ⇒ hourly 去重失效。**建议守阵**: 同上 |
| 87 | `xǁRuleǁ_dedup_allowed__mutmut_52` | Rule._dedup_allowed | `rec.get("HOUR")` | 真洞 | 大小写错位 ⇒ hourly 去重失效。**建议守阵**: 同上 |
| 88 | `xǁRuleǁ_dedup_allowed__mutmut_53` | Rule._dedup_allowed | 小时比较 `==`→`!=` | 真洞 | 同 mutmut_43: 同小时重复执行 / 跨小时漏执行。**建议守阵**: 同上 |
| 89 | `xǁRuleǁ_dedup_allowed__mutmut_54` | Rule._dedup_allowed | hourly 分支 `return False`→`True` | 真洞 | hourly 去重失效。**建议守阵**: 同上 |
