# 26-09-22-backend-partial-hr-verify — 进度纪要(外迁存档)

> 摘要: 任务档案「进度日志」段**早期纪要**的外迁存档(该段触 `TASK_LOG_CAP` 上限后按策略切出, 原样未改)。
> 触发: 早期进度, 计划为何改成这样, v1.2-v1.9 决策过程, 需求逐轮澄清

本文件是 [../26-09-22-backend-partial-hr-verify.md](../26-09-22-backend-partial-hr-verify.md) 的附件;
最近的纪要仍在档案本体里。以下按原顺序(最近在上)。

- **2026-09-29 (复审落地: 骤降保护移除 + 复审缺陷 H1/M1/M2 修复)** — 全面复审
  (reports/26-09-29-0404)后按用户裁决实施四项: ①**骤降保护移除**(裁决: 流转守恒是骤降的升级版,
  A 只流向 B/C/D, 骤降不构成漏 HR 面; 基线高水位永不回落会在站点合法清账后永久冻结批量签发) ——
  service/model(`HrWaveMeta.plunge/baseline_rows` 删除, hr_site 迁移不再产出, 读侧对旧键容忍不 bump
  schema)/status/events/report/WebUI/configuration.md 全链清理, 防伪收敛为「守恒 + 零行戳」两道;
  ②**H1**: Retry-After 指令落盘(`_do_wave` 分支 commit + mark; .torrent 下载路径带 retry_after
  上抛波级, 不再计成种子失败) —— 修复前 hold() 每波重读盘导致指令跨波即丢, 60s 节奏重试到日额烧尽;
  ③**M1**: 登录失效路径 `budget.mark()` 前进间隔基准(修复前每 poll 立即重发烧日额); ④**M2**: 站点
  文件 schema 比程序新(`HrLockSession.version_mismatch`)时跳过取数与写盘(修复前空壳数据照常跑波
  覆写新版文件)。测试: FakeFetcher 扩展 login_at/retry_after_at/retry_bytes_at; 骤降用例删除;
  test_light_wave_when_no_objects 重写为 test_no_objects_sweeps_to_last_page(钉裁决行为 —— 旧用例
  名不符实, 断言靠 fixture 缺页报错凑成); 新增 4 回归。**test.full 1739 passed + 3 skipped(90%)**,
  基线切片 26-09-29-0550。**未提交**(等显式指令); 真机走查开放。

- **2026-09-28 00:30 (v2 实施核对 + 安全/稳定性审计 —— 纯审计轮, 代码/文档零改动)** — 用户令「分析
  plans/26-09-27-1815 实施情况, 重点是安全性/稳定性/BUG, 并写报告含 HR 在线核实现状 (配置/默认节奏/
  限流)」。开工预检 `my-commit-flow.sync` PASS (与主线齐平 c7dfbd20)。产出:
  [reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html](../../reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html)。
  **核对结论**: M5.1-M5.5 共 33 个修改项逐条以 file:line 对到当前代码, 全部落地无缺席; 三个实施期收口
  (滚动窗口=max_pages_per_refresh / max_pages_per_round=9 / P 公式勘误) 均证实; 零静默变更成立
  (激活门 legacy 默认 + 新键全默认关/旧值)。**新发现 (均未改代码, 待拍板)**:
  ① **F1 (P2)**: 早停② 的 P 一致性机检空真 —— `period_ok` 初始 True 且只有 remain>0 的行参与反算
  (service.py:477/561-572), 整页 remain==0 时机检从未运行却被当作通过; 轮尾 meta 的
  `period_consistent=bool(period_values) and period_ok` (service.py:828) 却是 False —— 两道机检口径
  不一致。触发链: C 档(未达标)行 remain 若以可解析 0 展示 (实现注释自认「已到期行被站点截 0」) ⇒
  C 第 1 页即早停 ⇒ complete=True ⇒ C 第 2 页起种子走反应式「完整刷新未列出」放行 (resolve.py:260-273)
  ⇒ 漏管。B 档同形态无害 (本就可删); remain 空白形态则触发 S2 停站 (remain 是必填字段)。收口建议:
  早停②加 period_values 非空前置或限 A 档 + M0 补第④项实测 B/C 档 remain 形态。
  ② **F2 (P3)**: 跨页 S1 判据 `max(cur) > min(prev)` (parse.py:329-330) 对「轮内清单顶端插入」零容忍
  —— 相邻两页间隔 90~113s, 其间 ≥2 个新完成进清单顶端 ⇒ 判「跨页乱序」⇒ 本轮失败计熔断失败,
  连续 3 轮 ⇒ 12H 熔断 + suspended 人工恢复。fail-safe 方向无损, 是可用性风险; 与 2026-09-26
  「哪怕 1 处」定稿 (针对页面改版) 存在张力, 需单独拍板。
  ③ **F3 (P3)**: `parse_missing_rate_max` 被 S2 零容忍架空 —— service.py:551 任何缺失率>0 即中止,
  :806 的阈值分支不可达; keys.md:30 仍是旧语义 (死配置+文档漂移)。
  ④ **F4 (P4)**: status.py:143/190 注释仍写勘误前公式 (实现已正确); `covered_local_any`
  (service.py:486/596) 只写不读。
  **安全/稳定性结论**: 端点五道边界 (loopback/token 常数时间+0600 生成/origin/SSRF 白名单/回传双道校验)、
  存储自愈链 (.bad 留证→.bak→锁失效只读退化)、增量落盘、可中断停机、告警三档分级全部代码证实;
  残余在配置面 (extension_id 空 / token:123456, M5.5 WARNING 已就位)。
  **现状盘点** (报告 §5): 配置全表 3 张 (全局 23 键 + channel 5 键 + 站点 13 键含默认值) /
  默认节奏 (legacy: 12H 完整有效期, 抓取轮 ≤9 页·每档 ≤5 页·间隔 90~113s·配额 12/时·60/天 合并,
  15 页站点典型 2~3 轮 ~1-2h 收敛; split opt-in: 页面 40/时·下载 20/时双桶) / 限流全景 14 道 /
  站点文件字段 / 错误处理九分类 / 观测口子 (--hr-status/--hr-once/--hr-resume)。
  **基线复验与同步**: 分析轮开工时与主线齐平 c7dfbd2, test.full = 1811+3 (91%) 与切片 26-09-27-2326
  逐位一致; 提交轮预检发现远端进 aef2462 (webui 站点页搜索, hr/ 未动) ⇒ 按先同步后提交弃生成物
  _doc-map 后 ff 快进, 合并基线复跑 test.full = **1812 passed + 3 skipped (TOTAL 91%)** 与最新切片
  26-09-28-0014 逐位一致, 不新建重复切片。收尾动作: 报告按认领链协议补 5 处反向声明 (1815/2204/
  1628/档案/切片); _doc-map 因本报告入图超 cap —— 先按守卫指引收口**生成器头部说明** (省 147 字符),
  远端同期把 index-auto cap 提至 12100, 两相叠加后 12881 字节 (~11.5K 字符) 达标; activeContext 切片
  同轮蒸馏回 cap 内 (9579 → ~4.4K, 已完成明细沉降本档案)。

