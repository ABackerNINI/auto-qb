# 05-console-hub · 设置页重构设计方案

> 配套文件：`05-console-hub.html`（可交互样张）、`index.html`（挑选页）、`_shared/theme-tokens.css`。
> 本文是**给"正式改造代码"看的说明书**——包含设计决定、**踩过的坑**、可直接抄的 CSS，
> 以及落地到 `src/auto_qb/` 的文件清单。先读完第 8 节（踩过的坑）再动手，能省掉大半返工。

---

## 1. 这套是什么

| 维度 | 取自 | 落地形态 |
|---|---|---|
| **视觉语言** | 方案 A · 仪表台 Console（Ash Thorp `15-ash-thorp.html`） | 方角（用户覆盖，不用切角）、等宽读数、分段 LED 状态条、1px hairline、左上方向光渐变 |
| **信息架构** | 方案 C · Hub & Spoke | 首页 = 状态卡片网格 + 搜索 + 「建议你看一下」；点进二级页只处理一个分区，顶部面包屑退回 |
| **说明文字** | 方案 D · 双栏说明的**内容** | 改成**就近浮窗**（行尾 `?` 点开），不占常驻侧栏 |
| **控件** | Ash Thorp 输入框/按钮 + Fathom `04-fathom.html` 开关 | 按钮一律不带橙填充；开关 44×24 方角 + 18px 纯白滑块 |
| **发光** | Ash Thorp `.input:focus` 原值 | 见第 6 节，令牌化后全站统一 |
| **语义色** | 新增 | 常规 `--accent` / 重要 `--warn` / 危险 `--error`，描边与发光同色 |

为什么要三套合一：C 解决"设置项太多找不到"，D 解决"说明写不下、写得太技术"，
A 提供辨识度。三者拼起来正好覆盖现有设置页的全部毛病（乱 / 硬 / 丑 / 描述不对）。

---

## 2. 视觉语言（A）

- **方角**：控件层一律 `border-radius: 0`、无 `clip-path`。切角只在**大面**（卡片/块/规则卡/曲线卡/分区图标）保留 10px 作为 A 的签名——见坑 ①。
- **等宽读数**：所有数值/地址/端口/密钥用 `var(--font-mono)`（`--font-display` 给标题）。
- **分段 LED**：状态指示用 `repeating-linear-gradient` 分段光条，三态 `ok`(绿) / `warn`(橙) / 默认(灰)。比圆点更贴合"仪表台"。

  ```css
  .led { width:34px; height:7px; background: repeating-linear-gradient(90deg, var(--fg-dim) 0 5px, transparent 5px 8px); }
  .led.ok   { background: repeating-linear-gradient(90deg, var(--green) 0 5px, transparent 5px 8px); }
  .led.warn { background: repeating-linear-gradient(90deg, var(--warn)  0 5px, transparent 5px 8px); }
  ```

- **左上方向光**：卡片/面板叠一层很淡的渐变，底色不变只给光源方向。

  ```css
  background-image: linear-gradient(135deg, var(--surface-1), transparent 46%);
  ```

---

## 3. 信息架构（C）

```
首页（Hub）
 ├ 标题 + 「7 个分区 · 共 60 项 · N 项尚未保存」   ← 等宽读数
 ├ 搜索框（按配置项名直跳，不用记它在哪个分区）
 ├ 「有 1 项建议你看一下」警示条（把风险项主动推到面前）
 └ 卡片网格：每张卡 = 图标 + 标题 + 一句人话描述 + LED 状态 + 读数徽标
      ↓ 点击
二级页（Spoke）
 ├ 面包屑：设置 / 分区名（一步退回）
 ├ 分区标题 + 一句 lede
 ├ 块（blk）→ 行（row）：标签 | 控件 | 「?」说明钮
 └ 底部动作条：放弃改动 · 保存并应用
```

站点/规则集在二级页内用**切角小标签（pill）**切换，不再做左右主从两栏。
规则用「条件 → 动作」两栏卡片表达（`.rule-flow` / `.step`），危险动作标 `.step.danger`。

---

## 4. 说明浮窗（D 改形态）

- 触发：行尾一个 `?` 小按钮（22×22，方角）。
- 浮窗内容沿用 D 的五段：**它是什么 / 默认值 / 什么时候需要改 / 注意（风险）/ 容易和它搞混的**。
- 定位：`position: fixed`，优先放触发点右侧，右边放不下翻左侧，垂直夹在视口内。
- 箭头**必须是独立的兄弟元素**，不能做浮窗的子元素——浮窗若带 `clip-path` 会把箭头裁掉（本项目浮窗是方角，但保留这个写法以防将来加切角）。
- 关闭：点外部 / Esc / resize / 容器滚动。
- 内容来源：富条目走 `EX[key]`，其余回退到行的 `data-note` / `data-def` / `data-risk`。
  **真实实现应由 schema 的 `help` / `risk` / `default` 拼出**，见第 10 节。

