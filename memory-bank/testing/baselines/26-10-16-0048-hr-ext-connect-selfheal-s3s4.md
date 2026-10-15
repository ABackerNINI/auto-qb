# 3398 —— HR 扩展「连接自愈」S3/S4(选项页交互收口 + 布局合并)

> 摘要: 计划 `26-10-15-2357` 的 S3/S4 落地 —— 选项页从「发现区 + 手动区 + 底部工具栏」合并为**一个「① 连接后端」区**: 顶部「连接状态」总览(态 + 实例数 + 上次发现时间/命中端口 + 最近结果) + 「立即发现」**隐式保存**(归一化 → 授权 → 落盘 → 探测, 一次点击闭环) + 命中后**自动接一次自测**合成结论 + 失败码中文映射与逐候选结果(`未知` 字面量清零) + 实例列表「优先/自动」徽标与手动条目「疑似失效」标记(只提示不代删) + `storage.onChanged` 监听 `instances/instanceHealth/lastDiscovery` 实时刷新; 删「保存发现地址与配对码」按钮与独立 `saveDiscovery`。改动 2 个扩展源文件(`options.js`/`options.html`)+ 1 个测试文件(既有瑞士网格接线用例随口径更新, 零新增用例)。
> 档案: memory-bank/tasks/26-10-16-webui-hr-ext-connect-selfheal.md
> 基线时间: 2026-10-16 00:48

**Refs:** memory-bank/tasks/26-10-16-webui-hr-ext-connect-selfheal.md, memory-bank/plans/26-10-15-2357-plan-hr-ext-connect-selfheal.html

## TOTAL

```
TOTAL                                               17337    182   5846    158    99%
3398 passed, 4 skipped in 131.32s (0:02:11)
```

- 语句 17337 / 未覆盖 182; 分支 5846 / partial 158; 覆盖率 **99%**(`commands run test.full` 实测, Windows 侧)。
- 与上一基线 `26-10-16-0008`(3388 passed + 4 skipped)差 **+10 passed, 已对账**: S1/S2 轮新增 6 条扩展守阵(`d4d764d1`)+ 同期另一会话 doc-status 词表轮新增 4 条(`27d6a53a`), 两条都在本会话开工同步前已在树上 —— 本轮**零新增用例**(S6 的七条新守阵未做), 只更新既有用例的期望值。
- 语句/分支总数与上一基线**逐位相同** —— 本轮改动全在扩展侧 JS/HTML, Python 一行未动。
- Linux(WSL) 侧未重测 —— 本轮无平台相关改动。
