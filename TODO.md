# TODO

> 待办与已知缺陷清单。**只记"还没做/还没修"的事** —— 已完成项请走 `memory-bank/progress.md` 与各任务档案。
> 冲突裁决同 `AGENTS.md`: 代码 > `memory-bank/` > 根 `README.md` > `想法.md`。
> 本文件不是红线文件, 但**不要在提交时顺手带上用户的未提交改动**(`想法.md` 属高危, `config.yml` 是红线)。
> 仿真测试**怎么跑 / 怎么判 / 怎么回溯**见 [docs/sim-client-test-howto.md](docs/sim-client-test-howto.md)。

---

## 已知缺陷 (未修)

### BUG-01 · qB 短暂断连后 auto-qb 无法自愈, 永久停在断连态

- **发现**: 2026-09-19, 5000 种子仿真测试的 S5 断连降级场景(独立仿真服务端 + 真实 auto-qb 子进程)。
- **严重度**: 高 —— 断连 10 秒是 PT 场景常见抖动(qB 重启 / 网络闪断), 目前后果是**程序静默失去同步、必须人工重启**;
  且期间每 tick 一条 ERROR + 完整异常栈, 会淹没真正的错误。

**现象**(`--abort-after 12 --abort-duration 10`, 断 10 秒后恢复):

| 观测 | 结果 |
|---|---|
| 断连期间写请求 | `0`(符合预期, 没误删、没写风暴) |
| 恢复后是否重新同步 | **否** —— 直到运行结束一直是断连态 |
| 每 tick 日志 | `主循环异常: 'NoneType' object has no attribute 'torrents_info'` + 完整异常栈(30 秒 **28 条栈**) |
| sync 轮次 | 常态 ~22 → **5** |
| `sync_full_rounds` | 停在 **1**(rid 全量自愈从未发生) |

**根因**(`src/auto_qb/qbmanager.py` 的 `run()` 主循环):

```python
except APIConnectionError as e:
    if self._last_conn_ok is not False:
        logger.error(f"连接 qBittorrent 失败: {e}")
        self._last_conn_ok = False
    self.client = None                       # ← ① 置 None
    if self._reconnect_due(main_tick):       # ← ② 重连只在**本分支**里触发
        self.connect()
except Exception as e:
    logger.error(f"主循环异常: {e}", exc_info=True)   # ← ③ 只打日志, 不重连
```

1. 重连只在 `except APIConnectionError` 分支里做, 而该分支第一步就是 `self.client = None`;
2. client 一旦为 None, 下一次 `api.sync_maindata()` 抛的是 **`AttributeError`**, 不再是 `APIConnectionError`;
3. 于是落进 `except Exception` —— 这条分支**不重连**, 只打日志。死循环形成:

   ```
   tick k   : APIConnectionError → client=None → _reconnect_due() 未到期则不 connect()
   tick k+1 : client is None → AttributeError → except Exception(只打日志)
   tick k+2 … : 同上, 永远停在这里 —— 只能重启进程
   ```

退避逻辑 `_reconnect_due`(2s → 4s → 8s → … → 30s 上限)本身是对的, 但它被放在了一个**再也进不去的分支**里。
这就是"异常处理器改了状态、而这个状态又决定了下次抛什么异常"导致的**异常类型漂移**。

**复现**:

```bash
uv run python scripts/sim_run.py --scenario S5 --n 300 --duration 45 \
    --abort-after 12 --abort-duration 10 --web-port 18111
# 期望: verdict OK
# 实际: verdict FAIL —— LOG.tracebacks=28 / S5.full_update_after_recover / S5.outage_survived 全红
```

**修复方向**(二选一, 均需红绿验证: 先用上面这条 S5 场景跑出红, 再验绿):

- **A(推荐)** 把"已断连"做成显式状态位: 断连期间**跳过 `_tick`**, 由**独立分支**按退避重连 ——
  语义最清楚, 也顺带消掉断连期间的日志刷屏。
- **B** 让 `QbApi` 在 `self._client is None` 时抛 `APIConnectionError` 而不是 `AttributeError`,
  保证异常类型始终能表达"连接不可用" —— 改动最小, 但断连期间仍会每 tick 打一条日志。

**验证判据**(不只是"断连期间不崩"): 必须是 **"断连 N 秒后能自愈"** ——
恢复后 sync 轮次回到常态、`sync_full_rounds` 出现第二次(全量自愈)、`LOG.tracebacks == 0`。

