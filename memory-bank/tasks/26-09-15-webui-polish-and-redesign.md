# 26-09-15-webui-polish-and-redesign — WEB UI 打磨轮次与棱镜重设计 (第六 ~ 八轮 + 双界面命名)

**Status:** Done
**Added:** 2026-09-15
**Updated:** 2026-09-15
**专题:** WEB UI / 前端打磨 / 多主题
**Legacy-ID:** TASK003
**Summary:** `atlas`/`prism`/`shared` 目录化 + 五主题令牌 + 各轮冒烟全绿 (2026-09-15)
**Topics:** webui-polish-and-redesign

## 原始请求

- 2026-09-15: 连续多轮 WEB UI 优化诉求 (交互、对齐、滚动、图表、批量操作、反馈强度、设置页折叠…), 每轮要求先出计划再实施; 中途提出**新一代重设计**与**双界面命名** (星图 / 棱镜)。

## 思考过程与决策

- 每轮沿用"先计划文档 (delivery-artifact, Native 冷峻技术方向) → 用户拍板决策点 → 实施 → 浏览器冒烟 → pytest 闸门"的节奏。
- 第六轮起改为**运行时诊断优先**: 用 `FakeQbServer` + Edge CDP 实测取证, 再定方案 (第七轮遗留 3 项"未生效"即由此定根因)。
- 重设计选方案 A: **共享逻辑层 + 重写模板层** (否决全量复制与构建链); `/newui/` 零后端路由 (`StaticFiles(html=True)` 已验证)。
- 主题走语义令牌契约 `tokens.css` + 每主题一文件 (4 preset 改调 + 1 品牌绿定制 = 5 套), `data-theme` + `localStorage` + `prefers-color-scheme` 跟随, `theme.js` 首帧前同步防 FOUC。
- 命名原则沉淀: **身份名不代际名** (旧 UI = 星图 `atlas/`, 新 UI = 棱镜 `prism/`); 共享层三件套收进 `static/shared/` 单一来源。
- 浏览冒烟运维纪律: 每轮**独立 profile** + 起服务前清理残留 edge/端口 (曾有同 user-data-dir 单例移交导致幽灵操作误删数据)。

## 实现计划

- [x] 第六轮: 站点配色回退双色、数值列右对齐、多选 + Shift + 批量操作、命令回执、删除确认框重构、历史流量柱状图、设置页折叠、登录加载态
- [x] 第七轮: 双系列折线图、批量条吸顶、强制汇报三态强反馈、展开/选中视觉分家、Shift 锚点、设置页平铺、死 CSS 清理
- [x] 第八轮: 吸顶零缝、筛选器幽灵空位、`_findGroup` 派生层修复、H&R 筛选、单种子视图 (后端 `_build_singles_view`)、信息栏双模式、令牌中性化
- [x] 重设计 M1-M3: `newui/` 独立目录 + 五主题令牌 + 冒烟 34/34
- [x] 双界面命名与目录化: `atlas/` / `prism/` / `shared/` + 307 重定向 + 鉴权范围限定 `/api/*`
- [ ] 实机浏览器视觉走查 (M4 残余, 可再打磨)

## 子任务状态表

| ID | 描述 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| 3.1 | 第六轮打磨 + 计划文档 | Complete | 2026-09-15 | 命令回执链路 + 流量柱状图 |
| 3.2 | 第七轮打磨 (计划 v2) | Complete | 2026-09-15 | 冒烟 24/24; 提交 `2ed0890` |
| 3.3 | 第八轮打磨 (计划 v3) | Complete | 2026-09-15 | 冒烟 10/10; `362f292` 补交 |
| 3.4 | 重设计 M1-M3 (`feature/webui-redesign`) | Complete | 2026-09-15 | 冒烟 34/34; 五主题 WCAG 全达标 |
| 3.5 | 双界面命名与目录化 (`atlas`/`prism`/`shared`) | Complete | 2026-09-15 | 计划 `memory-bank/plans/26-09-15-1241-webui-naming-plan.html` |
| 3.6 | 实机视觉走查 | Not Started | 2026-09-15 | 需人工浏览器 |

