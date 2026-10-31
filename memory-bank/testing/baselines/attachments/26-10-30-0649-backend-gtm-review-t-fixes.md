# 4155 passed + 2 skipped(根) —— gtm 批T 三缺陷收口后全量

> 摘要: gtm 批T 三缺陷(T-01 config 写锁 / T-02 http_host 回环约束 / T-03 day_rolled 方向检查, issue 26-10-30-0624 三条)收口后全量基线; 档案 memory-bank/tasks/26-10-30-backend-gtm-review-t-fixes.md
> 基线时间: 2026-10-30 06:49

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-30 实测, 全量 129.96s, 建档 06:49):

```
  TOTAL                                                21061     99   7126    102    99%
  4155 passed, 2 skipped in 129.96s (0:02:09)
```

- 汇总行: **4155 passed + 2 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%, missed 102)。
- 本轮新增守阵 9 条: test_sampler 2(挂钟回跳跨日界保持/回跳后再前进自愈) +
  test_config 6(回环放行 5 形态参数化 / 非回环拒绝 6 形态参数化 / load_config 入口) +
  test_server 2(/autostart 与 PUT /config 写临界区互斥的确定性交叠复刻 / PUT 非回环 http_host 400)。

## 本改动面

- `tools/global-traffic-monitor/src/gtm/sampler.py`: sample_once day_rolled 判据加方向检查
  (`day > self._day` 才硬切; 回跳记 WARNING 保持累计且采样日钉原日界) + 模块 docstring。
- `tools/global-traffic-monitor/src/gtm/config.py`: 新增 `_check_http_host`(非空 + 回环约束,
  `ipaddress.is_loopback` + localhost 保留名), `_STR_FIELDS` → `_HOST_FIELDS`, docstring 两处。
- `tools/global-traffic-monitor/src/gtm/server.py`: ControlServer 新增 `_config_write_lock`,
  `_put_config` 与 `_autostart` 落盘临界区持锁(autostart 快照读取在锁内) + 模块 docstring 回环口径。
- `tools/global-traffic-monitor/src/gtm/storage.py`: docstring 声明面「强制绑定 127.0.0.1」→「回环地址(校验层限定)」。
- `tools/global-traffic-monitor/tests/{test_sampler,test_config,test_server}.py`: 新增守阵 9 条 + 头部测试计划清单同步。
