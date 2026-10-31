# 3418 passed + 4 skipped —— 全局流量监视小工具 S4 通知(工具测试新增 24 条; 根集相对 S3 切片 +4 条来自同期 replace-retry 轮)

> 摘要: 用户「实施计划S4:26-10-16-0541-plan-global-traffic-monitor.html」(对 S4 的显式授权, S5–S10 不动)。notifier.py 占位 -> 全量实现(~230 行: 阈值累计基数 = 上次事件时刻的当日合计、**只在派发成功后推进**; 跨天/累计回退只重置基数不产伪事件; catch_up 首帧补发不看阈值; 守护线程派发且**每订阅者一线程**、在途上限 32; 顺序 = 先落盘 -> 事件号 +1 落盘 -> 派发; http_push = urllib POST JSON + Bearer) + storage.py `bump_event_id`(事件号 +1 且落盘, 重启接续) + __main__.py `_run_loop` 接通知(首帧 catch_up; 抛错保持待补发下一轮重试) + cmd_run 接线 + tests/test_notifier.py 新文件 24 条守阵, 改 3 文件 + 1 新文件零 auto-qb 触碰。出口判据全过: 阈值触发/启动补发/重复投递去重单测; 两订阅者(含假死端点)推送不阻塞采样循环 —— 单测真 `_run_loop` 10s 压测(帧数下界 60) + 真机 12s 窗口实测 193 帧(16.1/s) 而假死推送每次占满 3s; 工具 122/122; 红验 7 条锚点突变全判 RED 字节恒等还原复绿; 真机冒烟 Bearer token 与 monitor.token 一致 + 假死端点只出 WARNING + kill -9 重启事件号 5->6(补发)->7 且订阅者续存 2。本切片为根 test.full 回归闸门数字(工具测试不在根 testpaths 内, 不进本 TOTAL)。
> 基线时间: 2026-10-16 10:16

- test.full: 3418 passed + 4 skipped / TOTAL 17383 185 5856 159 98%; 耗时 133.71s / 129.74s / 159.83s(三次采样, 口径见 baseline.md)。
- 根集相对 S3 切片(3413+4)的 **+4 条 / TOTAL +40 语句不是本轮改动**: 本轮零 auto-qb 触碰, 增量来自同期 `atomic-write-replace-retry` 轮(`infra/utils` `_replace_retry` + `hr/discovery` 读侧分档 + 守阵)经开工同步合入本 clone —— S3 切片是在其合入前测量的。
- 工具侧自测(独立 venv, 不计入根 TOTAL): `uv run pytest -q` 122 passed(4 条 S0 冒烟 + 29 条 S1 采样 + 27 条 S2 落盘 + 17 条 S3 配置 + 21 条 S3 控制面 + 24 条 S4 通知), 24.6s。
- 红验(临时脚本 `H:/Temp/gtm-s4-redverify.py`: bytes 层锚点、count==1、还原后字节恒等、基线复跑放还原后、解释器钉死工具 venv 绝对路径、子进程超时 90s 且接住 `TimeoutExpired`): 7 条锚点突变全 RED —— 阈值失效(threshold->0) / 跨天不重置基数(baseline_reset 去掉 day_rolled) / 事件号不落盘(bump_event_id 去掉 persist) / 鉴权头写错(Bearer wrong) / 派发同步化(thread.start->thread.run, 守阵**挂起**按未绿计) / 推送前不落盘(flush->pass) / 通知前不剔除租约(prune->()); 全部字节恒等还原后 23 passed 复绿。
- 阈值触发(计划 S4 出口): 事件体严格六键 {event_id, day, up_bytes, down_bytes, total_bytes, ts}; 累计基数 = 上次事件时刻的当日合计(逐样本累加, 非单样本 delta); 同一累计窗口重复投喂不重发; 事件号单调且落 state.json(重启接续); 阈值经 ConfigHolder 现读(PUT /config 热重载生效)。
- 启动补发(计划 S4 出口): `catch_up` 不看阈值发一次, 事件号接续(重启后 last+1, 不从 1 重来); 派发抛错时基数不推进 -> 阈值窗口保留, 下一轮重试。
- 重复投递去重(计划 S4 出口): 发送侧同一累计窗口只发一次(派发成功才推进基数); 事件号单调是订阅侧去重的判据(S7 消费)。
- 假死端点不阻塞采样循环(计划 S4 出口, >10s 压测): 单测真 `_run_loop` 10s(sample_interval 0.05 / 阈值 100KB / 超时 3s / 两订阅者一假死)—— 帧数下界 60 断言通过、停止信号即时收尾、健康订阅者收到事件; 真机 12s 窗口实测 **193 帧(16.1/s)**, 假死端点 accept 4 次(每次占满 3s 超时), 活订阅者收到 4 个事件, 推送失败 5 条 WARNING 不阻断。
- 真机冒烟(Windows, 真 `gtm run` + 真 HTTP 订阅者, 临时 data_dir `H:/Temp/gtm-s4-smoke-*`, 全程后清理): ①实测整机流量 468,593 B/s -> 自适应阈值 937,186 B(约 2s 一个事件); ②真 HTTP 接收端收到事件且 `Authorization: Bearer <token>` 与 monitor.token 逐字节一致; ③假死端点(accept 后不回包)只出 WARNING; ④kill -9 重启: 事件号 5 -> 6(首帧补发) -> 7(后续阈值事件), 订阅者注册表续存 2, state 快照恢复日志可见。
- `PUT /config` **全量覆盖**语义实测: 只发要改的键会把其余键静默打回默认值(sample_interval 0.05 -> 5)—— 冒烟脚本回填完整 config 后正常; S6 设置页「读后写」是硬要求。
- Linux/macOS 侧未跑 —— S4 为 stdlib urllib + threading, 三平台统一。本条 Windows 侧数字为事实源。

## 本改动面

- `src/gtm/notifier.py` 占位 -> 全量实现(~230 行: `Notifier`[阈值累计 + 跨天/回退归位 + catch_up + 守护线程派发(每订阅者一线程, 在途上限 32) + close/wait_idle] + `http_push`[urllib POST JSON + Bearer, 非 2xx 抛])
- `src/gtm/storage.py`: `bump_event_id`(事件号 +1 且 `_persist_state_locked` 落盘)
- `src/gtm/__main__.py`: `_run_loop` 接 notifier(首帧 catch_up; 派发抛错保持待补发) + cmd_run 接线(启动日志含通知阈值 MiB, 退出时 notifier.close)
- `tests/test_notifier.py` 新文件 24 条(全 hermetic: tmp_path + 注入推送替身/计数器/时钟; 其中 3 条走真 HTTP 本地接收端, 覆盖生产 `http_push` 单点)
- `README.md` / `src/gtm/__init__.py`: 「通知 (S4)」节 + PUT /config 全量覆盖告警 + 进度注记
- 坑档: `pitfalls/testing/redverify-anchor-lineendings.md` 复发+1 + 形态十二(设了子进程超时却没接住 `TimeoutExpired` -> 脚本崩、收尾基线复跑被跳过); `pitfalls/testing/red-verify-must-hit-behavior.md` 新增形态「兜底分支掩盖」

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md
