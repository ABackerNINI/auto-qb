# RM08 缺失站点扫描新鲜度验收: RM08-13 新建即 L3 红绿双验 —— 同进程双扫描读 qB 侧改后新值(issue 26-11-04-0228 修复真机直验), 4/4 全绿

> 摘要: 功能完工触发真机验收(2026-11-04 新口径, memory-bank/testing/real-machine.md §06): issue 26-11-04-0228(缺失站点扫描复用 store 记录级 tracker 惰性缓存, qB 侧改 tracker 后二次扫描吃首扫旧值)修复入库工作树后的当轮真机验收。新建 RM08-13(落 tests-real/rm08_webui_read/test_rm08_missing_groups.py, 与既有 RM08 附加轮 3 条共享 conftest 串行锁与造场基座): **同一产品进程**内两次 GET /api/sites/missing, 中间经 qB 原生 /torrents/addTrackers 绕产品改 tracker(等价 qB 自家 WebUI 操作)—— 修复前二次扫描吃首扫惰性缓存维持旧形态(RM08-12 时代被迫起新进程绕开, 首跑红记录在切片 26-11-04-0156), 修复后扫描走 torrents_trackers_fresh 直查旁路缓存。**红绿双验真跑**: 摘修复(git stash 两 src 文件)后 RM08-13 必红(二次扫描全单组无共现组, 恰 bug 本体), 恢复后复绿; RM08-12 形态二"必须起新进程"的旧事实注记就此被 RM08-13 取代(RM08-12 本身不动仍绿)。守卫 real.guard 开工/收尾双绿(环境2, 双实例 connected、真实种子 0、全 paused), 收尾 real.seed.clean 清 .work、实例回 0 种子。
> 基线时间: 2026-11-04 05:40(官方合跑 = 4 条一次, 28.63s; RM08-13 单条红验两轮各 ~6s)
> 基线 commit: `60e7abbb`(官方合跑时刻 HEAD; 修复两个 src 文件 + RM08-13 用例在工作树未提交)

## 01 验收数字

`uv run pytest tests-real/rm08_webui_read/test_rm08_missing_groups.py -q --no-cov -p no:cacheprovider`(2026-11-04 05:38, 环境2):

```text
4 passed in 28.63s
```

红验(RM08-13 单条, `real.run --case RM08-13 --yes`):

```text
摘修复(git stash push -- src/auto_qb/core/qbapi.py src/auto_qb/core/exporter.py):
  FAILED test_rm08_13_same_process_scan_freshness - AssertionError: 同进程二次扫描应读到
  qB 侧改后新值(恰一组 2 域名): [全单组 ×2]        (1 failed, 6.15s)
恢复修复(git stash pop)后:
  1 passed, 3 deselected in 5.02s
```

- 三态: **4/0/0**(PASS 4 / FAIL 0 / BLOCKED 0); 产品缺陷 0 个入池。
- 档位分布(L0/L1/L2/L3 = 0/0/3/1): RM08-13 **新建即 L3** —— 红验真跑(摘修复必红, 上面原文), 绿验复跑过; RM08-10/11/12 维持原档(11=L3, 10/12=L2)。
- 升档核验(§08 硬要求): 本轮新增 1 条即 L3, 满足「每轮至少 1 条升一档」。

## 02 本轮改动面(被测对象)

- `src/auto_qb/core/qbapi.py`: 新增 `torrents_trackers_fresh(torrent_hash)` —— 旁路 store 记录级惰性缓存的 tracker 直查(脱敏同口径); 常规 `torrents_trackers` 读路径不动
- `src/auto_qb/core/exporter.py`: `collect_torrent_tracker_hostnames` 优先走 fresh 直查(getattr 探测, 非 facade 客户端回退)—— CLI 与 WEBUI 扫描同一入口一并覆盖
- 单测面: tests/test_exporter.py 两条回归 + 全量基线切片 26-11-04-0531-missing-site-tracker-merge.md(5121 passed + 10 skipped)

## 03 事实回写

- RM08-12 docstring 的「产品 store 对 tracker 列表惰性缓存且只在产品自身 tracker 写操作时失效, 故形态二必须起新进程拿新 store」—— 该事实**只对常规读路径成立**; 扫描路径修复后同进程即可见, 由 RM08-13 专验钉死。RM08-12 断言本身不动仍绿(新进程形态照旧成立)。
- 真实种子清退口径下本片造场全假种子(real-fake 标签), 约束 2 零冲突。
