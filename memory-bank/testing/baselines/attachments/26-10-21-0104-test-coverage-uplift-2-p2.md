# 3967 passed + 2 skipped(根, 覆盖率 99.41%) —— 覆盖率第二轮 P2 收尾: 阈值抬 99 转绿 + watchlist 清零 + 计划 Done

> 摘要: 测试覆盖率提升第二轮(计划 26-10-20-2101)P2 阶段完成 —— TOTAL 99.03% → **99.41%**, 门槛由 98.5 抬到 **99** 并全量转绿; 单文件行覆盖 <95% 的 watchlist 从 1 个降到 **0 个**(清零); 计划三阶段全部收口
> 基线时间: 2026-10-21 01:04

## 验收数字

根(Windows 本机 `.venv` Python 3.14.7, `commands run test.full`, 2026-10-21 01:04, xdist `-n 8`):

```
TOTAL                                                20685     75   6998     87    99%
3967 passed, 2 skipped in 125.85s (0:02:05)
```

精确值 `uv run coverage report --precision=2` → **TOTAL 99.41%**(未覆盖 75 行 + 87 个 partial 分支出口 = **162 单位**; 分母 27,683 单位)。**门槛行零 FAIL**: `--cov-fail-under=99` 首次生效即转绿, 余量 0.41 点 —— 与「阈值恒低于实测约 0.3–1 点」的阶梯纪律一致。

口径注记:

- **基线对照**(P1 切片 2026-10-21 00:41): 267 单位 / 99.03% → 162 单位 / 99.41%,**净清偿 105 单位 = +0.38 点**。累计自计划基线(2026-10-20, 633 单位 / 97.66%)净清偿 **471 单位 = +1.75 点**, 超过计划终点 99% ± 0.3。
- 用例 3935 → **3967 passed**(+32),skipped 恒 2;本轮零新增测试档(全为既有档扩展)。
- **watchlist 清零(M5)**: 行覆盖 <95% 的单文件 **1 → 0**(`webui/tool_client.py` 91.3% → **98.3%**, 余 3 行 2 partial 由 `test_webui_*` 侧的直驱用例覆盖到 100% 口径)。当前最低档:`hr/threadlifecycle.py` 95.0% / `webui/server/auth.py` 95.5% / `routes/traffic_monitor.py` 95.7% / `hr/discovery.py` 95.9% —— **全部 ≥95%**, 达标。DoD「watchlist 清零」达成。
- **豁免行数(M6)**: `# pragma: no cover` 全仓 **8 行**(tray/app.py 4、infra/utils.py 2、core/qbmanager.py 2),本轮**零新增**。
- **分包缺口**(括号内为 P1 切片): webui 59(84)/ core 51(76)/ hr 41(41)/ tools 4(4)/ tray 3(3)/ config 2(26)/ torrents 1(1)/ infra 1(26)。webui 与 config/infra 是本轮主攻面(见下「本改动面」)。
- **残留硬骨头 162 单位**(计划允许 ≤220 留第三轮): `relocate_mod` 29 / `webui/runtime` 25 / `hr/discovery` 14 / `routes/traffic_monitor` 10 / `hr/service` 10 / `views` 8 / `traffic_grid` 8 / `hr/runtime` 7 / `ops_mod` 7 / `torrent_cmds` 5 / `auth` 5 / `hr/server` 5 / `finalize_watch` 4 / `tray` 3 / 其余散布 21。形态集中在**真机窗口/进程探测、GUI 托盘、低频错误路径与路由层竞态** —— 正是计划 §2 预判的第三轮范围。
- **Linux 侧本轮未取得数字**: `commands run test.linux` 起容器后 900s 超时(容器内 `uv sync` + 全量耗时超上限),不是用例失败;按 `testing/baseline.md` 常驻警告,两侧都重测前本切片只作 Windows 侧事实源,Linux 真值以 GitHub Actions 复跑为准。
- 副作用台账越界 0 条(回环 stub 的 BIND/CONNECT 各若干条由 sidefx 白名单放行)。
- 并行口径 `-n 8` 默认不变;`pytest.ini` 的 `--cov-fail-under` 本轮由 **98.5 → 99**(P2 验收动作,与切片同轮落地)。

## 变异红验(DoD: 抽 ≥10% 新用例)

本轮新增/改写约 36 例(T2.1 config 7 / T2.2 infra 10 / T2.3 core 12 / T2.5 订阅者 7),按 7 例(**19.4%**)逐条打产品码再跑对应用例,结果 **7/7 全杀**,产品码已全部 `git checkout` 还原(工作树零产品码改动):

