# 测试基线 · 变更流水

> 摘要: 测试基线的**逐次增量流水**(最近在上), 每次增删用例都记一条 —— 用来回答"这个数字是怎么来的"。
> 触发: 基线为什么是这个数, 某条用例何时加的, 覆盖率变化, 历史增量

> 迁移说明(2026-09-22 W3): 本节原在 `testing.md` 顶部的 ```bash 围栏里当注释, 现原样外迁 ——
> **只把 bash 注释标记转成 markdown 列表缩进**(内容逐字未改)。**当前数字**见 [baseline.md](baseline.md)。

> **更早的流水已外迁** → [attachments/baseline-history-archive.md](attachments/baseline-history-archive.md)
> (append-only 流水触顶时的处置: 从最老一端切到本文件 ≤ 16,000 字符, 原位留本行指针;
> 最近一次轮转: 2026-09-25 触顶 24,000, 外迁最老 17 条, 本文件保留 10 条)

- ↑ 收集数 **1502 → 1504**(**+2**; 2026-09-25 **页面取数改「零界面优先」**):
  上一版换来的隐藏窗口又被用户看成「打开新窗口」(`state:'minimized'` 在部分平台仍会先显示一下)。
  本版定型为**分层**: ①页面默认用扩展后台的 `fetch(credentials:'include')` **直取**(零标签零窗口);
  ②只有【内容没 `<table>`】或【出现密码输入框】才升级到渲染通道; ③兜底用**离屏 popup 窗口**
  (`left/top=-32000` + `type:'popup'` + `focused:false`)+ 焦点守卫, 用完删窗口。
  ❗第二个升级信号同时是 **SameSite 安全网**: 无 `SameSite` 属性的 cookie 按 Lax 对待, 而扩展发起的
  fetch 算跨站请求 ⇒ 可能不带 cookie 而拿到登录页; 登录页确实有 `<table>`, 只看表格判据会把它当正常页面,
  后端进而读成「表头缺失/疑似改版」, 把排查引到错方向。
  守阵改为「一次 node 真跑四个场景」(共 12 条), ★红验: 强制走渲染通道即变红。
  全量 **1503 passed + 1 skipped** / TOTAL 91%(10425 / 778 / 3446 / 308) / sidefx ≈2430 / 越界 0。
- ↑ 收集数 **1500 → 1502**(**+2**; 2026-09-25 **扩展页面取数改用自己的隐藏窗口**):
  用户实报「抓数据时会打开新的标签而不是后台抓取」。根因: `chrome.tabs.create({active:false})` **只**
  保证「不是那个窗口的活动标签」, **不保证窗口不被抬到前台** —— 扩展被 alarm 唤醒时用户往往正在别的
  程序里, Chrome 会把窗口连同新标签一起显示出来。修法: 取数一律在**自己的窗口**里做
  (`windows.create({focused:false, state:'minimized'})` + `tabs.create({windowId, active:false})`),
  用完删标签、窗口空闲 2 分钟自动关; 再加一道**焦点守卫**(记下原聚焦窗口, 取完还回去); 若最小化窗口
  让页面的延迟脚本变慢就取消最小化(仍不聚焦)并重试。
  新增 2 条守阵: **用假 chrome API 真跑 `background.js`** 并记下每一次窗口/标签调用
  (自建最小化窗口 / 标签必带 windowId 且 inactive / 取完删标签 / 空闲删窗口 / 焦点被抢后还回去),
  ★红验: 去掉 `windowId` 即当场变红。全量 **1501 passed + 1 skipped** /
  TOTAL 91%(10425 / 778 / 3446 / 308) / sidefx ≈2430 / 越界 0; 并行耗时 22.9–23.2s(两条新守阵各真跑一次 node)。
- ↑ 收集数 **1499 → 1500**(**+1**; 2026-09-25 **只读口径漏分支 + README 坏字符**):
  用户点名修两件事: ①`service._do_fetch` 的取数失败分支**漏了 `persist` 判断**(成功分支写了、失败分支没写) ⇒
  `--hr-once` 声称「不写文件」但一撞上取数失败就把**熔断/失败计数写进站点文件**, 而那份文件是正式实例共用的 ⇒
  只读口令偷改了别人的取数节奏。修法: 失败分支同样按 `persist` 走, `persisted` 口径与成功分支统一
  (`status == "written"`), 并在调用点写明「失败计数/熔断同属持久状态」; 守阵双向钉住(只读失败不落盘 /
  正式失败必须落盘), ★红验: 临时恢复旧实现即变红。坑入库 `pitfalls/backend/high-risk-ops.md`
  「只读口径是开关, 新加的写盘分支必须逐条带上它」。
  ②README 两处坏字符(已被存成 U+FFFD): `### �️ HR 在线核实` ⇒ 补回 🔍(核实语义),
  `### �👯 辅种管理` ⇒ 去掉坏字节保留 👯。全仓扫过 U+FFFD: 其余均为**乱码示例的刻意引用**
  (`pitfalls/ops/console-encoding.md` / `baseline-history.md` / 引擎脚本注释), 不动。
  全量 **1499 passed + 1 skipped** / TOTAL 91%(10425 / 778 / 3446 / 308) / sidefx ≈2430 / 越界 0。
