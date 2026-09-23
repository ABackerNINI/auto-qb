# 26-09-20-webui-appjs-split — WEB UI `shared/app.js` 按域拆分为内核 + 15 个片段文件

**Status:** Completed (已入库 `afef7ce` 并推送 Gitee; GitHub 镜像允许滞后)
**Started:** 2026-09-20
**Owner:** 主线 (单会话连续实施)
**Plan doc:** [memory-bank/plans/26-09-20-0906-appjs-split-plan.html](../plans/26-09-20-0906-appjs-split-plan.html)
**Legacy-ID:** 无
**Summary:** 5045 行的 `shared/app.js`(Vue 3 CDN 单文件, 两套 UI 共用)按域拆成 **1001 行内核 + 15 个片段文件**: 293 个 methods 与 71 个 computed 按域搬走, `data()`/`watch`/生命周期与 HTTP·鉴权·轮询·视图切换留在内核。机制沿用仓库既有范式(`window.AQB_*` 全局 mixin, app.js 末尾 `app.mixin`), 不引入构建链。守阵 `test_frontend_static_bundle_health` 新增第 10 项「拆分接线」并把第 7/8/9 项改为按整包扫描; 单测 1055 passed 不变, 浏览器冒烟拆分前后均 54 项 0 失败。

## 原始请求

> 目前qb的webui大部分集中在一个app.js中, 需要拆分, 分析可行性, 列一个拆分计划, 如果可行, 按计划执行

用户随后拍板两个选型: ①**window 全局 mixin**(与 `config_editor.js` / `config_rules.js` 同范式, 而非 ES Modules) ②**methods + computed 都拆**(常量留在 app.js 顶部, 不搬)。

## 可行性结论(拆分前)

- **可拆, 且机制几乎无风险**: 痛点不在耦合而在体积 —— 5045 行里 `methods` 3720 行 / `computed` 660 行, 但它们是**同一个组件实例**上的平铺成员, 互相只通过 `this` 调用; 仓库**已有**跨文件 mixin 范式(`window.CONFIG_EDITOR` / `window.CONFIG_RULES` 由 app.js `app.mixin` 注入), 照抄即可, 方法体里的 `this` 语义不变 ⇒ 两套模板(prism/atlas)**零改动**。
- **不引入构建链**: 前端是 Vue 3 CDN + 无构建。选 ES Modules 需把两个 HTML 改成 `type="module"` 并让两套机制(config_editor 仍是全局)并存; 选 window 全局 mixin 只需加 `<script>` 标签, 且**加载顺序语义与现状一致**。故取后者。
- **真正的风险不在拆分本身, 在"静默失效"**: 漏挂 `<script>` 或漏 `app.mixin` ⇒ 整块功能凭空消失且控制台不报错; 两个片段同名成员 ⇒ Vue 后者覆盖前者、被盖者永不执行。故拆分与**新增守阵**必须同批落地(见下)。
- **静态守阵会先红**: `test_web.py` 里第 7/8/9 项(集成员取 hash / `STATE_RANK` 对齐 / 乐观 UI 撤下顺序)是 `if name == "app.js"` 才扫的, 拆完必然漏 —— 这不是功能坏了, 是"不变量跨了文件"。

## 思考过程与决策

