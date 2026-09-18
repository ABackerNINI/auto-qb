# TASK005 - 依赖管理与运行环境现代化 (uv / pyproject / venv 重建)

**Status:** Completed
**Added:** 2026-09-15
**Updated:** 2026-09-15
**专题:** 工程基建 / 依赖 / CI

## 原始请求

- 2026-09-15: 用现代依赖管理 (PEP 621 + 锁文件) 取代裸 `requirements.txt`; 随后修复 `uvicorn` 启动异常并重建全部 worktree 依赖环境。

## 思考过程与决策

- 选型 `pyproject.toml` (PEP 621 + hatchling) + `uv.lock` 全量锁 + PEP 735 依赖组; 12 个直接依赖**锁死**版本; entry point `auto-qb = auto_qb.cli:main`。
- CI 切 `astral-sh/setup-uv@v10` (enable-cache) + `checkout@v6` + `setup-python@v7`。
- 先出调研报告 (`docs/plans/26-09-15-1150-dependency-lock-report.md`) 再实施。
- venv 事故根因: 半截 `httptools` 残留 (缺 `__init__.py` + dist-info 损坏, 疑杀软/中断所致) 被当命名空间包导入成功, `uvicorn` `http=auto` 误选它 → 修 `web.py` 显式指定协议 + 7 个 worktree venv 全量重建。

## 实现计划

- [x] 调研与选型报告
- [x] `pyproject.toml` + `uv.lock` + `uv sync` 重建 `.venv` (清除旧壳与约 20 个无关包)
- [x] CI 切换 uv
- [x] `uv build` sdist/wheel + entry point 冒烟
- [x] 7 个 worktree venv 全量重建 (含无 pyproject 的老提交统一按根锁定版本平装)
- [x] 文档回写 (README / AGENTS / testing / techContext / progress)

## 子任务状态表

| ID | 描述 | 状态 | 更新 | 备注 |
|----|------|------|------|------|
| 5.1 | 依赖锁调研报告 | Complete | 2026-09-15 | `docs/plans/26-09-15-1150-dependency-lock-report.md` |
| 5.2 | `pyproject.toml` + `uv.lock` + `uv sync` | Complete | 2026-09-15 | 41 包全量锁; 872 passed (uv 环境) |
| 5.3 | CI 切 uv | Complete | 2026-09-15 | `ci.yml` |
| 5.4 | worktree venv 全量重建 (7 个) | Complete | 2026-09-15 | 14 模块导入全 OK + `pip check` 无损 |
| 5.5 | `requirements-dev.txt` 删除 | Complete | 2026-09-15 | 曾被 Safety Guard 拒绝, 由用户手动 `git rm` |

## 进度日志

### 2026-09-15

- 依赖现代化完成; 基线 872 passed (uv 环境)。
- venv 事故修复: `web.py` 显式指定协议 + 7 环境重建, 根 venv 实机 `uvicorn` 启动与请求 200 验证通过 (880 passed)。
- 踩坑: VS Code isort 辅助进程占用并自动重生 venv `python.exe` 阻塞删除 (须在同一命令内先杀后删), 已记 `pitfalls.md` 环境条目。

## 历史会话纪要 (原文归档)

> 以下为 `activeContext.md` 会话纪要的**原文归档** (2026-09-17 机械迁移, 未删改; 含一处历史 GBK 编码损坏条目),
> 按时间倒序保留。新增进展请写 `## 进度日志`, 不要再往 `activeContext.md` 堆长纪要。

- 2026-09-15: venv 事故修复 + 7 worktree 依赖全量重建 — 用户报 uvicorn 每连接 `AttributeError: httptools 无 HttpRequestParser`: 根因=根 venv 里半截 httptools 残留(缺 `__init__.py` + dist-info 元数据损坏, 疑杀软/中断所致)被当命名空间包导入成功, uvicorn `http=auto` 误选它; `web.py` 的 uvicorn.Config 未显式指定协议。按用户指示全量重建 7 个 worktree venv(auto-qb/autoclaw 根/backend/other/trae/zcode 删旧重建, frontend 无 venv 新建; trae/zcode 老提交无 pyproject, 统一用根 pyproject 锁定版本平装, 其余 editable 安装 `-e .`), 依赖=12 运行时锁定 + pytest 9.1.1/pytest-cov 7.1.0, 基础解释器 Python 3.12.0(AppData, uv 仍禁用走 pip)。验证: 7 环境 14 模块导入全 OK + pip check 无损 + 传递依赖版本与 uv sync 时代一致; 根 venv uvicorn 实机启动解析到 H11Protocol 且请求 200(bug 路径复现通过); 根 venv 全量 pytest **880 passed**(基线 879 之上)。坑: VS Code isort 辅助进程占用并自动重生 venv python.exe 阻塞删除(杀完同命令内立即删, 详见 pitfalls 环境条目); auto-qb-long-seeding 非本仓库 worktree 且生产进程在跑, 未动。
- 2026-09-15: 依赖管理现代化实施 — 前置调研(docs/plans/26-09-15-1150-dependency-lock-report.md: 12 直接依赖 10 已最新, filelock/uvicorn 小落后, checkout/setup-python 各落后 1 major); 实施: 新增 pyproject.toml(PEP 621 + hatchling, 12 直接依赖 == 锁死, dev 走 PEP 735 依赖组, entry point auto-qb=auto_qb.cli:main) + uv.lock(41 包全量锁) + `uv sync` 重建 .venv(清除旧壳与约 20 个无关包, uv 0.12.13 winget 安装); ci.yml 切 uv(astral-sh/setup-uv@v10 enable-cache + checkout@v6 + setup-python@v7 + uv sync/uv run pytest); 验证: 新 venv 全量 872 passed + uv build 出 sdist/wheel + entry point 冒烟; README/AGENTS/testing/techContext/progress 回写; 坑: 旧 venv 被残留 smoke_server 进程占用致 uv sync os error 5(杀进程解决); requirements-dev.txt 删除被 Safety Guard 拒, 待用户手动 git rm; 未提交(工作区有并行会话未入库改动, 避免混提交)。
