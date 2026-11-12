# 进程级 monkeypatch 探针(builtins.open 等)在 xdist 下会被同 worker 遗留线程污染 —— 探针必须按目标根目录收窄

> 摘要: 测试用 monkeypatch 替换**进程级**单点(`builtins.open`/`subprocess.Popen` 等)当探针记录被测行为时, 记录面默认是「全进程」; -n 8 并行下同 worker 进程里**前序测试遗留的守护线程**(tests/ 有 20+ 文件起线程, xdist 每 worker 是独立进程但进程内测试按序复用)可能在被测窗口内并发触发同类调用 —— 它们打开的是**别的 tmp_path** 下的文件, 只按「路径含某子串」收录就会把残账记进本用例的期望集 ⇒ 断言假红(单跑恒绿, 并行偶发, 无法稳定复现取证)。对策: 探针收录面按**本用例的目标根目录前缀**收窄(被测代码只可能触碰自己的根目录, 收窄不放松断言语义); 守阵双向红验(跨根打开不入探针 + 自家根打开入探针)。
> 触发: builtins.open 探针, open 计数, 进程级 monkeypatch, 探针污染, xdist 遗留线程, 守护线程, tmp_path, 读集假红, 探针收窄, data_dir 前缀, global-open-probe-pollution
**Refs:** memory-bank/issues/26-11-12-0318-test-testing-parallel-flaky.html

### 2026-11-12 实证: test_read_side_view_contract_table[1m] 偶发假红

- **触发**: `commands run test.quick` / `test.full`(`-n 8` 并行, ship.commit 提交闸门内同款)五轮中偶红一次; 单文件隔离重跑恒绿 —— 与 [inproc-server-conn-abort.md](inproc-server-conn-abort.md) 同轮冒头(该件闪 qb_capture, 本条闪 traffic [1m], 两类机制不同)。
- **现象**: `tests/test_traffic_sample_store.py::test_read_side_view_contract_table[1m]` 在五轮 `-n 8` 全量中偶红一次, 单文件隔离重跑绿; 用例自身逻辑全部由冻结时钟 `frozen` 派生, 静态核查内部确定 —— 非确定通道只剩探针。
- **机制**: `tests/traffic_sample_support.py::_v4_open_paths`(取证 2026-11-12, 符号 `def _v4_open_paths`, grep `_v4_open_paths`)原实现 patch 进程级 `builtins.open`, 只按「路径含 `qb-traffic-v4/`」收录、不区分 data_dir; 同 worker 前序测试遗留的守护线程打开**它自己 tmp_path** 下的 qb-traffic-v4 文件(路径同样含该子串)即污染 `opened` 读集, 断言 `got_days == exp_days` 假红。
- **判别**: 用例断言面「日期集合不相等」而非 ConnectionError/Timeout; 用例自身时间参数冻结后内部确定; 探针 patch 面是进程级 —— 三件齐即本族, 别与 inproc-server-conn-abort(10053)/端口 TOCTOU(ConnectionRefused)混淆。
- **处置**: 收录判据加目标根目录前缀(本例 `data_dir`): `prefix = os.path.join(os.fspath(data_dir), "").replace("\\", "/")`, 被比对路径同样正斜杠归一后 `startswith(prefix)`; 守阵 `test_v4_open_paths_probe_scoped_to_data_dir` 双向红验。**不是放宽断言** —— 端点只可能打开自家 data_dir, 收窄只剔除物理上不可能属于被测行为的记录。
- **同族排查锚**: 仓库内其它进程级 patch 探针(如 sidefx 台账、`counting_open` 形态)若未来冒「并行偶红 + 单跑绿 + 断言集合面不等」, 先查收录判据是否含目标根收窄, 再查时序族。
