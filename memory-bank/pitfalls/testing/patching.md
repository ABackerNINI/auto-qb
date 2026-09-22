# 平台差异与打桩 (Windows / Linux)

> 摘要: 「Windows 全绿 / Linux 全红」的四类根因与"归错类比不修更危险"的教训 —— 平台相关测试必须以 `monkeypatch` 固定平台。
> 触发: CI 红, Linux CI, 平台差异, monkeypatch, WSL, normcase, dir_fd, 平台专属模块

### 「Windows 全绿 / Linux 全红」: 本机跑通不等于 CI 跑通 (Linux CI 一次红 4 项, 真根因三个)

- **触发**: 本机全绿但 CI 红。
- **判别**: 三个根因 ——
  ① **POSIX 的 `shutil.rmtree` 走 fd 版实现**(删目录内条目时传**纯文件名 + `dir_fd`**,
  而 Windows 不支持 dir_fd 走拼接绝对路径的另一支)⇒ 记账器只记 `path`,
  同一份临时目录清理在 Linux 记成 `'state.json'`、realpath 落到 CWD ⇒ 判越界。
  修法: 记账前用 `_with_dir_fd()` 把 `dir_fd` 补成绝对路径(Linux 读 `/proc/self/fd/<fd>`, macOS 用 `fcntl.F_GETPATH`)。
  ② **`utils.atomic_write("")` 不是"什么都不写"** —— `abspath("")` 是 CWD, `dirname` 再取一级就成了
  **CWD 的父目录** ⇒ 往仓库外丢 `.tmp`(本机长期误判成"IDE 临时文件"的越界项就是它);
  修法是对空路径直接 `raise ValueError`。
  ③ **平台专属模块导入 / 真实 socket 连接** —— `PlatformChannel("win32")` 内的 `import winreg` 在 Linux 抛
  `ModuleNotFoundError`(调用方只 catch `OSError`)⇒ 用例改为 `monkeypatch.setitem(sys.modules,"winreg",替身)`;
  patch `qbmanager.Client` **无效**(`connect()` 走的是 `qbclient._new_client`)⇒
  **patch 真正被调用的名字**, 与网络解耦。
- **处置**: 见下条判别法。

### 判别法: 四类"本机绿不算绿"

