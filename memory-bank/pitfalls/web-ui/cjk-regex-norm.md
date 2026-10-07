# CJK 搜索归一化: JS 照抄 Python `\W` 会把中文折成空格

> 摘要: 把 Python 的 `[\W_]+ → 空格` 归一化直译成 JS `s.replace(/[\W_]+/g,' ')` 会静默废掉中文搜索 —— Python `\W` 是 Unicode 语义(CJK 算词字符), JS `\W` 是 ASCII 语义(整个中文词全是"非词字符"被折成空格)。前端必须写 `[^\p{L}\p{N}]+/gu`(u 标志必带)。
> 触发: 写前端搜索/过滤, 前端照抄服务端归一化语义, 中文词搜不到, \W, \p{L}, unicode 归一化

### JS 文本归一化用 `[^\p{L}\p{N}]+/gu`, 不用 `\W`

- **触发**: 前端实现与 `views.py::_search_norm` 同语义的文本归一化(分隔符折叠 + 小写), 用于搜索 / 过滤 / 高亮。
- **判别**: 英文与数字能搜到、**中文词搜不到**(或中文整段被折叠后只剩单字) —— 把归一化结果 `console.log` 出来,
  中文被折成空格即为中招。纯代码审查查不出: `/[\W_]+/` 语法完全合法、测试英文用例全绿。
- **处置**: `String(s).replace(/[^\p{L}\p{N}]+/gu, ' ').toLowerCase().trim()`; **u 标志必带**
  —— 没有它 `\p{L}` 直接 SyntaxError(算是好事, 当场暴露)。
  守住同一语义的对照: Python `\W` ≈ JS `[^\p{L}\p{N}]`(Unicode 语义), JS `\W` ≈ ASCII `[^^0-9A-Za-z_]`。
- **守阵**: `tests/test_web_backend_misc.py::test_frontend_tracker_search_wiring` 正则断言 config_hub.js 的
  `trackerNorm` 必须含 `[^\p{L}\p{N}]+/gu`。
- **来源**: 2026-09-28 站点页搜索实施(计划 26-09-27-1852 §04 预警在先, 首踩未遂即入库)。
