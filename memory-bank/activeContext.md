# Active Context — 当前焦点

> Memory Bank 核心文件之一: 回答"现在正在做什么 / 上次做到哪 / 下一步从哪继续"。**每次会话开始先读本文件。**
> 稳定事实在 projectbrief / productContext / systemPatterns / techContext 与各主题文档; 计划与完成状态在 [progress.md](progress.md); 本文件只放**易变的会话级状态**。
> 维护纪律: **每次会话收尾更新本文件**; 条目完成后沉淀进 [progress.md](progress.md) (完成项) 或对应主题文档 (事实) 后从这里删除, 保持本文件精炼; 跨会话的大任务在 [tasks/_index.md](tasks/_index.md) 立档。

**最后更新**: 2026-09-15 (WEB UI 新版界面 M1-M3 实施完成, feature/webui-redesign 分支)

## 正在进行

- WEB UI 新一代重设计 (2026-09-15, 计划见 [docs/webui-redesign-plan.html](../docs/webui-redesign-plan.html), **M1-M3 已实施**, 分支 `feature/webui-redesign`): 新 UI 收敛到 `web_ui/static/newui/` 独立目录走 `/newui/` (FastAPI `StaticFiles(html=True)` 零后端路由已验证), 旧 UI 原样保留仅顶栏 +1 切换链接; 共享逻辑层三件套 (app.js/config_editor.js/config_rules.js) 单一来源不复制, 新模板须守 JS↔DOM 契约 (.group-head/.detail-head/gridStyle 列数/.search-hit/.ctx-menu/.sticky-head+--head-h/.bulk-bar+--bulk-h/tpl-ce-field/sprite #i-*/toast 确认框单例); 主题走语义令牌契约 tokens.css + 每主题一文件 (theme-factory 4 preset 改调 + 1 品牌绿定制, 共 5 套: 深海机房/暗夜星云/极地晨霜/麦秋/品牌轨道), data-theme + localStorage `autoqb.ui.theme` + prefers-color-scheme 跟随, theme.js head 同步防 FOUC; 冒烟 34/34 (双 UI/五主题 WCAG 对比度/移动宽/无控制台错误), pytest 871 全绿; D1-D5 按建议值落地 (默认主题深海机房/亮色极地晨霜、4+1 主题集、顶栏切换入口、第七轮逻辑项已在共享层生效、旧 UI 视觉冻结); 待办: M4 残余(实机视觉走查、可再打磨) 与合并回 develop。
- WEB UI 第七轮打磨 (2026-09-15, 计划见 [docs/webui-optimization-plan-v2.html](../docs/webui-optimization-plan-v2.html), **已实施完成 + 冒烟 24/24 全绿 + pytest 871 全绿**, 在现行 UI 上按用户指示直接实施): 历史流量改双系列折线图(920×380, 容器级悬停修复闪烁, draw-in 动效)、批量选择条 sticky 吸顶(--bulk-h 联动表头偏移)、强制汇报三态强反馈(toast sticky/busy/timeout, 去红色警告样式)、删除确认框 wide+成员明细+值换行可选、展开/选中视觉分家(展开=结构语言, 选中=accent 语言)、Shift 锚点=展开组、设置页 日志/WEB UI/通知 平铺(cfgFlatten 透明展开 + cfgGroupToggle 三态修复 + _attachGrey 守卫)、⚠/▲▼ 字形图标化、死 CSS 清理(strip-select/ce-dirty/ce-warn/sr-check/pill-limit .dot/modal-checks); 后端零改动; 已提交 `2ed0890`(第七轮独立落盘)。若后续推进新一代重设计, 本轮改动已在旧 UI 上生效(分流决策见重设计计划 D4)。
- WEB UI 第六轮打磨 (2026-09-15, 计划见 [docs/webui-optimization-plan.html](../docs/webui-optimization-plan.html), **已实施完成 + 冒烟全绿**): 站点配色回退状态双色、数值列右对齐/零值居中、多选+Shift+批量操作、命令回执(tracker 确认链路, 超时 30s)、删除确认框重构(信息/图标/汇报选项)、历史流量柱状图(天/月/年)、设置页折叠调整、登录加载态; 详见 pitfalls 第六轮条目。
- WEB UI 打磨循环 (第 3-5 轮, `5301084` → `ec0704a`): 交互/对齐/滚动修复、统计信息移至左侧固定栏、弹层视口翻转、站点专属色(已被第六轮反转)、列宽拖拽不误触排序、表头吸顶、时间单位中文化、关联配置默认折叠、站点状态色底。
- 图形化配置编辑已落地 (2026-09-14): 设置页全量增删改 + 结构化编辑器 (config/schema.py + writer + 守卫测试, 见 [testing.md](testing.md))。

## 下一步候选 (来源: `想法.md` 待办 + progress.md 规划中)

- WEB UI: WebSocket 推送; 多用户
- WEB UI: 窗口日志等级可选
- 规则系统: 条件取反 (`!`/非 logic); tracker 分组; 重新梳理 ignore_next_action_error / stop_following_rules_if
- 其它: 切分大文件; 种子未变动时不触发内置维护任务; 版本管理; 命中限速曲线强调显示; 插件系统
- 🚧 实机验证: README 标注 🚧 的功能 (alpha 阶段), 生产使用前先 `--dry-run` 观察

## 会话纪要

- 2026-09-15: WEB UI 新版界面实施 (M1-M3) — 切 `feature/webui-redesign` 分支(第七轮成果先独立落盘为 2ed0890); 逐文件读全 index.html/style.css 完成契约审计(M0), 拷贝模板保全部 Vue 绑定 + 顶栏加主题切换器(纯 DOM 事件委托)与互切链接; 新 CSS 四层落地(tokens 结构令牌/themes×5 全色令牌/base/components/views, 设计语言=实色表面+hairline 高程+小圆角+Bahnschrift display+mono 数据字体+rail 舵台大数字); theme.js 事件委托绑定(登录前顶栏未渲染不能用 getElementById 直绑); 冒烟基建: .openclaw/tmp/newui-smoke/(假 manager 复刻 test_web 手法 + Node CDP), 34/34 全绿含五主题 WCAG 对比度(亮色 --fg-dim 两档初值不达标已压暗修正); 踩坑: 企业策略强装 Dark Reader 污染 headless 冒烟(详见 pitfalls 新版 UI 条目), pytest 871 全绿, README/memory-bank 回写。
- 2026-09-15: WEB UI 第七轮实施完成 — 按计划 v2 阶段 A-E 全部落地(仅前端 app.js/index.html/style.css/config_editor.js), pytest 871 全绿, Edge headless CDP 冒烟 24/24(折线图/悬停连续性/吸顶联动/状态分家/平铺/Shift 锚点/三态汇报/wide 确认框/两档右对齐), 截图在 .openclaw/tmp/smoke-out。冒烟运维新踩坑: Edge 同 user-data-dir 单例移交 + 被杀脚本残留页面重连后执行幽灵操作(误删新环境同名组) → 每轮必须独立 profile + 起服务前清理 smoke edge/端口(见 pitfalls 第七轮)。未提交 git。
- 2026-09-15: WEB UI 重设计计划会话 — 读 AGENTS/memory-bank 后加载 `.github/skills/frontend-design` + `theme-factory` (用户指名的两个 skill, 2026-09-14 安装), 摸底现有 UI: index.html 1219 行 (#app 内联模板+sprite+tpl-ce-field) / style.css 1176 行 (单一 :root 约 50 令牌, 头注明文记载 JS↔DOM 契约) / app.js 1614 行 (createApp@107 mount@1695) / 脚本顺序 vue→config_editor→config_rules→app.js / web.py:277 `StaticFiles(html=True)`。产出 docs/webui-redesign-plan.html (delivery-artifact Native 冷峻技术方向, 与 v2 计划同族), 未改任何代码。关键结论: `/newui/` 天然可服务零后端改动; 方案选 A 共享逻辑层+重写模板层 (否决全量复制与构建链); 非 /api 已全量 no-cache 覆盖新目录。
- 2026-09-15: WEB UI 第七轮优化计划会话 — 读 AGENTS/memory-bank 后逐文件摸底 (app.js/index.html/style.css/config_editor.js + web.py/qbmanager.py 回执链路 + schema.py `Field.open` 声明), 产出 docs/webui-optimization-plan-v2.html (delivery-artifact Native 冷峻技术方向), 未改任何代码。关键事实: 闪烁根因=命中区只盖单柱; 折叠点不动根因=cfgGroupToggle 写不出 false; 第六轮回执链路是强反馈的地基, 后端无需改。
- 2026-09-15: WEB UI 优化实施完成 — 上午出计划文档(不改代码), 用户确认 D2 改 tracker 确认方案后按阶段 A-F 实施: 后端(schema Field.open / qbmanager 回执+确认跟踪 / web cmd+history 端点 / speed_curve history 发布) + 前端全部需求 + 5 个新单测; Edge headless CDP 冒烟 20/20 全绿(截图在 .openclaw/tmp/smoke-out); pytest 871 passed; README 与 memory-bank 回写。未提交 git。
- 2026-09-15: WEB UI 优化计划会话 — 逐文件摸底 (index.html/app.js/style.css/config_editor.js/config_rules.js/web.py/qbmanager.py/schema.py/curves.py/speed_curve.py) 后产出实施计划, 未改任何代码。关键事实: 命令队列无回执 (R05 需先补链路)、dat 天然按日行可直接做历史流量图、成员视图缺 name 字段、规则卡 collapsedRules 缺省展开。
- 2026-09-14: 安装 awesome-copilot 资产 (10 agents / 9 skills / 7 instructions); 知识库改造第一轮 — 根级 AGENTS.md 统一跨 agent 入口、测试基线单点化到 testing.md、各篇加基线锚点。
- 2026-09-15: 知识库全面迁移为 Memory Bank 结构 — `ai/` 整体迁入 `memory-bank/` (git mv 保留历史), 按六核心文件语义重命名, 新增 projectbrief / techContext / tasks/; 指令文件恢复原版 (applyTo: 'memory-bank/**'); AGENTS.md 与各指针文件改指 memory-bank/ 路径; src 注释与想法.md 中的文档引用同步更新。
