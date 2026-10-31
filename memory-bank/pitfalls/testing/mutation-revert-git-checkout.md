# 变异回退不得用 git checkout(会冲掉未提交改动)

> 摘要: 红绿双验做突变时, 用 `git checkout -- <file>` 还原文件会把**本轮尚未提交的全部改动**一起冲掉 —— 突变注入的 sed 与手头未提交的实现在同一个工作区文件里, checkout 不区分。防御: 精确反向 Edit 重放突变(或 `git stash` 之外的备忘), 还原后先 `git status` 核对改动面。
> 等级: L0
> 触发: 红绿双验, 变异测试, 突变, 判红, git checkout 还原, 冲掉未提交, 工作区回退, sed 注入

### 事故形态(2026-10-16, hr-ext-connect-ui S4–S6 收尾)

- **触发**: 新守阵做完要做红绿双验(计划 V5「至少一类突变判红」), 用 `sed -i` 注入突变 → 跑用例确认判红 → `git checkout -- <file>` 还原 → 继续下一个突变。
- **判别**: `git checkout -- <file>` 还原的是 **HEAD 版本**, 不是「注入突变前的版本」。本轮 S4–S6 的 background.js(setIcon/徽标折中)、options.js(旧按钮名串修复)当时**尚未提交**, 一次 checkout 把实现改动连突变一起冲掉 —— 表现是守阵照样红(突变还在跑), 但还原后新实现消失, 后续 `test.full` 全绿但产品行为已回退(静默丢失)。
- **处置**:
  1. 突变还原一律用**精确反向替换**(Edit/sed 把突变字符串改回原值), 不用 `git checkout`;
  2. 还原后立即 `git status --short` + 关键串 grep 核对改动面仍在(本轮靠 grep `badgeIconOf` 发现丢失, Edit 重放后复测 42 绿);
  3. 大批量红验前先想清楚「文件里哪些改动是未提交的」—— 未提交越多, checkout 越致命;
  4. 已入池提交后再做变异最安全(commit 后 checkout 只回退突变)。
