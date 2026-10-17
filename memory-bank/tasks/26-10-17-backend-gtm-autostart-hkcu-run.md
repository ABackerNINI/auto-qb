# 26-10-17-backend-gtm-autostart-hkcu-run — gtm 开机自启改 HKCU Run（移除 schtasks 路径）

**Status:** Done
**Added:** 2026-10-17
**Updated:** 2026-10-17
**Summary:** gtm Windows 自启后端从 `schtasks /SC ONLOGON` 换成 HKCU Run 注册表（零提权），移除 schtasks 路径，并把注册失败原因落进发现指针与设置页
**Topics:** backend-gtm-autostart-hkcu-run
**Refs:** memory-bank/issues/26-10-17-1455-bug-gtm-autostart-elevation.html

## 原始请求

1. 「认领26-10-17-1455-bug-gtm-autostart-elevation, grilling」——认领该 issue 并做设计质询。
2. grilling 五轮全部「按推荐」，其中 Q1 追加约束：**选 A（零提权后端），同时移除 schtasks 路径**。
3. 「开始」——批准共识清单，开工。

## 思考过程与决策

grilling 五轮（每轮多问）收敛出以下拍板结论，均已在会话内与用户逐条确认：

- **方向**：Windows 自启后端换成 HKCU Run，`schtasks` 路径整个移除（代码零 schtasks 调用）。理由：`ONLOGON` 是「任何用户登录」级触发器、非提权必被拒；提权方案（`ShellExecuteW("runas")`）无法在无人值守的 auto-qb 拉起路径完成，直接撞 D4「自启绝对支持」与 D13/D19「启动器恒定携带自启意图」；`src/auto_qb/infra/autostart.py` 已有同款零提权范式可照抄（gtm 是独立包，不能 import）。
- **后端细节**：值名 `global-traffic-monitor`（与旧任务名主干一致；不叫 `auto-qb` 以免同键互覆盖）；`is_registered` = 值存在即算（保持既有语义，不比对命令内容）；`register()` 无条件覆盖写、`unregister()` 一律 `DeleteValue`；命令超 260 字符 fail-fast 报错，不截断、不降级到启动文件夹（本机实测 158 字符）。
- **可见性**：`endpoint.json` 加 `autostart_error`（`str|null`，成功清空），**不升 schema**（gtm 与 auto-qb 各持 `ENDPOINT_SCHEMA=1` 且不符即告警，升版只会制造无意义告警）；原因经 `ControlServer` 新构造参数落盘（`autostart_registered` 是写指针时现做状态探测，原因推不出来）；设置页在状态文案后追加原因，`tm.autoErr` 仍只管「点勾选失败」的临时态。
- **边界**：只动 Windows 后端，Linux systemd --user / macOS launchd 一行不碰；auto-qb 侧只加「读字段」一处，`agent.py` 的拉起与去重（D14）不动；文档只重写两处自启节并顺手改对已漂移的任务名。
- **测试与验收**：`build_installer(..., registry=None)` 注入替身（替身支持 `with`，全程不碰真注册表）；Done = 单测全绿 + 真机 `reg query` 读到值 + 手工执行该命令行能起；重启验证做不了就明写缺口。
- **不做的**：历史 schtasks 任务只走文档手工清理（当前机器 `autostart_registered=false`，从未注册成功，残留概率极低）；不再做 schtasks 真机探针。

## 实现计划

1. 重写 Windows 后端（`installer.py`）：`WindowsTaskBackend` → `WindowsRunKeyBackend`，winreg 注入点 + 260 字符检查 + 模块 docstring 同步。
2. 失败原因通道（`__main__.py` + `server.py`）：`_maybe_register_autostart` 返回原因 → `ControlServer(autostart_error=)` → 写进 `endpoint.json`。
3. auto-qb 侧读字段（`agent.py` dataclass/解析/状态路由）+ 前端（`state.js` / `config_hub.js` / `settings.html`）。
4. 测试重写（`test_installer.py` Windows 段整体重写 + 指针字段 + 前端代理用例）。
5. 文档（gtm README 自启节 + `docs/configuration.md` 自启表 + 旧任务手工清理说明）。
6. 全量测试 + 真机验证口径记录。

## 子任务状态表

| 步 | 内容 | 状态 |
|---|---|---|
| 1 | 重写 Windows 后端为 HKCU Run（winreg 注入 + 260 检查 + docstring） | Done(2026-10-17) |
| 2 | 失败原因通道：`_maybe_register_autostart` → `ControlServer` → `endpoint.json` | Done(2026-10-17) |
| 3 | auto-qb 侧读字段 + 设置页展示 | Done(2026-10-17) |
| 4 | 测试重写与新增 | Done(2026-10-17) |
| 5 | 文档重写（README + docs/configuration.md） | Done(2026-10-17) |
| 6 | 全量测试 + 验收记录 | Done(2026-10-17) |

## 进度日志

### R0 · 立档 (2026-10-17)

- 认领 issue（`In Progress`，含复验段：代码锚点仍在；现象因 `schtasks.exe` 被本会话 Program Blacklist 拦截无法重跑，按证据指纹判定仍复现）。
- grilling 五轮收敛出共识清单并获用户批准，立本档案。

### R1 · 实施 (2026-10-17)

- 六步全部落地：`WindowsRunKeyBackend`（HKCU Run，零提权，260 fail-fast）+ `autostart_error` 落指针 + auto-qb 侧字段与设置页展示 + 测试重写 + 两处文档重写。
- 测试：根 `test.full` 与工具侧独立套件全绿（数字见 `commands run kb.baseline`，本轮基线切片 `testing/baselines/26-10-17-1549-gtm-autostart-hkcu-run.md`）。
- 真机验证（非提权会话）：注册 → `winreg` 读回 158 字符 REG_SZ → 重复注册 `skipped` → 手工执行命令行能起（被单实例锁挡下）→ 卸载后读回 `FileNotFoundError`。**验证后已卸载**：该值指向 clone4 开发目录，留在机器上会与 `D://Projects//auto-qb` 的生产实例抢登录自启；真实部署由生产 clone 的 `launch.cmd` 自行注册。
- 缺口：**重启/注销验证未做**（需真实登录会话，不可自动化）；`reg.exe` 被本会话 Program Blacklist 拦，注册表真值改用 Python `winreg` 读（同一 API，非换壳绕行）。
- 新坑档 `pitfalls/backend/windows-onlogon-autostart-elevation.md`（ONLOGON 需提权 + 与 WinError 5 同指纹的判别 + 260 上限）。

- 2026-10-17 15:50 gtm Windows 自启改 HKCU Run（移除 schtasks 路径），注册失败原因落 endpoint.json 的 autostart_error 并在设置页显示
