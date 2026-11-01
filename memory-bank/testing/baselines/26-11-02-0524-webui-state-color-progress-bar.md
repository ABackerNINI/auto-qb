# 4823 —— 种子状态色拆分与进度条着色后全量

> 摘要: 种子状态色拆分与进度条着色后全量
> 基线时间: 2026-11-02 05:24
**Refs:**

## 验收数字

`commands run test.full` 实测(2026-11-02 05:24, 状态色拆分 + 进度条着色后):

```text
TOTAL                                                22521    152   7726    135    99%
4823 passed, 10 skipped in 199.56s (0:03:19)
```

- 口径注记: 10 skipped 为既有跳过面(平台条件跳过, 与本轮改动无关); 覆盖率 99%。
- 守阵 `tests/test_webui_static_skins.py` 26 passed(含新增第 19 项 `_scan_state_color_tokens`),
  红验一次: 把 prism `.k-checking` 的 `--st` 改回 `--blue` 时精确报
  「`--st = var(--blue)(应为 var(--warn))` —— 校验中/下载中同色会复发」, 还原后绿。
- 渲染面 `e2e/state-moving.spec.mjs` 2 passed(atlas/prism): `.k-moving` 计算色 == `--violet`,
  且 moving 行进度条填充计算背景色 == `--violet`(`--st` 继承真到位)。console/flux 不在
  e2e `SKINS` 默认集合(既有口径), 其改动由静态守阵的四处成对检查覆盖。

## 本改动面

- `atlas/css/components.css`(严 700 行, 零净增): `.k-*` / `.g-status` 底 / 组行与成员行文字色 /
  `.site-chip` / tag·cat chip / `.m-state` / 进度条填充 —— 8 处 `--blue(-soft)` 改读
  `var(--st, …)` / `var(--st-soft, …)`; 进度条填充由 `linear-gradient(accent, accent-hi)` 改纯状态色。
- `atlas/css/views.css`: 新增「状态色令牌」段(7 kind × `--st`/`--st-soft`), 覆盖 `.k-*` /
  `.site-chip` / `.group-row.s-*` / `.member-row.<kind>`; components 顶 cap 故落此文件(有 `.h-cell` 先例)。
- `console/css/components.css`、`flux/css/components.css`、`prism/css/components.css`: 同款声明段
  (console/flux 就近 `.k-*`; prism 因 `css/views.css` 818 行存量冻结而落 components.css),
  并把各自状态蓝消费点改读变量; `prism/css/views.css` 仅作行内替换(行数 818 → 818, 未增)。
- `flux/css/fx-mount.css`: 进度条填充辉光 `--green` → `var(--st, var(--green))`(下载行原本绿光蓝条)。
- `e2e/state-moving.spec.mjs`: ④ 配色断言 `--blue` → `--violet`; 新增 ⑤ 进度条填充 == 行状态色。
- `tests/test_webui_static_skins.py`: 新增 `_scan_state_color_tokens` 与 `_STATE_TOKEN_EXPECT`
  (7 kind 期望值表), 接入 `_scan_frontend_assets`, 文档串补第 19 项。
- `memory-bank/conventions/webui.md`: 状态色族段补「状态色 → kind 映射与 `--st` 单点」。
- 无 .py 生产代码改动; 模板/JS 零改动(纯 CSS 变量 + 既有行状态类)。
