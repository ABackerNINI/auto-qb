# hold_run 经 bind(0) 取基址 = 站上 OS 分配前沿 —— 连号后位正是并行邻居的下一个落点

> 摘要: 连号段占位若经 `bind(0)` 取基址, 基址恰落在 OS 动态端口**分配前沿**上(探针实证: 连续 20 次 bind(0) 得 55011→55030 顺沿连号), 随后要绑的 base+1..+N 正是前沿即将发给其他并行 worker 的端口 —— `-n 8` 全量下毫秒级建段窗口被抢一位即 WinError 10048, 整段丢弃换基址也还是撞同一拥挤前沿, RETRIES=3 三连败(issue 26-11-20-0320, 两度偶红)。修法: 基址改**私用段随机数**(21000-31000, 两个平台默认动态段 Windows 49152-65535 / Linux 32768-60999 之下, 邻居 bind(0) 结构性够不着), 整段真绑自验+失败重画结构保留。判别要点: **10048(占用)≠ 10013(排除段)** —— 排除段假设(Hyper-V 预留)与事发留痕不符时, 先用探针验分配行为再定根因, 别把「环境性」当结论。
> 触发: bind(0), ephemeral, 分配前沿, 动态端口, 连号段, hold_run, 私用段, WinError 10048, 并行抢口, -n 8, 全量偶红, 排除段误判, ip_local_port_range

**Refs:** [issue 26-11-20-0320](../../issues/26-11-20-0320-test-hr-discovery-port-bind-flake.html)

## 本篇只回答

hold_run/连号段类 flake 报 10048 时, 怎么在 1 分钟内分辨「前沿邻接」与「排除段/残留占用」, 以及为什么修法是换抽取段而不是加重试。

### bind(0) 前沿邻接: 取号方式本身就是触发面

- **触发**: 连号段占位单点 `tests/unit/_test_ports.py::hold_run(n)` 旧实现先 `bind(0)` 取基址、再逐位真绑 base+1..+N。并行(全量 `-n 8`; 本机 test.quick 次轮 sidefx 副作用台账总计 11278 条, 2026-11-20 汇总; 台账以端口绑定为主 —— 直接占比证据来自隔离形态: 40 条中 BIND 占 38)下, 其他 worker 的 `bind(0)` 正沿前沿顺序取号, 与本 worker 的建段窗口赛跑。
- **判别**:
  - 事发码 **10048(端口被占)** —— 前沿邻接的指纹; **10013(权限拒绝)** 才是排除段(`netsh interface ipv4 show excludedportrange protocol=tcp`)的指纹。两码都可能出现时按实际报错端口分段归因。
  - 探针(30 秒): python 连续 20 次 `bind(0)+close`, 端口严格递增连号 ⇒ 前沿分配实锤(Windows 实测如此; Linux 推定同样顺沿, 待 testbed 实测)。持住刚取到的端口再取号, 下一个号绕开持住位继续递进。
  - 「隔离恒绿、全量偶红、重跑即绿」三件套齐 ⇒ 并行竞争面, 不是开机排除段(那个隔离也会红)。
- **处置**:
  - 基址**脱离动态段**: 在私用段(基址常量 `HOLD_RUN_PORT_LO/HI` = 21000-31000, 单点 `_test_ports.py`)随机取基址。邻居的 bind(0) 够不着私用段, 触发面结构性消除, 而非压窗口。
  - 整段逐位真绑+失败整段丢弃重画的结构**保留不变**(它兜住私用段内的残余碰撞: 真实服务端口 27017 等/排除段碎块/其他 worker 的 hold_run 段); RETRIES 与即时重画也不变 —— 换段之后剩余失败源都是「重画换个随机位即可解」的稀疏碰撞, sleep/抬次数是在给已消除的风险买保险。
  - 单端口取号(`free_port`)的 bind(0) **不必**同改: 无连号要求, 回绑自验已够, 且它的失败模式是「取号后被抢」而非「建段被邻居截胡」。
  - 平台差: 若某机器手动改窄过动态段(`netsh int ipv4 show dynamicport tcp` / `/proc/sys/net/ipv4/ip_local_port_range`)使之下探到私用段, 退化行为=回到概率性竞争, 不会更糟 —— Linux 侧以 `test.linux` 实测 testbed 的段下界为准。
- **守阵**: `tests/unit/test_free_port.py::test_hold_run_returns_bindable_run`(新增钉面: 基址必须落私用段, 回潮 bind(0) 即红)、
  `::test_hold_run_discards_run_whose_offset_is_refused`(整段丢弃重画, 纯合成 socket, 尝试边界由 close 事件判定 —— 取号 socket 消失后不再能用 bind(0) 定界)、
  `::test_hold_run_width_guard_rejects_oversized_count`(count 超段宽在 socket 创建前 RuntimeError, 零网络)、
  `::test_hold_run_redraws_with_new_random_base`(重画必须重新抽取随机基址 —— randint 提出循环的坏实现判红, 正钉本档「每轮换新随机基址」承重面)、
  `::test_hold_run_exhausted_retries_raises`(RETRIES 轮恒拒全败 ⇒ RuntimeError 且轮数 == RETRIES, 与 free_port 耗尽钉面对称)。
- **复发**: 0
- **同族**: [consecutive-port-run.md](consecutive-port-run.md) —— 上半场: 整段真绑自验的由来(10013 排除段形态, issue 26-11-06-0330); 本篇是下半场: 整段自验救不了「基址站在前沿上」的 10048 形态, 两坑叠加才是 hold_run 的完整故事。
