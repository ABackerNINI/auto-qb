# HR 在线核实 — 全量相关文档清单

> 生成于 2026-09-28, 基于 develop @ c4846705。覆盖 memory-bank 中与「部分种子 HR 在线核实」
> (`backend-partial-hr-verify` 主任务及其衍生任务) 相关的全部文档: 计划 / 任务档案 / 附件 / 审计报告 / 测试基线 / 活动切片,
> 另附无固定日期的常青(代码侧)文档。路径相对仓库根; 表内链接相对本文件(`docs/`)。
>
> 时间口径: 文件名内嵌 `YY-MM-DD-HHMM` 者取该时点; 基线切片多记为「时分不可考」, 按切片内注明的
> **当日序位** 排序, 表中写作 `MM-DD #N`。

## 一、主线时间总表 (按时间升序)

| 时间 | 文档 | 类型 | 一句话内容 | 关联任务 |
|---|---|---|---|---|
| 09-22 22:04 | [partial-hr-site-verify-plan.html](../memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html) | 计划 | 可行性分析与实施计划: 浏览器扩展代取 + 后端解析对账 + 三态判定的总体蓝图, M1–M4 里程碑拆解 | backend-partial-hr-verify |
| 09-22 | [26-09-22-backend-partial-hr-verify.md](../memory-bank/tasks/26-09-22-backend-partial-hr-verify.md) | 任务档案 | **主档案**: M1 核心管道 → M2 取数通道 → M3 判定联动 → M4 多站点 → 七批实报修复 → v2.9/v3.0/v3.5 → M5.1–M5.5(v2) 全过程记录 | backend-partial-hr-verify |
| 09-22 | [attachments/…-log.md](../memory-bank/tasks/attachments/26-09-22-backend-partial-hr-verify-log.md) | 档案附件 | 主任务的会话滚动日志 | backend-partial-hr-verify |
| 09-24 #1 | [hr-m1-core-pipeline.md](../memory-bank/testing/baselines/26-09-24-0000-hr-m1-core-pipeline.md) | 测试基线 | 1233→1375(+142): 新包 `hr/` 全链路(bencode/parse/adapters/model/store/ratelimit/resolve/service/report/fetcher) + 配置接入 | backend-partial-hr-verify |
| 09-24 #2 | [hr-m2-fetch-channel.md](../memory-bank/testing/baselines/26-09-24-0000-hr-m2-fetch-channel.md) | 测试基线 | 1375→1466(+91): 端点+队列+fetcher+worker+runtime+MV3 扩展; 新键 `channel.extension_id`/`channel.request_timeout` | backend-partial-hr-verify |
| 09-24 #5 | [hr-alert-tiers-hr-status.md](../memory-bank/testing/baselines/26-09-24-0000-hr-alert-tiers-hr-status.md) | 测试基线 | 1476→1489(+13): HR 告警按被拦根因三档分级去重 + `--hr-status` 只读摊开已落盘数据 | backend-partial-hr-verify |
| 09-25 #3 | [ext-hidden-window-fetch.md](../memory-bank/testing/baselines/26-09-25-0000-ext-hidden-window-fetch.md) | 测试基线 | 1500→1502(+2): 扩展页面取数改用自己的最小化隐藏窗口(焦点守卫), 替代不可靠的后台标签页 | backend-partial-hr-verify |
| 09-25 #5 | [m3-judgement-linkage.md](../memory-bank/testing/baselines/26-09-25-0000-m3-judgement-linkage.md) | 测试基线 | 1504→1520(+16): 三态判定接进 TorrentRecord(判定桥 `hr_link` 稳定引用), 四个消费点零改动 | backend-partial-hr-verify |
| 09-25 #6 | [hr-fetch-fix-ext-quota.md](../memory-bank/testing/baselines/26-09-25-0000-hr-fetch-fix-ext-quota.md) | 测试基线 | 1526→1542(+15): 三真缺陷(页面饿死下载/不等间隔/无索引键误标)修复 + 扩展侧配额第二道闸 | backend-partial-hr-verify |
| 09-25 #7 | [m4-multisite.md](../memory-bank/testing/baselines/26-09-25-0000-m4-multisite.md) | 测试基线 | 1542→1562(+20): 四类事件语文化 / 站点级状态单一事实源 / WebUI 出口 / 多站点隔离 | backend-partial-hr-verify |
| 09-25 #11 | [ext-hr-logging.md](../memory-bank/testing/baselines/26-09-25-0000-ext-hr-logging.md) | 测试基线 | 1576→1579(+3): 扩展运行日志落码, `chrome.storage.local` 单一事实源; 抓到 flush 链自引用死锁 | webui-ext-hr-logging |
| 09-25 #13 | [hr-overage-exempt.md](../memory-bank/testing/baselines/26-09-25-0000-hr-overage-exempt.md) | 测试基线 | 1579→1596(+17): HR 超龄豁免——新站点级键 `completed_age_limit`, 判定侧豁免 + 翻页早停 | backend-partial-hr-verify |
| 09-25 #16 | [hr-v30-source-priority.md](../memory-bank/testing/baselines/26-09-25-0000-hr-v30-source-priority.md) | 测试基线 | 1602(+1): v3.0 达标判定「档位即结论」(`satisfied_verdict` 来源优先级), +2 守阵 | backend-partial-hr-verify |
| 09-25 18:23 | [plan-webui-hr-safety-display.html](../memory-bank/plans/26-09-25-1823-plan-webui-hr-safety-display.html) | 计划 | HR 在线核实的 WEB UI 呈现: 删除安全档位 × 来源档位(着色/徽标/删除确认点名/筛选/批量统计) | webui-hr-safety-display |
| 09-25 #17 | [webui-hr-safety-display.md](../memory-bank/testing/baselines/26-09-25-0000-webui-hr-safety-display.md) | 测试基线 | 1607(+1): 安全档位呈现落地; 双 UI 浏览器冒烟 94 项全过 | webui-hr-safety-display |
| 09-25 19:14 | [activeContext/…webui-hr-safety-display.md](../memory-bank/activeContext/26-09-25-1914-webui-hr-safety-display.md) | 活动切片 | 安全档位呈现收尾切片(已入库 441ffe4) | webui-hr-safety-display |
| 09-25 20:15 | [activeContext/…webui-hr-site-blank-screen.md](../memory-bank/activeContext/26-09-25-2015-webui-hr-site-blank-screen.md) | 活动切片 | 故障切片: 站点接入后 `hr.js` 三处漏 `this.` 致 Vue 整树白屏, 修复入库 c00fc94 | webui-hr-safety-display |
| 09-25 20:43 | [plan-webui-hr-popup-t1-spec-card.html](../memory-bank/plans/26-09-25-2043-plan-webui-hr-popup-t1-spec-card.html) | 计划 | HR 悬停弹窗模板三选一 · T1 档案卡 | webui-hr-popup |
| 09-25 20:43 | [plan-webui-hr-popup-t2-verdict-card.html](../memory-bank/plans/26-09-25-2043-plan-webui-hr-popup-t2-verdict-card.html) | 计划 | HR 悬停弹窗模板三选一 · T2 结论卡 | webui-hr-popup |
| 09-25 20:43 | [plan-webui-hr-popup-t3-progress-ledger.html](../memory-bank/plans/26-09-25-2043-plan-webui-hr-popup-t3-progress-ledger.html) | 计划 | HR 悬停弹窗模板三选一 · T3 进度仪表(最终定稿) | webui-hr-popup |
| 09-25 | [26-09-25-webui-hr-safety-display.md](../memory-bank/tasks/26-09-25-webui-hr-safety-display.md) | 任务档案 | WEB UI 安全档位呈现任务档案(实现与验收全部完成) | webui-hr-safety-display |
| 09-25 | [26-09-25-webui-ext-hr-logging.md](../memory-bank/tasks/26-09-25-webui-ext-hr-logging.md) | 任务档案 | 扩展运行日志任务档案(分级 + 环形上限 + 选项页④区) | webui-ext-hr-logging |
| 09-25 #20 | [hr-ext-config-simplify.md](../memory-bank/testing/baselines/26-09-25-0000-hr-ext-config-simplify.md) | 测试基线 | 1615(clone3 旧基座实测): HR 扩展配置简化(端点 `/api/hr/sites` + 站点勾选授权); 已被合流重测覆盖 | backend-partial-hr-verify |
| 09-25 #22 | [hr-sites-endpoint.md](../memory-bank/testing/baselines/26-09-25-0000-hr-sites-endpoint.md) | 测试基线 | 1618(clone3 中间态): `/api/hr/sites` + 站点勾选授权; 已被合流重测覆盖 | backend-partial-hr-verify |
| 09-26 00:31 | [plan-hr-ext-options-style.html](../memory-bank/plans/26-09-26-0031-plan-hr-ext-options-style.html) | 计划 | HR 取数代理扩展选项页风格选型(三选一) | backend-partial-hr-verify |
| 09-26 00:31 | [hr-safety-rework.md](../memory-bank/testing/baselines/26-09-26-0031-hr-safety-rework.md) | 测试基线 | 1629: 两线合流重测——HR 未达标红档语义修正(+0 改 4 处守阵) × 扩展选项页终态(+1) | backend-partial-hr-verify |
| 09-26 00:31 | [ext-options-terminal.md](../memory-bank/testing/baselines/26-09-26-0031-ext-options-terminal.md) | 测试基线 | 扩展选项页终态基线(与 hr-safety-rework 同点, 次级键定序) | backend-partial-hr-verify |
| 09-26 02:24 | [activeContext/…hr-popup.md](../memory-bank/activeContext/26-09-26-0224-hr-popup.md) | 活动切片 | HR 悬停弹窗 T3 落码收尾切片(随 09-26 提交入库) | webui-hr-popup |
| 09-26 04:25 | [single-line-hr-v34.md](../memory-bank/testing/baselines/26-09-26-0425-single-line-hr-v34.md) | 测试基线 | 1638(+1): v3.4 缺口——HR D 档已免罪来源单列 | backend-partial-hr-verify |
| 09-26 08:20 | [hr-popup-t3.md](../memory-bank/testing/baselines/26-09-26-0820-hr-popup-t3.md) | 测试基线 | 1666: HR 悬停弹窗 T3 落码(原生 title 换进度仪表浮层, `shared/hr.js` 单点); 合并工作树重测 | webui-hr-popup |
| 09-26 | [26-09-26-webui-hr-popup.md](../memory-bank/tasks/26-09-26-webui-hr-popup.md) | 任务档案 | HR 悬停弹窗任务档案(做种时长/来源徽标 hover popover, T3 定稿) | webui-hr-popup |
| 09-26 16:28 | [report-hr-online-verify-audit.html](../memory-bank/reports/26-09-26-1628-report-hr-online-verify-audit.html) | 审计报告 | HR 在线核实设计审查: 触发模型 / 访问节奏 / 安全可靠性(此报告后转化为 09-27-1815 修改计划) | backend-partial-hr-verify |
| 09-26 16:33 | [hr-audit-report.md](../memory-bank/testing/baselines/26-09-26-1633-hr-audit-report.md) | 测试基线 | 1666(持平): 审查报告落盘纯文档轮, 验证报告通过文档形态守阵 | backend-partial-hr-verify |
| 09-27 12:35 | [activeContext/…backend-hr-carpt-site.md](../memory-bank/activeContext/26-09-27-1235-backend-hr-carpt-site.md) | 活动切片 | CarPT 接入收尾: v3.5 经用户样张验证; 挖出「H&R ID 与种子 id 是两个 id 空间」真缺陷已修(`HrEntry.dl_id`) | backend-partial-hr-verify |
| 09-27 12:35 | [hr-carpt-adapter.md](../memory-bank/testing/baselines/26-09-27-1235-hr-carpt-adapter.md) | 测试基线 | 1693: CarPT 变体 adapter(`?status=N` + H&R ID 十列表头), NexusPhpMyhrAdapter 参数化 | backend-partial-hr-verify |
| 09-27 12:46 | [hr-carpt-dlid.md](../memory-bank/testing/baselines/26-09-27-1246-hr-carpt-dlid.md) | 测试基线 | 1693: CarPT status=2 已达标样张(17 行)验证通过 + dl_id 修复 | backend-partial-hr-verify |
| 09-27 12:54 | [post-merge-hr-carpt.md](../memory-bank/testing/baselines/26-09-27-1254-post-merge-hr-carpt.md) | 测试基线 | 1693: 合并远端(webui 模板共享化)后重测, 数字零漂移 | backend-partial-hr-verify |
| 09-27 13:18 | [plan-hr-check-site-presets.html](../memory-bank/plans/26-09-27-1318-plan-hr-check-site-presets.html) | 计划 | HR 在线核实配置收敛: 内置站点档案(`config/site_presets.py`) + 站点配置上收 `hr_check.sites` 分区 | hr-check-site-presets |
| 09-27 14:20 | [hr-site-presets.md](../memory-bank/testing/baselines/26-09-27-1420-hr-site-presets.md) | 测试基线 | 1700: 配置收敛三里程碑落地(btschool/carpt 两档内置档案, 键 = 档案 id 点选启用) | hr-check-site-presets |
| 09-27 15:23 | [activeContext/…hr-site-presets.md](../memory-bank/activeContext/26-09-27-1523-hr-site-presets.md) | 活动切片 | 配置收敛收尾切片(plans 1318 REV2 全部落地: 后端 + 配置面/UI + 文档) | hr-check-site-presets |
| 09-27 15:47 | [report-docs-implementation-audit.html](../memory-bank/reports/26-09-27-1547-report-docs-implementation-audit.html) | 审计报告 | 全库 plans/reports 实施状态清点与漂移审计(含 HR 线清点: 只差真机走查; 弹窗 T1/T2 状态漂移等) | 全库(含 HR) |
| 09-27 15:47 | [activeContext/…docs-implementation-audit.md](../memory-bank/activeContext/26-09-27-1547-docs-implementation-audit.md) | 活动切片 | 上述清点审计的过程切片(61 计划 + 13 报告交叉核对) | 全库(含 HR) |
| 09-27 18:15 | [plan-hr-verify-audit-fixes.html](../memory-bank/plans/26-09-27-1815-plan-hr-verify-audit-fixes.html) | 计划 | **在线核实 v2**: 审计报告转修改计划——M5.1–M5.5 实施拆解 + P1/P2/P3 修复落点 + 10 项待拍板 | backend-partial-hr-verify |
| 09-27 18:38 | [hr-verify-audit-plan.md](../memory-bank/testing/baselines/26-09-27-1838-hr-verify-audit-plan.md) | 测试基线 | 1742(+3 skipped): 审计报告转修改计划轮(纯文档, 代码零改动) | backend-partial-hr-verify |
| 09-27 19:30 | [plan-hr-binding-tracker-mapping.html](../memory-bank/plans/26-09-27-1930-plan-hr-binding-tracker-mapping.html) | 计划 | HR 站点绑定改映射制: web 域与 announce 域两命名空间永不互相比对, 双域档案 + 已知映射零配置 + 旧键迁移 v1→v2 | hr-binding-tracker-mapping |
| 09-27 20:22 | [activeContext/…hr-binding-tracker-mapping.md](../memory-bank/activeContext/26-09-27-2022-hr-binding-tracker-mapping.md) | 活动切片 | 映射制实施完成 + 写回事故修复 + config 迁移物化重构落地 | hr-binding-tracker-mapping |
| 09-27 20:22 | [hr-binding-tracker-mapping.md](../memory-bank/testing/baselines/26-09-27-2022-hr-binding-tracker-mapping.md) | 测试基线 | 1752(+3): 映射制轮落地(档案双域硬编码 + 默认映射查表 + 迁移) | hr-binding-tracker-mapping |
| 09-27 20:35 | [hr-m5-implemented.md](../memory-bank/testing/baselines/26-09-27-2035-hr-m5-implemented.md) | 测试基线 | 1796(+3): **M5.1–M5.5 全部落地, 在线核实 v2 代码侧完成**(判据观测/信号处置与停用/配额拆分双令牌桶等) | backend-partial-hr-verify |
| 09-27 | [26-09-27-config-hr-binding-mapping.md](../memory-bank/tasks/26-09-27-config-hr-binding-mapping.md) | 任务档案 | HR 绑定映射制任务档案(含旧键迁移 v1→v2) | hr-binding-tracker-mapping |
| 09-28 00:30 | [report-hr-verify-v2-impl-audit.html](../memory-bank/reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html) | 审计报告 | **最新**: 在线核实 v2 实施核对 + 安全/稳定性审计——33 项修改全部落地; 新发现 F1–F4 待拍板 | backend-partial-hr-verify |
| 09-27 22:52 | [plan-config-migration-materialize.html](../memory-bank/plans/26-09-27-2252-plan-config-migration-materialize.html) | 计划(衍生) | config schema 迁移物化重构(加载即迁移 + 版本号备份)——由 HR 绑定映射制的迁移需求衍生 | hr-binding-tracker-mapping |
| 09-28 19:32 | [plan-hr-verify-rebuild.html](../memory-bank/plans/26-09-28-1932-plan-hr-verify-rebuild.html) | 计划 | **在线核实 v3**: 用户定调推翻 v2 模型(全量翻页/双频控/熔断回落/40 键)——四行判定表+12格矩阵(命中考察中即管束 — 本地达标与否都管; 终态档/未列出放行; 无证据按本地兜底) + 单波型取数(每波全量对账 + A/B/C 轮流 + 三个停翻条件: 完成时间覆盖/remain==0×5 到期段/全集覆盖, 对象集=未对账∪考察中, ≥3× 超额免对账出集, .torrent 下载=身份登记一次(同 tid 永不重下), 已见 A 档行无条件全下载, B/C/D 行=覆盖区间+宽泛名称粗配(D1 已拍板)) + 单频控三键 + 熔断/退避全删(档位截断/证据无时效/排序失效强制早停) + 证据防伪(A 档流转守恒/总量骤降/零行戳 + 失踪观察期: 失踪者一律无证据无豁免), 配置 40→14 键; M1-M5 待批准实施 (doc-status Open) | backend-partial-hr-verify |
| 09-29 19:05 | [plan-webui-hr-src-underline.html](../memory-bank/plans/26-09-29-1905-plan-webui-hr-src-underline.html) | 计划 | 做种时长列 HR 来源标记非文字化: 「在线/本地/未核」两字芯片 → 底线三编码(长度/线型/明暗, 线色随档位色); 「已排除」chip 同批撤进 title(经 hrDurHint 组装), 代码已落地待真机走查 | webui-hr-src-underline |
| 09-29 20:04 | [hr-src-underline.md](../memory-bank/testing/baselines/26-09-29-2004-hr-src-underline.md) | 测试基线 | 1749(+1 skipped): 来源标记非文字化落地轮(3 处模板 + 3 套 CSS + hr.js 换绑 + 守阵随绑改写; 2 条 file_access 失败为 symlink 环境项, 与改动无关) | webui-hr-src-underline |
| 10-03 15:05 | [report-hr-fetch-verify-forensics.html](../memory-bank/reports/26-10-03-1505-report-hr-fetch-verify-forensics.html) | 取证报告 | HR 波次引擎四现象故障取证(一直在拉取 / 核实「未核实」/ 失踪 0 波), §13 后记附稳态降频可行性 + 所有者拍板(idle_refresh_interval 默认 24H) | backend-partial-hr-verify |
| 10-04 03:12 | [plan-webui-hr-fetch-history.html](../memory-bank/plans/26-10-04-0312-plan-webui-hr-fetch-history.html) | 计划 | WEBUI HR 在线核实新增「拉取历史详情表」: 站点文件内嵌 `HrSiteData.history` 环形留痕(波次/拦截/对账三类事件, 拍板⑤=2000条/站点+6个月, 不抬版本链) + `GET /api/hr/history` + 全屏弹层表③(参照扩展选项页取数明细表并加细, 波次行展开档位明细); S1-S6 全部落地 | webui-hr-fetch-history |
| 10-04 | [26-10-04-webui-hr-fetch-history.md](../memory-bank/tasks/26-10-04-webui-hr-fetch-history.md) | 任务档案 | 拉取历史详情表任务档案: S1 数据模型 → S2 三类写入点 → S3 只读口径+API → S4 前端表③ → S5 冒烟桩走查 → S6 收尾, 全部完成(本地分支 `webui-hr-fetch-history`) | webui-hr-fetch-history |
| 10-04 06:32 | [webui-hr-fetch-history.md](../memory-bank/testing/baselines/26-10-04-0632-webui-hr-fetch-history.md) | 测试基线 | 2423→2442(+19): 拉取历史详情表 S1-S5 全链路(数据模型/三类写入点/只读 API/表③/冒烟桩) | webui-hr-fetch-history |
| 10-05 05:55 | [plan-hr-steady-throttle.html](../memory-bank/plans/26-10-05-0555-plan-hr-steady-throttle.html) | 计划 | HR 稳态降频实施: 拉取间隔闸按「对账对象集是否为空」动态取值(新站点键 idle_refresh_interval, 默认 24H), 六阶段 S1–S6 全部落地(分支 feat/hr-steady-throttle) | backend-hr-steady-throttle |

