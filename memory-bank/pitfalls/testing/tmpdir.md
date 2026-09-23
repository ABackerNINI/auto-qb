# 临时目录与跑全量

> 摘要: 临时目录必须在 `tempfile.gettempdir()` 之下、覆盖率文件不能留仓库根、`TMPDIR` 不设会让会话收尾崩。
> 触发: 跑全量, basetemp, TMPDIR, 临时目录, 覆盖率文件, COVERAGE_FILE, pytest-current, 耗时

### `--basetemp` 换了目录会让 4 条 sidefx 用例**假红**

- **触发**: 想换临时目录跑全量(2026-09-22 实测)。
- **判别**: 换 basetemp 时**必须仍在 `tempfile.gettempdir()`(本机 `H:\Temp`)之下** ——
  `test_sidefx_is_temp_path` 断言 `sidefx.is_temp_path(tmp_path)`,
  挪到 `C:\Users\...\AppData\Local\Temp` 会挂 4 条
  (`is_temp_path` / `policy_allows_known_effects` / `recorder_installed_and_records` /
  `rmtree_dir_fd_entries_not_flagged`)+ 1 条 ERROR, **看着像真失败, 实为临时目录搬家的假红**。
- **处置**: 正确姿势 `uv run pytest tests -q --no-cov --basetemp "H:/Temp/<新目录>"` → 与基线一致。
- **复发**: 2 —— 2026-09-23 复踩: 用 `--basetemp=R:/Temp/auto-qb/pa_bt`(在 TMPDIR
  `R:/Temp/auto-qb/tests` **之外**)跑全量, 又是 4 failed + 1 error, 与 2026-09-22 同形。
  **为什么没命中: 路由到了但文件没读** —— 本轮读过 [../../testing/run.md](../../testing/run.md),
  该文件末行明确指向本文件, 但没顺着点开就自己开测, 于是把已记的坑当"新发现"重新踩了一遍。
  同日复核补充: 只要 basetemp 落在 `tempfile.gettempdir()` **之内**就不假红 ——
  `--basetemp=R:/Temp/auto-qb/tests/bt` 实测越界 **0** 条、守卫全绿。

### 测试基线的临时目录与覆盖率文件必须落在仓库外, 且 basetemp 目录本身必须**不存在**

- **触发**: 跑带覆盖率的全量。
- **判别**: 四条机制 ——
  · `--basetemp` 指到**仓库内** ⇒ 仓内删除被判越界(**5 failed + 1 error**, 是环境口径差异不是回归)。
  · 默认 basetemp 下收尾批量删 `%TEMP%\pytest-of-*` 会撞删除拦截层 ⇒ **点号全过却打不出 `N passed` 与覆盖率表**
    (退出码 1, 看起来像失败)。
  · `COVERAGE_FILE` 留在仓库根 ⇒ coverage 开跑时先擦它, 这次删除同样被拦 ⇒ **开跑 1 秒即退出**。
  · 复用**已存在**的 basetemp ⇒ pytest 开跑前 `rm_rf` 会拉起回收站助手进程, 被记成越界 `POPEN`。
- **处置**: 写法 `COVERAGE_FILE=H:/Temp/aqb.coverage uv run pytest tests -q --basetemp=H:/Temp/<全新目录>`
  (**须在 `tempfile.gettempdir()` 之下**)。

### 速度画像: 直接跑全量即可, 不必挑子集

- **触发**: 想"只跑相关文件"省时间。
- **判别**: 空载全量 **19~20s**(2026-09-23 末态, 排除项调好之后; 同日更早分别是 54~81s 与 62~114s)——
  **当前基线数字一律以 [../../testing/baseline.md](../../testing/baseline.md) 为准**, 此处不复述;
  并发污染下测出的"某文件 300 秒"是**假数字**(本机放大得特别狠, 见 [perf-measurement.md](perf-measurement.md))。
- **处置**: 直接跑全量。
  ⚠ **别用 `| tail -N` 接 pytest** —— 会缓冲到进程结束才出任何输出, 容易**误判成卡死**。

### 全量 pytest 报 `PermissionError: … pytest-current` 是临时目录被污染, **不是测试红**

