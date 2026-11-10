# 5939 passed, 2 skipped —— recycle daemon 实例级证据链四波实装批实测

> 摘要: recycle daemon 实例级证据链四波实装+真机 P7 收口实测: 5939 passed, 2 skipped (173.75s), 覆盖率 99% (26638 stmts / 50 miss)
> 基线时间: 2026-11-11 02:25
**Refs:** memory-bank/issues/26-11-07-0528-feat-recycle-daemon-roster-machine-wide.html, memory-bank/plans/26-11-10-0318-plan-recycle-daemon-instance-evidence.html, memory-bank/tasks/26-11-10-backend-recycle-daemon-instance-evidence.md, memory-bank/pitfalls/backend/recycle-daemon-p7-evidence-chain.md

## 验收数字

```text
TOTAL                                                26638     50   9320     61    99%
5939 passed, 2 skipped in 173.75s (0:02:53)
```

(实测时点: HEAD 76c056ee + 本批回写工作树, `commands run test.full` 2026-11-11 02:25; 较上一基线 26-11-10-0132 的 5883: +56 = recycle daemon W1a/W1b/W2a/W2b 四波新用例与守阵, 2 skipped 为存量 skip 不变; 本轮 W3b 为纯知识库回写, 零代码改动, 数字与 W2b 收口实测一致)

注: 2026-11-11 合流 rebase 后提交对象重写——fbcf4117→1f36dd18, a3c0fc1e→3fd8092c, 2ca40f43→eba5ba3b, 76c056ee→972d7cd5, 202c807e→2a26dd65, f3356c1f→9ae076de; 文中旧 hash 为 pre-rebase 引用, 新 hash 见 git log。

## 本改动面

- **本轮(W3b 回写收口)零代码改动**——只有知识库面: issue 26-11-07-0528 翻 Done(复验行+修复后补充), 计划 26-11-10-0318 翻 Done(§10 实装收口行+§03.2 评审加固注记), 新建坑档 pitfalls/backend/recycle-daemon-p7-evidence-chain.md, 既有坑档 relocate-window-machine-roster.md 追加 L1 上线段, 任务档案 26-11-10-backend-recycle-daemon-instance-evidence 翻 Done(R1-R4 进度日志), kb.index 重建。
- **被测代码面**(W1-W2b 四波, 挂接提交 fbcf4117/a3c0fc1e/2ca40f43/76c056ee, 本基线首次整树收录): `src/auto_qb/tools/recycle_daemon.py` 观测通道函数族+`_Observation` 状态机+L1/L2/L3 三层判据接线+复验同级升级+告警 60s 节流; `src/auto_qb/infra/relocate_journal.py` obs 文件 helper; `tests/test_recycle_daemon.py` 六场景 7 测试与桩注入面。
- 真机 P7 三场景 3/3 PASS 零产品缺陷(证据根 `tests-real/.work/p7_w3a/`, gitignored, 不进基线): S1 死亡→开窗+首写 2.63s / S2 复活 qb_back 零落盘 / S3 通道故障退 L2 节流留痕, S1 2.63s vs S3b 37.54s 同机对照。
