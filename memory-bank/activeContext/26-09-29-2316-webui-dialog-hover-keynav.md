# 弹窗下拉悬停接管(issue 26-09-29-2142-bug-dialog-hover-keynav-fight)

> 摘要: 用户指派认领弹窗分类/标签下拉「mouseenter 高亮 × 键盘活动项同源打架」(站点搜索闪烁同族)并已修完(单轮): 真机复验坐实且比推定更重(↓×16 两次被拽回, Enter 实选光标行 cat-06 而非键盘到达的 cat-16 -- 不止闪烁, 实选错); 修 = comboHoverIdx 共享小工具(@mousemove + 3px 位移门限, 三处下拉共用) + 开层单点复位门限坐标 + 三皮肤 CSS data-hi 行摘 :hover(.on 单路); CSS 用 data-hi 定点中和而非全局摘(:pop-item:hover 是共享样式, 列菜单/UI 切换器仍靠它)。守阵 test_frontend_dialog_combo_hover_takeover(已红验); test.full 1760 passed + 2 skipped / 91%(30.90s)。
> 最后活动: 2026-09-29 23:16

## 已完成(已入库 1d711660, 2026-09-29 23:29)

- 修复 + 守阵 + A/B 验证全部落地并随 1d711660 提交推送: 档案 tasks/26-09-29-webui-dialog-hover-keynav.md, 基线切片 testing/baselines/26-09-29-2316-webui-dialog-hover-keynav.md, issue 已置 Done(修复后补充含实际修法/验证/数字), 坑档案 pitfalls/web-ui/hover-keynav-fight.md 已回写弹窗参考实现与守阵。
- 遗留观察(未入池, 非本专题): `_hiScroll` 用 scrollIntoView(block:nearest) 与 hover-keynav-fight 处置④差值法相悖 —— 现阶段滚跟随已工作且合成事件被门限挡住, 若未来弹窗内出现“滚动连带”报障再议。
- 本专题无未完事项; 切片留存供追溯, 后续同题续作时更新本片。
