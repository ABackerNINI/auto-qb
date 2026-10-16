# 3485 passed + 4 skipped —— 全局流量来源集成 S11（工具侧目录定位 / 数据落点 / 旧数据搬迁 / 启动器）

> 摘要: 用户「实施计划S11: 26-10-17-0339-plan-global-traffic-source-integration.html」(对 S11 的显式授权, S12–S19 不动; 开工同步 ab2e8e30)。工具侧落地四项: `storage.resolve_tool_root()` 目录定位单点(D11) + `default_data_dir()` 改判「<工具安装目录>/data」+ env 改名(D12/D16) + 旧用户目录数据一次性搬迁 + 新增启动器 launch.cmd/launch.sh(D19)。根套件自身无代码改动 ⇒ 回归数字与前一版基线同量级。本切片为根 test.full 回归闸门数字。
> 基线时间: 2026-10-17 05:34

- 根 `test.full`(契约: 覆盖率门槛 98% + 包内 TMPDIR; 跑在含本轮知识库回写的同一棵树上): **3485 passed + 4 skipped in 135.99s**; TOTAL **17885 246 6012 180 98%**(语句/未覆盖/分支/partial/覆盖率)。
- 工具侧套件(工具目录内、工具独立 venv, 不在根 `testpaths` 内): **181 passed** —— 含 S11 新增用例(源码态 + 模拟 frozen 态目录解析、env 覆盖、搬迁四场景、显式目录不搬迁)。

## 本改动面

- `tools/global-traffic-monitor/src/gtm/storage.py` —— `resolve_tool_root()` 单点(D11, 双模: frozen 用 `sys.executable`、源码态由 `__file__` 上溯) · `default_data_dir()` 改判「<工具安装目录>/data」(D12) · env `GLOBAL_TRAFFIC_MONITOR_DATA_DIR` 优先(D16) · `migrate_legacy_data_dir()` 旧用户目录一次性搬迁(三闸 + 幂等 + 失败不阻断)
- `tools/global-traffic-monitor/src/gtm/__main__.py` —— `_resolve_data_dir()` 接线搬迁(显式 `--data-dir` 不搬迁) + `run`/`autostart` 帮助文案 env 改名
- `tools/global-traffic-monitor/tests/test_storage.py` —— 增改用例 + 头文档测试计划清单同步
- `tools/global-traffic-monitor/launch.cmd` / `launch.sh` —— 新增启动器(D19: 恒定 `--autostart`、不传 `--data-dir`、优先自带 venv 解释器、uv 仅兜底)
- `memory-bank/tasks/26-10-17-backend-global-traffic-source-integration.md` —— 本专题立档(阈值命中: 跨会话 + ≥3 源文件 + 有计划文档)
- `memory-bank/activeContext/26-10-17-0339-traffic-source-integration.md` —— S11 已实施段 + 待办
- `memory-bank/pitfalls/testing/sandbox-tempfile-cwd-fallback.md`(新增) / `memory-bank/pitfalls/kb/discipline.md`(R1 改版教训)
- 未动(属计划内后续步骤): `docs/configuration.md` 与工具 README 的旧 env 名 / 平台默认目录文案 → S14 改名面 + S18 文档回写
