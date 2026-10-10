# 2886 —— 变异测试回灌(hr 首轮经验进 skill / 报告 / 命令包) + §03 漂移修复基线

> 摘要: 按 hr 首轮(R14)经验回灌变异测试指导面 —— skill 硬约束 **14/15** + 三分类「假存活率是池宽的函数」推论 + 派生计划 §2 墙时口径 / §5 停手点 + 4 条反模式 + 记录口径(轮次撞号); 新坑档 `pitfalls/testing/mutants-shared-mirror.md`; 报告 §14 第六/七/八条修正 + 「hr 包首轮实测」小节; 命令包 `config.toml`(`mutants.run` timeout 3600→7200)/ `references/why.md`(排障表 4 行 + hr 锚点 + 环境事实)。另修常驻锚 §03 `config/` 行漂移(六轮 → 七轮, 补 R13)。**零 `src/` / `tests/` 改动**。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-10 11:35

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2886 passed + 4 skipped / 0 failed / 覆盖率 TOTAL 99%**(16568 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标)

## test.pkg 实测(包脚本面)

- 命令: `commands run test.pkg`(`.commands/` 包脚本测试面 —— 本轮动了 `mutants` 包的 `config.toml` timeout)
- **实测**: **155 passed**(73.77s)

## 本轮改了什么(全是指导面 + 一处包配置值)

- **skill** `.agents/skills/mutation-testing/SKILL.md`: 硬约束 **14**(多 clone 并行用专用镜像)/ **15**(大包单轮 >60 min 且可续跑) + 三分类节新增「假存活率是池宽的函数」推论 + 派生计划 §2 墙时口径 / §5 停手点 + 坑指针 + 4 条反模式 + 记录口径「轮次号先看远端再取」; 流程约束计数 4→7。
- **坑档** `pitfalls/testing/mutants-shared-mirror.md`(新): 并行会话 `rm -rf mutants` 冲毁正在跑的 `.meta`。
- **报告** `reports/26-10-08-0231-…html`: §14 第六/七/八条修正 + 「hr 包首轮实测」小节 + §15 变更记录 + 抬 `doc-updated`。
- **命令包** `config.toml`(`mutants.run` timeout 3600→7200, note 补专用镜像 / 续跑提示)/ `references/why.md`(排障表 4 行 + hr 锚点 + 环境事实的专用镜像说明)。
- **常驻锚** `issues/26-10-08-0642-…html`: §03 `config/` 行漂移修复(六轮 → 七轮, 补 R13)+ §09 两条日志。
