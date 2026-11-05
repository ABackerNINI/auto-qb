# 26-11-05-backend-relocate-fastresume-finalize — relocate 收尾重构: fastresume 改写方案验证与计划入库

**Status:** In Progress
**Added:** 2026-11-05
**Updated:** 2026-11-05
**Summary:** relocate 收尾弃 dir_alias 链改 fastresume 改写: 用户原案「当场改」被源码+N1 实测证伪(0.5s 被覆盖), 修正案 journal+下线窗口+核验删链经测试 qB N2-N8 全绿, 计划 26-11-05-0808 已入库待实现轮认领
**Topics:** backend-relocate-fastresume-finalize
**Refs:** memory-bank/issues/26-11-05-0420-bug-relocate-zero-move.html

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

## 实现计划

实现轮按计划 26-11-05-0808 §3.4/§4 分期执行:

1. S1 配置与预检: `bt_backup` 配置键(validate_config+schema)+ 五类闸门(后端/可达/AutoTMM/嵌套/三态)。
2. S2 编辑器: 新模块 `core/fastresume.py`(双键前缀替换保风味/bdecode 往返自校验/原子写/.bak 备份/hybrid 用 .torrent 对定位)。
3. S3 journal 与下线窗口: state_file 账区 + tick 失联探测 + 幂等重放。
4. S4 核验与删链门: 全员核验/等值 OR 前缀门/删种穿 junction 拦截/失败反馈面; ACT_FINALIZE 链退役。
5. S5 全量验收: N0-N8 复跑 + 0546 继承项回归 + test.full 基线切片。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | grilling + 源码机制核对(qB/libtorrent) | Done(2026-11-05) |
| 2 | 测试 qB N0-N8 验证(原案证伪+修正案全绿) | Done(2026-11-05) |
| 3 | 计划文档 26-11-05-0808 入库 | Done(2026-11-05) |
| 4 | 实现轮 S1 配置与预检 | Open |
| 5 | 实现轮 S2 编辑器 | Open |
| 6 | 实现轮 S3 journal 与下线窗口 | Open |
| 7 | 实现轮 S4 核验与删链门 | Open |
| 8 | 实现轮 S5 全量验收+基线切片 | Open |

## 进度日志

### R0 · 立档 (2026-11-05)

方案验证轮: 源码机制 11 条钉死(单点=计划 §2.2); 用户原案「当场改」被 N1 证伪(0.5s 覆盖), 修正案(journal+下线窗口+核验删链)经 N2-N8 测试 qB 全链路实测成立(全绿, 断言明细见计划 §2.3); 部署矩阵 A-E 定稿(真机 N 系列即本轮真机自检形态); 计划 26-11-05-0808 入库, 实现轮 S1-S5 待认领; 新坑 2 条入档(testing: python 子进程调不到 commands wrapper / backend: qB fastresume 编辑纪律)。

- 2026-11-05 08:18 方案验证轮收口: 原案证伪+修正案 N2-N8 全绿, 计划 26-11-05-0808 入库, 实现轮 S1-S5 待认领