| # | 变异 | 被谁杀掉 |
|---|---|---|
| M1 | `_validate_channel_host` 不再放行 localhost(合法值被判非法) | `test_channel_host_literal_only` |
| M2 | channel.pairing 取值域校验失效(`if False`) | `test_channel_pairing_enum_and_token_type` |
| M3 | `is_loopback_host` 空输入判成回环(保守方向反转) | `test_is_loopback_host_empty_and_unparsable` |
| M4 | `_win_force_foreground` 拆掉 `bool(fg)` 短路(无前台窗口也借线程权限) | `test_win_force_foreground_skips_attach_when_no_foreground` |
| M5 | `_mark_third_party_link` 形态判定抛错时不再早退 | `test_grouping_third_party_link_alias_error_keeps_mark` |
| M6 | `_append` 去掉告警节流(每次失败都 WARNING) | `test_recorder_append_fail_arcs_bootstrap_and_throttle` |
| M7 | `_clear_error` 恢复时不再补 INFO(失败静默消失) | `test_clear_error_logs_recovery_info` |

> 无假绿返工:7 条一次转红。**但本轮在改写既有用例时发现 3 处既有假绿**(见下),已就地修好 —— 这类"断言对、路径错"的用例是覆盖率涨了却测不到东西的根源。

## 修掉的既有假绿(3 处)

`tests/test_traffic_monitor_client.py` 的 `_FAKE_EP.token_path` 是**空串**,而 `_register` / `_heartbeat` / `_unregister` 第一步都是 `read_token(...)`,读不到就**早退**。于是三类断言虽然通过,走的却是「密钥不可读」那条路:

| 用例 | 原断言通过的真实路径 | 目标分支(从未执行) |
|---|---|---|
| `test_register_token_missing_then_unreachable_then_no_id` | 密钥不可读早退 | 336-338 不可达收编 |
| `test_register_missing_id_in_response` | 密钥不可读早退 | 344-345 200 缺 id |
| `test_heartbeat_failure_branches_return_still_valid` | 密钥不可读早退 | 368-370 心跳不可达 / 378-379 被拒 |
| `test_unregister_defensive_and_failure_branches` | 密钥不可读早退 | 402-404 注销不可达 |

修法:新增 `_ep_with_token(tmp_path)`(真读得到密钥的端点), 并补 `tool.paths()` 断言确保请求**真的发出**;同时保留「密钥不可读」自己那条分支的独立断言(不再让两条分支互相冒充)。这正是 `pitfalls/testing/unreached-branch-guard.md` 说的「夹具必须让被测分支真正执行」。

## 本改动面

只补测试 + 一行阈值,**零产品码改动**(范围守恒:计划外缺陷入池,本阶段零新增)。

| 文件 | 改动 |
|---|---|
| `pytest.ini` | `--cov-fail-under=98.5` → **99**(P2 DoD 验收动作) |
| `tests/test_hr_config.py` | +5 例(T2.1): channel.host 只认字面量与 localhost / pairing 取值域与 token 类型 / port 与 discovery_port 相撞 / 非回环 + pairing=off + 无 token 必须拦 / discovery_port 落临时端口段只告警(含平台段值参数化, 自建 handler 收 WARNING) |
| `tests/test_relocate_config.py` | +1 例: 段形状守卫(缺省静默 / 非字典报「必须是字典」并停在该层) |
| `tests/test_config.py` | +1 例: `traffic_source.global_traffic_monitor` 非字典停在该层 + qb_traffic 时间串不可解析时范围比较整段跳过 |
| `tests/test_utils.py` | +7 例(T2.2): 回环判据两条保守出口 / `atomic_write` 失败清理两边缘 / PIDL 路线无 windll 降级 / 四个 Windows 入口缺导出静默 / 无前台窗口不借线程权限 / 复用标题候选空集跳过匹配 / 置前后台化线程真执行 |
| `tests/test_notify.py` | +2 例: APPDATA 缺失时旧快捷方式清单为空 / close 的哨兵投递失败只吞掉 |
| `tests/test_logging.py` | +1 例: `record_domain` 三档(未打标 / 打了标 / 值为 None) |
| `tests/test_grouping.py` | +6 例(T2.3): 物理解析三层保守出口 / 第三方链接打标抛错不清标记 / save_path 变化无组键跳过 / 原组解散仍重归组 / 重归组两条跳过 / 状态转移首轮无快照跳过 |
| `tests/test_traffic_limits.py` | +1 例: 追加失败三条边缘(首轮失败不推基线 / 无 carry 假弧 / 告警节流成一条) |
| `tests/test_speed_curve.py` | +2 例: `_require_snapshot` 装配缺项 fail-fast / 写后回读失败只降级 actual 不回滚 |
| `tests/test_relocate_exec.py` | +1 例: 规则 move_to 的 confirm 与「reasons 为空」两种回执文案 |
| `tests/test_expr_eval.py` | +1 例: 曲线段显式停用时流量变量报「数据源未启用」(与「来源已关闭」文案区分) |
| `tests/test_rule_base.py` | +1 例: 动作返回未知状态时兜底分支(不记 executed, 后续动作照跑) |
| `tests/test_traffic_monitor_client.py` | +3 例 + 修 4 例假绿(T2.5): `_ensure_thread` 幂等 / 主循环两条容错 / `_clear_error` 恢复 INFO;并新增 `_ep_with_token` 助手让「不可达 / 缺 id / 注销不可达」分支真正抵达 |
| `memory-bank/tasks/26-10-20-test-coverage-uplift-2.md` | R5 进度日志 + 步 3/4 状态 + 计划转 Done |
| `memory-bank/plans/26-10-20-2101-plan-test-coverage-uplift-2.html` | Status → Done(含残留清单) |