- ↑ 收集数 **1489 → 1499**(**+10**; 2026-09-24 **告警级别 / 重复告警 / 站点文件自愈**):
  用户补充贴出上一次提交版本的完整日志, 又掲了四件事(都不是取数故障):
  ①`WARNING HR 取数通道端点已启动` / `WARNING HR 在线核实已启动` —— **生命周期消息用错级别**, 用户重启一次
  连吃三条通知(该配置 WARNING 以上推系统通知) ⇒ 改为 INFO(含热重载重挂与已关闭)。
  ②一次扩展取数超时被 service(`取数失败(1 次): …`)与 worker(`error: …`)各告警一次 ⇒ **两条通知**;
  改为「谁产生原因谁告警」: 结果对象带 `alerted`, 产生处报 WARNING 后状态层只记 INFO。
  ③`站点文件解析失败: Expecting value: line 1 column 1 (char 0)` = **站点文件是空的**:
  新增两层保护 —— 写盘默认把上一版留为 `.bak`; 读到坏文件先把现场挪到 `.bad-<ts>`(否则下一次写盘就把它
  覆盖掉)再试 `.bak` 兜底, 取证串带大小与开头字节(空文件 vs 内容坏一眼可分), 同一文本只告警一次。
  ④顺带挖出两个真缺陷: (a)**恢复出来的备份必然比本进程上次写的旧** ⇒ 锁自检的「revision 回退」把自愈
  判成只读, 站点从此写不回去(自愈变砖) ⇒ 恢复后重置写者心跳基线; (b)关停/热重挂时被叫停的取数长着
  `HrChannelUnavailable` 的皮 ⇒ 每次关停都告警一条「无可用取数通道」且误计失败 ⇒ 分出子类 `HrChannelStopped`
  并按「非事件」处理(不告警不计失败)。
  新增 **10 条**(store 5 / runtime 2 / service 2 / worker 1)并把 fetcher 的叫停用例改为钉住子类;
  ★红验: 去掉 `alerted` / 启动消息打回 WARNING / 叫停降回父类 ⇒ 四条守阵当场变红。
  全量 **1498 passed + 1 skipped** / TOTAL 91%(10423 / 778 / 3444 / 308) / sidefx ≈2430 / 越界 0。
