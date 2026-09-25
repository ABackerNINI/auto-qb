# 已实现 · 客户端 / 主循环 / 状态 / 内置功能

> 摘要: 摘要: 后端主干与内置功能的落地记录 —— 客户端 / 主循环 / 数据层 / 任务队列 / 托盘 / 通知 / 标签 / HR / 分组。
> 触发: 做过没有, 主循环, 数据层, 任务队列, 托盘, 通知, 标签, HR, 分组, 单实例锁

## 已实现 (✅, 有单测覆盖)

- **HR 状态模型重新梳理 + D 档已免罪来源单列 (2026-09-26, 计划 v3.4)**: 用户指令钉死「优先级
  在线信息.考察中 > 在线信息.已达标 > 在线信息.未达标 > 本地信息(= v3.0 已落码), 最终态
  已达标 | 未达标 | 已免罪, 三个状态都代表结束状态」—— 终态语义收口进主计划 §9 新「状态模型」节
  (A 考察中 = 唯一进行中; 终态展示落点: safe 绿可删 / failed 红考核未通过 / 安全放行)。修复展示缺口:
  WebUI 曾把 D 档已免罪折进「在线·已核实」(与「完整刷新未列出」缺席证据共用 `SRC_SITE_RELEASED`) ⇒
  新增 `SRC_SITE_EXEMPT`「在线·已免罪」, `HrResolution.released_src` / `HrJudgement.verified_source`
  透传 D 档放行出处, `safety_display` 分流(缺席式放行原样 site_released); 前端 `shared/hr.js`
  两张映射表 +1 键(徽标「在线」/ 来源桶「在线核实」, 无新 CSS)。测试 +2 + test_web 字段级 D 档
  断言块, 守阵 SRC_* 常量 8→9, ★红验 3 条全红; 全量 **1637 passed + 1 skipped**(TOTAL 92%);
  计划 [plans/26-09-22-2204-partial-hr-site-verify-plan.html](../plans/26-09-22-2204-partial-hr-site-verify-plan.html)
  §9/§14 v3.4; 档案 [tasks/26-09-22-backend-partial-hr-verify.md](../tasks/26-09-22-backend-partial-hr-verify.md)
- **浏览器扩展运行日志(分级 + 环形上限 + 选项页④区) (2026-09-25)**: `extensions/hr-fetch-proxy` 加日志 ——
  条数 10–10000 可设(默认 1000, 环形丢最旧), 四级 debug/info/warn/error(记录阈值默认 info + 选项页分级过滤),
  明细含毫秒时间 / 收到的命令(kind·id·站点) / 请求类型(拉清单/页面直取/页面渲染/种子下载)与 HTTP 结果 /
  耗时 / 字节数 / 回传后端响应体快照 / 扩展侧硬上限拒发。MV3 SW 随时被回收 ⇒ 唯一事实源
  `chrome.storage.local`(内存环形缓冲 + 防抖 300ms 整份写回; 外部清空经 onChanged 采纳, 免得被内存缓冲盖回);
  选项页④区设置即时生效 + 清空走 `clear-logs` 协议 + 渲染 esc 转义 + 限渲染 3000 行。守阵真跑当场抓到
  flush 链**自引用死锁**(首刷即死锁且无报错, 已修并入坑 `pitfalls/web-ui/extension-bridge.md`); 顺带修选项页
  轮询周期文案漂移(5 分钟→1 分钟)+ 文案↔`POLL_MINUTES` 防漂守阵。新增守阵 3 条, 基线 1576 →
  **1579 collected**(TOTAL 91% 不变); 档案 [tasks/26-09-25-webui-ext-hr-logging.md](../tasks/26-09-25-webui-ext-hr-logging.md)
