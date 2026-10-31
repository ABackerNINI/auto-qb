# 基线切片 26-10-05-0143 — create-issue skill 认领链引导补位 (纯文档轮)

> 摘要: 认领链引导补位第二笔 —— create-issue skill 侧同样只字未提 doc-refs: 两个 issue 模板缺 `doc-refs` meta 行
> (与 doc-forms meta 协议相悖), SKILL.md 认领流程无反向声明步骤。补齐: 两模板 doc-topic 后加空 `doc-refs` meta(认领时填)
> + SKILL.md 新建段注声明位 / 「修一条 issue 时」插第 3 步(填认领链反向声明, 缺了提交闸门判红) / 可移植性 meta 行 / 反模式 1 条。
> 冒烟: 临时目录生成 issue, meta 原样透传 + 索引生成正常。基线时间: 2026-10-05 01:43

- 分支: develop @ 87fef709 (+ 本轮未提交改动: create-issue SKILL.md / 两模板 / 本切片)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2537 passed + 4 skipped, 32.11s (引擎计 32.9s), 覆盖率 TOTAL 99%**
  (14871 语句 / 156 未覆盖 / 4982 分支 / 114 partial; 门槛 98% 达标)
- 相对上基线 (26-10-05-0129: 2532 passed + 4 skipped / 99% / 30.71s): passed **+5** = 同步带入 87fef709
  的新用例(语句 +3); 本轮零代码改动, 无新增用例。
- 改动面: .agents/skills/create-issue/SKILL.md(4 处引导) · assets/issue-light.html + issue-standard.html(各 +1 meta 行)。
  **scripts/ 零改动**。
