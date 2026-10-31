# 4159 passed + 2 skipped(根) —— 乐观UI扩面 rename/alt 实施收口全量基线

> 摘要: 乐观 UI 扩面计划(26-10-30-0610)S1/S2/S4/S5 实施收口后的全量基线: rename 乐观补丁 + 主备速度切预翻转 + 单测四态/静态守阵/e2e 双皮, 计划置 Done
> 基线时间: 2026-10-30 07:46
**Refs:** memory-bank/plans/26-10-30-0610-plan-webui-optimistic-ui.html

## 验收数字

`commands run test.full`(pytest `-n 8 --cov-branch --cov-fail-under=99`(pytest.ini addopts, TMPDIR 由 task 内置); 2026-10-30 实测, 全量 115.17s, 建档 07:46):

```
  TOTAL                                                21061     99   7126    102    99%
  4159 passed, 2 skipped in 115.17s (0:01:55)
```

- 汇总行: **4159 passed + 2 skipped(根)**; 覆盖率门槛 99% 通过(TOTAL 行 99%)。
- 逐条口径注记:
  - 本基线树 = 乐观 UI 扩面 4 个提交(5ac63a7e S1 rename 乐观补丁 + S4 runtime.py 注释 / e6ef9344 S2 速度切预翻转 / c9b9a1c8 S5a 守阵+四态单测 / 19ab6fbb S5b e2e 双皮)后的分支 HEAD `19ab6fbb`(feat/webui-optimistic-ui, 本地分支)。
  - 「2 skipped(根)」为既有环境条件 skip, 与本计划无关(近期切片同为 2)。
  - 本轮新增: 静态守阵 2 条 + rename/altOverride 四态单测(`tests/test_webui_optimistic_rename_alt.py`)+ e2e 两条 × prism/atlas 双皮 4 例(本 spec 单跑 4 passed)。
  - 真机复测两链延迟(计划 S1/S2 验收项)**阻塞**: qBittorrent-testing 5.2.3 @127.0.0.1:36595 不可达(TCP 连接拒绝), 未测, 无数字。

## 本改动面

| 面 | 内容 |
| --- | --- |
| `src/webui/static/shared/commands.js` | S1: 通用乐观补丁注册口 `applyOptimisticPatch(hashes, action, patch)` + onTruthEvent kind 注入加 action 守卫(只 pause/resume) |
| `src/webui/static/shared/drawer.js` | S1: editRename 对话框确认后 POST 前贴 `{name}` 乐观补丁, 回执链沿用 `_editPost` |
| `src/webui/static/shared/state.js` · `dialogs.js` · `polling.js` | S2: `altOverride` 显示单点(`sbAltOn` override 优先)+ 预翻转 + 四路回滚 + 轮询对账清除 |
| `src/core/runtime.py` | S4: RESYNC_COMMANDS 分支过时注释修正为 D2 现行语义(1 处注释, 零行为) |
| `tests/test_webui_optimistic_rename_alt.py` | S5a: 静态守阵 2 条 + rename/altOverride 四态单测 |
| `e2e/optimistic-rename-alt.spec.mjs` | S5b: 改名立即可见 / 乌龟立即翻转 两条 × prism/atlas 双皮(4 例, 本 spec 单跑 4 passed) |
| `memory-bank/plans/26-10-30-0610-plan-webui-optimistic-ui.html` | R2 变更记录 + 状态 Done; issue 26-10-01-2137 补修复后补充 + 状态 Done |