- ↑ 收集数 **1476 → 1489**(**+13**; 2026-09-24 **HR 告警分档 + `--hr-status` 现状报告**):
  用户装上 M2 交付的扩展后实报两条体验问题: ①「会弹 warning」②「无法知晓拉取的数据是否正确」。
  ①定性: 日志里 `partial: 配额/间隔受限(间隔: 还差 104s)` 与 `waiting: 未到可取时刻(…)` **交替出现**,
  一句故障都没有 —— 那是后端按自己的频控取数的常态(一轮完整刷新 = 3 档位各翻到底 + 回填 .torrent,
  而请求间隔 >= `min_torrent_interval` 90s ⇒ 默认要几分钟); 真缺陷是**告警分级**: 取数线程把所有
  `PARTIAL` 一律 WARNING, 而 WARNING 会被 notify 推成系统通知 ⇒ 每 60~90s 一次弹窗; 更隐蔽的是
  同一个根因在轮次间动作不同(partial/waiting), 用 action 当“状态变化”判据等于逐轮都算变化。
  修法: 结果对象新增 `reason_kind`(budget / parse, 分类在**产生处**做一次供日志与报告复用);
  日志分三档 —— 节流中(未到点 / 被自己频控拦下)按「被拦根因类别」去重、消息明写“非故障”、
  被去重的降 DEBUG; 页面/解析类与取数失败才 WARNING; 完整刷新后清节流记忆。
  ②新增 `--hr-status [--hr-status-rows N]`: **不取数 / 不加锁 / 不写盘 / 不连 qB**, 摊开已落盘数据
  (档位分布 / 待回填 infohash / 配额与熔断 / 不完备的原样原因 / 明细表)。
  新增 **13 条**(service 分类 / worker 去重与提醒与清记忆 / report 六条含“站点文件一字未改”与坏文件 /
  cli 互斥与不构造 manager), ★红验: 去掉 `REASON_BUDGET` 分支 ⇒ 三条 worker 用例当场变红。
  全量 **1488 passed + 1 skipped** / TOTAL 91%(10349 / 768 / 3428 / 308) / sidefx 2390 / 越界 0。
- ↑ 收集数 **1468 → 1476**(**+8**; 2026-09-24 **扩展侧两条实报报错修掉 + 守阵**):
  用户装上 M2 交付的扩展后实报两条: ① `Invalid value for origin pattern pt.btschool.club:
  Missing scheme separator.` ② `TypeError: Failed to fetch`。根因: ①选项页把**原始输入**直喂
  `chrome.permissions.request`(它只吃带 scheme 的匹配模式, 报错还是**未捕获的 Promise 拒绝**);
  ② 后端 `config.yml` 里**根本没有 `hr_check` 段** ⇒ 端点从未启动(端点要三个开关同时满足:
  `hr_check.enabled` + 站点 `mode != off` + `channel.enabled`), 而浏览器对网络层失败只给一句
  `Failed to fetch` ⇒ 用户无从下手。修法: 输入**先归一化再交给浏览器 API**(裸域名→`https://host/*`;
  端点补 scheme / `localhost` 折 `127.0.0.1` / 协议固定 http), 非法输入**逐条**报错; 归一化抽成
  `normalize.js` **一份**(选项页 `<script>` + 后台 `importScripts` 共用, 防止两条路径漂移);
  选项页新增**自测端点连通**(把“连不上 / 401 / 403”分开)+ `unhandledrejection` 兜底;
  扩展 README 补「端点何时才会启动」三开关与排障表; `host_permissions` 补 localhost /[::1] 别名。
  新增 `tests/test_extension_proxy.py` **8 条**(manifest 作用域 / **真跑** normalize.js / 归一化只有一份 /
  与后端协议常量对照 / 调用顺序 / 不得留裸拒绝) —— ★红验过(去掉补 scheme 那行即当场变红);
  过程中真被 `node --check` 漏挡一次(删了本地副本、引用还在的 `ReferenceError`), 故守阵坚持"执行"而非"查语法"。
  全量 **1475 passed + 1 skipped** / TOTAL 91%(10217 / 763 / 3382 / 304) / sidefx 2357 / 越界 0。
