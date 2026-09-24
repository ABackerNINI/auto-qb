# 26-09-22-backend-partial-hr-verify — 部分种子 HR 的在线核实

**Status:** Open
**Added:** 2026-09-22
**Updated:** 2026-09-24
**Summary:** 部分种子 HR 站点在线核实。**M1 核心管道 (2026-09-24) + M2 取数通道 (2026-09-24) 均已落地**:
M1 = 新包 `src/auto_qb/hr/` 离线管道 + 配置全链路 + `--hr-once`; M2 = 本地端点 (`/api/hr/tasks` +
`/api/hr/result`, token + origin + URL 白名单) + 取数线程 (`hr/worker.py`) + 只读视图发布 +
MV3 扩展 (`extensions/hr-fetch-proxy/`) + `channel`/`shared_dir` 转 **L1** 并接上热重载重挂。
6 个测试文件 + 91 条新用例, 全量 **1465 passed + 1 skipped**。
**余 M3 (把三态接进 TorrentRecord 与四个消费点) / M4 (多站点) 未落地** ——
计划见 memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html (§13 决策记录与 M0 实测清单)。
**Topics:** backend-partial-hr-verify
**Refs:** memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html

## 原始请求

> 当前部分站点实行部分种子HR策略, 即一个种子无法确定其是否为HR种子, 需要上对应的PT站点查询, 通常各站点都会有HR种子统计页, 可以将种子下载下来对比, 注意种子下载速度不能太快, 次数也需限制, 可配置, 访问站点尽量在后台进行, 且复用当前浏览器的cookie, 分析可行性并列一个计划

## 思考过程与决策

- **现状模型**: `trackers.<site>.hr` 是站点级静态配置, 配了即全站按 HR 管束; 判定收口在 `TorrentRecord.check_hr_condition` / `check_hr_satisfied`, 四个消费点 (打标 mixins/tags.py `_add_hr_tag_or_category` · WEB 视图 mixins/web_view.py `_hr_view_fields` · 规则条件 `hr` rules/conditions.py · 表达式 `tor.hr_*` rules/expr/env.py) 全部经它 —— 收口单一, 改造面最小, 这是方案的红利。
- **可行性总评**: 可行。抓取→下载→算 infohash→对账→建索引每步都落在既有架构 (全局任务 / state_file / httpx 已是依赖); cookie 是最大不确定项; 账号安全 (频度) 是最大运营风险, 恰是需求原始诉求。
- **cookie 技术墙 (已核实外部事实)**: ① Chrome/Edge v127 起 Windows 上 cookie App-Bound Encryption, DPAPI 直解失效 (SpecterOps 2025-08 / ElcomSoft 2026-01 / THN 2024-08), 绕过属窃密技术不做; ② Chrome 136 起 `--remote-debugging-port` 在默认 user-data-dir 被忽略 (chromedriver v136 报错可证), CDP 附着日常浏览器已死。⇒ 分层方案: A 手工导入 (M1) → B 专用 profile + CDP (M4); C 扩展备选不排期; D 直读否决 (Firefox cookies.sqlite 明文待 M0 验证, 可作 B 平替)。
- **infohash 关键细节**: 必须 sha1/sha256 over info dict 的原始字节切片, 不能 decode→re-encode (键序/整数表示漂移会算错 hash); bencode 倾向自写 ~60 行解析器 (记录偏移), 零新依赖, M0 拍板。
- **线程模型**: 主循环单写线程约束下, 站点请求 (1s~20s) 不能内联硬等 (2s tick 会卡) ⇒ 取数线程只做 HTTP+解析, 主循环按频控发许可令牌、收结果写 state —— 与 Web 线程 post_command/consume_commands 同款先例; fetcher 永不触碰 store/队列/state。
- **判定语义**: `hr_check.mode = all(现状)/partial(在线核实)/off`; partial 下索引未命中按 `unknown_policy` (默认 hr 保守, 首刷前整站按 HR = 等同现状, 无回退风险); 索引是反应式的 (页面列"已下载且受 HR 约束"的种子), 滞后段由 unknown_policy 兜底。
- **v1.1 增补 (2026-09-22 用户确认后)**: 页面行八字段 (HR 编号/名称/上传量/下载量/分享率/还需做种时间/完成时间/剩余达标时间) 全部入模; tid 站点内唯一、跨站不混用 ⇒ 索引改 (站点, tid) 主键, infohash 下载后回填, 反查键 (站点, infohash) 在内存重建; 同一内容辅种多站 HR 身份独立。防重复下载三层: hr_downloaded 永久层 (条目消失/翻页遗漏/超期都不重下) + 已有 infohash 只更新字段 + 失败重试上限冷却 (新键 `max_download_retries`); `index_retention` 只淘汰页面快照条目。进度字段定位「展示/交叉核对」, 判定仍以 qB 本地实时值为准 (重加清零场景两套值互补)。

