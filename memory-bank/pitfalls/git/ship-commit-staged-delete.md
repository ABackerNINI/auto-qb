# ship.commit 逐路径 add 撞「已暂存删除」路径

> 摘要: commit.py 按纪律逐路径 `git add -- <path>`(禁 -A), 对**已暂存的删除**(`D `)必然 pathspec 落空 —— 删除一旦进暂存区, 该路径在工作区与索引里都不复存在, `git add` 无处匹配。
> 触发: ship.commit, git add 失败, pathspec did not match, 删除文件, 提交失败, 蒸馏切片

- **触发**: 本轮删除过已跟踪文件(如按 DoD 蒸馏 activeContext 切片)后跑 `commands run ship.commit`,
  暂存步骤报 `RESULT: FAIL git add 失败: <被删路径>` + `fatal: pathspec ... did not match any files`
  (2026-09-28 实测, 删除已随前次失败留在暂存区)。
- **判别**: `git status --porcelain` 看该路径首列 —— `D `(删除已暂存)必踩: 索引已无此文件、工作区也没有,
  `git add -- <path>` 无处匹配; ` D`(删除未暂存)则索引还留着条目, `git add -- <path>` 能正常登记删除。
- **处置**: `git restore --staged <path>` 把删除退回未暂存态(` D`)后重跑 ship.commit 即过;
  根修在 commit.py(对 `D`/` D` 路径改用 `git rm --cached -- <path>` 或带 `--ignore-missing` 的登记方式),
  本轮未动脚本(范围守恒)。
