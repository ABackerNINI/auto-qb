# 界面切换改顶栏下拉直选 —— 三套 UI 全列、当前项标记、点选直达

> 摘要: 用户报「三套 UI 切换方式不直观」, 环形互切链接(只能切到下一套, 看不到全部可选项)
> 改为顶栏右半部**下拉直选**。先做评审模板 resources/navbar-right-template.html(三皮肤令牌
> 面板 + 可交互), 浏览器截图自检通过后落地: topbar.html 单链接 → 按钮 + .pop-menu 复用面板;
> state.js 环形表 → UI_HOME 单点 + uiCurrent/uiOptions; lifecycle.js 挂点空白/Esc 关闭链。
> 三套 CSS 净增 0 行(atlas components.css 恰好顶满 700 行上限)。三皮肤真机冒烟全绿。
> 触发: 界面切换, 皮肤切换, 下拉, ui-link, UI_HOME, uiMenuOpen, 顶栏, topbar
> 最后活动: 2026-09-27 21:10

## 状态

**Done**(模板 + 落地 + 守阵全绿 + 三皮肤真机冒烟 + 文档回写 + **已提交推送: gitee/develop @ 3d0d1d2**)。

## 待办(下一步从这里接)

1. 用户确认 resources/navbar-right-template.html 观感(文案/描述/菜单宽度可再调, 调完重跑三套 CSS 对齐)。
2. 生产侧验证: 用户日常启动后看三套 UI 的下拉切换真实手感(qB 侧无任何配合改动)。

## 取证锚点(复核用)

- 基线 gitee/develop @ **b080086**(提交前再次同步: stash → ff-only → 施回, 无冲突; ls-remote 核实)。
- 改动: shared/tpl/topbar.html · shared/state.js · shared/lifecycle.js ·
  atlas/prism/console css/components.css(各成对改: .ui-tools position:relative /
  .ui-link font:inherit + .open / .pop-item text-decoration:none) · README.md;
  新增 resources/navbar-right-template.html · memory-bank/testing/baselines/26-09-27-ui-switch-dropdown.md。
- 测试: test.full **1752 passed + 3 skipped / 91%**(18.52s, b080086 基线; 合入远端 HR 绑定映射制后
  复测); 前端守阵(分片接线/CSS 括号/挂件类/_UI_ALL 成对)全绿。切片数超限按守卫蒸馏
  26-09-22-2318(纯指针件)后 test_memory_bank 24 passed。
- 冒烟: 三皮肤(星图/棱镜/控制台)经临时 stub + Playwright 截图与交互全链路 ✓;
  期间踩「静态资源启发式缓存」已记坑一次(自建 stub 漏 no-cache), 复发 +1 已回写
  pitfalls/web-ui/template-render.md。
