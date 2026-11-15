# 26-11-15-test-linux-clean — test.linux-clean 三层清扫自动化落地(issue 26-11-13-0212)

**Status:** Done
**Added:** 2026-11-15
**Updated:** 2026-11-15
**Summary:** 认领修复 issue 26-11-13-0212: 计划 26-11-12-0152 承诺的 test.linux-clean 落独立 task id(三层清扫自动化, 演练/--yes 两态, 白名单点名式, PT ban 终闸 + 面杀命令 absence 钉); 评审 3 轮 15 发现全修零 actionable
**Topics:** test-linux-clean
**Refs:** memory-bank/issues/26-11-13-0212-chore-linux-clean-automation.html, memory-bank/plans/26-11-12-0152-plan-linux-testbed-docker.html, memory-bank/pitfalls/testing/docker-id-truncation.md

## 本篇只回答

test.linux-clean 这条清扫自动化是怎么落地的: 形态怎么定的(演练默认 + --yes)、三层各自的纪律与实现锚点、评审揪出哪些真坑、实测数字在哪。方案背景看计划 26-11-12-0152(§03 承诺行 / §10 R9), issue 原文看 issues/26-11-13-0212。

## 原始请求

1. 用户: 「修复 memory-bank/issues/26-11-13-0212-chore-linux-clean-automation.html」—— 即认领该 issue: 落独立 task id `test.linux-clean` 自动化三层清扫, 纪律照抄 S5 手工轮(白名单点名式逐项删, 绝无面杀命令, PT 工具容器与镜像硬禁)。

## 思考过程与决策

- **两态默认(保守默认, 黄金法则 2)**: 无参 = 演练(只读盘点三层, 不动任何东西), `--yes` 才落实删除。删 docker 面是高险动作, 盘点先行是使用姿势。`--safety` 探针**不**自认 action-without-args(与 linux_ci/linux_env 的重动作脚本相反)—— 无参只读演练留在冒烟面。
- **一层复用单点**: 容器内 workdir 清扫执行路径直接调 `linux_ci.sweep_script`(双条件 pid 死 + mtime 12h, 不复制逻辑); `--name <slug>` 点名是清「已完结无标记」残留的唯一口子(正常收尾摘标记, 双条件 sweep 永远碰不到 —— 容器面累积主源), 先过 `linux_ci.sanitize_name` 再进 targeted_script(路径注入闸)。
- **二层三层白名单**: 悬空镜像逐 ID rmi(不带 -f, 在用自然拒绝; 被任何容器引用的先筛掉); 孤儿卷 `^auto-qb-` 白名单且无容器引用; 旧 testbed tag 三保留(current uv.lock hash8 / live 容器镜像 ID / latest, 只动 auto-qb-testbed 仓)。ban 名单终闸(PT 词 + 生产镜像 auto-qb 精确项)命中 [STOP] 全停; 面杀命令/容器删除在源码级 absence 钉死(守阵双形态: 散文 + argv 列表)。
- **--build-cache opt-in**: builder prune -f(S5 手工同款)是唯一批量面, 默认不含。
- **评审拍板修正**: 全部 15 条发现(2 major×2 面重复计 11 + 复评 4)当场修, 无入池。最重要的三条: ① docker CLI ID 截短回环(images {{.ID}} / ps {{.Image}} 默认 12 位 vs 容器 inspect full sha, 比较恒失配 —— 演练把在跑容器的镜像 tag 列成将删项, 实机演练抓出; 修法 = 枚举恒 --no-trunc, 坑档单点见 pitfalls/testing/docker-id-truncation.md); ② absence 守阵只钉散文形态对 argv 列表形态失明(补 `'"(system|volume|image|container)", "prune"'` 正则); ③ 枚举失败(daemon 未起)不许按空清单出假清洁报告(_docker_out 返回 (rc, out), 失败面跳过不删 + had_failure)。

## 实现计划

无独立计划文档(单批落地, 验收标准 = issue 承诺行)。步骤:

1. 写 `.commands/test/scripts/linux_clean.py`(三层 + 两态 + ban 终闸)。
2. 写守阵 `scripts/test_linux_clean.py`(纯函数钉面 + 脚本文本钉面 + absence 钉)。
3. config.toml 加 test.linux-clean 条目(doc 指计划)。
4. 实机演练验证(只读)→ 修演练抓出的 --no-trunc 回环。
5. 回写: 计划 §03 行落地注记 + §10 R9; issue 翻 Done + 修复后补充段; 立本档案。
6. 评审 3 轮(首轮 2 面 11 条 / 复评 4 条 / 三轮 0 条)全修; 引文过检 15/15(评审时点快照树重建核验)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | linux_clean.py 落地(演练/--yes 两态 + 三层白名单 + ban 终闸) | Done(2026-11-15) |
| 2 | 守阵 test_linux_clean.py(18 条, 含 absence/数据流/ban 终闸钉) | Done(2026-11-15) |
| 3 | config.toml 条目 + doc 指针 | Done(2026-11-15) |
| 4 | 实机演练验证 + --no-trunc 回环修复 | Done(2026-11-15) |
| 5 | 文档回写(计划 §03/R9 + issue Done) | Done(2026-11-15) |
| 6 | 评审 3 轮 15 发现全修 + review.check 过检 | Done(2026-11-15) |
| 7 | 容器内 6 个已完结无标记 workdir 的实际 --name 点名清 | Open(留用户演练后 --yes 拍板) |

## 进度日志

### R0 · 立档 (2026-11-15)

- 认领修复 issue 26-11-13-0212 全程单会话完成: 实现 + 守阵 + config + 文档回写 + 评审 3 轮。验证数字(实测): 守阵 18 passed / test.pkg 519 passed / test.quick 6179 passed + 2 skipped / 实机演练 rc 0; 全量基线切片 memory-bank/testing/baselines/26-11-15-0759-test-linux-clean.md(test.full 6179 passed / 2 skipped 覆盖 99%)。评审发现处理: 修 15 / 入池 0 / 检 15/15(含终审 2 条: 认领链双向补链 + 坑档 Refs 归纯)。提交待用户显式指令。

- 2026-11-15 07:55 修复 issue 26-11-13-0212: test.linux-clean 三层清扫自动化落地(演练/--yes 两态 + 白名单点名式 + PT ban 终闸 + absence 钉) + 守阵 18 条 + 评审 3 轮 15 发现全修零 actionable + 坑档 docker-id-truncation + 计划 R9/issue Done 回写; 实测 守阵18/test.pkg519/test.quick6179+2/演练rc0
