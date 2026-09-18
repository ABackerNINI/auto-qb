# Active Context — 当前焦点

> Memory Bank 核心文件之一: 回答"现在正在做什么 / 上次做到哪 / 下一步从哪继续"。**每次会话开始先读本文件。**
> 稳定事实在 projectbrief / productContext / systemPatterns / techContext 与各主题文档; 计划与完成状态在 [progress.md](progress.md); 本文件只放**易变的会话级状态**。
> 维护纪律 (完整规程见 [memory-bank skill](../.agents/skills/memory-bank/SKILL.md)): ①每次会话收尾更新本文件, 已完成条目沉淀到 [progress.md](progress.md) 或主题文档后**删除** — 本文件只放易变状态; ②命中立档阈值的任务在 [tasks/](tasks/_index.md) 立档并同步索引; ③**禁止**在本文件追加长流水账纪要 (会淹没真正的当前焦点)。

**最后更新**: 2026-09-18 (①**测试期禁止真实系统通知**: 真凶是 `test_cli.py::test_main_qb_compat_error_clean_exit` 的 `manager` 为 `MagicMock` ⇒ `notify_fatal(msg, manager.config.notify)` 拿到恒真配置、守卫放行 ⇒ 真发 Windows toast `auto-qb 已停止`(探针实测抓到); 已 mock 掉 `auto_qb.cli.notify_fatal` + 新增 `tests/conftest.py` 会话夹具拦通知器命令(安全网), 基线 1006→1007, **已入库 `7ae21a1`** — 详见 [progress.md](progress.md) 顶部与 [pitfalls.md](pitfalls.md) 新条目 ②WEB UI **第十二轮·状态色收口**(R12, 纯 CSS, 已入库 `f47e6b8`): 「进度/状态两列文字」纳入行状态色; **星图补齐暂停中性令牌族** —— 棱镜第九轮 FX-06 已落地、星图漏改, 于是 `.g-status.k-paused` 落回 `--surface-2` 白 6% 底 = 用户说的"**还是太白**"真因; paused/other 行文字由近白 `--fg` 改中性中间调 `--paused`(= `--fg-muted`, 即"已暂停"状态文字那支色); 双 UI × 六主题截图逐张核对, 1006 passed **不变** — 详见 [progress.md](progress.md) 顶部与 [pitfalls.md](pitfalls.md) 两条新条目 ③WEB UI **错误种子状态列改显示具体原因**(`missingFiles`→"文件丢失" / `error`→tracker `msg` 原文) 已入库 `9723a76` — 详见 [tasks/TASK015](tasks/TASK015-webui-error-reason.md) ④TASK014 UI 组件库 20 式已提交 `fae019a` ⑤**测试环境假失败清理**: 修掉 2 个环境性假失败(`APPDATA` 未设 ⇒ 通知用例断言必失败; 沙箱把 `os.symlink` 落成**真实目录** ⇒ 逃逸链接场景不存在) + `.gitignore` 补 `.coverage.*`, **实测 1007 passed / 0 failed**, 已入库 `7ae21a1`)

## 正在进行

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
  → 档案 [tasks/TASK016-test-notification-and-env-guard.md](tasks/TASK016-test-notification-and-env-guard.md)(本任务含上面那条"测试期禁止真实系统通知", 同属一个专题)

- **R12 状态色收口 (2026-09-18, 已入库 `f47e6b8`)**: 进度/状态两列文字随行状态着色 + 星图补 `--paused` 令牌族
  (与棱镜同值) + paused/other 行不再保持近白前景。改的是 `atlas/style.css` 与 `prism/css/views.css`;
  双 UI × 六主题截图已逐张核对(见 [pitfalls.md](pitfalls.md) 的核对手法条目), 剩**用户真机观感确认**

- **TASK015 WEB UI 错误原因展示 (2026-09-18, 已入库 `9723a76`)**: 错误种子的状态列不再只显示「错误」——
  `missingFiles` → "文件丢失"(零 API, 状态自明), `error` → tracker 报错原文(如
  `torrent not registered with this tracker`)。关键设计: qB `torrents/info` **无**错误文本字段(已核实),
  原因只能从 `torrents/trackers` 的 `msg` 取 → 主循环 `refresh_error_reasons` 按 TTL(300s)+预算(5/轮)
  预取, 视图组装**只读缓存**(视图可能每 tick 重建, 不得在里面发 API); 原因非快照字段, 变化由预取方
  **显式置脏**。剩用户真机走查 → 档案 [tasks/TASK015-webui-error-reason.md](tasks/TASK015-webui-error-reason.md)

