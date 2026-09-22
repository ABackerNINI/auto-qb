# 怎么跑测试

> 摘要: 跑全量的完整命令、工具 shell 必须设的 `TMPDIR`、耗时画像、WSL 侧复现 —— 以及"别并发跑"这类环境纪律。
> 触发: 跑测试, 全量, pytest, uv sync, TMPDIR, 覆盖率, 耗时, 并发, WSL, 图形化配置编辑器

## 命令

```bash
uv sync                                     # 依赖统一 uv 管理 (pyproject.toml + uv.lock); 首次 / 依赖变更后
uv run pytest tests -q                      # 全量 (pytest.ini 已带 --cov=src --cov-report=term-missing --cov-branch)
uv run pytest tests -q --no-cov             # 快速迭代; 提交闸门 (auto = true) 跑的就是这一档, 覆盖率基线另算
uv run pytest tests/test_grouping.py -q     # 单文件
uv run pytest tests/test_checking.py -q -k "skip"   # 按关键词
```

- **当前基线数字(唯一手改处)** → [baseline.md](baseline.md); **逐次增量流水** → [baseline-history.md](baseline-history.md)。
- `pytest.ini`: `pythonpath = src`(uv sync 也会把项目 editable 装入 venv, 双保险), `testpaths = tests`, addopts 含覆盖率。

## ⚠️ 工具 shell 里跑之前必须设 `TMPDIR`

```bash
TMPDIR="R:/Temp/auto-qb/tests" uv run pytest tests -q
```

- **原因**: 工具 shell 的 `TMPDIR` 默认指向 `H:\Temp`, pytest 会在**会话结束的清理阶段**抛
  `PermissionError [WinError 5] … pytest-current`(**测试本身是过的**, 崩在符号链接的 `resolve` / `readlink`)⇒
  **退出码非 0**、提交闸门误判红。
- 改 H 盘权限**无效**; 只改 `TMP` / `TEMP` 也无效(Python 的 `tempfile` **先读 `TMPDIR`**);
  只加 `--basetemp` 也不行(测试里直接用 `tempfile` 的仍落 H: ⇒ 4 failed + 1 error)。
- 备选 `C:/Users/11059/AppData/Local/Temp` → 1143 passed in 37.69s(更快), 但按约定**统一走 R 盘**。
- 完整判据与"治本解"见 [../pitfalls/testing/tmpdir.md](../pitfalls/testing/tmpdir.md)。

## 环境纪律

- **不要并发跑多个 pytest 进程**: 本项目有绑定本地端口的 `FakeQbServer` 用例, 且 sidefx 守卫按**会话**记账
  (任何进程删了越界文件都会算到当前会话头上)⇒ 并发跑会出现**假的失败**。
- 测试**基本全部使用 Fake, 不连真实 qBittorrent**(随时可全量运行)。唯一例外是
  `test_local_qb_service.py` 与 `test_ui.py::test_connect_failure_throttles_logging`(走 `FakeQbServer`)。
- **耗时画像**(空载): 含 `--cov-branch` ≈ **40 秒**; `--no-cov` ≈ **30 秒**; Linux(WSL, ext4)≈ **12 秒**
  —— Windows 慢约 3 倍, 差值主要来自 drvfs 与进程/文件操作。
  ⚠ **别用 `| tail -N` 接 pytest** —— 会缓冲到进程结束才出输出, 容易误判成卡死。
- ⚠ 主循环节拍类用例用**真实睡眠**(0.05~0.6s)观测节拍, **不能用 mocked 时钟** ——
  时间不前进会导致"两条线都不到期"的死循环, 用例会**挂死而非失败**。
- 覆盖率现状: 总 **90%**(以 [baseline.md](baseline.md) 为准); 低洼是 `ui.py`(GUI 本体真机冒烟不单测);
  近乎全绿(94%~100%): `config/impact.py` / `config/schema.py` / `logging.py` / `qbapi.py` /
  `registry.py` / `taskqueue.py` / `tracker.py`。

## WSL 侧复现(平台差异)

- **不要复用 Windows 建的 `.venv`**: 项目在 `/mnt/d/...`、`.venv` 是 Windows 侧 `uv sync` 建的
  (`Lib/` + `Scripts/`)时, WSL 的 uv 会判定环境不兼容并试图删掉重建 ⇒
  `error: failed to remove directory .venv/Lib: Input/output error (os error 5)`,
  而且可能把 Windows 侧的 venv 弄坏。
- **解法**: 给 WSL **单独指定环境目录** ——
  `UV_PROJECT_ENVIRONMENT=/tmp/aqb-venv uv sync && UV_PROJECT_ENVIRONMENT=/tmp/aqb-venv uv run pytest tests -q`
  (首次 sync 约几十秒, 之后 `/tmp` 里的环境可复用)。
- ⚠ **仓库副本要 `cp -r` 到 `~/` 下**(不要放 `/tmp`): 副本落在临时目录里会让 `test_sidefx.py` 的两条
  `is_temp_path` 类用例**假红**(实测 /tmp 副本 2 failed, 同代码挪到 `~/` 即 0 failed —— **不是回归**)。

## 图形化配置编辑器测试

- `test_config_schema.py` —— UI 元数据与配置键 / 插件的**一致性守卫**(20 项): 顶层键 vs `KNOWN_CONFIG_KEYS`、
  各段子键 vs `KNOWN_*_KEYS`、插件表 vs `registry`、kind / optional / enum 形态自检。
- `test_config_writer.py` —— 结构化写回: 读取语义 / 校验拒绝不碰磁盘 / 注释与标量风格保留 / 增删键 /
  R 级回退 / 预览不落盘 / 有损数字串不被规范化。
- ❗**新增配置键或插件时必须同步 `config/schema.py`**, 否则守卫测试**直接失败**。
