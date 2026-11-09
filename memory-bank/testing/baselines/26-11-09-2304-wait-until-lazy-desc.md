# 5871 —— wait_until 惰性 desc 基座改造后的全量基线

> 摘要: wait_until 惰性 desc 基座改造后的全量基线
> 基线时间: 2026-11-09 23:04

## 验收数字

`commands run test.full` 实测(2026-11-09 23:04, issue 26-11-08-0044 修复批后):

```text
TOTAL                                                26153     41   9102     53    99%
5871 passed, 2 skipped in 172.10s (0:02:52)
```

## 本改动面

- `tests-real/rm*/` 9 文件(+114/-49): ① 9 份 `wait_until` 基座 `desc: str` → `desc: str | Callable[[], str]`, 报错行 `{desc() if callable(desc) else desc}`(callable 只在超时构造报错时求值, str 调用点零漂移); ② 19 处活值 f-string desc(插值内嵌调用)改传 `lambda: (f"…")` —— 首轮顶层判别漏列表推导 1 处(rm04:1735), 评审抓出后补转并改递归深扫复查。
- 意识面: tests-real 真机轨不在 test.full 覆盖内, 本基线只证单测侧零扰动; 真机复跑按既有漂移轮节奏。
- 关联: issue `26-11-08-0044`(状态 Done)、坑档 `pitfalls/testing/ast-migration-fidelity.md`(新增 AST 位置切片条目)。
