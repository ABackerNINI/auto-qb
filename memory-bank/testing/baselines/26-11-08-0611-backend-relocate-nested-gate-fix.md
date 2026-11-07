# 5733 passed + 2 skipped —— rebase 远端 40 笔后基线: 移交项③④修复

> 摘要: rebase 远端 40 笔后基线: 移交项③④修复
> 基线时间: 2026-11-08 06:11

## 验收数字

- 汇总行: `5733 passed, 2 skipped, 1 warning in 134.82s (0:02:14)`(2026-11-08, `commands run test.full` 实测誊写)
- 覆盖率: TOTAL 25570 stmts / 6 miss / 8840 branch / 96 partial;`Required test coverage of 99.5% reached. Total coverage: 99.90%`
- 差值口径: 对 26-11-08-0317 切片(5653 passed)净变化 = ①`my-commit-flow.sync` rebase 远端 40 笔带入的用例增量(含 qbmanager/config 面新测;test.quick 单测中 `test_run_loop_layered_cadence` 一度 flake,单跑两过+全量未复现) ②本轮移交项修复无新用例(死字段删除零测试引用)。2 skipped 同权正面。

## 本改动面

- ①环境修复: `dev.fmt` 的 yapf shim 损坏(uv trampoline canonicalize 失败)→ `uv sync --reinstall-package yapf` 定点重装(yapf==0.43.0),`commands run dev.fmt` 实跑验证通过(0.9s);零代码改动。
- ③死字段清理(用户授权移交项): `relocate_units.py` GroupFacts 删 `member_save_paths` 字段与注释、`relocate_plan.py` `_group_facts` 删构建与传参(全仓 3 处,测试零引用;R1-R5 起判据改锚内容根派生物后该字段无消费面)。
- ④文案修复(用户授权移交项): `move-dialog.html` move-note「移动后该种子将离开当前辅种组」→「移动后保存路径变化, 种子将按新路径重新归组」—— 消除与整组迁移提示并排时的「单种子脱离组」歧义(两种模式语义均准确;测试零钉串,守阵无牵连)。
