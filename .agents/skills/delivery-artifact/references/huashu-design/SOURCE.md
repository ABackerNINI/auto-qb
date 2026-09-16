# huashu-design — 来源与同步说明

本目录是 `delivery-artifact` skill「Stage 形态」分支（iOS / Android 原型、motion design HTML、infographic、kiosk 全屏舞台）的 reference，**仅覆盖到 HTML 产物层面**。

## 上游

- 仓库：https://github.com/alchaincyf/huashu-design
- 作者：花叔（@AlchainHust）
- 许可：MIT（见同目录 `LICENSE`，版权与许可声明随包保留）
- 同步 commit：`9100be3d4638d6b7d47f0982ba3c1ae30cfdcd5a`（2026-05-25，HEAD）
- 拉取日期：2026-05-25

## 相对上游的改动

### 1. 去 frontmatter + 改名

上游 `SKILL.md` 改名为 `huashu-design.md` 并移除 YAML frontmatter —— 它在这里是 reference，不是独立 skill，改名/去 frontmatter 避免被 skill 扫描器二次注册（跟 `references/pdf-creator/`、`references/guizang-ppt/` 同治理）。

### 2. Scope-cut：删除「HTML → MP4 + 配音 + BGM」整个下游子功能

**理由**：`delivery-artifact` 的承诺始终是 **HTML 交付物**（见其 SKILL.md description）。huashu 上游附带的 narrated video pipeline（配音 / TTS / BGM 混音 / 视频导出 / launch-film 工作流）产物是 MP4，**不在 delivery-artifact 的产物边界内**。这条子功能跟「截图美化」之于 `guizang-ppt` 同性质 —— 属于另一项工作，不属本 skill。

砍掉这条子功能可省 27M+（主要来自 6 首 BGM mp3），同时去除 huashu SOP 中跟 delivery-artifact 路径无关的步骤（避免 LLM 顺着原 SOP 走到 MP4 输出路径）。

**删除清单**：

| 类别 | 文件 | 上游大小 |
|---|---|---|
| BGM | `assets/bgm-{ad,educational,educational-alt,tech,tutorial,tutorial-alt}.mp3` | 27M |
| SFX | `assets/sfx/` | 564K |
| Narration stage | `assets/narration_stage.jsx` | 18K |
| Launch-film 样本 | `assets/director-notes-samples/launch-film-30s-sample.md` | 80K |
| TTS / 配音脚本 | `scripts/{tts-doubao.mjs,narrate-pipeline.mjs,render-narration.sh,mix-voiceover.sh,add-music.sh}` | 32K |
| 视频导出脚本 | `scripts/{render-video.js,convert-formats.sh}` | 15K |
| 配音 / 视频 references | `references/{voiceover-pipeline.md,sfx-library.md,audio-design-rules.md,video-export.md,launch-film-director-notes.md}` | 60K |
| 配音 demos | `demos/voiceover-demo/`、`demos/md-html-narration/` | 60K |

**配套补丁**：

- `huashu-design.md` 文件顶部新增 **scope-cut 通告**，明确告知 LLM "下文 SOP 涉及配音 / BGM / 视频导出 / launch-film 的步骤一律跳过"。覆盖了原 SOP 中约 21 处对已删文件 / 子功能的引用 —— 通过通告统一打住，不一一改 SOP（保持上游同步代价低）。
- `references/hero-animation-case-study.md`、`references/multi-perspective-parallel-case-study.md` —— 末尾「相关文档」一节里指向已删文件的 4 条链接,改成 ~~strikethrough~~ + scope-cut 注释（不删整文，案例本身的 motion design 智慧仍然有效）。

### 3. 删除真孤儿（跨 SOP / cross-ref 零引用）

| 删除项 | 原因 |
|---|---|
| `demos/*-en.html`（9 份英文镜像） | 上游为英文读者准备的并行翻译，SOP 零引用 |
| `test-prompts.json` | 上游自家测试件，SOP / 任何 .md 都不引 |
| `references/cinematic-patterns.md` | 跨所有 .md 零引用，孤儿 |

