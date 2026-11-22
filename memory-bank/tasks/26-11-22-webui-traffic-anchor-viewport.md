# 26-11-22-webui-traffic-anchor-viewport — 流量图尾锚显式视口重构: 三不变量结构性消除压缩类问题

**Status:** Done
**Added:** 2026-11-22
**Updated:** 2026-11-22
**Summary:** 流量图尾锚显式视口重构: 视口从 auto 派生改尾锚显式恒等式 + 单列恒等 + 余量列 + 换窗竞态窗口分量, 三轮补丁层退役
**Topics:** webui-traffic-anchor-viewport
**Refs:** memory-bank/plans/26-11-22-0858-plan-webui-traffic-anchor-viewport.html, memory-bank/tasks/26-11-22-webui-traffic-interrupt-inherit.md, memory-bank/tasks/26-11-21-webui-traffic-window-head-trim.md, memory-bank/pitfalls/web-ui/traffic-implicit-viewport.md, memory-bank/issues/26-11-22-1401-bug-traffic-anchor-transient-gap.html

## 本篇只回答

「流量图 x 向压缩历经三轮修复(26-11-21-1704 数据面修剪 / 26-11-22-0626 打断继承 / 本轮分析定位换窗竞态)为何仍有残留, 以及如何用尾锚显式视口三不变量从结构上彻底消除此类问题」——重构方案与实施记录。三轮各自的根因与修法见 Refs 两档案与计划 26-11-22-0858。

## 原始请求

1. 「这个问题没有彻底解决：流量图左移时左边的曲线不出窗口而是曲线整体在x方向上压缩，这是错误的行为。目前还是偶尔有x方向上的压缩，特别是1m视图，分析原因。这是第三轮修复」(只读分析轮)
2. 「不要再打补丁了，需要重构，从结构上彻底消除此类问题」(授权重构; 计划 26-11-22-0858 经 ExitPlanMode 拍板批准, 动画语义 D1 = 保留平滑左移、全窗统一整体平移)

## 思考过程与决策

- **第三轮根因(本轮分析取证)**: `_qbLoad` 落袋前 stale 判据(`def.stale` 三谓词)只核对作用域上下文不含窗口名——换窗时旧窗口在途 GET 响应落袋覆盖新窗口数据; trim 门读 stale meta 的 span_s 使压缩不自愈到下一笔对账。端到端仿真复现: 快速双切 1m→5m→1m 响应乱序后, qbHistWindow="1m" 而视口跨度 299.5s。
- **结构根因裁决**: 视口是隐式派生态(uPlot auto range 从显示列现推, 显示列 = GET 组点列 + SSE 尾点 + F5 补点三源拼接)——列跨度 ≠ 名义窗的任何时刻(修剪失效/补点滞留/打断继承漏判/旧窗响应落袋)视口跟着错 = 用户看到的压缩。三轮补丁各修一层, 层层有残留。
- **重构裁决(D1-D3, 计划 26-11-22-0858)**: 三不变量——①视口恒等式 `[anchor − span_s, anchor]`(锚 = 末样本时刻单调递增, auto x range 全窗退役); ②单列恒等(store 列 == 显示列, 补点/`_qbPad` 记账/收敛 slice/悬停扣减退役, 列 = `[tail − (span+margin), tail]` margin=2 组距); ③取数有效性(_qbLoad stale 判据加窗口分量)。动画 = 锚点滑动(旧→新 easeOut, min/max 同步平移), 打断从自身存储在途锚续滑, `_qbInheritedViewport` 公式重建整套退役; instant/reduce 恒定压缩变体(上档案 D4 遗留)随补点退役自然消失。后端零改动(meta.span_s 供应契约原样)。
- **取证面**: 全链真函数仿真(16+15 相位 GET 打断扫描/隐藏往返/seq 断档/突发帧/尾点替代)证明前两轮修的拍机制无残留; 换窗竞态端到端复现坐实; 爆炸半径探查(补点/视口机制运行时消费面 100% 收敛在 qb_traffic_chart.js 自身, FX 层只读 bbox/valToPos 不读 scales.x, e2e 与电池分类清单齐备)。

## 实现计划

分四步(计划 26-11-22-0858 §实施; 每步独立可验):

