# 26-11-19-webui-kbd-scroll-band-shard-flake-rescroll — kbd-scroll-band shard 偶红归因与修复: 补正循环每帧幂等重发 rescroll

**Status:** Done
**Added:** 2026-11-19
**Updated:** 2026-11-19
**Summary:** kbd-scroll-band shard 偶红归因与修复: 补正循环每帧幂等重发 rescroll
**Topics:** webui-kbd-scroll-band-shard-flake-rescroll
**Refs:** memory-bank/issues/26-11-18-0308-test-e2e-kbd-scroll-band-shard-flake.html

## 本篇只回答

issue 26-11-18-0308(kbd-scroll-band atlas「Home/End 到首末行」shard 并发偶红)的归因过程与最终修法: flake 怎么被采样捕获、根因链怎么用 vm 现场数字钉死、为什么「等待面加窗」无效、补正循环每帧幂等重发 + 代际令牌 + 用户退避这套修法的构成与验证数字。机制细节沉淀在 pitfalls/web-ui/kb-scroll-reveal-clamp-deadlock.md, 本篇是过程档案。

## 原始请求

1. 用户: 「修复 memory-bank/issues/26-11-18-0308-test-e2e-kbd-scroll-band-shard-flake.html」—— 对该 issue 记录的 shard 形态偶红完成修复(issue 当时 W3 采样 81 例 0 复现挂起待自然复现, 修法候选留档未实施)。

## 思考过程与决策

- **先采样, 不先修**: issue 的 W3 轮 0 复现、无现场数字, 按台账纪律「retry 不是修复、无现场不猜」。直接以同形态(shard=3 全并发 + grep 钉该例 repeat-each=60)采样, 本轮即捕获: 修复前两轮合计 240 例 39 红(15/120 + 24/120)。
- **A/B 排除自身诱因**: 第一轮修法(deadline 1s→5s)落地后红率不降反看齐, 回退 1s 的 A/B 轮红率同量级(24/120 vs 15/120) ⇒ ①红与窗宽无关(不是等待窗不足); ②我的改动不是诱因(既有 flake 被当场捕获)。这是「产品面放宽 deadline」改道为「补正循环主动推进」的关键证据。
- **vm 现场取证钉死根因**: pollBand catch 里临时注入 vm 快照(kbCursor/前缀和/渲染窗/scrollY), 三失败现场数字一致: kbCursor 正确指向首行 + pre=301 完好 + kbInDom=false + scrollY 钳残位 + 切片停尾部 ⇒ scrollTo 被窗口化重渲中途的文档高度塌缩吞掉(钳到底部残位), 目标行永不进 DOM, 旧补正「只等 DOM」干等到死。候选 2(测试面加窗)被机制性排除。
- **修法构成**: rescroll 每帧幂等重发(主修) + 代际令牌(评审 major: 重入末键胜) + 用户滚轮/触摸退避(评审 minor: 不劫持手动滚动) + 测试面 pollBand 10s(双窗一致, 配套)。评审 nit(window 级监听冒泡误置位, 可自愈)按「nit 不阻塞」接受现状留痕, 不改码。
- **决策单点**: 修法细节与机制沉淀单点在 pitfalls/web-ui/kb-scroll-reveal-clamp-deadlock.md; issue 正文承载取证与验证数字; 本篇只记过程。

## 实现计划

1. 采样捕获: dev.e2e-fast-shard ×3 shard 全并发 + `--grep "Home / End" --repeat-each=60`, 确认稳定复现率。(Done 2026-11-19)
2. vm 现场取证: pollBand catch 注入 diag(临时代码), 跑到红取现场数字, 钉死「钳位残位 + 补正只等 DOM」机制链。(Done 2026-11-19)
3. 产品面修复: `shortcuts_engine.js` `_kbScrollRowIntoView` 窗口化分支滚动封 rescroll + 补正循环每帧重发; deadline 5s。(Done 2026-11-19)
4. 修复验证: 同形态 180/180 全绿 + 全 spec 6/6 + 守阵 46P。(Done 2026-11-19)
5. 评审循环: 首轮 2 发现(major 代际令牌 / minor 用户退避)当场修 → 复评零 actionable(1 nit 留痕)。(Done 2026-11-19)
6. 测试面配套: pollBand 5s→10s + 注释; 删诊断代码。(Done 2026-11-19)
7. 回写: issue 翻 Done(正文补根因/修法/验证) + flaky-ledger 翻 Done + pitfalls 新档 + kb.index。(Done 2026-11-19)

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 同形态采样捕获(240 例 39 红, A/B 两轮排除窗宽与自身诱因) | Done(2026-11-19) |
| 2 | vm 现场取证钉死根因(三现场数字一致: 钳位残位+只等 DOM) | Done(2026-11-19) |
| 3 | 产品面 rescroll 每帧幂等重发 + deadline 5s | Done(2026-11-19) |
| 4 | 修复验证 180/180 绿 + 全 spec 6/6 + 守阵 46P | Done(2026-11-19) |
| 5 | 评审循环: 2 发现当场修(令牌+退避), 复评零 actionable | Done(2026-11-19) |
| 6 | 测试面 pollBand 10s 双窗一致 + 删诊断代码 | Done(2026-11-19) |
| 7 | 回写(issue Done / ledger Done / pitfalls 新档 / kb.index) | Done(2026-11-19) |

## 进度日志

### R0 · 立档 (2026-11-19)

- 用户指派修复 issue 26-11-18-0308。完成: 采样捕获(39 红/240) → vm 现场归因(钳位残位卡死, 补正只等 DOM) → 产品面 rescroll 每帧幂等重发 + 代际令牌 + 用户退避, 测试面 pollBand 10s → 修复后同形态 180/180 全绿、全 spec 6/6、守阵 46P; 评审两轮(首轮 major/minor 各 1 当场修, 复评 1 nit 留痕零 actionable)。回写齐(issue/ledger/pitfalls/kb.index)。坑档: pitfalls/web-ui/kb-scroll-reveal-clamp-deadlock.md。

- 2026-11-19 23:47 1-7 全部 Done: 采样捕获(240 例 39 红)→vm 现场归因(钳位残位+补正只等 DOM)→产品面 rescroll 每帧重发+代际令牌+用户退避+deadline 5s→180/180 验证绿→评审 2 轮(2 修 1 nit 留痕)→回写齐(issue Done/ledger Done/pitfalls 新档/kb.index)→test.full 6486P/6S 99% 基线切片 26-11-19-2346
