# 6081 passed, 19 skipped in 110.33s —— test.full 基线: active-context 债务清理 + 保留带口径 [60,80] 落地批

> 摘要: test.full 基线: active-context 债务清理 + 保留带口径 [60,80] 落地批
> 基线时间: 2026-11-13 06:29

## 验收数字

实测(2026-11-13, clone1 本机, develop@58d443a8 + 未提交批(active-context 清理与口径面)):

```
TOTAL                                                27113    219   9480     89    99%
6081 passed, 19 skipped in 110.33s
```

环境注记: `TZ=Asia/Shanghai`(本机默认 America/Los_Angeles, 撞已入池 TZ 用例 26-11-12-2347, 逃生门同 issue 自证; 本轮实踩一次, 坑档 `pitfalls/testing/env3-test-run-prereqs.md` 复发+1) + `PATH` 补 `~/.local/node/bin`(node 电池依赖, 本工具 shell 不加载 zshrc)。test.passed 较上条基线(26-11-13-0513: 6077)+4, 差值 = 远端 58d443a8 带入的 flaky 守阵扩面(tests/test_flaky_timing_guards.py +164 行), 本批测试面仅改名与断言扩位(零新增用例)。

## 本改动面

- `.agents/skills/memory-bank/scripts/_common.py`: 新增 `SLICE_COUNT_TARGET_MIN = 60`(与 `SLICE_COUNT_LIMIT=120`/`SLICE_COUNT_TARGET=80` 同点)。
- `.agents/skills/memory-bank/scripts/gen_active_recent.py`: 债务文案改保留带「60<=目标<=80 …不足下限时停止删除」+ docstring 同步。
- `tests/test_memory_bank_docs.py`: `test_kb_slice_count_limit_warns_at_120_and_targets_80` 改名 `..._targets_band`, 常量断言扩 (120, 60, 80) 三元组, 文案断言加 "60"; 头部测试计划同步。
- `memory-bank/pitfalls/testing/env3-test-run-prereqs.md`: 复发+1 条目 + Refs 反向声明。
- `memory-bank/conventions/collaboration.md` / `memory-bank/pitfalls/kb/cap-counting.md`: 旧「处置目标 80」两处抄写同步为保留带(评审轮 1 发现)。
- 记账面: active-context 切片 150→75(删 75 条最老 closed, 11 条 pending + 64 条最近 closed 保留)+ 任务档案 + 本切片 + `pitfalls/_index*.md` 重生成。
