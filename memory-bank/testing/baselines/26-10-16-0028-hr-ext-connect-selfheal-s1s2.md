# 3394 —— HR 扩展连接自愈 S1/S2(合并语义翻转 + 失败即发现 + 徽标四态 + 健康台账)

> 摘要: 实施计划 `26-10-15-2357` 的 S1(`discovery.js` 合并语义翻转: 手动优先 + 发现集整批替换 + 空集不替换 + `isManualEntry`)与 S2(`background.js`: 任一实例失败即发现 + 周期 10→2 分钟 + 徽标四态 + 结构化 `lastDiscovery` + `instanceHealth` 台账)。改动面 = `extensions/hr-fetch-proxy/discovery.js` / `background.js` / `tests/test_extension_proxy.py`(新增 6 条守阵 + 既有合并语义断言随计划翻转)。**S3–S6 未实施**(计划仍 Open)。
> 档案: memory-bank/tasks/26-10-16-webui-hr-ext-connect-selfheal.md
> 基线时间: 2026-10-16 00:28

**Refs:** memory-bank/tasks/26-10-16-webui-hr-ext-connect-selfheal.md, memory-bank/plans/26-10-15-2357-plan-hr-ext-connect-selfheal.html

## TOTAL

```
TOTAL                                               17337    182   5846    158    99%
3394 passed, 4 skipped in 128.16s (0:02:08)
```

- 语句 17337 / 未覆盖 182; 分支 5846 / partial 158; 覆盖率 **99%**(`commands run test.full` 实测, Windows 侧)。
- 耗时两次采样(同树全量两跑): 145.24s / 128.16s —— 单次数字不构成基准, 口径见 [../baseline.md](../baseline.md)。
- 本轮无 Python 侧改动: 改动面是浏览器扩展 JS(不经 Python 覆盖率统计)与其 node 沙箱守阵 —— 语句/分支口径因此与上一切片同形。
- Linux(WSL) 侧未重测 —— 本轮无平台相关改动。
