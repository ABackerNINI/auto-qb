# 2958 —— 详情面板变体模板漏包 R() 修复基线

> 摘要: 用户报详情面板出现被转义的 `<span class="dt05-offnote">` 原文; 根因 = 变体模板把内层 T 标签模板的结果**裸插值**进外层模板、漏了 `R()`, 被 `dtHtml` 全量转义成纯文本。修 2 处(05 虚拟条目备注 / 11 筛选空态), 纯前端静态 JS 改动, **零测试面变化**(未新增亦未修改测试)。机理入坑档 `pitfalls/web-ui/template-render.md`。
> 基线时间: 2026-10-10 18:24

## test.full 实测

- 分支: `develop`(会话开工 `my-commit-flow.sync` 两度核验均 `38797291`, 无快进; 工作树含本轮改动 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测 (Windows)**: **2958 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16568 语句 / 165 未覆盖 / 5716 分支 / 142 partial; 门槛 98% 达标; 43.76s)
- 增量明细(本轮真正新增): `src/` 改动仅两份变体模板各 1 行(补 `R()`) + `pitfalls/web-ui/template-render.md` 一条目 + 一份 activeContext 切片; **零 Python 触碰** ⇒ 守阵收集面不变。
- 静态守阵: 详情面板静态 DOM 守阵(`tests/test_webui_static_dom_panel.py`)含在 test.full 内, 全绿; 该修复暂无非回归守阵(见坑档)。
