# backend-hr-carpt-site — HR 在线核实接入 CarPT

> 摘要: v3.5 已落地并经用户补交的 status=2 已达标样张(17 行)验证通过 —— 表头/档位/无秒完成时间全解析正确;
> 验证挖出真缺陷已修: **H&R ID 与种子 id 是两个 id 空间** ⇒ 新增 `HrEntry.dl_id`(行内链接提取) +
> service 下载 `entry.dl_id or tid`。全量 1693 passed + 1 skipped(TOTAL 91%), 基线 `26-09-27-1246`。
> 仍待真机: A 考察中页形态(还需做种/剩余考察实值、操作列是否有下载链接)。**提交轮: 已合并远端
> aeca1fb + 合并树重测零漂移, 随主提交入库**。
> 最后活动: 2026-09-27 12:54

## 本轮事实

- 用户令: 「HR在线核实添加支持站点: CarPT, 模板在 C:\Users\11059\Desktop\Projects\PT页\CarPT\HR」(样张 = 已登录空表页)。
- 样张差异点(与 BTSchool 标准): `?status=N`(1 考察中/2 已达标/3 未达标/4 已免罪)、`td.colhead` 十列、
  首列「H&R ID」、「下载完成时间/剩余考察时间」列名、末尾多备注/操作两列; 分页仍 nexus-pagination。
- 落点: `hr/adapters/nexusphp.py`(参数化) · `hr/adapters/carpt.py`(新) · `hr/adapters/__init__.py`(注册) ·
  `hr/fetcher.py` + `hr/report.py`(`_scope_of`) · `config/schema/hr.py`(文案) · `tests/test_hr_parse.py`(+5) ·
  fixture ×2。
- 配置写法: `trackers.carpt.hr_check: {mode: partial, adapter: "carpt", hr_page_url: "https://carpt.net/myhr.php", ...}`
  (**用户生产 config.yml 自行添加, 红线 AI 不动**)。
- 档案: tasks/26-09-22-backend-partial-hr-verify.md(v3.5 行 + 进度日志); 基线 `26-09-27-1235-hr-carpt-adapter`。
