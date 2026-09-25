# WEB UI 右键次级菜单: hover 变灰 / 移出不消失 / 复制并入更多操作

> 摘要: 用户报右键次级菜单三条 —— ①二级菜单图标 hover 时变灰(`.ctx-item:hover .ico` 是后代选择器, 而 `.ctx-sub` 是父项 DOM 后代 ⇒ 整片刷成 `--fg-muted`; 且不加 `:where()` 压特异性时连语义色也一起被压); ②移出不消失(只有 `mouseenter` 展开, 没有任何收起); ③「复制」二级菜单移入「更多操作」。修法: CSS 改 `.ctx-item:where(:hover) > .ico`; 收起挂**父项** `mouseleave` 延迟 180ms(只为跨过 4px 缝隙, 面板自身只挂 `mouseenter` 撤销); 复制三项并入「更多操作」末尾, 一级只留一个入口。
> 触发: 右键菜单, 次级菜单, flyout, ctx-sub, 图标变灰, 子面板不消失, 更多操作, 复制, CTX-04/05/06
> 最后活动: 2026-09-24 23:10

## 状态

**已完成(改完未提交)** —— 6 个源文件 + 1 条静态守阵 + 8 条冒烟, 已对 HEAD 红验。

- ① CSS 两处缺一不可: `>` 限直接子级(否则 hover 父项连子面板一起染) + `:where(:hover)`
  把特异性压到 0(否则 hover 规则 0,3,0 压过语义色 0,2,0, 有色图标照样变灰)。
- ② 收起**只能挂父项**: `mouseleave` 在"离开该元素及其全部后代"时才触发 ⇒ 父项↔面板互切不误收;
  面板上再挂一条 mouseleave 会在"从面板回到父项"时误收(父项不会再收一次 mouseenter)。
  延迟 `SUB_CLOSE_DELAY_MS = 180` 只为跨过 `.ctx-sub` 的 4px 缝隙; 一级关闭 / 点击收合都要撤销定时器。
- ③ 一级 `has-sub` 从 2 个收敛到 1 个; `subMenu` 取值只剩 `"" | "advanced"`。
- 守阵 `test_web.py::test_frontend_ctx_submenu_single_entry_and_hover_close`;
  冒烟 `scripts/ui_smoke.cjs` +8 条(双 UI × 四: 入口唯一 / 复制三项在面板内 / 图标仍是语义色 / 移出后收起)。
- 实测: 全量 **1375 passed + 1 skipped**(另有 2 条 GBK 守阵因本 shell `PYTHONUTF8=1` 恒红 —— 非代码缺陷,
  与上一轮同一结论) / 冒烟 **92 项 0 失败**(单 UI 各 46)。
- 红验: 临时回退棱镜两处 ⇒ CTX-04(图标 = `--fg-muted`)、CTX-05(残留 1 个)双双变红, 已恢复。

## 待用户处置

1. **未提交** —— 要入库说一声(提交口径: commit + push Gitee,  GitHub 镜像尝试一次)。
2. 「更多操作」面板现有 11 项(队列 4 / 开关 4 / 复制 3); 面板是 `position: absolute` 且**未做纵向钳位**,
   视口很矮时可能顶出屏幕下沿 —— 属既有形态(合并前 8 项就未钳位), 未按范围守恒处理, 仅报告。

## 单点指针

- 判据 → [../pitfalls/web-ui/overlays.md](../pitfalls/web-ui/overlays.md)(条目「flyout 次级菜单」)
- 分层原则 → [../conventions/webui.md](../conventions/webui.md) · 任务档案 → [../tasks/26-09-24-webui-ctx-submenu.md](../tasks/26-09-24-webui-ctx-submenu.md)
