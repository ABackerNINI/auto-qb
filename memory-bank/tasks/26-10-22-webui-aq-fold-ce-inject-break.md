# 26-10-22-webui-aq-fold-ce-inject-break — 修 WEBUI 流量卡开关恒显启用且无法保存: aq-fold 补 ce 透传 + e2e 回归守阵

**Status:** Done
**Added:** 2026-10-22
**Updated:** 2026-10-22
**Summary:** 修 WEBUI 流量卡开关恒显启用且无法保存: aq-fold 补 ce 透传 + e2e 回归守阵
**Topics:** webui-aq-fold-ce-inject-break
**Refs:** memory-bank/issues/26-10-22-0435-bug-webui-aq-fold-ce-inject-break.html

## 原始请求

1. 用户报障（承接上轮定性）：gtm 工具「关闭工具」后 `traffic_source.enabled=false` 正常落盘，但 WEBUI 仍显示开启、切换无法保存、重启无效、只能手改配置。并给出决定性事实：手改 `traffic_source.enabled=false` 后启动 auto-qb，`GET /api/config` 响应里该键确实是 false，界面仍显示「启用」——GET 与 UI 真相相反。
2. 定性落定后用户明确选择三项后续动作（均不选 commit）：① 入池 issue ② 补 e2e 回归守阵 ③ 坑档回写 memory-bank。
3. 本轮用户说「提交」——按 AGENTS.md 提交口径单点定义（「提交」= commit+push 一次走完）执行。

## 思考过程与决策

- **根因（浏览器级实证，非推断）**：`CONFIG_EDITOR` 全局 mixin（`app.js:913` 注册）的 `provide(){ce:this}` 挂在每个组件实例上，且每个实例带 mixin `data()` 新建的空 cfg 树（`tree:null`）。`6ad07b6a` 把折叠段头换成 `<aq-fold>` 组件后，hub-field 从直系孩子变成插槽内容；aq-fold 缺 `inject+provide` 透传 ⇒ 插槽内 hub-field 注入到 aq-fold 实例（空树）⇒ 开关回落 schema 默认 true 恒显「启用」+「默认」徽标、拨动写不进根树（「保存并应用」不出现）、磁盘不动（重启无效）；横幅走 `$root.tmSourceOff()` 读根树正确显「已关闭」——**开关与横幅自相矛盾正是用户所见**。
- **修法取舍**：单点透传（照抄仓库既有范式 `traffic_card.js:15` / `CE_FIELD_BASE` config_editor.js:1171）vs 全局兜底（`CONFIG_EDITOR.provide` 改 `{ce: this.ce || this}`）。选单点：全局兜底对二件皆缺的组件无效且触及每个组件；5 处 `<aq-fold>` 使用点全部位于 ce 提供者（根 / aq-traffic-card / hub-field）下游，无孤儿风险。
- **守阵判据设计**：既有 `views.spec`「三区同屏」只断言 schema 缺省 true，与断裂回落值同形 ⇒ 恒真，对注入断裂零鉴别力。新守阵必须钉**非缺省态**（磁盘 false → 显关闭）与**写路径往返**（拨动→脏标记→保存→PUT 载荷），并做**红/绿双向验证**（摘掉修复 6/6 全红才算 discriminate）。
- **第二现场**：同一 `<aq-fold>` 机制还包着规则卡「触发与节奏」meta 段（settings.html:237），第二现场用枚举字段 `execute_once`（磁盘 daily vs schema 默认 never）钉住，避免只在流量卡一处修。
- **不越界**（范围守恒）：不动全局兜底、不改其他组件、不顺手整理；坑档/基线/档案为 DoD 要求回写面，契约条目按前端 bug 修复先例（kbd-esc / time-tick）不新增。

## 实现计划

1. 复现与定位：Playwright 浏览器级复现 + 组件树遍历 + 三层 provide 探针，确认 `ce_name:"aq-fold"` / `raw:null` / `boolValue:true`。
2. 修 `ctl_bits.js` 的 `AQ_FOLD_COMPONENT`：补 `inject:["ce"]` + `provide(){ce:this.ce}`，写长注释记录事故机制。
3. 前后对照验证：修复前 checked=true 无脏标记；修复后 checked=false 显「关闭」、点击出现「有改动还没保存」+「保存并应用」。
4. 新建 e2e 守阵 `e2e/traffic-source-switch.spec.mjs`（读路径/写路径/规则卡第二现场，双皮肤 6 例，全打 @fast）。
5. 红/绿双向验证：修复在位 6/6 过；临时摘掉透传 6/6 全红（规则现场报 `Expected "daily", Received "never"` 即回落签名）；还原修复。
6. 全量闸门 `test.full` + e2e fast 全量 + kb.check。
7. 收尾回写：入池 issue（create-issue）→ 坑档（kb.new pitfall）→ 基线切片（kb.new baseline）→ 本档案 → issue 翻 Done → kb.wrap。
8. commit+push（用户本轮「提交」授权）。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 浏览器级复现 + 组件树遍历 + provide 探针定位 | Done(2026-10-22) |
| 2 | `ctl_bits.js` aq-fold 补 ce 透传 + 事故机制注释 | Done(2026-10-22) |
| 3 | 前后对照验证（checked/脏标记/保存钮） | Done(2026-10-22) |
| 4 | e2e 守阵 6 例（读/写/第二现场 × 双皮肤，@fast） | Done(2026-10-22) |
| 5 | 红/绿双向验证（摘修复 6/6 全红，还原后全过） | Done(2026-10-22) |
| 6 | test.full + e2e fast 全量 + kb.check 全绿 | Done(2026-10-22) |
| 7 | issue 入池 + 坑档 + 基线切片 + 档案 + issue 翻 Done | Done(2026-10-22) |
| 8 | commit + push | Done(2026-10-22) |

## 进度日志

### R0 · 立档 (2026-10-22)

根因确认与修复落地（工作树未提交态）：`ctl_bits.js` 单点透传；e2e 守阵 6 例双绿且摘修复全红；`test.full` 实测数字见本轮基线切片；坑档 `pitfalls/web-ui/mixin-ce-inject-break.md` 与 issue 26-10-22-0435 已回写。

- 2026-10-22 12:19 修 WEBUI 流量卡开关恒显启用且无法保存: aq-fold 补 ce 透传(inject+provide, 根因是 CONFIG_EDITOR 全局 mixin provide 被中间层组件截断致插槽内 hub-field 注入空 cfg 树); 新建 e2e 双皮肤 6 例守阵(非缺省态+写路径往返, 摘修复 6/6 全红); test.full 与 e2e:fast 全量双绿(数字见基线切片 26-10-22-1217); 坑档/基线/档案/issue 翻 Done 齐; 随提交入库
