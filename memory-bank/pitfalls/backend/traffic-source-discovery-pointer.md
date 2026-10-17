# 发现指针是唯一事实源: 用户级目录 + 探活判定, 不是数据目录 + pid

> 摘要: 工具发现层若把指针/锁放进 data_dir 或拿 pid 判存活, 一旦 `--data-dir` 改过、进程崩了留 pid、或按 cwd 推目录(自启时 cwd 是 system32)就全错。正解: 指针与锁锚用户级平台目录(与数据目录解耦)、就绪只认 `GET /status` 200、锁在绑端口前 acquire、两侧常量镜像同值。
> 触发: endpoint.json, 发现指针, 全局流量来源, global-traffic-monitor, 探活, 未运行, 拉不起来, data_dir, pid, 残留指针

### 指针锚用户级目录、锁锚指针旁、就绪只认探活 —— 拿 data_dir 或 pid 当判据必错

- **触发**: 给「独立进程 + 开机自启 + 多实例共享」的工具做发现层时(本仓 global-traffic-monitor,
  计划 26-10-17-0339 D6–D8), 本能做法是「去数据目录找 pid / 锁文件」或「按固定端口直接探」。
- **判别**: ①工具明明在跑, auto-qb 却报「未运行」且日志里读不到指针 —— 指针落在 data_dir 或旧版
  用户目录里, 而 data_dir 被 `--data-dir` / `GLOBAL_TRAFFIC_MONITOR_DATA_DIR` 改过(**指针不随
  data_dir 移动**); ②进程崩了但 pid 文件还在, 被判成「在跑」; ③被拉起/自启时数据写进
  `%Windir%\system32` —— 按 cwd 推目录(自启时 cwd 不可信)。
- **处置**: ①`endpoint.json` 与 `instance.lock` 锚在**用户级平台目录**(Windows
  `%LOCALAPPDATA%\global-traffic-monitor\` / macOS `~/Library/Application Support/...` / Linux
  `~/.local/share/...`), **与数据目录解耦**, 只此一处; ②就绪判据只认 `GET /status` 200(带 token) ——
  残留指针不算就绪、也不阻止拉起, pid 仅作展示; ③锁在**绑端口/采样之前** acquire, 抢输的进程
  fail-fast 且不占端口; ④两侧常量各持一份镜像(auto-qb `core/traffic_source/agent.py` ↔ 工具
  `gtm/storage.py`), 改一边必须同步另一边 —— 工具是独立包, auto-qb 不 import 它。
- **守阵**: `tests/test_traffic_source_agent.py::test_pointer_constants_mirror_tool_side`(跨包镜像
  常量同值) · 工具侧 `test_server.py::test_losing_instance_locks_out_before_binding_port` /
  `test_endpoint_written_on_start_with_fields` / `test_endpoint_removed_on_stop`
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
