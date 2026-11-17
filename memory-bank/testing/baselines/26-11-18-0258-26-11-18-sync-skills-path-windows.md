# 6452 passed, 6 skipped —— sync-skills-path-windows 收尾基线

> 摘要: sync-skills-path-windows 收尾基线
> 基线时间: 2026-11-18 02:58

## 验收数字

`commands run test.full` 实测(2026-11-18 02:56, Windows, 2m21s):

```
TOTAL                                                28864     43  10304     60    99%
6452 passed, 6 skipped in 141.04s (0:02:21)
```

同轮 Windows 侧 `commands run test.quick` 实测: `6456 passed, 2 skipped`(65s; 修复前该口径 `1 failed, 6455 passed, 2 skipped` —— 唯一红即本专题 issue 的 `test_config_can_add_and_remove_entries`)。

## 本改动面

- `scripts/sync_agent_skills.py`(+8/-2 含注释): `resolve_sync_config` link_targets 绝对判定平台/版本稳定化 —— `os.path.isabs` → `ntpath.isabs(p) or p[:1] in ("/", "\\")`(盘符/UNC 交 ntpath, 根锚定交纯字符串判定), 新增 `import ntpath`; 修 issue 26-11-18-0210(Windows Python 3.13 `ntpath.isabs('/x')` 语义变更致「绝对路径原样采用」断言恒红), 相对路径分支零行为变化。
- 测试零改动: `tests/test_sync_agent_skills_config.py` 11 条原样全绿(契约「绝对路径原样采用」由生产侧对齐, 未放宽断言)。
- 记账: issue 26-11-18-0210 翻 Done + 正文补复验行与「修复后补充」; 坑档 `pitfalls/backend/platform-fs.md` 增「Python 3.13 Windows isabs 根锚定语义变更」条; `commands run kb.index` 已重建。
- 本切片。
