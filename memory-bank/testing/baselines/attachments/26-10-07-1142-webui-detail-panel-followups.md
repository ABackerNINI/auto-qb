# 基线切片 26-10-07-1142 — 详情面板 followups 四修轮收尾(4 笔提交)

> 摘要: 专题 webui-detail-panel-followups 收尾 —— 用户点名 4 个详情面板缺陷修复
> (模板选择器定宽 / 切页返回变体宿主重挂 / 显式换种子软切换 / tooltip 锚定保活),
> 4 笔提交(`039ea285`..`8677a415`, 分支 fix/webui-detail-panel-followups), 每项独立
> 提交 + 红验守阵, 真机浏览器实测四项全 PASS、零 console 错误。Python 产品代码零改动
> (全部改动在 WebUI 静态 JS/CSS 与 test_web.py 守阵)。
> 基线时间: 2026-10-07 11:42
**Refs:** memory-bank/tasks/26-10-07-webui-detail-panel-followups.md

- 分支: fix/webui-detail-panel-followups @ `8677a415`(工作树含本轮收尾回写的未提交改动)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2717 passed + 4 skipped, 42.08s, 覆盖率 TOTAL 99%**
  (16061 语句 / 166 未覆盖 / 5496 分支 / 144 partial; 门槛 98% 达标)
- 相对上基线 (26-10-07-1003: 2713 passed + 4 skipped / 99% / 56.24s): passed **+4** =
  本轮 4 笔提交各新增 1 个守阵测试函数(模板选择器定宽页签无关 / 切页返回变体宿主重挂 /
  打开抽屉换目标不闪空态 / aq-tip 锚定 watch+reacquire 接线), 与逐笔 test.quick
  2714→2717 递增吻合。
- 语句 16061 与分支 5496 全同(零 Python 产品代码改动), 未覆盖 163→166 / partial 143→144
  属覆盖率采样噪声级(上基线同款差异方向相反), 无回归信号。
- 耗时 56.24s→42.08s 为单次采样波动(同机历史采样 34-57s 区间内), 按口径不更新区间结论。
