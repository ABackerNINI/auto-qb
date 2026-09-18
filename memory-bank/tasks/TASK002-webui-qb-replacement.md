# TASK002 - WEB UI 替代 qB 界面 (波次一 ~ 波次三 + 复查)

**Status:** In Progress
**Added:** 2026-09-15
**Updated:** 2026-09-17
**专题:** WEB UI / 替代 qB 界面 / 后端 Web 层

## 原始请求

- 2026-09-15: 用户升级 WEB UI 定位 — **将来直接替换 qB 界面** (取代 `想法.md` 旧定位"不是要做一个 qb 的 web ui"); 要求先调研计划。
- 2026-09-16: 给出 **30 条界面诉求清单** (辅种管理 16 / 设置页 1 / 其它 13), 要求拆解归类供 agent 集群任务分配。
- 2026-09-17: 反馈 8 条实机问题 (弹窗点击无反应、棱镜样式大面积丢失、状态栏与表头菜单口径等), 要求全面复查修复。

## 思考过程与决策

- 调研结论 (09-15): 技术无根本障碍 — `TorrentRecord` 70 字段供数 + 命令队列/确认链样板已验证; 缺口 = 种子中心视图 (P0) + 添加种子 (P0) + ~10 项 S/XS 操作补全 + `server_state` 捕获。
- 决策点: D1 双 UI 同步 (atlas + prism 同构) / D2 仅临时覆盖 (不改用户持久配置) / D3 搜索与 RSS 不做 / D4 添加种子不下放预览 / D5 双 tab 与种子页平级。
- 30 条诉求拆为 **32 工作项 × 8 类** (FIX7 / TBL8 / DLG4 / CTX3 / SPD4 / NAV3 / RFB2 / PRS1) → 6 波次 (W0 缺陷快修 → W1 表格层 → W2 弹窗右键 ∥ W3 限速 → W4 导航 IA → W5 详情与设置页)。
- 派工模式: 双 bot (backend / 前端) + 4 车道 worktree, 主线 `agentAutoClaw/develop` 负责合并与抢救; 车道分支先 `merge --ff-only` 对齐主线再动工 (曾有车道落后主线 1689 行致基线踩旧)。
- 双模板 86% 同构 → 棱镜采用"以星图模板为基线重建 + 棱镜专有替换", 而非逐块手抄。

## 实现计划

- [x] 波次一: 种子中心视图 + 详情抽屉 + 16 个写命令端点 + 右键/批量接线 (基线 949→964)
- [x] 波次二: 管理包 — 分类/标签 CRUD、限速托管与临时覆盖、添加种子 (bytes 内存直传)、导出 .torrent、日志 tail、统计面板 (964→971)
- [x] 波次三: 32 工作项全部落地, 双 UI 同构 (971→988)
- [x] 复查修复: 弹窗全灭 + 棱镜丢样式两大根因 + 6 项口径修订 (→989)
- [ ] 浏览器 CDP 双 UI 走查 + 真机 `--dry-run` (本机具备条件后补)
- [ ] git 提交 (复查修复尚未提交)

## 子任务状态表

| ID | 描述 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| 2.1 | 调研与计划 (替代 qB 可行性) | Complete | 2026-09-15 | `docs/plans/26-09-16-0123-webui-qb-replacement-plan.html` |
| 2.2 | 波次一 (视图 + 详情 + 写命令) | Complete | 2026-09-16 | 964 passed |
| 2.3 | 波次二 (管理包) | Complete | 2026-09-16 | 971 passed; 报告 `DELIVERY/webui-qb-replace-report.md` |
| 2.4 | 波次三计划 (30→32 工作项) | Complete | 2026-09-16 | `docs/plans/26-09-16-1128-webui-qb-replace-wave3-plan.html` |
| 2.5 | 波次三盘点与交接 | Complete | 2026-09-17 | `docs/plans/26-09-17-0346-webui-qb-replace-wave3-handover.md` |
| 2.6 | 波次三收口实施 (双 UI 同构) | Complete | 2026-09-17 | 988 passed; 星图 + 棱镜双车道 |
| 2.7 | 复查修复 (弹窗/CSS/口径 6 项) | Complete | 2026-09-17 | 989 passed; 守阵扩展 |
| 2.8 | 实机 CDP 双 UI 冒烟 + 真机 dry-run | Not Started | 2026-09-17 | 需浏览器自动化环境 |
| 2.9 | git 提交 (复查修复) | Not Started | 2026-09-17 | 等用户指示 |
| 2.10 | prism 追剧模板欠账 | Not Started | 2026-09-17 | `viewMode=shows` 目前兑底渲染种子页 |

