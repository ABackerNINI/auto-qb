# rules 真洞根因簇(284 条 → 60 簇)

- 来源: 18 份三分类 md(真洞 284 条)
- 归并结果: 60 簇, 覆盖 284/284
- 档位: A = 错动作作用到真实种子 / B = 引擎骨架与匹配顺序 / C = 配置期拒收与诊断

## 总表

| 簇 | 根因 | 文件·函数 | 条数 | 档 | 建议守阵 |
|---|---|---|---|---|---|
| C01 | 六个动作类 __init__ 把 ignore_error 第二实参传丢/置 None ⇒ ignore_next_action_error 整体失效 | actions/basic.py, actions/checking.py, actions/transfer.py · AddTags/RemoveTags/AddCategory/Check/MoveTo/_SpeedLimit.__init__ | 18 | A | test_actions.py 参数化遍历全部动作类, 断言 `X(spec, True).ignore_error is True`, 并构造 [ignore_next_action_error, 必失败动作, add_tags] 断言后续动作仍执行 |
| C02 | 动作下发 qB 时 torrent_hashes=ctx.hash 被置 None 或省略 ⇒ 副作用作用域失控(全库/被拒) | actions/basic.py, actions/transfer.py · RemoveTags.execute / AddCategory.execute / RemoveCategory.execute / MoveTo.execute / Reannounce.execute / _SpeedLimit.execute | 11 | A | test_actions.py 参数化断言各动作的 FakeClient 调用实参 `torrent_hashes == ctx.hash`(非 None) |
| C03 | Rule._dedup_allowed 的 hourly 分支判据(字符串字面量/日期键/小时键/比较方向/返回)被改坏 | base.py · Rule._dedup_allowed | 11 | A | test_rule_base.py 预置同小时记录断言 `_dedup_allowed` 为 False, 跨小时记录断言为 True |
| C04 | Rule._dedup_allowed 的 daily 分支判据(execute_once 字面量/date 键/比较方向/and→or/返回)被改坏 | base.py · Rule._dedup_allowed | 9 | A | test_rule_base.py 断言 daily 当天记录 → False、昨日记录 → True(两条即可覆盖全部 9 条) |
| C05 | Rule.__init__ 的 ignore_next 状态机(初值/置位/传给 create_action/消费后复位)被改坏 ⇒ 只忽略一次 的契约失效 | base.py · Rule.__init__ | 5 | A | test_rule_base.py 用 spec 构造 [fail, action, fail, action] 断言只有紧随标记的第一个动作被忽略, 第二个失败仍中断 |
| C06 | AddCategoryAction.__init__ 的 overwrite 开关读取被改坏(置 None/键名错位/大小写) | actions/basic.py · AddCategoryAction.__init__ | 4 | A | test_actions.py 断言 `AddCategoryAction({"format":"X","overwrite":True}).overwrite is True` |
| C07 | AddTags/RemoveTags.__init__ 的 `isinstance(spec, list) or True` 恒真 ⇒ 字符串 spec 被 list() 拆成单字符 | actions/basic.py · AddTagsAction.__init__ / RemoveTagsAction.__init__ | 2 | A | test_actions.py 断言 `AddTagsAction("TAG").tags == ["TAG"]` 与 `RemoveTagsAction("NOPE").patterns == ["NOPE"]` |
| C08 | AddCategoryAction.__init__ 的 format 兜底默认值被改坏(缺键时产出 "None"/"XXXX" 脏分类名) | actions/basic.py · AddCategoryAction.__init__ | 3 | A | test_actions.py 断言 `AddCategoryAction({}).format == ""` |
| C09 | replace_vars 的 tracker_conf 实参被置 None ⇒ ${required_seeding_time} 等变量永不展开 | actions/basic.py · RemoveTagsAction._expand_patterns / AddCategoryAction.execute | 2 | A | test_actions.py 断言含 `${required_seeding_time}` 的 pattern/format 展开为 "3D" |
| C10 | Rule.__init__ 读取 spec 的 enabled 键名错位 ⇒ enabled:false 的规则仍被执行 | base.py · Rule.__init__ | 3 | A | test_rule_base.py 断言 `Rule("g.x", {"enabled": False, "actions": []}, mgr).enabled is False` |
| C11 | Rule._dedup_allowed 的 once 分支判据被改坏(execute_once 字面量/返回方向) | base.py · Rule._dedup_allowed | 3 | A | test_rule_base.py 断言 once 已有执行记录时 `_dedup_allowed` 为 False |
| C12 | Rule._dedup_allowed 的 cooldown 边界比较被改坏(<=0→<=1, >0→>1) ⇒ 0<cooldown<=1 的冷却被整段跳过 | base.py · Rule._dedup_allowed | 2 | A | test_rule_base.py 用 `cooldown: "0.5S"` 连跑两次, 断言第二次不执行 |
| C13 | Rule._dedup_allowed 的 `execute_once != "never"` 语义反转 ⇒ never 规则也被去重 | base.py · Rule._dedup_allowed | 1 | A | test_rule_base.py 断言 execute_once="never" 且 cooldown<=0 时即使有记录仍返回 True |
| C14 | Rule.process 的断点续跑起点被改成恒 0 ⇒ 已成功动作被重复执行 | base.py · Rule.process | 1 | A | test_rule_engine.py 手工置 `task.resume_index = 1` 后 process, 断言 actions[0] 未再执行 |
| C15 | AddCategoryAction.execute 建分类时 name=None ⇒ qB 侧留下名为 None 的脏分类 | actions/basic.py · AddCategoryAction.execute | 1 | A | test_actions.py 断言 create_category 收到 `name == "AUTO-A"` |
| C16 | MoveToAction.execute 的 confirm 闸门被置 True ⇒ 规则侧无交互即执行需二次确认的整组迁移 | actions/transfer.py · MoveToAction.execute | 1 | A | test_actions.py 断言 CLS_CONFIRM 形态下 move_to 只回 skip、不建 job |
| C17 | _SpeedLimitAction.execute 的 "upload" 方向判定被改坏 ⇒ 上传限速动作改读 dl_limit 并做错闸门 | actions/transfer.py · _SpeedLimitAction.execute | 2 | A | test_actions.py 用 up_limit=1000/dl_limit=0 的种子跑上传限速, 并对称覆盖下载限速 |
| C18 | FUNC_TABLE 的 expensive=True 被降级/删除 ⇒ 同一 ctx 内昂贵函数被重复取数 | expr/env.py · _build_func_table | 12 | B | test_expr_eval.py 参数化遍历所有 expensive 函数, 断言同一 ctx 内两次调用只触发一次底层取数 |
| C19 | NAME_TABLE 时间类条目的 expensive=True 被降级/删除 ⇒ 同一规则执行内时间取值不固定 | expr/env.py · _build_name_table | 15 | B | test_expr_eval.py 断言求值 sys.hour/minute/time_of_day/dow/dom 后 `ctx.expr_cache` 含对应 ('name', 名字) |
| C20 | _binary 的 `or` 右支求值被改坏(丢 ctx/丢实参/传 None) ⇒ 左假时崩溃而非短路求值 | expr/eval.py · _binary | 7 | B | test_expr_eval.py 断言 `(1 > 2) or (2 > 1)` 为 True 且 `(1 > 2) or (tor.size > 1)` 按 ctx 取真值, 异常类型不为 TypeError |
| C21 | used_names 的集合聚合写错(赋值/交集/传 None) ⇒ Call 实参与 ListLit 元素里的取值名丢失 | expr/env.py · used_names | 6 | B | test_expr_eval.py 断言 `gated_names_in(compile_expr("min(sys.upload_today, 1) > 0")) == ["sys.upload_today"]` 且列表字面量版本同样命中 |
| C22 | _execute_skip_checking 的 origin=getattr(ctx,"task",None) 被改坏 ⇒ 跳检结算后规则任务永不回队 | actions/skip_checking.py · SkipCheckingMixin._execute_skip_checking | 5 | B | test_checking.py 断言 skip_submit 收到的 origin 与 ctx.task 同一对象, 且终态后 task_queue.add_task 被调用 |
| C23 | CheckAction._find_reference 的参考集构造被改坏(成员判据反转/遍历提前 break) | actions/checking.py · CheckAction._find_reference | 3 | B | test_checking.py 用 verified_references={组内X, 组外Y} + refs=[带跳检标签种子, 正常种子], 断言结果只含 X 与正常种子 |
| C24 | sys.downloading_count/seeding_count 的计数谓词被改坏(属性名漂移/谓词丢 None) ⇒ 计数恒 0 或退化成全库计数 | expr/env.py · _build_name_table (_count/_pred_state) | 3 | B | test_expr_eval.py 夹具加一颗 downloading 种子与一颗非 uploading 种子, 断言两个计数分别为精确值 |
| C25 | _skip_on_group_check_failed 的自身/无证据闸门判据被放宽(`h == hash or count <= 0` → and / `< 0`) | actions/full_checking.py · FullCheckingMixin._skip_on_group_check_failed | 2 | B | test_checking.py 断言自身 recheck_fails>0 时返回 None, 兄弟 count==0 时返回 None |
| C26 | _skip_on_group_check_failed 的 `continue` 被改成 `break` ⇒ 循环首轮即中断, 失败推断/自愈遍历被截断 | actions/full_checking.py · FullCheckingMixin._skip_on_group_check_failed | 2 | B | test_checking.py 断言 members 首位为自身/陈旧记录时, 后续真失败同 size 成员仍被判定并返回 skipped |
| C27 | CheckAction._run_custom_check 的 subprocess timeout=600 被去掉 ⇒ 挂死的外部校验程序无限阻塞规则线程 | actions/checking.py · CheckAction._run_custom_check | 2 | B | test_checking.py mock subprocess.run 断言调用 kwargs 含 `timeout=600` |
| C28 | bump_recheck_fail 跨自然日重置时 count 键名被改坏 ⇒ 昨日计数不清零, 当日首次即触上限 | checking_meta.py · bump_recheck_fail | 2 | B | test_checking.py 预置 `{"date": "昨日", "count": 3}` 后 bump, 断言返回 1 |
| C29 | tokenize 的字符集合常量被放宽(引号集/括号集混入字母 X) ⇒ 记号流被改写 | expr/lexer.py · tokenize | 2 | B | test_expr_parse.py 断言 `tokenize("X")` 返回单个 kind=="name" 的 token(不抛、kind 不为 "X") |
| C30 | _age 的年龄算式被改坏(减→加 / added_on and 0) ⇒ 年龄恒错或等于当前时间戳 | expr/env.py · _age | 2 | B | test_expr_eval.py 断言 `tor.age` 与 `now - added_on` 相差 < 5s |
| C31 | Start/Stop.execute 的 group=False 被省略或置 True ⇒ 起停判据从本 hash 扩到全组, 兄弟成员互相误伤 | actions/basic.py · StartAction.execute / StopAction.execute | 4 | B | test_actions.py 让同组另一成员有 own_write, 断言本 hash 的 start/stop 仍下发 |
| C32 | Rule._dedup_allowed 的 cooldown 合取 `and` 被改成 `or` ⇒ 有记录且 cooldown>0 时永不执行 | base.py · Rule._dedup_allowed | 1 | B | test_rule_base.py 断言记录 ts 早于 cooldown 窗口时 `_dedup_allowed` 为 True |
| C33 | _unary 的负号判定被追加 `or True` ⇒ 一元 `+` 变取负 | expr/eval.py · _unary | 1 | B | test_expr_eval.py 断言 `(+tor.ratio) > 0` 与 `tor.ratio > 0` 同值 |
| C34 | _binary 的 `/` 分支被改成乘法 ⇒ 除法静默变乘法 | expr/eval.py · _binary | 1 | B | test_expr_eval.py 断言 `(10 / 4) > 2` 为 True 且 `(10 / 4) > 3` 为 False |
| C35 | _binary 的比较分支边界被改坏(`>`→`>=`, `<` 分支失配/`<=`) ⇒ 相等值上比较结果偏移一格 | expr/eval.py · _binary | 3 | B | test_expr_eval.py 断言两侧相等时 `>` 与 `<` 均为 False |
| C36 | _binary 的 `~` 左值集合化被追加 `and False` ⇒ "任一元素命中"语义退化成整集合字符串匹配 | expr/eval.py · _binary | 1 | B | test_expr_eval.py 断言 tags 含 `HR-x` 时 `tor.tags ~ "regex:^HR"` 为 True |
| C37 | tokenize 的两字符运算符游标 `i += 2` 被改成 `+= 3` ⇒ 紧贴运算符的右操作数被吞 | expr/lexer.py · tokenize | 1 | B | test_expr_parse.py 断言 `tokenize("a<=b")` 恰为 name/op/name/eof 四项 |
| C38 | _read_string 的转义边界 `i + 1 < len(s)` 被改成 `i + 2` ⇒ 末尾转义引号被当收尾 | expr/lexer.py · _read_string | 1 | B | test_expr_parse.py 断言 `tokenize('"a\\"')` 抛「字符串缺少结束引号」 |
| C39 | _level_ex 的一元符号折叠被追加 `or True` ⇒ `+5` 被折叠成 -5 | expr/parser.py · _Parser._level_ex | 1 | B | test_expr_parse.py 断言 `compile_expr("(+5) > 3")` 求值为 True |
| C40 | _in_range 的区间上界 `<` 被改成 `<=` ⇒ 上界值(31 号 / 周日)被排除 | conditions.py · _in_range | 1 | B | test_conditions.py 补 `_in_range(8, "3-8")` 与 `_in_range(31, "1-31")` 的上界断言 |
| C41 | TrackersCondition.match 的 else 分支被 `or True` 短路 ⇒ conf=None 时抛 AttributeError 而非恒不匹配 | conditions.py · TrackersCondition.match | 1 | B | test_conditions.py 断言 conf=None 时 `TrackersCondition("HHan").match(ctx) is False` 且不抛 |
| C42 | SeedtimeCondition.match 的比较符被置 None ⇒ 落到 `left == right` 等值判断 | conditions.py · SeedtimeCondition.match | 1 | B | test_conditions.py 断言 `SeedtimeCondition(">1H").match(ctx) is False`(seeding_time==3600) |
| C43 | FUNC_TABLE 元数据(static 返回类型 / arity / arg_types)整体无守阵, 任一字段被置 None 或 arity 放宽都会让合法函数调用在配置期误拒或 TypeError 崩溃 | expr/env.py · _build_func_table | 40 | C | test_expr_parse.py 表驱动遍历 FUNC_TABLE: 每个函数用正确参数 validate 不抛(不得 TypeError)、用错类型参数抛「参数类型应为」 |
| C44 | NAME_TABLE 条目的 static_type 被置 None ⇒ 配置期 validate 把合法表达式判成类型错 | expr/env.py · _build_name_table | 24 | C | test_expr_parse.py 表驱动遍历 NAME_TABLE 断言每条 `info.type is not None`, 并对 tor./tracker./sys. 各取一条 validate 正例 |
| C45 | NAME_TABLE 条目丢失/键名漂移/取值器坏(tracker.url, sys.hour, sys.minute) ⇒ 该名配置期「未知取值」、运行期取值崩 | expr/env.py · _build_name_table | 17 | C | test_expr_eval.py 用 EXPECTED_NAMES 表驱动断言 `name in NAME_TABLE` 且 `_val(name, ctx)` 非 None |
| C46 | PrintTorrentDetailsAction 各数值字段的 None 兜底条件与格式化算式被改坏 ⇒ 有值显示 "-"、无值崩溃、数值错 | actions/basic.py · PrintTorrentDetailsAction.execute | 11 | C | test_actions.py 对 progress/ratio/seeding_time 各断言两条: 有值精确数值、None 时 ok 且显示 "-" |
| C47 | PrintTorrentDetailsAction 的空值兜底 `x or "-"` 被改成 `and "-"` ⇒ 非空字段恒显示 "-" | actions/basic.py · PrintTorrentDetailsAction.execute | 6 | C | test_actions.py caplog 断言详情行含真实名称/状态/路径/标签/分类, 而非 "-" |
| C48 | sys.up_limit / sys.dl_limit 的名字键或 server_state 源字段名漂移 ⇒ 永远报「未知取值 / 缺失字段」 | expr/env.py · _build_name_table | 6 | C | test_expr_eval.py 给 server_state 补 up/dl_rate_limit 后断言 `_val` 等于该值, 且两个名字在 NAME_TABLE |
| C49 | _jsonable 的浮点/兜底分支被改坏 ⇒ trace 里数值被转成字符串、非原始类型被吞成 "None" | expr/eval.py · _jsonable | 3 | C | test_expr_eval.py 断言 `_jsonable(3.5) == 3.5`、`_jsonable(float("inf")) == "inf"`、`_jsonable({"a": 1}) == "{'a': 1}"` |
| C50 | check_op_types 的同类型放行/混合类型拒收判据被改坏(same_str 置 None / and→or / right==NUM 反转) | expr/types.py · check_op_types | 3 | C | test_expr_parse.py 表驱动断言 `"a" < "b"`、`"a" == "b"` 通过, `1 == "a"` 抛「两侧类型不一致」 |
| C51 | PrintTorrentDetailsAction 的 fmt_size 实参被置 None ⇒ 大小/上传量/下载量恒显示 "-" | actions/basic.py · PrintTorrentDetailsAction.execute | 3 | C | test_actions.py caplog 断言 `大小=` / `上传量=` / `下载量=` 后为非 "-" 值 |
| C52 | static_type 的一元运算类型检查被绕过(op 传 None / 操作数 static_type 传 None) | expr/env.py · static_type | 2 | C | test_expr_parse.py 断言 `validate(compile_expr("-tor.name > 0"))` 抛「操作数必须是数值」、`not tor.size` 抛「操作数必须是布尔」 |
| C53 | trace 的递归遍历被改成 walk(None) ⇒ Call 实参与 ListLit 元素里的取值项从求值轨迹中消失 | expr/eval.py · trace | 2 | C | test_expr_eval.py 断言 `trace(compile_expr("exists(tor.save_path)").root, ctx)` 与列表字面量版本都含内层取值项 |
| C54 | _level_ex 的 `not` 关键字判定失效 ⇒ `not <字面量>` 被折叠成一元符号, 配置期类型检查被绕过 | expr/parser.py · _Parser._level_ex | 2 | C | test_expr_parse.py 断言 `compile_expr("(not 5) > 3")` 抛 ExprSyntaxError |
| C55 | PrintTorrentDetailsAction 的 detail 整行被置 None ⇒ 动作唯一产出只剩 "打印种子详情: None" | actions/basic.py · PrintTorrentDetailsAction.execute | 1 | C | test_actions.py caplog 断言详情行含 "名称=" 且含 "tracker=" |
| C56 | PrintTorrentDetailsAction 的 logger.info 被置 None ⇒ 只读动作变成完全空操作 | actions/basic.py · PrintTorrentDetailsAction.execute | 1 | C | test_actions.py caplog 断言有且仅有一行详情日志 |
| C57 | _server_state 的空 dict 判据 `or` 被改成 `and` ⇒ 数据源为空时不再报「数据源不可用」, 报错指向错方向 | expr/env.py · _server_state | 1 | C | test_expr_eval.py 断言 store.server_state={} 时取 sys.dl_speed 抛「数据源不可用」 |
| C58 | static_type 的 ListLit 元素递归校验被置 None ⇒ 列表内的未知取值/坏调用可过配置期 | expr/env.py · static_type | 1 | C | test_expr_parse.py 断言 `validate(compile_expr("tor.state in [nope]"))` 抛「未知取值」 |
| C59 | check_unary_types 的一元运算符枚举里 "+" 被改坏 ⇒ 一元加号不再做静态检查 | expr/types.py · check_unary_types | 1 | C | test_expr_parse.py 断言 `compile_expr('+"a"')` 抛「操作数必须是数值」 |
| C60 | _build_name_table 的快照过滤 `or` 被改成 `and` ⇒ 内部瞬态字段泄露为可取值名 | expr/env.py · _build_name_table | 1 | C | test_expr_parse.py 断言 `validate(compile_expr('tor.tracker_health_msg ~ "x"'))` 抛 ExprSyntaxError(未知取值) |

