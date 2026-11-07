# 26-11-08-webui-legacy-review4-webui-py-fix — 存量评审 R4 webui-py 主题修复批: 25 条批A-批L 委派实施与收编

**Status:** Done
**Added:** 2026-11-08
**Updated:** 2026-11-08
**Summary:** issue 26-11-07-0536(R4 存量评审 webui-py 主题, 25 条 = major 2/minor 23)修复批: 批A-批L 共 11 commit 委派实施(编排方统一提交); 逐批评审+接缝终审均无 blocker; 2 处改道(表行17 前提失真按实际契约守阵 / 表行22 防 30s 振荡); 真机两准入门(批K, 用户拍板)+真机挖出产品缺陷顺手修(批L); 全量回归全绿(见 kb.baseline); issue 收编 Open→Done; 计划外入池 11 件。
**Topics:** webui-legacy-review4-webui-py-fix
**Refs:** memory-bank/issues/26-11-07-0536-bug-legacy-review4-webui-py.html, memory-bank/testing/baselines/26-11-08-0025-r4-webui-py-closeout.md, memory-bank/pitfalls/ops/venv-trampoline-clone-copy.md

## 本篇只回答

issue 26-11-07-0536(R4 存量评审 webui-py 主题, 25 条)怎么组织修复、验证与收编 —— 批次映射、2 处改道、真机准入与收口动作在本篇; 逐条明细表在 issue 侧, 本档案不复述。

## 原始请求

