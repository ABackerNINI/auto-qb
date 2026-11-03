# 26-11-03-webui-bind-fail-fast — WebUI 启动期 bind 失败 fail-fast + 诊断

**Status:** Done
**Added:** 2026-11-03
**Updated:** 2026-11-03
**Summary:** 已交付(合入 develop 8e6b4bdc): WebUI 启动期 bind 失败 fail-fast + 跨平台占用者诊断
**Topics:** webui-bind-fail-fast
**Refs:** memory-bank/plans/26-11-03-0930-plan-webui-bind-fail-fast.html, memory-bank/testing/baselines/26-11-03-1112-webui-bind-fail-fast.md

## 原始请求

1. 2026-11-03 端口盘点的只读发现: `web.port` 被占用时 uvicorn 后台线程 bind 失败, 异常被吞成一条 ERROR 日志, 主程序继续运行; 用户看到进程活着但 WebUI 不可用, 且没有「谁占了端口 / 怎么改」的可操作信息。
2. 要求产品侧显式暴露: 绑定失败在启动阶段 fail-fast(进程退出并给出端口/占用者提示), 或至少标为不可用并持续可见; 不要只留一条 ERROR; `web.port` 保持固定, 不做动态分配。
3. 用户显式授权认领 issue `26-11-03-0316-bug-webui-bind-failure-silent` 并按 grilling Q1→Q6 逐题拍板 A / P1 / R1 后开工。

## 思考过程与决策

计划单点: [plans/26-11-03-0930-plan-webui-bind-fail-fast.html](../plans/26-11-03-0930-plan-webui-bind-fail-fast.html), D1-D10 见该计划 §10。关键拍板:

- **D1/D2**: 选 A 路线 —— web bind 失败无条件 fail-fast 带走主进程; 推翻「一个端口占用不该带走整个程序」; RM01-06 保留场景、改判据(不改场景不删用例)。
- **D4/D8**: 退出契约 P1 + 抛点 R1 —— `WebUIBindError(AutoQbError)` 在 `WebUIModule.start` 抛, 走 `AutoQbError` 通道(退出码 1 / 单行 stderr / 无堆栈); 低层 `start_web_server` 保持返回 handle 的原契约(热重载 `apply` 行为不变)。
- **D5/D9**: `start_all` 移入 `try/finally`, 接受连带修掉既有 `HrChannelBindError` 启动期漏锁; `lifecycle_ready` 闸门保证失败启动不写空态 `state.json`。
- **D6**: 占用者取证边界 —— 1.5s 总预算、单次 PowerShell、三态降级、探针结果只进日志(不进异常消息 / stderr / notify)。

## 实现计划

1. `infra/port_owner.py` + 测试: 三平台探针、三态降级、1.5s 预算。
2. `webui/server/lifecycle.py`: `WebUIBindError` + `_bind_message`; 低层 `start_web_server` 契约不变。
3. `webui/module.py`: `WebUIModule.start` 检查 `handle.started`, 失败落 INFO 诊断块后抛错。
4. `core/qbmanager.py`: `start_all` 移入 try + `lifecycle_ready` 闸门 + 任意路径释放锁。
5. 单测与真机 RM01-06 判据反转 + docs 文案(S5)。
6. 收尾闸门(S6): 全量实测 + 基线切片 + DoD 回写 + kb.wrap。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | `infra/port_owner.py` + `tests/test_port_owner.py` | Done(2026-11-03) |
| S2 | `WebUIBindError` / `_bind_message`(lifecycle, 低层契约不变) | Done(2026-11-03) |
| S3 | `WebUIModule.start` 抛点 + INFO 诊断块 + 探针接线 | Done(2026-11-03) |
| S4 | `start_all` 移入 try + `lifecycle_ready` 闸门 + 锁释放 | Done(2026-11-03) |
| S5 | 单测 / RM01-06 判据反转 / docs 文案 | Done(2026-11-03) |
| S6a | 全量测试实测: 4971 passed + 2 skipped, 覆盖率 99% | Done(2026-11-03) |
| S6b | 基线切片 + DoD 回写 + kb.wrap | Done(2026-11-03) |

## 进度日志

### R0 · 立档 (2026-11-03)

分支 `feat/webui-bind-fail-fast`(基于 `1d4f31fa`)已实现 S1-S5; 真机 RM01-06 复测绿(见 [real-baselines/26-11-03-1045-real-rm01-webui-bind.md](../testing/real-baselines/26-11-03-1045-real-rm01-webui-bind.md)); 全量实测 4971 passed + 2 skipped / 覆盖率 99%, 基线切片 [26-11-03-1112](../testing/baselines/26-11-03-1112-webui-bind-fail-fast.md)。分支未合入 develop, issue 保持 In Progress。

- 2026-11-03 11:19 S6b 收尾: 新建全量基线切片(4971 passed + 2 skipped / 99%); 回写 main-loop/web-runtime/core-runtime/overview 的启动期 fail-fast、port_owner、WebUIBindError、lifecycle_ready 事实; 新建 task 档案 26-11-03-webui-bind-fail-fast; issue 保持 In Progress

### R1 · 交付 (2026-11-03 11:44)

- 已交付: 8 笔提交(`e2353608..8e6b4bdc`)合入本地 `develop` `8e6b4bdc`; 分支 `feat/webui-bind-fail-fast` 与 develop 同一提交。
- issue `26-11-03-0316-bug-webui-bind-failure-silent` 与计划 `26-11-03-0930-plan-webui-bind-fail-fast` 由 In Progress 翻到 Done。
- 实测数字不在此手抄: 全量见 [baselines/26-11-03-1112](../testing/baselines/26-11-03-1112-webui-bind-fail-fast.md), 真机见 [real-baselines/26-11-03-1045](../testing/real-baselines/26-11-03-1045-real-rm01-webui-bind.md)。

- 2026-11-03 11:45 收口 issue 与计划状态，标记已交付
