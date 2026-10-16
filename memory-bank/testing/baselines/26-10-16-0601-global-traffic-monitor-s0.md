# 3413 passed + 4 skipped —— 全局流量监视小工具 S0 包骨架(纯新增 tools/ 目录, 根集回归验证)

> 摘要: 用户「实施计划S0:26-10-16-0541-plan-global-traffic-monitor.html」(对 S0 的显式授权, S1–S10 不动)。新建 tools/global-traffic-monitor/ 独立包骨架 11 文件(pyproject[hatchling/src 布局/入口 gtm/依赖仅 psutil+filelock/dev 组 pytest/自带 pytest 配置]、src/gtm/ 八文件[六个模块为 S1–S5 占位]、README、tests/test_smoke.py), 零 auto-qb 文件触碰。出口判据全过: 独立 venv 下 gtm --version=gtm 0.1.0; 根环境 import psutil 仍 ModuleNotFoundError(隔离验证); 工具冒烟 4 条全过。本切片为根 test.full 回归闸门数字(工具测试不在根 testpaths 内, 不进本 TOTAL)。
> 基线时间: 2026-10-16 06:05

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md

## 验收数字

- test.full: 3413 passed + 4 skipped / TOTAL 17343 182 5846 159 99%; 耗时 125.6s(单次采样, 口径见 baseline.md)。首轮 5 红均为本轮回写文档的文档闸门(计划缺 CSS color-scheme: dark / 档案头 Refs 行 dash 前缀致解析落空 + 缺 **Topics:** 主键 / 档案 Refs 引用了无法反向声明的旧报告 / kb.index 未重建四类), 补齐后全绿。
- 工具侧自测(独立 venv, 不计入根 TOTAL): `uv run pytest -q` 4 passed(版本一致性/模块可导入/--version/骨架提示)。
- 依赖隔离验证: 工具 venv psutil 7.2.2 / filelock 4.2.0 / pytest 9.1.1; 仓库根 `uv run python -c "import psutil"` = ModuleNotFoundError(装/卸验证两环境互不污染)。
- Linux(WSL)侧未跑 —— S0 无平台分支(installer 平台逻辑在 S5), 本条 Windows 侧数字为事实源。

## 本改动面

- `tools/global-traffic-monitor/`(新增 11 文件): `pyproject.toml` · `src/gtm/__init__.py` · `src/gtm/__main__.py`(CLI 入口, S0 仅 --version) · `src/gtm/config.py`(S3 占位) · `src/gtm/sampler.py`(S1 占位) · `src/gtm/storage.py`(S2 占位) · `src/gtm/server.py`(S3 占位) · `src/gtm/notifier.py`(S4 占位) · `src/gtm/installer.py`(S5 占位) · `README.md` · `tests/test_smoke.py`。
- 滚动面(文档): 计划 HTML 就地更新(doc-updated/状态行/§04 R0 实施记录/doc-refs/补 color-scheme: dark) · activeContext 切片追加 R1 · tasks 档案新建(立档阈值 #4) · pitfalls/testing/nested-pytest-config.md 新建 · kb.index 重建两次(基线入册前/后)。
