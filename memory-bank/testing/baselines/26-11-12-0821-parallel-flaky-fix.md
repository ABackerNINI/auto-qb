# 6072 —— 并行测试偶发假红修复(26-11-12-0318): 对照组受控重试+探针 data_dir 收窄

> 摘要: 并行测试偶发假红修复(26-11-12-0318): 对照组受控重试+探针 data_dir 收窄
> 基线时间: 2026-11-12 08:21

## 验收数字

`commands run test.full` 实测(2026-11-12 08:1x, 8 worker 带覆盖率, 最终树):

```
TOTAL                                                27110     65   9478     68    99%
6072 passed, 2 skipped in 148.97s (0:02:28)
```

配套: `commands run test.quick`(提交闸门同款, 修复轮闸门预跑)全绿; 目标面单跑 qb_capture 组 2 passed / 契约表 13 档+探针守阵 14 passed。

## 本改动面

- `tests/test_legacy_review4_scripts.py`: qb_capture 对照组受控重试 `_capture_with_retry`(每轮新假服+独立台账, 只对 RequestException 族, 耗尽上抛, SystemExit 不重试) + 守阵 `test_qb_capture_control_group_retry_guard` 三腿红验 + `import requests`。
- `tests/traffic_sample_support.py`: `_v4_open_paths` 探针加 `data_dir` 参数按前缀收窄(进程级 open 探针防同 worker 遗留线程跨 tmp_path 污染)。
- `tests/test_traffic_sample_store.py`: 契约表用例调用点传 `mgr.config.data_dir` + 探针收窄守阵 `test_v4_open_paths_probe_scoped_to_data_dir` 双向红验。
- 文档回写: issue 26-11-12-0318(Open→Done, 根因/复验/修复后补充)、flaky-ledger 新行(Done)、坑档 inproc-server-conn-abort 复发+1(受控重试兑现)、新坑档 global-open-probe-pollution、入池 26-11-12-0739(requests 直接依赖声明, Open)。
