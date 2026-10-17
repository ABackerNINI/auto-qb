# 3526 —— HR 扩展工具栏图标换中继双向箭头(A 版选定并入库)

> 摘要: 任务 `26-10-16-webui-hr-ext-icons` 收口 —— 用户在四版候选样张中拍板 A(中继双向箭头)。`scripts/gen_ext_icons.py` 字形层整体重写: 白色「H」-> 中继双向箭头(箭杆 x 6.5–9.5 居中 + 两端三角尖朝外至 x=4/12), 底形圆角 3 -> 4(squircle, 与候选样张一致), 新增 8x 超采样 + LANCZOS 降采样(原脚本按目标像素直绘矩形, 斜线/三角必须抗锯齿), 色框绘制同步改到超采样画布。重生成 8 个 PNG 覆盖 `extensions/hr-fetch-proxy/icons/`(基础无框 + 绿/橙/红框 × 16/32px), 与用户拍板样张 `plans/26-10-16-0453-plan-hr-ext-icons.html` 内嵌的 A 版**逐像素一致**(8/8 IDENTICAL, PIL `ImageChops.difference` 全空)。状态框体系、BADGE 三色(#2e7d46/#b8802f/#b0453d)、`background.js::badgeIconOf` 换图路径、manifest `action.default_icon` 全部不动 —— 只换字形本体与底形圆角。
> 档案: memory-bank/tasks/26-10-16-webui-hr-ext-icons.md
> 基线时间: 2026-10-17 13:33

**Refs:** memory-bank/tasks/26-10-16-webui-hr-ext-icons.md

## TOTAL

```
TOTAL                                               18169    260   6096    189    98%
3526 passed, 4 skipped in 125.77s (0:02:05)
```

- 语句 18169 / 未覆盖 260; 分支 6096 / partial 189; 覆盖率 **98%**(`commands run test.full` 实测, Windows 侧)。
- 改动面只有 PNG 二进制 + dev-only 生成脚本(`scripts/gen_ext_icons.py`, 不在 `testpaths` 内), **无 Python 可测代码变化**, 故本片数字是当轮全量快照, 不代表本任务引入的增量; 与上一基线的逐位差值请直接 `commands run kb.baseline -n 2` 两条各读一眼。
- 相关守阵(既有, 未改): `tests/test_extension_proxy.py` 只校验「8 个 PNG 在盘 + manifest `action.default_icon` 指向基础图 + `badgeIconOf` 四态映射」, **无像素断言** —— 换字形不会误红, 也不会替你守住视觉回归(目检仍是唯一手段, 见档案「目检」段)。
- Linux(WSL) 侧未重测 —— 纯 PNG + dev 脚本改动, 无平台分支。

## 本改动面

- `scripts/gen_ext_icons.py` —— 字形 H -> 中继双向箭头; 圆角 3 -> 4; 新增 `SS = 8` 超采样与 `render()` 统一出图(底 + 字形 + 可选色框 -> LANCZOS); 色框改在超采样画布绘制; docstring 记选定来源与超采样理由
- `extensions/hr-fetch-proxy/icons/*.png`(8 个, 覆盖) —— icon16/32 基础 + icon-ok/-warn/-bad × 16/32, 与拍板样张逐像素一致
- 未改: `extensions/hr-fetch-proxy/background.js` / `manifest.json` / `README.md`(README 只描述色框语义, 不含字形描述, 无需同步)

## 目检

- 16px / 32px 四态放大对照条(PIL 6x NEAREST 拼接)逐个看过: 箭头两尖对称、箭杆与三角基座不重叠、色框环宽 2px 与暗描边分离清晰, 无锯齿。
- 与样张一致性用 `ImageChops.difference` 机检: 8 个文件 `bbox is None`(全等)。
