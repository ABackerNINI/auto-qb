# Active Context — 当前焦点

> Memory Bank 核心文件之一: 回答"现在正在做什么 / 上次做到哪 / 下一步从哪继续"。**每次会话开始先读本文件。**
> 稳定事实在 projectbrief / productContext / systemPatterns / techContext 与各主题文档; 计划与完成状态在 [progress.md](progress.md); 本文件只放**易变的会话级状态**。
> 维护纪律 (完整规程见 [memory-bank skill](../.agents/skills/memory-bank/SKILL.md)): ①每次会话收尾更新本文件, 已完成条目沉淀到 [progress.md](progress.md) 或主题文档后**删除** — 本文件只放易变状态; ②命中立档阈值的任务在 [tasks/](tasks/_index.md) 立档并同步索引; ③**禁止**在本文件追加长流水账纪要 (会淹没真正的当前焦点)。

**最后更新**: 2026-09-17 (Memory Bank 触发机制修复**已完成** — skill 载体 + always-on 立档阈值 + TASK001~TASK010 回填 + activeContext 瘦身 (68→26 行) + 守卫 `test_memory_bank.py` 6 项; 995 passed, **未提交**; 详见 [tasks/TASK010](tasks/TASK010-memory-bank-trigger-fix.md))

## 正在进行

- **WEB UI 替代 qB 界面** (波次三复查已修完, **未提交 git**): 剩余 = 实机 CDP 双 UI 走查 + 真机 dry-run + prism 追剧模板 → 档案 [tasks/TASK002-webui-qb-replacement.md](tasks/TASK002-webui-qb-replacement.md)
- **tracker 分组阶段 2/3 前端** (待排期): 设置页 groups 快捷追加 + 辅种管理页按组筛选 → 档案 [tasks/TASK007-tracker-groups.md](tasks/TASK007-tracker-groups.md)

## 下一步候选 (来源: `想法.md` 待办 + progress.md 规划中)

- WEB UI: WebSocket 推送; 多用户
- WEB UI: 窗口日志等级可选
- 规则系统: 条件取反 (`!`/非 logic); 重新梳理 ignore_next_action_error / stop_following_rules_if
- tracker 分组前端增强 (阶段 2/3, 2026-09-15 拍板后续): 设置页 groups 下拉快捷追加 (rules_ref 风格); 辅种管理页按组筛选 (web_view 透出 conf.groups + app.js filterDefs)
- 其它: 切分大文件; 种子未变动时不触发内置维护任务; 版本管理; 命中限速曲线强调显示; 插件系统
- 🚧 实机验证: README 标注 🚧 的功能 (alpha 阶段), 生产使用前先 `--dry-run` 观察

## 历史归档 (已迁出本文件)

2026-09-14 ~ 2026-09-17 的全部会话纪要已按专题迁移到 [tasks/](tasks/_index.md) 各档案的"历史会话纪要 (原文归档)"段 (原文未删改)。需要回查历史请走 `tasks/_index.md` 定位专题档案, 本文件只保留**当前焦点**。
