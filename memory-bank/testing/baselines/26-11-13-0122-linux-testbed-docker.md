# 6063 passed + 2 skipped(根) —— linux testbed 容器化改造入库基线

> 摘要: linux testbed 容器化改造入库基线
> 基线时间: 2026-11-13 01:22
**Refs:** memory-bank/tasks/26-11-12-test-linux-testbed.md

## 验收数字

```text
TOTAL                                                27076     65   9462     68    99%
6063 passed, 2 skipped in 201.47s (0:03:21)
```

(实测时点: 修 S4 坑档判别字段回归(KB 守卫 test_kb_pitfall_entries_have_required_fields 拦下, 见本改动面)后收尾 `commands run test.full` 2026-11-13; 2 skipped 为存量 skip; 本切片为本专题组合树的测试数字权威, 其余处一律引用不手抄)

## 本改动面

- **linux testbed 专题 S1-S5 代码面**(7 笔提交: S1 39fdaeb8+c545883c / S2 b9e70cfc+4780168b / S3 60ea780e / S4 5b405bbd+a00c8ef7): `.commands/test/`——`docker/Dockerfile` 六层烘焙新增 + `config.toml` test.linux-env/test.linux/test.linux-e2e 三 task 接容器 + `scripts/linux_env.py`/`linux_e2e.py` 新增 + `linux_ci.py` docker exec 形态重写 + 守阵 `test_linux_ci.py`/`test_linux_e2e.py`; `.commands/mutants/`——`mutants.py` 六条后端 wsl.exe→docker exec + 守阵 `test_mutants.py` 同步。随 S2 落地 5 处 Linux 平台差异修复: `src/auto_qb/infra/utils_parse.py`(is_loopback_host IPv4-mapped IPv6 解包判定, 根因修复)+ `tests/test_tmp_bootstrap.py`/`test_release_pipeline.py`/`test_modules_p5.py`(testbed 性能档)/`test_utils_parse.py` + `tests/fixtures/perf_baseline.json`。
- **S6 回写面(随本专题入库)**: 坑档 `pitfalls/testing/attachments/patching-local-linux-repro.md` 容器配方改写 + 根 `AGENTS.md` linux 三面注记 + 计划 26-11-12-0152 转 Done + issue 26-11-12-0053 转 Done + `.commands/test/config.toml` note 数字单点指针 + 任务档案落数; 另本轮补回 `pitfalls/testing/mutants-shared-mirror.md` 历史条目的判别字段(S4 改写时判别整体上移容器节、历史条目漏挂, KB 守卫条目三字段机检拦下)。
- **本轮含 linux testbed 专题**: S1-S5 容器实测数字(pytest/e2e/变异)单点在任务档案 memory-bank/tasks/26-11-12-test-linux-testbed.md「S1-S5 实测」节; e2e 数字不进基线(锚 Windows 侧), 本切片只记 Windows 侧全量。
