# 4908 passed + 10 skipped —— e2e 行高几何守阵扩到四皮肤(SKINS_ALL)后全量基线

> 摘要: e2e 行高几何守阵扩到四皮肤(SKINS_ALL)后全量基线
> 基线时间: 2026-11-03 02:52
**Refs:** memory-bank/pitfalls/web-ui/dur-cell-padding-rowheight.md

## 验收数字

`commands run test.full`(2026-11-03 02:52, develop HEAD 936fd97d + 本轮未提交改动)实测:

```text
TOTAL                                                22531    152   7732    134    99%
4908 passed, 10 skipped, 3 warnings in 297.58s (0:04:57)
```

口径: 根目录全量(Windows 并行 + 覆盖率), TOTAL 表与汇总行逐字誊写。10 skipped 与上一基线同源(环境能力型: 符号链接 / POSIX-only / ext4 大小写语义), 与本轮 e2e 皮肤覆盖改动无关。

- 口径见 [baseline.md](../baseline.md)。

## 本改动面

- `e2e/harness.mjs`: 新增 `SKINS_ALL = ['prism','atlas','console','flux']`; 原 `SKINS`(prism/atlas)保持为冒烟运行时预算口径, 其余 spec 的测试量不翻倍。皮肤硬编码在 harness 单点, 不是夹具/参数问题(桩服务静态挂载通用, 四皮肤页面均可访问)
- `e2e/views.spec.mjs`: 「几何守卫(做种时长单元格行高恒定)」由 `SKINS` 改遍历 `SKINS_ALL` —— 四条用例共用同一份断言体(数据驱动, 未复制用例), 断言体沿用上轮(有/无文案行高差 ≤0.5px、`paddingBottom === '0px'`)
- 无新增夹具: 现有 300 合成种子(i=0 做种时间为空、其余有文案)即可覆盖四皮肤; Playwright 仍是可选依赖(`dev.e2e` 不在 `test.full` 内, 缺 node_modules 时命令自检失败而非 pytest 红)
- `memory-bank/testing/smoke.md` / `browser-env.md`: 同步 harness 用法约定 —— 双皮肤 = 冒烟预算口径, 跨皮肤只读测量走 `SKINS_ALL`
- 真机复验(环境2 56590 + 同组两枚伪造种子, 临时应用 8177): 四皮肤 × 种子页平铺行 + 辅种页明细成员行, 有/无文案行高差均为 0、`paddingBottom` 0px、HR 线可见且线底距行底未越界(平铺行 5px / 成员行 2px, 不被下一行裁切)
