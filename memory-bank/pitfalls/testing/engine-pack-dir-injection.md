# commands 引擎注入的 COMMAND_FLOW_PACK_DIR 指向 task 所在包, 包内测试要真实配置必须钉 PKG

> 摘要: commands 引擎注入的 COMMAND_FLOW_PACK_DIR 指向 task 所在包, 包内测试要真实配置必须钉 PKG
> 触发: COMMAND_FLOW_PACK_DIR, 包测试, ConfigMissing, load_config, 钉 PKG, 外置配置, test_commit 夹具

## 本篇只回答

包内脚本测试直接调 `load_config()` 想读"自家包"的 `.my-commit-flow.toml` 时, 为什么会在 commands 引擎链路下读到别家包、以及怎么钉回去。

### 包测试经 test.pkg.scoped 跑时, load_config 的配置源被引擎注入换到别的包

- **触发**: 新增包内脚本测试(如 test_gate.py)直接调 `load_config()` / `config_problems(cfg, src)` 且**不经过**带 `monkeypatch.setenv("COMMAND_FLOW_PACK_DIR", str(PKG))` 夹具的用例; 该测试经 `commands run test.pkg.scoped` 执行(提交闸门 / 手工都算)。单独 `uv run pytest <文件>` 复现不了 —— 引擎注入只在经 run.py 调 task 时发生。
- **判别**: 报错 `_ship_config.ConfigMissing: [STOP] 缺少外置配置: <仓库根>/.commands/test/.my-commit-flow.toml` —— 路径指到 `.commands/test`(pkg_scoped 所在包)而非被测包; 同一批用例里走夹具的全绿、不走夹具的独红。机理: `commands run` 调 task 时给子进程注入 `COMMAND_FLOW_PACK_DIR=<task 所在包>`(test 包 task 的注入值即 .commands/test), 该环境变量被 subprocess 原样透传给 pytest 及其全部 worker, `_ship_config.pack_dir()` 优先吃它(`_ship_config.py:40-47`); monkeypatch 的 setenv 只在各自用例内生效, 夹具外的用例裸奔在注入值上。
- **处置**: 凡在包内测试里要读**真实包配置**的用例, 一律 `monkeypatch.setenv("COMMAND_FLOW_PACK_DIR", str(PKG))` 钉回本包(PKG = `Path(__file__).resolve().parent.parent`); 系统性做法是像 test_commit.py 那样把 setenv 放进 repo 夹具, 新用例自觉挂夹具。写守阵自检用例(真实配置装载 + config_problems 零 STOP)时同样必须钉。
- **守阵**: `.commands/my-commit-flow/scripts/test_gate.py::test_pack_config_passes_config_problems`(注释里写明"必须钉 PKG"的原因; 漏钉时该用例在 test.pkg.scoped 链路下当场 ConfigMissing 红)。
- **复发**: 0 (复踩时在此行追加「+N (日期): 为什么没命中」, 无复发可删本行)
