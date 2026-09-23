# 浏览器站点级"关闭时清除站点数据" —— 偏好整站被清(真因已收口)

> 摘要: 用户报"浏览器重启后 localStorage 重置(所有偏好一起回默认)"。**真因不在应用**: 浏览器站点级 cookie 例外 `127.0.0.1,*` `setting=4`(SESSION_ONLY = "关闭窗口时清除 Cookie 和站点数据")会在关浏览器时把该 **host 全部端口**的 Cookie 与 localStorage 一起清 —— Edge/Chrome 各有一条(2023-12 / 2018 设)。已删 Edge 那条 + 前端提示补上这条通道与自查路径 + 守阵/知识库回写; Chrome 那条待用户退出 Chrome 后处理。
> 触发: 浏览器重启, 偏好回默认, localStorage 被清, 关闭窗口时清除, SESSION_ONLY, cookie 例外, 列设置被重置
> 最后活动: 2026-09-24 04:05

## 状态

**已完成**(本 clone):

- 真因取证: `Default/Preferences` → `profile.content_settings.exceptions.cookies` 里 `127.0.0.1,*` `setting=4`;
  三条现象全部自洽(会话内刷新正常 / 其它网站正常 / 全局 `clear_browsing_data_on_shutdown` 未开)。
  排除应用侧: 全仓无 `localStorage.clear()`, 唯一写入口 `persistPage` 只在用户操作时调, 启动路径只读不写。
- **删掉 Edge 那条例外**(改前备份 `Preferences.bak-autoqb-20260924`; `protection.macs` 与
  `Secure Preferences` 都不含 `content_settings` ⇒ 无 MAC 保护, 可直接改)。**下次启动 Edge 生效**。
- 前端: `shared/columns.js::_showColsOriginHint` 文案改为"事实 + 两条成因 + 自查路径"
  (`edge://settings/content/all` / 改用 `localhost:<端口>`), 并补 `sessionStorage` 会话级去重。
- 守阵: `test_frontend_cols_empty_hint_names_browser_clear_cause`(含 `test_web.py` 头部测试计划清单)。
- 回写: `pitfalls/web-ui/columns-persist.md`(新增 ❗ 条, "两种重置"→"三种")· `想法.md` 该条补结论 ·
  `testing/baseline.md` 1203 collected · `tasks/26-09-20-webui-column-prefs-reset.md` 进度日志。

**实测**(提交时刻): 全量 **1202 passed + 1 skipped**(原 1201+1, 未退化) / TOTAL 91% /
真浏览器(本 clone 桩服务 8200)提示条渲染与文案逐字一致。

## 待用户处置

1. **Chrome 的同类例外还在**(用户已要求删; 但 Chrome 当时有 8 个进程在跑, 改 `Preferences` 会被退出时覆盖)
   —— 等用户完全退出 Chrome 后按同法删 `127.0.0.1,*`。
2. **正在跑的实例是另一个 clone**: `38081` = `auto-qb-long-seeding`(独立 `.venv` + 自己的 src)。
   本次前端改动只在 clone2, 那边要看到新提示得自行同步代码(跨 clone 写操作按红线未动)。
3. 被清掉的偏好找不回来 —— 重设一次后关/开浏览器验证持久化。

## 单点指针

- 机理与处置全文 → [../pitfalls/web-ui/columns-persist.md](../pitfalls/web-ui/columns-persist.md)
- 列偏好重置全史(四轮修复 + 本次真因) → [../tasks/26-09-20-webui-column-prefs-reset.md](../tasks/26-09-20-webui-column-prefs-reset.md)
- 测试数字单点 → [../testing/baseline.md](../testing/baseline.md)
