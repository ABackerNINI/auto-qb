# 分类: src/auto_qb/rules/actions/transfer.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__actions__transfer.py.txt`
- 机器实测: 71 条全部真存活
- 计数: 71 条 = 真洞 14 / 等价 57 / 假存活 0

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁ__init____mutmut_1` | MoveToAction.__init__ | 参数默认值 `ignore_error=False` → `True` | 等价 | 生产唯一构造点是 registry.create_action 的三参调用（base.py:175 → registry.py:30 `ACTIONS[name](value, ignore_error)`），默认值在 src/ 内无读点，任何生产路径都拿不到差异（仅直接单参构造的测试/插件可见） |
| 2 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁ__init____mutmut_2` | MoveToAction.__init__ | `super().__init__(None, ignore_error)` | 等价 | `self.spec` 全仓只有赋值、无读取点（grep 仅 base.py:75/88/137 三处赋值），传 None 不进入任何判断 |
| 3 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁ__init____mutmut_3` | MoveToAction.__init__ | `super().__init__(spec, None)` | 真洞 | `ignore_error` 被顶成 None，而唯一消费点 base.py:257 是 `if not action.ignore_error` ⇒ 恒真分支：规则里 `ignore_next_action_error: true` 对 move_to 失效，移动失败后不再放行后续动作（base.py:175 确实会传 True）。**建议守阵**: 构造 `[ignore_next_action_error: true, move_to, add_tags]` 并让 move_to 失败，断言后续动作仍执行 |
| 4 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁ__init____mutmut_4` | MoveToAction.__init__ | `super().__init__(ignore_error)`（少一参） | 真洞 | spec 被顶成 bool（无读点，无副作用），ignore_error 落到默认 False ⇒ 同 #3，`ignore_next_action_error` 静默失效。**建议守阵**: 同上，并断言 `MoveToAction(spec, True).ignore_error is True` |
| 5 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁ__init____mutmut_5` | MoveToAction.__init__ | `super().__init__(spec, )`（省略第二实参） | 真洞 | 落到 BaseAction 的 `ignore_error=False` 默认值 ⇒ 同 #3。**建议守阵**: 同上 |
| 6 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁ__init____mutmut_8` | MoveToAction.__init__ | 条件 `isinstance(spec, dict)` → `... or True` | 等价 | spec 形状由 config 校验阶段保证为 object（schema/rules.py:277 起 `move_to` 插件 type=`object`、`path` required），非 dict 分支不可达，恒走 `spec.get("path","")` 与源码一致 |
| 7 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁ__init____mutmut_11` | MoveToAction.__init__ | `spec.get("path", "")` → `get("path", None)` | 等价 | 只在 `path` 键缺失时产生 "None" 差异，而 path 是 schema required 字段、缺键规则在校验阶段被拒；合法输入下与源码逐字节相同 |
| 8 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁ__init____mutmut_13` | MoveToAction.__init__ | `get("path", "")` → `get("path", )` | 等价 | get 无默认即 None，与 #7 同因（缺键不可达） |
| 9 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁ__init____mutmut_16` | MoveToAction.__init__ | 默认值 `""` → `"XXXX"` | 等价 | 同 #7：缺键输入被校验阶段挡住，合法 spec 恒带 path |
| 10 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁ__init____mutmut_17` | MoveToAction.__init__ | else 支 `str(spec)` → `str(None)` | 等价 | 非 dict 分支不可达（同 #6），`str(None)` 永不执行 |
| 11 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_2` | MoveToAction.execute | `fail("move_to.path 为空")` → `fail(None)` | 等价 | 仅 message 文案；ActionResult.message 全仓只做 f-string 日志与 WebUI 回执分桶（webui/commands.py:1163 起以 message 为 key），无内容分支，status 仍是 failed |
| 12 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_3` | MoveToAction.execute | fail 文案包 `XX…XX` | 等价 | 纯文案（同上），控制流不变 |
| 13 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_4` | MoveToAction.execute | fail 文案大小写 `MOVE_TO.PATH 为空` | 等价 | 纯文案（同上） |
| 14 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_10` | MoveToAction.execute | `getattr(..., "relocate", None)` → `getattr(..., "relocate", )` | 等价 | 省略默认值后 getattr 默认仍为 None，与源码同义 |
| 15 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_15` | MoveToAction.execute | `getattr(ctx.manager, "ctx", None)` → `(…, "ctx", )` | 等价 | 同上，默认仍 None |
| 16 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_26` | MoveToAction.execute | `enabled` 默认 `False` → `None` | 等价 | `and` 链只做真值判断，None 与 False 同分支 |
| 17 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_29` | MoveToAction.execute | `getattr(..., "enabled", False)` → `(…, "enabled", )` | 等价 | 默认变 None，但 RelocateConfig 恒有 `enabled` 字段，默认值无读点；即便读到 None 也与 False 同真值分支 |
| 18 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_34` | MoveToAction.execute | `getattr(ctx.config, "relocate", None)` → `(…, "relocate", )` | 等价 | 默认仍 None；Config.relocate 恒存在（models.py:518 default_factory） |
| 19 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_39` | MoveToAction.execute | `enabled` 默认 `False` → `True` | 等价 | 生产 Config 恒带 relocate 对象与 enabled 字段，`getattr` 默认值从不生效；关闭态读到的仍是真实 False（黄金法则 2 保守默认未被破） |
| 20 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_43` | MoveToAction.execute | `relocate_execute(..., confirm=False)` → `confirm=None` | 等价 | 消费点 relocate_mod.py:747 `if verdict["cls"] == CLS_CONFIRM and not confirm`，`not None` 与 `not False` 同为真，confirm 形态照样转 skip |
| 21 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_46` | MoveToAction.execute | 省略 `confirm=False` 实参 | 等价 | relocate_execute 签名默认 `confirm: bool = False`（relocate_mod.py:680），省略后取值与源码相同 |
| 22 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_47` | MoveToAction.execute | `confirm=False` → `confirm=True` | 真洞 | 直接绕过「目录别名需用户二次确认」闸门（relocate_mod.py:747）：规则侧无交互却执行整组迁移，与 docstring「需用户点头的形态一律 skip」相反，属安全语义。池内 test_relocate_exec.py:921 的 fake `lambda hashes, path, confirm=False` 忽略 confirm 故未抓到。**建议守阵**: 用真 relocate_execute（或按 confirm 分流返回的 fake）断言规则 move_to 在 CLS_CONFIRM 形态下只回 skip、不建 job |
| 23 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_50` | MoveToAction.execute | `items[0] if items else {}` → `if (items) or True` | 等价 | relocate_execute 对非空 req 恒返回至少一条回执（gone/blocked/skip/confirm 分支全覆盖，relocate_mod.py:687-703），空列表不可达，`{}` 兜底分支无读点 |
| 24 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_60` | MoveToAction.execute | `item.get('job_id')` → `item.get(None)` | 等价 | ok 回执文案里的字段取值，None 键恒缺 ⇒ 文案变 "None"，status 与副作用不变 |
| 25 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_61` | MoveToAction.execute | `'job_id'` → `'XXjob_idXX'` | 等价 | 纯文案（同 #24） |
| 26 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_62` | MoveToAction.execute | `'job_id'` → `'JOB_ID'` | 等价 | 纯文案（同 #24） |
| 27 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_63` | MoveToAction.execute | `item.get('form')` → `item.get(None)` | 等价 | 纯文案（同上） |
| 28 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_64` | MoveToAction.execute | `'form'` → `'XXformXX'` | 等价 | 纯文案（同上） |
| 29 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_65` | MoveToAction.execute | `'form'` → `'FORM'` | 等价 | 纯文案（同上） |
| 30 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_66` | MoveToAction.execute | `item.get(None, 0)`（link_count 键名被抹） | 等价 | 纯文案：别名条数显示 0，不参与任何判断 |
| 31 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_67` | MoveToAction.execute | `link_count` 默认 `0` → `None` | 等价 | 纯文案（显示 "None 条别名"） |
| 32 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_68` | MoveToAction.execute | `item.get('link_count', 0)` → `item.get(0)` | 等价 | 纯文案（同上） |
| 33 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_69` | MoveToAction.execute | `get('link_count', 0)` → `get('link_count', )` | 等价 | 默认变 None，仅缺键时文案变 "None"，无分支依赖 |
| 34 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_70` | MoveToAction.execute | `'link_count'` → `'XXlink_countXX'` | 等价 | 纯文案（同上） |
| 35 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_71` | MoveToAction.execute | `'link_count'` → `'LINK_COUNT'` | 等价 | 纯文案（同上） |
| 36 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_72` | MoveToAction.execute | `link_count` 默认 `0` → `1` | 等价 | 纯文案（缺键时显示 1 条别名），不参与判断 |
| 37 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_77` | MoveToAction.execute | skip 文案包 `XX…XX`（已在目标位置） | 等价 | 纯文案；`cls == "skip"` 的分支判定未动，幂等语义不变 |
| 38 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_82` | MoveToAction.execute | confirm 文案包 `XX…XX` | 等价 | 纯文案；`cls == "confirm"` 仍返回 skip，且指路 WebUI 的信息仍在（只是多了 XX） |
| 39 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_83` | MoveToAction.execute | confirm 文案 `WebUI` → `webui` | 等价 | 纯文案 |
| 40 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_84` | MoveToAction.execute | confirm 文案 `WebUI` → `WEBUI` | 等价 | 纯文案 |
| 41 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_85` | MoveToAction.execute | `reason = ""` → `reason = None` | 等价 | 后续只有 `reason or '未通过预检'`，None 与 "" 同分支；`r.get("text") or reason` 在 text 缺失时同样回落到假值 |
| 42 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_87` | MoveToAction.execute | `item.get("reasons") or []` → `… and []` | 等价 | 恒得空列表 ⇒ 循环不执行、文案退回「未通过预检」；reasons 缺键时 `None and []` 为 None 会抛 TypeError，但 base.py:237 兜成 `fail("异常: …")`，status 仍是 failed，只差文案 |
| 43 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_88` | MoveToAction.execute | `item.get("reasons")` → `item.get(None)` | 等价 | 恒 None → `or []` → 空循环，文案退回默认，status 不变 |
| 44 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_89` | MoveToAction.execute | `'reasons'` → `'XXreasonsXX'` | 等价 | 同上（空循环，仅文案） |
| 45 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_90` | MoveToAction.execute | `'reasons'` → `'REASONS'` | 等价 | 同上（空循环，仅文案） |
| 46 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_91` | MoveToAction.execute | 循环体 `reason = r.get("text") or reason` → `reason = None` | 等价 | 文案退回「未通过预检」，status 与是否失败不变 |
| 47 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_92` | MoveToAction.execute | `or reason` → `and reason` | 等价 | 恒得假值（reason 初值 ""），文案退回默认；仍只影响文案 |
| 48 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_93` | MoveToAction.execute | `r.get("text")` → `r.get(None)` | 等价 | 恒 None → `or reason` → 文案退回默认，仅文案 |
| 49 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_94` | MoveToAction.execute | `'text'` → `'XXtextXX'` | 等价 | 同上，仅文案 |
| 50 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_95` | MoveToAction.execute | `'text'` → `'TEXT'` | 等价 | 同上，仅文案 |
| 51 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_99` | MoveToAction.execute | fail 文案 `'未通过预检'` 包 `XX…XX` | 等价 | 纯文案 |
| 52 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_101` | MoveToAction.execute | `torrents_set_location(torrent_hashes=ctx.hash, …)` → `torrent_hashes=None` | 真洞 | 这是 relocate 未启用时的**默认生产路径**（relocate.enabled 缺省 false）：hash 置 None ⇒ qB 端未限定种子（对全部种子生效或参数缺失被拒），与「只搬这一个种子」语义相反，属可造成大面积搬迁/静默失败的副作用丢失。**建议守阵**: relocate 关闭态执行 move_to，断言 FakeClient 收到 `set_location` 且携带 ctx.hash 而非 None |
| 53 | `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_103` | MoveToAction.execute | 省略 `torrent_hashes=ctx.hash` 实参 | 真洞 | 与 #52 同因：qbapi.py:146 形参默认 None ⇒ 目标种子丢失，动作「看起来成功」但搬的不是这个种子。**建议守阵**: 同上，并断言 `ActionResult.ok` 与 qB 调用目标一致 |
| 54 | `auto_qb.rules.actions.transfer.xǁReannounceActionǁexecute__mutmut_1` | ReannounceAction.execute | `skip("种子已暂停, 无需汇报")` → `skip(None)` | 等价 | 纯文案；`is_stopped` 判定与「不汇报」副作用不变 |
| 55 | `auto_qb.rules.actions.transfer.xǁReannounceActionǁexecute__mutmut_2` | ReannounceAction.execute | skip 文案包 `XX…XX` | 等价 | 纯文案 |
| 56 | `auto_qb.rules.actions.transfer.xǁReannounceActionǁexecute__mutmut_16` | ReannounceAction.execute | `history.get(ctx.hash, 0)` → 默认 `1` | 等价 | epoch 秒级 `now` 恒远大于 MIN_INTERVAL(600)，`now-0` 与 `now-1` 同走「放行」分支；仅当 now < 601（1970-01-01）才可区分，生产不可达 |
| 57 | `auto_qb.rules.actions.transfer.xǁReannounceActionǁexecute__mutmut_17` | ReannounceAction.execute | `<` → `<=`（限频边界） | 等价 | 仅在 `now - history` 精确等于 600.0 时分流；history 与 now 都是 `time.time()` 浮点，相等测度为零，语义同为「间隔不足则跳过」（离散枚举上的 </<= 同类） |
| 58 | `auto_qb.rules.actions.transfer.xǁReannounceActionǁexecute__mutmut_18` | ReannounceAction.execute | 限频 skip 文案 → `skip(None)` | 等价 | 纯文案；限频逻辑与 `history` 写入不变 |
| 59 | `auto_qb.rules.actions.transfer.xǁReannounceActionǁexecute__mutmut_21` | ReannounceAction.execute | `torrents_reannounce(torrent_hashes=ctx.hash)` → `None` | 真洞 | hash 置 None ⇒ 汇报对象丢失（qbapi.py:186 透传 None 到 qB，全库广播或参数缺失），而 600s 限频保护只记录 `history[ctx.hash]`、护不住其它种子 ⇒ 与「只汇报这一个、且被限频保护」语义不同，存在被 tracker 判异常封号的面。**建议守阵**: 断言 `torrents_reannounce` 收到 `torrent_hashes == ctx.hash` |
| 60 | `auto_qb.rules.actions.transfer.xǁReannounceActionǁexecute__mutmut_23` | ReannounceAction.execute | `ok("强制汇报tracker")` → `ok(None)` | 等价 | 纯文案；`history[ctx.hash] = now` 的落账仍在 |
| 61 | `auto_qb.rules.actions.transfer.xǁReannounceActionǁexecute__mutmut_24` | ReannounceAction.execute | ok 文案包 `XX…XX` | 等价 | 纯文案 |
| 62 | `auto_qb.rules.actions.transfer.xǁReannounceActionǁexecute__mutmut_25` | ReannounceAction.execute | ok 文案 `tracker` → `TRACKER` | 等价 | 纯文案 |
| 63 | `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁ__init____mutmut_1` | _SpeedLimitAction.__init__ | 参数默认值 `ignore_error=False` → `True` | 等价 | 生产唯一构造点 registry.create_action 恒传第三参（base.py:175），默认值无读点 |
| 64 | `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁ__init____mutmut_2` | _SpeedLimitAction.__init__ | `super().__init__(None, ignore_error)` | 等价 | `self.spec` 无读点；`self.value` 仍由局部 `spec` 计算（`utils.parse_speed(str(spec))`），解析结果不变 |
| 65 | `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁ__init____mutmut_3` | _SpeedLimitAction.__init__ | `super().__init__(spec, None)` | 真洞 | ignore_error 恒假 ⇒ `ignore_next_action_error: true` 对 upload/download_speed_limit 失效，限速失败即中断后续动作。**建议守阵**: 同上（#3），覆盖限速动作的 ignore_error 透传 |
| 66 | `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁ__init____mutmut_4` | _SpeedLimitAction.__init__ | `super().__init__(ignore_error)`（少一参） | 真洞 | 同 #65：ignore_error 落默认 False，spec 被顶成 bool（无读点）。**建议守阵**: 同上 |
| 67 | `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁ__init____mutmut_5` | _SpeedLimitAction.__init__ | `super().__init__(spec, )` | 真洞 | 同 #65。**建议守阵**: 同上 |
| 68 | `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁexecute__mutmut_2` | _SpeedLimitAction.execute | `"upload" in self.api_method` → `"XXuploadXX" in …` | 真洞 | 条件恒假 ⇒ 上传限速动作改读 `ctx.torrent.dl_limit`（transfer.py:87-89）：`is_manual_speed_limit` 与 `current_limit == self.value` 两道闸门全部错位，可能出现「用户已设置下载限速」误 skip、或对已达标的上传重复下发，属业务语义错配。池内 test_actions.py:336 的 FakeTorrent 上下行同为 0 故未抓到。**建议守阵**: 构造 up_limit=1000/dl_limit=0 的种子跑 UploadSpeedLimitAction，断言不被 skip 且下发上传限速 |
| 69 | `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁexecute__mutmut_3` | _SpeedLimitAction.execute | `"upload"` → `"UPLOAD"` | 真洞 | 与 #68 同因：大小写不符 ⇒ 恒走 else 分支读 dl_limit。**建议守阵**: 同上，并对称覆盖 DownloadSpeedLimitAction（读 dl_limit、不读 up_limit） |
| 70 | `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁexecute__mutmut_13` | _SpeedLimitAction.execute | `getattr(ctx.api, self.api_method)(torrent_hashes=None, …)` | 真洞 | 限速目标丢失（qbapi.py:126-142 形参默认 None 并透传，`store.update_torrent_fields(None, …)` 也会波及全部记录），动作回 ok 但限的不是这个种子。**建议守阵**: 断言限速 API 收到 `torrent_hashes == ctx.hash` |
| 71 | `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁexecute__mutmut_15` | _SpeedLimitAction.execute | 省略 `torrent_hashes=ctx.hash` 实参 | 真洞 | 与 #70 同因：形参默认 None，目标种子丢失。**建议守阵**: 同上 |

