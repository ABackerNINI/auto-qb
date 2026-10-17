# kb — 知识库与协作纪律

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 请求边界(问答 vs 执行任务)、纪律为什么会失效、任务档案状态与回扫、改名查引用、skill 装载与脚本路径。
> **触发**: 知识库, 立档, 会话协议, 请求边界, 改名, 引用, skill, 脚本路径, 纪律

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [cap-counting.md](cap-counting.md) | 守卫的字符数比编辑器统计**每行多 1**(CRLF); cap 是**字符数**而外部常报**字节数**(中文一字 3 字节 ⇒ 可差 3 倍, 误报出根本不存在的债务); append-only 流水撞 `log` cap 的正解是**轮转**; 外迁到 `attachmen… | 判断文件是否超 cap, 字符数对不上, KB 超 cap, 字节 vs 字符, 债务误报, 单位换算, baseline-history 超 cap, 追加流水, log 档, 轮转, attachments, 外迁附件坏链, 随迁链接,… |
| [cap-debt.md](cap-debt.md) | 尺寸 cap 从「提交前置条件」降级为**债务**(2026-09-30) 时, 有三处会静默把债务重新变成阻塞 —— warns 里混入非债务提示、检查器不可用被判 STOP、以及删除尺寸断言后守卫退化成恒绿。 | cap 债务, doc.caps, --strict, warns 混装, DEBT_MARK, 检查器找不到, 降级守卫, 恒绿守卫, 可发现性断言, 债务清零, 清理会话 |
| [commit-hash-refs.md](commit-hash-refs.md) | KB(backtick / `<code>` / `commit <hash>` 语境)里记 feature 分支提交, 分支 rebase 并入 develop 后旧 hash 对象不可解析; 守卫(kb.check / test_docs_forms)不查可解析性, 静默累积… | KB 里写 commit hash, rebase 合流, 悬空 hash, cat-file missing, 按图索骥找不到提交, hash 时好时坏 |
| [date-authoring.md](date-authoring.md) | 「时间戳用命令取当前值」这条约定写了两处, 但那条命令**根本不存在** —— 日期实际全是 agent 按会话上下文手敲的(未来时间与错体例由此而来); 而守卫只查文件名的**形状**, 不查**值**。 | 日期不准, 未来日期, 时间戳, 文件名日期, 最后活动, doc-added, 时间体例, 取时命令 |
| [discipline.md](discipline.md) | 纪律为什么"反复强调却从不执行"、埋点与验收口径为什么必须有人消费、**闸门能判红却没有能修的命令**、**该判的却没判(闸门漏挂 → 静默红)**、测试写在没人跑的地方等于没写。 | 规则不执行, 立档, 收尾, 埋点, 验收标准, 口径, 测试没跑, testpaths, 生成物, 重建提示, 报错文案指错命令, 照做仍然红, 闸门漏挂, 静默红, 闸门覆盖, kb.check |
| [doc-status-meta.md](doc-status-meta.md) | `plans/` `reports/` 的 `<meta name="doc-status">` 不在 5 词表(`Open`/`In Progress`/`Done`/`Dropped`/`Superseded`)时, 该件不落任何分区 ⇒ **静默漏收**。修复前 `kb.i… | 新建计划/报告, doc-status, 状态词, 索引漏收, kb.index 已生成但件不在索引, Draft, test_status_vocabulary |
| [index-archive-view.md](index-archive-view.md) | 生成式索引撞 `index-auto` cap 且「无摘要口径」本身已 > cap(即摘要砍到 0 也超)时, 后备出口不是「搬走老条目」而是**视图归档** —— 生成器只渲染已关闭状态最近 N 条, 文件原地不动, 全量清单另落 `attachments/`; 因为搬文件的前… | 索引条目数撑爆 cap, 无摘要口径超 cap, 后备出口, 搬文件 vs 视图归档, CLOSED_KEEP, 归档索引, attachments, 冻结件认领链, issues/_index 触顶, EXTRA_GENERATED |
| [refs-rename.md](refs-rename.md) | 改文件名或移动文档后必须全仓查引用(坏链不会让任何测试失败); 生成型脚本写路径有两个必踩的坑; 认领链 `doc-refs` 是仓库根相对口径, 且双向是**对等义务**(报告/计划不进 doc-refs); 认领方件必须先落盘再回填 doc-refs, 悬空窗口会被全量闸门扫… | 改名, 移动文档, 重命名, 生成索引, 写链接, 新写切片, 相对深度, relative_to, relpath, 认领链, doc-refs, Refs, 单向链, 双向闭环 |
| [request-boundary.md](request-boundary.md) | 开工先判这一轮是"问答 / 只读"还是"执行任务" —— 把问答当执行任务去做, 是本仓库的**红线**。 | 用户提问, 想延伸排查, 想顺手入池 issue, 想顺手立档, 想 commit |
| [scope-qualifier-parenthetical.md](scope-qualifier-parenthetical.md) | 复合命题里的限定括注(如「仅写入计划」「仅记录」「先不实施」)被默认读成只修饰紧邻子句, 其余子句照常实施 —— 拆解出的实施步骤含了用户明确排除的项, 派工被用户当场纠正。括注的修饰范围是**逐项拍板的事实, 不是语法可推断的默认**。 | 括注, 仅写入计划, 仅记录, 先不实施, 拆解任务, 派工范围, 超范围实施, 复合命题, 限定语, 实施计划 |
| [scripts.md](scripts.md) | 脚本类改动里最容易漏的五件事 —— 冷门分支上的未定义名、STOP 级别一刀切、对固定列宽输出整段 strip、给调用方的输出做过有损摘要(只取末 N 行 / 略过提示都错, 终点是全文透传 + 声明式静默)、**正则匹配 markdown 粗体时用 `[^*]*` 横跨相邻粗体… | 改脚本, 改检查脚本, 预检, 解析 git 输出, 解析命令输出, 改名, 输出摘要, 截断, 略过 N 行, 信息预算, 全文透传, silent_success, token 税, 挑行, 守卫脚本, 正则, 粗体, markdown… |
| [skills-loading.md](skills-loading.md) | skill 里的脚本路径一律写 `<skill-dir>/scripts/…`; 项目级 skill 只挂 `.codebuddy/skills` 一处。 | 写 skill, 装 skill, skill 不出现, 脚本路径, find_root, 脚本找不到 |
| [task-command-surface.md](task-command-surface.md) | `commands` 包某条 task 的 `run` 条数 / 首个脚本名 / 生成器集合被别处写死 —— 引擎自证压缩用例、`gen_cmd` 守卫、文档里的"共 N 条"都可能据此断言; 收编命令前先搜消费点, 用例改成从声明处现算。 | 改包内 task 的 run 清单, 收编命令, 命令条数变化, gen_all, kb.index, test_engine 自证压缩, GEN_CMD_BY_SCRIPT |
| [tasks-archive.md](tasks-archive.md) | 任务档案 `Status` 只能取 4 个英文单词(2026-09-23 起为 `In Progress`/`Open`/`Done`/`Dropped`); 推送后要回扫"未提交"标记, 但只改自己那一轮的, 且只改**状态标记**不动**历史叙述**; 必备章节标题必须行首纯… | 立档, 改 Status, 重建索引, 推送后回扫, 标记未提交, 一并回扫, 状态标记, 历史叙述, 章节标题, 行首锚, 后缀注释 |
| [wrap-did-test-numbers.md](wrap-did-test-numbers.md) | `commands run kb.wrap --did "..."` 的一句话会同时写进切片 R 行(`**R1(日期):**` 前缀)与档案进度日志行, 两处都不匹配「带日期前缀的行」豁免; 句里带 `213 passed` 这类裸数字会被 kb.check 的 check_w… | kb.wrap, --did, 裸测试数字, check_wording 判红, R 行不写数字, 收尾回写 |
