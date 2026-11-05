# 测试文件约定

> 摘要: 十条逐条约定 —— 从 docstring 清单、命名、平台固定, 到"不得产生真实系统副作用"与"不得依赖宿主环境能力"。
> 触发: 写测试, 加测试文件, 测试命名, 平台相关测试, monkeypatch, 副作用, 环境能力, 测试计划清单

### 每个测试文件头部 docstring 维护 "## 测试计划" 清单

- **触发**: 新增 / 删除测试用例。
- **判别**: 项目明文规定; README 也强调。
- **处置**: 新增测试**必须同步更新**对应文件头部的清单。

### 大测试文件的 move-only 拆分

- **触发**: 单个测试文件过长, 要拆成多文件。
- **判别**: 只有「搬」没有「改」才叫 move-only —— 判据是**模块级界定**(`def` / `class` / 赋值)逐字不变 +
  **测试函数名集合**双向一致; 任一测试函数名消失或新增即越界。
- **处置**:
  - **辅助归属按依赖闭包定**: 被恰好一个桶引用的辅助内联进该桶; 多桶共用的提升为支撑模块。
  - **支撑模块不得以 `test_` 开头**(pytest 只收 `test_*.py`), 用 `<域>_support.py` / `webui_static_scan_{common,css,js}.py` 这类名字;
    支撑模块之间按无环分层, 常量集中一处。
  - **头部「## 测试计划」清单按桶切分**: 条目只在「锚点测试名属于当前桶」时保留原文; 跨桶共用条目在其余桶写派生行
    指向归属文件 —— 直接复制或整体重写会让 `test_test_plan_docstring_guard.py::test_repo_plan_matches_defs`
    同时报「未登记」与「ghost 条目」。
  - **文件仍留在 `tests/` 下**: 基于 `__file__` 推导仓库根 / `ROOT` 常量的用例不受目录深度变化影响。
  - 拆分后仍超千行的桶**不在同一轮继续下拆**, 登记到计划「新桶超阈值 · 后续排期」留待后续排期
    (R2 起口径; 下拆仍按同一 move-only 机制, 只搬不改)。
- **实证**: 2026-11-03 R1 拆了 10 个大型测试文件, R2 拆了其余 25 个(90 个分桶 + 20 个 support);
  2 个超千行新桶按上条口径排期。档案 `memory-bank/tasks/26-11-03-test-big-file-split.md`,
  计划 `memory-bank/plans/26-11-02-2342-plan-big-file-split.html`。

### 文件名与被测模块对应

- **触发**: 新建测试文件。
- **判别**: 约定是 `test_actions.py` ↔ `rules/actions.py`。
- **处置**: 一个模块可以有多个文件(如 `test_rules_core` / `test_rule_base` / `test_rule_engine` 拆分)。
  超大测试文件的拆分实操见下方「大测试文件的 move-only 拆分」。

### 粒度小而多, 名字用中文 / 英文短语描述场景

- **触发**: 拆用例。
- **判别**: 当前规模见 `commands run kb.baseline`(Windows 收集数)。
- **处置**: 保持"小而多", 不要写成一个大用例。

### 平台相关测试必须以 `monkeypatch` 固定平台

- **触发**: 写任何涉及平台分支的测试。
- **判别**: GitHub Actions 跑在 **Linux**, 而本项目以 **Windows** 为运行环境。
  ❗**判据是"本地全量绿"不算数**: 2026-09-19 Linux CI 一次红了 3 条, 全是"Windows 全绿 / Linux 全红"型 ——
  ①`shutil.rmtree` 在 POSIX 走 **fd 版实现**(传纯文件名 + `dir_fd`), 副作用记账器记到裸名字被判越界(76 条假阳性);
  ②`PlatformChannel("win32")` 里 `import winreg` 在 Linux 抛 `ModuleNotFoundError`, 而调用方只 catch `OSError`;
  ③`connect()` 真实连 `127.0.0.1:16585`, 是否抛异常取决于机器环境。
