# 26-09-22-backend-partial-hr-verify — 部分种子 HR 的在线核实

**Status:** Open
**Added:** 2026-09-22
**Updated:** 2026-10-03
**Summary:** 部分种子 HR 站点在线核实。**M1 核心管道 + M2 取数通道 + M3 判定联动 + M4 多站点与打磨均已落地**
(2026-09-24/25): M1 = 新包 `src/auto_qb/hr/` 离线管道 + 配置全链路 + `--hr-once`; M2 = 本地端点
(`/api/hr/tasks` + `/api/hr/result`, token + origin + URL 白名单) + 取数线程 (`hr/worker.py`) + 只读视图发布 +
MV3 扩展 (`extensions/hr-fetch-proxy/`) + `channel`/`shared_dir` 转 **L1** 并接上热重载重挂;
M3 = 三态接进 `TorrentRecord` 与四个消费点; M4 = 四类事件语文化 + 站点级状态单点与 WebUI 出口 +
多站点隔离守阵与接入指南。六批实报修复后 `--hr-status` 明细改版(档位人话/上传·下载·分享率·还需做种/
CJK 格宽对齐/剩余达标不显示)且 `hr_downloaded[].ts` 改记逐文件取回时刻。
**v2.9 超龄豁免已落地 (2026-09-25)**: 新站点级键 `completed_age_limit`(0=关闭) —— 完成时间超线的种子
判定侧直接豁免(第四态 `EXEMPT`, 压过清单命中), 取数侧超龄行不入索引/不回填 + 翻页早停(倒序证据成立才停)。
**v3.0 达标判定来源优先级已落地 (2026-09-25 17:37)**: 在线考察中 > 在线已达标 >
在线未达标 > 本地 —— 档位即站点的达标结论(A 恒未达标/B 已达标/C 未达标, 命中即停), 页面数值字段降为展示,
本地仅兜底; `satisfied_verdict` 删「A/D 档看剩余达标时间归零、缺字段回落本地」路径, `judge_record`
双命中按档位序取; +2 守阵红验 3 条全红, 全量 1601 passed + 1 skipped。
**v3.3 选项页终态已落地 (2026-09-26 01:30)**: 风格选型定 A(瑞士网格, 三套样张见 plans/26-09-26-0031)
后实施 —— 后台 events 结构化事件环 + 选项页两表(站点现状 / 取数明细) + 日志收起仅排障;
测试 +1(共 1624 passed + 1 skipped)。
**v3.1+v3.2 扩展配置简化已落地 (2026-09-25/26)**: 端点新增只读 `GET /api/hr/sites`(runtime `sites_fn` 现读配置,
热重载加站点即生效); 扩展选项页**整页三模板**(极简 = 粘 token + 一键授权 / 标准 = + 多实例管理 + 手动兜底 +
硬上限 + 日志 / 完整 = + JSON 直接编辑, 选择持久化 `uiTemplate`), 站点权限改后端拉清单勾选 + 一键申请
(手动填域名降级兜底); 测试 +7, 全量 1617 passed + 1 skipped。
**v3.5 CarPT 站点接入已落地 (2026-09-27)**: 新 adapter `carpt`(myhr 表格变体: `?status=1/2/3/4`
状态参数 + `H&R ID` 十列表头, "下载完成时间/剩余考察时间"列名) —— `NexusPhpMyhrAdapter` 参数化
(scope 参数/档位映射/表头/列名可注入), 配置 `adapter: "carpt"` 即接入; fetcher/report `_scope_of`
兼容 `status=`; 测试 +5, 全量 1693 passed + 1 skipped(TOTAL 91%)。
**只差真机走查**(M0 四项实测 + 装扩展后跑一轮真实取数 + v3.1 新配置面走查) —— 计划见 memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html (§13 决策记录与 M0 实测清单)。
**在线核实 v2 修改计划已产出 (2026-09-27, 审计报告转化, 代码未动)**: 见 plans/26-09-27-1815-plan-hr-verify-audit-fixes.html ——
P1/P2/P3 修复落点 + 主计划 §14 的 M5.1–M5.5 实施拆解, 10 项待拍板 (D1–D10) + 3 项前置实测; M5.1 观测步可即刻开工。
**v2 实施核对 + 安全/稳定性审计完成 (2026-09-28, 代码未动)**: 报告 reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html
逐项核对 33 个修改项全部落地且与计划一致; 独立发现 F1(P2: 早停② P 机检空真 + B/C 档 remain 形态假设 ⇒ C 档
误放行链)/F2(P3: 跨页 S1 对轮内清单插入零容忍 ⇒ 误停站场景)/F3(P3: parse_missing_rate_max 被 S2 架空)/
F4(P4: 注释漂移×2+死变量), 均只记录待拍板; test.full 1811+3(91%) 复验与基线 26-09-27-2326 逐位一致。
**在线核实 v3 模型重建计划已立档 (2026-09-28, 代码未动)**: 用户定调推翻 v2 模型 —— 每轮全量翻页违背「首波全量/后续增量」口径、legacy+split 双频控混杂、熔断停用回落本地是漏 HR 隐形炸弹、40 键配置面失控; 见
[plans/26-09-28-1932](../plans/26-09-28-1932-plan-hr-verify-rebuild.html) (doc-status Open, 22:55 修订, 待批准实施):
**四行判定表 + 12 格情形矩阵**(命中考察中(A)→管束 — **本地达标与否都管, 删了前功尽弃**; 站点终态档 B/C/D("未达标"=考核结论已定的终态)与移出未列出→放行; 无证据→本地兜底: 达标放行/未达标管束; 管束 = 打标/删除保护/辅种排除) +
**单波型取数**(每波以全量对账为目标 + A/B/C 轮流翻页 + **三个停翻条件**: 完成时间覆盖① / remain==0 连续 5 行到期段强信号②(纯页面信号, 独立于本地时间) / 本地全集 infohash 覆盖③, 任一成立即停 — 覆盖对象集 = 未对账 ∪ 考察中, 终态不可逆 ⇒ 终态种子不再翻页下载; 废除增量/全量/续翻三波型与断点续翻 — 清单在动, 每波自证覆盖) +
**下载规则**(下载=身份登记一次, 同 tid 永不重下, 状态追踪靠 tid 读页面档位; **已见 A 档行无条件全下载**硬规则; B/C/D 终态行 = 覆盖区间+宽泛名称粗配(D1 已拍板 21:53: 连续重合段≥K 即疑似本地, 宁误配不漏配; 漏配后果全方向安全无漏 HR; 粗配=疑似触发器, 定论一律 infohash 精配); 本地没有的种子不下载; 完成时间可信度分层, 纯辅种不参与条件①) + **超额线 SEED_EXEMPT_RATIO=3**(做种 ≥3×required+extra ⇒ 放行并免除在线对账 — 不进覆盖对象集, 特别老藏深的种子不再拉深覆盖深度, 纯辅种做满 3× 同样出集; 网站绝对权威 — 被动命中「考察中」仍转管束) +
单频控三键 + 熔断/停用/退避全删(档位级数据有效性截断式, 证据无时效 — 整波覆盖证据与两级证据年龄退役; 排序失效 = 强制早停立即停翻(之前数据有效, 等下周期))+ 证据防伪三道校验(A 档流转守恒: 上波考察中行在本波 A/B/C 留存 ≥0.7 首要; 总行数骤降 30% 粗保险; 零行对账戳)+ 失踪观察期(22:38 收紧: 失踪者一律当作无证据 — 无小样本豁免无快路径; streak 用局部覆盖证明推进 2 波判移出, 与整波校验解耦防死锁; 行 4 特例: 没看到不终结考察中); 22:15 梳理轮修 17 处漂移并补齐骤降保护/空对象集两个完备性缺口(§3 重编号 3.3 超额线/3.4 证据健康);
配置 40→14 键(completed_age_limit/auto_age_limit/seeding_exempt_ratio/hr_page_scopes/accept_empty_listing/quota_model/mode/unknown_policy 全删); M1-M5 里程碑与验收判据见计划 §8; v2 审计 F1-F4 由该计划整体消解。
**v3.1 HR 计数对平集成修改计划已产出 (2026-09-29, 代码未动)**: 可行性报告 26-09-29-1803 转化为
[plans/26-09-29-2036](../plans/26-09-29-2036-plan-hr-counter-integration.html) (doc-status Open, 拍板点 P1-P4 待用户) ——
M1 核心对平机制(上线即现状, 零拍板依赖) / M2 两站启用(前置 D2 样张) / M3 退役与打磨。
**四现象故障取证完成 (2026-10-03, 纯文档轮)**: 引擎数据/判定侧零故障, 四现象全闭合于展示与产品语义层 (仍拉取=设计内 / 未核实=双通路结构性矛盾 / 失踪 0 波=退役行 missing_streak 恒 0); 报告 [reports/26-10-03-1505](../reports/26-10-03-1505-report-hr-fetch-verify-forensics.html), 修复建议三级待拍板。
**Topics:** backend-partial-hr-verify
**Refs:** memory-bank/reports/26-09-29-1803-report-hr-counter-verify.html, memory-bank/plans/26-09-29-2036-plan-hr-counter-integration.html, memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html, memory-bank/plans/26-09-27-1815-plan-hr-verify-audit-fixes.html, memory-bank/plans/26-09-28-1932-plan-hr-verify-rebuild.html, memory-bank/reports/26-09-26-1628-report-hr-online-verify-audit.html, memory-bank/plans/26-09-25-1823-plan-webui-hr-safety-display.html, memory-bank/tasks/26-09-25-webui-hr-safety-display.md, memory-bank/plans/26-09-26-0031-plan-hr-ext-options-style.html, memory-bank/reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html, memory-bank/reports/26-10-03-1505-report-hr-fetch-verify-forensics.html

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
| M3 判定联动 | **Done** | 2026-09-25: 判定收口 `hr/resolve.py::judge_record`(+ `HrJudgement` / `HrSiteFacts`)与门面入口 `HrRuntime.judge()`; 记录侧只加 `hr_link` / `hr_judgement()` / `hr_anchor()`, **四个消费点调用点一行未动**(改的是它们共同调的 `check_hr_condition` / `check_hr_satisfied`), 站点侧优先、缺字段回落本地; 判定桥由 `TorrentStore` 挂上(门面稳定引用, 读取时现算 ⇒ 不置脏/不重写全库); `manager._hr_anchors()` 按站点给出 `{infohash: HrAnchor}`; `mode: all` 升为站点侧驱动(未核实恒受管束, policy 绕不过); WebUI 加三态/依据/来源与站点侧值字段 + 详情抽屉两行。全量 **1519 passed + 1 skipped** |
| M3 真机 `hr.once` 走查 | Pending | 需用户装扩展后跑 `python src/auto-qb.py config.yml --hr-once` 与主程序, 确认: 端点拉得到任务 / 页面直取拿到表 / 三态在 WebUI 与日志上对得上。与 M0 四项实测同批做 |
| 实报修复: 下载被饿死 + 扩展第二道闸 | **Done** | 2026-09-25: 用户贴 `--hr-status` + 站点文件报「种子似乎没有下载成功」⇒ 三个真缺陷: ①**下载被页面饿死**(频控门槛是「相邻两次请求」而页面永远排前面; 复用轮只补下载) ②**生产路径不等间隔**(计划 §8 本意是在锁内等满; 一次刷新只能发第一个请求 ⇒ 覆盖证明永不成立) ③**无可用索引键 ⇒ 整站按受管束打标**(无键时回落本地); ④ 扩展侧硬上限 `site-caps.js`(访问 10/时·50/天, 下种 50/时·200/天, 超限拒发 + `kind=ext-quota` ⇒ 后端让位不计失败)。合流后全量 **1541 passed + 1 skipped**(本分支合流前 1534) |
| M4 多站点与打磨 | **Done** | 2026-09-25: 四块一起交付 —— ①**四类事件语文化** `hr/events.py`(文案单点 + 标签前缀; **登录失效从熔断里摘出来**: 不计失败/不推熔断/只报一次并给动作, 原因仍写 `refresh.reason` 但**不碰** fetched_at 与新鲜度基准) + 通道静默告警补**受影响站点** ②**站点级状态单一点** `hr/status.py::site_status()`(CLI 与界面同一套数, 新增下次刷新/回填进度/「现在为什么不放行」) ③**WebUI 出口**: `GET /api/hr/status` + 设置页「HR 站点状态」章节(经典与 Hub 两入口 × 两套 UI) + **前端字段一致性守阵** ④**多站点**: `tests/test_hr_multisite.py` 5 条钉死「第二站点只改配置」与隔离(配额/熔断/锁/索引不串味) + `docs/configuration.md` 接入指南。全量 **1561 passed + 1 skipped** |
| v2.9 超龄豁免 (判定侧豁免 + 翻页早停) | **Done** | 2026-09-25: 用户指令「完成时间超过一年(可配)的种子没有必要验证 HR, 甚至也没有必要往下翻页」⇒ 新站点级键 `completed_age_limit`(0=关闭, 1D~3650D): 判定收口 `judge_record` 对本地完成时刻超线的种子给第四态 `EXEMPT`(排在「无可查键回落本地」之前, 压过清单命中与 unknown_policy, mode=all 也认); 取数侧超龄行不入索引/不回填 + 整页超龄且页内跨页倒序成立才早停(覆盖证明照常成立)。判定 7 + 取数 8 + 门面 1 + 配置 1 = 17 条测试, 红验 10 条全红; 全量 **1593 passed + 1 skipped**。计划 v2.9 (§4/§7/§9/§13/§14) |
| v3.0 达标判定来源优先级 (档位即结论) | **Done** | 2026-09-25 17:37: 用户指令「在线信息.考察中 > 在线信息.已达标 > 在线信息.未达标 > 本地信息」⇒ 计划 v3.0 (17:10) 收口后当轮落地 —— ① `hr/model.py::satisfied_verdict` 三档全档位即结论 (A/C ⇒ False · B ⇒ True · D/未知档位才 None), 删「A/D 档看 remain_seconds==0 ⇒ 已达标」推导 (v2.8 已实证该字段是考核窗口倒计时, 方向相反) 与缺字段回落本地; ② `hr/resolve.py::judge_record` 双命中改按 (判定档位, 达标档位序) 取更保守者 (新增 `_lane_rank`, 删「首命中即 break」); ③ `check_hr_satisfied` 分支逻辑不变 (site_satisfied 非 None 即采纳), 仅 docstring 同步。测试 +2 (`test_lane_verdict_ignores_remain_and_local` / `test_judge_record_double_hit_prefers_lane_order`) + 改写 1, 红验 3 条全红; 全量 **1601 passed + 1 skipped**。计划 v3.0 (§9/§12/§13/§14) |
| v3.5 CarPT 站点接入 (adapter 变体参数化) | **Done** | 2026-09-27: 用户令「HR在线核实添加支持站点: CarPT」(样张: 用户提供的 CarPT `myhr.php` 空表页, 2026-09-27)。样张核对: 状态参数 `?status=N`(1 考察中/2 已达标/3 未达标/4 已免罪), 表头 `td.colhead` 十列, 首列「H&R ID」, 「下载完成时间/剩余考察时间」列名, 末尾多备注/操作两列, 分页仍 nexus-pagination。实现: `NexusPhpMyhrAdapter` 构造参数化(`scope_param`/`scope_values`/`header_key`/`column_names`, 标准形态行为不变, `REQUIRED_COLUMNS` 兼容导出保留) + 新 `adapters/carpt.py`(`CarPtMyhrAdapter` 薄子类, 登录页识别换本站表头锚点) + 注册名 `"carpt"` + schema 帮助文案; `fetcher.py`/`report.py` 的 `_scope_of` 兼容 `status=`(排障展示与离线走查文件名)。测试 +5(CarPT fixture ×2: 数据页/空表样张结构) — 全量 **1693 passed + 1 skipped**(TOTAL 91% / 11227 / 815 / 3720 / 330), 基线 `26-09-27-1235` 已记。**待真机**: 数据行单元格形态(样张为空表)与 `download.php?id=` 实参(H&R ID 还是种子 id)待首刷核对 |
| 在线核实 v2 修改计划产出 (审计报告转化) | **Done** | 2026-09-27: 报告 26-09-26-1628 → [plans/26-09-27-1815](../plans/26-09-27-1815-plan-hr-verify-audit-fixes.html) (doc-status Open) —— 承接主计划 §14 M5.1–M5.5 骨架展开成文件级修改项 + 补齐 §14 未吸收的 P1 骤降保护/空表口径、P2 放行对账撤销/多实例引导、P3 登录退避/端点纵深; 新增配额激活门 / 单轮预算轮转 / 扩展 caps 上调三个设计点; 汇总 D1–D10 十项拍板 + 3 项前置实测; 产出时现场复核 (cbc4b80) 报告符号引用全部成立。**代码未动** |
| M5.1–M5.5 实施 (在线核实 v2) | **Done** (代码侧) | 2026-09-27 22:18: 用户令「实施计划 26-09-27-1815, 拍板按推荐」⇒ 五步全部落地, 每步独立全量绿 + 一红验 (M5.1 1763 → M5.2 1774 → M5.3 1787 → M5.4 1795 → 收尾 1796 passed + 3 skipped, 91%)。要点与三个实施决策见进度日志 2026-09-27 22:18 条; **余真机走查 + M0 前置实测三项**(阻塞早停②/豁免 A 的启用, 不阻塞代码) |
| v3 波次模型重建 (计划 26-09-28-1932 M1–M5) | **Done** (代码侧, 真机走查待) | 2026-09-29: 四行判定表重写 `hr/resolve.py`(HrIdentity: HR/RELEASED/NO_EVIDENCE, 12 格矩阵单测) + 波次引擎重写 `hr/service.py`(单波型 + A/B/C 轮流 + 三停翻条件①②③ + 档位级截断式有效性 + 失踪观察期 + 三道防伪 + 身份登记一次下载规则) + 单频控重写 `hr/ratelimit.py` + 熔断/停用/退避删除 + 配置 40→14 键 (config v2→v3 迁移 / hr_site v1→v2 迁移 / 档案 listing 字段) + `--hr-resume` 删 / `--hr-confirm-empty` 增 + WebUI 状态块重写与确认戳按钮 + keys.md 回写与键面基线重生成; 全量 1743 passed + 3 skipped; 真机走查(M0 剩余项 + 扩展 reload)仍开放 |
| 实报修复: 放行签发即作废 + 端点未监听 (v3 落地三缺陷) | **Done** | 2026-09-29 18:21: 用户实报「HR 热重载后种子仍显示本地兜底 + 扩展连不上端点 + NameError」⇒ 三处同族缺陷: ①`service.py::_freeze_terminal` 引用**未导入**的 `LANE_SATISFIED`(v3 重建起潜伏, 真机走到那一行才炸并崩整波) ②冻结/观察期签发的放行记录**漏带锚点快照** ⇒ `drift_reason` 把 `anchor_downloaded=0` 读成「downloaded 增长」, 记录**签发当刻作废**(用户症状「已在线核实过却显示本地兜底」; 计划 §7.2 明写 verified 含锚点) ③`HrRuntime.apply` L0 重建路径新建端点却不 `start()` ⇒ 端口从未绑定(扩展连不上, 取数线程照样派发任务白等 180s)。修复: 三处签发收敛单点 `_release_record`(带快照) + `HrVerified.has_anchor_snapshot`(无快照不作废) + L0 路径补端点启动; 既有守阵 `test_terminal_vanish_writes_release` 被揭穿常年**假绿灯**(夹具让目标分支不可达), 重塑并红验 4 条。全量 **1743 passed + 4 skipped (91%)**, 基线 26-09-29-1821(final: 同会话追加「端点未监听快速失败 + 观测期守阵加固」后 **1745 passed + 4 skipped**); 档案 [tasks/26-09-29-backend-hr-release-deadend.md](26-09-29-backend-hr-release-deadend.md) |
| v2 实施核对 + 安全/稳定性审计 | **Done** (纯审计, 代码未动) | 2026-09-28 00:30: 报告 [26-09-28-0030](../reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html) —— M5.1-M5.5 共 33 项逐条以 file:line 核对全落地; 安全面五道边界/稳定性六维度全核对; 新发现 F1(P2)/F2(P3)/F3(P3)/F4(P4) 见报告 §2 与切片「未完成」; 处置待用户拍板 |
| v3.1 计数集成修改计划产出 (报告 1803 转化) | **Done** (纯文档, 代码未动) | 2026-09-29 20:36: [plans/26-09-29-2036](../plans/26-09-29-2036-plan-hr-counter-integration.html) (doc-status Open) —— 报告 §7 草案对照代码基线 b6ce666 收口成触点清单 (M1 七文件) + 里程碑 M1-M3 + 六类测试 + 命中不受影响不变量; 三处设计定稿 (逐页提取首非 None 合并 / 收紧落点改 releases_enabled 单点 AND 门 / 截断波差值≠mismatch) + 新识别 T1 迁移陷阱 (旧档案 count_claim 误读 0 ⇒ 全站假 mismatch); 拍板点 P1-P4 待用户, M1 零拍板依赖可开工 |
| v3.1 计数集成 M1 核心对平机制 | **Done** (代码侧; M2 等样张+拍板, M3 缓做) | 2026-09-29 21:47: 用户令「按计划实施 M1」⇒ 触点 7 文件落地: `model.py` HrLaneState +3 additive 字段 (from_json 显式判空挡 T1 陷阱, 不抬 schema 版) / `adapters/base.py` 默认钩子 `parse_counters(html)={}` (契约三条进 docstring) / `service.py` 波内 counter_claims 首非 None 胜出 + `_finish_wave` 对平记账 + **唯一行为变更点** (releases_enabled 追加 `and not depth_broken`) + 零行自证 OR 分支 (三档 claim=0 视同人工戳) + 截断差值进 notes / `events.py` counter_mismatch 文案 (含口径校准引导) / `status.py` LaneStatus +2 字段与 rows/claim·对不平 展示 / report.py 走 lane_texts 单点零直改; 测试 T1–T6 七用例 + 红验闭环 (移门 T2/T5① 红 → 还原绿); 全量 **1756 passed + 3 skipped / 90%**, 基线 26-09-29-2147; M1 全 adapter 默认无计数 ⇒ 无计数站点行为与基线逐位一致 |
| v3.1 计数集成 M2 两站启用 (CarPT + BTSchool) | **Done** (代码侧; 真机走查 + R7 拍板待) | 2026-09-29 23:17: 用户给 D2 样张(C:/Users/11059/Desktop/Projects/PT页)并拍板口径 ⇒ 载体定形**页头摘要形**(页头状态栏「H&R:」计数条每页都有、与分页解耦 —— 计划原假设 CarPT 走分页区间形被样张证伪: 区间终点在早停页==已抓行数, 对「翻页标记失效」这一目标失效模式无保护); `nexusphp.py` 共享 `header_hr_numbers`(先剥标签再取数 —— 红 span 的 style 属性带数字) / `btschool.py` 新薄子类 2 数=考察中/未达标(考察中位样张实证: 页头 1 == A 档实抓 1 行; 位 1 非已达标反证: 已达标样例 50 行而页头 1) / `carpt.py` 覆写 3 数=考察中/未达标/上限(上限是处罚阈值不采, B 无声明不猜) / `ADAPTERS` 注册 btschool + 站点档案 adapter 改 btschool(loaders 派生视图自动生效, 无存量迁移) / docs/configuration.md 补「计数口径校准」节; 8 新用例 + 夹具按样张原文定形; 全量 **1767 passed + 3 skipped / 91%**(远端 WebUI 三修复合流后复测), 基线 [26-09-29-2317](../testing/baselines/26-09-29-2317-hr-counter-m2.md) |
| v3.1 计数集成 M3 退役与打磨 | **Done** (代码侧; 真机走查待用户侧) | 2026-09-30 00:24: 用户令「按计划实施 M3」并随问随拍两板: **R7 = 现状观察**(冻结方向保守 + 告警自带走查引导 + 连续 3 波 ERROR 升级, 信号充分; 当前账号 A/C 全 0 或对平风险未激活, 真出现再另立豁免计划), **P3 备选项全缓做**(M3 只做计划 §4 两件小事)。落地: ①提示语收尾 —— `--hr-confirm-empty` 帮助文案(cli.py)与 WebUI 确认戳弹窗(hr_status.js)补「页头计数可自证空集的站点无需人工确认」; ②展示口径对齐(实施期发现: 行为面 service.py:992 已认计数自证, 展示面 empty_confirmed 只认人工戳 ⇒ 计数自证站点被误标「零行未确认」+ 误报「需人工对账」) —— status.py 新增 `count_attested_empty`(SiteStatus 字段 + 与 service 同式 helper `count_attested_empty()`) 并进 `blocking_reason` 零行卡点分支, report.py 零行尾注三分支(已人工确认/计数自证空集/未确认); ③WebUI —— 站点状态块「各档波次」徽章化(`hrsLaneBadge`/`hrsLaneClass`: rows/声明 + 对不平 warn + 失效 error, 数字全来自后端 s.lanes), 自证空集站点摘「零行未确认」标签与「确认空清单」按钮、换「计数自证空集」ok 徽章。测试: T4 补展示对齐断言 + `test_zero_rows_no_release` 重排两波夹具(首波立索引让零行卡点分支可达 —— 索引全空时 blocking_reason 先报「还没有任何可判数据」) + 新增 `test_run_hr_status_zero_row_counter_attested_tail`(report 尾注守阵); docs/configuration.md 计数节补展示对齐段。全量 **1768 passed + 3 skipped / 91%**(f39413b0 上实测), 基线 [26-09-30-0024](../testing/baselines/26-09-30-0024-hr-counter-m3.md) |
| 四现象故障取证 (仍拉取x2 / 未核实 / 失踪 0 波) | **Done** (纯取证, 代码未动) | 2026-10-03 15:30: 四阶段串行子智能体 (P1 机制定位 / P2a 症状1-3 / P2b 症状4 / P3 报告), 零异常失败; 生产数据在主 clone auto-qb-data 只读取证 (本 clone 无运行数据)。结论: 引擎数据/判定侧零故障 —— ①②「仍拉取」=设计内 (账号级对账取数, 闸门 service.py:448-496 无一读本地种子状态, 波内零种子下载; 「该站点本地没有 HR 种子」=明细表空态文案, local_present=本地库存在含暂停, 实测本地与清单零交集); ③「未核实」=设计内+文案粒度缺陷 (命中 B 刻意不写放行, _record_hit service.py:861-867 只删, satisfied 唯一写点 _freeze_terminal 需行消失+位置证明; data.verified 与运行时视图双通路结构性矛盾, BTSchool 50 / CarPT 17 活跃 B 行 0 verified 实证, 守阵 test_hr_service.py:744); ④退役行 missing_streak 结构性恒 0, 09-28 07:14:04=v2 末次页面合并笔迹 (142 行单秒批量冻结), 127.1h=25.4 波槽 / 实际 >=14 波。报告 [26-10-03-1505](../reports/26-10-03-1505-report-hr-fetch-verify-forensics.html); 候选缺陷 wave_ts 跨波冻结 (service.py:517-523+649-651) 与 142 行 10-28 过 INDEX_RETENTION 静默清出, 均未入池待指派 |

