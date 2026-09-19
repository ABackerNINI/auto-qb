# Active Context — 当前焦点

> Memory Bank 核心文件之一: 回答"现在正在做什么 / 上次做到哪 / 下一步从哪继续"。**每次会话开始先读本文件。**
> 稳定事实在 projectbrief / productContext / systemPatterns / techContext 与各主题文档; 计划与完成状态在 [progress.md](progress.md); 本文件只放**易变的会话级状态**。
> 维护纪律 (完整规程见 [memory-bank skill](../.agents/skills/memory-bank/SKILL.md)): ①每次会话收尾更新本文件, 已完成条目沉淀到 [progress.md](progress.md) 或主题文档后**删除** — 本文件只放易变状态; ②命中立档阈值的任务在 [tasks/](tasks/_index.md) 立档并同步索引; ③**禁止**在本文件追加长流水账纪要 (会淹没真正的当前焦点)。

**最后更新**: 2026-09-18 (①**测试期禁止真实系统通知**: 真凶是 `test_cli.py::test_main_qb_compat_error_clean_exit` 的 `manager` 为 `MagicMock` ⇒ `notify_fatal(msg, manager.config.notify)` 拿到恒真配置、守卫放行 ⇒ 真发 Windows toast `auto-qb 已停止`(探针实测抓到); 已 mock 掉 `auto_qb.cli.notify_fatal` + 新增 `tests/conftest.py` 会话夹具拦通知器命令(安全网), 基线 1006→1007, **已入库 `7ae21a1`** — 详见 [progress.md](progress.md) 顶部与 [pitfalls.md](pitfalls.md) 新条目 ②WEB UI **第十二轮·状态色收口**(R12, 纯 CSS, 已入库 `f47e6b8`): 「进度/状态两列文字」纳入行状态色; **星图补齐暂停中性令牌族** —— 棱镜第九轮 FX-06 已落地、星图漏改, 于是 `.g-status.k-paused` 落回 `--surface-2` 白 6% 底 = 用户说的"**还是太白**"真因; paused/other 行文字由近白 `--fg` 改中性中间调 `--paused`(= `--fg-muted`, 即"已暂停"状态文字那支色); 双 UI × 六主题截图逐张核对, 1006 passed **不变** — 详见 [progress.md](progress.md) 顶部与 [pitfalls.md](pitfalls.md) 两条新条目 ③WEB UI **错误种子状态列改显示具体原因**(`missingFiles`→"文件丢失" / `error`→tracker `msg` 原文) 已入库 `9723a76` — 详见 [tasks/TASK015](tasks/26-09-18-webui-error-reason.md) ④TASK014 UI 组件库 20 式已提交 `fae019a` ⑤**测试环境假失败清理**: 修掉 2 个环境性假失败(`APPDATA` 未设 ⇒ 通知用例断言必失败; 沙箱把 `os.symlink` 落成**真实目录** ⇒ 逃逸链接场景不存在) + `.gitignore` 补 `.coverage.*`, **实测 1007 passed / 0 failed**, 已入库 `7ae21a1` ⑥**测试期真实系统副作用普查**: patch 五类入口写文件记账跑全量 —— 外部进程 0, **唯一真问题 = AUMID 注册表键**(真写且不清理), 已加 conftest 第二道守卫后**归零** ⑦**普查能力固化**: `tests/sidefx.py` 记账器 + 会话夹具(收尾有越界项即失败)+ 策略单测 10 项, **1015 passed / 0 failed**)

## 正在进行

