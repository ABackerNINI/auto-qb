# 4303 passed + 2 skipped(Windows) —— issue 26-10-31-0537 gtm /autostart 指针 patch 修复后全量

> 摘要: 认领修复 issue 26-10-31-0537(gtm POST /autostart 成功后 patch 发现指针 autostart 字段)后全量
> 基线时间: 2026-10-31 10:18

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-31 实测, 全量 206.2s, 建档 10:18):

```
  TOTAL                                                21803     145   7400    122    99%
  4303 passed, 2 skipped in 202.91s (0:03:22)
```

- 汇总行: **4303 passed + 2 skipped(Windows)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- skip 两例构成: 平台条件用例(与 26-10-31-0928 切片注记口径一致; 本会话环境无符号链接权限差异项)。
- 工具包侧(同轮先行): `commands run test.gtm` 429 passed + 2 skipped, 覆盖率 TOTAL 99%(gtm 分区, 门槛 98.5%); 首跑 1 红为本轮新增用例自身(Windows 把「父路径是文件」的 open 也映射成 FileNotFoundError, 用例改用坏 JSON 形态后全绿), 非既有失败。

## 本改动面

- `tools/global-traffic-monitor/src/gtm/server.py`: `_autostart` 成功路径新增 `_patch_endpoint_autostart()`(指针 autostart_registered 现货态改写 + autostart_error 清空, 缺失静默 / 失败 WARNING 不阻断), issue 26-10-31-0537 建议修法①。
- `tools/global-traffic-monitor/tests/test_server.py`: 新增回归三案(即时回写双向 + 失败降级/缺失幂等) + 文件头测试计划同步 + StatefulAutostartBackend 替身。
- `memory-bank/issues/26-10-31-0537-bug-gtm-autostart-pointer-stale.html`: Open → In Progress → Done + 状态日志/复验/修复后补充; `issues/_index.md` 为 kb.index 重建物。
- `memory-bank/pitfalls/backend/platform-fs.md`: 追加「open 异常类型在 Windows 不可区分缺失/路径组件异常」条目(本轮实测坑)。
- 未动: config.yml / auto-qb-data/ / 主仓源码。
