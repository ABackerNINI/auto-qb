# 26-11-21-test-review-real-baselines-exclusion — review 记账排除面增补 real-baselines 前缀

**Status:** Done
**Added:** 2026-11-21
**Updated:** 2026-11-21
**Summary:** 认领修复 issue 26-11-21-0639 收口: 排除面四处落地(正本/抄本/文档串/测试) + 漂移指针与坑档补记(用户追授权) + 评审零 actionable + 全绿(见 kb.baseline), issue 与本档案均 Done
**Topics:** test-review-real-baselines-exclusion
**Refs:** memory-bank/issues/26-11-21-0639-bug-review-bookkeeping-miss-real-baselines.html

## 本篇只回答

review 记账排除面如何把真机切片 `memory-bank/testing/real-baselines/` 机械排除出评审面(issue 26-11-21-0639 的修法、验证与契约面同步); 不回答评审分档口径本身。

## 原始请求

1. 修复 `memory-bank/issues/26-11-21-0639-bug-review-bookkeeping-miss-real-baselines.html`(排除面缺 real-baselines/ 前缀, 真机切片被计评审行)。
2. 「漂移和坑档一并更新」—— commit.py 抄本注释的陈旧指针 + 坑档 `review-trace-booking-sensitive-deadlock.md` 的排除面清单一并同步。
3. 「提交」。

## 思考过程与决策

- **照 issue §06 建议修法执行, 未改道**: `BOOKKEEPING_PREFIXES` 增一行 `"memory-bank/testing/real-baselines/"`。关键契约: 该清单有**两处**(正本 `review_content.py` + `commit.py` 同源抄本, 26-11-07-0826 基线 D3/0201 R2「改一处要改两处」), 两处同步增补。
- **坑档不改写历史快照**: 旧机制节是 2026-11-08 取证态, `activeContext/` 经 `git show b8895a77` 实核是**当时代码原串**(后才改 `active-context/`) —— 现状以「现口径」节后新增**补记段**承载(时间取 kb.time), 快照原样保留。
- **抄本指针陈旧一并修正**: `commit.py` 注释写「同源抄自 check_review_trace.py」, 但判据 2026-11 起收编进 `review_content.py` 单点 —— 指向随迁改准; `SENSITIVE_PATH_MARKERS` 双抄先例(review_pack.py + check_review_trace.py)经核实仍在, 该句保留。
- **测试同步面**: `test_review_pkg.py` 的 `test_generated_and_bookkeeping_are_not_counted` 加真机切片排除断言 + 头部「测试计划」清单同步(守卫要求); `check_review_trace.py` 计数面文档字符串同步。

## 实现计划

总体思路(单批小改, 无分步计划文档): 排除面清单增补一行 → 契约面四处同步(正本/抄本/文档字符串/测试) → issue 与坑档回写 → 包测试 + 直驱复核 → 分批评审 → 全量基线切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S1 | 正本 review_content.py + 抄本 commit.py 增补前缀与注释 | Done(2026-11-21) |
| S2 | check_review_trace.py 文档字符串 + test_review_pkg.py 断言与测试计划同步 | Done(2026-11-21) |
| S3 | issue 复验/修复后补充回填 + 翻 Done(kb.status) | Done(2026-11-21) |
| S4 | commit.py 指针注释修正 + 坑档补记段(用户追授权「漂移和坑档一并更新」) | Done(2026-11-21) |
| S5 | 分批评审 2 轮零 actionable(轮1 33 行零发现; 轮2 35 行, 增量=issue doc-refs 补链两行), 检 0/0 累计, 复核过 | Done(2026-11-21) |

## 进度日志

### R0 · 立档与修复落地 (2026-11-21)

- 复验锚点仍复现(两处清单均无 real-baselines 前缀; real-baselines/ 实存 44 份切片); 修复四处落地, `commands run test.pkg` 全绿(562 passed / 36 subtests), 直驱复核: 正本==抄本、真机切片不计行、issues 记录件与真实代码照旧计行。
- 用户追授权后补齐: commit.py 指针注释修正 + 坑档补记段; `commands run kb.index` 重建 33 生成物零 diff。
- 分批评审: pack 前置(探针远端态 → sync 齐平 → ship.gate 全绿) → pack 33 行全能档 → 只读子代理评审**零发现**(检 0/0) → 收尾复核 HEAD/远端均未动; 提交闸门实算 35 行揭出 doc-refs 补链增量 → 修复轮 pack(基 e88152d6ecad)增量复评仍零发现, 检 0/0 累计, 出口达成。
- 全量基线数字见 kb.baseline; 真机轨判定: 纯工具链机械面(评审计数排除面), 不涉「qB 真执行才成立」与「必须碰真文件系统·进程·注册表」两类准入, 免真机。

- 2026-11-21 10:05 认领修复 issue 0639: BOOKKEEPING_PREFIXES 增 real-baselines/ 前缀(review_content 正本+commit.py 抄本两处契约)+check_review_trace 文档串+测试断言; 漂移(commit.py 指针注释)与坑档(现口径补记段)经用户追授权一并更新; 评审 33 行全能档零发现 检 0/0; test.pkg 562P/36S 绿; 纯工具链免真机轨; 全绿见 kb.baseline
