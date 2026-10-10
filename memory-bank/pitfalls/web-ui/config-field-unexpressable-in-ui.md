# 键合法但 UI 表达不出差异的字段: 打 hidden, 不要从 schema 摘掉

> 摘要: 值域只有一档且**等于缺省值**的配置字段(如 v1 的 notify.channels: 渠道只有 platform, loader 缺省即 ["platform"])做成勾选框后, 两个方向都表达不出有效差异 —— 勾选只是写一条与缺省等价的键, 取消则写出**空列表**, 而空列表 ① 与"键缺失"不同构(脏标记是全树 JSON 对比 ⇒ 勾了再取消照样提示"有改动还没保存", 界面上却看不出差异) ② 过不了后端校验(必须是非空列表 ⇒ 保存必败, 报错还带临时文件路径, 用户找不到是哪一项)。处置 = 加 `Field.hidden` 让设置页不渲染(键仍在配置契约里: 校验接受 / loader 读 / 存量值保留), **不是**从 schema 摘字段 —— 键面守卫以 schema 为键面单点, 摘了会被判成"删键"(破坏性变更: 抬版本 + 注册迁移)。
> 触发: 设置页勾选框表达不出差异, 勾了再取消仍有未保存改动, 保存报"必须是非空列表", 想暂时隐藏某个设置项, keyed_list 清空, schema 摘字段被键面守卫判删键

## 触发 / 判别 / 处置

- **触发**: ① 某字段的值域只有一档且等于其缺省值, 用户勾/取消都看不出运行期变化; ② 取消勾选后保存报后端校验错(空列表类), 或勾了再取消脏标记消不掉; ③ 想"暂时把这个设置项从界面拿掉"。
- **判别**: 先问「取消勾选想表达的那个状态, 后端模型能不能承载?」—— 承载不了(缺省会把空值填回默认值)就说明这个控件**在语义上是空的**, 不是实现 bug。配套看两处: 脏标记是全树 `JSON.stringify` 对比(`cfgDirty`), 空容器与键缺失必然不等; 校验层对"必须非空"的键不接受空列表。
- **处置**: 三段走 —— ① `schema/fields.py` 用 `Field.hidden`(键留在契约里, 只是不进渲染; 别拿它表达"改了风险大", 那是 `risk` 的职责); ② 前端单点在 `config_editor.js::cfgFlatten` 的 `if (f.hidden) continue`(两套 UI 同源于此函数, 漏这条 skip = 字段照样渲染); ③ 顺手把容器类控件的"清空 = 删键"补齐(同文件 `toggleKey` 与 `cfgItemRemove` 必须同口径: `list.length ? cfgSetPath : cfgDelPath`)。
- **守阵**: `tests/test_config_schema.py::test_notify_channels_hidden_from_ui_but_kept_in_contract`(schema 保留该键且打 hidden / hidden 声明面恰好一处 / KNOWN_NOTIFY_KEYS 仍有该键 / 校验仍接受 platform 条目且仍拒绝空列表);`tests/test_webui_static_dom_page.py::test_frontend_flatten_skips_hidden_fields` 与 `::test_frontend_keyed_list_toggle_deletes_key_when_emptied`(后者钉 toggleKey 的 `cfgSetPath` 必须挂长度守卫)。

**Refs:** memory-bank/tasks/26-10-10-webui-notify-channels-hidden.md