- **WEB UI 追剧视图 剧/集右键"打开目标文件夹: 种子不存在" (2026-09-19, 已入库 `c888fba`, Gitee 推送成功 `044908d..c888fba`; GitHub 直连 `Recv failure` 不重试, 镜像滞后 3 个)**: 用户报追剧页**剧右键与集右键**的"打开目标文件夹"失败, 种子右键正常。**真因**: 后端 shows 视图的 `members` 是 **hash 数组**, 前端 `decoratedShows` 把它换成**成员对象**;`openShowEpMenu`/`openShowMenu` 直接把 members 当 hash ⇒ 拼进 URL/JSON 时字符串化成 `[object Object]` ⇒ 后端 404「种子不存在」。**同一根因还让整集/整剧的 开始/暂停/强制汇报 报 Not Found、删除静默无反应**(用户尚未察觉)。**已改**: `shared/app.js` 新增 `memberHashesOf(list)`(两形态都收)统一取 hash, 菜单(`openShowEpMenu`/`openShowMenu`)与选中态(`_showHashes`/`_epUnits`/`epSelState`)一律走它; 双 UI(星图/棱镜)共用该文件 ⇒ 一次修两处。**测试**: `node --check` 通过; 另用 node 桩掉 `Vue.createApp`/`window`/`document` 直接**加载真 app.js** 调 `openShowEpMenu`/`openShowMenu` 断言产出是字符串 hash —— 新版 9/9 通过, `git show HEAD:` 旧版 9 项挂 5 项(含"载荷 hash = 对象")(**红绿双验**); 守阵已固化进 `tests/test_web.py::test_frontend_static_bundle_health` 第 7 项(对旧版实测报出全部 5 处)。全量 **1041 passed / 0 failed**(未新增用例, 基线不变)。**端到端冒烟已过**(桩服务 + 无头 Edge 开真页面: 修复版 open-path 收到真 hash, 换成 `044908d` 版收到整个成员对象 —— 红验实证, 手法见 pitfalls 末条)。**剩用户真机走查**(真实 qB 数据下再点一次)(剧 → 集 → 种子 三级各点一次"打开目标文件夹", 并顺带确认整剧的开始/暂停/删除已恢复) → 坑已入 [pitfalls.md](pitfalls.md) 末条
- **WEB UI 视图重建范围收口 · 种子速度刷新滞后修复 (2026-09-18, 未提交)**: 用户报"WEBUI 种子速度更新慢但状态栏正常"。**真因**: 后端两条视图重建路径**范围不一致** —— 主循环 `_tick` 只重建 `_group_view` 却清掉共享的 `_group_view_dirty` ⇒ 会重建 singles/shows/flat 的 Web 线程兜底(`ensure_group_view`)永不触发, 而 `_group_view_ver` 照常自增 ⇒ 前端判 `updated=true` 把**陈旧数组整表换上去**; 状态栏"速度合计" = `Σ groups[].dlspeed` 恰是唯一在重建的那份 ⇒ 显正常。**同源第二坑**: 置脏写在 `if grouping.enabled` 块内而 consume 在块外 ⇒ 分组关闭时标记被吞。**已改**: 新增 `WebviewMixin.rebuild_views()` 作**唯一重建入口**(四视图 + 版本号 + 清标记一次完成, 两条路径都只调它); 置脏移出门控; 前端取消 `idlePolls` 退避(只留失败退避)并把 `server_state` 并入 `/api/state.status.server`(状态栏与行数据同源同轮, 每轮仍 1 请求)。**测试**: 改写 2 条固化缺陷的用例(`test_tick_rebuilds_group_view_only_when_changed` → `test_tick_rebuilds_all_views_when_changed`; `test_tick_skips_group_view_when_grouping_disabled` → `test_tick_rebuilds_views_when_grouping_disabled`) + 新增 3 条, 均**已红绿验证**(旧代码上必失败); **1021 passed / 0 failed**(基线 1018)。剩用户真机走查 → 档案 [tasks/TASK017](tasks/26-09-18-webui-view-rebuild-scope.md)
- **测试期禁止真实系统通知 (2026-09-18, 已入库 `7ae21a1`)**: 真凶是 `test_cli.py::test_main_qb_compat_error_clean_exit` ——
  `manager` 是 `MagicMock` ⇒ `notify_fatal(msg, manager.config.notify)` 拿到**恒真配置**, 守卫 `if not config or
  not config.enabled` 放行 ⇒ 真的发一条 Windows toast(探针实测抓到: `auto-qb 已停止`)。已 mock 掉
  `auto_qb.cli.notify_fatal` 并断言调用; 另加 `tests/conftest.py` 会话夹具把通知器命令拦在 `subprocess.run` 之前(安全网)。
  全量真实 send 4 → **0**; 基线 1006 → **1007**; 剩**用户再跑一次测试确认不再弹框**

- **测试环境假失败清理 (2026-09-18, 已入库 `7ae21a1`)**: 全量测试曾有 **2 个稳定失败**, 排查确认都是**环境能力**差异、
  `src/` 无问题 —— ① `test_notify.py::test_notify_legacy_shortcut_cleanup` 补 `monkeypatch.setenv("APPDATA", ...)`
  (`_legacy_shortcut_paths()` 在 `APPDATA` 缺失时返回 `[]`, `os.path.exists` 的 monkeypatch 从未被问到 ⇒ 断言必失败);
  ② `test_web.py::test_api_fs_dirs_endpoint` 第⑤条补 `os.path.islink()` 判定(本机 `os.symlink` 返回成功却落成
  **真实目录**, "逃逸链接"场景不存在)。另: `.gitignore` 补 `.coverage.*`(并行覆盖率数据漏进 `git status`)。
  **实测 1007 passed / 0 failed**(修前 1006 + 1 failed) — 判据入 [pitfalls.md](pitfalls.md) 与 [testing.md](testing.md) 约定 9
  → 档案 [tasks/26-09-18-test-sidefx-guard.md](tasks/26-09-18-test-sidefx-guard.md)(本任务含上面那条"测试期禁止真实系统通知", 同属一个专题)