## 进度日志

### 2026-09-17

- **复查修复两大根因**: ①模板 `<transition name="pop">` 未闭合导致其后 6 个弹窗被 Vue `Transition` 静默丢弃 (点击无反应且无控制台报错) — 删多余开闭标签即恢复; ②`prism/css/views.css` 两处残留 (规则漏 `; }` + 选择器头被吞) 使浏览器丢弃其后约 200 条规则 (全文件括号仍配平) — 按星图同名规则还原。
- 口径修订 6 项: 底部状态栏重排、页内三视图开关退役、已选批量条位置、TBL-03 改文字色、取消普通点击选中、TBL-05 表头右键改「隐藏该列」+ 排序 + 列选择器。
- 加固: 抽屉 `<transition :duration="200">` + `.drawer-leave-active{pointer-events:none}`。
- 守阵扩展: `test_frontend_static_bundle_health` 新增 CSS 规则块漏闭合与 `<transition>` 吞弹窗两类静态检查 (红绿验证: 修复前报 9 处 / 修复后 0)。
- 闸门 `uv run pytest tests -q` = **989 passed**; 未提交 git。
- 同日的"整页白屏"故障 (app.js 注释孤儿续行致整文件 SyntaxError) 亦属本专题, 详见原文归档。

### 2026-09-16

- 波次一合并至 `agentAutoClaw/develop @ 59498dd`, 闸门 964; 波次二完成 (34f0d41 / ed7a3c3), 闸门 971; 安全守卫事件: 首版"添加种子临时文件"方案被拦截, 重设计为 **bytes 内存直传** (零临时文件 / 零删除 API / 零新依赖)。
- 波次三计划产出 (32 工作项 / 6 波次 / 5 决策点带推荐值)。

### 2026-09-15

- 调研产出替代计划; 实施"跳过本地验证" `web.skip_local_verify` (本机免 token, 对外仍强制鉴权; 949 passed)。

## 历史会话纪要 (原文归档)

> 以下为 `activeContext.md` 会话纪要的**原文归档** (2026-09-17 机械迁移, 未删改; 含一处历史 GBK 编码损坏条目),
> 按时间倒序保留。新增进展请写 `## 进度日志`, 不要再往 `activeContext.md` 堆长纪要。

