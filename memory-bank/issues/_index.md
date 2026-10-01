# Issues Index

> **本文件是生成物, 不要手改** —— 由 `../../.agents/skills/create-issue/scripts/gen_issues_index.py` 扫描 `memory-bank/issues/*.html` 的 meta
> (`issue-status` / `issue-stamp` / `issue-title` / `issue-summary` / `issue-type`)生成;
> 新增报告或改状态后重跑脚本即可, 合并冲突也只需重跑。
> 每行 = **类型 · 简述 · 报告链接**(分区即状态); 状态改在报告 HTML 的封面徽标与
> `<meta name="issue-status">`(两处一起改)。状态取值: `Open` / `In Progress` / `Done` / `Dropped` / `Superseded`。
> 文件名 = `<YY-MM-DD-HHMM>-<type>-<slug>.html`, type 取值: bug / perf / docs / test / refactor / feat / chore / question。
> **入池规则**: 计划外问题一律不改码, 只入池 —— 见 create-issue skill (../../.agents/skills/create-issue/SKILL.md)
> (该不该现在修, 见 scope-guard skill)。


## 待处理分布（Open）

| 类型 | 条数 |
|---|---|
| bug | 7 |
| perf | 3 |
| docs | 5 |
| test | 4 |
| refactor | 2 |
| feat | 5 |
| chore | 4 |

## Open

