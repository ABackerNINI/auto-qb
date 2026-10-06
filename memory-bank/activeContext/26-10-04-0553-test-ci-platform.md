# Linux CI 平台差异连红(已修)

> 摘要: 用户给 CI 失败摘要(10 failed)要求修复。反查 GitHub 运行记录定位到最后一次绿 = `41aa9f00`
> (2026-10-02 00:06), 元凶是覆盖率提升轮(计划 `26-10-01-2157`)—— 那轮新增的 Windows 分支用例
> **只在 Windows 侧验收**(档案自记「Linux 侧待补」), 在 POSIX 上必红。四类根因: `ctypes.windll`/
> `WINFUNCTYPE` POSIX 不存在 / `winreg` Windows 专属 / `os.path` 是 posixpath(反斜杠不当分隔符) /
> 真值断言写死盘符。**生产代码一行未改**, 只把 4 个测试文件改成两平台同跑(补 ctypes 门面 + winreg 替身
> + 显式 ntpath + `tmp_path`)。两侧实测: **Linux 容器 2440 passed + 6 skipped / 98.69%**(修前 10 failed /
> 98.04%), **Windows `test.full` 2442 passed + 4 skipped / 99%**。基线切片 26-10-04-0553。

> 最后活动: 2026-10-04 06:30

## 进行中

- (无 —— 修复已完成并过两侧全量)

## 已完成

- 定位: `gh api` 查 `/actions/runs`(100 条 / 45 绿) → 最后绿 `41aa9f00`; `git log 41aa9f00..HEAD -- tests/`
  → 覆盖率提升轮 4 笔提交(`f6c3f239` P0 / `29f1841a` P1 / `1c237504` P2-b / `21b8db24` 阈值抬 98)。
- 量化: Linux 容器复现修前 = 10 failed / **覆盖率 98.04%**(门槛 98%) ⇒ 排除"跳过 Windows 用例"方案
  (跳过会让 Windows 专属行不覆盖, 跌破 98%)。
- 修复(4 文件, src/ 零改动):
  - `tests/test_utils.py`: 新增 `_shim_posix_ctypes`(POSIX 补 `windll`/`WINFUNCTYPE`, Windows 不装);
    4 处用例补 `sys.platform` 固定; `_win_reuse_and_wait_explorer` 把 utils 模块内 `os` 固定为 `ntpath`;
    `test_long_path_prefix_relative_path` 补平台 patch。
  - `tests/test_tray.py`: `_patch_windll` 的 `setattr` 加 `raising=False`。
  - `tests/test_ui.py`: 新增 `_winreg_or_stub`(替身须留 `CreateKeyEx`/`OpenKey`/`DeleteValue` 占位);
    `test_autostart_error_paths` 三段改 `monkeypatch.context()`。
  - `tests/test_expr_eval.py`: `exists` 真值断言改 `tmp_path`。
- 验证: Linux 容器全量 **2440 passed + 6 skipped / 98.69%**; Windows `commands run test.full`
  **2442 passed + 4 skipped / 99%**; `test_memory_bank.py` 31 passed。
- 回写: `pitfalls/testing/patching.md` 加「复发 +1」(含"为什么没命中" + 四类处置) 与
  「Docker 等价复现」配方(WSL 被黑名单拦的替代; 含"别删 `/work/.git`"等两个必踩点)。
- 后续轮(2026-10-04 06:30): 用户要求 ci.yml 加 windows-latest job —— 新增 `test-windows`
  job(3.12/3.13 矩阵)复用 ubuntu job 全部步骤, coverage artifact 改名 `coverage-ubuntu-<py>`
  防撞名; 本地(Windows)基线 2442 passed + 4 skipped / 99%(基线 26-10-04-0630)。知识库既有
  issue [26-09-21-1408](../issues/26-09-21-1408-chore-ci-no-windows-runner.html)
  (chore-ci-no-windows-runner)经用户显式认领后置 Done(§05 修复后补充), 索引已重建。

## 未验证面

- Python **3.13**(本机与容器均 3.12; CI 矩阵含 3.13) —— 失败形态是 POSIX 缺模块/路径语义, 与解释器版本无关,
  但未实测。
- 提交与 CI 复绿: 改动未提交, 需用户说「提交」后推 Gitee, 再由 GitHub 镜像触发 CI 复核。
