# 26-09-26-webui-torrent-meta-edit — WEB UI 种子级标签/分类即时编辑（添加/删除标签 + 设置分类）

**Status:** Done
**Added:** 2026-09-26
**Updated:** 2026-09-26
**Summary:** webui 补上"对种子加/删标签、设置分类"的用户能力：`/api/torrents/bulk` 动作表扩 `add_tags`/`remove_tags`/`set_category`（载荷加 `tags`/`category` 键，提供才透传，空串分类=清除），前端新增「标签/分类」即时编辑对话框（shared/dialogs.js）——目标集合打开时锁定，全部标签以 `.opt-pill` 切换胶囊展示（亮=选中种子共同拥有，点击即投递一条 bulk 命令），分类 combobox 支持现有分类选择与自由输入（新分类/新标签走"先建后设"，创建失败不影响后续设置，主循环 FIFO 保证顺序）。三处入口（批量浮条按钮 / 批量右键菜单 / 单种子右键菜单）双 UI 成对。+3 测试，全量 **1638 passed + 1 skipped**（TOTAL 92%）。双 UI 浏览器冒烟通过（atlas + prism）。
**Topics:** webui-torrent-meta-edit

## 原始请求

> webui缺少添加/删除标签功能, 缺少设置分类功能

（陈述式功能缺口 = 隐性实现请求；单会话一次落地，未经计划模式。）

## 思考过程与决策

- **D1 写路径扩 bulk 而非新端点/新命令**：bulk 已有"组键展开 + 快照缺失过滤 + 聚合回执"全套语义，且 `bulk_torrents` 本就在 `RESYNC_COMMANDS`（命令消费后主循环补一次完整刷新，前端立刻看到新 tags/category）与 `DEFERRED_RECEIPT_COMMANDS`（handler 聚合写回执）——新动作自动继承，零白名单改动。QbApi 侧 `torrents_add_tags/remove_tags/set_category` 早已就绪且同步 store 快照，只缺"webui 命令层没人调"。
- **D2 `_BULK_ACTIONS` lambda 签名统一 4 参 `(api, hashes, delete_files, extra)`**：`extra = {tags, category}`，既有 4 动作忽略它——避免逐动作特判；`extra` 在入口按动作校验后构造（add_tags/remove_tags 需非空 tags，set_category 的 category 允许空串=qB"清除分类"语义，None/缺键才 error）。
- **D3 路由层"提供才透传"**（与组键模式 DLG-02 同约定）：tags 非空才入 payload；category 按键存在性入（空串必须保留——清除分类的语义靠它承载）。纯 pause 调用的队列载荷与历史形态完全一致，不碰既有断言。
- **D4 前端即时模式（照 qB 官方 WebUI 交互）**：不设"应用/取消"，点胶囊即投递独立命令独立回执，对话框只是把候选摊开。目标集合在打开时刻锁定（遮罩下选择不会变）；共同标签取**交集**但不复用 `decorate._commonTags`——那条会过滤"与站点同名"的标签（组级**展示**口径），编辑场景必须能看到并移除这类标签，故在 dialogs.js 另写不过滤的交集。
- **D5 新分类/新标签"先建后设"，失败不阻断**：create 与 set 按队列 FIFO 在主循环顺序执行，create 失败（典型=已存在的 409）不影响后续 set/add——真正决定成败的是 set/add 的回执。不赌 qB 版本行为（addTags 是否自动建标签随版本有差异）。
- **D6 不做乐观贴片**：标签/分类不在 `_optimisticPatch` 白名单（那是 pause/resume 的 kind 预测）；行内新值靠 bulk 的 RESYNC 补刷新落下来（~1-2s），对话框内的即时确认走本地 `metaCommonTags/metaCat` 状态更新，观感即时。
- **D7 `.opt-pill` 首次引入 atlas**：static-contract 口径"勾选项一律 .opt-pill 切换胶囊"，但该组件此前只在 prism 有定义——atlas 照 prism/components.css 同源搬入（令牌两套同值），供标签胶囊用。
- **菜单分层（CTX-06）**：单种子菜单的「标签/分类…」放一级（与限速/移动/重命名同频同级）；批量菜单放"重新校验"与"批量删除"之间（标签/分类对 N 个目标有明确语义，不违反"批量菜单不放单目标项"红线）。

