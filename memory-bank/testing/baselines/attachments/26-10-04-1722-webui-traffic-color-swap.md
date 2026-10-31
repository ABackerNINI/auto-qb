# 基线切片 26-10-04-1722 — webui 上下行流量方向色交换 + 速度组图标统一 + 限速改灰

> 摘要: 交换 `--today-up/--today-down` 令牌值(上行=紫 `--indigo` / 下行=蓝绿 `--teal`), 覆盖历史流量图 / qB 流量图(种子·组·全局) /
> 状态栏今日统计与速度组图标; 速度组方向图标统一到流量语义色(`.sb-spd` 作用域覆盖), 状态栏限速值改中性灰 `--fg-dim`。
> 纯 CSS/HTML/JS 令牌与配色改动, 未新增或修改任何 Python 测试。
> 基线时间: 2026-10-04 17:22
> 档案: [tasks/26-10-04-webui-traffic-color-swap](../../tasks/26-10-04-webui-traffic-color-swap.md)

- 时间: 2026-10-04 17:22 (GMT+8); 基线 = develop @ `bc23748b` + 本轮 14 个未提交前端文件改动(树净, 改动全在 `src/auto_qb/webui/static/`)
- 分支: develop @ `bc23748b`
- 命令: `commands run test.full`
- 实测: **2508 passed + 4 skipped, 41.32s(pytest 计时), 覆盖率 TOTAL 99%**(14821 语句 / 152 未覆盖 / 4964 分支 / 112 partial)
- 相对上基线(26-10-04-1644: 2507 passed + 4 skipped / 14677 语句): passed +1、语句 +144 —— 均可归因于
  `bc23748b`(本轮 `my-commit-flow.sync` 带入的其它 clone 合并), **与本轮前端改动无关**(纯 CSS/HTML/JS, pytest-cov 不计)
- 分支 / partial 两个计数与上基线完全一致(4964 / 112); 语句基数随合并变化, 覆盖率仍 99%

**Refs:** memory-bank/tasks/26-10-04-webui-traffic-color-swap.md
