# my-commit-flow 自我改写版本撕裂 — 快照自举(已实施)

> 摘要: 本包脚本与配置住在它自己中途改写的仓库里 ⇒ 同一次调用里"提交前 / 提交后"跑的**可能不是同一版代码 /
> 同一份规则**(自指缺陷; 旧修法逐点重取配置 / 热刷新模块, 覆盖不全)。**快照自举已实施(2026-10-07)**:
> 入口把整包复制到**仓库之外**的临时目录再从副本重入(`scripts/_snapshot.py`) ⇒ **一次调用 = 一个版本**;
> 三条治标机制(`refresh_package_modules` / `reload_config` / `sync._reload_cfg`)及接线全部退役;
> 上游改本包时留一行提示重跑(不静默)。真机 sync / verify-ref 均经快照重入成功, test.pkg **142 passed**。
> 最后活动: 2026-10-07 02:41

**Refs:** memory-bank/tasks/26-10-07-ship-self-snapshot.md

## 现状

- **已实施, 无未闭环项**。契约 / 取舍 / 开销 / 泄漏处置的单点是
  `.commands/my-commit-flow/references/pipeline.md`「快照自举」节; 可行性分析与原型 10/10 实测见
  `memory-bank/reports/26-10-07-0208-report-my-commit-flow-self-snapshot.html`; 机制退役的收口注记见
  `memory-bank/pitfalls/git/self-rewrite-imports.md` 与 `self-rewrite-config.md` 文末「收口」节。
- **守阵**: `.commands/my-commit-flow/scripts/test_snapshot.py`(15 条: 重入 / 免疫 / 采纳 / 根注入 /
  `import` 不重入 / 退出码 / 治标机制已退役静态守卫) + `test_commit.py::test_post_rebase_pack_changed_leaves_hint`。

## 关键决策(留档)

- **快照语义 = 一次调用只认启动时那份代码 / 配置**。放弃"复跑用新规则"(那正是撕裂来源, 且永远补不全),
  改为 rebase 后若上游改动了本包, 登记一行 `快照: 上游改动了本包 → 本次仍按启动版本运行, 重跑以采用新版本`。
- **重入用 `subprocess.call`**(非 `os.execv`: Windows exec 语义不可靠); 纯信息入口(`--help` / `--safety` /
  `--show-config` / `--init`)不复制, 直接作用原包。
- **闸门等外部工具仍跟仓库走是对的**: 闸门要测**被测的树**, 每次都是新进程、内部一致; 必须固定的只有流水线自身。
