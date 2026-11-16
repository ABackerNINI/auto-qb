# PORTING — commands(自制: 命令引擎)

轨道移植 runbook 单点: [memory-bank/references/PORTING.md](../../memory-bank/references/PORTING.md) —— 双场景详版/配置落点/回落语义一律以它为准, 本件不复制, 只声明本 skill 的依赖面(照实核实)。

| 依赖面 | 内容 |
|---|---|
| 数据件 | 无 —— 引擎零数据件; 实际命令来自 `.commands/` 各包, 不拷包 = `commands list` 空转 |
| 配置键 | 引擎无自有配置, 唯一读 `<包>/config.toml`(schema 三块, 键白名单单点 `scripts/_config.py`); 各包起步模板见 runbook「模板清单」, `<skill-dir:NAME>` 占位符项目级 `.agents/skills/` 优先、用户级兜底 |
| 可选守卫 | 无 |
| 其它 | 解释器跟各包 config 的 `run` 写法走(出厂模板 `python3`; 本项目实例: `uv run`) —— wrapper(`install_wrapper.py`)按包内命令原样展开 |

- **新项目绿地**: 拷本 skill + 按模板建包, 走 runbook 移植单位清单表 #2/#3。
- **开发中途存量(重点)**: 引擎零配置直接拷, 包按需逐个收编 —— 项目已有脚本先照旧跑, 收编一条录一条 task id(口径见 runbook 双场景 B)。
