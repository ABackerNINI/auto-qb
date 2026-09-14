# Active Context — 当前焦点

> Memory Bank 核心文件之一: 回答"现在正在做什么 / 上次做到哪 / 下一步从哪继续"。**每次会话开始先读本文件。**
> 稳定事实在 projectbrief / productContext / systemPatterns / techContext 与各主题文档; 计划与完成状态在 [progress.md](progress.md); 本文件只放**易变的会话级状态**。
> 维护纪律: **每次会话收尾更新本文件**; 条目完成后沉淀进 [progress.md](progress.md) (完成项) 或对应主题文档 (事实) 后从这里删除, 保持本文件精炼; 跨会话的大任务在 [tasks/_index.md](tasks/_index.md) 立档。

**最后更新**: 2026-09-15 @ f18b4e7

## 正在进行

- WEB UI 第六轮打磨 (2026-09-15, 计划见 [docs/webui-optimization-plan.html](../docs/webui-optimization-plan.html), **已实施完成 + 冒烟全绿**): 站点配色回退状态双色、数值列右对齐/零值居中、多选+Shift+批量操作、命令回执(tracker 确认链路, 超时 30s)、删除确认框重构(信息/图标/汇报选项)、历史流量柱状图(天/月/年)、设置页折叠调整、登录加载态; 详见 pitfalls 第六轮条目。
- WEB UI 打磨循环 (第 3-5 轮, `5301084` → `ec0704a`): 交互/对齐/滚动修复、统计信息移至左侧固定栏、弹层视口翻转、站点专属色(已被第六轮反转)、列宽拖拽不误触排序、表头吸顶、时间单位中文化、关联配置默认折叠、站点状态色底。
- 图形化配置编辑已落地 (2026-09-14): 设置页全量增删改 + 结构化编辑器 (config/schema.py + writer + 守卫测试, 见 [testing.md](testing.md))。

## 下一步候选 (来源: `想法.md` 待办 + progress.md 规划中)

- WEB UI: 历史流量柱状图 (今日流量面板入口, 天/月/年视图切换); WebSocket 推送; 多用户
- WEB UI: 强制汇报显示是否成功; 窗口日志等级可选
- 规则系统: 条件取反 (`!`/非 logic); tracker 分组; 重新梳理 ignore_next_action_error / stop_following_rules_if
- 其它: 切分大文件; 种子未变动时不触发内置维护任务; 版本管理; 命中限速曲线强调显示; 插件系统
- 🚧 实机验证: README 标注 🚧 的功能 (alpha 阶段), 生产使用前先 `--dry-run` 观察

## 会话纪要

- 2026-09-15: WEB UI 优化实施完成 — 上午出计划文档(不改代码), 用户确认 D2 改 tracker 确认方案后按阶段 A-F 实施: 后端(schema Field.open / qbmanager 回执+确认跟踪 / web cmd+history 端点 / speed_curve history 发布) + 前端全部需求 + 5 个新单测; Edge headless CDP 冒烟 20/20 全绿(截图在 .openclaw/tmp/smoke-out); pytest 871 passed; README 与 memory-bank 回写。未提交 git。
- 2026-09-15: WEB UI 优化计划会话 — 逐文件摸底 (index.html/app.js/style.css/config_editor.js/config_rules.js/web.py/qbmanager.py/schema.py/curves.py/speed_curve.py) 后产出实施计划, 未改任何代码。关键事实: 命令队列无回执 (R05 需先补链路)、dat 天然按日行可直接做历史流量图、成员视图缺 name 字段、规则卡 collapsedRules 缺省展开。
- 2026-09-14: 安装 awesome-copilot 资产 (10 agents / 9 skills / 7 instructions); 知识库改造第一轮 — 根级 AGENTS.md 统一跨 agent 入口、测试基线单点化到 testing.md、各篇加基线锚点。
- 2026-09-15: 知识库全面迁移为 Memory Bank 结构 — `ai/` 整体迁入 `memory-bank/` (git mv 保留历史), 按六核心文件语义重命名, 新增 projectbrief / techContext / tasks/; 指令文件恢复原版 (applyTo: 'memory-bank/**'); AGENTS.md 与各指针文件改指 memory-bank/ 路径; src 注释与想法.md 中的文档引用同步更新。
