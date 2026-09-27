# 基线 · 1818 passed + 3 skipped · 0 warnings —— W2 推广落地(输出契约推广到其余命令)

> 摘要: 计划 26-09-28-0157 §10 W2 三件全落地: W2-1 根治 charset_normalizer 半装损坏
> (clone1 --reinstall-package 修复; 授权普查 7 个 auto-qb 目录仅 1/2 损伤; clone2 被 .pyd
> 占用待其进程退出后重跑, requests 导入已实测零警告); W2-2 引擎 _digest 结论行必保
> (_CONCLUSION: N passed/failed / TOTAL / no tests ran, 不与异常行竞争 break, +2 引擎用例);
> W2-3 盘点 6 条警告 → 自家 SyntaxWarning(test_web.py docstring \p 改 \\p) + starlette/anyio
> 弃用警告按消息前缀过滤(starlette 类别是 UserWarning 子类, 按类别匹配落空) → warnings 6→0。
> 其余命令盘点: 动作类成功输出全部 ≤2 行。test.full 可见 = [ok]+TOTAL+passed+位置提示。
> 基线时间: 2026-09-28 04:32
> 档案: memory-bank/tasks/26-09-28-commands-shipflow-output-contract.md

TOTAL 1818 passed + 3 skipped / 0 failed / 17.5s(并行 4 worker) / warnings 0(前基线 6)
覆盖率 91%(12512 语句 / 914 未覆盖 / 4204 分支 / 388 partial)
对比前基线(26-09-28-0321): 1816 passed —— passed +2(远端合并 curve-chart 轮用例), 零回归;
engine 测试 11 项(+2 结论行守阵)。包测试 57 + 引擎 11 全绿。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。
