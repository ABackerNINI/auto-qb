# 26-09-22-backend-partial-hr-verify — 进度纪要(外迁存档)

> 摘要: 任务档案「进度日志」段**早期纪要**的外迁存档(该段触 `TASK_LOG_CAP` 上限后按策略切出, 原样未改)。
> 触发: 早期进度, 计划为何改成这样, v1.2-v1.9 决策过程, 需求逐轮澄清

本文件是 [../26-09-22-backend-partial-hr-verify.md](../26-09-22-backend-partial-hr-verify.md) 的附件;
最近的纪要仍在档案本体里。以下按原顺序(最近在上)。

- **2026-09-25 (M4 多站点与打磨)** — 用户「继续 M4」令实施计划的最后一块。
  ① **先盘点**(子代理只读调研): 得到的关键结论是「站点隔离的工程骨架与 CLI 可观测性**已经具备**
  (站点分文件 / 每站点一把锁 / 每站点配额与熔断 / 站点级视图 / per-site adapter 工厂 / `--hr-status` 全摊开),
  真缺口只有三处: 非 NexusPHP adapter 要写代码、站点级状态**在界面上一个出口都没有**、四类事件只有级别没有语义」。
  ② **四类事件语文化**(`hr/events.py` 新模块): 告警文案收口到一处并加标签前缀(`[HR 登录失效]` / `[HR 熔断]` /
  `[HR 页面改版]` / `[HR 通道静默]`), 用户可直接 grep。**登录失效从熔断里摘出来**(新 `HrLoginExpired`):
  与 `HrChannelStopped`/`HrChannelQuota` 同一套判据 —— **能不能靠重试解决**。登录失效重试一万次也一样,
  算成失败会把「去登录」这个动作要求掩盖成「站点坏了」, 而且熔断冷却会让用户登录完还要白等; 故**不计失败、
  不推熔断**, 只报一次 WARNING(文案直接给动作), 原因写进站点文件 `refresh.reason`(失败路径里唯一持久可见的痕迹,
  `--hr-status` 与视图 notes 都读它) —— 但**绝不动** fetched_at / 覆盖证明 / 新鲜度基准(那会变成「登录失效反而
  给了新背书」)。通道静默是**端点级**事件 ⇒ 告警里列出受影响站点。
  ③ **站点级状态单点**(`hr/status.py`): `site_status()` 把「站点文件 + 视图」折成纯数据快照(含新派生量:
  下次刷新时刻 / 回填进度比例 / `blocking`「现在为什么不放行」); `report.py` 改为消费它(CLI 文本口径逐字未变,
  `test_hr_report.py` 13 条全绿就是证据) —— 这样 CLI 与界面**不可能**出现「报告说待回填 2 条、界面说 3 条」。
  ④ **WebUI 出口**: 只读端点 `GET /api/hr/status`(路由金清单 +1 条 ⇒ 同步 `test_web.py` 的 60→61) +
  设置页「HR 站点状态」章节。**两个入口都要有**(经典 `cfg.activeGroup === '__hr'` 与 Console Hub `hub.view === '__hr'`),
  两套 UI 成对改 —— 与日志页同款: 打开时拉一次, 手动刷新, 不轮询。新增**前端字段一致性守阵**:
  扫模板里的 `s.<字段>` / `hrs.<字段>` 引用, 断言它们都在后端快照键里(字段名打错 = 整段静默空白,
  pytest 全绿、后端也全绿, 只有真打开页面才看得出来)。
  ⑤ **多站点守阵**(`tests/test_hr_multisite.py` 5 条): 「第二/第三个 NexusPHP 站点**只改配置**就能用」不是文档承诺,
  而是钉死的断言 —— 第二站点各自文件 / 各自锁 / 各自配额与熔断 / 索引与已取记录不串味。顺手确认了一个语义:
  **配额是按请求记的**(页面与 `.torrent` 都算) —— 一轮三页 + 一次下载 = 4 次。
  ⑥ **本轮挖到的两个测试坑**(已回写 `pitfalls/testing/assertions.md`): (a) 守阵的取值锚点命中了**侧栏按钮**
  里的同名短串 ⇒ 扫到空块、断言**恒真**(守阵失效不报错); 修法是锚点选块独有的形态 + 加「必须扫到字段」兜底。
  (b) 红验的篡改用了大写字母(`fresh_textX`)⇒ `\b` 在 `t|X` 之间没有词边界 ⇒ 正则**根本看不见**它 ⇒ 红验假绿。
  ⑦ 测试 **+20 条**(events 7 · service 3 · worker 1 · web 4 · multisite 5), ★红验: 字段守阵(改错名 ⇒ 红),
  登录失效与静默文案断言也各自验过。全量 **1561 passed + 1 skipped**(TOTAL 91% / 10831 / 786 / 3556 / 321,
  并行 18.1 / 18.1 / 19.2s), sidefx 越界 0; `kb.check` / `doc.links` / `doc.caps` / `doc.drift` 全绿。
  文档: `docs/configuration.md`(接第二个站点要做什么 + 四类事件标签表 + 界面入口) · 根 `README.md`(M4 状态)。
  下一步: **真机走查**(装扩展 → `--hr-once` + 主程序跑一轮), 已在下方「未完成」保留; 非 NexusPHP 形态站点
  要写 adapter 时按 `adapters/__init__.py` 的注册协议加(本仓无该形态站点样本, 不猜着写)。

