# 测试文件约定

> 摘要: 十条逐条约定 —— 从 docstring 清单、命名、平台固定, 到"不得产生真实系统副作用"与"不得依赖宿主环境能力"。
> 触发: 写测试, 加测试文件, 测试命名, 平台相关测试, monkeypatch, 副作用, 环境能力, 测试计划清单

### 每个测试文件头部 docstring 维护 "## 测试计划" 清单

- **触发**: 新增 / 删除测试用例。
- **判别**: 项目明文规定; README 也强调。
- **处置**: 新增测试**必须同步更新**对应文件头部的清单。

### 文件名与被测模块对应

- **触发**: 新建测试文件。
- **判别**: 约定是 `test_actions.py` ↔ `rules/actions.py`。
- **处置**: 一个模块可以有多个文件(如 `test_rules_core` / `test_rule_base` / `test_rule_engine` 拆分)。

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

### `test_web.py` 不只测 FastAPI 路由

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

### `test_impact.py` 直接测分级表而非被测端

- **触发**: 改分级表或新增配置项。
- **判别**: 它用真实 `Config()`(字段默认即全默认实例)构造新旧配置做 diff, 分级表外字段用 `SimpleNamespace` 替身
  (验证"未列出默认 L2"); 含 `_diff_flat` / `_diff_trackers` / `max_level` / `restart_required_paths` 直测。
- **处置**: **必须同步此文件** —— 新增配置项未补表 ⇒ 默认 L2; 分级错误会让热重载**静默不生效**或**误要求重启**。

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

### 测试期禁止真实系统副作用(两道会话级守卫)

- **触发**: 写任何可能触达系统副作用的路径。
- **判别**: 全量测试实测会**真的发系统通知**(本机抓到一条 Windows toast `auto-qb 已停止`)。
  **主犯**: `test_cli.py::test_main_qb_compat_error_clean_exit` 把 `manager` 设成 `MagicMock`,
  `notify_fatal(msg, manager.config.notify)` 拿到恒真 MagicMock ⇒ 守卫 `if not config or not config.enabled` 放行 ⇒
  真发 toast —— **已改为 mock `auto_qb.cli.notify_fatal` 并断言调用**。**从犯**: `PlatformChannel("linux")` 只是**换后端, 不等于不发**, `NotifyHandler` 后台线程照样真跑 `notify-send`。
  **第二道守卫 · AUMID 注册表键**: `PlatformChannel("win32")` 构造时会**真写**
  `HKCU\Software\Classes\AppUserModelId\AutoQB.UI` 且**写完不清理** —— 每跑一次测试就在用户注册表留一个持久键
  (与 `test_autostart_windows_registry` 的 Run 键不同, 那个在 `finally` 里自清理)。
- **处置**: **通用规则: 给被测代码传 `MagicMock` 当配置对象时, `if not cfg.xxx` 形式的守卫一律会放行**,
  后面接着真实系统副作用的路径必须在测试里**显式 mock**。
  安全网: `tests/conftest.py` 会话级夹具把通知器命令名(`notify-send` / `osascript` / `powershell` / `pwsh`)
  拦在 `subprocess.run` **之前**(抛 `OSError` = "机器上没装通知器"), `send()` 仍走失败分支返回 False;
  命令**构造**(`_build_*`)与非通知器子进程(`node --check` 等)不受影响。
  同一夹具只把 **AUMID 前缀**的 `CreateKeyEx` / `SetValueEx` 变成空操作(**静默成功, 不抛异常** ——
  否则 `_appid` 会回退成 `WINDOWS_TOAST_APPID_FALLBACK` 打乱断言), 其余注册表写入放行。
  回归: `test_notify.py::test_notify_real_send_blocked_under_pytest`。
  **副作用普查结论**(全量 1007 项实测): 外部进程 0; 文件删除 157 条全在 `C:\TEMP\pytest-of-*`(仓库内外均 0);
  建链 117 条全在临时目录; 网络监听全为 `127.0.0.1` 且自清理; 注册表仅剩 autostart Run 键(自清理)。
  ⚠ **排查方法论**: 诊断插件输出**不能写 stderr**(pytest 按用例捕获、**通过的用例直接丢弃** ⇒ 假阴性),
  必须写**文件**; 统计用 **ASCII 标记**(中文串 grep 会误报 0)。

### 测试不得依赖宿主环境能力

- **触发**: 断言"环境相关能力"(环境变量 / 符号链接权限 / 注册表 / 文件系统重定向)。
- **判别**: 不显式给定前提会出现"单跑通过、全量失败"或"换台机器就红"的**假失败**。
  已修两例: ①`test_notify_legacy_shortcut_cleanup` 补 `monkeypatch.setenv("APPDATA", ...)` ——
  `_legacy_shortcut_paths()` 在 `APPDATA` 缺失时返回 `[]`, 不设等于空跑、断言必失败;
  ②`test_api_fs_dirs_endpoint` 第⑤条补 `os.path.islink()` 判定 —— 沙箱 / 重定向层会让 `os.symlink` "成功"
  却落成**真实目录**(实测 `islink=False`), 此时不存在"逃逸链接", 断言无意义。
- **处置**: **判据: 单跑通过 + 全量失败, 或本机失败但逻辑上看不出问题 ⇒ 先查环境能力,
  排除环境之前不要动 `src/`**(这两例生产代码都是对的)。

### 测试期真实系统副作用有常驻守卫(`tests/sidefx.py`)

- **触发**: 加任何会触达真实副作用的代码。
- **判别**: 记账器全程记录七类真实副作用(`POPEN` 外部进程 / **`LAUNCH`** `os.startfile`·`os.system`·`webbrowser.open`·`utils._win_shell_open` /
  `REG`+`REGVAL` 注册表 / `FSDEL` 文件删除 / `SYMLINK` 建链 / `BIND` 监听 / **`CONNECT`** 出站连接),
  由会话级 autouse 夹具安装, **收尾按放行清单判定 —— 有越界项直接让本次 pytest 失败**(报告含分类计数与逐条明细)。
  **实测测试全部走回环、零外网连接。**
  台账在**每次** pytest 收尾打印(`pytest_terminal_summary`, 全量约 **1742 条 / 越界 0**)—— 没有越界时守卫本来完全静默,
  不打印就没人知道它在工作, 久了会被当死代码删掉。
  `LAUNCH` 单列是因为它们**不走 `subprocess`**(`POPEN` 抓不到)却同样会弹窗口(资源管理器 / 浏览器 / shell)——
  `utils.open_path()` 在 Windows 上走 `utils._win_shell_open`(Shell PIDL 长路径路线, **ctypes 直调 shell32**),
  该路线失败才退回 `os.startfile`; `/api/open-path` 能触达全部入口; 这类放行清单**为空**。
  **放行清单**(只有确实必需的副作用才登记): `node` 子进程(前端静态守阵的 `node --check`) /
  autostart 的 HKCU Run 键及其 `auto-qb` 值(用例在 `finally` 自清理) / 临时目录内的删除与建链 / 回环地址监听。
- **处置**: 判定策略本身有单测 `tests/test_sidefx.py`(含"临时目录判定必须剥掉 `\\?\` 前缀"这一回归点 ——
  普查时 157 条假阳性就栽在这)⇒ **改清单时同步**。
  ❌ **不要**为了让测试变绿而随意放宽清单: 先确认该副作用是测试必需的。
  要临时诊断可取用 `sidefx_recorder` 夹具(如断言某操作未产生副作用)。
