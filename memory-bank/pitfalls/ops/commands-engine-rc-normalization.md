# commands 引擎把任务失败退出码归一成 1, rc 细分信号过不了闸门

> 摘要: 任务脚本用非 0/1 退出码传细分状态(如待评审 rc=3)时, 经 `commands run` 引擎转发恒变 1 —— rc 信号静默丢失, 消费方按 rc 分级的设计整层失效
> 触发: run.py 退出码,任务失败码,闸门 rc,rc=3,细分退出码,脚本 rc 语义,FAILED 归一化,经引擎的 rc

**Refs:** memory-bank/tasks/26-11-11-docs-ship-gate-prerun.md

### 事件 (2026-11-19, 闸门待评审降级批)

- **触发**: 脚本(`.commands/*/config.toml` 的 run)以非 0/1 退出码表达细分状态, 且消费方不是直接 shell 调用者而是**闸门/其它经引擎的调用方**。实证: check_review_trace.py 按契约出 rc=3(待评审), ship.gate 预跑按 rc==3 降级不拦 —— 自验时预跑仍红, 闸门记录 rc=1; 直跑脚本 rc=3 正确, 经引擎就丢。
- **判别**: 直跑脚本 rc 正确、经 `commands run` 后恒 1 → 引擎归一化面。机制两处: `run.py` 任务失败路径 `return FAILED`(FAILED=1), 且 `_shell` 只回 `proc.returncode == 0`(真值 rc 根本不出函数)。不是脚本 bug —— 脚本 rc 语义再对也传不过引擎这一层。
- **处置**: 细粒度状态走**输出协议行**(行首机器标记), 消费方匹配标记; rc 只承载 0/非 0。引擎对协议行有既有先例(`run.py._protocol_lines`), 失败输出尾(末 20 非空行)会随失败透传给闸门, 标记行不会丢。脚本文档可同时声明细分 rc(直调面/测试用), 但凡经引擎的消费方一律按标记判定。
- **实例**: `check_review_trace.py` 的「rc=3 + 行首标记 `评审留痕[待评审]:`」双机器面(契约单点见其模块头「rc=3 待评审」节), `gate.py._is_pending_failure` 消费标记。
- **守阵**: `test_gate.py::test_pending_prefix_pinned_across_packages`(消费侧字面量钉在产生侧) + `test_review_pkg` TraceGateTest rc=3 断言(直调面) —— 两侧任一漂移即红。
