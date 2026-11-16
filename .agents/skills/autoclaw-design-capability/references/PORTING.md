# PORTING — autoclaw-design-capability(半自制: design 路由库)

轨道移植 runbook 单点: [memory-bank/references/PORTING.md](../../memory-bank/references/PORTING.md) —— 双场景详版/配置落点/回落语义一律以它为准, 本件不复制, 只声明本 skill 的依赖面(照实核实)。

| 依赖面 | 内容 |
|---|---|
| 数据件 | 无外部数据件 —— 自足(路由/规则/参考面全在目录内: `INDEX.md` / `TASK_ROUTER.md` / `DESIGN.md` / `design-assets-index/` / 内嵌 `infinite-canvas-output/` 等) |
| 配置键 | 无 |
| 可选守卫 | 无 |
| 其它 | 来源与改造: store 件(v1.1.2)+ 本仓安全审查改造(2026-09-20 剔除凭据解密链/删 12MB 重复副本)—— **版本不随上游, 上游更新不可直接覆盖**(会带回被清理面); 体积大(数 MB 级), sync 挂载面建议排除(本项目实例: `sync_agent_skills.py` 的 `EXCLUDED`, S9 后收编进 `.agents/skills/.config/sync.toml`) |

- **新项目绿地**: 整目录拷或按需不拷(纯设计参考库, 不装不影响轨道其余单位)。
- **开发中途存量(重点)**: 唯一动作 = 决定是否纳入 sync 排除表(体积/挂载成本), 本体零配置零改动。
