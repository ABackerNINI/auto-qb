# 26-11-12-test-linux-testbed — Linux 测试端 Docker testbed 改造实施

**Status:** In Progress
**Added:** 2026-11-12
**Updated:** 2026-11-12
**Summary:** Linux 测试端 Docker testbed 改造实施
**Topics:** test-linux-testbed
**Refs:** memory-bank/plans/26-11-12-0152-plan-linux-testbed-docker.html

## 本篇只回答

Linux 测试端 Docker testbed 改造(计划 [26-11-12-0152-plan-linux-testbed-docker](../plans/26-11-12-0152-plan-linux-testbed-docker.html))实施到哪了: S1–S6 分期进度、每步实测数字与验收落点。方案本身看计划, 不在本篇复述。

## 原始请求

1. 认领 issue 26-11-12-0053(test.linux 包装超时 900s 不够 + 3.12 镜像 uv 补下载托管 CPython 走 github 不通), 准备彻底解决 linux 测试端问题。
2. 初步想法: 环境一次性完全搭好, 每次测试不用重新搭; 复制仅拷代码(注意 __pycache__ 等不要复制)。
3. linux 中有很多测试残留(后确认主体是变异测试镜像仓), 一并规划, 测试统一到一个目录(如 ~/auto-qb-tests/ 子目录), 不污染其它目录。
4. 多会话并行测试不相互影响。
5. 另一会话报告 docker ubuntu 中没有安装 node。
6. grilling 然后出一个计划; 拍板: 宿主改用 Docker(他机重建容易), WSL2 中的测试与变异测试残留清空。
7. 网络策略拍板(D8): 拉取镜像与依赖尽量用国内镜像站, github 尽量直连, 连不上让用户手动开代理。

## 思考过程与决策

- 两轮 grilling(Q1–Q8), 全部拍板, 结论 D1–D8 在计划 §06: 宿主 Docker 常驻容器(WSL2 让位)、e2e 进环境、双 venv 3.12+3.13、代码 tar 流推送(.git 随拷)、每会话独立 workdir 允许并行、变异体系迁入容器、WSL 残留清空、网络策略国内镜像站优先+github 直连+失败人工代理(D8, R1 改版)。
- 关键取舍: WSL2 vs Docker 的决定项是「环境即代码可移植重建」(用户口径)压过「变异体系零迁移」(WSL 现状优势); 变异迁移成本(8 条硬约束容器重验)已显式接受。
- 事实面 2026-11-12 实测: 仓库 478M 构成(pycache 82M/.git 99M/node_modules 21M/dist 26M); WSL Ubuntu-26.04 无 Linux node(现有 npm 是 Windows /mnt/h 泄漏假货); WSL 残留 7 个 mutmut 镜像仓 ~1.63G + ~/.cache/uv 258M; docker 孤卷 auto-qb-uv-cache 48M; 变异锚 §07 无进行中轮次(镜像仓可安全清)。

## 实现计划

按计划 §04 分期表执行: S1 镜像与容器基建(Dockerfile + test.linux-env)→ S2 test.linux 后端切换(docker exec 形态 + timeout 分层 + 守阵重写)→ S3 e2e(test.linux-e2e)→ S4 变异体系迁移(mutants 包后端 + 8 条硬约束重验)→ S5 残留清扫(WSL + docker 面, 白名单)→ S6 回写收尾(坑档/基线切片/issue Done/kb.index/test.full)。每步验收判据见计划 §04。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 镜像与容器基建: Dockerfile + test.linux-env task + 构建实测 | Open |
| S2 | test.linux 后端切换 docker exec + timeout 分层 + 守阵重写 | Open |
| S3 | test.linux-e2e(fast 子集)+ node_modules 接挂实测定型 | Open |
| S4 | mutants 包后端迁 docker + 8 条硬约束容器重验 + skill/坑档改写 | Open |
| S5 | 残留清扫: WSL(auto-qb-mut* 7 仓 + uv 缓存)+ docker 面(白名单) | Open |
| S6 | 回写收尾: patching.md 改写 + 基线切片 + issue Done + kb.index + test.full | Open |

## 进度日志

### R0 · 立档 (2026-11-12)

认领 issue 26-11-12-0053(状态 Open → In Progress); 两轮 grilling 完成并全量拍板; 计划 26-11-12-0152 落盘(单文件 HTML, topic linux-testbed-docker); 本档案立档并与计划双向补链。实施未开始, S1–S6 全 Open。