- **HR 在线核实(部分种子 HR 站点) —— M1 核心管道 + M2 取数通道 + 告警分档/现状报告 (2026-09-24)**: 站点侧核实「哪些种子受 HR 管束」并给出**三态**判定(受管束 / 已核实不受管束 / 未核实)。M1 = `src/auto_qb/hr/` 离线管道(bencode 取 info **原始字节切片**算 infohash · NexusPHP `myhr.php` 解析 · 站点分文件 + **每站点一把锁** · 频控「只向上抖动 + 两级配额 + 熔断 + 时间窗」 · 三态判定与不可变视图 · 刷新管道 · `--hr-once` 只读走查) + 配置全链路(两条配置期 fail-fast: `mode != off` 必配 `hr` 段 / `hr_page_scopes` 必含 A+B+C); M2 = **取数通道**: 后端零 cookie、零直连站点 —— 本地端点(`127.0.0.1` + token + origin/URL 白名单, 只入队) + **取数线程**(按 `poll_interval` 自唤醒、不随主循环 tick、持锁抓取、不碰 state_file/队列/store) + 只读视图**原子发布**(主循环零等待, 只在数据变化时抬 `revision`) + MV3 扩展 `extensions/hr-fetch-proxy/`(哑取数器: 页面**默认无界面直取**、必要时离屏 popup 窗口渲染 / service worker 取 .torrent, 不碰 cookie API); **告警分档与现状可见性**(M2 上线后按用户实报补): 结果对象带 `reason_kind`(budget = 被自己频控拦下 / parse = 页面字段翻页问题), 日志按此分级 —— 节流态只记一条 INFO(按被拦根因去重, 不逐轮刷、绝不 WARNING), 页面改版与取数失败才 WARNING; 新增 `--hr-status [--hr-status-rows N]` 只读现状报告(不取数/不加锁/不写盘/不连 qB, 摊开档位分布、待回填 infohash、配额与熔断、不完备原因与明细表); 告警级别与归属再收敛: 生命周期(启动/关闭/热重挂)与频控节流只记 INFO, 同一事件只由产生处告警一次(`alerted`), 关停时的取消用子类 `HrChannelStopped` 与「没通道」区分; 站点数据文件两层保护(`.bak` 上一版 + 坏文件挪 `.bad-<ts>` 并从备份恢复); 只读口径(dry-run / `--hr-once`)在**成功与失败两条写盘分支**上都拦得住。**M3 判定联动 (2026-09-25)**: 三态判定接进 `TorrentRecord` —— 记录持有 `QbManager.hr` 门面的**稳定引用**(`hr_link`, 由 `TorrentStore` 在构建/变更时挂上), `hr_judgement()` 读取时现算(锚点漂移/视图更新都不需要置脏), `check_hr_condition` / `check_hr_satisfied` **站点侧优先、站点没给再回落本地** ⇒ 打标 / WebUI 视图 / `hr` 规则条件 / `tor.hr_*` 表达式**四个消费点调用点一行未动**; `mode: all` 升为「站点侧驱动 + 未核实恒受管束」(新鲜度闸门 `unknown_policy` 绕不过); `QbManager._hr_anchors()` 按站点给出 `{infohash: HrAnchor}` 供取数线程提前作废本实例放行; WebUI 透出三态 / 依据 / 达标来源与站点侧值(档位·还需做种·剩余达标·分享率·站点下载量)供对账; **零静默变更**两道门(站点 `mode != off` + 全局 `hr_check.enabled`)。余 M4(多站点)未落地 —— 见 [tasks/26-09-22-backend-partial-hr-verify.md](../tasks/26-09-22-backend-partial-hr-verify.md) 与 [plans/26-09-22-2204-partial-hr-site-verify-plan.html](../plans/26-09-22-2204-partial-hr-site-verify-plan.html)。
- **state.json 损坏静默清空 / .bak 从不用于恢复 · issue 26-09-21-1347 (2026-09-22, 已置 `Fixed`, 已入库 `e11df80`)**: `_load_state` 的 `except (FileNotFoundError, json.JSONDecodeError): pass` 把「文件损坏」与「首启」同等对待 ⇒ 损坏时静默返回 `{}`(exec_history / skip_check_day / recheck_fails / 上传基线全丢且无线索), 而 `atomic_write(keep_backup=True)` 每次写盘前复制的 `state.json.bak` **全库零读取方**。**修法 = 拆三态 + 回退 + 自愈**: ①新增 `_read_state_file` 返回 `dict`(可用) / `None`(不存在=首启, 静默) / 哨兵 `_CORRUPT`(存在但非法 JSON、非 dict、非法 UTF-8; `OSError` 故意不吞 —— 那是环境问题不是内容问题) ②见 `_CORRUPT` 记 WARNING(损坏文件**原样保留不删**)并回退 `<state_file>.bak`, 读到合法 dict 即用以 INFO 记「用了备份」; 备份也不可用才 `{}` 并再告警说清后果 ③**自愈写回** `_write_back_recovered` —— 把恢复出的内容写回主文件且**刻意不带 `keep_backup`**, 否则下次 `save_state` 会把损坏内容复制成新的 `.bak`, 把唯一一份好备份盖掉(等于这次恢复白做) ④备份后缀单点化 `utils.BACKUP_SUFFIX`(写侧 `atomic_write` 与读侧共用, 防命名漂移)。**守阵 4 条**(回退+自愈 / 无备份时两条 WARNING / 首启不得告警 / 自愈写回失败只告警不抛)+ `test_utils` 备份路径断言改按常量; 红验: 运行期把 `_load_state` 打回旧实现 ⇒ 新守阵必红。全量 **1152 → 1160 passed + 1 skipped**。附带发现(报告里标「可选低优先」的孤儿 `state.json.*.tmp` 启动清理)
**也已一并修完**: 新增 `_cleanup_orphan_tmp`, 挂在 `QbManager.__init__` **持锁之后**(没锁说明有别的实例在写,
删它的临时文件会让那次写盘 `os.replace` 失败 ⇒ 状态白丢一次更新), 只认 `<state_file>.<随机>.tmp` 这一个形状
(`.bak` 是恢复凭据、别人的 `*.tmp` 与空随机段一概不碰), 只读模式 `no_lock=True` 不做这次磁盘副作用; 守阵 4 条
含一条**接线守阵**(源码里必须出现在 `acquire()` 之后且落在 `if not no_lock` 内)+ 幂等断言。报告 [issues/26-09-21-1347-bug-state-load-corrupt-silent-reset.html](../issues/26-09-21-1347-bug-state-load-corrupt-silent-reset.html)。
- 跳检备份时机修复 · issue 26-09-21-1347 (2026-09-22, 已置 `Fixed`): `.torrent` 备份原先只在**重加的两条失败分支**上落盘, 而删除是跳检链上第一个不可逆步骤 ⇒ 「删除已生效 → 重加未被 qB 接受」这个约 0.5~5.5s 的缝隙内崩溃/强杀, 种子从客户端消失、`data` 只在内存、state 无在途标记, 重启后无任何恢复凭据(需人工回站点重下 .torrent)。**修法 = 只挪调用时机**: 阶段 2 导出成功后立刻走现成的 `_backup_torrent`(落盘 + 元数据 + 立即 `save_state`), 并新增配对的 `_clear_backup` —— 重加确认成功后清理(文件 + 元数据)、删除未生效(种子仍在)也清理, 只有重加失败/崩溃才留下备份; 备份写不进去则**不删除**直接 fail(无损失)。**守阵 3 条**: ①在客户端的 `torrents_delete` 里快照备份文件是否存在(只查最终结果无法区分"之前写的"还是"之后补的") ②删除未生效 → 备份必须被清掉 ③备份失败 → 不得发出 delete。⚠ 顺带把 `test_checking.py::make_mgr` 改成**未指定 state_file 时自动发一份临时 state 文件** —— 跳检现在每次都真实落盘/删除备份, 留空会写到 CWD=仓库根(污染仓库 + 被 `tests/sidefx.py` 判成越界删除)。全量 **1142 → 1145 passed**; 知识库: `rule-system.md` / `config-reference.md` / `systemPatterns.md` / `docs/configuration.md` 已回写"备份先于删除"。报告 [issues/26-09-21-1347-bug-skip-checking-readd-no-backup-window.html](../issues/26-09-21-1347-bug-skip-checking-readd-no-backup-window.html)。
- 导出 .torrent 中文名 500 已修 (2026-09-17, 已入库 `4de0953`): `/api/torrents/{hash}/export` 把种子名直拼进 `Content-Disposition`, 而 HTTP 头只能 latin-1 ⇒ 中文名触发 `UnicodeEncodeError` 500。修法: 新增 `web.content_disposition(filename, fallback, ext)` 双段头(`filename=` ASCII 回退 + `filename*=UTF-8''<百分号编码>`)并清洗控制字符; 测试 `test_content_disposition_encoding` + 导出端点非 ASCII 用例。
- TorrentRecord 全字段缓存 (2026-09-15): 快照 21 → 70 字段(必需 21 + 重加升格 6 + 可选扩展 43, 字段定稿参照用户提供的真机 TorrentDictionary 样例 + 真机冒烟补 4 字段), 为 WebUI 后续功能供数; D1-D5 决策见 [memory-bank/plans/26-09-15-1302-record-full-fields-plan.html](../plans/26-09-15-1302-record-full-fields-plan.html): slots 全量声明(_raw 降为前向兼容兜底)/RE_ADD_FIELDS 升格进快照(变化开始计入变化集)/新字段全可选(默认值取 qB 哨兵 -1/-2/8640000, REQUIRED 校验面不变)/缓存≠展示(新字段不进 _VIEW_FIELDS, 视图重建成本零变化, 测试锁死)/哨兵原样透传; 新增 `to_dict()` 全字段导出; 真机只读冒烟(119 种子)响应字段全声明 _raw 无残留; 测试 +9 净 +7, 基线 879 passed; 视图/规则/HR/分组消费字段全在旧集合内零行为变化
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
  [26-09-21-1347-bug-state-load-corrupt-silent-reset.html](../issues/26-09-21-1347-bug-state-load-corrupt-silent-reset.html)
  已置 `Fixed`(索引已重建)。**附带发现(孤儿 `state.json.*.tmp` 启动清理)也已一并修完** —— 新增
  `_cleanup_orphan_tmp()`, 挂在 `QbManager.__init__` **持锁之后**(没锁说明有别的实例在写, 删它的临时文件
  会让那次 `os.replace` 失败 ⇒ 状态白丢一次更新), 只认 `<state_file>.<随机>.tmp` 这一个形状(`.bak` 是恢复
  凭据、别人的 `*.tmp` 与空随机段一概不碰), `no_lock=True` 的只读模式不调用; 守阵 4 条(含**接线守阵**:
  源码里必须出现在 `acquire()` 之后且落在 `if not no_lock` 内 + 幂等断言)。全量 **1160 passed + 1 skipped**。
  ✅ **本批改动(源码 3 文件 + 测试 1 文件 + 知识库 5 文件)已入库 `f261de7`**(Gitee + GitHub 均推上)。
  🧪 端到端复核(真实 `QbManager(..., no_lock=False)` 构造路径): 损坏 → 内存 state == `.bak` / 主文件被自愈
  写回 / 孤儿 tmp 被清理 / `.bak` 未被损坏内容盖掉 —— 四件事全成立(脚本在 `H:/Temp/e2e_state_recovery_check.py`,
  未进仓库)。