- **2026-09-27 22:18 (M5.1–M5.5 全部落地 —— 在线核实 v2 代码侧完成)** — 用户令「实施计划
  plans/26-09-27-1815, 拍板按推荐」。开工先同步: 远端 045ea27 比本地 cbc4b80 新两笔且纯落后
  (本地未提交的 10 个 memory-bank 文档与远端零重叠) ⇒ `merge --ff-only` 快进后再动代码。
  **五步各全量绿 + 一红验**:
  ① **M5.1 判据与观测** (1763 passed): `parse.order_violations` 纯函数(方向自适应由首两可比行推断,
  翻转视同逆序, 缺字段行不计比较但计「证据不足」)+ `cross_page_violation` 跨页证据; service 页内/跨页/
  方向翻转三路接线(判定前置 = 成功取回 + 表头 + 可比行 ≥ 2)+ `maxpage/currentpage` 进翻页判据**并集**
  (堵 P1 英文站「下一页」只认中文的缺口)+ 轮级骤降观测(`plunge_suspect`, 基线 = 最近结构完好且非零轮,
  可疑轮不计入 —— 堵「0 vs 0」自愈洞)+ `--hr-status` 观测面四行(排序 ✓/✗/未判定 · 考核期 P 分布 ·
  骤降观测 · 档位计数「上轮→本轮」)+ HrRefreshMeta 观测字段(order_ok/order_detail/entry_baseline/
  plunge_suspect/plunge_rounds/scope_counts/prev_scope_counts, 不抬 schema 版本)。
  ② **M5.2 信号处置与停用** (1774): S1 排序违反 / S2 必填字段缺失(均**不设阈值**, 2026-09-26 定稿)
  ⇒ `_SignalAbort` 停翻 + `ACTION_ERROR`(不产生放行)+ 计入熔断失败 + `signal_rounds` 累计
  (干净轮清零 = 三道隔离之三); 处置文案 S1/S2 分开(`events.order_broken` / `field_missing`, 节流共用);
  连续 3 轮(`SUSPEND_ROUNDS`)⇒ `HrSuspension` 停站: 取数侧**零请求**(连复用轮下载也让位)、
  判定侧 `judge_record` 返回 None **回落本地逻辑**(❗只停取数不停判定 = 拿旧清单继续放行, 比不停更危险)、
  恢复 = 新 CLI `--hr-resume <站点>`(锁内清 suspended + reason 留痕), 熔断到期不自动恢复;
  骤降保护生效(判不完备不产生放行, `accept_empty_listing` 站点级口子默认关; 持续 3 轮零 + 结构完好
  ⇒ WARNING 指引, 刻意不自动接受); 回填/清单**双路对账撤销放行**(P2: `_retract_on_backfill` 新算出/
  永久层复用 + `_retract_on_listing` 行重回清单 hash 继承的兜底, partial 轮即时收放行);
  登录失效指数退避(2^(n-1)×poll 封顶 refresh_interval, 退避期零请求/不计失败/不动 fetched_at,
  登录恢复清零); 多实例引导补「配额翻倍(2×12/时)」后果(D3=a)。
  ③ **M5.3 配额拆分** (1787): 激活门 `quota_model` 站点级默认 legacy(逐字节一致)+ 双令牌桶
  (HrLimits 扩展 split 字段 + `split_next_allowed_at`/`split_try_consume`; tokens/refill_ts 持久化,
  按「上次补充时刻+速率」恢复 —— 幂等跨重启消除整点突发; tokens=None ⇒ 首次满桶)+ 站点文件
  `torrent_quota`(不抬 schema 版本; 旧数据 quota 含下载计数 ⇒ split 初期页面用量高估, 保守方向)+
  页面只在新轮/下载只在复用轮(§3.4)+ `--hr-status` 页面/下载两组展示 + 速率×间隔自洽机检(3.6)+
  扩展 caps 上调 60/时·600/天(D6)+ `max_torrents_per_day` Optional 化(未配置按模型取 legacy 60 /
  split 200)。实施决策: 站点覆盖键 page_rate_per_hour/torrent_rate_per_hour 新增, 旧键
  max_torrents_per_hour 在 split 下映射为下载桶速率覆盖(已有配置不失效)。
  ④ **M5.4 早停与豁免** (1795): 预算**轮转起点**(D9=b: 上轮未完成档位优先, 跨轮语义不变)+
  单轮页面总量 `max_pages_per_round=9`(D5=a, 全局键, 0=不限)+ 早停② `remain==0` 连续 5 行
  (`AGE_STOP_STREAK`) + P 一致性机检(±1 天容差, 不过 ⇒ 告警 + 早停②/豁免 A 双禁用, 机检不是文档承诺)
  + 早停③ 覆盖本地严格版(本地种子 ⊆ 已抓行且索引无待回填 ⇒ 本档停翻但**绝不置 complete**)+
  豁免 A `auto_age_limit`(取数侧反算 P 喂豁免线, 判定与早停②同源, 默认关)+ 豁免 B
  `seeding_exempt_ratio`(本地做种 ≥ 要求 × 倍数 ⇒ 「义务已超额完成」, 压过清单命中, 默认关,
  不参与早停; `HrAnchor` 加 `seeding_time`, record.hr_anchor() 带出)。**实施决策与勘误**:
  滚动窗口收口 = `max_pages_per_refresh` 即窗口页数不另设键; P 反算公式**勘误**(三份制品同源笔误
  「P ≈ done + remain − now」数学上恒为负偏移 —— 正确 P = (now − done) + remain, 已按唯一正确方向
  实现, 主计划 §15 v3.6 注明); P 参与行 = remain>0 的行(已到期行 remain 被站点截 0, 反算负值不参与)。
  ⑤ **M5.5 收尾** (1796): 新键全链路(schema/validate/impact L0/keys.md/configuration.md)+
  端点纵深提示(extension_id 留空启动 WARNING —— 有意推通知, 配好即不再出现; 文档写明 token 自动生成
  与 config.yml 由用户手改, 红线不动)+ 扩展 README caps 表更新 + 零静默变更回归
  (legacy 站点行为逐字节一致独立守阵)。红验 ×4(翻页判据并集 / 骤降保护 / 激活门 / 早停②,
  临时还原 ⇒ 对应守阵红, 还原后全绿)。**最终 test.full 1796 passed + 3 skipped(91%)**,
  基线切片 26-09-27-2035; 主计划 §15 v3.6 + 计划 1815 v1.2 已回写。**未提交**(等用户显式指令);
  真机走查 + M0 前置实测三项(排序倒序 / P 恒定 / 英文站分页)仍开放。

