# 4024 passed + 2 skipped —— HR 扩展缺站点权限的可见化与失败分类修正

> 摘要: 扩展缺站点权限(MV3 可选权限重装后丢失)的可见化与失败分类修正落地后全量基线
> 基线时间: 2026-10-29 02:12
**Refs:** memory-bank/plans/26-10-29-0147-plan-hr-ext-site-permission.html

## 验收数字

`commands run test.full` 实测输出:

- 汇总行: **4024 passed, 2 skipped in 158.11s (0:02:38)**
- TOTAL 表: `21032  101   7112   102    99%`(语句 / missed / 分支 / partial / 覆盖率)
- 覆盖率门槛 99% 达标, 无 FAIL 行; 零失败零回归
- 同日后一跑(修复前的中间态)汇总行 153.80s、命令包装层计时 159.9s ⇒ 本机全量耗时区间约 **154–160s**

定向池单跑(本次改动的五个守阵文件, `--no-cov`): **343 passed in 6.38s**

- `tests/test_extension_proxy.py` —— 45 passed(新增跨层授权匹配 / 未授权零请求 / 已授权才判网络层)
- `tests/test_hr_status.py` —— 59 passed(新增两态文案 / 病因优先 / 陈旧痕不生效)
- `tests/test_hr_service.py` / `tests/test_hr_events.py` / `tests/test_hr_fetcher_channel.py` —— 其余 239 passed

口径注记: passed/skipped/覆盖率数字由 agent 从本次实测输出誊写; 相对上基线的逐位对比不写(看差值 `commands run kb.baseline -n 2`)。

## 本改动面

2026-10-28 生产故障(BTSchool / CarPT 三档全失败 12h+, 日志只有 `[HR 页面改版] … Failed to fetch`)的落点,
5 个源文件 + 3 个扩展文件 + 6 个测试件 + 3 份文档:

- `src/auto_qb/hr/channel.py` —— 新增 `KIND_NO_PERMISSION` / `KIND_NETWORK` 两个回传 kind(带「为什么它与既有 kind 不同层」的注释)
- `src/auto_qb/hr/fetcher.py` —— 新增 `HrExtensionNoPermission` / `HrExtensionNetwork`(都继承 `HrChannelUnavailable`, 于是「不计档位失败 / 不挂改版标签 / 不推 `fail_streak`」自动成立); `_fetch` 分支顺序 login-page → ext-quota → no-permission → network → 未知 kind 回落 `HrFetchError`(旧扩展兼容)
- `src/auto_qb/hr/model.py` —— `HrSiteData.channel_last_error` 落盘字段(零迁移: 缺键即空 dict, 不抬 schema_version) + 两个通道态常量
- `src/auto_qb/hr/events.py` —— `site_not_permitted` / `extension_network` 两条文案(各带动作, 都不带 `[HR 页面改版]`)
- `src/auto_qb/hr/service.py` —— 通道层 except 分支先记痕(`_note_channel_error`)再告警; 缺权限升 ERROR + 非静默, 网络层维持 WARNING + 静默; 恢复点(`_reset_warned_on_recovery`)清痕; `channel_state` 加两态并带 `ts > healthy_ts` 生效条件; `zero_rows` 改「总量为 0 ∧ 全档 ok」; 页面层取数失败补接 `_maybe_alert_lane_fail`(新增 `_WaveContext.alerted` 承接登录失效分支的告警信号)
- `src/auto_qb/hr/status.py` —— `CHANNEL_TEXTS` 两态文案(带动作); `blocking_reason` 把通道病因排到判定链最前
- `extensions/hr-fetch-proxy/background.js` —— `originGranted` / `siteGranted` 纯函数 + `sitePerms` 缓存 + 未授权**拒发**(零请求); 徽标第五态 `noSitePermission`(排在 `ok` 之前); `permissions.onAdded/onRemoved` 双监听重核
- `extensions/hr-fetch-proxy/options.js` —— `renderSiteChecks` 每行三格(input / 名称 / 授权态), `refreshSitePermUI` / `grantMissing`(仍保证手势内第一个 await 是 `permissions.request`); `TAG_TEXT` 两新 kind
- `extensions/hr-fetch-proxy/options.html` —— 站点权限汇总条 + 「授权未授权站点」按钮 + 授权态样式 + 图例第五态
- `tests/test_test_plan_docstring_guard.py` —— 本轮被它拦下一次(13 条新用例未登记「## 测试计划」), 五个文件的头部清单已同步
- `extensions/hr-fetch-proxy/README.md` —— 「授权站点」升为安装第 4 步 + 重装重置权限的醒目警告 + 排障表把「拉清单报 Failed to fetch」与「站点取数报 Failed to fetch」拆成两行
- `docs/configuration.md` —— 通道病因位两态与动作; 零行判据补「全档有效」; 日志标签表补 `[HR 通道不可用]` 三种成因
- `memory-bank/pitfalls/web-ui/extension-bridge.md` —— 新增一行(重装后未授权 → `Failed to fetch`) + `复发: 3` + 三条硬约束(先查权限再发请求 / 可选权限会静默清零 / 禁用 `permissions.contains` 判多 origin)
- `memory-bank/pitfalls/backend/fault-domain-classification.md` —— `复发 +1`: 同一坑(环境态冒充站点结论)的第二次实报
