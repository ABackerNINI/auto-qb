# 4461 passed + 2 skipped(根) —— test_yamls 样例目录移除收尾

> 摘要: 4461 passed + 2 skipped(根) -- test_yamls 样例目录移除收尾
> 基线时间: 2026-11-01 10:54
**Refs:** memory-bank/issues/26-11-01-0800-test-test-yamls-unknown-rule-keys.html

## 验收数字

`commands run test.full` (150.3s, 2026-11-01 实测):

```text
TOTAL                                                22482    179   7708    151    99%
4461 passed, 2 skipped in 150.31s (0:02:30)
```

口径: 全量 pytest 含覆盖率报表; 相对上基线逐位对比不写, 看差值 `commands run kb.baseline -n 2`。
注记: 首跑(179.5s)撞一次性测量竞态 —— 覆盖率闸门报 98.87% FAIL, 稳定树复跑未复现, 本条数字取稳定树复跑; 同跑还有 issues 索引漂移 1 条(issue 状态改后未重建), `kb.index` 重建后消除。skipped 2 与上基线 10 的差异是环境口径(node 等平台性跳过在本 clone 可用), 非本改动影响。

## 本改动面

- `test_yamls/` 整目录移除(git rm, 7 个 yml: `test_up_dl_limit_tracker.yml` + `test_actions/` 6 份) —— 早期手写测试配置, 未随 schema 演进维护, 规则 spec 含 `RULE_KNOWN_KEYS` 外键(`log_level` 等); 全仓 rg 核实 src/scripts/tests/docs/.github 零引用, 未被任何测试消费(示例配置守阵只扫 docker/config.example.yml 与 helpers 内置样例)。
- `.vscode/launch.json`: 删除指向 `test_yamls/test_up_dl_limit_tracker.yml` 的调试配置(4 → 3 个)。
- `.dockerignore`: 移除 `test_yamls/` 行。
- `AGENTS.md`: 红线节示例指引 `minimal.yml`/`test_yamls/` → `minimal.yml`(`doc.caps` 复查 7268/8000 PASS)。
- 文档回写: `memory-bank/config-reference/keys.md`(测试配置样例节改写)、`memory-bank/pitfalls/ops/prod-files.md`(示例指引)、`memory-bank/conventions/code-style.md`(夹具例外行)、`memory-bank/rule-system/conditions-and-actions.md`(choose 样例行改移除注记)。
- issue `26-11-01-0800-test-test-yamls-unknown-rule-keys`: Open → In Progress → Done, 复验/修法/验证留痕在该件。
