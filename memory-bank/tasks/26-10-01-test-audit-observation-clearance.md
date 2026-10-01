# 26-10-01-test-audit-observation-clearance — 内核化重构审计观察项 L4-L9 清偿 (四阶段)

**Status:** Done
**Added:** 2026-10-01
**Updated:** 2026-10-01 21:39
**Summary:** 审计报告 (reports/26-10-01-0918) 低严重度观察项 L4-L9 清偿, 四阶段各一笔提交: P1 (7e48e122) L4+L5 两处守阵 docstring 漂移修正 + 两处子串守阵升级 AST; P2 (036a3617) L6+L7 跨包私有名公开化 (bump_recheck_fail / recheck_fail_count / new_client), 43 处引用 15 文件纯改名; P3 (35d31469) L8 "6 条 warnings" 定性为 starlette TestClient cookies= 弃用 ×6 逐请求触发, 根修 tests/test_web.py 后 0 warnings; P4 (本笔) L9 计时断言从「只拦灾难」(1s/30s) 基线化为回归阈值 (短路 0.1ms / 重建 4.0ms, median-of-5 口径, 基线 tests/fixtures/perf_baseline.json)。终态 test.full 1916 passed + 3 skipped / 91% / 0 warnings。
**Topics:** test-audit-observation-clearance

> 关联件 (散文指针, 未声明机器认领链): 审计报告 memory-bank/reports/26-10-01-0918-report-kernel-module-refactor-audit.html; 终态基线切片 memory-bank/testing/baselines/26-10-01-2125-test-l9-perf-baseline.md。

> 背景关联 (不进机器认领链): 审计跟进闭环的收尾段。M1/M2 见 [tasks/26-10-01-backend-eventbus-suppress-request-bit.md](26-10-01-backend-eventbus-suppress-request-bit.md), M3 见 [conventions/modules.md](../conventions/modules.md)「订阅者异常约定」, L1-L3 见 activeContext 切片 26-10-01-0918 的历史纪要。

## 原始请求

用户要求清偿内核化重构审计报告 (memory-bank/reports/26-10-01-0918-report-kernel-module-refactor-audit.html) 低严重度观察项 L4-L9, 分四阶段实施、每阶段一笔提交 (用户预授权每阶段完成后单独提交): L4/L5 守阵 docstring 漂移与子串守阵弱判定, L6/L7 跨包私有名公开化, L8 warnings 清零, L9 把 5000 种子守阵「只拦灾难」的计时断言升级为有数据依据的回归阈值 (不引入 flaky、不过度工程、不碰 src/ 生产代码)。

## 思考过程与决策

- **Phase 1 (L4+L5, 7e48e122)**: 两处 docstring 漂移修正 (test_facade_modules 补漏条 / test_modules_p4 失配函数名 + 过时承诺重写); 两处子串守阵升级 AST —— test_core_modules 私有面清零 / test_facade_modules run() 接线。注入自验: 注释误红消除、真违规全红带行号。当时 test.full 1909+3 / 91% / 25.4s。
- **Phase 2 (L6+L7, 036a3617)**: `bump_recheck_fail` / `recheck_fail_count` (checking_meta) 与 `new_client` (qbclient) 公开化, 43 处引用 15 文件 (src 13 / tests 23 / 现役文档 7) 一次改净零残留, 纯改名零行为变更。当时 test.full 1912+3 / 91% / 24.6s。
- **Phase 3 (L8, 35d31469)**: "6 条 warnings" 定性为同一条 starlette TestClient `cookies=` 弃用 ×6 逐请求触发 (b 类, 测试代码自身), 根修 tests/test_web.py (cookies 改设 client 实例), 未新增 filterwarnings。处置后 0 warnings。当时 test.full 1914+3 / 0 warnings / 91%。
- **Phase 4 (L9, 本笔)**: 审计原文指出 1s/30s 断言只拦灾难性退化且「数字入档」靠人工无强制。设计: ①实测采样 —— coverage 插桩 (与 pytest-cov 断言环境同源, 插桩使重建约慢 2x) 下 2 进程 × 10 轮 (每进程第 1 轮冷), n=20/操作; 短路 min 0.01 / 中位 0.01 / max 0.03ms, 重建 min 0.74 / 中位 0.85 / max 1.48ms; 裸跑 10 样对照 (重建中位 0.43ms)。②基线落点 `tests/fixtures/perf_baseline.json` (实测分布 / 采样口径 / 机器 / commit f3564847 / 采样日期), 机器可读纯 stdlib。③阈值 = 实测中位 × 安全系数: 短路 0.1ms (中位 ×5, 向上取整到 0.1ms 整刻度 —— 亚毫秒量级下计时粒度与调度抖动绝对量主导), 重建 4.0ms (中位 ×~4.7, 3-5x 带内, 2.7x 于 20 样最大值); 均远紧于旧灾难线 (紧 4 个数量级), 旧 1s/30s 保留为第二道兜底 (数字也收进基线文件, 断言运行时读入, 无手抄副本)。④防 flaky 靠测试内 median-of-5 计时口径 (单次调度/GC 毛刺被中位吸收, 持续劣化才触发) 而非放大系数; 短路/重建均幂等 (纯比较 / 全新队列 + reset), 重复计时无状态漂移。⑤重采样流程零脚本: 测试把中位数 print 在 capsys.readouterr() 之后, `uv run pytest tests/test_modules_p5.py -k rebuild_benchmark -q -rP -n 0` 连跑 ≥6 次从 PASSES 段抓 `[5000-seed benchmark]` 行 (capsys 吞常规输出、-rP 浮出摘要 —— 已注入临时测试实证), 流程步骤写进测试 docstring。
- **范围外发现 (只报告未修)**: ① `test_ops_service_direct_call_and_inflight_mutex` 函数级 docstring 微漂移 (声称测 skip_check 直调实未触达) —— **已于本日 21:39 由用户指令单独清偿**: 按漂移定性收窄 docstring 为仅 recheck 直调 (skip_check 直调 web 源已由 test_ops.py 覆盖, 不重复补测), tests/test_modules_p4.py 8 passed; ② 本 clone 残留 `src/auto_qb/web` 与 `src/auto_qb/web/routes` 两个只剩 __pycache__ 的迁移残壳 (09-22 web→webui 迁移遗留, gitignored 未跟踪), 触红并行新落的幽灵包守阵 (2101976a), 按守阵 prescribed 整目录删除 —— 环境清理非代码改动, 其它 clone 留有同款残壳会同样标红; 已立新坑 [pitfalls/testing/ghost-pkg-residue.md](../pitfalls/testing/ghost-pkg-residue.md) (此前无同类条目); ③ 排障探针翻出的 anyio BlockingPortal 弃用警告已在 pytest.ini 既有过滤中处置, 非新问题。

