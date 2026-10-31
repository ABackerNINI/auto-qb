# 3878 passed + 2 skipped(根, 覆盖率 98.33%) —— 覆盖率第二轮 P0 清偿: 98% 门槛转绿 + 达标带

> 摘要: 测试覆盖率提升第二轮(计划 26-10-20-2101)P0 阶段完成 —— `--cov-fail-under=98` 由飘红转绿且留 0.33 点余量(TOTAL 97.66% → 98.33%)
> 基线时间: 2026-10-20 23:59

## 验收数字

根(Windows 本机 `.venv` Python 3.14.7, `commands run test.full`, 2026-10-20 23:59, xdist `-n 8`):

```
TOTAL                                                20685    272   6998    185    98%
3878 passed, 2 skipped in 148.58s (0:02:28)
```

精确值 `uv run coverage report --precision=2` → **TOTAL 98.33%**(未覆盖 272 行 + 185 个 partial 分支出口 = 457 单位; 分母 27,683 单位)。**门槛行零 FAIL**: `--cov-fail-under=98` 本轮首次转绿(上基线同一份 pytest.ini 一直在打 `FAIL Required test coverage of 98% not reached`)。

口径注记:

- **基线对照**(计划 §1, 2026-10-20 全量实测): 375 miss + 258 partial = 633 单位 / 97.66% → 本轮 272 + 185 = 457 单位 / 98.33%,**净清偿 176 单位 = +0.67 点**(计划预估 +130±40,落在带内偏上)。
- 用例 3790 → 3878 passed(+88),skipped 恒 2;新增测试档 2 个(`test_tool_client.py` 14 例、`test_finalize_watch.py` 26 例),其余为既有档扩展。
- **watchlist 复查(M5)**: 行覆盖 <95% 的单文件从基线 10 个降到 **3 个** —— `webui/tool_client.py` 90.8%(21 行)/ `webui/server/traffic_qb.py` 92.6%(13 行)/ `core/modules/relocate_mod.py` 93.9%(50 行)。前两个是 P1 目标项,relocate_mod 是 P1-T1.1 主攻。
- **豁免行数(M6)**: `# pragma: no cover` 全仓 **8 行**(tray/app.py 4、infra/utils.py 2、core/qbmanager.py 2),本轮**零新增**。
- **分包缺口**(括号内为上基线): core 230(244)/ webui 101(206)/ infra 51(61)/ hr 41(47)/ config 26(48)/ rules 6(6)/ tools 4(17)/ tray 3(3)/ torrents 1(1)。webui 降幅最大(-105),与 P0 主攻面(tool_client HTTP 契约 + commands 早退守卫 + traffic_monitor 错误路径)一致。
- **Linux 侧本轮未取得数字**: `commands run test.linux` 起容器后 900s 超时(容器内 `uv sync` + 全量耗时超上限),不是用例失败;按 `testing/baseline.md` 常驻警告,两侧都重测前本切片只作 Windows 侧事实源,Linux 真值以 GitHub Actions 复跑为准。
- 副作用台账越界 0 条(含回环 stub 收真 socket 的 BIND/CONNECT 各若干条,sidefx 白名单放行回环)。
- 并行口径 `-n 8` 默认不变;`pytest.ini` 的 `--cov-fail-under=98` **原样未动**(P0 只要求门槛转绿,P1 达标后才抬 98.5)。

## 变异红验(DoD: 抽 ≥10% 新用例)

本轮新增/改写用例约 88 例,按 12 例(≈14%)逐条打产品码再跑对应测试档,结果 **12/12 全红**,产品码已全部 `git checkout` 还原(工作树零产品码改动):

| # | 变异 | 被谁杀掉 |
|---|---|---|
| M1 | `tool_client.call_tool` 去掉鉴权头 | `test_tool_client.py`(2 failed) |
| M2 | 去掉 `HTTPError` 分支(4xx/5xx 变「不可达」) | `test_tool_client.py` |
| M3 | 空 body 回 `None` 而非 `{}` | `test_tool_client.py` |
| M4 | 删 `_resolve_hr_site_bindings` 的未登记档案 `continue` | `test_hr_config.py`(AttributeError) |
| M5 | v4→v5 迁移无条件重建空 `traffic_source`(清显式键) | `test_config_traffic_monitor.py`(KeyError) |
| M6 | `_bulk_receipt` 无条件写回执(空 cmd_id 也写) | `test_web_commands.py`(results 出现空键) |
| M7 | 删 bulk `skip_check` 菜单闸门 | `test_web_commands.py` |
| M8 | SSE 满额拒签改 200 空票据 | `test_web_auth.py` |
| M9 | 删 `release_file_lock` 的 None 早退 | `test_locking.py` |
| M10 | `StateService.save` 不再吞 OSError | `test_module_host.py`(OSError 上抛) |
| M11 | `_wait_until_started` 窗口判据反向(< 即放弃) | `test_web_api_core.py`(未等满窗口) |
| M12 | 删 `_on_full_round` 的 task_queue 缺失守卫 | `test_modules_p5.py`(AttributeError) |