- **先问"能不能拆", 再问"怎么拆"**: 看完构成后判定 —— 293 个 methods / 71 个 computed 只靠 `this` 互调, 没有模块级私有状态纠缠, 所以**耦合不是障碍, 体积才是**。这决定了拆分可以做成"纯搬运"(不改一行逻辑), 而不是需要重新设计依赖的重构 —— 后者在这个规模上风险不可控。
- **机制选型(用户拍板 ①)**: ES Modules 更"现代", 但要改两个 HTML 为 `type="module"`, 且 `config_editor.js` 仍是全局范式 ⇒ 两套机制并存。选 window 全局 mixin 的唯一代价是依赖仍隐式, 换来的是**加载顺序语义与现状完全一致** + 模板零改动。仓库一致性优先于技术先进性。
- **深度选型(用户拍板 ②)**: 常量不搬。287 行常量被上百处按裸名引用, 搬走就要全改命名空间访问 —— 收益(app.js 再少 287 行)远小于风险(漏改一处即运行时 `ReferenceError`)。而且顶层 `const` 本来就落在全局词法环境, 片段按裸名引用在运行时完全成立。
- **为什么必须同批改守阵**: 拆分是"纯搬运", 但**文件数从 1 变 16 这件事本身引入了新的失效形态**(漏挂 / 漏注入 / 重名), 且这三种都不报错。只搬代码不加守阵 = 把一类静默故障留给下一个人。
- **为什么守阵要改按整包扫**: 第 7/8/9 项钉的是"跨代码位置的不变量"(如 `_snapshotTruth` 必须早于 `reapplyPending`), 拆分后这两个调用可能落在不同文件。改成按 HTML 加载顺序拼接后扫描, 既覆盖单文件也覆盖跨文件, 且**加片段时自动跟随**(顺序取自 HTML, 不用维护第二份清单)。

## 实现计划

见 [memory-bank/plans/26-09-20-0906-appjs-split-plan.html](../plans/26-09-20-0906-appjs-split-plan.html): 可行性分析 → 域划分 → 两波执行与验证 → 守阵改动。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 可行性分析(构成 / 机制 / 风险) | ✅ |
| 2 | 写机械切分脚本(含覆盖断言 + 尾部注释归位) | ✅ |
| 3 | 波次一: 搬 293 个 methods | ✅ 5045 → 1629 |
| 4 | 守阵改造(第 7/8/9 项改整包 + 新增第 10 项接线) | ✅ |
| 5 | 守阵红验(漏注入 / 重名两种缺陷) | ✅ 均被精确报出 |
| 6 | 波次二: 搬 71 个 computed | ✅ 1629 → 1001 |
| 7 | 知识库回写(modules / testing / progress / activeContext) | ✅ |
| 8 | 计划文档 + 任务立档 + 索引重建 | ✅ |
| 9 | 提交与推送 | ✅ `afef7ce` → Gitee `develop` |

## 进度日志

- **2026-09-20**: 基线(1055 passed / 冒烟 54 项 0 失败) → 波次一 → 守阵改造 + 红验 → 波次二 → 全量验证(1055 passed / 冒烟 54 项 0 失败 / node --check 18 个文件全过) → 知识库回写 → 立档(本地提交 `ab82d6c`)。
- **2026-09-20 推送**: `git fetch` 发现 Gitee 已前进 3 个提交(`03ed9ed` / `5691c6f` / `f36a413`, 主循环 × WebUI 解耦 + 撤下 `via` 标记 + 知识库回写), 故 `git pull --rebase gitee develop`。**冲突 4 处**: `app.js`(整块"我的 1001 行 vs 上游 5045 行") + `activeContext.md` / `testing.md` / `tasks/_index.md`。
  - `app.js` 取**我的拆分版**, 再把上游 7 处语义改动按意图落到**方法已迁往的新文件**: `settleVia: null` 与 `_markCmdSettle` 的 `via=` 日志 → `commands.js`; `_settleFromTruth`「真值不一致时采纳真值」重写 → `commands.js`; 4 处 `settleVia = "pull"` → `commands.js` ×3(`act` / `bulkAct` / `actTorrent`) + `shows.js` ×1(`actEpisode`)。判据同 pitfalls「rebase 冲突落在已被迁走的方法上」。
  - 落点正确性**由冒烟背书**: 合并后再跑, `[perf]` 打出 `via=pull`(埋点在运行时确实走了新代码路径, 不只是文本搬对), 54 项 0 失败; 全量 **1057 passed**(上游新增 2 项, 我的改动未增减用例)。
  - 解冲突后重跑 `gen_tasks_index.py`, 两个档案条目(`26-09-20-webui-decoupling` / `26-09-20-webui-appjs-split`)并列 Completed 段。
  - 变基前整份备份 `.git`(58M → `.workbuddy-ai/tmp/git-backup-before-rebase`); 提交前后均核对 `HEAD == refs/heads/develop`。