## 成员明细

### C01 六个动作类 __init__ 把 ignore_error 第二实参传丢/置 None ⇒ ignore_next_action_error 整体失效

- 文件·函数: actions/basic.py, actions/checking.py, actions/transfer.py · AddTags/RemoveTags/AddCategory/Check/MoveTo/_SpeedLimit.__init__
- 条数 / 档: 18 / A
- 建议守阵: test_actions.py 参数化遍历全部动作类, 断言 `X(spec, True).ignore_error is True`, 并构造 [ignore_next_action_error, 必失败动作, add_tags] 断言后续动作仍执行
- 成员: `xǁAddTagsActionǁ__init____mutmut_3` `xǁAddTagsActionǁ__init____mutmut_4` `xǁAddTagsActionǁ__init____mutmut_5` `xǁRemoveTagsActionǁ__init____mutmut_3` `xǁRemoveTagsActionǁ__init____mutmut_4` `xǁRemoveTagsActionǁ__init____mutmut_5` `xǁAddCategoryActionǁ__init____mutmut_3` `xǁAddCategoryActionǁ__init____mutmut_4` `xǁAddCategoryActionǁ__init____mutmut_5` `xǁCheckActionǁ__init____mutmut_3` `xǁCheckActionǁ__init____mutmut_4` `xǁCheckActionǁ__init____mutmut_5` `auto_qb.rules.actions.transfer.xǁMoveToActionǁ__init____mutmut_3` `auto_qb.rules.actions.transfer.xǁMoveToActionǁ__init____mutmut_4` `auto_qb.rules.actions.transfer.xǁMoveToActionǁ__init____mutmut_5` `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁ__init____mutmut_3` `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁ__init____mutmut_4` `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁ__init____mutmut_5`
- 归并理由: 同一形参在 6 个类里各被 3 种形态改坏(super().__init__(spec, None) / 实参错位 / 丢第二参); 一条参数化断言可全灭。

