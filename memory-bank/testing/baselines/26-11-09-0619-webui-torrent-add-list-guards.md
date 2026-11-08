# 5,869 passed + 2 skipped —— torrent-add list 守卫补齐(issue 0043)

> 摘要: torrent-add list 守卫补齐(issue 0043)
> 基线时间: 2026-11-09 06:19

## 验收数字

`commands run test.full` 2026-11-09 06:20 实测(本轮收尾时点): **5,869 passed, 2 skipped in 123.38s**; 覆盖率 99% (TOTAL 26,153 语句 / 42 未覆盖 / 9,100 分支 / 54 未覆盖分支)。较基线 26-11-09-0549(5,866+2)净增 3 条用例: `test_api_list_body_fields_string_rejected_400` 坏例 +4(add files_b64/urls/tags 字符串、file-priority indices 字符串)与 bulk keys 字符串 1 条, 合法回归 +2(file-priority indices 入队、bulk keys 编码组键解码入队), 同一测试函数内净 +3 条断言组。

## 本改动面

- `src/auto_qb/webui/server/routes/torrent_cmds.py`: add 面 files_b64/urls/tags 与 file-priority indices 四处接 `_list_param` 守卫(字符串 400 拒收不入队, issue 26-11-08-0043); bulk keys 同换 `_list_param`(报错文案由逐字符「分组标识无效」误导改为准确的「keys 必须是数组」), bulk docstring 的 issue 归属分开(hashes·tags=0536 / keys=0043)。
- `tests/test_web_longtail_routes.py`: `test_api_list_body_fields_string_rejected_400` 扩展(坏例 +5 / 合法回归 +2), 文件头测试计划清单与函数 docstring 同步(覆盖面 5 处 → 10 处 _list_param 调用点)。
- memory-bank 回写: issues/26-11-08-0043(状态翻 Done + 复验行 + 修复后补充) + active-context 切片 26-11-09-0617。
