# 1629 collected: 1628 passed + 1 skipped —— HR 扩展选项页终态实施: 风格 A 瑞士网格 + 两表 + 日志收起

> 摘要: 合流远端 700a11b 五笔后重测; +1 条(事件环契约) + 三档接线守阵改写; 时分取本轮制品 26-09-26-0031 计划时点; 当日序位第 3
> 基线时间: 2026-09-26 00:31
> 档案: 26-09-22-backend-partial-hr-verify (v3.3)

(档案 `26-09-22-backend-partial-hr-verify` v3.3; 数字为**合流远端 `700a11b` 五笔[webui 修复/docker 验收]后重测**)。
本轮 **+1 条**: `test_extension_proxy.py::test_background_events_ring_dual_write` —— 真跑 background.js 六类场景
(页面成功×2 / HTTP 失败 / .torrent 成功 / 登录页 / 配额让位), 钉死后台与日志**同源双写**的结构化事件环契约
(tag 分类 ok/quota/login/error + host/kind/ms/bytes); 另把三档接线守阵改写为 `test_options_swiss_wiring`
(单一风格定案 + 三档共存机制不得回潮)。落地面: `background.js` 事件环(EVENT_CAP=50, 防抖整份写回,
五个事件点) + 选项页按样张 A 重写(①连接 ②站点权限 ③站点现状表 ④取数明细表 + 折叠区[日志/硬上限/高级 JSON]);
表内阈值从 `SITE_CAPS` 取不写死。**新增制品** [plans/26-09-26-0031-plan-hr-ext-options-style.html](../../plans/26-09-26-0031-plan-hr-ext-options-style.html)
(三套风格选型, 用户选定 A)。

耗时: 并行 17.1 / 18.1s(2 次采样, 全部 test.full)。
