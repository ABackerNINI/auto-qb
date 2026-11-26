# S0a 真机面起服 + 0037 档案欠账补跑 · 工作明细节(26-11-27)

> 纯 md 工作记录(不走 kb.new, 不建 HTML)。任务: 还 26-11-18-0037 档案步 9/10 两项改约
> (Docker testbed e2e + 真机冒烟), 服务于计划 26-11-26-2333 §04 S0 行。分支
> feat/traffic-seam-hardening(纯本地, 无远端, 未跑 sync——按简报禁令)。
> 欠账口径出处: memory-bank/tasks/26-11-18-webui-traffic-stepwise.md 子任务状态表步 9/10
> (原文: 「改约: Docker testbed e2e(test.linux-env + test.linux-e2e)」「改约: 真机冒烟
> (dev.run -- config.yml --dry-run, qB 离线拒连; 启动面日志已验正常)」)。
> 注: 简报里给的档案(26-11-15-webui-traffic-root-revamp.md)不含步 9/10, 实际欠账在
> 26-11-18 档案——已按计划 §02/aside 两处指向的「26-11-18-0037 档案」执行。

## 结论速览

| 项 | 结果 |
|---|---|
| Docker testbed e2e(@fast) | 555 例 = **549 passed / 1 failed / 5 skipped**, playwright 内层 34.2m, 任务全程 2063.8s |
| 真机冒烟(测试实例 qB 36595) | 启动面正常: 流量模块初始化 / 无异常栈 / 无连接失败 ERROR(运行 12+ 分钟覆盖多个同步间隔); **未复现「qB 拒连」** |
| BLOCKED | 无 |

## 1. Docker testbed e2e(欠账步 9)

| 步 | 命令(task id) | 引擎结果行 | 备注 |
|---|---|---|---|
| 1 | `commands run test.linux-env` | `[ok] test.linux-env (0.6s)` | 镜像 auto-qb-testbed:48e6fda6 已存在, 容器已在跑且镜像一致 → 秒级 no-op, 未重建 |
| 2 | `commands run test.linux-e2e` | `[FAIL] test.linux-e2e (2063.8s)` | 默认 @fast 子集(--grep @fast); 会话 aqb-10504-20261127T023501, python 3.13 |

数字(playwright 汇总行原文): `1 failed / 5 skipped / 549 passed (34.2m)`; "Running 555 tests using 1 worker"。

### 失败用例全文(唯一)

- 定位: `tests/e2e/main-table-pinned-matrix.spec.mjs:366` — 「新增行(stamped)悬停一致 › flux 新增种子行(data-fx=row-in)悬停逐帧同步 + 稳态像素同底 @fast (flux/flat)」
- 断言 1: `Error: 悬停未真命中(窗口化移行/几何漂移?) —— 缺陷面采样作废`(`expect(...).toBe(true)`, :498)——用例自身的采样前置守卫先判红(悬停没落在目标行上, 后续像素判据未采样)。
- 断言 2: `Error: page.evaluate: Test ended`(:449)——前序失败后用例收尾期 evaluate 再抛, 属同一次失败的次生输出。
- 归因: **未定论, 环境竞态嫌疑高**(推测, 标注为推测): ①不在流量系 spec 内, 与本欠账(SSE 路径)无直接关系; ②形态=悬停落点与窗口化移行/几何漂移的竞态, 容器 swiftshader 软渲染慢 CPU 显性化计时敏感面是本 testbed 已知特征(任务档案 26-11-12-test-linux-testbed 实测先例: traffic-source-switch route.fetch 竞态, 已修); ③Windows 侧同 spec 恒绿(T4b 基线口径)。建议主会话: Windows 侧单跑该用例核绿(`commands run dev.e2e -- tests/e2e/main-table-pinned-matrix.spec.mjs --grep "新增行"`), 绿则按容器计时敏感面入池/记档, 不当 SSE 回归。
- 流量系 spec 全部通过: traffic-stream 3 例(SSE 主路径渲染延迟/徽标/降级)、traffic-fx-frames、traffic-fx-anchor、traffic-grid-stability、traffic-fx-panel、traffic-gap-zones、traffic-source-switch 均绿——SSE 路径在容器侧 e2e 有了第一份全绿背书。
- 容器侧既知噪音: tar 推送 `SCHILY.fflags` 告警刷屏(历史记录既有现象, 与结果无关); harness 期一条「速率键已连续 3 轮未上报」WARNING(桩面既有告警)。

## 2. 真机面起服与冒烟(欠账步 10)

| 步 | 命令(task id) | 引擎结果行 / 关键读数 |
|---|---|---|
| 1 | `commands run real.env` | `[ok]`: 当前环境=环境1(D盘机), 主实例 36595 / 副 36596, exe 在 D:\Programs\qBittorrent-testing* 下, 四实例免鉴权 |
| 2 | `commands run real.guard`(实例未起) | `[FAIL]` 36595/36596 均未监听 → 按 real.up 指引拉起 |
| 3 | `commands run real.up -- --port 36595` | `[ok] 36595 启动成功`(3.7s; 经 explorer.exe 拉起) |
| 4 | `commands run real.guard`(复查) | 36595: `[ok] pid=26360 v5.2.3 firewalled 真实种子 0 个已全部暂停, 自造(real-fake) 0 个不计入`; 36596 `[FAIL] 未监听` |
| 5 | 冒烟配置写盘 | `tmp-analysis/s0a-smoke.yml`(gitignored 临时区): 以 examples/minimal.yml 为骨架, 改三处——qbittorrent.port=36595 / data_dir=tmp-analysis/s0a-smoke-data(隔离生产 auto-qb-data/, 锁与日志均不落生产) / web.enabled=false(冒烟只验启动面) |
| 6 | `commands run dev.run -- tmp-analysis/s0a-smoke.yml --dry-run`(后台跑) | 启动面日志见下 |

