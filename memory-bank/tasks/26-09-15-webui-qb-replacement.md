# 26-09-15-webui-qb-replacement — WEB UI 替代 qB 界面 (波次一 ~ 波次三 + 复查)

**Status:** In Progress
**Added:** 2026-09-15
**Updated:** 2026-09-24
**专题:** WEB UI / 替代 qB 界面 / 后端 Web 层
**Legacy-ID:** TASK002
**Summary:** 32 工作项双 UI 同构 + 两大根因修复完成并已入库; 2026-09-24 补修添加种子回执与 optional 选项(子任务 2.11); 剩实机 CDP 双 UI 走查 + 真机 dry-run + prism 追剧模板
**Topics:** webui-qb-replacement

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
- [x] git 提交 (复查修复已入库 `82652fc`)

## 子任务状态表

| ID | 描述 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| 2.1 | 调研与计划 (替代 qB 可行性) | Complete | 2026-09-15 | `memory-bank/plans/26-09-16-0123-webui-qb-replacement-plan.html` |
| 2.2 | 波次一 (视图 + 详情 + 写命令) | Complete | 2026-09-16 | 964 passed |
| 2.3 | 波次二 (管理包) | Complete | 2026-09-16 | 971 passed; 报告 `DELIVERY/webui-qb-replace-report.md` |
| 2.4 | 波次三计划 (30→32 工作项) | Complete | 2026-09-16 | `memory-bank/plans/26-09-16-1128-webui-qb-replace-wave3-plan.html` |
| 2.5 | 波次三盘点与交接 | Complete | 2026-09-17 | `memory-bank/plans/26-09-17-0346-webui-qb-replace-wave3-handover.html` |
| 2.6 | 波次三收口实施 (双 UI 同构) | Complete | 2026-09-17 | 988 passed; 星图 + 棱镜双车道 |
| 2.7 | 复查修复 (弹窗/CSS/口径 6 项) | Complete | 2026-09-17 | 989 passed; 守阵扩展 |
| 2.8 | 实机 CDP 双 UI 冒烟 + 真机 dry-run | Not Started | 2026-09-17 | 需浏览器自动化环境 |
| 2.9 | git 提交 (复查修复) | Not Started | 2026-09-17 | 等用户指示 |
| 2.10 | prism 追剧模板欠账 | Not Started | 2026-09-17 | `viewMode=shows` 目前兑底渲染种子页 |
| 2.11 | 添加种子回执误报 + optional 选项不生效 (真机 bug) | Complete | 2026-09-24 | 1225 passed; 三条根因均已红验 |

## 进度日志

### 2026-09-24

- **真机 bug: 添加种子显示失败(实际成功)+ 桌面 WARNING 弹窗 + 「添加后开始」不生效**。三条根因, 全部实测取证:
  ① 回执只认 `"Ok." in str(result)`, 而 qB 5.2.3(Web API 2.14.0 起)`/torrents/add` 已改回 **JSON 元数据**
  (`TorrentsAddedMetadata`, dict 子类)⇒ 判定恒假; ② 停止位被"False 就不传"的过滤器吞掉 ⇒ qB 回落到
  **会话级**默认 `isAddTorrentStopped()`; 另 qbittorrent-api 的 `is_paused or is_stopped` 会把
  `is_paused=False` 折成 `None`(实测请求体空串)⇒ 只能用 `is_stopped=`; ③ 成功路径记 WARNING, 而
  NotifyHandler 挂 `auto_qb` logger ⇒ 每次成功都推桌面弹窗。
- 修法: 新增 `webui/commands.py::_add_outcome` 双形态判定 + 两个 optional 选项
  (`is_stopped` / `use_auto_torrent_management`)恒显式下发 + 成功 INFO / 未受理才 WARNING。
  判据升级为"看 qB `addtorrentparams.h` 字段类型 —— `std::optional` 的必须显式, 普通 `bool` 省略安全"。
- 守阵: `test_web.py::test_add_torrent_receipt_and_optional_flags`(四条断言各自反向对照红验);
  替身补 `is_stopped` / `is_stopped_raw`(保真度)。闸门 **1232 passed + 1 skipped** / TOTAL 91%
  (提交前主线已前进 2 个提交, 按「移出改动 → `merge --ff-only` → 施回改动」同步后实测)。
- 回写: `pitfalls/backend/qb-api.md`(两条新坑)· `pitfalls/testing/stubs-sim.md`(仿真保真度 + caplog 陷阱)·
  `testing/baseline.md` + `baseline-history.md`。

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

> 原纪要约 9,396 字符 **已外迁** → [attachments/webui-qb-replacement-sessions.md](attachments/webui-qb-replacement-sessions.md)
