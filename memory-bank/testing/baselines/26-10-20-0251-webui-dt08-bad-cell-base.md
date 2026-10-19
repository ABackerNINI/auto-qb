# 3764 passed + 10 skipped —— 08 用户分组 bad 行首格承光底修正(--bg-card -> --bg-row)

> 摘要: 08 用户分组 bad 行首格承光底修正(--bg-card -> --bg-row)
> 基线时间: 2026-10-20 02:51

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 实测输出:

```text
TOTAL                                                20362    390   6982    262    98%
3764 passed, 10 skipped in 212.35s (0:03:32)
```

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 98`)照过。
- 相对上一条基线的逐位对比不写 —— 差值现看 `commands run kb.baseline -n 2`。
- 浏览器侧 `commands run dev.e2e`(全量套件, 端口 8401 —— 8137/8337 被残留桩占用, 见坑档
  testing/smoke.md 的换端口纪律): `320 passed, 10 skipped (11.7m)`, 0 failed。
- 红绿双验(本轮): ①e2e `STATE_CASES['08']`(新增测位)修前两条均红 —— 首格
  rgb(245,232,231) vs 行板 rgb(240,228,229)(atlas 同形); 修后两条均绿;
  ②静态守阵 08 条改口径后反向验证(把基色敲回 `--bg-card`) ⇒ 报「缺成分 var(--bg-row)」, 还原即绿。

## 本改动面

| 文件 | 改动 |
|---|---|
| `src/auto_qb/webui/static/shared/dt_table.css` | 08 `.bad` 行首格合成基色 `--bg-card` → `--bg-row`(+ 注释记实测承光链: `section.dt08-grp` 计算底 = `--bg-row`)。其余七个面的重锚规则一字未动 |
| `e2e/dt-table-face-bg.spec.mjs` | `STATE_CASES` 补 `'08': { sel: '.group-row.bad' }` —— 一直漏测的位(状态行家族里只缺它) |
| `tests/test_webui_static_skins.py` | `test_frontend_pinned_first_cell_bg_per_face` 的 08 条改口径(必含 `--bg-row` / 禁 `--bg-card`)+ `need()` 的 forbid 文案改为「基色按面确定」 |

未触及: 六个主表面的首格色值、行板/表头令牌、列模型、行为逻辑。
