# kb.wrap 的 --did 不能带裸测试数字

> 摘要: `commands run kb.wrap --did "..."` 的一句话会同时写进切片 R 行(`**R1(日期):**` 前缀)与档案进度日志行, 两处都不匹配「带日期前缀的行」豁免; 句里带 `213 passed` 这类裸数字会被 kb.check 的 check_wording 判红(判据族 B, 只拦新增)。2026-10-17 当天两个会话各踩一次。
> 触发: kb.wrap, --did, 裸测试数字, check_wording 判红, R 行不写数字, 收尾回写

**Refs:** memory-bank/tasks/26-10-17-webui-traffic-source-fixes.md

### --did 长句里顺手带进测试数字

- **触发**: 收尾时 `--did` 写成口语化长总结, 把「gtm 工具侧 213 passed」这类数字顺手带进句子(2026-10-17 21:17 实测, 同日 webui-delete-reannounce 会话已踩过一次但只记在当日日志、未升坑档)。
- **判别**: `commands run kb.check` 报 `[裸 passed 数字]`, 行号指向 activeContext 切片; 切片 R 行前缀是 `**R1(YYYY-MM-DD HH:MM):**`, **匹配不上**「带日期前缀的行」豁免(那条豁免救的是档案进度日志的 `- <stamp> <did>` 行首日期, 救不了 R 行句中数字); 修完切片行还要修档案进度行——kb.wrap 把同一句写了两处, 只改一处复跑仍红。
- **处置**: `--did` 只写量级/持平表述(「全域回归全绿」), 数字只进 `testing/baselines/` 新基线切片, 正文引切片文件名不抄数字; 写 --did 前先自问「这句里有没有 passed/失败数」。若已判红: 切片 R 行与档案进度行同源文本各改一处, 复跑 kb.check 转绿即可(改动不涉及索引, 不用 kb.index)。
