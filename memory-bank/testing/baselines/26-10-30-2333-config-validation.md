# 4173 —— chore: qbittorrent 三 str 键类型校验(26-10-30-0622)

> 摘要: chore: qbittorrent 三 str 键类型校验(26-10-30-0622)
> 基线时间: 2026-10-30 23:33

## 验收数字

`commands run test.full` 实测(2026-10-30 23:33, Windows, Python 3.14.7):

```text
TOTAL                                                20885    114   7156    105    99%
4173 passed, 10 skipped in 69.22s (0:01:09)
```

- 汇总行: 4173 passed / 10 skipped, 零 failed; 覆盖率总行 99%( statements 20885 / miss 114 / branch 7156 / brpart 105 )。
- 口径注记: 覆盖率总百分比按 TOTAL 行四舍五入为 99%; 10 skipped 为平台/真机条件跳过, 非本轮新增。

## 本改动面

- `src/auto_qb/config/validation/sections.py` — `_validate_qbittorrent` 补 username/password/api_key 三键 `isinstance(str)` 循环校验(照 `_validate_web` token 形态, 空串合法=未配置语义), 消除「键误写成容器时校验零报错、运行期才在 qB 登录载荷/Bearer 头构造处炸」的 fail-fast 覆盖缺口(issue 26-10-30-0622)。
- `tests/test_config.py` — 新增 `test_validate_qbittorrent_str_keys`(容器值三键各报「必须是字符串」/ 正常串与空串不误伤), 文件头测试计划同步登记。
- `memory-bank/issues/26-10-30-0622-chore-config-qbittorrent-str-typecheck.html` — 状态 Open→In Progress→Done, 状态变更日志补认领复验与修复两行。
- 生成物: `memory-bank/issues/_index.md`、`memory-bank/issues/attachments/_archive.md`(kb.index 重建)。
