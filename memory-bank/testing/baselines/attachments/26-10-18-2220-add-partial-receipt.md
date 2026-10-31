# 3635 passed + 10 skipped(根, TOTAL 18690/306/6338/208, 覆盖率 98%) —— 添加种子部分受理三态回执修复后全量基线

> 摘要: 添加种子部分受理三态回执修复后全量基线
> 基线时间: 2026-10-18 22:20
> 档案: webui-add-partial-receipt
**Refs:** memory-bank/tasks/26-10-18-webui-add-partial-receipt.md

## 验收数字

`commands run test.full`(2026-10-18 22:1x 实测):

```
TOTAL   18690   306   6338   208   98%
3635 passed, 10 skipped in 37.74s
```

口径: 根套件(pytest.ini 的 8 worker); `TOTAL` 列序 = 语句数 / 未覆盖 / 分支数 / 部分分支 /
覆盖率(成功路径只印整数位)。skipped 10 与上期基线相同(alias_fs 无 symlink 特权环境的约定 skip)。

## 本改动面

用户报障「WEBUI 部分种子添加失败(已存在)时添加窗口不消失」修复(生产 2 文件 + 测试 3 文件 +
新增 e2e 1 文件): ① `src/auto_qb/webui/commands.py` —— `_add_outcome` 由布尔扩为**三值受理态**
(`ok`/`partial`/`fail`: `failure_count>0 ∧ success+pending>0` = partial), `_cmd_add_torrents`
跨文件/链接两次调用聚合成**三态回执**(全受理 ok / 部分受理 warn 带计数 / 全拒 error);
② `src/auto_qb/webui/static/shared/add_torrent.js` —— `submitAddTorrent` 按 `r.status` 分流,
warn(部分受理)关窗 + warn toast, error(全拒)留窗等用户改完重提;
③ `tests/test_web_admin.py` / `tests/test_web_longtail.py` —— 既有部分失败断言由 error 改 warn,
补元数据单调用 + 旧文本混合两调用两种 partial 形态; ④ 新增静态守阵
`test_webui_static_dom_panel.py::test_frontend_add_torrent_partial_receipt_wiring`(已红验);
⑤ 新增 `e2e/add-partial-receipt.spec.mjs`(page.route 注入 warn/error 回执, 双皮肤 × 两方向,
已红验; e2e 不走 test.full, 数字以 `npm run test:e2e:fast` 为准)。关联件:
坑档 `pitfalls/web-ui/add-partial-receipt.md`、`pitfalls/backend/qb-api.md` 回写。
