# 26-09-22-backend-partial-hr-verify — 部分种子 HR 的在线核实

**Status:** Open
**Added:** 2026-09-22
**Updated:** 2026-09-25
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
**只差真机走查**(M0 四项实测 + 装扩展后跑一轮真实取数) —— 计划见 memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html (§13 决策记录与 M0 实测清单)。
**Topics:** backend-partial-hr-verify
**Refs:** memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html, memory-bank/plans/26-09-25-1823-plan-webui-hr-safety-display.html, memory-bank/tasks/26-09-25-webui-hr-safety-display.md

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

## 进度日志

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
 (第七批: 取证误读修复 —— `--hr-status` 明细表改版 + 已取记录逐文件 ts)** —
  用户拿 `hr/BTSchool.json` 取证问「是否短时间产生了大量种子下载」(分析结论: 无 —— 当天对站点仅 5 次请求
  = 3 页 + 2 个 .torrent, 全在频控内; `downloaded[]` 是「已取 .torrent」凭据不是 qB 下载), 顺带点出两处真问题:
  ① `hr_downloaded[].ts` **整批共用开始时刻**(同批两条微秒级相同 ⇒ 看着像瞬间批量下载, 取证误读);
  ② `--hr-status` 明细的「剩余达标」列(9d21h)会被读成「还要做种 9 天」—— 它实际是**考核窗口**
  (9d21h 内要完成做种要求), 真正的「还需做种时间」只有 16h57m。
  修: ① `_fill_infohashes` 的 ts 改记**各 .torrent 自己的取回时刻**(顺带同源的 `fail.last_ts` 一并修准);
  ② 明细表列 = tid / 档位(考察中·已达标·未达标·已免罪, 单点 `status.LANE_TEXTS`) / 上传量 / 下载量 / 分享率 /
  还需做种(镜像站点书写形态 HH:MM:SS·「N天HH:MM:SS」) / 名称(按**显示格宽**截断 40) / infohash;
  **剩余达标时间不再显示**; 列对齐走自写 `_dwidth/_pad`(str.format 按字符数对齐, CJK 双宽会错位)。
  测试 +2(service 1 钉逐文件 ts / report 1 钉 CJK 对齐·截断·列改版), 全量
  **1573 passed + 1 skipped**(TOTAL 91% / 10905 / 789 / 3582 / 327; HR 包 93%: 2782 / 143 / 766 / 91)。

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

- （本段更早的进度纪要已外迁: [attachments/26-09-22-backend-partial-hr-verify-log.md](attachments/26-09-22-backend-partial-hr-verify-log.md) —— 触顶处置见 `.agents/skills/memory-bank/scripts/_common.py` 的 `TASK_LOG_CAP`）
