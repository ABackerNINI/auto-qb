# 2689 —— WEBUI 移除冗余的搜索命中行级高亮收尾 (develop @ 2e2d6789, 源码小修轮)

> 摘要: 移除"保留即命中"的冗余行级 `search-hit` 高亮(种子页种子行 / 辅种页组行 / 追剧页集行 /
> 未识别行), 保留明细成员行与站点挂件"仅命中成员才亮"的高亮及追剧剧行; 同批清 `columns.js::isHit`
> 与组 / 集 / 未识别行的 `hit` 死字段。改动全在 `webui/static`(模板类绑定 + JS), 无测试增删。
> 基线时间: 2026-10-07 03:58

**Refs:** memory-bank/tasks/26-10-07-webui-search-highlight.md

- 分支: develop @ **2e2d6789**(开工 `commands run my-commit-flow.sync` = 已在最新; 本轮尚无本地提交)
- 命令: `commands run test.full`(Windows)
- **实测 (Windows)**: **2689 passed + 4 skipped, 覆盖率 TOTAL 99%(16021 语句 / 163 未覆盖 /
  5472 分支 / 143 partial)**; pytest 自报 **59.24s**(单次采样; 上一条 26-10-07-0251 为 33.75s, 差异属采样波动)。
- 相对上一条 [26-10-07-0251](26-10-07-0251-webui-drawer-tab-traffic-form-guard.md)
  (2689 + 4 / 16021 / 163 / 5472 / 143): 四项覆盖指标与 passed 数**逐位相同零增量** —— 本轮改动
  全在 `webui/static` 静态资源(不进 `--cov=src` 统计), 且无新增 / 改动测试, 收集面不变。
