# 26-09-25 WebUI 设置页控件两处打磨 (规则引用下拉 / 启用开关)

> 摘要: 用户指令「修复问题: ①设置页站点设置中『从已有规则集/规则中选择』按钮变形过高; ②设置页中所有
> 『启用』按钮稍微调小, 且未启用与启用两态颜色相近、一眼分不出」。两条都在 `shared/console_hub.css`
> 一处收口(两套 UI + 五个主题同担), 已修完并用真浏览器量到数字。**已入库 `c4fcc0c`**。
> 触发: 设置页控件, 规则引用下拉, 从已有规则集/规则中选择, 变形过高, 启用开关, 开关偏大, 两态分不出, hb-switch, hb-list
> 最后活动: 2026-09-25 18:20

## 状态

**Done(2026-09-25, 已入库 `c4fcc0c`)。** 全量 `test.full` **1601 collected: 1600 passed + 1 skipped / 0 failed**
(与 [testing/baseline.md](../testing/baseline.md) 顶部一致, **基线数字无需改动** —— 纯 CSS 改动, 不触及
任何 `.py`, 覆盖率同基线)。

## 两条根因(都在 `.hb-ct` 那条"定宽"规则上)

1. **下拉变形过高 = `flex-basis` 跨方向串味。** `.hb-ct .hb-input, .hb-ct .hb-select { flex: 0 1 250px }`
   是**后代**选择器, 会命中 `.hb-ct` 内所有嵌套层级; 而 `rules_ref` 的独立下拉是 `.hb-list` 的**直接子项**,
   `.hb-list` 是 `flex-direction: column` ⇒ flex-basis 落到**主轴 = 高度**上, 把它撑成竖条。
   真浏览器实测: 该下拉 **460×250**(同一条选择器在 row 方向的 `enum` 下拉上是正常的 250×37)。
   修法: `.hb-list > .hb-select { flex: none; }` —— 只复位这个方向, 不动 `.hb-ct` 那条(它服务横向排布的
   enum / unit 下拉, 改它会把 unit 下拉宽度一起改掉)。
2. **两态分不出 = 静息态底色借了 `--tone-line`。** 原 `.hb-sw-track { background: var(--tone-line) }`
   = `accent 45% 透明`, 与选中态的**实心 accent 同色相、只差透明度**(实测 atlas: `rgb(59,130,246)/0.45`
   vs `rgb(59,130,246)`), 只能靠滑块位置分辨。改为中性实心底 `--border-strong` ⇒「关 = 中性灰蓝实心,
   开 = accent 实心」一眼可分; 两态文字同步拉开(`--fg-dim` → `--fg`)。
   尺寸按用户要求整族等比收 0.86: **44×24 / 18 / 20 → 38×21 / 15 / 17**(比值不变)。

## 本轮完成

- **`src/auto_qb/webui/static/shared/console_hub.css`**(唯一改动文件):
  - `.hb-switch` 段: 尺寸整族收一号 + 静息态底色 `--tone-line` → `--border-strong` + 文字两态拉开;
    段首注释写明"原来是什么 / 为什么改 / 实测数字"。
  - `.hb-list` 段: 新增 `.hb-list > .hb-select { flex: none; }` + 方向串味的成因注释。
  - 文件头「原样复刻」的表述改掉(现已偏离样张): 明确两类偏离 —— ①工程化替换(前缀/令牌)
    ②**用户实测后按需调过的控件**; 并立规: 这类改动必须在对应规则处写清"原值 / 动机 / 实测数字",
    且**样张 `resources/` 保持原值不动**(它是设计参考素材, 不是交付物)。
- **验证(真浏览器量 computed 值, 不是肉眼看)**: 临时量测台(系统临时目录, 未入库)加载**真实 CSS** +
  从 `tpl-hub-field` 抄下来的真实结构, headless Chrome `--dump-dom` 回读 `getBoundingClientRect`。
  三个变体同测(atlas / prism-ocean 暗 / prism-frost 浅), 修复前后逐项对比:
  下拉 460×250 → **460×37**; 开关 44×24/18/20 → **38×21/15/17**;
  静息底 accent@45% → 中性(`#37455f` / `#34507c` / `#b3c9de`, 均为各主题 `--border-strong`);
  同页 `enum` 下拉 250×37 **未受影响**(无回归)。另出前后对照截图三张(临时目录)。
- **知识库**: 新坑入 [pitfalls/web-ui/layout-css.md](../pitfalls/web-ui/layout-css.md)(flex 简写跨方向串味);
  [progress/implemented-webui.md](../progress/implemented-webui.md) 补首条; 本切片。

## 下一步

1. ✅ 已入库 `c4fcc0c`(与后续的「经典页死代码清理」同一个提交; 提交时远端已前进 1 个提交,
   走 `pitfalls/git/history-integration.md`「单提交重放」落回, 详见切片 `26-09-25-1805`)。
2. 用户真机走查: 设置页 → 站点 → 某站点的「要跑哪些规则」, 确认下拉高度正常、右侧对齐;
   再扫一遍各分区的开关, 确认"开/关"一眼可分且尺寸合适(尤其棱镜浅色主题 frost / golden)。
3. ⚠ **`progress/implemented-webui.md` 已贴到 cap**(9,909 / 10,000 字符, 余量仅 91)—— 本次为塞进一条
   已把摘要压到最短。**下次再往这个文件加内容前必须先拆文件或外迁**(按 skill 的拆超标文档五步配方),
   否则 `test_kb_files_respect_caps` 会当场红。
   (本轮后续的「经典页死代码清理」就因此**没有**往这个文件写, 改记进
   [systemPatterns/web-config-editor.md](../systemPatterns/web-config-editor.md)。)
4. ✅ 原「顺带发现但未动」的两处死代码(`.hb-switch-entry` + `tpl-ce-field`/`ce-field`)已按用户指令
   在**同一会话**内移除, 见切片 `26-09-25-1805-webui-deadcode-cleanup`。

## 关键判据(避免重踩)

- **`flex: 0 1 <px>` 这种"定宽"简写不能配后代选择器** —— 换到 column 方向容器就是高度, 且容器高度 auto
  时不会缩回去。静态检查(花括号配平 / 类名配对 / JS 语法)**全过**, 只有真浏览器量 `getBoundingClientRect`
  才暴露 ⇒ 改共享控件的 flex 前先想"它还会被塞进哪个方向的容器"。
- **控件的"关"态不要借 `--tone` 派生色**(`--tone-line` 之流) —— 与"开"态同色相, 用户分不出。
  中性底要挑**两套 UI 五主题都定义**的令牌(`--border-strong` 满足; 别用 `--surface-2`, 暗底上只有白 6%,
  白滑块压上去几乎没对比 —— 与 conventions/webui.md「暂停/其它不铺平」同源)。
- 共享层(`shared/console_hub.css`)**一处改 = 两套 UI × 五个主题同时生效**, 所以"两套 UI 成对改"
  的纪律在这里**不适用**(那条针对 atlas/ 与 prism/ 各自那份 CSS); 但仍必须**三变体都量一遍**,
  因为浅色主题(frost / golden)的令牌取值与暗色是两套。
