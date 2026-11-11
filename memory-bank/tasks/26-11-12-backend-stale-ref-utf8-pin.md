# 26-11-12-backend-stale-ref-utf8-pin — 退役指路残留清零+src/文本子进程UTF-8钉死+qB5.x注释口径

**Status:** Done
**Added:** 2026-11-12
**Updated:** 2026-11-12
**Summary:** 退役目录指路残留 7 处全仓清零 + src/ 文本子进程 UTF-8 钉死 5 处(守卫扫描面纳入 src/) + qB 5.x 存储类型注释口径两处对齐; 两批入库 771f262d/807ad38d, 零行为代码改动
**Topics:** backend-stale-ref-utf8-pin

**Refs:** memory-bank/issues/26-11-07-1216-bug-port-kill-subprocess-encoding.html, memory-bank/pitfalls/ops/console-encoding.md, memory-bank/pitfalls/docs/drift.md, memory-bank/active-context/26-11-12-0127-stale-ref-utf8-pin.md, memory-bank/testing/baselines/26-11-12-0135-stale-ref-utf8-pin.md

## 本篇只回答

三个同批修掉的问题各自是什么、修到哪、为什么这样修: ①退役目录(memory-bank/config-reference/, 2026-11-08 退役)的活性指路残留有哪些、清零后统一改指什么权威; ②src/ 侧文本子进程 UTF-8 未钉死的有几处、守卫扫描面怎么补; ③qB 5.x 存储类型注释口径怎么对齐(为何零行为改动)。

## 原始请求

另一会话报告的 3 问题(用户会话 6 轮指令, 命中立档阈值 #2: 指令≥5 轮 + 改动≥3 源文件):

1. 退役目录指路残留清零: config-reference/(2026-11-08 退役)活性引用共 7 处修净 —— scripts/update_config_key_surface.py docstring+print 2 处、docs/configuration.md 2 处、docs/hr-online-verify-docs.md 1 处、webui static state.js/config_editor_curve.js 注释 2 处; 统一改指现行权威 src/auto_qb/config/schema/ + validate_config 与键面快照 tests/fixtures/config_key_surface.txt(再生入口 commands run test.keys-update); 两处 webui 注释继任单点不适用(工具控制面键不在 auto-qb 键面内), 删死链保留事实。
2. src/ 文本子进程 UTF-8 钉死 5 处(issue 26-11-07-1216 同病、守阵盲区): port_owner.py:108、traffic_source/agent.py _run_foreground、recycle_daemon.py tasklist/ps 两处、守卫扩面实扫出 checking.py:263 第 5 处; 口径 = encoding="utf-8", errors="replace"(守卫单点), 行为面核查全部无回退(判定只用 rc 或匹配目标恒 ASCII)。
3. qB 5.x 存储类型注释口径: bt_backup_probe.py 与 relocate_plan.py 两处注释补写 qB 5.x 线值字符串枚举(实测 5.2.3 = "Legacy"), 零代码行为改动。

用户拍板扩面 3 项: docs/ 引用一并修、守卫纳入 src/、relocate_plan 同源漂移并入。

## 思考过程与决策

- **指路权威取向**: 退役目录的继任权威是「现行事实源」而非「某个新文档」—— schema/ + validate_config(校验单点)与键面快照 tests/fixtures/config_key_surface.txt(再生入口 test.keys-update); webui 两处注释原本描述工具控制面键, 该键不在 auto-qb 键面内, 继任单点不适用, 处置=删死链保留事实, 不硬造新指路。
- **守阵扩面取向**: 1216 修复批把守卫扫描面扩到 tests/+scripts/ 时按「这次在哪发现」取面, src/ 成盲区; 本批改为按「文本子进程可能在哪些目录」取面, 纳入 src/ 后实扫当场抓出单点检索漏掉的第 5 处(checking.py:263)—— 印证静态守卫扩面本身有产出。
- **钉码口径**: 与守卫单点一致的字面量 encoding="utf-8", errors="replace", 写法照抄 recycle_daemon.py netstat/powershell 合规先例; 行为面逐点核查 5 处判定路径(只用 rc / 匹配目标恒 ASCII), 确认无回退才动手。
- **注释口径**: qB 5.x 线值为字符串枚举(实测 5.2.3 = "Legacy"), 容错分支 _LEGACY_TOKENS/_SQLITE_TOKENS + str().strip().lower() 归一路径早已覆盖 ⇒ 只修注释, 两处注释互认对齐 is_legacy_resume_storage。
- **分批**: 批1(指路残留+注释口径, 7 文件 32 行)与批2(src/ 钉码+守卫扩面, 5 文件 26 行)各自 ship.gate 预跑+分面/全能评审+review.check; 接缝终审零发现; 批2 评审检出 1 minor(守卫断言文案史实口径)当场修, 轮 2 复评零 actionable。

## 实现计划

1. 全量定位: git grep 退役路径(含无连字符变体)按类判读, 冻结件不改 → 批1 修净 7 处。
2. src/ 扫描: 守卫 AST 对账扩面纳入 src/ → 先扩面跑红, 逐处钉码 → 批2。
3. 两处 qB 5.x 注释口径对齐(随批1)。
4. 每批收尾: 分面评审 → review.check → 接缝终审。
5. 收尾 DoD: 切片/立档/坑档复发闭环/事实回写核对/基线切片/真机判定/kb.check。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 退役指路残留 7 处清零+改指现行权威(批1, 771f262d) | Done(2026-11-12) |
| 2 | qB 5.x 存储类型注释两处口径对齐(批1 同件) | Done(2026-11-12) |
| 3 | src/ 文本子进程 5 处钉死+守卫扫描面纳入 src/(批2, 807ad38d) | Done(2026-11-12) |
| 4 | 分批评审+接缝终审(批2 轮1 minor 修, 轮2 零 actionable) | Done(2026-11-12) |
| 5 | 收尾 DoD(切片/立档/坑档复发x2/回写核对/基线/真机判定) | Done(2026-11-12) |

## 进度日志

### R0 · 立档 (2026-11-12)

- 修复 3 问题 + 用户拍板扩面 3 项, 分两批入库: 771f262d(批1, 7 文件 32 行)/807ad38d(批2, 5 文件 26 行)。
- 坑档复发闭环 x2: ops/console-encoding.md 复发 +1(守阵扩面按「在哪发现」取面致 src/ 盲区, 5 处漏钉)、docs/drift.md 复发 +1(目录级退役清理验收漏脚本 docstring/print 文案与 webui 注释, 7 处残留; 再评估结论: 退役名册仍缺, 暂以流程约束兜, 第 3 次复发再立名册)。
- 事实回写核对: 常青主题文档与根 README 无把 keys.md 当现役单点的表述(pitfalls/ops/agent-write-guard-secret-false-positive.md 的命中为历史影响面记述, 不改) ⇒ 无需回写。
- test.full 全绿(见 kb.baseline); 真机判定: 不落入 —— 本任务主体是注释/文案/编码参数钉死+守卫扩面, 零行为代码改动, 纯桩可验(5 处钉码无行为语义变化, 判定路径只用 rc 或恒 ASCII 目标, 单测已覆盖), 见 testing/real-machine.md §00/§06 两类准入均不满足。