## 二、常青文档 (无固定立档时间, 随代码演进持续回写)

| 文档 | 类型 | 与 HR 在线核实的关系 |
|---|---|---|
| [docs/configuration.md](configuration.md) | 配置文档 | 「HR 在线核实(`hr_check`)」专节: 站点绑定/档案表/超龄豁免/频控/站点状态页等全部配置口径 |
| [extensions/hr-fetch-proxy/README.md](../extensions/hr-fetch-proxy/README.md) | 扩展说明 | 取数代理(MV3 扩展)的设计说明: 哑取数器定位、cookie 不出浏览器、无界面直取 + 离屏窗口回退 |
| [memory-bank/config-reference/keys.md](../memory-bank/config-reference/keys.md) | 配置键参考 | `hr_check.*` 全部配置键的参考条目 |
| [memory-bank/checklists/manual-walkthrough.md](../memory-bank/checklists/manual-walkthrough.md) | 走查清单 | 真机走查步骤含「HR 站点状态」分区(`--hr-once` 走查口径) |
| [memory-bank/pitfalls/backend/behavior-core.md](../memory-bank/pitfalls/backend/behavior-core.md) | 坑档(后端) | 含 HR 判定联动相关的行为坑条目 |
| [memory-bank/pitfalls/ops/alert-levels.md](../memory-bank/pitfalls/ops/alert-levels.md) | 坑档(运维) | 含 HR 告警分档相关条目 |
| extensions/hr-fetch-proxy/options.html | 扩展选项页 | 选项页 UI 本体(非文档), 站点授权勾选 / 日志④区所在 |

