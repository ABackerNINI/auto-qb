# 添加种子三下拉「第二轮遗留四项」修复

> 摘要: 上一轮(失焦即收 + 开层限高, `00c6fb16`)之后用户报的四条遗留, 已按根因修复并三皮肤真机验证 39/39。
> 最后活动: 2026-10-03 21:30

## 已完成 (2026-10-03)

- **①点字段 label 稳定复现下拉闪烁(保存路径/分类/标签 + 排查出的第 4 个: meta 对话框分类)**:
  输入框已聚焦时点 label 不 blur, 所以上一轮补的 @focusout 完全不参与; 真链条是「label 的 click
  冒泡到 window ⇒ lifecycle 收层名单关菜单 ⇒ label 默认动作把 click 转发给 for= 的输入框 ⇒ 重开」
  = 关了又开, 每次都这样 ⇒ 稳定复现。修法 = 四个字段 label 一律 `@click.stop`。
- **②三个 combobox 没有 x 清除**: 内嵌 `.add-pop-clear`(三皮肤 CSS 成对: absolute 钉右内侧 +
  输入框常驻右内边距, 避免按钮出现/消失挤窄输入框)。两个修饰符缺一不可 —— `@mousedown.prevent`
  保焦点(不拦 = 按钮抢焦点 → 失焦走 focusout 把下拉收掉), `@click.stop` 挡 window 收层(不挡 =
  点 x 顺手把下拉收了, 真机走查实测暴露)。清空后浮层仍在、焦点仍在。
- **③拖选输入框文字、终点落在遮罩上抬手 = 窗口消失**: click 的 target 是 mousedown/mouseup 的
  **公共祖先**, 这情形公共祖先就是遮罩 ⇒ `@click.self` 误判成点空白。修法 = 全仓 11 处遮罩统一改成
  `@mousedown="maskDownSelf"` + `@mouseup.self="maskCloseIfArmed(closeX)"`(dialogs.js 单点,
  支持带参关闭 resolveModal(false)); @click.self 零残留。
- **④选中分类后逐字删除把窗口撑变形**: 限高只在开层那一刻按当时的候选量算过, 删字让候选涨回
  全量时菜单没关过(开层 watcher 不触发)⇒ 旧限高不更新。修法 = 三个输入值各挂 watcher(开着才
  重限), meta 侧 `metaCatInput`/`metaCategories` 同族; `_fitAddPop` 放行 meta 对话框。
- **排查结论(用户要求"检测其它所有下拉框")**: 全仓 combobox 只有 4 个(三下拉 + meta 分类),
  其余(filterMenu/uiMenuOpen/colMenuOpen/searchHelp/filePrio/右键菜单)是按钮触发 + @click.stop
  自切换, 无 label 转发路径, 不存在同族问题; meta 分类下拉另有独立缺陷(既无 @focusout 也不在
  window click 名单里, 点对话框别处下拉悬着不收), 已一并补齐。
- **守阵**: `test_web.py::test_frontend_add_combo_label_clear_mask_and_refit` 六组断言(label
  @click.stop / 清空钮双修饰符 + clearAddField / 11 处遮罩臂位且零 @click.self / 过滤词 watcher
  重限 + meta 三处 / meta 失焦收层与兜底名单 / 三皮肤 CSS 成对), 文件头测试计划同步登记。
- **验证**: 三皮肤(atlas/prism/console)真浏览器 Playwright 走查 **39/39** —— 点 label 零
  transitionrun 重放 + 不失焦 / x 清空后文本空且菜单仍在且焦点未丢 / 逐字删除最大溢出 -6.8px 且
  body 滚动量零新增(449→449)且菜单可滚 / 拖选终点在遮罩上抬手窗口不消失 + 点空白仍关窗 /
  meta 分类下拉点 label 不闪且点别处失焦收层 / 控制台零 JS 异常。桩服务: sim_qb 18123 +
  dev_webui 18124(本 clone 现场起, 未复用残留服务)。
- **收尾**: 基线切片 [baselines/26-10-03-2130](../testing/baselines/26-10-03-2130-webui-addcombo-round2.md)
  (2416 passed + 3 skipped / 99%, 合并远端 `03b5e211` 后重测); 新坑 [pitfalls/web-ui/modal-mask-click-self-drag.md](../pitfalls/web-ui/modal-mask-click-self-drag.md);
  旧坑 combobox-focusout-close 补第二轮条目(label @click.stop / 清空钮双修饰符 / 过滤词重限)。
- 不满足立档阈值(单轮 3 份 JS/模板 + 3 份 CSS + 1 测试文件, 一条主线); issue 未入池(用户当轮直接报障)。

## 状态

实施与收尾完成, 随本轮提交入库(sync 合并远端 `03b5e211` 后提交, 推 Gitee develop)。
