# kb — 知识库与协作纪律

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 请求边界(问答 vs 执行任务)、纪律为什么会失效、任务档案状态与回扫、改名查引用、skill 装载与脚本路径。
> **触发**: 知识库, 立档, 会话协议, 请求边界, 改名, 引用, skill, 脚本路径, 纪律

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [cap-counting.md](cap-counting.md) | 守卫的字符数比编辑器统计**每行多 1**(CRLF); cap 是**字符数**而外部常报**字节数**(中文一字 3 字节 ⇒ 可差 3 倍, 误报出根本不存在的债务); append-only 流水撞 `log` cap 的正解是**轮转**; 而生成式索引撞 cap 时先查**渲染口径**而不是先搬条目。 | 判断文件是否超 cap, 字符数对不上, KB 超 cap, 字节 vs 字符, 债务误报, 单位换算, baseline-history 超 cap, 追加流水, log 档, 轮转, attachments, tasks/_index 超 cap, 索引膨胀, 新增主题放哪个类, 类索引贴顶, 切片计数超限, SLICE_COUNT_LIMIT, 蒸馏切片 |
| [cap-debt.md](cap-debt.md) | 尺寸 cap 从「提交前置条件」降级为**债务**(2026-09-30) 时, 有三处会静默把债务重新变成阻塞 —— warns 里混入非债务提示、检查器不可用被判 STOP、以及删除尺寸断言后守卫退化成恒绿。 | cap 债务, doc.caps, --strict, warns 混装, DEBT_MARK, 检查器找不到, 降级守卫, 恒绿守卫, 可发现性断言, 债务清零, 清理会话 |
| [commit-hash-refs.md](commit-hash-refs.md) | KB(backtick / `<code>` / `commit <hash>` 语境)里记 feature 分支提交, 分支 rebase 并入 develop 后旧 hash 对象不可解析; 守卫(kb.check / test_docs_forms)不查可解析性, 静默累积。另: `git cat-file --batch-check` 只报存在性不报类型, 旧 commit 被 GC 后同前缀 blob/tree 会顶占前缀, 核对结果「时好时坏」。 | KB 里写 commit hash, rebase 合流, 悬空 hash, cat-file missing, 按图索骥找不到提交, hash 时好时坏 |
| [date-authoring.md](date-authoring.md) | 「时间戳用命令取当前值」这条约定写了两处, 但那条命令**根本不存在** —— 日期实际全是 agent 按会话上下文手敲的(未来时间与错体例由此而来); 而守卫只查文件名的**形状**, 不查**值**。 | 日期不准, 未来日期, 时间戳, 文件名日期, 最后活动, doc-added, 时间体例, 取时命令 |
| [discipline.md](discipline.md) | 纪律为什么"反复强调却从不执行"、埋点与验收口径为什么必须有人消费、**闸门能判红却没有能修的命令**、测试写在没人跑的地方等于没写。 | 规则不执行, 立档, 收尾, 埋点, 验收标准, 口径, 测试没跑, testpaths, 生成物, 重建提示, 报错文案指错命令, 照做仍然红 |
| [refs-rename.md](refs-rename.md) | 改文件名或移动文档后必须全仓查引用(坏链不会让任何测试失败); 生成型脚本写路径有两个必踩的坑; 认领链 `doc-refs` 是仓库根相对口径。 | 改名, 移动文档, 重命名, 生成索引, 写链接, 新写切片, 相对深度, relative_to, relpath, 认领链, doc-refs, Refs |
| [request-boundary.md](request-boundary.md) | 开工先判这一轮是"问答 / 只读"还是"执行任务" —— 把问答当执行任务去做, 是本仓库的**红线**。 | 用户提问, 想延伸排查, 想顺手入池 issue, 想顺手立档, 想 commit |
| [scripts.md](scripts.md) | 脚本类改动里最容易漏的四件事 —— 冷门分支上的未定义名、STOP 级别一刀切、对固定列宽输出整段 strip、给调用方的输出做过有损摘要(只取末 N 行 / 略过提示都错, 终点是全文透传 + 声明式静默)。 | 改脚本, 改检查脚本, 预检, 解析 git 输出, 解析命令输出, 改名, 输出摘要, 截断, 略过 N 行, 信息预算, 全文透传, silent_success, token 税, 挑行 |
| [skills-loading.md](skills-loading.md) | skill 里的脚本路径一律写 `<skill-dir>/scripts/…`; 项目级 skill 只挂 `.codebuddy/skills` 一处。 | 写 skill, 装 skill, skill 不出现, 脚本路径, find_root, 脚本找不到 |
| [task-command-surface.md](task-command-surface.md) | `commands` 包某条 task 的 `run` 条数 / 首个脚本名 / 生成器集合被别处写死 —— 引擎自证压缩用例、`gen_cmd` 守卫、文档里的"共 N 条"都可能据此断言; 收编命令前先搜消费点, 用例改成从声明处现算。 | 改包内 task 的 run 清单, 收编命令, 命令条数变化, gen_all, kb.index, test_engine 自证压缩, GEN_CMD_BY_SCRIPT |
| [tasks-archive.md](tasks-archive.md) | 任务档案 `Status` 只能取 4 个英文单词(2026-09-23 起为 `In Progress`/`Open`/`Done`/`Dropped`); 推送后要回扫"未提交"标记, 但只改自己那一轮的, 且只改**状态标记**不动**历史叙述**; 必备章节标题必须行首纯标题(后缀注释撞守卫行首锚, 红在合流后的其它 clone 爆)。 | 立档, 改 Status, 重建索引, 推送后回扫, 标记未提交, 一并回扫, 状态标记, 历史叙述, 章节标题, 行首锚, 后缀注释 |
