# GitHub 镜像 develop 分叉合并

> 摘要: 用户报 GitHub 远端分叉 → 开工同步 + 取证(同补丁重复件)+ merge 取我方(树零变化)+ 记坑 2 条, 随本专题入库。
> 最后活动: 2026-10-16 16:22

- **开工同步**: my-commit-flow.sync 快进 2968b8bc→b0d467e7(origin/Gitee 领先 16 笔)。
- **取证**: GitHub develop 真值 06edcbcb(fetch 后 FETCH_HEAD + ls-remote 现查, refs/remotes/github 不可靠); 本地领先 67 笔; git cherry 判补丁等价 → patch-id 与本地 9a80bd00 全等(51a34b5f), 10 个涉及文件 blob 逐一相同 ⇒ 对方零新增内容, 纯双端重复件。合并前备份 .git 到仓库外 $TEMP。
- **合并**: merge --no-commit --no-ff; 5 处冲突(2 add/add + 3 content)全取我方 —— 我方是共享基底的后续演化(单文件最多再演化 10 笔), 零丢失; 生成物 _index 不重跑(树零差异下索引本就同步)。
- **核验**: 合并树与 HEAD git diff 为空; 3400 个跟踪文件在位零缺失; 未重跑 test.full —— 树与最新基线切片(kb.baseline 首条, 26-10-16 14:04 global-traffic-monitor-s7)同一棵, 数字沿用。
- **记坑 2 条**: pitfalls/git/editing-traps.md 新增「PowerShell 参数模式拆散变量双点区间 → git 区间静默反转」; 新建 pitfalls/git/mirror-divergence.md(判据三件套 + 取我方解法 + 零差异自证)。
- 用户指令 2 轮、零源文件改动、无计划/报告制品 → 立档阈值未达, 只留本切片。
