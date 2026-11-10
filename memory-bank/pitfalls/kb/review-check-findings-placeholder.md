# review.check findings 内联 JSON 里的尖括号片段被命令引擎当占位符拒收

> 摘要: review.check findings 内联 JSON 里的尖括号片段被命令引擎当占位符拒收
> 触发: review.check, findings, 内联 JSON, 占位符, 尖括号, STOP 残留, HTML 标签, 评审入账

## 本篇只回答

`commands run <task> --<参数>` 的**参数值里含尖括号片段**(HTML 标签名/泛型/占位符形态)被引擎的占位符展开器拦截怎么办(command 类 task 的残留扫描面; script 类参数直达 argv 不涉及)—— 聚焦 `review.check --findings` 内联 JSON 这一个触发面; 其它参数传长文本的同型问题照此处置。

### `review.check --findings '<内联 JSON>'` 引文含 HTML 标签片段 → [STOP] 残留无法展开的占位符 (2026-11-11 实证, 当场复现两次)

- **触发**: 评审收尾用 `commands run review.check --findings '<inline JSON>'` 把评审发现入账, 而 findings 的引文/描述里含尖括号片段 —— 评审对象是 issue/plan/report 这类 HTML 文件时**几乎必然**出现(引文原样贴 `<code>`、`<meta name="...">` 之类标签片段)。本坑立档时用含 `<code>` 的 `--summary` 建坑档, 建件命令本身当场报了同一个错 —— 占位符展开与残留扫描发生在 **command 类 task**(run 模板含占位符, 参数替换进模板后对整体做残留扫描), 不只 `--findings`; script 类 task 的调用方参数原样直达 argv、不走展开(`.agents/skills/commands/scripts/_config.py` `_script_argv`: `argv += args # 原样直达`, 核验 2026-11-11)。本坑两个实证对象 review.check / kb.new 均为 command 类, 经验事实不变。
- **判别**: 命令 rc=1, 报错行形如 `[STOP] 残留无法展开的占位符 <code>: <task 展开> —— 引擎只认 <root> / <skill-dir:NAME> / <args>`。症状特征: 报错点位的尖括号词**不在**引擎白名单(`<root>` / `<skill-dir:...>` / `<args>`)里, 且它来自你传入的参数文本而非包内 config.toml 的 run 模板。
- **处置**: 参数文本**不内联** —— 把 findings JSON 写进**仓库外**的临时文件(不放仓库内, 免得混进改动面), 再以 `--findings <文件路径>` 传入: `--findings` 参数本来就接受 json 文件路径, 走文件通道引擎不做占位符展开。其它同型参数(长文本/含标签片段)照此办理: 能落文件的落文件, 不能落文件的把尖括号改写为不触发展开的等价表述(如标签名不带尖括号), **不要**试图转义尖括号去哄展开器 —— 白名单形态依赖引擎实现, 不可靠。
- **守阵**: 无(引擎占位符展开器行为属 commands 包内部契约, 未设机检; 靠本档触发词在改码前扫到)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
