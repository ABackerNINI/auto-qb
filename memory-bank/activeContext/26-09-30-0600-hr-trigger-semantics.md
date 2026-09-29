# HR 触发语义重构: 计划已成文 → 待批准开工

> 摘要: 三轮讨论收敛(2026-09-30 会话)后计划落盘 plans/26-09-30-0559。起因: WebUI 实测出现
> 「未核实(本地不触发)」误导 —— 转移种子 downloaded=0 被当无义务(PT 圈常态), 且无证据路径下
> 「达标 ⇒ check_hr_condition 返回 False」导致做种已满的超额老种也落「未核实」。定稿模型:
> **「触发」降级纯展示辅助**(check_hr_condition = 纯本地下载判据, 只用于区分「本机下载 vs 疑似辅种」);
> **后端全量纳入**(配置 HR 站点所有种子进打标/管束分流, 单点 check_hr_satisfied 删触发前置,
> ratio 通道保留); **新增 hr_managed**(需管束 = 考察中 ∨ (无证据/未接入 ∧ 未达标), 放行类显式短路 ——
> 不能写 not satisfied, 放行记录种子本地没做够也不许管); **超额老种跳过打标**(站点侧未命中考察中时,
> 基准接入站=hr_check.required_seeding_time 与取数侧同源 / 未接入=hr.required_seeding_time);
> **疑似辅种 = warning 黄档**(用户拍板, 非 danger —— delete_flow 的 HR_NO_DELETE 只含 danger,
> 天然不拦删除); SAFETY_UNKNOWN/SRC_UNVERIFIED 退役; 规则 condition-met → hr_managed、
> satisfied 改单条件(修「无证据+达标恒 False」拧巴)、新增 tor.hr_local_triggered 保辅种判别力;
> 零配置变更。文档业务词口径: 不用判定表行号/档位字母, 用「考察中/毕业达标/未达标终态/免罪/
> 放行记录/无站点证据/未接入」。
> 触发: 未核实, 本地不触发, 疑似辅种, warning, hr_managed, 全量纳入, 超额跳过, 触发语义,
> check_hr_condition, check_hr_satisfied, tor.hr_local_triggered, SRC_UNVERIFIED, 标签铺面
> 最后活动: 2026-09-30 06:00 (计划成文, 未批准未实施)

## 状态

**计划文档已写, 未批准未实施**(本轮只写 plans/ 一份文件, 零代码变更)。
[修改计划 26-09-30-0559](../plans/26-09-30-0559-plan-hr-trigger-semantics.html) ——
设计经 2026-09-30 会话三轮讨论拍板: ①全量纳入+触发降级 ②疑似辅种 warning ③超额跳过不打标。

## 未完成

- **用户批准计划** → 批准后按 §10 步骤实施(后端 5 文件 → 前端 2 文件 → 测试 3 文件 → test.full 基线)。
- 迁移提示交付: `tor.hr_condition_met` 语义变化(→需管束), 旧「本机下载判别」用途迁移到
  `tor.hr_local_triggered`; 存量规则无法静态识别, 落地后提示用户自查。

## 指针

- [修改计划 26-09-30-0559 (Open)](../plans/26-09-30-0559-plan-hr-trigger-semantics.html) ·
  [上游计划 26-09-28-1932 (判定收口重建)](../plans/26-09-28-1932-plan-hr-verify-rebuild.html) ·
  [任务档案 tasks/26-09-22-backend-partial-hr-verify](../tasks/26-09-22-backend-partial-hr-verify.md)

**Refs:** memory-bank/plans/26-09-30-0559-plan-hr-trigger-semantics.html
