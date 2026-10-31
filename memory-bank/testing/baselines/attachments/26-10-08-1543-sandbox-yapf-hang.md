# 2815 —— 沙箱内 yapf 挂住取证与兜底 (引擎整树超时杀 + 项目内 yapf)

> 摘要: 「沙箱内 yapf 挂住/刷磁盘」修复轮收尾基线。改动: `run.py` 新增 `_kill_tree` + `_shell` 改 Popen(超时杀整棵树)、`pyproject.toml` dev 组钉 `yapf==0.43.0`、`dev.fmt` 与 fmt gate 的 timeout 收到 60s; 新增守阵 1 条(红验)。全量套件除 2 条**存量、与本件无关**的 KB 守卫外全绿。
> 档案: memory-bank/tasks/26-10-08-deps-sandbox-yapf-hang.md
> 基线时间: 2026-10-08 15:43

**Refs:** memory-bank/tasks/26-10-08-deps-sandbox-yapf-hang.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2815 passed + 4 skipped + 2 failed, 覆盖率 TOTAL 99%**(16479 语句 / 162 未覆盖 / 5696 分支 / 146 partial; 门槛 98% 达标)
- **耗时**: 43.87s
- **新增/修正用例**: `.agents/skills/commands/scripts/test_engine.py` +1(`test_shell_kills_process_tree_on_timeout`, 红验: 抽掉 `_kill_tree` 行即红); `tests/test_commands_engine.py` 的假子进程 `_FakeProc`/`_patch_run` 同步改为 **Popen 形态**(实现从 `subprocess.run` 换成 `Popen`, 假对象不跟着改就会"看着在测、其实真起子进程" —— 首跑即由 `tests/sidefx.py` 的 POPEN 台账抓到 3 条越界)。
- **2 failed 是存量守卫违规, 与本件无关**: `tests/test_memory_bank.py::test_wording_guard_is_green_on_current_kb` 与 `::test_number_guard_is_green_on_current_kb` —— 违规源在 `memory-bank/activeContext/26-10-08-1130-webui-qb-traffic-gap-hatch.md:13`(手抄裸 passed 数字), 来自**另一个 clone 的会话**(经 Gitee develop 同步入境), 既非本件改动也非本 clone 产出。**按范围守恒不动它**(与 [26-10-08-1016](26-10-08-1016-mutants-config-validator-strings.md) 记录的同源现象一致: 当时经用户裁定「暂时不用管」)。

## 说明

- **相对上基线的参考**: 与 [26-10-08-1307](26-10-08-1307-hr-exclude-steady-s4.md) 比, passed −2 恰等于上面 2 条存量失败(收集总数一致); 要看差值跑 `commands run kb.baseline -n 2`。
- **代码事实变更**: 有 —— ①`commands` 引擎 `_shell` 的超时语义(杀整棵进程树, 单点 `run.py::_kill_tree`); ②`dev.fmt` 改用项目内 yapf(dev 依赖组钉 `0.43.0`, `uv.lock` 已更新)。
- **未决残留(用户侧)**: yapf 语法缓存目录 `%LOCALAPPDATA%\Google\YAPF\Cache\0.43.0` 的清理与沙箱白名单放行 —— agent 侧对这两个路径的写/删均被拒(实测)。见坑档 [sandbox-tool-cache.md](../../pitfalls/testing/sandbox-tool-cache.md)。