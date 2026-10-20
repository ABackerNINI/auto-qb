# 372 passed(gtm 工具侧) —— P1 主路径整块: __main__/notifier/sampler 满覆盖 + server 守卫矩阵 99%, 阈值抬 91

> 摘要: gtm 工具侧 P1 完成 —— 补 69 例把 TOTAL 由 90.10% 推到 **95.80%**(净清偿 65 单位), `__main__.py` / `notifier.py` / `sampler.py` 三档**满覆盖**, `server.py` 99%; 阈值按阶梯抬到 **91** 并转绿; 7/7 变异红验全杀
> 基线时间: 2026-10-21 02:16
**Refs:** memory-bank/plans/26-10-21-0120-plan-gtm-coverage-gate.html, memory-bank/tasks/26-10-21-test-gtm-coverage-gate.md

## 验收数字

gtm 工具侧(Windows 本机, `commands run test.gtm`, 2026-10-21 02:16, 串行无 xdist):

```
TOTAL                   1943     79    462     20    96%
372 passed in 62.64s
Required test coverage of 91% reached. Total coverage: 95.80%
```

工具侧独立口径(分母 2405 单位 = 1943 语句 + 462 分支出口), 未覆盖 **79 行 + 20 partial = 99 单位**; 与主仓 `test.full` 的 `--cov=src` 不可比、不可合算。

口径注记:

- **用例 303 → 372 (+69)**: `test_main_run.py` 新建 30 例 / `test_server.py` +32 / `test_notifier.py` +3 / `test_sampler.py` +4。
- **门槛行零 FAIL**: `--cov-fail-under=91` 生效即转绿, 余量 4.80 点。
- **逐档进展**: `__main__.py` 74% → **100%**(62 行主路径 + 各错误出口) / `server.py` 86% → **99%**(仅剩 515-516 的二次兜底 `except: pass`) / `notifier.py` 95% → **100%** / `sampler.py` 97% → **100%** / `storage.py` 93% / `installer.py` 93% / `config.py` 92% / `identity.py` 92% / `units.py` 98%(1 行豁免)。
- **豁免行数(M5)**: 仍 **1 行**(`units.py:54`), 零新增 —— 平台/防御分支一律走注入替身而非 pragma。
- **耗时 62.6s**(P0 为 45.1s): +69 例里含真 socket 原始请求与线程用例; 距 D3 定的 180s 评估线仍有余量, 不加 xdist。
- **Linux 侧仍未取得数字**: 本机只能跑 Windows, ubuntu 侧以 CI `test-gtm` 首次运行为准; 阈值 91 已按「低侧 − 0.8」留足双平台差异余量。

## 变异红验(M3 · 新增 69 例抽 7 例 = 10.1%, 7/7 全杀)

| # | 变异 | 被谁杀掉 |
|---|---|---|
| M1 | `_run_loop` 的 `except Exception` 收窄成 `except ZeroDivisionError`(单轮异常杀循环) | `test_run_loop_single_round_failure_does_not_kill_loop` |
| M2 | `_maybe_register_autostart` 忽略 `config.autostart` 裁决(用户关过也装回) | `test_run_autostart_noop_when_config_disabled` |
| M3 | `TokenManager` 把「文件存在但为空」当有效密钥 | `test_token_empty_file_regenerates` |
| M4 | `ControlServer.stop()` 去掉 `_httpd is not None` 守卫(第二次 stop 抛 AttributeError) | `test_stop_is_idempotent` |
| M5 | `_subscribe` 去掉「载荷必须是 JSON 对象」守卫 | `test_non_object_payload_400_on_every_write_route[POST-/subscribe]` |
| M6 | `_Handler._dispatch` 去掉 500 兜底(单请求异常拖垮连接) | `test_dispatch_unhandled_exception_returns_500` |
| M7 | `Notifier._emit` 让前置落盘失败吃掉事件 | `test_emit_flush_failure_still_pushes` |

产品码全部 `git checkout` 还原, 工作树零产品码改动; 还原后复绿。

## 本改动面

只补测试 + 一行阈值, **零产品码改动**:

| 文件 | 改动 |
|---|---|
| `tests/test_main_run.py` | **新建 30 例**: `cmd_run` 主路径全序列(锁 -> 自启 -> 绑端口 -> 清注记 -> 恢复 -> 主循环 -> 收尾三段)与三条顺序不变式、构造参数透传、自启三态(注册/失败原因进指针/配置关过)、五类早退(身份/归属/配置/锁争/端口占用)、`KeyboardInterrupt` 与收尾抛错吞掉、主循环单轮容错与 catch_up 待补发、`_resolve_data_dir` 搬迁提示、`_load_config_or_fail` 聚合报错与 legacy 提示、`main()` 分发、`python -m gtm` 守卫、`cmd_endpoint` 读失败与顶层非对象、`cmd_claim` 身份失败与记录写失败 |
| `tests/test_server.py` | +32 例: 5 条写路由 × (非对象载荷 / 空体) 400 矩阵、`_read_json` 四类边界(Content-Length 非法 / 空体 / 超 1MiB / 坏 JSON / 非 UTF-8)、`_dispatch` 500 兜底、`stop()` 幂等、指针写失败只 WARNING、自启探测失败降级、endpoint 与 id 的类型守卫、`TokenManager` 空文件/读 OSError/并发双检锁。新增 `raw_request()` 原始 socket 助手(urllib 拼不出坏 Content-Length 与非 UTF-8 体) |
| `tests/test_notifier.py` | +3 例: 前置落盘失败仍推送、租约剔除失败仍派发、close 超时告警 |
| `tests/test_sampler.py` | +4 例: `AdapterFilter.select` 无 stats 映射、生产读数转发 psutil、快照 `day=None` 却带基线、当日累计为负 |
| `pyproject.toml` | `--cov-fail-under` 88 → **91**(P1 DoD 验收动作) |

验收 DoD 对照: TOTAL ≥ 92.5%(**95.80%**)✓ / 阈值抬 91 且绿 ✓ / 基线切片 ✓ / 新用例变异红验 ≥10%(**7/69 = 10.1%, 7/7 全杀**)✓ / 豁免仍 1 行 ✓。
