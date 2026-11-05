# 已实现 · 客户端 / 主循环 / 状态 · 2026-09 段 (外迁存档)

> 摘要: 2026-09-15~09-29 段原文逐字外迁 —— HR 站点侧核实 / CarPT 适配 / v3 波次模型 / 状态模型 / 扩展日志 / state.json 恢复 / 跳检备份 / 全字段缓存等 15 条。
> 触发: 已实现, HR, state.json, 跳检, TorrentRecord, 外迁存档

> 本文件是外迁存档: 主档 `memory-bank/progress/implemented-core.md` 的 2026-09-15~09-29 段 原文逐字搬来(仅相对链接整体下移一层 —— 本文件在 `progress/attachments/`); 主档原位留指针。

- **站点接入数据白屏修复: hr.js methods 裸调用缺 `this.` (2026-09-25, `c00fc94`)**: `hrSiteLine` 三处裸调 `fmtDuration`/`fmtSize`, 未接入站点时数据分支不进不响, Vue 3 渲染 ReferenceError 卸整树 = 全页白屏; 补 `this.` 修复, 桩服务加 `--hr-site` 注入堵替身盲区。判据 → [pitfalls/web-ui/vue-reactivity.md](../../pitfalls/web-ui/vue-reactivity.md)。
- **限速曲线手动保护日志节流 (2026-09-26, `16f1adc`)**: 手动保护分支逐轮 INFO 刷屏(手动值是持续状态); 抽 `_log_manual_skip`(进入/变化记 INFO + 每 1h 提醒, 其余 DEBUG, 退出清记忆) + `_MANUAL_REMIND_GAP` 常量; 节流不是行为开关, 不加配置键。判据 → [pitfalls/ops/alert-levels.md](../../pitfalls/ops/alert-levels.md)。
- **HR 接入 CarPT 适配器 (2026-09-27, 档案 [26-09-22-backend-partial-hr-verify](../../tasks/26-09-22-backend-partial-hr-verify.md))**: v3.5 站点参数化 + `hr/adapters/carpt.py` 新增; 验证挖出 H&R ID 与种子 id 是两个 id 空间 ⇒ 新增 `HrEntry.dl_id`(行内链接提取)。
- **HR 站点配置收敛: 内置站点档案 (2026-09-27)**: 站点启用改为 `hr_check.sites.<档案id>`(单点 `config/site_presets.py`)点选 + 微调, loaders 按域名交集自动绑定派生 `trackers.*.hr_check`, 旧键兼容等价迁移, 生产 config 零修改行为不变。计划 26-09-27-1318。
- **移除不成熟的限速统计设计 (2026-09-27, 计划 [26-09-27-1232](../../plans/26-09-27-1232-plan-remove-upload-stats.html))**: upload_size 四条件 + begin_round 底座整体拆除(7 代码触点 + state v1→v2 迁移清 upload_snapshots), 重设计候选入 feature issue 26-09-27-1248。
- **HR v3 波次模型重建 + 重写后复审 (2026-09-29, 计划 [26-09-28-1932](../../plans/26-09-28-1932-plan-hr-verify-rebuild.html) / 报告 [26-09-29-0404](../../reports/26-09-29-0404-report-hr-verify-v3-audit.html))**: 判定四行表 + 单波型波次引擎 + 三键频控 + 配置 v3(40→14 键); 复审总评通过附 1 高危 H1(Retry-After 不跨波)等, 已随报告 §13.5 修复; 防伪收敛为流转守恒 + 零行戳两道。真机走查遗留见档案。

- **HR 在线核实 v3 波次模型重建 (2026-09-29, 计划 26-09-28-1932 M1–M5)**: 判定=四行判定表
  (考察中管束/终态放行/无证据本地兜底硬编码, 12 格矩阵单测); 取数=单波型波次引擎(全量对账 +
  A/B/C 轮流 + 三停翻条件 + 档位级截断有效性 + 失踪观察期 + 流转守恒/骤降/零行戳三道防伪 +
  身份登记一次下载); 频控=单模型三键(熔断/停用/退避全删); 配置 40→14 键(config v2→v3 +
  hr_site v1→v2 迁移, 档案 listing 字段); `--hr-resume` 删 / `--hr-confirm-empty` 增(含 WebUI
  按钮)。HR 测试按新模型重写约 200 条; 全量 1743 passed + 3 skipped; 基线切片 26-09-29;
  档案 [tasks/26-09-22-backend-partial-hr-verify.md](../../tasks/26-09-22-backend-partial-hr-verify.md)。
  **追记(2026-09-29)**: 粗配判据收紧(剔技术噪声整词后再算 ≥K 重合, K 仍 12) —— 真实数据 159 → 31 对、
  新增 0; 坑档 [pitfalls/backend/fuzzy-match-noise.md](../../pitfalls/backend/fuzzy-match-noise.md)。