> M12 首轮是**假绿**:空快照下循环体一次都不跑,守卫删掉也测不出 —— 已补「注入一条已匹配 tracker 的记录」让循环体真正执行,复跑转红。M11 同类:原用例的线程 target 是 `lambda: None` 秒退,「超时」断言实际测的是「线程已死」分支(155 行从未执行),已改为常驻线程 + 断言真等满窗口。

## 本改动面

只补测试,**零产品码改动**(范围守恒:计划外缺陷入池,见下)。

| 文件 | 改动 |
|---|---|
| `tests/test_tool_client.py` | 新建(T0.1, 14 例): 回环 `ThreadingHTTPServer` stub 收真 socket —— GET/POST 载荷与鉴权头 / base_url 斜杠归一 / 4xx·5xx 正常返回 / 空 body / 非法 JSON / 非 UTF-8 / URLError·TimeoutError·裸 OSError 三档不可达(from 链保留) / `error_text` 三档 |
| `tests/test_finalize_watch.py` | 新建(T0.3, 26 例): `_port_refused` / tasklist·ps·`/proc` 三证解析(按 pid 分流 + OSError 保守) / `run()` 六出口 / `_delete_links` / `_verify_dst` / `main()` CLI / relocate_journal 心跳与 `_alive` |
| `tests/test_web_commands.py` | +12 例(T0.2 + 本轮收尾): `_add_outcome` fail 档 / bulk 单方向守卫 / 回执矩阵 / `_relocate_receipt` 直驱 / 六类非法载荷无 cmd_id / **无 cmd_id 一侧全覆盖(14 处 `if cmd_id:` 假弧 + `_bulk_receipt` 两档 + `_bulk_missing_msgs` 缺失组文案)** |
| `tests/test_web_auth.py` | 满额后走真实 POST 断言路由层 503 + `_host_header_parts` 非数字端口 fail-closed 断言 |
| `tests/test_web_traffic_monitor.py` | +5 例(T0.4): PUT config / autostart / shutdown 的 5xx→502、webui 模块缺失 502、notify 非 dict 体 400 |
| `tests/test_traffic_limits.py` · `test_hr_discovery.py` | T0.6: 空 data_dir / open OSError / LRU 上限 / 空窗零读盘 / 心跳注册与退避翻倍 |
| `tests/test_hr_config.py` | +2 例: 四个 loader 的非字典段早退 + `_resolve_hr_site_bindings` 三条 continue 与 `hr=None` 派生 0.0 |
| `tests/test_config_traffic_monitor.py` | +2 例: 迁移对畸形曲线数据源的保守跳过 + 预置 `traffic_source` 字典就地改写(不清空显式键) |
| `tests/test_config.py` | +1 例: `config:` 裸键(None) = 合法空配置零报错 |
| `tests/test_web_keys.py` | +1 例: PUT 非字典体的 handler 级 422 纵深守卫(路由注解先拦,直取端点函数) |
| `tests/test_locking.py` | +1 例: `release_file_lock` 的 None 早退 + 释放失败带 logger 留 DEBUG |
| `tests/test_module_host.py` | +2 例: `BaseModule` 默认 no-op + `StateService.save` 落盘 OSError 记 ERROR 不外抛 |
| `tests/test_modules_p5.py` | +1 例: `_on_full_round` 在 `ctx.task_queue` 缺失时静默返回(注入已匹配记录,防假绿) |
| `tests/test_web_longtail.py` | +1 例: `common.open_path` 包装层直驱(经 `get_file_access()` 透传 select) |
| `tests/test_web_api_core.py` | lifecycle 等待三出口改写(常驻线程真测超时分支)+ `stop_web_server` 超时 False / 正常 True |
| `tests/test_web_backend_misc.py` | +1 例: `WebContext`/`RoCache` 命中与 128 上限 + `require_torrent` 404 / `require_client` 503 |
| `tests/test_traffic_monitor_client.py` | +8 例: 订阅者 `_register`/`_heartbeat`/`_unregister` 失败矩阵 + `request_relaunch` 标志生命周期 + 间隔回落 |
| `memory-bank/issues/26-10-20-2230-bug-webui-origin-port-parse.html` | 新建(范围外缺陷入池, 未修): `_origin_allowed` 的 `parts.port` 在 try 外, 非数字端口 Origin 抛未捕获 ValueError(应为 fail-closed 403) |

验收 DoD 对照: `test.full` 全绿 ✓ / 门槛 98 转绿 ✓ / TOTAL ≥ 98.3%(98.33%)✓ / 基线切片(Windows 侧, Linux 侧超时待 CI)✓ / 变异红验 12 例全杀 ✓ / 阈值维持 98 不动 ✓ / watchlist 复查一行 ✓ / 豁免行数 8 行零新增 ✓。
