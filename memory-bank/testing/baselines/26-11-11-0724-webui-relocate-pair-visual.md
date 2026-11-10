# 6007 —— webui 双排title退役批收尾全量

> 摘要: webui 双排title退役批收尾全量
> 基线时间: 2026-11-11 07:24

## 验收数字

TOTAL                                                26747     55   9362     66    99%
6007 passed, 2 skipped in 145.49s (0:02:25)

## 本改动面

- `src/auto_qb/webui/static/shared/tpl/xtpl-cells.html`: 组行/种子行两个 save_path 分支原生 `:title` 改条件绑定 —— pair 双排置 null(原生 tooltip 退役: A/B 两排已明文 + relocate_pop.js 悬停浮窗全量), 单排(无标注/one)保留供截断路径看全文; 判定谓词与 sp-body 隐藏同一 `mode !== 'pair'`。
- `tests/test_webui_relocate_visibility.py`: 守卫断言 `mode !== 'pair'` 计数 2→4(sp-body 隐藏 + title 置空各一处 × 2 分支), 注释与文件头测试计划同步; `test_p1_pair_rendered_in_path_cells` 更新。
