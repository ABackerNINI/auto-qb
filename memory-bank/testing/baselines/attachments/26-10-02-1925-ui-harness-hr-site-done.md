# 基线 · 2292 passed + 3 skipped / 99% —— ui_harness --hr-site v3 替身重写轮

> 摘要: issue 26-10-02-1900 认领修复, scripts/ui_harness.py `_mk` 重写为 v3 四行判定表 7 场景轮转(枚举成员 + 构造 kwarg 双断点一并修); 真跑桩起盘成功, 六个 hr_safety_src 桶全覆盖(failed 红档首次入桩); 生产代码零改动。新坑 stubs-sim.md「替身引用生产 API 符号」条目。切片 activeContext/26-10-02-1925。
> 基线时间: 2026-10-02 19:25, develop @ 2a9932d9(收尾回写未提交工作树, test.full 实测)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2292 passed + 3 skipped / 99%**(13,259 语句 / 86 未覆盖 / 4,442 分支 / 81 partial,
test.full 37.0s, rc=0)。
相对上一切片(26-10-02-1828: 2291 passed + 3 skipped / 99%, @ d354745b)+1 passed —— 本轮唯一
Python 改动在 scripts/ui_harness.py(pytest 面之外), 增量与本轮改动无关(d354745b → 2a9932d9
间的远端推进)。