### C02 动作下发 qB 时 torrent_hashes=ctx.hash 被置 None 或省略 ⇒ 副作用作用域失控(全库/被拒)

- 文件·函数: actions/basic.py, actions/transfer.py · RemoveTags.execute / AddCategory.execute / RemoveCategory.execute / MoveTo.execute / Reannounce.execute / _SpeedLimit.execute
- 条数 / 档: 11 / A
- 建议守阵: test_actions.py 参数化断言各动作的 FakeClient 调用实参 `torrent_hashes == ctx.hash`(非 None)
- 成员: `xǁRemoveTagsActionǁexecute__mutmut_14` `xǁRemoveTagsActionǁexecute__mutmut_16` `xǁAddCategoryActionǁexecute__mutmut_31` `xǁAddCategoryActionǁexecute__mutmut_33` `xǁRemoveCategoryActionǁexecute__mutmut_8` `xǁRemoveCategoryActionǁexecute__mutmut_10` `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_101` `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_103` `auto_qb.rules.actions.transfer.xǁReannounceActionǁexecute__mutmut_21` `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁexecute__mutmut_13` `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁexecute__mutmut_15`
- 归并理由: 5 个动作类、同一 kwarg 的同一改坏形态; 一条参数化断言覆盖。

### C03 Rule._dedup_allowed 的 hourly 分支判据(字符串字面量/日期键/小时键/比较方向/返回)被改坏

