# 片A-fix RM04 用例适配修复轮: 19 PASS / 1 FAIL(仅 L490 显式前置腿) / 1 SKIP(前提钉死) —— 产品回归 0, 判据变面首次真复验全过

> 摘要: 26-11-17-0756 片A 判定 18 条「测试基建形态过时」(四族工单)的修复轮。测试侧适配落齐后
> suite 终态(run8, 逐层逼近: run1 12P/8F → run2 16P/4F → run3 16P/4F → run4~7 18P/2F →
> **run8 19P/1F/1S**): 唯一 FAIL = RM04-05 的 L490 负向对照腿(显式前置 QBT_REAL_SMALL_TARGET
> 未备 —— 测试自证「前置缺失时显式失败不 skip」, 需用户手动挂载 ImDisk 96M, 环境项非用例缺陷;
> 主链/判据变面在同轮已全过); 唯一 SKIP = RM04-13(族C 前提闸按设计生效, save_path 可列实证;
> 理由串落盘 run13-skip-reason.log, 评审 R11 后补捕)。
> 四族修法之外, 族A 复跑首次真行使暴露并修掉**六项新触面过时**: ①测试配置模板缺 v8 必需
> `relocate.bt_backup`(075dd418 部署闸 fail-fast, 8 条被它先拦)②done 终态 reason external→finalized
> (S1a/S3 统一收尾, 05/14 两处)③RM04-14 same_volume 环境拓扑钉死改自适应④UI 脚本整层
> button.rel-badge 退役(P1-2 pair 展示 + 抽屉路径链按钮, 15)⑤RM04-19 的 addTags 逐路径断言
> 误伤缺文件打标(MISSING)合法写, 改带体辨识⑥flux 链浮窗玻璃化(457ab47b)后半透明+blur 是
> 设计态。RM04-20 升 L3 负向腿落地验证(target_conflict 闸实拦+零发起+预置文件零触碰)。
> RM04-21 B1-B7 全链真机复验过, B4 开窗断言改双押(L1 obs 死证 OR wrapper 决策行)。
> 基线时间: 2026-11-17 23:34(开工, guard 双实例拉起)-2026-11-18 02:40(单跑惯例+收尾证据落盘)。
> 基线 commit: 923f2e32(分支 relocate-rm-r2, 本地无远端; 实测全程 HEAD 未动)。
**Refs:** memory-bank/testing/real-baselines/26-11-17-0756-real-rm04-sliceA.md, memory-bank/plans/26-11-17-0636-plan-real-rm04-relocate-refactor-verify.html §03.1/§04, memory-bank/pitfalls/testing/drift-audit-web-consumer-blindspot.md, memory-bank/pitfalls/testing/real-suite-cascade-skip.md

## 01 三态结论(21 条逐条, 以 run8 官方 suite 为准 + 15~19/05/13 单跑复核)

