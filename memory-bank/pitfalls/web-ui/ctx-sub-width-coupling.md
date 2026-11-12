# .ctx-sub 宽度五处耦合: 四皮肤 components.css min-width 260 + menu.js 首帧估宽 272

> 摘要: 右键菜单次级子面板宽度五处耦合 —— 四皮肤 css/components.css 的 .ctx-sub min-width 260(同值互证) + shared/menu.js _subOverflowsRight 首帧估宽 272(=260+12); 改宽度必须五处同步, scan_css _scan_ctx_sub_width 机械拦截
> 触发: .ctx-sub, 子面板宽度, min-width, 260, 272, 估宽, _subOverflowsRight, _subFitViewport, _scan_ctx_sub_width, 宽度耦合, flip-x, 键帽加宽
**Refs:** memory-bank/tasks/26-11-12-webui-kbd-hints.md

### 改右键菜单次级子面板宽度时五处数字必须同步 —— 单处改即守阵红或四皮肤静默分叉

- **触发**: 调整 `.ctx-sub`(右键菜单次级子面板)盒宽 —— 加宽/收窄 min-width、改内边距、或内容变宽(键帽列)触发重估; 特别容易漏的是「只改一处皮肤」和「改 CSS 忘了 JS 估宽」。
- **判别**: `tests/webui_static_scan_css.py::_scan_ctx_sub_width` 红(经 `webui_static_scan_js.py` 汇聚挂载): ①四皮肤 min-width 互证同值且 ==260px —— 单皮肤回退 = 四皮肤静默分叉, 该皮肤 label+键帽放不下折行(260 = 最长项「开启自动种子管理」+ 键帽「Shift + T」单行实需约 246 取整留余); ②menu.js `_subOverflowsRight` 的 `probeRight` 第二参 == min-width 260 + 内边距 12 = 272(JS 写字面量 272 或表达式 260+12 均认) —— CSS 侧与 JS 侧算术绑定, 改宽度漏同步 JS(或反之)即红。
- **处置**: 五处同步改: 四皮肤 `css/components.css` 的 `.ctx-sub min-width` + `shared/menu.js::_subOverflowsRight` 估宽(新 min-width + 内边距 12); 若是语义宽度重定(不止数值), 同步改守阵锚值 `want, pad = 260, 12` 并重跑双向变异自证守阵真红。估宽只管首帧水平翻转方向(flip-x), 实测重钳位在 `_subFitViewport` —— 别试图用实测逻辑替掉估宽(首帧无布局可测)。
- **守阵**: `_scan_ctx_sub_width`(2026-11-13 落地, 计划 26-11-12-0344 S6 评审 minor「五处数字耦合无守阵, 单皮肤回退静默复发」当场修; 四值互证 + 钉数 + 算术绑定三层)。
- **复发**: 0
