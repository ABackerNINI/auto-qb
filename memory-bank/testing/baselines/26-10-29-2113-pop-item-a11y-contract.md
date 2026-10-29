# 4053 passed + 10 skipped(根) —— pop-item a11y 三分类契约修复后全量基线(issue b-r23a09-pop-item-a11y-contract)

> 摘要: pop-item a11y 三分类契约修复后全量基线(issue b-r23a09-pop-item-a11y-contract)
> 基线时间: 2026-10-29 21:13
**Refs:** memory-bank/issues/26-10-29-1335-bug-b-r23a09-pop-item-a11y-contract.html

## 验收数字

`commands run test.full`(pytest `-n 8 --cov-branch --cov-fail-under=99`(pytest.ini addopts, TMPDIR 由 task 内置); 2026-10-29 实测, 全量 125.24s, 建档 21:13):

```
  TOTAL                                                20803    117   7126    108    99%
  4053 passed, 10 skipped in 125.24s (0:02:05)
```

- 汇总行: **4053 passed + 10 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记:
  - 本轮新增守阵 1 条: `test_webui_static_dom_panel.py::test_frontend_pop_item_a11y_contract`(三分类契约逐项钉)。
  - 「10 skipped(根)」为既有环境条件 skip, 与本轮无关(上一基线 26-10-29-1835 同为 10 skipped)。
  - 红验(修复前): `test.one -- tests/test_webui_static_dom_panel.py -k pop_item_a11y` **1 failed**(首断言恰缺 role="combobox", 红在缺口上); 修复后 `test.one -- tests/test_webui_static_dom_panel.py tests/test_webui_static_dom_page.py` **90 passed** 全绿。
  - 运行时冒烟: `npm run test:e2e:fast`(真浏览器 fast 子集) **228 passed**(9.6m) —— 添加种子三候选/设定位置对话框/渲染健康(双皮肤 Vue 挂载无运行时错误)直接踩过本轮改的模板。

## 本改动面

| 文件 | 改动 |
| --- | --- |
| `src/auto_qb/webui/static/shared/tpl/combo-input.html` | combobox 组件模板补 ARIA(单组件一处, 五调用点继承零改动): 输入框 role=combobox + :aria-expanded + aria-autocomplete=list + :aria-controls(仅开层时指面板, 关层 null 防悬空引用) + :aria-activedescendant(带界只指真实候选); 面板 role=listbox + :id=inputId+'-pop'; 两处 v-for 变体候选行 role=option + :id=comboOptId(i) + :aria-selected; 预置行 aria-hidden(不参与索引不配 option); 头注续写 .pop-item 三分类 a11y 契约判据(菜单式/选择式/导航式 + 同族参照) |
| `src/auto_qb/webui/static/shared/add_torrent.js` | aq-combo-input 组件新增方法 comboOptId(i) —— 候选 id 生成式单点(输入 aria-activedescendant 与行 :id 同一来源, 各写一份必漂移); 带参判定走 method(带参 computed 是静默白屏坑) |
| `src/auto_qb/webui/static/shared/tpl/topbar.html` | 列选择器项补 @keyup.space.prevent(与筛选器项逐字同款 handler, Space 无反应消除); UI 切换项补 :aria-current="o.id === ui ? 'page' : null"(导航式当前项标注, 不改视觉) |
| `tests/test_webui_static_dom_panel.py` | 新增守阵 test_frontend_pop_item_a11y_contract(输入侧五属性/面板 listbox/两变体 option 语义/id 单点计数/预置行 aria-hidden/列选择器双键/筛选器基准锚/aria-current) + 头部「## 测试计划」补 1 行 |
| `memory-bank/issues/26-10-29-1335-bug-b-r23a09-pop-item-a11y-contract.html` | 状态 Open → In Progress → Done(复验/实际修法/验证方式回填); doc-refs 反向声明本切片 |

**未改**: 右键菜单族(.ctx-item)键盘化(issue 06 明确不做, 重开另立件, 三分类契约即其判据底稿); 视觉高亮通道(.on/data-hi/CSS)零触碰 —— 纯属性层修复, 无布局与观感变化。
