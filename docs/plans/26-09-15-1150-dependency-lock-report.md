# 依赖版本调研与锁定建议 — auto-qb

> 快照日期：2026-09-15 · 数据来源：`.venv` 实测（`pip list --outdated`）+ PyPI（`pip index versions`）+ GitHub Releases
> 范围：12 个直接依赖（Python）+ 3 个 GitHub Actions + venv 环境卫生。本报告只调研，未改动任何文件。

## 核心结论

1. 依赖声明只有一处：`.github/workflows/requirements-dev.txt`，**12 个直接依赖全部无版本约束**，无 pyproject.toml / requirements.txt / lock 文件。
2. "全部最新版"基本成立：**10/12 已是 PyPI 最新**；仅 `filelock`（落后 1 个补丁版本）和 `uvicorn`（落后 1 个 minor 版本）小幅落后。
3. CI 的 GitHub Actions 有 2 个落后一个主版本：`checkout@v5`（最新 v6）、`setup-python@v6`（最新 v7.0.0）；`upload-artifact@v6` 已是最新。
4. 推荐锁定方式：**双层锁定** —— requirements-dev.txt 直接依赖全部改 `==` 精确锁 + 用干净 venv `pip freeze` 生成全量 lock 文件供 CI 使用。当前 venv 混有约 20 个与项目无关的包，**不要直接在现有 venv 里 freeze**。

## 依赖声明现状

| 声明位置 | 内容 | 锁定状态 |
|---|---|---|
| `.github/workflows/requirements-dev.txt` | 10 个运行依赖 + 2 个测试依赖 | 全部未锁（每次 CI 装最新） |
| `apm.lock.yaml` | agent 技能包 gem-team 1.125.0（commit 026742a） | 已锁，无需处理 |
| pyproject.toml / requirements.txt / lock | 不存在 | — |

## 直接依赖版本盘点（12 个）

| 包 | 用途 | venv 已装 | PyPI 最新 | 状态 | 建议锁定 |
|---|---|---|---|---|---|
| pyyaml | config.yml 读取（yaml.BaseLoader 全字符串） | 6.0.3 | 6.0.3 | ✅ 最新 | `pyyaml==6.0.3` |
| qbittorrent-api | qBittorrent WebUI API 客户端 | 2026.8.1 | 2026.8.1 | ✅ 最新 | `qbittorrent-api==2026.8.1` |
| filelock | 单实例锁 | 3.32.5 | 3.32.6 | ⚠️ 落后 1 patch | `filelock==3.32.6` |
| pystray | 系统托盘（仅 `--tray`） | 0.19.5 | 0.19.5 | ✅ 最新 | `pystray==0.19.5` |
| pillow | 托盘图标绘制 | 12.3.0 | 12.3.0 | ✅ 最新 | `pillow==12.3.0` |
| customtkinter | 托盘 GUI 界面 | 6.0.0 | 6.0.0 | ✅ 最新 | `customtkinter==6.0.0` |
| fastapi | WEB UI 后端 | 0.141.1 | 0.141.1 | ✅ 最新 | `fastapi==0.141.1` |
| uvicorn | WEB UI 服务器（线程内运行） | 0.52.4 | 0.53.0 | ⚠️ 落后 1 minor | `uvicorn==0.53.0` |
| ruamel.yaml | config 写回（保留注释 round-trip） | 0.19.1 | 0.19.1 | ✅ 最新 | `ruamel.yaml==0.19.1` |
| httpx | fastapi.testclient.TestClient 传输层（仅测试用） | 0.28.1 | 0.28.1 | ✅ 最新 | `httpx==0.28.1` |
| pytest | 测试框架 | 9.1.1 | 9.1.1 | ✅ 最新 | `pytest==9.1.1` |
| pytest-cov | 覆盖率 | 7.1.0 | 7.1.0 | ✅ 最新 | `pytest-cov==7.1.0` |

## 传递依赖映射（锁定需覆盖）

| 直接依赖 | 传递依赖 |
|---|---|
| qbittorrent-api | requests → charset-normalizer, idna, urllib3, certifi；six |
| fastapi | starlette；pydantic → pydantic-core, annotated-types, annotated-doc, typing-extensions, typing-inspection |
| uvicorn | click, h11；colorama（Windows） |
| httpx | anyio, certifi, httpcore, idna |
| pystray | pillow, six |
| customtkinter | darkdetect, packaging |
| pytest | iniconfig, packaging, pluggy, pygments；colorama（Windows） |
| pytest-cov | coverage, pluggy |
| pyyaml / filelock / pillow / ruamel.yaml | 无强制依赖 |