- **2026-09-25 (实报修复: 下载被饿死 + 扩展第二道闸)** — 用户贴 `--hr-status` 与 `BTSchool.json` 报
  「种子似乎没有下载成功」, 并授权修 P1/P2/P3 + 给扩展加硬上限(暂定 访问 10/时·50/天, 下种 50/时·200/天)。
  ① **先定位**: 报告里 `已取种子 0 条 / 取种子失败 0 条 / 待回填 infohash 1 条 / 受管束种子 0 个`
  = `.torrent` **一次都没取过**(不是失败), 扩展只被派了一个页面任务(扩展侧日志「取 1 条(成功 1; 全部直取)」)
  ⇒ 责任在后端的频控与流水线顺序, 不在扩展。
  ② **三个真缺陷**: (a) `_Budget` 的口径是「相邻两次**请求**间隔 >= 90s」, 而 `_do_fetch` 先抓 A/B/C
  页面再取 .torrent ⇒ 每个窗口唯一的名额总被页面吃掉; 不完备刷新只给 60s 有效期 ⇒ 下一轮又从页面开始,
  本小时 11 次配额全烧在重抓页面上。(b) 生产路径 `sleeper=None`(计划 §8 本意是在锁内等满) ⇒ 一次刷新
  只能发出第一个请求, `scopes_done=[A]` / `complete=False` ⇒ **永远没有安全放行**。(c) 索引 0 个 infohash 时
  所有种子落「未核实」⇒ 按 `unknown_policy=hr` **整站种子集体按受管束打标**。
  ③ **修法与守阵**: 复用轮只补下载(`_backfill_on_reuse`) · 门面提供可中断的锁内等待 + 单次/本轮两道上限 ·
  `has_lookup_keys` 为假时 `judge_record` 返回 None(回落本地, `mode: all` 不受影响) · 扩展 `site-caps.js`
  独立计数 + 超限拒发(`kind=ext-quota`, 后端 `HrChannelQuota` ⇒ ACTION_WAITING, 不计失败不推熔断, 只报一次 WARNING)。
  ④ **测试 +15 条**, ★**红验 4 处**(关掉补下载 / 关掉等待 / 关掉无键闸门 / 关掉扩展拒发 ⇒ 对应守阵全红)。
  合流后全量 **1541 passed + 1 skipped**(本分支合流前 1534); 坑已回写 `pitfalls/backend/high-risk-ops.md` 与 `behavior-core.md`; 
  文档: 扩展 README(第二道闸章节 + 修正「间隔受限不是故障」的旧口径) · 根 README · docs/configuration.md。
  ⚠ 仍待用户真机确认: 取 .torrent 后索引是否长出键、三态在 WebUI 上是否正确(以及那 2 次 `fuse.failures` 的来源)。

- **2026-09-25 (M3 落地)** — 用户「继续 M3」令实施判定联动:
  ① **判定收口**: `hr/resolve.py::judge_record(view, infohashes, anchor=, now=, unknown_policy=)` —— 两个 infohash
  取**更保守**结论(命中 > 恒受管束 > 已放行 > 未核实), 返回 `HrJudgement`(身份 / 最终布尔 / 依据 / 站点侧达标结论 /
  `HrSiteFacts` 站点侧展示值); 站点未接入或 `mode=off` 返回 **None = 本模块不适用**(调用方走既有本地逻辑)。
  门面入口 `HrRuntime.judge()` 只查**总开关**(站点级开关由记录侧先挡 —— 它手里就有 `tracker_conf`,
  不必每调用一次就遍历一遍配置)。
  ② **落点(计划 §9 的「稳定引用 + 读取时现算」)**: 记录加 `hr_link`(判定桥) / `hr_judgement()` / `hr_anchor()`;
  `check_hr_condition` 与 `check_hr_satisfied` 先问站点侧、站点没给再回落本地。**四个消费点(打标 / WEB 视图 /
  `hr` 规则条件 / `tor.hr_*` 表达式)调用点一行未动** —— 改的是它们共同调用的那两个方法。判定桥 = `QbManager.hr`
  门面的稳定引用(热重载不换对象), 由 `TorrentStore` 在记录构建/变更时挂上(`hr_link is not link` 才赋值),
  读取时现算 ⇒ **锚点漂移与视图更新都不需要记录置脏**, 也不做全库重写。
  ③ **零静默变更两道门**(缺一即回落本地): 站点配了 `hr_check` 且 `mode != off` + 全局 `hr_check.enabled`。
  当前用户配置无 `hr_check` 段 ⇒ 行为与之前逐字一致(既有测试全绿就是这个口径的回归)。
  ④ **锚点提供者**: `QbManager._hr_anchors()` 按站点给出 `{infohash: HrAnchor}`(只读遍历 `store.all()` 快照,
  取数线程经 `anchors_fn` 异步要), 与 `HrWorker._collect_anchors` 的形状/站点键同源。
  ⑤ **WebUI 可观测性**: 字段加 `hr_state` / `hr_state_text` / `hr_reason` / `hr_satisfied_src` +
  站点侧值(档位 / 还需做种 / 剩余达标 / 分享率 / 站点下载量), 详情抽屉加两行(三态·依据 / 站点侧值),
  安全放行用**中性色条**(不能把放行渲染成告警)。
  ⑥ **两处实现期拍板**(计划未覆盖的边界, 已写进计划 v2.3): (a) 站点**还没发布过视图**时回落本地而不按
  「未核实」算 —— 若按 policy 算, `mode: all` 站点会在启动窗口里让整站种子集体触发打标(千级标签风暴);
  (b) 站点行**缺达标字段 ≠ 未达标**(新 `HrEntry.satisfied_verdict` 的 None 语义) —— 不知道就回落本地。
  ⑦ **测试 +15 条**(收口判定 7 / 门面 3 / 记录接入 4 / 锚点 1 / WebUI 三态 1), 另把替身对齐真实模型:
  `FakeTracker` 补 `hr_check`(缺它会让「站点未接入」路径在测试里 AttributeError 而非走本地逻辑),
  `FakeTorrent` 补 `hr_judgement` / `hr_anchor`。★**红验已跑**(2 处反证, 共 4 红, 回滚后 89 绿):
  ① 临时旁路判定桥(`check_hr_condition` 无视 `judged`) ⇒ `test_record_hr_follows_site_judgement` /
  `test_record_hr_released_by_site_view` 变红; ② 站点未接入/无视图改成返回判定而非 `None` ⇒
  `test_judge_record_not_applicable_when_site_off` / `test_judge_without_published_view_falls_back` 变红。
  全量 **1519 passed + 1 skipped**(TOTAL 91% / 10534 / 779 / 3494 / 310~311; 并行 18.3 / 18.9 / 19.3s),
  sidefx 越界 0。
  下一步: **M4 多站点与打磨** + M0/真机走查(需用户装扩展)。

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
  sidefx ≈2430 / 越界 0; 新坑补进 [pitfalls/web-ui/extension-bridge.md](../../pitfalls/web-ui/extension-bridge.md)
  (「后台标签」≠「不影响用户」); 基线已回写。
  下一步仍是 **M3 判定联动**; 仍待定: `config.yml` 明文凭据入库。