- **2026-09-25 17:10 (计划 v3.0: 达标判定来源优先级 —— 仅计划修订, 代码待落地)** — 用户指令: 「HR在线核实优先级:
  在线信息.考察中 > 在线信息.已达标 > 在线信息.未达标 > 本地信息」。核查现行实现, 两处与该优先级冲突:
  ① `hr/model.py::satisfied_verdict` 对 A/D 档用「剩余达标时间 == 0 ⇒ 已达标」推导 —— v2.8 已实证该字段是
  **考核窗口倒计时**, 归零 = 考核到期(方向相反); ② A 档缺字段时 None 回落本地, 本地值越权推翻站点的明确清单结论。
  计划 v3.0 收口: §9 新增「达标判定的来源优先级」节(档位即结论: A 恒未达标 / B 已达标 / C 未达标, 命中即停,
  数值字段降为展示与进度参照; 本地仅在清单未命中 / 站点不可查时兜底; hybrid 双命中按 A>B>C 取);
  §2 判定边界补句 / §4 流量字段行改口径 / §9 三态表受管束行改写 / M3 落地实况拍板②标注取代 /
  §12 守阵更新(A 档命中+本地够线⇒仍未达标 · 双命中取序 · remain 退出推导) / §13 决策记录补行 /
  §14 变更记录 v3.0 / 封面元信息与 colophon。**纯文档修订, 无代码变更, 测试基线不变**;
  落地时改 `satisfied_verdict` + `judge_record` 并补 §12 新守阵。

- **2026-09-25 05:01 (第七批: 取证误读修复 —— `--hr-status` 明细表改版 + 已取记录逐文件 ts)** —
  用户拿 `hr/BTSchool.json` 取证问「是否短时间产生了大量种子下载」(分析结论: 无 —— 当天对站点仅 5 次请求
  = 3 页 + 2 个 .torrent, 全在频控内; `downloaded[]` 是「已取 .torrent」凭据不是 qB 下载), 顺带点出两处真问题:
  ① `hr_downloaded[].ts` **整批共用开始时刻**(同批两条微秒级相同 ⇒ 看着像瞬间批量下载, 取证误读);
  ② `--hr-status` 明细的「剩余达标」列(9d21h)会被读成「还要做种 9 天」—— 它实际是**考核窗口**
  (9d21h 内要完成做种要求), 真正的「还需做种时间」只有 16h57m。
  修: ① `_fill_infohashes` 的 ts 改记**各 .torrent 自己的取回时刻**(顺带同源的 `fail.last_ts` 一并修准);
  ② 明细表列 = tid / 档位(考察中等实际意思, 单点 `status.LANE_TEXTS`) / 上传量 / 下载量 / 分享率 /
  还需做种(镜像站点书写形态 HH:MM:SS·「N天HH:MM:SS」) / 名称(按**显示格宽**截断 40) / infohash;
  **剩余达标时间不再显示**; 列对齐走自写 `_dwidth/_pad`(str.format 按字符数对齐, CJK 双宽会错位)。
  测试 +2(service 1 钉逐文件 ts / report 1 钉 CJK 对齐·截断·列改版), 全量
  **1573 passed + 1 skipped**(TOTAL 91% / 10905 / 789 / 3582 / 327; HR 包 93%: 2782 / 143 / 766 / 91)。

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

