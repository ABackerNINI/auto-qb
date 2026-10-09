# 2838 —— 种子流量图的档位/纵轴控件改落图下统计栏

> 摘要: 「种子流量图控件落点」第 2 轮(用户更正上一轮: 放种子头部太挤/窄窗变形)收尾基线。改动: `shared/tpl/drawer.html` 删种子头部 `.qb-headctl` 控件组、改在 `.hist-summary`(图下统计栏)「下载累计」之后插 `.qb-statctl`, 统计栏本体的门放宽为 `qbCurSummary || qbCurScope === 'torrent'`; 三皮肤 `views.css` 把原 5 行 `.qb-headctl` 规则换成 4 行 `.hist-summary > .qb-statctl` 规则。守阵侧**只改写既有断言口径**(落点改判统计栏 + 次序单调 + 头部不得再有控件组 + CSS 成对清单换类名), 未新增测试函数。
> 档案: memory-bank/tasks/26-10-09-webui-qb-traffic-seed-header-controls.md
> 基线时间: 2026-10-09 11:14

**Refs:** memory-bank/tasks/26-10-09-webui-qb-traffic-seed-header-controls.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2838 passed + 4 skipped + 0 failed, 覆盖率 TOTAL 99%**(16553 语句 / 169 未覆盖 / 5708 分支 / 145 partial; 门槛 98% 达标)
- **耗时**: 43.81s(命令总耗时 45.9s)
- **新增/修正用例**: **零新增测试函数** —— 只**改写** `tests/test_webui_static_dom_panel.py` 两个既有守阵的断言口径: ①`test_frontend_qb_traffic_chart_wiring` 的种子侧断言由「种子头部含 `.qb-headctl` 控件组」改判「种子头部**不得**再含控件组 + `.hist-summary` 内含 `.qb-statctl`(门 `qbCurScope === 'torrent'`)」, 并新增统计栏本体门与「图例 → 窗口 N 桶 → 上传累计 → 下载累计 → 控件组 → 口径 hint」的下标单调断言; 两处控件组内层逐字同源比对的对象由「流量形态头部 vs 种子头部」换成「流量形态头部 vs 统计栏」。②`test_frontend_qb_traffic_yaxis_and_annotation` 的种子侧断言改判统计栏, 三皮肤 CSS 成对清单的钉点由 `.drawer-head > .qb-headctl { flex: 1 1 100%;` 换成 `.hist-summary > .qb-statctl {`。

## 说明

- **代码事实变更**: 有 —— 种子「流量」页签的档位/纵轴控件组落点由**种子详情头部**(`.qb-headctl`, 恒占第二行)改为**图下统计栏**(`.hist-summary` 内 `.qb-statctl`, 排在「下载累计」之后); 统计栏本体渲染门由 `qbCurSummary` 放宽为 `qbCurSummary || qbCurScope === 'torrent'`(首载/错误态无汇总时控件仍可见)。全局/分组流量形态零改动(控件仍在流量形态头部)。零 JS 改动。
- **真浏览器旁证**(临时桩 `tmp-analysis/`, 已 gitignore; 桩复用 `scripts/ui_harness.py` 的合成种子设施 + 打开 `qb_traffic` 旗标 + 合成流量响应, 用完即删): 三皮肤 1440x900 真实手势(双击种子行 → 点「流量」页签)实测 —— 控件组可见且落在「下载累计」右侧同行 / 档位 13 钮 / 纵轴 3 钮 / 控件组 821px 不越界 / 种子头部 44px(单行)/ 统计栏 54~57px / 图 235~238px / 点「7天」真换窗(桶数随之变化)/ 零 pageerror。窄视口 1180 / 980 / 820: 头部恒 44px、统计栏 58→81px、横向溢出 0。分组流量形态(组右键 → qB 口径流量图)实测: 头部仍含 13 档 + 纵轴控件, 统计栏无控件组 ⇒ 未被本次改动波及。
- **未验证面**: ①15 个 `drawer_tpl/` 变体下统计栏的观感未逐变体走查; ②折叠态(`drawer.collapsed`)与统计栏同屏时的观感未走查。
