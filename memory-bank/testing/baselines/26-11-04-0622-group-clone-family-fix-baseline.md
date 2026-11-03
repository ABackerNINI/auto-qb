# 5123 passed, 10 skipped —— group 克隆描述符族标记修复后全量基线

> 摘要: group 克隆描述符族标记修复后全量基线
> 基线时间: 2026-11-04 06:22
**Refs:**

## 验收数字

`commands run test.full` 实测输出誊写：

```text
TOTAL                                                23933    229   8184    171    99%
5123 passed, 10 skipped in 193.10s (0:03:13)
```

口径：仓库根全量；上一行为 test.full 的覆盖率 TOTAL 表原样誊写，下一行为 pytest 汇总行。分支 `develop`，HEAD `0c2571e1`，工作树含本轮未提交的 group 族标记修复与守阵改动。
相对上基线（`26-11-04-0507`，5119 passed / TOTAL 23893）增量 +4 passed / +40 stmts = 本轮 group 两态电池与签名守卫新增断言所在。

## 本改动面

代码面（issue 26-11-03-1035）：`src/auto_qb/webui/static/shared/columns.js` —— `WIN_SRC_DOC` 加 `family: "doc"`、`winSrcContainer` 工厂加 `family: "container"` 源族标记；`src/auto_qb/webui/static/shared/columns_grid.js` `_rowWindow` 分流判据由对象身份比较（`=== WIN_SRC_DOC`）改为 `family !== "container"`（group 克隆描述符曾被误判进容器分支：抽屉关全量渲染 / 抽屉开切片跟抽屉滚）。
测试面：`tests/webui_dom_page_support.py` node 探针新增 group 两态电池（抽屉关 h=0 / 抽屉开滚 5000 两态窗口逐位相同）+「三 kind 注册齐全」补族断言；`tests/test_webui_static_dom_page_layout.py` 签名守卫加两条（禁 `=== WIN_SRC_DOC` 回潮 / 必须含 `.family` 分流）。
文档面：issue 置 Done 并回写实际修法；本基线切片；pitfalls/testing/tmpdir.md 复发 2（开工 test.quick 踩外部 TMPDIR 拒收）。
