# 3777 passed + 2 skipped(根) —— WEBUI 顶层右键菜单左缘 clamp e2e 回归断言(issue 26-10-20-0148 清偿)

> 摘要: WEBUI 顶层右键菜单左缘 clamp e2e 回归断言(issue 26-10-20-0148 清偿)
> 基线时间: 2026-10-20 11:17

**Refs:** memory-bank/issues/26-10-20-0148-test-webui-ctx-menu-left-edge.html

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 实测输出:

```text
TOTAL                                                20610    373   6982    257    98%
3777 passed, 2 skipped in 106.36s (0:01:46)
```

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 98`)照过。
- 相对上一条基线的逐位对比不写 —— 差值现看 `commands run kb.baseline -n 2`。
- 浏览器侧 `commands run dev.e2e`(全量套件, 默认端口/默认矩阵): `326 passed, 10 skipped (9.7m)`,
  0 failed(10 skipped = off 模式精简组在默认 on 轮按 requireMode 整组跳过)。
- 目标 spec 单跑 `commands run dev.e2e -- menus.spec.mjs`: `30 passed, 6 skipped (58.3s)`。
- 新守阵 2 条(e2e/menus.spec.mjs「CTX-fit 横轴」两支, 双皮肤 ×2 = 4 个 test 实例):
  CTX-fit 右缘(真实右键, 锚点贴 .group-table 右缘内侧 2px, 断言菜单右缘 ≤ 视口宽-8+1)与
  CTX-fit 左缘(合成 contextmenu clientX=2 dispatch 真实行, 断言菜单左缘 ≥ 8-1);
  垂直 CTX-fit 用例内一条恒真的顺带右缘断言随本次移除。
- 红验(本轮, 两类突变各自判红且不误红): ①ui_feedback.js 左缘两级 `max(EDGE, …)` 全拆 →
  左缘支双皮肤 2 红(菜单左缘 2 < 8), 右缘支与垂直支绿; ②右缘两级钳位全拆 → 右缘支双皮肤
  2 红(菜单右缘 1622 > 1432), 左缘支与垂直支绿。突变均以精确反向编辑还原, `git diff`
  实证 ui_feedback.js 零改动 —— 本 issue 是纯测试缺口, 生产代码未动。

## 本改动面

| 文件 | 改动 |
|---|---|
| `e2e/menus.spec.mjs` | 新增「CTX-fit 右缘」「CTX-fit 左缘」两支(横轴 clamp 独立回归断言); 移除垂直 CTX-fit 用例内恒真的顺带右缘断言(锚点在行左缘 clientX≈14, 菜单 14..210 远离两缘); 文件头对账映射表补横轴两支条目 |
| `memory-bank/issues/26-10-20-0148-test-webui-ctx-menu-left-edge.html` | 状态 Open → In Progress → Done; §04 修复与验证(复验/实际修法/与建议的改道/红验); §05 状态变更日志追加两行; doc-refs 补坑档反向声明 |
| `memory-bank/pitfalls/web-ui/ctx-menu-edge-clamp.md` | 新坑档(锚点不贴缘的断言恒真 + 左缘 clamp 真实手势结构不可达两条); web-ui 类索引随之更新 |
| `memory-bank/activeContext/26-10-20-1111-webui-ctx-menu-left-edge.md` | 新会话切片(kb.wrap 建, R0) |

未触及: 生产代码(`ui_feedback.js` 红验后零改动, 见口径注记)、其它 e2e spec、
off/error/hang/3000 种子模式矩阵轮(横轴两支在默认 on 轮已双皮肤验证;
E2E_TORRENTS 分档不改变滚动容器左缘 12px 的几何事实)。
