# 26-11-05-backend-relocate-fastresume-finalize — relocate 收尾重构: fastresume 改写收尾 + 未收尾再迁移(S1-S6 全程)

**Status:** Done
**Added:** 2026-11-05
**Updated:** 2026-11-07
**Summary:** relocate 收尾弃 dir_alias 链改 fastresume 改写(N2-N8 实测背书); R1 并入 0247(Superseded): 收敛公理→回收 daemon 复活职权换位(下线窗口改写)+ 未收尾再迁移(supersede 两形态); R2 实验轮 N9-N12 全绿拍板 D19-D20; R3 实现轮 S1-S6 全部完成(9 子任务串行派遣, N0-N12 实现路径复跑全绿+0546 继承项回归全 PASS), 收口评审 blocker 清零(8+5 条全修, 入池 0), 全量全绿(见 kb.baseline); 后续 WebUI 设置页接线收口批(计划 26-11-07-0708): bt_backup 编辑组件嵌「整组迁移」块 / finalize_timeout v6 移除 / e2e settings spec / 评审 5 批全过, 计划已 Done
**Topics:** backend-relocate-fastresume-finalize
**Refs:** memory-bank/plans/26-11-05-0808-plan-relocate-fastresume-finalize.html, memory-bank/issues/26-11-05-0420-bug-relocate-zero-move.html, memory-bank/issues/26-11-06-0448-bug-real-down-force-kill.html, memory-bank/issues/26-11-07-0528-question-relocate-supersede-cancel-semantics.html, memory-bank/issues/26-11-07-0528-feat-recycle-daemon-roster-machine-wide.html, memory-bank/pitfalls/backend/prefix-rewrite-nested-root.md, memory-bank/pitfalls/testing/free-port-toctou-parallel.md, memory-bank/pitfalls/web-ui/ui-entry-tradeoff-unreported.md, memory-bank/plans/26-11-10-0318-plan-recycle-daemon-instance-evidence.html

## 原始请求

1. 整组迁移重构换思路: mover 数据移动成功/链接建立成功后, 当场直接改 fastresume 指向新路径, qB 重启后无感; 收尾仅需 qB 退出/重启后删链接。
2. 需读 qB/libtorrent 源码确定 qB 只在启动时读 fastresume。
3. 前提核查: auto-qb 必须能访问 qB 的 fastresume(同机/跨容器映射), 考虑受影响使用场景; HR 在线核实插件既有场景(NAS 部署 qB、电脑配置扩展)纳入, 出部署形态矩阵表。
4. 先用测试 qB 验证方案可行性、能否通过压测 26-11-05-0546、有无新问题; grilling。
5. (后续轮) 用户答 grilling: AutoTMM 释义询问; 后端检测手段补充; 删链按推荐+同窗删留作后续可选项; HR 场景仅作覆盖考量; 其余按推荐。
6. (后续轮) 写计划。 (后续轮) 提交。

## 思考过程与决策

