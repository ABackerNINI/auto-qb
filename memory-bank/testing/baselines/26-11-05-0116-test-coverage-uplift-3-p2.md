# 5167 passed + 2 skipped(根) —— 覆盖率第三轮 P2 收口全量基线(webui+core 长尾清偿, 缺口收敛 20 单位)

> 摘要: 覆盖率第三轮 P2 收口全量基线(webui+core 长尾清偿, 缺口收敛 20 单位)
> 基线时间: 2026-11-05 01:16
**Refs:** memory-bank/plans/26-11-04-0157-plan-test-coverage-uplift-3.html (§04 P2 收口 / D1·D3 拍板)

## 验收数字

`commands run test.full` 实测(coverage-uplift-3, Windows 并行 + 覆盖率, 新阈值 99.5/99.0 下复测):

```text
[ok] test.full (150.8s)
  TOTAL                                                23325      5   7956     15    99%
  5167 passed, 2 skipped, 1 warning in 148.82s (0:02:28)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率); wrapper 外层耗时 **150.8s**(单次采样, 区间口径见 [../baseline.md](../baseline.md)); 覆盖率闸 Windows **99.5**(`tests/conftest.py` 单点, 本轮自 99.3/98.8 抬至 99.5/99.0, 见「本改动面」)。精确 TOTAL **99.9361%**(31261/31281, 语句+分支合并口径)—— 过 D1 终点线(缺口 ≤100, 计划 26-11-04-0157 §04)。

- **缺口单位 20**(miss 5 + partial 15), 对照 P1 验收切片 118(44m + 74p, 分母同为 31281)**净清偿 98**——M8 净额 = 20 − 118 = **−98**, 为负无新模块入榜(M8 台账见 [../baseline.md](../baseline.md)「缺口净额台账」, 与 p0→p2 序列 319→217→118→20 一致)。
- **残留 20 单位逐文件列名**(实例根 cov 实测, `coverage report --show-missing`; 性质三档: tray 豁免 / 到不了防御支 / 零头):
  1. `tray/app.py` 111-112, 565(miss 3)—— **tray 豁免**(计划 T2.3 拍板「维持豁免口径不追加」): 111-112 端口文件 sock.close() 的 OSError 防御支, 565 `ui.run()` 托盘主循环入口, 均需真机桌面形态;
  2. `hr/threadlifecycle.py` 32 + 31->32 弧(miss 1 + partial 1)—— **到不了防御支**: start() 幂等守卫真支(线程已在跑 → return False), 现有测试只驱动「从无到有」形态, 竞态窗口单测难直驱;
  3. `webui/runtime_views.py` 542 + 541->542 弧(miss 1 + partial 1)—— **到不了防御支**: 剧集映射残值防御 continue, 行注释自证「理论不可达: 映射随删除清理」;
  4. `core/modules/relocate_units.py` 552->554(partial 1)—— **假弧**: same_volume 三态(True/False/None)穷尽后最后一个 elif 的假支逻辑不可达, 前轮已列名的同一条;
  5. `config/validation/rules.py` 464->466 / 536->544 / 544->exit(partial 3)—— **零头**: 动作校验可选键缺省三假支(params 无 on_error / on_error 无 retries / 无 backoff);
  6. `core/modules/fuse_mod.py` 284->286(partial 1)—— **零头**: 摘除标签 removed==0(无可摘)假支;
  7. `hr/report.py` 333->339(partial 1)—— **零头**: 文本不超宽(无需截断省略号)假支;
  8. `hr/resolve.py` 387->389(partial 1)—— **零头**: lane 既非 UNSATISFIED 也非 EXEMPT 的落空弧(经 389 released_src 兜底);
  9. `hr/runtime.py` 129->131 / 222->224(partial 2)—— **零头**: 启动编排 / 热应用 worker 为 None(无取数通道形态)假支;
  10. `hr/service_common.py` 426->exit(partial 1)—— **零头**: INDEX_RETENTION 关闭(=0)假支(保守默认关闭口径, 默认配置恒 >0);
  11. `hr/service_wave.py` 348->341(partial 1)—— **零头**: 预算档 elif(pages==0)假支落回循环头;
  12. `hr/worker.py` 190->exit(partial 1)—— **零头**: _handle.start() 返回 False(已启动幂等拒启)假支, 与第 2 条同族竞态防御;
  13. `torrents/store.py` 473->472(partial 1)—— **零头**: 跳检窗口 hash 恢复支后的循环回边(实测窗口恒单 hash)。
- **watchlist(合并覆盖 <95% 单文件)终态: 清零**。coverage 全表逐行核实(term 表剔除 100% 行后共 13 个 <100% 文件, 最低 `hr/threadlifecycle.py` **95%** 恰在线上不破榜, 其 miss 行即残留第 2 条), 无任何 <95% 单文件。P1 存量 3 个全部核销出榜: webui/commands.py 90→100(T2a)、runtime_common 93→100(T2a)、views_episodes 94→99+(T2a2)。
- **豁免行数**(`grep -rn "pragma: no cover" src/` 计数)8, 与基线持平。
- **阈值记录**: win 99.5 —— 抬后 `test.full` 实测全绿(上表), 无假红; other **99.0** —— **维持前会话定稿**, 依据: 本机无 Linux 实测能力, 无任何 Linux 侧覆盖率证据支持回退, 维持已审阅的保守抬升决策; 该侧闸门仅在 Linux CI/WSL 触发, 若余量不足会显式假红(可观测、可回退), 不构成静默放水风险。

## 本改动面

- **阈值抬升(验收动作)**: `tests/conftest.py` `COVERAGE_FLOOR_WIN` 99.3→**99.5** / `COVERAGE_FLOOR_OTHER` 98.8→**99.0**; 抬后 `commands run test.full` 复测全绿(150.8s, 上表)。**本步测试码零改动** —— P2 清偿明细全部在三个前置提交: T2a `91c8d516`(webui runtime 家族与 commands 42 单位)/ T2a2 `d14a5391`(views_episodes/auth/routes ≈23 单位)/ T2b `abc5381f`(traffic_grid/relocate/registry/finalize_watch ≈38 单位), 合计 49 条新用例把缺口从 118 收敛到 20。
- **变异红验(抽 6 个注入点 = 6 次变异, 每次只变异一处产品码, `commands run test.one` 定向跑确认变红后 `git checkout -- <单个产品文件>` 还原并复跑确认回绿)——5/6 杀死, 1 条假绿如实列名**:
  1. `tools/finalize_watch.py::run` verify 分支翻转 `if not _verify_dst` → `_verify_dst` → `test_run_verify_write_refused_returns_stopped` 红(误入 removing 支删了链接, 断言"failed 落账被拒不得动链接"命中);
  2. `core/traffic_grid.py::_v4_grid_obs` 窗首对齐守卫收紧 `b >= first` → `b > first` → `test_v4_grid_obs_wide_point_before_window_start_partial_overlap` 红(窗首桶不消费, obs 断言命中);
  3. `rules/registry.py::PluginEntry.plugin` 显式 KeyError 换静默 `return None` → `test_plugin_entry_schema_ref_miss_raises_keyerror` 红(pytest.raises(KeyError) 落空);
  4. `webui/views_episodes.py::_agg_show_node` 删 hr_pending 计数守卫(`if not hr_satisfied` → `if False`)→ `test_agg_show_node_hr_counts_and_show_row_empty_title` 红(hr_pending 1→0);注: 先试条件翻转(`not` 删除), 未杀死——断言 hr_pending==1 对翻转方向不敏感(1 pending + 1 satisfied 翻转后仍计 1), 换删语句变异后杀死;
  5. `webui/commands.py::_cmd_transfer_run` 删无 cmd_id 不写回执闸(`if cmd_id` → `if True`)→ `test_transfer_cmd_receipt_paths` 红(ghost 目标误写回执, `mgr.web.results == {}` 断言命中);
  6. **假绿**: `core/qbmanager.py` 主循环补刷新闸(619/624)三型变异(`if True` 直通 ×2 / `or`→`and` 收紧)全部存活 —— 定向用例 `test_run_cmd_driven_sync_not_by_time_keeps_next_sync` 的观察窗在第 4 轮 KeyboardInterrupt 退出, 而该闸重置节拍的可观测分歧(下一次自然同步时刻)恰好落在退出之后, 用例在此窗口内对这三型变异**不敏感**(直驱 trace 实证: 第 1 轮同步来自断连稳态支 608, 619/624 假支虽被用例踩到但后果不可见)。属用例断言窗口局限, 非测试无效应; 真值回归靠后续变异审计轮(mutants.*)兜。
  还原后 `git diff HEAD` 仅 `tests/conftest.py` 阈值 2 行 + `memory-bank/testing/baseline.md` M8 台账, 产品码零残留; 红验用 test.one(内置 --no-cov, 覆盖率闸只归 test.full)。
