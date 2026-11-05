# activeContext 切片归档 · 测试基座 / 变异测试 / 真机轨

> 摘要: 2026-11-05 activeContext 蒸馏轮逐字外迁的 16 条切片原文(2026-10-08~11-03, 变异测试平台/测试基座治理/大文件拆分/真机双环境)。
> 触发: 测试, 变异测试, mutation, TMPDIR, e2e 端口, 真机, 切片归档
> 本文件为逐字归档(attachments 不计 cap); 蒸馏结论与指针写在各 progress 主题文件。
> 归档说明: 原文中的相对链接已因换目录统一补一级 ../, 其余逐字未改。
> 归档说明之二: 原文中的 Refs 声明行改题为「切片原文」以免被知识库认领链解析误读; 链接路径已补一级 ../; 其余逐字未改。

---

<!-- slice: 26-11-01-0050-real-tag-parse-multi-tag.md; 最后活动: 2026-11-01 00:50 -->

# real-tag-parse-multi-tag

> 摘要: 修复 issue 26-10-31-1215(tests-real 多标签解析丢空白): lib/guard.py 新增 tag_set 单点, seed.py/_fakes 与 guard.snapshot 同改; 真机复验 list/guard/rm 三面通过; 新坑档 pitfalls/testing/qb-tags-multi-split-strip.md
> 最后活动: 2026-11-01 00:50
**Refs（切片原文）:** memory-bank/issues/26-10-31-1215-bug-real-tag-parse-multi-tag.html, memory-bank/pitfalls/testing/qb-tags-multi-split-strip.md

**R0(2026-11-01 00:50):** 修复 issue 26-10-31-1215(tests-real 多标签解析丢空白): lib/guard.py 新增 tag_set 单点, seed.py/_fakes 与 guard.snapshot 同改; 真机复验 list/guard/rm 三面通过; 新坑档 pitfalls/testing/qb-tags-multi-split-strip.md

---

<!-- slice: 26-11-01-0725-mutation-core-w6-orchestrator.md; 最后活动: 2026-11-01 07:25 -->

# mutation-core-w6-orchestrator

> 摘要: W6(R30) S6-S8 收口: 同池复跑 78.51%(修正口径)新增存活 0, 切片+档案 R30+锚 §07/§03 更新
> 最后活动: 2026-11-01 07:25

**R0(2026-11-01 07:25):** W6(R30) S6-S8 收口。S6 同目标同池复跑(5 文件分跑一次干净跑完): 1,275 变异, 全轮实测 杀 997/存活 101/超时 20/no tests 157(78.20%), 26 条条目级复验后修正口径 杀 1,001/超时 16(**78.51%**); 新增存活 0(101 ⊆ 首轮 444)。连带杀 17 条判读等价全稳定(新守阵精确断言转可观测, 同 W4 z_row_39 形态)+ 盲区回收 run_20 + gtn_17 转盲区 + 真洞残存活 6(含 3 条签名默认极低, S5b 红验覆盖声明对它们不成立)。test.full 全绿(数字见 kb.baseline, 切片 testing/baselines/26-11-01-0722-mutation-core-w6-orchestrator.md); 任务档案 R30 条目 + 锚 §07/§03 已更; 本地 commit 未 push。

---

<!-- slice: 26-11-01-0859-real-machine-dual-env.md; 最后活动: 2026-11-01 08:59 -->

# real-machine-dual-env

> 摘要: 真机轨双环境化: 新增 tests-real/lib/env_registry.py 单点(环境1 D盘机 36595/36596 与环境2 C盘机 56589/56590, QBT_REAL_ENV 显式 > EXE 探测 > fail-closed), guard/instances/runner/rm00-rm10 全部端口字面量改派生 + docstring 角色化; 新增 real.env 命令; token 口径改不落盘(用户每轮会话给 QBT_TEST_加端口号环境变量); 环境2 首轮基建实测: real.up 拉起双实例 + guard 全绿(firewalled), 踩坑 profile 残留环境1 网卡标识 ethernet_32769 → 双实例 disconnected 假红, 已置空修复入坑档; BT 端口 27049/32719 等环境2 事实回填规程 §2.5.2; 基线切片 26-11-01-0858(数字见 kb.baseline; src/ 零改动零扰动)
> 最后活动: 2026-11-01 08:59
**Refs（切片原文）:**

