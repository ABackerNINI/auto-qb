# 3130 —— 坏链判据收紧(Windows 归一化) + 容器代理透传

> 摘要: 档案 `26-10-11-doc-links-strict-check` 执行轮(CI 单条红 → 判据收紧 → 容器代理透传)。①坏链 `[history](...)` 改回准确字面量并裹行内代码; ②`check_doc_links.link_exists` 改**组件级 `listdir` 精确比对**(区分大小写 + 拒绝结尾点/空格组件名), 新增守阵 `test_doc_links_rejects_windows_normalized_targets`(红验: 旧判据下只报出 3 条中的 1 条); ③`linux_ci.py` 加**代理自动透传**(回环主机改写 `host.docker.internal` + `--add-host` + `no_proxy` 恒并入回环)与守阵 `.commands/test/scripts/test_linux_ci.py`; ④坑与取证写进 `pitfalls/testing/patching.md`(⑥ 新节 + 判别法四类升五类 + 容器网络两坑)。**两侧都重测**(Windows 与容器 Linux, 见下两段)。
> 基线时间: 2026-10-11 23:15

**Refs:** memory-bank/tasks/26-10-11-doc-links-strict-check.md

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 快进 d186d603→9b0d6f41; 工作树含本轮回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **3130 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**(覆盖率精确值 98.69%)

## Linux 侧实测(容器)

- 命令: `commands run test.linux`(容器 `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` = CI 矩阵 3.12; 本轮脚本新加代理透传, 输出含 `[linux-ci] 代理透传: …` 一行)
- **实测 (Linux)**: **3128 passed + 6 skipped, 0 failed, 覆盖率 98.63%**
- 与 Windows 侧的常态差异: 2 条 Windows 专属用例在 Linux 转 skip ⇒ `passed −2 / skipped +2`(收集数相同, 别拿 passed 直接比)。
- 用途: 本轮 CI 红正是"只有 ubuntu job 会判"的那一类(本机判据被平台语义骗过) —— 判别见 [../../pitfalls/testing/patching.md](../../pitfalls/testing/patching.md) ⑥。

## 包内脚本测试

- 命令: `commands run test.pkg`(本轮改了 `.commands/test/scripts/`, 闸门 `match` 命中)
- **实测**: **160 passed / 0 failed**(含本轮新增 `test_linux_ci.py` 的 5 条)

## 判据侧增量(非 pytest)

- `doc.links`: 1026 个文件 / 0 处坏链 —— 收紧后的判据在本机也判红, 不再被 Win32 归一化骗过。
- 定向复核: 用严格口径探针复扫 CI 现象提交 `b447c7fa` 的 `memory-bank/` 快照 ⇒ **恰好 1 处**坏链(`pitfalls/kb/index-archive-view.md:45 → ...`, 与 CI 报的一字不差); 扫当前工作树 0 处。
