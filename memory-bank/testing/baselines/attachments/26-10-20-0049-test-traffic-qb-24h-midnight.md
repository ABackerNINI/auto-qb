# 3758 passed + 10 skipped(根, 覆盖率 97.53%) —— 24h 端点面跨零点守阵落地后全量基线

> 摘要: 24h 端点面跨零点守阵落地后全量基线
> 基线时间: 2026-10-20 00:49

## 验收数字

`commands run test.full` 实测（2026-10-20 00:4x，本地）：

```
TOTAL      20328    391   6956    262    98%
3758 passed, 10 skipped in 37.31s
```

口径注记：

- 3758 = 上基线 3756 + 2：本轮把 `test_api_traffic_qb_global_24h_reads_only_involved_day_files`
  参数化成真钟 / 假钟 00:05 两档，+1；另一条是上一轮 WEBUI 首行光标那轮的参数化增量已在
  上基线内，此处 +1 来自本轮新档（共 +2 中含上轮提交后重基的差异，逐位对比看
  `commands run kb.baseline -n 2`）。
- 覆盖率 97.53%（pytest 显示 98%）；上一轮收尾时那条
  `test_api_traffic_qb_global_24h_...` 的 1 failed 已消失 —— 该条是时段性的，00:10 后自愈，
  本轮用假钟守阵把它钉住，不再是「看钟点才知道会不会红」。
- 中途一次 `test.full` 出现过 `test_gen_all_check_is_green` 红：本轮改了 issue 状态与新增
  档案后没重建索引；`commands run kb.index` 后复跑即绿 —— 属流程漏步，非代码问题。

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_web_traffic_qb.py` | ① `base` 构造 `((now - 600) // 30) * 30` → `v4_day_epoch(now)`（恒落 involved 末日，`now` 与服务端收边留在真钟）；② 该用例参数化 `frozen_offset = [None, 300]` 两档（真钟 + 假钟本地 00:05）；③ 新增常量 `_FIRST_10MIN_OFFSET`、导入 `pytest` / `v4_day_epoch`；④ 头部测试计划清单同步该条 |
| `memory-bank/pitfalls/testing/flaky-midnight-daycount.md` | 补「必须留真钟的那类窗口用例 → 锚 base 不锚 now」新分支 + 假钟参数化守阵 + 复发 1（0013 那轮漏扫 `test_web_traffic_qb.py`）+ 头部触发词与 Refs |
| `memory-bank/issues/26-10-20-0024-…html` | §06 补实际修法与 B 方案门槛订正、§07 状态日志与修复后补充；状态 In Progress → Done |
| `memory-bank/tasks/26-10-20-test-traffic-qb-24h-midnight.md` | 认领档案（Refs 双向链已由生成器建立）；子任务 5 步全 Done |

生产代码（src/）零改动。
