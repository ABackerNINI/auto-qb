# test-mutation-audit — 变异测试定期审计(指导 / 命令 / 排期锚)

> 摘要: 把可行性报告 `26-10-08-0231` 落成可复用流程 —— 指导 skill + 命令包 + 常驻排期锚 + 方法论坑档。**config / hr / rules / core 四包审计均已收官**(config 与 hr 的真洞 issue 全清, core 计划 W1–W9b 九个工作包全完成), 余量按 issue 口径在池; 逐轮细节在任务档案, 覆盖刻度见常驻锚 §07。
> 最后活动: 2026-11-02 22:45

## 包状态与刻度

| 包 | 终态 | 关键证据 | 指针 |
|---|---|---|---|
| `config/` | 已全清(首轮 + 六个实施轮 + R13) | 首轮 4799 变异 / 存活 893(**80.25%**); S4 逐条 `apply`→全套件确认 274 条 = **54 假存活 + 220 真洞**; 逐轮复跑收口 存活 443 / **90.02%**; 6 条 `test` issue 全实施 | 计划 `plans/26-10-08-0720`(Done); 切片 `testing/baselines/26-10-08-*` / `26-10-09-1611` / `26-10-10-0925` / `26-10-10-1045` |
| `hr/` | 已全清(首轮 R14 + R16–R22 七个模块轮) | 首轮 8027 变异 / 存活 2440(**69.2%**), 墙时 ≈96 min; 宽池 S4 抽验 **24/24 SURVIVED(零假存活)**; 6 条 `test` issue 全 Done | 计划 `plans/26-10-09-1459`; 切片 `testing/baselines/26-10-10-1108` 及之后各模块切片 |
| `rules/` | 已清(R23 首轮) | 名义 59.9% → 实测 **71.8%**; 60 簇守阵全过 | 切片 `testing/baselines/26-10-30-0549` |
| `core/` | 已收官(计划 W1–W9b 九个工作包) | 计划置 Done; 余量在池 | `plans/26-10-31-0128`; 刻度见常驻锚 §07 |

## 方法论要点(结论; 细节在坑档与档案)

1. **存活数是选择池的函数** —— 不同池不可直接比。池宽 ⇒ 零假存活(hr 实测), 池窄 ⇒ 约 20% 假存活(config 首轮), 故 S4 必逐条 `apply` + 全套件确认。
2. **S4 判据先自证干净** —— 镜像池含未提交改动、或两条「读源码文本」守卫在基线就红, 会把候选伪杀成零(writer 长尾 74 条实测); 先排除既有红守卫再判, 得 71 真洞 / 3 假存活。
3. **单条目用例分不出 `continue/break`** —— 必须成对放入「跳过分支条目 + 其后必处理条目」; readonly 路径探针须放**嵌套层**(顶层会被 `real_config_fields()` 滤掉, 首版即踩空转)。
4. **共享镜像会与并行会话冲突** —— 对方 `rm -rf mutants` 冲毁 `.meta`(hr 首轮 85% 作废); 处置 = 专用镜像 + 降 `--children`。大包单轮 >60 min 可续跑(`mutants.run` timeout 3600→7200, mutmut 续跑只补余量), 更稳是按模块切。
5. **工具侧硬坑** —— 红验锚点须保留 CRLF 行尾(LF 拼锚点会 ANCHOR-MISS); `.pyc` mtime 碰撞会复用上一条变异体(假 SURVIVED); mutmut 3.8 有 mtime 竞态(需清增量 + 预置 `src/`); 3.8.0 用 pytest 私有 `_nodeid` 与仓库 pytest 9.2 不兼容, 已升 3.8.1。
6. **每轮实施完成必更常驻锚 §07 覆盖进度总表**(skill 硬约束 12; 不更视为该轮未收尾)。`mutants.status` 在 WSL 下曾恒报 `mutmut=no`(登录壳实为 zsh 取错 cwd, 已修)。

## 未决项

- **余量**: config 包 555 条 S4 未逐条验证候选(按需另立轮); hr / rules / core 余量按各 issue 口径在池, 不另行排期(刻度见锚 §07)。
- `infra/` · `webui/server/` 估值最低, 暂不做(锚 §03)。
- 后续每轮新增计划/档案须同步常驻锚 issue 的 `doc-refs`(现认领链只有本任务档案一条)。
- 跑任一包一律走 task id(`mutants.run` / `mutants.report` / `mutants.verify`), 别再手工拼 S4。

## 资产指针