## 三、稳态降频机制 (idle_refresh_interval · 计划 26-10-05-0555)

> 2026-10-05 实施 (分支 `feat/hr-steady-throttle`)。上游: [计划 26-10-05-0555](../memory-bank/plans/26-10-05-0555-plan-hr-steady-throttle.html)
> (取证报告 [26-10-03-1505](../memory-bank/reports/26-10-03-1505-report-hr-fetch-verify-forensics.html) §13)。
> 核心一句话: **拉取间隔闸按「对账对象集是否为空」动态取值** —— 稳态期降频, 对象集一翻非空立即回退。

### 站点配置键 `idle_refresh_interval`

| 属性 | 口径 |
|---|---|
| 默认 | `24H`(所有者 2026-10-05 拍板, 默认启用降频 —— 量级与 HR 宽限期 7–14 天匹配, 最坏发现延迟只占宽限期 ~10%) |
| 语义 | 本地无义务对象(对账对象集为空)时, 拉取间隔闸改用的对账节奏; 键位置 `hr_check.sites.<site>` |
| 校验 | 须 ≥ `refresh_interval`(交叉校验拦「降频比常态还快」); 60s 下限 / 30d 上限(与拉取间隔同款口径) |
| 等效关闭 | 把 `idle_refresh_interval` 配得**与 `refresh_interval` 相等** |

