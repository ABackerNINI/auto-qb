# 分类: src/auto_qb/rules/expr/env.py · 运行时函数(169 条)

- 来源分片: `R:/Temp/auto-qb/mutants/chunks/rules__expr__env__D_rest.txt`
- 计数: 169 条 = 真洞 12 / 等价 57 / 假存活 100

> **判据**: 本片全在运行时闭包/求值函数上(非 import 期建表), 读 diff 即可定行为。凡「池内或池外任一既有用例会变红」的记**假存活**(含 mutmut 未杀的工具漏报, 理由里点到具体用例); 「改坏后无人读/无可达输入」的记**等价**; 「行为确变且 16 文件池内外都无守阵」的记**真洞**并给守阵断言。池 = 计划 26-10-30-0049 §3.2 的 16 文件(test_expr_eval/test_expr_parse/test_conditions/test_state_matrix 等)。

| # | 变异 id | 函数 | 变异形态 | 判定 | 理由 |
|---|---|---|---|---|---|
| 1 | `auto_qb.rules.expr.env.x__attr__mutmut_1` | _attr | getattr(ctx.torrent, name) → getattr(None, name) | 假存活 | 取 torrent 换成 None: 每个快照名取值抛 AttributeError; 池内 test_seed_fields(:110) 直接取 tor.size/tor.name ⇒ 池内可杀 |
| 2 | `auto_qb.rules.expr.env.x__attr__mutmut_2` | _attr | → getattr(ctx.torrent, None) | 假存活 | 属性名置 None: getattr 抛 TypeError; 同 test_seed_fields(:110) ⇒ 池内可杀 |
| 3 | `auto_qb.rules.expr.env.x__attr__mutmut_3` | _attr | → getattr(name)(丢对象参数) | 假存活 | 单参 getattr 缺对象 ⇒ TypeError; 同 test_seed_fields(:110) ⇒ 池内可杀 |
| 4 | `auto_qb.rules.expr.env.x__attr__mutmut_4` | _attr | → getattr(ctx.torrent, )(丢属性名) | 假存活 | 缺属性名 ⇒ TypeError; 同 test_seed_fields(:110) ⇒ 池内可杀 |
| 5 | `auto_qb.rules.expr.env.x__state__mutmut_1` | _state | enum = ctx.torrent.state_enum → None | 假存活 | enum 恒 None ⇒ 七个 tor.is_* 全 False; test_seed_fields(:114) 断言 is_uploading True ⇒ 池内可杀 |
| 6 | `auto_qb.rules.expr.env.x__state__mutmut_2` | _state | 条件追加 and False | 假存活 | 条件恒假 ⇒ 恒 False; 同 test_seed_fields(:114) ⇒ 池内可杀 |
| 7 | `auto_qb.rules.expr.env.x__state__mutmut_3` | _state | 条件改 or True | 等价 | 条件恒真 ⇒ 恒走取值支; enum 为 None 时 getattr(None, attr, False) 亦为 False, 两支与原式逐值相同 ⇒ 语义不可区分 |
| 8 | `auto_qb.rules.expr.env.x__state__mutmut_4` | _state | 取值表达式 → bool(None) | 假存活 | 恒 False; test_seed_fields(:114) 断言 is_uploading True ⇒ 池内可杀 |
| 9 | `auto_qb.rules.expr.env.x__state__mutmut_5` | _state | getattr(enum, …) → getattr(None, …) | 假存活 | 缺省 False 兜住 ⇒ 恒 False; 同 test_seed_fields(:114) ⇒ 池内可杀 |
| 10 | `auto_qb.rules.expr.env.x__state__mutmut_6` | _state | 属性名 attr → None | 假存活 | getattr 属性名非字符串 ⇒ TypeError; 同 test_seed_fields(:114) ⇒ 池内可杀 |
| 11 | `auto_qb.rules.expr.env.x__state__mutmut_7` | _state | getattr 缺省 False → None | 等价 | STATE_ATTRS 七个 is_* 在 TorrentState 上恒存在(record.py:243 兜底 UNKNOWN), 缺省分支不可达 ⇒ 等价 |
| 12 | `auto_qb.rules.expr.env.x__state__mutmut_8` | _state | → getattr(attr, False)(字符串当对象) | 假存活 | TypeError: attribute name must be string; 同 test_seed_fields(:114) ⇒ 池内可杀 |
| 13 | `auto_qb.rules.expr.env.x__state__mutmut_9` | _state | → getattr(enum, False)(属性名是 bool) | 假存活 | TypeError; 同 test_seed_fields(:114) ⇒ 池内可杀 |
| 14 | `auto_qb.rules.expr.env.x__state__mutmut_10` | _state | 缺省实参删成尾逗号 | 等价 | getattr(enum, attr, ) 与三参调用同义(尾逗号不产生实参) ⇒ 逐字同 |
| 15 | `auto_qb.rules.expr.env.x__state__mutmut_11` | _state | getattr 缺省 False → True | 等价 | 缺省分支不可达(属性恒存在); 即便到达也仅影响不存在的属性 ⇒ 等价 |
| 16 | `auto_qb.rules.expr.env.x__state__mutmut_12` | _state | 条件 enum is not None → enum is None | 假存活 | 两支都返回 False ⇒ 恒 False; test_seed_fields(:114) 断言 True ⇒ 池内可杀 |
| 17 | `auto_qb.rules.expr.env.x__state__mutmut_13` | _state | else False → else True | 等价 | else 支要求 state_enum is None, 而 record.state_enum 恒返回 TorrentState(含 UNKNOWN) ⇒ 分支不可达 ⇒ 等价 |
| 18 | `auto_qb.rules.expr.env.x__hr__mutmut_1` | _hr | tor = ctx.torrent → None | 假存活 | tracker_conf 取值 AttributeError; test_derived_values(:129) 取三名 ⇒ 池内可杀 |
| 19 | `auto_qb.rules.expr.env.x__hr__mutmut_2` | _hr | or → and | 假存活 | tracker_conf 为 None 时仍求值 None.hr ⇒ AttributeError; 同 :129 ⇒ 池内可杀 |
| 20 | `auto_qb.rules.expr.env.x__hr__mutmut_3` | _hr | is None → is not None | 假存活 | 有 conf 时恒短路返回 False(hr 名恒假); test_expr_eval:418 断言 hr_local_triggered True ⇒ 池内可杀 |
| 21 | `auto_qb.rules.expr.env.x__hr__mutmut_4` | _hr | 去掉 not(tracker_conf.hr) | 假存活 | 有 HR 配置时提前 return False(判定反转); 同 :418 ⇒ 池内可杀 |
| 22 | `auto_qb.rules.expr.env.x__hr__mutmut_5` | _hr | 缺省 return False → True | 假存活 | 无 tracker_conf 时三名变 True; test_derived_values(:129) 断言 False ⇒ 池内可杀 |
| 23 | `auto_qb.rules.expr.env.x__hr__mutmut_6` | _hr | → bool(None) | 假存活 | HR 命中时恒 False; test_expr_eval:418 断言 True ⇒ 池内可杀 |
| 24 | `auto_qb.rules.expr.env.x__hr__mutmut_7` | _hr | getattr(tor, method) → getattr(None, method) | 假存活 | AttributeError; 同 :418 ⇒ 池内可杀 |
| 25 | `auto_qb.rules.expr.env.x__hr__mutmut_8` | _hr | 方法名 method → None | 假存活 | getattr(tor, None) ⇒ TypeError; 同 :418 ⇒ 池内可杀 |
| 26 | `auto_qb.rules.expr.env.x__hr__mutmut_9` | _hr | → getattr(method)(丢对象) | 假存活 | TypeError; 同 :418 ⇒ 池内可杀 |
| 27 | `auto_qb.rules.expr.env.x__hr__mutmut_10` | _hr | → getattr(tor, )(丢方法名) | 假存活 | TypeError; 同 :418 ⇒ 池内可杀 |
| 28 | `auto_qb.rules.expr.env.x__age__mutmut_1` | _age | 减 → 加 | 真洞 | age 由 now-added_on 变成 now+added_on(恒错, 且恒大于真实年龄); 池内 test_derived_values(:123) 只断言 >0, 正负两种都成立 ⇒ 池内抓不住。**建议守阵**: 断言 tor.age ≈ now-added_on(±5s), 而非仅 >0 |
| 29 | `auto_qb.rules.expr.env.x__age__mutmut_2` | _age | (added_on or 0) → (added_on and 0) | 真洞 | 被减数恒 0 ⇒ age 恒等于当前时间戳(约 1.7e9), 语义全错; :123 的 >0 照样通过 ⇒ 池内抓不住。**建议守阵**: 断言 tor.age 与 now-added_on 差 < 5s |
| 30 | `auto_qb.rules.expr.env.x__age__mutmut_3` | _age | or 0 → or 1 | 等价 | 仅当 added_on 为 None/0 的兜底支差 1 秒, 该支测试不可达, 且判定面(age > 1d 等)不受 1s 影响 ⇒ 等价 |
| 31 | `auto_qb.rules.expr.env.x__idle__mutmut_4` | _idle | last < 0 → last <= 0 | 等价 | 只在 last==0(1970) 与原文不同; qB 用 -1 表示从未传输, 0 不可达 ⇒ 语义不可区分 |
| 32 | `auto_qb.rules.expr.env.x__idle__mutmut_5` | _idle | last < 0 → last < 1 | 等价 | 只在 last∈[0,1) 与原文不同, 同一不可达区间 ⇒ 等价 |
| 33 | `auto_qb.rules.expr.env.x__idle__mutmut_8` | _idle | float("inf") → float("INF") | 等价 | float() 的 inf 字面量大小写不敏感, "INF" 解析出同一个 inf ⇒ 逐值同 |
| 34 | `auto_qb.rules.expr.env.x__server_state__mutmut_6` | _server_state | getattr 缺省实参删成尾逗号 | 等价 | getattr(ctx.manager, "store", ) 与两参调用同义 ⇒ 逐字同 |
| 35 | `auto_qb.rules.expr.env.x__server_state__mutmut_11` | _server_state | 条件追加 or True | 等价 | 条件恒真 ⇒ store 为 None 时走 getattr(None, …, None), 结果仍是 None, 与原式同值 ⇒ 等价 |
| 36 | `auto_qb.rules.expr.env.x__server_state__mutmut_16` | _server_state | getattr 缺省实参删成尾逗号 | 等价 | getattr(store, "server_state", ) 与两参同义 ⇒ 等价 |
| 37 | `auto_qb.rules.expr.env.x__server_state__mutmut_20` | _server_state | or → and(空 dict 不再报错) | 真洞 | ss 为 {} 时原文抛「数据源不可用」, 变异后放行空 dict, 下游 _server_value 退化成「缺失字段」(报错指错方向); 池内 test_server_state_unavailable(:194) 只覆盖未同步(None) ⇒ 池内抓不住。**建议守阵**: 断言 store.server_state={} 时 sys.dl_speed 抛「数据源不可用」 |
| 38 | `auto_qb.rules.expr.env.x__server_state__mutmut_24` | _server_state | 异常文案加 XX 前后缀 | 等价 | 仅文案; 池内 match="数据源不可用" 仍命中 ⇒ 语义不可区分 |
| 39 | `auto_qb.rules.expr.env.x__server_state__mutmut_25` | _server_state | 异常文案 qB → qb | 等价 | 仅大小写文案, match 仍命中 ⇒ 等价 |
| 40 | `auto_qb.rules.expr.env.x__server_state__mutmut_26` | _server_state | 异常文案改大写(QB/SERVER_STATE) | 等价 | 仅文案, match 仍命中 ⇒ 等价 |
| 41 | `auto_qb.rules.expr.env.x__server_value__mutmut_1` | _server_value | ss = _server_state(ctx) → None | 假存活 | `key not in None` ⇒ TypeError; test_server_state_values(:205) 取 sys.dl_speed ⇒ 池内可杀 |
| 42 | `auto_qb.rules.expr.env.x__server_value__mutmut_2` | _server_value | → _server_state(None) | 假存活 | None.manager 取值 ⇒ AttributeError; 同 :205 ⇒ 池内可杀 |
| 43 | `auto_qb.rules.expr.env.x__server_value__mutmut_3` | _server_value | key not in ss → key in ss | 假存活 | 有字段时反抛「缺失字段」; :205 断言取值成功 ⇒ 池内可杀 |
| 44 | `auto_qb.rules.expr.env.x__server_value__mutmut_4` | _server_value | ExprError(文案) → ExprError(None) | 假存活 | 文案丢失, :209 match="缺失字段" 失败 ⇒ 池内可杀 |
| 45 | `auto_qb.rules.expr.env.x__server_value__mutmut_5` | _server_value | value = ss[key] → None | 假存活 | 取值恒 None; :205 断言 == 1024 ⇒ 池内可杀 |
| 46 | `auto_qb.rules.expr.env.x__server_value__mutmut_6` | _server_value | kind is BOOL → kind is not BOOL | 假存活 | 数值键被 bool 化(dl_speed 1024→True); :205 ⇒ 池内可杀 |
| 47 | `auto_qb.rules.expr.env.x__server_value__mutmut_7` | _server_value | → bool(None) | 假存活 | 布尔键恒 False; :207 断言 alt_speed_on True ⇒ 池内可杀 |
| 48 | `auto_qb.rules.expr.env.x__count__mutmut_1` | _count | pred is None → pred is not None | 假存活 | 无谓词(torrent_count)反走全库拷贝, test_torrent_count_no_full_copy(:186-191) 的 _NoValues.values 立即炸 ⇒ 池内可杀 |
| 49 | `auto_qb.rules.expr.env.x__count__mutmut_2` | _count | records = list(...) → None | 假存活 | 谓词支 sum 遍历 None ⇒ TypeError; test_more_getters(:440-441) 取 seeding/downloading_count ⇒ 池内可杀 |
| 50 | `auto_qb.rules.expr.env.x__count__mutmut_3` | _count | → list(None) | 假存活 | TypeError; 同 :440 ⇒ 池内可杀 |
| 51 | `auto_qb.rules.expr.env.x__count__mutmut_4` | _count | sum(生成器) → sum(None) | 假存活 | TypeError; 同 :440 ⇒ 池内可杀 |
| 52 | `auto_qb.rules.expr.env.x__count__mutmut_5` | _count | sum(1 …) → sum(2 …) | 假存活 | 每命中记 2, seeding_count 1→2; :440 断言 == 1 ⇒ 池内可杀 |
| 53 | `auto_qb.rules.expr.env.x__count__mutmut_6` | _count | pred(t) → pred(None) | 假存活 | 谓词吃 None ⇒ _pred_state 返回 False ⇒ 计数恒 0; :440 ⇒ 池内可杀 |
| 54 | `auto_qb.rules.expr.env.x__pred_state__mutmut_1` | _pred_state | enum = getattr(rec, …) → None | 假存活 | 谓词恒 False ⇒ seeding_count 0≠1; test_more_getters(:440) ⇒ 池内可杀 |
| 55 | `auto_qb.rules.expr.env.x__pred_state__mutmut_2` | _pred_state | → getattr(None, "state_enum", None) | 假存活 | 恒 None ⇒ 恒 False; 同 :440 ⇒ 池内可杀 |
| 56 | `auto_qb.rules.expr.env.x__pred_state__mutmut_3` | _pred_state | 属性名 → None | 假存活 | getattr 属性名非字符串 ⇒ TypeError; 同 :440 ⇒ 池内可杀 |
| 57 | `auto_qb.rules.expr.env.x__pred_state__mutmut_4` | _pred_state | → getattr("state_enum", None)(丢对象) | 假存活 | TypeError; 同 :440 ⇒ 池内可杀 |
| 58 | `auto_qb.rules.expr.env.x__pred_state__mutmut_5` | _pred_state | → getattr(rec, None) | 假存活 | TypeError; 同 :440 ⇒ 池内可杀 |
| 59 | `auto_qb.rules.expr.env.x__pred_state__mutmut_6` | _pred_state | 缺省实参删成尾逗号 | 等价 | getattr(rec, "state_enum", ) 与两参同义 ⇒ 逐字同 |
| 60 | `auto_qb.rules.expr.env.x__pred_state__mutmut_7` | _pred_state | 属性名加 XX 前后缀 | 假存活 | 取不到 state_enum ⇒ 恒 False; :440 ⇒ 池内可杀 |
| 61 | `auto_qb.rules.expr.env.x__pred_state__mutmut_8` | _pred_state | 属性名改大写 STATE_ENUM | 假存活 | 同上 ⇒ 池内可杀 |
| 62 | `auto_qb.rules.expr.env.x__pred_state__mutmut_9` | _pred_state | 条件追加 and False | 假存活 | 条件恒假 ⇒ 恒 False; :440 ⇒ 池内可杀 |
| 63 | `auto_qb.rules.expr.env.x__pred_state__mutmut_10` | _pred_state | 条件改 or True | 等价 | 条件恒真; enum 为 None 时 getattr(None, attr, False) 亦 False ⇒ 两支同值 ⇒ 等价 |
| 64 | `auto_qb.rules.expr.env.x__pred_state__mutmut_11` | _pred_state | 取值表达式 → bool(None) | 假存活 | 恒 False; :440 ⇒ 池内可杀 |
| 65 | `auto_qb.rules.expr.env.x__pred_state__mutmut_12` | _pred_state | → getattr(None, attr, False) | 假存活 | 恒 False; :440 ⇒ 池内可杀 |
| 66 | `auto_qb.rules.expr.env.x__pred_state__mutmut_13` | _pred_state | 属性名 attr → None | 假存活 | TypeError; :440 ⇒ 池内可杀 |
| 67 | `auto_qb.rules.expr.env.x__pred_state__mutmut_14` | _pred_state | getattr 缺省 False → None | 等价 | 七个 is_* 在 TorrentState 上恒存在, 缺省分支不可达 ⇒ 等价 |
| 68 | `auto_qb.rules.expr.env.x__pred_state__mutmut_15` | _pred_state | → getattr(attr, False)(字符串当对象) | 假存活 | TypeError; :440 ⇒ 池内可杀 |
| 69 | `auto_qb.rules.expr.env.x__pred_state__mutmut_16` | _pred_state | → getattr(enum, False)(属性名是 bool) | 假存活 | TypeError; :440 ⇒ 池内可杀 |
| 70 | `auto_qb.rules.expr.env.x__pred_state__mutmut_17` | _pred_state | 缺省实参删成尾逗号 | 等价 | getattr(enum, attr, ) 与三参同义 ⇒ 等价 |
| 71 | `auto_qb.rules.expr.env.x__pred_state__mutmut_18` | _pred_state | getattr 缺省 False → True | 等价 | 缺省分支不可达(属性恒存在) ⇒ 等价 |
| 72 | `auto_qb.rules.expr.env.x__pred_state__mutmut_19` | _pred_state | 条件 enum is not None → enum is None | 假存活 | 两支恒 False; :440 ⇒ 池内可杀 |
| 73 | `auto_qb.rules.expr.env.x__pred_state__mutmut_20` | _pred_state | else False → else True | 等价 | else 支要求 state_enum 为 None, 而 TorrentRecord.state_enum 恒返回枚举(含 UNKNOWN) ⇒ 不可达 ⇒ 等价 |
| 74 | `auto_qb.rules.expr.env.x__tracker_names__mutmut_7` | _tracker_names | tracker_urls(ctx.client) → tracker_urls(None) | 假存活 | 丢客户端后命中集变空; test_more_getters(:443) 断言 frozenset({"HHan"}) ⇒ 池内可杀 |
| 75 | `auto_qb.rules.expr.env.x__traffic__mutmut_1` | _traffic | 去掉 not(source_enabled) | 假存活 | 启用时反抛「不可用」; test_traffic_values(:309) 断言取值 ⇒ 池内可杀 |
| 76 | `auto_qb.rules.expr.env.x__traffic__mutmut_2` | _traffic | source_enabled(ctx.config) → (None) | 假存活 | None 配置按「未配置」处理 ⇒ 恒 True, 总开关优先级丢失: 关源+曲线停用时先报「数据源未启用」; test_traffic_source_off(:336) 期望「流量来源已关闭」⇒ 池内可杀 |
| 77 | `auto_qb.rules.expr.env.x__traffic__mutmut_3` | _traffic | ExprError(原因) → ExprError(None) | 假存活 | 关源文案丢失, test_traffic_source_off(:332) match="流量来源已关闭" 失败 ⇒ 池内可杀 |
| 78 | `auto_qb.rules.expr.env.x__traffic__mutmut_4` | _traffic | unavailable_reason(ctx.config) → (None) | 假存活 | 关源文案退化成「数据源未配置」; :332 match="流量来源已关闭" 失败 ⇒ 池内可杀 |
| 79 | `auto_qb.rules.expr.env.x__traffic__mutmut_5` | _traffic | conf = getattr(...) → None | 假存活 | 曲线段停用被绕过, test_traffic_curve_section_disabled(:691) 期望「数据源未启用」实得「不可读」⇒ 池内可杀 |
| 80 | `auto_qb.rules.expr.env.x__traffic__mutmut_6` | _traffic | → getattr(None, "global_speed_limit_curve", None) | 假存活 | conf 恒 None ⇒ 同 mutmut_5; :691 ⇒ 池内可杀 |
| 81 | `auto_qb.rules.expr.env.x__traffic__mutmut_7` | _traffic | 属性名 → None | 假存活 | TypeError; :691 ⇒ 池内可杀 |
| 82 | `auto_qb.rules.expr.env.x__traffic__mutmut_8` | _traffic | → getattr("global_speed_limit_curve", None)(丢对象) | 假存活 | TypeError; :691 ⇒ 池内可杀 |
| 83 | `auto_qb.rules.expr.env.x__traffic__mutmut_9` | _traffic | → getattr(ctx.config, None)(丢属性名) | 假存活 | TypeError; :691 ⇒ 池内可杀 |
| 84 | `auto_qb.rules.expr.env.x__traffic__mutmut_10` | _traffic | 缺省实参删成尾逗号 | 等价 | getattr(ctx.config, "global_speed_limit_curve", ) 与两参同义 ⇒ 逐字同 |
| 85 | `auto_qb.rules.expr.env.x__traffic__mutmut_11` | _traffic | 属性名加 XX 前后缀 | 假存活 | 取不到 conf ⇒ 同 mutmut_5; :691 ⇒ 池内可杀 |
| 86 | `auto_qb.rules.expr.env.x__traffic__mutmut_12` | _traffic | 属性名改大写 GLOBAL_SPEED_LIMIT_CURVE | 假存活 | 同 mutmut_11 ⇒ 池内可杀 |
| 87 | `auto_qb.rules.expr.env.x__traffic__mutmut_13` | _traffic | dat_path = traffic_paths.dat_path(...) → None | 假存活 | 已配置也被判「未配置」; test_traffic_values(:309) ⇒ 池内可杀 |
| 88 | `auto_qb.rules.expr.env.x__traffic__mutmut_14` | _traffic | → dat_path(None) | 假存活 | 返回 "" ⇒ 同 mutmut_13; :309 ⇒ 池内可杀 |
| 89 | `auto_qb.rules.expr.env.x__traffic__mutmut_15` | _traffic | 去掉 not(enabled) | 假存活 | 启用时反抛「未启用」; :309 ⇒ 池内可杀 |
| 90 | `auto_qb.rules.expr.env.x__traffic__mutmut_16` | _traffic | getattr(conf, …) → getattr(None, …) | 假存活 | 缺省 True 兜住 ⇒ 绕过曲线停用; :691 ⇒ 池内可杀 |
| 91 | `auto_qb.rules.expr.env.x__traffic__mutmut_17` | _traffic | 属性名 → None | 假存活 | TypeError; :691 ⇒ 池内可杀 |
| 92 | `auto_qb.rules.expr.env.x__traffic__mutmut_18` | _traffic | getattr 缺省 True → None | 假存活 | conf 为 None(未配置)时 `not None` 成立 ⇒ 误报「未启用」, test_traffic_unconfigured(:318) 期望「未配置」⇒ 池内可杀 |
| 93 | `auto_qb.rules.expr.env.x__traffic__mutmut_19` | _traffic | → getattr("enabled", True)(丢对象) | 假存活 | TypeError; :691 ⇒ 池内可杀 |
| 94 | `auto_qb.rules.expr.env.x__traffic__mutmut_20` | _traffic | → getattr(conf, True)(属性名是 bool) | 假存活 | TypeError; :691 ⇒ 池内可杀 |
| 95 | `auto_qb.rules.expr.env.x__traffic__mutmut_21` | _traffic | 缺省实参删成尾逗号 | 等价 | getattr(conf, "enabled", ) 与两参同义 ⇒ 逐字同 |
| 96 | `auto_qb.rules.expr.env.x__traffic__mutmut_22` | _traffic | 属性名加 XX 前后缀 | 假存活 | 取不到 enabled ⇒ 同 mutmut_5; :691 ⇒ 池内可杀 |
| 97 | `auto_qb.rules.expr.env.x__traffic__mutmut_23` | _traffic | 属性名改大写 ENABLED | 假存活 | 同 mutmut_22 ⇒ 池内可杀 |
| 98 | `auto_qb.rules.expr.env.x__traffic__mutmut_24` | _traffic | getattr 缺省 True → False | 假存活 | conf 为 None 时 `not False` 成立 ⇒ 误报「未启用」; :318 期望「未配置」⇒ 池内可杀 |
| 99 | `auto_qb.rules.expr.env.x__traffic__mutmut_25` | _traffic | ExprError(文案) → ExprError(None) | 假存活 | 曲线段文案丢失, :691 match="数据源未启用" 失败 ⇒ 池内可杀 |
| 100 | `auto_qb.rules.expr.env.x__traffic__mutmut_26` | _traffic | 异常文案加 XX 前后缀 | 等价 | 文案仍含「数据源未启用」, 判定与 match 均不受影响 ⇒ 等价 |
| 101 | `auto_qb.rules.expr.env.x__traffic__mutmut_27` | _traffic | 异常文案改大写(CONFIG…为 FALSE) | 等价 | 文案仍含「数据源未启用」⇒ 等价 |
| 102 | `auto_qb.rules.expr.env.x__traffic__mutmut_28` | _traffic | 去掉 not(dat_path) | 假存活 | dat_path 有效时反抛; :309 ⇒ 池内可杀 |
| 103 | `auto_qb.rules.expr.env.x__traffic__mutmut_29` | _traffic | ExprError(原因) → ExprError(None) | 假存活 | 未配置分支文案丢失, :318 match="数据源未配置" 失败 ⇒ 池内可杀 |
| 104 | `auto_qb.rules.expr.env.x__traffic__mutmut_30` | _traffic | unavailable_reason(ctx.config) → (None) | 等价 | None 配置按未配置处理, 未配置分支拼出同一句「数据源未配置」(:318 仍命中); 仅 provider=global_traffic_monitor 时文案不同, 属异常文案差异 ⇒ 等价 |
| 105 | `auto_qb.rules.expr.env.x__traffic__mutmut_31` | _traffic | open(dat_path, …) → open(None, …) | 假存活 | TypeError; :309 ⇒ 池内可杀 |
| 106 | `auto_qb.rules.expr.env.x__traffic__mutmut_32` | _traffic | mode "r" → None | 假存活 | TypeError; :309 ⇒ 池内可杀 |
| 107 | `auto_qb.rules.expr.env.x__traffic__mutmut_33` | _traffic | encoding → None | 等价 | encoding=None 走 locale 缺省, 测试 dat 全 ASCII ⇒ 解码结果逐字相同 ⇒ 等价 |
| 108 | `auto_qb.rules.expr.env.x__traffic__mutmut_34` | _traffic | errors → None | 等价 | errors=None 走缺省 strict, ASCII 内容无解码错误 ⇒ 等价 |
| 109 | `auto_qb.rules.expr.env.x__traffic__mutmut_35` | _traffic | 首参 dat_path → "r" | 假存活 | 打开名为 r 的文件失败 ⇒ OSError「不可读」; :309 ⇒ 池内可杀 |
| 110 | `auto_qb.rules.expr.env.x__traffic__mutmut_36` | _traffic | 省略 mode | 等价 | open 缺省 mode 即 "r" ⇒ 逐字同 |
| 111 | `auto_qb.rules.expr.env.x__traffic__mutmut_37` | _traffic | 省略 encoding | 等价 | 缺省编码, 测试 dat 全 ASCII ⇒ 同结果 ⇒ 等价 |
| 112 | `auto_qb.rules.expr.env.x__traffic__mutmut_38` | _traffic | errors 缺省实参删成尾逗号 | 等价 | errors="replace", ) 与两参同义 ⇒ 逐字同 |
| 113 | `auto_qb.rules.expr.env.x__traffic__mutmut_39` | _traffic | mode "r" → "XXrXX" | 假存活 | 非法模式 ⇒ ValueError(不被 OSError 捕获); :309 ⇒ 池内可杀 |
| 114 | `auto_qb.rules.expr.env.x__traffic__mutmut_40` | _traffic | mode "r" → "R" | 假存活 | 模式须小写 ⇒ ValueError; :309 ⇒ 池内可杀 |
| 115 | `auto_qb.rules.expr.env.x__traffic__mutmut_41` | _traffic | encoding "utf-8" → "XXutf-8XX" | 假存活 | 未知编码 ⇒ LookupError; :309 ⇒ 池内可杀 |
| 116 | `auto_qb.rules.expr.env.x__traffic__mutmut_42` | _traffic | encoding "utf-8" → "UTF-8" | 等价 | 编码名大小写不敏感, 同一 codec ⇒ 等价 |
| 117 | `auto_qb.rules.expr.env.x__traffic__mutmut_43` | _traffic | errors "replace" → "XXreplaceXX" | 假存活 | 未注册的错误处理器 ⇒ LookupError; :309 ⇒ 池内可杀 |
| 118 | `auto_qb.rules.expr.env.x__traffic__mutmut_44` | _traffic | errors "replace" → "REPLACE" | 假存活 | 错误处理器名大小写敏感 ⇒ LookupError; :309 ⇒ 池内可杀 |
| 119 | `auto_qb.rules.expr.env.x__traffic__mutmut_45` | _traffic | rows, _bad → None | 假存活 | aggregate(None, …) 遍历 None ⇒ TypeError; :309 ⇒ 池内可杀 |
| 120 | `auto_qb.rules.expr.env.x__traffic__mutmut_46` | _traffic | parse_history_dat(f.read()) → (None) | 假存活 | 解析 None 崩溃; :309 ⇒ 池内可杀 |
| 121 | `auto_qb.rules.expr.env.x__traffic__mutmut_47` | _traffic | ExprError(文案) → ExprError(None) | 假存活 | 不可读文案丢失, :499 match="数据源不可读" 失败 ⇒ 池内可杀 |
| 122 | `auto_qb.rules.expr.env.x__traffic__mutmut_48` | _traffic | aggregate(rows, period) → (None, period) | 假存活 | 遍历 None ⇒ TypeError; :309 ⇒ 池内可杀 |
| 123 | `auto_qb.rules.expr.env.x__traffic__mutmut_49` | _traffic | aggregate(rows, period) → (rows, None) | 假存活 | period=None 落 else 支 int(None[:-1]) ⇒ TypeError; :309 ⇒ 池内可杀 |
| 124 | `auto_qb.rules.expr.env.x__traffic__mutmut_50` | _traffic | → aggregate(period)(少 rows) | 假存活 | rows 变周期串, period 缺失 ⇒ TypeError; :309 ⇒ 池内可杀 |
| 125 | `auto_qb.rules.expr.env.x__traffic__mutmut_51` | _traffic | → aggregate(rows, )(少 period) | 假存活 | 缺 period ⇒ TypeError; :309 ⇒ 池内可杀 |
| 126 | `auto_qb.rules.expr.env.x__len_of__mutmut_4` | _len_of | label(type_name(value)) → label(None) | 等价 | 只改异常文案里的类型名; :512 match="不可计长" 仍命中 ⇒ 等价 |
| 127 | `auto_qb.rules.expr.env.x__len_of__mutmut_5` | _len_of | type_name(value) → type_name(None) | 等价 | 文案显示「未知类型」, match 仍命中 ⇒ 等价 |
| 128 | `auto_qb.rules.expr.env.x__num_unary__mutmut_1` | _num_unary | fn(require_number(...)) → fn(None) | 假存活 | abs/round 等对 None 崩溃; test_more_getters(:451) abs(-5)==5 ⇒ 池内可杀 |
| 129 | `auto_qb.rules.expr.env.x__num_unary__mutmut_2` | _num_unary | require_number(args[0], …) → (None, …) | 假存活 | 恒抛「必须是数值」; :451 ⇒ 池内可杀 |
| 130 | `auto_qb.rules.expr.env.x__num_unary__mutmut_3` | _num_unary | what 文案 → None | 假存活 | 报错主体变 "None", :513 match="参数必须是数值" 失败 ⇒ 池内可杀 |
| 131 | `auto_qb.rules.expr.env.x__num_unary__mutmut_4` | _num_unary | 少传 value 实参 | 假存活 | require_number("该函数的参数") ⇒ TypeError; :451 ⇒ 池内可杀 |
| 132 | `auto_qb.rules.expr.env.x__num_unary__mutmut_5` | _num_unary | what 缺省实参删成尾逗号 | 等价 | require_number(args[0], ) 与两参同义 ⇒ 逐字同 |
| 133 | `auto_qb.rules.expr.env.x__num_unary__mutmut_6` | _num_unary | args[0] → args[1] | 假存活 | 一元调用只有 1 个实参 ⇒ IndexError; :451 ⇒ 池内可杀 |
| 134 | `auto_qb.rules.expr.env.x__num_unary__mutmut_7` | _num_unary | what 文案加 XX 前后缀 | 等价 | 文案仍含「参数必须是数值」⇒ match 命中 ⇒ 等价 |
| 135 | `auto_qb.rules.expr.env.x__min_max__mutmut_1` | _min_max | require_number(a, …) → (None, …) | 假存活 | 每个实参恒抛; test_more_getters(:452) min(tor.ratio, 1.5) ⇒ 池内可杀 |
| 136 | `auto_qb.rules.expr.env.x__min_max__mutmut_2` | _min_max | what 文案 → None | 假存活 | 报错主体变 "None", :514 match="参数必须是数值" 失败 ⇒ 池内可杀 |
| 137 | `auto_qb.rules.expr.env.x__min_max__mutmut_3` | _min_max | 少传 value 实参 | 假存活 | TypeError; :452 ⇒ 池内可杀 |
| 138 | `auto_qb.rules.expr.env.x__min_max__mutmut_4` | _min_max | what 缺省实参删成尾逗号 | 等价 | require_number(a, ) 与两参同义 ⇒ 等价 |
| 139 | `auto_qb.rules.expr.env.x__min_max__mutmut_5` | _min_max | what 文案加 XX 前后缀 | 等价 | 文案仍含「参数必须是数值」⇒ 等价 |
| 140 | `auto_qb.rules.expr.env.x__min_max__mutmut_6` | _min_max | fn(args) → fn(None) | 假存活 | min/max 对 None 崩溃; :452 ⇒ 池内可杀 |
| 141 | `auto_qb.rules.expr.env.x__ann_name__mutmut_1` | _ann_name | isinstance(t, str) 追加 and False | 假存活 | 字符串注解也走 getattr("int", "__name__", "") → ""; import 期 _build_name_table 因此丢掉全部快照名, test_seed_fields(:110) 取 tor.size ⇒ 池内可杀(表在 import 期冻结, 属 B1 批注同一工具盲区) |
| 142 | `auto_qb.rules.expr.env.x__ann_name__mutmut_5` | _ann_name | getattr 缺省 "" → None | 等价 | 仅非 str 且无 __name__ 的对象受影响; 注解恒为 str 或带 __name__ 的类型, 该缺省不可达 ⇒ 等价 |
| 143 | `auto_qb.rules.expr.env.x__ann_name__mutmut_8` | _ann_name | 缺省实参删成尾逗号 | 等价 | getattr(t, "__name__", ) 与两参同义 ⇒ 等价 |
| 144 | `auto_qb.rules.expr.env.x__ann_name__mutmut_11` | _ann_name | getattr 缺省 "" → "XXXX" | 等价 | 缺省不可达; 即便到达 _PY_KIND.get("XXXX") 与 get("") 同为 None ⇒ 等价 |
| 145 | `auto_qb.rules.expr.env.x_static_type__mutmut_6` | static_type | 未知名错误位置 node.pos → None | 等价 | 仅让消息丢「（第 N 列）」后缀, 池内 match 子串 ⇒ 等价 |
| 146 | `auto_qb.rules.expr.env.x_static_type__mutmut_8` | static_type | 删错误位置实参 | 等价 | 同上, 仅诊断列号丢失 ⇒ 等价 |
| 147 | `auto_qb.rules.expr.env.x_static_type__mutmut_13` | static_type | 未知函数错误位置 → None | 等价 | 仅诊断列号丢失 ⇒ 等价 |
| 148 | `auto_qb.rules.expr.env.x_static_type__mutmut_15` | static_type | 删错误位置实参 | 等价 | 仅诊断列号丢失 ⇒ 等价 |
| 149 | `auto_qb.rules.expr.env.x_static_type__mutmut_17` | static_type | want = "/".join(...) → None | 等价 | 消息变「参数个数应为 None」, :255 match="参数个数" 仍命中 ⇒ 等价 |
| 150 | `auto_qb.rules.expr.env.x_static_type__mutmut_19` | static_type | 分隔符 "/" → "XX/XX" | 等价 | 消息变体, :255 仍命中 ⇒ 等价 |
| 151 | `auto_qb.rules.expr.env.x_static_type__mutmut_20` | static_type | join 内 str(a) → str(None) | 等价 | want 变 "None/None", :255 仍命中 ⇒ 等价 |
| 152 | `auto_qb.rules.expr.env.x_static_type__mutmut_22` | static_type | 参数个数错误位置 → None | 等价 | 仅诊断列号丢失 ⇒ 等价 |
| 153 | `auto_qb.rules.expr.env.x_static_type__mutmut_24` | static_type | 删错误位置实参 | 等价 | 仅诊断列号丢失 ⇒ 等价 |
| 154 | `auto_qb.rules.expr.env.x_static_type__mutmut_35` | static_type | 参数类型错误位置 → None | 等价 | 仅诊断列号丢失; :578-581 match="参数类型应为 数值" 仍命中 ⇒ 等价 |
| 155 | `auto_qb.rules.expr.env.x_static_type__mutmut_37` | static_type | 删位置表达式(仅留文案) | 等价 | 同上, 位置恒缺省 ⇒ 等价 |
| 156 | `auto_qb.rules.expr.env.x_static_type__mutmut_39` | static_type | 参数类型文案 label(got) → label(None) | 等价 | 消息变「得到 未知类型」, :578 仍命中 ⇒ 等价 |
| 157 | `auto_qb.rules.expr.env.x_static_type__mutmut_40` | static_type | 位置条件追加 and False | 等价 | 位置恒 None, 仅丢列号 ⇒ 等价 |
| 158 | `auto_qb.rules.expr.env.x_static_type__mutmut_42` | static_type | ListLit 元素 static_type(item) → (None) | 真洞 | 列表字面量元素不再递归校验(未知名/坏调用可过配置期 validate, 变成运行期才炸); 池内列表字面量只用合法元素(:542, :588) ⇒ 抓不住。**建议守阵**: 断言 validate(compile_expr('tor.state in [nope]')) 抛「未知取值」 |
| 159 | `auto_qb.rules.expr.env.x_static_type__mutmut_43` | static_type | check_unary_types(node.op, …) → (None, …) | 真洞 | op 变 None 后 check_unary_types 落入「规则表外静默放行」, `-tor.name`/`not tor.size` 配置期不再拒; 池内只在 test_expr_parse:210-213 直调 check_unary_types, 不经 static_type ⇒ 抓不住。**建议守阵**: 断言 validate(compile_expr('-tor.name > 0')) 抛「操作数必须是数值」 |
| 160 | `auto_qb.rules.expr.env.x_static_type__mutmut_47` | static_type | 一元操作数 static_type(node.operand) → (None) | 真洞 | 操作数恒 ANY ⇒ check_unary_types 首行即放行, 一元类型错误全部漏过配置期; 池内 :584 只覆盖 ANY 合法放行 ⇒ 抓不住。**建议守阵**: 断言 validate(compile_expr('not tor.size')) 抛「操作数必须是布尔」 |
| 161 | `auto_qb.rules.expr.env.x_validate__mutmut_5` | validate | label(kind) → label(None) | 等价 | 只改「得到 …」文案; :260 match="结果必须是布尔" 仍命中 ⇒ 等价 |
| 162 | `auto_qb.rules.expr.env.x_used_names__mutmut_3` | used_names | Unary 支 并赋值 → 赋值 | 等价 | 该支执行时 found 必为空集, 赋值与并赋值结果相同 ⇒ 等价 |
| 163 | `auto_qb.rules.expr.env.x_used_names__mutmut_6` | used_names | Binary 支 并赋值 → 赋值 | 等价 | 该支执行时 found 必为空集 ⇒ 同 mutmut_3 ⇒ 等价 |
| 164 | `auto_qb.rules.expr.env.x_used_names__mutmut_11` | used_names | Call 实参 并赋值 → 赋值 | 真洞 | 循环内改用赋值 ⇒ 多参调用只保留最后一参的名字, 前面的取值名从 used_names 消失(数据源门控漏放行/漏拦); 池内 gated_names_in 用例(:588)只含单参调用 ⇒ 抓不住。**建议守阵**: 断言 gated_names_in(compile_expr('min(sys.upload_today, 1) > 0')) == ['sys.upload_today'] |
| 165 | `auto_qb.rules.expr.env.x_used_names__mutmut_12` | used_names | Call 实参 并赋值 → 交集赋值 | 真洞 | 与空集求交 ⇒ 调用实参里的取值名全丢; 池内无「门控名在调用实参内」用例 ⇒ 抓不住。**建议守阵**: 断言 gated_names_in(compile_expr('min(sys.upload_today, 1) > 0')) == ['sys.upload_today'] |
| 166 | `auto_qb.rules.expr.env.x_used_names__mutmut_13` | used_names | Call 实参 used_names(arg) → (None) | 真洞 | used_names(None) 返回空集 ⇒ 调用实参名全丢; 同上无覆盖 ⇒ 抓不住。**建议守阵**: 断言 gated_names_in(compile_expr('min(sys.upload_today, 1) > 0')) == ['sys.upload_today'] |
| 167 | `auto_qb.rules.expr.env.x_used_names__mutmut_14` | used_names | ListLit 元素 并赋值 → 赋值 | 真洞 | 循环内改用赋值 ⇒ 多元素列表只保留最后一项的名字; 池内列表字面量元素无名(:542, :588) ⇒ 抓不住。**建议守阵**: 断言 gated_names_in(compile_expr('sys.upload_today in [1, sys.upload_month]')) == ['sys.upload_month', 'sys.upload_today'] |
| 168 | `auto_qb.rules.expr.env.x_used_names__mutmut_15` | used_names | ListLit 元素 并赋值 → 交集赋值 | 真洞 | 与空集求交 ⇒ 列表元素名全丢; 池内无覆盖 ⇒ 抓不住。**建议守阵**: 同上断言 |
| 169 | `auto_qb.rules.expr.env.x_used_names__mutmut_16` | used_names | ListLit 元素 used_names(item) → (None) | 真洞 | 返回空集 ⇒ 列表元素名全丢; 池内无覆盖 ⇒ 抓不住。**建议守阵**: 同上断言 |
