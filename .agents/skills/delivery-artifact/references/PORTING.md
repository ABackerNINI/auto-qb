# PORTING — delivery-artifact(半自制: 单文件 HTML 交付物)

轨道移植 runbook 单点: [memory-bank/references/PORTING.md](../../memory-bank/references/PORTING.md) —— 双场景详版/配置落点/回落语义一律以它为准, 本件不复制, 只声明本 skill 的依赖面(照实核实)。

| 依赖面 | 内容 |
|---|---|
| 数据件 | 无外部数据件 —— 自足(assets/references 内置; Stage 形态路由内嵌 `references/huashu-design/`) |
| 配置键 | 无 |
| 可选守卫 | 无 |
| 其它 | 两个项目侧绑定点: ① SKILL.md 把 PDF 路由到顶层 `pdf-creator` skill(本仓未装 —— 目标项目自行决定 PDF 路径或保留空路由); ② 适用边界由项目约定层定义(本项目实例: `memory-bank/conventions/doc-forms.md` 把计划/报告划给 `kb.new` 派生, 本 skill 只管四工位外的可视化交付物; HTML dark 主题口径在 conventions/webui.md) |

- **新项目绿地**: 整目录拷即用; 在项目约定层写明它与 KB 建件面的分工边界。
- **开发中途存量(重点)**: 本体零配置; 只需与项目既有交付约定合流时先划边界(哪些形态走本 skill、哪些走 KB 建件), 防同一成果两条产出路径。