## 判据补充（供主控核）

- 本分片的 `MoveToAction` **不做任何路径拼接**：`self.path` 直接来自 spec（`str(spec.get("path",""))`），搬迁字节由 qB mover 完成（relocate_mod.py:685 D2）。任务书点名的「分隔符/相对路径/`..`/空段拼接、目标已存在冲突策略、跨盘 vs 同盘、mkdir 时机、失败回滚」在本文件的变异作用面上**一条都没有**——它们全在 `core/modules/relocate_mod.py` / `relocate_units.py`，不在本分片。本分片能触及的相邻语义只有两条：①「目录别名需二次确认」闸门被 `confirm=True` 绕过（#22）；②空 path 的 fail 兜底（#11-#13，纯文案）。
- 14 条真洞按根因归并为 4 组：**A 副作用目标丢失**（#52/#53/#59/#70/#71，qB API 的 `torrent_hashes` 被置 None 或省略 ⇒ 动作「成功」但没作用在目标种子上）5 条；**B `ignore_error` 透传断裂**（#3/#4/#5/#65/#66/#67，`ignore_next_action_error` 静默失效）6 条；**C 确认闸门绕过**（#22）1 条；**D 上下行字段错配**（#68/#69）2 条。
- 57 条等价的大头：**文案类 30 条**（fail/skip/ok 的 message、`item.get(...)` 字段名被改写、reason 提取链被短路——`ActionResult.message` 全仓只进日志与 WebUI 分桶，无内容分支）；**`getattr`/`get` 省略默认值 9 条**（Python 语义下与原式逐字节同义）；**spec 形状非法分支 5 条**（path 为 schema required、type=object，校验阶段即拒）；**默认值无读点 5 条**（registry 恒传第三参；Config.relocate 恒存在）；**None 与 False 同真值分支 2 条**；**限频边界 2 条**（#56 默认 0→1、#57 `</<=`，浮点时钟下不可区分）；其余为空列表/空循环不可达分支。
