# 26-11-26-dev-repo-layout-refactor — 仓库目录结构重构

**Status:** In Progress
**Added:** 2026-11-26
**Updated:** 2026-11-26
**Summary:** 仓库目录结构重构:测试树三分(tests/{unit,e2e,real})与根目录瘦身;方案权威在计划 26-11-26-0503(Open),本档案跟踪执行 S0–S5 与验收
**Topics:** dev-repo-layout-refactor
**Refs:** memory-bank/plans/26-11-26-0503-plan-repo-layout-refactor.html

## 本篇只回答

本档案回答:仓库目录结构重构专题做到哪了、按什么口径执行与验收;方案与取舍的权威在计划 `memory-bank/plans/26-11-26-0503-plan-repo-layout-refactor.html`(doc-topic repo-layout-refactor),本档案只跟踪执行与验证,不重写方案。

## 原始请求

1. 「目前项目的文件/目录结构稍微有些混乱」+ 五条举例(assets 早期资产并入 resources;config/.dockerignore/Dockerfile 属 docker;e2e/tests-real/tests 三处放一起;hatch_build.py/minimal.yml 不放根;scripts 的 sim_* 单独工具入 tools/)+「还可能有其它问题,分析哪些文件的位置不合理…grilling 然后出一个改造计划」。
2. 拍板轮:config/ 挪(尚无 docker 用户);Dockerfile/.dockerignore 保留;原 tests 目录的测试移子目录;hatch_build.py 挪;sim_ 挪 tools/sim/;env.sh 删除;pytest.ini 并入 pyproject;其余按推荐。
3. 追问轮:语料抓取器(qb_capture 三件)与 sim 同族,一并迁 tools/sim/。
4. 「提交」:计划/档案/切片入库。

## 思考过程与决策

- 只读全库盘点引用面(HEAD 303164f1)发现隐藏耦合:tools/ 被生产代码运行时 tool_dir 解析(伴生工具语义)、e2e 被 8 类字面引用钉住、tests-real 被 .commands/real 与安全守阵钉住且并入 tests/ 会被主套件误收集、pytest.ini addopts 与 tests/_tmp_bootstrap.py 是并行/TMPDIR/覆盖率闸单点、.dockerignore 有窟窿(node_modules/ 与 config/ 生产凭据进 build context)。
- grilling 一轮九问(Q1–Q9)→ 用户拍板 D1–D11:四处改判(D3 config 入 docker/、D7 hatch_build 入 scripts/、D8 sim 入 tools/sim/、D10 pytest.ini 并入 pyproject)+ 一条追加(原 tests 内容移 tests/unit 子目录);R1 追问后扩围 qb_capture 三件整族迁移。
- 执行设计要点:tests/real 用 marker 三件套防误收集;JS 清单留根只改 testDir;tests/ 不留顶层 conftest(unit 夹具不外溢);pytest rootdir 锚转 pyproject(含 ini_options 即成立)。
- 结论与 D 编号权威 = 计划 §03/§06;本档案不重写方案。

## 实现计划

权威 = 计划 §04:S0 前置快照(引用清单冻结/collect-only 计数/各 clone WIP 核验/docker build 冒烟)→ S1 根瘦身批 → S2 测试树批 → S3 pytest 合并批 → S4 回写批 → S5 终验收尾(结构守阵名单/test.full 新基线切片/旧路径 grep 清零),单 commit 交付,随本专题入库。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|

| S0 | 前置快照与各 clone WIP 核验 | Done |
| S1 | 根瘦身批(assets/minimal/sim+qb_capture/hatch_build/env.sh/config/.dockerignore) | Open |
| S2 | 测试树批(tests/unit + tests/e2e + tests/real) | Open |
| S3 | pytest.ini 并入 pyproject | Open |
| S4 | 回写批(AGENTS/README/conventions/pitfalls) | Open |
| S5 | 终验收尾(守阵/test.full 基线切片/grep 清零) | Open |

## 进度日志

### R0 · 立档 (2026-11-26)

立项轮:全库引用面盘点 + grilling 一轮九问拍板(D1–D11,R1 扩围 qb_capture 三件)+ 计划 26-11-26-0503 入库 Open + 本档案立档 + wrap 切片;零代码改动,落盘件随本专题入库。

- 2026-11-26 05:21 立项轮: 全库引用面盘点 + grilling 九问拍板(D1-D11, R1 扩围 qb_capture 三件) + 计划 26-11-26-0503 入库 Open + 档案立档; 零代码改动
- 2026-11-26 22:06 S0 前置落档: collect-only 基线 7042 tests collected; 仓库根锚实测 83 处(69 文件, 比计划写的 64 多 19, 留 S2a 处理, 本批不管); tracked 数 tests 366 / e2e 90 / tests-real 65 / assets 17 / tools 34 / scripts 31 / resources 64; 冻结清单要点: 活口径最密集 tests-real/e2e/pytest.ini/scripts/sim_/qb_capture, 纯冻结豁免组 env.sh(全库无活口径引用)