- **WEB 跳过本地验证日志降为 INFO (2026-09-18, 已入库 `7ce54e9`)**: `web.py` 里"本机免密钥放行"提示原为 `logger.warning` → 改 `logger.info`(免鉴权是用户显式开的配置而非异常, WARNING 会经 notify 推送扰民); 变量 `_local_skip_warned` → `_local_skip_logged` 对齐; `test_web.py::test_skip_local_verify_loopback_bypass` 断言同步改为 INFO 级 + 断言不再产生 WARNING

- **TASK014 UI 组件库 20 式**: 交付物已产出并自检(文本层/渲染层/功能探针/390px 断点), 7 项缺陷已修; 剩用户挑选与按需迭代 → 档案 [tasks/TASK014-ui-component-libraries.md](tasks/TASK014-ui-component-libraries.md)

- **导出 .torrent 中文名 500 已修 (2026-09-17, 已入库 `4de0953`)**: `/api/torrents/{hash}/export` 把种子名直拼进 `Content-Disposition`, HTTP 头只能 latin-1 → 中文名 `UnicodeEncodeError` 500。修法: 新增 `web.content_disposition(filename, fallback, ext)` 双段头(`filename=` ASCII 回退 + `filename*=UTF-8''<百分号编码>`)并清洗控制字符; 测试 `test_content_disposition_encoding` + 导出端点非 ASCII 用例。剩用户真机走查
- **TASK013 第十一轮修复**: 代码/文档/验证已完, **已入库 `4a027ef`** —— 剩用户真机走查反馈
- **TASK012 第十轮修复**: 已入库 `cb57bef` (用户自行提交) —— 剩用户真机走查反馈
- **TASK011 第九轮修复**: 已入库 `49d3151`, 剩用户真机走查反馈
- **第十轮的两处已知限制**(已写入 pitfalls, 非待办): ① 列偏好受 localStorage **origin 隔离** 影响(`localhost` 与 `127.0.0.1`/换端口 = 不同站点各存一份) —— 用户明确要求只存浏览器, 不做服务端化; ② 目录浏览器只能浏览**已有保存路径及其子目录**(安全边界), 全新位置需在输入框手填
- **第十一轮的定案口径**(已写入 pitfalls, 别改回去): 行/表头一律 `fit-content; min-width: 100%`(**底色跟内容**), **行内单元格必须 `min-width: 0`**(否则 nowrap 文本把行顶宽 → 列没溢出却常驻横滚条); 曾用"行定宽 100%"治假滚动条, 会让**溢出段没有底色**(用户实测"滚动后右边无背景条"), 已回退
- **未入库的 `想法.md`**: 含用户自己的未提交改动 —— 本轮只勾选 WEBUI 条目, 其余改动未暂存, 由用户自行决定何时一并入库

## 下一步候选 (来源: `想法.md` 待办 + progress.md 规划中)

- WEB UI: WebSocket 推送; 多用户; **设置页全面重构**(`想法.md` 现存最大一条未做项)
- WEB UI: 窗口日志等级可选; 星图侧补齐第九轮的纯版式项(棱镜已做: FX-05/06/09/17~25)
- 规则系统: 条件取反 (`!`/非 logic); 重新梳理 ignore_next_action_error / stop_following_rules_if
- tracker 分组前端增强 (阶段 2/3, 2026-09-15 拍板后续): 设置页 groups 下拉快捷追加 (rules_ref 风格); 辅种管理页按组筛选 (web_view 透出 conf.groups + app.js filterDefs)
- 其它: 切分大文件; 种子未变动时不触发内置维护任务; 版本管理; 命中限速曲线强调显示; 插件系统
- 🚧 实机验证: README 标注 🚧 的功能 (alpha 阶段), 生产使用前先 `--dry-run` 观察

## 历史归档 (已迁出本文件)

2026-09-14 ~ 2026-09-17 的全部会话纪要已按专题迁移到 [tasks/](tasks/_index.md) 各档案的"历史会话纪要 (原文归档)"段 (原文未删改)。需要回查历史请走 `tasks/_index.md` 定位专题档案, 本文件只保留**当前焦点**。
