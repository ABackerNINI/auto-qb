#!/usr/bin/env python
"""生成 HR 扩展工具栏图标的 8 个 PNG(dev-only, 生成物入库 extensions/hr-fetch-proxy/icons/)。

计划 26-10-16-0214 S6(R4 路径 A): 徽标(文字层)的字号/占地/位置由浏览器固定渲染, 没有 API 可调 ——
「徽标挡住图标」无解, 唯一路径是 chrome.action.setIcon 重画图标本体。运行时零绘制, 像素级可控,
故一次生成 4 态 x 2 尺寸(16/32px)共 8 个 PNG 入库, background.js::refreshBadge 按 badgeStateOf
换图(setIcon 之后回不去默认图标, 所以基础图必须自带, manifest default_icon 与未配置态共用)。

- 基础无框: 中性深色圆角底(不随浏览器主题变, C8) + 白色 H 字形;
- 绿/橙/红框(连接正常/重连中/发现失败): 基础图 + 徽标既定色框(#2e7d46/#b8802f/#b0453d, 与
  background.js BADGE 同源), 色框外加暗色描边保证与图形分离。

用法(依赖 pillow, 已是项目依赖):
    uv run python scripts/gen_ext_icons.py          # 生成 8 个 PNG(幂等覆盖, 无副作用)
"""
from __future__ import annotations

import pathlib
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - 生成脚本只在开发期手工跑
    print("gen_ext_icons: 需要 pillow(uv sync 后重试)", file=sys.stderr)
    raise SystemExit(2)

OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "extensions" / "hr-fetch-proxy" / "icons"

BASE_BG = (23, 30, 38, 255)  # 中性深色底(#171e26), 不随浏览器主题变
GLYPH = (232, 237, 240, 255)  # 白色 H 字形
DARK_EDGE = (11, 15, 20, 255)  # 色框外的暗色描边(#0b0f14)
FRAME_COLORS = {
    # 与 background.js BADGE 的色同源(改一处必改另一处, 守阵会查)
    "icon-ok": (46, 125, 70, 255),  # #2e7d46 连接正常
    "icon-warn": (184, 128, 47, 255),  # #b8802f 重连中
    "icon-bad": (176, 69, 61, 255),  # #b0453d 发现失败
}
SIZES = (16, 32)


def draw_base(img: Image.Image, size: int) -> None:
    """基础图: 圆角深色底 + H 字形(坐标以 16px 为基准, 按 size/16 倍率缩放)"""
    s = size // 16
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=3 * s, fill=BASE_BG)
    # H: 两竖(宽 2s)一横(高 2s), 16px 基准下占 8x8(留 4px 内边距)
    vx, vw, vy, vh = 4 * s, 2 * s, 4 * s, 8 * s
    hy = 7 * s
    d.rectangle([vx, vy, vx + vw - 1, vy + vh - 1], fill=GLYPH)
    d.rectangle([vx + 6 * s, vy, vx + 6 * s + vw - 1, vy + vh - 1], fill=GLYPH)
    d.rectangle([vx, hy, vx + 6 * s + vw - 1, hy + 2 * s - 1], fill=GLYPH)


def draw_frame(img: Image.Image, size: int, color: tuple) -> None:
    """色框(16px: 1px 暗边 + 2px 色环; 32px 同比例放大)"""
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, size - 1, size - 1], outline=DARK_EDGE)
    ring = 2 * (size // 16)
    d.rounded_rectangle([1, 1, size - 2, size - 2], radius=max(2, 3 * (size // 16) - 1), outline=color, width=ring)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for size in SIZES:
        base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw_base(base, size)
        base_path = OUT_DIR / f"icon{size}.png"
        base.save(base_path)
        written.append(base_path.name)
        for stem, color in FRAME_COLORS.items():
            framed = base.copy()
            draw_frame(framed, size, color)
            framed.save(OUT_DIR / f"{stem}{size}.png")
            written.append(f"{stem}{size}.png")
    for name in written:
        print(f"[gen_ext_icons] {OUT_DIR / name}")
    print(f"[gen_ext_icons] 共 {len(written)} 个 PNG(基础无框 + 绿/橙/红框 x {SIZES})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
