# 基线切片 26-10-04-0353 — 弹窗滚轮穿透修复 (遮罩截断滚动链 CSS 主案 + JS 兜底)

> 摘要: 报告 26-10-04-0128 三项拍板 (JS 兜底本期做 / hidden + 6 号壳加固 / 无遮罩浮层不改)
> 落地: ① CSS 主案 8 文件, `overscroll-behavior` 全库 0→30 处 — .modal-mask ×3 + .hr-full-mask ×3
> 加 overflow:hidden+contain, 8 类内滚区补 contain (prism 无 .modal-members 跳过), 6 号壳 .modal ×3
> 补 max-height 内滚加固; ② JS 兜底 ui_feedback.js +52 行 IIFE — CSS.supports 注册期门控 +
> document 级捕获 wheel/touchmove {passive:false} + 白名单(8 内滚区 + modal 壳, 豁免 Ctrl+滚轮);
> ③ 压回 atlas components.css 700 行守卫。中途守卫拦截: 单 CSS 700 行上限 (701→压回 700)。

- 时间: 2026-10-04 03:53 (GMT+8); 会话起点 sync 至 13e2646f, 提交前 sync 至 71251d61 (rebase 后线性)
- 分支: develop @ e5a59841 (= fix/webui-modal-scroll-chaining 三提交 fdb97468/b989df10/e5a59841
  rebase 后快进合并; 远端 71251d61 的 aq-tip 修复与 ui_feedback.js 兜底同文件, rebase 零冲突)
- 命令: `commands run test.full`
- 实测: **2423 passed + 3 skipped, 28.82s, 覆盖率 TOTAL 99%**(14282 语句 / 132 未覆盖 / 4820 分支 / 105 partial)
- 相对上基线(26-10-04-0329: 2423 passed)用例数持平: 纯静态资源 (CSS/前端 JS) 改动, 无新增/删改用例;
  test.quick 全程三次绿 (P3 验证轮 2422 passed 守卫修复后 / 合并新基线复跑 2423 passed)
- 未验证面: 真机三皮肤滚轮/触屏走查 (报告 §7.3 验收清单: 内滚区到边界背景不动 / 无内滚区弹窗
  立即不连锁 / 弹窗叠加 1→2 退栈恢复 / DevTools 触屏模拟 / 老 Safari 特征模拟兜底生效) 待用户真机确认;
  caniuse 对 overflow:hidden+contain 组合全线标 partial support, 无权威反例 bug 单 (报告 §8.4 未证实项)