- 文件·函数: base.py · Rule._dedup_allowed
- 条数 / 档: 11 / A
- 建议守阵: test_rule_base.py 预置同小时记录断言 `_dedup_allowed` 为 False, 跨小时记录断言为 True
- 成员: `xǁRuleǁ_dedup_allowed__mutmut_43` `xǁRuleǁ_dedup_allowed__mutmut_44` `xǁRuleǁ_dedup_allowed__mutmut_45` `xǁRuleǁ_dedup_allowed__mutmut_46` `xǁRuleǁ_dedup_allowed__mutmut_47` `xǁRuleǁ_dedup_allowed__mutmut_48` `xǁRuleǁ_dedup_allowed__mutmut_50` `xǁRuleǁ_dedup_allowed__mutmut_51` `xǁRuleǁ_dedup_allowed__mutmut_52` `xǁRuleǁ_dedup_allowed__mutmut_53` `xǁRuleǁ_dedup_allowed__mutmut_54`
- 归并理由: 同一条 hourly if 表达式及其两个 rec.get 键; 一对正反断言全灭。

### C04 Rule._dedup_allowed 的 daily 分支判据(execute_once 字面量/date 键/比较方向/and→or/返回)被改坏

- 文件·函数: base.py · Rule._dedup_allowed
- 条数 / 档: 9 / A
- 建议守阵: test_rule_base.py 断言 daily 当天记录 → False、昨日记录 → True(两条即可覆盖全部 9 条)
- 成员: `xǁRuleǁ_dedup_allowed__mutmut_32` `xǁRuleǁ_dedup_allowed__mutmut_33` `xǁRuleǁ_dedup_allowed__mutmut_34` `xǁRuleǁ_dedup_allowed__mutmut_35` `xǁRuleǁ_dedup_allowed__mutmut_36` `xǁRuleǁ_dedup_allowed__mutmut_37` `xǁRuleǁ_dedup_allowed__mutmut_38` `xǁRuleǁ_dedup_allowed__mutmut_39` `xǁRuleǁ_dedup_allowed__mutmut_40`
- 归并理由: 同一条 daily if 表达式; 正反两条断言同时钉死漏执行与重复执行两侧。

### C05 Rule.__init__ 的 ignore_next 状态机(初值/置位/传给 create_action/消费后复位)被改坏 ⇒ 只忽略一次 的契约失效

- 文件·函数: base.py · Rule.__init__
- 条数 / 档: 5 / A
- 建议守阵: test_rule_base.py 用 spec 构造 [fail, action, fail, action] 断言只有紧随标记的第一个动作被忽略, 第二个失败仍中断
- 成员: `xǁRuleǁ__init____mutmut_88` `xǁRuleǁ__init____mutmut_98` `xǁRuleǁ__init____mutmut_109` `xǁRuleǁ__init____mutmut_112` `xǁRuleǁ__init____mutmut_115`
- 归并理由: 同一段 while 循环内的 5 个环节, 一条四步链路断言可全灭。

### C06 AddCategoryAction.__init__ 的 overwrite 开关读取被改坏(置 None/键名错位/大小写)

- 文件·函数: actions/basic.py · AddCategoryAction.__init__
- 条数 / 档: 4 / A
- 建议守阵: test_actions.py 断言 `AddCategoryAction({"format":"X","overwrite":True}).overwrite is True`
- 成员: `xǁAddCategoryActionǁ__init____mutmut_15` `xǁAddCategoryActionǁ__init____mutmut_17` `xǁAddCategoryActionǁ__init____mutmut_21` `xǁAddCategoryActionǁ__init____mutmut_22`

### C07 AddTags/RemoveTags.__init__ 的 `isinstance(spec, list) or True` 恒真 ⇒ 字符串 spec 被 list() 拆成单字符

- 文件·函数: actions/basic.py · AddTagsAction.__init__ / RemoveTagsAction.__init__
- 条数 / 档: 2 / A
- 建议守阵: test_actions.py 断言 `AddTagsAction("TAG").tags == ["TAG"]` 与 `RemoveTagsAction("NOPE").patterns == ["NOPE"]`
- 成员: `xǁAddTagsActionǁ__init____mutmut_8` `xǁRemoveTagsActionǁ__init____mutmut_8`

### C08 AddCategoryAction.__init__ 的 format 兜底默认值被改坏(缺键时产出 "None"/"XXXX" 脏分类名)

- 文件·函数: actions/basic.py · AddCategoryAction.__init__
- 条数 / 档: 3 / A
- 建议守阵: test_actions.py 断言 `AddCategoryAction({}).format == ""`
- 成员: `xǁAddCategoryActionǁ__init____mutmut_9` `xǁAddCategoryActionǁ__init____mutmut_11` `xǁAddCategoryActionǁ__init____mutmut_14`

### C09 replace_vars 的 tracker_conf 实参被置 None ⇒ ${required_seeding_time} 等变量永不展开

- 文件·函数: actions/basic.py · RemoveTagsAction._expand_patterns / AddCategoryAction.execute
- 条数 / 档: 2 / A
- 建议守阵: test_actions.py 断言含 `${required_seeding_time}` 的 pattern/format 展开为 "3D"
- 成员: `xǁRemoveTagsActionǁ_expand_patterns__mutmut_2` `xǁAddCategoryActionǁexecute__mutmut_3`

### C10 Rule.__init__ 读取 spec 的 enabled 键名错位 ⇒ enabled:false 的规则仍被执行

- 文件·函数: base.py · Rule.__init__
- 条数 / 档: 3 / A
- 建议守阵: test_rule_base.py 断言 `Rule("g.x", {"enabled": False, "actions": []}, mgr).enabled is False`
- 成员: `xǁRuleǁ__init____mutmut_6` `xǁRuleǁ__init____mutmut_10` `xǁRuleǁ__init____mutmut_11`

### C11 Rule._dedup_allowed 的 once 分支判据被改坏(execute_once 字面量/返回方向)

- 文件·函数: base.py · Rule._dedup_allowed
- 条数 / 档: 3 / A
- 建议守阵: test_rule_base.py 断言 once 已有执行记录时 `_dedup_allowed` 为 False
- 成员: `xǁRuleǁ_dedup_allowed__mutmut_29` `xǁRuleǁ_dedup_allowed__mutmut_30` `xǁRuleǁ_dedup_allowed__mutmut_31`

### C12 Rule._dedup_allowed 的 cooldown 边界比较被改坏(<=0→<=1, >0→>1) ⇒ 0<cooldown<=1 的冷却被整段跳过

- 文件·函数: base.py · Rule._dedup_allowed
- 条数 / 档: 2 / A
- 建议守阵: test_rule_base.py 用 `cooldown: "0.5S"` 连跑两次, 断言第二次不执行
- 成员: `xǁRuleǁ_dedup_allowed__mutmut_6` `xǁRuleǁ_dedup_allowed__mutmut_17`

### C13 Rule._dedup_allowed 的 `execute_once != "never"` 语义反转 ⇒ never 规则也被去重

- 文件·函数: base.py · Rule._dedup_allowed
- 条数 / 档: 1 / A
- 建议守阵: test_rule_base.py 断言 execute_once="never" 且 cooldown<=0 时即使有记录仍返回 True
- 成员: `xǁRuleǁ_dedup_allowed__mutmut_2`

### C14 Rule.process 的断点续跑起点被改成恒 0 ⇒ 已成功动作被重复执行

- 文件·函数: base.py · Rule.process
- 条数 / 档: 1 / A
- 建议守阵: test_rule_engine.py 手工置 `task.resume_index = 1` 后 process, 断言 actions[0] 未再执行
- 成员: `xǁRuleǁprocess__mutmut_32`

### C15 AddCategoryAction.execute 建分类时 name=None ⇒ qB 侧留下名为 None 的脏分类

- 文件·函数: actions/basic.py · AddCategoryAction.execute
- 条数 / 档: 1 / A
- 建议守阵: test_actions.py 断言 create_category 收到 `name == "AUTO-A"`
- 成员: `xǁAddCategoryActionǁexecute__mutmut_29`

### C16 MoveToAction.execute 的 confirm 闸门被置 True ⇒ 规则侧无交互即执行需二次确认的整组迁移

- 文件·函数: actions/transfer.py · MoveToAction.execute
- 条数 / 档: 1 / A
- 建议守阵: test_actions.py 断言 CLS_CONFIRM 形态下 move_to 只回 skip、不建 job
- 成员: `auto_qb.rules.actions.transfer.xǁMoveToActionǁexecute__mutmut_47`

