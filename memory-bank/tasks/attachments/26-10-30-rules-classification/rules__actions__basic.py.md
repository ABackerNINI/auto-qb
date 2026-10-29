# 分类: src/auto_qb/rules/actions/basic.py

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__actions__basic.py.txt`
- 机器实测: 108 条全部真存活(池抓不住)
- 计数: 108 条 = 真洞 53 / 等价 55 / 假存活 0

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `xǁAddTagsActionǁ__init____mutmut_1` | AddTagsAction.__init__ | 默认值 `ignore_error=False` → `True` | 等价 | 生产唯一构造点 registry.create_action 恒显式传第三参, 默认值不可达; 池内直接构造的实例只调 execute, 不读 ignore_error ⇒ 无可区分路径(同 registry 分片 mutmut_1 判法) |
| 2 | `xǁAddTagsActionǁ__init____mutmut_2` | AddTagsAction.__init__ | `super().__init__(None, ignore_error)` | 等价 | self.spec 全仓无读点(仅 base.py:88 赋值), tags 由本地参数 spec 算出, 与 self.spec 无关 ⇒ 无读点字段 |
| 3 | `xǁAddTagsActionǁ__init____mutmut_3` | AddTagsAction.__init__ | `super().__init__(spec, None)` | 真洞 | ignore_next_action_error=true 时 self.ignore_error 由 True 变 None, base.py:257 `if not action.ignore_error` 分支反转 ⇒ 前动作异常后本应中断整链却继续跑后续动作(错误隔离失效); 现测只在 skip 路径带该标志故池抓不住。**建议守阵**: 断言 `AddTagsAction(spec, True).ignore_error is True` |
| 4 | `xǁAddTagsActionǁ__init____mutmut_4` | AddTagsAction.__init__ | `super().__init__(ignore_error)` | 真洞 | 实参错位: spec 变 False/True(无读点), ignore_error 恒落默认 False ⇒ 同 mutmut_3, ignore_next_action_error 语义被吞。**建议守阵**: 传 True 时 `.ignore_error` 仍为 True |
| 5 | `xǁAddTagsActionǁ__init____mutmut_5` | AddTagsAction.__init__ | `super().__init__(spec, )` | 真洞 | 丢弃第二实参, ignore_error 回落 False ⇒ 同 mutmut_3。**建议守阵**: 同 mutmut_3 |
| 6 | `xǁAddTagsActionǁ__init____mutmut_8` | AddTagsAction.__init__ | `isinstance(spec, list)) or True` 恒真 | 真洞 | 条件恒真 ⇒ 非 list 的 spec(配置里 add_tag 常是单个字符串)走 `list(spec)` 被拆成单字符标签, 加标签副作用变成加一堆错标签。**建议守阵**: `AddTagsAction("TAG").tags == ["TAG"]` |
| 7 | `xǁAddTagsActionǁexecute__mutmut_12` | AddTagsAction.execute | `skip(f"标签已存在: {tags}")` → `skip(None)` | 等价 | 状态仍是 skipped, 只丢跳过文案; 池只断言 `.is_skipped`, 文案仅进 DEBUG 日志 |
| 8 | `xǁAddTagsActionǁexecute__mutmut_18` | AddTagsAction.execute | `ok(f"{new}")` → `ok(None)` | 等价 | 状态仍 success, 真实副作用 torrents_add_tags(tags=new, torrent_hashes=ctx.hash) 一字未变, 仅成功文案为空 |
| 9 | `xǁRemoveTagsActionǁ__init____mutmut_1` | RemoveTagsAction.__init__ | 默认值 `ignore_error=False` → `True` | 等价 | 同 mutmut_1: 默认值不可达, 直接构造只调 execute |
| 10 | `xǁRemoveTagsActionǁ__init____mutmut_2` | RemoveTagsAction.__init__ | `super().__init__(None, ignore_error)` | 等价 | 同 mutmut_2: self.spec 无读点, patterns 取自本地参数 |
| 11 | `xǁRemoveTagsActionǁ__init____mutmut_3` | RemoveTagsAction.__init__ | `super().__init__(spec, None)` | 真洞 | 同 mutmut_3: ignore_next_action_error 传 True 时被 None 吞掉, 失败动作后本应中断却继续。**建议守阵**: 断言 `RemoveTagsAction(spec, True).ignore_error is True` |
| 12 | `xǁRemoveTagsActionǁ__init____mutmut_4` | RemoveTagsAction.__init__ | `super().__init__(ignore_error)` | 真洞 | 实参错位, ignore_error 恒 False, 同 mutmut_3。**建议守阵**: 同 mutmut_11 |
| 13 | `xǁRemoveTagsActionǁ__init____mutmut_5` | RemoveTagsAction.__init__ | `super().__init__(spec, )` | 真洞 | 丢第二实参, 同 mutmut_3。**建议守阵**: 同 mutmut_11 |
| 14 | `xǁRemoveTagsActionǁ__init____mutmut_8` | RemoveTagsAction.__init__ | `isinstance(spec, list)) or True` 恒真 | 真洞 | 恒真 ⇒ 字符串 spec 被拆成单字符 pattern, 删标签匹配集合整体失真(副作用漏删/错删)。**建议守阵**: `RemoveTagsAction("NOPE").patterns == ["NOPE"]` |
| 15 | `xǁRemoveTagsActionǁexecute__mutmut_10` | RemoveTagsAction.execute | `skip("无匹配标签")` → `skip(None)` | 等价 | 状态仍 skipped, 仅文案, 池断言 `.is_skipped` |
| 16 | `xǁRemoveTagsActionǁexecute__mutmut_11` | RemoveTagsAction.execute | `skip("无匹配标签")` → `skip("XX无匹配标签XX")` | 等价 | 文案包裹, 状态与分支不变; 池不校验跳过措辞 |
| 17 | `xǁRemoveTagsActionǁexecute__mutmut_14` | RemoveTagsAction.execute | `torrents_remove_tags(..., torrent_hashes=None)` | 真洞 | 删标签的目标 hash 变 None ⇒ 请求失去作用域(作用于全库或被 qB 拒绝), 副作用对象错误; 池只查 `("remove_tags", ["seed-3D"])` 记录, 不校验 hash 实参。**建议守阵**: 断言调用实参 `torrent_hashes == ctx.hash` |
| 18 | `xǁRemoveTagsActionǁexecute__mutmut_16` | RemoveTagsAction.execute | 省略 `torrent_hashes=ctx.hash` | 真洞 | 同 mutmut_17: 删标签请求不带目标种子, 副作用范围失控。**建议守阵**: 同 mutmut_17 |
| 19 | `xǁRemoveTagsActionǁ_expand_patterns__mutmut_2` | RemoveTagsAction._expand_patterns | `replace_vars(pat, ctx.torrent.tracker_conf)` → `replace_vars(pat, None)` | 真洞 | tracker_conf=None 时 utils.replace_vars 直接返回原文 ⇒ `regex:${required_seeding_time}` 之类模式永不展开(文档声明支持该变量), 匹配集合变空; 现测只用无变量 pattern 故抓不住。**建议守阵**: 带 `${required_seeding_time}` 的 pattern 应展开为 "3D" 后再匹配 |
| 20 | `xǁAddCategoryActionǁ__init____mutmut_1` | AddCategoryAction.__init__ | 默认值 `ignore_error=False` → `True` | 等价 | 同 mutmut_1: create_action 恒显式传参, 默认不可达 |
| 21 | `xǁAddCategoryActionǁ__init____mutmut_2` | AddCategoryAction.__init__ | `super().__init__(None, ignore_error)` | 等价 | 同 mutmut_2: self.spec 无读点, format/overwrite 取自本地参数 |
| 22 | `xǁAddCategoryActionǁ__init____mutmut_3` | AddCategoryAction.__init__ | `super().__init__(spec, None)` | 真洞 | 同 mutmut_3: ignore_next_action_error 被 None 吞, 失败后不中断。**建议守阵**: 断言 `AddCategoryAction({}, True).ignore_error is True` |
| 23 | `xǁAddCategoryActionǁ__init____mutmut_4` | AddCategoryAction.__init__ | `super().__init__(ignore_error)` | 真洞 | 实参错位, ignore_error 恒 False, 同 mutmut_3。**建议守阵**: 同 mutmut_22 |
| 24 | `xǁAddCategoryActionǁ__init____mutmut_5` | AddCategoryAction.__init__ | `super().__init__(spec, )` | 真洞 | 丢第二实参, 同 mutmut_3。**建议守阵**: 同 mutmut_22 |
| 25 | `xǁAddCategoryActionǁ__init____mutmut_9` | AddCategoryAction.__init__ | `spec.get("format", "")` → `spec.get("format", None)` | 真洞 | 缺 format 键时 `str(None)=="None"` ⇒ 兜底从空串变脏值, 下游会去创建/设置名为 "None" 的分类(format 是 schema required, 但代码自带兜底被改坏)。**建议守阵**: `AddCategoryAction({}).format == ""` |
| 26 | `xǁAddCategoryActionǁ__init____mutmut_11` | AddCategoryAction.__init__ | `spec.get("format", )`(默认 None) | 真洞 | 与 mutmut_25 同效: 缺键时 format 变 "None"。**建议守阵**: 同 mutmut_25 |
| 27 | `xǁAddCategoryActionǁ__init____mutmut_14` | AddCategoryAction.__init__ | `spec.get("format", "XXXX")` | 真洞 | 缺键时分类名变 "XXXX" 并被真实下发, 兜底语义错。**建议守阵**: 同 mutmut_25 |
| 28 | `xǁAddCategoryActionǁ__init____mutmut_15` | AddCategoryAction.__init__ | `self.overwrite = None` | 真洞 | overwrite 恒假 ⇒ 配置 `overwrite: true`(schema 明示"开启后会覆盖人工设置的分类")被静默无视, 用户开关失效; 现测只覆盖 overwrite=False。**建议守阵**: `AddCategoryAction({"format":"X","overwrite":True}).overwrite is True` |
| 29 | `xǁAddCategoryActionǁ__init____mutmut_17` | AddCategoryAction.__init__ | `spec.get(None, False)` | 真洞 | 读不到键 ⇒ overwrite 恒 False, 同 mutmut_28。**建议守阵**: 同 mutmut_28 |
| 30 | `xǁAddCategoryActionǁ__init____mutmut_21` | AddCategoryAction.__init__ | 键名 `"overwrite"` → `"XXoverwriteXX"` | 真洞 | 键名打错 ⇒ overwrite 恒 False, 同 mutmut_28。**建议守阵**: 同 mutmut_28 |
| 31 | `xǁAddCategoryActionǁ__init____mutmut_22` | AddCategoryAction.__init__ | 键名 `"overwrite"` → `"OVERWRITE"` | 真洞 | 大小写变体读不到 ⇒ overwrite 恒 False, 同 mutmut_28。**建议守阵**: 同 mutmut_28 |
| 32 | `xǁAddCategoryActionǁexecute__mutmut_3` | AddCategoryAction.execute | `replace_vars(self.format, tracker_conf)` → `replace_vars(self.format, None)` | 真洞 | format 里的 `${required_seeding_time}` 不再展开(schema help 明确支持), 分类名留下占位符原文; 现测 format 全是常量。**建议守阵**: format 含变量时 category 应为展开后的 "3D" 而非 `${required_seeding_time}` |
| 33 | `xǁAddCategoryActionǁexecute__mutmut_10` | AddCategoryAction.execute | `skip("分类已设置")` → `skip(None)` | 等价 | 状态仍 skipped, 仅文案 |
| 34 | `xǁAddCategoryActionǁexecute__mutmut_11` | AddCategoryAction.execute | `skip("分类已设置")` → `skip("XX分类已设置XX")` | 等价 | 文案包裹, 分支与状态不变 |
| 35 | `xǁAddCategoryActionǁexecute__mutmut_26` | AddCategoryAction.execute | `skip(f"已有分类 {old_category}, 不覆盖")` → `skip(None)` | 等价 | 不覆盖的分支判定未动, 只是跳过文案为空(池断言 `.is_skipped`) |
| 36 | `xǁAddCategoryActionǁexecute__mutmut_29` | AddCategoryAction.execute | `torrents_create_category(name=category)` → `name=None` | 真洞 | 分类不存在时真去建一个名为 None 的分类(qB 侧留下脏分类); 池只断言 set_category 发生, 不校验 create 的 name。**建议守阵**: 断言 create_category 收到 `name == "AUTO-A"` |
| 37 | `xǁAddCategoryActionǁexecute__mutmut_31` | AddCategoryAction.execute | `torrents_set_category(..., torrent_hashes=None)` | 真洞 | 分类变更的目标 hash 变 None ⇒ 改分类作用域失控(全库/被拒); 池只查 `("set_category", "NEW")`。**建议守阵**: 断言 set_category 实参 `torrent_hashes == ctx.hash` |
| 38 | `xǁAddCategoryActionǁexecute__mutmut_33` | AddCategoryAction.execute | 省略 `torrent_hashes=ctx.hash` | 真洞 | 同 mutmut_37: 分类副作用不带目标种子。**建议守阵**: 同 mutmut_37 |
| 39 | `xǁAddCategoryActionǁexecute__mutmut_35` | AddCategoryAction.execute | `ok(category)` → `ok(None)` | 等价 | 状态仍 success, 副作用(create/set/auto_categories 记录)全在, 仅成功文案为空 |
| 40 | `xǁRemoveCategoryActionǁexecute__mutmut_4` | RemoveCategoryAction.execute | `skip("分类为空")` → `skip(None)` | 等价 | 状态仍 skipped, 仅文案 |
| 41 | `xǁRemoveCategoryActionǁexecute__mutmut_5` | RemoveCategoryAction.execute | `skip("分类为空")` → `skip("XX分类为空XX")` | 等价 | 文案包裹, 状态不变 |
| 42 | `xǁRemoveCategoryActionǁexecute__mutmut_8` | RemoveCategoryAction.execute | `set_category(category="", torrent_hashes=None)` | 真洞 | 清空分类的目标 hash 变 None ⇒ 副作用作用域失控(可能清掉全库分类); 池只查 `("set_category", "")`。**建议守阵**: 断言 set_category 实参 `torrent_hashes == ctx.hash` |
| 43 | `xǁRemoveCategoryActionǁexecute__mutmut_10` | RemoveCategoryAction.execute | 省略 `torrent_hashes=ctx.hash` | 真洞 | 同 mutmut_42。**建议守阵**: 同 mutmut_42 |
| 44 | `xǁStartActionǁexecute__mutmut_2` | StartAction.execute | `skip("已开始")` → `skip(None)` | 等价 | 状态仍 skipped, 仅文案 |
| 45 | `xǁStartActionǁexecute__mutmut_3` | StartAction.execute | `skip("已开始")` → `skip("XX已开始XX")` | 等价 | 文案包裹, 幂等分支未动 |
| 46 | `xǁStartActionǁexecute__mutmut_8` | StartAction.execute | `own_write_pending(hash, group=False)` → `group=None` | 等价 | store.own_write_pending 内是 `if not group: return False`, None 与 False 同分支 ⇒ 判据完全一致 |
| 47 | `xǁStartActionǁexecute__mutmut_10` | StartAction.execute | 省略 `group=False`(取默认 `group=True`) | 真洞 | 判据从"只看本 hash"变"看全组" ⇒ 同组兄弟刚被停/起时本 hash 也被判 pending 而跳过, 组内成员各自起停互相误伤(源码注释明确要求避免); 现测的种子不在任何组, 故 group 维度不可见。**建议守阵**: 同组另一成员有 own_write 时, 本 hash 的 start 仍应下发 |
| 48 | `xǁStartActionǁexecute__mutmut_11` | StartAction.execute | `group=False` → `group=True` | 真洞 | 同 mutmut_47(显式传 True), 组维度误伤。**建议守阵**: 同 mutmut_47 |
| 49 | `xǁStartActionǁexecute__mutmut_12` | StartAction.execute | `skip(_OWN_WRITE_PENDING_MSG)` → `skip(None)` | 等价 | 让位分支仍 skip, 只丢提示文案 |
| 50 | `xǁStartActionǁexecute__mutmut_14` | StartAction.execute | `ok("开始")` → `ok(None)` | 等价 | 状态仍 success, torrents_start 调用未变, 仅文案 |
| 51 | `xǁStartActionǁexecute__mutmut_15` | StartAction.execute | `ok("开始")` → `ok("XX开始XX")` | 等价 | 文案包裹, 状态与副作用不变 |
| 52 | `xǁStopActionǁexecute__mutmut_1` | StopAction.execute | `skip("已停止")` → `skip(None)` | 等价 | 状态仍 skipped, 仅文案 |
| 53 | `xǁStopActionǁexecute__mutmut_2` | StopAction.execute | `skip("已停止")` → `skip("XX已停止XX")` | 等价 | 文案包裹, 幂等分支未动 |
| 54 | `xǁStopActionǁexecute__mutmut_7` | StopAction.execute | `own_write_pending(hash, group=False)` → `group=None` | 等价 | 同 mutmut_46: `if not group` 真值判断, None 与 False 同分支 |
| 55 | `xǁStopActionǁexecute__mutmut_9` | StopAction.execute | 省略 `group=False`(默认 `group=True`) | 真洞 | 同 mutmut_47: 判据扩到全组 ⇒ 兄弟成员刚下发停/起会让本 hash 误跳过暂停。**建议守阵**: 组内他人有 own_write 时本 hash 的 stop 仍应下发 |
| 56 | `xǁStopActionǁexecute__mutmut_10` | StopAction.execute | `group=False` → `group=True` | 真洞 | 同 mutmut_55(显式 True)。**建议守阵**: 同 mutmut_55 |
| 57 | `xǁStopActionǁexecute__mutmut_11` | StopAction.execute | `skip(_OWN_WRITE_PENDING_MSG)` → `skip(None)` | 等价 | 让位分支仍 skip, 仅丢文案 |
| 58 | `xǁStopActionǁexecute__mutmut_13` | StopAction.execute | `ok("暂停")` → `ok(None)` | 等价 | 状态仍 success, torrents_stop 未变 |
| 59 | `xǁStopActionǁexecute__mutmut_14` | StopAction.execute | `ok("暂停")` → `ok("XX暂停XX")` | 等价 | 文案包裹, 状态与副作用不变 |
| 60 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_4` | PrintTorrentDetailsAction.execute | `fail("种子不存在, 无法打印详情")` → `fail("XX种子不存在...XX")` | 等价 | 仍 failed, 池断言 `"种子不存在" in message` 依旧成立, 只多包了前缀后缀 |
| 61 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_6` | PrintTorrentDetailsAction.execute | 键 `"名称"` → `"XX名称XX"` | 等价 | 仅日志行标签文案, 取值表达式 `tor.name or "-"` 未动 |
| 62 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_7` | PrintTorrentDetailsAction.execute | `tor.name or "-"` → `tor.name and "-"` | 真洞 | 名称非空时结果恒为 "-", 值语义反转(空值兜底被拿去替换有值) ⇒ 详情行丢失真实名称。**建议守阵**: caplog 断言含真实名(如 `名称=Some.Name`), 而非 `名称=-` |
| 63 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_8` | PrintTorrentDetailsAction.execute | 兜底串 `"-"` → `"XX-XX"` | 等价 | 仅空值时的占位文案, 有值时输出不变 |
| 64 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_9` | PrintTorrentDetailsAction.execute | 键 `"状态"` → `"XX状态XX"` | 等价 | 标签文案, 取值 `tor.state or "-"` 未动 |
| 65 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_10` | PrintTorrentDetailsAction.execute | `tor.state or "-"` → `tor.state and "-"` | 真洞 | 状态非空时恒 "-", 同 mutmut_62 的值反转。**建议守阵**: 同 mutmut_62(状态字段) |
| 66 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_11` | PrintTorrentDetailsAction.execute | 兜底串 `"XX-XX"`(状态) | 等价 | 同 mutmut_63: 占位文案 |
| 67 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_12` | PrintTorrentDetailsAction.execute | 键 `"保存路径"` → `"XX保存路径XX"` | 等价 | 标签文案 |
| 68 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_13` | PrintTorrentDetailsAction.execute | `tor.save_path or "-"` → `and "-"` | 真洞 | 保存路径非空时恒 "-", 同 mutmut_62。**建议守阵**: 同 mutmut_62(路径字段) |
| 69 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_14` | PrintTorrentDetailsAction.execute | 兜底串 `"XX-XX"`(保存路径) | 等价 | 占位文案 |
| 70 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_15` | PrintTorrentDetailsAction.execute | 键 `"内容路径"` → `"XX内容路径XX"` | 等价 | 标签文案 |
| 71 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_16` | PrintTorrentDetailsAction.execute | `tor.content_path or "-"` → `and "-"` | 真洞 | 内容路径非空时恒 "-", 同 mutmut_62。**建议守阵**: 同 mutmut_62(内容路径字段) |
| 72 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_17` | PrintTorrentDetailsAction.execute | 兜底串 `"XX-XX"`(内容路径) | 等价 | 占位文案 |
| 73 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_18` | PrintTorrentDetailsAction.execute | 键 `"大小"` → `"XX大小XX"` | 等价 | 标签文案, `fmt_size(tor.size)` 未动 |
| 74 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_19` | PrintTorrentDetailsAction.execute | `fmt_size(tor.size)` → `fmt_size(None)` | 真洞 | fmt_size(None) 走异常分支返回 "-" ⇒ 大小字段恒占位, 真实体积丢失。**建议守阵**: caplog 断言 `大小=<非->` |
| 75 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_20` | PrintTorrentDetailsAction.execute | 键 `"进度"` → `"XX进度XX"` | 等价 | 标签文案 |
| 76 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_21` | PrintTorrentDetailsAction.execute | 进度条件 `and False` | 真洞 | 条件恒假 ⇒ 进度恒 "-", 有进度也不显示。**建议守阵**: progress=0.5 时日志含 `进度=50.0%` |
| 77 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_22` | PrintTorrentDetailsAction.execute | 进度条件 `or True` | 真洞 | 条件恒真 ⇒ progress=None 时 `None*100` 抛 TypeError, 打印动作在缺字段种子上崩溃(正是兜底要防的)。**建议守阵**: progress=None 时仍返回 ok 且进度显示 "-" |
| 78 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_23` | PrintTorrentDetailsAction.execute | `tor.progress * 100` → `/ 100` | 真洞 | 进度百分比数值错 10000 倍(0.5 → 0.0% 而非 50.0%), 数值语义错。**建议守阵**: 同 mutmut_76 的精确数值断言 |
| 79 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_24` | PrintTorrentDetailsAction.execute | `* 100` → `* 101` | 真洞 | 进度数值错(0.5 → 50.5%), 同上。**建议守阵**: 同 mutmut_76 |
| 80 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_25` | PrintTorrentDetailsAction.execute | `progress is not None` → `is None` | 真洞 | 条件反转 ⇒ 有进度反而显示 "-", 无进度时进格式化分支抛 TypeError。**建议守阵**: 同 mutmut_76 + mutmut_77 |
| 81 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_26` | PrintTorrentDetailsAction.execute | 兜底串 `"XX-XX"`(进度) | 等价 | 占位文案 |
| 82 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_27` | PrintTorrentDetailsAction.execute | 键 `"上传"` → `"XX上传XX"` | 等价 | 标签文案 |
| 83 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_28` | PrintTorrentDetailsAction.execute | `fmt_size(tor.uploaded)` → `fmt_size(None)` | 真洞 | 上传量恒 "-", 同 mutmut_74。**建议守阵**: 同 mutmut_74(上传字段) |
| 84 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_29` | PrintTorrentDetailsAction.execute | 键 `"下载"` → `"XX下载XX"` | 等价 | 标签文案 |
| 85 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_30` | PrintTorrentDetailsAction.execute | `fmt_size(tor.downloaded)` → `fmt_size(None)` | 真洞 | 下载量恒 "-", 同 mutmut_74。**建议守阵**: 同 mutmut_74(下载字段) |
| 86 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_31` | PrintTorrentDetailsAction.execute | 键 `"分享率"` → `"XX分享率XX"` | 等价 | 标签文案 |
| 87 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_32` | PrintTorrentDetailsAction.execute | 分享率条件 `and False` | 真洞 | 分享率恒 "-", 有值也不显示。**建议守阵**: ratio=1.5 时日志含 `分享率=1.50` |
| 88 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_33` | PrintTorrentDetailsAction.execute | 分享率条件 `or True` | 真洞 | ratio=None 时 `None:.2f` 抛 TypeError, 缺字段兜底失效。**建议守阵**: ratio=None 时仍 ok 且显示 "-" |
| 89 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_34` | PrintTorrentDetailsAction.execute | `ratio is not None` → `is None` | 真洞 | 条件反转, 有分享率显示 "-", 无分享率崩溃, 同 mutmut_80。**建议守阵**: 同 mutmut_87 |
| 90 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_35` | PrintTorrentDetailsAction.execute | 兜底串 `"XX-XX"`(分享率) | 等价 | 占位文案 |
| 91 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_36` | PrintTorrentDetailsAction.execute | 键 `"做种时长"` → `"XX做种时长XX"` | 等价 | 标签文案 |
| 92 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_37` | PrintTorrentDetailsAction.execute | 做种时长条件 `and False` | 真洞 | 做种时长恒 "-", 有值也不显示。**建议守阵**: seeding_time=86400 时日志含 `做种时长=86400s` |
| 93 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_38` | PrintTorrentDetailsAction.execute | 做种时长条件 `or True` | 真洞 | seeding_time=None 时 `int(None)` 抛 TypeError, 缺字段兜底失效。**建议守阵**: seeding_time=None 时仍 ok 且显示 "-" |
| 94 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_40` | PrintTorrentDetailsAction.execute | `seeding_time is not None` → `is None` | 真洞 | 条件反转, 同 mutmut_89。**建议守阵**: 同 mutmut_92 |
| 95 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_41` | PrintTorrentDetailsAction.execute | 兜底串 `"XX-XX"`(做种时长) | 等价 | 占位文案 |
| 96 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_42` | PrintTorrentDetailsAction.execute | 键 `"标签"` → `"XX标签XX"` | 等价 | 标签文案 |
| 97 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_43` | PrintTorrentDetailsAction.execute | `tor.tags or "-"` → `and "-"` | 真洞 | 有标签时恒 "-", 同 mutmut_62。**建议守阵**: 同 mutmut_62(标签字段) |
| 98 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_44` | PrintTorrentDetailsAction.execute | 兜底串 `"XX-XX"`(标签) | 等价 | 占位文案 |
| 99 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_45` | PrintTorrentDetailsAction.execute | 键 `"分类"` → `"XX分类XX"` | 等价 | 标签文案 |
| 100 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_46` | PrintTorrentDetailsAction.execute | `tor.category or "-"` → `and "-"` | 真洞 | 有分类时恒 "-", 同 mutmut_62。**建议守阵**: 同 mutmut_62(分类字段) |
| 101 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_47` | PrintTorrentDetailsAction.execute | 兜底串 `"XX-XX"`(分类) | 等价 | 占位文案 |
| 102 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_48` | PrintTorrentDetailsAction.execute | 键 `"tracker"` → `"XXtrackerXX"` | 等价 | 标签文案 |
| 103 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_49` | PrintTorrentDetailsAction.execute | 键 `"tracker"` → `"TRACKER"` | 等价 | 大小写变体, 仍是标签文案, 取值 `tor.tracker_name` 未动 |
| 104 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_50` | PrintTorrentDetailsAction.execute | `detail = " \| ".join(...)` → `detail = None` | 真洞 | 整行字段明细丢失, 日志只剩 "打印种子详情: None" —— 该动作唯一产出即此行, 等于功能失效。**建议守阵**: caplog 断言日志行含 "名称=" 且含 "tracker=" |
| 105 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_52` | PrintTorrentDetailsAction.execute | 连接符 `" \| "` → `"XX \| XX"` | 等价 | 仅分隔符文案, 字段与取值全在 |
| 106 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_53` | PrintTorrentDetailsAction.execute | `logger.info(f"...")` → `logger.info(None)` | 真洞 | 动作唯一可观测产出(日志行)整体消失, 只读动作变空操作。**建议守阵**: 同 mutmut_104(caplog 有且仅有一行详情) |
| 107 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_54` | PrintTorrentDetailsAction.execute | `ok("打印种子详情")` → `ok(None)` | 等价 | 状态仍 success, 仅返回文案为空 |
| 108 | `xǁPrintTorrentDetailsActionǁexecute__mutmut_55` | PrintTorrentDetailsAction.execute | `ok("打印种子详情")` → `ok("XX打印种子详情XX")` | 等价 | 文案包裹, 状态与日志副作用不变 |
