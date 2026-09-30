# 26-10-01-backend-web-state-alias-disposal — 别名层处置: _WEB_STATE_ALIAS 与旧名委托层退役

**Status:** In Progress
**Added:** 2026-10-01
**Updated:** 2026-10-01
**Summary:** 计划 26-10-01-0350 拍板按推荐(D1 属性面永久保留 / D2 按模块域分批 / D3 W0 先行), W0 分诊清单 + 守阵立桩完成(纯文档与测试, 零产品代码): 逐名分诊落 JSON 清单(plans/26-10-01-0350-...triage.json, 20 别名 + 2 dunder + 57 单行转发 + 7 外观属性(D1 保留) + 17 内核自有 = 106 个类面成员; 波次 W1 src 消费方 15 名 / W2 仅测试 57 名 / W3 无消费方直删 5 名), 新增冻结守阵 tests/test_qbmanager_alias_freeze.py 4 例(AST 扫单行转发形状与清单双向比对: 清单外新增旧名委托即红 / 清单成员已删须同步清单 / kernel 成员不得退化 / counts 自洽)。分诊对计划数字的三处实测修正: ①委托成员实测 86(计划 81, 勘察基线差); ②「4 个纯内部属性对」实测仅 _next_state_flush_at 1 对; ③真实 src 消费方比 W1 原口径多三域(rules/actions/checking.py 组上下文 4 处 + rules/base.py 记录 2 处 + checking_meta.py 落盘 1 处, P6 后 rules 动作消费面)与 1 处 getattr 字符串暗消费方(context.py:32 _web_write_seq), 全部归入 W1。**W1 完成(2026-10-01)**: 分诊 W1×15 名的 src 消费方全部改新名口 —— webui 路由域(auth/system/state/torrent_detail/events/fs/hr/sites + context.py getattr 直取)改 `manager.web.*`; rules 三域(checking.py 组上下文 → host.get("grouping")._*、base.py 记录 → manager.ctx.state.*、checking_meta 冷却 helper 宿主收敛为 StateService)同波改净; 范围外注记 _hr_view_fields 处置落定 = **公开化改名 hr_view_fields**(路由直调私有名不成立, 不搬 hr 口 —— 搬移超 W1 只改名边界); 注释与 static 四文件旧名提法清零; test_web 假替身(SimpleNamespace 无别名层)同波接线 web.* 新名 + web_env 双写 token, 真 manager 测试经别名层零改动。验收: `grep manager\._`(webui)为空 + test.full 1894+3 / 91%(与 W0 持平, 纯改名)。基线 26-10-01-0545。**W2 完成(2026-10-01)**: 测试面按模块域四批 + 验收补漏共 5 提交 —— 批次1 web 域(5 文件 376 处, 别名 18 字段 → mgr.web.* + WEB 转发 8 名 → web.*, 假替身收尾 W1 双轨)/ 批次2 maintenance+trackers 域(6 文件 85 处, ctx.trackers/ctx.maintenance/host.get 口)/ 批次3 grouping 域(2 文件 52 处, host.get("grouping") 口)/ 批次4 rules+state+ops 域(9 文件 150 处, host.get("rules")/ctx.state(maybe_flush 补 interval、bind_field_snapshots 补 store 实参)/ctx.ops 口, helpers.make_manager 装载行同迁)/ 补漏(3 文件 9 处, 整仓验收 grep 抓出跨批漏迁)。过渡期钉子处置: test_modules_p4 两测试的「旧名委托等价/保持可用」断言改写为纯 ctx.ops 语义。豁免残留: test_qbmanager 别名守阵同对象断言 9 行(计划 §04, W3 同删)。验收: test.full 1894+3 / 90%(覆盖率 91→90 系转发方法失去唯一调用方的预期漂移, W3 删除面); 基线 26-10-01-0700。W3(删本体 + 回写 + 四场景走查)待做。

**Topics:** backend-web-state-alias-disposal

**Refs:** memory-bank/plans/26-10-01-0350-plan-web-state-alias-disposal.html

**Legacy-ID:** 无

> 关联件: 分诊清单 `memory-bank/plans/26-10-01-0350-plan-web-state-alias-disposal.triage.json`(W0 产物, 守阵直读); 兼容层成因见 1819 档案 `26-09-30-backend-kernel-module-refactor`。(不入 Refs: JSON 与旧档案无法反向声明, 认领链口径见 tests/test_docs_forms.py)

## 原始请求

用户: 「按推荐实施W0: 26-10-01-0350-plan-web-state-alias-disposal.html」—— 实施别名层处置计划的 W0 波(分诊清单 + 守阵立桩, 纯文档与测试, 零产品代码), 决策点 D1-D3 按计划推荐拍板。

## 思考过程与决策

