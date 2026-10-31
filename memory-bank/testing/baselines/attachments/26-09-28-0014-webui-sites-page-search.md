# 基线 · 1812 passed + 3 skipped —— 站点页搜索轮(webui-sites-page-search)

> 摘要: 设置页「站点」二级页搜索落地(计划 26-09-27-1852): 名称/域名/标签/分组/删标/规则/限速/HR
> 全字段前端匹配, 语法照搬种子搜索(空格 AND / -词排除 / "短语"), 命中列表+详情左右分栏 + 命中字段
> chip。纯前端四文件(settings.html / config_hub.js / config_editor.js / console_hub.css), Python
> 运行时零触碰; 守阵 +1(test_frontend_tracker_search_wiring)。
> 数字取自实施完成实测(`commands run test.full`; 开工已先合并远端 7 笔 6262d3b→c7dfbd2)。
> 基线时间: 2026-09-28 00:14
> 档案: memory-bank/tasks/26-09-28-webui-sites-page-search.md

- **测试增量**: +1(`test_frontend_tracker_search_wiring`: 模板接线 / CJK 安全归一化 / 双清空路径 /
  pill 无键数徽标 / hb-tr-* CSS 成对)。另 `_common.CAP_POLICY["index-auto"]` 12000→12100
  (sites-page-search 专题入册后 _doc-map 12,006 超 cap), 守阵 test_skill_cap_table_matches_cap_policy
  随 SKILL.md 表同步。

TOTAL 1812 passed + 3 skipped / 91%(12355 语句 / 914 未覆盖 / 4198 分支 / 387 partial, test.full 16.6s)
对比前基线(26-09-27-2326): 1811 passed + 3 skipped / 91%(12355 语句 / 914 未覆盖 / 4198 分支 / 387 partial)
—— passed +1(新增守阵), 其余全部持平, 零回归。
覆盖率口径见 [baseline.md](../../testing/baseline.md)。
