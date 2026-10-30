# 26-10-31-backend-global-traffic-source-acceptance — 全局流量来源 S19 真机验收(桩测 · Windows 侧)实施记录

**Status:** In Progress
**Added:** 2026-10-31
**Updated:** 2026-10-31
**Summary:** 按验收计划 26-10-31-0446 完成主计划 26-10-17-0339 S19 的桩测化真机验收:四场景 + 三波变更新增面(A5.1–A5.8)+ §08 十条判据逐项实测,全过(2 项标注 N/A/单测覆盖);现场已还原;产出 1 条 P3 级验收发现。
**Topics:** backend-global-traffic-source-acceptance
**Refs:** memory-bank/plans/26-10-31-0446-plan-global-traffic-source-acceptance.html, memory-bank/issues/26-10-31-0537-bug-gtm-autostart-pointer-stale.html

## 原始请求

1. 「26-10-17-0339-plan-global-traffic-source-integration.html 真机验收还未进行,先写一个验收计划」
2. 「注意该模块后续可能经过更改,先找到更改的文档,如果有一并纳入验收计划」
3. 「验收过程使用桩,不碰真实 qb。仅测试 windows 侧」
4. 「dat 来源可参考或直接使用 C:\Users\11059\Desktop\Projects\data\global-traffic-monitor-data,这是我的真机数据。其余两项拍板按推荐,实施」

## 思考过程与决策

- 变更考古(验收计划 §02):S19 成文后三波变更全部纳入验收面 —— ①R2/S20(删 data_dir 键、取数收归 `paths.py::dat_path`);②缺陷修复 Phase 1(26-10-17-1737,enabled 总开关/shutdown/去黑框/设置页四修/复合串/切源即刷新);③自启换轨 HKCU Run(dd4bccb8)+ Phase 2(26-10-18-0818:快照段级契约/三卡并一/正主注册与 claim/批T 三缺陷)。
- 桩策略:qB 用 `tests/helpers.py::FakeQbServer` 独立进程(真机语义 HTTP,登录免校验);工具本体真实运行(只读网卡流量,天然不接触 qB);auto-qb 真实主程序(`dev.run -- <验收yml>`)。验收配置 acc-a/acc-b.yml 放 `tmp-analysis/acceptance-gts/`(gitignored),`data_dir/state_file` 各自独立 → 单实例锁天然隔离,红线 `config.yml`/`auto-qb-data/` 零接触。
- 拍板(用户 26-10-31):D1 场景②走 B 级等价模拟(手工执行 HKCU Run 值命令),A 级真重启待用户;D2 TM 来源 dat 用真机数据副本;D3 工作区 tmp-analysis/acceptance-gts/。
- 现场基线(05:03 实测,backup/site-baseline.md):工具未运行、发现指针目录不存在、HKCU Run 无自启值 → A1 即「纯引导拉起」起点。

## 实现计划

