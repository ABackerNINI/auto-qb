# 5459 passed + 10 skipped in 119.15s (TOTAL 24538 stmts, 99% cover, 74 miss) —— 合流后复核全量基线(develop tip 099ae067 之上)

> 摘要: 合流后复核全量基线(develop tip 099ae067 之上)
> 基线时间: 2026-11-06 05:39

## 验收数字

- 汇总行: **5459 passed + 10 skipped** in 119.15s(0:01:59, xdist 并行, TMPDIR 由 tests/_tmp_bootstrap.py 自举); 命令整体 121.0s, 1 warning。
- 覆盖率 TOTAL 表末行: **TOTAL 24538 stmts / 74 miss / 8396 branch / 41 partial / 99%**(Windows 侧覆盖闸 99.0, PASS)。
- 口径注记: 较合流前切片(26-11-06-0454)净增 3 用例, 来自远端 f0883292→099ae067 六笔合流面(端口类假红三处全修新增用例), 非本专题改动引入; 产品行为零改动。
- 差值对比: `commands run kb.baseline -n 2`。

## 本改动面

- 本专题无新增产品代码; 本轮为提交动作触发的远端合流复核(开工基线 f0883292, 远端已到 099ae067, 领先 6 笔)。
- 合流冲突三处: `memory-bank/issues/_index.md` 与 `issues/attachments/_archive.md`(生成物, 取一侧后由 `commands run kb.index` 重建到合并后状态) + `scripts/check_command_drift.py`(手写件) —— 远端 de802b01 已补齐同款 `uv-trampoline-broken.md` 逐文件 EXEMPT 及另三条豁免与 _index 跳过逻辑, 本地冗余条目丢弃、采用远端版本。
- 收尾件: 本基线切片 + activeContext 切片 R2 行留痕; `commands run kb.check` 全绿(主键/状态词/认领链/回写措辞/日期/803 个 HTML 结构检查)。
- 收口评审不触发(立档阈值不命中 + 纯注释/文档改动); 未立任务档案。
