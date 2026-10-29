# 分类: src/auto_qb/rules/actions/checking.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__actions__checking.py.txt`
- 机器实测: 43 条全部真存活(池抓不住)
- 计数: 43 条 = 真洞 8 / 等价 35 / 假存活 0

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `xǁCheckActionǁ__init____mutmut_1` | CheckAction.__init__ | 默认值 `ignore_error=False` → `True` | 等价 | 生产唯一构造点是 registry.create_action(name, value, ignore_error)(registry.py:30)恒显式传第二实参 ⇒ 默认值不可达; 池内直接构造的实例只调 execute, 不读 ignore_error |
| 2 | `xǁCheckActionǁ__init____mutmut_2` | CheckAction.__init__ | `super().__init__(None, ignore_error)` | 等价 | `self.spec` 全仓无读点(仅 base.py:88 赋值, grep 无 `.spec` 读取); basic_check/段落全部由本地形参 spec 解析 ⇒ 无读点字段 |
| 3 | `xǁCheckActionǁ__init____mutmut_3` | CheckAction.__init__ | `super().__init__(spec, None)` | 真洞 | ignore_next_action_error=true 时 self.ignore_error 由 True 变 None, base.py:257 `if not action.ignore_error` 变假 ⇒ 前动作失败后本应中断整链却继续跑后续动作(错误隔离失效)。**建议守阵**: 断言 `CheckAction(spec, True).ignore_error is True` |
| 4 | `xǁCheckActionǁ__init____mutmut_4` | CheckAction.__init__ | `super().__init__(ignore_error)` | 真洞 | 实参错位: spec 落成 False(无读点), ignore_error 恒落默认 False ⇒ 同 #3, ignore_next_action_error 被吞。**建议守阵**: 同 #3 |
| 5 | `xǁCheckActionǁ__init____mutmut_5` | CheckAction.__init__ | `super().__init__(spec, )` | 真洞 | 丢弃第二实参, ignore_error 回落 False ⇒ 同 #3。**建议守阵**: 同 #3 |
| 6 | `xǁCheckActionǁ__init____mutmut_16` | CheckAction.__init__ | `or ""` → `or "XXXX"` | 等价 | config/validation/rules.py:208 强制 basic_check=custom 必配路径 ⇒ 兜底不可达; 即便直达, `subprocess.run(["XXXX",…])` 与 `["",…]` 均抛 FileNotFoundError 被同一 except 吞成 False |
| 7 | `xǁCheckActionǁexecute__mutmut_1` | CheckAction.execute | dry_run 文案 → `ok(None)` | 等价 | 状态仍 success, 仅试运行描述文案为空, 无副作用 |
| 8 | `xǁCheckActionǁexecute__mutmut_2` | CheckAction.execute | dry_run 文案包 `XX…XX` | 等价 | 同 #7, 纯文案 |
| 9 | `xǁCheckActionǁexecute__mutmut_5` | CheckAction.execute | S2 让位 `skip(文案)` → `skip(None)` | 等价 | 状态仍 skipped、放行时机不变, 仅丢跳过理由文案 |
| 10 | `xǁCheckActionǁexecute__mutmut_6` | CheckAction.execute | S2 让位文案包 `XX…XX` | 等价 | 同 #9 |
| 11 | `xǁCheckActionǁexecute__mutmut_7` | CheckAction.execute | 文案 `qB` → `qb` | 等价 | 纯文案大小写 |
| 12 | `xǁCheckActionǁexecute__mutmut_8` | CheckAction.execute | 文案 `qB`→`QB`, `tick`→`TICK` | 等价 | 纯文案大小写 |
| 13 | `xǁCheckActionǁexecute__mutmut_13` | CheckAction.execute | 决策链 0 `skip(文案)` → `skip(None)` | 等价 | 仍 skip, 判定条件(`is_stopped and progress<1.0`)未变, 仅文案空 |
| 14 | `xǁCheckActionǁexecute__mutmut_14` | CheckAction.execute | 决策链 0 文案包 `XX…XX` | 等价 | 同 #13 |
| 15 | `xǁCheckActionǁexecute__mutmut_22` | CheckAction.execute | 决策链 1 `skip(文案)` → `skip(None)` | 等价 | 仍 skip, 组内下载判定未变, 仅文案空 |
| 16 | `xǁCheckActionǁexecute__mutmut_23` | CheckAction.execute | 决策链 1 文案包 `XX…XX` | 等价 | 同 #15 |
| 17 | `xǁCheckActionǁexecute__mutmut_51` | CheckAction.execute | `which` 有参考文案包 `XX…XX` | 等价 | 仅拼接进 skip 文案, 分支判定(`segment is self.with_reference`)未变 |
| 18 | `xǁCheckActionǁexecute__mutmut_53` | CheckAction.execute | `which` 无参考文案包 `XX…XX` | 等价 | 同 #17 |
| 19 | `xǁCheckActionǁexecute__mutmut_61` | CheckAction.execute | 前置检查失败 `skip(f"…{err}")` → `skip(None)` | 等价 | 仍 skip(不进入跳检/全检), 仅丢 err 文案 |
| 20 | `xǁCheckActionǁexecute__mutmut_73` | CheckAction.execute | 跳检 `bool(reference)` → `None` | 等价 | has_reference 唯一消费点是 ops_mod.py:1147 的一条 `logger.warning`(无参考跳检高风险告警), 不参与 `_skip_begin` 闸门/相位/结果 ⇒ 文案面 |
| 21 | `xǁCheckActionǁexecute__mutmut_77` | CheckAction.execute | 跳检 `bool(reference)` → `bool(None)` | 等价 | 同 #20(恒 False) |
| 22 | `xǁCheckActionǁ_find_reference__mutmut_27` | CheckAction._find_reference | `logger.warning(f"…")` → `warning(None)` | 等价 | 仅日志 |
| 23 | `xǁCheckActionǁ_find_reference__mutmut_28` | CheckAction._find_reference | 取目标 piece hashes 异常时 `target = None` → `""` | 等价 | `"" is not None` 仍进候选循环, 但 `list == ""` 恒假 ⇒ refs 仍为空; 差别只是多 N 次 API 调用(且异常分支再记日志), 参考集不可区分 |
| 24 | `xǁCheckActionǁ_find_reference__mutmut_33` | CheckAction._find_reference | 候选异常 `logger.warning(f"…")` → `warning(None)` | 等价 | 仅日志 |
| 25 | `xǁCheckActionǁ_find_reference__mutmut_35` | CheckAction._find_reference | `self._run_custom_check(ctx, c)` → `(None, c)` | 等价 | `_run_custom_check` 形参 ctx 在函数体内无读点(只用 self.custom_program 与 candidate) ⇒ 无读点参数 |
| 26 | `xǁCheckActionǁ_find_reference__mutmut_43` | CheckAction._find_reference | 并集条件 `h in members` → `h not in members` | 真洞 | 条件反转: 组内已验证种子被排除, 而 `by_hash` 是 store 全域(非本组)映射 ⇒ 组外无关种子被当作参考, 有参考分支可能按不相关数据跳检/全量校验; 组内历史验证参考则全部失效。**建议守阵**: verified_references={组内兄弟 X, 组外 Y} 时 refs 只含 X、不含 Y |
| 27 | `xǁCheckActionǁ_find_reference__mutmut_45` | CheckAction._find_reference | 并集条件 `h in by_hash` → `h not in by_hash` | 真洞 | members 与 by_hash 同源(store.group_members ⊂ store.by_hash)⇒ 条件恒假, verified_references 并集整体失效: 历史 full-checking 通过的组内种子不再作参考, 重复全量校验/跳检退化为无参考。**建议守阵**: 组内兄弟在 verified_references 中时 `_find_reference` 非空 |
| 28 | `xǁCheckActionǁ_find_reference__mutmut_46` | CheckAction._find_reference | `refs.append(by_hash[h])` → `append(None)` | 等价 | 下游去重循环首条 `if t is None or … : continue` 把 None 全过滤, result 逐元素相同 |
| 29 | `xǁCheckActionǁ_find_reference__mutmut_53` | CheckAction._find_reference | 去重循环 `continue` → `break` | 真洞 | 首个被过滤项(带跳检标签/重复 hash/None)即中断遍历 ⇒ 其后候选与 verified 参考全丢, 有参考退化无参考(错误参考传播防线也因此少一环)。**建议守阵**: refs=[带标种子, 正常种子] 时结果含正常种子 |
| 30 | `xǁCheckActionǁ_run_custom_check__mutmut_3` | CheckAction._run_custom_check | `capture_output=True` → `None` | 等价 | 子进程输出改走继承 ⇒ `r.stderr` 为 None, 非零 rc 路径 `r.stderr.strip()` 抛 AttributeError 被外层 `except Exception` 吞, 仍 `return False`; 返回 True/False 两分支与源码一致, 只差日志与控制台噪声 |
| 31 | `xǁCheckActionǁ_run_custom_check__mutmut_4` | CheckAction._run_custom_check | `text=True` → `None` | 等价 | stderr 变 bytes, `.strip()[:200]` 仍可用, 仅日志显示 `b'…'`; 返回值恒同源码 |
| 32 | `xǁCheckActionǁ_run_custom_check__mutmut_5` | CheckAction._run_custom_check | `timeout=600` → `None` | 真洞 | 自定义校验程序挂死时规则线程无限阻塞(600s 是唯一保险丝), 全进程规则调度随之停摆。**建议守阵**: mock subprocess.run 断言调用 kwargs 含 `timeout=600` |
| 33 | `xǁCheckActionǁ_run_custom_check__mutmut_7` | CheckAction._run_custom_check | 删 `capture_output=True` | 等价 | 同 #30(缺省即不捕获, stderr=None → 异常被吞, 返回 False) |
| 34 | `xǁCheckActionǁ_run_custom_check__mutmut_8` | CheckAction._run_custom_check | 删 `text=True` | 等价 | 同 #31 |
| 35 | `xǁCheckActionǁ_run_custom_check__mutmut_9` | CheckAction._run_custom_check | 删 `timeout=600` 行 | 真洞 | 缺省 timeout=None, 与 #32 同因(无超时保险丝)。**建议守阵**: 同 #32 |
| 36 | `xǁCheckActionǁ_run_custom_check__mutmut_10` | CheckAction._run_custom_check | `capture_output=True` → `False` | 等价 | False 与 None 同为不捕获, 同 #30 |
| 37 | `xǁCheckActionǁ_run_custom_check__mutmut_11` | CheckAction._run_custom_check | `text=True` → `False` | 等价 | 同 #31 |
| 38 | `xǁCheckActionǁ_run_custom_check__mutmut_12` | CheckAction._run_custom_check | `timeout=600` → `601` | 等价 | 10 分钟超时边界的 1s 偏移, 任何测试/生产路径都不可区分(仍是有界超时) |
| 39 | `xǁCheckActionǁ_run_custom_check__mutmut_16` | CheckAction._run_custom_check | 非参考 `logger.info(f"…")` → `info(None)` | 等价 | 仅日志, 仍 `return False` |
| 40 | `xǁCheckActionǁ_run_custom_check__mutmut_17` | CheckAction._run_custom_check | 日志 `candidate.hash[:8]` → `[:9]` | 等价 | 仅日志截断长度 |
| 41 | `xǁCheckActionǁ_run_custom_check__mutmut_18` | CheckAction._run_custom_check | 日志 `r.stderr.strip()[:200]` → `[:201]` | 等价 | 仅日志截断长度 |
| 42 | `xǁCheckActionǁ_run_custom_check__mutmut_20` | CheckAction._run_custom_check | 异常 `logger.error(f"…")` → `error(None)` | 等价 | 仅日志, 仍 `return False` |
| 43 | `xǁCheckActionǁ_run_custom_check__mutmut_21` | CheckAction._run_custom_check | 异常日志 `candidate.hash[:8]` → `[:9]` | 等价 | 仅日志截断长度 |

## 真洞归并(3 个根因)

1. **ignore_error 透传丢失**(#3/#4/#5): `ignore_next_action_error` 配在 checking 前的动作上时, 检查动作失败不再被容错, 整链中断。
2. **参考并集筛选条件**(#26/#27): 一条反转成跨组参考(错误数据), 一条恒假使 `verified_references` 并集整体失效(重复全量校验)。
3. **自定义校验子进程保护**(#32/#35 超时) 与 **参考去重循环控制**(#29 `continue`→`break` 截断参考集)。
