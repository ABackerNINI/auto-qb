# tracker URL 源头脱敏(分步计划已派生, 未开工)
> 摘要: 把凭据脱敏从"日志出口"提到 **qbapi 拉取即脱敏**。方案 B(单轨 + 瞬时原文 + mask 形态)已转成 **S1–S4 分步实施计划**(26-10-07-0055, 基树 20bd2157 重取证), **仍未开工**。三条关键结论: ① 方案 B 四波次本体均未落码(报告 meta「已实施」指前置日志脱敏 26-09-21-1408); ② **编排修正**: 详情 API 收口与删除改道必须同批——拆开则 W2~W3 之间移除功能必断(前端提交 mask 值而旧后端直传 qB); ③ mask 规格已定案为 R1–R9(虚拟条目透传/全值 hash/不按参数名挑/不加盐 ≥16 位/path 末段高熵才 hash)。
> 触发: tracker URL, passkey, 凭据, 脱敏, 泄露, 源头脱敏, mask, 编辑下线, 汇报基线, reannounce, 分步计划, S1-S4
> 最后活动: 2026-10-07 00:55

**Refs:** memory-bank/tasks/26-10-07-webui-tracker-url-sanitize.md,memory-bank/plans/26-10-07-0055-plan-tracker-url-sanitize-planb.html

## 状态

**分步实施计划**(2026-10-07 本轮产出): [../plans/26-10-07-0055-plan-tracker-url-sanitize-planb.html](../plans/26-10-07-0055-plan-tracker-url-sanitize-planb.html)
(基树 `20bd2157` 全部行号重取; 批次 = S1 源头归一化 → S2 编辑下线 → S3 收口切换(原子) → S4 守阵+红验)。

**可行性报告与方案论证**(三方案对比 · 依赖核验 · 风险): [../plans/26-09-22-1801-tracker-url-source-sanitize-plan.html](../plans/26-09-22-1801-tracker-url-source-sanitize-plan.html)
(基树 `00c61f8`; 行号已过时——D1–D5 重构后确认机制有第二直读点 runtime.py:474, 以分步计划的重取行为准)。

**已定口径**(两轮讨论定案, 全文规格化在分步计划 §01/§03): mask 形态(保形状+值全 hash, 不按参数名挑, 不加盐) · 编辑下线 · 删除=「当场重取+用完即弃」(单轨+瞬时原文) · 汇报基线进程内豁免不改标识。2026-09-23 当轮的仓库体检(健康, 1191 passed)与「快进后工作区文件消失」坑复发记账已沉淀(见 [../pitfalls/git/history-integration.md](../pitfalls/git/history-integration.md) 与 `19fa6eed`)。

## 待办(下一步从这里接)

1. **开工指令**: 用户说开工即按分步计划 S1(源头归一化, 零行为)起, 每批独立提交; 排期结构已由 S1–S4 定案(旧「决策点 4」的 W1+W2 止血编排已被 S2/S3 原子批取代)。
2. **提交**: 本轮产物(分步计划 HTML + tasks 档案 + 切片更新 + 旧计划档回写)**尚未说「提交」**。

## 单点指针

- **分步实施计划(开工按这个)** → [../plans/26-10-07-0055-plan-tracker-url-sanitize-planb.html](../plans/26-10-07-0055-plan-tracker-url-sanitize-planb.html)
- 可行性报告(方案论证与依据) → [../plans/26-09-22-1801-tracker-url-source-sanitize-plan.html](../plans/26-09-22-1801-tracker-url-source-sanitize-plan.html)
- 任务档案 → [../tasks/26-10-07-webui-tracker-url-sanitize.md](../tasks/26-10-07-webui-tracker-url-sanitize.md)
- 已修的日志端脱敏(issue) → [../issues/26-09-21-1408-bug-web-tracker-url-passkey-log.html](../issues/26-09-21-1408-bug-web-tracker-url-passkey-log.html)
- 凭据脱敏长效约定 → [../conventions/code-style.md](../conventions/code-style.md)「日志规范」
- 合并后工作区文件消失(含快进) → [../pitfalls/git/history-integration.md](../pitfalls/git/history-integration.md)
