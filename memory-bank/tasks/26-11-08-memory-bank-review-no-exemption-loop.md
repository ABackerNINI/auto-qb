# 26-11-08-memory-bank-review-no-exemption-loop — 评审流程改造: 废除裁量豁免+修复增量强制复评+基哈希闸门

**Status:** In Progress
**Added:** 2026-11-08
**Updated:** 2026-11-08
**Summary:** 评审流程改造: 废除裁量豁免+修复增量强制复评+基哈希闸门
**Topics:** memory-bank-review-no-exemption-loop
**Refs:** memory-bank/plans/26-11-08-1240-plan-review-no-exemption-loop.html

## 本篇只回答

评审流程(分批评审 + 提交闸门)怎么从「50 行下限豁免 + 修复增量不复评」改成「可评必评 + 修复循环到零 actionable + 基哈希机械闸门」;方案与拍板单点在计划 `26-11-08-1240-plan-review-no-exemption-loop.html`(D1-D12)。

## 原始请求

1. 「当前的code review流程有些问题, 部分豁免审核的提交会导致后续同时工作的提交同时合并review, 初步想法是改为不设豁免, 提交前都要review一遍, 且对review后的二次增改也不设豁免, 每笔修改都当场review直到返回空[]. 一个计划的接缝还是要有review. grilling一个修改计划」
2. 三轮 grilling 均答「按推荐」;追加约束: 「要注意"全能档"阈值保留」。
3. 「写计划」——落成计划档。

## 思考过程与决策

- **归因澄清**(开工事实核查):用户观察到的「并发提交合并 review」= issue `26-11-08-0903`(平铺 log 锚点被侧分支 tip 遮蔽 + 树差虚增 9910 vs 272),commit `a9e1cbcf` 已修,与豁免无关——`Review-Skip` 同样推进锚点(`check_review_trace.py:277`)。真正未闭合的是两条政策缝:① <50 行不评;② 修复增量 ≤100 行不复评。
- **关键取舍**:字面「返回空 []」不可用(发现数 ≈ 派发次数 × 5.6 有 nit 底噪 → 不终止 + Goodhart 软化 reviewer 两个失效模式),出口改为**裁决后零 actionable**(refute 弃/计划外入池算闭合/blocker+major+minor 修完,nit 不阻塞留痕);复评载体因轮间无提交对象,从「对象级增量」修正为「整批过滤 diff + 指令层增量(只报新增 + 上一轮清单回退校验)」;执行强度加**基哈希机械闸门**(trailer `· 基` = 末轮 pack 过滤 diff 哈希,提交时重算比对)把「当场复评」变成 poka-yoke。
- **12 项拍板**(D1-D12,2026-11-08,grilling 3 轮):全部结论与日期见计划 §06;要点 = 只废裁量豁免留对象定义、新提交 `Review-Skip` 判红不追溯、可评 >0 必评、`dev.fmt` 算改动、trailer 加 `· 轮 R`/`· 基` 且计数全轮累计、接缝终审保留且处置拉齐、不加轻量档、**全能档 400 行阈值与拆批/分面保留**(D12,用户追加)。

## 实现计划

按计划 §04 分期执行,W1→W2→W3 串行(脚本口径先落地,文档跟脚本),W4 按 DoD 收尾:

- **W1 机械面**:`check_review_trace.py` 下限删除/`Review-Skip` 判红/`· 基` 哈希机检/轮与累计字段校验;`review.pack` 输出整批过滤 diff 哈希(与闸门共用过滤实现)。
- **W2 规则面**:`code-review/SKILL.md` 触发表/⑤修复循环/⑦trailer 语法/反模式重写;④分档表与⑧降级自查原样。
- **W3 测试面**:`test_review_pkg.py` skip 用例改判红 + 新增基哈希/轮字段/累计口径/0 行静默/历史锚点识别用例;头部「测试计划」同步。
- **W4 收尾**:DoD(切片/基线/pitfalls/回写)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|

| W1 | 机械面: check_review_trace.py + review.pack(下限删/判红/基哈希/累计) | Done(2026-11-08, T1=8cee7e11 + T2=84b8da8f) |
| W2 | 规则面: code-review SKILL.md 重写(触发表/⑤/⑦/反模式) | Done(2026-11-08, T34=960598ef; 接缝终审补 memory-bank SKILL.md 与 my-commit-flow 注册 note 两处副本) |
| W3 | 测试面: test_review_pkg.py 判红改写 + 新增用例 + 测试计划同步 | Done(2026-11-08, 定向 112; 基线切片归 W4) |
| W4 | 收尾 DoD: 切片/基线/pitfalls/回写 | Open |

## 进度日志

### R0 · 立档 (2026-11-08)

grilling 3 轮闭合设计树(12 项拍板,D1-D12)→ 计划档落成 `plans/26-11-08-1240-plan-review-no-exemption-loop.html`(10 SLOT 填毕,双链回指本档案)→ 本档案立档(阈值 #4:已产出计划文档)。W1-W4 未开工。

### R1 · 实施 (2026-11-08, 本地分支 review-no-exemption-loop, 全程 --no-push)

- **P0 计划档** e40f9566: 评审 1 轮 4 送检 4 过检 修 4(含派发 K 改回首轮拓扑口径, 计划 R1 同步)。
- **T1 机械面** 8cee7e11: review_content.py 共享单点(可评过滤+batch_base_hash, 双层配置隔离 13 颗钉+literal pathspec+--ignore-cr-at-eol)+ pack 基哈希输出; 评审 2 轮 7 送检 5 过检 修 5+1 自发(write_bytes); 4 钉变异自证全红。
- **T2 闸门规则** 84b8da8f: 下限退役/Review-Skip 判红/·基 必填现算比对/·轮 缺省 1/累计口径注释; 敏感面语义随下限退役修正为「强制评非必红」; 金值用例锁规范化(--unified=1 变异红); 评审 2 轮 4 送检 4 过检 修 4; **已知窗口如实声明: 0 行二进制改动基比对被短路**(用户批准入池: 26-11-08-1701)。
- **T34 规则文档+测试终扫** 960598ef: SKILL.md 全文新口径 + 测试计划 5 处漂移修正 + 3 缺口用例; 评审 2 轮 1 送检 1 过检 修 1(残余窗口口径补二进制窗)→ 复评空 [] 出口。
- **接缝终审**(4 送检 4 过检): 2 major 第三/四份旧口径副本(.my-commit-flow.toml 注册 note/memory-bank SKILL.md 第 0 步)+ 1 minor 档案 stale + 1 nit pack --base 措辞, 全修; 计划 R2 回写三处口径级偏差。
