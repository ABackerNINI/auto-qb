# v.Nu 把 Vue 模板分片整批判红: 那是范畴错误, 不是缺陷

> 摘要: `shared/tpl/*.html` 是 Vue 模板**片段**, `v-if` / `@click` / `:class` 是指令不是 HTML 属性 —— 送 W3C v.Nu 校验必然逐条报 `Attribute "…" not allowed`, 提交闸门因此整批红
> 触发: v.Nu 报 Attribute not allowed, check_html --vnu 红, 提交闸门 HTML 规范级, Vue 指令校验, tpl 分片, overlays.html, 皮肤壳 index.html, 模板片段不是文档
**Refs:** memory-bank/conventions/webui.md(模板分片) · memory-bank/pitfalls/web-ui/tpl-comment-split-orphan.md

### 改一行模板属性, 提交闸门被 22 条 "Attribute not allowed" 挡住

- **触发**: 第一次提交改动 `src/auto_qb/webui/static/shared/tpl/*.html` 时(`:data-id` 这类
  纯属性也算)。此前十轮改过多次但都没提交, 所以这条闸门从未撞上模板分片。

- **判别**: 报错**全部**是 `Attribute "X" not allowed on element "…"`, 且 X 形如 `:key` /
  `v-if` / `@click` / `:href` —— 一眼就是 Vue 指令。同批提交里的真页面(`fx/showcase.html`)零
  error, 说明网本身没坏, 是送检对象选错了。判据: 分片目录 `static/shared/tpl/` 下的 `.html`
  由 `boot.js` 按 tpl-manifest 聚合成页面再注入, 从来不是独立 HTML 文档。

- **根因**: `check_html.py --vnu` 把"改动里的 `.html`"一律当 HTML 文档送 v.Nu, 而闸门的
  `<changed:**/*.html>` 会命中模板分片。v.Nu 按 HTML 语义校验属性表, Vue 指令不在其中 ⇒ 必然
  全红。这不是模板写坏了, 也不该靠改写模板绕开(把 `v-if` 改成 `<!-- -->` 之类等于毁掉功能)。

- **处置**: `check_html.py` 增加路径判据 `is_vue_template_fragment()`
  (`VUE_TPL_SEGMENTS = ("shared", "tpl")`), `run_vnu` 先摘掉这些分片并**打印摘掉了谁**(摘掉要
  可见, 不静默); 全被摘掉时直接 rc=0, 连 vnu.jar 都不下载、不依赖 JDK —— 纯模板改动不该被
  Java 环境卡住。L1+L2 结构判据对分片**照常跑**(闭合标签/标签名对模板片段同样成立)。
  ⚠ 判据只认路径, 不用"文件里出现 `v-` 就跳过" —— 那会把真正写坏属性名的页面一并放过。

- **守阵**: `tests/test_memory_bank.py::test_html_vnu_skips_vue_template_fragments` ——
  ① 分片认得出; ② 普通页面不被误判; ③ 全是分片时 `run_vnu(..., "java-does-not-exist") == 0`
  (用不存在的可执行名证明没走到子进程, 也就不会下载 jar)。红验: 判据改 `return False` →
  「tpl 分片未被认出 —— v.Nu 会整批误报」, 还原后绿。

- **同族变体 (R4 · 2026-11-03)**: 首次改到皮肤壳 `src/auto_qb/webui/static/<atlas|console|flux|prism>/index.html`
  (挂 R4 片段与 CSS link) —— 壳里内联的 `<div id="app">` 是 Vue 根模板, v.Nu 一次报 44 条
  全是 `Attribute "v-else/@click/:disabled" not allowed`, 同批 `fx/showcase.html` 零 error。
  处置: 同族路径判据 `is_webui_skin_shell()`(`WEBUI_SKIN_SHELLS` 四皮肤 + 只认
  `webui/static/<皮肤>/index.html`), 与 tpl 分片一起在 `run_vnu` 里摘除并打印摘掉了谁;
  L1+L2 照常跑。守阵: `tests/test_memory_bank_docs.py::test_html_vnu_skips_vue_template_fragments`
  追加 ① 壳认得出 ② 普通页面/`fx/showcase.html` 不误判 ③ tpl 分片不被误判成壳 ④ 全是
  Vue 承载面时 `run_vnu(..., "java-does-not-exist") == 0`。

- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