- [docs] [代码内注释残留 4 处: 仍描述已退役的委托层与旧路径](26-10-01-1738-docs-code-comment-drift.html) — 内核化重构+别名层退役后, 4 处代码内注释/docstring 与代码相反或指向已迁路径 (core/state.py:4-5 / qbmanager.py:398 / webui/runtime.py:237 / core/mixins/__init__.py docstring)
- [docs] [create-issue SKILL.md 记载的脚本路径不解析](26-10-01-1738-docs-create-issue-skill-script-refs.html) — SKILL.md:60/107-108 写 agents/skills/... 缺 .agents/ 前缀, docs_drift 判 missing-script-file; 脚本实存于 .agents/skills/create-issue/scripts/
- [test] [冒烟「列设置·隐藏列宽保留」确定性失败: 隐藏列的意图宽度读不回](26-09-30-0602-test-ui-smoke-colwidth-hidden-preserve.html) — dev.harness 列设置用例「隐藏列宽度保留」双 UI 100% 失败(key=amount_left 前=undefined 后=92px), stash 对照确认先在于键盘快捷键 W1-W4 之前, 与列偏好双轨模型的意图/生效分轨有关, 待查
- [test] [冒烟 CTX-03 多选右键批量菜单: 追剧集行确定性失败 + 辅种组行抖动](26-09-30-0602-test-ui-smoke-ctx03-multiselect.html) — dev.harness 两条 CTX-03 多选用例失败(追剧集行 100% 复现/辅种组行间歇), stash 前后对照确认先在于键盘快捷键 W1-W4 之前; Ctrl+click 选择在冒烟完整链路下不生效而孤立探针正常, 疑似轮询重渲染与 ElementHandle 的竞态或真实 UI 缺陷, 待查
- [feat] [HR 计数：上限徽章总数轴互证（P3 缓做项）](26-09-30-0052-feat-hr-badge-total-crosscheck.html) — HR 上限徽章的 Σ分档 == 总数 == 实抓 三者两两互证（HR 计划 §4 备选项 / §7 P3），依赖 D4 计数口径实证，缓做
- [feat] [HR 计数：looks_like_login 补计数文本佐证（P3 缓做项）](26-09-30-0052-feat-hr-login-counter-attest.html) — 登录态判定 looks_like_login 补页头计数文本负信号佐证（报告 26-09-29-1803 §6 登录态负信号 / HR 计划 §7 P3），依赖 D4 口径实证，缓做
- [perf] [HR 计数：末页追翻省略（P3 缓做项）](26-09-30-0052-perf-hr-lastpage-fetch-skip.html) — HR 计数启用站点翻页达末页终点后仍多做一次追翻请求；报告 26-09-29-1803 §5.1 定性为优化非简化（收益偶有、风险面新增），HR 计划 §7 P3 拍板缓做
- [feat] [WEBUI 设置页支持只读字段: 程序托管/R 级字段改为只读展示](26-09-28-2135-feat-webui-readonly-fields.html) — schema_version/data_dir/state_file/fs.path_map 渲染为可编辑但保存必然被覆盖或静默回退, 且反馈误导; 需 Field 只读标志 + 前端禁用渲染 + 写盘防线
- [docs] [插件 spec 内部键无逐键参考文档, 键面守卫出处钩暂豁免](26-09-28-1946-docs-config-plugin-spec-docs.html) — conditions/actions 插件名之下的 spec 键在 keys.md 与 rule-system/conditions-and-actions.md 均无逐键覆盖, test_config_key_surface 出处检查对该层豁免(权威单点=schema 插件表)
- [bug] [commit.py 逐路径 git add 撞「已暂存删除」路径必败](26-09-28-0128-bug-my-commit-flow-staged-delete-add.html) — ship.commit 逐路径 add 对已暂存删除(D )路径 pathspec 落空直接 FAIL; workaround=退回未暂存( D)后重跑即过, 根修应对删除路径改用 git rm --cached 口径
- [feat] [重新设计单种周期上传/下载量统计 (upload_size 四条件 + begin_round 底座已移除)](26-09-27-1248-feat-stats-redesign-torrent-traffic.html) — upload_size/today/week/month 四条件与 begin_round/upload_delta/upload_snapshots 统计底座已随计划 26-09-27-1232 暂时移除; 待重新设计: 补下载量口径或改 global_* 全局口径
- [bug] [设置页有未保存改动时刷新会丢改动(无任何提醒)](26-09-25-1702-bug-webui-settings-unsaved-changes-lost.html) — 设置页(唯一 Console Hub)编辑配置后按 F5 / 关标签 / 后退会静默丢弃未保存改动 —— 全仓无 beforeunload 提醒, cfg.tree 是内存态, 重载即被服务端树覆盖
- [test] [FakeConfig 类级共享 grouping 实例被 test_web 实例改写, test_refresh_removed_grouping_disabled 顺序敏感](26-09-22-2311-test-fakeconfig-shared-state-order-pollution.html) — FakeConfig.grouping 为类级共享实例, test_web 两处在实例上改 enabled=True 后残留全局, test_qbmanager 该用例在 test_web 先跑的自定义顺序下必红（全量字母序不触发, 与方案 C 目录迁移无关）
- [feat] [跨组文件交叉紧急处置: 防止新种子覆盖已下载/已完成文件](26-09-22-2221-feat-cross-group-file-conflict.html) — 不同组之间出现文件交叉(如同名/同路径文件已被其他组下载完成)时需要紧急处置, 防止新种子下载覆盖已有数据
- [bug] [设置页警示条是伪警示: 只复述 schema 风险文案, 不反映配置健康; 升级失效键无任何提示](26-09-22-2002-bug-webui-config-health-warning.html) — 首页警示条由『已配置且 schema 带 risk 文案』驱动, 恒亮、静态、与配置健康无关; 且 load_config 对 schema 外键静默忽略, 版本升级后配置项失效无任何提示
- [bug] [WebUI 鉴权面三个低危加固点: SSE token 查询串 / config-public 暴露 / proxy_headers](26-09-21-1408-bug-web-auth-hardening-minors.html) — SSE ticket 化或 fetch 流消费; /api/config/public 限 loopback; uvicorn 显式 proxy_headers=False 防反代 XFF 误判
- [bug] [skip_local_verify 开启后无 Origin/Host 校验, 本机任意网页可跨站驱动 WebUI 写命令](26-09-21-1408-bug-web-skip-local-verify-csrf.html) — P2: CSRF+DNS rebinding, 删除/暂停/限速写动作照常入队执行; 默认关闭但开关一开即洞
- [chore] [CI 仅 ubuntu-latest, 主力平台 Windows 不在矩阵](26-09-21-1408-chore-ci-no-windows-runner.html) — pitfalls 已载平台差异史; 托盘/注册表自启/WinRT 通知等 Windows 专属路径只有手动跑测试才被执行
- [chore] [版本号双源矛盾: __init__.__version__ 0.2.0 vs pyproject 0.1.0](26-09-21-1408-chore-version-dual-source.html) — WebUI 顶栏透出与打包元数据已差一个 minor; 建议 pyproject 单源 + 动态读取
- [docs] [文档漂移: README 称 995 用例(实测 1098), modules.md 行数快照多文件 +34%~+201%](26-09-21-1408-docs-docs-readme-modules-drift.html) — 知识库守卫不覆盖数字类事实, 漂移静默累积; 易腐数字建议守阵化或从文档退场
- [perf] [大库下四视图全量重建是单轮成本大头, 追剧视图聚合最重](26-09-21-1408-perf-webui-shows-view-full-rebuild.html) — P2: 5000 种子单轮 ~550ms(项目实测); 轮询分档已缓解, 剩余痛点在 shows 全量聚合与前端全量重算
- [refactor] [类型注解完整覆盖仅 43%, 无 mypy/pyright 配置](26-09-21-1408-refactor-type-annotations-mypy.html) — 749 个 def: 完整 43%/部分 41%/无 16%(AST 实测); 建议渐进接入, 先 torrents/config 后 mixins/web
- [refactor] [WebUIRuntime 经 self._host 回调 QbManager 私有方法, 无 Protocol 约束](26-09-21-1408-refactor-web-runtime-host-protocol.html) — web_runtime.py:312/317/479 调 _build_search_index/_state_kind 等; 建议 HostCapabilities Protocol + 单写者假设注释
- [bug] [托盘退出 join(5s) 超时即放弃主循环线程, 本次状态不落盘](26-09-21-1347-bug-tray-join-timeout-abandons-save.html) — 托盘 manager 线程 daemon=True + join(timeout=5), 优雅退出超时则放弃落盘
- [bug] [web.token 生成是非原子写, 半截文件导致鉴权密钥静默漂移](26-09-21-1347-bug-web-token-non-atomic-write.html) — ensure_web_token 用 O_TRUNC 直写, 非空半截 token 会被持久化, 已存浏览器密钥 401
- [test] [test_truth_hold_budget_matches_backend 同名定义了两次, 前一条守阵从未执行](26-09-20-2212-test-duplicate-test-name-shadowed-guard.html) — 同名函数后者覆盖前者, 前端/后端真值宽限一致性守阵实际是死测试
- [chore] [grill-me skill 是 2 行占位 stub](26-09-20-1427-chore-skill-grill-me-empty-stub.html) — grill-me 仅含 openai.yaml 与 2 行 SKILL.md, 无实际内容却占一个技能位
- [chore] [hatch-pet 调付费 OpenAI 图像 API 且无成本提示](26-09-20-1427-chore-skill-hatch-pet-api-cost.html) — hatch-pet 生成图会直连 api.openai.com 计费接口, skill 未标注费用风险
- [docs] [两个 skill 对写 USER.md 的口径相反](26-09-20-1427-docs-skill-user-md-write-conflict.html) — aesthetic-preset-library 要求写入 USER.md, autoclaw INTERACTIONS.md 明令禁止回写
- [perf] [节拍门控未减少总重建次数: 一半只是从主循环搬到请求路径](26-09-19-2122-perf-webui-poll-gate-no-net-saving.html) — 节拍门控(95fb673)在 3s 客户端档实测 41→40 次重建, 未省 CPU; 省下的 50% 只出现在 6s 档

