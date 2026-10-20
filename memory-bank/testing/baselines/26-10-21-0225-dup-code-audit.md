# 3966 passed + 10 skipped —— 三 shell sprite/login 段守阵(issue 26-10-20-2231)

> 摘要: 三 shell sprite/login 段守阵(issue 26-10-20-2231)
> 基线时间: 2026-10-21 02:25

## 验收数字

`commands run test.full`(本机 Windows, 仓库自带 TMPDIR 前缀), 实测输出:

```text
TOTAL                                                20467     93   7012     93    99%
3966 passed, 10 skipped in 32.87s
```

口径注记:

- 0 failed / 0 error; 覆盖率闸(`--cov-fail-under 99`)照过(99%)。
- 本轮新增 1 条用例: `tests/test_webui_static_skins.py::test_frontend_shell_sprite_login_parity`
  (issue 26-10-20-2231, 三份 shell 的 sprite 段逐字相等 + `#app`+login 段注释归一后相等); 单跑 1 passed,
  所在文件全量 21 passed。
- 红验(守阵活性, 三类突变全部符合预期, 均以精确反向编辑还原):
  ① console sprite 段单边挪一个图标坐标 ⇒ 红, 报「console 的图标 sprite 段与 atlas 不一致 … 首个差异在第 2 行」并给出两侧原文;
  ② prism 登录段单边改一个类名 ⇒ 红, 报「prism 的 #app+login 段与 atlas 不一致 … 首个差异在第 3 行」;
  ③ prism 登录段仅加一行注释 ⇒ 绿(注释容差按设计生效, 不误红)。
  还原后 `git diff -- src/auto_qb/webui/static/` 为空 —— 三份 shell 零改动, 本 issue 纯测试缺口。

## 本改动面

| 文件 | 改动 |
|---|---|
| `tests/test_webui_static_skins.py` | 新增静态守阵 `test_frontend_shell_sprite_login_parity`(锚点切片 + 逐字/归一比对 + symbol 数 ≥40 下限 + 首个差异行报错) + 文件头「测试计划」清单一行 |
| `memory-bank/issues/26-10-20-2231-test-fe-tpl-shell-parity-guard.html` | 状态 Open → In Progress → Done; 新增 §04 修复与验证(复验/实际修法/与建议的改道/红验三类/测试数字) |
| `memory-bank/pitfalls/web-ui/frontend-split.md` | 新增「三份 shell 内联段 parity 守阵」节(触发/判别/处置/守阵登记) |
| `memory-bank/issues/_index.md` · `memory-bank/issues/attachments/_archive.md` | 索引重建生成物(`commands run kb.index`) |
| `memory-bank/testing/baselines/26-10-21-0225-dup-code-audit.md` | 本切片 |

未触及: 三份 `index.html` 生产 shell(红验突变已精确还原, `git diff` 零改动)、`shared/` 模板分片与全部后端代码。
上一轮(必显列选中/展开行保留行底)的改动与数字见 `memory-bank/testing/baselines/26-10-20-1339-webui-pinned-first-cell-selected.md`。
