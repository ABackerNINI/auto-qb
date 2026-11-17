# 26-11-18-backend-qbmanager-startup-reload-discard — qbmanager 启动序列修复: state 加载挪到 start_all 之前(issue 26-11-17-0214)

**Status:** Done
**Added:** 2026-11-18
**Updated:** 2026-11-18
**Summary:** 修 issue 26-11-17-0214: run() 启动序列 _reload_state/物化/落盘起点整体挪到 start_all 之前(方向 A 拍板), 启动期模块 state 写点不再被整体替换丢弃; 双守阵红绿 + 分面评审两轮零 actionable; 坑档/架构文档/issue 正文三面回写
**Topics:** backend-qbmanager-startup-reload-discard
**Refs:** memory-bank/issues/26-11-17-0214-question-qbmanager-startup-reload-state-discard.html,memory-bank/pitfalls/backend/startup-state-write-reload-discard.md

## 本篇只回答

qbmanager.run() 启动序列为什么必须把 state 加载放在 start_all 之前、这一摆位是怎么修的、守阵怎么钉 —— 认领修复 issue 26-11-17-0214 的完整过程与验收记录。

## 原始请求

1. 用户: 「修复memory-bank/issues/26-11-17-0214-question-qbmanager-startup-reload-state-discard.html」—— 修复内核启动序列通用隐患: start_all 先跑, _reload_state 随后整体替换 ctx.state.data, 模块启动期写点(迁移盖章/对账回写/prune 滚出)被静默丢弃。
2. 用户(AskUserQuestion 拍板): 修复方向选 A「reload 挪前」—— 加载/物化/落盘起点整体挪到 start_all 之前; 显式接管协议(方向 B)不立项。

## 思考过程与决策

- 取证闭环(修前): _reload_state = 磁盘 load() + 两个 bind(bind_field_snapshots / bind_transitional_missing_skips, 绑到构造期已有的 ctx.store), **零连接依赖** —— 「必须在 connect 之后」是历史摆位不是真约束(模块化前的平铺版里加载本就紧贴主循环开跑前; start_all 是后来插到连接之前的, 摆位悄悄变成丢弃窗口)。
- 方案裁决(方向 A 前置置疑排除): 物化接线守阵 test_state_migration_materialize_is_wired_in_run 只钉「物化在加载后」不钉连接顺序, W6 守阵亦然 → 挪位不破守阵; 现存唯一发病点 relocate 已有写穿规避(cd786499), speed_curve/maintenance 的 state 写点都在运行期任务线不在启动期。
- 连带收益(挪位的额外正当性): WebUI 随 start_all 启动, qB 宕机连接重试窗口内经 WebUI 产生的 state 写点今天同样被丢弃 —— 挪前一并消除。
- start_all 失败路径处置: 不回滚物化 —— 迁移/恢复写回幂等(黄金法则 1), 下次启动重放同链; lifecycle_ready 闸门语义不变(失败启动不落空态 state.json)。
- relocate 写穿的处置: 按 issue §06 建议保留为「接管即持久」语义面(非优雅终止时启动期突变丢失窗口压到零, 不依赖周期刷盘), 注释改口去「规避手段」叙事(relocate_mod.py 两处, 行为零变化)。
- 评审轮1 分面②唯一发现(坑档引用坑档名不精确)经 review.check REFUTE(引文跨行机械弃), 底层事实经主会话独立核实为真 → 自发修复引用名; 按修复循环扳机走轮2复评(增量+回退校验)零发现, 出口 = 裁决后零 actionable。

## 实现计划

1. 内核挪位: qbmanager.py run() 内 self._reload_state() + ctx.state.materialize_migration(dry_run) + next_flush_at 起点三行整体移到 self.host.start_all(dry_run) 之前(try 内), 注释写明判据与摆位史; _reload_state docstring 补「调用点必须在 start_all 之前」。
2. 守阵: test_qbmanager_w6.py 新增两条(顺序接线 test_w6_reload_precedes_start_all_wiring + 行为 test_w6_startup_state_write_survives_run), 文件头测试计划清单同步; 回归摆位红验两条全红后恢复修复摆位绿验。
3. 注释改口: relocate_mod.py 接管面写穿两处注释从「规避手段」改口「接管即持久」语义面(代码零变化)。
4. 回写: 新坑档 pitfalls/backend/startup-state-write-reload-discard.md(三必填字段条目 + 新模块接入动作面) + kb.index; 架构文档 main-loop-queue.md 启动序列行更新; issue 翻 Done + 复验/修复后补充节。
5. 收尾: 分面评审(2 派发) → 修复循环 → test.full → 基线切片 → 档案(本件)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 内核启动序列挪位(qbmanager.py) | Done(2026-11-18) |
| 2 | 双守阵红绿双验(test_qbmanager_w6.py) | Done(2026-11-18) |
| 3 | relocate 写穿注释改口(零行为) | Done(2026-11-18) |
| 4 | 坑档/架构/issue 三面回写 + kb.index | Done(2026-11-18) |
| 5 | 分面评审两轮 + test.full + 基线切片 | Done(2026-11-18) |

## 进度日志

### R0 · 立档+实施收尾 (2026-11-18)

- 取证: reload 零连接依赖实证(平铺版摆位史 + StateService.load/bind 实现核对); 守阵前置置疑排除。
- 实施: 步 1-4 落地; 红验(回归摆位两条守阵全红, 行为条失败信息精确复刻 issue 症状「盘面回旧版」)后绿验恢复; 受影响四面定向回归全绿(数字见 kb.baseline)。
- 评审: 分面档 2 派发(正确性 / 安全+测试缺口+文档事实); 轮1 分面①零发现, 分面②唯一发现 REFUTE 后底层事实核实为真、自发修复(坑档引用名), 轮2 复评(增量+回退校验)零发现, 出口零 actionable。
- 坑档首发踩到 pitfalls 条目三必填字段守阵(test_kb_pitfall_entries_have_required_fields): 全量红一处, 按判据(每个 ### 条目块内含 **触发**/**判别**/**处置**)改写为双条目结构后绿 —— 本坑此前未记, 属条目格式约定, 已在写作面遵守。
- 全量测试与基线切片: 全绿(见 kb.baseline 最新切片)。
- 真机自检: 纯桩可验 —— 机制面(reload 整体替换时序 vs 启动期写点落盘)完全确定, 行为守阵桩写点与真实模块启动期写点同位(回归摆位红验已证明桩忠实复刻丢弃机制); reload 零连接依赖已实证, 真机差分需构造特定 prune 滚出场景, 收益低不立项。

- 2026-11-18 07:22 修 issue 26-11-17-0214: run() 启动序列 reload/物化/落盘起点挪到 start_all 之前, 启动期模块 state 写点不再被整体替换丢弃; 双守阵红绿+分面评审两轮零 actionable; 坑档/架构/issue 三面回写, 全绿(见 kb.baseline)