## venv 环境卫生

- venv 基于 **Python 3.12.0**（系统 Python312）；CI 矩阵是 3.12 / 3.13，锁定值需两个版本都验证。
- `pyvenv.cfg` 显示 venv 创建于旧路径 `d:\Projects\auto-qb\.venv`（项目改名前的遗留），仍可用，但建议锁定时重建干净 venv。
- venv 里的 **pip 23.2.1 已落后**（最新 26.2.1），顺手升级。
- 混入的无关包（约 20 个，建干净 venv 后自然消失）：environs、marshmallow、python-dotenv、argon2-cffi（+bindings）、cffi、pycparser、cryptography、rich、markdown-it-py、mdurl、jinja2、markupsafe、esprima、quickjs、prettyprinter、colorful、merge_args、watchfiles、websockets、httptools（后三个是 uvicorn[standard] 的 extra，项目代码未用到）。

## GitHub Actions 版本（ci.yml）

| Action | ci.yml 现用 | 最新 | 状态 | 备注 |
|---|---|---|---|---|
| actions/checkout | v5 | v6 | 落后 1 major | v6 强化凭据安全 |
| actions/setup-python | v6 | v7.0.0 | 落后 1 major | v7 移除 `pip-install` 输入（本项目未用，无影响）；ESM 迁移 |
| actions/upload-artifact | v6 | v6 | ✅ 最新 | v6 需 runner ≥ 2.327.1，GitHub 托管 runner 已满足 |

## 锁定方案对比

| 方案 | 做法 | 优点 | 缺点 | 适配度 |
|---|---|---|---|---|
| **A. 双层锁定（推荐）** | requirements-dev.txt 直接依赖全部 `==`；干净 venv `pip freeze` 生成 requirements-lock.txt；CI 改装 lock 文件 | 改动最小；本地/CI 完全可复现；传递依赖也锁死 | 升级需手动 bump + 回归测试 | ★★★ |
| B. 范围锁定 | `pyyaml~=6.0`、`fastapi~=0.141` 等 | patch 自动跟进 | 依赖仍会漂移，与"锁定"目标不符 | ★ |
| C. pyproject.toml + uv / pip-tools | 现代化依赖管理 | 最规范，带哈希校验可选 | 引入新工具链，改动最大 | 后续可选 |

## 锁定时的注意点

1. `filelock`、`uvicorn` 建议直接锁到最新（3.32.6 / 0.53.0），而不是沿用本地旧版；锁完跑全量测试 + CI 3.12/3.13 双版本验证。
2. **不要在当前 venv 直接 `pip freeze`** —— 会把约 20 个无关包锁进 lock 文件；新建干净 venv 装完 12 个直接依赖后再 freeze。
3. uvicorn 的用法是线程内 `uvicorn.Config(app, host, port, log_level)`，不用 reload/watchfiles → **普通 uvicorn 即可，不需要 `[standard]`**。
4. qbittorrent-api 用 CalVer 日期版本号（2026.8.1），跟随 qBittorrent 5.x API 语义演进；未来升级时重点回归 `test_qbmanager` / `test_snapshot_sync`（见 memory-bank/pitfalls.md）。
5. customtkinter 6.0.0 是刚发布的 6.x 大版本，当前 venv 已在用且托盘功能正常，锁定即可。
6. CI 的 checkout→v6、setup-python→v7 可顺手升级（本项目未用到 v7 移除的 `pip-install` 输入）。
7. `apm.lock.yaml`（gem-team 1.125.0 @ 026742a）已锁定，无需处理。

## 建议的目标 requirements-dev.txt（仅建议，未写入）

```
# 运行依赖 (锁定 @ 2026-09-15)
pyyaml==6.0.3
qbittorrent-api==2026.8.1
filelock==3.32.6
pystray==0.19.5
pillow==12.3.0
customtkinter==6.0.0
fastapi==0.141.1
uvicorn==0.53.0
ruamel.yaml==0.19.1
httpx==0.28.1

# 开发/测试依赖
pytest==9.1.1
pytest-cov==7.1.0
```

## 数据来源

- 本地：`.venv`（Windows, Python 3.12.0）`pip list --outdated` / `pip index versions`，快照于 2026-09-15。
- 远端：PyPI（pip index 实时查询）；GitHub Releases（actions/setup-python releases 页全文读取；actions/checkout v6、actions/upload-artifact v6 经搜索结果确认）。
