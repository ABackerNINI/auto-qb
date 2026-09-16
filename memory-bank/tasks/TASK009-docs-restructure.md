# TASK009 - README 重构与配置文档分离

**Status:** Completed
**Added:** 2026-09-15
**Updated:** 2026-09-15
**专题:** 文档 / 用户视角

## 原始请求

- 2026-09-15: README 面向用户重写 (去开发者内容), 并把配置主路径切到 Web UI。

## 思考过程与决策

- README 从 29KB 压到 10KB: 移出配置说明 / 全局限速曲线 / 规则系统三大节 → 新建 `docs/configuration.md` (21KB)。
- 删除"架构要点 + 源码树"开发者内容 (归口 `memory-bank/modules.md`); "架构与设计原则"改名"设计理念"仅留 4 条。
- 补缺失信息: 首次配置引导、两种配置方式的生效语义差异 (热重载仅 Web UI 保存管线, YAML 直改需重启)、设置页可改全量配置的显式声明。
- 措辞去技术化 (端点名 / tick / 线程模型 / round-trip → 用户语言)。
- 修漂移: 测试数对齐 `testing.md`; 补 `--export-torrents_info`; 托盘取消"可选安装"。

## 实现计划

- [x] 新建 `docs/configuration.md`
- [x] `README.md` 瘦身与链接改指
- [x] `minimal.yml` 加 `web` 段 (与 qB WebUI 端口区分)
- [x] 保留 `--export-yaml` 模板导出说明

## 子任务状态表

| ID | 描述 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| 9.1 | `docs/configuration.md` 抽取 | Complete | 2026-09-15 | 配置参考单一入口 |
| 9.2 | `README.md` 用户视角重写 | Complete | 2026-09-15 | 29KB → 10KB |
| 9.3 | `minimal.yml` 补 `web` 段 | Complete | 2026-09-15 | 含 host / port / token |

## 进度日志

### 2026-09-15

- 两轮文档重构完成 (均仅文档, 未动代码): 先 README 用户视角重写, 再把配置主路径切到 Web UI 并抽出 `docs/configuration.md`。
- 遗留: `minimal.yml` 的 `add_episode_tags` 校验失败为既有问题 (与本次无关, HEAD 同样复现)。

## 历史会话纪要 (原文归档)

> 以下为 `activeContext.md` 会话纪要的**原文归档** (2026-09-17 机械迁移, 未删改; 含一处历史 GBK 编码损坏条目),
> 按时间倒序保留。新增进展请写 `## 进度日志`, 不要再往 `activeContext.md` 堆长纪要。

- 2026-09-15: README 配置主路径切换到 Web UI(仅文档, 未动代码, 未提交) — 新建 docs/configuration.md 配置参考(从 README 移入: 两种配置方式对比[Web UI 推荐/YAML 直改需重启]/通用约定/完整 YAML 示例/全局限速曲线/Traffic Monitor/规则系统全套含 checking 安全保障, 21KB); README 29KB→10KB: 快速开始·配置改为 Web UI 首配流程(minimal.yml 只填 qB 连接+web.enabled, 其余设置页点选)、保留 --export-yaml 模板导出、目录/功能特性/Web UI 共 6 处链接改指新文档、删配置说明/全局限速曲线/规则系统三大节换「配置参考」短节(链接+最常踩点: 单位/regex:/多实例 data_dir)、Web UI 节加推荐定位句与设置页阶梯图提示。补上的缺失信息: 首次配置引导、两方式生效语义差异(热重载仅 Web UI 保存管线, YAML 直改需重启)、设置页可改全量配置的显式声明。后补: minimal.yml 加 web 段(enabled/host/port/token, 放 qbittorrent 段后)与 README 最小配置块同步含 host/port, 注明与 qB WebUI 端口区分; yaml.safe_load 验证通过。
- 2026-09-15: README 用户视角重写(仅文档, 未动代码) — 修漂移: 测试数 849→872(对齐 testing.md 基线, 两处)、删除「架构要点+源码树」开发者内容(归口 memory-bank/modules.md)、「架构与设计原则」更名「设计理念」仅留 4 原则、托盘「可选安装」改为随主包安装(pyproject 证实 pystray/customtkinter/fastapi 等均为主依赖)、命令行表补 `--export-torrents_info`(cli.py 核实)、测试命令对齐 testing.md(自带覆盖率 + `--no-cov`)、max_tasks_per_tick 示例注明默认 20(models.py 核实)。措辞去技术化: 增量同步端点名/tick/线程模型/恒定时间比较/round-trip 等改用户语言, Web 设置页删「线程模型」条目。运行命令改 `uv run auto-qb`(pyproject `[project.scripts]` entry point, activeContext 有 entry point 冒烟记录), 旧式 `uv run python src/auto-qb.py` 注明等价。
