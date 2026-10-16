---
summary: 全局流量监视小工具(TM 替代)分步实施计划 — grilling 三轮收敛 + 计划产出 + S0 包骨架已落地
---

> 摘要: grilling 三轮 16 问收敛(用户两次纠正需求范围: TM 替代定位、多实例共享服务), 产出计划 26-10-16-0541(Open); S0 包骨架已实施(26-10-16-0601), S1–S10 待逐项授权
> 最后活动: 2026-10-16 06:01

# activeContext · global-traffic-monitor(26-10-16-0541)

用户要求:自写独立监视全局流量小工具 —— 独立于 auto-qb 主进程、开机自启、流量变化超阈值主动通知 auto-qb、设置进 auto-qb WebUI;前置可行性报告 26-10-13-1034(全局流量数据源滞后)。**用户中途两次纠正需求范围**:①工具定位 = TrafficMonitor 替代,仅记录整机流量历史(不是限速/provider 抽象);②工具是共享服务,auto-qb 是其配置方与消费者之一,须支持多 auto-qb 实例并发接入。

grilling 三轮 16 问全部按推荐拍板(口径=整机全适配器排回环;tools/global-traffic-monitor/ 独立包+独立 venv;psutil 采集;TM 兼容 dat 原子写;本地 HTTP 控制面 127.0.0.1:8099+token;Δ(上下行合计)≥100MiB 推通知+启动补发;工具自有 config、auto-qb WebUI 代理 PUT;多实例订阅+心跳租约+各自冷却;通知→auto-qb 重发快照刷新历史图;dat_path 双支持过渡;三平台自启由 WebUI 开关幂等注册)。

**产出**:计划 `memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html`(doc-status Open)。步骤 S0–S10(骨架/采样/落盘/控制面/通知/自启/配置面/接收面/过渡/守阵/验收),默认参数表、顺序依赖、黄金法则映射、验收 E1–E6、风险对策俱全。行号基准 3ba069d7。

**R1 · S0 已实施(2026-10-16-0601,clone @ 46d2ea11)**: 用户指令「实施计划S0」= 对 S0 的显式授权(S1–S10 不动)。新建 tools/global-traffic-monitor/ 完整骨架 11 文件(pyproject[hatchling/src 布局/入口 gtm/依赖仅 psutil+filelock/dev 组 pytest/自带 pytest 配置]、src/gtm/ 八文件[六个模块为 S1–S5 占位]、README、tests/test_smoke.py),零 auto-qb 文件触碰。出口判据全过: 独立 venv 下 `gtm --version`=gtm 0.1.0;根环境 import psutil 仍 ModuleNotFoundError(隔离验证);工具冒烟 4 条全过。坑: 工具目录内 uv run pytest 会拾取仓库根 pytest.ini → 已在工具 pyproject 补 [tool.pytest.ini_options],坑档 pitfalls/testing/nested-pytest-config.md。档案 tasks/26-10-16-backend-global-traffic-monitor.md(立档阈值 #4 命中: 已产出计划)。基线切片 testing/baselines/26-10-16-0601-global-traffic-monitor-s0.md(根 test.full 回归)。未提交(待用户「提交」指令)。

**待办**:S1(采样器 sampler)待用户显式授权实施。
