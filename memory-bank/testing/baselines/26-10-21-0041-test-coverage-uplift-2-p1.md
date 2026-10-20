# 3935 passed + 2 skipped(根, 覆盖率 99.03%) —— 覆盖率第二轮 P1 收尾: 阈值抬 98.5 转绿 + watchlist 降到 1

> 摘要: 测试覆盖率提升第二轮(计划 26-10-20-2101)P1 阶段完成 —— TOTAL 98.80% → 99.03%, 门槛由 `--cov-fail-under=98` 抬到 **98.5** 并全量转绿; 单文件行覆盖 <95% 的 watchlist 从 3 个降到 **1 个**
> 基线时间: 2026-10-21 00:41

## 验收数字

根(Windows 本机 `.venv` Python 3.14.7, `commands run test.full`, 2026-10-21 00:41, xdist `-n 8`):

```
TOTAL                                                20685    145   6998    122    99%
3935 passed, 2 skipped in 114.93s (0:01:54)
```

精确值 `uv run coverage report --precision=2` → **TOTAL 99.03%**(未覆盖 145 行 + 122 个 partial 分支出口 = **267 单位**; 分母 27,683 单位)。**门槛行零 FAIL**: `--cov-fail-under=98.5` 首次生效即转绿(上一基线为 98), 余量 0.53 点 —— 与「阈值恒低于实测约 0.3–1 点」的阶梯纪律一致。

口径注记:

- **基线对照**(P0 切片 2026-10-20 23:59): 457 单位 / 98.33% → 267 单位 / 99.03%,**净清偿 190 单位 = +0.70 点**。其中 P1-T1.1(relocate_mod)清 50、T1.2(traffic_store + traffic_sample_mod)清 82、T1.3–T1.5 清 62(其余为并行 partial 口径波动 ±3)。
- 用例 3878 → **3935 passed**(+57),skipped 恒 2;本轮新增测试档 0 个(全为既有档扩展: `test_relocate_exec.py` +17、`test_traffic_store.py` +11、`test_traffic_sample.py` +13、`test_traffic_source_agent.py` +6、`test_alias_fs.py` +6、`test_traffic_grid.py` +4、`test_web_traffic_qb.py` +1)。
- **P1 目标文件清零情况**: `core/traffic_store.py` 42 → **0**(100%) / `core/modules/traffic_sample_mod.py` 40 → **0**(100%) / `core/traffic_source/agent.py` 17 → **0**(100%) / `infra/alias_fs.py` 25 → **0**(100%) / `webui/server/traffic_qb.py` 15 → **0**(100%) / `core/traffic_grid.py` 16 → **8**(98.3%, 余 `492, 497->478, 503->478, 519->518, 615, 713->729`)。合计 73 → 8 单位。
- **watchlist 复查(M5)**: 行覆盖 <95% 的单文件从基线 3 个降到 **1 个** —— 仅 `webui/tool_client.py` 91.3%(21 行 + 4 partial = 25 单位);`webui/server/traffic_qb.py` 92.6% → **100%**、`core/modules/relocate_mod.py` 93.9% → **97.4%** 均出清。DoD「watchlist ≤ 6」达成。
- **豁免行数(M6)**: `# pragma: no cover` 全仓 **8 行**(tray/app.py 4、infra/utils.py 2、core/qbmanager.py 2),本轮**零新增**。
- **分包缺口**(括号内为 P0 切片): webui 84(101)/ core 76(230)/ hr 41(41)/ infra 26(51)/ config 26(26)/ rules 6(6)/ tools 4(4)/ tray 3(3)/ torrents 1(1)。core 降幅最大(-154),与 P1 主攻面(traffic 存储·采样·栅格 + relocate)一致。
- **P2 待清 Top10**: `relocate_mod` 29 / `tool_client` 25 / `webui/runtime` 25 / `validation/sections` 24 / `infra/utils` 20 / `grouping_mod` 17 / `hr/discovery` 14 / `routes/traffic_monitor` 10 / `hr/service` 10 / `views` 8。
- **Linux 侧本轮未取得数字**: `commands run test.linux` 起容器后 900s 超时(容器内 `uv sync` + 全量耗时超上限),不是用例失败;按 `testing/baseline.md` 常驻警告,两侧都重测前本切片只作 Windows 侧事实源,Linux 真值以 GitHub Actions 复跑为准。
- 副作用台账越界 0 条(含回环 stub 收真 socket 的 BIND/CONNECT 各若干条,sidefx 白名单放行回环)。
- 并行口径 `-n 8` 默认不变;`pytest.ini` 的 `--cov-fail-under` 本轮由 **98 → 98.5**(P1 验收动作,与切片同轮落地)。