1. **S0 立项**: 计划 HTML + 本档案 + 取证归档(零代码改动)。
2. **S1 几何核心重构**: chart 文件 judge/判定帧/帧循环/收敛帧/快路/修剪余量/历史保留合并/取数竞态窗口分量/fx spawn 公式/悬停直通/摘要窗内桶数/建图初始视口 + 头注与节注换代; 电池重写(锚不变量矩阵 + 静态钉) + e2e 适配; 红绿双验。
3. **S2 回写**: 权威附件 webui-traffic-beat.md 换代 + pitfalls 新档 + 架构文档 + kb.index。
4. **S3 收尾**: test.full 全绿 + 基线切片 + 分批评审零 actionable + 真机冒烟(1m 连续观察/换窗对比/对账撞拍)。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | S0 立项(计划+档案+取证归档) | Done(2026-11-22) |
| 2 | S1 几何核心重构(chart 全改动面 + 竞态窗口分量) | Done(2026-11-22) |
| 3 | S1 电池换代(J/L/S 系锚不变量矩阵 + S20b 封堵 + 静态钉)+ e2e 流量系零适配全绿 | Done(2026-11-22) |
| 4 | S1 提交(dev.fmt + 评审 + ship.commit) | Done(2026-11-22, 收口提交 284b152f · 本地未推送) |
| 5 | S2 回写(beat 附件换代收口节 + pitfalls 新档 + kb.index) | Done(2026-11-22) |
| 6 | S3 收尾(test.full 6789P 基线切片 26-11-22-1117 + 评审 + 真机冒烟) | Done(2026-11-22) |

## 进度日志

### R1 · S1+S2 实施 (2026-11-22)

- 几何核心: 三不变量落地(视口恒等式/单列恒等/取数窗口分量); 退役四层(_qbRollJudge/_qbPadTailColumns/_qbInheritedViewport/_qbBeatVpRem/_qbPad); 新纯函数三件(_qbAnchorJudge/_qbAnimAnchorAt/_qbRetainHistory); 修剪线 span+2 组距; fx spawn 名义窗长; 悬停直通; 摘要窗内桶数; 建图初始视口。
- 电池: 节拍 J1-J10/L1-L9/S0-S20b 换代(含 S20b 余量列变异盲区封堵 —— 红验实证: 停用收敛帧重申行即红); 静态钉换代+退役件零残留反向钉; mkBeat 签名全家化。test.quick 6793P; e2e 流量系 55P 零适配(锚视口下断言天然成立)。
- 回写: beat 附件换代收口节(现行权威)/pitfalls web-ui/traffic-implicit-viewport 新档/kb.index/基线切片 26-11-22-1117。
- 插曲: 早期 python 补丁用陈旧索引切片把测试文件复制出重复函数副本(重名守卫拦下) —— 从 HEAD 重建 + 补丁脚本重放(锚点修 i_shared 按位后移)收敛; 教训并入 pitfalls 流程面(大文件手术一律单目的原子化脚本 + 每步 AST 校验)。

### R2 · 评审修复轮 (2026-11-22)

- 分面评审(正确性/安全/测试缺口三只读子代理, 检 17/17 过检): 安全面零发现; 正确性 1 major(预览收口 _qbPreviewEnd 漏显式视口重申 —— setData 第 5 写点)+ 3 minor; 测试缺口 7 blocker(e2e 六处读退役字段 st.xN0/a.dx0/a.dxN —— 修复轮实证: e2e 流量系此前 55P 结论不可靠, 采样门关后断言空转)+ 2 major(保留合并/摘要桶数缺行为用例)+ 4 minor + 1 nit。
- 修复轮落地: 预览收口显式视口重申(chart)+ e2e 三 spec 换代(grid-stability 三桩补 span_s + A4 点数有界化 + 首刻位细化凹口容差 + fx-frames 采样器锚位移/shift 过滤/flipB 双缘签名 + A2 桩 span_s)+ 摘要 schema 门(agg 回落全列)+ 活节注/wiring/SSE doc 修剪线换代 + retain 边界点 + L9b 锚优先电池(锚领先尾时修剪线按锚 —— e2e A2-24h 实证 G-B 左缺口回潮路径, 数据面修剪线锚视口化)+ 入池 1(瞬态左缺口边角: 锚领先尾超 2 组距的连续滑动段, 间歇自愈, e2e A2-24h 曾实证)。
- 复跑: test.quick 6793P / e2e 流量系 69P 全绿。教训: e2e 绿结论必须核对逐用例名(采样门空转 = 断言全死的假绿)。

### R3 · S3 真机冒烟 (2026-11-22)