- **副作用普查能力固化进测试 (2026-09-18)**: 普查探针原是临时脚本(在 `%TEMP%`, 随会话消失),
  已固化为 `tests/sidefx.py`(七类入口记账器 + 放行清单 + `is_violation` 判定)+ `tests/conftest.py`
  第三道会话级夹具(**收尾有越界项即让 pytest 失败**)+ `tests/test_sidefx.py` 策略单测 8 项。
  **已反向验证**(注入越界记录 ⇒ 退出码 1 + 明细台账, 确认不是摆设), 临时验证文件已删。
  **实测 1018 passed / 0 failed**(基线 1007 + 11) — 详见 [testing.md](testing.md) 约定 10 与 [pitfalls.md](pitfalls.md)

- **测试期真实系统副作用普查 (2026-09-18)**: 通知只是**已知的一种**副作用, 于是 patch 五类入口
  (`subprocess.Popen` / `winreg` / 文件删除 / `os.symlink` / `socket.bind`) 写文件记账, 跑全量逐类判定。
  **结论(全量 1007 项)**: 外部进程 **0**(通知夹具生效); **唯一真问题 = AUMID 注册表键** ——
  `PlatformChannel("win32")` 构造时真写 `HKCU\Software\Classes\AppUserModelId\AutoQB.UI` 且**写完不清理**
  (autostart 的 Run 键是 `finally` 里自清理的, 性质不同), 触发用例 `test_notify_legacy_shortcut_cleanup`;
  其余干净(文件删除 157 条全在 `C:\TEMP\pytest-of-*`、建链全在临时目录、监听全为 `127.0.0.1` 自清理)。
  已加 `tests/conftest.py` **第二道会话级守卫**(只拦 AUMID 前缀, 静默成功**不抛异常** —— 否则 `_appid`
  会回退成 FALLBACK 打乱断言) ⇒ 复核 **AUMID 归零**, 注册表台账只剩 autostart 的自清理 Run 键;
  1007 passed / 0 failed — 手法与过滤坑入 [pitfalls.md](pitfalls.md) 与 [testing.md](testing.md) 约定 8

- **R12 状态色收口 (2026-09-18, 已入库 `f47e6b8`)**: 进度/状态两列文字随行状态着色 + 星图补 `--paused` 令牌族
  (与棱镜同值) + paused/other 行不再保持近白前景。改的是 `atlas/style.css` 与 `prism/css/views.css`;
  双 UI × 六主题截图已逐张核对(见 [pitfalls.md](pitfalls.md) 的核对手法条目), 剩**用户真机观感确认**

- **TASK015 WEB UI 错误原因展示 (2026-09-18, 已入库 `9723a76`)**: 错误种子的状态列不再只显示「错误」——
  `missingFiles` → "文件丢失"(零 API, 状态自明), `error` → tracker 报错原文(如
  `torrent not registered with this tracker`)。关键设计: qB `torrents/info` **无**错误文本字段(已核实),
  原因只能从 `torrents/trackers` 的 `msg` 取 → 主循环 `refresh_error_reasons` 按 TTL(300s)+预算(5/轮)
  预取, 视图组装**只读缓存**(视图可能每 tick 重建, 不得在里面发 API); 原因非快照字段, 变化由预取方
  **显式置脏**。剩用户真机走查 → 档案 [tasks/26-09-18-webui-error-reason.md](tasks/26-09-18-webui-error-reason.md)

- **WEB 跳过本地验证日志降为 INFO (2026-09-18, 已入库 `7ce54e9`)**: `web.py` 里"本机免密钥放行"提示原为 `logger.warning` → 改 `logger.info`(免鉴权是用户显式开的配置而非异常, WARNING 会经 notify 推送扰民); 变量 `_local_skip_warned` → `_local_skip_logged` 对齐; `test_web.py::test_skip_local_verify_loopback_bypass` 断言同步改为 INFO 级 + 断言不再产生 WARNING