## 变异红验(DoD: 抽 ≥10% 新用例)

T1.3–T1.5 新增 17 例(`agent` 6 / `alias_fs` 6 / `traffic_grid` 4 / `traffic_qb` 1),按 6 例(**35.3%**)逐条打产品码再跑对应用例,结果 **6/6 全杀**,产品码已全部 `git checkout` 还原(工作树零产品码改动):

| # | 变异 | 被谁杀掉 |
|---|---|---|
| M1 | `agent._platform_data_home` macOS 支判据 `"darwin"` → `"linux"`(macOS 落 XDG 支) | `test_pointer_path_macos_branch` |
| M2 | `TrafficSourceAgent._note_error` 去掉同因节流(每轮都 WARNING) | `test_note_error_throttles_same_reason` |
| M3 | `ensure_running` 拉起 OSError 后 `_retry_after = now`(退避量归零) | `test_ensure_running_launch_oserror_backs_off` |
| M4 | `request_relaunch` 不再清 `_retry_after`(手动重试仍被 30s 挡住) | `test_request_relaunch_clears_backoff_and_failure` |
| M5 | `alias_fs._remove_tree` 只吞 `FileNotFoundError`(locked 等 OSError 半途上抛) | `test_remove_tree_tolerates_failures` |
| M6 | `traffic_grid._bucket_delta` 去掉计数器回落判重置(产负增量) | `test_bucket_delta_null_and_reset` |

> 无假绿返工:6 条变异均一次转红。T1.1/T1.2 批次分别做过 12/12 与 5/5 抽验(见各自提交),P1 阶段累计抽验 23 例。

## 本改动面

只补测试 + 一行阈值,**零产品码改动**(范围守恒:计划外缺陷入池,本阶段零新增)。

| 文件 | 改动 |
|---|---|
| `pytest.ini` | `--cov-fail-under=98` → **98.5**(P1 DoD 验收动作) |
| `tests/test_traffic_source_agent.py` | +6 例: `_platform_data_home` macOS 支 / `parse_pointer` pid 非数值兜底 / 让位注记顶层非对象 / 拉起 OSError 记原因+退避+不算「拉起过」 / `request_relaunch` 清窗口·退避·失败记忆 / `_note_error` 同因节流(自建 `logging.Handler` 收 record,不用 caplog) |
| `tests/test_alias_fs.py` | +6 例: `mount_info_for_path` 读 `/proc/mounts`(非注入) / `_remove_tree` 三条容错出口(scandir 失败·子项删不掉·rmdir 残留) / `probe_junction` 非 Windows 早退 / `alias_kind_of` 无 reparse tag 走 `S_ISLNK` 兜底 / `_win_interactive_session` 两条保守出口(ctypes `WinDLL` 桩) / `_win_create_junction` 内核失败清现场(ctypes 桩 + `os.rmdir` 再失败) |
| `tests/test_traffic_grid.py` | +4 例: `grid_for_now` 包装层 / `_bucket_delta` 两条 None 出口 + 回落判重置 / 组累计逐向独立(上行回落不拖累下行) / `v4_grid_obs` 窗外不消费·越窗尾收口·同桶最晚覆盖胜 |
| `tests/test_web_traffic_qb.py` | +1 例: `QbTrafficChartApi` 防御面(限速缓存预建单例 / 读失败空注解 / `_live_agg_rows` 按段过滤 / 成员天文件与 agg 读竞态降级 / 单系列 all 窗竞态栅格兜底 / 成员月行并集铺格) |
| `memory-bank/tasks/26-10-20-test-coverage-uplift-2.md` | R4 进度日志 + 步 2 转 Done |

验收 DoD 对照: `test.full` 全绿 ✓ / 门槛抬 98.5 并转绿 ✓ / TOTAL ≥ 98.7%(99.03%)✓ / 基线切片(Windows 侧, Linux 侧超时待 CI)✓ / 变异红验 6 例全杀 ✓ / watchlist ≤ 6(实测 1)✓ / 豁免行数 8 行零新增 ✓。
