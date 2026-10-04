# WEBUI 上下行流量方向色交换 + 速度组图标统一 + 限速改灰 — 实施完成待提交

> 摘要: 用户拍板交换上下行流量方向色(上行=紫 `--indigo` / 下行=蓝绿 `--teal`), 覆盖历史流量图 / qB 流量图(种子·组·全局) / 状态栏今日统计 / 状态栏速度组图标; 速度组方向图标由全局绿/蓝统一到流量语义色(`.sb-spd` 作用域覆盖), 状态栏限速值改中性灰 `--fg-dim`(与做种要求值 `.m-pair .req` 同款)。14 文件改动, test.full 2508 passed + 4 skipped / 99%, 真浏览器三皮肤 30 断言全过。改动留在工作树, 等用户显式提交指令。
> 最后活动: 2026-10-04 17:23

**Refs:** memory-bank/tasks/26-10-04-webui-traffic-color-swap.md, memory-bank/testing/baselines/26-10-04-1722-webui-traffic-color-swap.md

## 现状

- 实施 + 验证完成, 无遗留子任务。
- 改动 14 文件: 7 处令牌定义(`atlas/style.css` · `console/style.css` · `prism/css/themes/*.css` 五主题) + 3 皮肤 `index.html`(i-traffic 内联兜底) + `shared/qb_traffic_chart.js`(兜底链) + 3 皮肤 `.sb-spd` 规则(`atlas|console/css/dialogs.css` · `prism/css/views.css`)。
- 口径已回写 `conventions/webui.md`「流量方向色族」条目(含「不要改全局 `.ico-up/.ico-down`」的边界)。

## 下一步

- 等用户显式提交指令(`commands run ship.commit`)。
