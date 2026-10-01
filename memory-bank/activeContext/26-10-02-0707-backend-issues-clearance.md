# 用户指派批 7 issue 分阶段清偿(委派模式, backend)

> 摘要: 主会话只委派: 7 条计划外 issue 分 4 阶段串行派子智能体, 每阶段单独提交(2359a3d1 hr 三项 / 4a883385 flaky / f89ceada qbmanager 两项 / 49d933b5 tray 读回), 3 项修法拍板问用户、2 项主会话按仓库惯例定夺; 7 条全部收口(5 Done + 1 Dropped 复验推翻 + 1 已消失), 子智能体 0 次异常失败。会话末基线 2289 passed + 3 skipped / 99%(baselines/26-10-02-0707)。
> 最后活动: 2026-10-02 07:07

- **已完成**: 全部 7 条收口, 逐条实际修法与提交对应关系看 [tasks/26-10-02-backend-issues-clearance.md](../tasks/26-10-02-backend-issues-clearance.md) 子任务状态表。
- **待用户决断(计划外发现, 均未处置)**:
  1. `_set_windows_appid` 生产零调用点(死函数, 自 9891c030) —— issue 26-10-01-2203 任务栏图标排查的「已设 AUMID」前提可能不成立(补调用点 / 删函数 / 另案);
  2. 首轮 tick 任意异常在 next_*_at 未推进时无退避快速重试(有 ERROR 日志不静默, 是否要退避待决);
  3. core-domain.md:27 AUMID 表述与 tray/app.py docstring「AutoQB.UI.lnk」为先在漂移, 未改;
  4. kb 债务(activeContext 切片 87 > 70 + cap 债务 1)需另开会话清理。