- **D1-D3 按推荐拍板**(2026-10-01, 随「按推荐实施W0」): D1 属性对(config/store/api/state/web/task_queue/state_file)属性面永久保留, 仅删纯内部属性对; D2 W2 测试迁移按模块域分 3-4 批; D3 独立排期, W0 分诊清单先行产出让冻结守阵尽早生效。计划状态 Open → In Progress。
- **分诊清单取 JSON 单文件形态**(plans/ 附件, 命名随 `.baseline.json` 先例): W1/W2 施工图需要的是逐名「类别/目标名/波次/消费方」结构化数据, 守阵测试直读同一文件 —— 一份文件同时服务人审与机检, 不做 HTML+JSON 双份。字段与判读口径见文件 `_legend`。
- **守阵形状判定**(单行转发 vs 内核自有): 去 docstring 后恰一条语句 + 该语句自 `self.<svc>`(svc ∈ ctx/web/hr/host/store/api/state/config/task_queue)起链(Attribute/Call 连降, 取紧邻 self 的属性判服务根)。内核自有方法(多语句体/事件广播/self._client 自有属性)天然不命中, 由清单显式标 kernel/保留。守阵做双向集合相等: 清单外新增转发即红(冻结目的), 清单成员消失也红(逼 W3 删除时同步清单)。
- **分诊数字以 82330d45 实测为准**(计划数字是 54c83ac3 勘察值): 委托成员实测 86(计划 81); 计划「仅删其中 4 个纯内部属性对(_next_state_flush_at 等)」实测**只有 _next_state_flush_at 1 对**纯内部, 其余属性对全是 D1 外观成员 —— W3 删除面据此收窄。
- **消费方统计分两级**: src 侧行级精查(接收者 + 注释甄别), 测试侧接收者级计数(限 mgr/mgr2/mgr3/manager/self.manager/ctx.manager/_manager)—— 排除模块同名方法(ctx.ops.X / host.get(...).X / mock.patch.object(mod, ...))造成的词边界误计; 由此发现 3 个名单的 manager 面已无消费方(_handle_state_transitions/_handle_removed_torrents/_handle_event_rule, 归 W3 直删)。
- **W1 范围按计划标题「路由与 src 侧改新名」执行**: 计划正文只点名 webui routes 8 处与 web.py 调用方, 但 P6 后 rules 动作经 manager 旧名消费(checking.py 组上下文 4 处 / base.py 记录 2 处 / checking_meta.py 落盘 1 处)与 getattr 字符串暗消费方(context.py:32)同为 src 侧旧名, 清单已逐名归 W1; 计划的 grep 验收(manager._ 于 webui 为空)作为其中 webui 域的守阵不动。
- **范围外注记**: `manager._hr_view_fields`(routes/torrent_detail.py:34)是 WebviewMixin 静态方法(非 qbmanager 委托层成员), 但会命中 W1 的 grep 验收 —— 处置方式(改经 hr 口/保留)由 W1 定; `rules/checking_meta.py:13` 宿主参数是「有 .state dict 与 .save_state() 的对象」鸭子类型契约, W1 改 manager.save_state → ctx.state.save 时须同步核对。

## 实现计划

W0-W3 四波见 [计划 26-10-01-0350](../plans/26-10-01-0350-plan-web-state-alias-disposal.html) §03; 逐名施工图 = [分诊清单 JSON](../plans/26-10-01-0350-plan-web-state-alias-disposal.triage.json)(名字/类别/消费方/目标名/波次)。每波独立入库全量绿; 删名字的提交不允许夹带行为变更; 涉及 run() 字面量的清理(_next_state_flush_at)连同 test_periodic_flush_is_wired_in_run 守阵同波改写。

## 子任务状态表

| 波 | 内容 | 状态 |
|---|---|---|
| W0 | 分诊清单 + 守阵立桩(零产品代码) | Done (2026-10-01) |
| W1 | 路由与 src 侧改新名(消费方最少的一刀) | Done (2026-10-01) |
| W2 | 测试面迁移(按模块域分批, D2) | Done (2026-10-01) |
| W3 | 删除兼容层本体 + 回写 + 四场景走查回放 | Open |

## 进度日志

