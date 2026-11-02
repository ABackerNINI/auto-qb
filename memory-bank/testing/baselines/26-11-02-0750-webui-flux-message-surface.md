# 4823 —— toast 文案统一为「主标题: 说明」(58 处)后全量

> 摘要: toast 文案统一为「主标题: 说明」(58 处)后全量
> 基线时间: 2026-11-02 07:50
**Refs:** memory-bank/testing/baselines/26-11-02-0723-webui-flux-message-surface.md

## 验收数字

`commands run test.full` 实测(2026-11-02 07:47, 七轮: 文案统一):

```text
TOTAL                                                22521    152   7726    135    99%
4823 passed, 10 skipped in 205.98s (0:03:25)
```

- 口径注记: 10 skipped 为既有跳过面(平台条件跳过, 与本轮改动无关); 覆盖率 99%。
- 守阵 `tests/test_webui_static_skins.py` 26 passed: 新增第 21 项 `_scan_toast_copy_two_part`
  (扫 `toast(` 与 `_finishToast(` 两个入口的文案, 判「主标题: 说明」), 用例数不变。
  红验一次: 把「已导出: .torrent 文件已保存」改回「已导出 .torrent」→ 精确报
  `shared/commands.js:969 toast 文案不是「主标题: 说明」形态`, 还原后绿。
- 期间连带修绿两处既有断言(文案变了它们必须同步): `tests/test_web_shortcuts.py` 两条
  源码断言(「功能未启用: qB 口径流量图」)、`tests/test_webui_static_dom_panel.py` 一条
  (空投递收口文案 → 「无可汇报目标: 没有可强制重新汇报的种子」)。
- e2e 同步: `e2e/menus.spec.mjs` 的 W4 导出回执断言改成 `ok|已导出: ${N} 个 .torrent 文件`;
  实跑 `commands run dev.e2e -- e2e/menus.spec.mjs -g "W4 多选导出"` → **2 passed**(prism/atlas)。
- 渲染面人工取证(桩服务 + Playwright): 八条改写后的普通回执与六条终态回执(含 sticky
  「等待中 → 成功/超时」原位升级)全部渲染成标题行 + 说明行; 控制台零错误。

## 本改动面

- `shared/*.js`(14 个文件, 58 处文案): 把所有没有分隔符的提示条文案改写成
  `主标题: 说明` —— 主标题 ≤14 字不含括号, 说明给出现场信息(数量/名称/位置/下一步)。
  典型: 「已导出 .torrent」→「已导出: .torrent 文件已保存」、「未作修改」→
  「未作修改: 输入与当前值一致」、「限速需为非负数字(KiB/s)」→「限速值无效: 需为非负数字(KiB/s)」、
  「正在向 tracker 汇报 N 个目标, 等待确认…」→「强制汇报进行中: N 个目标, 等待 tracker 确认…」、
  「强制重新汇报成功(tracker 已确认…)」→「强制汇报成功: tracker 已确认…」、
  「汇报确认成功(跳过 N 个非活跃), 开始删除…」→「汇报确认成功: 跳过 N 个非活跃, 开始删除…」、
  「已导出 N 个 .torrent」(终态) →「已导出: N 个 .torrent 文件」。
- `flux/fx-mount.js`: `TOAST_SPLIT` 说明门槛 6 → **2 字**(文案统一后说明常是一个名字/计数,
  门槛再高「已执行: 重命名」这类又会退回单行); 注释同步本轮口径。
- `tests/test_webui_static_skins.py`: 新增文案守阵 `_scan_toast_copy_two_part` +
  实参解析件(`_toast_literal_texts` / `_args_texts` / `_first_arg_text` / `_skip_string` /
  `_skip_braces`), docstring 增第 21 条。
- `e2e/menus.spec.mjs` / `tests/test_web_shortcuts.py` / `tests/test_webui_static_dom_panel.py`:
  三条既有断言随文案同步(只改期望字符串, 判据与意图不变)。
- `memory-bank/conventions/webui.md`: 新增「toast 文案 = 主标题: 说明」段(含改动面、四皮肤共享
  口径、守阵入口与「终态文案在 _finishToast 第 3 参」这个易漏点)。
- 样式面(components.css / views.css / 形状 / 图标)本轮零改动。
