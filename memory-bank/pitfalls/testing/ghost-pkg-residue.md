# 幽灵包守阵误红: 迁移残壳只剩 __pycache__

> 摘要: 包源码迁走后, 旧目录在 git 里已删但磁盘残留只含 `__pycache__` 的空壳目录 (gitignored 未跟踪, 检出/同步不清掉), 被幽灵包守阵 (test_no_ghost_pkg_dirs) 判红 —— 是环境残留不是代码缺陷, 整目录删除即绿。
> 触发: 跑 pytest 时 test_src_has_no_ghost_pkg_dirs 红, 报 src/ 下某目录; 或排障时发现某包「还在」但 import 不到。

### 迁移残壳触红幽灵包守阵 (环境残留, 非代码缺陷)

- **触发**: 包迁移/改名 (如 26-09-22 web→webui) 后, 旧包目录在 git 已删, 但本 clone 工作目录残留旧包的 `__pycache__` 字节码空壳 —— 多 clone 各自检出, 残壳**不同步**: 本 clone 删了别的 clone 可能还留着。2026-10-01 实证: 本 clone 残留 `src/auto_qb/web` 与 `src/auto_qb/web/routes` 两个只剩 `__pycache__` 的残壳, 触红并行新落的守阵 (2101976a)。
- **判别**: `git ls-files src/<路径>` 为空 (git 里已不存在) 但磁盘目录仍在、内部只有 `__pycache__` 无任何 .py; 守阵红并列出具体路径 —— 守阵判据 = 「子树含 `__pycache__` 却没有一个 .py」(tests/test_no_ghost_pkg_dirs.py, 纯静态)。看着像「包还在」会误导排障, 实为历史产物, 当前测试面已不再导入它。
- **处置**: 按守阵 prescribed **整目录删除**残壳 (`rm -rf` 报红路径) —— 环境清理, 非代码改动, 不入提交; 删后重跑该守阵确认绿。同日第二次目击 (第一次 core/mixins, issue 26-10-01-1946, 残壳「删过两次被目击再生」后复现取证确认是历史产物不会再生), 守阵两次都当场抓住 —— 守阵有效; 其它 clone 留有同款残壳会同样标红, 同法处置。
- **守阵**: tests/test_no_ghost_pkg_dirs.py (src 下含 __pycache__ 而无 .py 的目录即红)。
- **复发**: +1 —— 2026-10-02(backend-issues-clearance 阶段 1) test.full 首跑再撞 `src/auto_qb/core/mixins` 残壳, 按处方整目录删除即绿。为什么没命中: 残壳由多 clone 检出不同步产生, 流程上无法预防, 属守阵预期捕获路径(三度当场抓住), 非路由/执行失误。
