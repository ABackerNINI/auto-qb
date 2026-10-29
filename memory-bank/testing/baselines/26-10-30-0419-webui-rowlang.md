# 4086 passed + 2 skipped(根) —— 主表行语言 A/B 双实施后全量

> 摘要: 主表行语言 flat(平板发丝线)/wave(斑马+波即高亮) 双实施落地后全量基线; 挂载面为 shared/row_lang.css 单点 + groups.html 主表容器 rl-scope + topbar 行语言菜单 + 三皮肤 index.html 挂载; rowlang.js 的 localStorage 持久化使 test_webui_error_history 的 shared/ 层 setItem 基线 +1
> 基线时间: 2026-10-30 04:19

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-30 实测, 全量 137.10s, 建档 04:19):

```
  TOTAL                                                21061     99   7126    102    99%
  4086 passed, 2 skipped in 137.10s (0:02:17)
```

- 汇总行: **4086 passed + 2 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%, missed 102)。
- 逐条口径注记:
  - 相对上一可用基线(`26-10-30-0251-webui-traffic-gap-zone-tips`, 4065 passed + 10 skipped)的
    +21 passed / -8 skipped 来自两者之间的其它轮次与本轮: 本轮 test.webui 系守阵全绿
    (`test_webui_static_skins` 23 / `test_webui_static_dom_panel` 60 / `test_webui_static_dom_page` 34 /
    `test_webui_ctx_menu_registry` 5), `test_webui_error_history` 首跑 1 红
    (rowlang.js 新增 1 条 localStorage.setItem, shared/ 层 setItem 逐文件计数超基线) ——
    按该守阵行内口径「既有功能加写入属合法演化: 改基线并行内注明」补
    `rowlang.js: 1` 后全绿; 最终全量一次通过, 零失败。
  - 阶段 5 不改面核对(计划 §04-5/§06 Q5)随本基线留痕: row_lang.css 全部 40 条规则组 / 50 个选择器分支
    均带 `html[data-rowlang=…]:not(frost):not(golden) + .rl-scope` 双前缀(脚本逐行核对, 零例外);
    `.rl-scope` 全仓唯一挂点 = `shared/tpl/groups.html` 主表容器; `shared/dt_table.css` 与
    row_lang.css 选择器零交集; 抽屉落点 `dock.html` 的 `.drawer-dock` 在 `#app` 直下、不在
    `.rl-scope` 后代树内, 抽屉面结构上不可命中。

## 本改动面

- `src/auto_qb/webui/static/shared/rowlang.js` + `src/auto_qb/webui/static/shared/row_lang.css`: **新建**
  (行语言引擎 + 结构规则单点, 计划 26-10-30-0217 阶段 1/2/3/4)。
- `src/auto_qb/webui/static/shared/tpl/topbar.html`: 主题菜单加「主表行语言」分组(.rowlang-item 两条)。
- `src/auto_qb/webui/static/{atlas,console,prism}/index.html`: head 挂 rowlang.js + views.css 后挂 row_lang.css。
- `src/auto_qb/webui/static/prism/css/components.css`: 菜单条目样式并选择器复用 theme-item 规则 + frost/golden 下整组隐藏。
- `src/auto_qb/webui/static/shared/tpl/groups.html`: 主表容器挂 `rl-scope`。
- `tests/test_webui_static_skins.py`: shell 体量 cap 214→218 + 首格过渡守阵豁免 row_lang.css(::before 本体动效)。
- `tests/test_webui_error_history.py`: STORAGE_WRITE_BASELINE 补 `rowlang.js: 1`(行内注明来源)。
