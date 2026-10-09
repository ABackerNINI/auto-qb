# 2870 —— 路径筛选强调框贴文字宽度(sp-body 文字包裹层)基线

> 摘要: 用户报「点击路径筛选后匹配的路径强调框宽度错误, 跟随保存路径栏宽度而不是文字宽度」—— `.f-cell.f-on` 的 inset 描边挂在 grid 拉满列宽的 `.g-save-path` 单元格 div 上, 框随列宽。修法 = 保存路径文字包 `<span class="sp-body f-cell">` 内联块包裹层, 强调/点击/省略全部挪上去(torrents.html + groups.html), 三皮肤 views.css 各增一条 `.g-save-path .sp-body` 规则; 机理单点: pitfalls/web-ui/cell-frame-vs-text-width.md。
> 基线时间: 2026-10-09 21:12

**Refs:** memory-bank/tasks/26-10-09-webui-path-filter-frame-width.md,memory-bank/pitfalls/web-ui/cell-frame-vs-text-width.md

## test.full 实测

- 分支: `develop`(HEAD `aec6e2e8`, 会话开工快进所得; 工作树含本修复 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2870 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标; 25.2s —— 与上基线 42.7s 同区间噪声)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- 收集面差异说明: 上基线 2872+3(合计 2875), 本轮 2870+4(合计 2874)—— 合计 -1 且 skipped +1, 与覆盖率语句数(16567)逐位持平一致; 开工 sync 快进的 1 笔(22988fce→aec6e2e8)夹带收集面变化, 非本修复引起(本修复零 Python 触碰)。
- 增量明细(本轮真正新增): `src/` 改动仅 shared/tpl 2 份(torrents/groups 保存路径格包裹层)+ 三皮肤 views.css 各 1 条规则; 知识库回写件 3 份(任务档案 / 本切片 / 坑档)+ `_index.md` 重建。
- 静态守阵: `commands run test.one -- tests -k webui_static` 69 passed(含三皮肤 700 行体量守阵)。
