# 添加种子三下拉 label 闪烁「第三轮」修复

> 摘要: 用户报 a7ebbe14(第二轮)未修住「点字段 label 稳定复现下拉闪烁」。真浏览器事件埋点定位:
> label 的 **mousedown** 默认动作先 blur 输入框, addPopBlurClose 的 40ms 合帧定时器在**人手按住
> 期间**(80~150ms 必 > 40ms)先收层, 松手 label click 默认动作回焦重开 = 每次必闪。第二轮走查
> 全绿是因为 Playwright 默认点击 down/up 只隔 ~2ms, 撞不上 40ms 窗。修法 = 四个字段 label 一律
> `@mousedown.prevent`(根除 blur, 竞态消失; @click.stop 保留挡 window 收层), 关闭态点 label 仍
> 正常聚焦+开菜单。
> 最后活动: 2026-10-04 00:54

## 已完成 (2026-10-04)

- **根因定位(事件埋点探针, atlas/prism 双皮肤一致)**: 点 label 事件序 = mousedown(label) →
  blur+focusout(related=null) → mouseup → click(label) → **focus/focusin(回焦, label click 默认
  动作)** → 转发 click(输入框)。focusout→focus 间隔 == 按住时长: delay=0 时 1.2ms(定时器不触发,
  无闪烁), delay=150 时 155ms(定时器 40ms 处触发收层, 116ms 后回焦重开) —— rAF 时间线实测
  `open=false`(1597ms) → `open=true`(1713ms)。
- **修复**: `dialogs-mgr.html` 三个字段 label + `popovers.html` meta 分类 label 加
  `@mousedown.prevent`(模板注释改写真根因); `add_torrent.js::addPopBlurClose` 注释修正(2ms 假象
  → 按住时长真相), 40ms 窗口只兜点空白/Tab 这类瞬时焦点迁移。
- **守阵**: `test_web.py::test_frontend_add_combo_label_clear_mask_and_refit` 第 1 组断言扩为
  `@mousedown.prevent + @click.stop` 双断言, docstring 与「测试计划」头同步改写。
- **终验**: 三皮肤 × (三字段 + meta 分类) × 两场景 24/24 —— 开着按住 150ms 点 label 零翻转
  (flips=[]), 关着点 label 正常开且焦点落位; 根因侧 pre-fix 探针复现闪烁(post-fix 消失)。
- **收尾**: 坑档 `combobox-focusout-close.md` 复发+1(第三轮条目 + 摘要/触发词改写 + 教训: 合成
  零延迟点击验证不了按住时序竞态, 走查必须 delay>=120ms); 基线切片 26-10-04-0054;
  progress 条目; kb.index 重建。

## 待办 / 观察

- **计划外既有不对称已入池(未修, 范围守恒)**: [26-10-04-0130-bug-webui-add-pop-mutex](../issues/26-10-04-0130-bug-webui-add-pop-mutex.html)
  —— `openAddCatMenu`/`openAddTagMenu` 不收 `addPathPop`(反向却收), 切换字段时路径面板与下拉
  双开且面板可盖住相邻字段 label。待用户指派认领。
