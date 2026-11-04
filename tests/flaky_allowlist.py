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
(tests 裸 sleep 19 处/13 文件[S1 实测 27 处/15 文件, S3 优先域已清 2 文件 8 处] · e2e waitForTimeout 91 处/20 文件 · src 裸取时 **已全部清零**
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
    # S3 hr 域清理: discovery 轮询真睡改事件/wait_until 后删除
    "tests/test_hr_discovery.py": {
        "time.sleep(0.005)": 1,
        "time.sleep(0.01)": 1,
        "time.sleep(0.05)": 1
    },
    # S3 hr 域清理: 线程协作点改事件/wait_until 后删除
    "tests/test_hr_fetcher_channel.py": {
        "time.sleep(0.005)": 1
    },
    # S3 hr 域清理: 线程协作点改事件/wait_until 后删除
    "tests/test_hr_runtime_lifecycle.py": {
        "time.sleep(0.02)": 1
    },
    # S3 hr 域清理: 服务线程协作点改事件/wait_until 后删除
    "tests/test_hr_server.py": {
        "time.sleep(0.05)": 2
    },
    # S3 hr 域清理: worker 等待改 wait_until(长预算真睡兜底一并评估)后删除
    "tests/test_hr_worker_lifecycle.py": {
        "time.sleep(0.4)": 1
    },
    # S3 清理: filelock 竞态窗口改事件同步后删除
    "tests/test_locking.py": {
        "time.sleep(0.05)": 1
    },
    # S3 清理: 通知派发线程改 wait_until 后删除
    "tests/test_notify.py": {
        "time.sleep(0.05)": 1
    },
    # S3 清理: 同秒覆盖语义改注入假钟后删除
    "tests/test_relocate_probe_cache.py": {
        "time.sleep(0.01)  # 保证 at 有机会前进(同秒也算覆盖, 这里只验证字段换新)": 1
    },
    # S3 清理: tray 线程协作改 wait_until 后删除
    "tests/test_tray.py": {
        "time.sleep(0.01)": 1
    },
    # S3 清理: webui 轮询真睡改 wait_until/事件后删除
    "tests/test_ui.py": {
        "time.sleep(0.01)": 2,
        "time.sleep(0.15)": 1,
        "time.sleep(0.2)": 1
    },
    # S3 清理: 会话过期时序改注入假钟后删除
    "tests/test_web_auth.py": {
        "time.sleep(0.15)": 1
    },
    # S3 清理: 迁移链轮询真睡改 wait_until 后删除
    "tests/test_webui_relocate_chain.py": {
        "time.sleep(0.03)": 1
    },
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
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(1 处)
    "e2e/add-options-recent-order.spec.mjs": {
        "await page.waitForTimeout(300);  // > 40ms 合帧窗, 定时器该响的都响完了": 1
    },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(6 处)
    "e2e/column-prefs.spec.mjs":
        {
            "*  · 装饰性 waitForTimeout(400/600/500/300/200) 全部换成 expect / expect.poll 显式等待:": 1,
            "* 末尾旧 waitForTimeout(300) 换成 poll 等固化落地 —— 固化页 colW.group 非空是后续断言的前提。": 1,
            "* 菜单里切换某列显隐(真实手势), 等勾选态翻转(旧 waitForTimeout(400) 的显式化)再 Escape 收起": 1,
            "/* 旧 waitForTimeout(500) → poll 等 B 采纳 A 的改动。旧条件 h.group.length >= 2 被播种恒真,": 1,
            "/* 旧 waitForTimeout(600)「等 storage 事件把 B 的改动推给 A」→ poll 等采纳。 */": 1,
            "/* 旧 waitForTimeout(600)「等 storage 事件把改动推给标签 2」→ poll 显式等标签 2 采纳。 */": 1
        },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(1 处)
    "e2e/drawer-bridge-stub.spec.mjs": {
        "await page.waitForTimeout(800);": 1
    },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(2 处)
    "e2e/drawer-content-perf.spec.mjs":
        {
            "await page.waitForTimeout(500);": 1,
            "await page.waitForTimeout(500); // 交互 + 窗口重算余波落进观察窗": 1
        },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(1 处)
    "e2e/drawer-fileprio-optimistic.spec.mjs": {
        "await page.waitForTimeout(400); // 等旧路径重拉落定, 再量候选组": 1
    },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(4 处)
    "e2e/drawer-merge.spec.mjs": {
        "await page.waitForTimeout(300);": 4
    },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(1 处)
    "e2e/drawer-switch-no-flash.spec.mjs": {
        "await page.waitForTimeout(1200);": 1
    },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(12 处)
    "e2e/dt-live-update.spec.mjs":
        {
            "await page.waitForTimeout(120);": 1,
            "await page.waitForTimeout(1600); // 覆盖换帧后的全部余波": 1,
            "await page.waitForTimeout(30);": 1,
            "await page.waitForTimeout(300); // 数据回路窗口内持续采样": 1,
            "await page.waitForTimeout(40);": 1,
            "await page.waitForTimeout(400);": 1,
            "await page.waitForTimeout(400);  // 窗口重算(合帧 rAF + 重渲)落定": 1,
            "await page.waitForTimeout(400); // 首渲 settle(千行挂载自身的成本不计入判据窗口)": 1,
            "await page.waitForTimeout(500); // 交互 + patch 全部余波落进观察窗": 1,
            "await page.waitForTimeout(80); // 攒基线采样": 1,
            "await page.waitForTimeout(80); // 等一帧渲染(换代重挂若有, 此处即暴露)": 1,
            "await page.waitForTimeout(800); // 覆盖 POST→回执→补拉→换帧全程": 1
        },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(3 处)
    "e2e/dt-table-face-bg.spec.mjs":
        {
            "await page.waitForTimeout(150);": 2,
            "await page.waitForTimeout(500); /* 等 transition: background 走完(旧值/中间值不算) */": 1
        },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(1 处)
    "e2e/hr-history.spec.mjs": {
        "*  · 无保留 sleep: 旧块的 waitForTimeout(250/200/800) 全是等本地过滤/弹层渲染的装饰性等待,": 1
    },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(5 处)
    "e2e/hscroll-indicator.spec.mjs": {
        "await page.waitForTimeout(300);": 3,
        "await page.waitForTimeout(350);": 2
    },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(3 处)
    "e2e/kbd-scroll-band.spec.mjs":
        {
            "await page.waitForTimeout(250); // 等滚动 + 窗口化重渲染落定(本视图非窗口化, 只等滚动)": 1,
            "await page.waitForTimeout(50);": 1,
            "await page.waitForTimeout(800); // 面板长到自然高后可见带才落定": 1
        },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(3 处)
    "e2e/main-table-pinned-selected.spec.mjs":
        {
            "await page.waitForTimeout(300);": 2,
            "await page.waitForTimeout(400);": 1
        },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(6 处)
    "e2e/menus.spec.mjs":
        {
            "await page.waitForTimeout(1200); // 观察窗: 越过点击 -> 投递的短窗": 1,
            "await page.waitForTimeout(450);": 1,
            "await page.waitForTimeout(500); // 观察窗: 确认没有第二条(旧 W3 同款\"恰好 1 条\"语义)": 1,
            "await page.waitForTimeout(500); // 观察窗: 确认没有误发第二条(旧 1200ms 等回执同语义)": 1,
            "await page.waitForTimeout(600); // 旧 400ms 同款观察窗: 取消后不该有 POST": 1,
            "await page.waitForTimeout(700); // 观察窗: 越过点击 -> 投递的短窗": 1
        },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(16 处)
    "e2e/move-dialog-fit.spec.mjs":
        {
            "await page.waitForTimeout(1000);": 1,
            "await page.waitForTimeout(140);": 1,
            "await page.waitForTimeout(150);": 2,
            "await page.waitForTimeout(300);": 1,
            "await page.waitForTimeout(300);  // > 40ms 合帧窗, 定时器该响的都响完了": 1,
            "await page.waitForTimeout(350);": 1,
            "await page.waitForTimeout(400);": 3,
            "await page.waitForTimeout(450);": 2,
            "await page.waitForTimeout(450);  // 过渡 200ms + settle 240ms 全跑完": 1,
            "await page.waitForTimeout(450);  // 过渡 200ms + settle 重测 240ms": 1,
            "await page.waitForTimeout(700);": 2
        },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(1 处)
    "e2e/multiselect-shows.spec.mjs": {
        "await page.waitForTimeout(1500);": 1
    },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(6 处)
    "e2e/optimistic.spec.mjs":
        {
            "await page.waitForTimeout(1500);": 1,
            "await page.waitForTimeout(400); // 旧同值: 等 ver 去抖 + DOM 落地": 1,
            "await page.waitForTimeout(400); // 旧同值: 让记录器把瞬时起落采完再读": 1,
            "await page.waitForTimeout(6500);": 1,
            "await page.waitForTimeout(900); // 旧同值: 等首轮轮询/渲染尘埃落定再装采样器": 1,
            "await page.waitForTimeout(900); // 旧同值: 让记录器把组行 pending 起落采完": 1
        },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(9 处)
    "e2e/perf.spec.mjs":
        {
            "await page.waitForTimeout(400);": 5,
            "await page.waitForTimeout(600);": 1,
            "await page.waitForTimeout(600);  // 等 updated 量齐拍结束, 计数稳定": 1,
            "await page.waitForTimeout(600); // 抽屉 dock 挤压视口后主表窗口重测 settle": 1,
            "await page.waitForTimeout(80);": 1
        },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(3 处)
    "e2e/views.spec.mjs":
        {
            "*  · 装饰性 waitForTimeout(400/700/300/150…) 全部换成 expect 自动等待 / expect.poll;": 1,
            "await page.waitForTimeout(2000);": 1,
            "await page.waitForTimeout(300); /* 等列对齐规则注入 + 首帧布局稳定 */": 1
        },
    # S4 e2e 清理: 替换为 expect(locator).toHaveXxx() / expect.poll / toPass() 后删除(7 处)
    "e2e/window-invalidation.spec.mjs":
        {
            "await page.waitForTimeout(2000);": 1,
            "await page.waitForTimeout(2500); // 量齐轮 settle": 1,
            "await page.waitForTimeout(2500); // 首访量齐全量轮 settle(设计内一次; 3000 种子实测 ~5.4s 长任务在此窗内完成)": 1,
            "await page.waitForTimeout(500); // 全量渲染进行中就要读数(修复后窗口化即时, 修复前 3000 行 patch 中)": 1,
            "await page.waitForTimeout(600);": 1,
            "await page.waitForTimeout(600); // 收场 RO 余波落定(修复前 bump 在此窗内发生)": 1,
            "await page.waitForTimeout(800);": 1
        },
}

# ---------- ALLOW_BIND_PORT: bind 调用位的字面固定端口(配置值位不拦) ----------
# 实测存量 0: tests/ 全部 bind 已走 port=0 OS 分配(_test_ports 单点 + 26-11-03-0316 治理)。
# 表语义与上同: 文件 -> {行文本: 条数}; 有新固定口 bind 位即红, 进表须带理由。
ALLOW_BIND_PORT: dict[str, dict[str, int]] = {}
