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
> 最后活动: 2026-10-02 05:36