**R0(2026-11-01 08:59):** 真机轨双环境化: 新增 tests-real/lib/env_registry.py 单点(环境1 D盘机 36595/36596 与环境2 C盘机 56589/56590, QBT_REAL_ENV 显式 > EXE 探测 > fail-closed), guard/instances/runner/rm00-rm10 全部端口字面量改派生 + docstring 角色化; 新增 real.env 命令; token 口径改不落盘(用户每轮会话给 QBT_TEST_加端口号环境变量); 环境2 首轮基建实测: real.up 拉起双实例 + guard 全绿(firewalled), 踩坑 profile 残留环境1 网卡标识 ethernet_32769 → 双实例 disconnected 假红, 已置空修复入坑档; BT 端口 27049/32719 等环境2 事实回填规程 §2.5.2; 基线切片 26-11-01-0858(数字见 kb.baseline; src/ 零改动零扰动)

**R1(2026-11-01 08:59):** 真机轨双环境化: 新增 tests-real/lib/env_registry.py 单点(环境1 D盘机 36595/36596 与环境2 C盘机 56589/56590, QBT_REAL_ENV 显式 > EXE 探测 > fail-closed), guard/instances/runner/rm00-rm10 全部端口字面量改派生 + docstring 角色化; 新增 real.env 命令; token 口径改不落盘(用户每轮会话给 QBT_TEST_加端口号环境变量); 环境2 首轮基建实测: real.up 拉起双实例 + guard 全绿(firewalled), 踩坑 profile 残留环境1 网卡标识 ethernet_32769 → 双实例 disconnected 假红, 已置空修复入坑档; BT 端口 27049/32719 等环境2 事实回填规程 §2.5.2; 基线切片 26-11-01-0858(数字见 kb.baseline; src/ 零改动零扰动)

---

<!-- slice: 26-11-01-1054-test-yamls-removal.md; 最后活动: 2026-11-01 10:54 -->

# test-yamls-removal

> 摘要: 认领 issue 26-11-01-0800: test_yamls 整目录移除 + 引用面清理(launch.json/.dockerignore/AGENTS.md/4 份 KB 文档), test.full 稳定树全绿, 基线切片 26-11-01-1054
> 最后活动: 2026-11-01 10:54
**Refs（切片原文）:**

**R0(2026-11-01 10:54):** 认领 issue 26-11-01-0800: test_yamls 整目录移除 + 引用面清理(launch.json/.dockerignore/AGENTS.md/4 份 KB 文档), test.full 稳定树全绿, 基线切片 26-11-01-1054

---

<!-- slice: 26-11-01-2157-real-rm08.md; 最后活动: 2026-11-01 21:57 -->

# real-rm08

> 摘要: RM08 漂移复测轮官方 suite 实测(7 passed / 1 skipped, 143.43s)
> 最后活动: 2026-11-01 21:57
**Refs（切片原文）:**

**R0(2026-11-01 21:57):** RM08 漂移复测轮官方 suite 实测(7 passed / 1 skipped, 143.43s)

**R1(2026-11-01 21:57):** RM08 漂移复测轮官方 suite 实测(7 passed / 1 skipped, 143.43s)

---

<!-- slice: 26-11-02-0056-test-traffic-sample-livetail-interval-contract.md; 最后活动: 2026-11-02 00:56 -->

# test-traffic-sample-livetail-interval-contract

> 摘要: 修复 issue 26-11-01-0050(改间隔复位窗口无块 LiveTail 取陈旧旧块 interval_s): _publish_live_tail 加 has_block 守门, 补契约守阵一条, 全量测试全绿
> 最后活动: 2026-11-02 00:56
**Refs（切片原文）:** memory-bank/issues/26-11-01-0050-bug-traffic-sample-livetail-stale-interval.html

**R0(2026-11-02 00:56):** 修复 issue 26-11-01-0050(改间隔复位窗口无块 LiveTail 取陈旧旧块 interval_s): _publish_live_tail 加 has_block 守门, 补契约守阵一条, 全量测试全绿

---

<!-- slice: 26-11-02-0212-mutation-tooling-deselect-guards.md; 最后活动: 2026-11-02 02:12 -->

# mutation-tooling-deselect-guards