### C17 _SpeedLimitAction.execute 的 "upload" 方向判定被改坏 ⇒ 上传限速动作改读 dl_limit 并做错闸门

- 文件·函数: actions/transfer.py · _SpeedLimitAction.execute
- 条数 / 档: 2 / A
- 建议守阵: test_actions.py 用 up_limit=1000/dl_limit=0 的种子跑上传限速, 并对称覆盖下载限速
- 成员: `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁexecute__mutmut_2` `auto_qb.rules.actions.transfer.xǁ_SpeedLimitActionǁexecute__mutmut_3`

### C18 FUNC_TABLE 的 expensive=True 被降级/删除 ⇒ 同一 ctx 内昂贵函数被重复取数

- 文件·函数: expr/env.py · _build_func_table
- 条数 / 档: 12 / B
- 建议守阵: test_expr_eval.py 参数化遍历所有 expensive 函数, 断言同一 ctx 内两次调用只触发一次底层取数
- 成员: `auto_qb.rules.expr.env.x__build_func_table__mutmut_29` `auto_qb.rules.expr.env.x__build_func_table__mutmut_36` `auto_qb.rules.expr.env.x__build_func_table__mutmut_41` `auto_qb.rules.expr.env.x__build_func_table__mutmut_50` `auto_qb.rules.expr.env.x__build_func_table__mutmut_57` `auto_qb.rules.expr.env.x__build_func_table__mutmut_62` `auto_qb.rules.expr.env.x__build_func_table__mutmut_71` `auto_qb.rules.expr.env.x__build_func_table__mutmut_78` `auto_qb.rules.expr.env.x__build_func_table__mutmut_83` `auto_qb.rules.expr.env.x__build_func_table__mutmut_92` `auto_qb.rules.expr.env.x__build_func_table__mutmut_99` `auto_qb.rules.expr.env.x__build_func_table__mutmut_104`

### C19 NAME_TABLE 时间类条目的 expensive=True 被降级/删除 ⇒ 同一规则执行内时间取值不固定

- 文件·函数: expr/env.py · _build_name_table
- 条数 / 档: 15 / B
- 建议守阵: test_expr_eval.py 断言求值 sys.hour/minute/time_of_day/dow/dom 后 `ctx.expr_cache` 含对应 ('name', 名字)
- 成员: `auto_qb.rules.expr.env.x__build_name_table__mutmut_254` `auto_qb.rules.expr.env.x__build_name_table__mutmut_258` `auto_qb.rules.expr.env.x__build_name_table__mutmut_262` `auto_qb.rules.expr.env.x__build_name_table__mutmut_269` `auto_qb.rules.expr.env.x__build_name_table__mutmut_273` `auto_qb.rules.expr.env.x__build_name_table__mutmut_277` `auto_qb.rules.expr.env.x__build_name_table__mutmut_284` `auto_qb.rules.expr.env.x__build_name_table__mutmut_288` `auto_qb.rules.expr.env.x__build_name_table__mutmut_295` `auto_qb.rules.expr.env.x__build_name_table__mutmut_302` `auto_qb.rules.expr.env.x__build_name_table__mutmut_306` `auto_qb.rules.expr.env.x__build_name_table__mutmut_310` `auto_qb.rules.expr.env.x__build_name_table__mutmut_317` `auto_qb.rules.expr.env.x__build_name_table__mutmut_321` `auto_qb.rules.expr.env.x__build_name_table__mutmut_325`

### C20 _binary 的 `or` 右支求值被改坏(丢 ctx/丢实参/传 None) ⇒ 左假时崩溃而非短路求值

- 文件·函数: expr/eval.py · _binary
- 条数 / 档: 7 / B
- 建议守阵: test_expr_eval.py 断言 `(1 > 2) or (2 > 1)` 为 True 且 `(1 > 2) or (tor.size > 1)` 按 ctx 取真值, 异常类型不为 TypeError
- 成员: `_binary__mutmut_34` `_binary__mutmut_36` `_binary__mutmut_37` `_binary__mutmut_38` `_binary__mutmut_39` `_binary__mutmut_40` `_binary__mutmut_41`

### C21 used_names 的集合聚合写错(赋值/交集/传 None) ⇒ Call 实参与 ListLit 元素里的取值名丢失

- 文件·函数: expr/env.py · used_names
- 条数 / 档: 6 / B
- 建议守阵: test_expr_eval.py 断言 `gated_names_in(compile_expr("min(sys.upload_today, 1) > 0")) == ["sys.upload_today"]` 且列表字面量版本同样命中
- 成员: `auto_qb.rules.expr.env.x_used_names__mutmut_11` `auto_qb.rules.expr.env.x_used_names__mutmut_12` `auto_qb.rules.expr.env.x_used_names__mutmut_13` `auto_qb.rules.expr.env.x_used_names__mutmut_14` `auto_qb.rules.expr.env.x_used_names__mutmut_15` `auto_qb.rules.expr.env.x_used_names__mutmut_16`

### C22 _execute_skip_checking 的 origin=getattr(ctx,"task",None) 被改坏 ⇒ 跳检结算后规则任务永不回队

- 文件·函数: actions/skip_checking.py · SkipCheckingMixin._execute_skip_checking
- 条数 / 档: 5 / B
- 建议守阵: test_checking.py 断言 skip_submit 收到的 origin 与 ctx.task 同一对象, 且终态后 task_queue.add_task 被调用
- 成员: `auto_qb.rules.actions.skip_checking.xǁSkipCheckingMixinǁ_execute_skip_checking__mutmut_5` `auto_qb.rules.actions.skip_checking.xǁSkipCheckingMixinǁ_execute_skip_checking__mutmut_10` `auto_qb.rules.actions.skip_checking.xǁSkipCheckingMixinǁ_execute_skip_checking__mutmut_15` `auto_qb.rules.actions.skip_checking.xǁSkipCheckingMixinǁ_execute_skip_checking__mutmut_20` `auto_qb.rules.actions.skip_checking.xǁSkipCheckingMixinǁ_execute_skip_checking__mutmut_21`

### C23 CheckAction._find_reference 的参考集构造被改坏(成员判据反转/遍历提前 break)

- 文件·函数: actions/checking.py · CheckAction._find_reference
- 条数 / 档: 3 / B
- 建议守阵: test_checking.py 用 verified_references={组内X, 组外Y} + refs=[带跳检标签种子, 正常种子], 断言结果只含 X 与正常种子
- 成员: `xǁCheckActionǁ_find_reference__mutmut_43` `xǁCheckActionǁ_find_reference__mutmut_45` `xǁCheckActionǁ_find_reference__mutmut_53`

### C24 sys.downloading_count/seeding_count 的计数谓词被改坏(属性名漂移/谓词丢 None) ⇒ 计数恒 0 或退化成全库计数

- 文件·函数: expr/env.py · _build_name_table (_count/_pred_state)
- 条数 / 档: 3 / B
- 建议守阵: test_expr_eval.py 夹具加一颗 downloading 种子与一颗非 uploading 种子, 断言两个计数分别为精确值
- 成员: `auto_qb.rules.expr.env.x__build_name_table__mutmut_352` `auto_qb.rules.expr.env.x__build_name_table__mutmut_353` `auto_qb.rules.expr.env.x__build_name_table__mutmut_368`

### C25 _skip_on_group_check_failed 的自身/无证据闸门判据被放宽(`h == hash or count <= 0` → and / `< 0`)

- 文件·函数: actions/full_checking.py · FullCheckingMixin._skip_on_group_check_failed
- 条数 / 档: 2 / B
- 建议守阵: test_checking.py 断言自身 recheck_fails>0 时返回 None, 兄弟 count==0 时返回 None
- 成员: `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_14` `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_20`

### C26 _skip_on_group_check_failed 的 `continue` 被改成 `break` ⇒ 循环首轮即中断, 失败推断/自愈遍历被截断