- **2026-09-25 03:50 (v2.7 实报修复: 增量落盘)** — 用户删 hr_check 数据重启实测:「BTSchool.lock 长期被持有 /
  后端无落盘, Ctrl+C 后才落盘」。诊断(无死锁): v2.6 修好后一轮真实跨多个扩展轮询周期(3 页 + 回填, 中间夹
  间隔等待, 分钟级、按 §5/§8 **持锁进行**), Ctrl+C 打断的是**派发前的间隔睡眠**(sleeper 可中断, 日志
  「放弃本轮剩余的等待」即它), 轮次随即完成记账并落盘 —— 所以「Ctrl+C 后成功落盘」; 但落盘只在**轮尾**,
  中途断电/Ctrl+C 会丢已抓页面与配额账本。修: **每抓到一页**(complete=False 语义合并, 只置命中为 active)
  与**每个 .torrent 结果**(hr_downloaded 凭据 / fails 记账)当场提交; 轮尾仍按完整语义合并 + 写覆盖证明;
  叫停备注改「下载阶段被叫停」(叫停≠一定在取 .torrent)。⚠ `<site>.lock` 文件在释放后仍存在属正常
  (OS 级锁, 进程死即释放, 文件在 ≠ 被持有)。测试 +1, ★红验 1; 全量 **1571 passed + 1 skipped**(TOTAL 91% / HR 包 93%)。

- **2026-09-25 (审查修复: 通道时序错配 + 饿死残留, 计划 v2.6)** — 用户令「审查计划实施情况」并点名
  「种子下载不触发」, 中途补报 02:20 实测日志「tid=327727 取 .torrent 失败: 等待浏览器扩展取数超时(180s)」。
  审查结论: M1-M4 落地与计划一致、安全面(token/origin/SSRF/任务绑定/凭据归零)无高危, 但「不触发」的根因链清晰:
  ① **主因 = 通道时序错配**: 扩展 `chrome.alarms` 5 分钟轮询 vs 后端 `request_timeout=180s` ⇒ 轮询周期 300s >
  等待窗口 180s, 每条任务约四成概率因轮询相位落窗外直接超时(烧配额 + 计失败 ⇒ 3 次页面失败 = 12h 熔断);
  计划 §6 原是「批量清单」模型, 实现却是「派一条等一条」⇒ `MAX_BATCH=16` 永远只装得下 1 条。
  修: 扩展 `POLL_MINUTES` 5 → **1**(空轮询只打 loopback), `DEFAULT_POLL_HINT` 300 → 60, §6 补时序硬约束。
  ② **v2.4 P1 的饿死残留**: 不完备有效期 60s == poll 60s ⇒ 下一轮永远晚一个 ε ⇒ 复用轮补下载从不发生;
  且页面取数失败的 `except HrFetchError` 分支直接 return ⇒ 回填被一起跳过。修: 有效期 `max(120s, 2×poll)`
  (判定不读 expires_at, 拉长不产生放行) + `_backfill_on_page_failure`(页面失败后仍补一次下载, 待回填来自
  已持久化索引)。
  ③ **下载阶段异常语义**: `HrChannelStopped` / `HrChannelQuota` / `HrLoginExpired` 是 `HrFetchError` 子类,
  曾被 `_fill_infohashes` 吞掉计成 tid 失败(关停三次 = 12h 冷却) ⇒ 原样上抛 + `_guarded_backfill` 折成备注;
  扩展 fetchBinary 检测 download.php 返回 HTML(SameSite 剥 cookie 实测风险) ⇒ 新 `KIND_LOGIN_PAGE` ⇒
  后端按 `HrLoginExpired` 处置(不计失败)。
  ④ 展示与边角: 配额展示按窗口键折算(修「本小时 7/12 · 还能取 12 次」自相矛盾)、`--hr-status` 去掉
  「v1/v2 各一」硬编码后缀、Retry-After 以 cooldown 封顶、ext-quota 告警文案补「扩展上限本就低于后端配额」、
  qbmanager 死注释校准。
  ⑤ M0 实测收口: 下载 URL = `https://pt.btschool.club/download.php?id=<tid>`(用户实测, 计划 §13 已标)。
  测试 +11(service 7 / fetcher_channel 1 / ratelimit 1 / report 1 / extension_proxy 1), ★红验 7 条(还原旧实现
  全红); 全量 **1570 passed + 1 skipped**(TOTAL 91% / HR 包 93%; 本 shell PYTHONUTF8=1 的 2 条 GBK 假红
  单独复测通过)。扩展需在 chrome://extensions **reload 一次**才吃到 1 分钟轮询与登录页检测。
  计划文档已按用户令直接改原文档(v2.6 变更行 / 封面 / §6 / §13 / 页脚); 基线已回写。

- **2026-09-27 12:54 (提交轮: 合并远端 + 合并树重测零漂移)** — 用户令「提交」。预检发现远端在 `aeca1fb`
  (webui 模板共享化), 按「移出改动 → `merge --ff-only` 快进 → 施回改动」合流; 回写件无冲突。
  合并树重测 **1693 passed + 1 skipped**(TOTAL 91% / 11238 / 816 / 3728 / 331) 与 `26-09-27-1246`
  完全一致 —— 合并只动 webui 静态层, 不触碰 hr; 基线 `26-09-27-1254-post-merge-hr-carpt` 已记。

- **2026-09-27 12:46 (v3.5 补验: 已达标样张验证通过 + 挖出并修掉「双 id 空间」真缺陷)** — 用户补交
  CarPT `?status=2` 已达标页样张(17 行数据)令「验证是否正确」。
  ① **验证通过的部分**: 十列表头锚定 / H&R ID 纯数字 / 完成时间 "YYYY-MM-DD HH:MM" 无秒形态
  (parse_datetime 已认) / B 档 `satisfied_verdict=True` / 翻页判据(灰色下一页) / 序列化 roundtrip;
  B 档「还需做种时间/剩余考察时间」显示 `---` —— 非空白不计字段缺失, parse 成 None(展示层不显示),
  语义正确。
  ② **挖出真缺陷**: 种子名称列详情链接 `details.php?id=173107` 与该行 H&R ID `8017746` **不同空间**
  ⇒ 标准 `download_url(tid)` 拿 H&R ID 下载必然取错/取不到 —— 上一轮「待真机核对」的第②项提前由样张
  实证, 且答案是否定的。
  ③ **修复**: `HrEntry` 新增 `dl_id`(可选, to_json/from_json 同步); 基类 `_map_row` 经 `_dl_id_of`
  从行内链接提取(download.php 优先 / details.php 兜底 —— 标准 NexusPHP 两 id 同空间, dl_id==tid
  行为不变); `service._backfill` 下载改 `adapter.download_url(entry.dl_id or tid)`。
  真样张回归: 17 行 dl_id 全部正确, 下载地址落 `download.php?id=173107` 等种子 id。
  ④ 测试: fixture 改为真实双 id 空间结构(名称列 details 链接用种子 id / 操作列空), 标准 + CarPT 两侧
  各加 dl_id 断言; 全量 **1693 passed + 1 skipped**(TOTAL 91% / 11238 / 816 / 3728 / 331), 基线
  `26-09-27-1246-hr-carpt-dlid` 已记。**仍待真机**: A 考察中页(数据行含还需做种/剩余考察实值)与
  操作列是否有下载链接(A 页形态未知, dl_id 提取已有 details 兜底不依赖它); 未提交。

