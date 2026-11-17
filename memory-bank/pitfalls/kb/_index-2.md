# kb — 知识库与协作纪律 · 卷 2/2

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 生成; 主索引 [_index.md](_index.md) 是分卷路由。
> 本卷主题: `refs-rename.md` … `wrap-did-test-numbers.md`(共 16 条); 主题越多时索引按文件名分卷, 每卷 ≤ 8,000 字符。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [refs-rename.md](refs-rename.md) | 改文件名或移动文档后必须全仓查引用(坏链不会让任何测试失败); 生成型脚本写路径有两个必踩的坑; 认领链 `doc-refs` 是仓库根相对口径, 且双向是**对等义务**(报告/计划不进 doc-refs, 但基线切片/坑档/档案会被扫); 认领方件必须先落盘再回填 doc-refs, 新切片与新 `**Refs:**` 要同一笔写, 悬空/单向窗口都会被全量闸门扫红。 | 改名, 移动文档, 重命名, 生成索引, 写链接, 新写切片, 新写基线切片, 相对深度, relative_to, relpath, 认领链, doc-refs, Refs, 单向链, 双向闭环 |
| [request-boundary.md](request-boundary.md) | 开工先判这一轮是"问答 / 只读"还是"执行任务" —— 把问答当执行任务去做, 是本仓库的**红线**。 | 用户提问, 想延伸排查, 想顺手入池 issue, 想顺手立档, 想 commit |
| [review-check-findings-placeholder.md](review-check-findings-placeholder.md) | review.check findings 内联 JSON 里的尖括号片段被命令引擎当占位符拒收 | review.check, findings, 内联 JSON, 占位符, 尖括号, STOP 残留, HTML 标签, 评审入账 |
| [review-finding-claim-verify.md](review-finding-claim-verify.md) | review.check 只验「引文与源文件逐字一致」(±3 行邻近), 不验 claim 的事实性 —— reviewer 报「某行号失实」这类发现时, 引文合法但方向可能反了; 主会话采纳前必须实测目标行, 否则错向修复会被后续轮的回退校验连环背书, 三轮才纠出 | 评审发现行号, 引文过检, claim 事实性, 行号漂移修复, 回退校验背书, 评审发现采纳 |
| [review-pack-count-vs-gate-count.md](review-pack-count-vs-gate-count.md) | review.pack 的 diff 统计与 review.trace 闸门实算口径不同(后者排除生成物/记账面), 批内混有生成物时声明行数必不等 —— 2026-11-11 起已根治: 锚点与逐笔实算收编 review_content 单点, pack「评审规模」= 闸门实算恒同源, trailer 行数照 pack 抄即可 | review.pack, review.trace, Review trailer, 声明行数, 实算, 生成物排除 |
| [review-pack-rename-double-count.md](review-pack-rename-double-count.md) | 行数实算单点(`review_content.py` 全部 numstat 调用)恒钉 `--no-renames`,批内大文件移动被计成删+增双份全文 —— 这是刻意取舍(开 rename 检测会打开 0 行改名假绿漏算 + 排除面被合成路径绕开 + 相似度阈值跨 clone 漂移),不是「rename 未被检测」的 bug。 | 批内有大 HTML/大文件移动(如收尾回写挪件), pack 报出远超实质改动的规模(2026-11-17 实测: 13 行实质 + 移动 1172 行 HTML → 2357 行,另一会话误判成脚本缺陷并来复验)。 |
| [review-trace-booking-sensitive-deadlock.md](review-trace-booking-sensitive-deadlock.md) | 旧闸门(count<FLOOR 先于 trailer 解析)下, 记账类不计行 + 文件名含敏感词(state/auth/token/credential/secret/password 子串)的 <50 行批无论写 Review: 还是 Review-Skip: 都被前置硬拦, 收尾批无法提交 —— 2026-11-08 大重构 D9 退役 50 行下限后死结消失; 本档留作事故档案与命名警觉 | review.trace 触碰安全敏感面, 不论行数都要评, 收尾批过不了闸, 记账类不计行, 敏感词文件名, Review-Skip 也被拦 |
| [reviewer-subagent-hang-on-long-commands.md](reviewer-subagent-hang-on-long-commands.md) | 评审/实现子代理在可跑长命令的派遣上挂死: 纯静态+短命令纪律防免 | 子代理挂死, 600s 无活动, TaskStop 拒绝, SendMessage 续跑, 纯静态评审 |
| [scope-qualifier-parenthetical.md](scope-qualifier-parenthetical.md) | 复合命题里的限定括注(如「仅写入计划」「仅记录」「先不实施」)被默认读成只修饰紧邻子句, 其余子句照常实施 —— 拆解出的实施步骤含了用户明确排除的项, 派工被用户当场纠正。括注的修饰范围是**逐项拍板的事实, 不是语法可推断的默认**。 | 括注, 仅写入计划, 仅记录, 先不实施, 拆解任务, 派工范围, 超范围实施, 复合命题, 限定语, 实施计划 |
| [scripts.md](scripts.md) | 脚本类改动里最容易漏的五件事 —— 冷门分支上的未定义名、STOP 级别一刀切、对固定列宽输出整段 strip、给调用方的输出做过有损摘要(只取末 N 行 / 略过提示都错, 终点是全文透传 + 声明式静默)、**正则匹配 markdown 粗体时用 `[^*]*` 横跨相邻粗体段而误报**。 | 改脚本, 改检查脚本, 预检, 解析 git 输出, 解析命令输出, 改名, 输出摘要, 截断, 略过 N 行, 信息预算, 全文透传, silent_success, token 税, 挑行, 守卫脚本, 正则, 粗体, markdown 解析, 误报 |
| [skills-loading.md](skills-loading.md) | skill 里的脚本路径一律写 `<skill-dir>/scripts/…`; 项目级 skill 只挂 `.codebuddy/skills` 一处。 | 写 skill, 装 skill, skill 不出现, 脚本路径, find_root, 脚本找不到 |
| [subagent-quota-kill-redispatch.md](subagent-quota-kill-redispatch.md) | 长子代理(评审/实施)可能被宿主配额限流中途截断(exceed quota limit, 交回部分输出); 此时 `SendMessage` 续跑报「No active local_agent task found」—— 被配额终止的代理实例不可恢复, 唯一恢复路 = **同任务重派全新代理**, 任务提示必须自含全部上下文(前任零记忆)。与 `kb-subagent-concurrency`(并发拒收, 逐个重派即恢复)是两类独立故障。 | exceed quota limit, No active local_agent task found, 子代理截断, 重派, 部分输出, SendMessage 失败 |
| [subagent-survey-fact-verify.md](subagent-survey-fact-verify.md) | 盘点子代理报告与源码注释都是二手事实 —— 计数/文件名/语义映射直接采信进制品, 评审轮才抓回; 承重项引用前自己数一遍/grep 一遍, 语义相似 ≠ 同一动作, 映射要追到方法链终点 | 盘点, 二手事实, 子代理报告, 采信, 抽验, 语义推断, 方法链, 源码注释计数 |
| [task-command-surface.md](task-command-surface.md) | `commands` 包某条 task 的 `run` 条数 / 首个脚本名 / 生成器集合被别处写死 —— 引擎自证压缩用例、`gen_cmd` 守卫、文档里的"共 N 条"都可能据此断言; 收编命令前先搜消费点, 用例改成从声明处现算。 | 改包内 task 的 run 清单, 收编命令, 命令条数变化, gen_all, kb.index, test_engine 自证压缩, GEN_CMD_BY_SCRIPT |
| [tasks-archive.md](tasks-archive.md) | 任务档案 `Status` 只能取 4 个英文单词(2026-09-23 起为 `In Progress`/`Open`/`Done`/`Dropped`); 推送后要回扫"未提交"标记, 但只改自己那一轮的, 且只改**状态标记**不动**历史叙述**; 必备章节标题必须行首纯标题(后缀注释撞守卫行首锚, 红在合流后的其它 clone 爆)。 | 立档, 改 Status, 重建索引, 推送后回扫, 标记未提交, 一并回扫, 状态标记, 历史叙述, 章节标题, 行首锚, 后缀注释 |
| [wrap-did-test-numbers.md](wrap-did-test-numbers.md) | `commands run kb.wrap --did "..."` 的一句话会同时写进切片 R 行(`**R1(日期):**` 前缀)与档案进度日志行, 两处都不匹配「带日期前缀的行」豁免; 句里带 `213 passed` 这类裸数字会被 kb.check 的 check_wording 判红(判据族 B, 只拦新增)。2026-10-17 当天两个会话各踩一次, 2026-10-22 再犯(--did 路径); 2026-11-05 第 4 次走的是**另一条路径** —— 档案收尾段直接抄数字(SKILL.md DoD 第 4 条「写进本次结论」歧义措辞所致, 当轮已修); 2026-11-17 第 5 次同走档案正文路径(收口结论节抄数字), 且同轮再次实证「判红行指存量件」形态。另: 2026-11-17 前, 判红时打印的违规行取自全量命中的扫描序末 N 条, 常指向无关的存量件; 守阵已改(issue 26-11-17-0852, 超线时对 HEAD 清单现算 diff 报真新增), 「判红位置可能指向存量件」节的判别法降级为备用。 | kb.wrap, --did, 裸测试数字, check_wording 判红, R 行不写数字, 收尾回写, 手抄数字判红位置, 末 N 条, 存量还是新增, 清单 diff 定位, 误判入池 |
