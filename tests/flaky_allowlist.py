"""flaky 守阵白名单单点: 存量违例集中登记(flaky 治理计划 26-11-05-0118 S1)

四类守阵(tests/test_flaky_timing_guards.py)的存量违例全部收在这里 —— 守阵上线即全绿,
S2/S3/S4 清理时逐条删除收紧。**新增违例不经本表直接红**; 本表只许删除, 新增条目须带理由。

契约(机器可清点, 守阵两侧对账):
- 键 = 仓库相对路径(POSIX 形式), 值 = {违例行文本(strip 后全等): 允许条数};
- 新增侧: 扫描出的违例行不在表内 / 条数超出 -> 守阵红;
- 失效侧: 表内行在对应文件已扫不到 / 条数下降 -> 守阵红(清理后必须回来删条目, 白名单只减不涨);
- 匹配口径: strip 后**全行全等**含行内注释 —— 改注释也判失效+新增, 强制同步本表;
  同文件同文本多处出现按条数记(清一处条数即降, 对账当场暴露)。
  行文本是**数据**(逐字镜像被扫文件原行, 含 e2e 注释里的既有符号) —— 非 ASCII 处按
  code-style 的数据例外保留, 不算代码用语。

各文件条目上方注释 = 该文件存量的清理归属与理由; 条目数 = 实测存量
(tests 裸 sleep **已清零**[S1 实测 27 处/15 文件 -> T3b 清 2 文件 8 处 -> S3 收口清 12 文件 18 处,
仅剩 clock.py 合法等待单点本体 1 处带理由保留] · e2e waitForTimeout **已全部清零**
[S1 实测 91 处/20 文件 -> S4 前半 2026-11-05 清 move-dialog-fit/dt-live-update/perf/
window-invalidation/column-prefs 5 文件 50 处 -> S4 后半 2026-11-05 清其余 15 文件 41 处,
替换为 expect 系/expect.poll/Node 侧观察窗后条目删净, S4 判据①达成] · src 裸取时 **已全部清零**
[core 90 处/16 文件、hr 12 处/5 文件、webui/traffic 35 处/11 文件、其余叶子 24 处/11 文件
已随 S2 各域提交清零, 本表 src 组只剩完成注释]
· bind 位固定端口 0 处), 与守阵扫描逐条对得上。
"""

# ---------- ALLOW_SLEEP_TESTS: tests/ 裸 time.sleep 调用(AST 实调用, patch 字符串不算) ----------
ALLOW_SLEEP_TESTS: dict[str, dict[str, int]] = {
    # wait_until 轮询节拍的睡眠 —— 收编后的合法等待单点本体(真睡的唯一合法位), 不清零
    "tests/clock.py": {
        "time.sleep(interval)": 1
    },
    # S3 收口(2026-11-05): 其余 12 文件 18 处已全部清零, 条目删净 —— 线程协作点改 Event/
    # wait_until(判据①); 时间语义(TTL/覆盖戳)改注入假钟(判据②); 有意真窗(忙等观察窗/
    # h11 分片时序)改 Event.wait 真窗 + 注明判据③后不再属裸 sleep 实调用。
}

# ---------- ALLOW_TIME_SRC: src/ 裸 time.time()/time.monotonic[_ns]() 直调(clock.py 本体路径豁免, 不进本表) ----------
ALLOW_TIME_SRC: dict[str, dict[str, int]] = {
    # S2 core 域提交已完成(2026-11-05): 上表 16 文件 90 处已按 D8 构造期注入 clock 清零, 条目删净
    # S2 hr 域提交已完成(2026-11-05): 5 文件 12 处已按 D8 清零, 条目删净 —— 等待预算
    # (runtime.sleeper / queue.wait)走 SYSTEM_CLOCK.monotonic 单点保真实单调钟(与既有
    # sleeper/now_fn 可调用注入口径对齐, 阻塞预算不入假钟); 挂钟叶子走 SYSTEM_CLOCK.now() 单点。
    # S2 webui/traffic 域提交已完成(2026-11-05): 11 文件 35 处已按 D8 清零, 条目删净 ——
    # WebUIRuntime/ChainCache/RoCache 构造期注入 clock(WebUIRuntime 经 QbManager 装配链透传),
    # 路由/处理器与请求期栅格等叶子走 SYSTEM_CLOCK.now() 单点, lifecycle 等待预算走 monotonic 单点。
    # S2 其余叶子提交已完成(2026-11-05): 11 文件 24 处已按 D8 清零, 条目删净 —— src/ 裸取时归零
    # (除 clock.py 单点本体豁免), S2 收口。TorrentStore 构造期注入 clock(expect 调度与 state_since
    # 挂钟侧走注入钟 now, own_writes TTL 单调侧走注入钟 monotonic); 其余 10 文件叶子走
    # SYSTEM_CLOCK 单点: journal/probe/留证戳与 reannounce 限频/HR 锚点/托盘 uptime 挂钟语义走
    # now(), port_owner/utils/full_checking 等待预算与 base 同因节流单调语义走 monotonic()。
}

# ---------- ALLOW_WAIT_TIMEOUT_E2E: e2e/*.mjs 的 page.waitForTimeout(...) 固定睡等(含注释里的历史提及, 行文本全等口径) ----------
ALLOW_WAIT_TIMEOUT_E2E: dict[str, dict[str, int]] = {
    # S4 后半收口(2026-11-05): 15 文件 41 处已全部清零, 条目删净 —— 机制去向四类:
    # DOM 条件 -> expect(locator) 自动轮询(时长即断言的挂同值 timeout); 赌完成 -> expect.poll
    # (稳态类三拍口径, 拍距 >= 300ms 保静默跨度 >= 350ms); 负条件观察窗(「不该发生的」poll 首拍
    # 即中会提前通过)与页内采样器量具窗 -> Node 侧 setTimeout observeWindow/measureWindow
    # (时长逐字保留并注释); 合帧收层危险窗 -> rAF 逐帧采样恒真断言(move-dialog-fit 同款)。
}

# ---------- ALLOW_BIND_PORT: bind 调用位的字面固定端口(配置值位不拦) ----------
# 实测存量 0: tests/ 全部 bind 已走 port=0 OS 分配(_test_ports 单点 + 26-11-03-0316 治理)。
# 表语义与上同: 文件 -> {行文本: 条数}; 有新固定口 bind 位即红, 进表须带理由。
ALLOW_BIND_PORT: dict[str, dict[str, int]] = {}