## 进度日志
- **2026-10-03 15:30 (四现象故障取证 —— 纯文档轮, 代码未动)** — 用户报四现象 ⇒ P1-P3 串行子智能体取证, 报告 [26-10-03-1505](../reports/26-10-03-1505-report-hr-fetch-verify-forensics.html) 出厂并挂本档案 Topics。核心结论与证据链见子任务状态表新行与报告; 补充不可考项: 盲窗成因 (09-28 07:14 后页面为何零解析, 扩展超时/登录页/站点批量移出三说并存) 与本地 BTSchool 种子零交集成因 (毕业后已删为吻合解释) —— v2 期日志被 09-29 03:25 部署崩溃循环 (RecursionError x6) 轮转清空 / 磁盘不可考, 均不影响根因判定。30 天淘汰预测: 142 行 10-28 07:14 后首波静默清出 (仅删 index, verified 永续 model.py:250-256, 判定零影响 resolve.py:371-391, 仅 entry_details 消失)。收尾: 同步 @ 61c0ddc4 (stash->sync->pop, 与远端流量图 P3/P4 + copytext 轮的索引重生成零冲突); test.full 闸门数字见 kb.baseline 最新切片, 基线切片随本轮入库。**修复建议 (报告: 设计确认 1 / 显示文案 4 / 次要 3) 与两项入池候选等用户指派, 本轮未动代码未入池**。
- **2026-09-30 00:24 (v3.1 计数集成 M3 落地 —— 退役与打磨代码轮)** — 用户令「按计划实施 M3」并预告「有待拍板的询问」(两站样张仍在 C:/Users/11059/Desktop/Projects/PT页)。开工核对代码时发现**展示口径不一致**: 行为面 `_finish_wave` 的 confirmed_empty(M1 §2.5)已认「各档声明全 0」自证空集, 但展示面三处(SiteStatus.empty_confirmed 只映射人工戳 / blocking_reason 同款条件 / report 零行尾注两分支)仍只认 `empty_confirmed_at` ⇒ 计数自证空集的站点会被误标「零行未确认」、误报「现在不放行: 需 --hr-confirm-empty」—— 行为真值正确, 纯展示层谎言, 收进 M3-1 一并对齐。**拍板两项**(AskUserQuestion): R7 = **现状观察**(另立豁免计划被否 —— 理由: 冻结方向保守只拦批量签发, 命中/观察期/终态不受影响; 告警文案自带「可能是口径校准错误」引导 + 连续 3 波 ERROR 升级, 信号充分; 当前账号 A/C 全 0 或对平, 风险未激活), P3 备选项(末页追翻省略/总数轴互证/登录态佐证)= **全部缓做**(M3 只做计划 §4 定的两件小事)。落地三件: ①提示语收尾(cli.py `--hr-confirm-empty` help + hr_status.js 确认弹窗补「页头计数可自证空集的站点无需人工确认」); ②展示对齐(status.py 新增模块级 `count_attested_empty(data)` helper 与 SiteStatus 字段, 与 service.py:992 同式 —— 对持久化波次复算, 零行 ∧ 各档声明全 0; blocking_reason 零行分支补该豁免; report.py 零行尾注三分支); ③WebUI(settings-detail.html「各档波次」由纯文本换逐档徽章 —— hr_status.js 新 `hrsLaneBadge`/`hrsLaneClass`, 内容 `A 有效: N页M行(全) · M/声明N` + 对不平 warn/失效 error, 数字全来自后端 `s.lanes` 不重算; 头部标签: 自证空集站点摘「零行未确认」warn 与「确认空清单」按钮, 换「计数自证空集」ok 徽章; 确认按钮条件同步三联)。测试三处: T4 补两断言(count_attested_empty True + blocking 空)、`test_zero_rows_no_release` 重排两波夹具(首波 `myhr_page([row(11,"EXAMPLE 11")])` 立索引, 次波 EMPTY_TABLE_PAGE —— 索引全空时 blocking_reason 先报「还没有任何可判数据」, 零行卡点分支不可达, 单波空表夹具够不着它)、test_hr_report 新增 `test_run_hr_status_zero_row_counter_attested_tail`(monkeypatch build_adapter 三档声明 0, 断言尾注「计数自证空集, 无需人工确认」且全文无 --hr-confirm-empty 话术)。全量 **1768 passed + 3 skipped / 91%**(12403 语句 / 997 未覆盖, test.full 19.5s; develop f39413b0 无远端新提交), 基线切片 [26-09-30-0024](../testing/baselines/26-09-30-0024-hr-counter-m3.md)。docs/configuration.md 计数节补「展示面与行为面同口径」段。计划 v1.3 + 状态改「M1+M2+M3 Done(拍板全闭)」。收尾踩已记坑 cap-counting(追加未量余量 25,574>24,000 + 归一脚本 5 文件拍成 LF + 随迁链接层级坏链, 复发 +1): M1 修复轮与 M2 两条日志外迁 attachments、全改动文件归一 CRLF、链接改 `../../` 收口。**未提交**(等用户显式指令)。
- **2026-09-29 23:17 (v3.1 计数集成 M2 落地 —— 两站启用代码轮)** — 已外迁: [attachments/26-09-22-backend-partial-hr-verify-log.md](attachments/26-09-22-backend-partial-hr-verify-log.md); 摘要见本档案子任务状态表「v3.1 计数集成 M2」行与基线切片 [26-09-29-2317](../testing/baselines/26-09-29-2317-hr-counter-m2.md)。


