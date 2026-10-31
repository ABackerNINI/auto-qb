# 3483 passed + 4 skipped —— 全局流量监视小工具 S8 集成与过渡(纯文档轮)

> 摘要: 用户「实施S8:26-10-16-0541-plan-global-traffic-monitor.html」(对 S8 的显式授权, S9–S10 不动)。**纯文档轮, 零代码/配置/数据改动**: ① `docs/configuration.md` 新增「全局流量监视器工具（gtm）」段 —— 定位与边界 / 安装运行与三平台数据目录 / 工具参数表(全量覆盖写语义) / 三平台自启(注册项 + 幂等判据 + 退出码) / auto-qb 侧 6 键联动配置 / 迁移检查单(9 步 + 回退) / 并行对照 24h 方法(口径差异先排除 + 容差 ≤5% + 可执行脚本) / 双写者禁令; ② `memory-bank/config-reference/keys.md` 联动段补「过渡与迁移」注记; ③ 根 `README.md` 配置参考清单补一条; ④ 三个文档文件被工作区写入判据整文件拦下, 属主授权下按形态等价改写 5 行(语义零变化)。本切片为根 test.full 回归闸门数字。
> 基线时间: 2026-10-16 17:37

- test.full(切片落盘后复跑, **全绿**): **3483 passed + 4 skipped in 186.80s**(墙钟 189.9s); TOTAL 17684 245 6012 180 98.18%(覆盖率门槛 98%)。
- 首跑记录(同一棵树, 在本切片落盘**之前**): 3482 passed + 4 skipped + **1 failed**(195.4s) —— 唯一失败为 `tests/test_docs_forms.py::test_claim_chain_is_bidirectional`, 原因是本档案已声明引用本切片而切片文件尚未落盘(认领链「目标不存在」); 切片落盘后该链自然闭环, 复跑全绿(链上其它件未动)。
- 本步零 `src/` 与 `tools/` 代码改动; 工具的 venv 为按检查单第 1 步现场建立(独立 venv, 仅本目录 `.venv`, 不入库)。
- 沙箱实跑(临时数据目录, 全程后清理; 零触碰生产 config.yml / auto-qb-data): ① 工具目录内同步依赖(独立 venv) → `gtm --version` = `gtm 0.1.0`; ② `gtm run --data-dir <tmp>` 45s: `history_traffic.dat`(`lines: "1"` + 当日行 `2026/10/16 2115/5530` KB, 按 30s 时间面节流刷新) / `state.json`(当日累计 up 2,166,638 / down 5,663,252 B, 每帧推进) / `monitor.token`(43 字符) / `gtm.lock`(+ 伴生 meta) 齐备; ③ 控制面 `GET /status`: 无凭据 401 / 带凭据 200, payload 键 = day / day_up_bytes / day_down_bytes / day_total_bytes / last_event_id / subscriber_count / paths{dat,state,config,token} / config / uptime_s; ④ 对照脚本**从 `docs/configuration.md` 原文抽出**执行: 合成 TM 侧(up +3%+100KB / down -2%+100KB) 与工具侧真 dat 比较 → `2026-10-16 CHECK up 2.2 vs 2.1 MiB (7.16%) | down 5.4 vs 5.4 MiB (0.20%)`(单侧超 5% 判 CHECK); ⑤ 收尾 terminate 后端口释放、临时目录清理。
- 文档机检: `doc.links` / `doc.drift`(无手抄) / `doc.caps` 全过; `test_config_schema`(docs↔代码漂移) + `test_config_key_surface`(键面 + keys.md 反引号出处) + `test_docs_forms` 快跑全绿。
- **未闭合**: S8 出口原文的 24h 并行对照(E1)未跑(需真实 Traffic Monitor + 24h 挂机, 本环境连其数据目录所在盘都不存在) —— 留 S10 真机验收; 检查单第 3 步的 schtasks 自启注册仍受本会话命令安全策略拦截(与 S5 同一缺口); 第 5—8 步涉及真机 auto-qb 与浏览器, 留 S10。

## 本改动面

- `docs/configuration.md`(新段「全局流量监视器工具（gtm）」+ 摘要行与 Traffic Monitor 小节交叉指针; 其中 2 行为属主授权的形态等价改写)
- `memory-bank/config-reference/keys.md`(「过渡与迁移」注记; 1 行形态等价改写)
- 根 `README.md`(配置参考清单 +1 条; 2 行形态等价改写)
- `memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html`(§04 R0 增 S8 行 + 状态行 + 脚注 + doc-updated; 改后跑 HTMLParser 标签平衡机检: 未闭合 0 / 乱序 0)
- `memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md`(R9 + 子任务表 S7/S8 → Done)
- `memory-bank/pitfalls/ops/agent-write-guard-secret-false-positive.md`(复发 +1: 文档类三文件 + 「整文件级探针」手法)
- 沙箱脚本为 scratch(`.openclaw/tmp/`, 不入库)

**Refs:** memory-bank/tasks/26-10-16-backend-global-traffic-monitor.md, memory-bank/plans/26-10-16-0541-plan-global-traffic-monitor.html
