# 5663 passed + 2 skipped(根) —— fix/r4-webui-py 收尾验证基线: 批A-批L(webui/qbapi/tests-real)全量绿

> 摘要: fix/r4-webui-py 收尾验证基线: 批A-批L(webui/qbapi/tests-real)全量绿
> 基线时间: 2026-11-08 00:25
**Refs:** memory-bank/tasks/26-11-08-webui-legacy-review4-webui-py-fix.md

## 验收数字

`commands run test.full` 实测 (151.5s):

```text
TOTAL                                                25549      8   8826     30    99%
5663 passed, 2 skipped, 1 warning in 149.22s (0:02:29)
```

一次通过零失败零重跑; 覆盖率闸(Windows 99.0, tests/conftest.py::pytest_configure)随 rc=0 过检。
2 skipped 为既有设计性跳过(见上片 -rs 实核, 本轮未新增跳过)。POSIX 侧未本地重测, 随推送由
GitHub CI 验证; 相对上片差值看 `commands run kb.baseline -n 2`。批K 改的 tests-real/ 三文件不在
tests/ 收集面(真机轨走 real.suite), 本数字不含真机轨; 本轮收尾验证零代码改动, 未动 .commands/,
test.pkg 不触发。

## 本改动面

本轮(收尾验证 + 基线建档)零源码/测试改动; 数字钉在分支 fix/r4-webui-py 顶(6352ccc8), 改动面 =
该分支批A-批L 共 11 commits(git diff develop...HEAD: 34 文件 +1317/-137):

- src/auto_qb/webui/ 16 文件(批A/C/E/F/G/H/I: runtime_views / commands 族 / runtime 族 /
  server routes 校验加固 / traffic_qb / views 族 / tool_client 实例锁) + 批D 三文件带圈数字清 ASCII;
- src/auto_qb/core/qbapi.py 一行(批L set_alt_speed_limits 签名漂移) + torrents/record.py
  tracker 槽位掩码(批B);
- tests-real/ 3 文件(批K ALT 限速与 tracker 报错两条准入门); tests/ 新增/扩展 12 文件,
  净增 14 例(git diff 计数 +14/-0), 与上基线 5649+14=5663 吻合。