- **2026-09-29 22:12 (M1 修复轮: fail_streak 清零 + events 重复常量 + 计划 v1.1)** — 已外迁: [attachments/26-09-22-backend-partial-hr-verify-log.md](attachments/26-09-22-backend-partial-hr-verify-log.md); 摘要见本档案子任务状态表与基线切片 26-09-29-2147 追加修复轮复测段。

- **2026-09-29 21:47 (v3.1 计数集成 M1 落地 —— 代码轮)** — 已外迁: [attachments/26-09-22-backend-partial-hr-verify-log.md](attachments/26-09-22-backend-partial-hr-verify-log.md); 摘要见本档案子任务状态表「v3.1 计数集成 M1」行与基线切片 [26-09-29-2147](../testing/baselines/26-09-29-2147-hr-counter-m1.md)。

- **2026-09-29 20:36 (v3.1 计数集成修改计划产出 —— 纯文档轮, 代码未动)** — 用户令「按照报告出一个修改计划」。
  [plans/26-09-29-2036-plan-hr-counter-integration.html](../plans/26-09-29-2036-plan-hr-counter-integration.html) 出厂
  (doc-status Open)。设计定稿相对报告 §7 草案三处收口: ①提取契约 = adapter 逐页 `parse_counters(html)` +
  service 侧首非 None 合并 (tab 形第 1 页全档有据, 分页区间形末页才有据); ②收紧落点改 `releases_enabled`
  单点 AND 门 (`depth_broken`), 不折叠 `full_depth` 赋值 —— 观察期出口 (:943 在闸门之前) 与终态冻结
  (:962 走位置覆盖) 逐字不动, 报告「只影响批量签发」口径精确成立; ③mismatch 判定边界排除截断/早停波
  (rows<claim 是量化差值进 notes, 不告警不冻结)。**新识别 T1 迁移陷阱**: from_json 若走 `_as_int` 缺省路径,
  旧档案无键会被读成 count_claim=0 ⇒ 全站假 mismatch ⇒ 批量签发永久冻结 —— 守阵钉死。里程碑: M1 核心
  机制 (全 adapter 默认无计数 ⇒ 上线即现状, 零拍板依赖) / M2 两站启用 (前置 D2 样张 + P2 校准策略,
  推荐方案 A 硬编码) / M3 退役与打磨。测试六类 + 不变量 + 红验。认领链五处回写 (报告 1803 / 计划 1932 /
  审计 0404 / 审计 0030 / 本档案); test.full 首跑 2 红均为守卫按预期拦截 (索引未重建 + 认领链单向),
  回写后复跑全绿 1749 passed + 3 skipped (90%, 与基线一致, 无代码变更不新建基线切片)。

