# 沙箱内跑工具自体套件: tempfile 静默回退 cwd, 临时垃圾落进工具目录

> 摘要: 工具(`tools/global-traffic-monitor`)是独立 uv 项目, 其套件不在根 `testpaths` 内 ⇒ 跑它时**不带**根 `test.*` 包的 `TMPDIR` 收口; 若又在本 agent 沙箱内跑, `H:\Temp` 与 `%TEMP%` 对 uv 子进程都不可写 ⇒ python `tempfile.gettempdir()` 候选目录全失败后**静默回落 cwd** ⇒ 测试临时文件(随机名文件 + `pytest-of-<user>/`)落进工具目录, `git status` 变脏。
> 触发: 跑工具侧测试, 工具套件, global-traffic-monitor, 临时目录, TMPDIR, 沙箱, 临时垃圾, git status 脏, tmp 文件, pytest-of

## 现象与处置(2026-10-17 实测, 专题 26-10-17-0339 S11)

- **触发**: 在本 agent 沙箱内跑工具自体套件(工具目录内的独立 venv, 未设 TMPDIR)后。
- **判别**: 工具目录里多出 8 位随机名文件与 `pytest-of-<user>/`; 根因 = 沙箱把 `H:\Temp` 与 `%TEMP%` 均判不可写
  (子进程 python 报 `PermissionError [Errno 13]`), `tempfile` 候选目录全失败后**回落当前工作目录**。
  与 [sandbox-full-run.md](sandbox-full-run.md) / [tmpdir.md](tmpdir.md) 的「R 盘 TMPDIR 等于没设」同源,
  但落点不同: 那两条是**收尾崩**(点号全过却判红), 本条是**往仓库里落垃圾**(测试本身全过)。
- **处置**:
  ①**提交前手工清理**(删随机名文件与 `pytest-of-*`), 别让垃圾混进提交 —— 它是 untracked,
    不清理就会被 `git add .` 或面板一并收走;
  ②判定权威 = **自然跑法**(未设 TMPDIR、套件全绿)下的结果; **不要**为了躲垃圾就手工把 `TMPDIR`
    指到仓内目录 —— 实测那样做会因沙箱拦子进程 unlink 而**多出 7 条无关失败**
    (atomic_write 残留 / lock meta 未删 / uninstaller 删除), 看着像回归实为沙箱拦截;
  ③要彻底消除, 把该测试用到的临时目录加进沙箱白名单(Settings → Permission & Approval)。
