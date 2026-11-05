# clone 连 .venv 复制致 uv trampoline 内嵌路径失效, env.sync 假自愈

> 摘要: clone 连 .venv 复制致 uv trampoline 内嵌路径失效, env.sync 假自愈
> 触发: uv trampoline failed to canonicalize script path,uv run pytest 报错,console script 起不来,uv sync 后仍坏,uv run python 却正常
**Refs:**

### clone 连 .venv 复制后 console-script trampoline 全坏, `uv sync` 假装自愈

- **触发**: 本机多 clone 工作区里, 新 clone 由旧 clone **整目录复制**而来（.venv 跟着进来）。uv 的 console-script trampoline（`.venv/Scripts/pytest.exe` 等入口 exe）内嵌**创建时那份 .venv 的绝对路径**；复制后路径指向源 clone，目标失效。
- **判别**: `uv run pytest --version`（任何 console script）报 `error: uv trampoline failed to canonicalize script path`，而 `uv run python -c ...` **正常**（python.exe 不走同款内嵌路径）；跑 `commands run env.sync`（`uv sync`）输出 `Resolved/Checked ...` 全绿**但症状不变**——sync 校验包完整性，不校验/不重建已存在的 trampoline，属假自愈。提交闸门表现为 `test.pkg.scoped` 0.3s 内 FAIL 且只有这一行 uv 报错。
- **处置**: 定点重装坏入口所属包，强制 uv 重写 trampoline：`uv sync --reinstall-package pytest`（缺哪个修哪个，先 `uv run <script> --version` 逐个确认）。全量重建用 `uv sync --reinstall`（慢，按需）。修完 `uv run pytest --version` 出版本号即愈。预防口径：新 clone 初始化**不要整目录复制旧 clone**，先复制代码再对裸目录跑 `commands run env.sync`；已复制的 clone 逐个试 console script，坏即定点重装。
- **守阵**: 无机检——症状只在首次调用对应 console script 时显形（提交闸门 test.pkg.scoped 是最常见的显形点）；复发靠触发词路由本档。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
