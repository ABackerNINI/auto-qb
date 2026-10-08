# 2817 —— 修种子流量图档位/纵轴控件消失 (版式改只接了流量形态头部)

> 摘要: 「种子流量图的时间档位与纵轴控件消失」修复轮收尾基线。改动: `shared/tpl/drawer.html` 种子形态头部补 `.qb-headctl` 控件组(门 = `qbCurScope === 'torrent'`), 三皮肤 `views.css` 补 `.qb-headctl` 版式(整体占满第二行); 守阵侧**只改写既有断言口径**(两头部控件组齐全 + 内层逐字同源 + 三皮肤 CSS 成对), 未新增测试函数。
> 档案: memory-bank/tasks/26-10-09-webui-qb-traffic-seed-header-controls.md
> 基线时间: 2026-10-09 07:40

**Refs:** memory-bank/tasks/26-10-09-webui-qb-traffic-seed-header-controls.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2817 passed + 4 skipped + 0 failed, 覆盖率 TOTAL 99%**(16479 语句 / 162 未覆盖 / 5696 分支 / 146 partial; 门槛 98% 达标)
- **耗时**: 36.35s(命令总耗时 38.5s)
- **新增/修正用例**: **零新增测试函数** —— 本次只**改写** `tests/test_webui_static_dom_panel.py` 两个既有守阵的断言口径: ①`test_frontend_qb_traffic_chart_wiring` 加「种子形态头部控件组齐全 + `qbCurScope === 'torrent'` 门 + 两处控件组内层逐字同源(空白归一后比对)」; ②`test_frontend_qb_traffic_yaxis_and_annotation` 的 `qbSetYAxisMode(` 计数 3→6、补种子头部 `.qb-tools/.qb-seg` 与手动输入框断言、三皮肤 CSS 成对清单加 `.drawer-head > .qb-headctl`。

## 说明

- **代码事实变更**: 有 —— 流量图的「时间档位 + 纵轴控件」由**单一挂点(流量形态头部)**变为**两处挂点**(流量形态头部 + 种子「流量」页签头部), 两处内层标记由守阵钉逐字同源; 新增版式类 `.qb-headctl`(种子头部第二行容器, 三皮肤成对)。
- **真浏览器旁证**: 临时桩(`qb_traffic` 旗标打开 + 40 合成种子)三皮肤 1440x900 实测 —— 种子详情「流量」页签下 `.qb-headctl` 可见、档位 13 钮 / 纵轴 3 钮齐全、控件框 `x=29 w=1388`(未越界)、头部高 65px(两行)、图/空态仍可见、**零 pageerror**; 临时桩与截图已删(不入库)。
- **未验证面**: 窄视口(≤900px)下种子头部的换行逐档观感未走查(规则靠 `flex-basis:100%` + `flex-wrap` 抗挤压)。
