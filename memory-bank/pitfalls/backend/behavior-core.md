# 行为细节 (易误判为 bug)

> 摘要: 后端一批"看着像 bug 其实是特性"的行为 —— 改之前先确认它是不是有意设计。
> 触发: 改规则, 改主循环, 改归组, 改缺文件扫描, 改限速, 改状态持久化, 改 web 服务生命周期

### 奇数限速保护 (`(limit/1024)%2==1` 跳过) 是特性不是 bug

- **触发**: 看到限速没被覆盖 / 写限速断言。
- **判别**: 奇数 KiB 被视为**用户手动设置** ⇒ 跳过。
- **处置**: 断言写"奇数不覆盖"; 测试数据用奇数(见 [high-risk-ops.md](high-risk-ops.md) 限速那条)。

### `interval` 归一化: `Task.interval <= 0` → 1s

- **触发**: 配任务 / 规则的 interval。
- **判别**: `Task.interval <= 0` 归一成 **1s**; 而**规则** interval 为 0 = **每轮执行**(两者不同)。
- **处置**: 别把规则语义套到 Task 上。

### `handled` 返回值: 最后一个动作 skip 时 `handled=False`, 但执行历史已记录

- **触发**: 读 `Rule.process` 返回值做判断。
- **判别**: 它返回 `not result.is_skipped`。
- **处置**: 设计如此, 不要"修"; 需要判断"有没有跑过"请看执行历史。

### 上传增量下限 0

- **触发**: 算上传增量。
- **判别**: `max(0, uploaded - baseline)` —— 种子重加后 uploaded 归零**不产生负增量**。
- **处置**: 别去掉 `max`。

### 代表种已分化: 缺文件扫描与跳检参考的选取口径**不同**

- **触发**: 改代表种选取。
- **判别**: 缺文件扫描代表种 `_valid_for_representative` = `is_complete or is_errored` 且非 checking
  (**errored 恰是缺文件第一现场**); 跳检参考候选 `_group_reference_candidates` 仍**只**从
  `is_complete 且非 checking` 选。
- **处置**: **别混** —— 统一成一个口径会破坏其中一侧。

### MISSING 组豁免 mixed 冲突是**有意设计**

- **触发**: 改组冲突检测 / 缺文件标记。
- **判别**: 缺文件组被标记后用户重新下载是**合法补救**, 不该被"已完成与下载中并存"拦停(**multi-dl 不豁免**)。
  重校验发现文件缺失(`stalledUP→missingFiles`)也是缺文件扫描触发路径。
- **处置**: 保留豁免; 注意 **MISSING 标签无自动清除逻辑, 补齐后需手动摘**。

### tracker 匹配是"第一个命中"且统一为 hostname 精确匹配

- **触发**: 改站点匹配 / 导出模板。
- **判别**: 命中多个配置**打 ERROR 后仍用第一个**(不跳过种子); 导出模板 `find_missing_domains`
  仍用**包含匹配**(有意宽松)。
- **处置**: 两处口径**故意不同**, 别"统一"掉。

### `RuleContext.torrent` 的快照回退是合法语义

- **触发**: 看到种子已删除却还能读到字段。
- **判别**: 种子已从客户端删除时**回退删除前 `RuleContext.snapshot` 副本**, 供只读留档。
  需活种子的动作在 **config 白名单阶段**已被拒绝。
- **处置**: 别把这个回退当 bug 删掉。

### 每个动作的 dry-run 返回 success

- **触发**: 用 `--dry-run` 观察。
- **判别**: **别据 dry-run 日志判断真实执行结果** —— 它一律返回 success。
- **处置**: 要看真实结果就跑真实档(并注意它真的会作用到 qB)。

### 重启监听同一端口前必须确认旧监听器已 `close()`

- **触发**: 改 web 配置后重启服务。
- **判别**: uvicorn 的 `stop()` 只是**请求退出**(主循环每 0.1s 才读 `should_exit`), 毫秒级内重新 bind 必
  `Errno 10048`; 且**非主线程的 `SystemExit` 会被 `threading` 静默吞掉**, 日志里只看到一行不带时间戳的 uvicorn ERROR。
- **处置**: 现由 `WebServerHandle.stop()/wait()` + `_apply_web_config`(只在 enabled/host/port 变化时重启)处理。

### `state_file` 仅退出时落盘

- **触发**: 运行中 kill / 断电。
- **判别**: 运行中 kill -9 会丢执行历史 → **去重可能重放**。
- **处置**: **已知取舍**, 不是 bug; 需要更稳的持久化要先推翻这条设计。

### qB 断连期间错误日志静默是**有意节流**

- **触发**: 排查"为什么断连时没有日志"。
- **判别**: 仅"连接态→断开"转换记一次 ERROR, 恢复记一次 INFO; **非 `APIConnectionError` 照常记"主循环异常"**。
- **处置**: 别为"日志太少"去加日志 —— 那会刷屏; 要排查就看那两次转换记录。

### 配置热重载的两处"看着像 bug"的现状(**未改动**)

- **触发**: 读 `_diff_flat` / 热重载逻辑。
- **判别**: ①`_diff_flat` 的分支条件是"两侧都是纯 dict", 真实 Config 的 L0 段是 dataclass ⇒
  实际产出**整段单条变更**(级别判定仍正确, 只是**粒度粗**);
  ②`max_level` / `restart_required_paths` 当前**无生产调用**(Web 与 qbmanager 各自内联)。
- **处置**: ①属已知粒度问题; ②属**清理候选**。两者都不是缺陷, 改动前先确认影响面。

### 主循环节流必须经模块级 `_throttle(stop_event, main_tick)`

- **触发**: 改主循环节流 / 等待逻辑。
- **判别**: 正确实现是**非托管**(CLI, `stop_event=None`)走 `time.sleep`, **托管**(`--tray`)走 `Event.wait`。
  写成 `if stop_event is not None and stop_event.wait(...)` 会被 `and` **短路成完全不阻塞** ⇒
  主循环空转(**CPU 打满 + sync 请求放大数千倍**)。
- **处置**: 一律经 `_throttle`; ⚠ **托管模式会掩盖该 bug** ⇒ 回归测试必须用**非托管**模式。
  另: 首连失败重试循环里 `stop_event is None or stop_event.wait(...)` 是**有意语义**, 不要一并改。
