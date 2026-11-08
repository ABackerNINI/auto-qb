# skill 装载与脚本路径

> 摘要: skill 里的脚本路径一律写 `<skill-dir>/scripts/…`; 项目级 skill 只挂 `.codebuddy/skills` 一处。
> 触发: 写 skill, 装 skill, skill 不出现, 脚本路径, find_root, 脚本找不到

### skill 里的脚本路径要写 `<skill-dir>/scripts/...`

- **触发**: 在 SKILL.md 或其它 skill 文档里写自己脚本的路径。
- **判别**: 写成相对路径(如 `scripts/xxx.py`)⇒ 执行者会去**仓库根的 `scripts/`** 里找(已踩过, 找不到还以为脚本没写)。
- **处置**: 文档里写 `<skill-dir>/scripts/...`; 脚本内部找仓库根用 **`find_root()` 向上找 `.git`**,
  **不要按 skill 安装深度反推 `parents[n]`** —— 那个下标只在 `.agents/skills/<name>/scripts/` 一种布局下成立。

### 项目级 skills 只挂 `<workspace>/.codebuddy/skills` 这一处

- **触发**: 新增 skill 后"技能列表里没有它"。
- **判别**: ①链接是否在 `.codebuddy/skills` 下 ②是否**重启了会话**(技能列表启动时加载一次)。
  另: 产品文档里的 `.workbuddy-ai/skills` **内置 CLI 根本不读**。
- **处置**: 现状由 `scripts/sync_agent_skills.py` 只挂**顶层** skill(排除设计预设包), 幂等;
  **在源目录增删 skill 后必须重跑该脚本**。
  ⚠ 装载器**递归最深 5 层**收集每一个 `SKILL.md` ⇒ 把整棵技能树挂上去会注入数百条、严重挤占上下文, 所以不能整棵挂。