> 摘要: 修复 issue 26-10-31-1539(deselect-guards): DEFAULT_DESELECT 表前补同步纪律 + cmd_run 基线失败行点名该表 + DeselectTableTest 机械对差守阵(覆盖新 FLAKY_DESELECT); issue 置 Done, 数字见基线切片 26-11-02-0209
> 最后活动: 2026-11-02 02:12
**Refs（切片原文）:** memory-bank/issues/26-10-31-1539-bug-mutation-tooling-deselect-guards.html

**R0(2026-11-02 02:12):** 修复 issue 26-10-31-1539(deselect-guards): DEFAULT_DESELECT 表前补同步纪律 + cmd_run 基线失败行点名该表 + DeselectTableTest 机械对差守阵(覆盖新 FLAKY_DESELECT); issue 置 Done, 数字见基线切片 26-11-02-0209

---

<!-- slice: 26-11-02-0213-mutation-tooling-verify-channel.md; 最后活动: 2026-11-02 02:13 -->

# mutation-tooling-verify-channel

> 摘要: 修复 issue 26-10-31-1539(verify-channel)四形态: verify 前置注册表预检 + APPLY_FAIL 归未判定可重试; why.md 固化 dump->post-image 手工通道; FLAKY_DESELECT 自动 deselect; _ensure_mirror 先探 WSL 可达性再分三态(不对不可达 clone); issue 置 Done, 数字见基线切片 26-11-02-0209
> 最后活动: 2026-11-02 02:13
**Refs（切片原文）:** memory-bank/issues/26-10-31-1539-bug-mutation-tooling-verify-channel.html

**R0(2026-11-02 02:13):** 修复 issue 26-10-31-1539(verify-channel)四形态: verify 前置注册表预检 + APPLY_FAIL 归未判定可重试; why.md 固化 dump->post-image 手工通道; FLAKY_DESELECT 自动 deselect; _ensure_mirror 先探 WSL 可达性再分三态(不对不可达 clone); issue 置 Done, 数字见基线切片 26-11-02-0209

---

<!-- slice: 26-11-02-0745-testing-tmpdir-bootstrap.md; 最后活动: 2026-11-02 09:44 -->

# testing-tmpdir-bootstrap

> 摘要: TMPDIR 自举+互斥锁五步实施完毕, 逐条判据实测通过; coverage 改走 retarget_cov_data_file 修正面(pytest-cov 早于 conftest 绑定 .coverage, env 无效); 计划 26-11-02-0657 转 Done
> 最后活动: 2026-11-02 09:44
**Refs（切片原文）:**

**R0(2026-11-02 07:45):** TMPDIR 自举+互斥锁五步实施完毕, 逐条判据实测通过; coverage 改走 retarget_cov_data_file 修正面(pytest-cov 早于 conftest 绑定 .coverage, env 无效); 计划 26-11-02-0657 转 Done

**R1(2026-11-02 07:45):** TMPDIR 自举+互斥锁五步实施完毕, 逐条判据实测通过; coverage 改走 retarget_cov_data_file 修正面(pytest-cov 早于 conftest 绑定 .coverage, env 无效); 计划 26-11-02-0657 转 Done

**R2(2026-11-02 08:00):** 拍板轮收尾: 计划09节/边界②明示本轮未跑test.full(留提交轮不标已验证); AGENTS.md的TMPDIR旧句回写新机制(自举R→H→C:\Users\11059\AppData\Local\Temp/外部拒收rc=4/换根改TMP_ROOT_CANDIDATES); 计划补变更记录段+kb.bump(R1); .tmp_s3_t1.py核实已被git追踪(e2fa1625)按用户条件停手未删

**R3(2026-11-02 08:39):** 提交轮: 全量 test.full 实测跑绿(首跑一红=新建 test_tmp_bootstrap.py 缺「测试计划」清单, 补 7 条后复跑); 新建基线切片 26-11-02-0838; 计划边界②/09节改记为提交轮已验证(kb.bump R2); git rm .tmp_s3_t1.py; kb.index 23 生成物

**R4(2026-11-02 09:44):** 端口分层补做提交轮: 全量 test.full 全绿(增量为端口守卫新用例, 数字见 kb.baseline 切片 26-11-02-0943); 走 ship.commit 入库

---

<!-- slice: 26-11-02-2219-test-sidefx-guard.md; 最后活动: 2026-11-02 22:19 -->

# test-sidefx-guard

> 摘要: 修复 sidefx 串行假阳性: 临时根按当前 TMPDIR 按需重算(延迟求值+签名缓存) + 回归测试 test_sidefx_temp_roots_follow_tmpdir_switch
> 最后活动: 2026-11-02 22:19
**Refs（切片原文）:**

