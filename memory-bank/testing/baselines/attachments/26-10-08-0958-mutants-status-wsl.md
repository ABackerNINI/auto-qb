# 2783 —— 修 issue 26-10-08-0758(mutants.status 在 WSL 下恒报 mutmut=no)基线

> 摘要: 修 `mutants.status` 在 WSL 下的失真 —— 本机 WSL 登录壳实为 zsh, `cd` 只改真实 cwd 而 `$PWD` / `$()` 子壳仍按「启动目录」解析相对路径, 四条回显全错(`mutmut` 恒报 no / `mutants` 报空 / `head` 读到主仓而非镜像)。把回显改成 `cd {mq} && <直接命令>` 直连形态(与 `cmd_run` 一致), 并给末行 `only_mutate` 加 fallback。**零 `src/`、零 `tests/` 改动**(只动 `.commands/mutants/scripts/mutants.py` 与文档)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-08 09:58

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## test.full 实测

- 分支: `develop`(工作树含本专题全部改动时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2783 passed + 4 skipped, 2 failed, 覆盖率 TOTAL 99%**(16476 语句 / 164 未覆盖 / 5694 分支 / 148 partial; 门槛 98% 达标)。2 failed 为 `tests/test_memory_bank.py` 的存量守卫红(`test_wording_guard_is_green_on_current_kb` / `test_number_guard_is_green_on_current_kb`), 根因是无关文件 `activeContext/26-10-08-0713-webui-qb-traffic-head-layout.md` 的裸 passed 数字(已 `git stash` 回退验证: 干净基线上同样 2 failed, 与本轮改动无关)。
- 相对上基线 [26-10-08-0939](26-10-08-0939-mutation-audit-standing-table.md)(2785 passed + 4 skipped, 同 16476 / 164 / 5694 / 148): 覆盖口径**逐位持平**(本轮零 `src/`、零 `tests/` 改动); passed 数差 2 即上述存量守卫红。

## 文档守卫实测

- `commands run kb.index`: 重建 20 个生成物。
- `commands run kb.check`: 主键纪律(520 份文档 / 274 个专题)· 认领链(双向闭环)OK; 回写守卫 1 项新增红(即上述无关文件的裸 passed 数字, 存量); 存量 cap 债务未增/未减(不拦提交, 转告用户另开会话清理)。
- `commands run doc.links` 无坏链; `commands run doc.drift` 0 处手抄命令; `commands run doc.caps` 无**新增**债务。

## 对照判据(后续沿用)

- `test.full` 覆盖口径以本切片(16476 / 164 / 5694 / 148 / TOTAL 99%)为对照点。
- 已知存量红 2 项(`test_memory_bank.py` 两个守卫, 源于 `activeContext/26-10-08-0713` 裸 passed 数字)—— 修它属另一次改动, 本轮未动(范围守恒)。