- 文件·函数: actions/full_checking.py · FullCheckingMixin._skip_on_group_check_failed
- 条数 / 档: 2 / B
- 建议守阵: test_checking.py 断言 members 首位为自身/陈旧记录时, 后续真失败同 size 成员仍被判定并返回 skipped
- 成员: `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_22` `xǁFullCheckingMixinǁ_skip_on_group_check_failed__mutmut_38`

### C27 CheckAction._run_custom_check 的 subprocess timeout=600 被去掉 ⇒ 挂死的外部校验程序无限阻塞规则线程

- 文件·函数: actions/checking.py · CheckAction._run_custom_check
- 条数 / 档: 2 / B
- 建议守阵: test_checking.py mock subprocess.run 断言调用 kwargs 含 `timeout=600`
- 成员: `xǁCheckActionǁ_run_custom_check__mutmut_5` `xǁCheckActionǁ_run_custom_check__mutmut_9`

### C28 bump_recheck_fail 跨自然日重置时 count 键名被改坏 ⇒ 昨日计数不清零, 当日首次即触上限

- 文件·函数: checking_meta.py · bump_recheck_fail
- 条数 / 档: 2 / B
- 建议守阵: test_checking.py 预置 `{"date": "昨日", "count": 3}` 后 bump, 断言返回 1
- 成员: `x_bump_recheck_fail__mutmut_28` `x_bump_recheck_fail__mutmut_29`

### C29 tokenize 的字符集合常量被放宽(引号集/括号集混入字母 X) ⇒ 记号流被改写

- 文件·函数: expr/lexer.py · tokenize
- 条数 / 档: 2 / B
- 建议守阵: test_expr_parse.py 断言 `tokenize("X")` 返回单个 kind=="name" 的 token(不抛、kind 不为 "X")
- 成员: `auto_qb.rules.expr.lexer.x_tokenize__mutmut_19` `auto_qb.rules.expr.lexer.x_tokenize__mutmut_45`

### C30 _age 的年龄算式被改坏(减→加 / added_on and 0) ⇒ 年龄恒错或等于当前时间戳

- 文件·函数: expr/env.py · _age
- 条数 / 档: 2 / B
- 建议守阵: test_expr_eval.py 断言 `tor.age` 与 `now - added_on` 相差 < 5s
- 成员: `auto_qb.rules.expr.env.x__age__mutmut_1` `auto_qb.rules.expr.env.x__age__mutmut_2`

### C31 Start/Stop.execute 的 group=False 被省略或置 True ⇒ 起停判据从本 hash 扩到全组, 兄弟成员互相误伤

- 文件·函数: actions/basic.py · StartAction.execute / StopAction.execute
- 条数 / 档: 4 / B
- 建议守阵: test_actions.py 让同组另一成员有 own_write, 断言本 hash 的 start/stop 仍下发
- 成员: `xǁStartActionǁexecute__mutmut_10` `xǁStartActionǁexecute__mutmut_11` `xǁStopActionǁexecute__mutmut_9` `xǁStopActionǁexecute__mutmut_10`

### C32 Rule._dedup_allowed 的 cooldown 合取 `and` 被改成 `or` ⇒ 有记录且 cooldown>0 时永不执行

- 文件·函数: base.py · Rule._dedup_allowed
- 条数 / 档: 1 / B
- 建议守阵: test_rule_base.py 断言记录 ts 早于 cooldown 窗口时 `_dedup_allowed` 为 True
- 成员: `xǁRuleǁ_dedup_allowed__mutmut_15`

### C33 _unary 的负号判定被追加 `or True` ⇒ 一元 `+` 变取负

- 文件·函数: expr/eval.py · _unary
- 条数 / 档: 1 / B
- 建议守阵: test_expr_eval.py 断言 `(+tor.ratio) > 0` 与 `tor.ratio > 0` 同值
- 成员: `_unary__mutmut_17`

### C34 _binary 的 `/` 分支被改成乘法 ⇒ 除法静默变乘法

- 文件·函数: expr/eval.py · _binary
- 条数 / 档: 1 / B
- 建议守阵: test_expr_eval.py 断言 `(10 / 4) > 2` 为 True 且 `(10 / 4) > 3` 为 False
- 成员: `_binary__mutmut_79`

### C35 _binary 的比较分支边界被改坏(`>`→`>=`, `<` 分支失配/`<=`) ⇒ 相等值上比较结果偏移一格

- 文件·函数: expr/eval.py · _binary
- 条数 / 档: 3 / B
- 建议守阵: test_expr_eval.py 断言两侧相等时 `>` 与 `<` 均为 False
- 成员: `_binary__mutmut_93` `_binary__mutmut_95` `_binary__mutmut_96`

### C36 _binary 的 `~` 左值集合化被追加 `and False` ⇒ "任一元素命中"语义退化成整集合字符串匹配

- 文件·函数: expr/eval.py · _binary
- 条数 / 档: 1 / B
- 建议守阵: test_expr_eval.py 断言 tags 含 `HR-x` 时 `tor.tags ~ "regex:^HR"` 为 True
- 成员: `_binary__mutmut_132`

### C37 tokenize 的两字符运算符游标 `i += 2` 被改成 `+= 3` ⇒ 紧贴运算符的右操作数被吞

- 文件·函数: expr/lexer.py · tokenize
- 条数 / 档: 1 / B
- 建议守阵: test_expr_parse.py 断言 `tokenize("a<=b")` 恰为 name/op/name/eof 四项
- 成员: `auto_qb.rules.expr.lexer.x_tokenize__mutmut_79`

### C38 _read_string 的转义边界 `i + 1 < len(s)` 被改成 `i + 2` ⇒ 末尾转义引号被当收尾

- 文件·函数: expr/lexer.py · _read_string
- 条数 / 档: 1 / B
- 建议守阵: test_expr_parse.py 断言 `tokenize('"a\\"')` 抛「字符串缺少结束引号」
- 成员: `auto_qb.rules.expr.lexer.x__read_string__mutmut_13`

### C39 _level_ex 的一元符号折叠被追加 `or True` ⇒ `+5` 被折叠成 -5

- 文件·函数: expr/parser.py · _Parser._level_ex
- 条数 / 档: 1 / B
- 建议守阵: test_expr_parse.py 断言 `compile_expr("(+5) > 3")` 求值为 True
- 成员: `_Parser._level_ex__mutmut_25`

### C40 _in_range 的区间上界 `<` 被改成 `<=` ⇒ 上界值(31 号 / 周日)被排除

- 文件·函数: conditions.py · _in_range
- 条数 / 档: 1 / B
- 建议守阵: test_conditions.py 补 `_in_range(8, "3-8")` 与 `_in_range(31, "1-31")` 的上界断言
- 成员: `auto_qb.rules.conditions.x__in_range__mutmut_15`

### C41 TrackersCondition.match 的 else 分支被 `or True` 短路 ⇒ conf=None 时抛 AttributeError 而非恒不匹配

- 文件·函数: conditions.py · TrackersCondition.match
- 条数 / 档: 1 / B
- 建议守阵: test_conditions.py 断言 conf=None 时 `TrackersCondition("HHan").match(ctx) is False` 且不抛
- 成员: `auto_qb.rules.conditions.xǁTrackersConditionǁmatch__mutmut_4`

### C42 SeedtimeCondition.match 的比较符被置 None ⇒ 落到 `left == right` 等值判断

- 文件·函数: conditions.py · SeedtimeCondition.match
- 条数 / 档: 1 / B
- 建议守阵: test_conditions.py 断言 `SeedtimeCondition(">1H").match(ctx) is False`(seeding_time==3600)
- 成员: `auto_qb.rules.conditions.xǁSeedtimeConditionǁmatch__mutmut_1`

### C43 FUNC_TABLE 元数据(static 返回类型 / arity / arg_types)整体无守阵, 任一字段被置 None 或 arity 放宽都会让合法函数调用在配置期误拒或 TypeError 崩溃