### 机制口径

- **判据 = 对账对象集为空**: 每 poll 在 `_refresh_locked` 波前现算(未对账 ∪ 考察中, 终态/已放行/超额 ≥3× 排除后为空);
  锚点**采集失败不算**稳态(见失败纪律)。
- **即时回退**: 对象集翻非空 ⇒ 间隔闸回退 `refresh_interval`, 而上次健康波早在 24H 前 ⇒ **下一 poll(≤60s)立即开波** ——
  新种子的发现延迟是 ≤60s + 波时长, 不是 24H。
- **失败纪律**: 锚点采集失败(`None`, 扩展侧/主循环侧故障或未接)= 「未知」⇒ **不降频**, 按常态间隔; 与「确认零锚点」
  (空映射, 采集成功)严格区分 —— 不把「不知道」当「零种子」。
- **写盘与展示**: 稳态旗标 `wave.idle_mode` 仅**翻转时**落盘, 稳态期反复 poll 零写盘; 展示层单点换算(`site_conf_interval`),
  稳态期「下次核对清单」显示 idle 倒计时 + kv 行「(稳态降频)」注记。

### 与既有机制的关系 (不变项)

- **复用窗不跟随降频**: 时长仍 = `min(reuse_window, refresh_interval)`(取常态间隔), 新鲜度与节奏解耦;
- **force(立即拉取)不受影响**: 照常跳过复用窗与拉取间隔两道调度闸;
- **账号安全线照常**: `min_interval` / 日额 / Retry-After / 时间窗在间隔闸之后, 不被降频(或 force)越过;
- **对象集为空不跳波**: 波照开、页照翻, 降频省的是波次, 不是单波页数。

## 四、阅读路径建议

- **想了解功能全貌**: 先读 [任务档案](../memory-bank/tasks/26-09-22-backend-partial-hr-verify.md)(主档案, 全程记录), v3 重构后的复审现状见 [activeContext 切片 26-09-29-0404](../memory-bank/activeContext/26-09-29-0404-hr-verify-v3-audit.md)。
- **想了解为什么这么设计**: 计划 [26-09-22-2204](../memory-bank/plans/26-09-22-2204-partial-hr-site-verify-plan.html)(初版) → 审计 [26-09-26-1628](../memory-bank/reports/26-09-26-1628-report-hr-online-verify-audit.html) → v2 计划 [26-09-27-1815](../memory-bank/plans/26-09-27-1815-plan-hr-verify-audit-fixes.html)。
- **想知道 v2 之后还有什么没做**: 最新审计 [26-09-28-0030](../memory-bank/reports/26-09-28-0030-report-hr-verify-v2-impl-audit.html) 的 F1–F4 待拍板项。
- **想配置/接入新站点**: [docs/configuration.md](configuration.md) 的 `hr_check` 节 + [extensions/hr-fetch-proxy/README.md](../extensions/hr-fetch-proxy/README.md)。
