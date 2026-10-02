# issue-clearance-roadmap — Issue 全量清偿路线图(滚动执行)

> 摘要: 用户两轮要求的摸排-分波-排期任务,路线图已出至 **v2**:
> [plans/26-10-01-1758-plan-issue-clearance-roadmap.html](../plans/26-10-01-1758-plan-issue-clearance-roadmap.html)(同文件改版, 变更记录见 §A)。
> v1(26-10-01)摸排 31 条分七波, 其后清偿 12 条(v1-W1 闸门波 5/5 全清、v1-W2 3/4, 明细迁
> progress/implemented-core.md · implemented-webui.md + issues Done 分区, 此处只留路标)。
> v2(26-10-02 02:34)在「清偿 12 条 + 新入池 46 条」后改版: 未决 31→**59 条**(58 Open + 1 In Progress),
> test 类型清零(闸门已绿, 基线 26-10-02-0203: 2143+3 / 96.49%), 重排**九波**:
> W1 后端速赢(凭据/状态/鉴权 4)→ W2 WebUI 正确性(7)→ W3 数据安全大件(3)→ W4 性能(4)→
> W5 HR/统计拍板簇(6)→ W6 体验批(13)→ W7 扩展(3)→ W8 穿插(13)→ W9 挂账(6, 不排期)。
> 关键标记: 26-09-22-2221(跨组交叉)用户曾排除, 开工需单独授权; transmission-compat 停在拍板(报告 26-10-01-2347);
> 热重载两条 / EXT 两条 / tag-category-dialog 开工先复验。滚动档案 = tasks/26-10-02-memory-bank-issue-clearance-roadmap.md。
> **待办**: W1 起逐波推进, 每波待用户显式授权; 未全清计划不转 Done; 实时以 issues/_index.md 为准。
> **W1 已收官(3/3, 用户授权后 26-10-02 当日完成)**: ① hr.token 生成改原子写(issue 26-10-01-2151
> → Done, 档案 [tasks/26-10-02-hr-token-atomic-write.md](../tasks/26-10-02-hr-token-atomic-write.md));
> ② HrEntry.last_seen 写入点 + INDEX_RETENTION 清理复活(issue 26-10-01-2335 → Done,
> 档案 [tasks/26-10-02-hr-entry-last-seen-prune.md](../tasks/26-10-02-hr-entry-last-seen-prune.md));
> ③ web 鉴权加固双件(issue 26-09-21-1408 CSRF + 鉴权三小件 → Done,
> 档案 [tasks/26-10-02-web-auth-hardening.md](../tasks/26-10-02-web-auth-hardening.md))。
> 收官基线 26-10-02-0459: 2288+3 / 99.01%(阈值 98)。
> **W1 收官后范围外发现统一入池(26-10-02, 用户授权)**: ① `_sign_releases` 对已 verified
> infohash 不查重整条覆写(26-10-02-0526 bug/疑点, 可达性待核) ② hr/service.py 直调 time.time()
> 绕过 now_fn(26-10-02-0526 refactor/light) ③ O_TRUNC 直写静态守阵并入(26-10-02-0527 test/light,
> 生效条件已达成)。池内实测 Open 63 + In Progress 2(transmission + 26-09-25-1702 已被并行
> clone 认领出调研报告 be74bbe1; 含并行 clone 328a6704 入池 6 条);
> 新条目并入波次待路线图下次改版。**下一步: W2(WebUI 正确性 7 条)待用户显式授权。**
> **全表状态核对轮(2026-10-02, 用户指派「核对+加状态栏」, 主会话委派 5 批次串行子智能体,
> 每批次单独提交: a26123e5 结构+W1-W2 → 3e77fb57 W3-W5 → cfbfa712 W6 → d354745b W7-W8
> → 7c61e87a W9+复核+池计数刷新)**: 59 条逐一静态核对(读档案+查代码+git log 交叉, 不跑测试),
> 九张波次表各加「状态」列(五档: ✅已修复/🔶部分修复/⛔已过时/⏳待处理/📌挂账, 格内附依据),
> §1 末加图例与全表统计小结, §A 变更记录 v2.1-v2.5。最终分布 **✅8 / 🔶3 / ⛔4 / ⏳39 / 📌5**。
> 顺带回写池状态 7 份(meta+徽标+状态日志): Done 3(2108-selection-follow-mouse /
> 2108-esc-clear-filter / 1408-web-runtime-host-protocol) · Dropped 3(2129-batch-warning-notify /
> 2138-traffic-history-chart / 0052-hr-login-counter-attest) · Superseded 1(2129-hotreload-ext-vanish),
> `_index.md` 随每批次 kb.index 重建。**存疑留给用户**: login-counter-attest 判 ⛔ 的依据是负信号
> 守卫(5c518b3b)早于入池、入池前提当日即不成立, 不认可则一行改回 Open; W5 hr-online-vs-sitewide
> 配置收敛后混淆是否仍成立静态无法确证, 待拍板。核对期间池内又入 13 条 26-10-02 记录(不在 59 行内,
> 待下次改版并入), roadmap 封面计数已按 18:45 实测刷新。零生产代码改动, 无测试基线需求。
> **下一步**: 按状态列推进 —— 39 ⏳(W2 正确性簇 3 条仍未动) + 39 条中 W3 大件需方案先行;
> 逐波开工仍待用户显式授权。
> 最后活动: 2026-10-02 18:50(状态核对轮)
