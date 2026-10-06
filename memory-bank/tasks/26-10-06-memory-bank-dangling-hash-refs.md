# 26-10-06-memory-bank-dangling-hash-refs — KB 悬空提交 hash 清理

**Status:** Done
**Added:** 2026-10-06
**Updated:** 2026-10-06 20:09
**Summary:** 认领 issue 26-10-06-1904 并实施完成: 39 条悬空提交 hash(复验 38 + 批量检查漏报 1)按 commit message 考古映射到 develop 现存等价 commit / 重写事件转平文 / 孤儿去 hash 保留叙述, 026742a 查明为 apm.lock.yaml 技能包外部 pin(误报消源); 改动 20 份文件, 提取管线复扫悬空 0; 坑档 pitfalls/kb/commit-hash-refs.md 新立(batch-check 类型盲区)。

**Refs:** memory-bank/issues/26-10-06-1904-docs-kb-dangling-hash-refs.html
**Topics:** kb-dangling-hash-refs

## 原始请求

用户指派(2026-10-06 19:13): 「认领并修复:memory-bank/issues/26-10-06-1904-docs-kb-dangling-hash-refs.html」。issue 内容: memory-bank 的 backtick/code/commit 语境提交引用中 40 条 hash 在 feature 分支 rebase 并入 develop 后不可解析, 建议逐条按 message 考古映射, 无等价的去 hash 保留叙述。

## 思考过程与决策

- **复验先行**: 重跑提取管线(backtick md + `<code>` html + `commit <hash>` 语境, `git cat-file --batch-check` 过滤 missing), 371 个候选中 40 条悬空, 与 19:04 取证数量一致但构成有变:
  - 9e70b0bd / ae94311e 已可解析 —— 随远端 b6d0a608(「知识库回填: 修 S7a 悬空 hash + issue 0458 置 Done + 悬空 hash 清理入池」)修复, 从实修范围剔除;
  - c9ae4853(§01 示例) / d2dc3ba1(§03 先例)是本报告正文自己的 `<code>` 引用, 19:04 管线先跑、报告后写所以没算进去 —— 属自引用, 不改 KB 其它文件, 收尾置 Done 时随状态更新一并改写掉可提取形态;
  - 实修 = 38 条真实悬空引用, 落在 19 份文件。
- **旧对象不可复原**: 悬空 hash 的 commit 对象已不在本 clone(rebase 重写后 GC), 无法读原始 message; 映射依据 = KB 叙述里随附的 message/步骤描述 + `git log --grep` 在 develop 找 message 匹配的现存 commit, 再核对改动面。跨 clone 读旧对象不做(跨仓库红线)。
- **无等价 commit 的处置**: 叙述已明说「无重放版」的(如 wave3 handover 的 48836d7 孤儿提交)去 hash 保留叙述; 叙述含「已被 X 重放」的按文中映射表替换并核对新 hash 可解析。
- **替换形态约束**: 只在原提取语境(backtick / `<code>` / `commit `前缀)内做整 token 替换, 避免误伤子串; 档案与 issue 正文不新增 backtick 包裹的死 hash, 防止自污染后续扫描。

## 实现计划

1. 认领: issue 置 In Progress + doc-refs 反向声明 + 本档案建立 + kb.index 重建。✅
2. 分组考古: 38 条按提交链分 6 组, 逐条 message 匹配 + 改动面核对, 产出映射表(新 hash 或「去 hash」)。
3. 批量替换: 脚本按语境整 token 替换; 「去 hash」条目逐处手改措辞。
4. 验证: 重跑扫描 ⇒ 悬空 0; 抽查替换处上下文语义通顺。
5. 收尾: issue 置 Done(实际修法/验证方式/数字) + 自引用清理; kb.index; test.full + 基线切片; 新坑入库(pitfalls/kb: KB 引 hash 会被 rebase 打断, 守卫不查可解析性)。

## 子任务状态表

