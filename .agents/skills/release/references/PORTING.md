# PORTING — release(自制: 机械化发版管线)

轨道移植 runbook 单点: [memory-bank/references/PORTING.md](../../memory-bank/references/PORTING.md) —— 双场景详版/配置落点/回落语义一律以它为准, 本件不复制, 只声明本 skill 的依赖面(照实核实)。

| 依赖面 | 内容 |
|---|---|
| 数据件 | 项目侧口径单点 `<KB>/conventions/release.md`(版本语义/major 判据/分支模型 —— 通用性契约, SKILL.md 只留流程) |
| 配置键 | skill 脚本零项目事实(参数化设计); 项目事实全在 `.commands/release/config.toml`(远端名/gh repo/gitee+github 仓/发布分支/解释器/**tag 附注前缀** `release.tag` run 行 `--tag-note-prefix`, 计划 26-11-17-0010 S11 批9b 外置 —— 缺省脚本回落通用附注 `release <tag>` 并打 WARN, 非静默) —— **移植改动面 = bump 配置 + commands 包 config + 口径文档**(SKILL.md 拍板) |
| 可选守卫 | 无 |
| 其它 | 运行依赖: commands 引擎 + release 包 + my-commit-flow(ship) + `GITEE_TOKEN` 环境变量(未配 = 降级过渡 WARN 不失败)+ `gh` CLI + 测试门 task id(本项目实例: `test.full`/`dev.e2e`/`test.linux`) |

- **新项目绿地**: 拷 skill + release 包 → config.toml 填项目仓与远端 → 写 conventions/release.md 口径 → 先走一次 patch 级冒烟发版。
- **开发中途存量(重点)**: 分支模型按项目现状填(发布分支/工作分支), 远端只一个就删镜像步; token 未配先按降级口径跑通主线 —— 八步流水与判断点以 SKILL.md 为准, 口径单点 conventions/release.md。
