# HR 在线核实 v3 重构后全面复审(安全/稳定性/缺陷)

> 摘要: 应用户要求对 v3 波次模型(05a8415)做重写后彻底复审: hr/ 全部 20 文件(约 6000 行)+ record.py 桥 + WebUI 路由/前端 + 配置五层 + qbmanager 接线逐文件通读, 按 security-review 方法论 + 黄金法则对审。**总评通过, 附 1 高危**: H1 站点 Retry-After 不跨波生效(service `_do_wave` 失败分支写 `retry_after_until` 后不 commit, `hold()` 每波重读盘 ⇒ 指令丢失 + mark() 不执行 ⇒ 60s 节奏重试到日额 240 烧尽; .torrent 路径的 Retry-After 还被计成种子失败); M1 登录失效路径不记间隔基准(烧日额 + 登录恢复后当日核实可能停摆到零点); M2 站点文件 schema 比程序新时空数据照常取数并覆写新版文件。L1–L4: judge_record tie-break 文档未实现 / 完整 URL 进日志无脱敏钩子(当前 preset 无 passkey) / skip_local_verify=true 时 confirm-empty 可 CSRF(非默认) / 排序方向仅波内校验(纵深防御可兜底)。I1–I5: 死代码簇(_prune_index 重复/HrStoreCorrupted 未用等) / 两处 time.time() 绕过注入时钟 / parse 递归无上限 / CLI confirm-empty 不校验站点名 / 0600 Windows 不生效。安全面核验全绿: 零 cookie 边界、端点四道防线(token 常数时间/origin/URL 白名单/127.0.0.1 独占)、回传防伪、bencode 深度上限、WebUI 无 v-html、配置三层未知键拦截。递归修复(05a8415)复核无环语义等价。实测 1736 passed + 3 skipped(90%)。
> 触发: HR 在线核实, 审计, Retry-After, 登录失效, 站点文件覆写, 认领链, test_docs_forms, hr_check, 安全复审
> 最后活动: 2026-09-29 06:13
> (报告出厂: reports/26-09-29-0404-report-hr-verify-v3-audit.html; 同日 0512
> 增补第 9–12 章: 端到端流程/情况处置/配置字段/默认画像, 扩展侧双闸与 POLL_MINUTES=1 均从扩展代码核实;
> 0506 **设计裁决追记 §13**: ①轻量波已否决(撤销「未实现」结论, test_light_wave 名不符实降级观察项)
> ②「remain==0×档位A」矛盾检测无口径(同撤) ③**流转守恒是骤降保护的升级版, A 只流向 B/C/D, 骤降
> 不构成漏 HR 面且基线高水位永不回落会在站点合法清账后永久冻结 —— 裁决移除骤降保护, 防伪收敛为
> 守恒+零行戳两道; 实施触点已清点(§13.3), 待用户下令动代码); 0530 **§13.4 观察期设计依据确认**:
> 「缺席 ≠ 没证据」—— 行 4 特例不可塌缩进缺席(考察中种子本地达标恰不能放行, 观察期=拒绝单次缺席
> 下结论, 2 波+位置覆盖, 零成本), 用户认可存档); 0550 **实施落地(用户「开工」)**: §13.3 骤降移除
> + H1/M1/M2 修复全部完成 —— 防伪收敛为守恒+零行戳两道, Retry-After 落盘/登录 mark/schema 跳过门,
> 新增 4 回归 + light-wave 用例重写; test.full 1739 passed + 3 skipped(90%), 基线切片 26-09-29-0550;
> 明细见报告 §13.5 与任务档案进度日志。**代码未提交(等显式指令)**

## 状态

**审计完成, 报告已出厂(Done)** —— [26-09-29-0404-report-hr-verify-v3-audit](../reports/26-09-29-0404-report-hr-verify-v3-audit.html)。
发现**未修复**(本轮只审计; 用户未授权修复/入池): H1/M1/M2 与 L1–L4 等待用户定夺 —— 修复还是入池 issue 由用户拍板。
测试缺口单点: 「取数失败路径的跨波状态持久化」service 级零覆盖(H1/M1 同根), 修时必须补三类用例
(Retry-After 跨波生效 / 登录失效节奏 ≥ min_interval / schema 过新不取数不覆写)。

## 未完成

- **本轮代码未提交**(等显式「提交」指令): 骤降移除 + H1/M1/M2 已实施(0550) —— 防伪收敛为
  守恒+零行戳两道, Retry-After 落盘/登录 mark/schema 跳过门; test.full 1739+3(90%),
  基线切片 26-09-29-0550; 明细见报告 §13.5 与任务档案进度日志。
- **真机走查**(上轮遗留, 仍开放): chrome://extensions reload 扩展 → `--hr-once` → 主程序跑一轮 →
  `--hr-status` 核对; 顺带真机验证 H1 修复后的 Retry-After 行为。

## 指针

- [审计报告 26-09-29-0404 (本轮, Done)](../reports/26-09-29-0404-report-hr-verify-v3-audit.html) ·
  [计划 26-09-28-1932 (v3, Done)](../plans/26-09-28-1932-plan-hr-verify-rebuild.html) ·
  [上轮审计 26-09-28-0030](../reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html) ·
  [任务档案](../tasks/26-09-22-backend-partial-hr-verify.md)

**Refs:** memory-bank/reports/26-09-29-0404-report-hr-verify-v3-audit.html, memory-bank/plans/26-09-28-1932-plan-hr-verify-rebuild.html
