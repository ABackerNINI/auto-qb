# 26-10-02-webui-nav-focus — WEBUI 键盘切页旧页签残留焦点框修复

**Status:** Done
**Added:** 2026-10-02
**Updated:** 2026-10-02 17:05
**Summary:** 用户报「键盘切页(辅种/种子/追剧)后, 鼠标点选过的上一页签残留高亮框」。Playwright 探针实证根因: 鼠标点过的页签持有 DOM 焦点, 键盘切页不动焦点, Chromium 在 keydown 分发时把焦点元素重估为 :focus-visible ⇒ 旧页签画出残留 outline; 且分发期间 matches(":focus-visible") 已翻转, 无法据此区分焦点来源。修法 = 维护不变式而非识别来源: view.js::syncNavFocus —— 切页后导航焦点要么恰在新活动页签(保留, 不打断键盘 Tab 序)要么 blur 归还 body; topbar.html 三页签加 data-view。smoke 双断言守阵。
**Topics:** webui-keyboard-shortcuts
**Refs:** memory-bank/pitfalls/web-ui/nav-focus-stale-ring.md

## 原始请求

用户: 「WEBUI使用键盘切换页(辅种/种子/追剧)后上一页(使用鼠标切换)会留下高亮框, 先看看有没有相关issue,修复」。次轮: 「提交」。

## 思考过程与决策

- **issue 池查重**: 无同款。最接近的 26-09-29-2142(弹窗下拉 hover/键盘高亮同源打架)与 26-09-29-2142(站点搜索命中列表无滚动跟随)复现路径不同, 不合并。
- **根因实证**(桩服务 + playwright-core 探针, 6 步状态读数): ①鼠标点页签 → focused=true / fv=false / outline=none; ②按数字键切走 → 旧页签仍 activeElement 且 fv=true / outline solid 2px(残留框); ③焦点永不自动离开; ⑤按当前页自己的数字键同样触发; ⑥**keydown 捕获级监听里 matches(":focus-visible") 已是 true** —— 分发时 Chromium 已重估, 修复不能读它区分鼠标/键盘来源。
- **方案取舍**: 采纳「维护不变式」(切页后导航焦点 == 新活动页签, 否则 blur 归还 body) —— 点击路径焦点同值不动、Tab+Enter 路径焦点保留(a11y 不倒退)、键盘切页残留焦点清掉。否决「读 :focus-visible 识别来源」(⑥实证不可行); 否决「切页后 focus 新页签」(会给键盘切页引入新可见框, 且同值 focus() 是 no-op 治不了⑤)。⑤残留为标准焦点行为(焦点恰在活动页签上), 记入坑单不改。
- **范围裁剪**: 同机制的「鼠标点页签后 Ctrl+, 进设置页」路径不在用户报的复现内, 未动, 已向用户报告待定夺。

## 实现计划

| # | 改动 | 主点 |
|---|---|---|
| 1 | tpl/topbar.html | 三个视图页签加 `data-view="groups\|torrents\|shows"`(DOM 身份标识; 设置页签在 `nav.tabs-right` 无此属性天然豁免) |
| 2 | view.js::goView + syncNavFocus | 切页后: activeElement 是带 data-view 的 button 且 data-view != mode → blur(); 恰等则保留 |
| 3 | scripts/ui_smoke.cjs | 「导航焦点」双断言: 鼠标点页签持焦无框 / 键盘切页后旧页签不残留焦点框(双 UI 各跑一遍) |

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| issue 查重 + 根因探针实证 | Done |
| 修复(tpl data-view + syncNavFocus) | Done |
| ui_smoke 回归用例 + 双 UI 全量冒烟 | Done |
| test.full 基线切片 | Done |

## 进度日志

- 2026-10-02 17:05: 全部完成。实测: 探针修复后残留 0; ui_smoke 双 UI 104 项 0 失败(含新增 4 断言); test.full 2290 passed + 3 skipped / 99%(13,251 语句 / 86 未覆盖 / 4,436 分支 / 81 partial), 基线切片 testing/baselines/26-10-02-1705-webui-nav-focus.md。新坑入池 pitfalls/web-ui/nav-focus-stale-ring.md; smoke.md「Playwright 从哪来」条环境漂移回写(npx 缓存已空)+复发 +1。
