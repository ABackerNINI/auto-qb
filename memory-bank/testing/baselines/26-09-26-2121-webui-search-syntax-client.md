# 1680 passed + 1 skipped / 0 failed —— 搜索语法客户端补齐(种子页过滤升级 + 清除钮焦点态修复)

> 摘要: 用户真机报障双修: ①种子页 `filteredTorrents` 仍是旧整句子串客户端过滤, 词 AND / `-排除` 在该视图全失效 ——
> 升级为与服务端同一语法(filters.js `_parseSearchQuery`/`_searchNorm`/`_torrentTextMatch` 单点, hr.js 旧版删除);
> ②搜索清除钮在输入框有焦点时点击无效(focus 宽度过渡把绝对定位按钮移出光标) —— 两主题加 `@mousedown.prevent`。
> +1 守阵测试(静态 + node 行为对账); 无配置/状态/依赖变化
> 基线时间: 2026-09-26 21:21
> 档案: 26-09-26-webui-search-query-syntax

- **测试增量**: +1 条(`test_web.py::test_frontend_search_syntax_wiring`,「## 测试计划」docstring 同步)——
  四段: 清除钮 `@mousedown.prevent` 两主题成对 / 解析匹配单点在 filters.js 且 hr.js 旧整句实现已删 /
  归一折叠须 Unicode 词字符(`\W` 会折叠掉 CJK)/ filteredTorrents 接线 + searching 守卫(仅负词返回空)。
  有 node 时以 vm 沙箱真跑 filters.js 三个纯函数, 与 `views.py` 的 `_parse_query`/`_search_norm`
  **逐项对账**(跨语言口径漂移即红); 无 node 静默跳过(不引入 pytest skip)。
- **对账守阵当场抓到 1 处真实漂移**: JS 首版归一保留了下划线(`[^\p{L}\p{N}_]+`), 而 Python `[\W_]`
  显式折叠下划线 —— 手工用例没覆盖下划线名字, 跨语言对账用例一次钉出, 修为 `[^\p{L}\p{N}]+`。
- **无 node 环境行为**: 守阵的静态四段仍生效, 行为段自动跳过。

TOTAL 91%(11298 语句 / 816 未覆盖 / 3724 分支 / 332 partial; views.py 97%;
test.full 19.4s; 覆盖率口径见 [../baseline.md](../baseline.md))。