- 文件·函数: expr/env.py · _build_func_table
- 条数 / 档: 40 / C
- 建议守阵: test_expr_parse.py 表驱动遍历 FUNC_TABLE: 每个函数用正确参数 validate 不抛(不得 TypeError)、用错类型参数抛「参数类型应为」
- 成员: `auto_qb.rules.expr.env.x__build_func_table__mutmut_4` `auto_qb.rules.expr.env.x__build_func_table__mutmut_6` `auto_qb.rules.expr.env.x__build_func_table__mutmut_19` `auto_qb.rules.expr.env.x__build_func_table__mutmut_25` `auto_qb.rules.expr.env.x__build_func_table__mutmut_26` `auto_qb.rules.expr.env.x__build_func_table__mutmut_27` `auto_qb.rules.expr.env.x__build_func_table__mutmut_40` `auto_qb.rules.expr.env.x__build_func_table__mutmut_46` `auto_qb.rules.expr.env.x__build_func_table__mutmut_47` `auto_qb.rules.expr.env.x__build_func_table__mutmut_48` `auto_qb.rules.expr.env.x__build_func_table__mutmut_61` `auto_qb.rules.expr.env.x__build_func_table__mutmut_67` `auto_qb.rules.expr.env.x__build_func_table__mutmut_68` `auto_qb.rules.expr.env.x__build_func_table__mutmut_69` `auto_qb.rules.expr.env.x__build_func_table__mutmut_82` `auto_qb.rules.expr.env.x__build_func_table__mutmut_88` `auto_qb.rules.expr.env.x__build_func_table__mutmut_89` `auto_qb.rules.expr.env.x__build_func_table__mutmut_90` `auto_qb.rules.expr.env.x__build_func_table__mutmut_103` `auto_qb.rules.expr.env.x__build_func_table__mutmut_144` `auto_qb.rules.expr.env.x__build_func_table__mutmut_160` `auto_qb.rules.expr.env.x__build_func_table__mutmut_161` `auto_qb.rules.expr.env.x__build_func_table__mutmut_162` `auto_qb.rules.expr.env.x__build_func_table__mutmut_171` `auto_qb.rules.expr.env.x__build_func_table__mutmut_176` `auto_qb.rules.expr.env.x__build_func_table__mutmut_177` `auto_qb.rules.expr.env.x__build_func_table__mutmut_178` `auto_qb.rules.expr.env.x__build_func_table__mutmut_187` `auto_qb.rules.expr.env.x__build_func_table__mutmut_192` `auto_qb.rules.expr.env.x__build_func_table__mutmut_193` `auto_qb.rules.expr.env.x__build_func_table__mutmut_194` `auto_qb.rules.expr.env.x__build_func_table__mutmut_203` `auto_qb.rules.expr.env.x__build_func_table__mutmut_208` `auto_qb.rules.expr.env.x__build_func_table__mutmut_209` `auto_qb.rules.expr.env.x__build_func_table__mutmut_210` `auto_qb.rules.expr.env.x__build_func_table__mutmut_219` `auto_qb.rules.expr.env.x__build_func_table__mutmut_227` `auto_qb.rules.expr.env.x__build_func_table__mutmut_228` `auto_qb.rules.expr.env.x__build_func_table__mutmut_229` `auto_qb.rules.expr.env.x__build_func_table__mutmut_238`
- 归并理由: 类型置 None 11 条、arity 置 None 9 条、arg_types 置 None 10 条、arity 放宽 10 条; 一条表驱动用例全灭。

### C44 NAME_TABLE 条目的 static_type 被置 None ⇒ 配置期 validate 把合法表达式判成类型错

- 文件·函数: expr/env.py · _build_name_table
- 条数 / 档: 24 / C
- 建议守阵: test_expr_parse.py 表驱动遍历 NAME_TABLE 断言每条 `info.type is not None`, 并对 tor./tracker./sys. 各取一条 validate 正例
- 成员: `auto_qb.rules.expr.env.x__build_name_table__mutmut_44` `auto_qb.rules.expr.env.x__build_name_table__mutmut_59` `auto_qb.rules.expr.env.x__build_name_table__mutmut_72` `auto_qb.rules.expr.env.x__build_name_table__mutmut_86` `auto_qb.rules.expr.env.x__build_name_table__mutmut_98` `auto_qb.rules.expr.env.x__build_name_table__mutmut_112` `auto_qb.rules.expr.env.x__build_name_table__mutmut_126` `auto_qb.rules.expr.env.x__build_name_table__mutmut_140` `auto_qb.rules.expr.env.x__build_name_table__mutmut_151` `auto_qb.rules.expr.env.x__build_name_table__mutmut_162` `auto_qb.rules.expr.env.x__build_name_table__mutmut_185` `auto_qb.rules.expr.env.x__build_name_table__mutmut_204` `auto_qb.rules.expr.env.x__build_name_table__mutmut_223` `auto_qb.rules.expr.env.x__build_name_table__mutmut_237` `auto_qb.rules.expr.env.x__build_name_table__mutmut_252` `auto_qb.rules.expr.env.x__build_name_table__mutmut_267` `auto_qb.rules.expr.env.x__build_name_table__mutmut_282` `auto_qb.rules.expr.env.x__build_name_table__mutmut_300` `auto_qb.rules.expr.env.x__build_name_table__mutmut_315` `auto_qb.rules.expr.env.x__build_name_table__mutmut_330` `auto_qb.rules.expr.env.x__build_name_table__mutmut_341` `auto_qb.rules.expr.env.x__build_name_table__mutmut_359` `auto_qb.rules.expr.env.x__build_name_table__mutmut_402` `auto_qb.rules.expr.env.x__build_name_table__mutmut_427`

### C45 NAME_TABLE 条目丢失/键名漂移/取值器坏(tracker.url, sys.hour, sys.minute) ⇒ 该名配置期「未知取值」、运行期取值崩

- 文件·函数: expr/env.py · _build_name_table
- 条数 / 档: 17 / C
- 建议守阵: test_expr_eval.py 用 EXPECTED_NAMES 表驱动断言 `name in NAME_TABLE` 且 `_val(name, ctx)` 非 None
- 成员: `auto_qb.rules.expr.env.x__build_name_table__mutmut_219` `auto_qb.rules.expr.env.x__build_name_table__mutmut_220` `auto_qb.rules.expr.env.x__build_name_table__mutmut_221` `auto_qb.rules.expr.env.x__build_name_table__mutmut_224` `auto_qb.rules.expr.env.x__build_name_table__mutmut_230` `auto_qb.rules.expr.env.x__build_name_table__mutmut_231` `auto_qb.rules.expr.env.x__build_name_table__mutmut_232` `auto_qb.rules.expr.env.x__build_name_table__mutmut_248` `auto_qb.rules.expr.env.x__build_name_table__mutmut_249` `auto_qb.rules.expr.env.x__build_name_table__mutmut_250` `auto_qb.rules.expr.env.x__build_name_table__mutmut_253` `auto_qb.rules.expr.env.x__build_name_table__mutmut_261` `auto_qb.rules.expr.env.x__build_name_table__mutmut_263` `auto_qb.rules.expr.env.x__build_name_table__mutmut_264` `auto_qb.rules.expr.env.x__build_name_table__mutmut_265` `auto_qb.rules.expr.env.x__build_name_table__mutmut_268` `auto_qb.rules.expr.env.x__build_name_table__mutmut_276`

### C46 PrintTorrentDetailsAction 各数值字段的 None 兜底条件与格式化算式被改坏 ⇒ 有值显示 "-"、无值崩溃、数值错

- 文件·函数: actions/basic.py · PrintTorrentDetailsAction.execute
- 条数 / 档: 11 / C
- 建议守阵: test_actions.py 对 progress/ratio/seeding_time 各断言两条: 有值精确数值、None 时 ok 且显示 "-"
- 成员: `xǁPrintTorrentDetailsActionǁexecute__mutmut_21` `xǁPrintTorrentDetailsActionǁexecute__mutmut_22` `xǁPrintTorrentDetailsActionǁexecute__mutmut_23` `xǁPrintTorrentDetailsActionǁexecute__mutmut_24` `xǁPrintTorrentDetailsActionǁexecute__mutmut_25` `xǁPrintTorrentDetailsActionǁexecute__mutmut_32` `xǁPrintTorrentDetailsActionǁexecute__mutmut_33` `xǁPrintTorrentDetailsActionǁexecute__mutmut_34` `xǁPrintTorrentDetailsActionǁexecute__mutmut_37` `xǁPrintTorrentDetailsActionǁexecute__mutmut_38` `xǁPrintTorrentDetailsActionǁexecute__mutmut_40`

