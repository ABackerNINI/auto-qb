# HR 三参数解耦: 计划已批准(拉取间隔/复用窗/立即拉取) → 未开工

> 摘要: 用户实报三参数互相掣肘 —— 排查定根因一个: **「对账波周期」与「复用窗」实现上是同一个数**
> (service.py:1031 `expires_at = 波结束 + refresh_interval`, 全链路无第二节奏闸门),
> 插件「立即拉取一次」设计上就只是排空任务队列(server.py take_batch), 从不能触发取数。
> 计划(plans/26-09-30-0240)把三者拆正交: **拉取间隔**(refresh_interval 只改展示名, 新增
> healthy_ts+interval 节奏闸门; 基准取 healthy_ts 而非 fetched_at 保住失败波 60s 重试语义) /
> **数据复用窗**(新全局键 hr_check.reuse_window 默认 2H, 生效值 clamp ≤拉取间隔) /
> **立即拉取**(人工 force: 插件按钮+WebUI 按钮+--hr-once 三入口同一 request_refresh 通路;
> 跳两道闸但 min_interval/日额/Retry-After/时间窗照常)。❗唯一行为风险点: 缩复用窗必须与
> 新增间隔闸门同批落地, 否则取数频率 12H→2H 放大 6 倍。兼容: config.yml 零改动 / 旧站点
> 文件 expires_at 下次成功波自愈 / 插件对旧后端 404 降级纯排空。
> 触发: 拉取间隔, 复用窗, reuse_window, refresh_interval, 立即拉取, force, request_refresh,
> expires_at, healthy_ts, POST /api/hr/refresh, 对账波周期改名, take_batch
> 最后活动: 2026-09-30 02:50 (计划按拍板更新并提交)

## 状态

**计划已批准, 未开工。** 用户拍板(2026-09-30): ①人工动作统一叫「立即拉取」(原计划「立即对账」
因不直观被否) ②refresh_interval 展示名「拉取间隔」(原推荐「对账间隔」被否) ③其余按计划推荐
—— WebUI 要「立即拉取」按钮(每站+全部) / 插件按钮保留「立即拉取一次」只改行为 / 复用窗
clamp 不超拉取间隔。本切片轮仅文档(计划+本切片), 无代码变更, 沿用基线
[26-09-30-0024](../testing/baselines/26-09-30-0024-hr-counter-m3.md)。

## 未完成

- **实施**(按计划 §7 顺序): 配置层(§3.1) → 核心语义(§3.2+§3.6 走查 force, 与间隔闸门同批,
  ❗顺序硬约束) → 端点+runtime(§3.3/3.4) → WebUI → 插件(§3.5) → test.full+基线+收尾。
- 测试计划见计划 §6(reuse_window 配置四态 / service 八态含 force 保 min_interval /
  worker 消费语义 / WebUI 路由 / 插件真机端到端)。

## 指针

- [修改计划 26-09-30-0240 (已批准, §8 拍板记录)](../plans/26-09-30-0240-plan-hr-reuse-window-decouple.html) ·
  [上游计划 26-09-28-1932(HR v3 重建)](../plans/26-09-28-1932-plan-hr-verify-rebuild.html) ·
  [任务档案](../tasks/26-09-22-backend-partial-hr-verify.md)

**Refs:** memory-bank/plans/26-09-30-0240-plan-hr-reuse-window-decouple.html