1. 认领修复 issue 26-11-07-0536(存量评审 R4·webui-py 汇总, major 2/minor 23 共 25 条): 分支 fix/r4-webui-py(基于 develop f7ac0e46)批A-批L 委派实施, 每批独立 commit, 提交由编排方统一负责。
2. 执行期拍板: 表行21(R4#27)本轮补真机用例(批K RM08-14); 批K 真机挖出的产品缺陷(qbapi.set_alt_speed_limits 签名漂移)顺手修(批L, 用户拍板)。
3. 收口: 逐批评审 + 接缝终审均无 blocker 后, issue 收编 Open→Done, 收尾回写与立档(本轮纯文档面, agent 零 git 写)。

## 思考过程与决策

- **委派模型**: 25 条按表行聚 11 个修复批(批A-批I、批K、批L)串行实施, 每批独立 commit 批次边界可回溯; 复验口径 = 认领后先逐条锚点重定位(行号漂移按符号, freeze f0883292 后代码已漂移), 25/25 仍复现再修。
- **改道①(表行17/R4#37)**: issue「零测试覆盖」前提经复验失真 —— HA.X 用例已在 tests/, 真缺口是 400 detail 契约无守阵; 且存储层口径是文件名安全集而非 40/64 hex, 按实际契约补 detail 断言守阵(不照建议修法的「非 40/64 位 hex」表述)。
- **改道②(表行22/R4#15)**: 建议修法(亮灯时同步置 suspect_since=0)单做会 30s 振荡 —— 实施改道: 亮灯清 suspect_since + 补「已亮且仍报错保持已亮」早退, 已亮记录才真正落 buckets[1] 按 TRACKER_LIT_TTL 调度。
- **真机准入(批K)**: RM07-11(ALT 限速真下发)与 RM08-14(tracker 报错原文/健康 chip)两条真机轨准入门, 用户拍板本轮补; RM07-11 首跑 BLOCKED 暴露 qbapi.set_alt_speed_limits 签名漂移(真机挖出的产品缺陷)→ 批L 一行修 + 用例升档全量真断言。
- **计划外发现处置**: 修复/真机过程中撞出的计划外缺陷一律不改码, 入池 11 件 + 口径拍板 1 件(question), 见「影响面与验证」。

## 实现计划

无独立计划 HTML(用户指令直行)。链路: 批A-批L(串行委派 + 每批 commit, 编排方统一提交)→ 接缝终审 → 全量回归 + 基线切片 → issue 收编 Open→Done + 11 件入池 + 立档回写。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 批A | 行1(R4#14 major) hr_wave 登记 _pending_full_reasons + 行13(R4#23) + 行25 半边(runtime_views.py:475, R4#20) | Done(2026-11-08, 980e2cce) |
| 批B | 行2(R4#33 major) tracker 入库单点掩码(apply_delta 收口)+ 规则表达式 tracker.url 与 /api/expr/eval 收紧 | Done(2026-11-08, 48f2ce8b) |
| 批C | 行3(R4#10) 守阵注释改实际文件名 + 行4(R4#3) 单发限速负数 400 + 行7(R4#1) 整组迁移缺失计数进回执 | Done(2026-11-08, f8bde913) |
| 批D | 行6(R4#4) + 行8(R4#22) + 行24(R4#24) 带圈数字清 ASCII | Done(2026-11-08, e8c3766c) |
| 批E | 行9(R4#16) runtime.py 死导入 13 个 + 行10(R4#2) check_pending 读失败留 pending + 行11(R4#9) effect-confirmation.md D2 回写 + 行12(R4#8) _truth_landed docstring | Done(2026-11-08, e48c023e) |
| 批F | 行14(R4#34) keys.py re.fullmatch + 行15(R4#31) ChainCache miss deepcopy + 行16(R4#30) torrent_cmds 五处接 _list_param | Done(2026-11-08, 45c04c07) |
| 批G | 行17(R4#37, 改道) 非法哈希 400 detail 契约补断言 + 行18(R4#29) traffic_qb tuple 快照 | Done(2026-11-08, 6379679e) |
| 批H | 行20(R4#17) views.py 死导入 7 个 + 行22(R4#15, 改道) 已亮分档可达化 + 行23(R4#21) 失败 hash 不入索引+保住 dirty + 行25 半边(views_group.py:132) | Done(2026-11-08, 651d2fe6) |
| 批I | 行19(R4#19) _ensure_thread 检查+创建段加实例锁 | Done(2026-11-08, a79cc045) |
| 批K | 行5(R4#13) RM07-11 ALT 限速真机用例 + 行21(R4#27) RM08-14 tracker 报错真机用例(用户拍板本轮补真机用例) | Done(2026-11-08, c56ef164) |
| 批L | 批K 真机挖出产品缺陷顺手修(非 issue 条目, 用户拍板): qbapi set_alt_speed_limits 签名漂移一行修, RM07-11 升档全量真断言 | Done(2026-11-08, 6352ccc8) |
| 收编 | issue Open→Done(复验/修复后补充落档)+ 11 件入池 + 立档回写 | Done(2026-11-08) |

(批号无 J —— 批A-批L 跳号, 共 11 commit 齐表行 25 条。)

## 影响面与验证

- 代码: src/auto_qb/webui/ 16 文件(批A/C/E/F/G/H/I) + 批D 三文件带圈数字清 ASCII + src/auto_qb/core/qbapi.py 一行(批L) + src/auto_qb/torrents/record.py tracker 槽位掩码(批B); tests-real/ 3 文件(批K); tests/ 新增/扩展 12 文件净增 14 例; 11 commit(git diff develop...HEAD: 34 文件 +1317/-137)。
- 验证: 逐批评审 + 接缝终审均无 blocker; 全量回归全绿(数字单点见 kb.baseline 切片 26-11-08-0025-r4-webui-py-closeout); 真机轨两准入门全过(RM07-11 三轮复跑、RM08-14, 断言升档见批L)。
- 计划外入池 11 件(2026-11-08 stamps, 见 issues/_index.md)+ 口径拍板 1 件(question): 泄敏同族 magnet_uri、add 面列表型参数、tool_client stop 竞态、views.py 残留死导入、effect-confirmation 陈旧指针、带圈数字第二片、RM08 基座 schema_version 过期、clock wait_until desc 惰性、非 ASCII 口径拍板、speed kib 负数、_INFOHASH_RE 尾换行。

## 进度日志

### R0 · 立档 (2026-11-08)

收尾轮立档: 阈值命中 #2(改动 ≥3 源文件, 实为 16 src 文件)与 #3(批A-批L 波次表述); issue 26-11-07-0536 收编 Open→Done(复验/修复后补充/批次映射落 issue 侧); 基线切片 26-11-08-0025 已建; 坑档处置 = venv-trampoline-clone-copy 复发 +1(tools/global-traffic-monitor/.venv pytest.exe trampoline, 同坑扩面到 tools 级 venv); 回写判断 = 主题文档 grep 核查(关键词 defer_receipt/真值落地/TRACKER_LIT_TTL/已亮/check_pending/mask_tracker/alt_up_limit/ChainCache/_pending_full): 矛盾一处已回写 `conventions/attachments/code-style-examples.md`(守阵①~⑤→①~⑦ + tracker 掩码入库单点执行点前移注记), 其余命中为 tasks/baselines/progress 冻结面或与批H 改道后行为一致(web-runtime-details 四档 TTL 描述经批H 修复反而成真); 根 README 零回写(用户可见面/配置面未变)。

- 2026-11-08 00:52 issue 26-11-07-0536(R4 webui-py 25 条)批A-批L 修复收编: issue 置 Done+复验/修复后补充/批次映射落 issue 侧, 认领链双向(kb.ref), 11 件计划外入池, pitfall venv-trampoline-clone-copy 复发+1(tools 级 venv), 基线切片 26-11-08-0025 补 Refs
