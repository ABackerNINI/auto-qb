# 26-09-26-webui-button-system — WEB UI 按钮体系重构(星图 B 胶囊 / 棱镜 C 双色)

**Status:** Done
**Added:** 2026-09-26
**Updated:** 2026-09-26
**Summary:** 用户报"大部分按钮与 UI 不符"; 截图实证后出 3 组全状态方案模板供挑选, 定案星图 B(胶囊统一)/棱镜 C(强声明双色); ce-btn/ce-icon 全量迁入 .bt 族, 两套 UI 成对, 守阵测试钉住成对性。

## 原始请求

"WEBUI 大部分的按钮风格与 UI 不符, 比如各种弹窗中的确认按钮, 添加种子的取消/添加按钮, 等等, 所有按钮需要彻底重构。" → 先按 UI 风格各出 3 组按钮模板(含全部状态)供挑选 → 用户选定: 棱镜用 C, 星图用 B, 实施。

## 思考过程与决策

- **实证先行**: 用 stub 服务器挂真实 static + 注入 createApp 包装钩子 + 无头 Edge 截图, 拿到弹窗/工具栏/设置页基线截图 —— 确认四类问题: 弹窗动作钮存在感弱(7px 内边距细描边在深底"下沉")、同屏八套按钮写法(高度 21~34px/圆角 999 与 7px/0 混用)、状态纪律缺失(棱镜无聚焦 ring/disabled 三种/加载态各写各的)、两套 UI 同名类手感不一。
- **三方案设计**(交付物 `memory-bank/plans/26-09-26-0538-plan-webui-button-3-proposals.html`, 单文件 dark + 全状态陈列 + 弹窗样机 + 五主题巡回): A 精修现行 / B 胶囊统一 / C 强声明双色; 三方案语义与类名一致, 支持两套 UI 各挑不同方案。用户选: 星图 B + 棱镜 C。
- **迁移策略**: 模板类名成对替换(ce-btn → bt 变体), CSS 各写一份配方; 语义变体 = primary / 默认(次) / ghost / danger / danger-solid / icon + sm。站内确认框的危险确认动态绑定改 `'danger-solid'`; 登录页裸按钮迁入(bt primary/bt ghost)。
- **范围裁量**: 批量浮条 bulk-btn 并入配色/状态语言但**保留 21px 紧凑档** —— .bulk-inline 27px 与 .status-strip min-height 是 FIX-06/FX-09 实测锁定; row-btn/prio-btn 圆角随星图 B 改胶囊, 棱镜保持方角随 C。设置页 hb-*(Ash Thorp 发光语言)按交付物定案保留其形。
- **双色配方令牌**: `--on-accent`(渐变主钮前景)/`--on-accent-ink`(实心主钮深字)/`--on-error`(实心危险钮前景), 星图 :root 一处 + 棱镜五主题各一处成对声明; 亮色主题(frost/golden)accent 偏深, ink/error 前景翻转为白字保对比度。
- **纠缠处理**: 本 clone 工作区另有未提交线「Console Hub 分区重组(日志并入常规)」(schema ×2/config_hub.js/dialogs.js + 两套 index.html 各 3 个 hunk + test_web.py 1 个 hunk); 提交时按 hunk 过滤暂存, 该线改动原样留在工作区。

## 实现计划

1. 方案模板交付物(3 组 × 两套 UI × 全状态) → 用户挑选。
2. atlas/style.css 写入 .bt 体系(B) + bulk/row/prio/login 对齐; prism components.css 写入 .bt 体系(C) + themes ×5 令牌 + views.css bulk 对齐。
3. 两套 index.html 类名迁移(43 处/边 + 动态绑定 + 登录页)。
4. 双向死类清查(ce-btn/ce-icon 全语料零残留, 复合选择器只摘死分支)。
5. 守阵测试 + stub 预览回归截图(两套 UI + frost 亮色)。

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 现状盘点与截图实证(stub + 无头 Edge 冒烟工装) | Done |
| 3 组方案模板 HTML(全状态)供挑选 | Done |
| atlas .bt 体系(B 胶囊)落地 | Done |
| prism .bt 体系(C 双色)落地 + 五主题令牌 | Done |
| 模板类名迁移(成对) + danger-solid 绑定 + 登录页 | Done |
| 双向死类清查(复合选择器死分支摘除) | Done |
| 守阵测试 test_frontend_button_system_paired | Done |
| stub 预览回归截图(含 frost 亮色验证) | Done |

## 进度日志

- **2026-09-26**: 方案模板交付(`plans/26-09-26-0538-plan-webui-button-3-proposals.html`), 用户定案星图 B + 棱镜 C。实施: 两套 CSS 写入 .bt 配方、五主题令牌、模板 43 处/边迁移、死类清查零残留; 新增守阵测试; test.quick 1641 passed。回归截图验证两套 UI(含 frost 亮色白字翻转)。收尾: 撞上 docs-forms 制品 meta/命名协议(测试报错即修, 计划文档补 meta 并改名加 `-plan-` token); Vue 3 生产版 `app._instance` 恒 null 的冒烟工装坑入册 `pitfalls/testing/ui-preview-harness.md`。