- ↑ 收集数 **1466 → 1468**(**+2**; 2026-09-24 **WEB UI 多选右键菜单目标 = 整个选中集合** + **生成物重建提示指错命令**):
  ①`test_web.py::test_frontend_ctx_menu_multi_select_targets_selection` —— 用户报"多选时右键菜单
  应该对所有选择的种子生效, 当前仅对鼠标指向的触发右键的种子生效"。根因: 四个 `open*Menu`(组/成员/剧/集)
  只记 anchor(`key`/`hash`/`episode`), 动作端点直接拿它拼 URL ⇒ 无论选了多少都只动被点的那一个
  (菜单照常弹出、照常成功、**无任何报错**, 肉眼难辨)。修法: `menu.js::_ctxMulti` 判"这一行属于选中集合
  且集合范围 ≠ 该行自身范围"(判据**不是**"选中数 > 1" —— 否则"选中 1 个辅种 + 右键它的成员行"会给出
  文案说"该种子"、实际动整组的错菜单), 四入口各写 `menu.multi`; 双 UI 模板加 `v-if="menu.multi"` 批量分支,
  动作整份复用批量浮条链路(`commands.js::ctxAct`→`bulkAct` / `ctxDelete`→`bulkDelete`), 不另拆目标集合。
  守阵钉三处成对关系(四入口写 `multi` / 双 UI 分支逐项一致 / `ctxAct` 复用 `bulkAct`), 两处红验过;
  冒烟 `scripts/ui_smoke.cjs` +12 条 CTX-03(双 UI × 六: 三视图批量菜单 / 未选中行负向对照 /
  合单一条 bulk / 乐观覆盖), 已对 HEAD 红验(prism 三条变红)。冒烟三模式 84/84/8 全 0 失败。
  ②`test_memory_bank.py::test_gen_cmd_hints_name_real_tasks` —— 修上一条报告、本轮由用户指令
  「修复既有缺陷然后提交」的既有缺陷: `_common.gen_cmd()` 忽略传入的脚本名、一律返回
  `commands run kb.index`, 而 `kb.index` 只跑 `gen_tasks_index` + `gen_kb_index` ⇒ `_doc-map.md` /
  `plans|reports/_index.md` 的报错文案把用户指向一条**跑完仍然红**的命令(提交闸门 `my-commit-flow`
  的 `memory-bank/` 一条早就挂了这四条的 `--check` ⇒ "闸门能红、却没有一条能修的命令")。
  修法两条一起: `kb.index` / `kb.check` 补上 `gen_docs_index.py` + `gen_doc_map.py`(与闸门**同集**) +
  `_common.GEN_CMD_BY_SCRIPT` 按脚本查表(`gen_active_recent.py` → `kb.active --check`, 它是只校验的)。
  守阵钉"调用点全覆盖 / task id 真实存在 / 提示说跑 `kb.index` 的脚本必须真在它的 run 列表里",
  两处红验过, 并端到端复现原症状(写坏 `_doc-map.md` → 照文案跑 `kb.index` → `--check` PASS)。
  ⚠ 本批与主线 `5c518b3`(HR 在线核实 M1, +142)合流: 按「移出改动 → `merge --ff-only` → 施回改动」
  同步(全程未用 stash/rebase), 基线数字取**合流后实测**; 流水轮转沿用主线的**两级方案**
  (`-archive.md` = 中间段 / `-old.md` = 最老段) —— 我此前并入 `-old.md` 的那 15 条**已撤**,
  因为它们已在 `-archive.md` 里(避免同一段历史存两份)。
  ⚠ 本条的绝对数字已按**合流后链条**改写: 它落在地下一条(HR 在线核实 M2, +91 ⇒ 1466)之**后**, 故起点是 1466、终点 1468; 远端提交时记的「合流后实测 1375 → 1377」是只并到 M1 时的读数。
