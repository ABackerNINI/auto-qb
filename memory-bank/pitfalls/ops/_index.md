# ops — 生产文件与环境

> **本文件是生成物, 不要手改** —— 由 `python .agents/skills/memory-bank/scripts/gen_kb_index.py` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 不许碰的生产文件(`config.yml` / `auto-qb-data/`) —— 已在 `.commit-flow.toml` 的 `red_lines` 里, 提交时会被直接拒交。
> **触发**: 改配置示例, 提交前扫红线, 整理仓库, 统一格式, 运行时数据

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [prod-files.md](prod-files.md) | `config.yml` 与 `auto-qb-data/` 是用户真实生产数据, 不许改、不许提交 —— 示例一律用 `minimal.yml` / `test_yamls/`。 | 改配置示例, 新增示例 yml, 提交前扫红线, 整理仓库, 统一格式 |