## 进度日志

### 2026-09-15

- 第六 / 七 / 八轮打磨全部落地 (仅前端 + 少量后端 singles/回执), 各轮均经 Edge headless CDP 冒烟 (20/20 → 24/24 → 10/10) 与 pytest 871→872 闸门。
- 重设计 M1-M3 与"双界面命名"完成, 后续界面级诉求转入 [TASK002](26-09-15-webui-qb-replacement.md) (替代 qB 界面波次)。

## 历史会话纪要 (原文归档)

> 以下为 `activeContext.md` 会话纪要的**原文归档** (2026-09-17 机械迁移, 未删改; 含一处历史 GBK 编码损坏条目),
> 按时间倒序保留。新增进展请写 `## 进度日志`, 不要再往 `activeContext.md` 堆长纪要。

- 2026-09-15: WEB UI 第八轮实施(旧 UI) — 按计划 v3 阶段 A-E 落地(前端 app.js/index.html/style.css + 后端 qbmanager singles + test_web 新单测); 冒烟首轮 7/10 排查为环境坑(残留服务器占 18099 端口致新服务器 bind 失败, 冒烟连到旧进程; HD 无文件列表=天然 single; 视口太高滚动余量不足吸顶阈值)而非代码 bug, 清场(按端口杀残留进程)+修断言后 10/10 全绿; pitfalls 回写第八轮条目(诊断优先方法论/_findGroup 派生层/visibility 占位幽灵空位/--bulk-h 语义/冒烟吸顶视口压矮技巧)。pytest 872 全绿, README 辅种管理页回写。未提交 git。后续: 并行后端拆分会话将本轮工作区遗留以 `362f292` 补交入库(qbmanager/app.js/index.html/test_web/计划 v3), 并在其后继续拆分 qbmanager(mixins/web_view+web_commands+qbclient)与 schema 包, 各批 pytest 872 全绿; 本轮剩余未入库: style.css 全部令牌与新组件样式、index.html 末批 transition 包裹、README/memory-bank 回写 —— 均在并行会话批次三(torrents/validation 拆分)工作树之上, 该批次中间态有暂态 NameError(非本轮改动)。
- 2026-09-15: WEB UI 第八轮计划会话(旧 UI) — 读 AGENTS/memory-bank 后逐文件摸底(index.html/app.js/style.css 全量 + qbmanager._build_group_view/torrents._VIEW_FIELDS/web.py no-cache), 对第七轮遗留 3 个"未生效"项跑运行时诊断(smoke_server.py + 自写 diag_ui.mjs)定根因, 产出 memory-bank/plans/26-09-15-1042-webui-optimization-plan-v3.html(delivery-artifact Native 冷峻技术方向, 与 v2/redesign 同族), 未改任何代码。关键事实: 成员视图字段已齐(name/save_path/HR); 未归组种子不在 groups payload(仅搜索露出)→单种子视图需后端 singles(~30行); store.view_changed 对任意种子视图字段变化置真→singles 同快照重建可行; web.py 非 /api no-cache 中间件存在→缓存假说排除; 当前分支 agentAutoClaw/develop, 新 UI 在 feature/webui-redesign 并行。
- 2026-09-15: WEB UI 新版界面实施 (M1-M3) — 切 `feature/webui-redesign` 分支(第七轮成果先独立落盘为 2ed0890); 逐文件读全 index.html/style.css 完成契约审计(M0), 拷贝模板保全部 Vue 绑定 + 顶栏加主题切换器(纯 DOM 事件委托)与互切链接; 新 CSS 四层落地(tokens 结构令牌/themes×5 全色令牌/base/components/views, 设计语言=实色表面+hairline 高程+小圆角+Bahnschrift display+mono 数据字体+rail 舵台大数字); theme.js 事件委托绑定(登录前顶栏未渲染不能用 getElementById 直绑); 冒烟基建: .openclaw/tmp/newui-smoke/(假 manager 复刻 test_web 手法 + Node CDP), 34/34 全绿含五主题 WCAG 对比度(亮色 --fg-dim 两档初值不达标已压暗修正); 踩坑: 企业策略强装 Dark Reader 污染 headless 冒烟(详见 pitfalls 新版 UI 条目), pytest 871 全绿, README/memory-bank 回写。
- 2026-09-15: WEB UI 第七轮实施完成 — 按计划 v2 阶段 A-E 全部落地(仅前端 app.js/index.html/style.css/config_editor.js), pytest 871 全绿, Edge headless CDP 冒烟 24/24(折线图/悬停连续性/吸顶联动/状态分家/平铺/Shift 锚点/三态汇报/wide 确认框/两档右对齐), 截图在 .openclaw/tmp/smoke-out。冒烟运维新踩坑: Edge 同 user-data-dir 单例移交 + 被杀脚本残留页面重连后执行幽灵操作(误删新环境同名组) → 每轮必须独立 profile + 起服务前清理 smoke edge/端口(见 pitfalls 第七轮)。未提交 git。
- 2026-09-15: WEB UI 重设计计划会话 — 读 AGENTS/memory-bank 后加载 `.github/skills/frontend-design` + `theme-factory` (用户指名的两个 skill, 2026-09-14 安装), 摸底现有 UI: index.html 1219 行 (#app 内联模板+sprite+tpl-ce-field) / style.css 1176 行 (单一 :root 约 50 令牌, 头注明文记载 JS↔DOM 契约) / app.js 1614 行 (createApp@107 mount@1695) / 脚本顺序 vue→config_editor→config_rules→app.js / web.py:277 `StaticFiles(html=True)`。产出 memory-bank/plans/26-09-15-0956-webui-redesign-plan.html (delivery-artifact Native 冷峻技术方向, 与 v2 计划同族), 未改任何代码。关键结论: `/newui/` 天然可服务零后端改动; 方案选 A 共享逻辑层+重写模板层 (否决全量复制与构建链); 非 /api 已全量 no-cache 覆盖新目录。
- 2026-09-15: WEB UI 第七轮优化计划会话 — 读 AGENTS/memory-bank 后逐文件摸底 (app.js/index.html/style.css/config_editor.js + web.py/qbmanager.py 回执链路 + schema.py `Field.open` 声明), 产出 memory-bank/plans/26-09-15-0910-webui-optimization-plan-v2.html (delivery-artifact Native 冷峻技术方向), 未改任何代码。关键事实: 闪烁根因=命中区只盖单柱; 折叠点不动根因=cfgGroupToggle 写不出 false; 第六轮回执链路是强反馈的地基, 后端无需改。
- 2026-09-15: WEB UI 优化实施完成 — 上午出计划文档(不改代码), 用户确认 D2 改 tracker 确认方案后按阶段 A-F 实施: 后端(schema Field.open / qbmanager 回执+确认跟踪 / web cmd+history 端点 / speed_curve history 发布) + 前端全部需求 + 5 个新单测; Edge headless CDP 冒烟 20/20 全绿(截图在 .openclaw/tmp/smoke-out); pytest 871 passed; README 与 memory-bank 回写。未提交 git。
- 2026-09-15: WEB UI 优化计划会话 — 逐文件摸底 (index.html/app.js/style.css/config_editor.js/config_rules.js/web.py/qbmanager.py/schema.py/curves.py/speed_curve.py) 后产出实施计划, 未改任何代码。关键事实: 命令队列无回执 (R05 需先补链路)、dat 天然按日行可直接做历史流量图、成员视图缺 name 字段、规则卡 collapsedRules 缺省展开。