- **触发**: 全量 pytest 起不来 / 打完点号后报错(2026-09-21 实测)。
- **判别**: 删除拦截层让 pytest 的 `garbage-*` 目录**删不掉、越堆越多**(实测 **283 个**),
  下次运行时 `cleanup_numbered_dir → cleanup_dead_symlinks` 去 `resolve()` 那个已成死链的
  `pytest-of-<user>/pytest-current` ⇒ `PermissionError [WinError 5]`,
  **连汇总行都不打印**(极易误判成"测试全崩")。
- **处置**: **不要去删那些目录**(同样会被拦), 给 pytest 指一个全新临时根即可:
  `mkdir -p H:/Temp/pfresh && TMP=H:/Temp/pfresh TEMP=H:/Temp/pfresh uv run pytest tests -q`。

### ❗工具 shell 的 `TMPDIR` 指向 `H:\Temp`, pytest 会在**会话结束时**崩(但测试其实全过)

- **触发**: 在工具 shell 里跑全量(2026-09-22 实测)。
- **判别**:
  - **现象**: `uv run pytest tests -q` 打完所有点(如 `[100%]`)之后抛
    `PermissionError [WinError 5] … pytest-current`, **退出码非 0** ⇒ 提交闸门会判红。
    **注意测试本身是过的**, 崩在 `pytest_sessionfinish` → `cleanup_dead_symlinks()`
    对 `pytest-current` 这个**符号链接**做 `.resolve().exists()`。
  - **改 `H:\Temp` 的目录权限无效**(用户改过, 仍然红)。更精细的实测: 该链接
    `stat(follow_symlinks=False)` **成功**(mode `0o120777` = 符号链接)、`readlink` **失败**、
    `os.rmdir` / `os.unlink` **失败** —— 即"能列不能读、也删不掉"; 关沙箱跑同样如此,
    所以**不是工具沙箱**, 是那个盘上的**重解析点读取被拒**。
  - **只改 `TMP` / `TEMP` 无效** —— Python 的 `tempfile` **先读 `TMPDIR`**。
  - **只加 `--basetemp <C 盘路径>` 也不行**: pytest 的 tmp_path 走了 C 盘,
    但测试里直接用 `tempfile` 的仍落 `H:\Temp` ⇒ 实测 **4 failed + 1 error**
    (含 `test_sidefx_rmtree_dir_fd_*` 这类 dir_fd 用例)。
- **处置**(两档可用解, 都实测过): 跑之前把 `TMPDIR` 指到一个**不靠重解析点**的盘 ——
  · `TMPDIR="C:/Users/11059/AppData/Local/Temp"` → **1143 passed in 37.69s**(最快)
  · `TMPDIR="R:/Temp"` → **1143 passed in 58.85s / 63.29s**(两次均全过; R 盘**不支持符号链接** ——
    `os.symlink` 能建但 `readlink` 报 `WinError 4390 不是一个重解析点`, 反倒**绕开了**上面的崩溃,
    因为 pytest 的 `cleanup_dead_symlinks` 没东西可读)
  用户自己的终端 `TMPDIR` 在 C 盘, **没有这个问题**。
  ⇒ 在工具 shell 里跑全量测试前**先设 `TMPDIR`**; 看到这个 `PermissionError` **先怀疑临时目录, 别当成代码回归**。
  📌 **2026-09-22 已固定为 `TMPDIR="R:/Temp/auto-qb/tests"`**(R 盘不支持符号链接, 反而绕开了这个崩溃),
  完整约定见 [../../techContext.md](../../techContext.md)「临时目录 / 备份盘约定」。
- ✅ **治本解 (2026-09-22 实测): 把整个 pytest 临时根 rename 走, 默认路径就恢复了** ——
  `os.rename(r"H:\Temp\pytest-of-11059", r"H:\Temp\pytest-of-11059-broken")` **成功**
  (改名只作用于**目录项**, 不需要能读那个重解析点), 之后在**默认 TMPDIR** 下跑
  `uv run pytest tests -q --no-cov` 实测 **exit=0 / 1169 passed + 1 skipped**。
  ⇒ 死链本身 `readlink` / `os.rmdir` / `os.unlink` / `icacls` **全被拒**(用户态修不掉),
  但**可以连它的父目录一起搬走**, 新根由 pytest 自动重建。
  ⚠ 同根的 `garbage-*` 一堆目录会一并搬走 —— 那是 pytest 自己的清理残渣, 无害;
  ⚠ 这是**环境修复不是仓库改动**, 换机器 / 换用户不适用 ⇒ 仍按上面的约定**优先设 `TMPDIR`**。