## 实现计划

单点在 [计划文档](../plans/26-09-22-2204-partial-hr-site-verify-plan.html) (§11 分阶段): M0 调研拍板 → M1 核心管道 (dry-run, bencode/infohash + adapter + 对账建索引) → M2 频控与后台化 (取数线程+令牌 / 配额 / 熔断 / notify) → M3 判定联动 (TorrentRecord 收口 + 四消费点回归 + unknown_policy) → M4 cookie 自动化 (专用 profile + CDP; Firefox 路线视 M0 验证)。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 计划审核与 v1.2→v1.7 修订 | Done | 2026-09-24: v1.2 = 按审核 + 用户否决手工 cookie 重写 §6/§8; v1.3 = 扩展形态澄清 + 「未核实」边界收口 (三态); v1.4 = 站点侧权威 + 放行有效期; v1.5 = 站点分文件+带锁访问+有效期复用、线程三分职责、mode: all 纳入、hr_channel 并入 hr_check; v1.6 = 锁粒度改为**每站点一把锁** + 取数节奏与 tick 解耦; v1.7 = 5 项决策拍板后定稿 (§13 改决策记录 + M0 实测清单)、**channel 推荐都启用** (扩展侧加实例端点列表)、**shared_dir 多实例部署引导** |
| 独立实验程序 `scripts/hr_fetch_experiment.py` | Done | bencode/infohash (原始字节切片) + selftest 11 项 + myhr 解析样张 + 限速下载 + CDP 自动取 cookie (机器链路全通, 仅剩人工登录一步) |
| 文档漂移收尾 | Done | 2026-09-24 20:15 (计划 v1.8, 纯文档无设计变更): 删 §6 遗留 cookie 分层表 (与「扩展主选」矛盾) / 修 §1 旧路径 · §3 旧落点 · §4 旧判定口径 · §5 bencode 待办 · §11 M0 依赖与抖动口径 / 删 §9 consumer 残留行 + 补 mode 三态语义与 `mode != off ⇒ hr 段必填` / 目录与 CSS 注释更名 |
| 前置决策拍板 | Done | 2026-09-24 用户拍板 5 项: 接受装扩展 / 首站 **BTSchool** (页面数据实施时提供) / 频度按推荐 / `unknown_policy=hr` + `verified_ttl=refresh_interval` / `shared_dir` 默认数据目录; 另定 **channel 推荐都启用**。计划 §13 由「开放问题」改为「决策记录 + M0 实测清单」 |
| M0 实测收口 (download URL 形态 / BTSchool scope 与分页判据 / 后台标签页观感 / 共享目录 filelock 互斥) | Pending | 4 项实测 (**不阻塞 M1**, 可与 M1/M2 并行); 部分已由本轮测试**钉死结构**(灰色「下一页」判到底 / 免罪链接 / 九列表头), 仍需真机确认 `?page=N` 参数名与 passkey |
| M1 核心管道 (离线可做) | **Done** | 2026-09-24: `src/auto_qb/hr/` 10 个模块 (bencode/parse/adapters/model/store/ratelimit/resolve/service/fetcher/report) + 配置全链路 (校验/schema/impact/loader/Hub 文案) + `--hr-once` 只读走查; 8 个测试文件 + 共享夹具与脱敏 fixture, 全量 **1374 passed + 1 skipped** |
| M2 取数通道 (扩展 + 本地端点 + 取数线程) | **Done** | 2026-09-24: `hr/channel.py`(协议 + 密钥 + origin/URL 白名单) · `hr/queue.py`(派发式队列) · `hr/server.py`(stdlib 端点, 仅听回环) · `ChannelFetcher` · `hr/worker.py`(取数线程 + 视图原子发布 + 告警节流) · `hr/runtime.py`(`QbManager.hr` 门面) · 扩展 `extensions/hr-fetch-proxy/`; `channel`/`shared_dir` 已改 **L1** 并在 L1 分支接上 `HrRuntime.apply`。**本轮挖出并修掉一个真缺陷**: 线程正等扩展回传时关停会白等到 `request_timeout` 且持着站点锁 ⇒ 改为先叫停队列再 join |
| M3 判定联动 + 真机 `hr.once` 走查 | Pending | 1 会话; **原料已齐**: `resolve_identity` 三态(含新鲜度闸门 / 锚点漂移 / 放行有效期)已测; **M2 已把只读视图门面备好** —— 主循环用 `manager.hr.view_snapshot()` 取 `(revision, views)`(零等待、单次属性读取), 版本没变就不做任何 record 更新, 需要新数据时 `manager.hr.wake()`(非阻塞)。**要做的**: 接进 `TorrentRecord` 两个方法 + 四个消费点(打标 / WEB 视图 / `hr` 条件 / `tor.exp_*` 表达式), 并把 `mode: all` 升为「站点侧驱动 + 未核实恒受管束」。另需在主循环提供 `manager._hr_anchors`(取数线程已在调它, 现在恒空) |
| M4 多站点与打磨 | Pending | 1 会话; 还需补 M2 到 M4 之间漏掉的 notify 四类事件(登录失效 / 熔断 / 改版 / 通道静默)—— 现在这四类只落日志(WARNING 会被 notify 处理器推成系统通知, 但没做"四类事件"语文化) |

