# config-reference — 配置参考

> **本文件是生成物, 不要手改** —— 由 `commands run kb.index` 扫描本目录主题文件的三行头元数据生成; 新增 / 改名 / 改摘要后重跑即可, 冲突也只需重跑。
> 库内细路由见 [memory-bank/README.md](../README.md)。
> **检索纪律**: 先读本索引定位, 再按需打开单个主题文件 —— **不要整读本目录**。
> **摘要**: 配置加载/写回/fail-fast 校验, 以及全部配置键与语法速查、运行时文件。
> **触发**: 配置, 配置键, load_config, 校验, 写回, trackers, 限速曲线, 运行时文件

## 主题

| 主题 | 一句话 | 触发词 |
|---|---|---|
| [keys.md](keys.md) | 顶层键、trackers 站点段、限速曲线段、规则集段、变量与匹配语法、运行时文件、测试样例。 | 配置键, 配置项, trackers, 限速曲线, 规则集段, 变量替换, 匹配语法, 运行时文件, hr_check, HR 在线核实 |
| [loading-and-write.md](loading-and-write.md) | `load_config` 加载机制、图形化编辑器的写回、`validate_config` 全量聚合校验。 | 配置加载, load_config, 写回, 图形化编辑器, fail-fast, validate_config, 新配置键 |
