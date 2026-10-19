# 26-10-11-doc-links-strict-check — 坏链判据收紧(Windows 归一化) + 容器代理透传

**Status:** Done
**Added:** 2026-10-11
**Updated:** 2026-10-11
**Topics:** doc-links-strict-check
**Summary:** 用户贴 CI 单条红求助(`test_doc_links_are_not_broken`: `pitfalls/kb/index-archive-view.md:45 → ...`)。根因不是相对层级写错, 而是**省略号占位被当真链接** + **判据被 Windows 路径归一化骗过**: `(dir/rel).exists()` 在本机对 `kb/...` 返回 True(Win32 剥掉结尾点 ⇒ 塌成父目录), 于是坏链连过 doc.links 闸门 / test.quick 闸门 / 手工 test.full **三道本机防线**, 只在 ubuntu job 红。修法: ①坏链处改回准确字面量并裹行内代码; ②`check_doc_links.link_exists` 改**组件级 listdir 精确比对**(区分大小写 + 拒绝结尾点/空格), 守阵 `test_doc_links_rejects_windows_normalized_targets`(红验已做, 旧判据只报 3 条中的 1 条); ③顺带解开 `test.linux` 的网络死结 —— `linux_ci.py` 加**代理自动透传**(回环主机改写 `host.docker.internal` + 补 `--add-host` + `no_proxy` 恒并入回环), 守阵 `test_linux_ci.py`(红验拆两处即红)。两处根因与容器网络坑一并写进 `pitfalls/testing/patching.md`。实测数字见 `kb.baseline`。
**Refs:** memory-bank/pitfalls/testing/patching.md, memory-bank/testing/baselines/26-10-11-2315-doc-links-strict-check.md
## 原始请求

> 用户(2026-10-11): 「修复问题: FAILED tests/test_memory_bank.py::test_doc_links_are_not_broken - AssertionError: 相对链接坏链: memory-bank/pitfalls/kb/index-archive-view.md:45 → ...」

同一会话内随后三轮: ①「这个错误提交前为什么没拦下来」(问因); ②「按步骤1/2执行」(= 收紧判据 + 补跑 `test.linux`); ③「加代理透传, DoD, 然后提交」。

## 思考过程与决策

- **请求边界**: 首轮为执行任务(修坏链); 第二轮为**纯问答**(只查证作答, 未改文件/未入池); 第三、四轮为显式指派的执行任务 + 收尾 + 提交。
- **立档依据**: 阈值 2 命中 —— 改动 ≥3 个源文件(`check_doc_links.py` / `tests/test_memory_bank.py` / `linux_ci.py` + 新增 `test_linux_ci.py`)。立档前已查重(本 clone 与平级工作区均无 doc-links 专题)。
- **根因取证(为什么没拦下来)**: 不是闸门缺口(`(.my-commit-flow.toml)` 里 `match=["memory-bank/"]` 挂着 `check_doc_links --quiet`, `auto=true`; 该提交还改了 `tests/` ⇒ test.quick 闸门也会跑 pytest 里的同名守阵)。真因是**同一行判据在两套文件系统语义下答案相反**: `(kb / "...").exists()` 在 Windows 为 True(Win32 剥结尾点, 路径塌成 `kb/`), 而 `os.listdir(kb)` 里根本没有 `...`; 同族还有大小写不敏感(`kb/Cap.md` 命中 `cap.md`)。方向单一(本机只会把"坏"判成"好")⇒ 本机绿只是上界。
- **取证纪律**: 用严格口径(组件级 listdir)探针复扫 `b447c7fa` 快照 ⇒ **恰好 1 处**, 与 CI 报的一字不差; 扫当前树 0 处。❗写探针时自己也踩了同一条坑一次 —— `os.path.abspath()` / `resolve()` 同样做 Win32 归一(`abspath(".../kb/...")` 直接变成 `.../kb`), 于是探针首版报假绿; 严格判据必须完全不碰这两个 API。
- **修法取舍**: 不把省略号"美化"成真链接(那会篡改对历史字面量的引述), 而是照抄原文并裹行内代码(检查器 `CODE_RE` 只豁免反引号内 —— 这正是它的既有用途); 判据侧则彻底改为 Linux 口径, 让检查器**在本机就能判红**。
- **`linux_ci.py` 为什么只加自动透传、不加开关**: 宿主代理写在回环地址上是常态, 容器里那是容器自己 ⇒ 透传必须同时**改写主机**(否则传了也没用); 而注了代理必须**放行回环**, 否则 `urllib` 把 `127.0.0.1` 的请求也交给代理, 回环端点用例集体假红(实测)。两条都是"不这么做必错"的默认正确解, 不需要用户开关; 守阵钉住即可。
- **红验两处**: ①`link_exists` 退回 `.exists()` ⇒ 新守阵当场红且**只报 3 条中的 1 条**(漏 `kb/...` 与 `kb/Cap.md`, 正是两类漏检现场); ②`rewrite_proxy` 去改写 / `no_proxy` 不并入回环 ⇒ `test_linux_ci.py` 两条对应用例红。

