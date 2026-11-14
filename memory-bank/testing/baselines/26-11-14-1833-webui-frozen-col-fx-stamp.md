# 6120 passed, 19 skipped(根) —— fx 基线改写固定列修复批全量绿

> 摘要: fx 基线改写固定列修复批全量绿
> 基线时间: 2026-11-14 18:33

## 验收数字

`commands run test.full` 实测(2026-11-14 18:32, Linux env3, 本批工作树):

```
TOTAL                                                27305    221   9588     93    99%
6120 passed, 19 skipped in 95.92s (0:01:35)
```

覆盖率 99%。e2e 另计: pinned 四守阵(main-table-pinned-matrix/-hover/-selected + dt-table-face-bg)81 passed; 本批新增 stamped 行用例(两段式)在内。评审轮修后复跑 test.quick 亦全绿(同数字面)。

## 本改动面

- `src/auto_qb/webui/static/flux/css/fx-mount.css`: D4-7 行板过渡复位规则(修 fx.css [data-fx] 基线顶掉行板过渡的反向竖带)
- `src/auto_qb/webui/static/flux/fx-mount.js`: row-in stamp 实测行高覆写 --fx-row-h + 入场毕摘除(animationend 名/目标双守卫 + 280ms 兜底)
- `e2e/main-table-pinned-matrix.spec.mjs`: 新增 stamped 行用例(生命周期段 + 合成 stamp 缺陷面, oklab->srgb 归一逐帧采样)
- `tests/test_webui_static_skins_table.py`: parity 守阵钉 5(fx 层改写必须带逐字复位)
- `tests/test_webui_static_skins_skin.py`: fx_wiring 钉 stamp 生命周期五件(摘除/行高覆写/名守卫/目标守卫/兜底)
- `tests/test_webui_static_r4_node_batteries.py`: 电池桩补监听面 + 摘除三分支真跑判据
- `tests/test_relocate_units.py`: :928 断言数据改大小写全同(POSIX 平台既有红放行, issue 26-11-14-1727)
- `memory-bank/`: issue 26-11-14-1727 新建(Done) / 坑档 frozen-column 第11条(运行时改写) / 任务档案与切片