## 进度日志

- **2026-09-25 03:10** — 用户接着报「现在是打开新窗口而不是后台抓取」(上一版刚改的隐藏窗口):
  ① **根因**: `state:'minimized'` 不是灵药 —— 在用户平台上新建窗口仍会先显示一下, 用户看到的就是「弹出一个新窗口」。
  ② **口径定型为分层**: **零界面优先** —— 页面用扩展后台的 `fetch(credentials:'include')` 直取
  (站点侧页面本来就是服务端渲染的表格), 不开标签也不开窗口; 只有两个**通用结构信号**才升级到渲染通道:
  【拿到内容没 `<table>`】或【页面里有密码输入框(=看到登录页)】; 渲染兜底改为 **离屏 popup 窗口**
  (`left/top=-32000` + `type:'popup'` + `focused:false`, 三段式降级尝试), 用完连窗口一起删, 并保留焦点守卫。
  ③ **顺手补的 SameSite 安全网(重要)**: 无 `SameSite` 属性的 cookie 按 Lax 对待, 而扩展发起的 fetch 算
  **跨站请求** ⇒ 可能不带 cookie 而拿到**登录页**; 登录页确实有 `<table>`, 若只看表格判据就会被当成正常页面
  ⇒ 后端读成「表头缺失/疑似改版」, **把排查引到错误方向**。所以升级判据必须包含「有密码输入框」。
  ④ 守阵: 扩展侧改为「一次 node 跑四个场景」(直取零界面 / 内容不像页面 ⇒ 离屏 popup / 登录页也得升级 /
  焦点被抢后还回去), 共 **12 条**; ★红验: 强制走渲染通道 ⇒ `test_page_fetch_is_headless_when_html_looks_fine` 变红。
  ⑤ 全量 **1503 passed + 1 skipped**(TOTAL 91% / 10425 / 778 / 3446 / 308), sidefx 越界 0;
  manifest 描述 / 扩展 README / 坑文件 / 计划 v2.2 均已同步。
  下一步仍是 **M3 判定联动**; 仍待定: `config.yml` 明文凭据入库。

- **2026-09-25 02:10** — 用户实报「抓数据时会打开新的标签而不是后台抓取」, 修:
  ① **根因**: `chrome.tabs.create({active:false})` **只**保证「不是那个窗口的活动标签」, **不保证窗口不被
  抬到前台** —— 扩展被 alarm 唤醒时用户往往正在别的程序里, Chrome 会把窗口连同新标签一起显示出来。
  ② **修法**: 页面取数一律在**扩展自己的窗口**里做 —— `windows.create({focused:false, state:'minimized'})`
  + `tabs.create({windowId, active:false})`, 用完删标签、窗口空闲 2 分钟自动关(不长期挂一个窗口);
  再加一道**焦点守卫**(取数前记下原聚焦窗口, 取完还回去); 若最小化让页面延迟脚本变慢则取消最小化
  (**仍不聚焦**)并重试一次。manifest 描述 / 扩展 README / 切片与计划 v2.1 变更行同步口径。
  ③ **守阵**: `tests/test_extension_proxy.py` 新增 2 条 —— **用假 chrome API 真跑 background.js**,
  记下每一次窗口/标签调用并断言(自建最小化窗口 / 每个标签必带 `windowId` 且 `active:false` / 取完删标签 /
  空闲删窗口 / 焦点被抢后还回去); ★红验: 去掉 `tabs.create` 的 `windowId` ⇒ 当场变红。
  ④ 全量 **1501 passed + 1 skipped / 22.90–23.18s**(TOTAL 91% / 10425 语句 / 778 未覆盖 / 3446 分支 / 308 partial),
  sidefx ≈2430 / 越界 0; 新坑补进 [pitfalls/web-ui/extension-bridge.md](../pitfalls/web-ui/extension-bridge.md)
  (「后台标签」≠「不影响用户」); 基线已回写。
  下一步仍是 **M3 判定联动**; 仍待定: `config.yml` 明文凭据入库。

