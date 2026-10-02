# 基线 · 2309 passed + 3 skipped / 99% —— webui 多选右键菜单计划(26-10-02-1955) W5 收尾

> 摘要: 计划 26-10-02-1955 全五波完成(W1 配置键全链路 / W2 批量限速·移动 / W3 批量跳检 / W4 多选导出 /
> W5 冒烟走查汇总); W5 仅动 scripts/(ui_harness.py 跳检开关两态参数化 + ui_smoke.cjs 汇总断言),
> 产品代码零改动; 冒烟双皮肤 on 态新断言全 PASS, off 态精简轮 10/10 全绿(含 console.error/pageerror 干净)。
> 基线时间: 2026-10-03 05:42, develop @ 9f1e2a32(W5 已推送, test.full 实测)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2309 passed + 3 skipped / 99%**(13,452 语句 / 88 未覆盖 / 4,502 分支 / 89 partial,
test.full 32.13s, rc=0)。
相对上一切片(26-10-03-0440: 2309 passed + 3 skipped / 99%, 13,354 语句 / 88 未覆盖 / 4,502 分支 /
89 partial, @ 8cb2da59): passed / 未覆盖 / 分支 / partial **全部持平**, 语句 +98 —— 区间内
(8cb2da59 → 9f1e2a32)py 源零改动(仅静态 JS / 文档 / scripts), 属统计口径波动(导入面差异), 非代码增量。
