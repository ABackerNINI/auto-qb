# 单 CSS 文件 700 行体量上限(atlas components.css 已卡满)

> 摘要: 单 CSS 文件 700 行体量上限(atlas components.css 已卡满)
> 触发: 追加 CSS 规则, 三套皮肤成对改, test_frontend_template_split_wiring 红

### 追加共享 CSS 规则前先量行数 —— atlas `css/components.css` 恰好 700 行零余量, 往里加一行就红

- **触发**: 往 atlas / console 的四个 CSS 文件(`style.css` / `css/components.css` / `css/views.css` / `css/dialogs.css`)追加规则, 特别是「三套皮肤成对同改」类任务 —— 注意力全在「三份文本一致」上, 不会想到其中一份已经顶到天花板。典型做法是把新规则就近贴在语义最近的基线规则旁, 而那常常正是 `components.css`。
- **判别**: `tests/test_webui_static_skins.py::test_frontend_template_split_wiring` 报 `AssertionError: 模板分片接线问题: <file> NNN 行, 超 700 行单 CSS 体量上限`。两点误导: ①看着像「模板接线」问题, 根因只是一个文件的行数; ②该守阵只检查 atlas / console(prism 不在检查面), 常常只有一份皮肤红 —— 别误判成「prism 漏改」。
- **处置**: ①先量四份文件行数找余量(`wc -l < <skin>/css/*.css`); ②把新规则挪到本套仍有余量的那个文件 —— 落地时的选择是: 框级 `.modal.tone-*` / `.modal.strip` 与行级 `.is-*` 三组规则一起进 `css/views.css`, 而不是各贴各的基线; ③不要为压行数牺牲注释; 若确实无处安放, 应拆分文件而不是删注释。
- **守阵**: `tests/test_webui_static_skins.py::test_frontend_template_split_wiring`(同时钉三件事: 四文件 ≤700 行、link 顺序、tpl-manifest 逐项相等)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)

> 该守阵同时钉三件事, 报红时先分辨是哪条分支: 行数超限的措辞是 `<file> NNN 行, 超 700 行`; 顺序问题的措辞是 `CSS 链接顺序漂移`。