- **2026-09-29 (HR 计数可行性分析 —— 纯文档轮)** — 用户问「HR 页计数能否佐证完整性/简化模型/增强安全稳定」。报告出厂
  [reports/26-09-29-1803-report-hr-counter-verify.html](../reports/26-09-29-1803-report-hr-counter-verify.html) —— 结论: 计数是清单的
  校验和非替代品, 补绝对量轴堵 B/C 档批量误放行洞; 用户实测两站均有计数(CarPT 存档分页区间 1-17 对平实证); 裁决点 D1-D4 待拍板, 未动代码。

- **2026-09-29 (v3 波次模型重建 M1–M5 全落地 —— 代码大改轮)** — 已外迁: [attachments/26-09-22-backend-partial-hr-verify-log.md](attachments/26-09-22-backend-partial-hr-verify-log.md); 摘要见本档案子任务状态表「v3 波次模型重建」行与 [plans/26-09-28-1932](../plans/26-09-28-1932-plan-hr-verify-rebuild.html)。

- **2026-09-28 00:30 (v2 实施核对 + 安全/稳定性审计 —— 纯审计轮)** — 已外迁: [attachments/26-09-22-backend-partial-hr-verify-log.md](attachments/26-09-22-backend-partial-hr-verify-log.md); 摘要见本档案子任务状态表「v2 实施核对」行与报告 [26-09-28-0030](../reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html)。

