# 3755 passed + 2 skipped(根, 覆盖率 98%) —— 流量与限速页去嵌套 + 只读状态行宽度修复后全量基线

> 摘要: 3755 passed + 2 skipped(根, 覆盖率 98%) —— 流量与限速页去嵌套 + 只读状态行宽度修复后全量基线
> 基线时间: 2026-10-19 19:38

## 验收数字

`commands run test.full`(2026-10-19 19:37 实测, 127.8s):

```
3755 passed, 2 skipped in 124.88s (0:02:04)
TOTAL   20504   376   6914   256   98%
```

口径: 根套件(pytest.ini 的 8 worker); `TOTAL` 列序 = 语句数 / 未覆盖 / 分支数 / 部分分支 / 覆盖率。
e2e 侧本轮只跑相关子集: `commands run dev.e2e -- e2e/views.spec.mjs --grep "流量与限速|单位控件"`
6 passed(双皮肤 × 3 条: 来源块闸门 / 工具参数单位控件(含新增的只读行宽度断言) / 三区同屏+折叠+历史图入口)。

回写后复验(2026-10-19 19:43): 补完切片 / 坑档 / 结构文档后重跑 `commands run test.full` 得
**3755 passed, 2 skipped**(121.78s), `TOTAL 20504 / 376 / 6914 / 256` 与上表逐位一致(覆盖率同 98%,
耗时差为机器负载)。中途两红均已消且非代码问题: ① 切片摘要里带了裸 `passed` 数字 ⇒ 数字守阵 +2,
改成「见 kb.baseline」后复绿; ② 同一条措辞守阵, 同一个根因。

## 本改动面

- `webui/static/shared/tpl/traffic-card.html`: 去掉同名外壳卡(`.hb-blk.hb-cut` + 卡头「流量与限速」),
  三区提升为页面级 `.hb-blk.hb-cut` 块(区头折叠不变); 卡头内容下沉为 `.hb-tl-bar`(现状摘要 +
  「打开历史图表」)。根节点改 `.hb-tl` 纯包裹层。
- `webui/static/shared/console_hub.css`: `.hb-ro`(只读摘要容器, `max-width:460px`)改名
  `.hb-ro-sum`/`.hb-ro-sum-line`, 与行修饰 `.hb-row.hb-ro` 解撞; 新增 `.hb-tl-bar` / `.hb-tl-sum`;
  `.hb-tl-dep` 由卡内通栏改为独立提示条(自带边框与下边距)。
- `webui/static/shared/tpl/xtpl.html`: readonly 列表/对象摘要分支跟着改名(`hb-ro-sum*`)。
- `webui/static/shared/config_hub.js`: `traffic_limit` 的 lede 文案去掉「这一张卡」「卡头」口径,
  改按三区名指路。
- `tests/test_web_traffic_limit_card.py`: 三区结构断言补「页面级 `hb-cut` 且无同名块标题」;
  历史图入口断言改钉 `.hb-tl-bar`。
- `tests/test_web_traffic_monitor.py`: 新增 `test_frontend_readonly_row_class_not_colliding`
  (裸 `.hb-ro` 选择器必须为 0 + 摘要容器改名成对 + 模板跟随改名)。
- `e2e/views.spec.mjs`: 三区选择器改页面级; 新增「页面只有一条『流量与限速』」与
  「`.hb-row.hb-ro` 铺满所属块、值列 > 400px」两条真 DOM 断言。
