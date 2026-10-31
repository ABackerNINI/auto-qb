# 4300 passed + 10 skipped —— kb 分级清理 R1 试点轮(git+ops)全量基线

> 摘要: kb 分级清理 R1 试点轮(git+ops)全量基线
> 基线时间: 2026-10-31 10:29
**Refs:** memory-bank/plans/26-10-31-0534-plan-kb-cleanup-tiers.html

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-31 实测, 全量 78.81s, 建档 10:29):

```
  TOTAL                                                21548    163   7400    126    99%
  4300 passed, 10 skipped in 78.81s (0:01:18)
```

- 汇总行: **4300 passed + 10 skipped(Windows)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记: 相对上基线(4299 passed)净增 1 条 = 本轮新增
  `test_kb_tier_migrate_skips_already_migrated`(migrate 幂等闸); skipped 10 条 =
  tests-real 真机轨(测试实例未起, `tests-real/conftest.py` 按 port 探活跳过) + 少量
  平台态 skip —— 与上基线 skipped 数的差异是环境态(实例起没起), 非代码差异。
- 迭代中真红 1 次: prod-files.md 重写时删了各条目的 `- **触发**:` 行, 守阵
  `test_kb_pitfall_entries_have_required_fields` 判红(每条目三必填字段), 恢复字段后复绿
  —— pitfall 条目的「触发」行是结构必填, 不是可删的叙事。
- 配套验证: doc.links 绿 / doc.caps 债务 7 项(全部 §2.6 既有项, git/ops 零新增) /
  kb.check 绿 / kb.index 重建 21 生成物 / kb.tier list 四级核对: L0×16(git 9 + ops 7) ·
  L1×6(git 4 + ops 2) · L2×2(git, 均已外迁带指针) · L3×0 · 未打标 226(其余 5 类, R2 面)。

## 本改动面

- `memory-bank/pitfalls/ops/` 9 主题文件定级: L0×7(alert-levels, console-encoding,
  docker-host-features, msys-container-path, prod-files, session-program-blacklist,
  shell-env) / L1×2(agent-write-guard-secret-false-positive, port-kill-prod-instance) /
  L2×0 / L3×0(无守阵齐全 + 观察期件, 不启用)。
- L1 删叙事(判别法与判据单点一字不动): port-kill 事故形态四条根因流水压缩为 2 行 + 指向
  任务档案; agent-write-guard 复发①-⑤流水/影响面逐文件日期清单压缩为判据沉淀((a) 行号=
  重建文本行号 (b) oldText 缩不含命中行照拒), 整文件级探针/形状速查/等价改写工具箱全数保留。
- ops/ 主题文件 32,070 → 30,426 字符(-1,644, -5.1%); R1 试点全程(git+ops) 85,273 →
  71,076 字符(-16.6%)。ops 零外迁: 9 件判别法全是唯一单点(环境事实/红线明细), 无「已彻底
  解决、叙事零贡献」的 L2 形态。
- 过时约束修正(计划 §2.3 点名的 ops/ 一处): prod-files.md 「不许改/不许提交」禁令口吻改为
  「`red_lines` 机器预检强制执行 + 人工红线说明」, 保留红线清单与判别, 消除与预检的重复。
- 工具幂等修复(计划内, `.agents/skills/memory-bank/scripts/kb_tier.py`): migrate 对已带
  `> 已外迁:` 指针的主档一律幂等跳过(旧逻辑把已迁档当目标扫, R1 实测 dry-run 清单包含
  git/ 两件已迁档); 同步守阵 `test_kb_tier_migrate_skips_already_migrated`(残留 `## ` 段
  也不二次外迁、零写盘) + 脚本 docstring 与测试文件「## 测试计划」清单。
- 行尾事实修正: msys-container-path / docker-host-features 工作区副本历史上是 CRLF
  (HEAD 存 LF), 本轮统一归一回 LF, 提交 diff 只含内容变化。