- **HR 状态模型重新梳理 + D 档已免罪来源单列 (2026-09-26, 计划 v3.4)**: 用户指令钉死「优先级
  在线信息.考察中 > 在线信息.已达标 > 在线信息.未达标 > 本地信息(= v3.0 已落码), 最终态
  已达标 | 未达标 | 已免罪, 三个状态都代表结束状态」—— 终态语义收口进主计划 §9 新「状态模型」节
  (A 考察中 = 唯一进行中; 终态展示落点: safe 绿可删 / failed 红考核未通过 / 安全放行)。修复展示缺口:
  WebUI 曾把 D 档已免罪折进「在线·已核实」(与「完整刷新未列出」缺席证据共用 `SRC_SITE_RELEASED`) ⇒
  新增 `SRC_SITE_EXEMPT`「在线·已免罪」, `HrResolution.released_src` / `HrJudgement.verified_source`
  透传 D 档放行出处, `safety_display` 分流(缺席式放行原样 site_released); 前端 `shared/hr.js`
  两张映射表 +1 键(徽标「在线」/ 来源桶「在线核实」, 无新 CSS)。测试 +2 + test_web 字段级 D 档
  断言块, 守阵 SRC_* 常量 8→9, ★红验 3 条全红; 全量 **1637 passed + 1 skipped**(TOTAL 92%);
  计划 [plans/26-09-22-2204-partial-hr-site-verify-plan.html](../../plans/26-09-22-2204-partial-hr-site-verify-plan.html)
  §9/§14 v3.4; 档案 [tasks/26-09-22-backend-partial-hr-verify.md](../../tasks/26-09-22-backend-partial-hr-verify.md);
  **已入库 `a497fba`**(合并远端 4 笔[docker 部署/种子级标签分类编辑/分享率列对齐]后经合并提交 `d72a538` 推送,
  合并树重测 1641 collected: 1640 passed + 1 skipped / TOTAL 92%)
- **浏览器扩展运行日志(分级 + 环形上限 + 选项页④区) (2026-09-25)**: `extensions/hr-fetch-proxy` 加日志 ——
  条数 10–10000 可设(默认 1000, 环形丢最旧), 四级 debug/info/warn/error(记录阈值默认 info + 选项页分级过滤),
  明细含毫秒时间 / 收到的命令(kind·id·站点) / 请求类型(拉清单/页面直取/页面渲染/种子下载)与 HTTP 结果 /
  耗时 / 字节数 / 回传后端响应体快照 / 扩展侧硬上限拒发。MV3 SW 随时被回收 ⇒ 唯一事实源
  `chrome.storage.local`(内存环形缓冲 + 防抖 300ms 整份写回; 外部清空经 onChanged 采纳, 免得被内存缓冲盖回);
  选项页④区设置即时生效 + 清空走 `clear-logs` 协议 + 渲染 esc 转义 + 限渲染 3000 行。守阵真跑当场抓到
  flush 链**自引用死锁**(首刷即死锁且无报错, 已修并入坑 `pitfalls/web-ui/extension-bridge.md`); 顺带修选项页
  轮询周期文案漂移(5 分钟→1 分钟)+ 文案↔`POLL_MINUTES` 防漂守阵。新增守阵 3 条, 基线 1576 →
  **1579 collected**(TOTAL 91% 不变); 档案 [tasks/26-09-25-webui-ext-hr-logging.md](../../tasks/26-09-25-webui-ext-hr-logging.md)
