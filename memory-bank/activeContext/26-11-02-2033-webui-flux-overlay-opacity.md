# webui-flux-overlay-opacity

> 摘要: 新增 --bg-pop 不透明浮层底: flux 自有 12 处浮层换值 + shared 7 处 html[data-fx-preset] 覆盖, 另三皮肤补惰性别名; 根因=flux 表面令牌带 alpha 且毛玻璃预算仅 4 处; 口径回写 webui.md 与 overlays.md
> 最后活动: 2026-11-03 01:01
**Refs:** memory-bank/tasks/26-11-02-webui-flux-overlay-opacity.md

**R0(2026-11-02 20:33):** 新增 --bg-pop 不透明浮层底: flux 自有 12 处浮层换值 + shared 7 处 html[data-fx-preset] 覆盖, 另三皮肤补惰性别名; 根因=flux 表面令牌带 alpha 且毛玻璃预算仅 4 处; 口径回写 webui.md 与 overlays.md

**R1(2026-11-03 01:01):** 找回 flux 弹窗毛玻璃(回归): 根因=26-11-02 消息面统一把 .modal 底从 --bg-card(.82) 换成 --bg-elev(.92), blur(14px) 声明仍在但仅剩 8% 透视; 修法=--msg-surface 拆角色底 --msg-base(.modal-mask 回落 --bg-card/提示条仍 --bg-elev) + .modal 补 -webkit- 前缀; 守阵新增 _scan_flux_modal_frost(双向钉弹窗 blur+半透明底 / --bg-pop 不透明 + 八类无 blur 浮层); 口径回写 webui.md 与 overlays.md