**R0(2026-11-02 22:19):** 修复 sidefx 串行假阳性: 临时根按当前 TMPDIR 按需重算(延迟求值+签名缓存) + 回归测试 test_sidefx_temp_roots_follow_tmpdir_switch

---

<!-- slice: 26-10-08-0642-test-mutation-audit.md; 最后活动: 2026-11-03 00:26 -->

# test-mutation-audit — 变异测试定期审计(指导 / 命令 / 排期锚)

> 摘要: 把可行性报告 `26-10-08-0231` 落成可复用流程 —— 指导 skill + 命令包 + 常驻排期锚 + 方法论坑档。**config / hr / rules / core 四包审计均已收官**(config 与 hr 的真洞 issue 全清, core 计划 W1–W9b 九个工作包全完成), 余量按 issue 口径在池; 逐轮细节在任务档案, 覆盖刻度见常驻锚 §07。
> 最后活动: 2026-11-03 00:26

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
- 后续每轮新增计划/档案须同步常驻锚 issue 的 `doc-refs（切片原文）`(现认领链只有本任务档案一条)。
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

**R14(2026-11-02 22:51):** W3 四件 test issue 收尾: 全量 test.full 后新建基线切片 26-11-02-2250 并回补四件 doc-refs（切片原文）

**R15(2026-11-02 23:48):** W4 批次 2 issue 结清: extreme-low-residue(6 用例, 红验 17/17 KILLED) + observability-logs(4 用例, 红验 18/19 KILLED, _wblp_20 判等价), 各随件提交 5f63962e/da5f498a; 全量 4896 passed + 10 skipped, 基线切片 26-11-02-2348

**R16(2026-11-03 00:26):** 修复 tvshows 展示名尾 trim 拆散成对括号缺陷(Show.Name.(US) -> Show Name (US)); 新增守阵 test_title_paired_bracket_tail_preserved; 全量 4897 passed + 10 skipped; 基线切片 26-11-03-0025; 更新 issue 26-10-31-1212 状态日志

---

<!-- slice: 26-11-02-1213-real-machine-rm04-drift-plan.md; 最后活动: 2026-11-03 00:38 -->

# real-machine-rm04-drift-plan

> 摘要: RM04 漂移复测计划收尾: RM04-05 负向对照 Z:/ 上溯整链不可判定红验落地(issue 26-11-02-1144 闭环), RM04-09 facade shareLimitAction PASS(issue 26-11-01-2102 闭环), 计划 Done. issue 26-11-02-1208 仍 In Progress: 纯函数层四条判别红验已闭环; 真机 L490 段改为显式入口 QBT_REAL_SMALL_TARGET + 硬守卫; 上一轮「隐藏 Recovery 卷 + mklink /J」做法已废弃并彻底移除(该卷是系统恢复分区); 本轮重跑主链全过、L490 段以明确断言失败提示用户准备小容量卷(非 skip), 待前置复验.
> 最后活动: 2026-11-03 00:38
**Refs（切片原文）:** memory-bank/plans/26-11-01-2033-plan-real-machine-rm04-drift-plan.html, memory-bank/issues/26-11-02-1208-bug-rm04-gate-space-crossvol-branch-missing.html

**R0(2026-11-02 12:13):** RM04 漂移复测计划收尾: RM04-05 负向对照 Z:/ 上溯整链不可判定红验落地(issue 26-11-02-1144 闭环), RM04-09 facade shareLimitAction PASS(issue 26-11-01-2102 闭环), 真机 9 passed 全绿, 计划 Done. 方案B跨卷空间不足分支另立 issue 26-11-02-1208 交他环境.

**R1(2026-11-02 22:07):** 认领修复 issue 26-11-02-1208: L490 跨卷空间不足分支在纯函数闸门层补四条判别红验(严格小于才拒/恰等放行/same_volume=None 保守拒/同卷豁免), 产品代码零改动; issue 置 Done; 全量数字见基线切片 26-11-02-2206. (R1 里「真机前置本机不可造」的前提已被 R2 更正)

