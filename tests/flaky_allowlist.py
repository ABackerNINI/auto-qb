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
(tests 裸 sleep 27 处/15 文件 · e2e waitForTimeout 91 处/20 文件 · src 裸取时 161 处/43 文件 ·
 bind 位固定端口 0 处), 与守阵扫描逐条对得上。
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
    # S3 hr 域清理: feeder 协作点改事件/wait_until 或注入假钟后删除
    "tests/test_hr_runtime_feeder.py":
        {
            "time.sleep(0.02)": 1,
            "time.sleep(0.1)  # 让它真的睡进去": 1,
            "time.sleep(0.2)  # 让它真的睡进 wait()": 1
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
    # S3 清理: qbmanager 任务时序真睡改注入假钟推进后删除
    "tests/test_qbmanager_tasks.py":
        {
            "time.sleep(0.15)": 2,
            "time.sleep(0.8)": 1,
            "time.sleep(0.9)": 1,
            "time.sleep(1.5)  # 兜底: 第 3 次没来时不挂死": 1
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
    # S2 core 域提交: 组件构造期注入 clock 后删除(1 处)
    "src/auto_qb/core/modules/fuse_mod.py": {
        "now = time.time()": 1
    },
    # S2 core 域提交: 组件构造期注入 clock 后删除(6 处)
    "src/auto_qb/core/modules/ops_mod.py":
        {
            "\"ts\": time.time(),": 1,
            "elapsed=time.time() - submitted_at,": 1,
            "elapsed_now = time.time() - submitted_at  # 真实等待时长(日志用; 须在宽限重置前取)": 1,
            "submitted_at = time.time()": 2,
            "submitted_at = time.time()  # 校验启动宽限窗口起点(recheck 发送成功时刻)": 1
        },
    # S2 core 域提交: 组件构造期注入 clock 后删除(12 处)
    "src/auto_qb/core/modules/ops_skip.py":
        {
            "deadline = time.monotonic() + (budget_ms / 1000.0)": 1,
            "deadline = time.time() + SKIP_DRIVE_TIMEOUT": 1,
            "if stepped >= budget_calls or time.monotonic() >= deadline:": 1,
            "job.next_run = time.time()": 5,
            "job.next_run = time.time() + (_SKIP_BACKOFF_MS[job.attempts] / 1000.0)": 1,
            "now = time.time()": 3
        },
    # S2 core 域提交: 组件构造期注入 clock 后删除(20 处)
    "src/auto_qb/core/modules/relocate_exec.py":
        {
            "\"started\": time.monotonic(),":
                1,
            "armed = replace(job, phase=ru.PHASE_ARMED, armed_at=time.time(), reason=\"\", attempts=0)":
                1,
            "elapsed = time.time() - float(job.armed_at or job.updated_at or time.time())":
                2,
            "heartbeat_age = max(0.0, time.time() - float(hb)) if hb else float(\"inf\")":
                1,
            "if rebuild_ts is not None and time.monotonic() - float(rebuild_ts) < ru.REBUILD_BACKOFF:":
                1,
            "if time.time() - float(rt.get(\"finalize_ts\") or time.time()) > float(":
                2,
            "now = time.monotonic()":
                3,
            "relocate_journal.write_journal(self._data_dir(), job.job_id, {\"phase\": ru.PHASE_ARMED, \"ts\": time.time()})":
                2,
            "relocate_journal.write_journal(self._data_dir(), job.job_id, {\"phase\": ru.PHASE_DONE, \"ts\": time.time()})":
                2,
            "relocate_journal.write_journal(self._data_dir(), job_id, {\"phase\": ru.PHASE_CANCELLED, \"ts\": time.time()})":
                1,
            "rt[\"finalize_ts\"] = time.time()":
                1,
            "rt[\"rebuild_ts\"] = time.monotonic()":
                1,
            "rt[\"started\"] = time.monotonic()":
                1,
            "stamp = time.time()  # 设置位置发起时刻: created_at 与首笔 updated_at 同一窗口, 不取两次":
                1
        },
    # S2 core 域提交: 组件构造期注入 clock 后删除(1 处)
    "src/auto_qb/core/modules/relocate_lifecycle.py": {
        "now = time.monotonic()": 1
    },
    # S2 core 域提交: 组件构造期注入 clock 后删除(3 处)
    "src/auto_qb/core/modules/relocate_mod.py":
        {
            "\"at\": int(time.time()),": 1,
            "\"started\": time.monotonic(),": 1,
            "job = replace(job, updated_at=time.time())": 1
        },
    # S2 core 域提交: 组件构造期注入 clock 后删除(10 处)
    "src/auto_qb/core/modules/relocate_probe.py":
        {
            "deadline = time.monotonic() + PROBE_CLEANUP_TIMEOUT_S": 1,
            "evidence[\"elapsed_s\"] = round(time.monotonic() - started, 3)": 1,
            "if time.monotonic() >= deadline:": 2,
            "read_verdict = _read_progress_poll(api, probe_hash, time.monotonic() + PROBE_READ_TIMEOUT_S, evidence)": 1,
            "started = time.monotonic()": 1,
            "time.monotonic() + PROBE_WRITE_TIMEOUT_S": 1,
            "tor = _await_probe_torrent(api, time.monotonic() + PROBE_READ_TIMEOUT_S, evidence)": 1,
            "while time.monotonic() < deadline:": 2
        },
    # S2 core 域提交: 组件构造期注入 clock 后删除(2 处)
    "src/auto_qb/core/modules/rules_mod.py":
        {
            "now = time.time()": 1,
            "self._ctx.task_queue.add_task(task, now=time.time() + task.retry_delay, keep_progress=True)": 1
        },
    # S2 core 域提交: 组件构造期注入 clock 后删除(1 处)
    "src/auto_qb/core/modules/speed_curve_mod.py": {
        "now = time.time()": 1
    },
    # S2 core 域提交: 组件构造期注入 clock 后删除(6 处)
    "src/auto_qb/core/modules/traffic_sample_mod.py":
        {
            "elapsed = time.time() - t0": 1,
            "now = time.time()": 3,
            "self._agg_flush_all(time.time())": 1,
            "t0 = time.time()": 1
        },
    # S2 core 域提交: 组件构造期注入 clock 后删除(1 处)
    "src/auto_qb/core/modules/traffic_snapshot_mod.py": {
        "view[\"ts\"] = time.time()": 1
    },
    # S2 core 域提交: 组件构造期注入 clock 后删除(17 处)
    "src/auto_qb/core/qbmanager.py":
        {
            "_backoff = time.time() + main_tick": 1,
            "_t_line = time.time() if (cmd_changed_state and not dry_run) else 0.0": 1,
            "deadline = time.time() + timeout": 1,
            "next_sync_at = time.time() + TRUTH_RETRY_S": 1,
            "next_sync_at = time.time() + sync_interval": 3,
            "next_tick_at = time.time() + main_tick": 3,
            "now = time.monotonic()": 1,
            "now = time.time()": 2,
            "remaining = deadline - time.time()": 1,
            "self.ctx.state.maybe_flush(time.time(), self.config.state_save_interval)": 1,
            "self.ctx.state.next_flush_at = time.time() + max(self.config.state_save_interval, 0.0)": 1,
            "wait_for = max(0.0, wake_at - time.time())": 1
        },
    # S2 core 域提交: 组件构造期注入 clock 后删除(6 处)
    "src/auto_qb/core/taskqueue.py":
        {
            "now = time.time() if now is None else now": 2,
            "return None if ts is None else max(0.0, time.monotonic() - ts)": 1,
            "self._active_checks[task.hash] = time.monotonic()": 1,
            "self.created_at = time.time()": 1,
            "self.uid = f\"{kind}:{name}:{hash}:{time.monotonic_ns()}\"": 1
        },
    # S2 core 域提交: 组件构造期注入 clock 后删除(1 处)
    "src/auto_qb/core/traffic_grid.py": {
        "return build_grid(window, time.time(), sample_interval)": 1
    },
    # S2 core 域提交: 组件构造期注入 clock 后删除(2 处)
    "src/auto_qb/core/traffic_limits.py": {
        "now = time.monotonic()": 2
    },
    # S2 core 域提交: 组件构造期注入 clock 后删除(1 处)
    "src/auto_qb/core/traffic_store.py": {
        "now = time.monotonic()": 1
    },
    # S2 hr 域提交: 与 runtime.sleeper 等待注入口径对齐后删除(1 处)
    "src/auto_qb/hr/channel.py":
        {
            "return 0.0 if not self.last_contact_ts else max(0.0, time.time() - self.last_contact_ts)": 1
        },
    # S2 hr 域提交: 与 runtime.sleeper 等待注入口径对齐后删除(2 处)
    "src/auto_qb/hr/queue.py":
        {
            "deadline = time.monotonic() + max(0.0, timeout)": 1,
            "left = deadline - time.monotonic()": 1
        },
    # S2 hr 域提交: 与 runtime.sleeper 等待注入口径对齐后删除(1 处)
    "src/auto_qb/hr/ratelimit.py": {
        "return time.time()": 1
    },
    # S2 hr 域提交: 与 runtime.sleeper 等待注入口径对齐后删除(6 处)
    "src/auto_qb/hr/report.py":
        {
            "data.empty_confirmed_at = time.time()": 1,
            "elapsed = time.time() - started": 1,
            "f\"放行={len(view.verified)} 最近健康波={ago_text(view.healthy_ts, time.time())} 通道={channel}\",": 1,
            "now = time.time()": 1,
            "started = time.time()": 1,
            "status = session.commit(time.time())": 1
        },
    # S2 hr 域提交: 与 runtime.sleeper 等待注入口径对齐后删除(2 处)
    "src/auto_qb/hr/runtime.py":
        {
            "deadline = time.monotonic() + max(0.0, seconds)": 1,
            "remain = deadline - time.monotonic()": 1
        },
    # S2 其余叶子提交: 叶子函数走 clock 单点或加参注入后删除(1 处)
    "src/auto_qb/infra/alias_fs.py": {
        "probed_at=time.time(),": 1
    },
    # S2 其余叶子提交: 叶子函数走 clock 单点或加参注入后删除(2 处)
    "src/auto_qb/infra/port_owner.py":
        {
            "deadline = time.monotonic() + budget": 1,
            "return deadline - time.monotonic()": 1
        },
    # S2 其余叶子提交: 叶子函数走 clock 单点或加参注入后删除(3 处)
    "src/auto_qb/infra/relocate_journal.py":
        {
            "_write_json(path, {\"pid\": os.getpid(), \"ts\": time.time()})": 1,
            "body.setdefault(\"ts\", time.time())": 1,
            "return max(0.0, (now if now is not None else time.time()) - float(ts))": 1
        },
    # S2 其余叶子提交: 叶子函数走 clock 单点或加参注入后删除(1 处)
    "src/auto_qb/infra/store_recovery.py": {
        "target = f\"{p}.bad-{int(time.time())}\"": 1
    },
    # S2 其余叶子提交: 叶子函数走 clock 单点或加参注入后删除(2 处)
    "src/auto_qb/infra/utils.py":
        {
            "deadline = time.monotonic() + _EXPLORER_FG_TIMEOUT": 1,
            "if time.monotonic() >= deadline:": 1
        },
    # S2 其余叶子提交: 叶子函数走 clock 单点或加参注入后删除(2 处)
    "src/auto_qb/rules/actions/full_checking.py":
        {
            "if time.time() - start > GROUP_CHECK_WAIT_LIMIT:": 1,
            "start = time.time()": 1
        },
    # S2 其余叶子提交: 叶子函数走 clock 单点或加参注入后删除(1 处)
    "src/auto_qb/rules/actions/transfer.py": {
        "now = time.time()": 1
    },
    # S2 其余叶子提交: 叶子函数走 clock 单点或加参注入后删除(1 处)
    "src/auto_qb/rules/base.py": {
        "now = time.time()": 1
    },
    # S2 其余叶子提交: 叶子函数走 clock 单点或加参注入后删除(1 处)
    "src/auto_qb/torrents/record.py": {
        "now=time.time(),": 1
    },
    # S2 其余叶子提交: 叶子函数走 clock 单点或加参注入后删除(8 处)
    "src/auto_qb/torrents/store.py":
        {
            "if self._expect_retries >= _EXPECT_MAX_RETRIES or time.time() >= self._expect_deadline:": 1,
            "now = time.monotonic()": 2,
            "now = time.time()": 2,
            "now_ts = time.time()  # state_since 的同一时刻基准(纯展示用, 不参与判定)": 1,
            "return None if ts is None else max(0.0, time.time() - ts)": 1,
            "self._expect_due_at = time.time() + _EXPECT_RETRY_INTERVAL": 1
        },
    # S2 其余叶子提交: 叶子函数走 clock 单点或加参注入后删除(2 处)
    "src/auto_qb/tray/app.py":
        {
            "self._started = time.time()": 1,
            "self.card_uptime.configure(text=self._format_uptime(time.time() - self._started))": 1
        },
    # S2 webui/traffic 域提交: 构造期注入 clock 后删除(1 处)
    "src/auto_qb/webui/commands_common.py": {
        "\"exec_ms\": round((time.time() - start_ts) * 1000, 1),": 1
    },
    # S2 webui/traffic 域提交: 构造期注入 clock 后删除(1 处)
    "src/auto_qb/webui/commands_torrents.py": {
        "t0 = time.time()": 1
    },
    # S2 webui/traffic 域提交: 构造期注入 clock 后删除(3 处)
    "src/auto_qb/webui/relocate_chain.py":
        {
            "\"probed_at\": time.time(),": 1,
            "now = time.time()": 1,
            "self._data[key] = (time.time(), value)": 1
        },
    # S2 webui/traffic 域提交: 构造期注入 clock 后删除(2 处)
    "src/auto_qb/webui/runtime.py":
        {
            "self.group_view_ver: int = int(time.time())": 1,
            "self.search_rev: int = int(time.time() * 1000)": 1
        },
    # S2 webui/traffic 域提交: 构造期注入 clock 后删除(7 处)
    "src/auto_qb/webui/runtime_commands.py":
        {
            "\"ts\": time.time(),": 1,
            "body[\"_queued_ts\"] = time.time()  # 埋点: 投递时刻, 回执据此拆出排队耗时": 1,
            "ms = round((time.time() - t0) * 1000, 1)": 1,
            "now = time.time()": 3,
            "start_ts = time.time()  # 出队即开始, 用于拆 wait_ms / exec_ms": 1
        },
    # S2 webui/traffic 域提交: 构造期注入 clock 后删除(6 处)
    "src/auto_qb/webui/runtime_stream.py":
        {
            "ev = {\"type\": etype, \"payload\": payload, \"ts\": time.time()}":
                1,
            "now = time.time()":
                1,
            "return (time.time() - self.last_seen) < WEB_VIEW_TTL":
                1,
            "return issued_at is not None and (time.time() - issued_at) <= EVENT_TICKET_TTL_S":
                1,
            "self.err_log_ring.append({\"seq\": self.err_log_seq, \"ts\": time.time(), \"level\": level, \"msg\": msg})":
                1,
            "self.last_seen = time.time()":
                1
        },
    # S2 webui/traffic 域提交: 构造期注入 clock 后删除(2 处)
    "src/auto_qb/webui/server/context.py": {
        "now = time.time()": 1,
        "self._cache[full_key] = (time.time(), value)": 1
    },
    # S2 webui/traffic 域提交: 构造期注入 clock 后删除(3 处)
    "src/auto_qb/webui/server/lifecycle.py":
        {
            "deadline = time.monotonic() + timeout": 1,
            "if time.monotonic() >= deadline:": 1,
            "now = time.monotonic()": 1
        },
    # S2 webui/traffic 域提交: 构造期注入 clock 后删除(4 处)
    "src/auto_qb/webui/server/routes/hr.py": {
        "\"now\": time.time(),": 2,
        "now = time.time()": 2
    },
    # S2 webui/traffic 域提交: 构造期注入 clock 后删除(5 处)
    "src/auto_qb/webui/server/traffic_qb.py":
        {
            "_SERVER_STARTED_AT = time.time()": 1,
            "grid = tg.build_month_grid(epochs, time.time()) if epochs else self._grid(window)": 2,
            "return tg.build_grid(window, time.time(), sample)": 1,
            "return tg.build_month_grid((), time.time())": 1
        },
    # S2 webui/traffic 域提交: 构造期注入 clock 后删除(1 处)
    "src/auto_qb/webui/views.py": {
        "now = time.time()": 1
    },
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