- **处置**: 测试主体行为的是"**平台逻辑**"而非"当前真实平台", 一律**显式 monkeypatch**, 不要依赖运行环境。
  纯 Windows 行为(如长路径 `\\?\` 前缀)若直接断言, 在 Linux CI 上**必失败**(实测 3 例):
  `test_utils.py` 的 `test_add_long_path_prefix_for_win/unc/already_prefixed` 用
  `monkeypatch.setattr(sys, "platform", "win32")` 模拟 Windows。
  修法与判别法见 [../pitfalls/testing/patching.md](../pitfalls/testing/patching.md); 本机复现 Linux 的办法同见该文。

### 跨平台断言规范(平台容差单点, flaky 治理计划 26-11-05-0118 S6/D6)

- **触发**: 写计时断言 / 平台分支测试 / 平台相关 skipif。
- **常量单点**: 平台相关容差一律 import `tests/platform_tolerance.py`, 禁手写刻度魔数 ——
  `WIN_TIMER_TICK_S`(Windows 等待原语按 15.6ms 定时器刻度取整)与
  `SLEEP_LOWER_MARGIN_S`(挂钟**下界**断言余量, >= 2 tick = 31.2ms)。
  用法: `assert elapsed >= nominal - SLEEP_LOWER_MARGIN_S`。
- **下界留余量、上界不加对称余量**: 下界假红来自刻度取整(50ms 等待实测提前到 46.8ms);
  上界假红来自负载/CI 抢占, 加余量治不了 —— 性能上界优先 `time.process_time`
  (CPU 时间), 挂钟上界放宽到不可撞线。判别与实证:
  [../pitfalls/testing/timing-tolerance.md](../pitfalls/testing/timing-tolerance.md)。
- **平台相关 skipif 强制带理由 + 负责人**: reason 写明"该断言依赖的语义在另一侧为何不成立",
  装饰器行范围内加 `# owner: <名>`; skip 的处置(issue 入池)按
  [flaky-ledger.md](flaky-ledger.md)「巡检约定」节。守阵:
  `tests/test_platform_tolerance_guards.py::test_repo_skipif_all_have_reason_and_owner`
  (缺任一即红, 合成源红验内建)。
- **禁写死仅一侧成立的形状**: 前缀切片长度 / 路径分隔符 / 大小写折叠语义 / 仅一侧存在的
  模块常量 —— 按平台分支分别断言, 不写"两侧共用的单一期望值"
  (实证: [../pitfalls/testing/ci-only-guard.md](../pitfalls/testing/ci-only-guard.md))。

### `test_web_*.py` 不只测 FastAPI 路由

- **触发**: 找 WEB 功能的测试 / 加 WEB 功能。
- **判别**: 它还覆盖 **manager 侧** —— 搜索索引构建与搜索、`_drain_web_commands` 各命令执行(含未知命令 / 异常的容错)、
  `ensure_group_view` / `ensure_group_state` 脏重建与版本自增、`_state_kind` 状态分类、
  `build_group_view` 字段(含单种子大小 / 总大小 / 标签 / 分类 / 保存路径 / **组级 `added_on` 取组内最大值** /
  **组级 `hr_triggered` 与 `hr_pending` 计数**)、**错误原因展示**(TASK015: `_error_reason` 的
  missingFiles→"文件丢失" / error→tracker `msg` / 非错误→空串; `refresh_error_reasons` 的预算与 TTL 限额、
  虚拟 tracker 条目跳过、离开错误态清空缓存、qB 断连跳过且不清值)、
  **HR 展示字段**(`hr_tag` / `hr_tag_done` 文本 + `hr_triggered` / `hr_satisfied` 布尔 + `hr_req_time` / `hr_req_ratio` 阈值)、
  `apply_new_config` 分级应用。
  另有: 鉴权 / API / 命令入队 / 设置读写 / `?rid=` 视图版本门控 / **静态资源 no-cache 响应头** /
  **前端静态资源守阵** `test_frontend_static_bundle_health`(冲突标记残留、JS 注释孤儿续行、
  **装了 node 时跑 `node --check` 真语法校验**、CSS 规则块漏闭合、`<transition>` 吞弹窗、
  模板引用的静态资源是否存在 —— 这类问题会让整页只剩背景色或整块功能静默失效)。
- **处置**: **找 WEB 功能的测试先看这个文件**。
  `test_speed_curve.py` 另覆盖 **`_traffic_view` 只读快照**的各分支
  (disabled / ok 含 periods 与 target+actual / dry_run 无 actual / manual 原因 / stale 的两种原因码)。

### `test_sync.py` 专测增量同步层

- **触发**: 改 `torrents.py` 的同步层或 `_refresh_torrents`。
- **判别**: 它覆盖 `TorrentRecord.apply_delta`(只遍历 patch 字段 / 变化字段集 / 量化 / 双通道源 / `_raw` 兜底 /
  `state_enum` 缓存)、`TorrentStore.apply_sync`(首轮全量 / 增量只改变化记录 / 无变化零成本 / 增删 / 全量剪除 /
  待报删除 / 降级 / 异常 / `reset_sync`), 以及 QbManager 接线(增量轮不做 schema 校验、变化集与冲突脏组)。
- **处置**: 改同步层**必须同步此文件**。

### `test_impact.py` 直接测变更影响分析(diff + R 闸)

- **触发**: 改 `config/impact.py`(diff / R 级重启闸)或新增配置顶层段。
- **判别**: 级别表(L0/L1/L2)退役后它测两件事 —— `diff_config_impacts` 做**顶层段级** diff
  (粒度 = 段, 段内嵌套不展开; 一侧多出/独有的段按变更报告, **无「默认 L2」兜底**; 变更按段名排序),
  以及 `restart_required_paths` 的 R 闸(`RESTART_SECTIONS` = state_file / data_dir / fs, 命中即拒绝热应用提示重启)。
- **处置**: **必须同步此文件** —— 新增顶层段必须落到「某模块 `sections()` 认领 or `KERNEL_SECTIONS` or
  `RESTART_SECTIONS`」之一(守阵 `test_modules_p6`), 段变了之后做什么由认领模块 apply 自判。

### `test_memory_bank.py` 守知识库结构(不覆盖 src)

- **触发**: 改 `memory-bank/` 结构或会话协议。
- **判别**: 它守 —— `_index.md` 登记项 ↔ `tasks/*.md` **双向一致** /
  文件名 `YY-MM-DD-<slug>.md`(**兼容期内也接受旧 `TASKnnn-<slug>.md`**)/ 五个必备章节齐全 /
  档案 `**Status:**` 与索引分区一致 / 索引保留四个状态分区 /
  **档案 slug 唯一 + 索引同一 ID 只登记一次**(并行工作区各自立档会产出重复档案与重复条目, 而 dict 式解析会**静默覆盖**)/
  **`activeContext.md` 不得出现 `^- 2026-` 流水账纪要行** / skill 载体存在且 `AGENTS.md` 与
  `copilot-instructions.md` 均声明立档阈值并指向 skill;
  另有 2026-09-22 起的一组**知识库目录化守卫**(索引 == 生成结果 / 索引↔目录双向一致 / 三行头元数据 / cap 策略 /
  类名与文件名 / 无孤儿索引 / 存根合法 / pitfalls 条目三字段 / skill 脚本可 import), 检查器在
  `.agents/skills/memory-bank/scripts/check_kb_structure.py`, **进程内 import**(本项目测试禁止起子进程)。
- **处置**: 改结构**必须同步此文件**(红绿验证过: 幽灵任务与纪要回流两类违例都会失败)。

### 测试期禁止真实系统副作用(会话级守卫 + 常驻 sidefx)

> 已外迁: 两道会话级守卫(通知 / AUMID 注册表键)与常驻 `tests/sidefx.py` 记账器(七类副作用 / 放行清单 / 临时根缓存失效)的完整判据与处置 → [attachments/file-conventions-details.md](attachments/file-conventions-details.md)。

### 测试不得依赖宿主环境能力

- **触发**: 断言"环境相关能力"(环境变量 / 符号链接权限 / 注册表 / 文件系统重定向)。
- **判别**: 不显式给定前提会出现"单跑通过、全量失败"或"换台机器就红"的**假失败**。
  已修三例: ①`test_notify_legacy_shortcut_cleanup` 补 `monkeypatch.setenv("APPDATA", ...)` ——
  `_legacy_shortcut_paths()` 在 `APPDATA` 缺失时返回 `[]`, 不设等于空跑、断言必失败;
  ②`test_api_fs_dirs_endpoint` 第⑤条补 `os.path.islink()` 判定 —— 沙箱 / 重定向层会让 `os.symlink` "成功"
  却落成**真实目录**(实测 `islink=False`), 此时不存在"逃逸链接", 断言无意义;
  ③`test_file_access._dir_symlink_or_skip` 建链后补 `os.path.islink()` 复核(issue 26-09-29-2031) ——
  旧实现只 catch `OSError`, 本机 `os.symlink` 是**假成功**: 不抛异常但 `os.path.lexists(link)` 为 False
  (**连普通目录都没建出来**, 比 ② 的"落成真实目录"更彻底), 两条端到端用例因此 **failed 而非 skip**,
  直接卡死 `ship.commit` 的 `test.quick` 闸门。
  ⚠ **建链类 helper 的通用形态**: `try: os.symlink(...) except OSError: skip` **不够** ——
  异常路径之外必须再判 `os.path.islink(link)`; 该 skip 的必须 skip, 不能落成断言红。
- **处置**: **判据: 单跑通过 + 全量失败, 或本机失败但逻辑上看不出问题 ⇒ 先查环境能力,
  排除环境之前不要动 `src/`**(这三例生产代码都是对的)。