---

## 5. 控件规范

### 输入框 / 下拉框（Ash Thorp `15-ash-thorp.html:342`）

```css
padding: 10px 14px;                      /* Ash 原值 */
background-color: var(--bg-sunken);      /* 沉底，比卡片更暗 */
border: 1px solid var(--tone-line);      /* 静息 = tone 淡版 */
border-radius: 0;
```

### 按钮（四档，一律**不带橙色填充**）

| 档 | 类 | `--tone` | 静息描边 | hover |
|---|---|---|---|---|
| 次要 | `.u-btn` | `--fg-dim` | `--tone-line` | `--tone` + `--glow-soft` |
| 重要 | `.u-btn.important` | `--warn` | `--tone-line` | `--tone` + `--glow-soft` |
| 主行动 | `.u-btn.primary` | `--accent` | `--tone-line` | `--accent-hi` + `--glow` |
| 危险 | `.u-btn.danger` | `--error` | `--tone-line` | `--error` + `--glow-soft` |
| 安静 | `.u-btn.ghost` | transparent | 无 | 只点亮文字，不发光 |

橙渐变实心只出现在 Ash Thorp 的 `.btn`（主 CTA）上——设置页有几十个按钮，全用实心会把主次冲掉，所以这里一律描边型。

### 开关（Fathom）

```css
.u-switch .sw-track { width:44px; height:24px; border-radius:0; background: var(--tone-line); }
.u-switch .sw-track::after { width:18px; height:18px; top:3px; left:3px; background:#fff; }  /* 纯白滑块 */
.u-switch input:checked + .sw-track { background: var(--tone); }
.u-switch input:checked + .sw-track::after { transform: translateX(20px); }                  /* 行程 20px */
```

⚠ 不能写死 Fathom 的深海军蓝 `#1d3a54`——那是亮色主题的色，在本项目 3 套暗色主题上等于隐形。

---

## 6. 发光系统

### Ash Thorp 原值（`15-ash-thorp.html:344`，风格覆写层）

```css
.input:focus{
  outline:none;
  border-color:var(--primary);
  box-shadow: inset 0 0 0 1px var(--primary),
              0 0 22px -6px rgba(255,138,61,.8);
}
```

### 令牌化复刻（`--primary` → `--tone`，`rgba(...,.8)` → `color-mix 80%`）

```css
--glow: inset 0 0 0 1px var(--tone),
        0 0 22px -6px color-mix(in srgb, var(--tone) 80%, transparent);
--glow-soft: inset 0 0 0 1px color-mix(in srgb, var(--tone) 50%, transparent),
             0 0 16px -8px color-mix(in srgb, var(--tone) 60%, transparent);
```

> `inset 1px` + 外层 `22px/-6px` 加起来在边缘形成**紧贴同色的 2px**——这正是 Ash Thorp 的观感（一道"被点亮的粗边" + 大范围柔光）。
> 它不是"两个描边"；真正的两个描边来自原生 select 外框和浏览器 focus ring（坑 ⑤⑥）。

### 实测配方对比（指标 = 描边外 1px 处发光强度占描边色的百分比）

| 配方 | 边缘强度 | 判定 |
|---|---|---|
| 正 spread `0 0 10px 3px / 0 0 26px 8px` | **76%** | ❌ 几乎和描边一样亮 |
| 零 spread `0 0 12px 0 / 0 0 28px -6px` | 45% | 偏亮 |
| 负 spread `0 0 16px -3px / 0 0 34px -10px` | 36% | 柔和但清晰 |
| **Ash Thorp `0 0 22px -6px @80%`** | **18%** | ✅ 采用 |
| 超大负 spread | 10% | 太弱 |

---

## 7. 语义化语调（三档）

```css
/* 常规 */  --tone: var(--accent);
/* 重要 */  .important { --tone: var(--warn); }   /* 影响面大但可逆：凭据、改了要重启、弱化安全边界 */
/* 危险 */  .danger    { --tone: var(--error); }  /* 破坏性/不可逆：明文密码、对外暴露、删除 */
```

三态同色相，只变强度：

```
静息 --tone-line (color-mix 45%)  →  悬浮/聚焦 --tone (实)  →  聚焦再叠 --glow (发光)
```

