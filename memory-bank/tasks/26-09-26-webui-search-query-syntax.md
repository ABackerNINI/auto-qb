# 26-09-26-webui-search-query-syntax — WEBUI 搜索强化(查询语法调研 → 实施)

**Status:** Done
**Added:** 2026-09-26
**Updated:** 2026-09-28
**Summary:** WEBUI 搜索现状为「整句归一后连续子串匹配」(views.py `search_torrents`),「恶女 10」搜不到单文件发布物(两词不连续必不命中)且无排除能力。调研六系成熟方案收敛出 websearch 公共核心(**词 AND + `-排除` + `"短语"` + 宽容解析**),用户拍板**行级语义**后实施:后端 `_parse_query` 纯函数 + `search_torrents` 行级匹配(候选行=种子名或单个文件名,行通过 ⇔ 含全部正词且无负词,任一行通过即命中;负词按行作废不误杀合集包;仅负词返回空 + `negative_only`),前端两主题 placeholder 提示语法 + 5 处空态「只有排除词」提示。+6 测试,全量 **1679 passed + 1 skipped**(TOTAL 91%)。**真机回访(2026-09-26 晚)**用户报两缺口:①种子页 `filteredTorrents` 仍是旧整句子串客户端过滤(该视图词 AND/`-排除` 全失效)→ 升级为同一语法(filters.js 三函数单点,hr.js 旧版删除,与 views.py 行为级对账守阵);②清除钮有焦点点不动(focus 宽度过渡移出光标)→ 两主题 `@mousedown.prevent`。+1 守阵,全量 **1680 passed + 1 skipped**(TOTAL 91%,基线 26-09-26-2121)。**随本提交入库。→ 26-09-26 晚~27 四轮追加**: 季包"cat 12"修复 → **单点化**(匹配收敛服务端 `search_torrents`, 三页消费 searchHits, 前端匹配清零+反漂移守阵)→ **负词种子级定案**(「cat and -11」「-mteam」两轮泄漏收口, 基线 26-09-27-0045)→ **正词逐词跨行 AND 定案**(「minions mteam」「delta 03」两轮跨字段漏配收口, 26-09-26「多词须同行」作废, 基线 26-09-27-0138, 全量 1685 passed + 1 skipped / TOTAL 91%)。**26-09-28 语法帮助入口**(框内幽灵「?」+ 锚定浮卡, 方案A)已随 `9dc7a1b` 入库; 「?」无清空钮右移补位微调随本提交入库。
**Topics:** webui-search-query-syntax
**Refs:** memory-bank/reports/26-09-26-1918-report-webui-search-query-syntax.html, memory-bank/plans/26-09-28-0201-plan-search-help-button-3-proposals.html

## 原始请求

> WEBUI搜索"恶女 10"无法匹配"[虽然我不是完美恶女～雏宫蝶鼠替换传～].Futsutsuka.na.Akujo.dewa.Gozaimasu.ga.Suuguu.Chouso.Torikae.Den.2026.S01E10.1080p.CR.WEB-DL.H264.AAC-UBWEB.mkv"
>
> (第二问)强化搜索功能, 比如支持"-DV"排除"DV"词, 等, 调研常用成熟的解决方案

第一问已答(根因定位 + 实测复现,未改代码);第二问 = 本档案,产出调研报告。

## 思考过程与决策