- **2026-09-27 22:18 (M5.1–M5.5 全部落地 —— 在线核实 v2 代码侧完成)** — 已外迁: [attachments/26-09-22-backend-partial-hr-verify-log.md](attachments/26-09-22-backend-partial-hr-verify-log.md); 摘要见本档案子任务状态表 M5.1–M5.5 行与报告 [26-09-28-0030](../reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html)。

- **2026-09-27 18:15 (v2 修改计划产出 = plans/26-09-27-1815) 与 12:54/12:46 (提交轮 + v3.5 补验「双 id 空间」真缺陷修复) 三条日志已外迁**: [attachments/26-09-22-backend-partial-hr-verify-log.md](attachments/26-09-22-backend-partial-hr-verify-log.md)(档案触顶处置); 摘要见 activeContext 切片。
- （本段更早的进度纪要已外迁: [attachments/26-09-22-backend-partial-hr-verify-log.md](attachments/26-09-22-backend-partial-hr-verify-log.md) —— 触顶处置见 `.agents/skills/memory-bank/scripts/_common.py` 的 `TASK_LOG_CAP`）

- **2026-09-29 (v3 跟进修复: WEBUI 站点接入卡片 mode→enabled 口径)** — v3 重构(be83d61)把
  `hr_check.sites.<档案>` 收敛为 `enabled/tracker/refresh_interval` 三键, 但设置页「站点接入」
  卡片前端仍按旧三态写 `mode`, 保存即被 validate_config 拒(未知键 ['mode'], btschool/carpt 实报)。
  修: config_hub.js `hrSiteMode/SetMode`→`hrSiteEnabled/SetEnabled`(布尔, 关闭且条目不存在时不写
  垃圾键), 首页读数按 enabled 真值计数, 微调表改滤 enabled; settings-detail.html 三态下拉换
  「启用在线核实」勾选框。纯前端两文件, node --check 通过; 存量 `mode` 由 `_migrate_config_2_3`
  加载期自动转换, 无需手工改。

