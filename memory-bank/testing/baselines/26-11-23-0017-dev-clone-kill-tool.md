# 7024P/6S 覆盖率 99% —— clone_kill 新工具批后基线

> 摘要: dev.clone-kill 新工具批(scripts/clone_kill.py + 守阵新文件 15 用例 + 收录/豁免/坑档治理链)落地后基线; 产品代码零改动, 增量 +15 用例全为本批新守阵
> 基线时间: 2026-11-23 00:17
**Refs:** memory-bank/tasks/26-11-23-dev-clone-kill-tool.md

## 验收数字

`commands run test.full` 实测:

```
TOTAL                                                31412    108  11190     93    99%
7024 passed, 6 skipped, 8 warnings in 117.64s (0:01:57)
```

## 本改动面

- 新增 `scripts/clone_kill.py`(296 行, clone 域残留定点清理; 判据/实杀 import 复用 port_kill 单点, nt/posix 双支, --match+--yes 双闸, 自身/祖先硬排除, 后代过闸连杀)。
- 新增 `tests/test_clone_kill_script.py`(15 用例: 判据单点/候选矩阵/排除集含生产 getpid 支/后代闸/双闸接线/双平台扫描/角落加固)。
- `.commands/dev/config.toml` 收录 `dev.clone-kill`; `AGENTS.md` 进程安全节豁免追加第三处(7995/8000); `memory-bank/pitfalls/ops/dev-run-dry-run-daemon-orphan.md` 新档 + 索引重建。
- 新入池 `memory-bank/issues/26-11-23-0012-bug-port-kill-gbk-mojibake.html`(范围外既有缺陷, 本批零产品代码改动)。
- 相对 26-11-22-2252(7009P): +15 用例 = 本批守阵新文件(tests/test_clone_kill_script.py); 产品面零改动, 其余计数不变。
- 真机端到端冒烟通过: 本会话自有 dummy 探针 spawn→list→match→kill→零残留; 38080/38081(其它 clone 生产实例)全程零出现在候选行(clone 域闸真机背书)。
