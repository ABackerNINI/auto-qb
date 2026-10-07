# 2757 —— 流量图速率口径调研收尾基线 (纯文档轮, src 零改动)

> 摘要: 任务档案 [26-10-07-webui-qb-traffic-rate-basis.md](../../tasks/26-10-07-webui-qb-traffic-rate-basis.md)
> 的收尾基线 —— 本轮产出调研报告 26-10-07-2031(纯 HTML 制品)与档案/切片回写,
> `src/` 业务代码零改动, pytest 面零新增; 相对上一基线 26-10-07-1336 的 passed/语句增量
> 来自其间其它会话已入库的守阵, 与本轮无关。
> 档案: memory-bank/tasks/26-10-07-webui-qb-traffic-rate-basis.md
> 基线时间: 2026-10-07 20:53

**Refs:** memory-bank/tasks/26-10-07-webui-qb-traffic-rate-basis.md

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2757 passed + 4 skipped, 0 failed, 29.50s, 覆盖率 TOTAL 99%(98.55%)**
  (16457 语句 / 166 未覆盖 / 5686 分支 / 150 partial; 门槛 98% 达标)
- 相对上一基线 [26-10-07-1336](26-10-07-1336-webui-delta-sync-s10-baseline.md)
  (2745 passed + 4 skipped @ 35.4s, 16259 语句 / 166 未覆盖 / 5686 分支 / 150 partial):
  passed **+12** / 语句 **+198** / 未覆盖·分支·partial 全部持平 —— 增量来自 1336 基线之后
  其它会话入库的测试(delta-sync 后续守阵等), 本轮 pytest 面零新增; 满足「未覆盖 / partial 不升」判据。
  4 skipped 为 Windows 侧 POSIX 专属存量。
- 首跑曾 1 failed(`test_wording_guard_is_green_on_current_kb`): 档案「原始请求」引述用户原话
  「等提交指令」踩 `[等…指令]` 模式 —— 按守卫提示加行内 `<!-- wording:allow -->`(引述原文豁免)后
  复跑全绿, 上列数字即复跑实测。
- 本轮改动面: memory-bank 5 个文件(报告 / 档案 / activeContext 切片 / 本切片 / reports/_index.md 生成物),
  `src/`、`tests/`、配置零改动。
