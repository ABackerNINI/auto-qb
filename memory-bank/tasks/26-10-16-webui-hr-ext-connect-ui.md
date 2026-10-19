# 26-10-16-webui-hr-ext-connect-ui — HR 扩展「连接后端」区重排 + 实例状态入表(计划立档)

**Status:** Done(S1–S6 全部实施完成; 真机验收 V1/V2/V7 待用户, 桩服务已备)
**Added:** 2026-10-16
**Updated:** 2026-10-16
**Summary:** 用户实报 HR 扩展「1 连接后端」区排版糟糕(大段文字/表格不清晰), 追问「工具栏图标徽标」指什么(答: 浏览器工具栏扩展图标, 图例措辞歧义), 并指出「自测端点连通」与计划不符 —— 状态应直接表现在实例表里(instanceHealth 台账已落盘但 UI 只用了「疑似失效」一角)。经 grilling 两轮(首轮选择卡故障改纯文字重问; 用户拍板「按推荐」+ 模板评审二轮 R1–R3 + 排序补记)立计划 `plans/26-10-16-0214-plan-hr-ext-connect-ui.html` 并落三份可交互候选模板(A 纵向流 / B 双栏台账 / C 常驻顶部状态条), 逐波实施。S1–S3(04:00): options.html ①区重排 / background.js 台账 state + probe-all / options.js 表格化。S4–S6(04:20): README 口径 / 守阵七项(6 新用例 + 接线清单更新 + badge 用例随 R4 翻转) / 图标状态色外框(R4: gen_ext_icons.py 8 PNG + manifest default_icon + refreshBadge setIcon)。test.full 全绿(基线 26-10-16-0420)。仅动扩展侧 + 守阵 + dev 工具。
**Topics:** hr-ext-connect-ui
**Refs:** memory-bank/plans/26-10-16-0214-plan-hr-ext-connect-ui.html
## 原始请求

用户指令(2026-10-16 01:56): 「HR扩展的"1 连接后端"目前排版很糟糕, 大段文字, 表格不清晰, 需要重新设计; 另外描述"工具栏图标徽标四态…"里的工具栏指的是实例表吗? 没有图标; 自测端点连通也与计划不符, 状态应该直接表现在表格里, 之前的计划实施似乎不完整; 使用设计相关技能以及grilling, 写一个修改计划, 附带3个简单的可交互模板」。

模板评审(02:30): token 列截断太短(拍板前 32 位指纹+悬停全值); 来源徽标「优先」本来就是错的, 改「手动」; 「(免抄)」改「-」; 「载入」「行内测」删除(改 token=删除重加, 探测=重测全部统一承载); 「删」仅手动条目, 自动条目操作列留空。排序补记(02:46): 手动组在前、自动组在后(上游 Q9 既有语义)。

## 思考过程与决策

- **grilling 收敛(Q1–Q6 + R1–R3 + 排序)**: 决策权威 = 计划 §01 两轮拍板表。范围=①区重排 + ③④表样式微调(不加功能); 状态列=四态色点+短语+悬停详情; 自测按钮=重测全部(行内测在二轮取消); 文字=状态卡+行内短句+折叠说明区; 模板=两布局+一激进; 落盘=3 独立文件+计划引用。
- **数据流关键决策**: 选项页不直写 `instanceHealth`(单一写入口), 探测经后台消息 `probe-all`(probe-one 随 R3 取消); 台账条目补结构化 `state` 字段支撑红/橙分色, 旧条目无该键按 C2 降级显示, 无迁移脚本。
- **事实澄清**: 「工具栏」= 浏览器工具栏扩展图标(`chrome.action` 徽标, background.js 已实现), 非实例表; `options.html:135` 图例措辞歧义随 S1 修。

## 实现计划

按计划 §04 分波推进(待用户选型模板 A/B/C 后发「实施计划S1-2」式指令): S1 options.html 重构 → S2 background.js(probe 消息 + state 字段) → S3 options.js(表格化 + 重测全部) → S4 README → S5 守阵(含「优先/载入」不得回潮的反向断言)。

## 子任务状态表

| # | 任务 | 状态 |
|---|---|---|
| S0 | grilling 收敛 + 计划落盘 + 三模板落盘 + 认领链 + 收尾回写 | Done |
| S1 | options.html ①区重构(纵向流基准 = §03.1 规格, 模板 A 形态) | Done |
| S2 | background.js 台账 state + probeInstance/probeAll + probe-all 消息 | Done |
| S3 | options.js 实例表表格化(rowHealthOf/重测全部/状态卡) | Done |
| S4 | README §2 与徽标口径同步 | Done |
| S5 | 守阵七项(含「优先/载入/自测端点连通」反向断言、`[优先]` 期望随 R2 翻转) | Done |
| S6 | 工具栏图标状态色外框(R4: gen_ext_icons.py + setIcon) | Done |

## 进度日志

