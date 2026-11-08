# 5753 passed + 2 skipped(根) —— R3 批次基线: 位置集匹配 + 两排路径 chip 点击筛选

> 摘要: R3 批次基线: 位置集匹配 + 两排路径 chip 点击筛选
> 基线时间: 2026-11-08 08:25

## 验收数字

```
TOTAL                                                25635     12   8870     34    99%
5753 passed, 2 skipped, 7 warnings in 148.86s (0:02:28)
```

实测 2026-11-08 08:25, `commands run test.full`(151.5s)。较上基线(26-11-08-0713, 同为 5753+2):
用例总数持平(守阵改写 3 例不增数, 新增 e2e spec 不进 pytest 面), 覆盖率语句缺失 12 不变。

## 本改动面

- 生产: `webui/static/shared/tpl/xtpl-cells.html`(组行/种子页两 save_path 分支: pair 隐藏原单排路径行, A/B 排 +f-cell/+f-on/@click filterFromChip)· `shared/decorate.js`(+`_pathPositions` 位置集单点 + `RELOCATE_ACTIVE_STATES`)· `shared/filters.js`(_facetPick/组级谓词/虚拟行谓词 三处换位置集)· `shared/hr.js`(_memberPass 换位置集)· `shared/state.js`/`shared/relocate_pop.js`/`row_lang.css`(注释口径 D16/D17 同步 + 删 has-relpair .sp-body 死规则)
- 守阵: `tests/test_webui_relocate_visibility.py`(3 用例改写: pair 替换断言/位置集匹配矩阵/pathOpts 计数; 红验先行 3 例对旧生产红)
- e2e: `e2e/relocate-pair-filter.spec.mjs` 新增(两皮肤: pair 替换单排/B 排筛 dst 且 done 不命中/toggle/f-on/A 排筛 src)
- 文档: 计划 26-11-07-2344 R3+D16/D17 回写 · `conventions/webui.md` 迁移展示口径段
- e2e 全量(非本基线口径): 460 passed / 2 failed = 存量 issue 26-11-08-0820(move-note strict collision, 与本批无关)