模板中已标注：**危险** = qB 密码（明文写盘）、WEB 监听地址（可暴露）；
**重要** = 数据目录（改了要重启）、访问密钥（凭据）、跳过本机验证开关；
**危险按钮** = 删除曲线、删除站点。

---

## 8. 踩过的坑（**动手前必读**）

### ① 切角和发光是死敌
`clip-path` 会把 `box-shadow` **和** `filter` 的外发光**整圈裁掉**。
只剩 `drop-shadow` 一条路，而它**没有 spread 参数**，调来调去不是糊就是弱。
→ **结论：控件层不要切角**，切角只留给大面。

### ② 正 spread 会让边缘**更亮**（我搞反过）
正 spread 把阴影**实心区**铺到元素外，边缘 alpha 最高；真正让边缘变暗的是**负 spread**（把实心区推到元素底下，只露模糊尾巴）。

### ③ `box-shadow` 做光，**不要用 `blur=0` 的层**
`0 0 0 Npx ...` 是一个**边缘锐利的实环**，叠在 1px 描边外 = "描边加粗"。要做硬边光环才用它，否则一律 `blur ≥ 1`。

### ④ 元素已有 1px 实描边时，**不要自己叠 inset 环**
两道同心线一定被读成"描边加了一圈"。
（例外：Ash Thorp 原版**有** `inset 0 0 0 1px`，但它与 border **紧贴同色**，形成的是 2px 实边而非两道线——用户最终选择复刻原版。）

### ⑤ 原生 `<select>` 必须 `appearance: none`
否则浏览器自带一圈外框 + CSS 的 1px 边框 = **两道线**。
`_shared/demo.css` 里 `.u-select` 写了、`.demo-bar select` **漏了**——同类控件要**配对检查**。

### ⑥ `<select>` 聚焦必须 `outline: none`
否则**浏览器 focus ring** 又叠一圈。实测在描边外 2~3px 量到 `#5cc3c3`（比 accent 还亮的青），就是它。

### ⑦ ⚠ 最重要：**CSS 自定义属性会被"固化"**
自定义属性是「**在元素上计算一次，再按计算值继承**」，不是"用时才替换"。

在 `:root` 写 `--glow: ... var(--tone) ...` ⇒ 在 `:root` 上就把 `var(--tone)` 替换成 `:root` 的 `--tone`(accent) 并**固化**，后代继承到的是不含 `var(--tone)` 的成品——之后在任何后代覆盖 `--tone` **完全无效**。

实测症状（密码框 danger）：静息描边**青**（派生变量固化）/ hover 描边**红**（`border-color: var(--tone)` 现算）/ 聚焦**红描边 + 青 inset 环 + 青发光**。

**修法：派生变量必须声明在使用 `--tone` 的那一层元素上**（与 `--tone` 覆盖规则命中同一元素）：

```css
:root { --tone: var(--accent); --tone-soft: var(--accent-soft); }   /* 只放默认值 */

.u-input, .u-select, .u-btn, .card, .pill, .ask, .u-switch, .demo-bar select {
  --tone-line: color-mix(in srgb, var(--tone) 45%, transparent);
  --glow: inset 0 0 0 1px var(--tone),
          0 0 22px -6px color-mix(in srgb, var(--tone) 80%, transparent);
  --glow-soft: inset 0 0 0 1px color-mix(in srgb, var(--tone) 50%, transparent),
               0 0 16px -8px color-mix(in srgb, var(--tone) 60%, transparent);
}
```

实测四格对比确认：旧写法 danger 仍 `#3aa6a6` 青 ❌；新写法 danger 正确 `#f3766f` 红 ✅。

### ⑧ 描边色与发光色必须**同一个来源**
曾经 `.u-select:hover` 描边写 `--fg-dim`（灰）、发光走 `--accent`（青），一灰一青。
→ 凡是有发光的 hover/focus 态，描边一律 `var(--tone)`。

### ⑨ 不要靠肉眼"看截图"验证
本机环境**没有 PIL**，截图也未必真能看清。
→ 写了极简 PNG 解码器 `pngscan.py`（zlib + 5 种 scanline filter 反算，支持 8bit RGB/RGBA 非隔行），
把几何用注入 CSS 固定后扫一条横切线，读 hex 值。**"看着有两个边/颜色不对"一律先扫像素。**

---

## 9. 文案改写对照（schema 落地时直接搬）

