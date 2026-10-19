# 3766 passed + 10 skipped(Windows 单侧) —— 弹窗语义配色分级落地 + 合流远端 7 笔后的全量

> 摘要: 3766 passed + 10 skipped(Windows 单侧) —— 弹窗语义配色分级落地 + 合流远端 7 笔后的全量
> 基线时间: 2026-10-20 02:37

## 验收数字

```
TOTAL                                                20362    391   6982    262    98%
3766 passed, 10 skipped in 50.22s
```

口径注记:
- 本侧 = Windows(本机 `.venv` Python 3.14.7, `commands run test.full`, xdist `-n 4`)。Linux 侧本轮未跑(本机无 Docker/WSL, `test.linux` 跑不了) —— 且本轮是**纯前端改动**(JS/CSS/HTML), 不触碰 Python 可执行行, 跨平台差异风险为零。
- 两次数值: 提交前 3757 passed; 提交时 `ship.commit` 撞上远端分叉(远端领先 7 笔)自动 rebase 重放(`2387b6b6→b47804f6`), 合流后复跑得 **3766 passed**(+9 来自远端新增用例, 其中 `test_webui_ctx_menu_registry.py` 325 行是右键菜单注册表新守阵)。**以合流后这次为准** —— 合流前那次不能代表仓库最终状态。
- 远端 7 笔里有 4 笔动过 `tests/test_webui_static_dom_panel.py`(T23/T24 所在文件)与三套 CSS 模板消费侧, 故合流后必须重跑, 不可沿用提交前数字。
- 覆盖率达标(98%), 未触发 fail-under; 语句未覆盖数 391 与合流前一致。

## 本改动面

弹窗语义配色分级(计划 `26-10-19-2341`)的实施 S1~S5 + 目视反馈迭代:

- `shared/ui_feedback.js`: `_modalInit` 增 `tone: ""` / `strip: false`; `_openModal` 增派生单行 `cfg.tone || (cfg.danger ? "error" : "warn")` 并入 modal 字面量(`mid` 自增留在同一字面量内, identity 守阵要求)。
- `shared/tpl/popovers.html`: 框容器类绑定改数组式(追加 `strip` 与 `tone-*`); verdict 行与 details 行的 `:class` 改 `[d.tone && 'is-' + d.tone, { wide: d.wide }]` —— 容器与 `.bt.danger-solid` 按钮一字符未动(T23 整行硬锚定)。
- `shared/delete_flow.js`: `_confirmDelete` 显式 `tone: "error"` + `strip: true`; HR 风险行 `tone: "error"`。
- `shared/drawer.js`: `_skipCheckDialog` 显式 `tone: "warn"` + `strip: true`; 固定警示区 4 行 / 预检失败行(2 处)/ 计数行 / 按原因分组行 / 单发原因行 / 全满足行各自挂 tone。**`_skipPrecheck` 六分支语块零增删**(T24 逐语句等值断言)。
- CSS 三套成对: atlas `css/views.css` + console `css/views.css` + prism `css/components.css`。首版各 10 条规则; 目视反馈迭代追加 8 条 —— 框级兜底继承(`:where(.modal.strip.tone-*)`)与 `.is-error` 强调底。
- 新增 pitfall `pitfalls/web-ui/css-file-line-cap.md`(atlas `components.css` 卡满 700 行的体量守阵)。

未改动: Python 侧零改动、零新增 Python 测试 —— 行为变更为零(纯装饰层), 故不加新守阵; 视觉验收靠 `dev.e2e` 冒烟 + 人工目视 + 真浏览器 `getComputedStyle` 复核(层叠优先级不靠肉眼判)。