## 实现计划

- Phase 1-3 已入库 (7e48e122 / 036a3617 / 35d31469, 各自独立提交, 明细见进度日志)。
- Phase 4: 精读 test_modules_p5.py 守阵 → 采样 (临时脚本放系统 TEMP 不入库, coverage 插桩口径) → 落 perf_baseline.json → 改守阵 (median-of-5 + 基线阈值 + 兜底灾难线 + docstring 设计理由与重采样流程) → `commands run test.quick` 连跑 3 次确认稳定 → test.full 取终态数字。
- 收尾回写与 L9 同笔提交: activeContext 切片滚动 / 本档案立档 + kb.index / 基线切片 / pitfalls 新条目 / progress 沉淀。

## 子任务状态表

| 子任务 | 状态 | 备注 |
|---|---|---|
| Phase 1 L4+L5 | ✅ 完成 | 7e48e122 已推 Gitee develop |
| Phase 2 L6+L7 | ✅ 完成 | 036a3617 已推 Gitee develop |
| Phase 3 L8 | ✅ 完成 | 35d31469 已推 Gitee develop, warnings 6→0 |
| Phase 4 L9 采样 + 基线 + 改守阵 | ✅ 完成 | n=20/操作; 阈值 0.1ms/4.0ms; perf_baseline.json |
| Phase 4 稳定性验证 | ✅ 完成 | test.quick ×3 全绿 (1916+3, ~21.8s); test.full 绿 |
| 收尾回写 (切片/立档/基线/pitfalls/progress) | ✅ 完成 | 与 L9 同笔提交; 基线切片 26-10-01-2125 |

## 进度日志

- **2026-10-01 Phase 1-3**: 依审计报告四阶段清偿 L4-L8, 每阶段一笔提交 (7e48e122 → 036a3617 → 35d31469), 均已推 Gitee develop; test.full 演进 1909+3 → 1912+3 → 1914+3 (0 warnings), 覆盖率恒 91%。
- **2026-10-01 Phase 4 (本笔)**: 同步至 f3564847 后实施 L9: 插桩采样 n=20/操作 + 裸跑对照; 阈值短路 0.1ms / 重建 4.0ms (median-of-5 口径), 旧 1s/30s 留作兜底; test.quick 连跑 3 次全绿确认不 flaky; 终态 **test.full 1916 passed + 3 skipped / 91% (13278 语句 / 1030 未覆盖 / 4410 分支 / 435 partial) / 24.8s / 0 warnings** (+2 与 L9 无关, 来自 9f73b6d8 托盘守阵), 基线切片 [26-10-01-2125](../testing/baselines/26-10-01-2125-test-l9-perf-baseline.md)。范围外发现三条只报告 (见思考过程), 其 ② 立坑 pitfalls/testing/ghost-pkg-residue.md。收尾回写 (切片滚动 / 本档案 / 基线切片 / progress 沉淀 / kb.index) 与 L9 同笔提交。
- **2026-10-01 21:39 范围外发现 ① 清偿**: 用户单独指令修复 ① docstring 微漂移 —— 同步至 9c9e966e 后, tests/test_modules_p4.py:175 docstring 收窄为「ctx.ops.recheck 直调可用(web 源)」; 不补测代码, 因 ctx.ops.skip_check 直调 (web 源) 已由 tests/test_ops.py:163 覆盖; 该文件 8 passed (4.55s)。② ③ 维持只报告。
