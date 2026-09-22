# Issues Index

> **本文件是生成物, 不要手改** —— 由 `../../.agents/skills/create-issue/scripts/gen_issues_index.py` 扫描 `memory-bank/issues/*.html` 的 meta
> (`issue-status` / `issue-stamp` / `issue-title` / `issue-summary` / `issue-type`)生成;
> 新增报告或改状态后重跑脚本即可, 合并冲突也只需重跑。
> 每行 = **类型 · 简述 · 报告链接**(分区即状态); 状态改在报告 HTML 的封面徽标与
> `<meta name="issue-status">`(两处一起改)。状态取值: `Open` / `In Progress` / `Fixed` / `WontFix` / `Duplicate`。
> 文件名 = `<YY-MM-DD-HHMM>-<type>-<slug>.html`, type 取值: bug / perf / docs / test / refactor / feat / chore / question。
> **入池规则**: 计划外问题一律不改码, 只入池 —— 见 create-issue skill (../../.agents/skills/create-issue/SKILL.md)
> (该不该现在修, 见 scope-guard skill)。


## 待处理分布（Open）

| 类型 | 条数 |
|---|---|
| bug | 7 |
| perf | 2 |
| docs | 2 |
| test | 2 |
| refactor | 3 |
| chore | 4 |

## Open