- ↑ 收集数 **1375 → 1466**(+91; 2026-09-24 **HR 在线核实 M2: 取数通道**):
  用户令「提交…然后继续 M2」。本轮落地计划的 **M2**(后端端点 + 取数线程 + 共享站点数据 + MV3 扩展):
  新增 `hr/channel.py`(协议 `HrTask`/`HrResult` + 密钥落 `<data_dir>/hr.token` + origin 白名单 +
  URL 白名单(SSRF)) / `hr/queue.py`(派发式队列 = 端点线程与取数线程的**唯一**交接面; 只接受
  「确实派发过且未作废」的回传, 且回传域名须与任务一致) / `hr/server.py`(stdlib
  `ThreadingHTTPServer`, 仅听回环, `allow_reuse_address=False`) / `hr/fetcher.py::ChannelFetcher`
  (把请求变任务并阻塞等回传) / `hr/worker.py`(取数线程按 `poll_interval` 自唤醒 + 只读视图
  **原子发布**(单元组赋值, 读方零等待) + 告警节流) / `hr/runtime.py`(`QbManager.hr` 门面:
  按配置启停、热重载重挂、自检快照); 扩展在 `extensions/hr-fetch-proxy/`(MV3 哑取数器 + 实例端点列表)。
  配置侧: `channel`/`shared_dir` 改 **L1** 并接上 `HrRuntime.apply`(监听身份变了才重绑端口);
  新增两个键 `channel.extension_id`(§6 要求「优先固定扩展 id」, 没有它无从固定)与
  `channel.request_timeout`(**必须有**: 否则扩展中途被杀会让持锁的取数线程永久挂住)。
  新增 6 个测试文件; 覆盖端点鉴权三道 + 真 HTTP 往返 + 端口冲突 fail-fast + 任务伪造注入 +
  视图「只在数据变化时抬 revision」+ 关停叫停 + 热重载重挂。
  **本轮测出一个真缺陷并修掉**: 取数线程正阻塞等扩展回传时, `stop()` 会白等到
  `request_timeout`(默认 180s)且**一直持着站点锁** ⇒ 改「先 `cancel_all` 叫醒等待方, 再 join」
  (`HrWorker.stop()` 内建, 调用方不可能忘); 这也是本轮 7 条用例各慢 10.5s 的根因。
  红验方式: 首跑 4 条真红(队列未派发即回传 / `path_of` 尾斜杠 / `silent_for` 伪时钟 / publish 空视图),
  逐条定位后全绿。
  全量 **1465 passed + 1 skipped** / TOTAL 91%(10217 语句 / 763 未覆盖 / 3382 分支 / 304 partial) /
  sidefx 台账 2353 / 越界 0(**合流后为 1467 passed + 1 skipped = 1468 collected**, 见上一条 ——
  本轮实测时还未并入那 +2)。⚠ 余下 **M3(判定联动四消费点) / M4(多站点)** 未落地 ——
  本档案「子任务状态表」逐项记状态。耗时升到 17.1–17.2s(真 socket + 线程用例, 见 [baseline.md](baseline.md))。
- ↑ 收集数 **1233 → 1375**(+142; 2026-09-24 **HR 在线核实 M1: 核心管道**):
  用户令「实施该计划」(部分种子 HR 的在线核实), 并指定页面样本 `D:/Projects/站点页面/BTSchool`
  与前期实验脚本 `scripts/hr_fetch_experiment.py` 为输入。本轮落地计划的 **M1(离线可做)**:
  新包 `src/auto_qb/hr/` —— `bencode`(infohash 取 info 的**原始字节切片**, 定位跨度时只跳不建对象) /
  `parse`(栈式表格抽取 + 数值容错) / `adapters`(NexusPHP `myhr.php` 九列形态) /
  `model`(站点文件内的账号级状态) / `store`(**每站点一个 JSON + 一把 filelock**, 持锁期间完成
  「读→判有效期→必要时抓→写→释放」; revision 回退 / 心跳被覆盖 ⇒ 退化只读) /
  `ratelimit`(间隔 **只向上抖动** + 小时/天两级配额 + 失败退避熔断 + 时间窗) /
  `resolve`(**三态判定** = 受管束 / 已核实不受管束 / 未核实 + 不可变只读视图) /
  `service`(刷新管道; `dry_run` 零请求零写入、`hr.once` 抓取但不写盘) / `report`(`--hr-once` 走查) /
  `fetcher`(取数通道协议; 后端零 cookie、不直连站点)。
  配置接入全链路: `KNOWN_*_KEYS` + 校验器(**站点 mode != off 但没配 hr 段 ⇒ 配置期直接报错**,
  否则 `check_hr_condition` 恒 False、整站保护静默失效) + `config/schema/hr.py` + 新分组 +
  `HR_CHECK_FIELD_LEVELS`(热重载分级) + loaders; 设置页 Hub 补 `hr_check` 文案 / 未启用判定 / 读数。
  新增 8 个测试文件 + 共享夹具 `tests/hr_helpers.py` 与**脱敏页面 fixture**(取自真实样张结构:
  含 `<td class="embedded">` 包裹表、灰色不可点的「下一页」、免罪链接); 覆盖 bencode 钉死向量 /
  原始切片 vs 重编码(钉死计划 §5 的坑) / 畸形输入 / 表头缺失=改版 vs 表头在 0 行=合法空 /
  防重取三层 / 有效期复用零请求 / 翻页未到底 ⇒ 覆盖证明不成立 / **判定表逐行** /
  **新鲜度闸门不可被 `unknown_policy` 绕过** / 熔断 / 并发锁粒度 = 站点。
  红验方式: 11 条首跑真红(见提交说明), 逐条定位后全绿。
  全量 **1374 passed + 1 skipped** / TOTAL 91%(9278 语句 / 727 未覆盖 / 3128 分支 / 277 partial) /
  sidefx 台账 2212 / 越界 0。⚠ 余下 **M2(取数通道 + 取数线程) / M3(判定联动四消费点) / M4(多站点)**
  未落地 —— 本档案「子任务状态表」逐项记状态。
