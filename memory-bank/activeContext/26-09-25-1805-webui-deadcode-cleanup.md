# 26-09-25 WebUI 经典设置页遗留死代码清理 (ce-field / tpl-ce-field / .ce-* CSS)

> 摘要: 用户指令「移除死代码, 然后提交」。清掉经典设置页(`7fcdc9c` 移除)留下的三处遗留:
> ①`tpl-ce-field` 模板块(两套 index.html, 唯一引用是**自身模板内的递归** ⇒ 永不可达) +
> `ce-field` 组件注册; ②其行为基座 `CE_FIELD_COMPONENT` → `CE_FIELD_BASE`(去掉 `name`/`template`,
> **逻辑层不能删** —— hub 侧靠它拿全部 `cfg*` 读写); ③只被该模板引用的 **40 个 `.ce-*` 类**
> (含 `is-pattern`/`ceg-*` 动态类)共 **177 条 CSS 规则 / 约 250 行**, 外加 `.hb-switch-entry`、
> `.logs-page` 两处历史死类。**已修完并验证, 已提交。**
> 触发: 死代码, 死类, 经典设置页遗留, tpl-ce-field, ce-field, CE_FIELD_BASE, ce-* CSS, hb-switch-entry, logs-page
> 最后活动: 2026-09-25 18:05

## 状态

**Done(2026-09-25, 已提交)。** 全量 `test.full` **1600 passed + 1 skipped / 0 failed**(与基线一致);
浏览器冒烟 **94 项 0 失败**(与清理前逐项相同); 反向校验"被引用但 CSS 无定义"的集合**未扩大**。

## 关键判据(为什么"逻辑层不能删")

- `window.HUB_FIELD_COMPONENT = Object.assign({}, window.CE_FIELD_COMPONENT, {name, template})`
  ⇒ 基座里的 `props` / `inject` / `provide` / `methods` 是 **hub-field 的全部读写逻辑**。
  所以本次只做**去组件化改名**(`CE_FIELD_COMPONENT` → `CE_FIELD_BASE`, 摘掉 `name`/`template`),
  **不删对象**; 删 `app.component("ce-field", …)` 注册 + 两处 `tpl-ce-field` 模板。
- 守阵 `_scan_mixin_wiring` 的"`window.X = {` 定义即需接线"会把改名后的基座判红 ⇒ 已给守阵加第三种
  "已接线"形态: **被另一个全局用 `Object.assign({}, window.X, …)` 拷走**也算接线(不是放宽成"出现即算")。
  **红绿双验**: 摘掉这条新规则 → 报 `定义了 window.CE_FIELD_BASE 但 app.js 没有 app.mixin(…)`; 装上 → 0 问题。

## 死类判定与验证(可复用)

1. **死类集** = CSS 定义集 − 语料引用集(html 的 `class=`/`:class=` 属性 + js 字符串字面量, 先剥注释)。
2. ⚠ 两个必须处理的边界: **动态类**(`'ceg-' + n` / `is-pattern` 不在语料里, 靠差值捞)与
   **混合选择器**(`.pop-count, .ce-num, .hist-axis text` 里没前缀的活类最易漏算 —— 只挑带前缀的类
   会把整条规则误判成纯死而**整条删掉**)。
3. **决定性校验**: 每个死类在 index.html 里的**全部**出现是否都落在被删模板的行区间内(脚本比对, 40/40 通过)。
4. **反向校验**(防"删多了"的机械兜底): "被引用但 CSS 无定义"的集合与 HEAD 对比**不得扩大**
   —— 实测 2 → 1(少的那个 `ce-subcard-body` 本来就只被被删模板引用)。
5. 真浏览器复量: 桩服务 `ui_harness.py --port 8098` + `ui_smoke.cjs`(94 项) + 一次性定点脚本
   (设置页 → 站点分区 → 量 `hb-list > .hb-select` 与 `hb-switch`)。
   实测: 规则引用下拉 **460×37**(不是 250 竖条)、开关 **38×21**、两态底色
   atlas `rgb(55,69,95)` vs `rgb(59,130,246)` / prism-frost `rgb(179,201,222)` vs `rgb(61,106,163)`。
6. 花括号配平(11 份 CSS 全 OK) + `test_web.py::test_frontend_static_bundle_health` 全过。

## 改动面

- **模板**: 两套 `index.html` 删 `tpl-ce-field` 整块(atlas −156 行 / prism −160 行, 含说明注释)。
- **JS**: `config_editor.js` 基座去组件化改名 + 注释重写; `config_hub.js` 改引用; `app.js` 删注册。
- **CSS**: `atlas/style.css` −182 行; `prism/css/views.css` −69; `prism/css/components.css` −84;
  `prism/css/base.css` 摘混合选择器里的 `.ce-num` 分支; `shared/console_hub.css` 删 `.hb-switch-entry`。
  顺带退役只被死规则引用的自定义属性 `--ce-label-w` / `--ce-ctl-gap` / `--ce-row-pad-x`
  (`--ce-input-max` 保留 —— 仍被活规则 `.ce-note` 引用)。
- **守卫**: `test_web.py` 的 `_scan_mixin_wiring` 加第三种接线形态 + 两处历史注释按事实更新
  (`_scan_css_blocks` 的判据来源规则已删, 标注为留档)。
- **知识库**: `systemPatterns/web-config-editor.md` 补「经典页死代码清理」条并订正 `ce-field` 表述;
  新坑入 `pitfalls/web-ui/template-render.md`「删死模板要连带清它独占的 CSS」。

## 遗留

- ⚠ **未做**(不属本次指令范围): `tpl-ce-field` 删除后, `hub-field` 是否还覆盖原 `ce-field` 支持的全部
  字段类型(尤其嵌套 `item.items` 分组)未逐项走查 —— 现状是 `cfgFlatten` 已把嵌套扁平化, 冒烟与真机
  设置页均正常; 若后续发现某类字段不渲染, 从这里查起。
- `progress/implemented-webui.md` 仍在 cap 边缘(9,909/10,000), 本次记录改记进 `systemPatterns/`。
