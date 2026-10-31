# kb.new baseline 的 --total 会自动拼进标题, title 里再带一份就双前缀

> 摘要: kb.new baseline 的 --total 会自动拼进标题, title 里再带一份就双前缀
> 等级: L0
> 触发: kb.new, baseline, 标题双前缀, --total, 基线切片, new_doc.py, 誊写

### kb.new baseline 的 `--total` 会自动拼进标题, title 里再带一份就双前缀

- **触发**: 建基线切片时给 `commands run kb.new baseline --title` 传了以 test.full 汇总行开头的标题(如 `"3983 passed + 10 skipped —— xxx"`)—— `new_doc.py` 自己会把 `--total` 拼到标题与摘要最前面, 手写的那份就成了第二份前缀。
- **判别**: 建成后切片 H1/摘要行出现 `# <total> —— <total> —— <主题>` 的重复前缀; `kb.baseline` 列表里同一条目名也带双前缀。
- **处置**: `--title` 只传主题部分(如 `"抽屉变体渲染层三族重复收敛(issue 26-10-20-2231)"`), `--total` 单独传(它必填, 是防编造数字的闸); 已经建重复了就 Edit 删掉手写那份前缀(只动 H1 与摘要两行, 正文 SLOT 不受影响)。
- **守阵**: 无(头部生成物, 无既有守阵扫标题重复; 靠本条路由)
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
