# 测试基线 · 变更流水

> 摘要: 测试基线的**逐次增量流水**(最近在上), 每次增删用例都记一条 —— 用来回答"这个数字是怎么来的"。
> 触发: 基线为什么是这个数, 某条用例何时加的, 覆盖率变化, 历史增量

> 迁移说明(2026-09-22 W3): 本节原在 `testing.md` 顶部的 ```bash 围栏里当注释, 现原样外迁 ——
> **只把 bash 注释标记转成 markdown 列表缩进**(内容逐字未改)。**当前数字**见 [baseline.md](baseline.md)。

> **更早的流水已外迁** → [attachments/baseline-history-archive.md](attachments/baseline-history-archive.md)
> (append-only 流水触顶时的处置: 从最老一端切到本文件 ≤ 16,000 字符, 原位留本行指针;
> 最近一次轮转: 2026-09-26 触顶 24,000, 外迁最老 1 条(添加种子回执轮, 相对链接已按 attachments/ 重写);
> 2026-09-25 曾触顶外迁最老 17 条)

- ↑ **耗时采样归档**(2026-09-26 轮转: baseline.md 触 evergreen cap 10,000, 把 2026-09-24/25 的"更早"耗时段从
  baseline.md 切到此处; 当前基线只留区间结论): 禁令解除回写 19.5 / 18.5s(2 failed 为当时已记载的 GBK 假红,
  已随 a760da0 修复)· v2.8 明细表改版 18.3 / 18.7 / 19.1s · v2.6/v2.7 通道时序 + 增量落盘 / M4 多站点
  19.3 / 20.0 / 21.7s 与 18.1 / 18.1 / 19.2s(⚠ 扩展守阵真跑 node —— 一次运行覆盖四个场景 + 登录页场景各一次
  —— 耗时比 M1 末态高约 5s, 属预期的环境成本; ⚠ M2 用例含真回环 socket、线程启停与「等扩展回传」场景 ⇒
  整体比 M1 末态 ~9s 慢约一倍, 其中一处 10s 级浪费是**真缺陷**: 关停时线程正阻塞等扩展回传白等到
  `request_timeout`, 已修为「先叫停队列再 join」并有 `test_stop_is_prompt_while_waiting_for_extension` 守死)·
  GBK 回退修复 14.3 / 20.9 / 21.2s · 扩展运行日志 17.6 / 19.8 / 19.9 / 20.5s · 2026-09-24 告警分档 +
  `--hr-status` 并行 16.88–21.40s / 串行 30.93s。

> **2026-09-26 自 baseline.md 迁出**(合流去重时让位给新条目; 2026-09-25 各轮状态快照, 内容照旧):

- **1617 collected: 1616 passed + 1 skipped** —— 2026-09-25 **示例配置守阵**(`pitfalls/docs/drift.md`
  根治 follow-up): +2 条(test_config.py) —— minimal.yml 与 docker/config.example.yml 过 fail-fast 校验,
  并分别钉 README 开箱语义与容器契约字段; minimal 守阵**红验过**。TOTAL **91%**(10924 语句 / 785 未覆盖 /
  3622 分支 / 326 partial)。
- **1618 collected: 1617 passed + 1 skipped**(clone3 中间态, 已被合流重测覆盖) —— 2026-09-25 HR
  `/api/hr/sites` + 站点勾选授权(+7 条, 明细见档案 v3.1)。
- **1611 collected: 1610 passed + 1 skipped / Windows** —— 2026-09-25 **full-checking 首样本竞态修复**
  (切片 `26-09-25-2348-full-checking-verdict-fix`, 取证报告
  [26-09-25-0853-report-full-checking-verdict-poison](../reports/26-09-25-0853-report-full-checking-verdict-poison.html))。**+3 条**:
  首样本竞态回归 / 启动宽限保险丝(`CHECK_START_GIVEUP`) / 1.6 假失败自愈; 另改造 3 条相关用例。
- **1615 collected: 1614 passed + 1 skipped**(clone3, 合并远端 1610 之前的旧基座实测) —— 2026-09-25
  **HR 扩展配置简化(端点 /api/hr/sites + 站点勾选授权)** + `test_extension_proxy.py` 2 条 +
  `test_hr_runtime.py::test_site_origins_served_live_for_extension`。落地面: 只读 `GET /api/hr/sites`
  + 扩展选项页三模板表单 / 站点权限拉清单勾选 + 一键申请。TOTAL **91%**(10920 语句 / 792 未覆盖 /
  3626 分支 / 327 partial)。
- **1608 collected: 1607 passed + 1 skipped** —— 2026-09-25 **WEB UI 展开态跨视图记忆**(切片
  `26-09-25-1835-webui-expand-state-across-views`)。**+1 条**
  `test_frontend_expand_state_survives_view_switch`(切视图不得置空展开态, 还回前必须验行还在);
  同轮压回 `pitfalls/testing/tmpdir.md` 超 cap 并修掉一处控制字符乱码。
- **1607 collected: 1606 passed + 1 skipped** —— 2026-09-25 **HR 删除安全档位 WEB UI 呈现落地**
  (计划 `26-09-25-1823-plan-webui-hr-safety-display`, 档案 `26-09-25-webui-hr-safety-display`)。**+4 条**:
  `test_hr_resolve.py` safety_display 三档位派生 3 条(站点档位即结论 / 身份层 / judged None 回落) +
  `test_web.py::test_frontend_hr_safety_wiring` 前端接线守阵(token 映射表逐字一致 / 做种时长列 6 处换绑 /
  新样式两套 CSS 成对 / `m.hr_*` 字段 ⊆ `_hr_view_fields` 键集); 另扩 `test_hr_view_fields_three_state`
  与 `_scan_filter_facets` 同查 `hrSrcOptions`。落地面: `hr/resolve.py::safety_display` 派生单点 +
  `views.py` 透出三字段(退役二值 `hr_satisfied_src`); 前端做种时长列按档位着色 + 来源徽标 + 悬停全文、
  删除确认框点名、H&R 筛选两档→四档 + 来源副筛选、批量条「含 N 个不能删」。
  TOTAL **91%**(10991 语句 / 791 未覆盖 / 3612 分支 / 327 partial; resolve.py 98% / views.py 97%);
  双 UI 浏览器冒烟 **94 项全过 0 失败**(桩服务 1500 种子)。
- **1602 collected: 1601 passed + 1 skipped** —— 2026-09-25 **HR v3.0 达标判定来源优先级**: +2 守阵 +
  改写 1, **3 条红验全红**; `satisfied_verdict` 改**档位即结论**(A 考察中/C 未达标 ⇒ False, B ⇒ True) +
  `judge_record` 双命中按档位序取; 动机见计划 v3.0 §9/§12/§14 与档案 `26-09-22-backend-partial-hr-verify`。
- **1601 collected: 1600 passed + 1 skipped** —— 2026-09-25 **两线合一**: HR 超龄豁免(develop, **+17 条**:
  判定收口 7 + 取数侧过滤/早停 8 + 门面透传 1 + 配置解析 1; 新键 `completed_age_limit`) 并入 GBK 修复/
  搜索分隔符(master, **+2 条**); 同日 DND 拖拽 / 右键次级菜单 / UI 位置持久化各 +1(1597→1600 链)。
  TOTAL **91%**(10950 语句 / 791 未覆盖 / 3594 分支 / 326 partial —— 并行采样; **HR 包 93%**: 2814 / 147 /
  774 / 93), sidefx 台账并行汇总 / **越界 0**。

- ↑ 收集数 **1598 → 1599**(**+1**; 2026-09-24/25 **WEB UI 右键次级菜单三条 CTX-04/05/06**):
  `test_web.py::test_frontend_ctx_submenu_single_entry_and_hover_close` —— 用户报 ①二级菜单图标
  hover 变灰 ②二级菜单移出不消失 ③「复制」二级菜单移入「更多操作」。
  ①是两层叠加: `.ctx-item:hover .ico` 是**后代**选择器而 `.ctx-sub` 是父项 DOM 后代 ⇒ hover 父项把
  **整个子面板**的图标刷成 `--fg-muted`; 且只加 `>` 不够(hover 规则 0,3,0 压过语义色 0,2,0)⇒ 终解
  `.ctx-item:where(:hover) > .ico`(`>` 限直接子级 + `:where()` 把 `:hover` 特异性压到 0, 按源码顺序让位)。
  ②收起挂**父项** `mouseleave` 延迟 180ms(`scheduleSubClose`/`keepSub`; 面板上再挂一条会在
  "从面板回到父项"时误收; 延迟只为跨过 `.ctx-sub` 的 4px 缝隙)。③复制族并入「更多操作」末尾,
  一级 `has-sub` 2 → 1 个。冒烟 `scripts/ui_smoke.cjs` **+8 条**(双 UI × 四), 已对 HEAD 红验;
  冒烟 84 → **92 项 0 失败**(单 UI 各 46)。⚠ 本轮与主线 10 个提交合流(两边 `test_web.py` 同一位置
  各加一个测试 ⇒ `--3way` 冲突, 取并集; `_doc-map.md` 是生成物, 取主线版后重跑 `kb.index`),
  基线数字取**合流后实测**: **1599 passed + 1 skipped / 0 failed**(本 shell 的 GBK 假红已由主线
  `a760da0` 修掉, 不再需要 `env -u PYTHONUTF8`)。

- ↑ 收集数 **1579 → 1596**(**+17**; 2026-09-25 **HR 超龄豁免: 判定侧豁免 + 翻页早停**): 用户新需求
  「完成时间超过一定期限(如一年)的种子不再验证 HR、也不再翻页」。新站点级键
  `trackers.<站>.hr_check.completed_age_limit`(0=关闭, 默认行为不变): 判定收口 `judge_record`
  对完成时刻超线的种子直接给第四态 `EXEMPT`(压过清单命中, 排在「无可查键回落本地」之前);
  取数侧超龄行不入索引/不回填(省 .torrent 配额), 整页超龄且页内+跨页呈完成时间倒序才允许早停
  (倒序证据不成立就继续翻 —— 错误方向只是多花配额, 不是漏判)。新增判定 7 + 取数 8 + 门面 1 +
  配置 1 = 17 条, 红验 10 条全红后还原。TOTAL **91%**(10849 / 791 / 3598 / 327)。

- ↑ 收集数 **1579 → 1580**(+1)、失败 **2 → 0**(2026-09-25 **commands 引擎 GBK 回退修复**): 注入
  `PYTHONUTF8=1` 的本工具 shell 里, `test_commands_engine` 两条 GBK 码页守阵恒红(2026-09-24 起记载为
  "已知假红, `env -u` 转绿")。本轮红验推翻"纯环境差异"定性: `PYTHONUTF8` 只影响 Python 解释器,
  原生子进程仍按 ANSI 码页输出 ⇒ UTF-8 模式下引擎码页回退**真失效**(回退链退化, 中文静默变 U+FFFD)。
  修三件: 引擎 `_local_codepage` 改 `ctypes GetACP`(win32); 两条守阵钉缝(monkeypatch `_local_codepage`
  → cp936, GBK 字节在 cp1252 下也能"解成功"成乱码, 不钉缝在非中文环境照样红); 新增防回潮守阵
  `test_local_codepage_ignores_utf8_mode`(打回旧写法立即红)。
  TOTAL **91%**(10809 / 789 / 3582 / 326 —— 语句 10905 → 10809 随快进合并 fda13cd → 1516bd6 的 20 个
  主线提交而来, 非本轮所致)。详见 [pitfalls/testing/patching.md](../pitfalls/testing/patching.md)。

- ↑ 收集数 **1576 → 1579**(**+3**; 2026-09-25 **扩展运行日志: 分级 + 环形上限 + 选项页④区**): 用户要求扩展
  加日志 —— 条数可设 10–10000(默认 1000, 环形丢最旧)、四级 debug/info/warn/error(记录阈值默认 info +
  选项页分级过滤)、明细含毫秒时间 / 收到的命令 / 请求类型与站点 / HTTP 结果 / 耗时 / 字节数 / 回传后端响应体
  快照。MV3 SW 随时被回收 ⇒ 唯一事实源 `chrome.storage.local`(内存环形缓冲 + 防抖整份写回)。新增
  `test_extension_proxy.py` 3 条: logger 行为(真跑)1 + 选项页日志面接线 1 + 轮询周期文案↔`POLL_MINUTES`
  防漂 1。守阵真跑当场抓到 flush 链**自引用死锁**(首刷即死锁且无报错, 已修并入坑
  `pitfalls/web-ui/extension-bridge.md`); 顺带修选项页轮询周期文案漂移(停在"每 5 分钟", 实际 1 分钟)。
  TOTAL **91%** 不变(10905 / 789 / 3582 / 327, 无 .py 源码变更)。档案 `26-09-25-webui-ext-hr-logging`。

- ↑ 收集数 **1574 → 1576**(**+2**; 2026-09-25 **v2.8 取证误读修复: 明细表改版 + 逐文件 ts**): 用户拿
  BTSchool 站点文件取证「是否短时间大量下载」(结论: 无 —— 当天 5 次请求 = 3 页 + 2 个 .torrent, 全在频控内),
  顺带点出 `hr_downloaded[].ts` 整批共用开始时刻(同批微秒级相同 ⇒ 误读为瞬间批量下载)与明细「剩余达标」列
  被读成还需做种(9d21h 实为考核窗口, 还需做种仅 16h57m)。修: ts 改记各 .torrent 自己的取回时刻;
  明细列 = tid/档位(考察中等人话)/上传量/下载量/分享率/还需做种(镜像站点 HH:MM:SS 形态)/名称
  (显示格宽截断)/infohash, CJK 双宽对齐走自写 `_dwidth/_pad`, 剩余达标不显示。新增 `test_hr_service.py` 1 +
  `test_hr_report.py` 1。TOTAL 91%(10905/789/3582/327; HR 包 93%: 2782/143/766/91)。

- ↑ 收集数 **1573 → 1574**(**+1**; 2026-09-25 **v2.7 增量落盘**): 用户删数据重启实测「后端无落盘,
  Ctrl+C 后才落盘」—— v2.6 修好后一轮跨多个扩展轮询周期(分钟级、持锁进行), 落盘只在轮尾 ⇒ 中途
  Ctrl+C/断电丢已抓页面与配额账本。修: 每抓到一页(complete=False 语义合并)与每个 .torrent 结果
  (hr_downloaded 凭据 / fails 记账)当场提交, 轮尾仍完整合并 + 写覆盖证明; 叫停备注改「下载阶段被叫停」
  (叫停可能打在派发前的间隔睡眠上)。新增 `test_hr_service.py` 1 条, ★红验 1(关增量提交 ⇒ 红)。
  TOTAL 91%(10881/788/3578/324; HR 包 93%)。

- ↑ 收集数 **1562 → 1573**(**+11**; 2026-09-25 **v2.6 通道时序与饿死残留修复**):
  「种子下载不触发」审查实报 —— 主因是**扩展轮询 5 分钟 vs 后端 request_timeout 180s** 的时序错配
  (每条任务约四成概率超时: 烧配额 + 计失败 ⇒ 3 次页面失败 = 12h 熔断)。① 扩展 `POLL_MINUTES` 5 → 1、
  `DEFAULT_POLL_HINT` 300 → 60; ② 不完备刷新有效期 60s → `max(120s, 2×poll)`(旧窗口与 poll 相同 ⇒
  复用轮「只补下载」从不发生 —— 下一轮永远晚一个 ε); ③ 页面取数失败后仍补一次下载
  (`_backfill_on_page_failure`, 待回填来自已持久化索引); ④ 下载阶段让位/人工事件(叫停/扩展硬上限/登录页)
  原样上抛不再计成 tid 失败(旧实现被 `except HrFetchError` 吞掉 ⇒ 关停三次 = 12h 冷却);
  ⑤ 扩展 fetchBinary 登录页检测(`kind=login-page` ⇒ `HrLoginExpired`, SameSite 剥 cookie 实测风险);
  ⑥ Retry-After 以 cooldown 封顶; ⑦ 配额展示按窗口键折算(修「本小时 7/12 · 还能取 12 次」自相矛盾)。
  新增: `test_hr_service.py` 7(窗口 3 + 页面失败补下载 1 + 下载阶段让位 3)· `test_hr_fetcher_channel.py` 1 ·
  `test_hr_ratelimit.py` 1 · `test_hr_report.py` 1 · `test_extension_proxy.py` 1(真跑 node)。
  ★红验 7 条(临时还原旧实现全红, 还原后全绿)。TOTAL 91%(10872/788/3574/325; HR 包 93%)。

- ↑ 收集数 **1542 → 1562**(**+20**; 2026-09-25 **M4 多站点与打磨**):
  四块一起交付 —— ① **四类事件语文化**: 新 `hr/events.py` 是告警文案的**单点**(带标签前缀
  `[HR 登录失效]` / `[HR 熔断]` / `[HR 页面改版]` / `[HR 通道静默]`, 用户可 grep), 并把**登录失效从熔断里摘出来**
  (新 `HrLoginExpired` ⇒ 不计失败、不推熔断, 只报一次并给动作「去浏览器登录哪个站点」; 重试无用, 计成故障
  会把「去登录」掩盖成「站点坏了」而且熔断冷却会让人登录完白等; 原因仍写进站点文件 `refresh.reason` ⇒
  `--hr-status` 与界面都看得到, **但绝不碰** fetched_at / 覆盖证明 / 新鲜度基准) · 通道静默告警补上**受影响站点**。
  ② **站点级状态单一事实源**: 新 `hr/status.py::site_status()` —— CLI 报告与 WebUI 看的是**同一套数**
  (含新派生量: 下次刷新时刻 / 回填进度比例 / 「现在为什么不放行」), `report.py` 改为消费它(文本口径逐字未变)。
  ③ **WebUI 出口**: 新只读端点 `GET /api/hr/status` + 设置页「**HR 站点状态**」章节(经典与 Console Hub 两个入口,
  两套 UI 成对) —— 数据新鲜度 / 索引进度 / 配额熔断 / 挡路原因一眼可见; 并加**前端字段一致性守阵**
  (扫模板引用的字段 ⊆ 后端快照键, 防"字段名打错 = 整段静默空白")。④ **多站点**: 新 `tests/test_hr_multisite.py`
  5 条钉死「第二站点只改配置」与站点隔离(配额/熔断/锁/索引/已取记录都不串味); `docs/configuration.md` 补
  「接第二个站点要做什么」+ 四类事件标签表, 根 README 更新 M4 状态。★红验: 字段守阵(改错名 ⇒ 红)。
  本条目实测 **1561 passed + 1 skipped**(TOTAL 91% / 10831 / 786 / 3556 / 321, 并行 18.1 / 18.1 / 19.2s)。
- ↑ 收集数 **1526 → 1542**(**+15**; 2026-09-25 **HR 取数实报修复 + 扩展侧硬上限**):
  用户贴 `--hr-status` + 站点文件报「种子似乎没有下载成功」⇒ 三个真缺陷(扩展无责: 只被派了一个页面任务):
  ①下载被页面饿死(`_Budget` 门槛是「相邻两次**请求**」而页面永远排前面; 修法: 复用轮只补下载)
  ②生产路径不等间隔(计划 §8 本意是锁内等满; 不等待 ⇒ 一次刷新只能发第一个请求, `complete` 永不成立)
  ③无可用索引键 ⇒ 整站种子按 `unknown_policy=hr` 打标(修法: 无键时 `judge_record` 返回 None 回落本地);
  另加**扩展侧硬上限**(第二道闸: 访问 10/时·50/天, 下种 50/时·200/天, 超限拒发 + `kind=ext-quota`
  ⇒ 后端 ACTION_WAITING 让位, 不计失败不推熔断)。新增 15 条(服务 6 · 判定 1 · 协议 2 · 门面 3 · 扩展 3),
  ★红验 4 处。本条与对方「运行日志按等级查看修复」并行开发 ⇒ 合流后实测 **1541 passed + 1 skipped**
  (总账以 baseline.md 顶部为准)。
- ↑ 收集数 **1377 → 1384**(**+7**; 2026-09-25 **运行日志按等级查看修复**); ⚠ 与下方 M2/M3 两批**并行开发**, 本条在合流前旧基上实测(未含 M2/M3 用例), 合流后总账以 baseline.md 顶部为准):
  用户报"新版设置里运行日志选 WARNING 显示『日志文件暂无内容』"。根因: `/api/log` 的等级过滤按
  **字面量** `f"[{lv}" in ln` 捞, 锚死默认格式的方括号; 生产 `config.yml` 的 `log.format` 是
  `%(asctime)s - %(levelname)s - %(message)s`(无方括号)⇒ 选任何等级恒空, 且与"确实没有该等级日志"
  完全同形(不报错、不返回 None)。修法: 新增 `infra/logging.py::filter_log_lines()` —— 按**配置的
  format 反推** `%(levelname)s` 位置编正则(字面量空格**不放宽**成 `\s*`: 放宽会让前一个纯字母字段把
  等级名吃掉, 实测 `%(name)s %(levelname)s` 下 `core` 被当成等级; **要吸收**字段宽度补的空格:
  `%(levelname)-8s` 在等级名后补空格, 漏了则该格式一行都对不上), 多行记录(traceback)折行跟随上一条的
  取舍; 两种"筛不了"(格式无等级字段 / 已存行与当前格式不符)回**全部行 + `note` 提示语**, 前端两套 UI
  两处日志章节成对加提示条。用例: `test_logging.py` +4(格式形状矩阵 / 多行记录 / 提示语 / 字段宽度与
  `%%` 变体) + `test_web.py` +3(生产格式 / 多行 traceback / note); **旧 `test_api_log_endpoint` 重写** ——
  它手写 `[INFO]` 语料而替身 format 是 `%(message)s` ⇒ **配置没被读到, 摆设断言**(旧实现下绿、真机恒空
  它也绿)。**红验**: 临时还原旧字面量实现 ⇒ 7 条新用例全红。端到端(真机 `setup_logging` + 真实
  `exc_info` traceback, 生产 format): 全部 8 行 / INFO 2 / WARNING 1 / ERROR 5(整段栈保留)。
  冒烟 82 项 0 失败 + 专项浏览器验证 18 项 0 失败(双 UI × 新版/经典 × 双格式)。
  本轮另踩两坑(均已入库): 手工跑子集把 cmd.exe 的 `set "TMPDIR=..."` 照搬进 Git Bash ⇒ TMPDIR 没导出
  (tmpdir.md 复发 2); `test_commands_engine.py` 两条 GBK 守阵在本 shell 恒红 = `PYTHONUTF8=1` 注入
  (patching.md 已有记载), `env -u` 后全绿, 非回归。详见
  `tasks/26-09-25-webui-log-level-filter.md` 与 `pitfalls/backend/format-driven-parse.md`。



- ↑ 收集数 **1504 → 1520**(**+16**; 2026-09-25 **M3 判定联动**):
  三态判定接进 `TorrentRecord` —— 记录侧只加 `hr_link`(判定桥 = `QbManager.hr` 门面的**稳定引用**,
  由 `TorrentStore` 在记录构建/变更时挂上)/ `hr_judgement()` / `hr_anchor()`, 而 `check_hr_condition` 与
  `check_hr_satisfied` 改成「站点侧优先、站点没给再回落本地」⇒ **四个消费点(打标 / WebUI 视图 / `hr` 规则条件 /
  `tor.hr_*` 表达式)调用点一行未动**; 判定收口在 `hr/resolve.py::judge_record`(多 infohash 取更保守者 +
  `HrJudgement` / `HrSiteFacts`), 门面入口 `HrRuntime.judge()`; `mode: all` 升为站点侧驱动(未核实恒受管束);
  `manager._hr_anchors()` 按站点给出 `{infohash: HrAnchor}`; WebUI 透出三态/依据/达标来源 + 站点侧值。
  新增用例 16 条(收口判定 7 · 门面 3 · 记录接入 4 · 锚点 1 · WebUI 1) —— 收集数 1504 → 1520。
  ★红验 2 处反证(旁路判定桥 / 站点未接入返回判定) ⇒ 4 条守阵变红, 回滚后 89 绿。
  全量 **1519 passed + 1 skipped** / TOTAL 91%(10534 / 779 / 3494 / 310~311) / sidefx ≈2447 / 越界 0。
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
