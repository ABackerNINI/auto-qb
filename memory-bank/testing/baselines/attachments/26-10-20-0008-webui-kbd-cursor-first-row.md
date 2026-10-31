# 3756 passed + 10 skipped(根, 覆盖率 98%) —— WEBUI 三主表首行光标虚线让位后全量基线

> 摘要: WEBUI 三主表首行光标虚线让位后全量基线
> 基线时间: 2026-10-20 00:08

## 验收数字

```
TOTAL                                                20327    391   6954    262    98%
3756 passed, 10 skipped in 39.46s
```

口径注记:

- 与上基线(22:56 切片)同为 3756 passed + 10 skipped —— 本轮只动前端 CSS 与 e2e, Python 用例数不变, 零回归。
- 首跑(00:08)时 `test_api_traffic_qb_global_24h_reads_only_involved_day_files` 红过一次: 该用例取真实
  `time.time()`, 在本地 00:00~00:10 之间「10 分钟桶 base 与窗尾跨本地午夜」的缝上判 0 而非 null;
  00:10:01 复跑即绿, 与本改动无关(纯 dat 读侧)。本轮未动它, 是否入池待用户决定。
- 前端 e2e(真浏览器): 全量 308 passed / 10 skipped; 其中 `e2e/kbd-scroll-band.spec.mjs` 本轮新增的
  三视图首行间隙断言已红验(撤掉三条 padding → 三视图间隙归 0, 双皮肤双双转红)。

## 本改动面

- `src/auto_qb/webui/static/prism/css/views.css`: `.torrents-dock > .group-table { padding-top: 5px }`
- `src/auto_qb/webui/static/atlas/css/views.css`: 同规则 6px(components.css 的 700 行 cap 已满)
- `src/auto_qb/webui/static/console/css/components.css`: 同规则 6px
- `e2e/kbd-scroll-band.spec.mjs`: Home/End 用例内补三视图「首行顶 - 列头底 >= 4px」断言(双皮肤)
- 知识库: 任务档案 `tasks/26-10-20-webui-kbd-cursor-first-row.md` + 坑档 `pitfalls/web-ui/kbd-cursor-first-row-gap.md`