- 源码核对(qB 8182ae071 / libtorrent 53acefea9 只读)钉死 11 条机制(机制表单点 = 计划 26-11-05-0808 §2.2): fastresume 仅启动读; 运行期 ~20 类操作挂 `deferredRequestResumeData` 秒级重写 + 60min 周期 + 退出必写; save path 双键(`save_path`/`qBt-savePath`)加载各取各键且分隔符风味不同; SQLite 后端无文件可改; AutoTMM 成员无 qBt-savePath; libtorrent `verify_resume_data` 尺寸级核对无 mtime。
- **N1 实测证伪用户原案「当场改」**: 编辑双键生效后 `/torrents/start` 0.5s 被 qB 整体重写回旧路径, 重启终局=旧路径, 端到端零效果。
- 修正案(拍板 D1): 当场只记 journal(state_file) → qB 下线窗口落盘改写 → 重启 API 核验 → 在线删链(门=等值 OR 前缀+组外依赖扫描)。
- 用户拍板 D2-D5: 后端 Legacy 但加运行时检测(`app/preferences` 的 `resume_data_storage_type`)非 Legacy fail-fast; 删链核验后在线删、同窗删留作稳定后可选; 部署矩阵 D/E 格禁用不保留双轨; HR 场景按通用拓扑覆盖。
- N2-N8 测试 qB(36596, v5.2.3 Legacy)全绿: 下线改写无感加载 / 竞态自愈 / 删链门正确 / 坏 bencode=种子静默消失+备份回滚全愈 / 全链路(3 成员共享根+组外共享者)零拒载零重校验账面 1.00 / AutoTMM 闸门依据实测。
- grilling 轮次与实验证据逐条沉淀进计划 26-11-05-0808(§2.2 机制表 / §2.3 实测背书 / §3 时序与组件 / §5 待拍板 D6-D8 / §6 拍板 D0-D6)。
- 过程插曲: 生产 26586 在本轮开工前 1h42m 已非优雅退出(日志止于 06:00:43, 无退出记录), 经日志时间线交叉核验确认与本轮无关(本轮全部动作仅触 36596/36595, 用户确认继续)。
- R1(2026-11-06): 用户判定 0247(单回收 daemon+supersede)基于重构前机制设定, 需重新考量后并入;grilling 两轮收敛出公理 —— 收尾收敛不得依赖退出顺序与 auto-qb 存活(主循环捕窗在 auto-qb 关闭态 qB 退出、关机风暴、开机双自启竞速上系统性漏窗;journal 永久悬挂 = 别名存续/拦截面/确认门/跳检屏蔽风险随时长单调增, 不可接受;收敛画像不得低于旧 guardian)。
- 公理推翻「下线窗口执行器=主循环」原判 ⇒ daemon 复活职权换位: 等 qB 下线批量改写 fastresume(触发单事件 ⇒ nudge/端口文件/300s 兜底扫整套不要, 窗口开头现读 pending);核验+删链留主循环在线(破坏性步骤必须被监督, 0420 教训);账本 = per-job journal 文件协议(daemon 绝不碰 state.json, 法则 5 修订注记);永不退出尾巴 = WebUI「立即收尾」按钮(app/shutdown), 配置化自动重启不做。
- 0247 改动二保留目标重写实现: 闸门放行 {armed, rewritten},rewritten 态 = 链式独立双门近零新逻辑,armed 态 = supersede 重定向(journal 条目+junction 重建, alias_fs 重定向函数从零写 —— 现状无此函数);失败整体拒绝+回滚;删种拦截须覆盖文件级 symlink(现状完全无拦截);FINALIZE_WINDOW 重定义新相位且更承重。
- 实验前置 N9-N12(daemon 捕窗收敛含 auto-qb 关闭态 / pending supersede / 链式塌缩 / 失败回滚), 全绿后 S5 细则定稿;0808 删除重写防增量漂移(用户拍板), 0247 翻 Superseded 附继承/退役清单, 0247 专题切片迁出 activeContext。
- R2 实验轮(2026-11-06, 全绿; 详录 tests-real/.work/nseries/results-n9-n12.md): N9 四场景全过(关闭态 37.6s 收敛/app/shutdown HTTP 200 可用/风暴+竞速零坏状态); N10 经 junction 搬 B→C moving 态信号仍出现; N11 双门独立互不扰; N12 OS 级+机制级注入均指纹级回滚。
- S5 硬约束两条(实测): ①重定向/重建别名必须在数据搬移之后(第二次搬移的源解析跟随 junction 现目标, 先重定向会把源指离数据); ②supersede 必须覆盖旧 mover —— 新 mover 搬走共享数据后老 mover(account=被搬离根)立刻断粮, 须补 {B→C} 条目或让老 mover 当新 mover(待拍板)。
- N12 边界: 搬移完成后再注入失败, 回滚无法恢复成员服务(数据已在 C / 恢复的 A→B 悬空 / 新 mover 账面已 C)⇒ 搬后失败语义待拍板(搬前预检 / 补偿搬回 / 重试至收敛)。
- 编辑器输入(S2): 跨卷 setLocation 会把 lt save_path 键写成 CWD 相对路径(qBt-savePath 保持绝对), 重载按 qB CWD 解析回同一目标 —— 「不匹配即跳过」正确且绝不可自行重推导绝对路径; 「零重校验」断言口径排除 loading 期 checkingResumeData(良性)。
- R2 拍板(2026-11-06, 用户按推荐): 旧 mover 处置 = 通用补条目规则(D19)、失败语义分段 = 搬前整体拒绝回滚+搬后重试至收敛+搬前预检加项(D20)→ S5 细则写死进计划 §3.2/§3.4/§04; 附带发现 real.down(cmd_down)实现为 Stop-Process -Force 强杀触进程红线, 本轮弃用改走 app/shutdown, 已入池 26-11-06-0448(bug/standard, 与本档案双向链)。
- R3 实现轮(2026-11-07, 委派者会话拆 9 子任务串行派遣, commit c84049d4..4f70190f 共 10 个): S1 配置与预检五闸门(16e7c7b7)→ S2 编辑器 core/fastresume.py(5954dd69)→ S3a journal+daemon 主体(5cd27795)→ S3b 对账接线+立即收尾按钮(c65bd368)→ S4a 相位模型切换拆旧(dir_alias 收尾链整链退役含 finalize_watch.py 删除, 净 -1353 行, d3a70275)→ S4b 核验删链门+删种拦截+重放入口+反馈面(2fe6ca61)→ S5 未收尾再迁移(armed supersede 先搬后重定向+rewritten 链式双门, de774ad5)→ S6 真机验收 T8a-T8c(N0-N12 实现路径复跑全绿+0546 继承项回归全 PASS, 803c4039 修复部署维闸门只挂预检漏执行入口的绕过洞, b5115eb6 覆盖率补测 +45 用例)→ 收口评审修复(4f70190f)。
- R3 关键实现事实: bt_backup 配置键(host:port → BT_backup 目录表, hidden 不图形化); fastresume 双键改写单点 core/fastresume.rewrite_save_paths(嵌套根两向裁决: already 只认「改写确为无操作」); 回收 daemon tools/recycle_daemon.py(三证窗口=名册证+端口证合取, 实例级 daemon.json 心跳, 绝不碰 state.json); 相位 {armed, rewritten}; 核验删链门=等值 OR 前缀+组外依赖扫描; 删种拦截覆盖 junction+文件级 symlink; 未收尾再迁移=supersede 先搬后重定向(硬约束①)+旧 mover 通用补条目(D19)+失败分段(D20)。
- R3 评审留痕: 收口评审分面 3 轮只读子代理, 主评 8 条(1 blocker+2 major+3 minor+2 nit)全修, 修复增量 463 行触发复查轮 2 面 5 条(4 minor+1 nit)次修, 入池 0; blocker=#1 嵌套根 already 误判(前缀替换幂等判定教训入坑档 backend/prefix-rewrite-nested-root)。
- R3 验收与基线: N0-N12 实现路径复跑全绿(详录 tests-real/.work/nseries/results-n0-n8-impl.md 与 results-n9-n12-impl.md, gitignored 区; N9-N12 驱动脚本按计划 §03.5 重建留档); 0546 继承项回归全 PASS; T8b 发现并修复部署维闸门执行入口漏拦(SQLite/bt_backup 坏路径可经移动按钮绕过预检, +8 行修复+3 回归用例); test.full 全量全绿(见 kb.baseline, 切片 26-11-07-0440-code-review-fix-baseline)。
- R3 坑档两条(本档案 Refs 已互链): ①testing/free-port-toctou-parallel —— test_hr_discovery 真绑定用例并行 TOCTOU 撞段(T3/T5/T6/T8c 四轮各中一次, 单跑恒绿; 与 fixed-port-test-collision 机制不同故新记不复发); ②backend/prefix-rewrite-nested-root —— 评审 #1 blocker 的幂等判定教训。

