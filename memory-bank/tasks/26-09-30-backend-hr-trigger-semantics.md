# 26-09-30-backend-hr-trigger-semantics — HR 触发语义重构 (触发降级展示辅助 / 全量纳入)

**Status:** Done
**Added:** 2026-09-30
**Updated:** 2026-09-30 07:47
**Summary:** 计划 plans/26-09-30-0559 全量落地:「触发」降级纯展示辅助(check_hr_condition = 纯本地下载判据), 后端管理全量纳入(check_hr_satisfied 删触发前置成为义务已了单点, 新增 hr_managed 需管束单点), 打标改「放行短路+超额跳过+satisfied 分流」(超额基准 _seed_exempt_baseline 与取数侧同源), 展示三分(疑似辅种 = warning 黄档, SAFETY_UNKNOWN/SRC_UNVERIFIED 退役), 规则 condition-met=hr_managed + satisfied 单条件, 表达式 tor.hr_condition_met 换绑 hr_managed(语义变化) + 新增 tor.hr_local_triggered。test.full 1806 passed + 3 skipped / 91%, 真机 dry-run 零报错。已随 **87d154c** 入库(推 Gitee 核验经后继 87f3437 父链可见)。
**Topics:** backend-hr-trigger-semantics

## 原始请求

用户: 「实施计划26-09-30-0559-plan-hr-trigger-semantics.html」—— 按 plans/26-09-30-0559(2026-09-30 会话三轮讨论拍板)实施 HR 触发语义重构。

## 思考过程与决策

- **判定层三方法各管一件事**(计划 §3): `check_hr_condition` 简化为纯本地触发判据(唯一消费点是前端区分「本机下载 vs 疑似辅种」); `check_hr_satisfied` 删「未触发 ⇒ 未达标」前置, 本地判据抽 `_local_satisfied` 私有方法(两处回落共用), 防递归注释段随递归源消失; 新增 `hr_managed` 按计划伪代码落地 —— 放行必须**显式**短路, 不能写 `not check_hr_satisfied()`(放行记录 + 本地未做够也不许管束)。
- **打标层**(§4): 门禁从「check_hr_condition 不过就早退」改三段; 超额基准抽模块级 `_seed_exempt_baseline(rec)`(接入站读 `hr_check.required_seeding_time` 与取数侧 `_build_objects` 同源, 未接入站回落 `hr.required_seeding_time`, 基准 ≤ 0 不跳过); 复用 `hr/service.py` 的 `SEED_EXEMPT_RATIO = 3.0` 常量, 避免两处各写 3×。导入链核过无环(core → hr 单向)。
- **展示层**(§5): `safety_display` 无证据分支 satisfied×triggered 三分; 「未接入但未触发」从 SAFETY_NONE 改产 **warning 疑似辅种**(计划拍板: 黄档警示不拦删); 排除态维持「不适用」空白 —— `safety_display` 的 None 分支无法区分排除与未接入, 由 `views.py` 组装层先把排除态短路成空串(计划点名该实现路径)。
- **规则/表达式**(§6): condition-met/condition-not-met 切 `hr_managed`; satisfied 改单条件; `tor.hr_condition_met` 换绑 `hr_managed` 并在 env.py 注释标注语义变化与迁移去向; 新增 `tor.hr_local_triggered` 保辅种判别力。不带自动迁移(存量无法静态识别), 落地后在基线切片与收尾总结交付迁移提示。
- **前端**: HR_SAFETY_CLASSES/BUCKETS 换 warning 词表; HR_SRC_CLASSES/BUCKETS 删 unverified; 弹窗 lane === "unknown" 的 dash 徽标分支删除(warning 按 check 处理), popovers.html 的虚线盾 `v-else` SVG 分支随之退役; `HR_NO_DELETE` 集合不动(只含 danger), 仅同步注释与批量提示档位清单; 三主题 CSS `.hr-unk`/`.src-unver` 删、`.hr-warn` 与弹窗 lane 五处 unknown→warning 增(--warn 令牌三主题本就有)。
- **不变项**(§7)核验: 站点权威/排除表优先级/取数对象集/零配置变更全未触碰; 打标是加法不回撤历史标签。

## 实现计划

按计划 §10 十步: record.py → resolve.py → tags.py → conditions.py → env.py → views.py → hr.js+样式表 → delete_flow.js → 测试 → test.full + dry-run。实际执行与计划一致, 额外发现并同步: helpers.py FakeTorrent 影子实现(check_hr_satisfied 影子删触发门 + 补 hr_managed)、test_trigger_events 维护节奏测试、filters.js/state.js 桶名注释、三主题 dialogs.css 弹窗 lane 色、popovers.html dash 徽标模板。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | record.py 三方法重构 | ✅ 完成 |
| 2 | resolve.py 档位增删与三分 | ✅ 完成 |
| 3 | tags.py 打标门禁三段 | ✅ 完成 |
| 4 | conditions.py + env.py 切换 | ✅ 完成 |
| 5 | views.py 排除态短路 | ✅ 完成 |
| 6 | 前端 hr.js + 三主题 CSS + popovers/delete_flow/filters/state 注释同步 | ✅ 完成 |
| 7 | 测试改写与新增(8 文件 + helpers) | ✅ 完成 |
| 8 | test.full 基线 + dry-run 走查 | ✅ 完成 |
| 9 | 长青文档回写(overview/web-runtime/conditions-and-actions) + 基线切片 | ✅ 完成 |
| 10 | commit + push | ✅ 完成(87d154c, Gitee 已可见) |

## 进度日志

- **2026-09-30 07:09**: 全量落地。test.full **1806 passed + 3 skipped / 91%**(12602 语句 / 995 未覆盖, 24.9s, rc=0), 较上基线 26-09-30-0555(1802)净增 4 条(打标三分 +3 / 结构断言 +1), 语义反转改写 8 测试文件。真机 dry-run 走查: 零 ERROR/Traceback, 未达标转移种按新语义在维护轮进入 HR 打标分流(dry-run 不落盘), RecursionError 无复发。基线切片 [testing/baselines/26-09-30-0709](../testing/baselines/26-09-30-0709-hr-trigger-semantics.md)。**未提交**。
- 范围外发现(未动, 待用户决定是否入池): `webui/static/shared/config_hub.js:93` 仍在文档化已废弃配置键 `hr_check.unknown_policy`(26-09-28-1932 判定收口已删该键, models.py 注释可证) —— config 编辑器提示文案漂移。
- **2026-09-30 07:47**: 上面那条范围外漂移用户拍板直接修(未入池): config_hub.js HUB_HELP 删 `hr_check.unknown_policy` 死条目(8 行, rel 引用的 verified_ttl 同批已删); 「未核实怎么算」v3 语义硬编码为行 4 本地兜底, 由 schema hr.py sites.enabled help 承载, webui grep 无其它残留。先合并远端 87f3437(危险操作独立操作层波)再复测: **1829 passed + 3 skipped / 91%**(基线 [26-09-30-0747](../testing/baselines/26-09-30-0747-webui-config-hub-drift.md)), 与上基线 1210 通过数持平, 零测试增删。修复 + 收尾回写随本轮提交入库。

**Refs:** memory-bank/plans/26-09-30-0559-plan-hr-trigger-semantics.html, memory-bank/testing/baselines/26-09-30-0709-hr-trigger-semantics.md, memory-bank/testing/baselines/26-09-30-0747-webui-config-hub-drift.md