- **2026-09-25 01:10** — 用户点名修两件: ①`service._do_fetch` 的**取数失败分支漏了 `persist` 判断**
  (成功分支有、失败分支没) ⇒ `--hr-once` 声称「不写文件」但一撞上取数失败就把熔断/失败计数写进站点文件,
  而那份文件是**正式实例共用**的 ⇒ 只读口令偷改了取数节奏。修法: 失败分支同样按 `persist` 走,
  `persisted` 口径与成功分支统一(`status == "written"`), 并在调用点写明「失败计数/熔断同属持久状态」;
  守阵双向钉住(只读失败不落盘 / 正式失败必须落盘), ★红验: 临时恢复旧实现即当场变红。
  坑入库 [pitfalls/backend/high-risk-ops.md](../pitfalls/backend/high-risk-ops.md)
  「只读口径是开关, 新加的写盘分支必须逐条带上它」。
  ②README 两处**坏字符**(存成了 U+FFFD): `HR 在线核实` 标题补回 🔍, `辅种管理` 去掉坏字节保留 👯;
  全仓扫过 U+FFFD, 其余均为乱码示例的刻意引用(`pitfalls/ops/console-encoding.md` 等), 不动。
  ③ 全量 **1499 passed + 1 skipped / 17.90–22.91s**(TOTAL 91% / 10425 语句 / 778 未覆盖 / 3446 分支 / 308 partial),
  sidefx ≈2430 / 越界 0; 基线已回写。
  下一步仍是 **M3 判定联动**; 仍待定: `config.yml` 明文凭据入库。

- **2026-09-25 00:30** — 用户补充上一次提交版本的完整日志(含重启段) ⇒ 又从日志里读出**四件事**, 逐条定位:
  ① `WARNING HR 取数通道端点已启动` / `WARNING HR 在线核实已启动` —— **生命周期消息用错级别**: 本仓 WARNING 以上
  会被 notify 推成系统通知, 用户重启一次连吃三条 ⇒ 启动 / 关闭 / 热重载重挂全改 INFO。
  ② 一次扩展取数超时被 **两处各告警一次**(service 的 `取数失败(1 次): …` 与 worker 的 `error: …`) ⇒ 一次收两条通知;
  改成「谁产生原因谁告警」: 结果对象新增 `alerted`, 产生处(取数失败 / 刷新异常 / 存储层读坏)报 WARNING 后
  状态层只记 INFO。
  ③ `WARNING HR 站点 BTSchool | 站点文件解析失败: Expecting value: line 1 column 1 (char 0)` = **站点文件是空的**。
  给站点文件补两层保护: 写盘默认把上一版留为 `.bak`; 读到坏文件**先把现场挪到 `.bad-<ts>`**(否则下一次写盘
  就把它覆盖掉、线索永远消失)再试 `.bak` 兜底, 取证串带上大小与开头字节(「空文件」与「内容坏」一眼可分),
  同一文本只告警一次(持续状态不逐轮重报)。
  ④ 过程中挖出**两个真缺陷**(都是守阵自己抓到的): (a)**恢复出来的备份必然比本进程上次写的旧** ⇒ 锁自检的
  「revision 回退」把这次自愈判成「锁不生效」而退化为只读, 该站点从此写不回去 —— **自愈反而变砖**; 修法是
  恢复后重置写者心跳基线, 并且恢复后的第一次写盘**不得**再复制 `.bak`(否则好备份被坏内容盖掉, 与 `state.json`
  自愈同一个坑)。(b)关停 / 热重挂时被叫停的取数长着 `HrChannelUnavailable` 的皮 ⇒ **每次关停都告警一条
  「无可用取数通道」且误计失败次数**; 分出子类 `HrChannelStopped`, service 按「非事件」处理(不告警、不计失败、
  不推熔断, 本轮转 WAITING)。
  ⑤ 测试 **+10**(store 5 / runtime 2 / service 2 / worker 1)并把 fetcher 的叫停用例改为钉住子类;
  ★红验: 去掉 `alerted` / 启动消息打回 WARNING / 叫停降回父类 ⇒ 四条守阵当场变红。
  ⑥ 全量 **1498 passed + 1 skipped / 18.08–22.89s**(TOTAL 91% / 10423 语句 / 778 未覆盖 / 3444 分支 / 308 partial),
  sidefx ≈2430 / 越界 0; 文档(配置说明 / 扩展 README / 根 README)与新坑
  [pitfalls/ops/alert-levels.md](../pitfalls/ops/alert-levels.md)(扩写为四条判据 + 两个同族旧账)已回写, 基线已更新。
  ⑦ **顺带发现但未动(待你定)**: `service._do_fetch` 的取数失败分支 `session.commit()` **没看 `self.persist`**
  ⇒ `--hr-once` 声称「不写文件」但取数失败时会写熔断计数, 与文档承诺不符。
  下一步仍是 **M3 判定联动**; 另两个待定: `config.yml` 明文凭据入池 / README 里一个坏 emoji。