- **D1 语法层采纳 websearch 公共核心**(词 AND / `-` 排除 / `"短语"`):跨六系压倒性惯例(Google/GitHub/PG websearch_to_tsquery/Meilisearch/Typesense/Everything 高度一致),用户零学习成本;`-` 排除正是用户点名的能力。PG `websearch_to_tsquery`、Typesense、Meilisearch 三条语法细节本轮经官方文档网络核实,其余为公认口径。
- **D2 解析器必须宽容、永不报错**(F3):ES `simple_query_string` 的存在动机;孤立 `-` 忽略、未闭合引号收至行尾、语法错误部分按字面降级。
- **D3 匹配语义推荐行级**:候选行 = 归一种子名或单个归一文件名(`files_q` 既有缓存);行通过 ⇔ 含全部正词/短语且无负词;种子命中 ⇔ 任一行通过。与单文件 scene 命名现实和前端 placeholder「搜索种子名或文件名…」承诺的模型一致;负词不误杀合集包(行级 DV 行作废、非 DV 行仍可命中)。种子级(跨行 AND + 整种子负词排除)召回更高但跨文件连词不可预测、负词误杀合集包 —— 已在报告 §5.2 给三行对比表,**待拍板**。
- **D4 保留子串语义、不为 CJK 引入分词**(F4):成熟方案全为词元匹配且 CJK 都要额外 machinery(FTS5 trigram ≥3 字符限制等);本项目规模下「归一+子串」即 CJK 词元匹配的务实近似。
- **D5 兼容性论证**:新语义是旧语义严格超集 —— 单词不变、多词连续同序不变、多词非连续从恒不中变可中;无配置/state/依赖变化,不触发 validate_config 守卫面。
- **D6 仅负词查询返回空 + 前端提示**(与 Google 一致);短数字词子串误命中(`10`→`1080p`/`2026`)现状已有且新语义不放大,维持。
- **D7 后续扩展留口不动核心**:`site:`/`tag:` 限定符(结果项字段已齐)、OR/括号、前缀通配 —— 均为解析器增量。

## 实现计划

1. `src/auto_qb/webui/views.py`:新增 `_parse_query(q) -> (positive, negative)` 纯函数(原始查询切 token → 词首 `-` 判负 → 逐词 `_search_norm`;`"…"` 短语整段归一为连续子串);重写 `search_torrents` 两处匹配段(名/文件)为行级判定;docstring 更新口径。
2. `tests/test_web.py`:解析器 ~5 条(引号/负词/孤立-/未闭合引号/CJK)+ 语义 ~5 条(行级 AND/负词/短语/仅负词空结果)+ 回归「恶女 10」;docstring「## 测试计划」同步。
3. 前端:atlas / prism 两主题 placeholder 文案成对(提示 空格=且、-排除、"短语");strip-note 不动。
4. 前置:行级 vs 种子级拍板(报告 §5.2);拍板后出计划文档(`plans/`,delivery-artifact skill)或直接实施(小改)。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 根因定位(「恶女 10」失配) | Done | 整句连续子串口径,两词不连续必不中;实测复现,未改代码 |
| 六系成熟方案调研 | Done | 报告 26-09-26-1918;PG/Typesense/Meili 三条经网络核实 |
| 推荐设计定稿(语法+行级语义) | Done | 报告 §5;严格超集论证见 §5.3 |
| 行级 vs 种子级拍板 | Done | 用户拍板**行级**(2026-09-26) |
| 实施(后端+测试+前端) | Done | `_parse_query` + `search_torrents` 行级;+6 测试全绿;两主题 placeholder/空态成对 |
| 全量闸门 | Done | 1679 passed + 1 skipped / 0 failed,TOTAL 91%(基线切片 26-09-26-2030) |
| 真机走查 | In Progress | 用户真机回访(26-09-26 晚)报两缺口(见下), 已修复待复测: 双主题实测「恶女 10」「恶女 10 -DV」搜索与空态提示 |
| 真机回访修复(种子页客户端补齐 + 清除钮) | Done | 见进度日志 2026-09-26 (真机回访轮); +1 守阵, 全量 1680 passed + 1 skipped(基线 26-09-26-2121) |
| 季包修复 + 单点化 + 负词种子级(26-09-26 晚~27, 并发 clone 会话) | Done | 已随 `8e93023`/`f187904` 入库; 细节见 activeContext 切片 + 基线 26-09-27-0045(本档案该两轮未及时追加, 此行补记) |
| 正词逐词跨行 AND 定案(26-09-27) | Done | 「minions mteam」分轨中间态 → 用户实测「delta 03」推翻文件行隔离 ⇒ 逐词跨行; 守阵改名 `cross_row_and` + 5 断言翻转; 基线 26-09-27-0138 |
| 提交入库 | In Progress | 随本次提交入库(26-09-27; 含上两轮全部改动 + 收尾回写) |
| 语法帮助入口(浮卡方案A, 26-09-28) | Done | 3 版提案(计划 26-09-28-0201)→ 用户拍板 A + 占位符简化; 详见进度日志 2026-09-28 |
| 「?」无清空钮右移补位(26-09-28) | Done | 空框 6px 贴缘 / 有词 27px 让位(与 x 间隙 1px); 守阵同步; 基线 26-09-28-0546 |

