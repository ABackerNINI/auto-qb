# 26-09-28-webui-keyboard-shortcuts — WEBUI 键盘快捷键(可自定义): 成熟方案调研 + 存储定案

**Status:** Open
**Added:** 2026-09-28
**Updated:** 2026-09-28
**Summary:** 前案 26-09-26-0822 (localStorage 预选) 经成熟方案调研与存储对比后被 26-09-28-0354 取代(0822 置 Superseded): 定案建议后端独立文件 auto-qb-data/webui-keys.json + GET/PUT /api/keys(金清单+2); 引擎不引库自写 ~200 行(tinykeys 为参照), 沿 0822 注册表/e.code/作用域/三段屏蔽设计; 自定义面板进设置页「快捷键」分区 + ? 浮层; W1-W7 修订波次, 6 个决策点建议案待拍板。
**Topics:** webui-keyboard-shortcuts
**Refs:** memory-bank/plans/26-09-28-0354-plan-webui-keyboard-shortcuts.html, memory-bank/plans/26-09-26-0822-plan-webui-keyboard-shortcuts.html

## 原始请求

为 WEBUI 添加键盘快捷键, 调研成熟的设计方案; 需要支持自定义, 自定义在设置里; 存储在后端单独文件还是前端 localStorage 需要对比分析优劣; 写一份计划(只计划不改代码)。

## 思考过程与决策

- **调研(外部, 2026-09-28 实测)**: 支持逐条重映射的成熟产品只有 Gmail(服务端账号)/VS Code(keybindings.json 本地文件+可选按 OS 同步)/JupyterLab(服务端 $HOME/.jupyter 用户文件 JSON5) 三家, **无一用 localStorage 作正式存储**(vscode.dev 未登录只是兜底); 库横评: tinykeys 4.0.1 最活跃且 key+code 双匹配(UMD 1.1KB gzip), hotkeys-js/keyCode 系与 e.code 设计相抵, @github/hotkey 仅 ESM, Mousetrap/keymaster 停更, react-hotkeys-hook 需构建。
- **不引库自写**: 「可自定义」完整栈(录制器/冲突/黑名单/作用域接线/存储)没有库覆盖, 库只解决派发 ~40 行; tinykeys ~6.4KB 源码作实现细节参照(isComposing/repeat/AltGraph/defaultPrevented/$mod)。
- **存储定案(建议)**: 后端独立文件。0822 把「服务端持久化」等同「写 config.yml 红线」是假二分 —— 独立文件既不碰 config.yml 也不碰 state.json(黄金法则 5 主循环单写线程, web 线程本就不能写 state); localStorage 的失效通道(浏览器「关闭窗口时清除站点数据」)在本项目列偏好上已实际发生(pitfalls/web-ui/columns-persist.md), 且快捷键是「用户逐条录制的配置」, 信息价值高于列宽/主题这类可低成本重派生的偏好 —— 两范式并存各安其位, 不是破坏一致性。
- **沿袭 0822**: 注册表单一事实源 AQB_KEYS(58 条=52 默认+6 空位)/e.code 归一化/scope 五值/输入态三段屏蔽/Esc 唯一 fixed 接 lifecycle 退栈链尾/kbCursor 光标/_actCore 唯一重构点。
- **新增修订**: 字符语义键与 code 的权衡按 MDN 口径落注; 黑名单以 Chromium reserved accelerators + Firefox bug 1052569 为准(Ctrl+W/T/N/Q 不可拦); 录制器走 VS Code ⌘K⌘K 模式; 跨标签语义明示为「刷新后生效」(与 config 保存语义一致, 混合镜像方案缓议)。

## 实现计划

波次(可拆口 W1-W4 先行交付默认键位, W5-W6 第二波): W1 引擎+注册表+适配器桩 → W2 光标模型+滚动进视口 → W3 目标解析+commands._actCore 抽取 → W4 绑定 A-D 组 → W5 绑定 E-H+局部作用域 → W6 后端 webui-keys.json + GET/PUT /api/keys + 金清单 + 面板录制器 → W7 静态守阵 + 真机走查 + 文档回写。可拆口: W1-W4 先行交付默认键位, W5-W6 第二波。

## 子任务状态表

| # | 子任务 | 状态 |
|---|---|---|
| 1 | 前案 0822 可行性分析 | Done (26-09-26) |
| 2 | 成熟方案调研(产品/库/坑/上游) + 存储对比分析 → 计划 26-09-28-0354 | Done |
| 3 | §08 六个决策点拍板(核心: 存储定案) | Pending |
| 4 | W1-W7 实施 | Pending |
| 5 | 收尾回写(基线/progress/pitfalls) | Pending |

## 进度日志

- 2026-09-28 03:54 调研与计划落地(未动代码): 计划 26-09-28-0354 立档, 0822 置 Superseded 并回链; 6 决策点建议案就绪, 等拍板。
