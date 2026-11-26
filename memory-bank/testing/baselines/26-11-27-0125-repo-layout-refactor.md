# 7036 passed + 6 skipped, TOTAL 31424/0% —— 仓库目录结构重构(测试树三分 + 根目录瘦身)全量基线

> 摘要: 仓库目录结构重构落地后的全量基线
> 基线时间: 2026-11-27 01:25
> 档案: memory-bank/tasks/26-11-26-dev-repo-layout-refactor.md

## 验收数字

`commands run test.full` 实测(2026-11-27 01:23, Windows, rc=0, 168.55s, 工作树 = 重构专题 8 批全部落地且本地提交，工作树干净):

```
TOTAL                                                31424  31424     0%
7036 passed, 6 skipped, 1 warning in 168.55s (0:02:48)
```

与上基线(26-11-26-0606, 7036P/6S, TOTAL 31424/108/11198/94)对账: 通过/跳过数字完全一致; 本专题为纯目录搬家 + 引用更新 + 配置合并, 零逻辑改动, 用例面与语句/分支分母不变 —— 用例数与覆盖零变化。唯一 warning 为 `test_platform_tolerance_guards.py` 既有 SyntaxWarning, 与本专题无关。

## 本改动面

- 测试树三分: `tests/`→`tests/unit/`(366 tracked, 84 处 __file__ 仓库根锚 +1 层)、`tests-real/`→`tests/real/`(65 tracked, marker 四件套防误收集 + lib 探测 PEP 562 惰性化)、`e2e/`→`tests/e2e/`(90 tracked, JS 清单留根)。collect-only 对账: `7042/7179 collected (137 deselected)`, real 全 deselect、e2e 零 .py 误收集。
- 根目录瘦身: `assets/icons/`→`resources/icons/`、`minimal.yml`→`examples/`、`hatch_build.py`→`scripts/`、`env.sh` 删除、`sim_*.py` 九件 + `qb_capture` 三件→`tools/sim/`。
- docker 归置: `config/`→`docker/config/`(部署目录语义, 容器内 `/config` 路径不变)、`.dockerignore` 补窟窿 + 排除闸探针验证。
- pytest 配置合并: `pytest.ini` 删除, 配置平移至 `pyproject.toml [tool.pytest.ini_options]`(含 `real_machine` marker 注册与 `-m "not real_machine"` 默认过滤)。
- 文档回写: AGENTS.md 与 memory-bank 活口径路径更新, 3 处先征询文件(2 处 skill + 1 处规程)仅改事实行, AGENTS.md 收敛到 7989 字符(守住 8000 硬限)。
- 结构守阵 6 项全绿: test_no_ghost_pkg_dirs(1) / test_memory_bank_structure(15) / test_docs_forms(15) / test_ascii_symbol_guard(13) / test_command_drift(4) / test_impact(9)。
- 接缝终审(开发中本地分支态)零发现; `doc.caps` / `kb.check` / `kb.docmap` / `doc.links` 全绿。
- 未验面(如实记录): 真机 `real.guard` 冒烟(会暂停真实种子, 留待环境可用 + 授权)、全量 `dev.e2e`(仅跑 fast 分片 174P/4S 验证路径生效)、docker build(命中计划 R4 既有钩子缺失事实, 非本专题引入)。