| 现在 | 改成 | 原因 |
|---|---|---|
| qBittorrent 连接与主循环节奏 | 让 auto-qb 连上你的 qBittorrent，并决定它多久检查一次 | 「主循环」是实现词 |
| 落盘轮转与格式 | 日志记在哪、留多久、记多细 | 回答用户真正关心的三个问题 |
| 图形界面的监听与鉴权 | 这个浏览器界面怎么开、谁能访问 | 用户不知道"监听/鉴权"指的就是眼前这个界面 |
| WARNING 及以上日志推送平台原生通知 | 出错或有风险操作时，用电脑的系统通知提醒你 | 原说法要求读者先懂日志级别 |
| 主循环间隔 | 检查间隔 | 说它做了什么，不说它叫什么 |
| 轮转大小 | 单个日志文件上限 | 「轮转」是行业黑话 |
| 保存并热重载 | 保存并应用 | 用户不需要知道"热重载" |
| 未配置条件 = 对所有匹配该规则的种子执行动作 | 没配条件 = 这条规则总是执行 | **原文有歧义/不准**：无条件时不是"匹配才执行" |
| （无说明） | 端口：注意别和「界面与日志 → 端口」搞混 | 两个端口最容易填错 |

---

## 10. 落地到真实代码

### 文件清单

| 改动 | 文件 |
|---|---|
| 设置页模板（两套 UI 各一份，目前是复制关系） | `src/auto_qb/web_ui/static/prism/index.html`、`static/atlas/index.html` |
| 字段渲染组件 | `static/shared/config_editor.js` + `index.html` 里的 `<script id="tpl-ce-field">` |
| 设置页样式 | `static/prism/css/views.css`（`.ce-*` 段）、`static/atlas/style.css` |
| **分组/字段文案**（内容改动最大） | `src/auto_qb/config/schema/groups.py`（`Group(...)` 的 help、`Field(...)` 的 help/risk）+ `trackers.py`、`rules.py` |
| 新增 schema 字段（浮窗需要 default / when / 易混淆项） | `src/auto_qb/config/schema/fields.py` + `config/validation`（**新键必须进 `validate_config` 并同步 `config/schema.py`**） |

### 映射到 Vue

- 字段外壳做成组件（历史上叫过 `.fi`，**当前方案不需要**——输入框是普通的 `<input>`，样式全靠 `.u-input`）。
- 说明浮窗做成一个 `<CeHelp>` 组件：`?` 按钮 + 单例浮层（挂在 body 上，`position: fixed`）。
- 首页卡片从 schema 分组生成，状态徽标/读数由 `config.schema` 的分组元信息 + 运行时状态拼出。
- 主题：**不要写死颜色**。全部走 `css/tokens.css` + `css/themes/*.css`（现有 5 套：ocean / galaxy / frost / golden / orbit，其中 frost、golden 是**亮色**）。
- Ash Thorp 暖炭 + 暖橙若要做成第 6 套主题：新增 `css/themes/ash.css` + `js/theme.js` 注册表加一行即可，**与版式是独立决定**。

### 现有设置页的旧结构（改造时要拆掉的）

- 五种折叠容器：`ce-group` / `ce-section` / `ce-subcard` / `pattern_list` 折叠列表 / 规则卡折叠——语义重叠，收敛成「块 → 行」两层 + 站点/规则集用 pill 切换。
- 一律「标签 | 控件」两列导致说明只能当小字——改成说明进浮窗，行本身更紧凑。
- 普通分组是卡片、站点/规则/限速各一套布局——统一成同一套 `.blk / .row`。

---

## 11. 验收清单

- [ ] 切主题（含 frost / golden 两个**亮色**）后：输入框、下拉框、按钮、卡片、开关、发光全部正常，没有"隐形"或"过曝"。
- [ ] 每个可交互 + 有边框的对象在 hover / focus 下都发光，且**描边与发光同色**。
- [ ] danger / important 档：**静息描边就是语义色**（不聚焦也能看出轻重），且发光同色——按第 7 节实测方法扫像素确认，不要只看。
- [ ] `<select>`：无原生外框（`appearance:none`）、无浏览器 focus ring（`outline:none`）、有自绘箭头。
- [ ] 说明浮窗：点 `?` 就近弹出，Esc / 点外部 / 滚动都能关，窄屏不越界。
- [ ] 首页卡片：LED 三态正确、读数正确、"建议你看一下"能指向风险项。
- [ ] 文案：第 9 节对照表全部替换，且 schema 的新键已进 `validate_config`。
- [ ] 全量测试：`uv run pytest tests -q`（前端静态资源有 `test_web.py::test_frontend_static_bundle_health` 之类守阵，改完必跑）。