- [bug] [WebUI 鉴权面三个低危加固点: SSE token 查询串 / config-public 暴露 / proxy_headers](26-09-21-1408-bug-web-auth-hardening-minors.html) — SSE ticket 化或 fetch 流消费; /api/config/public 限 loopback; uvicorn 显式 proxy_headers=False 防反代 XFF 误判
- [bug] [skip_local_verify 开启后无 Origin/Host 校验, 本机任意网页可跨站驱动 WebUI 写命令](26-09-21-1408-bug-web-skip-local-verify-csrf.html) — P2: CSRF+DNS rebinding, 删除/暂停/限速写动作照常入队执行; 默认关闭但开关一开即洞
- [chore] [CI 仅 ubuntu-latest, 主力平台 Windows 不在矩阵](26-09-21-1408-chore-ci-no-windows-runner.html) — pitfalls 已载平台差异史; 托盘/注册表自启/WinRT 通知等 Windows 专属路径只有手动跑测试才被执行
- [chore] [版本号双源矛盾: __init__.__version__ 0.2.0 vs pyproject 0.1.0](26-09-21-1408-chore-version-dual-source.html) — WebUI 顶栏透出与打包元数据已差一个 minor; 建议 pyproject 单源 + 动态读取
- [docs] [文档漂移: README 称 995 用例(实测 1098), modules.md 行数快照多文件 +34%~+201%](26-09-21-1408-docs-docs-readme-modules-drift.html) — 知识库守卫不覆盖数字类事实, 漂移静默累积; 易腐数字建议守阵化或从文档退场
- [perf] [大库下四视图全量重建是单轮成本大头, 追剧视图聚合最重](26-09-21-1408-perf-webui-shows-view-full-rebuild.html) — P2: 5000 种子单轮 ~550ms(项目实测); 轮询分档已缓解, 剩余痛点在 shows 全量聚合与前端全量重算
- [refactor] [类型注解完整覆盖仅 43%, 无 mypy/pyright 配置](26-09-21-1408-refactor-type-annotations-mypy.html) — 749 个 def: 完整 43%/部分 41%/无 16%(AST 实测); 建议渐进接入, 先 torrents/config 后 mixins/web
- [refactor] [web.py create_app 单函数 926 行, 鉴权与全部端点挤在一个工厂函数](26-09-21-1408-refactor-web-create-app-monolith.html) — P1: 全项目最大函数坐在唯一对外暴露面里, 本次审计三条安全发现同出一文件; 建议按域拆 Router
- [refactor] [WebUIRuntime 经 self._host 回调 QbManager 私有方法, 无 Protocol 约束](26-09-21-1408-refactor-web-runtime-host-protocol.html) — web_runtime.py:312/317/479 调 _build_search_index/_state_kind 等; 建议 HostCapabilities Protocol + 单写者假设注释
- [bug] [热重载 L2 分支重读磁盘 state, 运行期内存态被回滚到上次退出版本](26-09-21-1347-bug-backend-hot-reload-l2-state-rollback.html) — apply_new_config L2 分支 self.state=_load_state() 用磁盘旧版覆盖内存态, Web UI 改规则保存即确定性触发
- [bug] [后端状态仅优雅退出时落盘, 非优雅终止丢失整个运行期状态](26-09-21-1347-bug-backend-state-save-only-on-exit.html) — save_state 仅优雅退出可达, 强杀/断电/关机丢 exec_history/skip_check_day/recheck_fails/上传基线
- [bug] [托盘退出 join(5s) 超时即放弃主循环线程, 本次状态不落盘](26-09-21-1347-bug-tray-join-timeout-abandons-save.html) — 托盘 manager 线程 daemon=True + join(timeout=5), 优雅退出超时则放弃落盘
- [bug] [web.token 生成是非原子写, 半截文件导致鉴权密钥静默漂移](26-09-21-1347-bug-web-token-non-atomic-write.html) — ensure_web_token 用 O_TRUNC 直写, 非空半截 token 会被持久化, 已存浏览器密钥 401
- [bug] [qB 移动已完成种子时有概率把文件改名为 .!qB 后缀, 导致重新校验并误触缺文件检查](26-09-21-0219-bug-qb-move-dot-qb-suffix-recheck.html) — qB 移动种子时偶发追加 .!qB 后缀, 触发重新校验并误判缺文件
- [test] [test_truth_hold_budget_matches_backend 同名定义了两次, 前一条守阵从未执行](26-09-20-2212-test-duplicate-test-name-shadowed-guard.html) — 同名函数后者覆盖前者, 前端/后端真值宽限一致性守阵实际是死测试
- [chore] [grill-me skill 是 2 行占位 stub](26-09-20-1427-chore-skill-grill-me-empty-stub.html) — grill-me 仅含 openai.yaml 与 2 行 SKILL.md, 无实际内容却占一个技能位
- [chore] [hatch-pet 调付费 OpenAI 图像 API 且无成本提示](26-09-20-1427-chore-skill-hatch-pet-api-cost.html) — hatch-pet 生成图会直连 api.openai.com 计费接口, skill 未标注费用风险
- [docs] [两个 skill 对写 USER.md 的口径相反](26-09-20-1427-docs-skill-user-md-write-conflict.html) — aesthetic-preset-library 要求写入 USER.md, autoclaw INTERACTIONS.md 明令禁止回写
- [test] [主循环节拍断言无容差: 机器负载高时偶发假红](26-09-20-0952-test-mainloop-tick-timing-flaky.html) — test_qbmanager.py:186 断言 elapsed >= 0.05 无容差, 负载下实测 0.046s 即假失败
- [perf] [节拍门控未减少总重建次数: 一半只是从主循环搬到请求路径](26-09-19-2122-perf-webui-poll-gate-no-net-saving.html) — 节拍门控(95fb673)在 3s 客户端档实测 41→40 次重建, 未省 CPU; 省下的 50% 只出现在 6s 档

## In Progress

(暂无)

## Fixed