- **2026-10-01 W0 完成**: ①分诊清单落 `memory-bank/plans/26-10-01-0350-plan-web-state-alias-disposal.triage.json`(20 别名 + 2 dunder + 57 单行转发 + 7 外观(D1 保留) + 17 内核自有; 波次 W1×15 / W2×57 / W3×5 / 保留×24)。②守阵 `tests/test_qbmanager_alias_freeze.py` 4 例全绿(别名表==清单 / 转发面双向冻结 / kernel 不退化 / counts 自洽)。③test.full 1894 passed + 3 skipped / 91%(较上基线净增 4 = 守阵 4 例), 基线切片 `baselines/26-10-01-0443-w0-alias-triage-freeze.md`。④计划标 In Progress; conventions/modules.md 兼容层现状节补守阵指针。待用户评审清单后 W1 开工。
- **2026-10-01 W2 完成**: ①批次1 web 域(3e4231d1): 别名 18 字段测试消费方 → mgr.web.*、WEB 转发 8 名 → web.consume_commands/check_pending/flush_truths/flush_views/rebuild_views/ensure_view/ensure_state/touch; test_web 假替身收尾 W1 双轨(旧名属性删除, 数据挂 mgr.web.*, token 双写改单写, ensure_view/ensure_state 替身改读 web.*); test_qbmanager 顺带迁跨域 8 处; 别名守阵区(847-890)按计划 §04 保持原样。②批次2 maintenance/tags/trackers 域(fe0cc172): ctx.trackers.match/apply_speed_limit、ctx.maintenance.七方法、host.get("maintenance").handle_*、host.get("speed_curve").handle_speed_limit_curve(Task handler= 取引用形态含内)。③批次3 grouping 域(e88d4e4b): host.get("grouping")._* 十名 52 处。④批次4 rules/state/ops 域(e4c57568): mgr.rules/enabled_rules 属性对 → host.get("rules")、rules 六方法同口、状态八名 → ctx.state(_maybe_flush_state(now) → maybe_flush(now, config.state_save_interval) 补转发层读 config 的间隔实参; _bind_field_snapshots() → bind_field_snapshots(mgr.store) 补 store 实参; _next_state_flush_at → ctx.state.next_flush_at)、ops 三名 → ctx.ops、helpers.make_manager 装载行 mgr._load_rules() → host.get("rules")._load_rules()。⑤补漏(5a3c8a75): 整仓验收 grep(全部 W2 名 × tests/)抓出跨批漏迁 9 处(test_trigger_events._handle_maintenance ×6 / test_web._assign_new_torrent ×2 / test_hr.save_state ×1 —— 名字归批与文件归批错位, 漏迁不红因转发还在), 修复后残留仅剩别名守阵 9 行(豁免)。⑥坑: 批次1 脚本首版替换串丢接收者(376 处全毁)被 diff 复核抓住回滚重做 —— 两坑落 pitfalls/testing/bulk-rename.md(捕获组回填+畸形形态检查 / 整仓验收 grep 兜底跨批遗漏), W3 复用。⑦src docstring(W1 边界注记移交)webui/server/__init__.py 提法改新名; WebviewMixin(views.py)docstring 自身字段名提法留 W3 回写。⑧实测: test.full 1894 passed + 3 skipped / 90%(35.9s rc=0), 覆盖率 91→90 系转发方法失去唯一测试调用方的预期漂移(未覆盖 1058→1106 与迁移掉的转发方法数同量级, 随 W3 删除)。基线 baselines/26-10-01-0700-w2-test-surface-newname.md。W3 待用户指令。
- **2026-10-01 W1 完成**: ①webui 路由域改新名 —— auth.py ×2(`web.token`)/ system.py(`web.results`)/ state.py + torrent_detail.py(`web.group_view`/`web.traffic_view`/`web.ensure_state`/`web.ensure_view`)/ touch_web_client → `web.touch` ×26(七路由文件)/ context.py:32 getattr 暗消费方改 `web.write_seq` 直取(替身与真身都有该属性, 兜底不再需要)。②范围外注记落定: `_hr_view_fields` **公开化改名 `hr_view_fields`**(routes/torrent_detail.py 直调静态方法, 私有下划线名不成立; views.py 4 处内部调用 + record.py 注释 + test_web.py 15 处同步; 不搬 hr 口, 搬移是行为面重排超出只改名边界)。③rules 三域: checking.py 组上下文 4 处改 `host.get("grouping")._*`(两处提局部变量 grouping); base.py ×2 改 `manager.ctx.state.record_execution/get_exec_record`; checking_meta.py 冷却 helper 宿主参数由「.state dict + .save_state() 鸭子类型」收敛为 **StateService**(`.data` + `.save()`), ops_mod.py ×3 传 `self._ctx.state`、full_checking.py ×1 传 `manager.ctx.state`、测试 ×3 直传 `mgr.ctx.state`(test_checking ×2 / test_ops ×1)。④注释与 static 清零: webui/module.py、runtime.py、lifecycle.py 注释改新名提法; static 四文件(app.js/decorate.js/hr.js/atlas components.css)的 `qbmanager._*` 提法改指 WebviewMixin/新名。⑤test_web 假替身接线: `_make_web_manager` 移除替身上的 `_web_token/_web_last_seen/_traffic_view/_web_results/_web_write_seq` 旧名属性, 数据改挂 `mgr.web.*`(group_view/traffic_view)并覆盖 `web.ensure_view/ensure_state`/`hr_view_fields`; web_env 双写 token(`web.token` 为 routes 读点, 旧名留 W2); 替身测试体 3 处(cmd_result 预置 / traffic_history 预置 / 缓存失效模拟)改 `web.results`/`web.traffic_view`/`web.write_seq`。真 manager 测试(test_qbmanager/test_web 大部)经别名层转发零改动。⑥验收: `grep -rn "manager\._" src/auto_qb/webui/` 为空; test.full 1894+3 / 91% 与 W0 持平(26 文件 +116/-122); 冻结守阵 4 例绿(qbmanager.py 未动)。基线 `baselines/26-10-01-0545-w1-web-routes-src-newname.md`。W2 待用户指令。
