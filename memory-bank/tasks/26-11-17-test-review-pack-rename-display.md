# 26-11-17-test-review-pack-rename-display — review.pack 展示面对齐实算 rename 口径 + 改名对提示

**Status:** Done
**Added:** 2026-11-17
**Updated:** 2026-11-17
**Summary:** review.pack 展示面对齐实算 rename 口径 + 改名对提示
**Topics:** test-review-pack-rename-display

## 本篇只回答

pack 的评审规模在批内含大文件移动(rename)时为何会删+增双计、为什么这是实算面的刻意设计而非缺陷、以及 26-11-17 怎么只对齐展示面(文件清单钉 `--no-renames` + 「改名对」提示行)让双计规模当场可对账,消掉「2357 行被误判成脚本缺陷」这类误报通路。

## 原始请求

1. 另一会话报告: 评审包规模 2357 行远超预期(≈13 行实质改动)——疑似 rename 未被检测、HTML 移动被算成删+增全文,复验 code review 脚本是否有缺陷。
2. 继续排查时注意查原设计文档了解设计意图。
3. 追问: 不开 `--no-renames` 的话代价是什么。
4. 「好, 按处置建议做, 直接修」——采纳最小修法(展示面对齐),不动实算面。
5. 「提交」。

## 思考过程与决策

- 定位: 行数实算单点在 `review_content.py`,所有 numstat 调用恒钉 `--no-renames`(闸门与 pack 共用);引入提交 `0967985a` 的原始注释即设计意图: numstat 的 rename 合成串 `a/{b => c}/d` 不是真实路径、绕开记账/生成物排除面,改删+增「宁可多算不漏算」。
- 代价分析(用户追问 3): 开 rename 检测 = ① 100% 相似改名 numstat `0 0` → 0 行假绿漏算通路; ② 排除面被合成路径绕开; ③ 相似度阈值/renameLimit 是机器与版本变量 → trailer `<N> 行` 与分档跨 clone 漂; ④ 基哈希失去跨 clone 确定性(架构支柱); ⑤ inexact detection 性能。失效方向不对称: 双计只多派评审(钱), 开检测是假绿+不确定(制度失效) → 维持实算面原设计。
- 2357 指纹核实: 2357 = 13 实质行 + 2×1172,与「1172 行 HTML 被移动 + 13 行真改动」吻合(另一 clone 现场,本 clone 无该文件)。
- 真缺陷在展示面: `cmd_pack` 文件清单走 name-status 默认 rename 检测 → rename 折叠成一行只列新路径,旧路径不进清单也不进删除行 → 2357 行规模在清单里无处对账,直接引发误判。
- 拍板(用户确认): 展示面钉 `--no-renames` 与实算同口径 + 第二次 `git diff --name-status -M`(rename 检测)出「改名对」提示行(仅提示,两侧任一在可评面才显示,不进计行/清单/敏感面);红线/敏感面扫描随 D 旧路径进 `all_paths` 与闸门 `name-only --no-renames` 口径一致(旧代码漏检 rename 旧路径,反而是一致性收口)。

## 实现计划

总体思路: 只动展示面,实算面一字不改;描述面四处同步;测试翻转+新增;收尾按 DoD 全套(建档/基线/切片/坑档)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | review_pack 展示面 --no-renames + 改名对提示行 | Done(2026-11-17) |
| 2 | 测试: 翻转 rename 清单断言 + 新增提示行用例 + 删除专用行断言(评审 minor) | Done(2026-11-17) |
| 3 | 描述面同步: 模块 docstring / config.toml note / SKILL.md ③ / 测试计划 | Done(2026-11-17) |
| 4 | 评审两轮: 首轮 1 minor 修完,复评零 actionable | Done(2026-11-17) |

## 进度日志

### R0 · 立档 (2026-11-17)

review: pack 展示面 rename 对齐批(全能) · 42 行(收尾回写前) · blocker 0 · 修 1 · 入池 0 · 检 1/1 · 轮 2 · 基 9ac8f9a96fa0 · 派发 1 · 齐平 3840ba10 —— 首轮评审唯一发现(test 删除专用行缺断言)已修并过检,复评轮交回 [](零 actionable)。test.pkg 全绿(见 kb.baseline);ship.gate 预跑全绿。

- 2026-11-17 04:39 pack 展示面对齐实算 rename 口径 + 改名对提示; 守卫白名单收编 reports/ 存档特例 .md
