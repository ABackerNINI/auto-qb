# 兼容 Transmission 可行性分析（报告轮）

> 摘要: 认领 issue 26-10-01-2212 并出可行性报告 26-10-01-2347（取证基线 826f25e6）。查重确认此前无同类报告。结论：技术可行性**中**、业务可行性**低**、全量 38–58 人日（最小只读子集 8–12 人日）、**建议暂不做**。停在用户拍板。
> 最后活动: 2026-10-01 23:47

## 正在进行

- 收尾闸门：`commands run test.full`。
- 之后待用户拍板结论：拍「不做」→ issue 转 Dropped；拍「做」→ 新建 plan 引用报告，不走 issue 实施。

## 本轮产出

- 报告 [reports/26-10-01-2347-report-transmission-compat-feasibility.html](../reports/26-10-01-2347-report-transmission-compat-feasibility.html)（11 节 + 附录：49 个 qB 端点 → tr RPC 映射表）。
- 档案 [tasks/26-10-01-backend-transmission-compat.md](../tasks/26-10-01-backend-transmission-compat.md)（立档阈值 #4：已产出 reports/ HTML 制品）。
- issue 26-10-01-2212 状态 Open → In Progress，补齐三方认领链（issue ↔ 报告 ↔ 档案）。

## 关键结论（详情在报告，此处不复制论证）

- 调用面集中：49 个 qB 端点全收在 `core/qbapi.py`（413 LOC）；全仓 `downloader` / `client_type` / `backend_type` **零命中** —— 下载器从未被设计成可替换插槽。
- 类型面渗透：`TorrentRecord` 70 个槽名逐字等于 qB 字段名且**无翻译层**；向上穿透前端（29 JS / 10,742 LOC 直吃 qB 字段名），向外穿透规则 DSL 的 70 个 `tor.*`（**已发布对外契约**），向下穿透持久化键（hash 作稳定主键，横跨 35 文件）。
- 唯一干净解耦项：`infra/file_access.py`（393 LOC），可直接复用。
- **修正了起手假设**：tr 4.0+ 有 `torrent-added-verify-mode: fast`（默认），可**条件**跳过完整校验，其条件与 auto-qb 自己的跳检前置 filelist 检查同向 —— 所以不是「能力缺失」，而是「能力不可控」。这才是建议不做的真正理由（辅种核心流程从确定性降级为启发式，失败模式是静默的完整校验）。

## 未决

- 结论待拍板。三条重开条件见报告 §10：① tr 上游提供 per-add 校验控制 ② 出现可点名的真实 tr 用户需求 ③ 因其它原因要建下载器抽象层（届时 tr 边际成本大幅下降）。
