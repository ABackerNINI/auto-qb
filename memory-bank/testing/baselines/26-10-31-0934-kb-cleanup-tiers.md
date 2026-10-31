# 4299 passed + 10 skipped —— kb.tier 分级清理四动作 R0 工具轮全量基线

> 摘要: kb.tier 分级清理四动作 R0 工具轮全量基线
> 基线时间: 2026-10-31 09:34
**Refs:** memory-bank/plans/26-10-31-0534-plan-kb-cleanup-tiers.html

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-31 实测, 全量 73.43s, 建档 09:34):

```
  TOTAL                                                21548     163   7400    126    99%
  4299 passed, 10 skipped in 73.43s (0:01:13)
```

- 汇总行: **4299 passed + 10 skipped(Windows)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记: 本轮新增 5 条 kb.tier 测试(四动作覆盖 + 收录守卫, 见下「本改动面」);
  skipped 10 条 = tests-real 真机轨(测试实例未起, `tests-real/conftest.py` 按 port 探活
  跳过) + 少量平台态 skip —— 与上一基线 skipped 数的差异是环境态(实例起没起), 非代码差异。
- 迭代中真红 1 次: purge 首版在部分闸门未过时仍删掉三闸门全过的文件, 违背「全或无」——
  改两阶段(先全体评估后统一删)后复绿, 已由 test_kb_tier_purge_gates_all_or_nothing 钉死。

## 本改动面

- `.agents/skills/memory-bank/scripts/kb_tier.py`(新增): kb.tier 四动作 —— list(--level
  列该级文件含行数/字符数, 未打标件区分呈现) / set(头部区第 4 行 `> 等级: L<n>`, 已有则
  原地改值, 词表外 rc=1) / migrate --level L2(默认 dry-run; --apply 整段叙事逐字节搬
  `pitfalls/<类>/attachments/`, 主档留 `> 已外迁:` 指针, 相对链接自动加一层 `../`, 写完
  回读校验行尾) / purge --level L3(默认 dry-run; 三闸门 —— 守阵齐全/全仓反向引用清零/
  头部 `> 观察通过: YYYY-MM-DD` 标记 —— 任一不过全体拒绝全或无)。
- `.commands/kb/config.toml`: 新增 `[tasks."kb.tier"]` 收录(when/note 按收录协议)。
- `tests/test_memory_bank.py`: 新增 5 条 kb.tier 测试(四动作覆盖 + 收录守卫), 头部 docstring
  「## 测试计划」清单同步; 全部 tmp 夹具进程内 import, 不碰真实 memory-bank/。
- R0 只建能力: 未对真实知识库文件打标/外迁/删除; 本切片与反向声明行是唯一 md 触碰面。
