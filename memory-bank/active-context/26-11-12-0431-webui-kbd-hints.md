# webui-kbd-hints

> 摘要: webui 键帽提示专题全程: 计划入库(grilling D1-D12) → S1-S6 实施完成(五笔提交 3df2c3b9..e544bfd2, 全量全绿见 kb.baseline, 四皮肤真机截图目检过) → 收尾回写/入池 2/坑档 2/计划收口; 档案结档 Done
> 最后活动: 2026-11-13 04:47

**Refs:** memory-bank/tasks/26-11-12-webui-kbd-hints.md

**R0(2026-11-12 04:31):** 快捷键现场提示计划入库: grilling 两轮拍板 D1-D12 + 计划 26-11-12-0344(Open) + 分批评审 3 轮 10 发现全修零 actionable + 坑档 subagent-survey-fact-verify 立档; S1-S6 等显式开工

**R1(2026-11-12 05:21):** 漂移直接修复(用户扩围): _scan_keys_serial_re 指称 3 处(shortcuts.js/keys.py/web_shortcuts_support.py 改指 webui_static_scan_js.py 定义点) + ctx_menu.js:93 次级计数 11->10 + 第四处同款 keys.py:32 对照面; 电池补桩 test_r4_move_dialog_partial_disclosure_bar(入库树既有红, e1fbd849 ensureWebFlags 接线 vs 沙箱缺桩); test.full 全绿(见 kb.baseline); 评审 5 轮轮 4/5 零 actionable; 随本专题入库

**R2(2026-11-12 05:28):** 漂移族入池 issue 26-11-12-0527-docs-webui-guard-ref-drift(15 处现存指称/11 文件, docs 便签, 不同符号面, 用户拍板入池): L1 三段齐(现象/位置锚点表/建议), 双向链挂任务档案; 随本专题入库

**R3(2026-11-13 04:47):** 收尾回写完成: §09 三处(architecture 键位现场提示节/conventions 悬浮提示例外/README 零漂移) + 入池 2(0443-bug 子菜单溢出残余/0443-test UIS 枚举漂移) + 坑档 2(ctx-sub-width-coupling 新立/css-file-line-cap 复发+1 扩 flux) + issue 0318 复发+1 + 计划收口(D13/doc-status Done/R2); 顺延三条 nit 勘正随本专题入库; 档案结档 Done
