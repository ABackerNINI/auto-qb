# 1615 collected: 1614 passed + 1 skipped —— HR 扩展配置简化(端点 /api/hr/sites + 站点勾选授权) (clone3)

> 摘要: clone3 合并远端 1610 之前的旧基座实测, 已被后续合流重测覆盖; 时分不可考; 当日序位第 20
> 基线时间: 2026-09-25 00:00
> 档案: 26-09-22-backend-partial-hr-verify (v3.1)

- **1615 collected: 1614 passed + 1 skipped**(clone3, 合并远端 1610 之前的旧基座实测) —— 2026-09-25
  **HR 扩展配置简化(端点 /api/hr/sites + 站点勾选授权)** + `test_extension_proxy.py` 2 条 +
  `test_hr_runtime.py::test_site_origins_served_live_for_extension`。落地面: 只读 `GET /api/hr/sites`
  + 扩展选项页三模板表单 / 站点权限拉清单勾选 + 一键申请。TOTAL **91%**(10920 语句 / 792 未覆盖 /
  3626 分支 / 327 partial)。