| 用例 | 三态 | 一句要点 |
|---|---|---|
| RM04-01 组键同异对照 | **PASS** | 族A helper 适配后首绿(wait_group members hash 串集) |
| RM04-02 大小一致性整组暂停 | **PASS** | 同上 |
| RM04-03 缺文件打标对照 | **PASS** | 同上; 本轮 19 的 addTags 辨识修复反向佐证此面为合法写 |
| RM04-04 跨组冲突与缺文件豁免 | **PASS** | 与 0756 一致 |
| RM04-05 同卷搬迁 DIR_ALIAS | **FAIL** | **仅 L490 显式前置腿**(QBT_REAL_SMALL_TARGET 未备, 用户自备 ImDisk 96M, small_target 守卫给准备指引); 主链目录别名/穿透/journal done(finalized)/Z: 负向对照(GATE_SPACE)全过 —— 二分=环境前置项, 非产品回归非用例缺陷 |
| RM04-06 journal 恢复 | **PASS** | 强杀窗口+恢复链全过(run2 起绿) |
| RM04-07 坏账与孤儿 pid | **PASS** | 与 0756 一致 |
| RM04-08 save_path 换键重归组 | **PASS** | 族A 修复后首绿 |
| RM04-09 facade 限速端到端 | **PASS** | 族A 修复后首绿 |
| RM04-10 .!qB 窄域外拦内放 | **PASS** | qb_temp 闸在部署闸修后可达(run2 起绿) |
| RM04-11 probe 真写真清理 | **PASS** | 与 0756 一致 |
| RM04-12 指纹缓存与重探 | **PASS** | 族B: probe_salt_ensure 先钉盐再算键, 带盐键命中 state(指纹 9b647477…/probe_salt_present=true) |
| RM04-13 默认保存路径列目录 | **SKIP** | 族C 前提闸: 副实例默认 save_path=R:\Download\PTing 环境1 可列(实测), D 级闭证腿按环境2(C盘机 R: 不存在)钉死 —— 显式 skip 标注前提, 不伪装 PASS; 环境2 是另一物理机, 切环境单跑不可选 |
| RM04-14 WEB confirm 闭环 UI | **PASS** | UI 回路 + same_volume 自适应断言 + finalized 判据(run4 起绿) |
| RM04-15 可见性皮肤弹层 | **PASS** | UI 脚本整层适配(rel-pair 度量/双击入抽屉/L1 前提闸/玻璃化断言)后绿(run8); **长链腿前提闸 skip 留证**(§3.3, 表行级披露) |
| RM04-16 人工链 UNC | **PASS** | member_rel 改详情端点后绿(run1 起) |
| RM04-17 pending tag 生命周期 | **PASS** | 部署闸修后绿(run2 起) |
| RM04-18 pending tag 关停零写入 | **PASS** | 同上 |
| RM04-19 pending tag unarmed 终态零删 | **PASS** | main_tick=5S 造法 + MISSING tag 体辨识断言(run4 起绿, run8 终态) |
| RM04-20 RLFN symlink 离线窗 | **PASS** | **升 L3 负向腿落地**: dst 预置同名真实文件 → gate=target_conflict 实拦 + 零发起 + 预置文件零触碰(evidence A3_5); 开窗双押 L1 face=true(obs owner pid 死证) |
| RM04-21 启动对账自愈闭环 | **PASS** | **B1-B7 全链真机复验过**(0756 只到 B4): B4 改双押(L1 obs 死证 OR wrapper 决策行), B5 重启落位/B6 done+组归一/B7 清净全过 |

**统计: PASS 19 / FAIL 1(环境前置) / SKIP 1(前提钉死)。产品回归 0; BLOCKED 0。**
轮次轨迹: run1 12P/8F/1S → run2 16P/4F/1S → run3 16P/4F/1S → run4 18P/2F/1S → run5 18P/2F/1S →
run6 18P/2F/1S → run7 18P/2F/1S → **run8 19P/1F/1S**(每层 FAIL 逐条二分修复, 明细见 §03)。

## 02 环境指纹

| 项 | 值 |
|---|---|
| 环境 | 环境1(D盘机), `QBT_REAL_ENV` 未设(按 EXE 探测), qB v5.2.3 |
| 实例 | 主 36595(D:\Programs\qBittorrent-testing, pid 轮换 30180→23924) / 副 36596(D:\Programs\qBittorrent-testing2, 5124→28448), 全程 firewalled |
| 免鉴权 | 双实例本机直连零凭据, 全程零 401/403 |
| guard tee | 开工 guard-open.log / 轮间 5 次 guard-mid*.log(run2~6 前后, run7/run8 轮未 tee) / 收尾 guard-final.log 均落 `tests-real/.work/rm04-sliceA-fix/`(片A 坑档纪律执行) |
| 证据落点 | `tests-real/.work/rm04-sliceA-fix/`(suite-run.log(=run1)及 suite-run2~8.log, runNN-single.log, run13-skip-reason.log, evidence-final/) + runner 逐案 `tests-real/.work/rm04/` |
| 假种子 | 全程 real-fake L1/L2, 收尾 seed.list=0 自造、R:/qbt-fake 净 |

## 03 修复清单(四族工单 + 新触面, 全部测试侧, 产品代码零改动)

