# 核心模块 · 运行时主干

> 行数为 2026-10-03 实测(`wc -l`, 快照日期即口径截止日)。所有路径相对 `src/auto_qb/`(除注明)。

> 摘要: 入口 / 主协调者 / 模块宿主与模块包 / 表现层门面 / HTTP 层 / 客户端 / 队列 / Facade / 锁 / 工具 / 日志 / 错误根。
> 触发: cli, qbmanager, webui-runtime, qbclient, taskqueue, qbapi, locking, utils, logging, errors

## 核心模块

| 文件 | 行数 | 职责 | 关键内容 |
|------|------|------|----------|
| `cli.py` | 211 | argparse 入口 | `--export-yaml/-e`, `--only-missing`, `--dry-run/-n`, `--export-torrents_info`; 导出模式不进主循环; **单点捕获 `AutoQbError` 体系**(ConfigError 输出 `配置错误: ...` 前缀, 锁/qB 兼容等其它 AutoQbError 直接输出消息; 均无堆栈, 退出码 1; 非 AutoQbError 异常照常抛出); 运行期致命错误退出前 best-effort 补发通知 (`notify_fatal`); `--tray` 托盘模式入口(与导出模式互斥; 双开唤起失败回退常规锁错误); 入口 `sys.exit(main())` 使退出码生效 |
| `core/qbmanager.py` | — | 已外迁 | 见 [attachments/core-runtime-details.md](attachments/core-runtime-details.md)(逐字原文) |
| `core/module.py` | — | 已外迁 | 见 [attachments/core-runtime-details.md](attachments/core-runtime-details.md)(逐字原文) |
| `core/modules/` (包) | — | 见 [conventions/modules.md](../conventions/modules.md) | 旧「2,390 行 / 9 文件 / 十模块」结构描述已过期删除; 现行装配清单在 `core/qbmanager.py` 构造期。 |
| `core/state.py` | 228 (26-10-03 实测) | **状态持久化服务 StateService**(2026-09-30 P0 自 RuleEngineMixin 迁出): state.json 读写的单点 —— load(损坏回退 .bak + 自愈写回)/_migrate_state_dict(schema 升级链)/save(原子写 + keep_backup + 版本章)/materialize_migration/maybe_flush(周期落盘, interval 由调用方现读传入保 L0 语义)/record_execution/get_exec_record/bind_field_snapshots/cleanup_orphan_tmp; 单一写线程约束不变(仅主循环线程); **调用方一律走 `ctx.state.*`** —— manager 旧调用面委托已随别名层处置 W3 删除(2026-10-01), 见 [client-and-state.md](../systemPatterns/client-and-state.md) |
| `webui/runtime.py` | — | 已外迁 | 见 [attachments/core-runtime-details.md](attachments/core-runtime-details.md)(逐字原文) |
| `webui/server/` (包) | — | 已外迁 | 见 [attachments/core-runtime-details.md](attachments/core-runtime-details.md)(逐字原文) |
| `core/qbclient.py` | 64 (26-10-03 实测) | qB 客户端构造(2026-09-15 拆分) | `_LOCAL_HOSTS`/`_is_local_qb`/`LocalQbClient`(本地地址强制 Session 关闭 requests `trust_env`)/`new_client`; test_local_qb_service 直接导入 |
| `core/taskqueue.py` | 218 (26-10-03 实测) | 单任务队列 | 生命周期只有 `add_task`(入队; check 自动登记 `_active_checks` 在途, 重复返回 False)/`run_due`(到期执行+收尾: True 重入队 / False 消亡释放) 两个动词; `Task.reset()` 显式重置断点; 无 defer/resume 挂起态 —— 推迟执行由子任务按情况重新入队; `active_check_hashes`(组内校验串行化依赖)/`active_check_age`(登记时长, 供闸门 TTL 判泄漏) |
| `core/qbapi.py` | 413 (26-10-03 实测) | qB API Facade | `QbApi`: store 必传, 确定性字段写后同步(运行状态只等 qB 同步), 读走缓存, `sync_maindata(rid)` 增量同步透传, `get/set_global_speed_limits`(qB5.0 transfer 端点) |
| `infra/errors.py` (包级) | 22 (26-10-03 实测) | `AutoQbError` 致命错误根: CLI 单点捕获(stderr 干净 + 退出码 1); 子类并列: `ConfigError`(config)/`SingleInstanceLockError`(locking)/`QbCompatError`(torrents)/`WebUIBindError`(`webui/server/lifecycle.py`, WEBUI 启动期 bind 失败) |
| `infra/locking.py` | 112 (26-10-03 实测不变) | 单实例锁 | `SingleInstanceLock`(基于第三方 `filelock` + 伴生 `<lock>.meta.json` 记录 PID/启动时间/配置路径); `SingleInstanceLockError(AutoQbError)` 走 CLI 退出码 1; 仅正常 run 模式持锁, `--export-yaml` 等只读模式通过 `no_lock=True` 跳过; 锁文件路径 `<state_file 去扩展名>.lock` (避免与 state 文件同目录同名冲突) |
| `infra/port_owner.py` | 228 (26-11-03 实测) | **端口占用者探针**(plan 26-11-03-0930, 2026-11-03): `describe_port_owner(host, port)` 三平台查监听进程(Windows netstat+tasklist / Linux ss / macOS lsof), 返回三态 `found`/`absent`/`unavailable`; 分步与总预算(1.5s)双重截止, 任何异常一律降级为 `unavailable` 且**绝不抛出** —— 仅用于启动失败诊断块, 不影响 fail-fast 判定 |
| `infra/utils.py` | 1075 (26-10-03 实测) | 通用工具 | `parse_time/parse_fsize/parse_speed/parse_bool/parse_compare/compare/parse_hr_condition`; `MatchPattern.parse`(regex:/:ignore_case 语法解析唯一入口)+ `match_value`(单值多模式匹配核心); `match_tag_patterns`/`match_path_patterns` 为薄包装; `path_normalize`; `match_tracker_confs`(hostname 精确匹配); `add_long_path_prefix_for_win`(长路径 `\\?\` 前缀); `open_path`(跨平台打开: Windows 走 `_win_shell_open` 的 Shell PIDL 长路径路线, 失败退回 `_win_string_open`; 打开前后快照差集找新弹窗口并经 `_win_force_foreground` 的 AttachThreadInput 强推前台 —— 后台进程弹窗被前台锁压住的修复, 见 pitfalls/backend/explorer-foreground.md; macOS/Linux 走 `open`/`xdg-open`)+ 私有 `_exists_dir`/`_exists_file`(长路径判定必须带前缀)、`WIN_MAX_PATH`; `extract_tracker_hostnames`; `fmt_speed`; `replace_vars`(规则变量替换); `timer` 装饰器 |
| `infra/logging.py` | 128 (26-10-03 实测) | 日志配置 | `setup_logging`: 控制台 + RotatingFileHandler(5 备份), **两者均跟随配置 level**; root 跟随配置拦第三方 DEBUG, `auto_qb` logger 放开 DEBUG, `qbittorrentapi` 封顶 INFO(排除请求噪音), `urllib3` 封顶 ERROR(排除断连期间连接重试的 Retry WARNING 刷屏)。注意与 stdlib logging 同名, 包内相对导入 |
