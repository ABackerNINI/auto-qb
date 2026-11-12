# 6076 —— 6076 passed + 19 skipped(env3 Linux, 无 TZ 前置) —— TZ 敏感用例根治批次

> 摘要: 6076 passed + 19 skipped(env3 Linux, 无 TZ 前置) —— test_hr_ratelimit TZ 敏感用例根治批次(issue 26-11-12-2347)
> 基线时间: 2026-11-13 05:26

## 验收数字

```text
TOTAL                                                27113     219   9480     89    99%
6076 passed, 19 skipped in 121.42s (0:02:01)
```

(实测时点: 修复 + 评审 2 轮 2 发现全修后收尾 `commands run test.full` 2026-11-13; 宿主 env3 原生 Linux(Ubuntu 24.04, TZ=America/Los_Angeles 含 DST), **只带 `PATH=$HOME/.local/node/bin:$PATH`(node 电池前置)、不带 TZ 前置** —— 上一切片 26-11-13-0411 必须带 `TZ=Asia/Shanghai` 否则 TZ 敏感存量用例红的「既有红」, 本切片起已随 26-11-12-2347 根治消失, 这是本轮在 DST 宿主裸跑全量绿的直接证据; 上一切片 6075+19 -> 本切片 6076+19: 差值 = 本批 +1 守阵用例, 零回归)

## 本改动面

- **`tests/test_hr_ratelimit.py`**(测试面, 生产代码零改动): 模块级 autouse 夹具 `_pin_dst_free_tz` —— POSIX 侧(hasattr(time,"tzset"))进程内 `os.environ["TZ"]="Asia/Shanghai"` + `time.tzset()`, try/finally 恢复原值; Windows 无该原语早退维持宿主时区。让 `_ts()` naive 解析与实现侧 `fromtimestamp` 同源, 2026-03-07/08 墙钟翻日恒 86400s, DST 宿主(America/Los_Angeles)不再恒红。新增守阵 `test_dst_free_tz_pinned_for_wallclock_asserts`(POSIX: `time.timezone == -8*3600` + 03-07→03-08 墙钟差恰 86400; Windows 支早退), 头部「测试计划」docstring 同步 +1 行。
- **文档面**: issue 26-11-12-2347 翻 Done(kb.status 两处翻转 + 复验行 + 修复后补充); 坑档 env3-test-run-prereqs.md TZ 前置口径回写为已根治(node PATH 部分保留) + `kb.index` 再生; 本基线切片。