- ↑ 收集数 **1232 → 1233**(+1; 2026-09-24 **WEB UI 添加种子回执与 optional 选项**):
  用户报"添加种子显示失败 + 桌面弹 WARNING 但实际添加成功, 且「添加后开始」不生效"。三条根因:
  ① 回执只认 `"Ok." in str(result)`, 而 qB 5.2+(Web API 2.14.0)的 `/torrents/add` 已改回 JSON 元数据
  (`TorrentsAddedMetadata`, dict 子类)⇒ 判定恒假; ② 停止位被"False 就不传"的过滤器吞掉 ⇒ qB 回落到
  **会话级**默认 `isAddTorrentStopped()`, 勾了也按停止添加; 另 qbittorrent-api 的
  `is_paused or is_stopped` 会把 `is_paused=False` 折成 `None`(实测请求体空串)⇒ 只能用 `is_stopped=`;
  ③ 成功路径记 WARNING, 而 NotifyHandler 挂在 `auto_qb` logger 上 ⇒ 每次成功都推桌面弹窗。
  同轮按用户"修复同类隐患"把 `use_auto_torrent_management` 一并改成恒显式(它同为 `std::optional`,
  未勾 + 未填保存路径时会吃 qB 全局管理模式); 判据升级为"看 `addtorrentparams.h` 的字段类型 ——
  optional 的必须显式, 普通 bool 省略安全"。
  修法: 新增 `webui/commands.py::_add_outcome` 双形态判定 + 恒显式下发 `is_stopped` /
  `use_auto_torrent_management` + 成功 INFO / 未受理才 WARNING。替身同步补 `is_stopped` 与
  `is_stopped_raw`(保真度)。用例名 `test_add_torrent_receipt_and_optional_flags`(四条断言全红验)。
  两条新坑写进 [pitfalls/backend/qb-api.md](../pitfalls/backend/qb-api.md) 与
  [pitfalls/testing/stubs-sim.md](../pitfalls/testing/stubs-sim.md)(含 `make_manager` 清 root handlers
  ⇒ 用例体内建 manager 时 caplog 恒空)。⚠ 本轮开工时与主线齐平, 提交前发现主线已前进 2 个提交
  (`9d7a3eb` / `2e2e2b5`)⇒ 按"移出改动 → `merge --ff-only` → 施回改动"同步(重叠仅 3 个文件:
  两个基线文档 + 生成物 `tasks/_index.md`), 故本条收集数在**合流后**的 1232 基础上 +1。
  全量 **1232 passed + 1 skipped** / TOTAL 91%(7782 语句 / 622 未覆盖 / 2648 分支) / sidefx 2067 / 越界 0。
