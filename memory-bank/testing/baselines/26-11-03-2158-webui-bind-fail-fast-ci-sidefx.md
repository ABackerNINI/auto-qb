# 4994 passed + 10 skipped(根) —— 生产诊断探针测试副作用修复全量基线

> 摘要: 生产诊断探针测试副作用修复全量基线(CI 越界 POPEN ss -ltnp 消除)
> 基线时间: 2026-11-03 21:58
**Refs:** memory-bank/tasks/26-11-03-webui-bind-fail-fast.md

## 验收数字

`commands run test.full` 实测(Windows, 并行 + 覆盖率):

```text
TOTAL                                                23292    185   7948    158    99%
4994 passed, 10 skipped in 211.04s (0:03:31)
```

口径: 根目录全量(`pytest.ini` 默认并行 + 覆盖率; warnings 已归零, 见下条改动面); wrapper 外层耗时 213.6s; 与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。

## 本改动面

- `tests/test_web_admin.py`: `test_webui_module_start_raises_bind_error_when_port_taken` 注入 `describe_port_owner` 替身 —— 消除 Linux 侧真实 `ss -ltnp`(sidefx 越界 POPEN); 并新增「探针仍被调用一次(host/port)」断言, 钉住诊断接线。
- `tests/test_port_owner.py`: Linux 命中用例补精确 argv 断言(`["ss", "-ltnp"]`)。
- `tests/test_tmp_bootstrap.py`: 模块 docstring 加 raw 前缀, 清掉 `H:\Temp` 的 `\T` 无效转义 —— 编译期 `SyntaxWarning` 消失(运行汇总 warnings 归零), 字面语义与候选根/拒收判据均未动。
- 零 `src/` 改动; `tests/sidefx.py` 放行清单未新增条目(走「消除」而非「登记」)。

