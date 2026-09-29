# 基线 · 1792 passed + 3 skipped / 91% —— HR 三参数解耦 (拉取间隔 / 复用窗 / 立即拉取)

> 摘要: 计划 plans/26-09-30-0240 全量落地 —— 三参数解耦成正交: **节奏归拉取间隔**(refresh_interval
> 键不变, 展示名「对账波周期」→「拉取间隔」, 闸门在 service._refresh_locked 复用分支之后新增, 基准 =
> wave.healthy_ts, 失败波不推进基准 ⇒ 失败档下一轮重试节奏不变)、**新鲜度归复用窗**(新全局键
> `hr_check.reuse_window` 默认 2H, `_finish_wave` 时长换源 `min(reuse_window, 拉取间隔)` clamp)、
> **人工意志归立即拉取**(force 跳过复用窗 + 拉取间隔两道调度闸, min_interval/日额/Retry-After/
> 时间窗照常)。三条入口同一实现: 插件按钮 refresh-now → POST /api/hr/refresh(worker.force_fn)、
> WebUI「立即拉取/全部立即拉取」→ manager.hr.request_refresh、`--hr-once` 走查 →
> refresh_all(force=True)。worker 新增 `request_refresh`(一次性 force 旗标, cond 保护, run_once
> 消费即清) + 「拉取间隔」节流类别; status 展示层 next_wave_at 改 healthy_ts + interval、fresh_text
> 补「下次拉取」、blocking stale 文案改「可点『立即拉取』提前」。基线时间: 2026-09-30 04:50
> (develop @ 0e43bf7d) 制品: plans/26-09-30-0240 **未提交**(等用户显式指令)。

TOTAL **1792 passed + 3 skipped / 91%**(12477 语句 / 995 未覆盖 / 4240 分支 / 413 partial, test.full 20.4s, rc=0) ——
较上基线 26-09-30-0024(1768)增 24 条: test_hr_service 9(①-⑧ 三态解耦矩阵 + clamp 两半)、
test_hr_worker 3(旗标一次性消费 / 按站点名只影响该站 / 「拉取间隔」节流类别与 min_interval 区分)、
test_hr_runtime 2(线程未启动如实返回 / 线程在跑受理)、test_hr_server 4(refresh 路由 401/403 不触
force_fn / 受理回清单 / 无 force_fn 404 / force_fn 异常不死)、test_web 3(受理 / 未启用 400 + 未接入
400 / 线程未启动 409)、test_hr_config 3(reuse_window 默认与解析 / 60s~7d 边界 / impact L0)。键面基线
147→148 键(keys.md 已回写); 路由金清单 +1(POST /api/hr/refresh); 前端 hrs 字段守阵 +refreshing/
refreshNote。

## 本轮改动面

- 配置层 5 文件: models(HrCheckConfig.reuse_window=2H, docstring 15 键)/ loaders(解析)/
  schema/hr(reuse_window Field「数据复用窗」+ refresh_interval 展示名「拉取间隔」help 重写)/
  validation/sections(KNOWN_HR_CHECK_KEYS + 60s~7d 边界)/ impact(reuse_window L0)。
- 核心 4 文件: service(refresh_site/refresh_all/_refresh_locked 加 force; 复用分支 `not force and…`
  跳过; 拉取间隔闸门 healthy_ts + interval; _finish_window 换源 min)/ worker(request_refresh 置旗
  + wake; run_once 消费即清; _PACING_CLASSES 头插「拉取间隔」)/ report(--hr-once force=True)/
  status(next_wave_at=healthy_ts+interval; fresh_text「下次拉取」; blocking stale 文案)。
- 端点 2 文件: channel(API_REFRESH 常量)/ server(force_fn 注入; POST /api/hr/refresh
  鉴权/origin 照走; docstring 边界声明改「只入队 + 置一次性 force 旗标并唤醒」)。
- runtime/WebUI 3 文件: runtime(request_refresh 汇合点, 未启动返回 note; _build 传 force_fn)/
  webui routes/hr(POST /api/hr/refresh: site 校验同 confirm-empty 风格, 空受理回 409)/
  settings-detail.html + hr_status.js(每站「立即拉取」+ 卡片头「全部立即拉取」+ 受理注记行)。
- 插件 2 文件: background.js(refresh-now 消息 → 逐实例 POST /api/hr/refresh; 404 降级纯排空 +
  日志提示升级; 随后 pollAll 排空)/ options.js(poll() 改发 refresh-now, 状态行汇总「已受理 N 个
  站点 + 排空结果」); 按钮文案按拍板保留「立即拉取一次」; poll-now 消息保留(旧插件兼容)。
- docs 回写: keys.md(hr_check 7 键 + 站点条目改名)/ docs/configuration.md(全局段 7 键 +
  reuse_window 示例 + refresh_interval 改名)/ extensions README(立即拉取行为)。

## 开放项

- **真机端到端**(计划 §6 插件行, 用户侧): 复用窗内点「立即拉取一次」→ 后端日志见波启动 →
  WebUI「上次取波」前进; 连点两次第二次因 min_interval 等待且文案可见。
