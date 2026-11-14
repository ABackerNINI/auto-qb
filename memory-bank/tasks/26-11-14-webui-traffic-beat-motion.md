# 26-11-14-webui-traffic-beat-motion — WEBUI 流量图节拍动效与数值面板(S0-S4 八批+S5 收口)

**Status:** Done
**Added:** 2026-11-14
**Updated:** 2026-11-14
**Summary:** 流量图节拍动效全专题完结: S0 面板/持久化 + S1 节拍内核/L0/L1 + S2 视觉引擎/T6 + S3 接线/预览 + S4 电池/e2e 八批入库(3 blocker / 55 发现全修(56 送检) / 22 评审轮), S5 收口回写 webui 附件与计划 Done; 领域口径单点在 conventions/attachments/webui-traffic-beat.md
**Topics:** webui-traffic-beat-motion
**Refs:** memory-bank/testing/baselines/26-11-14-0949-webui-traffic-beat-s5.md, memory-bank/plans/26-11-12-1139-plan-webui-traffic-beat-motion.html, memory-bank/pitfalls/testing/static-guard-mutation.md, memory-bank/conventions/attachments/webui-traffic-beat.md

## 本篇只回答

流量图节拍动效(S0-S4 八批实施)与 S5 收口的实施档案: 各批范围与提交、评审统计、实施期拍板偏差、留痕项与回写去向。领域口径单点在 `conventions/attachments/webui-traffic-beat.md`(以已提交实现为准), 方案与逐轮拍板全档在计划 26-11-12-1139(D1-D28), 本档均不复述。

## 原始请求

1. 按计划 26-11-12-1139 实施(R8 用户拍板定形态): 「将数值调整设计为一个单独的页面挂在右键菜单上, 只做 T6, 其余模板当参考但不实现」「采样周期涉及后端与数据文件, 在此处不可编辑」。
2. 分批评审(code-review skill, 每批可评提交必评)修完 blocker 后逐批入库; 分支 `feat/traffic-beat-motion`(本地, 无远端)。
3. S5 收口: 知识库回写(conventions/webui.md)、计划收口(Done)、基线切片、任务立档、pitfalls 处置、根 README 评估。

## 思考过程与决策

方案取舍与 D 编号拍板单点在计划 §07/§08; 本档只记**实施期新增**的决策:

- **P18 照表 15 项交付**: 字段名与默认值逐字落 `QB_FX_DEFAULTS`(S0-a), 用户拍板照表。
- **P9 偏差拍板**: 计划原型 `leadLevel() <= 1 → 0`(Lv.1 不发粒子); 生产 `_qbFxPartCap` 给 Lv.1 基数 16×密度 —— **Lv.1 发粒子维持现状**, 用户拍板保留(计划 §07 行注已标)。
- **D24 终态**: 图区右键监听只 `openFxPanel` 零开关语义(计划早期「图区右键勾选项」方案废弃), 总开关唯一入口在面板; `menu.js` 早退判据一行未动。
- **full 降格 auto**: 整幅扫掠(D19)不交付 —— `echoSpan:"full"` 存储白名单放行、观感降格 auto(`_qbFxEchoSpan`), 对照臂语义保留在枚举层; 计划 §10 扫描束探针第 8 点已补口径。
- **calm 零粒子门**: S4-a 评审定 eff 门唯一闸(palette=calm 时密度强制 0)。
- **坑档路由决定**: 守阵捕聚合原文含注释两次踩坑（均在 S0-b，其一为 Esc 修复轮的 fx-panel 头注）, grep 查重命中 `pitfalls/testing/static-guard-mutation.md`(处置⑤已及该方向) —— 走**复发 +1**而非新建 web-ui 档(同族不拆档; 处置升⑥「守阵覆盖面内的注释不得复现锚串原文」)。
- **tests:4312 注释失实修正**: S4-b 留痕原记「installRuntimeErrorGuard 全仓无定义」不准确 —— 实为 `e2e/lib/errors.mjs` 有定义(只收 console.error/pageerror); 失实根因 = **Vue 生产构建(vue.global.prod.js 3.5.13)对模板缺失处理器完全静默**(警告仅 dev 构建)。注释改如实表述, 「模板绑定静态钉是唯一闸」结论不变且更强。

## 实现计划

