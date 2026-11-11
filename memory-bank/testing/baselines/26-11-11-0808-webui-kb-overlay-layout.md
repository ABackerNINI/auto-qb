# 6007 —— webui 快捷键覆盖层行布局重排入库基线

> 摘要: webui 快捷键覆盖层行布局重排入库基线
> 基线时间: 2026-11-11 08:08
**Refs:** memory-bank/tasks/26-11-11-webui-kb-overlay-layout.md

## 验收数字

```text
TOTAL                                                26747     55   9362     66    99%
6007 passed, 2 skipped in 152.26s (0:02:32)
```

(实测时点: 本批评审复评零 actionable 后终轮 `commands run test.full` 2026-11-11; 较上片 5999: +8 = 远端并行批合流带入新增用例, 2 skipped 为存量 skip 不变; 本切片为本批组合树的测试数字权威, 其余处一律引用不手抄)

## 本改动面

- `src/auto_qb/webui/static/shared/tpl/settings-detail.html`: 键位编辑全屏覆盖层 section 加 `kb-full` 类(限宽钩子); v-for 分组包进 `.kb-table` 包裹 div(说明段/加载失败段留在网格外), kb-row 开标签两行合一 + kb-note 文本两行合一抵消包裹行数代价, 分片恰 560 行(单分片体量上限)。
- `src/auto_qb/webui/static/shared/console_hub_panels.css`: `.kb-row` flex(名称列 `flex:1 1 200px` 吃满)改 `.kb-table` 单一 grid 三列 `420px minmax(220px, auto) auto`, `width: max-content; max-width: 100%; margin-inline: auto` 居中 + `overflow-x: auto` 兜底; `.kb-grp`/`.kb-row` `display: contents` 展平, 行分隔虚线/录制高亮移到三单元格(列 gap 归 0 用 padding 拉开), rec-tip/conflict `grid-column: 1/-1` 各占整行, `.kb-danger` 加 nowrap; 新增 `.hr-full-modal.kb-full { max-width: 1120px; margin-inline: auto }`(骨架 `.hr-full-modal` 不动)。
- `tests/test_web_shortcuts_drawer.py`: `class="hr-full-modal"` 断言改 `class="hr-full-modal kb-full"` + 新增 `class="kb-table"` 模板锚; CSS 守阵类清单补 `.kb-table`/`.hr-full-modal.kb-full`。
- 验证: Playwright 实机截图目检(dev.webui 最小配置 + dev.sim 仿真 qB)1920/900 两视口; 首截图暴露 kb-note 跨列项 max-content 摊进 auto 轨道把键帽列撑到 ~375px(守阵测不出的观感缺陷), 包裹 div 修复后复截通过。
