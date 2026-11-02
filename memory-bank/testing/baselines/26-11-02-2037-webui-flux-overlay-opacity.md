# 4859 passed + 2 skipped —— flux 浮层不透明兜底修复后全量回归

> 摘要: flux 浮层不透明兜底修复后全量回归
> 基线时间: 2026-11-02 20:37

## 验收数字

`commands run test.full` 实测 (2026-11-02 20:37):

- 汇总行: `4859 passed, 2 skipped, 3 warnings in 176.33s (0:02:56)`
- 覆盖率 TOTAL: `22521 stmts / 134 miss / 7726 branch / 128 BrPart / 99%`(Required 99.0% reached, Total 99.11%)
- 3 warnings 均为存量 `SyntaxWarning: invalid escape sequence '\T'`(tests/test_tmp_bootstrap.py 等), 与本轮改动无关
- 首轮曾 3 红: 本任务档案正文手抄 `4859 passed` 触发措辞族 B + 档案空 `**Refs:**` 被认领链误读为下一节标题; 改档后复跑全绿

## 本改动面

- `src/auto_qb/webui/static/flux/style.css`: 新增 `--bg-pop: #1c2a3f` 不透明浮层底令牌
- `src/auto_qb/webui/static/atlas/style.css`、`console/style.css`、`prism/css/tokens.css`: 补惰性别名 `--bg-pop: var(--bg-elev)`(令牌名集守阵)
- `src/auto_qb/webui/static/flux/css/components.css`: 4 处浮层改读 `--bg-pop`(不增行, 仍 700 行)
- `src/auto_qb/webui/static/flux/css/dialogs.css`: 5 处浮层改读 `--bg-pop` + 文末 shared 浮层 flux 作用域覆盖块
- `src/auto_qb/webui/static/flux/css/views.css`: 2 处浮层改读 `--bg-pop`
- `memory-bank/conventions/webui.md`、`memory-bank/pitfalls/web-ui/overlays.md`: 口径与新坑回写
- 无新增测试、无后端改动; flux `backdrop-filter` 仍恰 4 处(预算守阵未动)
