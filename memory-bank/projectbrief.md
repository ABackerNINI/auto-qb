# Project Brief — 项目纲领

> 摘要: 所有文档的上游, 目标与范围 (scope) 的唯一权威: 项目是什么 / 核心目标 / 领域知识 (PT·HR·辅种) / 技术栈与运行依赖 / 环境约束。目标变更先改这里, 再同步其它文档。
> 触发: 项目是什么, 目标, 范围, 领域, 术语, PT, HR, 辅种, 技术栈, 依赖, 环境, uv, 平台

## 项目是什么

**auto-qb** — 基于 qBittorrent WebUI API (`qbittorrent-api`) 的 PT (Private Tracker) 种子自动化管理工具。单机常驻 Python 程序, 每 2 秒一个 tick, 经 `/api/v2/sync/maindata` rid **增量同步**打理种子 (只取变化种子与字段, 几乎不增加 qB 负载); 一切种子运行状态以 qB 为准, 本地只持快照与决策产物。许可 Apache-2.0, 仅供个人学习使用 (README 有声明)。

架构设计 (不变量 / 黄金法则依据 / 模块装配) 单点 → [architecture/overview.md](architecture/overview.md)。

## 核心目标 (范围唯一权威)

1. **省心保种** — 按 tracker 自动加删站点标签/分类、相似标签清理、自动集数标签; HR 自动打标 (义务了结前含转移种) + 站点清单在线核实。
2. **辅种安全** — 指向相同文件的种子按 (save_path, 文件列表) 自动归组; 缺文件 / 大小不一致 / 下载冲突时**整组暂停**, 防止误传垃圾数据被站点封号。
3. **灵活自动化** — 规则引擎: 5 种触发时机 × 13 种筛选条件 × 12 种动作 (2026-11-08 实测), 去重/冷却/断点续跑/错误控制齐备。
4. **智能限速** — tracker 级单种限速 + 规则动作限速 + 基于流量历史 (Traffic Monitor 数据源, 可配) 的全局限速曲线, 到量自动降速。
5. **可视可控** — 内置 Web UI (辅种分组视图、组级控制、搜索、H&R 栏、图形化配置编辑) + `--tray` 托盘常驻 + 桌面通知。
6. **安全第一** — 高风险动作 (跳检/强制汇报/移动) 默认关闭; `--dry-run` 试运行; 启动全量配置校验。

机制细节按域入 architecture/: 规则引擎 → [rule-engine.md](architecture/rule-engine.md); HR 与辅种分组/迁移 → [hr-groups.md](architecture/hr-groups.md); WebUI → [webui.md](architecture/webui.md); 主循环/任务队列/落盘时机 → [main-loop-queue.md](architecture/main-loop-queue.md); 数据层/增量同步/state_file → [data-state.md](architecture/data-state.md)。

## 范围边界

- 与 qBittorrent 的通信**只走 WebUI API** (`qbittorrent-api`), 不直接操作 qB 内部数据/文件。
- 不做通用下载器; 只服务 PT 场景 (tracker 语义、HR、辅种分组)。
- 运行主平台 Windows (托盘/通知/Traffic Monitor 数据源), Linux/macOS 可跑核心 (CI 覆盖 3.12/3.13)。

## 领域知识 (PT 语境)

- **PT (Private Tracker)**: 私有种子站, 有严格分享率/做种时长规则。
- **HR (Hit and Run)**: 站点惩罚规则 — 下载后须在规定时间内做种达标 (时长/分享率), 否则受罚。站点清单是权威 (考察中恒管束, 终态放行), 本地判据兜底; 义务了结前打 HR 标签, 达标打 satisfied 标签 (模板变量展开)。管束/触发语义分离与在线核实机制见 architecture/hr-groups.md。
- **辅种 (cross-seeding)**: 同一份文件在多个站发种, 客户端里存在多个指向相同文件列表的种子; 项目自动归组统一管理。
- **缺文件检查**: 辅种组共享物理文件, 组内文件丢失则全部成员失效。事件驱动扫盘 (组内删除/上传转暂停/errored/路径变化), 命中**整组暂停 + `MISSING` 标签**。
- **校验 (checking/recheck)**: qB 对种子逐块哈希校验。**跳检 (skip-checking)**: 导出 .torrent → 删种保留文件 → 重加 `is_skip_checking=True`; 保留标签/分类/限速/路径, 但**统计清零** (上/下载量、做种时长, HR 锚点倒退); 文件内容错误会上传垃圾数据, 多数 PT 站严令禁止 — 故默认关。
- **reannounce (强制汇报)**: 立即向 tracker 汇报, 高频使用有封号风险。
- **单数值限速保护**: 用户手动设置的全局限速习惯写成"奇数 KiB/s" (如 2001); 当前限速为正奇数 KiB 时视为手动值, 该方向本轮跳过不覆盖 — 全项目的约定魔法。
- **做种状态词汇**: qB `TorrentState` 枚举 — stalledUP 做种中 / pausedUP·stoppedUP 已完成暂停 / stalledDL 下载停滞; 类别归组 (is_downloading/is_uploading/is_complete...) 见 `src/auto_qb/rules/conditions.py` 状态条件。