- **HR 在线核实(部分种子 HR 站点) —— M1 核心管道 + M2 取数通道 + 告警分档/现状报告 (2026-09-24)**: 站点侧核实「哪些种子受 HR 管束」并给出**三态**判定(受管束 / 已核实不受管束 / 未核实)。M1 = `src/auto_qb/hr/` 离线管道(bencode 取 info **原始字节切片**算 infohash · NexusPHP `myhr.php` 解析 · 站点分文件 + **每站点一把锁** · 频控「只向上抖动 + 两级配额 + 熔断 + 时间窗」 · 三态判定与不可变视图 · 刷新管道 · `--hr-once` 只读走查) + 配置全链路(两条配置期 fail-fast: `mode != off` 必配 `hr` 段 / `hr_page_scopes` 必含 A+B+C); M2 = **取数通道**: 后端零 cookie、零直连站点 —— 本地端点(`host` 可配默认回环 + `port` 默认 0 随机 + token + origin/URL 白名单 + 发现端点自动分发与配对码门, 只入队; 去端口+跨机 = 计划 26-10-14-1241) + **取数线程**(按 `poll_interval` 自唤醒、不随主循环 tick、持锁抓取、不碰 state_file/队列/store) + 只读视图**原子发布**(主循环零等待, 只在数据变化时抬 `revision`) + MV3 扩展 `extensions/hr-fetch-proxy/`(哑取数器: 页面**默认无界面直取**、必要时离屏 popup 窗口渲染 / service worker 取 .torrent, 不碰 cookie API); **告警分档与现状可见性**(M2 上线后按用户实报补): 结果对象带 `reason_kind`(budget = 被自己频控拦下 / parse = 页面字段翻页问题), 日志按此分级 —— 节流态只记一条 INFO(按被拦根因去重), 页面改版与取数失败才 WARNING; 新增 `--hr-status [--hr-status-rows N]` 只读现状报告; 生命周期/节流只记 INFO, 同一事件只由产生处告警一次(`alerted`); 站点数据文件两层保护(`.bak` + `.bad-<ts>`); 只读口径在**成功与失败两条写盘分支**上都拦得住。**M3 判定联动 (2026-09-25)**: 三态判定接进 `TorrentRecord`(记录持 `QbManager.hr` 门面稳定引用 `hr_link`, 读取时现算), `check_hr_condition` / `check_hr_satisfied` **站点侧优先、站点没给再回落本地** ⇒ 打标 / WebUI 视图 / `hr` 规则条件 / `tor.hr_*` 表达式四个消费点一行未动; `mode: all` 升为「站点侧驱动 + 未核实恒受管束」; WebUI 透出三态/依据/达标来源供对账; **零静默变更**两道门。余 M4(多站点)未落地 —— 明细见 [tasks/26-09-22-backend-partial-hr-verify.md](../../tasks/26-09-22-backend-partial-hr-verify.md)。
- **state.json 损坏静默清空 / .bak 从不用于恢复 · issue 26-09-21-1347 (2026-09-22, 已置 `Fixed`, 已入库 `e11df80`)**: `_load_state` 的 `except (FileNotFoundError, json.JSONDecodeError): pass` 把「文件损坏」与「首启」同等对待 ⇒ 损坏时静默返回 `{}`(exec_history / skip_check_day / recheck_fails / 上传基线全丢且无线索), 而 `atomic_write(keep_backup=True)` 每次写盘前复制的 `state.json.bak` **全库零读取方**。**修法 = 拆三态 + 回退 + 自愈**: ①新增 `_read_state_file` 返回 `dict`(可用) / `None`(不存在=首启, 静默) / 哨兵 `_CORRUPT`(存在但非法 JSON、非 dict、非法 UTF-8; `OSError` 故意不吞 —— 那是环境问题不是内容问题) ②见 `_CORRUPT` 记 WARNING(损坏文件**原样保留不删**)并回退 `<state_file>.bak`, 读到合法 dict 即用以 INFO 记「用了备份」; 备份也不可用才 `{}` 并再告警说清后果 ③**自愈写回** `_write_back_recovered` —— 把恢复出的内容写回主文件且**刻意不带 `keep_backup`**, 否则下次 `save_state` 会把损坏内容复制成新的 `.bak`, 把唯一一份好备份盖掉(等于这次恢复白做) ④备份后缀单点化 `utils.BACKUP_SUFFIX`(写侧 `atomic_write` 与读侧共用, 防命名漂移)。**守阵 4 条**(回退+自愈 / 无备份时两条 WARNING / 首启不得告警 / 自愈写回失败只告警不抛)+ `test_utils` 备份路径断言改按常量; 红验: 运行期把 `_load_state` 打回旧实现 ⇒ 新守阵必红。全量 **1152 → 1160 passed + 1 skipped**。附带发现(报告里标「可选低优先」的孤儿 `state.json.*.tmp` 启动清理)
**也已一并修完**: 新增 `_cleanup_orphan_tmp`, 挂在 `QbManager.__init__` **持锁之后**(没锁说明有别的实例在写,
删它的临时文件会让那次写盘 `os.replace` 失败 ⇒ 状态白丢一次更新), 只认 `<state_file>.<随机>.tmp` 这一个形状
(`.bak` 是恢复凭据、别人的 `*.tmp` 与空随机段一概不碰), 只读模式 `no_lock=True` 不做这次磁盘副作用; 守阵 4 条
含一条**接线守阵**(源码里必须出现在 `acquire()` 之后且落在 `if not no_lock` 内)+ 幂等断言。
报告 [issues/26-09-21-1347-bug-state-load-corrupt-silent-reset.html](../../issues/26-09-21-1347-bug-state-load-corrupt-silent-reset.html)。
- 跳检备份时机修复 · issue 26-09-21-1347 (2026-09-22, 已置 `Fixed`): `.torrent` 备份原先只在**重加的两条失败分支**上落盘, 而删除是跳检链上第一个不可逆步骤 ⇒ 「删除已生效 → 重加未被 qB 接受」这个约 0.5~5.5s 的缝隙内崩溃/强杀, 种子从客户端消失、`data` 只在内存、state 无在途标记, 重启后无任何恢复凭据(需人工回站点重下 .torrent)。**修法 = 只挪调用时机**: 阶段 2 导出成功后立刻走现成的 `_backup_torrent`(落盘 + 元数据 + 立即 `save_state`), 并新增配对的 `_clear_backup` —— 重加确认成功后清理(文件 + 元数据)、删除未生效(种子仍在)也清理, 只有重加失败/崩溃才留下备份; 备份写不进去则**不删除**直接 fail(无损失)。**守阵 3 条**: ①在客户端的 `torrents_delete` 里快照备份文件是否存在(只查最终结果无法区分"之前写的"还是"之后补的") ②删除未生效 → 备份必须被清掉 ③备份失败 → 不得发出 delete。⚠ 顺带把 `test_checking.py::make_mgr` 改成**未指定 state_file 时自动发一份临时 state 文件** —— 跳检现在每次都真实落盘/删除备份, 留空会写到 CWD=仓库根(污染仓库 + 被 `tests/sidefx.py` 判成越界删除)。全量 **1142 → 1145 passed**; 知识库: `rule-system.md` / `config-reference.md` / `systemPatterns.md` / `docs/configuration.md` 已回写"备份先于删除"。报告 [issues/26-09-21-1347-bug-skip-checking-readd-no-backup-window.html](../../issues/26-09-21-1347-bug-skip-checking-readd-no-backup-window.html)。
- 导出 .torrent 中文名 500 已修 (2026-09-17, 已入库 `4de0953`): `/api/torrents/{hash}/export` 把种子名直拼进 `Content-Disposition`, 而 HTTP 头只能 latin-1 ⇒ 中文名触发 `UnicodeEncodeError` 500。修法: 新增 `web.content_disposition(filename, fallback, ext)` 双段头(`filename=` ASCII 回退 + `filename*=UTF-8''<百分号编码>`)并清洗控制字符; 测试 `test_content_disposition_encoding` + 导出端点非 ASCII 用例。
- TorrentRecord 全字段缓存 (2026-09-15): 快照 21 → 70 字段(必需 21 + 重加升格 6 + 可选扩展 43, 字段定稿参照用户提供的真机 TorrentDictionary 样例 + 真机冒烟补 4 字段), 为 WebUI 后续功能供数; D1-D5 决策见 [memory-bank/plans/26-09-15-1302-record-full-fields-plan.html](../../plans/26-09-15-1302-record-full-fields-plan.html): slots 全量声明(_raw 降为前向兼容兜底)/RE_ADD_FIELDS 升格进快照(变化开始计入变化集)/新字段全可选(默认值取 qB 哨兵 -1/-2/8640000, REQUIRED 校验面不变)/缓存≠展示(新字段不进 _VIEW_FIELDS, 视图重建成本零变化, 测试锁死)/哨兵原样透传; 新增 `to_dict()` 全字段导出; 真机只读冒烟(119 种子)响应字段全声明 _raw 无残留; 测试 +9 净 +7, 基线 879 passed; 视图/规则/HR/分组消费字段全在旧集合内零行为变化