## 实现计划

| 步 | 内容 | 状态 |
| --- | --- | --- |
| S1 | 修坏链: 照抄原字面量 + 裹行内代码; 坑档补"省略号占位"判据 | Done |
| S2 | 判据收紧: `link_exists` 组件级精确比对 + 守阵 + 头注释 | Done |
| S3 | 红验(旧判据必红) → 复位 → 复绿 | Done |
| S4 | `linux_ci.py` 代理透传 + `test_linux_ci.py` 守阵 + 红验 | Done |
| S5 | 文档回写: `config.toml` note / `patching.md` 两处 | Done |
| S6 | DoD: 档案 + 切片 + 基线切片 + `kb.index` / `kb.check` | Done |
| S7 | `test.pkg` + `test.full` + `test.linux` 三侧实测 | Done |
| S8 | 提交(`ship.commit`: 闸门 + 暂存 + 提交 + 同步 + 推 Gitea/Gitee) | Done |

## 子任务状态表

| 子任务 | 状态 | 说明 |
| --- | --- | --- |
| 坏链修复(原 CI 红) | Done | `pitfalls/kb/index-archive-view.md` 的 `[history](...)` 改回 `[implemented-webui-history.md](implemented-webui-history.md)` 并裹行内代码 |
| 判据收紧 | Done | `check_doc_links.link_exists` + `_entries` + `_is_literal_name`; 旧判据不再可能把坏链判成好 |
| 链接守阵 | Done | `test_doc_links_rejects_windows_normalized_targets`(夹具含 `..` 导航与行内代码两条反向钉) |
| 容器代理透传 | Done | `container_env` / `rewrite_proxy`; `no_proxy` 恒并入回环; 打印透传行 |
| 容器守阵 | Done | `.commands/test/scripts/test_linux_ci.py`(5 条, 含 `--safety` 自认) |
| 坑档回写 | Done | `pitfalls/testing/patching.md`: ⑥ 新节 + 判别法四类升五类 + 容器网络两坑 |
| 三侧实测 | Done | Windows `test.full` / 包内 `test.pkg` / 容器 `test.linux`(数字见基线切片) |

## 进度日志

### 2026-10-11 R0 — 修坏链 + 定位"为什么没拦下来"

- 开工同步 `d186d603→9b0d6f41`。定位坏链为省略号占位; 从 `b447c7fa^` 取回压缩前 41 行原文, 确认字面量是 `[implemented-webui-history.md](implemented-webui-history.md)`。修完 `doc.links` 绿、`test.full` 绿。
- 独立追因轮: 逐条排除"闸门缺口"假设, 用严格探针复扫快照取证(1 处) —— 见「思考过程与决策」。

### 2026-10-11 R1 — 判据收紧 + 守阵 + 红验

- `link_exists` 落地; 新增守阵并同步测试文件头「## 测试计划」; 红验后复位。
- 坑档 ⑥ 节与判别法五类; `kb.index` 重建。

### 2026-10-11 R2 — Linux 侧复现(含两轮环境假红)

- `commands run test.linux` 首跑**没进到测试**即挂: 容器内 `uv` 直连 PyPI 被墙。诊断出容器可用出口(宿主代理 `host.docker.internal:4085` / 清华镜像通, 直连不通)。
- 手工等价容器跑出第一份结果: 原 CI 红已消失, 但 6 failed + 2 errors —— 定位为**注入代理未放行回环**所致的环境假红。
- 补 `no_proxy` 后容器全绿; 取证对账: 原 CI 的 skip 数与 Linux 侧一致 ⇒ 当初红的确实是 ubuntu job。

### 2026-10-11 R3 — 代理透传 + 收尾 + 提交

- `linux_ci.py` 自动透传落地(回环改写 + `--add-host` + `no_proxy` 并入), `test_linux_ci.py` 5 条守阵; 红验拆两处即红。
- `config.toml` note 与 `patching.md`「已内建」回写; 真跑 `test.linux` 复验新代码路径。
- DoD: 本档案 + 切片 + 基线切片 + 索引重建; 三侧实测后提交。
