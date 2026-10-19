# 弹窗宽度档位与内容形态错配: 编辑框骑通用基档, 长值被输入框裁掉

> 摘要: 弹窗宽度档位与内容形态错配: 编辑框骑通用基档, 长值被输入框裁掉
> 触发: 弹窗太小, 对话框太小, 重命名弹窗, modal 宽度, 宽度档位, --modal-w-base, --modal-w-add, rename-dialog, 输入框裁掉, 长名显示不全, 种子名显示不全, 弹窗宽度档, cls 附加类, _openModal cls, 编辑对话框宽度
**Refs:** memory-bank/tasks/26-10-19-webui-modal-width-tier.md

### 通用 modal 基档(520)是为「确认/提示一句话」设计的 —— 字段值是长文本的编辑框骑上去, 输入框裁名

- **触发**: 给通用 `.modal`(popovers.html 单例模态, `_openModal` 开)加**编辑类**对话框( fields 多字段表单), 且字段值天然是长文本(种子显示名/路径/URL), 却沿用缺省宽度 —— 缺省 = `.modal` 基档 `--modal-w-base` 520px(注释原话「标准: 确认框 / 输入框」), 输入框实得仅 474px。2026-10-19 重命名对话框即此: 用户报「弹窗太小」, 实测(1440x900 双皮肤同数)97 字符真实长名 `scrollWidth 695 > clientWidth 472` ⇒ **裁掉 223px**, 近三分之一不可见, 改个名得在输入框里左右滚。同族先例: 同日「设定位置」弹窗(骑 560 窄档)用户报「太小 + 下拉显示不全要滚动」, 修法同样是加宽到 `--modal-w-add` 860(见 combobox-focusout-close 第五轮)。
- **判别**: ①用户报「弹窗太小 / 显示不全 / 要滚动」而功能逻辑全对 —— 先量几何再谈逻辑; ②量 `input.scrollWidth - input.clientWidth`, 正数即被裁(桩数据常恰好不裁: 桩名 43 字符 fits 474px, 真名 80~120 字符不 fits —— **冒烟全绿也照样裁**, 必须注入真实感长名才暴露); ③档位表(三皮肤 tokens/style.css 同值): narrow 460(单列小表单)/ base 520(确认·提示)/ form 560(双列编辑)/ add 860(添加种子·移动·历史流量)/ wide 920(删除确认)。字段值是长文本的编辑框只配 860 档。
- **处置**: ①加宽到 `--modal-w-add`(与添加种子/设定位置同档, 同一右键菜单里相邻的编辑对话框同宽也顺眼); ②挂法走 `_openModal` 的 `cls` 附加类选项 —— `ui_feedback.js _modalInit` 单点声明 `cls: ""`(空 = 既有对话框零变化, 不进初值则后补属性不进 Vue 响应 = 挂类不生效), popovers.html 模态根类绑定 `:class="[{ danger, wide }, modal.cls]"` 并入, 调用方传 `cls: "rename-dialog"`; ③三皮肤 CSS 成对写 `.modal.rename-dialog { width: var(--modal-w-add); }`(css-perf-parity: 漏一档 = 该皮肤仍旧宽)。不要为单对话框新造宽度变量 —— 档位表是跨对话框的语义层, 新增一档全部注释与文档都要跟着改。
- **守阵**: 静态 `tests/test_webui_static_dom_panel.py::test_frontend_rename_dialog_width_wiring`(cls 字段/模板绑定/传类/三皮肤宽档规则四锚); e2e `e2e/rename-dialog-fit.spec.mjs`(双皮肤 @fast: 860 宽档 + 97 字符长名 `scrollWidth <= clientWidth` 零裁剪 + 取消零提交; 三条断言各自红验过 —— 回退 CSS 时宽度 860→520、输入框 814→474、裁剪 0→223 逐个判红)。
- **教训**: ①「弹窗太小」这类观感报障的根因常在**宽度档位与内容形态错配**, 不在布局 bug —— 复用通用视觉体系时, 档位选择要按**本对话框的内容**(字段值是长文本吗)复核, 不能因为「都是模态框」就骑缺省档; ②桩数据不暴露 ≠ 没缺陷: 桩名 43 字符恰好 fits 基档, 几何守阵必须注入真实感数据(长名)才有鉴别力; ③连带产出: 通用 modal 自此有了 per-dialog 定制类的正规出口(cls 选项), 后续同类需求(编辑框骑基档)直接复用, 不要再复制模板或新造变量。