- **2026-09-27 (v3.5 CarPT 站点接入)** — 用户令「HR在线核实添加支持站点: CarPT」, 样张为用户提供的
  CarPT `myhr.php` 已登录页(空表, 2026-09-27 存档)。
  ① **样张核对**: 与 BTSchool 标准形态的差异 = 状态参数 `?status=N`(1 考察中 / 2 已达标 / 3 未达标 /
  4 已免罪, tab 文字逐一核对) 而非 `?hrtype=A/B/C/D`; 表头格是 `<td class="colhead">` 十列, 首列锚点
  「H&R ID」(非「HR编号」), 列名「下载完成时间/剩余考察时间」, 末尾多「备注/操作」两列; 分页仍
  nexus-pagination(`?page=N`), 服务端渲染无异步取数。样张为空表 ⇒ 数据行形态按 NexusPHP 惯例
  假设, 待首刷核对。
  ② **实现取向**: 不复制解析逻辑 —— `NexusPhpMyhrAdapter` 构造参数化(`scope_param`/`scope_values`/
  `header_key`/`column_names`, 语义列键 `tid/name/.../remain` 单点), 标准形态零行为变化;
  新 `adapters/carpt.py` 只是薄子类(登录页识别换本站表头锚点), 注册名 `"carpt"`。判定/取数/频道
  上游全部无感 —— `build_adapter` 工厂注入后, `page_url`/`parse_page` 走同一套代码。
  ③ **连带兼容**: `fetcher.py`/`report.py` 的 `_scope_of`(排障展示与离线走查 `<档位>.html` 文件名)
  兼容 `status=`; schema 的 `adapter` 帮助文案列明 carpt; `config-reference/keys.md` 同步。
  ④ **测试**: +5(URL 档位映射/数据行解析/空表样张结构/改版识别/登录识别), fixture ×2 按真实样张
  结构构造(数据行 NexusPHP 惯例补齐, 已注明); 首版 fixture「下一页」误用 `<b class="next">`,
  与 `has_next_page` 正则不符红一次, 改回标准 `<b>` 形态绿。
  ⑤ 全量 **1693 passed + 1 skipped**(TOTAL 91% / 11227 / 815 / 3720 / 330; test.full 18.1s),
  基线 `26-09-27-1235-hr-carpt-adapter` 已记。**未提交**(等用户显式指令)。

- **2026-09-26 (v3.4 状态模型重新梳理: 三个终态都已结束 —— 纯文档)** — 用户指令: 「HR在线核实计划重新梳理,
  优先级: 在线信息.考察中 > 在线信息.已达标 > 在线信息.未达标 > 本地信息, 最终态: 已达标 | 未达标 | 已免罪,
  3 个状态都代表着结束状态」。
  ① **优先级链核查**: 与 v3.0 落地口径逐字一致 (`judge_record` 档位即结论 + `_lane_rank` A>B>C>本地兜底),
  无实现缺口。
  ② **终态语义收口**: 「已达标/未达标/已免罪是考核期已过的终态」此前只散在展示层档案
  (webui-hr-safety-display 修正轮 / webui-hr-popup) 与代码注释 (`resolve.py` SAFETY_* 段), 主计划 §9
  **零处提及「终态」** —— 本轮在 §9 v3.0 优先级节之前新增「状态模型」节: A 考察中 = 唯一进行中;
  B/C/D = 三个终态 (各自展示落点: safe 绿 / failed 红·考核未通过 / 安全放行)。
  ③ **记录展示缺口**: WebUI 来源徽标把 D 档已免罪折进「在线·已核实，安全放行」(`SRC_SITE_RELEASED`),
  与「完整刷新未列出」共用 token —— 终态模型下应分开呈现, 拟随 webui-hr-popup 落码轮补
  `SRC_SITE_EXEMPT`, **待用户确认**。
  ④ 计划封面 / 页脚 / §14 变更记录补 v3.4 (版本注: v3.1-v3.3 记于各自档案); 本档案与 activeContext 切片
  同步; webui-hr-popup 档案落码行挂缺口备忘。
  ⑤ **落地实况 (同日, 用户令「修复缺口」)**: `hr/resolve.py` 新增 `SRC_SITE_EXEMPT`("site_exempt",
  「在线·已免罪」), `HrResolution.released_src` / `HrJudgement.verified_source` 透传 D 档放行出处,
  `safety_display` 据此分流(D 档 ⇒ site_exempt; 缺席式放行 ⇒ site_released 原样); 前端 `shared/hr.js`
  两张映射表各 +1 键(徽标「在线」/ 来源桶「在线核实」; 徽标 class 固定 hr-src, 无新 CSS)。
  测试 **+2**(`test_judge_record_carries_verified_source` 透传 / `test_safety_display_site_exempt_split_from_released`
  分流) + test_web 字段级 D 档断言块; 守阵 SRC_* 常量数 8→9; ★**红验 3 条全红**(临时还原旧分支)后还原;
  全量 **1637 passed + 1 skipped**(TOTAL 92% / 10998 / 787 / 3644 / 328); 基线已回写。
  **已入库 `a497fba`**: 合并远端 4 笔(docker 部署 / 种子级标签分类编辑 / 分享率列对齐 / 切片回写)后经
  合并提交 `d72a538` 推送, 合并树重测 **1640 passed + 1 skipped**(TOTAL 92% / 11013 / 787 / 3656 / 331),
  baseline 已记合并条目。

