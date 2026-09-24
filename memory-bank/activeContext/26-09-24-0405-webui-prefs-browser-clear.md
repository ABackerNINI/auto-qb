# 浏览器站点级"关闭时清除站点数据" —— 偏好整站被清(真因已收口)

> 摘要: 用户报"浏览器重启后 localStorage 重置(所有偏好一起回默认)"。**真因不在应用**: 浏览器站点级 cookie 例外 `127.0.0.1,*` `setting=4`(SESSION_ONLY = "关闭窗口时清除 Cookie 和站点数据")会在关浏览器时把该 **host 全部端口**的 Cookie 与 localStorage 一起清 —— Edge/Chrome 各有一条(2023-12 / 2018 设), **两条均已删除**(复查 `exceptions.cookies` 皆空)。前端提示已补上这条通道与自查路径, 守阵/知识库已回写。
> 触发: 浏览器重启, 偏好回默认, localStorage 被清, 关闭窗口时清除, SESSION_ONLY, cookie 例外, 列设置被重置
> 最后活动: 2026-09-24 04:35

## 状态

**已完成**(本 clone):

- 真因取证: `Default/Preferences` → `profile.content_settings.exceptions.cookies` 里 `127.0.0.1,*` `setting=4`;
  三条现象全部自洽(会话内刷新正常 / 其它网站正常 / 全局 `clear_browsing_data_on_shutdown` 未开)。
  排除应用侧: 全仓无 `localStorage.clear()`, 唯一写入口 `persistPage` 只在用户操作时调, 启动路径只读不写。
- **删掉 Edge 那条例外**(改前备份 `Preferences.bak-autoqb-20260924`; `protection.macs` 与
  `Secure Preferences` 都不含 `content_settings` ⇒ 无 MAC 保护, 可直接改)。**下次启动 Edge 生效**。
- **Chrome 同类例外也已删**(同日): 先前那 8 个 `chrome.exe` 是**别的会话遗留的无窗口桩**
  (`--user-data-dir=H:\Temp\HeadlessChrome…`, 不碰用户 Default 配置), 关闭后按同法删掉 `127.0.0.1,*`。
  复查: **两个浏览器的 `exceptions.cookies` 现均为空**。
- 前端: `shared/columns.js::_showColsOriginHint` 文案改为"事实 + 两条成因 + 自查路径"
  (`edge://settings/content/all` / 改用 `localhost:<端口>`), 并补 `sessionStorage` 会话级去重。
- 守阵: `test_frontend_cols_empty_hint_names_browser_clear_cause`(含 `test_web.py` 头部测试计划清单)。
- 回写: `pitfalls/web-ui/columns-persist.md`(新增 ❗ 条, "两种重置"→"三种")· `想法.md` 该条补结论 ·
  `testing/baseline.md` 1203 collected · `tasks/26-09-20-webui-column-prefs-reset.md` 进度日志。

**实测**(提交时刻): 全量 **1202 passed + 1 skipped**(原 1201+1, 未退化) / TOTAL 91% /
真浏览器(本 clone 桩服务 8200)提示条渲染与文案逐字一致。

## 待用户处置

1. **正在跑的实例是另一个 clone**: `38081` = `auto-qb-long-seeding`(独立 `.venv` + 自己的 src)。
   本次前端改动只在 clone2, 那边要看到新提示得自行同步代码(跨 clone 写操作按红线未动)。
2. 被清掉的偏好找不回来 —— 重设一次后关/开浏览器验证持久化(两套存储各设一次: `127.0.0.1:38080` 与 `:38081`)。

## 单点指针

- 机理与处置全文 → [../pitfalls/web-ui/columns-persist.md](../pitfalls/web-ui/columns-persist.md)
- 列偏好重置全史(四轮修复 + 本次真因) → [../tasks/26-09-20-webui-column-prefs-reset.md](../tasks/26-09-20-webui-column-prefs-reset.md)
- 测试数字单点 → [../testing/baseline.md](../testing/baseline.md)
