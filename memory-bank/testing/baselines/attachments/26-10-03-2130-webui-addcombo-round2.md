# 基线 · 2416 passed + 3 skipped / 99% —— 添加种子三下拉「第二轮遗留四项」修复轮

> 摘要: 上一轮(失焦即收 + 开层限高, 基线 26-10-03-1550 @ 2391)之后用户报的四条遗留 —— ①点字段
> label 稳定复现下拉闪烁(输入框已聚焦, 不 blur, 真链条是「label click 冒泡到 window 收层 → 转发
> click 重开」, @focusout 挡不住)②三个 combobox 无 x 清除 ③拖选文字终点落在遮罩上抬手把窗口关了
> (click target = mousedown/mouseup 的公共祖先 = 遮罩, @click.self 误判)④选中分类后逐字删除把窗口
> 撑变形(限高只在开层那一刻按当时候选量算过, 删字涨回全量时旧限高不更新)。修法 = 四个 label
> @click.stop + 内嵌清空钮(双修饰符)+ 全仓 11 处遮罩改「mousedown 记臂位 + mouseup.self 才关」
> + 三个输入值 watcher 重限(meta 侧同族三处)。
> 守阵 `test_web.py::test_frontend_add_combo_label_clear_mask_and_refit` + 文件头测试计划同步。
> 基线时间: 2026-10-03 21:30, develop @ 03b5e211(stash → sync 合并远端新提交后重测, 工作区含本轮
> 修复与回写件, 未提交)。
> 三皮肤真浏览器 Playwright 走查 39/39(sim_qb 18123 + dev_webui 18124 现场起桩; 判据含点 label
> 零 transitionrun / x 清完后菜单仍在且焦点未丢 / 逐字删除 body 滚动量零新增 / 拖选抬手不关窗
> 而点空白仍关窗 / meta 下拉点 label 不闪且点别处失焦收层 / 控制台零异常)。
> Linux 侧: 待补(仅 Windows 侧重测, 见 baseline.md 常驻警告)。

TOTAL **2416 passed + 3 skipped / 99%**(14,395 语句 / 131 未覆盖 / 4,810 分支 / 104 partial,
test.full 42.6s, rc=0)。
相对本切片初次记录(7ca46436 基线: 2415 passed + 3 skipped)**passed +1** = 合并远端 `03b5e211`
(双击末尾种子让位)带入的 1 条守阵; 语句/分支数与上一切片持平(纯前端接线与守阵, 无新语句路径)。
