# 3485 passed + 4 skipped —— 全局流量监视小工具 S9 守阵测试

> 摘要: 用户「实施S9:26-10-16-0541-plan-global-traffic-monitor.html」(对 S9 的显式授权, S10 不动; 开工同步 f8db7019 无 HEAD 改写步骤)。**逐项核对后只补缺口**: S9 清单里「工具侧七类 + auto-qb 侧三类」随 S1–S7 已落地, 唯一未覆盖的是「`dat_path` 指向工具文件时解析兼容」—— 新增跨侧契约守阵 `tests/test_traffic_monitor_dat.py`(2 条: 工具真写者 `gtm.storage.DatStore` 原子落盘的 dat 经 auto-qb `dat_path` 只读刷新读回; 格式单点同值), 并给 `tests/test_web_traffic_monitor_notify.py` 的鉴权守阵补「错 Bearer 也 401」分支(窄池假存活暴露的覆盖缺口)。本切片为根 test.full 回归闸门数字。
> 基线时间: 2026-10-16 18:24

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR; 跑在代码面冻结的同一棵树上, 其后只有文档回写): **3485 passed + 4 skipped in 186.28s**; TOTAL **17684 245 6012 180 98%**(语句/未覆盖/分支/partial/覆盖率)。
- 工具侧套件(工具目录内、工具独立 venv, 不在根 `testpaths` 内): **173 passed in 155.77s** —— 本片未增工具侧用例(该侧七类守阵已随 S1–S5 落地)。
- 手工红验(harness `.openclaw/tmp/redverify_s9.py`, 未入库; 全程 bytes 层 + 锚点 count==1 兜底 + 钉死两侧 venv 解释器绝对路径 + 突变前先跑无变异基线 + 捕获 TimeoutExpired + 还原后复跑基线, 汇总 ALL-RED-AND-GREEN-AFTER-RESTORE): 4 条突变**全判 RED**, 每条还原后字节恒等。
  - 阈值失效(工具 `gtm/notifier.py` 阈值比较改为 `< 0`): 工具 notifier 池 5 条红(accumulation_is_relative_to_last_event / threshold_hot_reload / same_window_not_reemitted_and_ids_monotonic / total_regression_only_resets_baseline / catch_up_emits_once_regardless_of_threshold)。
  - 鉴权绕过(auto-qb `webui/server/auth.py` 密钥比较改为 `compare_digest(token, token)`): notify 池 1 条红(test_notify_requires_auth)。**首轮此突变在 notify 单文件池里 SURVIVED** —— 该文件当时只断言「没带 Bearer 也 401」, 突变打的比较分支它没走到; 按判据拿全量池复验, 被 `tests/test_web_auth.py::test_api_requires_token` / `::test_skip_local_verify_cross_site_guard_credentials_bypass` / `test_webui_backend_errlog.py::test_errlog_requires_token` 三条杀死 ⇒ 假存活; 据此补错 Bearer 分支后本池即可判红(见坑档 `pitfalls/testing/mutation-pool-artifact.md` 复发+1)。
  - 单位漂移(工具 `gtm/storage.py` `KB = 1024` → `1000`): 新守阵 2 条红(round-trip 值 + 格式单点)。
  - 表头漂移(工具 `DAT_HEADER` 的 `lines:` → `rows:`): 只打红格式单点那条 —— 与「值断言抓不到表头层」的设计预期一致(读侧把表头行计成坏行时值仍对得上)。
- 窄池/全量池两次全量复跑(手工, `--no-cov -n 8`, 仅用于定性 M2): 突变态 3 failed + 3482 passed + 4 skipped(172.13s) / 还原态 **3485 passed + 4 skipped**(174.13s), 副作用台账越界 0 条。
- **未闭合(诚实标注)**: S10 真机验收(E1–E6)未动 —— 需真机 Traffic Monitor / 工具进程 / 浏览器, 待逐项授权; 与 S5/S8 同源的 schtasks 自启注册缺口仍在。

## 本改动面

- `tests/test_traffic_monitor_dat.py`(新文件 2 条; 工具写者按源码路径进程内加载 —— 根测试副作用守阵的 POPEN 白名单只放行 node 与临时 wrapper, 因此不起子进程跑工具 venv; 只替 `import psutil`, 根环境刻意无它是 S0 的隔离判据)
- `tests/test_web_traffic_monitor_notify.py`(`test_notify_requires_auth` +2 行: 错 Bearer 也 401; 头文档测试计划清单同步)
- `memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html`(§04 R0 增 S9 行 + 状态行 + 脚注 + doc-updated; HTMLParser 机检未闭合 0 / 乱序 0)
- `memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md`(R10 + 子任务表 S9 → Done)
- `memory-bank/activeContext/26-10-16-0541-global-traffic-monitor.md`(R10 + 摘要/待办)
- `memory-bank/pitfalls/testing/no-uv-fallback.md` / `mutation-pool-artifact.md`(各复发+1)
- 红验 harness 为 scratch(`.openclaw/tmp/`, 不入库)

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md, memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html, memory-bank/testing/baselines/26-10-16-1737-global-traffic-monitor-s8.md
