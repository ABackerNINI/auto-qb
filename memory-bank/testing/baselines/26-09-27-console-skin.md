# 1725 passed + 1 skipped —— 第三套 UI「控制台」(console 皮肤)落地

> 摘要: 实施 resources/main-ui-templates/(Console Hub 仪表台风格): 新增 `static/console/`
> 第三套皮肤(index.html shell + style.css 令牌基线 + css/components·views·dialogs 三层),
> 与 atlas/prism 并列、后端零改动(目录即 UI); shared/state.js 皮肤判定扩三值(_aqbDetectUi)
> + uiSwitchTarget 改三套环形互切; tests/test_web.py 双 UI 守阵扩档为
> `_UI_ALL = ("atlas", "prism", "console")`(backdrop 计数对齐 / 清单逐项相等 / 差异口白名单 /
> bt·meta·ctx CSS 成对断言 / CSS 链接序守阵)。皮肤差异纯 CSS: 方角控件(圆角令牌归零) +
> 大面切角 14px(clip-path 只给卡/弹窗/投放区) + 负 spread 发光 + 数值读数 mono +
> 分布条/进度条分段 LED(纯 CSS 替换) + 批量操作条改底部悬浮指令条(.bulk-inline 纯 CSS 定位)。
> 浏览器实测(测试替身 + uvicorn + Playwright 截图): 登录/分组/种子/悬浮批量条/删除确认/添加
> 弹窗全部渲染正确; 截图轮次里唯一 500 来自临时替身缺 `.api` 属性(种子标签端点), 与本次
> 纯前端改动无关。基线时间: 2026-09-27。

- **测试**: 1725 passed + 1 skipped(+2 来自远端 0eb87da 文件访问层审查修复的守阵, 本轮扩档不加测试); test.full 16.03s。
- **改动面**: 新增 `static/console/`(5 文件) / 改 `shared/state.js`(皮肤判定 + 互切环) /
  `tests/test_web.py`(守阵扩三档) / README.md·`__init__.py`·conventions/webui.md「两套」表述。
  现有两套皮肤(atlas/prism)文件零改动。
- **覆盖率**: TOTAL 91%(11546 语句 / 846 未覆盖 / 3842 分支 / 343 partial; 数字取自合并远端 0eb87da 之后的合并树; 1 采样)。
