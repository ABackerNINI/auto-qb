# 26-11-12-test-linux-testbed — Linux 测试端 Docker testbed 改造实施

**Status:** In Progress
**Added:** 2026-11-12
**Updated:** 2026-11-13
**Summary:** Linux 测试端(pytest/e2e/变异)统一迁 Docker 常驻容器 testbed: S1–S6 落盘, Windows 全量绿(基线切片见 Refs); 实测数字单点=本档案「S1–S5 实测」节
**Topics:** test-linux-testbed
**Refs:** memory-bank/plans/26-11-12-0152-plan-linux-testbed-docker.html, memory-bank/issues/26-11-12-0053-chore-linux-ci-timeout-py-download.html, memory-bank/testing/baselines/26-11-13-0122-linux-testbed-docker.md

## 本篇只回答

Linux 测试端 Docker testbed 改造(计划 [26-11-12-0152-plan-linux-testbed-docker](../plans/26-11-12-0152-plan-linux-testbed-docker.html))实施到哪了: S1–S6 分期进度、每步实测数字与验收落点。方案本身看计划, 不在本篇复述。**本档案是 S1–S5 容器实测数字的单点**(mutants/test.linux-e2e 等 config note 的「数字单点=任务档案」都指这里); Windows 侧 test.full 基线数字不在此, 见 `commands run kb.baseline` 最新切片(T6b 建)。

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
| S1 | 镜像与容器基建: Dockerfile + test.linux-env task + 构建实测 | Done |
| S2 | test.linux 后端切换 docker exec + timeout 分层 + 守阵重写 | Done |
| S3 | test.linux-e2e(fast 子集)+ node_modules 接挂实测定型 | Done |
| S4 | mutants 包后端迁 docker + 8 条硬约束容器重验 + skill/坑档改写 | Done |
| S5 | 残留清扫: WSL(auto-qb-mut* 7 仓 + uv 缓存)+ docker 面(白名单) | Done |
| S6 | 回写收尾: 坑档改写+计划/issue 收口+档案落数(已落); 基线切片+test.full+kb.index+提交归 T6b | In Progress |

## S1–S5 实测(数字单点=本节; 2026-11-12 容器实测)

- **S1 基建**: Dockerfile 六层烘焙(`.commands/test/docker/Dockerfile`); 首建约 161s / 镜像 2.95GB / 幂等复跑 0.5s no-op; tag=`auto-qb-testbed:<uv.lock sha256 前 8>`。**各源实测钉值单点在 Dockerfile 头注**(Docker Hub 候选链 / apt / PyPI / npm+playwright / NodeSource / github CPython 六面), 本档不抄。
- **S2 pytest 主线**(docker exec 形态, 引擎 1800s + 容器内 1500s 分层):
  - 3.13 solo `6043 passed / 19 skipped`(pytest 126.64s, 端到端 140s); 3.12 solo `6044 passed / 19 skipped`(158.44s / 172s); 双会话并行各 `6046 passed / 19 skipped` 全绿互不影响(~208s); 内存峰值 solo 2.2GiB / 双开 5.60GiB(<10G, R5 不触发)。
  - 覆盖率闸: 非 Windows 闸=conftest 常量 `COVERAGE_FLOOR_OTHER=99.0`, 容器实测 99.08–99.09% 过闸。
  - **5 处 Linux 平台差异修复**: ① install_wrapper.py POSIX fallback python 不存在 rc 127→`command -v` 探测缺则 exec python3; ② test_tmp_bootstrap.py Windows 盘符字面量 POSIX 相对解析误撞 BOOTSTRAP_MARK→按平台取真绝对路径; ③ test_release_pipeline.py bump-my-version PATH 假绿→shutil.which stub; ④ utils_parse.py is_loopback_host IPv4-mapped IPv6 在 3.12/3.13 行为分裂→显式解包后判(根因修复); ⑤ testbed 性能档(perf_baseline.json 加 testbed_threshold + test_modules_p5.py AUTO_QB_TESTBED 分支, linux_ci.py 导出 env)。
