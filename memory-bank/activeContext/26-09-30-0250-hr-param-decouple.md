# HR 三参数解耦: 已实施完成(拉取间隔/复用窗/立即拉取) → 待提交 + 真机端到端

> 摘要: 计划 plans/26-09-30-0240 **全量实施完成**(2026-09-30)。三参数拆正交:
> **拉取间隔**(refresh_interval 键不变, 展示名「对账波周期」→「拉取间隔」; service._refresh_locked
> 复用分支之后新增节奏闸门, 基准 = wave.healthy_ts, 失败波不推进基准 ⇒ 失败档下一轮 60s 重试语义不变) /
> **数据复用窗**(新全局键 hr_check.reuse_window 默认 2H; _finish_wave 时长换源
> min(reuse_window, 拉取间隔) clamp; 复用窗只管新鲜度) / **立即拉取**(force 跳过复用窗+拉取间隔
> 两道调度闸, min_interval/日额/Retry-After/时间窗照常)。三入口同一实现: 插件按钮 refresh-now →
> POST /api/hr/refresh(worker.force_fn) / WebUI「立即拉取·每站+全部」→ manager.hr.request_refresh /
> --hr-once → refresh_all(force=True)。worker.request_refresh 一次性 force 旗标(cond 保护,
> run_once 消费即清, 不落盘, 单一写线程假设不变)。展示层: next_wave_at=healthy_ts+interval、
> fresh_text 补「下次拉取」、blocking stale 文案「可点『立即拉取』提前」。实施期一处与计划文字的
> 偏差按 §6-④ 测试口径修正: 复用分支也必须被 force 跳过(计划「复用分支保持不动」指 REUSED 语义
> 本身)。❗风险点已按顺序硬约束落地: 间隔闸门与缩窗同批, service 八态测试钉死。
> 触发: 拉取间隔, 复用窗, reuse_window, refresh_interval, 立即拉取, force, request_refresh,
> expires_at, healthy_ts, POST /api/hr/refresh, 对账波周期改名, take_batch
> 最后活动: 2026-09-30 04:50 (实施完成, 全量 1792 passed, 未提交)

## 状态

**代码与测试全部完成, 未提交**(等用户「提交」指令)。改动面: 配置层 5 + hr 核心 4 + 端点 2 +
runtime/WebUI 3 + 插件 2 + 测试 5 + docs(keys.md / configuration.md / 扩展 README)+ 基线切片。
键面基线 147→148; 路由金清单 +1; 前端 hrs 守阵 +refreshing/refreshNote。
基线: [26-09-30-0450](../testing/baselines/26-09-30-0450-hr-reuse-window-decouple.md) ——
test.full **1792 passed + 3 skipped / 91%**(较上基线 +24 条, service 八态/worker 消费/端点路由/
WebUI 409 等全覆盖)。

## 未完成

- **提交**: 用户显式「提交」后 ship.commit 入库(回写件随主提交暂存)。
- **真机端到端**(计划 §6 插件行, 用户侧): 复用窗内点「立即拉取一次」→ 后端日志见波启动 →
  WebUI「上次取波」前进; 连点两次第二次因 min_interval 等待且文案可见。
- 兼容确认(用户侧, 低风险): 旧站点文件 expires_at(旧 12H 窗)最多再生效一次, 下次成功波按新公式自愈。

## 指针

- [修改计划 26-09-30-0240 (已批准, §8 拍板记录)](../plans/26-09-30-0240-plan-hr-reuse-window-decouple.html) ·
  [基线切片](../testing/baselines/26-09-30-0450-hr-reuse-window-decouple.md) ·
  [上游计划 26-09-28-1932(HR v3 重建)](../plans/26-09-28-1932-plan-hr-verify-rebuild.html) ·
  [任务档案](../tasks/26-09-22-backend-partial-hr-verify.md)

**Refs:** memory-bank/plans/26-09-30-0240-plan-hr-reuse-window-decouple.html