- **2026-09-29 (v3 跟进修复②: 行 4 判定无限递归 RecursionError)** — `check_hr_satisfied` 的
  行 4(站点无有效证据)回落分支调 `check_hr_condition()`, 而后者行 4 又调回 `check_hr_satisfied()`
  —— 站点已接入 + 判定落行 4(取数未产出证据 / 全站型 listing=none)即无限递归, BTSchool 实报;
  主循环每轮重试重复报错形似「无限循环」。record 级测试的行 4 只测过「桥返回 None」路径
  (该路径 check_hr_condition → _local_hr_triggered 不递归), 「桥返回 NO_EVIDENCE」无覆盖故漏网。
  修: 行 4 回落直调纯本地判据 `_local_hr_triggered()`(走到该行时 judged 只能是 None/NO_EVIDENCE,
  check_hr_condition 站点侧分支均已返回, 语义等价)。test_torrents.py 补
  test_record_hr_no_evidence_row4_no_recursion(触发/未达标/达标 + 纯辅种不触发);
  test.quick 1736 passed + 3 skipped。

- **2026-09-29 (复审落地: 骤降保护移除 + 复审缺陷 H1/M1/M2 修复)** — 已外迁: [attachments/26-09-22-backend-partial-hr-verify-log.md](attachments/26-09-22-backend-partial-hr-verify-log.md); 摘要见报告 [26-09-29-0404](../reports/26-09-29-0404-report-hr-verify-v3-audit.html)与本表「v3 波次模型重建」前后行。
