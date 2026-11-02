# 4823 —— flux 消息面图标统一(圈内字形族)后全量

> 摘要: flux 消息面图标统一(圈内字形族)后全量
> 基线时间: 2026-11-02 06:45
**Refs:** memory-bank/testing/baselines/26-11-02-0626-webui-flux-message-surface.md

## 验收数字

`commands run test.full` 实测(2026-11-02 06:45, 三轮: 形状定档 D9-1 + 图标圈内字形族):

```text
TOTAL                                                22521    152   7726    135    99%
4823 passed, 10 skipped in 217.90s (0:03:37)
```

- 口径注记: 10 skipped 为既有跳过面(平台条件跳过, 与本轮改动无关); 覆盖率 99%。
- 守阵 `tests/test_webui_static_skins.py` 26 passed: 第 20 项追加「每档必须有 `--msg-ico`」断言
  (漏一张 mask = background-color 把图标位铺成实心色块, 比没图标更糟), 用例数不变。
  红验一次: 摘掉 `.toast.busy` 的 `--msg-ico` 精确报「该档图标退成实心色块/无字形」, 还原后绿。
- 渲染面人工取证(桩服务 + Playwright, flux 不在 e2e `SKINS` 默认集合): 六档提示条并排截图均为
  圈内字形(圆环 + 圈内单形, 18px / stroke 2), 计算样式 `color: transparent` + `background-color`
  = 语义色 + `mask-image` 命中; 挑选台 D9 六张卡 18 个样例图标同族, 控制台零错误。

## 本改动面

- `flux/css/views.css`(484 行, 余量充足): 新增「消息面图标: 圈内字形族」段 —— `@supports
  (mask-image)` 内 ①`.toast .ico` 换漆(color: transparent 藏旧字形 + mask 画形状 +
  background-color 取 `--msg-tone`); ②mask 表六档(kind 一行, `.toast.info` 为基线档);
  ③`@supports` 外留兜底尺寸规则(18px / stroke 2, 不画圈但字形仍在 = 能力降级不丢信息)。
- `flux/css/components.css`: 零改动(700 行 cap 已满, 图标段落 views.css, 与既有「顶 cap 规则挪
  有余量文件」惯例一致)。
- `fx/showcase.html`: D9 区样例图标换成同族圈内字形(24 viewBox + 圆环 r9 + 圈内单形, 与生产
  mask 数据同源), 卡内 `.mst svg` 13px/1.7 → 18px/2; 区注补现状(形状暂定 D9-1 / 图标族已定),
  D9-1 卡名标注「暂定选定 = 生产现状」。
- `tests/test_webui_static_skins.py`: `_scan_message_surface_parity` 追加 `--msg-ico` 收集与
  每档断言(与 `--msg-tone` 同一张 kind 表), docstring 同步。
- `memory-bank/conventions/webui.md`: 新增「消息面图标: 圈内字形族」段(参考物 / 渲染层换漆的
  理由与降级口径 / 新增 kind 要登记三张表 / 形状暂定 D9-1)。
- 共享模板、sprite、另三皮肤零改动(图标源与四皮肤共享守阵面一律不碰)。
