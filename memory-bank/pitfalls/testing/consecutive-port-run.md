# 连号候选端口只验基址 —— base+1/+2 落排除段即 10013 假红

> 摘要: 「连续 N 个候选端口」类用例(发现端点 base/base+1/base+2)若只用 `_free_port()` 取基址、再自己逐个显式 bind, 后 N-1 位从未被验证: 落进 Windows 动态排除段(Hyper-V/WSL 开机预留, 每次开机不同)或被独占进程占住就抛 WinError 10013/10048 ⇒ 假红。修法两条: ①占位走端口单点 `tests/_test_ports.py::hold_run(n)`(整段逐个真绑并持有, 任一位失败整段丢弃换基址); ②断言写「落在候选表」而不是钉死某个端口号(顺延是正确行为)。**守阵用例本体同理**: 控制流断言不得架在真实端口底板上(issue 26-11-10-0456)。
> 触发: 连号候选端口, base+1, base+2, 排除段, WinError 10013, 10048, _hold_ports, discovery_candidates, 端口单点, hold_run, 假红, netsh excludedportrange, 守阵用例假红, 断言写死重试次数, 真实端口底板, 纯合成 socket

**Refs:** [issue 26-11-06-0330](../../issues/26-11-06-0330-test-hr-discovery-busy-retry-flake.html)

## 本篇只回答

要连续 N 个端口(而不是"一个空闲端口")的测试, 怎么取号才不假红; 以及 10013 假红怎么在 30 秒内确诊。

### 基址自验过 ≠ 整段可绑: 连号候选段必须整段真绑

- **触发**: 写/改任何"占住候选端口表"或"断言顺延到 base+1"的用例 —— 典型是 HR 发现端点
  (`discovery_candidates(base)` = base/base+1/base+2), 用 `_free_port()` 拿基址后自己 `socket().bind(base+1)`。
- **判别**:
  - 报错形如 `PermissionError: [WinError 10013] 以一种访问权限不允许的方式做了一个访问套接字的尝试`
    (端口号通常不是 18788 这类模型默认值, 而是随机高位) —— 10013 是**权限/排除段拒绝**, 不是时序竞态,
    别往 async-wait/flaky timing 上归因。
  - 一行确诊: `netsh interface ipv4 show excludedportrange protocol=tcp` —— 报错端口落在任一区间内即命中本坑。
    区间由 Hyper-V/WSL 开机预留, **每次开机不同**, 所以同一用例今天绿明天红。
  - ⚠ netsh 输出里带 `*` 的「管理的端口排除」段**不等于拒绑**: 2026-11-06 本机实测 50000-50059
    (`*` 段)在 `127.0.0.1` / `0.0.0.0` / `::` 三地址上 bind 全部成功, 真正抛 10013 的是不带 `*` 的
    5357。⇒ 判别以「实测 bind」为准(先试一次), 别只凭 netsh 列表断言某段不可绑。
  - 注意 `bind(0)` 只会分配**未被排除**的端口, 所以基址永远合法 —— 坑一定出在 `base+1` 及其后。
- **处置**:
  - 用单点 `tests/_test_ports.py::hold_run(count=3)` 取号: 它整段逐个真绑并**持有**返回的句柄
    (没有 TOCTOU 窗口), 任一位抛 OSError 就整段关掉换新基址, 连抢 `RETRIES` 次才 `RuntimeError`。
  - **不要**给 10013 加"带理由的有限重试": 重试是遮症状, 整段自验把触发面消掉; 固定候选端口语义
    (base/+1/+2)也因此完整保留。
  - 只要"一个空闲端口"的用例仍用 `free_port()`; 两个入口都在同一单点, 别在测试文件里复制 bind 逻辑。
  - **断言也要跟着改形态**: 别写 `bound_port == base` / `== base + 1` —— 基底被并行 worker 抢走、
    或 base+1 落排除段时, 服务顺延到候选表下一位是**正确行为**。断言落在
    `bound_port in discovery_candidates(base)`(或 `[1:]`)这种**语义**上; 钉死具体端口号 =
    把环境噪声写成判据。`_free_port()` 的 TOCTOU 只能压不能消, 别指望它替断言兜底。
- **守阵用例本体也不许把真实端口环境当判据** (issue 26-11-10-0456): 验证 `hold_run`「整段丢弃换基址」
  控制流的用例若用真实 socket 当底板、只在某一位注入 10013, 那么除注入点外的 bind 都走真实网络 ——
  并行 worker 抢口 / 排除段会让 `hold_run` 多重试一轮, `assert attempt == 2` 被环境噪声打红;
  反方向第一次尝试若因真实端口失败, 注入根本不触发, 用例还会**假绿**。处置: 控制流守阵一律用
  **纯合成 socket**(端口由桩分配、零真实 bind), 断言只认桩内可确定的尝试次数 / 归属 / 关闭状态;
  真绑与持有的语义另留一条用真实 socket 的用例覆盖, 两用例分工不重叠。确定性复验两条: 让所有真实
  bind 一律拒绝 ⇒ 用例仍绿且真实 bind 次数为 0; 把 `hold_run` 换成「吞掉被拒位」的坏实现 ⇒ 用例必须判红。
- **守阵**: `tests/test_free_port.py::test_hold_run_returns_bindable_run`(连号+持有+释放后可绑)、
  `::test_hold_run_discards_run_whose_offset_is_refused`(整段有一位被拒 ⇒ 整段丢弃换基址, 纯桩)、
  `tests/test_hr_discovery.py::test_start_all_busy_returns_false_and_retries`(真实消费方)。
- **复发**: 1
- **同族**: [fixed-port-test-collision.md](fixed-port-test-collision.md) —— 另一半: 夹具沿用**模型默认固定端口**
  导致并行撞端口 / 污染 WARNING 断言(那件的解是默认关掉发现端口, 不是换端口);
  [../ops/port-kill-prod-instance.md](../ops/port-kill-prod-instance.md) —— 10013 的**生产侧**误判:
  端口"有主"与"被排除"是两回事, 别不核实身份就杀进程。
