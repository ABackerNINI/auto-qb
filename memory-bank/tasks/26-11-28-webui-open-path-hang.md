# 26-11-28-webui-open-path-hang — WEBUI 打开目标文件夹偶发卡死：取证与异步隔离修复

**Status:** In Progress
**Added:** 2026-11-28
**Updated:** 2026-11-28
**Summary:** WEBUI 打开目标文件夹偶发卡死：取证与异步隔离修复
**Topics:** webui-open-path-hang
**Refs:** memory-bank/plans/26-11-28-0730-plan-webui-open-path-hang.html, memory-bank/issues/26-11-28-0731-bug-webui-open-path-hang.html

## 本篇只回答

怎么在「先稳定复现并抓到根因」的前提下修复 WEBUI 打开目标文件夹偶发卡死，以及抓不到现场时如何诚实降级为加固。方案细节见计划（Refs 第一条）。

## 原始请求

1. WEBUI 使用「打开目标文件夹」时偶尔导致 auto-qb 卡死，彻底无响应，WEBUI 断联，无相关 log，无法 Ctrl+C 退出。
2. 触发平台：Win11 uv 直跑；触发方式：选中种子按键盘 o；右键菜单未测但猜测一致（后端问题）。
3. 只是偶尔触发，强关终端重启后选同种子正常。
4. 先分析原因（已完成：同步 Shell 调用占死 uvicorn worker + 置前 Win32 调用两个嫌疑面）。
5. 后续指令：grilling 然后出修复计划；Q4 选 c+a——**需要找到根因、稳定复现，再确定方案是否适用**；Q8 强调常规 <2s 无感、慢 Shell 显示「正在执行」、避免用户再点一次；其余按推荐。

## 思考过程与决策

四轮 grilling（Q1-Q12 + Q8a/b/c）全部拍板，逐条记在计划 §06（D1-D15）。关键取舍：

- **根因未定不先修**：用户明确要求先稳定复现再定方案，故设计树根改为「取证 gate」，修复是 gate 通过后的后置分支；gate 空手走「未确证加固」而非宣称修复（D4/D7/D14）。
- **命令队列不能直投**：handler 在主循环同步执行，投进去只是把阻塞搬到主循环、违反单一写线程；改走 transfer 已验证的 deferred 回执通道（后台跑完→回灌→主循环 set_result）（D1/D9）。
- **时延与状态的平衡**：常规 <2s 不弹 toast（延迟 2s 才显示 busy），慢 Shell 有「正在执行」，同目标在途连点被 inflight Set 吞掉（D8/D10/D11）。
- **置前不倒退**：置前是历史三轮修出的体验，保留但搬进同一隔离边界、加总时限，失败静默语义不变（D3）。
- **诊断不碰配置**：faulthandler 看门狗用环境变量开关，绕开「新配置键进 validate_config+schema」的成本（D12）。

三份只读事实清单（命令队列/日志/真机基建、诊断工具、异步回执）均已并入计划 §02/§03，避免计划落地时重新调查。

## 实现计划

分三期，完整步骤与判据见计划 §04：S0 取证 gate（埋点+看门狗、故障注入、真机复现、适用性判决）→ S1 修复（后端 deferred 回执 + 隔离；前端三态 + 幂等闸）→ S2 验收（守阵同步 + 真机 20+20 次）。gate 不通过走 S1' 加固分支。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0.1 | 端点 INFO / Shell DEBUG 耗时埋点 + 环境变量 faulthandler 看门狗 | Open |
| S0.2 | 故障注入：patch `_win_shell_open` 为挂起，验证请求线程占死链 | Open |
| S0.3 | 真机 CDP 重复按 o/右键 + 前台条件叠加，抓现场或记录未复现 | Open |
| S0.4 | 按 D14 判决方案适用性，结论写回本节 | Open |
| S1.1 | 后端：新 open_path 命令 + deferred 回执 + Shell/置前 daemon 隔离与超时 | Open |
| S1.2 | 前端：cmd_id 等待 + 2s 延迟 busy toast + inflight 闸 + 复制路径兜底 | Open |
| S2 | 守阵同步与新增用例 + 真机 20+20 次冒烟 + 全量测试 | Open |

## 进度日志

### R0 · 立档 (2026-11-28)

完成原因分析与四轮 grilling 拍板；建计划 HTML、任务档案、issue 三件并补齐双向认领链。尚未动任何代码——下一步是 S0 取证 gate，未拿到根因证据前不进 S1。