验收 DoD 对照: `test.full` 全绿 ✓ / TOTAL ≥ 99.2%(**99.41%**)✓ / watchlist 清零(**0 个 <95%**)✓ / 阈值抬 99 并转绿 ✓ / 基线切片(Windows 侧, Linux 侧超时待 CI)✓ / 变异红验 7 例全杀(19.4%)✓ / 豁免行数 8 行零新增 ✓ / gtm 门禁评估结论 ✓(下节) / 残留硬骨头 162 单位列名留第三轮 ✓。

## T2.6 · gtm 工具侧覆盖率门禁评估(结论, 不改配置)

**现状**: `tools/global-traffic-monitor` 是独立包(独立 `pyproject.toml` + 独立 venv), 自带 `[tool.pytest.ini_options]` 只设 `testpaths = ["tests"]`;**无覆盖率门禁**, dev 依赖组只有 `pytest`(无 `pytest-cov`)。测试面本身不小:10 个测试文件 / **265 个用例**(`test_installer` 49 / `test_storage` 44 / `test_server` 42 / `test_identity` 35 / `test_sampler` 29 / `test_config` 27 / `test_notifier` 24 / `test_units` 11 / `test_smoke` 4)。

**结论: 应该加, 且应作为独立任务实施, 起步值建议 85。** 理由三条:

1. **它与主仓是跨进程契约的两端**: 主仓 `webui/tool_client.py` 与 `traffic_source/agent.py` 消费的 `/status`、`/subscribe`、`/heartbeat`、`/unsubscribe` 全在工具侧实现。主仓侧已有 99%+ 的契约测试, 工具侧却没有门禁 —— 契约任一端裸奔, 漂移只会以"订阅莫名失效"的形态暴露。
2. **门禁成本低**: 265 例已在跑, 加 `pytest-cov` + `--cov=src/gtm --cov-branch --cov-fail-under=N` 只是配置面变更, 不新增用例。
3. **起步值不能直接抄主仓的 99**: 工具侧有大量真机探测(psutil 适配器枚举、文件锁、Windows 通知), 这些与主仓 `tray`/`finalize_watch` 同族, 天然有到不了的分支。按主仓「阈值恒低于实测 0.3–1 点」的纪律,**先实测再定档**。

**实施步骤(留给独立任务)**:
1. dev 依赖组加 `pytest-cov`;`[tool.pytest.ini_options]` 加 `addopts = "--cov=src/gtm --cov-branch --cov-fail-under=85"`;
2. 先**只加 `--cov` 不加上限**跑一轮, 取实测值, 再按「实测 − 0.5 点」定 `--cov-fail-under`;
3. 门禁数字进本仓 `testing/baseline.md` 的工具侧一行, 与主仓分开记(两套 venv / 两套 rootdir)。

**未实测说明**: 本机 `tools/global-traffic-monitor/.venv` 不可用(`pyvenv.cfg` 缺失, `uv run` 报 exit 107), 无法当场取实测覆盖率 —— 上述 85 是按「主仓同类真机探测模块实测 95–98% 打八折」给的保守起步值, **实施时必须先跑一次实测再定档**, 不要把 85 当验收线。
