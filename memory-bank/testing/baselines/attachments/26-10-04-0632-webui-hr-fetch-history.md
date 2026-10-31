# 基线切片 26-10-04-0632 — WEBUI HR 拉取历史详情表 S1-S6 收尾 (history 环形留痕 + GET /api/hr/history + 弹层表③)

> 摘要: HR在线核实新增「拉取历史详情表」—— 后端站点文件内嵌 `HrSiteData.history` 环形留痕
> (波次/拦截(含 force-defer)/对账三类事件, 拍板⑤=2000条/站点+6个月, 不抬 hr_site 版本链) +
> `history_rows()` 只读口径(合并/降序/limit/人话/徽章映射) + `GET /api/hr/history` + 全屏弹层表③
> (懒加载/站点chips/仅看异常/行展开档位明细) + ui_harness 桩五形态。S1-S5 每步一 commit
> (0227f25c/4c88e8e2/2923ffa4/85a22f8a/ec697a08), 各步 test.quick 2427/2431/2441/2442/2442 passed;
> S5 三皮肤冒烟 207/207 + 15 张截图目检零缺口(追剧集行 Ctrl+click 存量 flaky 按既有处置绕行,
> 坑档 pitfalls/testing/smoke.md 复发 +1)。

- 时间: 2026-10-04 06:32 (GMT+8); 本轮收尾按任务铁律禁 git 写操作未做远端同步, 基线 = 本地分支
- 分支: webui-hr-fetch-history @ ec697a08(S5 桩走查; 工作树仅 memory-bank/docs 回写件, 不影响测试)
- 命令: `commands run test.full`
- 实测: **2442 passed + 3 skipped, 30.93s, 覆盖率 TOTAL 99%**(14571 语句 / 138 未覆盖 / 4850 分支 / 107 partial)
- 相对上基线(26-10-04-0308: 2423 passed)净增 19 用例: S1 数据模型 +4 / S2 写入点 +4 / S3 只读口径+API
  +10 / S4 前端表③ +1 / S5 +0(冒烟桩不进 pytest); 语句 +155(14416→14571) / 分支 +30(4820→4850)
- 未验证面: 真机 WebUI 走查(表③三皮肤视觉/交互 + 真实 HR 数据)待用户执行; 新旧版本混跑窗口期
  旧程序写盘丢 history 键为已知限制(业务字段无损, 不做双写兼容)