## 技术栈与运行依赖

- **Python 3.12+** (类型注解, dataclass; CI 矩阵 3.12/3.13)。
- **核心依赖 10 个, 全 `==` 精确锁定** (升级: 改 pyproject 再 `uv lock --upgrade`): `qbittorrent-api` (qB WebUI 客户端), `PyYAML` (`yaml.BaseLoader` 全字符串解析), `ruamel.yaml` (配置往返保留注释), `filelock` (单实例锁), `fastapi`+`uvicorn` (WebUI server), `httpx`; `--tray` 分支另加载 `customtkinter`+`pystray`+`Pillow`。桌面通知零第三方依赖 (win=PowerShell WinRT toast / linux=notify-send / darwin=osascript)。
- **配置键权威**: `src/auto_qb/config/schema/` 与 `config.validation` 的 `validate_config` (fail-fast 聚合报错) — 键语义问 schema/代码, 不问文档。

## 环境约束

- 依赖管理统一 **uv** (pyproject.toml PEP 621 + uv.lock 全量锁); 依赖变更后 `commands run env.sync` 重建 .venv 并 editable 安装。
- 入口 `python src/auto-qb.py [CONFIG]` (兼容入口) / `python -m auto_qb` / `uv run auto-qb`; 运行模式: 正常 tick 循环 / `--dry-run` (写操作只打日志) / `--tray` (主循环入后台线程, UI 线程轮询只读快照, 单实例锁 + localhost IPC 双开唤起) / `--export-yaml` (从现有种子生成配置模板, `--only-missing` 只导未配置站点, 不进主循环)。
- 项目命令 (测试/格式化/真机跑/提交) 一律走 commands 引擎按 task id, 单点见根 [AGENTS.md](../AGENTS.md)「命令」节; 测试口径与基线数字 → [testing/baseline.md](testing/baseline.md) (勿手抄)。
- 一切"用完就扔"的临时产物放 `R:/Temp/auto-qb/<用途>/`; 跑测试的 TMPDIR 有自举守卫与判据 (见 [pitfalls/testing/tmpdir.md](pitfalls/testing/tmpdir.md)); 长期归档走 `D:/Projects/_archive/`; R 盘不支持符号链接, 依赖重解析点的工具别放。
- Windows 磁盘文件检查走 `\\?\` 长路径前缀 (`utils.add_long_path_prefix_for_win`); 平台相关测试必须 monkeypatch 固定 `sys.platform`。
- 已实测 qB: 5.2.3 (qB 5.0+ Web API 语义变化见 [pitfalls/backend/qb-api.md](pitfalls/backend/qb-api.md))。

## 当前阶段

**Beta** (pyproject 分类器) — 功能齐备, 全量测试有基线; 大规模实机验证仍在推进 (真机走查规程 [testing/real-machine.md](testing/real-machine.md)), README 标 🚧 的功能先用 `--dry-run` 观察再上生产。

## 上游文档 (权威关系)

- `README.md` — 用户视角功能说明 (权威); `想法.md` — 设计草稿 (权威)
- 本知识库 (`memory-bank/`) — 代码实况核对版; 冲突时以代码为准并回写文档
- 黄金法则与项目命令单点在根 AGENTS.md; 架构设计单点在 architecture/ (经 overview.md 进入)
