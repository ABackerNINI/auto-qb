# webui 种子级标签/分类即时编辑

> 摘要: `/api/torrents/bulk` 扩 add_tags/remove_tags/set_category + 前端「标签/分类」即时编辑对话框(浮条/批量菜单/单种子菜单三处入口, 双 UI 成对); 全量 1638 passed + 1 skipped(TOTAL 92%), 双 UI 冒烟通过。
> 最后活动: 2026-09-26 17:00

## 已完成

- 功能一次落地全绿(11 文件): 后端 2(commands.py 4 参 lambda + extra / 路由透传 tags/category) + 前端 shared 3(app.js meta* 字段 / dialogs.js 对话框逻辑 / commands.js ctxMeta) + 模板 2(atlas/prism 三处入口 + metaOpen 对话框) + CSS 3(atlas 补 .opt-pill 与 .ico-tag / prism 两处) + 测试 1(+3 条)。
- 浏览器冒烟(harness 桩): 加/删标签、设分类、分类不一致提示、三种入口全通过(atlas + prism 截图确认)。
- 收尾: 档案 [tasks/26-09-26-webui-torrent-meta-edit](../tasks/26-09-26-webui-torrent-meta-edit.md) / baseline 顶部 / progress/implemented-webui / pitfalls/testing/stubs-sim.md(+1 新坑: harness 命令泵不执行 handler) / webui-static-contract(.opt-pill 两套都有) / README 批量操作行。**已入库 `d0c39bf`**。

## 正在进行

- 无(单会话完成)。

## 备注

- 真机走查待真实 qB: RESYNC 补刷新后行内标签/分类列更新与 qB 端标签定义可见性。
- 坑: 冒烟桩上验证写命令后不要用 /api/tags 之类读端点核对"后端状态变了" —— harness 命令泵只写回执不执行 handler(见 pitfalls/testing/stubs-sim.md)。
