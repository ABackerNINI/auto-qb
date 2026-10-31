# 基线 · 1806 passed + 3 skipped / 91% —— HR 触发语义重构 (触发降级展示辅助 / 全量纳入 / 超额跳过)

**Refs:** memory-bank/tasks/26-09-30-backend-hr-trigger-semantics.md

> 摘要: 计划 plans/26-09-30-0559 全量落地 —— 「触发」降级纯展示辅助, 后端管理全量纳入。
> 判定层 `torrents/record.py` 三方法各管一件事: `check_hr_condition` 简化为纯本地下载触发判据
> (docstring 明令管理语义不得消费)、`check_hr_satisfied` 删触发前置(达标只看做种事实, 转移种
> 做种满也达标; `_local_satisfied` 承载本地判据, 递归风险源消失)、新增 `hr_managed`(需管束单点:
> 考察中恒真 / 放行显式短路 —— 不能写 `not satisfied` / 无证据·未接入按未达标兜底)。打标层
> `tags.py` 门禁改「放行短路 + 超额跳过 + satisfied 分流」, 超额基准抽 `_seed_exempt_baseline`
> (接入站 = `hr_check.required_seeding_time` 与取数侧同源 / 未接入站回落 `hr.required_seeding_time`,
> 基准 0 不跳过)。展示层 `resolve.py` `safety_display` 无证据分支改 satisfied×triggered 三分
> (达标 → safe「本地·达标」/ 未达标+触发 → danger「本地·未达标」/ 未达标+未触发 →
> **warning「本地·未达标(疑似辅种)」**), `SAFETY_UNKNOWN`/`SRC_UNVERIFIED` 退役, 来源统一
> `SRC_LOCAL`(SRC_* 7→6 个); 排除态在 `views.py` 组装层短路成空串(「不适用」由组装层保证)。
> 规则 `conditions.py` 三模式: condition-met = `hr_managed` / condition-not-met = 补集 /
> satisfied = 单条件(修「无证据+达标恒 False」拧巴); 表达式 `env.py` `tor.hr_condition_met`
> 换绑 `hr_managed`(**语义变化, 已发布表达式**) + 新增 `tor.hr_local_triggered`(纯本地触发)。
> 前端 hr.js 映射表 warning 档(hr-warn 黄, --warn 系) / 删 unknown·unverified, 三主题 CSS
> `.hr-warn` 与弹窗 lane 五处 unknown→warning 成对更新, popovers.html 虚线盾(dash 徽标)分支
> 退役; delete_flow.js `HR_NO_DELETE` 集合不动(只含 danger), 注释与档位清单同步。
> 真机 dry-run 走查零报错, 转移种按新语义进入 HR 打标分流。基线时间: 2026-09-30 07:09
> (develop @ 3113627, 本轮改动未提交, 等用户显式指令)。

TOTAL **1806 passed + 3 skipped / 91%**(12602 语句 / 995 未覆盖 / 4246 分支 / 414 partial, test.full 24.9s, rc=0) ——
较上基线 26-09-30-0555(1802)增 4 条: test_mixins_tags +3(打标三分: 转移种未满打 HR 标签 /
超额跳过三段基准 / 超额被动命中考察中仍打标 + 放行记录不打标, 净 +3 替换旧 not_met)、
test_torrents +1(`test_record_hr_methods_decoupled_structurally` 结构断言两方法互不调用)。
语义反转改写 8 文件: test_hr_resolve(未核实桶断言删, 三分断言) / test_torrents(行 4 语义反转:
纯辅种做种满 → satisfied True; check_hr_condition 不受站点身份影响) / test_hr(4 条「未触发不打标」
改「未触发但未达标仍打标」) / test_conditions(condition-met = 需管束全量纳入) / test_rule_base /
test_web(hr_view_fields 未接入 = warning 黄档 + 排除态空串 + 前端接线守阵换 warning 词表) /
test_expr_eval(+hr_local_triggered 断言) / test_trigger_events(on_change 轮 satisfied 翻转走分类通道)。

**提交前合并(12b018cf 键盘 W5-W7 波)后复测: 1817 passed + 3 skipped / 91%**(12668 语句 /
997 未覆盖 / 4268 分支 / 416 partial, 27.1s, rc=0)—— 两波共存全绿; stash→sync→pop 零冲突
(重叠 4 文件: plans/_index.md 索引重建 / state.js·popovers.html·test_web.py 两侧异区自动并合)。

## 本轮改动面

- 判定层 1: torrents/record.py(check_hr_condition 简化 / check_hr_satisfied 删触发前置 +
  _local_satisfied / 新增 hr_managed / 四入口排除短路)。
- 展示层 2: hr/resolve.py(SAFETY_WARNING 增, SAFETY_UNKNOWN·SRC_UNVERIFIED 删, 三分,
  __all__ 同步); webui/views.py(排除态组装层短路空串, docstring 档位词表更新)。
- 打标层 1: core/mixins/tags.py(放行短路 + 超额跳过 + satisfied 分流; _seed_exempt_baseline
  模块级函数; 导入 hr.resolve.HrIdentity 与 hr.service.SEED_EXEMPT_RATIO 无环)。
- 规则层 2: rules/conditions.py(HrCondition 三模式); rules/expr/env.py(hr_condition_met
  换绑 hr_managed + 新增 hr_local_triggered)。
- 前端 7: shared/hr.js(映射表/桶名/弹窗组装 dash 分支删)、delete_flow.js、filters.js、
  state.js(注释)、tpl/popovers.html(虚线盾分支删)、atlas+console+prism 三主题 views.css
  (.hr-warn / .src-unver 删)、三主题 dialogs.css 或 prism views.css 弹窗 lane 五处
  unknown→warning。
- 测试 8 + helpers.py(FakeTorrent 影子同步: check_hr_satisfied 删触发门 + 新增 hr_managed)。

## 迁移提示(交付用户)

- `tor.hr_condition_met` 与规则 `hr: condition-met` **语义已变**: 旧 ≈「本机下载触发(带站点侧
  短路)」→ 新 =「需管束」。存量规则若用它过滤「我下载的种子」, 手动迁移到新表达式
  `tor.hr_local_triggered`(纯本地触发判据)。存量规则/表达式无法静态识别, 需用户自查配置。
- 「疑似辅种」黄档(warning)不拦删除(HR_NO_DELETE 只含 danger), 删除确认框不点名 —— 与语义一致。