## 进度日志

- **2026-09-26 (调研轮)** — 同步远端一致(b5e78a4)后开工:①复现根因(归一后两词不连续,整句必不中;拆词 AND 即命中)②网络核实 PG `websearch_to_tsquery`(隐式 AND/`-`排除/永不抛错)、Typesense(`-` 算子)、Meilisearch(负词)③读码补齐项目侧事实(views.py / app.js / 两主题 index.html / test_web.py 既有搜索测试)④落报告 `26-09-26-1918-report-webui-search-query-syntax.html`(六系对比 + 5 条公共性事实 + 推荐设计 + 改动面预估),初稿两处笔误(阿拉伯字符混入 / `<trigram>` 被当标签)当场修正。未改任何源码/配置/测试。**未提交 —— 等用户显式指令。**
- **2026-09-26 (收尾闸门)** — 三次全量 + 守卫定向复跑排障:①新制品未登记索引 8 红 → `kb.index` 后 6 绿;②我方 doc-refs 写成文件相对被认领链守阵判"目标不存在" → 改**仓库根相对**后绿(坑已入 `pitfalls/kb/refs-rename.md`);③activeContext 41>40 超 cap → 最老切片 `26-09-19-0000-docs-plan-review-wrapup` 蒸馏进 `progress/roadmap.md`(遗留项本就被 Open issue 26-09-19-2122 追踪)后删除;④终态红经查全部归属同 clone 并发会话在途工作,未代修。
- **2026-09-26 (合流全绿)** — 用户告知并发会话已停止且改动已提交:fetch 后本地 HEAD == gitee develop == `cd7c3c9`(db0993c fs 长路径修复 / 7bea270 基线 / cd7c3c9 档案更新);其以「档案不声明 Refs」解认领链,`kb.index` 后 doc 守阵 **34 绿**,全量 **1673 passed + 1 skipped / 0 failed**(16.9s,TOTAL 91%),最终基线切片 `26-09-26-2002-webui-search-query-syntax`。⚠ 并发会话的任务档案 `tasks/26-09-26-webui-long-path-open.md` **未入库**(untracked,磁盘在故本机绿、换 clone 即消失)——已记入基线切片,待下次提交随车。本轮未提交,等用户显式指令。
- **2026-09-26 (实施落地)** — 用户拍板**行级**并令按推荐实施。①`views.py`:`_parse_query` 纯函数(词法在**原始查询**上判定:词首 `-`+非空白=排除、`"…"` 短语整段归一连续子串、孤立 `-`/未闭合引号/纯标点/`--dv`/词中引号宽容降级)+ `search_torrents` 行级重写(`_row_passes`: 行含全部正词且无负词;种子命中 ⇔ 名字行或任一 files_q 行通过;仅负词/空查询返回空 + `negative_only` 标记不投递构建)。②测试 +6(词法/行级 AND 钉跨行不命中/负词按行作废钉合集包不误杀/短语词序敏感/报障回归「恶女 10」/仅负词空态),「测试计划」docstring 同步;首跑 2 红均为**测试预期写错**非实现错:`dragon cat` 里 HB 的下划线文件行也同含两词应命中、负词用例顺序是名字轮先于文件轮([HC,HB]/[HA,HC,HB]),修正后绿;另按新语义更新旧断言 `dragon cat`(旧口径序敏感判空 → 行级判命中,注释说明口径变更)。③前端:`searchNegativeOnly` 状态单点(app.js 声明/reset/doSearch 三处)+ 两主题 placeholder 提示语法(引号用全角,避免 HTML 属性转义)+ 5 处空态「只有排除词」提示(atlas/prism 3+3 处成对)。④闸门:dev.fmt → test_web 169 绿 → 全量 **1679 passed + 1 skipped / 0 failed**(19.0s,TOTAL 91%,views.py 97%,新增路径全覆盖)。⑤回写:progress/implemented-webui 置顶新条目(触碰 evergreen cap 10,742>10,000 → 按既有轮转机制把 2026-09-15/18/19 四条最老整条外迁 `implemented-webui-history.md` 冷库,主文件原位并入指针行,回落 7,949 字符);README/docs 无搜索口径描述不需改。**未提交 —— 等用户显式指令;真机走查待真实 qB。**
- **2026-09-26 (真机回访轮)** — 用户真机报两缺口, 均定位修复:①**种子页搜索整句失配**:`filteredTorrents`(viewMode=torrents 平铺视图)的搜索是**客户端**过滤(filters.js, 不依赖服务端 searchHits —— 站点/分类/标签/路径字段服务端不搜), 上轮只升级了服务端口径, 该视图仍是旧「整句 includes」(「恶女 10」要求名字含连续子串"恶女 10"、`-DV` 要求字面含"-dv") ⇒ 词 AND 与排除在该视图全失效, 分组/追剧视图(走服务端)正常 —— 与报障症状完全吻合。修复: filters.js 新增 `_parseSearchQuery`/`_searchNorm`(服务端同名口径的客户端单点)+ `_torrentTextMatch` 重写为行级语义(名称/站点/分类/路径/每个标签各为一候选行, 行含全部正词且无负词; 仅负词恒 false 与 negative_only 口径一致; `searching` 守卫区分空查询), hr.js 旧整句版删除(防双实现漂移)。守阵 `test_frontend_search_syntax_wiring`: 静态四段(清除钮成对/单点在 filters.js/归一 Unicode 词字符/接线守卫)+ 行为段(vm 沙箱真跑 filters.js 与 views.py `_parse_query`/`_search_norm` **逐项对账**, 无 node 静默跳过) —— **对账当场抓到 JS 首版归一保留 `_` 而 Python `[\W_]` 折叠 `_` 的真实漂移**(手工用例未覆盖, 守阵价值实证), 修为 `[^\p{L}\p{N}]+/gu`; `\W` 会折叠掉 CJK 是第二类雷(JS `\w` 仅 ASCII), 一并钉死。②**清除钮焦点态失灵**: input `:focus` 宽度 240→300px 过渡 + 清除钮绝对定位锚右沿 ⇒ 有焦点时按下瞬间失焦收窄, 按钮移出光标, click 落空(无焦点宽度不变故正常, 与症状吻合) ⇒ 两主题清除钮加 `@mousedown.prevent`(按下不夺焦)。坑回写 `pitfalls/web-ui/search-views.md` 追加两条(清除钮 focus 宽度过渡 / JS·Python 归一行为级对账)。③闸门: dev.fmt → 新守阵绿 → 全量 **1680 passed + 1 skipped / 0 failed**(19.4s, TOTAL 91%, views.py 97%), 基线切片 26-09-26-2121。**随本提交入库。**
- **2026-09-27 (正词口径定案轮)** — 两轮报障驱动正词边界演进, 当日两改定案:①**「minions mteam」漏配**: 行级「多词须同行」下 `minions` 只在名字行、`mteam` 只在站点/标签行 ⇒ 漏配(单搜 `mteam` 正常)。第一版按行性质**分轨**(全称行=名字/站点/分类/路径/标签 逐词跨行; 文件行保持整行 AND, 保 26-09-26「gamma delta」钉死边界)。②用户再实测「包名 Gamma.Delta + 集文件 Gamma.E01-E03 搜 **delta 03**」仍漏配(delta 在名字行、03 只在集文件行)—— 分轨的召回代价正中真实用法, **知情拍板推翻 26-09-26 文件行隔离**: 正词定案**逐词跨行 AND**(每词命中任一候选行即可、行可不同), 季包吸词代价(附加词可被包内任一文件名吸收, 「gamma delta」翻转为命中)接受。实施: `views.py` 匹配两分支(全称行全覆盖 → results/by=首个含正词全称行; 需文件行补词 → file 兜底排后)+ 删无引用 `_row_passes` + docstring 口径重写; `test_search_torrents_row_level_and` → `cross_row_and` 重写(报障原型夹具 + 5 条「跨行不命中」断言翻转 + AND 不退化 OR 守卫), 模块头测试计划 + facet/phrase/季包注释等 6 处措辞同步; 前端 app.js/filters.js/shows.js 3 处「行级裁决」注释改「匹配裁决」(纯注释)。③开工同步: 远端前移 `c36fbf5`(仅 memory-bank, 零重叠)stash→ff→pop 快进。④闸门: yapf 清 → 全量 **1685 passed + 1 skipped / 0 failed**(19.7s, TOTAL 91%, views.py 97%), 基线切片 26-09-27-0138。回写: 本档案 + activeContext 切片 + pitfalls/web-ui/search-views.md(三处收敛条目口径更新)。**随本次提交入库。**
- **2026-09-28 (语法帮助入口轮)** — 用户令给搜索框加「高级用法」帮助按钮, 先出 3 版模板供挑选:①产出交互式提案 `plans/26-09-28-0201-plan-search-help-button-3-proposals.html`(A 框内幽灵「?」+锚定浮卡 / B 框外「语法」chip+下拉 / C 圆「?」+mini 弹窗, 含 7 主题令牌走查与文案全稿), 用户**拍板 A** 并令占位符简化为「搜索种子或文件名...」。②实施: `topbar.html`(「?」钮 + 浮卡模板 + `ref="searchInput"`); 共用样式入 `shared/console_hub.css`(三 UI 同载层, mono 用 `var(--font-mono, 内联栈)` longhand —— 星图无该令牌, shorthand 遇未定义令牌整条失效), 各皮肤只留差异(atlas pill 钮圆)与 input 右内边距 52px; 状态 `searchHelpOpen` + `view.js` `toggleSearchHelp`/`searchHelpFill`(回填即搜 `doSearch` + 焦点还输入框), 三条收起路径(点空白/Esc 退栈挂 lifecycle 既有链 + goView/openSettings 导航收起)。③守阵 `test_frontend_search_help_wiring`(模板/state/方法/三收起路径/CSS 成对与 52px 留位)。④实机验证: `dev.harness` 桩 + Playwright 驱动三套 UI 全交互项通过, 示例 `"web dl"` 经真实后端命中 35/60 辅种。⑤索引收口: 新计划文档触 `_doc-map.md` 撞 index-auto cap(12,284>12,200) → 按 pitfalls/kb/cap-counting.md「两个出口」处置①改**渲染口径**(计划/报告展示戳截到日期精度, 与档案行一致, 全表省 ~245 字符, 零信息损失), 本档案追加不新建(查重命中)。⑥闸门: 全量 **1813 passed + 1 skipped / 0 failed**(TOTAL 91%), 基线 26-09-28-0245。**未提交 —— 等用户显式指令。**
- **2026-09-28 (「?」补位微调轮)** — 用户令: 无「x」清除钮时「?」自动靠右。`searchQuery` 为空 ⇔ 清除钮不渲染(同源条件), 故 `topbar.html` 帮助钮加 `'no-clear': !searchQuery` 条件类; 共用层 `console_hub.css` 新增 `.search-help.no-clear { right: 6px }`(即清除钮的位, 有词时保持 27px 让位) + `.search-help` transition 补 `right`(滑动与聚焦展宽同拍); 守阵 `test_frontend_search_help_wiring` 同步两条断言(模板绑定 + 共用层规则)防回退。冒烟: 自建桩挂真静态 UI(no-cache) + Playwright 量测三态 —— 空框距右缘 6px / 有词 27px 且与 x 间隙 1px / 点 x 清空回 6px, 星图+棱镜双皮目检通过。⚠ 自建桩还差免鉴权端点才能进主界面(boot 读 `/api/config/public` 的 `web.skip_local_verify`), 已续记 `pitfalls/web-ui/template-render.md`; 日常冒烟优先 `dev.harness`(桩配方带齐)。闸门: dev.fmt → 全量 **1818 passed + 3 skipped / 0 failed**(20.0s, TOTAL 91%), 基线 26-09-28-0546。**随本提交入库。**
