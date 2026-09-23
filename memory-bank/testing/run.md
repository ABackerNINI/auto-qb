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
- 备选是 `C:/Users/11059/AppData/Local/Temp`(更快), 但按约定**统一走 R 盘**。
  ⚠ 换盘**省不了多少** —— 本机文件操作的固定开销在 R: / D: / C: 上完全一致, 见下「耗时画像」。
- 完整判据与"治本解"见 [../pitfalls/testing/tmpdir.md](../pitfalls/testing/tmpdir.md)。

## 环境纪律

- **并发跑 pytest**: 既有说法"`FakeQbServer` 绑固定端口所以不能并行"**事实有误**
  (它用 `("127.0.0.1", 0)`, 端口由内核分配)。系统层排除项调好之后, `-n 4` 全量 **5.0s**(串行 19.6s, 约 4×)
  且**波动极小**, 建议作本地快车道; 但 sidefx 台账在并行下**不打印**(拦截仍在, 只是看不见)、
  覆盖率与串行差 1 个单位 ⇒ 当**闸门**用之前先补控制器侧台账聚合。
  取舍、样本与判据见 [../pitfalls/testing/parallel-run.md](../pitfalls/testing/parallel-run.md)。
- 测试**基本全部使用 Fake, 不连真实 qBittorrent**(随时可全量运行)。唯一例外是
  `test_local_qb_service.py` 与 `test_ui.py::test_connect_failure_throttles_logging`(走 `FakeQbServer`)。
- **耗时画像**: **当前数字以 [baseline.md](baseline.md) 为准, 本节只记量级与成因**(避免两处各自漂移)。
  2026-09-23 末态: 串行空载约 **19.6s**, 并行 `-n 4` 约 **5.0s**(同日更早是 61s / 75s 量级)。
  Linux(WSL, ext4) 约 **12s** 量级(旧测)。
  ⚠ **单次数字没有意义, 报耗时必须带区间** —— 逐次实测集只在 [baseline.md](baseline.md) 里枚举一处。
  ❗**耗时曾被"每次文件操作的固定开销"支配**(不是 Python / 覆盖率): 初始态每次操作收
  **20ms(写)/ 43ms(删)** 的固定过路费(与数据量无关, 三块盘一致), 全量一次建 577 个临时目录 ⇒ 约 26s。
  **已由系统层排除项治好**(现 `mkdir` 0.13 / 写 0.21 / `remove` 0.16 / `rmdir` 0.14ms, 全部 <1ms)
  ⇒ 全量 **75s → 19.6s**。⇒ 这 3.8× 来自**环境**不是代码; 若哪天又变慢, **先按操作类型逐项复测**,
  并注意白名单**粒度**(只加项目子目录没用, 要按 Temp 目录加)。定位三步与探针见
  [../pitfalls/testing/perf-measurement.md](../pitfalls/testing/perf-measurement.md)。
- ⚠ **别用 `| tail -N` 接 pytest** —— 会缓冲到进程结束才出输出, 容易误判成卡死。
- ⚠ **别用"全量总时"判断某处优化省了多少** —— 会被别处抵消(实测: 守卫收尾从 4.7~9.0s 掉到 1.04s,
  总时却没降, 因为同一次跑里另一处冒出 10s)。收益一律看 `--durations` 里**目标条目本身**或 A/B 两次跑。
- ⚠ **有并发负载时测出的耗时一律是假的**(本机放大得特别狠: 同一份代码 62.87s ↔ 124.48s)。
- ⚠ 主循环节拍类用例用**真实睡眠**(0.05~0.6s)观测节拍, **不能用 mocked 时钟** ——
  时间不前进会导致"两条线都不到期"的死循环, 用例会**挂死而非失败**。
- 覆盖率现状: 总覆盖率**以 [baseline.md](baseline.md) 为准**(此处不抄数字); 低洼是 `ui.py`(GUI 本体真机冒烟不单测);
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
