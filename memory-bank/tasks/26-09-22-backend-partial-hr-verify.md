# 26-09-22-backend-partial-hr-verify — 部分种子 HR 的在线核实

**Status:** Open
**Added:** 2026-09-22
**Updated:** 2026-09-28
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
**Topics:** backend-partial-hr-verify
**Refs:** memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html, memory-bank/plans/26-09-27-1815-plan-hr-verify-audit-fixes.html, memory-bank/plans/26-09-28-1932-plan-hr-verify-rebuild.html, memory-bank/reports/26-09-26-1628-report-hr-online-verify-audit.html, memory-bank/plans/26-09-25-1823-plan-webui-hr-safety-display.html, memory-bank/tasks/26-09-25-webui-hr-safety-display.md, memory-bank/plans/26-09-26-0031-plan-hr-ext-options-style.html, memory-bank/reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html

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
| v2 实施核对 + 安全/稳定性审计 | **Done** (纯审计, 代码未动) | 2026-09-28 00:30: 报告 [26-09-28-0030](../reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html) —— M5.1-M5.5 共 33 项逐条以 file:line 核对全落地; 安全面五道边界/稳定性六维度全核对; 新发现 F1(P2)/F2(P3)/F3(P3)/F4(P4) 见报告 §2 与切片「未完成」; 处置待用户拍板 |

## 进度日志

- **2026-09-29 (v3 波次模型重建 M1–M5 全落地 —— 代码大改轮)** — 用户令「按照计划重构 HR 在线核实
  26-09-28-1932」。五步一次落完: **M1** 判定重写(`resolve.py` 四行判定表, HrIdentity 收敛三态
  HR/RELEASED/NO_EVIDENCE, `NO_EVIDENCE` 即判定表行 4 —— 本地兜底在调用方 `check_hr_condition` 合成;
  satisfied 独立于受管束 —— 命中 B 毕业也达标; `record.py` 双入口重写, 消费点零接口变化); **M2**
  波次引擎(`service.py` 重写: 对象集 = 未对账∪考察中现算, 三停翻条件, A 档行无条件下载 + 终态行
  宽泛粗配触发(归一后完全相等也算疑似), 档位级截断(表头/字段/排序三种失效, 失效点前有效), 批量
  「未列出」签发要过防伪三道闸, 失踪观察期独立推进与防伪解耦, 终态冻结落放行记录); **M3** 单频控
  (`ratelimit.py` 重写, 账本 `HrRateLedger` 日窗口 + 间隔基准; Retry-After 单存 `retry_after_until`);
  **M4** 配置(models/schema/loaders/validation/impact/migrations 五处同步, `_migrate_config_2_3`
  删 26 废弃键 + mode→enabled + `enabled` 键原样保留(治「无版本章新配置被当 v1 误杀」), hr_site
  v1→v2 迁移删双桶/熔断/停用账本, 档案 `listing` 字段 + `required_seeding_time` 派生); **M5**
  status/report/worker/CLI/events/WebUI 波次视图(`--hr-confirm-empty` 新增 + `/api/hr/confirm-empty`
  路由 + `--hr-resume` 删除)。**实施中修掉的真 bug**: 轮转循环「末页/停翻 break」吞掉同轮其它档位
  取数机会(改 continue); 无版本章新配置在 v2→v3 迁移被清空 enabled。测试: HR 九文件按新模型重写
  (resolve 35 / service 29 / ratelimit 8 / config 29 / report 18 / store 17 / runtime 28 / worker 21 /
  multisite 5), 键面基线 `commands run test.keys-update` 重生成, keys.md 同步; 全量 **1743 passed +
  3 skipped**(test.quick 实测; 基线切片另记)。**未提交**(等用户显式指令); 真机走查仍开放。

- **2026-09-28 00:30 (v2 实施核对 + 安全/稳定性审计 —— 纯审计轮, 代码/文档零改动)** — 用户令「分析
  plans/26-09-27-1815 实施情况, 重点是安全性/稳定性/BUG, 并写报告含 HR 在线核实现状 (配置/默认节奏/
  限流)」。开工预检 `my-commit-flow.sync` PASS (与主线齐平 c7dfbd20)。产出:
  [reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html](../reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html)。
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

- **2026-09-27 18:15 (v2 修改计划产出: 审计报告 26-09-26-1628 转化为 plans/26-09-27-1815 —— 纯文档,
  代码未动; 含承接不重证 / P1-P3 缺口补齐 / 三个实施设计点 / D1-D10 拍板汇总 / 认领链踩坑复发 +1 /
  v1.1 骤降判据细化)** — 原文已外迁: [attachments/26-09-22-backend-partial-hr-verify-log.md]
  (attachments/26-09-22-backend-partial-hr-verify-log.md)(档案触顶处置); 摘要见 activeContext 切片。
- **2026-09-27 12:54 (提交轮: 合并远端 + 合并树重测零漂移) 与 12:46 (v3.5 补验: 已达标样张验证 + 「双 id 空间」真缺陷修复
  —— H&R ID 与种子 id 是两个空间, dl_id 落地) 两条日志已外迁**: [attachments/26-09-22-backend-partial-hr-verify-log.md]
  (attachments/26-09-22-backend-partial-hr-verify-log.md)(档案触顶处置); 摘要见 activeContext 切片「已交付 · v3.5」。
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