按验收计划 26-10-31-0446 §04:A0 准备(桩/配置/备份/dry-run 冒烟)→ A1–A4 主计划四场景 → A5.1–A5.8 变更新增面 → A6 §08 对账 → A7 还原与落档。全程经 WebUI API(18080,skip_local_verify)+ 日志 + 注册表/指针实测取证。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| A0 | 桩 qB runner(:63931) + acc-a/acc-b.yml + 现场备份 + dry-run 冒烟(修 refresh_interval 格式 `10`→`10S`) | Done(26-10-31) |
| A1 | 场景①未跑→拉起→订阅:零参 launch.cmd→探活 3s→订阅注册;指针随机端口 64821/数据目录=指针值/endpoint 子命令一致/Run 值注册 | Done(26-10-31) |
| A2 | 场景②B 级模拟:Run 值命令手工执行→工具起(正主判定/状态恢复)→实例 A 重启零拉起(全日志「已拉起」仅 1 条);A 级真重启待用户 | Done(26-10-31, A 级 Open) |
| A3 | 场景③双实例:实例 B 零拉起直接订阅 55679;A/B 独立出数;工具侧订阅者含租约过期机制 | Done(26-10-31) |
| A4 | 场景④切 TM 来源(真机 dat 副本):保存即热重载换源(S8 切源即刷新)、订阅自动注销、工具参数保留不参与取数、工具不被自动关;切回 gtm 往返对称 | Done(26-10-31) |
| A5.1 | enabled 总开关:off 快照契约精确(`{"state":"off","history":[]}`/periods 空/source 带原因)、重启不拉起(60s 缺席窗零动作)、一键恢复自动重拉 | Done(26-10-31) |
| A5.2 | 关闭工具:代理 POST /shutdown → 优雅退出、指针删、五态 not_running | Done(26-10-31) |
| A5.3 | 自启不被装回:uninstall 回写 cfg autostart=false → 重拉(恒定 --autostart 意图)Run 值未被写回、指针 autostart_registered=False | Done(26-10-31) |
| A5.4 | 去黑框:`CREATE_NO_WINDOW`(agent.py:241)+ 启动器 pythonw.exe(GUI 子系统)双保险 | Done(26-10-31) |
| A5.5 | 合并卡:traffic-card.html 295 行/settings.html 313 行(<400)、来源区 provider 条件、tmAffectLabels 文案单点、schema 组数 6 | Done(26-10-31) |
| A5.6 | 轮询无 history 键:`/api/status` traffic keys=[date,limit,periods,source,state,ts];`/api/traffic/history` 独立端点 | Done(26-10-31) |
| A5.7 | 复合串:代理读后写 sample_interval 3S,盘上 config.yml 全复合串("3S"/"1MiB"/"3M"),热生效 3.0 | Done(26-10-31) |
| A5.8 | 抢输 fail-fast(锁锚单点、正主 50914 独占监听、无第二端口)+ claim 运行中拒绝 + 正主判定日志 | Done(26-10-31) |
| A6 | §08 对账:10 条中 8 条实测过;「编译态可定位」N/A(无 frozen 产物,分支单测覆盖);「拉起不依赖 uv」实测过(升级模拟由 D19 守阵单测覆盖) | Done(26-10-31) |
| A7 | 现场还原:优雅停工具→停实例 A→停桩;指针目录与工具 data 删除;Run 值零条;真机数据目录原样;零 python 进程 | Done(26-10-31) |

## 进度日志

### R0 · 立档 (2026-10-31)

**验收结论:全过**。主计划 26-10-17-0339 S19 的四场景 + 三波变更新增面全部有逐项实测记录(证据落 `tmp-analysis/acceptance-gts/` 各实例日志与 backup/site-baseline.md;本文档子任务表为索引)。

**验收发现(1 条 P3,待用户决定是否入池)**:
- 卸载自启(POST /autostart uninstall)后,发现指针 `autostart_registered` 字段不即时回写真值(仍 True),UI 开关态读此字段存在漂移窗口,直到工具下次重启写指针自愈(A5.3 重拉后实测 False,自愈确认)。注册方向(install)未见此问题。

**验收注记(非缺陷)**:
- 指针缺失期(工具未跑)快照模块告警文案为 `读取流量数据失败(): ...: ''`(空路径 errno),未走 `unavailable_reason` 的「未在运行/指针缺失」分支 —— 文案可读性改进候选。
- Phase 1 S4 判据「关闭工具后 enabled 变 false 且落盘」由前端一并提交;API 侧 shutdown 端点不改 enabled,本轮分开验证(shutdown ✓ / enabled 持久化 ✓)。
- expr 试算端点在桩 0 种子下无法驱动求值路径;关源文案与 `source.reasons` 同一 `unavailable_reason` 单点(已在 off 快照实测),求值路径由单测覆盖。
- 首拉后首个刷新周期快照短暂 stale,下一周期自愈(工具刚起 dat 未落盘),符合预期。

**测试**:tests/test_sidefx.py 11 passed(coverage 门红为单文件运行的配置伪报);git status 干净(仅 memory-bank 文档变更),工具 data/.venv 均在 ignore 面。

**现场还原核验**:无 python 进程;`%LOCALAPPDATA%\global-traffic-monitor\` 已删;HKCU Run 无工具自启值;`tools/global-traffic-monitor/data/` 已删(验收期创建);用户真机数据目录(`Desktop/Projects/data/global-traffic-monitor-data/`)四文件原样未动。

**遗留**:①A2 A 级真重启待用户方便时补做(结论不受影响);②P3 发现是否入池待用户;③主计划 26-10-17-0339 的 S19 勾选/状态收口待用户确认验收结论后执行;④工作区 `tmp-analysis/acceptance-gts/` 留档(gitignored)。