**R2(2026-11-02 22:43):** 前提更正重做真机验证: 接手机环境1 与撰写 issue 的环境2 不同, 隐藏 Recovery 卷(free 86,564,864)经 mklink /J 造出「跨卷 + target_free<needed」前置并跑 L490 拒绝分支 —— status=error + gate=space + 文案「空间不足」+ 零 started + 零「迁移发起」; RM04-05 单跑 1 passed 94.55s, RM04 套件 9 passed 186.99s; 改动仍在 tests-real + 纯函数红验, src/ 零 diff; issue 维持 Done 并改写错误改道理由; 真机数字见 real-baselines 26-11-02-2243. (该隐藏卷构造已废弃并移除, 见 R4)

**R3(2026-11-02 22:51):** issue 26-11-02-1208 前提更正后重做真机 RM04-05 L490 跨卷空间不足分支: 隐藏 Recovery 卷经 junction 造前置, 真跑命中拒绝分支, RM04 套件 9 passed; issue 维持 Done 并改写错误改道理由. (**该做法已废弃并移除, 见 R4**)

**R4(2026-11-02 23:46):** 磁盘安全性复验: 隐藏 Recovery 卷构造已废弃并彻底移除(用例删 _volume_roots/small_volume_junction, 文档/issue/基线改为『曾用过、已废弃并移除』并保留证据链); 新增 tests-real/lib/small_target.py 显式入口 QBT_REAL_SMALL_TARGET + 硬守卫与 tests/test_real_machine_safety.py 复发守卫(4 passed); 正向对照证明普通大容量目录不等价于真跨卷; 真机重跑 RM04-05 1 failed 8 deselected 33.09s(唯一失败为 L490 段前置缺失显式断言, 主链全过); issue 退回 In Progress 待用户准备小容量目标; 产品代码零改动; 全量 4899 passed 2 skipped

**R5(2026-11-03 00:06):** ImDisk 内存盘前置调研: 官方 CLI 语法/-o fix-rem/-s 单位/-d-强制-D 卸载确认; 本机 imdisk 2.1.1 驱动 RUNNING、AWEAlloc STOPPED; 当前进程 Medium 未提权, 非提权尝试产生半挂载设备 0 + 格式化失败(退出码 0 但 Y: 不存在), 已用 -D 清理; 配方写入 real-machine.md §2.9 作为首选; issue 1208 维持 In Progress 待用户提权实跑

**R6(2026-11-03 00:38):** issue 26-11-02-1208 真机复验跑通: 用户手动挂载 ImDisk 96M 内存盘(Y: FreeSpace 84,054,016 < needed 134,217,728, st_dev 互异), QBT_REAL_SMALL_TARGET 下 RM04-05 六条 L490 断言全成立(1 passed 32.90s), RM04 套件 9 passed 199.57s, 全量 4909 passed 2 skipped; issue 置 Done; real-machine.md §2.9 改 ImDisk 为唯一指定前置; 测试实例已关停, 内存盘保留待用户卸载; src 零 diff

---

<!-- slice: 26-11-03-0332-test-web-longtail-clock-pin.md; 最后活动: 2026-11-03 04:22 -->

# test-web-longtail-clock-pin

> 摘要: 修复 CI flaky: test_api_traffic_qb_global_live_tail_realtime 入口钉钟(5m 滚动窗跨 30s 边界桶数翻转); 全量 4915 passed/10 skipped/99%
> 最后活动: 2026-11-03 04:22
**Refs（切片原文）:**

**R0(2026-11-03 03:32):** 修复 CI flaky: test_api_traffic_qb_global_live_tail_realtime 入口钉钟(5m 滚动窗跨 30s 边界桶数翻转); 全量 4915 passed/10 skipped/99%

**R1(2026-11-03 04:22):** P1/P2 三条尾桶边界用例按 B 端点固定钟收口(helper 单点); 双面钟红/绿实证; 定向 168 passed, 全量 4915 passed/10 skipped/99%

---

<!-- slice: 26-10-31-0132-mutation-core.md; 最后活动: 2026-11-03 04:29 -->

# mutation-core

> 摘要: core/ 变异测试分步计划 26-10-31-0128 已整包收官(W1–W9b): 九个工作包全部完成、计划置 Done、§04.3 验收五项自查通过; D1–D3 已决(计划 §06); 刻度见常驻锚 §07, 轮次明细见任务档案, 逐轮数字见最新切片。
> 最后活动: 2026-11-03 04:29

**R0(2026-10-31 01:32):** 新建 core/ 变异测试分步计划 26-10-31-0128-plan-mutation-core.html: `**/core/**/*.py` 32 文件 14,710 行摸底, 不做整包首轮, 拆 W1–W9 按出错代价排序; 三个池面缺口立牌(state.py / qbapi.py / reader.py)。

