# [tool.mypy] files 相对 cwd 解析: 基线对比必须在基线目录内跑, 否则静默查的是工作树

> 摘要: mypy 的 `[tool.mypy] files = [...]` 按**当前工作目录**解析相对路径, 不按 pyproject.toml 所在目录 —— 想跑「某个基线 commit 的类型检查」时, 若从别处指 `--config-file` 指到基线目录, 实际检查的仍是 cwd 下的工作树, 结果**静默张冠李戴**, 前后对比数字全部作废。
> 触发: mypy, files, 相对路径, cwd, 基线对比, 静默查错, 工作树, 改错文件, typecheck 前后对照

### 做类型检查前后对比时, 错把基线 commit 的配置套在工作树上跑

- **触发**: mypy 渐进接入(计划 26-11-05-0635)做「首跑 vs 清债后」错误数对比时, 想法是
  `git worktree/clone 出基线 commit → 用它的 pyproject.toml 跑 mypy`。若在**当前工作树目录**
  里执行 `uv run mypy --config-file <基线目录>/pyproject.toml`, 或把 cwd 留在别处只换配置,
  配置里的 `files = ["src/auto_qb"]` 会被解析成 **cwd 下的 `src/auto_qb`** —— 查的是工作树,
  不是基线。
- **判别**: 症状是「换了基线配置, 错误清单却和当前工作树一模一样」。硬核验: 对比输出里的
  文件路径前缀(指向哪个目录)与 `mypy --version` 无关 —— 直接看**清单里文件的绝对路径**
  落在哪个 tree; 或在基线 tree 里 `touch` 一个已知坏点看它是否出现在输出里。
- **处置**: 基线对比一律**进基线目录内跑**(cwd = 基线 tree 根, `uv run --project <基线目录>`
  或在该目录里装好环境后执行), 让 `files` 的相对解析自然命中基线源码; 前后两次跑的
  mypy 版本与环境保持一致(同一 venv 版本), 只换被查的树。对比清单存盘时文件名注明
  「树 + commit」(如 `%TEMP%\typing-mypy\baseline-mypy.txt`), 别只写"before/after"。
- **复发**: 1(2026-11-06 首记, S1-S4 实施期实撞后修正跑法)。