- **触发**: 判断一条失败是不是平台差异。
- **判别**: 凡是"**记账器判越界 / 平台专属模块导入 / 真实 socket 连接 / 平台相关的路径 API**"这四类,
  本机绿**不算绿**。平台相关测试必须以 `monkeypatch` **固定平台**(测试主体是"平台逻辑"而非"当前真实平台");
  纯 Windows 行为(长路径 `\\?\` 前缀)直接断言在 Linux CI 上**必失败**。
- **处置**: 按四类分别用 `monkeypatch.setitem(sys.modules, …)` / 补 `dir_fd` 绝对路径 / patch 真实名字。

### ④ 平台相关的路径 API: `os.path.normcase` 在 Linux 是恒等函数

- **触发**: 用 `os.path.*` 做大小写 / 分隔符归一(2026-09-22 Linux CI 红了 `test_fsmock_long_path_prefix_and_case`)。
- **判别**: `os.path` 在 Windows 是 `ntpath`、在 Linux 是 `posixpath`, 而 **`posixpath.normcase` 是恒等函数**
  (POSIX 本来就区分大小写)⇒ `scripts/sim_fsmock.py::_key` 用 `os.path.normcase` 做大小写折叠,
  在 Linux 上**静默退化成大小写敏感** ⇒ 把存在的文件报成缺失 ⇒ **D4 判据全假**(判据绿得发亮却什么都没测到)。
  **修法: 该 mock 模拟的是 NTFS 语义(语料抓自 Windows 真机), 归一必须固定 ⇒ 显式 `ntpath.normcase`**
  (纯字符串模块, 两平台同语义)。
  **泛化: 用 `os.path.*` 时凡涉及"大小写 / 分隔符"语义, 都要先问一句"我到底在模拟哪个文件系统"。**
- **处置**: ⚠ 同类**未修**: `scripts/sim_qb.py::_norm`(B2 路径逃逸判定)仍是 `os.path.normcase` ——
  它在 Linux 上**更严格**(只误拒、不会放过逃逸), 且 `is_within` 目前**无测试覆盖**,
  故按范围守恒未动(已补守阵, 见下条)。

### ❗⑤ 归错类比不修更危险 —— 判断"该不该跟随平台"前, 必须先看路径是**怎么来的**

- **触发**: 顺着上一条的"同类未修"去推(2026-09-22 我自己踩的)。
- **判别**: 我曾给出"`sim_qb` 也可以统一到 `ntpath`"的**错误建议**, 因为默认了它的路径是"语料里的 Windows 假路径";
  实际 `sim_qb.py:480` 是 `fs_root = os.path.join(run_dir,"fs")` + `os.makedirs`(**宿主真实目录**),
  `save_path` 一律由它拼出, 语料档还经 `resolve_fsroot` 把 `<FSROOT>` 解析到同一个 `fs_root`
  ⇒ 路径是**宿主形态** ⇒ `os.path.normcase`(Win 折叠 / Linux 恒等)+ `os.sep` **正是所需**,
  两平台各自自洽, **改成 `ntpath` 反而坏**(实测真子路径 `True→False`)。
  **判别法(动手前先做这两问)**:
  ① 这条路径是 `os.makedirs` / `os.path.join` 出来的**真实宿主路径**, 还是仅供查表的**纯字符串**(mock 表 / 语料假名)?
  **前者跟随平台, 后者固定为它要模拟的那个 FS 的语义。**
  ② "换 normcase" **不是单点改动** —— 折叠与分隔符必须**同源**:
  只换折叠、分隔符还是 `os.sep` ⇒ 混分隔符 ⇒ 全线误拒(**fail-closed**, 明显但难查);
  两者都换到**生产代码** ⇒ Linux 上 `/x/Media` 与 `/x/media` 被当成同一目录 ⇒ **越界放行**
  (**fail-open**, 静默且方向反了)。
  **根因(为什么错得出来)**: `is_within` **没有 pytest 覆盖**(只有 `sim_qb.py --self-test`, CI 不跑)⇒
  没有任何守阵能在改完那一秒判红, 只能靠读代码推断。
- **处置**: **泛化: 「只在 `--self-test` / 手动脚本里跑过」的判据等于没判据** ——
  它要真起 HTTP **且**真装 `qbittorrentapi`(没装就整段 `return 0`), CI 从不执行 ⇒ 平台差异、回归全都**静默**。
  已把 B2 段下沉进 `tests/test_sim_corpus.py::test_safe_delete_rejects_path_outside_fs_root`
  (直接打方法, 不起服务, 两平台 CI 都跑), 并比原自检多钉两条: 拒绝时**文件没被真删** + **记进 `violations`**。
  红验: `is_within` 改恒 True ⇒ 该用例 `DID NOT RAISE` 立刻红。
  B3 / D4 两段**同属这一类**, 也已下沉(B3 阈值改 *99 ⇒ `DID NOT RAISE`; D4 改成"假装删了" ⇒ `assert 0 > 0`)。
  **❗下沉时的两个坑(踩过)**:
  ① **阈值类判据必须钉两侧** —— 只钉"超了要拒", 有人改成 1 倍(更严格)也绿;
  只钉"2 倍不拒", 改成 10 倍(形同虚设)也绿。
  ② **"磁盘上少了文件"类判据必须走 `--source=synthetic`** —— 语料档是 `fs-mode=mock`,
  磁盘上根本没有文件 ⇒ `_walk()` 前后都是 0 ⇒ 断言**恒假**(比不测更糟);
  用例里显式断言 `before > 0`, 把"没物化"变成**红**。

### 本机复现 CI 的平台差异(比推上去等 CI 快得多)

- **触发**: 怀疑平台差异, 想在本机验证。
- **判别**: WSL 里 `wsl -- bash -c '...'` 复制一份仓库(排除 `.venv` / `.git`)、`uv sync`、
  `uv run pytest tests -q` 即可(加 `-p 3.12` / `-p 3.13` 还能对上 CI 矩阵版本)。
  ❗**WSL 可能被安全策略拦在黑名单里**(2026-09-22 实测: `wsl.exe` 命中 Program Blacklist 被拒, **不可绕过**)。
- **处置**: 退而求其次的**等价论证** —— 用
  `monkeypatch.setattr(模块, "os", types.SimpleNamespace(path=posixpath))` 再跑判据 ——
  这**精确等价**于"该代码跑在 Linux", 于是**在 Windows 上就能复现 Linux 的失败**。
  写成守阵即成防回潮(见 `tests/test_sim_corpus.py::test_fsmock_case_folding_does_not_follow_platform`:
  还原成旧写法时它在本机**立刻红**, 而原有那条 `test_fsmock_long_path_prefix_and_case` **仍然绿** ——
  后者正是"只在 Linux 现形"的原因)。
  ❗守阵判据**别用文本扫描**: `os.path.normcase` 这串字就写在 `_key` 的 docstring 里当反例,
  扫描会被注释骗过(与冒烟 `_scan_filter_facets` 必须先剥 JS 注释同一个坑)。
