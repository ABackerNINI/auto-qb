# 基线 · 1725 passed + 1 skipped —— 文件访问层审查修复轮(casefold 边界 + fs 三态消费)

> 摘要: plan 26-09-27-1407 审查轮(对照 d50fa12 实施)发现两处 P2 并当轮修复: ①`map_to_container`
> 按 casefold 折叠后前缀长度硬切原串 —— 变长折叠字符(ß→ss、İ)进 `fs.path_map` 的 from 时切片
> 错位 ⇒ 容器路径错误 ⇒ `exists` 误判「不存在」(报告 §05 红线窄条件重演面), 修复 = `_fold_prefix_len`
> 沿原串逐码点累加折叠定位边界; ②routes/fs.py 五处两态布尔消费在 Mapped miss 时 UNDETERMINED
> `__bool__` 抛 TypeError ⇒ 裸 500, 修复 = `_determinable` 三态消费单点 → 带原因语义化 404。
> 数字取自修复后全量(`commands run test.full`)。
> 基线时间: 2026-09-27 17:12
> 档案: memory-bank/plans/26-09-27-1407-plan-docker-fs-wrapper-pathmap.html(变更记录 26-09-27-1712 条)

- **测试增量**: +2 回归 —— `test_mapped_casefold_expanding_prefix`(ß 前缀: 命中 / 展开变体大写 /
  根命中 / D:/Straße2 边界不命中) + `test_fs_endpoints_unmapped_root_semantic_404`(Mapped 白名单内
  未命中映射 → dirs/mkdir/open-path 四路径语义化 404 而非 500); tests/test_file_access.py 与
  tests/test_web.py 头部「## 测试计划」同步。

TOTAL 1725 passed + 1 skipped / 91%(11546 语句 / 846 未覆盖, test.full 16.0s)
对比前基线(26-09-27-1620): 1723 passed + 1 skipped / 91%(11531 语句) —— +2 恰为本轮新增回归,
既有用例(含既有 20 条映射用例: 边界 / 根命中 / 尾斜杠 / `\\?\` / scandir 回译)零回归。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。
