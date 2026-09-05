# 01 项目概览与领域知识

## 项目定位

**auto-qb** (v0.2.0, 🚧施工中) — 基于 [qbittorrent-api](https://pypi.org/project/qbittorrent-api/) 的 PT 种子自动化管理工具。长驻运行, 每 2 秒一个 tick, 通过 qBittorrent WebUI API 自动管理种子: 打标签/分类、HR 合规、辅种(跨种)分组与缺文件保护、自定义规则引擎、tracker 级与全局限速。

| 项 | 值 |
|----|----|
| 语言 | Python 3.12+ (类型注解, dataclass) |
| 运行依赖 | `qbittorrent-api`, `PyYAML` (仅两个) |
| 开发依赖 | `pytest`, `pytest-cov`, `yapf` |
| 已测试 qB 版本 | qBittorrent 5.2.3 (代码已适配 qB 5.0 Web API 变化, 见 pitfalls) |
| 平台 | Windows 为主要运行环境 (长路径前缀、Traffic Monitor 数据源), 代码有 POSIX 分支 |
| 许可 | Apache 2.0, 仅供个人学习使用 |

## 领域词汇 (PT 语境, AI 必须理解这些才能看懂注释/日志/规则)

- **PT (Private Tracker)**: 私有种子站, 有严格分享率/做种时长规则。
- **HR (Hit and Run)**: 站点惩罚规则 — 下载后必须在规定时间内做种达到要求(时长/分享率), 否则受罚。本项目自动给"触发 HR"的种子打标 (如 `!!HR3D!!`), 给"已满足 HR"的打标 (如 `--HR3D--`)。触发条件 = 下载比例 (如 80%) 或下载量绝对值。
- **辅种 (cross-seeding)**: 同一份文件在多个站发种, 客户端里存在多个指向相同文件列表的种子。本项目将它们自动归组统一管理。
- **缺文件检查**: 辅种组中若文件被删, 所有同组种子都会失效。项目事件驱动地扫描磁盘, 丢失则整组暂停 + `MISSING` 标签。
- **校验 (checking/recheck)**: qB 对种子逐块哈希校验。
- **跳检 (skip-checking)**: 跳过哈希校验直接做种。本项目实现方式: 导出 .torrent → 删除种子(保留文件) → 重新导入并 `is_skip_checking=True`。**有风险**: 保留标签/分类/限速/路径, 但丢失下载量/上传量/做种时长等统计; 文件内容错误会上传垃圾数据, 被多数 PT 站严令禁止。
- **reannounce (强制汇报)**: 立即向 tracker 汇报, 高频使用有封号风险。
- **单数值限速保护**: 用户手动设置的限速习惯性写成"奇数 KiB/s" (如 2001 KiB/s), 程序检测到当前限速为奇数 KiB 时跳过不覆盖。这是全项目的约定魔法。
- **做种状态词汇**: stalledUP (做种中), pausedUP/stoppedUP (已完成暂停), stalledDL (下载停滞) 等, 完整映射见 [04-rule-system.md](04-rule-system.md) 状态映射表。

## 功能全景 (均可用配置开关)

1. **标签/分类管理** (内置 maintenance 任务): 按 tracker 加/删站点标签; 删除相似标签(大小写差异); 彻底删除标签 (`delete_tags`); 删除无种子使用的标签 (`delete_tags_if_has_no_torrents`); 自动集数标签 (种子添加时从文件列表解析, 单集 `zE${episode_first}` / 多集 `zE${episode_first}-${episode_last}`, 用户可配置模板, 仅集数连续时生成)。
2. **HR 管理** (maintenance 任务内): 触发 HR → 加标签/分类; 做种满 required+extra 或分享率达标 → 加 satisfied 标签/分类。站点配置覆盖全局。
3. **辅种分组** (事件驱动): 相同文件列表的种子归组; 大小不一致 → 警告+整组暂停; 缺文件 → 整组暂停+MISSING; 同组多种子同时下载/已完成与下载中并存 → 警告+整组暂停。
4. **自定义规则引擎** 🚧: 触发时机(目前仅 interval) + 条件(15 种) + 动作(11 种), 支持去重/冷却/断点续跑/错误控制。
5. **限速**: tracker 配置单种限速(种子添加时); 规则动作单种限速; 全局限速曲线 (读 Traffic Monitor 流量历史, 按日/月/N天聚合, 阶梯限速写 qB 全局)。
6. **导出**: `--export-yaml` 从现有种子 tracker 生成配置模板 (尽量保留原配置含注释), `--only-missing` 只导出未配置站点。
7. **状态持久化**: 规则执行历史/上传量快照/自动分类记录/曲线状态/跳检备份元数据 → `state_file` (JSON), 仅退出时落盘。

## 运行模式与入口

```
python src/auto-qb.py [CONFIG] [--export-yaml OUTPUT] [--only-missing] [--dry-run/-n] [--export-torrents_info]
python -m auto_qb  # 等价入口
```

- 正常运行: 连接 qB → 加载规则 → 创建全局任务 → 无限 tick 循环; Ctrl-C 退出时 `save_state()`。
- `--export-yaml`: 连接 qB → exporter 生成模板 → 退出 (不进主循环, 也不加载规则)。
- `--dry-run`: 所有写操作点调用前判断 `dry_run`, 只打日志不碰客户端。

## 顶层目录

```
auto-qb/
├── src/auto-qb.py          # 兼容入口 (8行, 转发到 auto_qb.cli.main)
├── src/auto_qb/            # 主包 (~4700 行, 模块地图见 03)
├── tests/                  # 24 个测试文件 + helpers.py (见 07)
├── config.yml              # ★ 用户真实生产配置 (含真实站点域名/规则, 勿改勿提交, 已 gitignore)
├── minimal.yml             # 最小配置示例
├── logs/auto-qb-state.json # ★ 生产运行状态文件 (与日志同目录, 勿改勿提交, 已 gitignore)
├── 想法.md                 # 设计草稿/TODO (上游文档)
├── README.md               # 用户文档 (2026-09-05 已与代码核对同步)
├── pytest.ini              # pythonpath=src, 默认带 --cov
├── .style.yapf             # facebook 风格, 列宽 120
├── .github/instructions/   # Copilot 指令: 性能优先设计 / 精确类型
└── ai/                     # 本知识库
```

## 四大设计原则 (出现在 想法.md / README / 代码注释中, 评审代码时逐条对照)

1. **幂等性** — 所有动作重复执行无副作用; 窗口语义 (每天一次) 靠 state_file 去重, 不靠循环频率。
2. **保守默认** — 高风险动作默认关闭; 只对显式允许范围生效。
3. **状态持久化** — 跨轮次状态统一进 state_file, 重启继续有效。
4. **fail-fast** — 启动时全量校验配置, 尽早报错。
