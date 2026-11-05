# 平台差异与打桩 (Windows / Linux)

> 摘要: 「Windows 全绿 / Linux 全红」的**五类根因**与"归错类比不修更危险"的教训 —— 平台相关测试必须以 `monkeypatch` 固定平台; 末一类最隐蔽: **Windows 路径归一化(结尾点/空格被剥、大小写不敏感)让"路径存在性"判据在本机恒真**, 2026-10-11 一条坏的相对链接连过三道本机防线、只在 Linux CI 红; 另记一条**本工具 shell 注入 `PYTHONUTF8=1` 造出的假红**(2026-09-25 已修: 环境揭出引擎码页回退真缺陷, GetACP + 测试钉缝双修)。
> 等级: L1
> 触发: CI 红, Linux CI, 平台差异, monkeypatch, WSL, normcase, dir_fd, 平台专属模块, 码页, GBK, cp936, PYTHONUTF8, 假红, 路径归一化, 结尾点, 大小写不敏感, exists, 坏链, 省略号占位

**Refs:** memory-bank/tasks/26-10-04-test-ci-platform.md,memory-bank/tasks/26-10-11-doc-links-strict-check.md

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
  patch `qbmanager.Client` **无效**(`connect()` 走的是 `qbclient.new_client`)⇒
  **patch 真正被调用的名字**, 与网络解耦。
- **处置**: 见下条判别法。
- **复发** +1 —— 新增的 **Windows 分支用例**只在 Windows 侧验收, 推上 `develop` 后 **Linux CI 连红 10 条**
  (`test_utils` 的 Shell/PIDL/user32 组 5 条 + `test_tray` 的 `_set_windows_appid` 组 3 条 +
  `test_ui::test_autostart_error_paths` + `test_expr_eval::test_more_getters_and_funcs`)。
  四类形态: ① `ctypes.windll` / `ctypes.WINFUNCTYPE` 在 POSIX **不存在**(直取属性即 AttributeError);
  ② `winreg` 是 Windows 专属模块(`import winreg` → ModuleNotFoundError); ③ `os.path` 在 POSIX 是
  `posixpath`, 反斜杠不当分隔符(`_win_reuse_title_candidates("R:\\")` 的盘根断言必红);
  ④ 真值断言写死 Windows 盘符(`exists("C:/")`)。
  (为什么没命中: 提覆盖率时只问"这行覆盖上没有", 没问"这条在 Linux 上会怎样" —— 判别法没被路由到**写测试**这个动作上。)
  **处置**: ① `ctypes.windll`/`WINFUNCTYPE` 用 `_shim_posix_ctypes`(POSIX 补门面, Windows 不装走真门面);
  ② `winreg` 用 `setitem(sys.modules, "winreg", 替身)`(替身要给 `setattr` 覆盖的入口留占位, 否则撞
  "属性必须已存在"); ③ Windows 路径语义用显式 `ntpath`; ④ 真值改用 `tmp_path` 这类跨平台真实存在的路径。
  **判据**: 改完必须在 **Linux 容器**里跑全量(见 [attachments/patching-local-linux-repro.md](attachments/patching-local-linux-repro.md)), 与 Windows 侧**两侧都绿**才算完。

### 判别法: 五类"本机绿不算绿"

- **触发**: 判断一条失败是不是平台差异。
- **判别**: 凡是"**记账器判越界 / 平台专属模块导入 / 真实 socket 连接 / 平台相关的路径 API /
  路径存在性归一化(结尾点 · 空格 · 大小写, 见 ⑥)**"这五类,
  本机绿**不算绿**。平台相关测试必须以 `monkeypatch` **固定平台**(测试主体是"平台逻辑"而非"当前真实平台");
  纯 Windows 行为(长路径 `\\?\` 前缀)直接断言在 Linux CI 上**必失败**。
- **处置**: 按四类分别用 `monkeypatch.setitem(sys.modules, …)` / 补 `dir_fd` 绝对路径 / patch 真实名字。

**形态④ 平台相关的路径 API(`os.path.normcase` 在 Linux 是恒等函数)**: 触发/判别/处置(含
`sim_fsmock._key` 修法与 `sim_qb._norm` 同类未修现状)原文见 [attachments/patching-form-path-api.md](attachments/patching-form-path-api.md)。

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

### ⑥ 路径归一化: 判据在本机恒真, 只在 Linux 现形(结尾点 / 大小写)

- **触发**: 2026-10-11 develop 上 CI 单条红(`test_doc_links_are_not_broken`:
  `memory-bank/pitfalls/kb/index-archive-view.md:45 → ...`), 而本机 **doc.links 闸门 + test.quick 闸门
  + 手工 test.full 三道防线全绿**, 提交信息也诚实地写着"doc.links 绿" —— 不是三处都漏, 是同一行判据
  在两套文件系统语义下答案相反。
- **判别**: 坏链目标是省略号占位 `[history](...)`, 而检查器的判据只有 `(dir / rel).exists()` 一句:
  - `(kb / "...").exists()` 在本机返回 **True** —— Win32 把结尾的点剥掉, 路径**塌成父目录 `kb/`**
    (父目录当然存在); 而 `"..." in os.listdir(kb)` 是 **False**, 磁盘上从无此名 ⇒ 判的根本不是同一件事。
  - 同族第二类: **大小写不敏感** —— 本机 `(kb / "Cap.md").exists()` 也是 True(命中 `cap.md`)。
  - 两类方向一致: 本机只会把"坏"判成"好" ⇒ **本机绿只是上界, 真值在 Linux**。
  - ❗**写核对探针时自己也踩了一次**: `os.path.abspath()` / `Path.resolve()` 同样走 Win32 归一
    (实测 `abspath(".../kb/...")` 直接变成 `.../kb`), 探针于是报"0 处", 假绿复现一遍。
    严格判据必须**组件级 `os.listdir` 精确比对**, 全程不碰 `resolve()` / `abspath()`。
- **处置**: `check_doc_links.py::link_exists` 改组件级精确比对 + 拒绝结尾点/空格的组件名
  (`_is_literal_name`: Windows 存不出这种名字 ⇒ 该链接在 CI 必坏); 守阵
  `tests/test_memory_bank_docs.py::test_doc_links_rejects_windows_normalized_targets`。
  **红验现场**(退回 `.exists()` 即红): 夹具里三条可疑目标只报出 `kb/x.`, **漏掉 `kb/...` 与 `kb/Cap.md`**
  —— 正是两类漏检的实证。
  **泛化: 任何"按路径存在性判绿"的检查(链接 / 找文件 / 白名单比对)在本机都是上界**;
  收口时补一次 `commands run test.linux` 或等 CI, 别拿本机绿当结论。

## 已外迁(原文见附件)

- 本机复现 CI 的平台差异(`test.linux` / Docker / WSL / 容器代理 / canon 等价论证): [attachments/patching-local-linux-repro.md](attachments/patching-local-linux-repro.md)
- 工具 shell 注入 `PYTHONUTF8=1` 造的「本地码页回退」假红(含 2026-09-25 真缺陷修正与守阵): [attachments/patching-pythonutf8.md](attachments/patching-pythonutf8.md)