**证据**:
`memory-bank/plans/26-09-19-1433-sim-client-5000-plan.html` 第 09 节;
`memory-bank/pitfalls.md`「仿真驱动器: 又四类"测假"陷阱 + 一个真缺陷」第 ⑨ 条;
运行产物 `R:\auto-qb-sim\runs\20260919-165128-S5\`。

---

## 性能发现 (观测结论, 未动代码)

### PERF-01 · 5000 种子规模下, WEB UI 并发轮询会把主循环拖到近乎停摆

- **发现**: 2026-09-19, P6 场景(5000 种子, 主循环 tick 2 s), 只改 WEB 轮询强度做对照:

  | 轮询 | sync 轮次 / 45 s | `torrents/trackers` | `torrents/files` | 首轮灌入 | `/api/state` 全量 p95 | 稳态间隔 / 漂移 |
  |---|---|---|---|---|---|---|
  | 无 | 15 | 5007 | 5000 | ✅ 完成 | — | 2.24 s / **0.33 s** |
  | 1 线程(≈4 req/s) | 14 | 5007 | 5000 | ✅ 完成 | **609 ms** | 2.43 s / **0.95 s** |
  | 4 线程(≈16 req/s) | **1** | **2002** | **0** | ❌ 45 s 未完成 | 1279 ms | **8.52 s** / 8.11 s |

- **解读**: `/api/state`(全量, `rid=-1`)在 5000 种子下**单次就要约 0.6 s**, 与它同进程的
  主循环直接被抢走时间片 —— 单线程轮询已把稳态漂移从 0.33 s 顶到 0.95 s, 打满时首轮灌入
  连 `torrents/files` 一次都没来得及拉。
- **保留意见**: 测试用的是 `rid=-1` 强制全量, 比真实前端(增量 rid)**更狠**; 但真实用户
  开多个标签页 / 首屏 / 切页时同样会要全量, 峰值是存在的。建议先按真实前端节奏
  (增量 rid + 2–5 s 轮询)复测一次再决定是否动手。
- **若动手, 方向**: ① `/api/state` 走增量(已有 rid 机制, 确认前端是否用满);
  ② 全量视图构建移出 Web 线程或加缓存/节流(视图已有版本号与 `_view_lock`, 可复用);
  ③ 5000 种子下考虑分页/按需字段。

### PERF-02 · 渐进灌入(--ramp 200/拍)时主循环掉拍

- **实测**: P2 场景稳态间隔 **2.87 s** vs `main_tick` 2.0 s, 最大漂移 **1.22 s**;
  对比一次性灌入的 P1 稳态 2.23 s / 漂移 0.31 s。
- **解读**: 每拍 200 个新种子 ⇒ 每拍约 200 次 `torrents/trackers` + 200 次 `torrents/files`,
  首轮成本被打散后**每拍都在还债**, 直到灌完才回到稳态。属可接受的"灌入期代价",
  但值得给 `max_tasks_per_tick` 做自适应(候选已列入 W5)。
- **已按观测项处理**: 灌入期的漂移记为 `P2.drift_max_s`(BASELINE), 不用稳态阈值判红 ——
  否则会把"灌入期跟不上"这个结论埋掉。

---

## 待办 (按波次)

仿真测试计划(`TASK018`)的剩余波次, 详见
[memory-bank/plans/26-09-19-1433-sim-client-5000-plan.html](memory-bank/plans/26-09-19-1433-sim-client-5000-plan.html)。

- **W3 安全矩阵** — ✅ 已跑完。S1/S2 每次运行都判(全绿)、S3 已由 W4 固化阈值、
  S4 由 D5 两相运行覆盖、**S5 = BUG-01(实测 FAIL, 待修)**、S6/S7/S8 ✅ 全绿。
  - [x] **S6 数据面只读**: `data_dir` 跑前后快照对比, 只允许 `state.json` / 日志 / `web.token` / 锁(实测 0 越界)。
  - [x] **S7 WEB 并发只读**: 并发轮询 500 次, 4xx/5xx = 0, p95 见 PERF-01。
  - [x] **S8 限速保护**: 30 个奇数 KiB/s 手设限速**一个没被改写**, `setUploadLimit` 命中 0。
- **W4 性能矩阵** — ✅ 已跑齐 P1–P7 并固化阈值到
  `memory-bank/plans/26-09-19-1433-sim-client-5000.baseline.json`(`sim_run.py` 启动时自动读取;
  不存在时相关项记 BASELINE)。当前阈值:
  `P1.first_round_s ≤ 22.68` / `S3.write_rate_per_min ≤ 6210.49` / `S7.p95_ms ≤ 1218.4` /
  `SYNC.drift_max_s ≤ 1.0`(纯主循环; 灌入期与带 WEB 轮询的漂移另记 `P2.drift_max_s` 观测)。
  - [x] P1 首轮灌入 14.4 s / P2 渐进灌入 2.7 s(见 PERF-02) / P3 churn tick2 14.2 s /
        P3b tick1.5 13.5 s / P4 steady 14.4 s / P6 WEB 并发(见 PERF-01) / P7 删除风暴 9.6 s
  - [ ] **P5 任务吞吐** 尚未单独出数: 需观测"队列深度 / 任务实际执行周期 vs 名义 interval",
        现有外部观测只能拿到"写台账收敛时间", 建议留到 W5 归因一并做。
- **W5 归因(只出结论, 不动代码)** — 候选: `torrents/files` 拉取预算、**WEB 全量视图(PERF-01)**、
  `max_tasks_per_tick` 自适应(PERF-02)、批量打标签(实测 `qbittorrent-api` 每次写请求前额外查一次
  `app/webapiVersion` ⇒ 写请求量翻倍, 而 qB 的 `addTags` 支持一次传多个 hash)。
- **W6 收尾** — 基线写入 `memory-bank/testing.md`; 新坑入 `pitfalls.md`(W3b 的 ⑤–⑧ 与本轮的 ⑩–⑫ 已入)。
