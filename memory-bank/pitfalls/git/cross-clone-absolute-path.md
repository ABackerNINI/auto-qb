# AI 代理默认 cwd 与绝对路径指向不同 clone: 修复被落到非工作区 clone

> 摘要: AI 代理默认 cwd 与绝对路径指向不同 clone: 修复被落到非工作区 clone
> 触发: 跨clone, 工作区clone, 绝对路径, 默认cwd, 误改其它clone, 多clone并行

**Refs:** memory-bank/tasks/26-11-10-test-github-ci-e2e-red-fix.md

## 本篇只回答

多 clone 并行时, 工具默认 cwd 与编辑调用里的绝对路径若分属不同 clone, 如何发现并撤回落到非工作区 clone 的改动。

### 工具默认 cwd 与绝对路径分属两个 clone 时, 修复落到错误 clone

- **触发**: 本轮工作区是 `D:\Projects\workbuddy-ai\auto-qb-wbai-clone1`, 但 Read/Edit 参数写成 `D:\Projects\auto-qb\...`; 不带 cd 的 `git status` 看的是工作区 clone, 两个 clone 的 HEAD/树态不同(`832ffc4d` vs `8f5a73d`), 于是在错误 clone 改代码、跑测试、回写文档, 直到 `git diff --stat` 与 `pwd` 对账才暴露。
- **判别**: `pwd` / `git rev-parse --show-toplevel` 与编辑参数里的盘符路径不是同一个根; 或两个 clone 上 `git status --short` 呈现不同改动集; 或测试通过的 clone 与待提交 clone 不是同一个。
- **处置**: 先 `pwd` + `git rev-parse --show-toplevel` 钉死工作区根, 所有编辑只用该根下绝对路径; 已误改时只 `git checkout -- <本轮自己改过的具体文件>` 还原(保留该 clone 原有无关改动), 再把同款改动重新应用到工作区 clone 并重跑验证。跨仓库写操作绝对禁止, 误改即止损并报告, 不借势提交。
- **守阵**: 提交前把 cwd、`git rev-parse --show-toplevel`、`git status --short` 三处对账; 可写子代理任务提示里钉死基线仓库绝对路径。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