- 真机面: 生产 config.yml 干跑探针确认 qB 在线(主循环连真 qB 跑通; 规则动作 dry_run 桩零副作用, checking.py:110 显式短路实证)。观察面 = 测试实例 36595(real.env 环境1, connection_status=firewalled 合格态, 免鉴权零凭据)——生产 WebUI 凭据面在 config.yml(红线不读), 按 real-machine.md 真机轨口径连白名单测试实例。WebUI 经 dev.run + 自写最小派生配置(H:/Temp/agent-smoke-config, data_dir 显式钉 temp, qb_traffic.enabled=true, 全自动任务关零凭据)。
- 协议(playwright chromium 真浏览器; 全局流量图走 Ctrl+\ 键盘入口——qb_traffic 缺省关时状态栏入口不渲染): 1m 连续观察 344s(覆盖约 11 次 30s 对账撞拍)→ 换 5m 停 46s → 回 1m 停 46s → 切页往返(设置页往返, 抽屉保持打开经 drawerVisible 补拉恢复)再观察 45s; 2s/拍采样读 uPlot scales.x.min/max + _qbBeat.anchor + 数据列头尾。
- 验收判据(231 个稳定样本, 1m×210 + 5m×21): **视口跨度恒等于名义窗——spanDev 全零**(60s/300s 逐样本分毫不差); **无压缩**(压缩 0 / 越界 0); **无左缺口**(0 次, 已知瞬态 issue 26-11-22-1401 形态未复现); tail 全程 == anchor(锚领先尾未出现); 零 console/page 运行期错误。三不变量真机面全部成立。
- 记账: ① dev.webui 启动迁移备份落仓库 auto-qb-data/config.yml.v1.bak(21:05 前一次 20:58 覆盖写; 内容 = temp dev 配置备份无凭据, 已 grep 核验; 根因 = dev_webui.py CONFIG_TMPL 未设 data_dir, 默认相对 "auto-qb-data"(models.py:583)所致, 与其头注「不碰仓库 auto-qb-data」相悖)——脚本缺口非本次手写, 范围外不入修, 建议主会话入池; ② 干跑探针进程(15624/36312)父控制台已消亡无法投递 Ctrl-C, taskkill 红线禁强杀, 留用户手动关闭(持生产 state 锁; dry-run 语义零 qB 变更)。

### R4 · 复评轮4-8闭环 + 收口提交 (2026-11-22)

- 复评闭环(本地分支态, 分面 3 + 全能档串行, 轮 4-8): 送检 50 / 过检 49(弃 1 幻觉引文), 48 条发现全修, blocker 0, 累计入池 1(26-11-22-1401 保持 Open)。主要修复: 收敛帧/预览收口/rescale 三写点 y 成对钉(根除两把尺纵轴泵动) + 电池钉 b/j/d 成对钉红网 + S20c 余量持峰用例 + 旧尾锚形注释/文档 12 处迁锚优先形。
- 收口提交 284b152f(trailer: 3033 行 · blocker 0 · 修 48 · 入池 1 · 检 49/50 · 轮 8 · 基 d28706217ad7 · 派发 3); 本地分支 webui-traffic-anchor-viewport-cont, 未推送。
- 全链实测: test.quick 6793P/2S; test.full 6789P/6S 覆盖率 99%; e2e 七 spec 69P; 基线切片 26-11-22-1117 数字未变。
- 插曲: 轮 6 评审子代理被宿主内存崩溃打断一次, SendMessage 续跑成功, 结论完整。

### R0 · 立档 (2026-11-22)

用户第三轮报障(只读分析轮)→ 全链仿真取证定位换窗竞态(stale 判据不含窗口名, 端到端复现 299.5s 视口)→ 用户拍板重构(「不要再打补丁了」)→ 计划 26-11-22-0858 经 grilling(D1 动画语义拍板整体平移)与 ExitPlanMode 批准 → 计划与档案入库, 双向补链两前档案。S1 待显式开工。

- 2026-11-22 11:18 S1+S2 落地: 三不变量几何核心+电池换代+e2e零适配全绿+回写四面; 待评审与提交
- 2026-11-22 21:17 S3 真机冒烟完成: 231 稳定样本 spanDev 全零(1m/5m 名义窗恒等), 无压缩无左缺口, issue 26-11-22-1401 形态未复现; 三不变量真机面成立(详见 R3)

- 2026-11-22 21:24 复评轮4-8闭环(送检50/过检49, 48条发现全修, blocker 0, 累计入池1)+ 收口提交 284b152f(本地未推送)+ 真机冒烟三判据全过; 全链测试数字见基线切片 26-11-22-1117 未变