- **2026-09-24 23:45** — 用户实报 M2 上线后的两个体验问题: ①「会弹 warning」(通知轰炸) ②「无法知晓拉取的数据是否正确」。
  ① **定性(先判是不是 bug)**: 逐行读用户贴的日志 —— `partial: 配额/间隔受限(间隔: 还差 104s)` 与
  `waiting: 未到可取时刻(间隔, 还差 51s)` **交替出现**, 一句故障都没有; 那正是后端按自己的频控节奏取数的常态
  (一轮完整刷新 = 3 档位各翻到底 + 回填 .torrent, 而请求间隔 >= `min_torrent_interval` 90s ⇒ 默认要几分钟)。
  真正的缺陷是**告警分级**: 取数线程 `_note` 把所有 `ACTION_PARTIAL` 一律 WARNING, 而 WARNING 会被 notify 推成
  系统通知 ⇒ 每 60~90s 一次弹窗。更隐蔽的一半: 同一根因在轮次间动作不同(`partial` 首页抓到/第二页被拦 vs
  `waiting` 没到时刻), 用 action 当「状态变化」判据等于逐轮都算变化, **去重形同虚设**。
  ② **修法(分类在产生处做一次, 日志/报告/后续通知复用)**:
  `HrRefreshResult` 新增 `reason_kind`(`REASON_NONE/BUDGET/PARSE`), `_do_fetch` 分别打 `budget_limited`
  (频控 `take()` 被拒)与 `parse_problem`(表头缺失 / 翻页上限 / 必填字段缺失率超阈)两个标记, 判据口径:
  **沾了页面问题就算 parse, 纯被频控拦下才是 budget, 不明原因保守当 parse**(宁可多看一眼)。
  `worker._note` 三档: 正常动作变化时 INFO; **节流中**(WAITING 或 budget 类 partial)按「**被拦根因类别**」
  (间隔/配额/时间窗/熔断/只读)去重 —— 一整个等间隔时期只说明白一次, 消息里明写「非故障」, 被去重的轮次降 DEBUG;
  页面/解析类与失败才 WARNING, 持续时按 `channel_silence_warn` 周期提醒; 完整刷新后清掉节流记忆。
  ③ **可见性**: 新增 `--hr-status [--hr-status-rows N]`(`report.run_hr_status`)—— **不取数、不加锁、不写盘、不连 qB**,
  把已落盘数据摊开: 站点文件目录 / 通道自检 / 模式·覆盖证明·最近完整刷新·有效期 / 档位分布(A/B/C/D)与受管束种子数 /
  已取与失败与**待回填 infohash** / 配额与熔断与时间窗 / 最近一次刷新不完备的**原样原因** / 明细表
  (tid · 档位 · 下载量 · 剩余达标 · 名称 · infohash 前 12 位) —— 拿站点页面即可逐行对账。CLI 侧与托盘/导出/走查互斥。
  ④ **守阵(16 条)**: service 3 类 `reason_kind` 分类 / worker ④ 频控截断**零 WARNING** 且同根因只记一条(降 DEBUG)、
  持续态按窗提醒一次、完整刷新清记忆、`stable_key` 抹数字 / report 4 条(含「站点文件一字未改」与坏文件仍出报告)/
  cli 2 条(互斥 + 不构造 manager 且行数透传)。★红验: 临时去掉 `REASON_BUDGET` 分支 ⇒ 三条 worker 用例立刻变红。
  ⑤ 文档: `docs/configuration.md` 增 `--hr-status` 用法与「`partial: 配额/间隔受限` 不是故障、默认一轮要几分钟」;
  扩展 README 排障表增同义一行; 新坑 [pitfalls/ops/alert-levels.md](../pitfalls/ops/alert-levels.md)(判据=「故障
  还是我们本来就要等」; 去重键要选根因不要选本轮返回值; 持续态不静默消失)。
  ⑥ 全量 **1488 passed + 1 skipped / 16.88–21.40s**(TOTAL 91% / 10349 语句 / 768 未覆盖 / 3428 分支 / 308 partial),
  sidefx 台账 2390 / 越界 0; 基线已回写。
  下一步仍是 **M3 判定联动**; 用户待定: 是否把「`config.yml` 被 git 跟踪且含明文 qB 凭据」入池。

