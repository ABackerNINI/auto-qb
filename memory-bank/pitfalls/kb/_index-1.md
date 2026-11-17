# kb — 知识库与协作纪律 · 卷 1/2

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 生成; 主索引 [_index.md](_index.md) 是分卷路由。
> 本卷主题: `artifact-secret-write-guard.md` … `rebase-conflict-resolve.md`(共 16 条); 主题越多时索引按文件名分卷, 每卷 ≤ 8,000 字符。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [artifact-secret-write-guard.md](artifact-secret-write-guard.md) | 工作区写入守卫(artifact_secret_detected)扫的是**落盘后的整份文件**, 不是本次新增文本 —— 文件里既有 `token: ""`(空串初值)或测试夹具里的 `Authorization` 头这类「长得像凭据赋值」的历史行时, 对该文件的 edit/apply_patch/write **任何一次**都会被拦, 且报错行号指向既有行而非本次改动。绕过(换工具直改)被守卫自己禁止; 唯一正道 = 如实把误判证据交给用户裁定, 批准后用**锚点替换脚本**(断言锚点唯一、不动既有行)落盘, 事后在档案里留痕。 | 写入被拦, artifact_secret_detected, 键名 token, Authorization, 凭据字面量误判, state.js 写不进, 测试文件写不进, 整文件扫描 |
| [cap-counting.md](cap-counting.md) | 守卫的字符数比编辑器统计**每行多 1**(CRLF); cap 是**字符数**而外部常报**字节数**(中文一字 3 字节 ⇒ 可差 3 倍, 误报出根本不存在的债务); append-only 流水撞 `log` cap 的正解是**轮转**; 外迁到 `attachments/` 时随迁的相对链接要**整体上移一层**(否则 `doc.links` 坏链); 而生成式索引撞 cap 时先查**渲染口径**而不是先搬条目。 | 判断文件是否超 cap, 字符数对不上, KB 超 cap, 字节 vs 字符, 债务误报, 单位换算, baseline-history 超 cap, 追加流水, log 档, 轮转, attachments, 外迁附件坏链, 随迁链接, 相对链接上移, doc.links 坏链, tasks/_index 超 cap, 索引膨胀, 新增主题放哪个类, 类索引贴顶, 切片计数超限, SLICE_COUNT_LIMIT, 蒸馏切片 |
| [cap-debt.md](cap-debt.md) | 尺寸 cap 从「提交前置条件」降级为**债务**(2026-09-30) 时, 有三处会静默把债务重新变成阻塞 —— warns 里混入非债务提示、检查器不可用被判 STOP、以及删除尺寸断言后守卫退化成恒绿。 | cap 债务, doc.caps, --strict, warns 混装, DEBT_MARK, 检查器找不到, 降级守卫, 恒绿守卫, 可发现性断言, 债务清零, 清理会话 |
| [commit-hash-refs.md](commit-hash-refs.md) | KB(backtick / `<code>` / `commit <hash>` 语境)里记 feature 分支提交, 分支 rebase 并入 develop 后旧 hash 对象不可解析; 守卫(kb.check / test_docs_forms)不查可解析性, 静默累积。另: `git cat-file --batch-check` 只报存在性不报类型, 旧 commit 被 GC 后同前缀 blob/tree 会顶占前缀, 核对结果「时好时坏」。 | KB 里写 commit hash, rebase 合流, 悬空 hash, cat-file missing, 按图索骥找不到提交, hash 时好时坏 |
| [date-authoring.md](date-authoring.md) | 「时间戳用命令取当前值」这条约定写了两处, 但那条命令**根本不存在** —— 日期实际全是 agent 按会话上下文手敲的(未来时间与错体例由此而来); 而守卫只查文件名的**形状**, 不查**值**。 | 日期不准, 未来日期, 时间戳, 文件名日期, 最后活动, doc-added, 时间体例, 取时命令 |
| [discipline.md](discipline.md) | 纪律为什么"反复强调却从不执行"、埋点与验收口径为什么必须有人消费、**闸门能判红却没有能修的命令**、**该判的却没判(闸门漏挂 → 静默红)**、测试写在没人跑的地方等于没写。 | 规则不执行, 立档, 收尾, 埋点, 验收标准, 口径, 测试没跑, testpaths, 生成物, 重建提示, 报错文案指错命令, 照做仍然红, 闸门漏挂, 静默红, 闸门覆盖, kb.check |
| [doc-status-meta.md](doc-status-meta.md) | `plans/` `reports/` 的 `<meta name="doc-status">` 不在 5 词表(`Open`/`In Progress`/`Done`/`Dropped`/`Superseded`)时, 该件不落任何分区 ⇒ **静默漏收**。修复前 `kb.index` 仍打印「已生成 N 个生成物」、零警告, `kb.check` / `kb.docmap --check` / `doc.links` 全绿, 只有 `test.full`(`test_docs_forms.py::test_status_vocabulary`)才红。2026-10-16 已把检查**提前到根因**(生成器 fail-fast + 闸门同源校验, 见处置)。诱因通常是写了「语义上像状态、但不在表里」的词(如 `Draft`)。 | 新建计划/报告, doc-status, 状态词, 索引漏收, kb.index 已生成但件不在索引, Draft, test_status_vocabulary |
| [doc-topics-comma-composite.md](doc-topics-comma-composite.md) | Topics 行英文逗号不拆主键 | Topics, 专题主键, docmap, 跨形态视图, 名录 |
| [doc-verify-completed-claim.md](doc-verify-completed-claim.md) | 结档文档禁把未执行的验证写成完成式 (含悬空基线引用) | 结档, 修复后补充, 全量测试全绿, 见 kb.baseline, 完成式断言, 验证依据, 悬空引用 |
| [handmade-doc-header-escape.md](handmade-doc-header-escape.md) | 手写计划/报告绕过 kb.new: 缺 doc-* 头部整件逃出新增面守卫 | 计划件无状态, (无状态), 手写头部, doc-status, doc-added, 缺状态, 排期计划, 新建计划 |
| [index-archive-view.md](index-archive-view.md) | 生成式索引撞 `index-auto` cap 且「无摘要口径」本身已 > cap(即摘要砍到 0 也超)时, 后备出口不是「搬走老条目」而是**视图归档** —— 生成器只渲染已关闭状态最近 N 条, 文件原地不动, 全量清单另落 `attachments/`; 因为搬文件的前提是「被搬物零引用」, 而实测零引用条目远不够清偿, 且会牵动 md 链接与双向认领链。 | 索引条目数撑爆 cap, 无摘要口径超 cap, 后备出口, 搬文件 vs 视图归档, CLOSED_KEEP, 归档索引, attachments, 冻结件认领链, issues/_index 触顶, EXTRA_GENERATED |
| [index-volume-routing.md](index-volume-routing.md) | `pitfalls/{backend,testing,web-ui}` 主索引是分卷路由(只有卷号/主题范围/条数), 定位表在 `_index-<n>.md`; 主索引查不到不等于没有这个坑。 | 分卷索引,卷页,主索引找不到,多一跳,pitfalls 索引,卷号定位,CLOSED_KEEP,归档索引,全量清单 |
| [kb-baseline-title-double-prefix.md](kb-baseline-title-double-prefix.md) | kb.new baseline 的 --total 会自动拼进标题, title 里再带一份就双前缀 | kb.new, baseline, 标题双前缀, --total, 基线切片, new_doc.py, 誊写 |
| [kb-subagent-concurrency.md](kb-subagent-concurrency.md) | 同一轮并发派遣多个子代理(或后台代理未收割时再派)会被宿主并发上限拒收, 失败形态是 `user concurrency limit exceeded` —— 逐个重派即恢复, 不是派遣机制坏了 | 派子代理, 并发派遣, review 分面, user concurrency limit exceeded, 后台代理, 调研代理 |
| [nav-ref-guard-mismatch.md](nav-ref-guard-mismatch.md) | 认领链「未入库」多半不是丢件: 导航层判据必须与 kb.check 对齐 | 未入库,认领链死链,关系图悬空,ref 判据不一致,归档回退,仓库根相对 |
| [rebase-conflict-resolve.md](rebase-conflict-resolve.md) | 与远端分叉后 `git rebase origin/develop`, 冲突几乎全落在「双方各追加一行」的档案进度日志、切片 R 行与生成物索引上 —— 追加行要**两边都留**(不是二选一), 撞号的 R 要**顺延**, 生成物**取一侧 + 重跑生成器**, 而用字符串替换解冲突时切记 `>>>>>>> <hash>` 后面还跟着**提交主题**, 只匹配到 hash 会把主题留在行尾变成脏值。 | rebase 冲突, 解冲突, R 编号撞车, 同号 R12, 最后活动 格式坏, 冲突标记残留, 追加行冲突, 生成物取一侧, 提交主题残留在行尾, git rebase --continue |