- 指导 skill: `.agents/skills/mutation-testing/SKILL.md` —— 四段流程 / 硬约束(含 9–15) / 标准步骤 / 三分类 / 派生计划模板。
- 命令包: `.commands/mutants/`(`setup` / `run` / `gremlins` / `status` / `report` / `verify`); 编排在 `scripts/mutants.py`, `[tool.mutmut]` 由 `scripts/set_conf.py` 写, 排障 `references/why.md`。**主仓依赖面与环境未动**(镜像与工具只在 WSL 侧)。
- 任务档案(逐轮细节事实源): `tasks/26-10-08-test-mutation-audit.md`。
- 常驻排期锚(恒 `Open`): `issues/26-10-08-0642-test-mutation-audit-standing.html`。
- 方法论坑档: `pitfalls/testing/` 下 mutation-pool-artifact · mutants-wsl-shell · read-source-static-guard-mutation · mutants-shared-mirror · mutants-mirror-dirty-worktree · redverify-anchor-lineendings · redverify-pycache-stale-verdict · mutmut-mtime-race-stale-trampoline · mutmut-survived-verdict。
- 基线切片: `testing/baselines/` 各轮一条; 最新见 `commands run kb.baseline`。

**R1(2026-10-31 01:57):** 常驻锚蒸馏改版: 移除逐轮台账/逐轮状态日志(事实源=任务档案+基线切片), 只留 §07 覆盖进度总表; 修 hr 漏记 R22 与 core 计划指针漂移; §07 表格排版修复(版心放宽 + 窄视口目录移出栅格 + 固定列宽/路径不换行, 1280 视口实测零换行零滚动); 新增守阵 check_mutation_anchor.py(挂 kb.check+提交闸门, 3 条测试)防流水回归

**R2(2026-11-01 20:54):** 修伞形切片 3 处过时表述为 core 包收官口径(计划 Done, 刻度见锚 §07)

**R3(2026-11-01 21:03):** wrap 档案锚点自证: --archive 命中伞形档案

**R4(2026-11-02 02:56):** W9a/W9b low-residue 余量 issue 成簇守阵收口: 两条分别置 Done; 定向 233 过 + 全量 4805 过(99%); 手搓红验 26/26; 零 src 改动; 未跑 mutmut 全轮

**R5(2026-11-02 03:05):** W7 no-tests 与 W5 零块存疑两件计划外闭合: 注入式直测钉 _run_foreground 18/18 killed(W7 池 566 变异 no tests 归零); W5 两条空块/空桶变异定等价并补解析/入账定向用例; 两件均设置 Done、零 src 改动、未扩池

**R6(2026-11-02 03:18):** W8 遗留两件结清后提交闸门双红清零: 10 件 2026-09 旧档工作树行尾归一 LF(内容零改) + transfer/adapters/qb 的 find_torrent/pause_torrent 等扩展点补 11 条守阵(覆盖率 98.96% -> 99.08%); 全量 4820 过 2 跳; 本轮两笔提交推送

**R7(2026-11-02 20:46):** core W5 traffic_sample_mod 中池单轮复跑收尾: children=1 + 1.5 GiB ulimit, 97 survived 逐 id 对差 W5 终态真新增 0(2 条为 59e814fd 修复后重编号), 4 条 timeout 单列; 2 条表面新增红验 SURVIVED 不声称杀; 结果文件已备份仓库外, 数字见基线切片 26-11-02-2044

**R8(2026-11-02 20:46):** W2 变异 4 件(parse-edges/badbytes-read/boundary-grid/broke-contract)收尾补全: 核对 Done 回写与双向认领链, 全量测试全绿并新建基线切片 26-11-02-2045, 零 src 改动

**R9(2026-11-02 21:36):** 结清 W2 元数据/状态方向 4 件 issue(empty-meta-grid / guard-counter / recorder-defense / snapshot-mixbucket): 零 src 改动, 10 个新守阵用例, 红验 14 KILLED + 2 判等价; 全量测试数字见基线切片 26-11-02-2135

**R10(2026-11-02 22:18):** 结清 W3 标题/年月/键名归一化 4 件 issue，补守阵并消除归一化循环死循环变异面；全量数字见 kb.baseline

**R11(2026-11-02 22:26):** W3 簇3 tvshows 组名括号: 补 test_bracket_group_hint_case_and_negation 守阵, 红验 is_groupish_2/4 + strip_group_19 3/3 KILLED, 零 src 改动

**R12(2026-11-02 22:38):** issue 26-10-31-1212-w3-episodes-dir-strip 结清: 补 test_episode_path_directory_stripped 参数化守阵, names_5/9/14/16 红验 4/4 KILLED, 零 src 改动

**R13(2026-11-02 22:45):** curves W3 簇7/簇8 结清: normalize D 别名 / 坏行同分支累加 / merge_direction 1B/s 非零断言, 红验 4/4 KILLED, 零 src 改动
