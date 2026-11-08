# tmpdir · 工具 shell TMPDIR 会话收尾崩溃(原文归档)

> 外迁自 memory-bank/pitfalls/testing/tmpdir.md · 26-11-08 cap 清零 —— 「工具 shell TMPDIR 会话收尾崩溃」条目逐字外迁, **原样保留**(唯一改动: 指向复发史料的相对链接随本件位置去 `attachments/` 前缀)。
> 主档案: [../tmpdir.md](../tmpdir.md)

### ❗工具 shell 的 `TMPDIR` 指向 `H:\Temp`, pytest 会在**会话结束时**崩(但测试其实全过)

- **触发**: 在工具 shell 里跑全量(2026-09-22 实测)。
- **判别**:
  - **现象**: `uv run pytest tests -q` 打完所有点(如 `[100%]`)之后抛
    `PermissionError [WinError 5] … pytest-current`, **退出码非 0** ⇒ 提交闸门会判红。
    **注意测试本身是过的**, 崩在 `pytest_sessionfinish` 对 `pytest-current` 符号链接做
    `.resolve().exists()`(机制见上条 2026-09-21 条目)。
  - **改 `H:\Temp` 的目录权限无效**(用户改过, 仍然红); 关沙箱跑同样如此 ⇒ **不是工具沙箱**,
    是那个盘上的**重解析点读取被拒**(该链接能 stat 能列, `readlink` / `unlink` 全被拒 —— 用户态修不掉)。
  - **只改 `TMP` / `TEMP` 无效** —— Python 的 `tempfile` **先读 `TMPDIR`**。
  - **只加 `--basetemp <C 盘路径>` 也不行**: pytest 的 tmp_path 走了 C 盘,
    但测试里直接用 `tempfile` 的仍落 `H:\Temp` ⇒ 实测 **4 failed + 1 error**
    (含 `test_sidefx_rmtree_dir_fd_*` 这类 dir_fd 用例)。
- **处置**(两档可用解, 都实测过): 跑之前把 `TMPDIR` 指到**不靠重解析点**的盘 ——
  `C:/Users/11059/AppData/Local/Temp`(最快)或 `R:/Temp`(R 盘不支持符号链接: `readlink` 报
  WinError 4390, `cleanup_dead_symlinks` 没东西可读, 反倒绕开崩溃); 两者全量均全过。
  用户自己终端(`TMPDIR` 在 C 盘)无此问题。
  ⇒ 工具 shell 跑全量前**先设 `TMPDIR`**; 见到这个 `PermissionError` **先怀疑临时目录, 别当代码回归**。
  📌 **2026-09-22 已固定为 `TMPDIR="R:/Temp/auto-qb/tests"`**(R 盘不支持符号链接, 反而绕开了这个崩溃),
  ⚠ **2026-11-02 起废止**: 改由 `tests/_tmp_bootstrap.py` 自举(见首条), 手工固定写法全部拆除;
  完整约定原在 techContext.md「临时目录 / 备份盘约定」(已随 2026-11-08 重构移除, git 历史可考)。
  📌 **2026-09-23 已写进闸门命令(真正的收口)**: ⚠ **2026-11-02 起废止**(自举接管, 见首条)。原记录:
  `.commands/my-commit-flow/.my-commit-flow.toml` 里那条 pytest 闸门改成
  `set "TMPDIR=R:/Temp/auto-qb/tests" && uv run pytest tests -q --no-cov` —— 以前**靠调用者记得导出**,
  从工具 shell 跑 `preflight.py` / `commit.py` 忘导出就假红。
  ⚠ 该写法是 **cmd.exe** 的: 预检用 `subprocess.run(shell=True)`, Windows 上解析到 COMSPEC → cmd.exe,
  POSIX 的 `TMPDIR=x cmd` 前缀**不生效**(实测 rc=1); 且**引号不能省** ——
  `set VAR=value && cmd` 会把 `&&` 前的空格并进 value(实测变成 `'R:/Temp/auto-qb/tests '`, 带尾随空格)。
- **复发**: 累计 12 —— 更早的逐条流水(1 / 2+3 / 4→9, 共九踩)已外迁: [tmpdir-recurrence-history.md](tmpdir-recurrence-history.md)(2026-09-27)
- **复发**: 11 —— 2026-09-26: 为拿引擎截掉的覆盖率表, `cmd //c` 复刻闸门 `set "TMPDIR=…"` ⇒ 引号
  转义使 `set` 失效回落 `H:\Temp` 同崩(rc=1)。没命中: 只读前 30 行。⇒ 兜底同上(bash 前缀, rc=0)。
- **复发**: 12 —— 2026-09-27 同一根因(裸跑 `uv run pytest <两条 doc 守卫>`)再踩同崩。⇒ 任何 pytest 一律走 `test.one`。
- ✅ **治本解 (2026-09-22 实测): 把整个 pytest 临时根 rename 走, 默认路径就恢复** ——
  `os.rename(r"H:\Temp\pytest-of-11059", r"H:\Temp\pytest-of-11059-broken")` 成功
  (改名只作用于**目录项**, 不需能读那个重解析点), 之后在**默认 TMPDIR** 下跑
  `uv run pytest tests -q --no-cov` 实测 **exit=0**。死链本身 `readlink` / `os.rmdir` / `os.unlink` /
  `icacls` 全被拒(用户态修不掉), 但**可连它的父目录一起搬走**, 新根由 pytest 自动重建
  (`garbage-*` 残渣一并搬走, 无害)。⚠ 是**环境修复不是仓库改动**, 换机器不适用 ⇒ 仍优先设 `TMPDIR`。
