# 嵌套子包跑 pytest 拾取仓库根 ini

> 摘要: 仓库内子目录独立包(自带 pyproject+venv)内 `uv run pytest` 会向上拾取仓库根 pytest.ini, rootdir 上移, 根 ini 的 addopts(-n/--cov 等)在子包 venv 不可用 → unrecognized arguments 直接报错
> 等级: L0
> 触发: 在 tools/ 下「仓库内嵌套、自带 pyproject 与 venv 的独立子包」内跑 pytest

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md

## 触发

- 子包目录内 `uv run pytest` 报 `pytest: error: unrecognized arguments: -n --cov=src ...`, 报错尾部可见 `inifile: <仓库根>\pytest.ini`、`rootdir: <仓库根>` —— 配置拾取到了父级仓库
- 更隐蔽的变体: 若根 ini 恰好与子包 venv 兼容(无插件依赖), 子包测试会被**静默跳过**, 反而把仓库主测试集跑了一遍(testpaths 相对上移后的 rootdir 解析)

## 判别

- pytest 输出的 inifile / rootdir 指向**父级仓库**而非子包 → 中招
- 判据一句话: 先看 inifile 路径是不是本包的 pyproject.toml / 包内 ini

## 处置

- 子包 `pyproject.toml` 自带 `[tool.pytest.ini_options]`(更近的配置文件优先, rootdir 停在子包)。26-10-16 S0 已为 `tools/global-traffic-monitor` 落地, 后续 S1–S9 工具侧测试沿用
- 反向保证: 根 `pytest.ini` 的 `testpaths = tests` 只收根 `tests/`, 主测试集不会误收子包测试; 两边互不干扰
