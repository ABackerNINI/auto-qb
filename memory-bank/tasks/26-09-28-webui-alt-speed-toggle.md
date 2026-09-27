# 26-09-28-webui-alt-speed-toggle — WebUI 备用速度切换(乌龟) + 主/备同窗限速弹窗

**Status:** Done
**Added:** 2026-09-28
**Updated:** 2026-09-28
**Summary:** 状态栏速度区新增备用速度切换(TPL-A 乌龟单图标双态: 熄灭=主速/亮绿=备速, 状态读主轮询 server_state 零新增请求); 限速浮层改主/备同窗双组卡片(TPL-C, 生效组描边高亮); 后端 qbapi +2 方法 / 路由 +2(金清单 61→63) / 命令 +2; test.full 1814 passed(基线 26-09-28-0111)。
**Topics:** webui-alt-speed-toggle

## 原始请求

在 WebUI 状态栏"上传下载速度"前添加切换至备用速度的纯图标按钮; 确认 qB 是否有相关接口; 备用速度值可修改, 弹窗采用主/备同窗(对齐 qB 客户端); 先出 3 套设计模板供挑选, 不直接改代码。模板出完后用户定案: 图标沿用 qB 设计语言, 状态栏选模板 A(乌龟开关), 弹窗选模板 C(双组卡片), 实施。

## 思考过程与决策

- **接口核实**: qB WebAPI 有现成三件套 —— `GET /transfer/speedLimitsMode`(0=主/1=备)、`POST /transfer/toggleSpeedLimitsMode`、`app/preferences` 的 `alt_dl_limit`/`alt_up_limit`(bytes/s); `qbittorrent-api 2026.8.1` 已全封装。qB 5.0 的端点迁移只动**主速度**键, alt_* 仍在 preferences。
- **模式状态零新增请求**: `server_state.use_alt_speed_limits` 已随 `/api/state` 主轮询下发(规则引擎 `sys.alt_speed_on` 同源同键), 乌龟按钮点亮态直接读 `statsServer`。
- **三模板设计**(计划 26-09-28-0037): A 乌龟开关 / B 仪表+角标合成(独立位) / C 仪表|乌龟分段直切; 弹窗三套均主/备同窗, 差异在布局(纵向两节/左右两列/双组卡片+生效高亮)。用户选 A + C 混搭。
- **切换语义**: 用 toggle 端点原生语义, 新状态由主轮询回读、不本地预翻转(幂等, 无本地状态分叉)。
- **弹窗提交**: 应用一次提交两组 —— 主速走既有 override 通道(`speed_override`), 备速走新 `speed_alt_set`(setPreferences 增量语义); **未改动的组不下发**; 任一组失败留在窗内并重取 qB 值回填。
- **与限速曲线互不接管**: 曲线任务只写主速度(transfer 端点), 备用速度无接管方(已写进命令 docstring)。

## 实现计划

1. 后端: `qbapi.py` +`get/set_alt_speed_limits` +`get/toggle_speed_limits_mode`; `/api/speed/mode` 增列 `alt_on`/`alt_current`(读失败回 None 不冒充); 新路由 `POST /api/speed/alt`、`POST /api/speed/alt/toggle`; 命令 `speed_alt_set`/`speed_alt_toggle` 入单一写线程队列。
2. 前端: 三主题 sprite +`i-turtle`(新绘 16px 单线); `statusbar.html` 速度组最左加 `.sb-alt`; `dialogs.html` 浮层改双组卡片(`.pop-grp`, 生效组 `.live` 描边 + "生效中"角标); `state.js` +`speedAlt`/`altToggling`; `dialogs.js` +`sbAltOn`/`sbAltTitle` computed +`toggleAltSpeed`/`submitAltLimits`/`_fillSpeedFields`; 三主题 CSS 同步(`.sb-alt`/`.pop-grp`)。
3. 测试: FakeClient +4 方法; `test_api_speed_alt_and_toggle`(三端点) + `test_qbapi_alt_speed_limits_normalization`(KiB↔bytes 换算/增量语义); `_GOLDEN_ROUTES` 金清单 +2。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 接口核实 + 三套设计模板(26-09-28-0037) | Done |
| 2 | 后端 qbapi 方法 + 路由 + 命令 | Done |
| 3 | 前端三主题(图标/按钮/弹窗/逻辑/CSS) | Done |
| 4 | 测试(FakeClient + 2 条新测试 + 金清单) | Done |
| 5 | 收尾回写(档案/切片/基线/坑条/索引) | Done |

## 进度日志

- 2026-09-28 00:37 设计模板落地(未动代码); 用户挑定 A(状态栏) + C(弹窗)。
- 2026-09-28 01:00 实施完成。test.full 首轮 5 失败归因: 4 条 docs 守阵(计划 HTML 缺 doc-* meta + _doc-map 超 index-auto cap) + 1 条金清单(新路由未登记); 修复 = 补 meta、gen_doc_map.py 头部收口、金清单 +2。
- 2026-09-28 01:30 提交轮: 合并远端 aef2462d→e8978704(stash→ff→pop, 3 处生成物/生成器冲突按"生成器看远端+索引重建"消解); 合并后 doc-map 仍超 cap, 头部二次收口至 12,118/12,200。终轮 **1815 passed + 3 skipped**, 基线切片 26-09-28-0111 已按合并后数字修订。
