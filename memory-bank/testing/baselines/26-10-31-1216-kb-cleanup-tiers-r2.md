# 4300 passed, 10 skipped in 64.07s, 覆盖 99%(21548 stmts / 163 miss; branches 7400, 126 partial) —— kb 分级清理 R2 铺开轮全量基线(git/ops/docs/kb/backend/testing/web-ui 六批收官)

> 摘要: kb 分级清理 R2 铺开轮全量基线(git/ops/docs/kb/backend/testing/web-ui 六批收官)
> 基线时间: 2026-10-31 12:16
**Refs:** memory-bank/plans/26-10-31-0534-plan-kb-cleanup-tiers.html

## 验收数字

`commands run test.full`(pytest `-n 4 --cov=src --cov-branch --cov-fail-under=99`(pytest.ini addopts); 2026-10-31 实测, 全量 64.07s, 建档 12:16):

```
  TOTAL                                                21548    163   7400    126    99%
  4300 passed, 10 skipped in 64.07s (0:01:04)
```

- 汇总行: **4300 passed + 10 skipped(Windows)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记: 与上基线(R1, 4300 passed + 10 skipped / 78.81s)持平 —— R2 铺开轮六批全是
  文档处置轮, 零代码/零测试改动(无新增用例), 用例总数不变; skipped 10 条 = tests-real
  真机轨(测试实例未起, `tests-real/conftest.py` 按 port 探活跳过) + 少量平台态 skip,
  与上基线同环境态, 非代码差异。
- 配套验证: doc.links 绿 / doc.caps 债务 6 项(smoke 14,138 / frontend-split 13,859 /
  frozen-column 14,700 / implemented-core 21,058 / tasks/26-10-20-frontend-dup-code-audit
  127,962 / tasks/_index 28,868; redverify-anchor-lineendings 11,989 已由 testing 批清偿
  出清单, 债务 7 → 6) / kb.check 绿(回写/锚/新增面/日期四道守卫) / kb.index 重建 21 生成物 /
  kb.tier list 全库核对: L0×230 · L1×17 · L2×3 · L3×0 · 未打标 0(250 主题文件全打标;
  _about 件为生成物描述按设计豁免)。

## 本改动面

- R2 铺开轮六批收官(计划 plans/26-10-31-0534 §04 R2), 累计**零删除文件**、L3 全库 0、
  未打标 0。六批分布: R1 git 15(L0×9/L1×4/L2×2) + ops 9(L0×7/L1×2); R2 docs+kb 25(L0×22/L1×3)
  · backend 42(L0×42) · testing 77(L0×69/L1×8) · web-ui 82(L0×81/L2×1 = drawer-switch-flicker
  外迁 attachments)。全库 pitfalls 主题层 250 件 725,519 → 697,154 字符(-28,365, -3.9%;
  含 250 行等级行)。cap 债: 计划 §2.6 登记的 pitfall 债中 redverify 已清偿(7 → 6), 其余
  smoke/frontend-split/frozen-column 判据密集、无 >5 行独立叙事段可压, 留 R3。
- 本批(R2 第五批后半, hr-tooltip-overlap → wording-audit-surface 共 42 件): **全部 L0** ——
  逐件深读/粗读均为「触发/判别/处置/守阵」判据密集形态, 无 >5 行独立叙事段(校准: 判据密集
  件不进 L1); 摘要现行判据均无文件外单点(不凑 L2); 无守阵齐全+观察期件(不进 L3)。
  本批 121,094 → 121,313 字符(+219 = 42 条等级行, 摘要收拢与数字修正相抵后净)。
- 摘要折行收拢 2 件(等级行落点在头部区第 4 行, 折行摘要会把等级行腰斩进摘要块):
  injected-dom-title-migrated-to-aq-tip(6 行续行)、tpl-comment-split-orphan(2 行续行),
  判据句逐字保留只并为一行。
- 枚举数字实测修正 1 处: webui-css-block-move「index.html ≤214 行」→「≤218 行」(守阵
  test_frontend_template_split_wiring 现行 enforcement 实测 218)。同批核对无漂移: modal
  档位表 460/520/560/860/920 与 prism tokens.css 实测一致; 700 行单 CSS cap 与
  atlas/css/components.css=700 一致。
- 行尾: perf-cadence(113)/svg-chart-mapping(19)/js-comment-terminator(11) 存量 CRLF→LF
  归一; 全批 42 件 b.count(CRLF)=0 字节级断言通过, 提交 diff 无行尾噪音。
- Refs 双向链: 本切片与计划文档由 new_doc 补链函数双向声明(与 kb.new --refs 同一实现)。
