# 改 md 档案时用替换片段吞掉相邻字段

> 摘要: 在 Markdown 文档(尤其 `memory-bank/tasks/*.md` / `activeContext/*.md` 的头部元数据块)上做字符串替换时, 把**下一行的字段标签**一起卷进 `old` 会静默删掉它 —— md 没有闭合标签, 删了不报错, 渲染出来只是"少了一个字段"。
> 触发: 改任务档案, 改 activeContext 切片, 头部元数据, Status/Updated/Summary 字段, 字符串替换, 替换片段吞掉整行, Markdown 静默丢失

## 头部元数据是行级字段: `old` 不要跨到下一行的标签

- **触发**: 想改 `**Updated:**` / `**Summary:**` 这类头部字段, 而 `old` 顺手带上了下一行的开头
  (例如 `old` = `**Updated:** 2026-09-24\n**Summary:** 部分种子 HR 站点在线核实`, `new` 只写了 `**Updated:** 2026-09-24`)。
- **判别**: 目标字段改了, 但**被带上的那个标签也被删了** —— 档案变成
  `**Updated:** 2026-09-24 (取 HR 统计页 …)` 这种"Summary 正文粘在 Updated 后面"的畸形行。
  与 HTML 不同, **这里没有任何机检会报错**: md 没有闭合标签, `kb.index` / 文档守阵只查链接与元数据存在性,
  所以只有"改完立刻回读那几行"才能发现。踩过 1 次 (2026-09-24, 改 `26-09-22-backend-partial-hr-verify.md`)。
- **处置**: ① `old` 的边界**只到目标行的行尾**, 需要跨行时把中间行**原样抄进 `new`**;
  ② 一条替换只动**一个字段** (改 `Updated` 就只匹配 `**Updated:** <旧值>`);
  ③ 改完立刻 `read_file` 回读头部 5–10 行, 确认 `Status/Added/Updated/Summary/Topics/Refs` 六个标签都还在 ——
  这一步比任何机检都便宜可靠。
