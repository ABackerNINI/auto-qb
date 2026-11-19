# 6486 passed + 6 skipped —— ESC 鼠标遗留焦点框修复批基线

> 摘要: ESC 鼠标遗留焦点框修复批基线
> 基线时间: 2026-11-19 23:33

## 验收数字

实测树: develop tip `44119ca6` + 本批工作树(修复 + 评审修复 + 回写, 随本专题入库)。`commands run test.full` 实测(2026-11-19 23:2x, 188.0s):

```
TOTAL                                                28915     44  10322     61    99%
6486 passed, 6 skipped, 7 warnings in 185.47s (0:03:05)
```

与上一条切片(26-11-19-0854, 6486P/6S)数字持平 —— 本批新增的 e2e 用例不计入 pytest 数字, node 电池是在既有 test 函数内加断言(test 数不变), 故总量/passed 与上一条对齐; 覆盖率门槛 99.5% 达标(实测 99% 为展示取整, 输出行 `Required test coverage of 99.5% reached`)。

## 本改动面

- `src/auto_qb/webui/static/shared/lifecycle.js`: ESC 残留框修复 —— created 加 `_mouseFocusEl` 缓存; mounted 注册 `focusin` 捕获监听(当场按 `:focus-visible` 记 modality, 鼠标焦点入账/键盘焦点清空)与 `_onKeyModalityTrack`(非 Escape/非纯修饰键 keydown 清账); `_onEscKey` 退栈链**尾**无条件归还鼠标遗留焦点 `blur()` 到 body, 键盘焦点不入账原样保留; unmounted 对称撤两支监听并清缓存。四皮肤共用同一条全局 `:focus-visible`, 改 JS 一处全覆盖, 零 CSS 改动。
- `e2e/views.spec.mjs`: 新增守阵用例「Esc 归还鼠标遗留焦点」(双皮肤)—— 主标签/主表表头/状态栏按钮三类控件鼠标点击后 Esc 无残留框 + 键盘 modality(End)下 Esc 焦点框保留; 两条断言均做过红验(注掉 blur/清账即变红)。
- `tests/test_webui_static_r4_poll_auth_lifecycle.py`: node 监听电池核注册/撤除对称(keydown 4→5 + focusin×1)与三 handler 记账语义(鼠标/键盘/body/空 target 入账判定、Esc 归还、实键清账、修饰键与 Escape 不清账、键盘焦点不被抹); 文件头测试计划清单同步。
- KB: 坑档 `pitfalls/web-ui/nav-focus-stale-ring.md` 复发扩大版(焦点来源记账范式 + modality 配对守卫 + 为何没命中旧守阵), 三段式字段合规; `_index-6.md` 生成器重建; 会话切片 `26-11-19-2325-webui-esc-focus-ring-fix.md`。
- 真机轨不适用: 纯前端焦点可见性修复, Playwright 真浏览器(e2e)已覆盖四皮肤中 prism/atlas 两类 + 全局规则同构, 桩可验, 不涉 qB 真执行/真文件系统·进程·注册表。
