# 5888 passed + 2 skipped —— 修复 issue 26-11-10-0456 纯桩守阵批全量绿

> 摘要: 修复 issue 26-11-10-0456 纯桩守阵批全量绿
> 基线时间: 2026-11-10 06:17

## 验收数字

```text
TOTAL                                                26198     45   9134     57    99%
5888 passed, 2 skipped in 170.21s (0:02:50)
```

(实测时点: HEAD c1200d7b + 本轮工作树改动, `commands run test.full` 2026-11-10 06:17; 全绿, 覆盖率 99%)

## 本改动面

- **唯一代码文件**: `tests/test_free_port.py::test_hold_run_discards_run_whose_offset_is_refused` —— 由「真实 socket 代理 + 单点注入 10013」改为纯合成 socket(零真实 bind), 断言加强(拒绝落在第一次尝试第二位 / 返回段不来自被丢弃的尝试 / 被拒段全关 / 返回段仍持有); 文件头 docstring 测试计划清单同步; `tests/_test_ports.py::hold_run` 零改动。
- **记录面**: issue 26-11-10-0456 翻 Done(补复验 / 修复后补充 / kicker 改已修口径); 坑档 `pitfalls/testing/consecutive-port-run.md` 复发 +1 并补「守阵用例本体也不许把真实端口环境当判据」段, 摘要与触发词同步后 `kb.index` 重建。本轮零新增用例、零生产代码改动。
- **验证**: 确定性红验(修复前模拟并行抢口 ⇒ 判红) + 修复后双探针(所有真实 bind 一律拒绝仍绿且真实 bind 次数 0 / 把 hold_run 换成不丢弃坏段的坏实现 ⇒ 判红) + 单文件守阵全绿(副作用台账 BIND 条数下降、越界 0) + `test.quick` 全量并发全绿 + `test.full` 全绿。真机不适用(纯桩可验)。
- **环境**: 开工同步快进 21 笔(b8afa3ad→fa00a0b9), 收尾前再快进 1 笔(fa00a0b9→c1200d7b, 纯协议文档); 两笔远端推进均非本轮改动。
