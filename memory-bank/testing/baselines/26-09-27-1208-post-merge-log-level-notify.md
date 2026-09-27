# 1688 passed + 1 skipped / 0 failed —— 合并远端后新基线(等级整改落地 + 旧计划 meta 修复生效)

> 摘要: ff 合并远端 `6fd1331`(前端模板拆分 + web 生命周期日志采集自足化 + 26-09-26-2345 旧计划 meta 修复)
> 后重测: 等级整改(表 A 升 20 / 表 B 降 13 / 表 D 反向 1 / notify.min_level 默认 ERROR)在合并树上全绿;
> 26-09-27-1152 切片中的 2 failed(既有 docs 守阵红)随远端修复消失, 入池 issue 26-09-27-1153 置 Done。
> 测试数 1685→1688(远端净增 3)。基线时间: 2026-09-27 12:08
> 档案: 26-09-27-backend-log-levels-notify

TOTAL 91%(11206 语句 / 815 未覆盖 / 3720 分支 / 330 partial; test.full 19.7s;
覆盖率口径见 [../baseline.md](../baseline.md))。