### C47 PrintTorrentDetailsAction 的空值兜底 `x or "-"` 被改成 `and "-"` ⇒ 非空字段恒显示 "-"

- 文件·函数: actions/basic.py · PrintTorrentDetailsAction.execute
- 条数 / 档: 6 / C
- 建议守阵: test_actions.py caplog 断言详情行含真实名称/状态/路径/标签/分类, 而非 "-"
- 成员: `xǁPrintTorrentDetailsActionǁexecute__mutmut_7` `xǁPrintTorrentDetailsActionǁexecute__mutmut_10` `xǁPrintTorrentDetailsActionǁexecute__mutmut_13` `xǁPrintTorrentDetailsActionǁexecute__mutmut_16` `xǁPrintTorrentDetailsActionǁexecute__mutmut_43` `xǁPrintTorrentDetailsActionǁexecute__mutmut_46`

### C48 sys.up_limit / sys.dl_limit 的名字键或 server_state 源字段名漂移 ⇒ 永远报「未知取值 / 缺失字段」

- 文件·函数: expr/env.py · _build_name_table
- 条数 / 档: 6 / C
- 建议守阵: test_expr_eval.py 给 server_state 补 up/dl_rate_limit 后断言 `_val` 等于该值, 且两个名字在 NAME_TABLE
- 成员: `auto_qb.rules.expr.env.x__build_name_table__mutmut_458` `auto_qb.rules.expr.env.x__build_name_table__mutmut_459` `auto_qb.rules.expr.env.x__build_name_table__mutmut_460` `auto_qb.rules.expr.env.x__build_name_table__mutmut_461` `auto_qb.rules.expr.env.x__build_name_table__mutmut_462` `auto_qb.rules.expr.env.x__build_name_table__mutmut_463`

### C49 _jsonable 的浮点/兜底分支被改坏 ⇒ trace 里数值被转成字符串、非原始类型被吞成 "None"

- 文件·函数: expr/eval.py · _jsonable
- 条数 / 档: 3 / C
- 建议守阵: test_expr_eval.py 断言 `_jsonable(3.5) == 3.5`、`_jsonable(float("inf")) == "inf"`、`_jsonable({"a": 1}) == "{'a': 1}"`
- 成员: `x__jsonable__mutmut_2` `x__jsonable__mutmut_8` `x__jsonable__mutmut_12`

### C50 check_op_types 的同类型放行/混合类型拒收判据被改坏(same_str 置 None / and→or / right==NUM 反转)

- 文件·函数: expr/types.py · check_op_types
- 条数 / 档: 3 / C
- 建议守阵: test_expr_parse.py 表驱动断言 `"a" < "b"`、`"a" == "b"` 通过, `1 == "a"` 抛「两侧类型不一致」
- 成员: `auto_qb.rules.expr.types.x_check_op_types__mutmut_14` `auto_qb.rules.expr.types.x_check_op_types__mutmut_24` `auto_qb.rules.expr.types.x_check_op_types__mutmut_29`

### C51 PrintTorrentDetailsAction 的 fmt_size 实参被置 None ⇒ 大小/上传量/下载量恒显示 "-"

- 文件·函数: actions/basic.py · PrintTorrentDetailsAction.execute
- 条数 / 档: 3 / C
- 建议守阵: test_actions.py caplog 断言 `大小=` / `上传量=` / `下载量=` 后为非 "-" 值
- 成员: `xǁPrintTorrentDetailsActionǁexecute__mutmut_19` `xǁPrintTorrentDetailsActionǁexecute__mutmut_28` `xǁPrintTorrentDetailsActionǁexecute__mutmut_30`

### C52 static_type 的一元运算类型检查被绕过(op 传 None / 操作数 static_type 传 None)

- 文件·函数: expr/env.py · static_type
- 条数 / 档: 2 / C
- 建议守阵: test_expr_parse.py 断言 `validate(compile_expr("-tor.name > 0"))` 抛「操作数必须是数值」、`not tor.size` 抛「操作数必须是布尔」
- 成员: `auto_qb.rules.expr.env.x_static_type__mutmut_43` `auto_qb.rules.expr.env.x_static_type__mutmut_47`

### C53 trace 的递归遍历被改成 walk(None) ⇒ Call 实参与 ListLit 元素里的取值项从求值轨迹中消失

- 文件·函数: expr/eval.py · trace
- 条数 / 档: 2 / C
- 建议守阵: test_expr_eval.py 断言 `trace(compile_expr("exists(tor.save_path)").root, ctx)` 与列表字面量版本都含内层取值项
- 成员: `x_trace__mutmut_30` `x_trace__mutmut_34`

### C54 _level_ex 的 `not` 关键字判定失效 ⇒ `not <字面量>` 被折叠成一元符号, 配置期类型检查被绕过

- 文件·函数: expr/parser.py · _Parser._level_ex
- 条数 / 档: 2 / C
- 建议守阵: test_expr_parse.py 断言 `compile_expr("(not 5) > 3")` 抛 ExprSyntaxError
- 成员: `_Parser._level_ex__mutmut_10` `_Parser._level_ex__mutmut_11`

### C55 PrintTorrentDetailsAction 的 detail 整行被置 None ⇒ 动作唯一产出只剩 "打印种子详情: None"

- 文件·函数: actions/basic.py · PrintTorrentDetailsAction.execute
- 条数 / 档: 1 / C
- 建议守阵: test_actions.py caplog 断言详情行含 "名称=" 且含 "tracker="
- 成员: `xǁPrintTorrentDetailsActionǁexecute__mutmut_50`

### C56 PrintTorrentDetailsAction 的 logger.info 被置 None ⇒ 只读动作变成完全空操作

- 文件·函数: actions/basic.py · PrintTorrentDetailsAction.execute
- 条数 / 档: 1 / C
- 建议守阵: test_actions.py caplog 断言有且仅有一行详情日志
- 成员: `xǁPrintTorrentDetailsActionǁexecute__mutmut_53`

### C57 _server_state 的空 dict 判据 `or` 被改成 `and` ⇒ 数据源为空时不再报「数据源不可用」, 报错指向错方向

- 文件·函数: expr/env.py · _server_state
- 条数 / 档: 1 / C
- 建议守阵: test_expr_eval.py 断言 store.server_state={} 时取 sys.dl_speed 抛「数据源不可用」
- 成员: `auto_qb.rules.expr.env.x__server_state__mutmut_20`

### C58 static_type 的 ListLit 元素递归校验被置 None ⇒ 列表内的未知取值/坏调用可过配置期

- 文件·函数: expr/env.py · static_type
- 条数 / 档: 1 / C
- 建议守阵: test_expr_parse.py 断言 `validate(compile_expr("tor.state in [nope]"))` 抛「未知取值」
- 成员: `auto_qb.rules.expr.env.x_static_type__mutmut_42`

### C59 check_unary_types 的一元运算符枚举里 "+" 被改坏 ⇒ 一元加号不再做静态检查

- 文件·函数: expr/types.py · check_unary_types
- 条数 / 档: 1 / C
- 建议守阵: test_expr_parse.py 断言 `compile_expr('+"a"')` 抛「操作数必须是数值」
- 成员: `auto_qb.rules.expr.types.x_check_unary_types__mutmut_10`

### C60 _build_name_table 的快照过滤 `or` 被改成 `and` ⇒ 内部瞬态字段泄露为可取值名

- 文件·函数: expr/env.py · _build_name_table
- 条数 / 档: 1 / C
- 建议守阵: test_expr_parse.py 断言 `validate(compile_expr('tor.tracker_health_msg ~ "x"'))` 抛 ExprSyntaxError(未知取值)
- 成员: `auto_qb.rules.expr.env.x__build_name_table__mutmut_3`
