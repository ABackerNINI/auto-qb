# 4823 —— flux 消息通知去切角 + showcase D9 形态挑选区后全量

> 摘要: flux 消息通知去切角 + showcase D9 形态挑选区后全量
> 基线时间: 2026-11-02 06:26
**Refs:** memory-bank/testing/baselines/26-11-02-0553-webui-flux-message-surface.md

## 验收数字

`commands run test.full` 实测(2026-11-02 06:26, 二轮: 通知去切角 + 挑选台追加):

```text
TOTAL                                                22521    152   7726    135    99%
4823 passed, 10 skipped in 199.22s (0:03:19)
```

- 口径注记: 10 skipped 为既有跳过面(平台条件跳过, 与本轮改动无关); 覆盖率 99%。
- 守阵 `tests/test_webui_static_skins.py` 26 passed: 第 20 项由「要求 `.toast` 带 clip-path」改为
  **反向钉**(`clip-path` 出现在 `.toast` 上即红, 用户口径「消息通知不要切角」), 用例数不变。
  红验一次: 把 10px 切角加回 `.toast` 精确报「`.toast` 出现 clip-path —— 消息通知不切角」, 还原后绿。
- 渲染面人工取证(桩服务 + Playwright): 生产 `.toast` 计算 `clip-path` = `none`(方角), 材质/语义档
  未退(渐变首层、`--bg-elev` 底、语义描边仍在); `/fx/showcase.html` D9 区 6 张候选卡全部渲染,
  控制台零错误, 区导航自动收录; 展示页内联脚本 `node --check` 通过。

## 本改动面

- `flux/css/components.css`(700 行, 上限 700): `.toast` 去掉 `--hb-cut` 与 `clip-path`(方角),
  段注改写为「形状**不跟弹窗**」+ 用户二轮口径 + 反面提醒; 材质与语义档(`--msg-surface` /
  `--msg-tone` / `--msg-line`)一行未动。`.modal` 侧不返工(切角 14px 保留 —— 切角只属弹窗级大面)。
- `tests/test_webui_static_skins.py`: `_scan_message_surface_parity` 第 ② 条由「要求 clip-path」
  改为「禁止 clip-path」, docstring 与 `_scan_frontend_assets` 文档串第 20 项同步。
- `fx/showcase.html`: 新增 D9「消息通知形状 / 边标」挑选区 —— 页内 `.mst` 基座(变量集与 flux 令牌
  逐字同源: `--accent/--green/--warn/--error` + 各 `-line` + `--bg-elev` 92% + 白 4.5% 高光) +
  六个形状变体类(`v-cut` 否决对照 / 方角基线 / `v-rail` / `v-top` / `v-tint` / `v-r2`), 每卡三档
  (ok/warn/error) 并排; CARDS 追加 D9-0~D9-5 六条, 样例由 `MST_ICO`/`MST_SHAPE` 装配(装配在
  CARDS 字面量之后、渲染之前), 复用既有「演示 / 选定 / 导出」机制。共享模板与三旧皮肤零改动。
- `memory-bank/conventions/webui.md`: 消息面段改写 —— 形状不统一(通知方角, 用户口径 + 反向守阵),
  并登记 D9 挑选台入口与「选定后落 `.toast` 一条规则」的落点。
- 无 .py 生产代码改动。
