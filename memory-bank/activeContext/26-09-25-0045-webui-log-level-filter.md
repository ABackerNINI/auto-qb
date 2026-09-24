# 运行日志按等级查看恒空(生产格式无方括号) — 已修复待提交

> 摘要: `/api/log` 等级过滤写死 `[LEVEL` 字面量, 生产 format(无方括号)下恒空; 已改为按配置 format 反推等级字段位置 + "筛不了"回全部行加 note。修复与验证全部完成; 提交前与主线 M2/M3 五笔合流(补丁→ff-only→3way 施回), 合流后全量 1527 collected: 1526 passed + 1 skipped。
> 最后活动: 2026-09-25 01:10

## 正在进行

- 无 —— 修复、测试(1383 passed + 1 skipped)、红验(7 条)、冒烟(82/0)、专项浏览器验证(18/0)、
  知识库回写(pitfalls×3 / baseline / 档案 `tasks/26-09-25-webui-log-level-filter.md`)全部完成。
- 用户已说"提交": 走 `my-commit-flow` 的 ship.commit / ship.push(合流后改动 12 源/测文件 + 8 知识库文件)。

## 关键结论(沉淀给后续)

- 解析"按 format 渲染的文本"不能用字面量锚点 ⇒ 单点 `infra/logging.py::filter_log_lines()`;
  详见 `pitfalls/backend/format-driven-parse.md`(新建主题)。
- 旧 `test_api_log_endpoint` 是摆设断言(手写语料 × 替身 format=`%(message)s`, 配置没被读到);
  样本必须由被测配置生成 ⇒ `pitfalls/testing/assertions.md` 新条目。
- `/api/log` 响应新增 `note` 字段("筛不了"提示语), 前端两套 UI 的两处日志章节成对加了 `.logs-note` 提示条。
