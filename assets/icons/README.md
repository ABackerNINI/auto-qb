# auto-qb 图标设计稿(扁平风格 SVG)

> 设计草稿, 供挑选与迭代; 尚未接入程序(打包 .ico / 任务栏引用等后续由你确认方案后进行)。

## 字标变体系列(基于 qb monogram, 共 9 版)

几何基线已统一校准(字母居中、描边 40、碗半径 64), 齿轮齿 22.5° 相位错开以避让笔画衔接处。

| 文件 | 概念 | 说明 |
|------|------|------|
| `auto-qb-mono-01-classic.svg` | 经典版 | 原始 monogram 的居中修正版, 纯几何描边 q/b |
| `auto-qb-mono-02-gear-q.svg` | **齿轮 q(推荐)** | q 的圆碗化为 8 齿齿轮, 字尾保留; 齿轮=自动化, 辨识与语义平衡最好 |
| `auto-qb-mono-03-gear-b.svg` | 齿轮 b | 齿轮放在 b 的圆碗, q 保持圆环 |
| `auto-qb-mono-04-cycle-q.svg` | 循环 q | q 的圆碗断开为带箭头的循环弧, 与主方案的循环箭头呼应 |
| `auto-qb-mono-05-upload-b.svg` | 上传 b | b 的上升笔画顶端化作向上箭头(做种/上传) |
| `auto-qb-mono-06-orbit.svg` | 轨道 | qb 外围 330° 细轨道弧 + 绿色种子点, "自动运行中" |
| `auto-qb-mono-07-duo-gears.svg` | 双齿轮 | q(白)/b(绿)双齿轮联动, 自动化引擎感最强, 信息量最大 |
| `auto-qb-mono-08-bolt.svg` | 闪电 | b 的碗孔内嵌绿色闪电, 速度/能量 |
| `auto-qb-mono-09-light.svg` | 亮底反转 | 浅蓝灰底 + 深蓝字 + 绿色字尾, 适配浅色主题桌面 |

原始稿 `auto-qb-monogram.svg` 保留作对照(= 01 的未校准版本)。

## 候选方案(首轮概念稿)

| 文件 | 概念 | 说明 |
|------|------|------|
| `auto-qb-main.svg` | **循环箭头 + 种子(推荐)** | 270° 循环箭头 = "auto 自动管理"; 绿色水滴种子 = "做种"; 蓝底呼应 qBittorrent 生态。语义最完整, 小尺寸下形状仍清晰, 推荐作桌面/应用主图标 |
| `auto-qb-sprout.svg` | 做种发芽 | PT 语境"做种(seeding)"的直译双关, 双叶新芽 + 地面线。亲和度高, 适合社区传播场景 |
| `auto-qb-arrows.svg` | 上下行箭头 | 白=下载 / 绿=上传, 高低错落; 最直白的传输意象 |
| `auto-qb-gauge.svg` | 限速仪表盘 | 呼应全局限速曲线功能, 深蓝底 + 绿色指针 |

## 任务栏/托盘透明底(glyph)

- `auto-qb-glyph-white.svg` — 白色, 适配深色任务栏/托盘
- `auto-qb-glyph-dark.svg` — 深色(`#1F2937`), 适配浅色任务栏/托盘

取主方案(循环箭头 + 种子)去底单色化; 若最终主图标改选其它方案, glyph 可按同样方式提取。

## 配色

| 用途 | 色值 |
|------|------|
| 主蓝(qBittorrent 生态联想) | `#2E6FE0` |
| 深蓝(深色底) | `#16294A` |
| 绿(做种/上传/强调) | `#34C759` |
| 白 | `#FFFFFF` |
| Glyph 深色 | `#1F2937` |

## 导出为桌面/任务栏可用格式

SVG 仅为源稿, Windows 桌面快捷方式与任务栏需要 `.ico`(打包如 PyInstaller 用 `--icon`):

```bash
# ImageMagick(一次生成多尺寸 ICO)
magick auto-qb-main.svg -define icon:auto-resize=256,128,64,48,32,16 auto-qb.ico

# 或 Inkscape 先出 PNG 再合成
inkscape auto-qb-main.svg -w 256 -o main-256.png
magick main-256.png main-128.png main-64.png main-32.png main-16.png auto-qb.ico
```

建议导出尺寸: 256 / 128 / 64 / 48 / 32 / 16。所有源稿 viewBox 统一 `0 0 512 512`, 16px 下主方案的粗描边(44/512 ≈ 8.6%)仍可辨识。