- 2026-10-16 02:14 — S0 完成: 开工同步 `9dca92a6`; grilling 两轮收敛(Q1–Q6, 首轮选择卡故障改纯文字重问); 计划 `plans/26-10-16-0214-plan-hr-ext-connect-ui.html`(Open, 11 节)与三份候选模板(`plans/26-10-16-0214-hr-ext-connect-ui-templates/`)落盘; `kb.index` 重建收录核验。本轮纯文档, 无代码/测试改动, 与上一基线同树。
- 2026-10-16 02:38 — 模板评审二轮拍板(R1–R3)入册: token 32 位指纹+悬停全值 / 徽标「手动」废止「优先」/ 操作列收窄(删仅手动, 载入与行内测删除, probe-one 取消); 计划 §03/§04/§05/§06/§08 同步改写 + §11 变更记录; 三模板同步。
- 2026-10-16 02:47 — 排序补记: 实例表手动组在前、自动组在后(上游 26-10-15-2357 Q9 既有语义); §03.1 与三模板行序修正并核验。
- 2026-10-16 03:06 — 第三轮拍板 R4(徽标外框)入册: 用户实报工具栏徽标太大挡住图标, 问「能否改状态色外框」; 可行性分析(问答轮)结论 = 无现成 API, 唯一路径 setIcon 重画图标本体。拍板「路径 A 预生成 4 态 × 2 尺寸 PNG + setIcon({path})」+ 折中「仅发现失败态追加红色 ! 徽标」(平时零遮挡 + 色觉冗余)。计划新增 §3.5/§04 S6/§05 C8/§06 V7/S5 守阵⑦; 三模板图例改框式色样。代码未动, 待实施。
- 2026-10-16 04:00 — S1–S3 实施(用户指令「实施计划S1-3」; 模板选型未记录, 布局按计划 §03.1 纵向流规格 = 模板 A 形态落地, 裁量已记): S1 options.html ①区重排(状态卡 → 发现行短句 → 实例表真 table → 动作行+反馈区 → 说明与排障折叠(收编三段长文 + 徽标图例改「浏览器工具栏」+ 四态框式色样) → 手动端点折叠; ③④两表色点+行 hover, C5 纯展示); S2 background.js(noteInstanceHealth 第四参 state, pollInstanceOnce 全路径带 state, probeInstance 只读探测, probeAll + probe-all 消息, probe-one 随 R3 取消, 徽标/发现/自愈零改动); S3 options.js(renderInstList 表格化: rowHealthOf 四态纯函数/token 前 32 位指纹+悬停/「手动/自动」徽标 R2/删仅手动 R3, testEndpoint→retestAll 走 probe-all + C4 10s 节流, 状态卡拆大状态字+指标 C6, fillForm 空态化)。test.full 3405 passed + 4 skipped 全绿(既有守阵未改一字); rowHealthOf 真值表与 probe-all 沙箱另验。基线切片 `testing/baselines/26-10-16-0400-hr-ext-connect-ui-s1s3.md`。遗留: S4 README / S5 守阵七项 / S6 图标外框; 验收 V1/V2/V7 待真机。
- 2026-10-16 04:20 — S4–S6 实施(用户指令「实施计划S4-6」+「完成后启动桩服务让我验收」): S4 README §2 布局块/排障表/「怎么确认它在工作」/徽标描述(R4 框式「浏览器工具栏的扩展图标状态色外框」)按新形态同步; S6 新增 `scripts/gen_ext_icons.py`(PIL 生成 8 PNG 入库 icons/: 基础无框 + 绿/橙/红框 × 16/32px, 框色与 BADGE 同源, 色框外暗色描边, 中性深色底), manifest `action.default_icon` 指向基础图, background.js::refreshBadge 改 setIcon 换图 + 徽标文字折中(平时清空, 仅发现失败态红 `!`), badgeStateOf 判据不变; S5 新增 6 守阵(rowHealthOf 四态真值表/probe-all 真跑落台账/重测全部走后台反向断言+旧字面量不回潮/图例措辞/来源徽标两值/图标映射+文件在盘), swiss_wiring 元素清单随 S1 更新, badge 用例随 R4 翻转; 上游 `[优先]` 徽标断言经核查在历史测试中不存在, 无需翻转。附带修复 options.js 一处 S3 遗漏的旧按钮名用户可见串。test.full 全绿(数字见基线切片 `testing/baselines/26-10-16-0420-hr-ext-connect-ui-s4s6.md`, 红绿双验三类突变判红), 验收桩 `scripts/hr_ext_stub.py`(dev-only)已启动: 发现端点 18788 + 双数据端点(A 正常/B 401), /control 实时翻转 ok/401/down, 全端点冒烟通过, 待用户真机验收 V1/V2/V7。教训: 变异测试用 `git checkout --` 回退冲掉未提交改动(已 Edit 精确重放复测), 待入坑档。

## 遗留与下一步

- 待用户真机验收(计划 §06): V1 实例表状态列(切 down/401 后点「重测全部」或等 1 分钟轮询, 悬停可见 note) / V2 重测全部(无实例时按钮给指路空态) / V7 图标四态外框(发现地址改 127.0.0.1:19999 演示红框 + 角标 !)。⚠验收桩已于 04:31 停掉(起桩时误杀生产实例, 见下), 需要桩验收时换非生产端口(如 28788)再起。
- 实施时注意: probe 语义若与后端频控冲突见计划 C3 降级路径; 模板选型从未记录, 布局按 §03.1 纵向流基准(= 模板 A 形态)落地, 已记档。
- **事故(2026-10-16 04:31, 用户令记录)**: 起验收桩 `scripts/hr_ext_stub.py` 时 18788(生产发现端点默认端口)绑不上, 未核实监听 pid 身份即跑 `scripts/port_kill.py -- 18788` 强杀, 杀掉用户生产 auto-qb 主程序。已停桩释放端口, 生产数据未动, 重启待用户决定。坑档 `pitfalls/ops/port-kill-prod-instance.md`(杀进程前必须能说出 pid 是什么程序; dev 桩不得默认占生产端口)。教训: 变异回退之外的第二条 —— 「绑不上」的第一解读是「端口有主」不是「端口有垃圾」。
