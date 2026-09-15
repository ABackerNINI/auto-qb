# AGENTS.md

> 所有 AI 编码代理的统一入口 (Copilot / Codex / Cursor / Gemini CLI / Claude Code / ZCode / Trae 通用)。
> 完整知识库在 `memory-bank/` (Memory Bank 模式) — 本文件只放路由与硬约束; 不要凭印象回答项目问题, 按路由深入后再动代码。

## 会话协议

- **开始**: 读 [memory-bank/activeContext.md](memory-bank/activeContext.md) (当前焦点) + [memory-bank/README.md](memory-bank/README.md) 路由表, 按任务选择深入文档。
- **收尾**: 更新 `memory-bank/activeContext.md`; 代码事实变更时回写 `memory-bank/` 对应文档与根 `README.md`; 跨会话的大任务在 `memory-bank/tasks/` 立档。
- **冲突裁决**: 代码 > `memory-bank/` > 根 `README.md` > `想法.md`。发现文档漂移时以代码为准并回写文档。

## 黄金法则 (来自设计原则, 违反即破坏设计)

1. **幂等性**: 动作重复执行不得产生副作用; "每天一次"等窗口语义必须靠 state_file 去重 (`record_execution`), 不依赖循环频率。
2. **保守默认**: 高风险动作 (跳检/强制汇报/删除种子/覆盖限速) 默认关闭, 只对显式配置范围生效。
3. **状态持久化**: 跨轮次状态统一进 state_file, 程序退出时才落盘。
4. **fail-fast**: 配置在 `config.validate_config` 全量校验并聚合报错; 校验之后的代码假定配置正确, 不做防御性检查; **新配置键必须加入 validate_config 并同步 `config/schema.py`** (守卫测试会查)。
5. **单一写线程**: 只有主循环线程修改任务队列结构与 state_file; 不要引入绕开该假设的并发代码。

## 红线 (生产文件, 禁止改动/提交)

- **`config.yml`**: 用户真实生产配置 (真实 PT 站点域名、tracker 规则、qB 凭据引用), 不是示例! 示例用 `minimal.yml` / `test_yamls/`。
- **`auto-qb-data/`**: 运行时数据目录 (state.json / 锁 / 日志 / 跳检备份), 已 gitignore; 不要"顺手"格式化或重排。

## 命令

注意: uv报毒, 暂时禁用uv等后续修复, 测试使用元素命令!!

```bash
# 依赖统一走 uv (pyproject.toml + uv.lock); 首次/依赖变更后先 `uv sync`
uv run pytest tests -q                                 # 全量测试 (pytest.ini 已带分支覆盖率; 基线数字单点见 memory-bank/testing.md 顶部)
uv run pytest tests/test_grouping.py -q
uv run pytest tests -q --no-cov                        # 快速迭代 (跳过覆盖率报表)
uv run python src/auto-qb.py config.yml --dry-run      # 运行 (需真实 qBittorrent; 一律先 --dry-run 观察)
yapf -i src/auto_qb/**/*.py                            # 格式化 (.style.yapf: facebook 风格, 列宽 120)
```

- 测试命令 2026-09-15 实测通过 (uv 环境下 872 passed); 命令与 `memory-bank/testing.md` 同源维护。
- 新增测试必须同步该测试文件头部 docstring 的 "## 测试计划" 清单 (项目明文规定)。

## 知识库路由 (先查这里再动代码)

| 任务 | 读 |
|---|---|
| **会话开始/收尾** (现在做什么/做到哪) | [memory-bank/activeContext.md](memory-bank/activeContext.md) |
| 项目目标与范围 (纲领) | [memory-bank/projectbrief.md](memory-bank/projectbrief.md) |
| 项目是什么 / 领域知识 | [memory-bank/productContext.md](memory-bank/productContext.md) |
| 主循环/任务队列/数据层/异步校验 | [memory-bank/systemPatterns.md](memory-bank/systemPatterns.md) |
| 找功能位置 / 加新模块 | [memory-bank/modules.md](memory-bank/modules.md) |
| 规则/条件/动作 | [memory-bank/rule-system.md](memory-bank/rule-system.md) |
| 配置解析 / 新配置键 | [memory-bank/config-reference.md](memory-bank/config-reference.md) |
| 命名/风格/约定 | [memory-bank/conventions.md](memory-bank/conventions.md) |
| 技术栈/开发环境/约束 | [memory-bank/techContext.md](memory-bank/techContext.md) |
| 写/跑测试 | [memory-bank/testing.md](memory-bank/testing.md) |
| 改代码前必读 (风险点/陷阱) | [memory-bank/pitfalls.md](memory-bank/pitfalls.md) |
| XX 做了吗 / 计划怎么做 | [memory-bank/progress.md](memory-bank/progress.md) |
| 跨会话任务档案 | [memory-bank/tasks/_index.md](memory-bank/tasks/_index.md) |

## 提交 / PR

- 日常开发在 `develop` 分支; 提交信息为中文一句话概述 (参照 `git log` 风格)。
- 提交前: 全量测试通过; 用户可见行为变更需同步 `README.md` 与 `memory-bank/`。