副实例 36596 未拉起: 简报只要求「--port <白名单主端口>」, 冒烟配置只连主实例, 按最小动作不扩大。guard 对 36596 的 FAIL 仅为「实例没起」, 安全面(真实种子归零)在主实例已过。

### 冒烟启动面日志(auto-qb.log 原文, UTF-8)

```
[INFO] root: 日志初始化完成
[WARNING] auto_qb.config.loaders: 配置 schema 迁移(tmp-analysis/s0a-smoke.yml) v1→v8:
  config.hr.add_tag / add_tag_for_satisfied: 显式置空已移除, 语义为使用默认值
[INFO] auto_qb.core.qbmanager: 磁盘配置 schema 落后(v1→v8), dry-run 仅内存生效不落盘
[INFO] auto_qb.core.qbmanager: 启动 qB 管理器: 主循环 2.0s, 默认任务间隔 60.0s
[INFO] auto_qb.core.module: 创建全局任务 1 个: ['internal:traffic_snapshot_refresh']
[WARNING] auto_qb.core.modules.traffic_snapshot_mod: 流量快照 | 数据源未配置:
  需要 config.traffic_source.traffic_monitor.dat_path
```

### 冒烟结论与证据边界

- **与欠账当时(qB 离线)的差异已清偿**: 全程无 `连接 qBittorrent 失败` ERROR、无重试 WARNING、无 QbConnectError——按 qbmanager.py 的连接日志口径(首连失败必打 ERROR, `_note_conn_failed` 转换节流; 首连成功不打日志), 这是「首连即成功」的必要条件面; 后台运行 12+ 分钟(覆盖多个同步间隔)无主循环异常栈。**「连接成功」判定 = 负向日志证据 + 代码路径检视的推断**(首连成功本身无正日志), 不是直接观测, 如实标注。
- 直接观测受限点: 测试实例 0 种子 → 同步线无可同步数据, state.json 未生成(无变更可存); qB 侧 /api/v2/log/main 只有自身启动记录(免鉴权不记登录)。启动面形态与 0037 档案当时的验法(「流量模块初始化/无异常栈」)逐条对上, 且补上了当时缺的「qB 在线不拒连」。
- --dry-run 语义提醒(坑档 pitfalls/ops/dev-run-dry-run-daemon-orphan.md): dry-run 是守护循环不退出。首轮前台 300s 超时被引擎杀树(无残留, 事后盘点核实); 正式取证轮改后台跑, 取证后按坑档口径 `commands run dev.clone-kill -- --match dev_run --yes` 定点清理。
- 清理实录: clone-kill 杀掉 venv shim python(pid 27904); 其子进程 39624(uv 管理的真实解释器, cmdline 仅相对路径)被 in_clone_domain fail-closed 判 OUTSIDE-REPO 拒杀——**事后核实 39624 已随 shim 死亡**(shim 链断即退, 非本次杀掉), 当前无任何 dev_run/s0a-smoke python 残留; state.lock.meta.json 残留(pid 已死)属正常遗留, 下次启动由孤儿锁清理面处理。
- 冒烟产物留存: `tmp-analysis/s0a-smoke.yml` + `tmp-analysis/s0a-smoke-data/`(gitignored 临时区, 不入库; 复跑可直接用)。

## 3. 环境问题与处置汇总

1. **--dry-run 首轮前台超时**: dry-run 是常驻守护循环, 前台 300s 超时被引擎杀树, stdout 丢失。处置: 改后台跑 + 日志取证 + clone-kill 定点清理(坑档既有口径, 未踩新坑)。
2. **clone-kill 对 uv trampoline 子进程拒杀(fail-closed by design)**: 真实解释器 cmdline 只有相对脚本路径, 不落 clone 域判据。本次观察其随 shim 死亡自退, 未扩大处置面; 若未来遇到确需杀的此类活体, 按坑档只能由用户手动(任务管理器)处理——已如实记录, 不绕闸。
3. **副实例 36596 未起**: 按简报最小动作(只主端口), 不算环境故障。
4. **测试实例保持运行**: 本批未执行 `real.down`(简报未要求, 保守默认不动); 实例空闲(0 种子、firewalled)。需要回收时: `commands run real.down -- --port 36595`。
5. 红线遵守: 未改任何代码/配置; config.yml 与 auto-qb-data/ 未触碰(冒烟数据隔离在 tmp-analysis/); 全程未用 taskkill(清理走 dev.clone-kill 豁免脚本); 命令全部走 task id(唯一直接 shell 动作为只读盘点: Get-CimInstance/Get-NetTCPConnection/qB 日志 GET)。

## 4. 验证层级声明

- 实际执行并观察到结果: test.linux-env / test.linux-e2e(全文输出已读) / real.env / real.guard×2 / real.up / dev.run 冒烟(启动面日志全文) / dev.clone-kill / 残留进程盘点。
- 检视层(读代码判断, 未运行): 首连成功无正日志的判定依据(qbmanager.py connect/_note_conn_failed/_note_conn_ok 路径)。
- 未验证: e2e 唯一失败用例的 Windows 侧复跑(容器/宿主归因); SSE 路径的浏览器真机面(档案冒烟口径只到 dev.run --dry-run 启动面, 未扩大——浏览器面归 S0 主批的 dev.webui + 浏览器自动化取证)。
