# 包内 task 的命令清单是隐式契约 (改条数会红别处的硬编码用例)

> 摘要: `commands` 包某条 task 的 `run` 条数 / 首个脚本名 / 生成器集合被别处写死 —— 引擎自证压缩用例、`gen_cmd` 守卫、文档里的"共 N 条"都可能据此断言; 收编命令前先搜消费点, 用例改成从声明处现算。
> 触发: 改包内 task 的 run 清单, 收编命令, 命令条数变化, gen_all, kb.index, test_engine 自证压缩, GEN_CMD_BY_SCRIPT

### 收编一条 task 的多条命令 → 别处硬编码的用例会红 (2026-10-03 实证)

- **触发**: 把某条 task 的 `run` 从多条收成一条(如 `kb.index` 由四个生成器收成 `gen_all.py` 一条)。
- **判别**: 命令清单是**隐式契约**, 至少三处按它写死 —— ①`commands` 引擎的
  `test_run_selfcheck_compressed` 借一条"多命令 task"验证自证压缩行(`…(共 N 条, 全量: show <id>)`),
  收成一条后压缩行直接消失; ②memory-bank skill 的 `test_gen_cmd_hints_name_real_tasks` 要求
  「提示说跑 `kb.index` 的脚本必须出现在 `kb.index` 的 run 列表里」; ③文档 / 注释里可能抄着"共 N 条"。
  红点出现在**别处**(另一个 skill 的测试), 报错信息不指向你改的那份 `config.toml` —— 只在 `test.pkg` 才暴露。
- **处置**: 收编命令前**先搜消费点**(按 task id 全仓 grep `.agents` / `.commands` / `tests`)再改;
  用例不要写死条数 / 脚本名 —— 改成从声明处现算(如 `len(C.task_commands(task, ...))` / `gen_all.GENERATORS`)。
  守阵: `test_engine.py::test_run_selfcheck_compressed`(改用 `kb.check` + 动态条数)、
  `test_memory_bank.py::test_gen_cmd_hints_name_real_tasks`(认可 `gen_all` 的间接覆盖)。
