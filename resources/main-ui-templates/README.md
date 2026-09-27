# main-ui-templates · 全新 UI 模板(Console Hub 风格)

> 参照 [settings-page-templates/05-console-hub.html](../settings-page-templates/05-console-hub.html) 的设计语言,
> 并以落地版 `src/auto_qb/webui/static/shared/console_hub.css` 的**用户实测微调值**为基线,
> 为设置页之外的四个界面出的简单模板。
> **定位(2026-09-27 更正): 这是一套全新的独立 UI —— 与 prism(棱镜)/atlas(星图) 并列的第三套皮肤,
> 不覆盖、不改造现有两套 UI 的任何文件。** 评审调整后实施。

## 文件

| 文件 | 内容 |
|---|---|
| `01-login.html` | 登录页(表单 / 验证中 / 服务不可达三态, 左下演示条切换) |
| `02-torrents.html` | 种子页(顶栏 + 分布条/筛选器 + **悬浮批量指令条** + 种子表 + 状态栏) |
| `03-dialog-add-torrent.html` | 添加种子弹窗(表单型原型, 860 宽档) |
| `04-dialog-delete.html` | 删除确认弹窗(危险语义原型, 920 宽档) |
| `archive/` | 历史版本快照(V1 = 首轮评审版), 严禁修改 |

两份弹窗覆盖两个极端形态, 其余弹窗(统计/限速/目录选择/分类管理/标签管理)由这两套派生:
表单类照 03, 只读/确认类照 04 换语义色。

## 设计语言(与 console_hub.css 完全同源, 直接抄这几条)

- **方角控件 + 切角只留大面**: 控件(border-radius:0)不切角——clip-path 会裁掉 box-shadow 发光(硬知识①);
  切角 10px 只给卡片/弹窗/投放区等大面, 内边距 ≥ 14px 保证内部控件聚焦发光不被裁。
- **发光配方**(Ash Thorp 原值, 负 spread): `--glow: inset 0 0 0 1px var(--tone), 0 0 22px -6px color-mix(...80%)`;
  `--glow-soft` 给悬浮态。派生变量必须声明在与 `--tone` 覆盖同层(硬知识③)。
- **语义三档**: 常规 accent / 重要 warn(凭据: 登录密钥输入框走 important) / 危险 error(删除确认全链)。
  静息描边即语义色, 描边与发光同色(硬知识⑧)。
- **等宽读数**: 所有数值/路径/密钥提示/列头用 `--font-mono`; 列头小号大写字距。
- **分段 LED**: 状态指示(登录服务状态/表格行状态/分布条/进度条)统一 `repeating-linear-gradient`
  5px 亮 + 3px 隙段光, 三态 ok 绿 / warn 橙 / 灰。
- **开关**: 38×21 方角 + 15px 白滑块 + 行程 17px(2026-09-25 微调值); 静息底 = 中性 `--border-strong`。
- **颜色零写死**: 每份文件内联的令牌块与 `prism/css/themes/ocean.css` 同源; 实施时换回 `css/tokens.css`
  + `themes/*.css` 引用, 五主题自动适配。
- **不做的事**: 不引外部字体、不加毛玻璃卡片底、不填橙实心按钮、不引入圆角。

## 实施映射要点

- **全新 UI 目录**(与 `static/prism/`、`static/atlas/` 并列, 如 `static/<新名>/`):
  自带 index.html + css/ + 复用 `shared/` 的 Vue 与模板层; 后端 UI 注册表加一档, 现有两套零改动。
- 类名沿用模板里的 `hb-` 前缀; `console_hub.css` 的组件段(输入/按钮/开关/LED/切角/发光令牌)可直接
  复制为新一层的组件基线 —— 设置页那套继续用它的, 互不影响。
- 弹窗骨架沉淀成与 `--modal-w-*` 五档配套的 `.hb-modal` 族, 03/04 是 860/920 两档的样子。
- 分布条/进度条改分段 LED 是**纯 CSS** 替换, 不动 JS 数据结构。
- 批量操作条 = 悬浮指令条(选中即浮现, 不再挤进分布条一行): 新增一个 fixed 容器 + 显隐动画,
  选中状态源不变。
