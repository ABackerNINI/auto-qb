# 3968 passed + 10 skipped —— 前端列表外壳两件套单点(issue 26-10-20-2231)

> 摘要: 前端列表外壳两件套单点(issue 26-10-20-2231)
> 基线时间: 2026-10-21 04:26
**Refs:** memory-bank/issues/26-10-20-2231-refactor-fe-tpl-list-row-empty-dup.html

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 实测输出:

```text
TOTAL                                                20467     93   7012     93    99%
3968 passed, 10 skipped in 39.06s
```

与上一切片 `26-10-21-0323-dup-code-audit.md`(3967 passed / 同样 20467 语句 / 93·93 缺口)相比:
**passed +1** = 本轮新增的那条守阵; 语句与分支分母、缺口均未变 —— 本轮只改模板分片与前端
JS 常量, 不新增 Python 语句, 也无新增可覆盖行。

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 99`)照过(99%)。
- 本轮新增 1 条用例: `tests/test_webui_static_dom_page.py::test_frontend_list_row_pad_and_empty_single_point`
  (静态形态 + 活性探针 + node 语义电池 15 项); 单跑 1 passed。
- 前端静态三件套一起跑(`skins` / `dom_page` / `dom_panel`): **103 passed**。
- **行为电池**: 三张列表 × 五种空态场景 = 15 项, 收敛时刻意保留的分歧逐条钉死 ——
  ①辅种页搜索分支说「种子」而面筛分支说 `l10nGroup`(服务端匹配裁决落在成员不在组);
  ②追剧页全空是「暂无剧集可展示」(不是「暂无剧集」); ③种子页补上的「正在构建文件索引…」分支
  (收敛前该页缺这一支, 索引构建期把中间态说成了「无匹配种子」)。
- 红验(守阵活性, **四类突变全部判红**, 均以精确反向编辑还原, 还原后逐字节比对原文件):
  ①把某张列表的空态换回手写 `<div class="empty">` ⇒ 红, 报「列表外壳两件套回潮: tpl/torrents.html
  手写了 1 处空态块」; ②抹掉追剧页「暂无剧集可展示」的分歧 ⇒ 红, 报「列表空态文案行为漂移:
  plain/showsEmptyText = "暂无剧集"(应为 "暂无剧集可展示")」; ③删掉种子页一个 `<aq-row-pad>` 调用点
  ⇒ 红, 报「列表外的 \<aq-row-pad\> 调用点只剩 7 处(下限 8)」; ④把带参单点 `listEmptyText` 从
  `methods` 挪进 `computed` ⇒ 红(Vue 3 computed 无参, 带参会 TypeError ⇒ 空态整块白屏)。
  **突变 ③ 第一轮曾误判为绿** —— 活性探针用原始 count 计调用点, 而各分片头注里就写着
  `<aq-row-pad>` 字样(解释收敛缘由), 注释把下限撑满; 已改为计数前剥离 `<!-- -->`, 剥后实测
  row-pad = 8 / empty = 12, 下限与实际值相等, 删任一处即红。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/shared/tpl/list-shell.html` | **新增**(单点分片): 两个 x-template `#tpl-aq-row-pad` / `#tpl-aq-empty` + 头注(行窗口化为何是两实例、`.empty` 结构不可动、图标语义口径 inbox/hourglass/warn) |
| `src/auto_qb/webui/static/shared/table.js` | 新增 `AQ_ROW_PAD_COMPONENT`(prop `height`)与 `AQ_EMPTY_COMPONENT`(`icon` 缺省 `#i-inbox` / `text`); 文件头组件清单补两行 |
| `src/auto_qb/webui/static/shared/filters.js` | 新增 methods 单点 `listEmptyText(hitNoun, noun, noneText)`(四层嵌套三元收敛为一份) + 三个视图级 computed 薄壳 `groupsEmptyText` / `torrentsEmptyText` / `showsEmptyText` |
| `src/auto_qb/webui/static/shared/app.js` | 注册 `aq-row-pad` / `aq-empty`(与 `aq-table` / `combo-input` 同范式) |
| `static/prism|console|atlas/index.html` | `tpl-manifest` 挂载 `/shared/tpl/list-shell.html`(`into: body`, 不进 `#app` 根模板) |
| `tpl/groups.html` | 组行上下 + 明细成员上下 4 处三明治 → `<aq-row-pad>`; 空态 → `<aq-empty>` |
| `tpl/torrents.html` | 种子行上下 2 处 → `<aq-row-pad>`; 空态 → `<aq-empty>`(**并补回缺失的「正在构建文件索引…」分支**) |
| `tpl/shows.html` | 集明细成员上下 2 处 → `<aq-row-pad>`; 空态 → `<aq-empty>` |
| `tpl/drawer.html` | 5 处空态 → `<aq-empty>`(流量三态 + 详情加载/错误) |
| `tpl/settings-detail.html` | 3 处空态 → `<aq-empty>`, **补齐此前缺失的图标**(error/readError 用 `#i-warn`) |
| `tpl/xtpl.html` | 变体表 teleport 兜底空态 → `<aq-empty>`(**补齐此前缺失的图标**, inbox) |
| `tests/test_webui_static_dom_page.py` | 新增守阵 `test_frontend_list_row_pad_and_empty_single_point` |
| `memory-bank/issues/26-10-20-2231-refactor-fe-tpl-list-row-empty-dup.html` | 状态 Open → In Progress → Done; §04 改「修复与验证」, 状态日志下沉 §05 |
| `memory-bank/issues/_index.md` · `memory-bank/issues/attachments/_archive.md` | 索引重建生成物(`commands run kb.index`) |
| `memory-bank/testing/baselines/26-10-21-0426-dup-code-audit.md` | 本切片 |

**入池计数更正**: issue 原写「`.empty` 11 处、其中 3 处无图标」, 认领复验实测 **12 处、其中 4 处无图标**
(drawer 5 / groups 1 / torrents 1 / shows 1 / settings-detail 3 / xtpl 1)。两处偏差:
①总数差 1 —— 入池时把 drawer 的流量三态并作一处数; ②无图标的除设置页 HR 三态外还有 xtpl 的
变体表 teleport 兜底(`<div v-else class="empty"><span>暂无数据</span></div>`), 入池时漏计。
守阵下限按 12 定。

未触及: 全部后端代码与 `config.yml`; 三皮肤 CSS(组件刻意保留 `.empty` + `svg.ico` + `span`
结构与类名, 皮肤样式无需改一行); 行本身仍由调用方 `v-for` 内联 —— 每列表两个占位实例,
不引入逐行组件实例(性能纪律见 `pitfalls/web-ui/frontend-split.md`)。
上一轮的改动与数字见 `memory-bank/testing/baselines/26-10-21-0323-dup-code-audit.md`。