- **2026-09-26 01:30 (v3.3 落地: 选项页终态实施 —— 风格 A 瑞士网格 + 两表 + 日志收起)** — 用户令「实施」
  (前情: 三套风格选型定 A, 见上一条选型结论)。用户另令「扩展需要 HR 在线核实详情表, 把冗长 log 总结成表格,
  log 收起仅排障用; 先计划两张表展示哪些信息, 更新模板 A」—— 两表规划已并入选型文档后一并实施。
  ① **后台事件环**(`background.js`): 新增 `events` 结构化环形缓冲(上限 50, 防抖整份写回, 与日志同源双写
  但各记各的 —— 日志给人排障, 事件环给表格渲染, 解析日志文案做表太脆), 字段
  `{t, host, kind(page/torrent), ok, status, ms, bytes, tag(ok/quota/login/error), note}`;
  五个事件点: 页面直取成功 / 离屏渲染成功(标「离屏渲染」—— 同一任务第二次真实访问, 便于用量对账) /
  种子下载成功 / runTask 失败(含 quota 与 login-page 分类); `pollAll` 收尾与日志一并落盘。
  ② **选项页重写**(`options.html`/`options.js`, 按样张 A): 自上而下 ①连接端点(表单, 存入即生效, 多实例列表
  保留) ②站点权限(自动拉清单勾选 + 一键授权, 手动兜底收进折叠 details) ③**站点现状表**(一行一站:
  最近活动/动作与结果/用量(本时·本日 访问·下种 —— 阈值从 `SITE_CAPS` 取不写死)/状态(正常·受限·登录失效·异常,
  由该站最近一条事件的 tag 定)) ④**最近取数明细表**(环形 50 条: 时间/站点/类型/结果/耗时/大小) → 状态行 +
  自测/拉取按钮 → **折叠区**(运行日志全套[过滤/清空/限渲染原样保留] + 硬上限展示 + 高级 JSON + 保存);
  「清空日志」只清日志不动两表; 两表随后台落盘经 `storage.onChanged` 防抖自动刷新。
  ③ **守阵**: `test_background_events_ring_dual_write`(真跑 background.js 六类场景钉事件契约) +
  `test_options_swiss_wiring`(替掉三档接线守阵, 钉单一风格终态 + 共存机制不回潮)。
  ④ 全量 **1624 passed + 1 skipped**(TOTAL 92% / 10952 / 786 / 3636 / 327; 含远端 443a785 的 docker +6);
  基线已回写; README §2 改为终态口径; 制品 meta/认领链(计划 ↔ 档案双向引用)已按守阵要求闭环。
  待真机: reload 扩展后核两表在真实取数下的可读性。

- **2026-09-26 00:15 (v3.2 修正: 三模板改为**整页**三档)** — 用户纠偏「三种模板指的是整个扩展设置页面 3 个模板,
  不是实例端点的模板」。重做选项页结构: 页顶「页面模板」三卡 **极简 / 标准 / 完整**, 选择持久化到新键
  `uiTemplate`(首次默认: 有存量实例 → 标准, 全新安装 → 极简)。极简 = 粘 token + 自动拉站点 + 一键授权,
  收起多实例管理(`multiTools`)/手动兜底/硬上限展示/运行日志; 标准 = 极简 + 那些区块; 完整 = 标准 +
  「表单 / JSON 直接编辑」切换(旧 JSON 文本域原样保留, `setMode` 双向互导不变)。
  上一轮的「实例端点三模板」按钮撤销, 换成表单常驻 + 全新安装自动按本机默认预填。
  实现细节: 切档靠 `[hidden]`, 但 `div.row` 的 display:flex 等作者样式会盖过 UA 的 `[hidden]` ⇒
  加全局 `[hidden]{display:none!important}` 兜底(守阵钉住); 极简档多实例时亮提示行(`multiNote`),
  实例数据不动、轮询全部生效。守阵 `test_options_templates_and_site_checks_wiring` 改钉新接线
  (三卡/两模式按钮/区块 id/`uiTemplate`/`[hidden]` 兜底); 全量 **1617 passed + 1 skipped**(TOTAL 91% /
  10942 / 792 / 3636 / 329; 含远端 c46e67e 的 full-checking +3), 基线已回写; README §2 改为整页三模板口径。
  **选型结论(2026-09-26)**: 用户澄清三模板是三套独立风格、选一套实施 —— 出三套样张
  ([26-09-26-0031-plan-hr-ext-options-style.html](../../plans/26-09-26-0031-plan-hr-ext-options-style.html)),
  **选定 A · 瑞士网格, 实施暂缓**;工作区「三档共存」实现如何处置待用户定(站点勾选授权半边是原始需求、应保留)。

