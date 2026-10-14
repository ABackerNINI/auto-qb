# 变体表格体整帧换清宿主子树后滚动容器 scrollTop 现算落 0 —— 缺成对恢复即列表跳

> 摘要: 变体表格体整帧换清宿主子树后滚动容器 scrollTop 现算落 0 —— 缺成对恢复即列表跳
> 触发: 点击跳动, 列表跳, 整列表位移, 滚动位落 0, 整帧换, replaceChildren, withScroll, scrollTop 现算, 滚到中间再点后跳, 数据回路重拉后跳, rerender 单点重渲后跳
**Refs:** memory-bank/tasks/26-10-14-webui-content-click-jump.md

## 条目

### 变体 10/11 整帧换缺 withScroll (26-10-14 三复查「点击跳动」, 已修)

- **触发**: 用户报「点击跳动(点击引发行位移/重排)」; 或任何变体整帧换清宿主子树后滚动位跳.
- **判别**: 症状即整列表 scrollTop 跳后点击走数据回路(setFilePriority 到 _editPost 到 _fetchDrawerFiles 到 _dtNotify 到 rerender 到 replaceChildren). 行身份 ref-stable(_dtMergeRows 写字字段, 不重建) —— 位移即滚动位, 不行重建.
- **处置**: 整帧换收进 H.withScroll(host, ...) —— 01-09 变体同口径成对恢复单点 helper. withScroll 记 scrollTop/scrollLeft 宿主父(.drawer-body) 帧换前, 恢复后.
- **守阵**: 既有 dt-live-update #8 check-no-jump 仍绿(本修不改列集/几何/交互件).
- **家族关系**: 同族「整帧换清滚动宿主后需成对恢复」—— 凡整帧换清滚动宿主都要问「滚动位落 0 后回?」. 新写整帧换时先 grep withScroll, 别手写恢复算式.
- **复发**: 0
