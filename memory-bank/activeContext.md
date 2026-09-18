# Active Context — 当前焦点

> Memory Bank 核心文件之一: 回答"现在正在做什么 / 上次做到哪 / 下一步从哪继续"。**每次会话开始先读本文件。**
> 稳定事实在 projectbrief / productContext / systemPatterns / techContext 与各主题文档; 计划与完成状态在 [progress.md](progress.md); 本文件只放**易变的会话级状态**。
> 维护纪律 (完整规程见 [memory-bank skill](../.agents/skills/memory-bank/SKILL.md)): ①每次会话收尾更新本文件, 已完成条目沉淀到 [progress.md](progress.md) 或主题文档后**删除** — 本文件只放易变状态; ②命中立档阈值的任务在 [tasks/](tasks/_index.md) 立档并同步索引; ③**禁止**在本文件追加长流水账纪要 (会淹没真正的当前焦点)。

**最后更新**: 2026-09-18 (①WEB UI **错误种子状态列改显示具体原因**(`missingFiles`→"文件丢失" / `error`→tracker `msg` 原文): 后端主循环 TTL+预算预取 + `error_reason` 透出 + 前端 `stateText` 双 UI 生效, 1006 passed, **未提交** — 详见 [tasks/TASK015](tasks/TASK015-webui-error-reason.md) ②WEB 跳过本地验证提示日志由 WARNING 降为 INFO — 免鉴权是显式配置而非异常, 避免经 notify 推送扰民; `test_web.py` 断言同步 ②TASK014 UI 组件库 20 式**已提交** `fae019a`, 996 passed — 详见 [tasks/TASK014](tasks/TASK014-ui-component-libraries.md) ③清理并行分支造成的重复档案: 删除与 TASK014 逐字节相同的 `TASK015-ui-component-libraries.md` + 索引重复条目, 守卫测试新增同 slug/重复登记检查)

## 正在进行

- **TASK015 WEB UI 错误原因展示 (2026-09-18, 未提交)**: 错误种子的状态列不再只显示「错误」——
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