- **2026-09-25 23:43 (v3.1 落地: 扩展配置简化 —— 三模板 + 站点勾选一键授权)** — 用户指令「HR 在线核实插件配置
  需要简化, 尽量做到自动: 站点权限可直接勾选已支持的站点 / 配置好后端后只需申请权限; 实例端点改为点击或输入,
  先做三个简单的模板供选择」。
  ① **端点新增只读 `GET /api/hr/sites`**(`channel.py::API_SITES` + `server.py::route/_sites_response`):
  与 `tasks`/`result` 同一道门(token + origin 白名单, 401 前不写任何状态), 返回
  `{sites: [{site, origin}], error, server_time}`; `sites_fn` 由 `runtime._site_origins` 提供 —— **每次请求现读
  配置**(热重载加站点不改端点监听身份、不重绑, 构造期快照会把新站点漏在授权清单外), 从各站点
  `hr_page_url` 派生 `scheme://host/*`(与 UrlPolicy 同源), `mode=off`/空 URL 不出现; `sites_fn` 抛异常
  (配置重载窗口)回 200 + 空清单 + error, 不打死端点线程。
  ② **扩展选项页重构**(`options.html`/`options.js`): 实例端点改**表单**(地址默认 `127.0.0.1:8788` 只粘 token;
  「存入实例列表」**即时落盘**, 列表可载入/删除, 同地址覆盖; 高级 JSON 保留为可切入口 —— 该轮先做成
  「实例端点三模板」, 次轮 v3.2 按用户纠偏改为**整页**三档, 见上一条)。
  ②站点权限改**从后端拉清单勾选**: 进页面自动拉一次(失败保持安静), 「全选」+「申请勾选站点的权限」一键授权
  (合并手动兜底条目并去重; 授权窗前**无 await** 保持用户手势), 勾选状态持久化到新键 `siteSelections`;
  手动填域名降级为 `<details>` 兜底, `siteOrigins` 键语义不变(后台本就不消费它, 权限真门是 Chrome)。
  归一化守则不动(先 normalize 再进浏览器 API)、日志区不动。
  ③ **测试 +7**: `test_hr_server.py` 4 条(清单下发/同门 401·403/sites_fn 异常不炸/无 sites_fn 向后兼容) +
  `test_extension_proxy.py` 2 条(`API_SITES` 与 `hr.channel` 同源钉死 / 三模板与勾选面接线齐全) +
  `test_hr_runtime.py::test_site_origins_served_live_for_extension`(现读派生 + 热加站点即生效 + mode=off 不出现)。
  ④ 全量 **1614 passed + 1 skipped / 18.6s**(TOTAL 91% / 10920 语句 / 792 未覆盖 / 3626 分支 / 327 partial),
  sidefx 越界 0; 基线已回写; 扩展 README §2 改写为新配置面。
  待真机: 扩展 reload 后走一遍「模板一 → 粘 token → 自动拉站点 → 一键授权 → 立即拉取」。

- **2026-09-25 17:37 (v3.0 落地: 达标判定来源优先级 —— 档位即结论)** — 接上一条计划收口, 用户令「修复问题, 落地」。
  ① `hr/model.py::satisfied_verdict`: A/B/C 三档**全部档位即结论** (A 考察中 / C 未达标 ⇒ False, B 已达标 ⇒ True),
  删「A/D 档看 remain_seconds == 0 ⇒ 已达标」推导 (v2.8 已实证该字段是考核窗口倒计时, 归零 = 考核到期, 方向
  相反) 与「缺字段回落本地」路径 (本地值不得越级推翻站点清单结论); D 已免罪不进命中清单, 未知档位才 None。
  ② `hr/resolve.py::judge_record`: 双命中 (hybrid 两 hash 映两个 tid) 改按 `(判定档位, 达标档位序)`
  取更保守者 —— 新增 `_lane_rank` (A=3 > B=2 > C=1), 删「首命中即 break」; 与键序无关。
  ③ `torrents/record.py::check_hr_satisfied` 分支逻辑不变 (site_satisfied 非 None 即采纳; mode=all 未核实的
  None 仍回落本地), 仅 docstring 同步; 四个消费点调用点零改动。
  ④ 测试 **+2** (`test_lane_verdict_ignores_remain_and_local`: A 档命中 + remain 归零/缺失都 ⇒ False, 本地
  不可越级; `test_judge_record_double_hit_prefers_lane_order`: B+A 双命中取 A、C+B 取 B, 两键序同结论)
  + 改写 1 (`test_judge_record_carries_site_satisfied_verdict`: A 档期望 None → False); test_hr_parse 注释与
  测试计划 docstring 同步。★**红验 3 条全红** (临时还原旧实现: A 档回落 None + 去档位序) 后还原全绿。
  ⑤ 全量 **1601 passed + 1 skipped / 18.6·18.1s** (TOTAL 91% / 10950 / 791 / 3594 / 326; HR 包 93%:
  2814 / 147 / 774 / 93); 基线已回写; 计划 v3.0 标记已落地 (§14 落地实况⑤)。

- **2026-09-25 17:10 (计划 v3.0: 达标判定来源优先级 —— 仅计划修订)** — 原文已外迁:
  [attachments/26-09-22-backend-partial-hr-verify-log.md](../26-09-22-backend-partial-hr-verify.md)(档案触顶处置);
  落地实况见下一条 17:37, 收口内容见主计划 v3.0 变更行。