- **2026-09-24 23:10** — 用户装上 M2 交付的扩展后实报两条报错 ⇒ 逐条定位并修掉(含可跑守阵)。
  ① `Invalid value for origin pattern pt.btschool.club: Missing scheme separator.` —— 选项页把**原始输入**
  直喂 `chrome.permissions.request`(它只吃带 scheme 的匹配模式), 而且那是**未捕获的 Promise 拒绝**。
  ② `TypeError: Failed to fetch` —— 用户生产 `config.yml` **没有 `hr_check` 段**(只读确认, 未改), 端点从未启动
  (让它启动需三个开关同时满足: `hr_check.enabled` + 站点 `mode != off` + `channel.enabled`); 而浏览器对
  网络层失败只给这一句 ⇒ 用户无从下手, 这就是本次真正的用户体验缺陷。
  修法: 输入**先归一化再交给浏览器 API**(裸域名→`https://host/*`; 端点补 scheme / `localhost` 折 `127.0.0.1` /
  协议固定 http), 非法输入**逐条**报错、不拖垮整批; 归一化抽成 `normalize.js` **一份**(选项页 `<script>` +
  后台 `importScripts` 共用 —— 两份分头演化必然漂移, 漂移的症状是“配了不生效”); 选项页新增
  **自测端点连通**(把“连不上 / 401 / 403”分开)+ `unhandledrejection` 兜底(不再有英文红字裸奔);
  README 补「端点何时才会启动」三个开关与排障表; manifest `host_permissions` 补 localhost /[::1] 别名。
  新增 `tests/test_extension_proxy.py` 8 条(manifest 作用域 / **真跑** normalize.js / 归一化只有一份 /
  与后端协议常量对照 / 调用顺序 / 不得留裸拒绝), ★红验过(去掉补 scheme 那行即变红);
  过程中真被 `node --check` 漏挡一次(删了本地副本、引用还在的 `ReferenceError`, 语法是合法的) ⇒ 守阵坚持“执行”而非“查语法”。
  坑入库: 新增 [pitfalls/web-ui/extension-bridge.md](../pitfalls/web-ui/extension-bridge.md);
  [pitfalls/ops/console-encoding.md](../pitfalls/ops/console-encoding.md) 补“反向子进程解码(node 输出 UTF-8 而 `text=True` 按 locale 解 ⇒ 直接抛)”。
  全量 **1475 passed + 1 skipped**; 基线已回写。下一步仍为 **M3 判定联动**(门面已备好)与 M0 真机实测。