- **S3 e2e**(**数字不进基线, 锚 Windows 侧**; 容器 swiftshader 软件渲染, 单用例比 Windows 慢一个量级): node_modules 接挂定案 **symlink**(ln -s /opt/e2e-node/node_modules 0.002s vs per-workdir npm ci 冷 0.820s/热 0.469s; symlink 零外呼不新增 D8 网络依赖面; 接挂失败 rc 26); @fast 344 例 342 绿/2 败 41.7m; --full 512 例 490 绿/4 败/18 skip 59.2m(3551s); **4 个计时敏感差异**(traffic-source-switch 的 route.fetch 在测试结束后才 resolve 的 spec 层竞态 ×2 + settings-bt-backup「探测 ambiguous」双皮肤 ×2), Windows/CI 恒绿 —— 用户拍板收下, 修法方向(spec 层加固/计时探测加档)记 test.linux-e2e note 走正式认领另开任务。
- **S4 变异迁移**: mutants.* 六条后端 wsl.exe→docker exec(同一容器, mirrors 落 /root/auto-qb-tests/mutation/<pkg>); setup 首建 22.0s(clone 13.5s + cp 模板 venv 0.4s + export/pip delta ~0.1s + mutmut 首装 ~7s), 镜像仓 setup 后 ≈280M/跑一轮后 ≈378M; 冒烟 versioning.py 155 变异/147 杀/7 survived/1 timeout, 变异段 6.96 变异/s(≈22s), 整轮 65.6s; report 8 条带 diff 1.2s; **8 条硬约束容器重验 8/8**(wsl --shutdown→docker restart; /mnt 禁令→overlayfs 天然满足; 8 核/12G 与 --max-children 纪律沿用); mutation-testing skill 与坑档(mutants-wsl-shell/mutants-shared-mirror)随 S4 提交改写。
- **S5 残留清扫(白名单, PT 容器无损)**: WSL 释放 ~2.0GB(auto-qb-mut* 7 仓 1655M + ~/.cache/uv 258M); docker 面卷 auto-qb-uv-cache 48.12MB + 悬空镜像层 402.1MB + 构建缓存(builder prune)2.342GB + 容器内测试残留 4.81GB; 合计 ~9.6GB; `docker ps -a` 无新增孤儿。
- **Windows 侧对照**: test.pkg 全绿(`452 passed` @S2 下半 / `467 passed` @S3 时点); Windows 全量基线数字不在此, 见 kb.baseline(T6b 切片)。

## 进度日志

### R0 · 立档 (2026-11-12)

认领 issue 26-11-12-0053(状态 Open → In Progress); 两轮 grilling 完成并全量拍板; 计划 26-11-12-0152 落盘(单文件 HTML, topic linux-testbed-docker); 本档案立档并与计划双向补链。实施未开始, S1–S6 全 Open。

### R1 · S1–S4 实施 (2026-11-12)

- 2026-11-12 S1–S4 全部实施完成, 共 8 笔提交: S1 基建(39fdaeb8 + c545883c)/ S2 后端重写 + 容器全量(b9e70cfc + 4780168b)/ S3 e2e(60ea780e)/ S4 变异迁移(5b405bbd + a00c8ef7); 各批评审轮次与实测数字见提交信息与本档案「S1–S5 实测」节; 计划 §04 各步验收判据逐项满足(5 处平台差异修复与 4 个计时敏感差异的裁决见上)。

### R2 · S5 清扫 + S6 回写半 (2026-11-13)

- 2026-11-13 00:41 S5 清扫执行完毕(数字见「S1–S5 实测」节, 无代码产物); S6 回写半落盘: 坑档 `pitfalls/testing/attachments/patching-local-linux-repro.md`「Docker 等价复现」节改写为 testbed 常驻容器配方(WSL/docker run 留痕降级为历史)→ AGENTS.md 命令注记补 linux 三面(test.linux-env/test.linux/test.linux-e2e + mutants.* 容器化)→ 计划 26-11-12-0152 转 Done(变更记录 R7; §04 S2 覆盖率闸口径钉准: 闸=conftest COVERAGE_FLOOR_OTHER=99.0 常量单点, 98.5 为 2026-11-05 提升第三轮前旧值)→ issue 26-11-12-0053 补复验与实际修法后转 Done → `.commands/test/config.toml` test.linux-e2e note 数字单点指针改指本档案(对齐 mutants 双锚写法)。基线切片 + test.full 全量 + kb.index + 最终提交归 T6b。

- 2026-11-13 01:24 S6 测试+基线半: 补回 S4 坑档历史条目判别字段(条目三字段守卫拦下的回归)后 test.full 全量绿(见 kb.baseline), 基线切片入库并双向补链, kb.index 重建; 提交归主会话