- **2026-09-25 (v2.9: 超龄豁免 —— 判定侧豁免 + 翻页早停)** — 用户指令: 「忽略下载时间超过一定期限的种子,
  比如完成时间超过一年的种子没有必要验证 HR, 甚至也没有必要往下翻页」。同步: 本 clone 落后 Gitee
  develop 51 提交(本地 master 齐平 origin/master 但 develop 已前进), 备份 .git 后 `merge --ff-only`
  快进到 1516bd6 —— M1–M4 与 v2.6~v2.8 修复均已由其它 clone 交付, 本轮在现实现上加功能。
  ① **判定侧**: 新站点级键 `trackers.<站>.hr_check.completed_age_limit`(0 = 关闭, 默认行为不变;
  开启时 1D~3650D, 单位写错如 365S 配置期拦下 —— 按秒配等于把刚完成的种子集体豁免)。
  `judge_record` 对锚点里**本地完成时刻**超线的种子直接给第四态 `HrIdentity.EXEMPT`「超龄豁免」:
  排在「无可查键回落本地」闸门**之前**(豁免是 qB 侧事实, 不依赖索引建到哪), **压过清单命中**
  与 unknown_policy, `mode: all` 也认 —— 都是配置者显式取舍, 写进 schema help 与 §13。
  参数由记录侧 `hr_judgement()` 从 `tracker_conf` 带进, 门面只透传(不多一次配置遍历)。
  WebUI 沿用 `state_text` 单点显示「超龄豁免」, 前端零改动。
  ② **取数侧**: 页面上超龄的行**不入索引、不回填 .torrent**(判定会豁免它们, 索引行留着只会白烧
  下载配额; 完成时间不可解析的行保留 —— 不猜); 当前页整页超龄且**页内 + 跨页都呈完成时间倒序**
  才允许早停 —— 后续页只会更老, 本档位在豁免线内的清单已全覆盖, **覆盖证明照常成立**
  (complete 可达 ⇒ 放行照常产生; 若把早停算成「不完备」, 清单长过豁免线的站点会永远没有放行,
  功能自废)。倒序证据不成立(页内升序 / 跨页倒序链断裂 / 缺完成时间)就照常翻到底 ——
  错误方向是多花配额, 不是漏判; 早停在 `refresh.reason` 留痕(`--hr-status` 可见)。
  ③ **测试 +17**(判定 7: 压过清单命中 / 线内不豁免 / 0 关闭 / completion_on 缺位不猜 /
  无可查键仍豁免 / mode=all 认 / 边界含等号; 取数 8: 关闭不变 / 行过滤不回填 / 早停跳页 /
  线内行阻止早停 / 页内升序不早停 / 跨页断链不早停 / 缺完成时间不早停 / 上页无时刻不早停;
  门面透传 1; 配置 1), ★红验 3 处(豁免短路 / 早停 / 行过滤停用 ⇒ 10 条守阵全红, 还原后全绿)。
  全量 **1593 passed + 1 skipped**(TOTAL 91% / 10849 / 791 / 3598 / 327; 并行 19.9s +
  一次 36.8s 负载离群; 本 shell 2 条 GBK 假红按 pitfalls/testing/patching.md 复测通过)。
  基线已回写(baseline.md + history)。文档: 计划 v2.9(封面/§4 早停 note/§7 键/§9 两表/§13 决策行/§14) ·
  docs/configuration.md「超龄豁免」节 · config-reference/keys.md。
  待真机确认: BTSchool 页面排序是否完成时间倒序(决定早停是否实际生效; 不倒序只是不省配额, 不会错)。
- **2026-09-25 05:01 (第七批: 取证误读修复 —— `--hr-status` 明细表改版 + 已取记录逐文件 ts)** — 原文已外迁:
  [attachments/26-09-22-backend-partial-hr-verify-log.md](../26-09-22-backend-partial-hr-verify.md)(档案触顶处置);
  摘要见 activeContext 切片「已交付 · 第七批」。

- **2026-09-27 18:15 (v2 修改计划产出: 审计报告转化 —— 纯文档, 代码未动)** — 用户令「将
  reports/26-09-26-1628-report-hr-online-verify-audit.html 转化为修改计划, 注意前置关联计划与其他相关文档」。
  ① **承接不重证**: 报告 §7–§11 已由主计划 §14 (v3.5) 定稿为「在线核实 v2 方案」, 设计取舍权威留在 §14,
  本轮只做实施拆解 (落点 / 顺序 / 守阵); ② **补缺口**: §14 未吸收的审计结论全部入计划 —— P1 骤降保护 +
  空表口径矛盾定案 (推荐「对照上轮」双判据: 稳定空表 = 合法 complete / 骤降 = 不完备, docstring 与
  `test_empty_listing_is_complete` 一并改对)、P2 放行收不回 (推荐回填对账撤销 + 新行优先回填, 窗口 ≤12H →
  ≤ 回填时延)、P2 多实例引导 (判据受限, 推荐 INFO+后果文案)、P3 登录失效指数退避、P3 端点纵深代码侧提示;
  ③ **新增三个实施设计点 (§14 未显式展开)**: 配额激活门 (`quota_model` 站点级默认 legacy —— 40/时 比 12/时
  松, 不设门直接切违反保守默认) / 单轮预算轮转起点 (固定 A→B→C 在总量 8~10 预算下会饿尾档, complete 恒假 =
  「功能自废」换形态复发) / 扩展 page caps 上调 (后端拆分后 10/时 拦得住正常运营, 需 ≥ 后端 × 1.5);
  ④ **拍板汇总**: D1–D10 十项 (含 §14.9 原四项参数) + M0 前置实测三项 (只阻塞 M5.4 早停启用);
  **M5.1 判据与观测步不消费任何拍板项, 可即刻开工**。制品: plans/26-09-27-1815 (doc-topic
  `backend-partial-hr-verify`, 与报告/主计划/档案串联); 切片同步。
  ⑤ **踩坑复发 +1** (pitfalls/kb/refs-rename.md 认领链条目): 新计划 doc-refs 首版写成文件相对 ⇒ 认领链守卫红,
  连带暴露报告与主计划未反向声明; 未命中原因 = 写制品前只读 doc-forms.md(「相对路径」没写基准), 没路由到
  pitfalls/kb。已改根相对 + 给报告/主计划补 doc-refs 反向声明 + 档案触顶外迁一条日志(v3.0 17:10 → attachments)。
  ⑥ **计划 v1.1 (同日)**: 用户问「骤降保护在考核中页会不会误判」并点出两个站点语义 —— 考核通过移去已达标页 /
  旧已达标被站点清除 ⇒ 单档清零属正常语义, 判据确立为<strong>轮级合计</strong> + 基线取「最近可信非零轮」(堵
  「0 vs 0」自愈洞) + 持续零走「告警 + 人工确认」不做自动接受 (持续零 + 结构完好同样可由改版造出); D1 与
  骤降守阵组同步, 残余风险 (单档改版下 X% 线只挡一轮) 如实注明。计划 §8 v1.1。
  **未提交**(等用户显式指令)。