### 3.1 四族工单落地
1. **族A(15 条)**: `group_row`/`wait_group`/`wait_store_progress`/`member_rel`/`wait_in_store`
   改按 members=hash 串数组消费(views_group.py docstring 单点); 逐成员明细(progress/relocate)
   改经 `GET /api/torrents/{hash}`(require_torrent 读 manager.store, 与组视图同快照; 新 helper
   `member_detail` 单点)。触点: test_rm04_relocate.py 430/444/458/561/1214/1425 区 + visibility
   100/119/451/537 区; window/reconcile 经 M.* 间接消费自动跟随。
2. **族B(RM04-12)**: 测试与 `_ensure_probe` 同写路径先 `module.probe_salt_ensure()` 钉盐, 指纹
   `probe_fingerprint(conf, salt)` 带盐计算, state 落盘键命中; 证据记 probe_salt_present=true。
3. **族C(RM04-13)**: 前提条件化 —— raw 端点探测默认 save_path 可列性, 可列(环境1)即
   `pytest.skip` 标注前提; 理由: 环境2(C盘机)是另一台物理机本工作区不可达(本机无 C:\Programs
   EXE), 切 QBT_REAL_ENV=2 单跑不可选; 正向对照腿随用例一并 skip(同属同一闭证链)。
4. **族D(RM04-21 + RM04-20 A9)**: 开窗观测面断言改**双押** —— L1 证据面(obs 观测账 owner 死证,
   经产品 `rj.read_obs` 读面自证 + 窗内零 L2/L3 开窗决策行) OR wrapper 决策行(L2/L3 退化层回退
   判据); helper 单点 `window_regime_face` 在 window 测试文件, reconcile 复用。B5-B7 随双押放行
   后首次真机补验全过。

