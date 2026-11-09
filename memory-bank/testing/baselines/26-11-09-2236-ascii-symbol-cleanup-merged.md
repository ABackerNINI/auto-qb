# 5876 passed + 2 skipped —— 合流后全量: 非 ASCII 符号清偿并入远端 18 笔(kb 闸门增量治理)后复测

> 摘要: 合流后全量: 非 ASCII 符号清偿并入远端 18 笔(kb 闸门增量治理)后复测
> 基线时间: 2026-11-09 22:36

## 验收数字

`commands run test.full`(2026-11-09, 分支 develop, rebase 并入远端 18 笔后, 索引归位提交 `addf729d` 之后):

```text
TOTAL                                                26153     41   9102     53    99%
5876 passed, 2 skipped in 121.83s (0:02:01)
```

`commands run test.one -- tests/test_ascii_symbol_guard.py -n 0 --no-cov` → 13 passed, 0 失败, 副作用台账 0 条, 越界 0 条。

- 缺口净额 (M8 口径, miss + partial): 本片 41 + 53 = **94 单位**; 上基线 [26-11-09-2213](26-11-09-2213-b19-ascii-symbol-cleanup-complete.md) 为 42 + 54 = 96 ⇒ 净额 **-2**(改善, 不点名); 分母(语句 + 分支合并)35195 → 35255(语句 +40 / 分支 +20), 跨轮分母已变, 对比时注明。

## 本改动面

- 为何复测: 上一片 [26-11-09-2213](26-11-09-2213-b19-ascii-symbol-cleanup-complete.md) 的 5856 是在**合流前旧基**(`216387e2`)上测的, 而远端并行推进了 18 笔(kb 闸门 timekit/check_html 增量治理、提交引擎复跑清单扩面与 changed 分片修、终审两条 minor), 其中已含自己的基线(26-11-09-0742 记 5872)。合流后旧片数字反低于更早的远端片, 单看 `kb.baseline` 会读成「用例被删」, 故在合并树上重测并补本片, 让最新片与当前 tip 对齐。
- 合流处理(非代码改动): rebase 重放 18 笔时两处冲突 —— ①`commit.py` 复跑闸门注释段(远端把它扩成 `_rebase_merged_paths` / `_tracked_scan_paths` 扩面逻辑, 本分支只是把其中 U+2757 换成 `!`), 按「远端新逻辑 + 本批 ASCII 化」解, 远端重新引入的 U+2757 一并换回 `!`; ②5 个 `memory-bank/pitfalls/testing/_index*` 生成物, 按 AGENTS.md「取一侧 + 重跑生成器」口径, rebase 时取一侧让它通过, 合流后重跑 `kb.index` 归位并单独提交(`addf729d`)。
- 产品代码与测试集合零改动: 本片实测前, 本地树只多出上述索引生成物差异(+13/-12 行), 无手写内容; 非 ASCII 符号全仓复扫仍为 `{}` `[]`(0 单元 / 0 处), `FROZEN` 保持空字典, 守阵 13 条全绿。