### 未纳入的上游文件

`README.md`、`README.zh.md`、`.git*`（仓库元文件）。

## 最终目录大小

约 **4M**（上游 62M → 排除 BGM 后 35M → scope-cut 后 4M）。其中:
- `assets/` 3.3M(主要是 `showcases/` 24 份风格样例,服务 huashu 的「设计方向 fallback advisor」流程)
- `demos/` 284K(11 份中文 demo)
- `references/` 240K(18 份核心 .md)
- `scripts/` 72K(剩余 5 个非视频/非配音脚本)
- `huashu-design.md` 60K

## 路由方式

`delivery-artifact/SKILL.md` 的「第一步：选介质 / 形态例外」检测到用户要 Stage 形态时，
直接路由到本目录的 `huashu-design.md`，按它自己的工作流走（**跳过通告里列的子功能步骤**）。

进入 huashu 分支后不再走 delivery-artifact 第二步（Stage 跟 Native / 杂志 / 交互 / PPT 不是同类形态）。

## 重新同步

```bash
SRC=/tmp/huashu-src
DST=resources/skills-domestic/delivery-artifact/references/huashu-design

git clone --depth 1 https://github.com/alchaincyf/huashu-design $SRC

# 全量覆盖（排除 README + 真孤儿 + 整个 narrated-video subfeature）：
rsync -a --delete \
  --exclude='README.md' --exclude='README.zh.md' --exclude='.git*' \
  --exclude='test-prompts.json' \
  --exclude='demos/*-en.html' \
  --exclude='references/cinematic-patterns.md' \
  --exclude='assets/bgm-*.mp3' \
  --exclude='assets/sfx' \
  --exclude='assets/narration_stage.jsx' \
  --exclude='assets/director-notes-samples' \
  --exclude='scripts/tts-doubao.mjs' --exclude='scripts/narrate-pipeline.mjs' \
  --exclude='scripts/render-narration.sh' --exclude='scripts/mix-voiceover.sh' \
  --exclude='scripts/add-music.sh' --exclude='scripts/render-video.js' \
  --exclude='scripts/convert-formats.sh' \
  --exclude='references/voiceover-pipeline.md' --exclude='references/sfx-library.md' \
  --exclude='references/audio-design-rules.md' --exclude='references/video-export.md' \
  --exclude='references/launch-film-director-notes.md' \
  --exclude='demos/voiceover-demo' --exclude='demos/md-html-narration' \
  $SRC/ $DST/

# 重新去 frontmatter + 改名 + 重新加 scope-cut 通告（从本文件 commit 历史里捞 patch）：
sed -i '' '1,4d' $DST/SKILL.md && mv $DST/SKILL.md $DST/huashu-design.md
# 手工重新加 scope-cut 通告 + case-study patches（见本目录 git log）

# 同步前重新跑孤儿审计（上游可能新增了某些资源 / 删了某些引用）：
for f in $DST/references/*.md $DST/assets/*.{mp3,jsx,svg,html,js} $DST/demos/*.html; do
  bn=$(basename "$f")
  cnt=$(grep -rc "$bn" $DST/huashu-design.md $DST/references/ 2>/dev/null | awk -F: '{s+=$2}END{print s}')
  [ "$cnt" -eq 0 ] && echo "ORPHAN: $f"
done

# 人工 review 改动 + 更新本文件的 commit / 同步日期 / 大小
```

## 治理原则

**Vendor 时按目标 skill 的承诺边界做 scope-cut** —— 不是无脑全量。如果上游某个子功能产出的东西超出本 skill 的产物边界（比如本 skill 只产 HTML，上游子功能产 MP4），就整体砍掉那个子功能的 assets / scripts / refs / demos，并在主 SOP 顶部加 scope-cut 通告统一镇压悬挂引用。

**真孤儿才裁剪**（跨 SOP + 所有 cross-ref 零引用）才能放心删；**功能裁剪要明示**（不是悄悄删一两个文件，是连同子功能整条管线一起砍并打通告）。
