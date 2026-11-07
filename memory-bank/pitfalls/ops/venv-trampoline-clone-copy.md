# clone 连 .venv 复制致 uv trampoline 内嵌路径失效, env.sync 假自愈

> 摘要: clone 连 .venv 复制致 uv trampoline 内嵌路径失效, env.sync 假自愈
> 触发: uv trampoline failed to canonicalize script path,uv run pytest 报错,console script 起不来,uv sync 后仍坏,uv run python 却正常
**Refs:** memory-bank/tasks/26-11-08-webui-legacy-review4-webui-py-fix.md

### clone 连 .venv 复制后 console-script trampoline 全坏, `uv sync` 假装自愈

- **触发**: 本机多 clone 工作区里, 新 clone 由旧 clone **整目录复制**而来（.venv 跟着进来）。uv 的 console-script trampoline（`.venv/Scripts/pytest.exe` 等入口 exe）内嵌**创建时那份 .venv 的绝对路径**；复制后路径指向源 clone，目标失效。
- **判别**: `uv run pytest --version`（任何 console script）报 `error: uv trampoline failed to canonicalize script path`，而 `uv run python -c ...` **正常**（python.exe 不走同款内嵌路径）；跑 `commands run env.sync`（`uv sync`）输出 `Resolved/Checked ...` 全绿**但症状不变**——sync 校验包完整性，不校验/不重建已存在的 trampoline，属假自愈。提交闸门表现为 `test.pkg.scoped` 0.3s 内 FAIL 且只有这一行 uv 报错。
- **处置**: 定点重装坏入口所属包，强制 uv 重写 trampoline：`uv sync --reinstall-package pytest`（缺哪个修哪个，先 `uv run <script> --version` 逐个确认）。全量重建用 `uv sync --reinstall`（慢，按需）。修完 `uv run pytest --version` 出版本号即愈。预防口径：新 clone 初始化**不要整目录复制旧 clone**，先复制代码再对裸目录跑 `commands run env.sync`；已复制的 clone 逐个试 console script，坏即定点重装。
- **守阵**: 无机检——症状只在首次调用对应 console script 时显形（提交闸门 test.pkg.scoped 是最常见的显形点）；复发靠触发词路由本档。
- **复发**: 1(2026-11-06, 107 笔同步后首次跑包测试)—— 触发词「uv trampoline failed to canonicalize」命中坑档路由, 按处置 `uv sync --reinstall-package <pkg>` 定点重装 pytest/yapf 两包即愈 —— 路由按设计工作, 非漏防; 注意坏入口是逐个显形的, 修完 pytest 还要探 yapf 等流水线会用的其余入口。
- **复发**: 2(2026-11-06, 同日 clone1 版本管理 S1-S5 实施轮)—— env.sync 后 pytest 显形、修完又见 yapf 显形(同款逐个显形), 同处置定点重装即愈; 事发时未先查本档(改代码前未跑 pitfalls 索引路由, 检索纪律漏执行), 修完拟立新坑才发现已立档。
- **复发**: 3(2026-11-06, 同日 clone3 跑 test.one 同症状)—— 触发词路由命中本档, pytest/yapf/coverage 三包定点重装即愈 —— clone3 的 .venv 仍是整目录复制遗留, 预防口径未回溯适用; 事前无路由点, 首个踩 trampoline 的动作就是跑测试。
- **复发**: 4(2026-11-06 04:40, issue 26-11-06-0330 修复轮)—— `commands run test.full` 0.2s 内 FAIL 且只有一行 `uv trampoline failed to canonicalize script path`; 未命中本档的原因是**没先跑 pitfalls 索引路由就直接跑全量**(先看到报错才去 grep `trampoline`), 与前三轮同款漏执行; `uv sync --reinstall-package pytest` → 探 yapf 也坏 → 同法重装, 两包各 0.5s 即愈。
- **复发**: 5(2026-11-06 04:45, clone2 修 issue 26-11-06-0330 轮)—— 55 笔同步后首次 `commands run test.one` 0.3s 内 FAIL, 报错原文只有一行 `uv trampoline failed to canonicalize script path`; 触发词路由命中本档, 探出 pytest/yapf/coverage **三包同坏**, `uv sync --reinstall-package pytest --reinstall-package yapf --reinstall-package coverage` 一次装完即愈 —— 本 clone 的 .venv 同为整目录复制遗留, 预防口径仍未回溯适用。
- **复发**: 6(2026-11-06 06:05, clone2 修 issue 26-11-06-0448 轮)—— `commands run test.one` 0.2s 内单行 trampoline 错; **为什么没命中**: 本轮开工已按路由读 `pitfalls/_index.md` 与 `ops/_index.md`(触发词在册, 路由到位), 但没把「逐个探 console script」的预防自检列为开工动作, 首个踩坑动作就是跑定向测试; 按处置一次定点重装 pytest/yapf/coverage 三包即愈, 三入口探测均出版本号。预防口径(新 clone 不要连 .venv 整目录复制)仍未回溯适用。
- **复发**: 7(2026-11-08, R4 webui-py 收尾轮)—— **坑面首次扩到 tools 级 venv**: `tools/global-traffic-monitor/.venv` 的 `pytest.exe` 报同款 `uv trampoline failed to canonicalize script path`(该 venv 落盘 2026-10-17, 疑复制迁移带来的陈旧绝对路径, 机制与本档 clone 复制同源); 对策同款定点重装 `uv sync --reinstall-package pytest` 后恢复。**为什么没命中**: 事发点在 tools 子目录 venv 而非仓根 `.venv`, 历史六轮复发全在仓根, 触发词路由虽在册但排查动线没把 tools/ 下 venv 纳入「逐个探 console script」的自检面 —— 教训: 复制迁移**任何** venv 都会留陈旧绝对路径, 修法一律 uv 重装入口而不是手工补 exe。
