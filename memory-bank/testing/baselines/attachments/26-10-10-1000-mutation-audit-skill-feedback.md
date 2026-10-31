# 2878 —— 变异测试指导回灌(形态级复验进 skill / 报告 / 命令包 / 锚)基线

> 摘要: 用户「根据此轮经验优化变异测试 skill 与指导文档」—— 把 R11(config loader-defaults 轮)现踩出的两条可复用经验回灌进指导: ①**形态级手搓复验**(只有变异形态没给 id 时, 临时脚本造同构变异跑**定向池** ≈3s/条, 对 `mutants.verify` 全套件 ≈15s/条; 边界 = 手搓条数**不进存活计数**, 量化只认 `mutants.run`)②**等价变异的一类新形态**(派生值恰等于字段默认 ⇒ 删实参/默认值换 None 是等价变异, 判等价前先造能区分的输入)。落点: `.agents/skills/mutation-testing/SKILL.md`(硬约束 13 + 专节 + 三分类 + 坑指针 + 3 条反模式)、证据报告 §14 第五条流程修正 + §15 变更记录、命令包 `references/why.md`、常驻锚 §05/§06/§09。**`src/` 与 `tests/` 零改动**(纯文档), 故测试面与上基线逐位持平。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-10 10:00

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## test.full 实测

- 分支: `develop`(工作树含本轮文档回写时实测; 与 R11 提交 `0dea0884` 同一基线上)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时/波动口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2878 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial)
- 覆盖率明细(语句 / 未覆盖 / 分支 / partial)与上一条切片 [26-10-10-0925](../baselines/26-10-10-0925-mutants-config-loader-defaults.md) **逐位持平** —— 本轮零代码 / 零测试改动, 覆盖事实无变化属预期。
- passed 较上条切片 **+1**: 本轮没加任何用例, 且已用 `git stash -u` 对照确认**收集数 2882 与提交基线 `0dea0884` 一致**、两份新切片各加不加都不改收集数 ⇒ 差值不是本轮引入的用例; 未逐条定位到具体哪一条(不追 —— 不影响本轮「零 `src/` / `tests/` 改动」的结论, 也不影响覆盖率读数)。
- Linux(WSL 沙箱)侧未重测 —— 本轮零代码 / 零测试改动, 无平台相关事实变更(口径见 baseline.md 常驻警告)。