单点 = 计划 26-11-12-1139 §06 波次表(S0-S5)与 §10 回写清单; 本档不复述。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| S0-a | 右键浮层骨架 + autoqb.ui.qbFx 持久化三件套 + 四皮肤登记(d413387c) | Done(11-13) |
| S0-b | 七处收层/Esc 登记 + IO 宿主兜底 + reduced-motion 红线(e44e1138) | Done(11-13) |
| S1 | 节拍内核(公式单点+每拍 rAF 调度器)+L0 视口偏置+L1 双轨状态机+y 定档/ticks 冻结(79b4e3c3) | Done(11-13) |
| S2-a | V1 分级色相+V2 形状+V3 三阶段粒子+N 白名单层+D3 双轨仲裁(9f6b2c16) | Done(11-14) |
| S2-b | T6 综合表现层: T2 光带+T4 双相位六层扫描束+R6 横向线条+T5 分级收口(97499818) | Done(11-14) |
| S3 | 面板接线: ease/shift 消费端+预览一拍六条语义+状态行真值回填(61411817) | Done(11-14) |
| S4-a | 探针盘点覆盖矩阵+六处电池补缺+calm 零粒子门(df26195e) | Done(11-14) |
| S4-b | 面板冒烟链+帧级采样探针 e2e(@fast)+折叠/预览/reduce 实高变化补重钳位(0ba4df8f) | Done(11-14) |
| S5 | 收口: webui 回写/计划 Done/基线切片/立档/坑档/README 评估(本批) | Done(11-14) |

## 进度日志

### R0 · 立档 (2026-11-14)

S5 收口轮立档(跨八批提交, 远超立档阈值)。八批评审统计(trailer 口径 B=blocker / F=发现全修 / R=轮): S0-a 1B/8F/3 · S0-b 0B/3F/3 · S1 0B/8F/3 · S2-a 1B/9F/3 · S2-b 1B/8F/3 · S3 0B/4F/2 · S4-a 0B/7F/2 · S4-b 0B/9F/3 —— **合计 3 blocker / 55 发现全修(56 送检) / 0 入池 / 22 轮**(F 列=各批 trailer「检 T」口径: 8+3+8+9+8+4+7+9=56 送检; 修 55, 其中 S0-a 8 检 7 修, 1 条留痕裁决弃不计修（=留痕⑦同源）)。测试面: S4-b 与 S5 终树两轮全量均全绿(数字权威见 kb.baseline 最新切片); e2e 面板冒烟链与帧级采样两 spec 进 @fast 子集, 容器跑绿。留痕七项(只入本档不入池, 入池需用户显式授权): ① 流量图轮询首轮周期恒 fallback 30s(`_qbLoad` 异步后立刻起轮询, 仅影响首拍延迟, 建议单独立项); ② tests/test_webui_static_dom_panel_traffic.py:4312 注释引证失实已修正(见上方决策); ③ `test.linux-e2e` 的 `--` 透传被引擎层吞(引擎面缺口, 未动); ④ 相位 A「首帧即墨」待计划侧拍板(出处 S2-b 97499818/S4-a df26195e 提交留痕; 张力=计划 §04 原型「t=0 首帧即可见」vs 实现粗粒度窗起步帧束体画布外零墨、scan_band 电池已显式钉零墨 —— 待拍板语义张力); ⑤ S3 两 nit(61411817 评审, nit 只留痕不修): fxPreviewing 注释枚举漏令牌(state.js 写入点实为 4 处, `_qbBeatFrame` 翻沿未列)、`!n` 早退防御分支无行为断言(生产不可达+还原幂等); ⑥ S0-b 计划外留痕(e44e1138 提交留痕): lifecycle.js:103 等多处注释写 `dialogs.js::escBusy` 实为 dialogs_meta.js(域聚合名拆分遗留, 未修); ⑦ 图宿主 contextmenu stopPropagation 使 lifecycle.js:448(注释, d413387c 时 :442)/监听面 :243-252 的 ensureWebFlags 右键惰性补拉对图宿主面失效(boot 三层韧性第三层在图宿主面收窄; S0-a 评审留痕「收口档案统一处置」的兑现落点=本批 qb_traffic_chart.js 宿主 contextmenu 注释补记)(d413387c)。坑档: `static-guard-mutation.md` 复发 2→3 并升处置⑥, `kb.index` 已重建。回写: `conventions/webui.md` 主题地图加行 + 新附件 `attachments/webui-traffic-beat.md`(领域口径单点); 计划 26-11-12-1139 收口 Done(meta/§07 P18 与 P9 行注/§10 守阵行号 :426→:486 现值 + 探针第 8 点补口径/§11 R10); 根 README「Web UI」节补「流量图节拍动效」条(先例成立, 最小条目)。闪烁族未复发(`drawer-switch-flicker` 未动)。

- 2026-11-14 09:51 S5 收口: conventions/webui.md 回写(附件 webui-traffic-beat.md)+计划 26-11-12-1139 转 Done(§07 P18/P9 行注+§10 两处修正+R10)+终树全量基线切片+任务立档 Done+static-guard-mutation 复发+1+根 README Web UI 节补条
