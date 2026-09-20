# Third-Party Attribution Notice

> 本目录下的内容部分衍生自开源项目 **open-design.ai**，遵循 MIT 协议。
> 本文件用于记录来源、修改与第三方品牌商标声明，符合 MIT 协议的归属要求。

---

## 一、源项目信息

| 项 | 内容 |
|---|---|
| 项目名 | open-design.ai |
| 组织 | OpenCoworkAI |
| 仓库 | <https://github.com/OpenCoworkAI/open-codesign> |
| 协议 | MIT License |
| 版本 | 0.7.0（本仓库 copy 时） |
| 原始版权 | Copyright (c) 2026 OpenCoworkAI |
| 完整协议文本 | 见同目录 [`LICENSE.md`](./LICENSE.md) |

---

## 二、本仓库使用的源项目子目录

以下子目录的内容衍生自 open-design.ai：

| 本仓库路径 | 源项目对应路径 |
|---|---|
| `design-skeletons/` | `Open Design.app/Contents/Resources/open-design/design-templates/` |
| `design-systems/` | `.../design-systems/` |
| `skills/` | `.../skills/` |
| `craft/` | `.../craft/` |
| `prompt-templates/` | `.../prompt-templates/` |
| `frames/` | `.../frames/` |

---

## 三、修改说明

以下修改已应用于源项目内容：

### 新增

- 新增 `design-skeletons/saas-landing/` —— 完整中文化骨架（仅 `SKILL.md` 和 `example.html`，与源项目同名目录区分）

### 删除

- 删除 `community-pets/` —— 桌面陪伴动画 sprite（与设计 agent 功能无关）
- 删除 `bin/` —— Node 二进制运行时（autoclaw 平台已自带）
- 删除 `design-skeletons/AGENTS.md` —— open-design 桌面 app 内部 API 端点开发文档（与本仓库 agent 配置无关）

### 改名

无重命名操作。`design-templates/` 在本仓库下改名为 `design-skeletons/`（语义更明确，但 SKILL.md 内部路径引用未受影响）。

---

## 四、个别模板的独立协议

源项目内部分模板自带独立 LICENSE（如 `zhangzara-*` 系列由 Zara Zhang 个人提供，遵循各自的 MIT 协议）。这些 LICENSE 文件已随 rsync 完整保留在对应模板目录下，包括但不限于：

```
design-skeletons/html-ppt-zhangzara-*/LICENSE  (约 30 个，Zara Zhang © 2026)
design-skeletons/guizang-ppt/LICENSE
design-skeletons/html-ppt/LICENSE
skills/hatch-pet/LICENSE.txt
... 等
```

---

## 五、第三方品牌商标声明

`design-systems/` 目录下包含对**第三方品牌**的视觉规范引用，包括但不限于：

```
Apple · Linear · Stripe · Notion · Vercel · Figma · Airbnb ·
Raycast · Arc · Airtable · Bento · Binance · BMW · Bugatti ·
... （共 149 个）
```

**重要声明**：

1. 这些品牌名称及其相关商标、Logo、设计语言**归各自所有者所有**
2. 本仓库收录的 `DESIGN.md` 仅作为**视觉风格参考**（"unofficial reference"），不构成与上述品牌的官方合作或授权关系
3. 使用本仓库生成的设计稿时，**不得以这些品牌名义**对外发布商业内容，也不得用于商业混淆
4. 详细的商标 disclaimer 见同目录 [`design-systems/BRAND-DISCLAIMER.md`](./design-systems/BRAND-DISCLAIMER.md)

---

## 六、责任声明

源项目按"AS IS"提供，无任何明示或默示担保。本仓库的二次使用亦遵循同样的责任分配——使用本仓库内容产生的任何法律 / 商业 / 技术后果由使用方自行承担。

---

**版本**：v1.0
**更新日期**：2026-05-18
**维护**：新增 / 修改源项目内容时请同步更新本文件「修改说明」章节