- **2026-09-25 01:10** — 用户点名修两件: ①`service._do_fetch` 的**取数失败分支漏了 `persist` 判断**
  (成功分支有、失败分支没) ⇒ `--hr-once` 声称「不写文件」但一撞上取数失败就把熔断/失败计数写进站点文件,
  而那份文件是**正式实例共用**的 ⇒ 只读口令偷改了取数节奏。修法: 失败分支同样按 `persist` 走,
  `persisted` 口径与成功分支统一(`status == "written"`), 并在调用点写明「失败计数/熔断同属持久状态」;
  守阵双向钉住(只读失败不落盘 / 正式失败必须落盘), ★红验: 临时恢复旧实现即当场变红。
  坑入库 [pitfalls/backend/high-risk-ops.md](../../pitfalls/backend/high-risk-ops.md)
  「只读口径是开关, 新加的写盘分支必须逐条带上它」。
  ②README 两处**坏字符**(存成了 U+FFFD): `HR 在线核实` 标题补回 🔍, `辅种管理` 去掉坏字节保留 👯;
  全仓扫过 U+FFFD, 其余均为乱码示例的刻意引用(`pitfalls/ops/console-encoding.md` 等), 不动。
  ③ 全量 **1499 passed + 1 skipped / 17.90–22.91s**(TOTAL 91% / 10425 语句 / 778 未覆盖 / 3446 分支 / 308 partial),
  sidefx ≈2430 / 越界 0; 基线已回写。
  下一步仍是 **M3 判定联动**; 仍待定: `config.yml` 明文凭据入库。

