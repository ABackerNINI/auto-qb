# 浏览器冒烟 · 其它环境坑原文(外迁)

> 摘要: `pitfalls/testing/smoke.md`「其它环境坑(一批)」条原文整体外迁(2026-11-05 压缩), 正文原样照搬, 标题降一级以避开坑档条目扫描。
> 触发: window-size 钳制, iframe, file:// anchor 空白图, 整页截图裁剪, 平铺底纹, dump-dom 一行, headless=new 挂起, 注入路由 404, StaticFiles 遮蔽

## 其它环境坑(一批)

- **触发**: 冒烟环境相关的怪现象。
- **判别 / 处置**:
  · `--window-size` 在 Windows 被**最小窗口宽度钳制**(要验真窄屏就外层包 **iframe**);
  · `file://...#anchor` 截中间区块得到**空白图**(注入 `display:none` 把目标顶到首屏);
  · 整页截图 + PIL 自动裁剪在有**平铺底纹 / 渐变**的页面上失效;
  · `--dump-dom` 里顶层 DOM 是**整整一行**(按行 grep 全落空);
  · `--headless=new` 在本环境曾**挂起**(回落 legacy);
  · **注入路由必须插到 `app.router.routes` 最前**(否则被 `StaticFiles` 挂载遮蔽返回 404);
  · 注入脚本必须放 `<head>`(在 app.js 读 localStorage **之前**)。