- **2026-09-24 22:30** — 用户令「提交包括 settings.json, 然后继续 M2」⇒ ① 按 ship 流水线提交 M1(含 `.vscode/settings.json` 的三个拼写词), Gitee `develop` 已一致(GitHub 镜像一次失败, 按约定不重试); ② 本轮落地 **M2 取数通道**。
  ① **范围**: 计划 §11 的 M2 = 后端端点 + 取数线程 + 共享站点数据 + MV3 扩展 + 多实例引导 + `channel`/`shared_dir` 转 L1。
  ② **新增 6 个模块**: `channel.py`(协议 `HrTask`/`HrResult` 与密钥/白名单纯函数) · `queue.py`(派发式队列: 端点线程与取数线程的**唯一**交接面) · `server.py`(stdlib `ThreadingHTTPServer`, 仅听 `127.0.0.1`) · `fetcher.py::ChannelFetcher`(请求 → 任务 → 阻塞等回传) · `worker.py`(取数线程 + 视图原子发布 + 告警节流) · `runtime.py`(`QbManager.hr` 门面: 启停 / 热重载重挂 / 自检快照)。
  ③ **三道边界**: token(常数时间比对; 无 token/不符 ⇒ 401 **且不写任何状态**) / origin(扩展 origin 放行, 普通网页 403) / URL 白名单(SSRF: 任务 URL 只能由配置拼出)。**另加一道更硬的**: 回传必须绑定「确实派发过且未作废」的任务, 且域名须与任务一致 ⇒ 伪造注入进不来。
  ④ **关停缺陷(本轮最有价值的发现)**: 取数线程在锁内等扩展回传最长 `request_timeout`(默认 180s) ⇒ 不叫停的话, 正常关停要白等到超时, **该站点期间锁死**、进程退出被拖住, 而 2s 主循环节拍不受影响(线程边界是对的)。修法: `HrWorker.stop()` 内建「先 `queue.cancel_all` 叫醒等待方, 再 join」; `ChannelFetcher` 把「被叫停」与「等超时」分开上报(前者是 `HrChannelUnavailable`, **不计失败/熔断**); `HrRuntime._build` 用 `queue.resume()` 清掉残留标记。这也是本轮 7 条用例各慢 10.5s 的根因(测试的 `stop(timeout=10)` 白等)。
  ⑤ **热重载**: `channel`/`shared_dir` 改 **L1**(`impact.py`), L1 分支接 `HrRuntime.apply` —— 监听身份(启用/端口/扩展 id/token/共享目录)变了才重挂端点, 只改 L0 字段(如 `poll_interval`)不白重绑端口; 无通道实例仍跑取数线程但 `allow_fetch=False`(只读共享数据 = 能力即角色)。
  ⑥ **两个增补配置键**(计划 §7 草案没有, 实现时判定必要, 已写进计划 v2.0 变更行): `channel.extension_id`(§6 要求「优先固定扩展 id」, 没有这个键无从固定)与 `channel.request_timeout`(必须有, 见 ④)。两者都进了 `KNOWN_HR_CHANNEL_KEYS` + 校验(32 位 a~p / 5s–1h)+ schema Field + loader。
  ⑦ **扩展** `extensions/hr-fetch-proxy/`: MV3 哑取数器 —— `chrome.alarms` 逐个实例拉清单 / 页面用**后台标签页**取渲染后 DOM(不抢焦点、能过挑战页)/ `.torrent` 由 service worker 带 `credentials: include` 取 / 实例端点列表(一个浏览器服务同机多实例)/ 选项页申请**按站点**授权(不给 `<all_urls>`); 明确不读 `chrome.cookies`、不解析、不限速(策略唯一权威在后端)。`node --check` 两个 JS 与 manifest 解析均过。
  ⑧ **告警节流**(防通知淹没): WARNING 会被 notify 推成系统通知, 而取数线程是分钟级轮询 ⇒ 「无可用取数通道」每站只报一次(通道恢复后重置), 持续静默由通道接触时间按 `channel_silence_warn` 周期提醒, 「刷新不完备(疑似改版)」在状态变化时告警。
  ⑨ **测试**: 新增 6 个文件 91 条(协议/密钥/白名单、队列含叫停与恢复、端点纯逻辑路由 + **真回环 HTTP 往返** + 401/403/400/413/404 + 端口冲突 fail-fast、ChannelFetcher 超时与叫停、取数线程与视图发布、运行时门面与热重载重挂)。首跑 4 条真红: 队列接受「未派发任务」的回传 / `path_of("…/")` 返回空串 / `ChannelStatus.silent_for` 在伪时钟测试下失真 / publish 空视图被当作变化。另修既有守阵: `tests/helpers.FakeConfig` 补 `hr_check`(否则所有跑主循环的用例 AttributeError)、`test_web.py` 的旧配置桩补 `hr_check`。
  ⑩ 全量 **1465 passed + 1 skipped / 17.20s**(TOTAL 91% / 10217 语句 / 763 未覆盖 / 3382 分支 / 304 partial; 新模块 90–98%), sidefx 台账 2353 / 越界 0; 基线已回写 `testing/baseline.md` + `baseline-history.md`。
  下一步(计划 §11): **M3 判定联动** —— 把三态接进 `TorrentRecord` 与四个消费点, 并让主循环用 `manager.hr.view_snapshot()` 消费视图(门面已备好)。