| # | 组 | hash 与处置 | 状态 |
|---|---|---|---|
| 1 | hr-fetch-history 链 S0-S5 | 49da6d06→70d70e3f · 0227f25c→13df6a80 · 4c88e8e2→805da878 · 2923ffa4→e8edae01 · 85a22f8a→d8c4cb8c · ec697a08→3acc3914(message+改动面双核) | Done |
| 2 | hr-steady-throttle 链 S1-S5 | 66696eac→10984535 · 3e4745c2→eeb9290e · e087aa57→4d88bf7e · 22625b49→a270aabb · 9f096c09→943ff662 | Done |
| 3 | drawer-redesign W1-W4 | f994ce20→dadc97a6 · 9c594e1e→7d38e2ea · b81a1ee4→14a4d0e2 · a0b5d73f→54d8b6fc | Done |
| 4 | implemented-webui reannounce/预检链 | f251e301→bf12a487 · 8873c889→89840a3c · 04b5899f→554bf03e · bcc2bce2→ae2982d9 · 09683720→372f197c(批量检查漏报: 前缀被非 commit 对象顶占) · 7d9595a7→64479a28 · 0ff19787→0d2ff943 · 51e30393→005dd20a · bd532d26→b87ed2e1 | Done |
| 5 | wave3-handover 重放映射 | 66f4111→82c5d16 · f38eb32→78672fa · 3da9f1a→9c9d1de · ab9a863→2b4ad3b · f359390/f396972→1371bdb; 48836d7 孤儿→去 hash 保留叙述, §0.1 登记重放入库 21044ac7 | Done |
| 6 | 散件 | 0811ac5→67b3828 · f3cfe91→ccedce8 · 2094a36→0c18fcda · ab82d6c→afef7ce1 · 633d58cd→11619fbf · aac3dcc5→295bb226 · 7e45063c→22429d1a(证据锚点改指 S4 提交); 026742a=apm.lock.yaml 技能包外部 pin→改写「技能包仓库 @ 026742a」消误报; 重写事件旧 hash 全部转平文 | Done |
| 7 | issue 正文自引用 | 0227f25c / c9ae4853(§01) · d2dc3ba1(§03)→平文化, 状态置 Done | Done |
| 8 | 验证与收尾 | 复扫悬空 0(候选 361) + kb.index + test.full + 基线切片 + 坑档 pitfalls/kb/commit-hash-refs.md | Done |

## 进度日志

- 2026-10-06 19:28 — 认领建档。同步 b6d0a608(远端快进 5 笔); 复验 40 条悬空构成如上; 开工。
- 2026-10-06 19:35-19:55 — 分组考古完成: 锚定 13df6a80(S1')正向走链拿齐 hr-fetch-history 全链; 其余四链逐条 `git log --grep` 命中 message 与叙述完全一致的现存 commit; wave3 组映射表文中自带, 逐个核对新 hash 可解析; 散件 0811ac5/f3cfe91/aac3dcc5 由各自档案自证的「重写前后」对定, ab82d6c 经 `git log -- <档案路径>` 定位立档内容随拆分提交 afef7ce1 入库。
- 2026-10-06 19:58 — **发现批量检查盲区**: 09683720 在 batch-check 批量核对中时好时坏 —— 旧 commit 被 GC 后同前缀 blob/tree 顶占前缀, batch-check 只报存在性不报类型; 单验 `git cat-file -t` 返回 missing。纳入映射(→372f197c, message 核对一致)并入坑档。
- 2026-10-06 20:00 — 批量替换: 精确改写 19 处(重写事件转平文 / 孤儿去 hash / 误报源改写 / 自引用去 backtick)+ 边界保护整 token 替换 60 处, 20 份文件零错误; 633d58cd 在 traffic-v3 档案里还有 1 处非提取形态的平文引用也一并替换。
- 2026-10-06 20:05 — 复扫验证: 候选 371→361, 悬空 40→4(全部为预期遗留: issue 自引用 3 条 + tasks/_index.md 生成物 1 条); kb.index 重建后生成物清零。
- 2026-10-06 20:09 — issue 置 Done(含实际修法与验证段), 坑档 pitfalls/kb/commit-hash-refs.md 新立, 全量测试与基线切片收尾。
- 2026-10-06 20:12 — 首跑 test.full 红 1 条: 新档案缺 **Topics:** 主键, `test_doc_topics_complete` 抓到 —— 补 `**Topics:** kb-dangling-hash-refs`(与 issue 的 doc-topic 同键)后复跑全绿 **2679 passed + 3 skipped / 99% / 40.0s**(基线切片 26-10-06-2015)。守阵有用, 记录在案。