## In Progress

- [bug] [qB 移动已完成种子时有概率把文件改名为 .!qB 后缀, 导致重新校验并误触缺文件检查](26-09-21-0219-bug-qb-move-dot-qb-suffix-recheck.html) — qB 移动种子时偶发追加 .!qB 后缀, 触发重新校验并误判缺文件

## Done

- [bug] [L2 重建抑制窗内二次重建会吞 queue_rebuilt: 全局任务从新队列丢失](26-10-01-0750-bug-events-suppress-window-queue-rebuilt.html) — rebuild_runtime 置位总线 live 抑制旗标(请求语义应只盖下轮两个事件相位), 窗口内(重建→下轮刷新轮首, 约 1 个 sync_interval)若发生第二次 L2 重建, 其 queue_rebuilt emit 被吞 -> 全局任务(delete_tags 等)不重注册, 新队列永久缺失该任务至下次重建/重启
- [bug] [弹窗分类/标签下拉仍是 mouseenter 高亮 + 键盘活动项同源并存(站点搜索闪烁同族)](26-09-29-2142-bug-dialog-hover-keynav-fight.html) — add_torrent/dialogs 的分类/标签下拉沿用 @mouseenter 直写高亮 + 键盘 ArrowDown/Up 活动项, 与站点搜索已修的闪烁同族(静止光标合成 hover 事件夺高亮)
- [bug] [站点搜索命中列表超一屏后 ↑↓ 无滚动跟随, 活动项走出视野](26-09-29-2142-bug-tracker-hit-keynav-scroll.html) — 站点搜索命中列表(max-height 300px)超出后, 键盘 ↑↓ 移动活动项无 scrollIntoView/滚动跟随, 活动项高亮走出可视区, 键盘选择在长列表上不可用
- [test] [test_file_access 两条 symlink 端到端用例依赖宿主建链能力: 本机 os.symlink 假成功(建出的不是重解析点)时断言红而非 skip, 卡住提交闸门](26-09-29-2031-test-file-access-symlink-host-capability.html) — _dir_symlink_or_skip 只捕获 OSError 而未做 os.path.islink() 判定 —— 本机 os.symlink 返回成功却建不出重解析点(R 盘与 C 盘实测均如此), 两条端到端用例因此 failed 而非 skip, test.quick 闸门恒红
- [test] [既有: 26-09-26-2345 旧计划缺 doc meta, test_docs_forms 两条守阵红](26-09-27-1153-test-plan-shipflow-v2-missing-meta.html) — plans/26-09-26-2345-plan-commands-shipflow-v2.html 缺 doc-status/doc-topic/doc-added/doc-updated, test_docs_forms::test_artifacts_meta_complete 与 test_status_vocabulary 恒红(HEAD 上复验同红)
- [test] [throttle 守阵 elapsed 容差无 sleep 精度余量, 文件级/全量跑偶发假红](26-09-22-2052-test-throttle-test-sleep-tolerance.html) — test_run_loop_throttles_without_stop_event 的 mock 场景断言 elapsed >= 0.05, Windows sleep(50ms) 实测可 46ms(定时器精度), 文件级跑时前序测试改变定时器状态即红; 单跑恒绿
- [bug] [config 校验缺少取值范围约束, 可配出合法格式但危险的值](26-09-22-1937-bug-config-value-range-validation.html) — validate_config 只拦格式与未知键, 数值/时间类配置取值范围大多无上下限约束, 可能引发运行时问题, 需逐项分析收紧
- [bug] [tracker URL 含 passkey 全文写入日志, 可经 /api/log 读回](26-09-21-1408-bug-web-tracker-url-passkey-log.html) — P2: 私站 announce URL 内嵌 passkey, 轮转日志备份/同机进程是泄露面; 建议单点 sanitize_tracker_url 脱敏
- [refactor] [web.py create_app 单函数 926 行, 鉴权与全部端点挤在一个工厂函数](26-09-21-1408-refactor-web-create-app-monolith.html) — P1: 全项目最大函数坐在唯一对外暴露面里, 本次审计三条安全发现同出一文件; 建议按域拆 Router
- [bug] [热重载 L2 分支重读磁盘 state, 运行期内存态被回滚到上次退出版本](26-09-21-1347-bug-backend-hot-reload-l2-state-rollback.html) — apply_new_config L2 分支 self.state=_load_state() 用磁盘旧版覆盖内存态, Web UI 改规则保存即确定性触发
- [bug] [后端状态仅优雅退出时落盘, 非优雅终止丢失整个运行期状态](26-09-21-1347-bug-backend-state-save-only-on-exit.html) — save_state 仅优雅退出可达, 强杀/断电/关机丢 exec_history/skip_check_day/recheck_fails/上传基线
- [bug] [跳检「删除→重加」之间存在无备份崩溃窗口, 崩溃后种子无恢复凭据](26-09-21-1347-bug-skip-checking-readd-no-backup-window.html) — 删除确认后重加前崩溃: .torrent 仅在内存、备份只在重加失败路径, 重启后无任何恢复标记
- [bug] [state.json 损坏时静默清空, .bak 备份从不用于恢复](26-09-21-1347-bug-state-load-corrupt-silent-reset.html) — _load_state 吞 JSONDecodeError 静默返回 {}; atomic_write 维护的 .bak 全库无读取方
- [test] [sim_qb 缺「/sync/maindata 快照滞后」模型, 本地无法复现/验证真值直查的收益](26-09-20-2145-test-sim-qb-maindata-snapshot-lag.html) — 仿真端状态瞬时翻转, 掩盖一切'真值尚未落地'类缺陷; 需加 1.5s 快照滞后模型
- [bug] [状态栏今日流量: 图标与数值同色且非真图标, 易被读成数值的一部分](26-09-20-1840-bug-webui-statusbar-traffic-icon.html) — 今日流量块图标(#i-chart)与 ↑/↓ 数值同色同排, 易误读为数值一部分; 棱镜侧同病且图标无颜色
- [bug] [WebUI 列设置(顺序/显示/宽度)经常被重置](26-09-20-1800-bug-webui-column-prefs-reset.html) — 表格列的顺序/显隐/宽度偏好偶发丢失, 刷新后回到默认布局
- [bug] [状态栏上传/下载速度不更新, 恒显示 0](26-09-20-1646-bug-webui-statusbar-speed-always-zero.html) — 状态栏速度由前端对 groups 求和(totalDl/totalUl), 真机有下载/上传时仍恒为 0
- [test] [主循环节拍断言无容差: 机器负载高时偶发假红](26-09-20-0952-test-mainloop-tick-timing-flaky.html) — test_qbmanager.py:186 断言 elapsed >= 0.05 无容差, 负载下实测 0.046s 即假失败
- [docs] [conventions.md 的『绝对不要 push』与 AGENTS.md 现行『提交=commit+自动推送』矛盾](26-09-19-2359-docs-memory-bank-push-rule-drift.html) — 知识库 Git 约定仍写禁 push, 与 2026-09-19 用户新规相反, 会让 agent 拒绝推送
- [bug] [3s 兜底超时后补丁值永久留在行上: 「不再贴、等下轮服务端」在 rid 门控下不成立](26-09-19-2141-bug-webui-pending-timeout-stale-patch.html) — isPending() 超时只 delete pendingOps[hash], 注释称'下轮以服务端为准'; 但 rid 未变时服务端不回传数组、行对象不被替换 ⇒ 乐观补丁(kind=paused)留在行上不走。hang 模式实测: 3.66s 清 pending 后行仍 s-paused, 真值 s-downloading
- [bug] [乐观态要挂满 3 秒才消除: 「真值匹配即清」从未实现, 且回执后不立即拉真值](26-09-19-2024-bug-webui-truth-convergence.html) — pendingOps 只有超时/失败两个清除点(app.js:2315/2361), 真值到了也不清; 且 act*/bulk 回执后无 refresh, 真值要等下一轮轮询(>3000 种子 3s) —— 用户报的「乐观后 2-4s 才恢复」
- [bug] [整剧(show 级)操作在剧行上没有 is-pending 标记: 补丁 0ms 贴上但用户看不到任何即时反馈](26-09-19-1959-bug-webui-show-row-no-pending.html) — 剧行 .show-row 不绑 is-pending(只有集行 .ep-row 绑), 整剧暂停/开始时剧行折叠 ⇒ 补丁 0ms 也无可见反馈; 与 BUG-3 同类的漏绑
- [perf] [乐观 UI 反应迟缓: 真机点击后约 2-4 秒才看到变化(补丁被 POST 往返挡在后面)](26-09-19-1939-perf-webui-optimistic-latency.html) — 乐观补丁在 await POST 之后才贴(app.js:3319→3327 等 4 处), 真机点击到界面变化 2-4s, 违背「点击即变」设计; 需先定测量口径再定位 POST 慢还是命令消费慢
- [bug] [sync_interval 与前端分档轮询错配: >3000 种子时约一半视图重建无人消费](26-09-19-1900-bug-webui-poll-cadence-mismatch.html) — 服务端固定 1.5s 重建四视图, 前端 >3000 种子时 3s 才取一次 ⇒ 约一半 rebuild_views 无人消费; 需先拍板方向
- [perf] [/api/search 等热端点仍返回裸 dict: 服务端白跑 jsonable_encoder(实测 82.6 ms)](26-09-19-1900-perf-webui-hot-endpoints-jsonable-encoder.html) — /api/state 与 /api/groups 已改 JSONResponse 直返(189→23.5ms), /api/search(1.46MB/82.6ms)与详情族未改

## Dropped

(暂无)

## Superseded

- [question] [doc-map 容量无余量: 任何新「计划+档案」对必破 12200 cap](26-09-28-0219-question-kb-doc-map-cap.html) — HEAD 源重生成 12153/12200 (余 47 字符), 一笔合规计划+档案对固定占 ~106 字符; topic 收口反而增大文件 —— 需要定调: 提 cap / 砍单件登记段 / 精简多件条目
