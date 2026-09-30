# 26-09-30-0936-memory-bank-timekit — memory-bank 取时间标准化

> 摘要: 用户提出文档日期不准/体例漂移/文件名出现未来时间, 要求 UTC+8 脚本单点取时 + 守卫 + 守卫脚本随 skill 移植。两轮探索定稿计划: timekit.py 单点 (date/time/stamp/check) + commands run kb.time 流程接入 + 三层日期守卫 (文件名/元数据严格, 正文只查体例) + check_doc_links 迁入 skill + 收口 gen_active_recent 静默回退 + create-issue 钉 +08。**计划已入档 (plans/26-09-30-0931), 用户指令暂不实施**。
> 最后活动: 2026-09-30 09:36

## 状态

- 计划文档: `plans/26-09-30-0931-plan-memory-bank-timekit.html` (doc-status Open); 档案: `tasks/26-09-30-memory-bank-timekit.md` (Status Open, 子任务表 2/9 完成 —— 仅入档轮)。
- 根因已钉死: 约定要求「时间戳用命令取当前值」但 `.commands/` 里该命令 0 命中; 守卫只查形状不查值; 唯一脚本化取时点 (create-issue stamp) 裸本地时区。存量未来日期 0 (防再生为主), 体例噪音约 20 处待清洗。

## 正在进行

- 无 —— 等待用户显式启动实施 (「暂不实施」是本轮收尾指令)。

## 下一步

- 用户说「实施」→ 按计划 05 执行步骤推进: 步骤 1 = `timekit.py` + 单测 (先有单点, 后续一切时间戳取自它); 步骤 6 存量清洗必须在收口静默回退**之前**; 收尾 pitfalls/kb/ 记坑「约定命令不存在 → 凭记忆写日期; 日期值无机检」。
