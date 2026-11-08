# 分卷索引多一跳: 主索引只给卷号, 定位表在卷页

> 摘要: `pitfalls/{backend,testing,web-ui}` 主索引是分卷路由(只有卷号/主题范围/条数), 定位表在 `_index-<n>.md`; 主索引查不到不等于没有这个坑。
> 触发: 分卷索引,卷页,主索引找不到,多一跳,pitfalls 索引,卷号定位,CLOSED_KEEP,归档索引,全量清单
**Refs:** `memory-bank/pitfalls/backend/_index.md` · `memory-bank/pitfalls/testing/_index.md` · `memory-bank/pitfalls/web-ui/_index.md` · `memory-bank/tasks/_index.md` · `memory-bank/tasks/attachments/_archive.md`

## 本篇只回答

分卷索引(主题文件多到超单文件预算)下怎么找全一个坑/一条完结记录 —— 只讲「多一跳」与「索引不全」这一类, 不涉及单篇坑的判据。

### 主索引只列卷号, 只 grep 主索引会漏掉大部分条目

- **触发**: 在 `pitfalls/backend`、`pitfalls/testing`、`pitfalls/web-ui` 找某条坑; 或问「库里有没有这个坑」。
- **判别**: 主索引 `_index.md` 顶部写「主题(分卷)」, 表头只有「卷 | 主题范围 | 条数」三列, 没有文件名/摘要 —— 这是分卷路由, 不是全量清单。只看主索引就下「没有」的结论即误判。
- **处置**: ①先按主题范围选卷号, 打开 `_index-<n>.md`; ②卷页里才是逐条定位表(文件名 + 摘要), 再打开单篇; ③跨卷时用 `grep -rn "<关键词>" memory-bank/pitfalls/<类>/` 兜底, 而不是只 grep `_index.md`; ④主索引找不到时先看卷页, 再判断「确实没有」。
- **守阵**: `commands run kb.check`(索引完整性) + `commands run doc.links`(全库死链) + `commands run kb.index` 重建; 单篇坑档三行头元数据齐全。
- **复发**: 0

### 完结档的 `CLOSED_KEEP` 是上限, 主索引可能不含老记录

- **触发**: 在 `tasks/`、`plans/`、`reports/`、`issues/` 找一条已完结(Done/Dropped)的记录; 或按主索引核「全量」。
- **判别**: 主索引说明写明 `CLOSED_KEEP` 只是**最近若干条**的展示上限(受 8,000 字符预算挤压), 老档案原地仍在目录里, 只是不出现在索引 —— 主索引缺条目不代表档案不存在。
- **处置**: ①先看 `_index.md` 的已完结段; ②不在索引时查各目录 `attachments/_archive.md`(全量清单, 不计 cap); ③仍无则按日期前缀直接 `ls` 对应目录/文件; ④统计「全量 N 条」以目录实文件为准, 不以主索引条数为准。
- **守阵**: `commands run kb.check`(索引与档案一致性) + 目录实文件计数。
- **复发**: 0