## 决策与实施

1. **机械切分而非手改**: 写一次性脚本按行区间搬运(`.workbuddy-ai/tmp/split_appjs.py`), 逐块原文拷贝、不重新缩进、不改一行代码; 脚本自带三道断言(成员区间首尾相接无空洞 / 每个成员有且仅有一个归属 / 搬运前后行数守恒 3722)。成员**尾部注释**(描述的是下一个成员)在切分前挪到下一个成员头上, 避免注释跟着上一个文件走。
2. **两波执行, 每波独立验证**: 波次一搬 methods(5045 → 1629 行), 波次二搬 computed(→ 1001 行)。每波跑 `node --check` + 守阵 + 全量 pytest + 真浏览器冒烟。
3. **域划分**(`window.AQB_*`): ui_feedback(toast/确认框/菜单定位) / filters / columns(列宽列序列菜单 + 行窗口化) / format / decorate(状态聚合·共同标签分类) / hr / sort / menu(表头菜单·右键·展开) / commands(命令投递 + 乐观 UI) / add_torrent / selection / shows / delete_flow / drawer / dialogs(统计·管理·日志·限速·历史)。
4. **内核保留**: `api` / `_request` / `_logout` / `bootstrap` / `saveToken` / `retryAuth` / 轮询四件套 / `refresh` / 搜索 / `goView` `setViewMode`, 以及 `data()` / `watch` / `created` / `updated` / `unmounted`。
5. **常量不搬**: `TABLE_COLUMNS` / `MIN_COL_PX` / `STATE_RANK` / `ROW_WIN_*` 等仍单点在 app.js 顶部, 片段按**裸名**引用 —— 顶层 `const` 在经典脚本里落在全局词法环境, 方法体运行时才求值, 与加载顺序无关。**已写进片段文件头注释**(别再搬, 一搬就是上百处改名)。

## 守阵改动(tests/test_web.py)

- 第 7/8/9 项: 由「只扫 app.js」改为按 **app.js 整包**扫描 —— 顺序取自 prism/index.html 的 `<script>` 加载顺序(`_app_bundle_files()`), 拼接后跑 `_scan_episode_member_hashes` / `_scan_state_rank` / `_scan_pending_settle`。
- 新增第 10 项 `_scan_mixin_wiring`: ①`shared/` 下每个非 vendor 的 js 必须被 prism/index.html 引用 ②每个 `window.X` 必须在 app.js 里 `app.mixin(window.X)`(`ce-field` 走 `app.component`, 已计入) ③跨文件 methods/computed 成员不得重名。
- **红验**(故意注入两种缺陷, 均被精确报出): 删掉 `app.mixin(window.AQB_HR);` → "定义了 window.AQB_HR 但 app.js 没有 app.mixin(片段漏注入)"; 在 hr.js 复制一个 `kindIcon` → "methods.kindIcon 与 shared/decorate.js 重名 —— Vue mixin 后者覆盖前者"。

## 验证

| 项 | 拆分前 | 波次一后 | 波次二后 |
|---|---|---|---|
| `uv run pytest tests -q` | 1055 passed | 1055 passed | 1055 passed |
| 浏览器冒烟(3000 种子, prism+atlas) | 54 项 / 失败 0 | 54 项 / 失败 0 | 54 项 / 失败 0 |
| `node --check` 全部前端 js | — | 18/18 通过 | 18/18 通过 |
| app.js 行数 | 5045 | 1629 | **1001** |

## 遗留 / 注意

- **已提交并推送**: `afef7ce` → Gitee `develop`(GitHub 镜像允许滞后)。
- 发现一处**既有文档漂移**: `testing.md` 顶部基线写 1054, 本机实测恒为 1055(本轮改动前后各测一次均如此)。按范围守恒未在本轮改基线, 只在 testing.md 里加注说明。
- 后续若再加片段文件: ①写 `window.AQB_<域>` ②两个 index.html 都加 `<script>` 且排在 app.js 前 ③app.js 加 `app.mixin` —— 漏任何一步守阵会红。
