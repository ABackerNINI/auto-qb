---
summary: 全局流量监视小工具(TM 替代)分步实施计划 — grilling 三轮收敛 + 计划产出
---

> 摘要: grilling 三轮 16 问收敛(用户两次纠正需求范围: TM 替代定位、多实例共享服务), 产出计划 26-10-16-0541(Open 待拍板), S0-S10 待逐项授权实施

# activeContext · global-traffic-monitor(26-10-16-0541)

用户要求:自写独立监视全局流量小工具 —— 独立于 auto-qb 主进程、开机自启、流量变化超阈值主动通知 auto-qb、设置进 auto-qb WebUI;前置可行性报告 26-10-13-1034(全局流量数据源滞后)。**用户中途两次纠正需求范围**:①工具定位 = TrafficMonitor 替代,仅记录整机流量历史(不是限速/provider 抽象);②工具是共享服务,auto-qb 是其配置方与消费者之一,须支持多 auto-qb 实例并发接入。

grilling 三轮 16 问全部按推荐拍板(口径=整机全适配器排回环;tools/global-traffic-monitor/ 独立包+独立 venv;psutil 采集;TM 兼容 dat 原子写;本地 HTTP 控制面 127.0.0.1:8099+token;Δ(上下行合计)≥100MiB 推通知+启动补发;工具自有 config、auto-qb WebUI 代理 PUT;多实例订阅+心跳租约+各自冷却;通知→auto-qb 重发快照刷新历史图;dat_path 双支持过渡;三平台自启由 WebUI 开关幂等注册)。

**产出**:计划 `memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html`(doc-status Open 待拍板)。步骤 S0–S10(骨架/采样/落盘/控制面/通知/自启/配置面/接收面/过渡/守阵/验收),默认参数表、顺序依赖、黄金法则映射、验收 E1–E6、风险对策俱全。行号基准 3ba069d7。

**未做**:零代码改动;未入池 issue;未立档(单会话,未达阈值);未提交(待用户「提交」显式指令)。S0–S10 实施需逐项授权。
