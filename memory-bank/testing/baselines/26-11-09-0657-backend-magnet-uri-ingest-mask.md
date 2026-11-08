# 5871 —— magnet_uri 入库掩码批(issue 26-11-08-0043)

> 摘要: magnet_uri 入库掩码批(issue 26-11-08-0043)
> 基线时间: 2026-11-09 06:57

## 验收数字

`commands run test.full` 2026-11-09 07:32 实测(本轮收尾时点, 评审修复轮后最终树): **5,871 passed, 2 skipped in 155.93s**; 覆盖率 99% (TOTAL 26,154 语句 / 41 未覆盖 / 9,102 分支 / 53 未覆盖分支)。较基线 26-11-09-0619(5,869+2)净增 2 条用例: `test_utils_parse.py::test_mask_magnet_tracker_urls` 与 `test_sync.py::test_apply_delta_masks_magnet_uri_tr_values`; 另有 `test_web_seed_center.py::test_api_torrent_detail_endpoint` 原函数扩断言(magnet_uri 掩码钉面)不计新增。

## 本改动面

- `src/auto_qb/torrents/record.py`: apply_delta 增设入库泄敏单点之二(issue 26-11-08-0043) —— magnet_uri 的 tr= 落槽即掩, 同 tracker 批B 口径(掩码在相等比较之前/空值不掩/确定性一致零假变化); 槽位注释同步。
- `src/auto_qb/infra/utils.py`: 新公开单点 `mask_magnet_tracker_urls`(自 qbmanager `_mask_magnet_tracker_urls` 逐字下沉, 26-11-07-0527 debug 导出先例函数体); quote/unquote 导入补充。
- `src/auto_qb/core/qbmanager.py`: `_mask_debug_torrent_dict` 改引用 utils 下沉单点, 本地函数退役。
- `src/auto_qb/webui/server/routes/torrent_detail.py` / `views_row.py`: 注释口径同步(详情响应体只含掩码值; 复制 magnet 出掩码版指向 0639)。
- 测试钉面: `tests/test_utils_parse.py`(mask_magnet_tracker_urls: tr= 掩码/多 tr=/非 magnet 与空原样/确定性)、`tests/test_sync.py`(apply_delta 落槽即掩/重复喂同原文零假变化/无 tr= 原样)、`tests/test_web_seed_center.py`(详情响应体 passkey 原文不外发), 三文件 docstring 测试计划同步。
- memory-bank 回写: issues/26-11-08-0043(Done + 复验行 + 修复后补充)、issues/26-11-09-0639 入池(复制 magnet 入口处置待拍板)、档案 26-11-09-backend-magnet-uri-ingest-mask、切片 26-11-09-0657(本件)。