- **🆕 state.json 损坏静默清空 + .bak 从不用于恢复 —— 已修并验证, 已入库 `e11df80`(见本文件顶部「最后更新」首条)**: issue
  [26-09-21-1347-bug-state-load-corrupt-silent-reset.html](../../issues/26-09-21-1347-bug-state-load-corrupt-silent-reset.html)
  已置 `Fixed`(索引已重建)。**附带发现(孤儿 `state.json.*.tmp` 启动清理)也已一并修完** —— 新增
  `_cleanup_orphan_tmp()`, 挂在 `QbManager.__init__` **持锁之后**(没锁说明有别的实例在写, 删它的临时文件
  会让那次 `os.replace` 失败 ⇒ 状态白丢一次更新), 只认 `<state_file>.<随机>.tmp` 这一个形状(`.bak` 是恢复
  凭据、别人的 `*.tmp` 与空随机段一概不碰), `no_lock=True` 的只读模式不调用; 守阵 4 条(含**接线守阵**:
  源码里必须出现在 `acquire()` 之后且落在 `if not no_lock` 内 + 幂等断言)。全量 **1160 passed + 1 skipped**。
  ✅ **本批改动(源码 3 文件 + 测试 1 文件 + 知识库 5 文件)已入库 `f261de7`**(Gitee + GitHub 均推上)。
  🧪 端到端复核(真实 `QbManager(..., no_lock=False)` 构造路径): 损坏 → 内存 state == `.bak` / 主文件被自愈
  写回 / 孤儿 tmp 被清理 / `.bak` 未被损坏内容盖掉 —— 四件事全成立(脚本在 `H:/Temp/e2e_state_recovery_check.py`,
  未进仓库)。
