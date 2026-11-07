# 26-11-07-test-legacy-review4-scripts-fix — 存量评审 R4 scripts 主题修复批: 24 条 17 文件五批委派实施

**Status:** Done
**Added:** 2026-11-07
**Updated:** 2026-11-07
**Summary:** issue 26-11-07-0536(R4 存量评审 scripts 主题, 24 条 = major 1/minor 23, 17 文件)修复批: 用户指定委派制, 5 修复批(sim组A/B、守卫组、工具组、taskkill组)串行子代理实施 + 主会话本地 commit; 只读评审 blocker 0, 3 minor+1 nit 全修; 补针对性单测 19 例(红验 7 处实测); 末次全量回归全绿(见 kb.baseline); issue 收编 Open→Done; 提交区间 ddf6acca..c9e13890。
**Topics:** test-legacy-review4-scripts-fix
**Refs:** memory-bank/issues/26-11-07-0536-bug-legacy-review4-scripts.html, memory-bank/pitfalls/testing/inproc-server-conn-abort.md, memory-bank/pitfalls/ops/console-encoding.md

## 本篇只回答

issue 26-11-07-0536 的 24 条怎么组织修复、验证与收编 —— 分批与委派模型、4 项拍板与 2 处改道、影响面与验证口径在本篇; 逐条明细表在 issue 侧, 本档案不复述。

## 原始请求

1. 处置 issue 26-11-07-0536(R4 存量评审 scripts 主题, 24 条 = major 1 / minor 23, 涉 17 文件); 用户指定**委派制**: 5 个修复批(同文件按主题聚合: sim组A / sim组B / 守卫组 / 工具组 / taskkill组)串行子代理实施, 每批主会话本地 commit。
2. 执行期拍板(4 项): taskkill 红线走 AGENTS.md 豁免落档(不换通道); qb_capture --dry 提前判定真零请求; 补针对性单测; 验证 = 定向 + 末次全量回归。
3. 收口: 只读评审处置后 issue 收编 Open→Done, 合流本地 develop(rebase 保线性)。

## 思考过程与决策

- **委派模型(用户拍板)**: 5 批串行子代理实施、每批独立 commit —— 批次边界可回溯; major #1 最先(sim组A: sim_qb_server 缺 import sys)。
- **拍板①(#10/#8 改道)**: taskkill 红线不走"换通道", 走 **AGENTS.md 红线条目写明豁免**(用户拍板 2026-11-07): `scripts/port_kill.py`(杀前核验 + --yes 门)与 `scripts/hr_fetch_experiment.py` 两处**脚本内**定点杀为唯一许可面, AI 代理 shell 直接执行 taskkill 仍一律禁止; 落档时 doc.caps 6915/8000 PASS。
- **拍板②(#11 改道)**: qb_capture --dry 判定从 run_capture 里提前到 **main() 在 Capture 构造之前分流**(_dry_plan) —— 实测旧路径发 9 个真实请求(4 login + 4 handshake + 1 计数, 多于原 claim 的 4 个); 修后真零请求, _count_torrents 失去调用方一并删除。
- **拍板③**: 补针对性单测 19 例(test_legacy_review4_scripts 15 + test_sim_corpus 4), 红验 7 处逐字重放实测必红(UNC 旧序 / corpus 裸阈值 / porcelain 整串 / e2e IndexError / 守卫 IndexError / kill 旧循环 / capture 旧顺序); 既有用例 0 改写。
- **拍板④**: 验证 = 每批定向 + 末次全量回归; 全绿数字单点见 kb.baseline 最新切片。

## 实现计划

无独立计划 HTML(用户指令直行)。链路: P1-P5 修复批(串行子代理 + 每批 commit)→ P6 只读评审(接缝终审)→ P7 全量回归修复 → P8 issue 收编 + 合流本地 develop(rebase 保线性; `_index` 生成物撞车按兜底口径重跑生成器自证)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| P1 | sim组A: sim_qb_server 补 import sys(major #1)+UNC 死代码重排+corpus 阈值路由+非ASCII 清理 | Done(2026-11-07, ddf6acca) |
| P2 | sim组B: WEB delete declared 按 len(paths) 核账(#19)+4 文件非ASCII | Done(2026-11-07, 4761d5ce) |
| P3 | 守卫组: check_context_caps porcelain rename 行两侧路径入改动集+3 文件非ASCII | Done(2026-11-07, 592e8ef9) |
| P4 | 工具组: qb_capture --dry 真零请求(#11)+e2e_selfcheck 缺值守卫+ui_harness 守卫<4+非ASCII | Done(2026-11-07, 62594a90) |
| P5 | taskkill组: port_kill 杀前进程核验 kill_decision+--yes 门(#9)+AGENTS.md 红线豁免落档(#10) | Done(2026-11-07, c73bad87) |
| P6 | 只读评审: blocker 0, 3 minor+1 nit 全修 | Done(2026-11-07, b5439a4e) |
| P7 | 全量回归修复: 平台守卫抓新测试 text=True 缺 encoding + process_info 子进程补钉 | Done(2026-11-07, ecede34a) |
| P8 | issue 收编 Open→Done(复验/修复后补充落档)+合流本地 develop | Done(2026-11-07, c9e13890) |

## 影响面与验证

- 代码: scripts/ 17 个工具 + tests/ 新增 2 文件(671 行) + `.commands/dev/config.toml`(dev.port-kill note) + AGENTS.md(红线条目新增 taskkill 豁免 2 行); 8 提交(ddf6acca..c9e13890)净 1067 插入 / 188 删除。
- 非 ASCII: 修复批将 scripts/ 目录图形符号清零(含扫描追加同类 ⊕/·/…/① 等)。
- 验证: 红验 7 处实测; 末次 test.full 与 test.pkg 全绿(数字见 kb.baseline 最新切片)。P7 首跑红一笔: 平台守卫抓到新测试 text=True 缺 encoding —— [console-encoding.md](../pitfalls/ops/console-encoding.md) 复发 +1(为什么没命中录在那条); 守阵不扫 scripts/ 的存量同病(port_kill 两处)入池 26-11-07-1216 bug-port-kill-subprocess-encoding 另裁。收尾复跑 test.full 首跑遇一次并行负载 flake(对照组 10053, 主断言已过)—— 已立坑档 [inproc-server-conn-abort.md](../pitfalls/testing/inproc-server-conn-abort.md), 复跑全绿。

## 进度日志

### R0 · 立档 (2026-11-07)

修复批八提交(ddf6acca..c9e13890)后收尾轮立档: 阈值命中 #2(改动 ≥3 源文件, 实为 17 文件)与 #3(P1-P8 批次表述); 基线切片与坑档处置(复发 +1 / 新坑)同轮完成; 根 README 与 conventions 回写判断 = 零回写(对本批工具行为无既有陈述, AGENTS.md 豁免批内已落档)。

- 2026-11-07 12:46 R4 scripts 修复批收尾: test.full/test.pkg 全绿入基线切片(见 kb.baseline), 立档 tasks/26-11-07-test-legacy-review4-scripts-fix.md, 坑档双向处置(console-encoding 复发+1 / 新立 inproc-server-conn-abort), 回写判断=零回写; 待办: issues/_index 超预算待清理 + 4 件 26-11-07-1216 issue 待认领