- 2026-09-16: WEB UI 替代 qB 界面·波次二完成(08:17 续): 管理包全部落地 —— 后端 34f0d41(分类/标签 CRUD+限速托管与临时覆盖+添加种子 bytes 内存直传+导出+日志 tail)/ed7a3c3(GET 列表端点) + 前端 FE-2A 添加对话框(bot 12.5 分钟正常完成, 主线适配 base64-JSON)/FE-2B 编辑对话框与 Content 编辑/Tracker 编辑(bot 3 提交超时前已全部落盘)/FE-2C1 统计日志限速卡(bot 5 提交)/FE-2C2 分类标签管理对话框(bot 4 提交隔夜完成); agentAutoClaw/develop @ 3e57917, 最终闸门 971 全绿(基线 949+22)。安全守卫事件: 首版添加种子临时文件方案(rmtree 清理)被拦截, 重设计为 bytes 内存直传(零临时文件零删除 API 零新依赖), 非绕过。剩余: prism 追剧模板欠账 + 实机 CDP 冒烟。报告 DELIVERY/webui-qb-replace-report.md
- 2026-09-17: **波次三复查修 bug(用户 8 条反馈 + 全面验证)** — 用假 qB(FakeQbServer)+真实 QbManager+真实 Web 服务搭冒烟环境, 浏览器逐项验证。**两个根因**修完全部"弹窗类"故障: ①`atlas/prism` 模板里抽屉外层的 `<transition name="pop">` 未闭合(波次一残留), 其后的**6 个弹窗**(统计/限速/添加/分类标签管理/全局确认框)全被浏览器解析成它的子节点 → Vue `Transition` 只渲染首个子节点 → **弹窗全被静默丢弃**(点击无反应、控制台无报错) —— 删掉多余开闭标签即恢复; ②`prism/css/views.css` 两处波次三批量编辑残留(一条规则漏 `; }` + 一条选择器头被吞) → 浏览器把其后**约 200 条规则整段丢弃**(棱镜大半样式静默消失, 全文件括号还是配平的) —— 按星图同名规则还原。口径修订: 底部状态栏重排(左=统计摘要常显+完整统计入口, 右=速度+限速, 删全局状态徽标)/页内第二套三视图开关退役/已选批量条移到"做种数量统计后、筛选器前"/TBL-03 由背景色改为**文字色**/取消普通点击选中(仅 Ctrl/⌘ 与 Shift)/TBL-05 表头右键改为「隐藏该列」+排序+列选择器入口(双 UI 同步)。另加固: 抽屉 `<transition :duration="200">` + `.drawer-leave-active{pointer-events:none}`(防不可见全屏遮罩滞留拦点击)。守阵扩展: `test_frontend_static_bundle_health` 新增 CSS 漏闭合与 `<transition>` 吞弹窗两类静态检查(红绿验证过: 对修复前文件报 9 处, 修复后 0)。闸门 `uv run pytest tests -q` = **989 passed**。文档回写: README(状态栏/表头右键/文字着色/三视图/删除框摘要) + pitfalls(新增"三类结构性损坏 + 集成浏览器 hidden 态冒烟坑"条目)。未提交 git。
- 2026-09-17: **修 WEB UI 整页白屏(用户报"进入 webui 只显示背景")** — 根因: 波次三"以星图模板为基线重建 + 批量替换"把 `shared/app.js` 一条注释续行(`* 列宽重实体化契约由 watch(page) 与 …`)留在了**已闭合的 `*/` 之后**, 整文件 `SyntaxError: Unexpected identifier 'watch'` → app.js 零执行 → Vue 不 mount → `v-cloak` 的 `#app` 恒 `display:none` → **页面只剩背景色**(atlas/prism 同因, 共用 shared 层)。定位手法: 起静态服务(`python -m http.server --directory src/auto_qb/web_ui/static`)+ 浏览器 `addInitScript` 挂 `error` 监听再 reload, 拿到 `app.js:1997:18`(后端日志/curl/pytest 全看不到)。修复: 删该孤儿行(app.js -1 行)。防回归: 新增 `tests/test_web.py::test_frontend_static_bundle_health`(静态扫 web_ui/static: 冲突标记/JS 注释孤儿续行/模板引用的静态资源存在性), 已红绿验证(对修复前 app.js 精确报出 1997 行, 修复后 0 问题)。闸门 `uv run pytest tests -q` = **989 passed**(988→989)。文档回写: testing.md 基线 988→989 + 前端守阵说明补充 / README 用例数 / AGENTS 测试命令数字 / pitfalls 新增"整页白屏"条目(含两类"没内容"的判别法)。未提交 git(按规矩等用户指示)。
- 2026-09-17: WEB UI 波次三**收口实施**(按车道模型, 用户拍板"全部补完 + 一并回写文档") — 起点=交接文档盘点的 15 项半完成 + 3 项未做。①四车道分支先 `merge --ff-only` 同步到主线 HEAD(此前车道落后主线 1689 行, 直接改会踩旧基线); ②**星图车道**(frontend/develop)两单: TBL-07 全宽(清 3 处 max-width:2560px + 两侧 12px 内边距) + CTX-01 彩色图标集(`.ctx-item .ico-*` 12 个操作族语义色 + `.ico-chart`/`.ico-log`) + CTX-02 触发源强调(共享层 `_markCtxSource`/`_clearCtxSource` DOM 标记 + watch(menu.visible/filePile.visible) 清理, 模板零改动即双 UI 生效) + RFB-02 件4 密度打磨(段距 8px/折叠头 8px/标题分级 13.5/奇偶区隔) ; 随后第二单收尾 **RFB-02 件2**(设置页风险标识切到 `.ce-note`: 4 处风险说明 + 3 处徽标退役 + cfg.notice 死横幅清除 + 新增 `.ico-risk` 紧凑图标) —— 此前 `.ce-note` CSS 已入库但模板从未切换, 属"两不管"缺口; ③**棱镜车道**(agentTrae/develop)一单打平: 因两模板 86% 同构, 采用「以星图模板为基线重建 + 棱镜专有替换(head 主题链/主题切换器/界面互切链接)」而非逐块手抄, 再补 prism CSS 211 行(状态栏/批量段/拖动落点/色阶/详情字段行/限速弹窗/日志章节/设置页栅格令牌与注记/顶栏右置与品牌动画/彩色图标/触发源强调)并退役 rail 与 `.bulk-bar`; ④文档回写: README(两套界面+新拓扑+988)/testing.md(949→988 单点)/想法.md(30 条勾选+定位更正)/activeContext/progress/pitfalls。闸门: 合并后 `uv run pytest tests -q` = **988 passed / 92% 分支覆盖**。未做: 浏览器 CDP 双 UI 冒烟与真机 `--dry-run`(本环境无 node/无浏览器自动化), 需人工走查。
- 2026-09-17: WEB UI 波次三·实施现状盘点与交接 (只读分析, 仅新增交接文档, 未改代码) — 全量核对 9 个 worktree/8 个分支 + 32 工作项落地面 + 实跑 pytest, 产出 [docs/plans/26-09-17-0346-webui-qb-replace-wave3-handover.md](../../docs/plans/26-09-17-0346-webui-qb-replace-wave3-handover.md)。关键事实: ①合并靶 agentAutoClaw/develop @ e7093b7, 工作区干净, **全量 988 passed / 92% 分支覆盖** (波次二闸门 971, +17 用例); ②所有车道分支均已合回主线 (无独有提交), 生产 develop @ 5aa47b3 与合并靶已分叉 (merge-base b9066c7, 3/76), 回流须 merge --no-ff; ③完成度: 完全完成 16 项 / 仅差棱镜镜像 15 项 / 完全未做 3 项 (TBL-07/CTX-01/CTX-02), **计划 W1d「移植到棱镜」从未执行** (W1 表格层/W4 导航/W5 详情与设置全部只落 atlas+shared); ④UT 无提交: CTX-01 彩色图标集、CTX-02 触发源强调; RFB-02 件4 视觉打磨为孤儿提交 48836d7 (未入库, 兄弟提交 66f4111/f38eb32/3da9f1a/ab9a863/f359390/f396972 均已重放归档); ⑤TBL-07 仅 frontend 工作区有未提交草稿, 棱镜同改未做; ⑥文档全面滞后 (testing.md/README 写 949, activeContext 停在 09-15, 想法.md 未勾选, DELIVERY/ 不存在); ⑦生产工作区 想法.md 有未提交新需求 `"0分钟"做种时长且没有HR要求改为不显示` (未纳入 32 项); ⑧残留清理项: backend `tests/test_zz_probe_scratch.py`、zcode `w1b1_punct_scan.py`。接手建议路线 (交接文档 §7): 批次 A 补棱镜 P-1~P-13 ∥ 批次 B (CTX-01/02 + RFB-02 件4 + 新需求) → 批次 C 终验 (CDP 双 UI 冒烟 + 真机 dry-run + 文档回写 + DELIVERY + 回流 develop)。
- 2026-09-17: WEB UI 波次三·实施现状盘点与交接 (只读分析, 仅新增交接文档, 未改代码) — 全量核对 9 个 worktree/8 个分支 + 32 工作项落地面 + 实跑 pytest, 产出 [docs/plans/26-09-17-0346-webui-qb-replace-wave3-handover.md](../../docs/plans/26-09-17-0346-webui-qb-replace-wave3-handover.md)。关键事实: ①合并靶 agentAutoClaw/develop @ e7093b7, 工作区干净, **全量 988 passed / 92% 分支覆盖** (波次二闸门 971, +17 用例); ②所有车道分支均已合回主线 (无独有提交), 生产 develop @ 5aa47b3 与合并靶已分叉 (merge-base b9066c7, 3/76), 回流须 merge --no-ff; ③完成度: 完全完成 16 项 / 仅差棱镜镜像 15 项 / 完全未做 3 项 (TBL-07/CTX-01/CTX-02), **计划 W1d「移植到棱镜」从未执行** (W1 表格层/W4 导航/W5 详情与设置全部只落 atlas+shared); ④UT 无提交: CTX-01 彩色图标集、CTX-02 触发源强调; RFB-02 件4 视觉打磨为孤儿提交 48836d7 (未入库, 兄弟提交 66f4111/f38eb32/3da9f1a/ab9a863/f359390/f396972 均已重放归档); ⑤TBL-07 仅 frontend 工作区有未提交草稿, 棱镜同改未做; ⑥文档全面滞后 (testing.md/README 写 949, activeContext 停在 09-15, 想法.md 未勾选, DELIVERY/ 不存在); ⑦生产工作区 想法.md 有未提交新需求 `"0分钟"做种时长且没有HR要求改为不显示` (未纳入 32 项); ⑧残留清理项: backend `tests/test_zz_probe_scratch.py`、zcode `w1b1_punct_scan.py`。接手建议路线 (交接文档 §7): 批次 A 补棱镜 P-1~P-13 ∥ 批次 B (CTX-01/02 + RFB-02 件4 + 新需求) → 批次 C 终验 (CDP 双 UI 冒烟 + 真机 dry-run + 文档回写 + DELIVERY + 回流 develop)。
- 2026-09-16: WEB UI 替代 qB 界面·波次三计划会话 (只计划未改代码) — 用户提供 30 条界面诉求清单 (辅种管理 16/设置页 1/其它 13), 目标不变 (WEBUI 直接替代 qB 界面), 要求拆解归类供 agent 集群任务分配。摸底核实: ①peers 报错根因=qbittorrent-api 2026.8.1 无 torrents_peers 只有 sync_torrent_peers (实测 hasattr=False), web.py:368 一行修; ②atlas 现拓扑=辅种管理(三态视图+rail)/设置/统计弹窗/日志四页; ③限速配置=global_speed_limit_curve (models.py:168 GlobalSpeedLimitCurve); ④testing.md 基线 949 未随波次二回写 (实际闸门 971, 已记漂移)。产出 [docs/plans/26-09-16-1128-webui-qb-replace-wave3-plan.html](../../docs/plans/26-09-16-1128-webui-qb-replace-wave3-plan.html): 30 条→32 工作项×8 类 (FIX7/TBL8/DLG4/CTX3/SPD4/NAV3/RFB2/PRS1)→6 波次 (W0 缺陷快修→W1 表格层主战场→W2 弹窗右键+棱镜追剧∥W3 限速→W4 导航 IA 重排[硬依赖 TBL-08 底部状态栏]→W5 详情+设置页重构), 最大并行 3, 派发指引沿用双 bot 模式 (backend/星图前端/棱镜前端+主线合并); 5 决策点 (D1 数值色阶映射/D2 连接数数据源/D3 目录选择走聚合方案 A/D4 分组页保留主从/D5 末档 clamp 语义) 均带推荐值; 红线含 prism CRLF/PowerShell 编码/bot 20min 窗口/sticky 契约等历次踩坑。待用户拍板 D1-D5 后按 W0 开工。
- 2026-09-16: WEB UI 替代 qB 界面·实施波次一(双 bot 编排 + 主线接管, 已全部合并 agentAutoClaw/develop @ 59498dd, 最终闸门 pytest 964 全绿) — 编排: backend/frontend bot 各在 backend/frontend worktree 实施, 主线合并至 agentAutoClaw/develop; 共 5 次派发(后端×2 网络瞬断零落盘, 前端整包超时零落盘, 前端拆段后超时但落盘 5 文件由主线抢救审查补全, 后端 R2A 超时但落盘 995 行 salvage 后直接过测), 全部由主线接力完成。已交付: ①后端 R1(server_state 捕获+/api/stats + 平铺 SEED_ITEM /api/state.torrents 同门控 + 单种详情/trackers/files/peers 端点, 4efa9cf) ②前端 R1A 种子页(数据源切换+列扩展+客户端文本过滤+复制名称/哈希/magnet, e607e86; prism 补视图切换器) ③前端 R1B 详情抽屉(常规/Tracker/用户/内容 四 tab 双 UI, 94a5d2f) ④后端 R2A 16 个写命令端点+QbApi 封装+trackers 缓存失效+bulk 聚合(d4fe0b8) ⑤前端接线(右键 重新校验/超级做种/强制开始/队列 + 批量校验 + 抽屉校验, e6634b3)。测试基线 949→964。决策落地: D1 双UI同步 / D2 仅临时覆盖 / D3 搜索RSS不做 / D4 推荐方案(下一波) / D5 双tab平级(prism 补切换器; prism 追剧模板仍缺, viewMode=shows 兑底渲染种子页)。待办(下一波, 契约见 .cluster/webui-qb-replace/r2-contract.md): BE-2b 管理端点(分类标签 CRUD/限速覆盖+mode/添加 multipart/导出 .torrent/日志 tail) + 前端对应 UI(添加对话框含 D4 预览/单种限速分享率移动改名 trackers 对话框/Content 优先级编辑/分类标签管理入口/统计面板/日志页/限速卡覆盖控件) + README 已补种子页与抽屉说明(本次已回写) + 实机 CDP 冒烟。坑: PowerShell `>` 重定向 UTF-16 坏 git patch(用 --output); prism views.css 是 CRLF(编辑锚需匹配或追加); bot 20 分钟窗口装不下大型前端任务(拆段+代码地图+允许从落盘现场续作); 前后端工作树冗余脏状态挡 FF(内容入库后 checkout -- . 清理)。交付报告: DELIVERY/webui-qb-replace-report.md。
- 2026-09-15: WEB UI 跳过本地验证实施完成 — 新配置键 `web.skip_local_verify`(默认 false, 保守): 开启后本机(loopback 127.0.0.1/::1)访问 /api/* 免 token 鉴权直接进入, 对外暴露(host 非本机)仍强制鉴权。后端五触点(models.WebConfig 字段 + validation/sections.py KNOWN_WEB_KEYS/_validate_web bool + loaders.load_web_config 解析 + web.py require_token 顶部本机免鉴权放行 + 公开只读端点 /api/config/public[免 token 暴露标志不含机密]); impact.py 不改(web 已是 L1, 新键随段热重载); 前端两处(schema/groups.py web 组加 skip_local_verify Field 设置页自动渲染开关 + shared/app.js mounted 先读 /api/config/public 本机免鉴权则直接放行不弹登录表单)。测试 +3(test_web: 公开端点免鉴权/本机放行+远端仍401/默认关闭), 全量 pytest **949 passed**; 文档同步(docs/configuration.md/minimal.yml/README[YAML 示例+访问与鉴权段]/memory-bank config-reference.md/testing.md 基线 946→949)。坑: test_web 的 web_cfg 是 SimpleNamespace 缺 skip_local_verify 导致 require_token 直接 AttributeError, 补默认 False 后 57→60 全绿; minimal.yml 的 add_episode_tags 校验失败为既有问题(实测 HEAD 同样失败, 与本次无关)。
- 2026-09-15: WEB UI 替代 qB 界面 · 调研计划会话 (只计划未改代码) — 用户明确目标升级: WEB UI 将来直接替换 qB 界面 (取代 想法.md 旧定位"不是要做一个qb的web ui")。逐文件核实数据层与 API 现状 (compat.py 70 字段表 / view.py _VIEW_FIELDS 13 项 / web_view.py / web_commands.py 命令与确认链 / qbapi.py 封装面 / web.py 端点 / store.py apply_sync 丢弃 server_state) 后产出 [docs/plans/26-09-16-0123-webui-qb-replacement-plan.html](../../docs/plans/26-09-16-0123-webui-qb-replacement-plan.html): 结论=技术无根本障碍 (TorrentRecord 70 字段供数 + 命令队列/确认链样板已验证), 缺口=种子中心视图 (P0) + 添加种子 (P0) + ~10 项 XS/S 操作补全 (P0/P1) + server_state 捕获 (XS); 搜索/RSS/设置面板 P2 延后; 5 个决策点 (D1 双 UI 主战场建议 prism / D2 龟速托管语义 / D3 搜索 RSS 是否常用 / D4 添加种子接管预览 / D5 种子页与辅种页关系); 专章梳理自动化×手动冲突边界 (标签/限速/组键 save_path/校验闸门)。Phase 0 基建→1 种子页→2 操作管理→3 按需。
