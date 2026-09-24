# kb — 知识库与协作纪律

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 请求边界(问答 vs 执行任务)、纪律为什么会失效、任务档案状态与回扫、改名查引用、skill 装载与脚本路径。
> **触发**: 知识库, 立档, 会话协议, 请求边界, 改名, 引用, skill, 脚本路径, 纪律

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [cap-counting.md](cap-counting.md) | 守卫的字符数比编辑器统计**每行多 1**(CRLF); append-only 流水撞 `log` cap 的正解是**轮转**; 而生成式索引撞 cap 时先查**渲染口径**而不是先搬条目。 | 判断文件是否超 cap, 字符数对不上, baseline-history 超 cap, 追加流水, log 档, 轮转, attachments, tasks/_index 超 cap, 索引膨胀 |
| [discipline.md](discipline.md) | 纪律为什么"反复强调却从不执行"、埋点与验收口径为什么必须有人消费、**闸门能判红却没有能修的命令**、测试写在没人跑的地方等于没写。 | 规则不执行, 立档, 收尾, 埋点, 验收标准, 口径, 测试没跑, testpaths, 生成物, 重建提示, 报错文案指错命令, 照做仍然红 |
| [refs-rename.md](refs-rename.md) | 改文件名或移动文档后必须全仓查引用(坏链不会让任何测试失败); 生成型脚本写路径有两个必踩的坑。 | 改名, 移动文档, 重命名, 生成索引, 写链接, relative_to, relpath |
| [request-boundary.md](request-boundary.md) | 开工先判这一轮是"问答 / 只读"还是"执行任务" —— 把问答当执行任务去做, 是本仓库的**红线**。 | 用户提问, 想延伸排查, 想顺手入池 issue, 想顺手立档, 想 commit |
| [scripts.md](scripts.md) | 脚本类改动里最容易漏的四件事 —— 冷门分支上的未定义名、STOP 级别一刀切、对固定列宽输出整段 strip、把"回给调用方的摘要"当成"只取末 N 行"。 | 改脚本, 改检查脚本, 预检, 解析 git 输出, 解析命令输出, 改名, 输出摘要, 截断, 略过 N 行, 信息预算 |
| [skills-loading.md](skills-loading.md) | skill 里的脚本路径一律写 `<skill-dir>/scripts/…`; 项目级 skill 只挂 `.codebuddy/skills` 一处。 | 写 skill, 装 skill, skill 不出现, 脚本路径, find_root, 脚本找不到 |
| [tasks-archive.md](tasks-archive.md) | 任务档案 `Status` 只能取 4 个英文单词(2026-09-23 起为 `In Progress`/`Open`/`Done`/`Dropped`); 推送后要回扫"未提交"标记, 但只改自己那一轮的。 | 立档, 改 Status, 重建索引, 推送后回扫, 标记未提交 |
