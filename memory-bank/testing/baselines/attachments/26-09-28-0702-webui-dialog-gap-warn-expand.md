# 1817 passed / 3 skipped —— 弹窗按钮排 16px 间隙 + 跳检警告塌缩展开

> 摘要: 用户报「标签弹层『完成』/添加种子『取消/添加』与上文间隙太小」+「跳检警告留空突兀, 改为勾选时带过渡展开」。处置 = 三套皮肤 `.modal-actions` 统一 `margin-top: 16px`(相邻兄弟 margin 折叠取最大, 对已有 18px 的确认框零影响); 警告行从 FX-21 常驻占位反转为塌缩/展开(max-height/margin-top/opacity 三属性过渡 0.22s, 零占位, 下方内容平滑下移)。真浏览器专项量测三套 UI 全绿(塌缩 0px/展开 17.3-18.4px/收回 0px, 下方内容布局坐标下移 27.8-29.4px)。纯 CSS + tpl 注释改动, 无 Python 源改动。
> 基线时间: 2026-09-28 07:02
> 档案: tasks/26-09-28-webui-dialog-gap-warn-expand.md

- test.full 首轮 1 失败 = 已记录的 Windows throttle 假红(`test_run_loop_throttles_without_stop_event`, sleep 46ms < 0.05s 下限, 见 testing/baseline.md 常驻警告), deselect 重跑稳态: **1817 passed / 3 skipped**, 20.77s, TOTAL **91%**(12512 语句 / 917 未覆盖 / 4204 分支 / 389 partial), 与前基线(26-09-28-0632)同口径持平(该基线 1818 = 含 throttle 用例, 净增 0)。
- 插曲: 新切片使 activeContext 目录数逼近上限 —— 按归档口径删除已完全沉淀且主题已入库(e897870)的冗余切片 26-09-28-0041-ext-log-noise-suppress, 目录数 56(≤56) 归绿。
- 浏览器冒烟 96 项 2 失败(「列设置·隐藏列宽度保留」atlas/prism), stash 本改动干净 HEAD 复跑同样失败 —— 既有问题, 与本次无关(未入池: 列偏好主题已有失败分析报告在案, 待列状态双轨主线处理)。
