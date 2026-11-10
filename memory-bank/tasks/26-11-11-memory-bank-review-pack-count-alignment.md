# 26-11-11-memory-bank-review-pack-count-alignment — review.pack 行数口径对齐闸门实算(审计 P1/P2/P3 修复)

**Status:** In Progress
**Added:** 2026-11-11
**Updated:** 2026-11-11
**Summary:** review.pack 行数口径对齐闸门实算(审计 P1/P2/P3 修复)
**Topics:** memory-bank-review-pack-count-alignment

## 本篇只回答

评审管线的 pack 统计面为什么与提交闸门行数实算曾经两套口径、审计怎么实测出分歧、修复怎么收编成单点(锚点/逐笔实算进 review_content, pack 消费), 以及评审派发 2 + 修复轮 1 的全过程与实测数字。

## 原始请求

1. 「查询一下git历史, 对比code review流程, 看看最新的code review流程有没有问题, 有没有值得优化的地方」—— 只读审计轮。
2. 「按建议修」—— 修复授权: P1(pack 统计面接入闸门实算口径)+ P2(二进制 0 行)+ P3(SKILL.md 条 14 漂移)+ 顺手项(TIER_LIMIT 注释依据)。
3. 「立档, 提交」—— 立档授权 + 提交触发词。

## 思考过程与决策

- **审计方法**: 读 SKILL.md 全文 + 9 笔演进提交 + 三个脚本(gate/pack/content)对照; 临时仓库实测复现分歧(pack 报 9 行 vs 闸门实算 1 行; 未跟踪 60k 行 blob 被 pack 报 60009 行推上分面档)。
- **根因定位**: b8895a77(1240 T1)抽共享过滤模块时只把**基哈希**接进了 review_content, pack 的 diff 统计/评审规模漏接 —— 树差 shortstat + 全量 untracked 的旧口径留下。
- **修复架构拍板**: 不做「pack 内本地过滤」的半修(多笔提交/合并拓扑下树差 ≠ 逐笔和, 分叉还在), 直接把 gate 的锚点与逐笔实算(anchor_commit/numstat_batch/_commit_numstat/_count_numstat/untracked_batch + Review trailer 正则)收编进 review_content.py, gate 与 pack 都消费 —— 延续 1240 的「哈希同源」架构先例, 排除面/锚点/实算/哈希四处一份实现。
- **输出形态拍板**: pack 只报「评审规模(闸门实算口径)」一个数, 删树差 shortstat 行 —— 两个数并排必然抄错一个; 红线/敏感面预警仍扫全量路径(预警不过滤); 文件清单过滤记账/生成物、单列排除面行(清单=reviewer 阅读面, 规模=trailer 申报面, 两个口径各自有主)。
- **拆批 vs 派发**: 525 行 > 400, 拆批需 stash 舞蹈(批A/批B 文件级分离)—— 提交管线口径「stash舞蹈自提交路径退役」, 且共享模块+消费方+测试+文档是原子改造 → 走「确实不可拆残余批」: 派发 2 全量评审。
- **审计附带的文档漂移**: SKILL.md ⑥ 条 14「提交闸门未覆盖源码符号」写于 11-08 16:46, 同日 22:18 符号守卫落地(c63f1ff5)进 test.quick —— 同日漂移, 恰是条 17 说的那类事实错误。

## 实现计划

1. review_content.py: 收编 gate 的锚点与逐笔实算(REVIEW_LINE_RE/SKIP_LINE_RE/anchor_commit/_count_numstat/numstat_batch/_commit_numstat/untracked_batch), 模块头与节注释写明「实算面环境原样、哈希面才隔离」与 excludesFile 例外。
2. check_review_trace.py: 删本地副本改 import 消费, docstring 计数面指向单点。
3. review_pack.py: cmd_pack 重写 —— 评审规模走 numstat_batch+untracked_batch(闸门同源), 二进制 0 行, 文件清单过滤+排除面行, --base≠锚点 [warn], TIER_LIMIT 注释换产出密度实验依据。
4. test_review_pkg.py: 改 1 个被钉断言(0 行金值)+ 新增 7 条回归(15 行金值、逐笔≠树差 7/6、记账排除面、二进制 0 行、锚点警告、excludesFile 不改写未跟踪集合、unborn HEAD 容忍)+ 同步测试计划 docstring。
5. SKILL.md: ③ 机械五件新口径 + ⑥ 条 14 括号注。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 临时仓库实测复现 P1/P2 分歧 | Done(2026-11-11) |
| 2 | review_content 收编锚点+逐笔实算单点 | Done(2026-11-11) |
| 3 | gate 改消费共享实现 | Done(2026-11-11) |
| 4 | pack 统计面对齐 + 二进制 0 行 + 锚点警告 | Done(2026-11-11) |
| 5 | 测试金值更新 + 7 条回归 + 测试计划同步 | Done(2026-11-11) |
| 6 | SKILL.md ③/⑥-14 更新 | Done(2026-11-11) |
| 7 | 评审: 派发 2(首轮 10 条送检/9 过检/1 REFUTE, 全修)+ 复评轮 1(零 actionable) | Done(2026-11-11) |
| 8 | 收尾: 切片/立档/回写/test.full/基线/提交 | Done(2026-11-11) |

## 进度日志

### R0 · 立档 (2026-11-11)

- 审计轮实测: 同一工作树 pack 报 9 行、闸门实算 1 行(记账类 tasks/t1.md + active-context/s2.md 虚增); 未跟踪 60k 行 blob 被 pack 报 60009 行推上「分面」档(闸门计 0)。
- 修复主体落地: 5 文件 +342/-183; 冒烟对齐(pack 1 行=闸门 1 行; 真仓 pack 525 行=闸门 525 行)。
- 首轮评审(派发 2, 串行): 10 条送检、9 过检(1 major/4 minor/4 nit)、1 REFUTE(行号偏移 7 行弃, 注释数字失真本身属实按自发顺手修); 7 个独立问题全修: F1(major) anchor_commit unborn HEAD 容忍回归 + 用例、F2(minor) pack 展示面 excludesFile 同钉 + 用例、F3(minor) 三新用例补 git 身份、F4-F7 nit(节注释例外段/remerge 静默 quiet/commit.py 交叉引用/excludesFile 用例合并 F2)。
- 修复轮评审(轮 2): 逐条实测核验 9 条在位, 本轮零 actionable —— 出口达成。
- 坑档对账: P1 实为已记录坑 `pitfalls/kb/review-pack-count-vs-gate-count.md`(复发 +3 在案)—— 审计轮 grep 用词「评审规模/分档」不命中坑档的「diff 统计」, 收尾回写才撞见; 已按协议复发 +1 + 坑档补根治段(绕行流程作废, trailer 行数照 pack「评审规模」抄)。教训记入坑档复发行。
- 实测: test.pkg 与 test.quick 全绿(见 kb.baseline); test.full 数字见基线切片。
