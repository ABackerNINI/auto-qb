# 已实现 · 客户端 / 主循环 / 状态 / 内置功能

> 摘要: 摘要: 后端主干与内置功能的落地记录 —— 客户端 / 主循环 / 数据层 / 任务队列 / 托盘 / 通知 / 标签 / HR / 分组。
> 触发: 做过没有, 主循环, 数据层, 任务队列, 托盘, 通知, 标签, HR, 分组, 单实例锁

## 已实现 (✅, 有单测覆盖)

- **state.json 损坏静默清空 / .bak 从不用于恢复 · issue 26-09-21-1347 (2026-09-22, 已置 `Fixed`, 已入库 `e11df80`)**: `_load_state` 的 `except (FileNotFoundError, json.JSONDecodeError): pass` 把「文件损坏」与「首启」同等对待 ⇒ 损坏时静默返回 `{}`(exec_history / skip_check_day / recheck_fails / 上传基线全丢且无线索), 而 `atomic_write(keep_backup=True)` 每次写盘前复制的 `state.json.bak` **全库零读取方**。**修法 = 拆三态 + 回退 + 自愈**: ①新增 `_read_state_file` 返回 `dict`(可用) / `None`(不存在=首启, 静默) / 哨兵 `_CORRUPT`(存在但非法 JSON、非 dict、非法 UTF-8; `OSError` 故意不吞 —— 那是环境问题不是内容问题) ②见 `_CORRUPT` 记 WARNING(损坏文件**原样保留不删**)并回退 `<state_file>.bak`, 读到合法 dict 即用以 INFO 记「用了备份」; 备份也不可用才 `{}` 并再告警说清后果 ③**自愈写回** `_write_back_recovered` —— 把恢复出的内容写回主文件且**刻意不带 `keep_backup`**, 否则下次 `save_state` 会把损坏内容复制成新的 `.bak`, 把唯一一份好备份盖掉(等于这次恢复白做) ④备份后缀单点化 `utils.BACKUP_SUFFIX`(写侧 `atomic_write` 与读侧共用, 防命名漂移)。**守阵 4 条**(回退+自愈 / 无备份时两条 WARNING / 首启不得告警 / 自愈写回失败只告警不抛)+ `test_utils` 备份路径断言改按常量; 红验: 运行期把 `_load_state` 打回旧实现 ⇒ 新守阵必红。全量 **1152 → 1160 passed + 1 skipped**。附带发现(报告里标「可选低优先」的孤儿 `state.json.*.tmp` 启动清理)
**也已一并修完**: 新增 `_cleanup_orphan_tmp`, 挂在 `QbManager.__init__` **持锁之后**(没锁说明有别的实例在写,
删它的临时文件会让那次写盘 `os.replace` 失败 ⇒ 状态白丢一次更新), 只认 `<state_file>.<随机>.tmp` 这一个形状
(`.bak` 是恢复凭据、别人的 `*.tmp` 与空随机段一概不碰), 只读模式 `no_lock=True` 不做这次磁盘副作用; 守阵 4 条
含一条**接线守阵**(源码里必须出现在 `acquire()` 之后且落在 `if not no_lock` 内)+ 幂等断言。报告 [issues/26-09-21-1347-bug-state-load-corrupt-silent-reset.html](issues/26-09-21-1347-bug-state-load-corrupt-silent-reset.html)。
- 跳检备份时机修复 · issue 26-09-21-1347 (2026-09-22, 已置 `Fixed`): `.torrent` 备份原先只在**重加的两条失败分支**上落盘, 而删除是跳检链上第一个不可逆步骤 ⇒ 「删除已生效 → 重加未被 qB 接受」这个约 0.5~5.5s 的缝隙内崩溃/强杀, 种子从客户端消失、`data` 只在内存、state 无在途标记, 重启后无任何恢复凭据(需人工回站点重下 .torrent)。**修法 = 只挪调用时机**: 阶段 2 导出成功后立刻走现成的 `_backup_torrent`(落盘 + 元数据 + 立即 `save_state`), 并新增配对的 `_clear_backup` —— 重加确认成功后清理(文件 + 元数据)、删除未生效(种子仍在)也清理, 只有重加失败/崩溃才留下备份; 备份写不进去则**不删除**直接 fail(无损失)。**守阵 3 条**: ①在客户端的 `torrents_delete` 里快照备份文件是否存在(只查最终结果无法区分"之前写的"还是"之后补的") ②删除未生效 → 备份必须被清掉 ③备份失败 → 不得发出 delete。⚠ 顺带把 `test_checking.py::make_mgr` 改成**未指定 state_file 时自动发一份临时 state 文件** —— 跳检现在每次都真实落盘/删除备份, 留空会写到 CWD=仓库根(污染仓库 + 被 `tests/sidefx.py` 判成越界删除)。全量 **1142 → 1145 passed**; 知识库: `rule-system.md` / `config-reference.md` / `systemPatterns.md` / `docs/configuration.md` 已回写"备份先于删除"。报告 [issues/26-09-21-1347-bug-skip-checking-readd-no-backup-window.html](issues/26-09-21-1347-bug-skip-checking-readd-no-backup-window.html)。
- 导出 .torrent 中文名 500 已修 (2026-09-17, 已入库 `4de0953`): `/api/torrents/{hash}/export` 把种子名直拼进 `Content-Disposition`, 而 HTTP 头只能 latin-1 ⇒ 中文名触发 `UnicodeEncodeError` 500。修法: 新增 `web.content_disposition(filename, fallback, ext)` 双段头(`filename=` ASCII 回退 + `filename*=UTF-8''<百分号编码>`)并清洗控制字符; 测试 `test_content_disposition_encoding` + 导出端点非 ASCII 用例。
- TorrentRecord 全字段缓存 (2026-09-15): 快照 21 → 70 字段(必需 21 + 重加升格 6 + 可选扩展 43, 字段定稿参照用户提供的真机 TorrentDictionary 样例 + 真机冒烟补 4 字段), 为 WebUI 后续功能供数; D1-D5 决策见 [docs/plans/26-09-15-1302-record-full-fields-plan.html](../docs/plans/26-09-15-1302-record-full-fields-plan.html): slots 全量声明(_raw 降为前向兼容兜底)/RE_ADD_FIELDS 升格进快照(变化开始计入变化集)/新字段全可选(默认值取 qB 哨兵 -1/-2/8640000, REQUIRED 校验面不变)/缓存≠展示(新字段不进 _VIEW_FIELDS, 视图重建成本零变化, 测试锁死)/哨兵原样透传; 新增 `to_dict()` 全字段导出; 真机只读冒烟(119 种子)响应字段全声明 _raw 无残留; 测试 +9 净 +7, 基线 879 passed; 视图/规则/HR/分组消费字段全在旧集合内零行为变化
- 标签/分类管理: 站点标签加/删、相似标签清理、`delete_tags`/`delete_tags_if_has_no_torrents` 全局清理、集数标签
- HR 管理: 触发标签/分类 + satisfied 标签/分类, 站点覆盖全局
- 辅种分组: 增量归组、大小一致性、缺文件事件驱动扫描 (删除/上传转暂停/路径变化)、下载冲突检查
- 托盘常驻 UI (2026-09-12, --tray): `ui.py` —— CustomTkinter 深色窗口(状态卡片/最近日志/暂停恢复/通知热切换/开机自启)+ pystray 托盘(6 项菜单, 勾选态实时); 运行时暂停/恢复 = pause_event 完全旁观, 恢复后增量 diff 补上; 双开唤起 = 单实例锁 + localhost IPC(ui.port, 第二实例静默退出 0); 托管模式主循环移入后台线程(单一写线程约束保持), 首连失败重试常驻; GUI 栈仅 tray 分支加载; 通知开关支持从未配置状态热挂载(setup_notify force, 会话级); toast 点击激活唤起窗口(launch_arguments 经 AUMID 快捷方式 Arguments); 窗口图标 CTk iconbitmap 防 CTk 默认覆盖(assets/icon.ico); 打开日志目录前绝对化路径并确保目录存在, 托盘事件单点失败不中断 UI 轮询链; 新依赖 pystray/Pillow/customtkinter
- 主动通知 (2026-09-12): `notify.py` 零第三方依赖 —— NotifyHandler 挂 `auto_qb` logger 复用日志规范, PlatformChannel 按平台分派(win32=PowerShell WinRT toast / linux=notify-send / darwin=osascript), quiet_hours 免打扰(与 date_time 共用 utils.time_in_range) + 每小时上限 + 同键去重窗(内存态); CLI 致命退出补发 notify_fatal; dry-run 不挂载; toast 来源显示 "AutoQB" —— 首次运行幂等注册开始菜单快捷方式 AutoQB.lnk(%APPDATA% Programs 目录, 隐式 AppUserModelID), 注册失败回退 PowerShell 来源
- 任务队列: 单 heapq 队列 + `add_task(keep_progress=...)` 断点语义 + check 轮询在途去重 (12f3b46 重构完成)
- 数据层: TorrentStore 快照+惰性缓存+分组索引; QbApi Facade写后同步
- YAML 导出 (`--export-yaml`, `--only-missing`), qB 5.0 API 适配
- 单实例锁 (2026-09-05): 基于第三方 `filelock`, 锁文件 `<state_file 去扩展名>.lock` + 伴生 `.meta.json`; 仅正常 `run()` 模式持锁, `--export-yaml` 等只读模式通过 `no_lock=True` 跳过; 失败抛 `SingleInstanceLockError(AutoQbError)`, CLI 单点捕获 AutoQbError 体系干净退出 (退出码 1, stderr 无堆栈); 陈旧锁不接管 (OS 句柄随进程退出自动释放, 必要时手动删除)
- **🆕 state.json 损坏静默清空 + .bak 从不用于恢复 —— 已修并验证, 已入库 `e11df80`(见本文件顶部「最后更新」首条)**: issue
  [26-09-21-1347-bug-state-load-corrupt-silent-reset.html](issues/26-09-21-1347-bug-state-load-corrupt-silent-reset.html)
  已置 `Fixed`(索引已重建)。**附带发现(孤儿 `state.json.*.tmp` 启动清理)也已一并修完** —— 新增
  `_cleanup_orphan_tmp()`, 挂在 `QbManager.__init__` **持锁之后**(没锁说明有别的实例在写, 删它的临时文件
  会让那次 `os.replace` 失败 ⇒ 状态白丢一次更新), 只认 `<state_file>.<随机>.tmp` 这一个形状(`.bak` 是恢复
  凭据、别人的 `*.tmp` 与空随机段一概不碰), `no_lock=True` 的只读模式不调用; 守阵 4 条(含**接线守阵**:
  源码里必须出现在 `acquire()` 之后且落在 `if not no_lock` 内 + 幂等断言)。全量 **1160 passed + 1 skipped**。
  ✅ **本批改动(源码 3 文件 + 测试 1 文件 + 知识库 5 文件)已入库 `f261de7`**(Gitee + GitHub 均推上)。
  🧪 端到端复核(真实 `QbManager(..., no_lock=False)` 构造路径): 损坏 → 内存 state == `.bak` / 主文件被自愈
  写回 / 孤儿 tmp 被清理 / `.bak` 未被损坏内容盖掉 —— 四件事全成立(脚本在 `H:/Temp/e2e_state_recovery_check.py`,
  未进仓库)。