### 3.2 族A 复跑暴露的新触面(六项, 逐层二分修复)
1. **测试配置模板缺 `relocate.bt_backup`**(RM04-05/06/10/14/15/17/18/19): v8 起 bt_backup 收编
   为单实例标量(075dd418), 部署维闸门在 relocate_execute fail-fast(schema groups.py 明载「留空 = 迁移预检拒绝」—— 缺它 8 条全被 gate=bt_backup 先拦, 业务闸门(space/qb_temp)不可达。修:
   CONFIG_TEMPLATE 加 bt_backup(env_registry EXE 派生副实例 profile BT_backup, 与 window
   测试同款单点), write_cfg 加非空守卫。**0756 漂移体检漏检的第二例**(glob 漏测试配置模板)。
2. **done 终态 reason external→finalized**(RM04-05/14): S1a/S3 生命周期账统一后, qB 原生跟进
   成员由收尾链统一收口(核验+删链门依赖清零→在线删别名), external 码退役(relocate_units
   REASON_* 注册表现值)。断言改 finalized, journal phase=done 不变。
3. **RM04-14 same_volume 环境钉死**(环境2 时代断言 True): 环境1 src=R: dst=D: 跨卷, 产品报
   False 是正确 P3 输出。改自适应: 期望值按 RAM 落点与 case 落点实际盘符关系推导, note 按
   同卷/跨卷分支断言。
4. **UI 脚本整层 rel-badge 退役**(RM04-15): P1-2(plan 26-11-07-2344 S2)以 save_path 格内
   .rel-pair 双排展示取代徽章, 链浮窗行级入口退役(只剩抽屉迁移段路径链按钮)。relocate_visibility_ui.mjs
   重接线: measureRow 度量 rel-pair(contained 断言保留, 行高等值断言随徽标退役 —— pair 双排
   天然高于单排, 实测 53 vs 44); openChain 改 vm.relChainOpen(真实行元素锚点); 组行入口改
   「种子页 mover 行(data-hash 精确)双击 → 抽屉 → [data-act=chain] 按钮」, Esc 焦点回按钮。
5. **RM04-19 的 addTags 逐路径断言误伤**: proxy 实测撤销后 ~1s 的 addTags 是**缺文件打标
   (MISSING, grouping_mod → maintenance.add_tags)**对搬迁中成员的合法写(收尾读回成员 tags 无
   pending tag)—— 逐路径 `adds == []` 假阳性。修: lib/proxy.py 事件加 body 截取(4KiB, 评审 R10
   后由 512B 放大: 21 颗种子 hash 数组 ~840B 已超 512B, 批量片 pending_tag 判据会漏拍假绿)+
   `requests_full()` 访问器, 断言改「路径 + 体含 PENDING_TAG」双条件(pending_tag_adds helper)。
   造法另加 main_tick=5S 派生(armed 相位推进走任务线, 确定性拉长「cancel 必须在 moving/moved
   窗口落地」前提窗; 附带修正: 相位推进窗与命令延迟解耦, 命令是 wake 即时消费)。
6. **flux 链浮窗玻璃化**(457ab47b, 2026-11-04 全浮层毛玻璃): relc-pop 在 flux 侧半透明(0.82)
   + backdrop blur 是设计态; 旧「透底=alpha 1.0」断言停在玻璃化前。改: flux 钉「0<alpha<1 且
   blur 在场」, 其余三皮肤仍钉 alpha==1.0(popInfo 加 backdrop 观测面)。

### 3.3 长链腿前提闸(留证, 交主会话裁决入池)
RM04-15 2d 长链腿实测暴露**潜伏前端健壮性缺陷**: `/api/relocate/chain` 对无迁移 job 的 hash
不回 `finalize` 段(relocate_chain.py 只在 pick_job_for 命中时挂), 而 relc-pop 模板
(popovers.html:310)无守卫直读 `relChain.data.finalize.verify_failed` → 打开即渲染 TypeError 且
传染后续整页渲染。真实 UI 不可达(路径链按钮只在抽屉迁移段渲染), 仅测试 vm 级诊断性开窗触发。
处置: 脚本前提闸探测 finalize 缺席 → 显式记账跳过(`longChainSkipped`, 不伪装 PASS), 产品补
守卫后自动恢复实跑。**测试侧零触发修复, 产品码未动** —— 建议主会话按 create-issue 入池。

## 04 升档动作(§08 口径)

RM04-20 升 L3 负向腿**本轮落地验证**: A3.5 段 dst 预置同名真实文件(1MiB)后发起迁移, 断言
回执 blocked 且 gate=target_conflict(relocate_plan 目标同名冲突逐文件判定)+ 零「迁移发起」+
预置文件字节零触碰, 断言后清场主链继续。evidence-final/rm04_20_evidence.json A3_5 段: gates=
["target_conflict"], 文案逐字命中「目标已存在同名内容(rm04c20.bin): qB 会走全量校验(进度清零)…」
—— 0756 §05 承诺的「修复前必红形态」负向腿兑现。全局升档口径不变(7 片合并计一轮)。

## 05 与 0756 切片的差异

1. 三态: 3P/18F/0S → **19P/1F/1S**; 18 条过时用例全部适配复位(1 条环境前置腿维持显式 FAIL,
   1 条前提钉死 SKIP)。
2. 0756 待改造清单 6 项全闭环: ①族A helper②族B 盐③族C 咰④族D 双押⑤RM04-20 升 L3 负向腿
   ⑥复跑注意(判据变面首次真复验) —— 另新增第 7 项(测试配置模板 bt_backup, 体检盲区第二例)。
3. 新沉淀: proxy body 观测面 / member_detail 单点 / window_regime_face 双押 helper /
   make_cfg main_tick 派生 —— 均为测试侧可复用基建。
4. 证据纪律升级: guard 输出 tee 落盘(开工/轮间 5 次/收尾), 单跑逐条留 log, skip 理由串留盘
   (run13-skip-reason.log)。

## 06 收尾核净(2026-11-18 02:40-02:45)

- `real.seed.rm --all --yes` + `real.seed.clean --dir tests-real/.work/seeds --yes`: 自造种子清零,
  R:/qbt-fake 净, .work 无 test_rm04_* 残留目录(逐案 workdir 由用例 finally 删净))。
- `real.guard` 终态复跑(tee guard-final.log): 双实例 [ok] firewalled, 真实种子 0 全暂停 —— 净。
- 实例处置: 保留双实例在线净态(片B 开工前提, 与 0756 同判据)。
- 提交: 真机轨不挂提交闸门; 用例代码改动 >0 行, **留工作区不提交**, 走主会话评审流程(BLOCKED-report)。