- [bug] [config 校验缺少取值范围约束, 可配出合法格式但危险的值](26-09-22-1937-bug-config-value-range-validation.html) — validate_config 只拦格式与未知键, 数值/时间类配置取值范围大多无上下限约束, 可能引发运行时问题, 需逐项分析收紧
- [bug] [tracker URL 含 passkey 全文写入日志, 可经 /api/log 读回](26-09-21-1408-bug-web-tracker-url-passkey-log.html) — P2: 私站 announce URL 内嵌 passkey, 轮转日志备份/同机进程是泄露面; 建议单点 sanitize_tracker_url 脱敏
- [bug] [跳检「删除→重加」之间存在无备份崩溃窗口, 崩溃后种子无恢复凭据](26-09-21-1347-bug-skip-checking-readd-no-backup-window.html) — 删除确认后重加前崩溃: .torrent 仅在内存、备份只在重加失败路径, 重启后无任何恢复标记
- [bug] [state.json 损坏时静默清空, .bak 备份从不用于恢复](26-09-21-1347-bug-state-load-corrupt-silent-reset.html) — _load_state 吞 JSONDecodeError 静默返回 {}; atomic_write 维护的 .bak 全库无读取方
- [test] [sim_qb 缺「/sync/maindata 快照滞后」模型, 本地无法复现/验证真值直查的收益](26-09-20-2145-test-sim-qb-maindata-snapshot-lag.html) — 仿真端状态瞬时翻转, 掩盖一切'真值尚未落地'类缺陷; 需加 1.5s 快照滞后模型
- [bug] [状态栏今日流量: 图标与数值同色且非真图标, 易被读成数值的一部分](26-09-20-1840-bug-webui-statusbar-traffic-icon.html) — 今日流量块图标(#i-chart)与 ↑/↓ 数值同色同排, 易误读为数值一部分; 棱镜侧同病且图标无颜色
- [bug] [WebUI 列设置(顺序/显示/宽度)经常被重置](26-09-20-1800-bug-webui-column-prefs-reset.html) — 表格列的顺序/显隐/宽度偏好偶发丢失, 刷新后回到默认布局
- [bug] [状态栏上传/下载速度不更新, 恒显示 0](26-09-20-1646-bug-webui-statusbar-speed-always-zero.html) — 状态栏速度由前端对 groups 求和(totalDl/totalUl), 真机有下载/上传时仍恒为 0
- [docs] [conventions.md 的『绝对不要 push』与 AGENTS.md 现行『提交=commit+自动推送』矛盾](26-09-19-2359-docs-memory-bank-push-rule-drift.html) — 知识库 Git 约定仍写禁 push, 与 2026-09-19 用户新规相反, 会让 agent 拒绝推送
- [bug] [3s 兜底超时后补丁值永久留在行上: 「不再贴、等下轮服务端」在 rid 门控下不成立](26-09-19-2141-bug-webui-pending-timeout-stale-patch.html) — isPending() 超时只 delete pendingOps[hash], 注释称'下轮以服务端为准'; 但 rid 未变时服务端不回传数组、行对象不被替换 ⇒ 乐观补丁(kind=paused)留在行上不走。hang 模式实测: 3.66s 清 pending 后行仍 s-paused, 真值 s-downloading
- [bug] [乐观态要挂满 3 秒才消除: 「真值匹配即清」从未实现, 且回执后不立即拉真值](26-09-19-2024-bug-webui-truth-convergence.html) — pendingOps 只有超时/失败两个清除点(app.js:2315/2361), 真值到了也不清; 且 act*/bulk 回执后无 refresh, 真值要等下一轮轮询(>3000 种子 3s) —— 用户报的「乐观后 2-4s 才恢复」
- [bug] [整剧(show 级)操作在剧行上没有 is-pending 标记: 补丁 0ms 贴上但用户看不到任何即时反馈](26-09-19-1959-bug-webui-show-row-no-pending.html) — 剧行 .show-row 不绑 is-pending(只有集行 .ep-row 绑), 整剧暂停/开始时剧行折叠 ⇒ 补丁 0ms 也无可见反馈; 与 BUG-3 同类的漏绑
- [perf] [乐观 UI 反应迟缓: 真机点击后约 2-4 秒才看到变化(补丁被 POST 往返挡在后面)](26-09-19-1939-perf-webui-optimistic-latency.html) — 乐观补丁在 await POST 之后才贴(app.js:3319→3327 等 4 处), 真机点击到界面变化 2-4s, 违背「点击即变」设计; 需先定测量口径再定位 POST 慢还是命令消费慢
- [bug] [sync_interval 与前端分档轮询错配: >3000 种子时约一半视图重建无人消费](26-09-19-1900-bug-webui-poll-cadence-mismatch.html) — 服务端固定 1.5s 重建四视图, 前端 >3000 种子时 3s 才取一次 ⇒ 约一半 rebuild_views 无人消费; 需先拍板方向
- [perf] [/api/search 等热端点仍返回裸 dict: 服务端白跑 jsonable_encoder(实测 82.6 ms)](26-09-19-1900-perf-webui-hot-endpoints-jsonable-encoder.html) — /api/state 与 /api/groups 已改 JSONResponse 直返(189→23.5ms), /api/search(1.46MB/82.6ms)与详情族未改

## WontFix

(暂无)

## Duplicate

(暂无)