- **2026-09-24 21:40** — 用户令「实施该计划」, 并指定输入: 页面样本 `D:/Projects/站点页面/BTSchool` 与前期实验脚本 `scripts/hr_fetch_experiment.py`(未经真机验证)。
  ① **范围判定**: 计划是 5 段里程碑(1–2 + 1–2 + 1 + 1 会话), 本轮按计划自身的顺序取 **M1(纯离线可做, 计划明写「输入 = 实验脚本」)**; 余下 M2/M3/M4 已在档案逐项标状态。
  ② **交付 `src/auto_qb/hr/` 10 个模块**: `bencode`(infohash 只取 info 的**原始字节切片**; 定位跨度时只做字节跳跃不解码 info —— 大种子下少一次全量解码) · `parse`(栈式 `<tr>/<td>` 树, 容忍 NexusPHP 的 `<td class="embedded">` 包裹表; 数值容错认不出就返回 None 不猜) · `adapters/{base,nexusphp,__init__}`(站点隔离; NexusPHP `myhr.php` 九列形态即首站 BTSchool) · `model`(站点文件内容: `hr_index` / `hr_downloaded` / `hr_dl_fails` / `hr_verified` / `hr_refresh` / 配额 / 熔断) · `store`(**每站点一个 JSON + 一把 filelock**; 持锁期间完成「读→判有效期→必要时抓→写→释放」全程; revision 回退或本实例心跳被覆盖 ⇒ 判锁不生效并**退化为只读**) · `ratelimit`(间隔 **只向上抖动** +0~25% · 小时/天两级配额按**窗口键**幂等 · 失败退避熔断 · `allow_window` 可跨午夜) · `resolve`(**三态** + 新鲜度闸门 + 锚点漂移 + 放行有效期; 不可变视图, 读取时现算时间敏感判定) · `service`(刷新管道; `persist` / `allow_fetch` 组合出三种口径: 正常 / `--dry-run`(零请求零写入) / `hr.once`(抓但只读)) · `fetcher`(取数通道协议 + `NullFetcher` —— 无通道时**如实上报**, 绝不静默降级为后端直连) · `report` + `cli --hr-once [--hr-html-dir]`。
  ③ **配置全链路**: `KNOWN_CONFIG_KEYS` + `KNOWN_HR_CHECK_KEYS` / `KNOWN_HR_CHANNEL_KEYS` / `KNOWN_SITE_HR_CHECK_KEYS` + 校验器 + `config/schema/hr.py`(新分组「HR 在线核实」+ 站点段 `hr_check`) + `HR_CHECK_FIELD_LEVELS`(热重载分级; 全 L0, 并在注释里写明「落地取数通道时 channel/shared_dir 必须改 L1」) + loaders + 设置页 Hub 文案 / 未启用判定 / 首页读数。
  ④ **两条 fail-fast 是这一轮最值钱的防线**: (a) 站点 `mode != off` 却没配 `hr` 段 ⇒ **配置期直接报错** —— 否则 `check_hr_condition` 第一行 `if not self.tracker_conf.hr` 恒 False, 整站保护**静默失效且无任何报错**; (b) `hr_page_scopes` **必须含 A+B+C** —— 少抓一档会让该档种子在「完整刷新」里未列出而被**误放行**(漏 HR)。
  ⑤ **测试**: 新增 8 个文件 + 共享夹具 `tests/hr_helpers.py`(假取数通道 / 可推进假时钟 / 页面构造器)与**脱敏页面 fixture**(`tests/fixtures/hr/nexusphp_myhr_{page1,last}.html`, 取自真实样张结构: 包裹表 / 灰色不可点的「下一页」/ 免罪链接)。覆盖: infohash 钉死向量 + 「原始切片 ≠ 重编码」+ 畸形与深嵌套拒收 / 表头缺失=改版 vs 表头在但 0 行=合法空 / 防重取三层 / 有效期复用**零请求** / 翻页未到底 ⇒ 覆盖证明不成立且不推进 `last_success_ts` / **判定表逐行** / **新鲜度闸门不可被 `unknown_policy` 绕过** / 熔断与冷却 / 锁粒度=站点(同站互斥、异站不阻塞) / 走查模式不写盘。
  ⑥ **首跑 11 条真红**, 逐条定位后全绿; 其中 3 条是**实现真 bug**(进度锚点漂移被 `completion_on` 抢先命中 → 测试参数补全; D 档放行记录被后续 `not-listed` 覆盖 → 加 `exempt` 白名单; `next_allowed_at` 门槛已满足时仍报原因 → 改回报空)。另修一条自己挖的坑: `page_bounds` 的松正则把完成时间 `2026-09-21` 当成页脚区间 ⇒ 改为**锚定 `<b>`**。
  ⑦ 全量 **1374 passed + 1 skipped / 8.83s**, TOTAL 91%(9278 语句 / 727 未覆盖 / 3128 分支 / 277 partial), sidefx 台账 2212 / 越界 0 → 基线已回写 `testing/baseline.md` + `baseline-history.md`(该文件本轮**触顶 24,000 字符 cap** ⇒ 按守卫给的处置从最老一端切到 ≤16,000, 外迁 `testing/attachments/baseline-history-archive.md` 并原位留指针)。
  ⑧ 踩坑记录: 改计划 HTML 时**又**吞了收尾标签(`old` 带了 `</tbody></table><p>`, `new` 只写到 `</tbody>`) ⇒ 已给 `pitfalls/docs/html-edit.md` 的对应条目记 **复发 +1** 与未命中原因; 另新增一条 `pitfalls/backend/page-scraping.md`(页面捉取里的松正则把完成时间当页脚区间, 必须锤定结构)。
  下一步(计划 §11): **M2 取数通道**(MV3 薄代理 + 本地端点 + 取数线程 + 共享站点数据), 之后 M3 才把三态接进 `TorrentRecord` 与四个消费点。


- （本段更早的进度纪要已外迁: [attachments/26-09-22-backend-partial-hr-verify-log.md](attachments/26-09-22-backend-partial-hr-verify-log.md) —— 触顶处置见 `.agents/skills/memory-bank/scripts/_common.py` 的 `TASK_LOG_CAP`）
