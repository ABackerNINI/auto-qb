# 5912 passed, 2 skipped (146.20s), 覆盖率 99% (26254 stmts / 48 miss) —— 双排路径上排删除线替代透明度分层: 全量绿

> 摘要: 双排路径上排删除线替代透明度分层: 全量绿
> 基线时间: 2026-11-10 08:44
**Refs:** memory-bank/tasks/26-11-10-webui-relocate-pair-visual.md

## 验收数字

`commands run test.full` 实测输出誊写:

```
TOTAL                                                26254     48   9150     58    99%
5912 passed, 2 skipped in 146.20s (0:02:26)
```

## 本改动面

- `src/auto_qb/webui/static/shared/row_lang.css`: `.rl-scope .rel-pa` 去 `opacity:.55`, 改 100% 不透明 + `text-decoration: line-through`; 迁移展示注释块口径同步(上排 = 删除线旧值)。下排、弧形箭头、tone 着色、rel-pulse、浮窗与四皮肤令牌零改动。
- `tests/test_webui_relocate_visibility.py`: 新增 `test_p1_pair_upper_row_uses_strikethrough_not_opacity`(正则取 `.rel-pa` 规则块, 正反双断言) + 头部「## 测试计划」清单同步; 红验双验留痕(旧 CSS 反断言红 / 只去 opacity 时正断言红 / 最终态绿)。
- `memory-bank/conventions/webui.md`: 「迁移状态展示口径(路径列)」现状句改述(层级靠形状差异, 两排同色 100% 不透明)。
- `memory-bank/plans/26-11-07-2344-plan-relocate-status-display.html`: 追加 D18(D6 部分修订)行 + `kb.bump` 抬 doc-updated 与 R4; 原 D6 行保留作历史。
- `memory-bank/plans/attachments/relocate-status-display-v2-mockup.html`: 四状态 `.aq-pa` 由 `opacity` 改 `text-decoration:line-through`, 头部加修订注释。
- `memory-bank/pitfalls/web-ui/opacity-tier-ghosting.md`(新) + `kb.index` 生成物 `web-ui/_index*.md`; 任务档案与本切片(记账类)。
- 分批只读评审零发现(`review.check` 0 条 / 通过 0 / 弃 0); 齐平后重算 `review.pack` 基哈希 `101f0904651a` 未变, 无需复评。
