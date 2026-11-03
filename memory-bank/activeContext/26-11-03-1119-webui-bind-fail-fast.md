# webui-bind-fail-fast

> 摘要: 启动期 fail-fast + 跨平台占用者诊断已合入 develop; 回写 main-loop/web-runtime/core-runtime/overview 事实; 本轮 R2 修其测试面 CI 副作用(启动失败用例真跑 ss -ltnp → 注入探针替身 + 接线断言), 零 src 改动
> 最后活动: 2026-11-03 22:23
**Refs:** [计划](../plans/26-11-03-0930-plan-webui-bind-fail-fast.html) · [档案](../tasks/26-11-03-webui-bind-fail-fast.md) · [全量基线](../testing/baselines/26-11-03-2158-webui-bind-fail-fast-ci-sidefx.md) · [真机 RM01-06](../testing/real-baselines/26-11-03-1045-real-rm01-webui-bind.md) · [issue In Progress](../issues/26-11-03-0316-bug-webui-bind-failure-silent.html)

**当前状态**: S1-S6b 已完成并合入 develop(档案已标 Done); 本轮 R2 只动测试面(消除 CI 侧真实外部命令副作用), `src/` 零改动; 全量实测数字见 `commands run kb.baseline`。

**R0(2026-11-03 11:19):** S6b 收尾: 新建全量基线切片(4971 passed + 2 skipped / 99%); 回写 main-loop/web-runtime/core-runtime/overview 的启动期 fail-fast、port_owner、WebUIBindError、lifecycle_ready 事实; 新建 task 档案 26-11-03-webui-bind-fail-fast; issue 保持 In Progress

**R1(2026-11-03 11:45):** 收口 issue 与计划状态，标记已交付

**R2(2026-11-03 21:59):** 修复 CI sidefx 越界(越界项 POPEN ss -ltnp): 启动失败用例只验文案、未注入端口探针替身, Linux 上真跑 ss -ltnp; 改为注入 describe_port_owner 替身 + 断言探针仍被调用(host/port), 另补 ss argv 精确守阵; 零 src 改动, 未登记放行清单; 数字见 kb.baseline

**R3(2026-11-03 22:23):** 追加: tests/test_tmp_bootstrap.py 模块 docstring 改 raw 前缀清掉 \\T 无效转义(编译期 SyntaxWarning 归零, 字面语义与判据未动); notifier 按命令名拦截 PowerShell 的耦合入池(bug/light, Open, 未挂本档案); 全量数字见 kb.baseline