- **2026-09-22 22:04** — 可行性分析完成, 计划 v1 产出 ([../plans/26-09-22-2204-partial-hr-site-verify-plan.html](../../plans/26-09-22-2204-partial-hr-site-verify-plan.html))。读路由: config-reference (keys / loading-and-write) · systemPatterns (taskqueue / web-runtime / client-and-state) · modules/overview · conventions/webui; 源码锚点: TorrentRecord.check_hr_* / mixins/tags._add_hr_tag_or_category / mixins/web_view._hr_view_fields / rules (conditions + expr/env) / qbmanager._create_global_tasks; 外部事实两条经 web_search 核实。立档 (阈值 #4: 产出计划文档)。下一步: 等开放问题拍板 → M0。
- **2026-09-22 22:10** — 全量闸门首跑红 1 条 (`test_doc_links_are_not_broken`): 本档案内链接深度误写 `../docs` (`memory-bank/tasks/` 到根 `docs/` 应为 `../../docs`), 修正后重跑全绿 (1189 passed + 1 skipped, TOTAL 91%, 与基线稳态一致)。该坑已有守阵 (test_memory_bank.py 链接机检) 兜住, 不另立 pitfalls 条目。
- **2026-09-22 23:00** — 用户指令: 同步远端 + 在 scripts/ 实现独立实验程序 (用现有 cookie 下载 HR 种子)。
  ① 同步: preflight 报落后 3 提交(按 origin/GitHub 快照), 实拉 gitee/develop 确认 3 提交 (e50755d 同步规则修正 / a61d0f4 README 同步 / 49eacb8 入池跨组交叉 issue), 恰好都动本轮两个脏文件 → 走 sync-pull 安全流程 (diff --output 备份 + restore + ff-only); restore 后 activeContext 仍幽灵 M 拒 ff, `git add`+`git reset` 刷新后 ff 成功 → 49eacb8; 会话回写已在新版本上重施 (activeContext 滚动链压缩了远端三条旧状态)。
  ② 页面解剖: 样张 `D:/Projects/站点页面/` (myhr.php, utf-8, 含 Darkreader 属性); HR 表在 `<td class=embedded>` 包裹表内 (两层嵌套), 表头 colhead 九列与用户描述一致; 页面无 download.php 链接 (按 NexusPHP 惯例拼 download.php?id={tid}); 状态过滤 hrtype=A考察中/B已达标/C未达标/D已免罪; 样张含 1 行 (tid 313852, 27.34 GB, 还需做种 2:42:17, 剩余达标 9天06:05:11)。
  ③ 交付 `scripts/hr_fetch_experiment.py` (独立实验, 不接主程序): bencode 解码 + infohash v1/v2 (原始字节切片) + 栈式树 HTML 解析 (容忍包裹表) + 离线 `--html` / 在线 `--cookie-file` 两模式 + 限速下载 (±25% 抖动, 已存在文件跳过防重下) + `--selftest` 钉死向量。
  ④ 验证: selftest 11 项全过 (2 infohash 向量 + 9 数值解析); 离线解析样张 1 行全部字段正确; **在线路径未验证 (需用户 cookie)**。过程中自测向量当场抓到一个真 bug: 向量生成器用 `data[start:-1]` 粗切 info 切片, 当 info 后还有顶层键 (private) 时期望值错 —— 修正生成器后确认解码器无误; 向量改 base64 装载避开二进制转义层。
  ⑤ 下一步: 用户拿 cookie 跑在线模式验证下载 URL 形态 (是否需 passkey) → 拍板开放问题 4 条 → M1。
- **2026-09-23 00:15** — 用户: 「我需要的是自动抓取cookie」⇒ 实验脚本升级 --auto-cookie / --auto-cookie-login:
  专用浏览器 profile + CDP (Storage.getCookies) 自动读 cookie —— Chrome 136+ 禁默认目录开调试端口的
  合规路线; 首次可见登录一次, 之后无头全自动; cookie 不落明文 (浏览器自己解密, 脚本只经内存)。
  实现: 浏览器探测 (chrome→edge, 可指定路径) + 极小 WebSocket 客户端 (手写帧/mask/ping-pong, 零新依赖)
  + Browser.close 优雅退出。
  实测三坑: ① 启动器进程秒退 (exit 0/21, ProcessSingleton 直方图证实移交) 而真实浏览器存活 —— 就绪判定
  只看调试端口, 不能用 proc.poll(); ② proc.terminate() 只杀启动器杀不掉浏览器树 —— 改按命令行匹配
  profile 路径 taskkill /T /F (不碰用户自己的浏览器); ③ 被杀残留的 profile 状态会让下次启动端口不再就绪
  (Edge 报 crashpad "Settings version is not 7") —— 加 --disable-crashpad + profile 绝对路径; 失败信息引导删
  profile 重登。
  验证: selftest 11/11; --auto-cookie 全新 profile 无登录态: 无头拉起→CDP 抓取(0 条)→干净报错→清理零残留,
  机器链路全通, 仅剩人工登录一步; 安全护栏拦了一次 rm profile 目录 (改用全新目录验证, 不重试删除);
  全量 1189 passed + 1 skipped (TOTAL 91%)。用户已令「提交」, 流水线进行中。
- **2026-09-24 18:08** — 用户: 「审核该计划是否有问题和可优化的地方」+「更新计划, 否定手动填写 cookie … 比较两种扩展方式的实现维护成本与效果」。
  ① 审核 (只读, 未改任何文件): 查出 4 条事实性错误/过期 —— 计划不知 `scripts/hr_fetch_experiment.py` 已落地并部分验证 (bencode/infohash + 钉死向量 11 项 + myhr 解析 + 限速下载 + CDP 抓 cookie);
  `mixins/web_view.py` 路径不存在, 实为 `webui/views.py::_hr_view_fields` 且被 **Web 线程**调用 (`webui/server/routes/torrent_detail.py`);
  测试基线数字过期 (计划写 1190/1188, 单点 baseline.md 实为 1203/1202+1); `fetch_window` 全库无此键, notify 的同类项是**语义相反**的 `quiet_hours`。
  另 3 条架构判断需修正 (身份字段不能反向依赖 `manager.state`; partial 站点未配 `hr` 段则 `check_hr_condition` 恒 False、保护静默失效; 线程生命周期与 notify 跨线程),
  3 条内部矛盾 (配额口径"全站合计"vs"站点独立" / 抖动 ±25% 与"间隔 ≥ min"验收互斥 / dry-run"零请求"与 M1"报告含新增"互斥)。
  ② 用户否决手工填写 cookie (「解决麻烦不是制造新的麻烦」), 要求比较扩展的两条路线。v1.2 采纳**路线 1**: 扩展在后台标签页取 DOM 快照与 .torrent 二进制 → **回传后端解析** (扩展=哑取数器, 无策略/无解析/不碰 cookie API), 通道走拉取式任务 ⇒ 后端零 cookie/passkey 依赖、零凭据配置、cookie 风险整体移除; 路线 2 (扩展内解析) 判为改版成本落在用户侧 (要重装扩展) 且解析脱离 pytest/fixture 体系, 仅在"必须交互才出数据"的站点降级使用。新增通道安全边界 (token 鉴权 + origin/SSRF 白名单 + 防伪造注入) 作为替代风险面。
  ③ 计划 v1.2 落地: §6 重写 (通道对比表 + 两路线成本/效果表 + 结论 + 安全边界 + 分发成本 + 待真机验证四问), §8 重写 (取数线程+令牌作废 ⇒ 端点线程只入队 + 主循环唯一写者, 新数据流图, 生命周期复用 `webui/server/lifecycle.py`), §2/§3/§5/§7/§9/§10/§11/§12/§13 相应修订, 新增 §14 变更记录; `doc-updated` 抬到 26-09-24-1808, 加 `doc-refs` 与本档 `Refs:` 形成双向认领。待拍板收敛为 4 条, 第 1 条即"是否接受装一个 unpacked 扩展"(不接受则走 CDP 备选, 接口不变)。
  ④ 结构自检: 标签配平 (section 14/14 · svg 1/1 · figure 1/1 · table 10/10 · pre 2/2), dark 口径保留; 浏览器实渲染 §7 配置块与 §8 新数据流图, 可读性正常。替换 §8 figure 时曾把旧 `<svg>`/`<figcaption>` 整块残留在文件里 (只数配对不看数量就发现不了), 已清除并复盘进 `pitfalls/docs/html-edit.md`。
  ⑤ 收尾: 档案回写 + activeContext 切片更新 + `kb.index` 重建 + 全量 `test.full` = **1207 passed + 1 skipped / 9.06s** (与单点 `testing/baseline.md` 的 1208 collected = 1207+1 一致, 本次只改文档未加测试, 无需改基线)。
  下一步: 等用户拍板 (取数通道 + 频度默认) → M0 收口 (download URL 形态 + 扩展通道四问实测)。
- **2026-09-24 18:33** — 用户: 「打包的扩展应该也能实现 unpacked 的功能吧? 不需要专用浏览器; 另外"未核实的种子"必须确认好边界, 首要是不要漏 HR, 其次是没有 HR 的要安全放行 —— 更新计划」。
  ① **扩展形态澄清** (§6): 扩展能力与分发形态**无关** —— unpacked / 打包 `.crx` / 商店版是同一套 manifest 与 API (`host_permissions` / `alarms` / `scripting` / `tabs`), 差别只在**怎么装、怎么更新**; 因此**不需要专用浏览器** (扩展就跑在日常 Chrome/Edge; "专用浏览器"只是 CDP 备选通道的代价)。id 固定改为「优先固定, 否则白名单放通 + **强制 token**」—— 真鉴权是 token, origin 白名单只是第二道 (设计不依赖"id 一定能固定"这个前提)。另补一句坦白: 商店版可自动更新会削弱路线 2 的"用户侧重装"摩擦, 但审核/发版周期与"解析脱离 pytest 体系"两条仍在, 结论不变。
  ② **「未核实」边界收口** (§9, 本版核心): 判定改**三态** —— 受管束 (`hr`) / **安全放行** (`verified_non_hr`) / 未核实 (`unknown`); 穷举未核实四类边界: 从未成功刷新 · **刷新不完备** (分页未到底/scope 失败/解析可疑/登录失效) · **新鲜度闸门** (`added_on` 晚于 `hr_refresh[site].last_success_ts` ⇒ 恒按受管束, **不可被 `unknown_policy` 绕过**) · 身份缺位 (infohash 未回填/站点未匹配)。
  ③ **放行只由「完整核实过且不在清单内」产生**, 并**粘性长期有效**(写 `hr_verified`) —— 这修正了 v1.2 的「索引过期回落 unknown」: 那会让通道静默期全站回到 HR, 正好把本功能的主要收益抵掉; 需要收紧的只有新种子, 交给闸门。两个方向的取舍与代价 (policy=not-hr 等于自愿放弃第一重保证) 写进 §9 取舍块。
  ④ **支撑件**: §4 加抓取范围 (**只抓 A 会把"已达标"的 HR 种子误放行** ⇒ 默认 `A+B+C`, D 视为放行) 与**覆盖证明**字段 (`hr_refresh`); §5 state 加 `hr_verified` / `hr_refresh` 并写明放行粘性; §7 配置加 `hr_page_scopes`、`unknown_policy` 注记; §10 风险由"误判方向"一行拆成「漏判 HR (最危险)」与「过度保护」两条; §12 新增 三态矩阵 / 放行粘性 / 覆盖证明 / scope 完整性 四组守阵。
  ⑤ 自检: 标签配平 (section 14/14 · table 11/11 · pre 3/3 · ol 2/2 · div 62/62), dark 口径保留; 浏览器实渲染 §9 三态表与边界块正常。过程中一次替换把 `old` 只写到 `</figure>` 导致旧块残留、又一次多删了 `<div class="colophon">` 开标签 —— 均由上面的配平机检当场拦下 (坑已在 `pitfalls/docs/html-edit.md`)。
  下一步: 等用户拍板 4 条 (第 1 条 = 是否接受装扩展) → M0 收口。
- **2026-09-24 18:56** — 用户两轮追问把方案推进到 **v1.4**: ①「二次下载/二次触发 HR 覆盖了吗」 ②「多下载客户端是常态, 需要谨慎考虑」 ③「同一账号只在一个实例启用 hr_check 不现实, 除非两个实例数据互通; 转移种子很普遍 (A 客户端下载 → B 客户端保种, B 的 downloaded=0 被当辅种); 所以网站数据是权威数据; 更新计划」。
  ① **自查发现的漏洞 (已被 v1.4 修掉)**: v1.3 引入的「放行粘性长期有效」在多客户端下不成立 —— 账号在**别的客户端**下载时本地零信号, 若清单未更新就会继续放行 ⇒ 漏 HR; 另 D 档(已免罪)被当永久有效也不对 (免罪只针对那一次下载)。
  ② **v1.4 的四个决定 (全部按"站点数据权威 + 多实例常态"重排)**:
  (a) **站点侧驱动判定** (§9): partial 站点「是否触发/是否达标」一律看站点侧 —— 清单命中即**触发** (不再看本地 `downloaded`), 达标看档位(B/剩余为 0)优先于本地值、站点字段缺失才降级回本地并标注来源。直接治「转移种子 ⇒ B 的 downloaded=0 被当辅种 ⇒ 不打标不保护」这条漏管; 「纯辅种不触发」保留给非 partial 站点。四消费点调用点仍零改动, 但**语义变了**, 必须用回归钉住。
  (b) **放行有效期取代永久粘性** (§5/§9): 有效期 = `min(下一次成功完整刷新, verified_ts + verified_ttl)`, `verified_ttl` 默认 = `refresh_interval`; 通道正常时每轮刷新自动续期 (收益不减), 只有长期静默才回落保守。下载锚点 (added_on/downloaded/completion_on/progress) **降为辅助**信号 (只提前作废本实例放行), 不再当作放行的充分条件。
  (c) **多实例账号级状态互通** (§5/§6/§7): `role: publisher` 集中核实 + 原子发布 `hr_snapshot.json` (同目录 tmp + os.replace), `consumer` 只读订阅 (不访问站点/不占配额/不写账号级状态), 快照陈旧 ⇒ 放行失效 + 告警; 配额/熔断/已取记录随发布方集中 ⇒ 双倍访问站点风险消失, 扩展只挂 publisher。「同一账号只在一个实例启用」这条不现实约束**取消**。
  (d) **身份判定改只读视图** (§9): 稳定引用 + 内容原子替换 (先例: 搜索索引整体替换引用, Web 线程并发只读安全), record 读时现算三态 + 锚点 —— 取代 v1.2 的「主循环预取写字段 + 置脏」(锚点漂移不置脏, 那种写法会漏更新)。
  ③ 计划改动面: §2/§5/§6/§7/§9/§10/§11/§12/§13 + §14 变更行, 封面与 doc-updated 抬到 26-09-24-1856; §10 新增「转移种子 / 别处下载 / 多实例 / 快照陈旧 / 站点值滞后」五条风险; §12 新增「转移种子 / 放行有效期与锚点 / 共享快照 / 降级路径」四组守阵, 并删掉已作废的「放行粘性」用例; §13 开放问题回到 5 条 (新增部署形态: 谁做 publisher、shared_dir 放哪)。
  ④ 自检: 标签配平 (section 14/14 · table 11/11 · pre 3/3 · ol 2/2 · li 63/63 · div 63/63 · tr 88/88), dark 口径保留; 浏览器实渲染 §5 state 模型块正常; 文中残留「粘性」字样只在 §14 历史行与"修正 v1.3"说明里 (有意保留)。
  下一步: 等用户拍板 5 条 (第 1 条=是否接受装扩展; 第 5 条=publisher 部署形态) → M0 收口。
- **2026-09-24 19:48** — 用户四条指令把方案推进到 **v1.5**: ①「纯辅种不触发似乎是一个 BUG, 非 partial 站点似乎也需要纳入该体系」 ②「hr_channel 收入 hr_check 中」 ③「publisher/consumer 不能覆盖多实例站点配置不同 / publisher 未启用或已退出的情形」 ④ 判定规则: **「带锁访问是安全的关键 (即使有 bug 也不会同时读); 另一实例有锁就等下一轮; 抓数据等几分钟可接受但不能卡主循环; 站点数据分单文件保存、锁也是单文件一个锁; 数据记有效期 —— 有效期内把另一实例的数据当作此次抓取的数据并消耗配额; 主循环不需要管这些, 只向另一线程申请数据更新种子状态」**。
  ① **多实例改为「共享站点数据 + 带锁访问」** (§5 重写): 账号级状态**不进 state_file**, 改为**站点分文件** `<shared_dir>/hr/<site>.json` + **唯一一把锁** `hr.lock` (filelock, 项目直接依赖, `infra/locking.py::SingleInstanceLock` 是现成样板); **取数线程持锁期间完成「读→判有效期→必要时抓→写→释放」全程** (连分钟级抓取也在锁内) ⇒ 即使代码有 bug 也不可能两个实例同时读/写/抓; 拿不到锁**直接等下一轮** (不排队、不重试轰炸); **有效期 = 「本轮已完成」**: 读到效期内的数据即当作本次抓取结果直接采用并**照样记一次配额** (按窗口键幂等) ⇒ 站点访问频率由数据有效期决定, 与实例数/谁抓的无关; **能力即角色**: 只有启用 `channel` 的实例会抓, 无通道实例只读; **写者心跳 + revision 回退自检**锁是否真的生效 (失效 ⇒ 告警 + 退化单实例只读); **合并式写入** (写前必读, 只补自己新增的) ⇒ 各实例站点配置不同也能各抓各的、互不覆盖。publisher/consumer 与 `shared_stale_warn` 随之删除。
  ② **线程模型改三分职责** (§8 重写 + 新图): 扩展 / 端点线程(只入队) / **取数线程**(持锁 + 解析 + 算 infohash + 发布不可变只读视图) / 主循环(只读视图 + state 唯一写者); 主循环读视图**零等待**(原子引用替换), 需要时只 `wake()` 取数线程(非阻塞) —— **绝不与取数线程同步握手** ⇒ 抓取再慢也卡不住 2s 节拍, 完全符合"不能卡主循环"。取数线程**不碰 state_file / 任务队列 / store** (新守阵)。
  ③ **「纯辅种不触发」缺口修掉 + 非 partial 纳入** (§9): 该判断用本地 `downloaded` 近似账号级义务 —— **真辅种**(从未下载过该 tid) 结论碰巧对, **转移/重加/换客户端的保种副本**(downloaded=0 但账号欠 HR) 则**漏管**。⇒ `mode: all` 语义从「全站按 HR + 本地下载量触发」升级为「站点侧驱动 + 未核实默认受管束」, 与 `partial` 的唯一差别只剩未核实的默认值; 真辅种改由「完整核实 + 清单未命中 ⇒ 安全放行」给出同一结论。**零静默变更**: 只有配了 `hr_check` 段的站点走新语义, 也不全局改 `check_hr_condition` (未接入站点行为不变)。
  ④ **`hr_channel` 并入 `hr_check.channel`** (§7): 已核对 `config/impact.py` —— 它只按**顶层键**查 `SECTION_LEVELS` (只有 `trackers` 有逐字段特判), 所以合并后 `channel.*`(端口/token) 会被误判成 L0 而实际需重挂端点 ⇒ 必须在计划里写明**补一张 `HR_CHECK_FIELD_LEVELS` 内部字段表**(仿 `TRACKER_FIELD_LEVELS`), 这是合并的唯一代价。新增 `shared_dir` / `lock_timeout`。
  ⑤ 自检: 标签配平 (section 14/14 · svg 1/1 · figure 1/1 · table 11/11 · pre 4/4 · div 64/64 · tr 94/94), dark 口径保留; 浏览器实渲染 §8 新数据流图正常。过程中又踩一次"替换片段只盖到起始标记 ⇒ 旧 SVG 整块残留"(已按 `pitfalls/docs/html-edit.md` 的计数机检当场拦下并清除)。
  下一步: 等用户拍板 5 条 (第 1 条=是否接受装扩展; 第 5 条=shared_dir 放哪 + 哪台启用 channel + 实测 filelock 互斥) → M0 收口。
- **2026-09-24 19:59** — 用户两条澄清把方案推进到 **v1.6**: ①「锁单文件一个锁」= **每个站点一个数据文件一把锁** (减小数据更新延迟) ②「HR 通常按小时甚至天计算, 没必要每 tick 更新, 且更新只在数据更新时发生」。
  ① **锁粒度改为站点** (§2/§5/§8 SVG/§10/§11/§12/§13 + 封面): `<shared_dir>/hr/<site>.lock`, 一站一锁 (不再全局 `hr.lock`) ⇒ 抓站点 A 不阻塞站点 B, **数据更新延迟随站点切分下降**; 同站点仍严格互斥 (「持锁期间完成读→判有效期→抓→写→释放」全程不变, 安全性不降级)。副作用是好的: **跨站点天然无覆盖问题** (每实例只写自己的站点文件), 原先的「合并式写入防抹掉其它站点」收窄为「站点内读-改-写」(仍防同站已有条目丢失)。§10 锁竞争风险行从「另一实例本轮不干活」改为「该站点本轮不干活, 其它站点不受影响」; §13 实测项不变 (仍是「filelock 在该共享目录上是否真互斥」)。
  ② **节奏与 tick 解耦 + 只在数据变化时更新** (§5/§7/§8/§12): HR 粒度是小时~天 ⇒ 取数线程按**自己的定时器** `poll_interval` (新配置键, 默认 `1M`) 自醒检查「哪个站点过期/需抓」, **不随主循环 2s tick 跑**; 视图只在**数据实质变化** (抓取成功 / 熔断进入退出 / 通道状态翻转) 时才抬 `revision` 并原子发布 ⇒ **主循环每 tick 只做一次版本号比较, `revision` 没变就零工作** (满足"更新只在数据更新时发生", 同时保住"抓取再慢也卡不住主循环")。**时间敏感判定在读取时现算** (`now` vs `expires_at`): 「过期」只是读时结论, 不为时间流逝重发布视图。§12 新增守阵: 版本未变 ⇒ 不更新任何 record / 读取时过期现算 / 锁粒度=站点 (并发两站可同时进) / 取数线程不随 tick 唤醒。
  ③ 自检: 标签配平 (section 14/14 · svg 1/1 · figure 1/1 · table 11/11 · pre 4/4 · li 65/65 · div 64/64 · tr 95/95), dark 口径保留; 全文 `hr.lock` 字样仅剩 §14 v1.5 历史行 (有意保留, 由 v1.6 行说明修正); 浏览器实渲染 §5「多实例: 共享站点数据」块正常。
  ④ 本档回写时踩到一条新坑: 改 `**Updated:**` 的替换片段顺手带上了下一行 `**Summary:**` 标签, 把标签静默删掉 (md 无边标签 ⇒ 机检不报)。已当场回读修回, 并按动作记进 `pitfalls/docs/md-edit.md` (同类坑的 md 版; 顺手把 `html-edit.md` 里过期的计数示例校正为现值)。收尾 `kb.index` + `kb.check` 过, 全量 **1224 passed + 1 skipped / 8.56s** (与单点 baseline 的 1225 collected 一致; 本轮只动文档未加测试, 不改基线)。
  下一步: 等用户拍板 5 条 (第 1 条=是否接受装扩展; 第 5 条=shared_dir 放哪 + 哪台启用 channel + 实测 filelock 互斥) → M0 收口。
- **2026-09-24 20:09** — 用户把 5 项前置决策全部拍板 (另追问「channel 不应该都启用吗」) ⇒ 计划升 **v1.7** (定稿, 无待拍板项)。
  ① 决策: **接受装扩展** (unpacked 自用即可, 不必上商店; CDP 专用 profile 降为应急不排期) / **首站 BTSchool**, 页面数据实施时由用户提供 (已有 `myhr.php` 样张可开工) / **频度按推荐** (90S·12 每时·60 每天, 站点级独立) / **`unknown_policy=hr` + `verified_ttl=refresh_interval`** / **`shared_dir` 默认数据目录** (多实例由用户决定是否改共享目录)。§13 由「开放问题」改写为**决策记录表 + M0 实测清单** (4 项实测: download URL 形态 / BTSchool scope 与分页判据 / 后台标签页观感 / 共享目录 filelock 互斥), 封面状态改「决策齐备 · 待开工」, M1 写明首站与页面样本来源。
  ② **channel 改为「推荐都启用」** (§5/§6/§10/§11/§12): 用户问得对 —— 抓取能力的硬边界不是「名额」而是**本机有没有装扩展的浏览器**: 端点只听 `127.0.0.1`, 浏览器只能连本机 loopback, 所以**跨机器**的实例配了也驱动不了 (只能只读共享数据); 反过来凡是本机有浏览器的实例都该开 ⇒ ① 消掉「唯一能抓的那台退出 ⇒ 抓取能力消失」的单点故障 ② 站点配在哪台哪台自己能抓 ③ 多通道**不会**双倍访问站点 (同站点靠锁 + 有效期复用, 谁先拿到锁谁抓, 另一个复用并记一次配额)。扩展侧因此新增**实例端点列表** (`[{name, endpoint, token}]`, `chrome.alarms` 逐个拉 ⇒ 一个浏览器可服务同机多实例); §10 新增「同机多实例端口/token 撞车」风险行 (端口被占启动即 fail-fast; token 打错 ⇒ 401)。
  ③ **多实例部署引导** (§7 新增 note): `shared_dir` 留空 = `<data_dir>/hr/` 为默认; 程序**无法可靠判断「我是不是多实例」** ⇒ **只引导不强求** (功能开启且留空时记一条 INFO 提示, 不阻断启动, 由用户决定是否配置); 配套用户文档 + `hr.once` 顺带打印实际路径与锁自检 (M2 加)。
  ④ 自检: 标签配平 (section 14/14 · svg 1/1 · figure 1/1 · table 12/12 · pre 4/4 · tr 104/104 · td 265/265 · th 37/37 · p 48/48 · strong 363/363 · code 394/394), dark 口径保留; 浏览器实渲染 §13 决策表 + M0 实测清单正常。过程中 3 处手误当场被拦: 替换时误插了一个反引号、两处「跨机器」写成「跳机器」、§14 v1.7 行因 `old` 漏了 `</strong>` 首次替换失败 (重做)。
  下一步: **M1 可开工** (首站 BTSchool 离线管道, 不需要浏览器); M0 四项实测可与 M1/M2 并行。
- **2026-09-24 20:15** — 用户: 「文档经过多轮修改可能已有飘移, 最后更新一下文档」⇒ 计划升 **v1.8 (纯文档, 无设计变更)**, 逐节回扫清漂移:
  ① <strong>删矛盾表</strong>: §6 里还留着 **v1.1 的 cookie 分层方案表** (A 手工导入「M1 落地」/ B CDP「M4 落地·推荐目标形态」/ C 扩展「备选不排期」) —— 与现行「扩展主选 / 手工导入否决 / CDP 不排期」**直接矛盾**, 整表删除 (同类对比已由上一张 v1.2 通道表覆盖)。
  ② <strong>旧路径</strong>: §1 `mixins/web_view.py` → `webui/views.py` (v1.2 已更正但 §1 漏改)。
  ③ <strong>旧落点</strong>: §3 `state.hr_index` → 站点文件里的 `hr_index` (v1.5 已把账号级状态移出 `state_file`)。
  ④ <strong>旧口径</strong>: §4 流量字段「决策以 qB 本地值为准」→ 站点侧优先、本地兜底 (§9 自 v1.4 起已是站点侧权威)。
  ⑤ <strong>旧待办/旧措辞</strong>: §5 bencode「M0 拍板」→ 已定自写; §11 M0 「依赖: 开放问题拍板」→ 依赖无、可与 M1/M2 并行; 实验脚本 ±25% 抖动加注「正式实现只向上」; §2「许可令牌整体作废」补明取数线程 v1.5 以新职责回来。
  ⑥ <strong>旧角色</strong>: §9 判定表删「consumer 侧」行 (publisher/consumer 已于 v1.5 删除) → 改「本实例无通道且共享数据已过期」。
  ⑦ <strong>mode 语义补齐</strong>: §7 配置注释补 `all` 三态语义; §9 硬约束与判定表把「partial ⇒ hr 段必填」放宽为 **`mode != off` ⇒ hr 段必填** (`all` 站点同需参数); §9 未核实态补「`mode: all` 恒受管束」; §2/§13「partial 站点」→「接入 `hr_check` 的站点」。
  ⑧ 导航/措辞: 目录与节注释 §13「开放问题」→「决策记录」; CSS 注释「粘性目录」→「吸顶目录」(避开已废弃的「放行粘性」撞词)。
  ⑨ 自检: 标签配平 (section 14/14 · table 11/11 (删表后 -1) · svg/figure/pre/ul/ol/li/div/tr 均配平 · td 248/248 · th 32/32), 目录锚点 14 = 节数 14, dark 口径保留; 浏览器实渲染 §6 (删表处) 与 §13 正常; 漂移关键词终扫: `web_view`/`state.hr_index`/`consumer`/`开放问题` 仅存于 §14 历史行 (有意保留)。
  下一步: 仍为 **M1 可开工** (首站 BTSchool); 本轮不动代码, 不建 issue。
- **2026-09-22 22:32** — 用户补充 HR 页字段与防重下要求 ⇒ 计划升 v1.1: 索引改 (站点, tid) 主键 + infohash 回填; 新增 `hr_downloaded` 永久已下载层与 `hr_dl_fails` 重试记账 (新配置键 `max_download_retries`); 反查键 (站点, infohash) 跨站独立; 进度字段「展示/交叉核对, 判定以 qB 本地值为准」; 原开放问题「页面是否给要求值」解决, 新增「进度字段用途边界」, 余 4 条待拍板。

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
  扩展 README 排障表增同义一行; 新坑 [pitfalls/ops/alert-levels.md](../../pitfalls/ops/alert-levels.md)(判据=「故障
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
  坑入库: 新增 [pitfalls/web-ui/extension-bridge.md](../../pitfalls/web-ui/extension-bridge.md);
  [pitfalls/ops/console-encoding.md](../../pitfalls/ops/console-encoding.md) 补“反向子进程解码(node 输出 UTF-8 而 `text=True` 按 locale 解 ⇒ 直接抛)”。
  全量 **1475 passed + 1 skipped**; 基线已回写。下一步仍为 **M3 判定联动**(门面已备好)与 M0 真机实测。

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
  [pitfalls/ops/alert-levels.md](../../pitfalls/ops/alert-levels.md)(扩写为四条判据 + 两个同族旧账)已回写, 基线已更新。
  ⑦ **顺带发现但未动(待你定)**: `service._do_fetch` 的取数失败分支 `session.commit()` **没看 `self.persist`**
  ⇒ `--hr-once` 声称「不写文件」但取数失败时会写熔断计数, 与文档承诺不符。
  下一步仍是 **M3 判定联动**; 另两个待定: `config.yml` 明文凭据入池 / README 里一个坏 emoji。
