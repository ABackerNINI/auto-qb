# guizang-ppt — 来源与同步说明

本目录是 `delivery-artifact` skill「PPT 风」形态的 reference,内容来自上游开源 skill。

## 上游

- 仓库:https://github.com/op7418/guizang-ppt-skill
- 作者:歸藏(op7418)
- 许可:MIT(见同目录 `LICENSE`,版权与许可声明随包保留)
- 同步 commit:`6bfa520b86ed5a3dffdac0a3323155e2b6f516b6`(2026-05-19)
- 拉取日期:2026-05-22

## 相对上游的改动

只做了两类**最小必要改动**,未改写任何工作流逻辑或视觉规范:

1. **去 frontmatter + 改名**:上游 `SKILL.md` 改名为 `guizang-ppt.md` 并移除 YAML frontmatter
   —— 它在这里是 reference,不是独立 skill,改名/去 frontmatter 避免被 skill 扫描器二次注册。
2. **移除截图美化子功能**:删去 `assets/screenshot-backgrounds/`(9 张 WebP,约 2MB)
   与 `references/screenshot-framing.md` —— 该子功能服务于「给做好的 deck 拍营销截图」,
   与「生成 deck」无关。`guizang-ppt.md`、`checklist.md`、`components.md`、`image-prompts.md`、
   `swiss-layout-lock.md`、`layouts-swiss.md` 中对它的引用一并改写为「按标准比例保真落位」。

未纳入的上游文件:`README.md`、`README.en.md`、`CONTRIBUTING.md`、`.github/`、`.gitignore`
(仓库元文件,与 deck 生成无关)。

## 如何重新同步上游

```bash
git clone --depth 1 https://github.com/op7418/guizang-ppt-skill.git /tmp/guizang-src
# 覆盖 deck 生成相关文件(保持本目录结构):
#   /tmp/guizang-src/SKILL.md            → guizang-ppt.md(去 frontmatter)
#   /tmp/guizang-src/LICENSE             → LICENSE
#   /tmp/guizang-src/assets/{template.html,template-swiss.html,motion.min.js} → assets/
#   /tmp/guizang-src/references/*.md(除 screenshot-framing.md)               → references/
#   /tmp/guizang-src/scripts/validate-swiss-deck.mjs                          → scripts/
# 再按上面「改动」两条复核截图引用,更新本文件的 commit / 日期。
```
