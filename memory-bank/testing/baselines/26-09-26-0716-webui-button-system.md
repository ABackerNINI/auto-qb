# 1642 collected / 1641 passed + 1 skipped —— webui 按钮体系重构(星图 B 胶囊 × 棱镜 C 双色)

> 摘要: 全动作按钮收敛 .bt 族(ce-btn/ce-icon 零残留), 守阵 +1; 数字为本 clone 合并工作树重测(工作区当时含另一条未提交线「Console Hub 分区重组」, 该线改动已按 hunk 过滤排除在提交之外)
> 基线时间: 2026-09-26 07:05
> 档案: 26-09-26-webui-button-system

- **本轮 +1 条**(test_web.py): `test_frontend_button_system_paired` 按钮体系守阵 —— ce-btn/ce-icon 全语料零残留 /
  `.bt` 六变体两套 CSS 成对定义 / 两套模板 bt 用量逐类相等 / 双色令牌(`--on-accent/--on-accent-ink/--on-error`)
  星图 `:root` + 棱镜五主题成对声明。落地面: 两套 UI 全动作按钮 ce-btn/ce-icon → `.bt` 族(43 处/边 + 站内确认框
  `danger-solid` 动态绑定 + 登录页); `.bt` 配方入 atlas style.css(B 胶囊)与 prism components.css(C 双色);
  bulk/row/prio/login 家族对齐(紧凑档尺寸不动); 新增计划制品
  [plans/26-09-26-0538-plan-webui-button-3-proposals.html](../../plans/26-09-26-0538-plan-webui-button-3-proposals.html)。

TOTAL **92%**(11013 语句 / 787 未覆盖 / 3656 分支 / 331 partial)。