**结果指针(本专题只认这几处, 不在此复述):** 覆盖刻度·轮次·状态 = 常驻锚 `issues/26-10-08-0642-test-mutation-audit-standing.html` §07 core 行; 轮次明细 = `tasks/26-10-08-test-mutation-audit.md`(R25–R34); 逐轮数字 = `testing/baselines/` 最新切片(`commands run kb.baseline`); 计划状态 = `plans/26-10-31-0128-plan-mutation-core.html`(Done); 余量真洞按 issue 口径在池不补测不排期。

**R1(2026-11-01 20:43):** 收尾蒸馏: 计划 26-10-31-0128 置 Done(W1–W9b 整包收官, R25–R34 十轮验收五项通过), 切片正文收敛为结果指针; 另补常驻锚 §07 core 行 W9b 切片链接(10 条齐)。

**R2(2026-11-03 04:29):** 认领并结清 issue 26-10-31-0458(W1 state 读侧 encoding 守阵): core/state.py 零改动, 补 builtins.open 探针守阵 test_read_state_file_pins_utf8_encoding(主文件 + .bak 双覆盖), 红验两回归形态(encoding=None / 删参)均红, 全量套件通过(数字见 kb.baseline); 选型改道: 探针式行为守阵替代源码文本守阵, 无需 mutants deselect。

---

<!-- slice: 26-11-03-0431-test-port-zero.md; 最后活动: 2026-11-03 04:48 -->

# test-port-zero

> 摘要: e2e/开发桩端口改 0 并由脚本取号回传; S1-S6 完成, 并发双 e2e 验收通过, 全量基线见 kb.baseline
> 最后活动: 2026-11-03 04:48
**Refs（切片原文）:**

**R0(2026-11-03 04:32):** S1-S5 实施完成并验收(并发双 e2e 独立端口); 档案已立, S6 命令入口/行为文档待授权
**R1(2026-11-03 04:48):** S6 文档同步: dev 包说明改脚本取号口径、smoke/browser-env 更新、4 处坑档补现状注记; doc.caps/drift/links 与 memory-bank 守阵全绿; 计划与档案转 Done

---

<!-- slice: 26-11-03-0042-test-big-file-split.md; 最后活动: 2026-11-03 08:20 -->

# test-big-file-split

> 摘要: 按计划完成 R1: 10 个大型测试文件 move-only 拆为 36 个测试文件 + 12 个支撑/扫描模块; 906 个测试函数名与 1170 个模块级界定逐字不变; 全量见 kb.baseline; 12 个仍超千行的桶留 R2
> 最后活动: 2026-11-03 08:20
**Refs（切片原文）:**

**R0(2026-11-03 00:42):** 按计划完成 R1: 10 个大型测试文件 move-only 拆为 36 个测试文件 + 12 个支撑/扫描模块; 906 个测试函数名与 1170 个模块级界定逐字不变; 全量见 kb.baseline; 12 个仍超千行的桶留 R2

**R1(2026-11-03 01:58):** R2 完成: 25 个测试文件 move-only 拆为 90 桶 + 20 support(用例数守恒), 同步并入远端 test_kb_nav 新用例, 新口径与排期清单入计划, 全量见 kb.baseline

**R2(2026-11-03 03:27):** R3 完成: 4 个工具/脚本/扩展文件 move-only 拆分(sim_qb 2077->166 入口+4 模块; qb_capture 1559->959+2 模块; background.js 1427->642+2 分片; test_server.py 1274->552+1 support+2 分文件), 3 个暂缓零改动; 扩展守阵按 importScripts 顺序拼接 bundle; 全量见 kb.baseline

**R3(2026-11-03 04:59):** R4 完成: 8 个前端文件 move-only 拆为 20 个域名片段 + 4 段连续 CSS(2 暂缓/2 不拆零改动), 四皮肤清单与守阵域聚合读同步; 新桶均 <=1000(最大 804), 排期无新增

**R4(2026-11-03 08:20):** R5 完成并收束计划: 9 个后端大文件 move-only 拆分(34 个新模块, 2 暂缓零改动), patch 敏感名留根/MRO 与公开面不变, 新桶最大 945; 全量见 kb.baseline; 计划 R1-R5 全部完成, 状态 Done

