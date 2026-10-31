# 生产文件红线

> 摘要: `config.yml` 与 `auto-qb-data/` 是用户真实生产数据 —— 提交面禁令由 `.commands/my-commit-flow/.my-commit-flow.toml` 的 `red_lines` **机器预检强制执行**(预检与 `commit.py` 直接拒交, 不靠记性); 本条目是人工红线说明: 红线清单、判别与为什么禁碰。
> 等级: L0
> 触发: 改配置示例, 新增示例 yml, 提交前扫红线, 整理仓库, 统一格式

## 人工红线说明

### `config.yml`: 用户真实生产配置, 不是示例

- **触发**: 想"顺手"改配置 / 提交前扫红线 / 要加一个示例配置。
- **判别**: 文件里出现**真实 PT 域名、tracker 规则、qB 凭据引用** ⇒ 这是生产配置, 不是示例。加/改示例一律用 `minimal.yml` / `test_yamls/`。
- **强制执行**: 已登记进 `red_lines`, 预检与 `commit.py` 都会**直接拒交** —— 禁令不靠人自觉; 预检拦截即红线生效, 别找绕过。

### `auto-qb-data/`: 运行时数据, 不要格式化 / 重排

- **触发**: 整理仓库目录 / 统一文件格式 / 写"清理脚本"时。
- **判别**: 路径是 `auto-qb-data/`, 内容是 `state.json`、锁 `<state_file 去扩展名>.lock` + 伴生 `.meta.json`、`logs/auto-qb.log`、`skip-check-backup/`。
- **为什么禁碰**: `state.json` 由程序**周期性覆写**(`state_save_interval`, 默认 120s, `core/state.py` `maybe_flush`)且优雅退出立即落盘, 是活数据 —— 改坏等于让下次启动读到错状态。工作区写操作不在 `red_lines` 预检面内, 这里只靠本条说明守住。

### 两者都已 gitignore, 但"看得见"不等于"可以动"

- **触发**: 做"整理仓库 / 统一行尾 / 格式化"这类动作时。
- **判别**: `git status` 里看不到它们(gitignore) ⇒ 容易误以为"不属于项目, 随便动"。gitignore 只挡提交面, 不挡工作区误操作。
- **处置**: 保持不动; 需要在工作区里排除干扰就只处理**跟踪文件**, 别对整目录下手。