- **TASK014 UI 组件库 20 式**: 交付物已产出并自检(文本层/渲染层/功能探针/390px 断点), 7 项缺陷已修; 剩用户挑选与按需迭代 → 档案 [tasks/26-09-17-webui-component-libraries.md](tasks/26-09-17-webui-component-libraries.md)

- **导出 .torrent 中文名 500 已修 (2026-09-17, 已入库 `4de0953`)**: `/api/torrents/{hash}/export` 把种子名直拼进 `Content-Disposition`, HTTP 头只能 latin-1 → 中文名 `UnicodeEncodeError` 500。修法: 新增 `web.content_disposition(filename, fallback, ext)` 双段头(`filename=` ASCII 回退 + `filename*=UTF-8''<百分号编码>`)并清洗控制字符; 测试 `test_content_disposition_encoding` + 导出端点非 ASCII 用例。剩用户真机走查
- **TASK013 第十一轮修复**: 代码/文档/验证已完, **已入库 `4a027ef`** —— 剩用户真机走查反馈
- **TASK012 第十轮修复**: 已入库 `cb57bef` (用户自行提交) —— 剩用户真机走查反馈
- **TASK011 第九轮修复**: 已入库 `49d3151`, 剩用户真机走查反馈
- **第十轮的两处已知限制**(已写入 pitfalls, 非待办): ① 列偏好受 localStorage **origin 隔离** 影响(`localhost` 与 `127.0.0.1`/换端口 = 不同站点各存一份) —— 用户明确要求只存浏览器, 不做服务端化; ② 目录浏览器只能浏览**已有保存路径及其子目录**(安全边界), 全新位置需在输入框手填
- **第十一轮的定案口径**(已写入 pitfalls, 别改回去): 行/表头一律 `fit-content; min-width: 100%`(**底色跟内容**), **行内单元格必须 `min-width: 0`**(否则 nowrap 文本把行顶宽 → 列没溢出却常驻横滚条); 曾用"行定宽 100%"治假滚动条, 会让**溢出段没有底色**(用户实测"滚动后右边无背景条"), 已回退
- **`想法.md`**: 工作区**干净**(最后一次入库 `3bface9`)。它属于红线文件(与 `config.yml` / `auto-qb-data/` 同级), 提交前照例用 `git status --short` 确认一遍是否又有改动, 不进暂存区

- **列偏好"升版本"口径已单点统一 (2026-09-19, 文档回写)**: `pitfalls.md`(两条) 与 `systemPatterns.md` 原写"加/减列**必须**升列状态存储版本", 与代码 R10-09(`shared/app.js:128-134`)及 `modules.md:62` 相反 —— 已按"代码 > memory-bank"裁决回写: 列集变更(加列/减列/重排)与存储结构扩展**一律不升版本**, 只有"旧缓存结构已无法被 `loadColState()` 正确解释"才升(如 v2 按列索引存), 且升版本必须同时挂 `LEGACY_COLS_KEYS` 迁移。当前键冻结在 `autoqb_cols_v4`, 无 v5 计划。历史计划 `docs/plans/26-09-15-1042-webui-optimization-plan-v3.html` 里"重排列集则升 v4→v5"是当时口径, 已被第十轮计划取代 —— 存档未改动, 别照抄

## 下一步候选 (来源: `想法.md` 待办 + progress.md 规划中)

- WEB UI: WebSocket 推送; 多用户; **设置页全面重构**(`想法.md` 现存最大一条未做项)
- WEB UI: 窗口日志等级可选; 星图侧补齐第九轮的纯版式项(棱镜已做: FX-05/06/09/17~25)
- 规则系统: 条件取反 (`!`/非 logic); 重新梳理 ignore_next_action_error / stop_following_rules_if
- tracker 分组前端增强 (阶段 2/3, 2026-09-15 拍板后续): 设置页 groups 下拉快捷追加 (rules_ref 风格); 辅种管理页按组筛选 (web_view 透出 conf.groups + app.js filterDefs)
- 其它: 切分大文件; 种子未变动时不触发内置维护任务; 版本管理; 命中限速曲线强调显示; 插件系统
- 🚧 实机验证: README 标注 🚧 的功能 (alpha 阶段), 生产使用前先 `--dry-run` 观察

## 历史归档 (已迁出本文件)

2026-09-14 ~ 2026-09-17 的全部会话纪要已按专题迁移到 [tasks/](tasks/_index.md) 各档案的"历史会话纪要 (原文归档)"段 (原文未删改)。需要回查历史请走 `tasks/_index.md` 定位专题档案, 本文件只保留**当前焦点**。