## 实现计划

1. 后端 `webui/commands.py`：`_BULK_ACTIONS` 4 参签名 + 3 个新动作；`_cmd_bulk_torrents` 加 `tags`/`category` 参数与校验；未知动作文案补新动作名。
2. 后端 `webui/server/routes/torrent_cmds.py`：`/api/torrents/bulk` 透传 tags/category（提供才入 payload）。
3. 前端 shared：`app.js` data 加 `meta*` 状态字段 + Esc 栈 + 登出重置；`dialogs.js` 加 openMetaDialog/closeMeta/_metaBulk/metaToggleTag/metaAddNewTags/metaSetCategory/combobox 系列；`commands.js` 加 `ctxMeta()`（先收菜单再 openMetaDialog(null)）。
4. 前端模板双 UI 成对：批量浮条按钮、批量菜单项、单种子菜单项、`metaOpen` 对话框（mgr 标签管理对话框之后）；CSS 两套加 `.meta-dialog/.meta-targets/.meta-tags`，atlas 补 `.opt-pill` 全套与 `.ico-tag` 语义色（indigo）。
5. 测试 +3（API 入队 / handler 执行 / 静态守阵）+「## 测试计划」docstring 同步。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| bulk 动作表扩展 + 路由透传 | Done | 4 参 lambda + extra；tags/category 提供才透传，空串分类保留 |
| 前端 shared（app.js/dialogs.js/commands.js） | Done | 打开时锁定目标 + 拉候选；即时投递；先建后设 |
| 双 UI 模板 + CSS 成对 | Done | 三处入口 + 对话框；atlas 补 .opt-pill 与 .ico-tag |
| 测试（+3）与 docstring 同步 | Done | 见 baseline 顶部 |
| 浏览器冒烟（双 UI） | Done | harness 桩：浮条/两处右键菜单入口、加/删标签、设分类、分类不一致提示全通过 |
| 真机走查 | Pending | 需真实 qB：真值落行（RESYNC 补刷新后行内标签/分类列更新）与 qB 端标签定义可见性 |

## 进度日志

- **2026-09-26 (一次落地全绿)** — 开工同步快进 1 笔（远端名 origin 指 Gitee）→ Explore 摸清 webui 结构（命令链/右键菜单/combobox/mgr 对话框四个模式全部就位）→ 实施 11 文件（后端 2 + 前端 shared 3 + 模板 2 + CSS 3 + 测试 1）。
  ① test.quick 1638 passed + 1 skipped 一次全绿（含新增 3 条）。
  ② 浏览器冒烟（ui_harness 桩 60 种子/20 组 + 内置浏览器）：atlas——批量浮条「标签/分类」→ 对话框（分类不一致提示/空标签态正确）→ 输入新标签添加（toast + 胶囊亮态）→ 点胶囊移除（灭态）→ 输入新分类回车（先建后设，提示消失）；单种子右键与批量右键菜单均出现「标签/分类…」且打开时目标数正确（1/2）；prism——浮条入口 + 对话框渲染截图确认。
  ③ 冒烟中一度误判：`/api/tags` 冒烟后为空 —— 实为 harness 命令泵**只写回执不执行 handler**（设计如此），非功能缺陷；已按"替身盲区"记入 pitfalls/testing/stubs-sim.md。
  ④ test.full **1638 passed + 1 skipped, TOTAL 92%**（11008 语句 / 787 未覆盖 / 3654 分支 / 330 partial）；dev.fmt 已跑。
  ⑤ 未提交 —— 等用户显式指令。
