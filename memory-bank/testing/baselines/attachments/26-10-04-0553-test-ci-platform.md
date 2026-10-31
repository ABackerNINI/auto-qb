# 基线切片 26-10-04-0553 — 修 Linux CI 平台差异连红(覆盖率提升轮的 Windows-only 用例两平台同跑)

> 摘要: CI 在 `ubuntu-latest` 上连红 10 条(修前 `10 failed, 2430 passed, 6 skipped` / 覆盖率 **98.04%**),
> 元凶是覆盖率提升轮新增的 Windows 分支用例只在 Windows 侧验收。**生产代码一行未改**, 只把 4 个测试文件
> 改成两平台同跑(补 `ctypes.windll`/`WINFUNCTYPE` 门面 + `winreg` 替身 + 显式 `ntpath` + `exists` 真值改
> `tmp_path`)。本切片**首次同时记两侧**(上一条基线记「Linux 侧未重测」)。

> 基线时间: 2026-10-04 05:53
> 档案: memory-bank/tasks/26-10-04-test-ci-platform.md

**Refs:** memory-bank/tasks/26-10-04-test-ci-platform.md

- 分支: develop @ 30b887e9(+ 本轮未提交改动: 4 个测试文件 / `pitfalls/testing/patching.md` / 本切片 / 档案 / 切片)
- 命令(Windows): `commands run test.full`
- 命令(Linux): `commands run test.linux`(本轮**新增收录** —— 此前每次都要手拼 docker 命令且两次踩坑,
  遂按 commands skill 收录协议进 `test` 包; 配方与两个必踩点见
  [pitfalls/testing/patching.md](../../pitfalls/testing/patching.md)「Docker 等价复现」节)
- **实测 (Windows)**: **2442 passed + 4 skipped, 40.63s, 覆盖率 TOTAL 98.74%**
  (14495 语句 / 133 未覆盖 / 4864 分支 / 106 partial; 门槛 98% 达标)
- **实测 (Linux 容器)**: **2440 passed + 6 skipped, 31.01s, 覆盖率 TOTAL 98.69%**
  (14495 语句 / 140 未覆盖 / 4864 分支 / 109 partial); 同环境**修前** = `10 failed` / 98.04%
- 相对上基线(26-10-04-0527: 2442 passed + 4 skipped / 99% / 47.76s): Windows 侧用例数与覆盖率**持平**
  —— 本轮零新增/删改用例, 只把既有用例改成平台无关; Linux 侧为**首次补测**(上一条记「Linux (WSL) 侧未重测」),
  覆盖率较修前 **+0.65 个百分点**(98.04% → 98.69%), 因为原本直接报错的用例现在真跑起来, 把 Windows 专属行覆盖上了。
- 两侧口径: **收集数相同**(均 2446 = passed + skipped), 差异全在 skip 集合上(实测 `-rs` 逐条核对):
  - **Linux 上 skip 6 条**(Windows 专属, Windows 侧照跑): `test_grouping.py:1588`(大小写折叠仅 Windows)/
    `:1600`(junction 仅 Windows)/ `test_commands_engine.py:226`(仅 win32 + PYTHONUTF8=1)/
    `test_sidefx.py:184`(非 Windows 无 winreg)/ `test_ui.py:219`(真注册表 autostart)/
    `test_utils.py:969`(真签名验收 `test_win_user32_binds_signatures`)。
  - **Windows 上 skip 4 条**(POSIX 专属, Linux 侧照跑): `test_file_access.py:279` ×2(`os.symlink` 假成功)/
    `test_grouping.py:1577`(normcase 折叠)/ `test_web.py:6763`(仅大小写敏感 FS)。
  - 注意本轮**新修的那批用例在 Linux 上是真跑**的(不再靠 skip) —— 这正是覆盖率从 98.04% 升到 98.69% 的来源;
    上述 6 条 Linux skip 都是**改动前就已存在**的真平台专属用例。
- 未验证面: Python **3.13**(CI 矩阵含 3.13; 本机与容器均 3.12)—— 失败形态是 POSIX 缺模块 / 路径语义,
  与解释器版本无关, 但未实测。
