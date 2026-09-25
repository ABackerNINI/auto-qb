# 26-09-25 WebUI 全局拖拽添加种子 (DND-01)

> 摘要: 用户指令「添加功能: 拖拽添加种子」—— .torrent 文件与 magnet/URL 链接拖到页面任意位置即开
> 添加种子对话框并自动填入(全局落点遮罩 + window 级 drag 四监听); 纯前端改动, 后端协议与路由金清单
> 不动; 两皮肤共用 add_torrent.js 逻辑 + 守阵 test_frontend_add_torrent_drag_drop_wiring 钉接线四点。
> 触发: 拖拽, 添加种子, DND-01, dragenter, dataTransfer, addDragOver, add-drop-mask, 两套 UI 成对改
> 最后活动: 2026-09-25 08:48

## 本轮完成

- **DND-01 全局拖拽添加种子**（两皮肤共用逻辑，后端零改动零新路由）:
  - `shared/add_torrent.js`（AQB_ADD 加 mounted/unmounted 钩子，照 config_hub 先例）: window 级
    dragenter/dragover/dragleave/drop 四监听 add/remove 严格对称；`_dragDepth` 非响应式计数器抗
    子元素 enter/leave 交替抖动；接管判据 `_addDragTakes` 只认 `Files`/`text/uri-list`
    （页面内拖选中文本/拖词进输入框原生行为不受影响）。
  - drop 分流: 文件 → 过滤 `.torrent`（大小写不敏感）复用 name+size 去重 push `addFiles`
    （对话框未开**先** `openAddTorrent()` 再填——它会清空 addFiles）；链接 → uri-list 按行取
    `magnet:`/`http(s)://` 追加 `addUrls`（不覆盖）+ 自动展开链接域。非 .torrent（含文件夹条目，
    不做递归）计数 toast 忽略。
  - `app.js`: data 加 `addDragOver`。`prism|atlas/index.html`: 模板尾部全屏落点遮罩
    （`pointer-events:none`，drop 由 window 收，自身不产生 enter/leave 抖动）。
  - `prism/css/components.css` / `atlas/style.css`: `.add-drop-mask` z-index **132**
    （盖 modal 130 / speed-pop 131）；半透明底沿用两皮肤 modal-mask 的结构黑散写先例，
    框线/文字全走主题 token。
  - 守阵 `test_frontend_add_torrent_drag_drop_wiring`（test_web.py）: 四事件对称、drop 必须
    preventDefault、判据不得放宽 text/plain、双 UI 遮罩成对；docstring 测试计划已同步。
- **实测**: `commands run test.quick` → **1598 collected: 1597 passed + 1 skipped**，
  sidefx 越界 0（与 baseline 两线合一带一致，本包内增量 +1 守阵）。

## 取舍记录

- 不引入 python-multipart / 不加后端路由: `/api/torrents/add` 的 JSON+base64 协议不动，
  拖拽只是给 addFiles/addUrls 换"进料口"。
- 不做文件夹递归拖拽（webkitGetAsEntry），目录条目按非 .torrent 忽略。
- 对话框开着时拖链接 = 追加进链接域；手动拖纯文本进 textarea 不受影响（types 无 uri-list 放行）。

## 下一步

- 用户在运行中的 WebUI 实测拖拽交互（文件/链接/混合/误拖非种子四类路径）。
