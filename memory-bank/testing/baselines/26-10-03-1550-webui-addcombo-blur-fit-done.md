# 基线 · 2391 passed + 3 skipped / 99% —— 添加种子三下拉「失焦即收 + 限高不出窗」修复轮

> 摘要: 用户报添加种子窗口三个下拉(保存路径/分类/标签)两类故障: ①点窗口其它位置下拉不收、闪烁重现
> (label `for=` 转发激活先 blur 再回焦, click 关层 + 转发 click 重开); ②选项过长菜单伸出窗口外把
> 内容撑变形(.pop-menu 基础 max-height 只保证菜单自身可滚, 绝对定位溢出把 .add-dialog-body
> scrollHeight 撑大, 实测 449→591)。修法 = 收层主判据改 @focusout + 40ms 合帧守卫(label 回焦由
> 开层方法撤销, 菜单全程不闪) + 开层 watcher 量「输入行→滚动容器可见底沿」净空限高(滚动条留在窗内)。
> 守阵 `test_web.py::test_frontend_add_combo_blur_close_and_fit` + 文件头测试计划同步。
> 基线时间: 2026-10-03 15:50, develop @ 4978a717(工作区含本轮修复与回写件, 未提交)。
> 三皮肤真浏览器 Playwright 走查 12/12 × 3(atlas/prism/console, 桩服务 8177; 判据含点空白收层/
> label 点击无 leave 过渡重放/40 项长菜单不出窗且 body 零新增滚动/Esc/Tab/选项行回归)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2391 passed + 3 skipped / 99%**(13,996 语句 / 127 未覆盖 / 4,728 分支 / 99 partial,
test.full 35.0s, rc=0)。
相对上一切片(26-10-03-1431: 2390 passed + 3 skipped / 99%, 同语句分支数, @ da23e842)
**passed +1** = 本单新增守阵 1 条; 语句/分支数与上一切片持平(纯前端接线与守阵, 无新语句路径)。
