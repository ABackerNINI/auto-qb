# 闸门并发内存峰值导致超时型假红

> 摘要: 提交闸门 `ship.commit` 把闸门命令放进 4 线程池并发, 而 pytest 类闸门自身又用 `-n 8` —— 峰值 4×8 = 32 worker 打满内存, 表现为 **`timekit --check` 超时 / node battery flake** 这类资源型红, 内容本身零问题; 处置是**运行时降并发**, 一个文件都不用改。
> 触发: 提交闸门超时, timekit --check 超时, 闸门红, 假红, node battery flake, 内存打满, 换页, GATE_WORKERS, ship.commit 五连红
**Refs:** memory-bank/tasks/26-11-09-docs-ascii-symbol-cleanup.md

## 本篇只回答

闸门**红了但错的是超时 / 资源**时, 怎么在动内容之前先排除「并发把机器打满」这条: 看什么数字、怎么零改动绕过去。

### 闸门连续红且错误形态是超时 —— 先查 worker 数与内存, 再怀疑内容

- **触发**: 跑 `ship.commit` 闸门**连续多轮红**, 报错是 `timekit --check` 超时 (常态 4s, 实测涨到 45-60s)、node battery 偶发 flake; 工作树内容与前一轮无实质变化 (2026-11-09 实测 5 连红)。
- **判别**: ①错误形态是**超时 / 资源型**, 不是断言失败 —— 单项耗时比常态膨胀一个数量级, 输出里没有 `FAILED` 用例; ②算峰值并发: `.commands/my-commit-flow/scripts/_pipeline.py:489` 的 `GATE_WORKERS = 4`(闸门线程池) × `pytest.ini:17` 的 `addopts = -n 8`(pytest 类闸门自身的 xdist 并行) = **4 × 8 = 32 worker**; ③看内存: 12GB 机器被压到 Free 2.6GB / Committed 13.3GB, 已进换页; ④反证: 同一份内容把闸门串行化后零 flake。
- **处置**: **运行时 monkeypatch 后调 `commit.main`**, 零文件改动:
  ```bash
  python -c "import sys; sys.path.insert(0,'.commands/my-commit-flow/scripts'); import _pipeline; _pipeline.GATE_WORKERS = 1; import commit; sys.exit(commit.main(['--no-push']))"
  ```
  串行闸门实测 4m52s, 零 flake。**生效前提已实测**: `run_gates` 在调用时按模块全局解析 `GATE_WORKERS`, 且 `commit` 模块**没有**本地同名别名 —— 若哪天有人在 `commit.py` 里 `from _pipeline import GATE_WORKERS` 拷一份, patch 就静默失效, 提交前可 `grep -n "GATE_WORKERS" .commands/my-commit-flow/scripts/*.py` 复核只有 `_pipeline.py` 命中。
  `_pipeline.py:489` 的注释本身就写了处置方向 (「改这里降并发或给 pytest 类命令独占池」), 但那要改文件; **只想提交一次**的场合用运行时 monkeypatch 更省 —— 改默认值属另一个决定 (影响所有 clone 的闸门吞吐), 另开 issue 走拍板。
- **守阵**: 无 —— 资源型偶发红依赖机器负载, 不稳定复现, 不入自动闸门; 判据靠人读本节。
- **同族**: pytest 侧并行甜点与 `-n auto` 打满机器的实测见 [parallel-run.md](parallel-run.md); 单文件另用 `-n 0` 见 [single-file-xdist-hang.md](single-file-xdist-hang.md)。
