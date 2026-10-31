# 2871 —— dt12 空间树图单点遮蔽修复 + 新守阵基线

> 摘要: 用户报「WEBUI 种子详情内容页空间树图异常: 选择后无显示, 切换种子后回到经典」。根因 = `12-content-space-treemap-collapsed.js` layoutMap 局部 `H`(clientHeight)遮蔽文件头 helpers 单点, `H.rowFocusKey(...)` 对数字取属性抛 TypeError → 树图空白 + `_dtRender` catch 复位 classic 并落盘。修复 = 局部改名 mapW/mapH(squarify 局部 H 同坑类一并改 RH); 新增守阵 `test_drawer_tpl_variant_no_singleton_shadowing`(T/R/H 单点遮蔽禁令, 含多声明符与解构两形态); 坑档 `pitfalls/web-ui/variant-singleton-shadow.md` 入池。
> 基线时间: 2026-10-09 19:55

**Refs:** memory-bank/activeContext/26-10-09-1945-webui-dt12-treemap-singleton-shadow.md,memory-bank/pitfalls/web-ui/variant-singleton-shadow.md

## test.full 实测

- 分支: `develop`(HEAD `19175361`, 会话开工快进所得; 工作树含本轮修复 + 回写件时实测)
- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 testing/baseline.md「必须带区间」)
- **实测 (Windows)**: **2871 passed + 4 skipped, 0 failed, 覆盖率 TOTAL 99%**
  (16567 语句 / 167 未覆盖 / 5716 分支 / 143 partial; 门槛 98% 达标; 26.8s)
- 与上基线的差值: `commands run kb.baseline -n 2` 现列(切片正文只写自己的 TOTAL, 不抄逐位对比)。
- 增量明细(本轮真正新增): `tests/` +1 守阵(上基线 2870 → 本基线 2871); `src/` 改动仅 dt12 变体局部改名(零语义面变化, 收集面不变); 知识库回写件 3 份(activeContext 切片 / pitfalls 坑档 / 本切片)+ `_index.md` 重建。
- 备注: 本会话首次后台 test.full 曾报 2 个 kb-index 失败 —— 系与并发 `kb.index` 重建撞时序的测量污染(索引当时未含新坑档), 非代码缺陷; 索引落定后 `test_memory_bank.py` 43 passed 复核绿, 本切片为索引稳定后的干净复跑。

## 对照判据(后续沿用)

- 以本切片(2871+4 / 16567 / 167 / 5716 / 143)为对照点: 预期 passed 只升不降、未覆盖 / partial 不升。
- 变体「渲染成功路径逐函数 node 真跑」电池仍是缺口(见坑档条目尾), 补齐时预期 passed 再 +1 量级并另立基线。
