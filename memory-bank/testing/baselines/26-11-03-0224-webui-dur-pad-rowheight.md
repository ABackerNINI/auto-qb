# 4906 passed + 10 skipped —— 修做种时间格 6px padding 撑高整行(四皮肤)后全量基线

> 摘要: 修做种时间格 6px padding 撑高整行(四皮肤)后全量基线
> 基线时间: 2026-11-03 02:24
**Refs:** memory-bank/testing/real-machine.md

## 验收数字

`commands run test.full`(2026-11-03 02:24, develop 61b04b85→0c60bcf0 同步后)实测:

```text
TOTAL                                                22531    152    7732    134    99%
4906 passed, 10 skipped, 3 warnings in 349.90s (0:05:49)
```

口径: 根目录全量(Windows 并行 + 覆盖率), TOTAL 表与汇总行逐字誊写。10 skipped 全是环境能力型用例(6 条 `test_alias_fs.py` 建不出符号链接、3 条目录符号链接/POSIX-only 断言、1 条 ext4 大小写语义), 已用 `-rs` 逐条复核; 与本轮 CSS 改动无关。与上基线的逐位差值看 `commands run kb.baseline -n 2`, 本文不手抄对比。

## 本改动面

- `src/auto_qb/webui/static/{prism,atlas,console,flux}/css/views.css`: `.m-pair.m-dur` 去掉 `padding-bottom: var(--dur-pad)`, `--dur-pad` 只保留作 HR 线下移偏移(两条 `.hr-line` 的 `bottom: calc(-1 * var(--dur-pad))` 不变) —— 有文案的做种时间格不再高 6px, 整行高度恒定(皮肤间 ±1px)
- `tests/test_webui_static_skins_widget.py`: 新增守阵 —— `.m-pair.m-dur` 规则体不得出现 `padding`, 且两条 `.hr-line` 必须按 `var(--dur-pad)` 下移(防 padding 回归 / 线压文字)
- `e2e/views.spec.mjs`: 新增「几何守卫(做种时长单元格行高恒定)」—— 同一条种子行补文案 / 清空各量一次 `getBoundingClientRect().height`, 差值 ≤0.5px 且 `paddingBottom === '0px'`
- 真机复验(环境2 56590, 伪造种子暂停): 四皮肤 × 种子页平铺行 + 辅种页明细成员行, 有/无文案行高差均为 0, HR 线完整可见且不被下一行裁切
