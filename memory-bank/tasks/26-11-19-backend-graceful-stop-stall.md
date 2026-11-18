# 26-11-19-backend-graceful-stop-stall — 优雅停偶发 38.75s: 复验判别与定位

**Status:** In Progress
**Added:** 2026-11-19
**Updated:** 2026-11-19
**Summary:** 优雅停偶发 38.75s(issue 26-11-18-2350): 静态排查闭合排除面并修正停滞窗口(信号触发 ~12.4s→KI 浮出 50.99s, 主线程 ~38.4s 零 checkpoint), 剩余假设 H1 整机/进程冻结 / H2 主线程单 C 调用(qB 涓流响应 defeating 字节间超时) / H3 GIL 持有者; 复验判别计划入库(观测面贯穿停机窗口 + faulthandler 看门狗 + ≥20 轮采样, 零产品改动), 执行待显式开工
**Topics:** backend-graceful-stop-stall
**Refs:** memory-bank/plans/26-11-19-0054-plan-graceful-stop-sigterm-stall.html, memory-bank/issues/26-11-18-2350-bug-graceful-stop-sigterm-stall.html

## 本篇只回答

issue 26-11-18-2350(优雅停偶发 38.75s, SIGTERM 后主线程长时未到收尾)的挂点排查进展: 静态排除面闭合到哪、剩余假设是什么、复验判别怎么设计 —— 方案正文单点在计划; 顺带发现的 traffic 空路径告警缺陷已独立入池(26-11-19-0052), 与本专题无因果耦合。

## 原始请求

1. 「分析memory-bank/issues/26-11-18-2350-bug-graceful-stop-sigterm-stall.html」(问答/只读轮, 2026-11-19)
2. 「traffic_snapshot_mod.py:245的问题入池, 落成正式计划, 回写issue然后提交」(执行授权: 入池 + 计划 + 回写 + 提交, 四动作逐项显式)

## 思考过程与决策

- 静态排查(2026-11-19, 证据 = tests-real/.work/s0boot/ 本地留存产物): 时间线用 run1 标定驱动「测量结束→touch」固定延迟 ~2.8s ⇒ run2 信号触发 ~12.4-12.6s, 而「停止」LogRecord.created = 50.995(asctime 取 created 非写盘时刻, 硬判定)⇒ 主线程 ~38.4s 零 eval-loop checkpoint。
- 排除面(全部有证据): stdout/stderr 直写文件句柄(无管道背压); qB API 有界 (3,10)s 且失败必落日志; tool_client 全 urlopen(timeout) 有界且订阅在 daemon 线程; flush_truths 空 pending 直 return; _publish 无锁单引用; 210 种子管线(含 re 重户段)在 09.365 前完成; 纯 Python 主循环(sync_interval 1.5s + ≤0.5s 分段等待)处处是 checkpoint。
- 剩余假设排序: H1 整机/进程冻结(磁盘停顿/AV/系统暂停 —— 进程内证据完全不可见, 奥卡姆, 1/6 形态吻合) > H2 主线程单个不可中断 C 调用(具体嫌疑: requests timeout=(3,10) 是 connect/字节间读超时非总时长, qB 忙时涓流响应可静默存活任意久) > H3 其他线程持 GIL 的 C 调用(无持有者候选, 存疑)。
- 判别设计(零产品改动, 全在 tests-real): 观测面贯穿停机窗口(graceful_stop 等待期继续轮询 WEB, H1/H2 一拍判定) + faulthandler.dump_traceback_later 看门狗(复发自动落全线程栈) + ≥20 轮采样; D 编号与判据见计划。
- 范围裁决: traffic 空路径 WARNING 是独立缺陷(文案失真, 数据面正确), 按范围守恒入池不顺手修。

## 实现计划

计划单点: `memory-bank/plans/26-11-19-0054-plan-graceful-stop-sigterm-stall.html`(见该件状态)。
- S0 观测面贯穿: run_s0_boot.py graceful_stop 等待期每 0.25s 轮询 /api/state, polls 序列进 measure.json stop 子树; 判据: 轮询正常=主线程单点(H2), 轮询冻结=整进程(H1)。
- S1 看门狗: runner stopfile 触发后 arm faulthandler.dump_traceback_later(15s, file=case 目录), 复发时全线程栈落盘即挂点。
- S2 批量采样: ≥20 轮受控重启测量记 stop_s 分布, 判定回写 issue 26-11-18-2350。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0 | 观测面贯穿停机窗口(driver 轮询 + polls 字段) | Open |
| S1 | runner faulthandler 看门狗 | Open |
| S2 | ≥20 轮批量采样 + 判定回写 issue | Open |

## 进度日志

### R0 · 立档 (2026-11-19)

分析轮(只读): issue 26-11-18-2350 全锚点核到代码与原始产物, 时间线修正 + 排除面闭合 + 剩余假设排序; 执行轮: traffic 空路径缺陷入池(26-11-19-0052) + 复验判别计划入库 + 本档立档 + issue 26-11-18-2350 回写判别结论; 零产品代码改动。

- 2026-11-19 00:57 分析轮: issue 26-11-18-2350 静态排查(窗口修正 12.4->50.995, 排除面闭合, H1/H2/H3 排序) + 复验判别计划入库 + traffic 空路径入池 26-11-19-0052 + issue 回写; 零产品改动
