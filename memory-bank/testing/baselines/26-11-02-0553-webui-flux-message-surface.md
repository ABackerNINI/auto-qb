# 4823 —— flux 消息面统一(提示条与确认框材质同源)后全量

> 摘要: flux 消息面统一(提示条与确认框材质同源)后全量
> 基线时间: 2026-11-02 05:53
**Refs:**

## 验收数字

`commands run test.full` 实测(2026-11-02 05:53, 消息面统一后):

```text
TOTAL                                                22521    152   7726    135    99%
4823 passed, 10 skipped in 285.96s (0:04:45)
```

- 口径注记: 10 skipped 为既有跳过面(平台条件跳过, 与本轮改动无关); 覆盖率 99%。
- 守阵 `tests/test_webui_static_skins.py` 26 passed(第 20 项 `_scan_message_surface_parity` 收进
  既有健康用例, 用例数不变), 红验四形态各报预期文案: 摘掉 `.toast.warn` 档 → 「缺 `.toast.warn`
  的 --msg-tone 声明」+「kind `warn` 有调用但没有规则」两条; `timeout` 改回 accent → 「--msg-tone
  = --accent(应为 --warn)」; 摘 `.toast` 的 clip-path → 「基线缺 clip-path」; 摘 `.modal.tone-error`
  → 「缺 --msg-line = --error-line」。
- 渲染面人工取证(桩服务 `--port 8399` + Playwright, flux 不在 e2e `SKINS` 默认集合故不入 e2e 门禁):
  `.toast.error` 与 `.modal` 的计算样式逐项对齐 —— 同一渐变首层、`background-color` 同为
  `--bg-elev`, `border-color` 同为对应 `--*-line`, `clip-path` 仅差族值(10px vs 14px);
  提示条各档并排(ok/warn/error/busy/info)语义可辨; 琥珀档确认框与大面表单框(无 tone, 边框
  仍是中性 `--border-strong`)均无越权着色。

## 本改动面

- `flux/css/components.css`(699 行, 上限 700): 新增「消息面(message surface)」声明段 +
  `.toast-wrap, .modal-mask` 一条 `--msg-surface` 供给面单点; `.toast` 由平面方角老配方
  (`--bg-card` + `--shadow-2` + 方角)改为「切角 10px + 同一 `--msg-surface` + `--msg-line` 描边 +
  `--msg-tone` 图标」; 五档语义收成变量声明(新增 `warn` 档 —— 此前 21 处调用点整档无样式, 与 info
  同貌); `.modal` 的 background 改读同一 `--msg-surface` 且边框改读 `--msg-line`, 新增
  `.modal.tone-warn/.tone-error` 描边染色(与提示条同一套语义语法)。
- `tests/test_webui_static_skins.py`: 新增 `_scan_message_surface_parity` + `_toast_kinds_in_use` +
  `_MSG_TONE_EXPECT`/`_MSG_NEUTRAL_KINDS`, 接入 `_scan_frontend_assets`, 文档串补第 20 项。
- `memory-bank/conventions/webui.md`: fx/flux 节补「消息面统一」口径段(三件共用 + kind↔语义档
  期望表 + 范围只 flux)。
- `memory-bank/pitfalls/web-ui/toast-kind-unstyled.md`: 新建(新 kind 不登记样式 = 与 info 同貌)。
- 无 .py 生产代码改动; 共享模板/JS/其它三皮肤 CSS 零改动(纯 flux 皮肤 CSS + 守阵)。
