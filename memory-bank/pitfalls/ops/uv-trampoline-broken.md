# uv trampoline 失效: .venv/Scripts 下 exe 报 failed to canonicalize script path, env.sync 不自愈

> 摘要: `.venv/Scripts/` 下的工具入口 exe(pytest.exe / yapf.exe 等)是 uv 的 trampoline 薄壳, 一旦壳与目标 venv 的相对位置/路径解析对不上就整体失效: 直接跑 `<tool>.exe` 报 `uv trampoline failed to canonicalize script path`, 而 `uv sync`(含 `commands run env.sync`)**不会重建这些壳** —— 不自愈。解法是删掉失效的 exe 让 uv sync 按 `--reinstall-package` 重装该包, 或改走 `uv run python -m <module>` 等价入口。
> 触发: uv trampoline, canonicalize, pytest.exe, yapf.exe, .venv/Scripts, 打不开工具, env.sync 不自愈, uv sync --reinstall-package

### 直接调 .venv/Scripts 下的工具 exe 报 trampoline 错, env.sync 跑完依旧

- **触发**: 本仓实施期(2026-11-06, mypy 接入计划 S1-S5)实测: `.venv/Scripts/` 下
  `pytest.exe` / `yapf.exe` 等入口直接执行报
  `uv trampoline failed to canonicalize script path`; 环境没坏(包都在), 坏的只是
  **入口 exe 壳**。clone 目录被移动/改名/整树拷贝后尤易触发(trampoline 记录的路径
  解析不再成立)。
- **判别**: 报错原文含 `uv trampoline failed to canonicalize script path`; 同包用
  `uv run python -m <module>` 跑是好的 —— 说明只有壳失效, 不是包/依赖损坏。
  `uv sync` 跑完再试 exe **仍然报错**(sync 不检查不重建这些壳), 即"sync 不自愈"。
- **处置**: ①**重建壳**: 删掉失效的入口 exe 再让 uv 重装该包, 例如
  `rm .venv/Scripts/pytest.exe && uv sync --reinstall-package pytest`(yapf/mypy 等同理,
  包名以 pyproject 依赖名为准); ②**等价替代**(不想动 venv): 一律走
  `uv run python -m pytest` / `uv run python -m yapf` 形态 —— 本仓 `commands run <task>`
  的封装多数已按此形态收录, 优先走 task id 就绕开了裸 exe。
- **守阵**: 无专项守阵; `commands run test.full` 全绿可作「壳失效但 -m 入口可用」的旁证。
- **复发**: 1(2026-11-06 首记)。
