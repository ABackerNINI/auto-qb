# 平台差异 · 形态④ 平台相关路径 API(外迁)

> 摘要: `pitfalls/testing/patching.md`「④ 平台相关的路径 API: `os.path.normcase` 在 Linux 是恒等函数」节原文整体外迁(2026-11-05 压缩), 正文原样照搬, 标题降一级以避开坑档条目扫描。
> 触发: normcase, posixpath, ntpath, sim_fsmock, _key, 大小写折叠, 路径语义, D4, 平台路径 API

## ④ 平台相关的路径 API: `os.path.normcase` 在 Linux 是恒等函数

- **触发**: 用 `os.path.*` 做大小写 / 分隔符归一(2026-09-22 Linux CI 红了 `test_fsmock_long_path_prefix_and_case`)。
- **判别**: `os.path` 在 Windows 是 `ntpath`、在 Linux 是 `posixpath`, 而 **`posixpath.normcase` 是恒等函数**
  (POSIX 本来就区分大小写)⇒ `scripts/sim_fsmock.py::_key` 用 `os.path.normcase` 做大小写折叠,
  在 Linux 上**静默退化成大小写敏感** ⇒ 把存在的文件报成缺失 ⇒ **D4 判据全假**(判据绿得发亮却什么都没测到)。
  **修法: 该 mock 模拟的是 NTFS 语义(语料抓自 Windows 真机), 归一必须固定 ⇒ 显式 `ntpath.normcase`**
  (纯字符串模块, 两平台同语义)。
  **泛化: 用 `os.path.*` 时凡涉及"大小写 / 分隔符"语义, 都要先问一句"我到底在模拟哪个文件系统"。**
  **复发** +1(2026-11-07)—— 这次方向相反: **生产码 `_norm`(relocate_units)跟随平台是对的**(§3.3
  设计口径: qB 在哪平台跑, save_path 就是哪平台形态, 归一自洽), 红的是**测试把 Windows 侧折叠结果
  写死成期望值**(`test_under_alias_root_dual_criteria` 断言 `== "r:/media"` 小写盘符, Linux 上
  normcase 恒等 ⇒ 本机绿 CI 必红)。修法: 断言改对 `ru._norm(root)` 平台中立项 —— "命中返回该根的
  归一形"这个契约两侧一致, 绑平台的只有折叠结果本身。
  (为什么没命中: 写用例在 Windows 本机验收, "归一跟随平台"的设计口径记得, 落断言时却又写回本机
  观察值 —— 判别法只被用来审"生产码该不该换 ntpath", 没审"测试期望值同样不能绑平台折叠结果"。)
- **处置**: ⚠ 同类**未修**: `scripts/sim_qb.py::_norm`(B2 路径逃逸判定)仍是 `os.path.normcase` ——
  它在 Linux 上**更严格**(只误拒、不会放过逃逸), 且 `is_within` 目前**无测试覆盖**,
  故按范围守恒未动(已补守阵, 见下条)。