## 实现计划

实现轮按计划 26-11-05-0808(R1 重写)§3.4/§4 分期执行(实验轮与 S1-S4 可并行, S5 实施前 N10-N12 必须全绿):

0. 实验轮 N9-N12: daemon 捕窗收敛矩阵(含 auto-qb 关闭态)/pending 态 supersede/链式塌缩/重定向失败回滚; 复用 tests-real/.work/nseries 脚手架。
1. S1 配置与预检: `bt_backup` 配置键(validate_config+schema)+ 五类闸门(后端/可达/AutoTMM/嵌套/三态)。
2. S2 编辑器: 新模块 `core/fastresume.py`(双键前缀替换保风味/bdecode 往返自校验/原子写/.bak 备份/hybrid 用 .torrent 对定位)。
3. S3 回收 daemon 与下线窗口: 新模块 `tools/recycle_daemon.py`(三证/现读 pending/批量改写/pid 抢占退位)+ journal 协议 rewritten 相位 + ACT_ENSURE_DAEMON + 立即收尾按钮。
4. S4 核验与删链门: 新相位模型/等值 OR 前缀门/删种拦截(junction+文件 symlink)/FINALIZE_WINDOW 重定义/rebuild-from-journal/ACT_FINALIZE 链退役/失败反馈面。
5. S5 未收尾再迁移: 细则待 N10-N12 全绿定稿(闸门收窄/supersede 重定向/失败回滚/登记迁移)。
6. S6 全量验收: N0-N12 复跑 + 0546 继承项回归 + test.full 基线切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | grilling + 源码机制核对(qB/libtorrent) | Done(2026-11-05) |
| 2 | 测试 qB N0-N8 验证(原案证伪+修正案全绿) | Done(2026-11-05) |
| 3 | 计划文档 26-11-05-0808 入库 | Done(2026-11-05) |
| 4 | R1 合并重写: 并入 0247(daemon 复活职权换位+再迁移), 0808 删除重写、0247 翻 Superseded | Done(2026-11-06) |
| 5 | 实验轮 N9-N12(daemon 收敛/supersede/链式/回滚): 全绿, 结论与硬约束入思考 R2 块 | Done(2026-11-06) |
| 6 | 实现轮 S1 配置与预检(五闸门) | Done(2026-11-07, 16e7c7b7) |
| 7 | 实现轮 S2 编辑器 core/fastresume.py | Done(2026-11-07, 5954dd69) |
| 8 | 实现轮 S3 回收 daemon 与下线窗口(主体+接线+按钮) | Done(2026-11-07, 5cd27795+c65bd368) |
| 9 | 实现轮 S4 核验与删链门(相位切换拆旧+删链门) | Done(2026-11-07, d3a70275+2fe6ca61) |
| 10 | 实现轮 S5 未收尾再迁移(supersede) | Done(2026-11-07, de774ad5) |
| 11 | 实现轮 S6 全量验收+基线切片(N0-N12+0546 回归+覆盖率补测) | Done(2026-11-07, 803c4039+b5115eb6) |
| 12 | 收口评审(分面 3 轮, 8+5 条全修, 入池 0) | Done(2026-11-07, 4f70190f) |
| 13 | 收尾回写(切片/回写/pitfalls/索引) | Done(2026-11-07) |

## 进度日志

→ 逐轮进度日志(R0 立档至 2026-11-07 WebUI 设置页接线收口批, 共 11 条)已逐字外迁: [attachments/26-11-08-relocate-fastresume-finalize-progress-log.md](attachments/26-11-08-relocate-fastresume-finalize-progress-log.md)(26-11-08 cap 清零)。
