# 26-10-01-backend-web-state-alias-disposal — 别名层处置: _WEB_STATE_ALIAS 与旧名委托层退役

**Status:** In Progress
**Added:** 2026-10-01
**Updated:** 2026-10-01
**Summary:** 计划 26-10-01-0350 拍板按推荐(D1 属性面永久保留 / D2 按模块域分批 / D3 W0 先行), W0 分诊清单 + 守阵立桩完成(纯文档与测试, 零产品代码): 逐名分诊落 JSON 清单(plans/26-10-01-0350-...triage.json, 20 别名 + 2 dunder + 57 单行转发 + 7 外观属性(D1 保留) + 17 内核自有 = 106 个类面成员; 波次 W1 src 消费方 15 名 / W2 仅测试 57 名 / W3 无消费方直删 5 名), 新增冻结守阵 tests/test_qbmanager_alias_freeze.py 4 例(AST 扫单行转发形状与清单双向比对: 清单外新增旧名委托即红 / 清单成员已删须同步清单 / kernel 成员不得退化 / counts 自洽)。分诊对计划数字的三处实测修正: ①委托成员实测 86(计划 81, 勘察基线差); ②「4 个纯内部属性对」实测仅 _next_state_flush_at 1 对; ③真实 src 消费方比 W1 原口径多三域(rules/actions/checking.py 组上下文 4 处 + rules/base.py 记录 2 处 + checking_meta.py 落盘 1 处, P6 后 rules 动作消费面)与 1 处 getattr 字符串暗消费方(context.py:32 _web_write_seq), 全部归入 W1。全量 1894 passed + 3 skipped / 91%。W1(路由与 src 侧改新名)待做。

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
| W1 | 路由与 src 侧改新名(消费方最少的一刀) | Open |
| W2 | 测试面迁移(按模块域分批, D2) | Open |
| W3 | 删除兼容层本体 + 回写 + 四场景走查回放 | Open |

## 进度日志

- **2026-10-01 W0 完成**: ①分诊清单落 `memory-bank/plans/26-10-01-0350-plan-web-state-alias-disposal.triage.json`(20 别名 + 2 dunder + 57 单行转发 + 7 外观(D1 保留) + 17 内核自有; 波次 W1×15 / W2×57 / W3×5 / 保留×24)。②守阵 `tests/test_qbmanager_alias_freeze.py` 4 例全绿(别名表==清单 / 转发面双向冻结 / kernel 不退化 / counts 自洽)。③test.full 1894 passed + 3 skipped / 91%(较上基线净增 4 = 守阵 4 例), 基线切片 `baselines/26-10-01-0443-w0-alias-triage-freeze.md`。④计划标 In Progress; conventions/modules.md 兼容层现状节补守阵指针。待用户评审清单后 W1 开工。
