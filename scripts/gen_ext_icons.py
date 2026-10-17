#!/usr/bin/env python
"""生成 HR 扩展工具栏图标的 8 个 PNG(dev-only, 生成物入库 extensions/hr-fetch-proxy/icons/)。

计划 26-10-16-0214 S6(R4 路径 A): 徽标(文字层)的字号/占地/位置由浏览器固定渲染, 没有 API 可调 ——
「徽标挡住图标」无解, 唯一路径是 chrome.action.setIcon 重画图标本体。运行时零绘制, 像素级可控,
故一次生成 4 态 x 2 尺寸(16/32px)共 8 个 PNG 入库, background.js::refreshBadge 按 badgeStateOf
换图(setIcon 之后回不去默认图标, 所以基础图必须自带, manifest default_icon 与未配置态共用)。

- 基础无框: 中性深色 squircle 底(不随浏览器主题变, C8) + 白色中继字形;
- 绿/橙/红框(连接正常/重连中/发现失败): 基础图 + 徽标既定色框(#2e7d46/#b8802f/#b0453d, 与
  background.js BADGE 同源), 色框外加暗色描边保证与图形分离。

字形为「中继双向箭头」(任务 26-10-16-webui-hr-ext-icons 四版候选的 A 版, 用户拍板选定):
箭杆水平居中 + 两端三角尖朝外, 表达代理/通道语义; 纯几何不依赖字母, 16px 下笔画最稳。
底形圆角 3->4(更接近 squircle), 与候选样张 `plans/26-10-16-0453-plan-hr-ext-icons.html` 一致。
斜线与三角必须超采样后再降采样 —— 直接按目标像素画会出锯齿(16px 尤其明显), 故统一 8x 渲染。

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
GLYPH = (232, 237, 240, 255)  # 白色字形(#e8edf0)
DARK_EDGE = (11, 15, 20, 255)  # 色框外的暗色描边(#0b0f14)
FRAME_COLORS = {
    # 与 background.js BADGE 的色同源(改一处必改另一处, 守阵会查)
    "icon-ok": (46, 125, 70, 255),  # #2e7d46 连接正常
    "icon-warn": (184, 128, 47, 255),  # #b8802f 重连中
    "icon-bad": (176, 69, 61, 255),  # #b0453d 发现失败
}
SIZES = (16, 32)
SS = 8  # 超采样倍数(斜线/三角抗锯齿)
CORNER_R = 4  # 16px 基准圆角(3 -> 4, 更接近 squircle)


def _px(v: float, s: int) -> float:
    """16px 基准单位 -> 超采样像素"""
    return v * s * SS


def draw_base(img: Image.Image, size: int) -> None:
    """基础图: squircle 深色底 + 中继双向箭头(坐标以 16px 为基准, 按 size/16 倍率缩放)"""
    s = size // 16
    w = size * SS
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, w - 1], radius=_px(CORNER_R, s), fill=BASE_BG)
    # 箭杆: x 6.5..9.5, y=8, 粗 2(两三角基座之间, 不重叠避免加粗)
    d.line([_px(6.5, s), _px(8, s), _px(9.5, s), _px(8, s)], fill=GLYPH, width=int(2 * s * SS))
    # 左箭头: 尖 (4,8), 基座 x=6.5, y 5.8..10.2(高 4.4)
    d.polygon([(_px(4, s), _px(8, s)), (_px(6.5, s), _px(5.8, s)), (_px(6.5, s), _px(10.2, s))], fill=GLYPH)
    # 右箭头: 尖 (12,8), 基座 x=9.5
    d.polygon([(_px(12, s), _px(8, s)), (_px(9.5, s), _px(5.8, s)), (_px(9.5, s), _px(10.2, s))], fill=GLYPH)


def draw_frame(img: Image.Image, size: int, color: tuple) -> None:
    """色框(16px: 1px 暗边 + 2px 色环; 32px 同比例放大), 画在超采样画布上"""
    s = size // 16
    w = size * SS
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, w - 1], outline=DARK_EDGE, width=int(1 * s * SS))
    d.rounded_rectangle(
        [_px(1, s), _px(1, s), _px(15, s) - 1, _px(15, s) - 1],
        radius=_px(CORNER_R - 1, s),
        outline=color,
        width=int(2 * s * SS),
    )


def render(size: int, frame_color: tuple | None = None) -> Image.Image:
    """一次渲染到底: 超采样画布 -> 底 + 字形 + (可选)色框 -> LANCZOS 降采样到目标尺寸"""
    canvas = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
    draw_base(canvas, size)
    if frame_color is not None:
        draw_frame(canvas, size, frame_color)
    return canvas.resize((size, size), Image.LANCZOS)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for size in SIZES:
        base_path = OUT_DIR / f"icon{size}.png"
        render(size).save(base_path)
        written.append(base_path.name)
        for stem, color in FRAME_COLORS.items():
            render(size, color).save(OUT_DIR / f"{stem}{size}.png")
            written.append(f"{stem}{size}.png")
    for name in written:
        print(f"[gen_ext_icons] {OUT_DIR / name}")
    print(f"[gen_ext_icons] 共 {len(written)} 个 PNG(基础无框 + 绿/橙/红框 x {SIZES})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
