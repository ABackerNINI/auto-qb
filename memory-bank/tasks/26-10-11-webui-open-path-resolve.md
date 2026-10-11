# 26-10-11-webui-open-path-resolve — WEBUI 打开目标解析口径优化(文件优先 + 辅种组按单个 + 目录"进入")

**Status:** Done
**Added:** 2026-10-11
**Updated:** 2026-10-11 19:05
**Topics:** webui-open-path-resolve
**Summary:** 用户令「WEBUI 打开路径优化」四点 —— ①解析尝试顺序 = 文件(单文件种子) > root_path/content_path > save_path; ②打开后「选中条目」、多条目不选中; ③组内只含一个种子按单个处理; ④组内成员路径一致(辅种组, 都指向同一份文件)也按单个处理。后端 `/api/open-path` 解析单点重构(`_probe` + `_paths_consistent`), `open_path` 目录语义由"在父目录高亮"改"进入该目录"(Windows 新 `_win_shell_enter` 走 `ShellExecuteExW` + 目录 PIDL, 长路径安全); 6 个 Python 文件(2 源码 + 4 测试)改动, 全量结果见 kb.baseline。
**Refs:** memory-bank/testing/baselines/26-10-11-1905-webui-open-path-resolve.md,memory-bank/pitfalls/backend/qb-content-path-semantics.md,memory-bank/pitfalls/backend/windows-long-path.md,memory-bank/activeContext/26-10-05-2015-webui-open-path-fallback.md

## 原始请求

> WEBUI打开路径优化: 尝试顺序: 文件(单文件种子) > root_path/content_path > save_path, 要求打开后选中条目(多条目不选中); WEBUI中的组中如果只含一个种子也当作一个种子, 如果组中路径一致也当作一个种子, 比如辅种组, 其都指向同一份文件, 理应按单个处理

开工前用选项问清三处歧义, 用户答:

- 「条目/选中」= **文件管理器条目**(资源管理器里的高亮, 不是 WebUI 表格行选中)。
- 解析落到**目录**时 → **直接进入该文件夹**(显示其中内容), 不在父目录里高亮它。
- 组内「路径一致」判据 = **任一相同即可**(content_path **或** root_path 归一后全同)。

## 思考过程与决策

### 口径来源: qB 的 root_path / content_path 语义(源码确认, 非推断)

查 qBittorrent 源码 `torrent.h` 注释定死:

- `contentPath()` —— "root path for multifile torrents, absolute file path for singlefile torrents"(多文件=根目录, 单文件=该文件绝对路径)。
- `rootPath()` —— "absolute path of torrent file tree (**first common subfolder** of torrent files); empty string if torrent has no root folder"(**始终是目录**; 单文件落在 save_path、或条带根目录模式下为空串)。

⇒ 顺序「文件 > root_path/content_path > save_path」自洽: 先拿两个字段当**文件**探(命中即单文件种子 → 选中); 再当**目录**探(root_path 优先, 它比 content_path 更贴近"这份内容在哪"); 都不中回落 save_path。旧口径的根因坑(下载中 content_path 是**逻辑完成名**、磁盘上不存在)已在 2026-10-05 修过一次, 本次是把"只分文件/目录两段"细化为"字段 × 存在形态"的四段, 并补上组的语义。

### 组按单个处理的判据

组 key = `(规范化 save_path, 文件列表)` ⇒ save_path 与文件集**天然一致**, 所以"路径一致"只需补**内容路径**这一维:

- 组内**只一个成员** → 直接按单个种子走 `_probe`(旧口径会退回 save_path, 反而丢掉"单文件组能定位选中 / 多文件组进内容目录"的好处)。
- 组内成员 `content_path` / `root_path` **任一**归一后全同(空值不参与) → 视为"都指向同一份内容"(辅种组常态)。qB 报回的这两个字段仍可能逐成员有差异(老版本无 root_path / torrent 名称变动), 任一字段全同即可放心。
- 否则(确有多份不同内容) → 退回组 key 首元(save_path), 保持旧口径。

判据按用户拍板取"任一相同即可"。函数 `_paths_consistent` 对每个字段收成归一集合(丢空串), 任一集合 `len == 1` 即判一致。

### 目录: "进入" vs "高亮"(Windows 路线实测定案)

用户要"落到目录就进入"。但旧 `_win_shell_open` 走的 `SHOpenFolderAndSelectItems`, **实测对目录 pidl 与文件 pidl 行为一致 —— 都是"打开父窗口并选中该条目"**(旧注释"传目录 pidl = 打开该目录"与实测不符)。所以"进入目录"必须另找路线:

| 路线 | 结果 |
|---|---|
| `SHOpenFolderAndSelectItems(目录 pidl)` | ❌ 打开**父**窗口并在其中选中该目录(不是进入) |
| `os.startfile(目录)` / `explorer <目录>` | ✅ 进入, 但字符串路线对 >MAX_PATH 长路径一个抛错、一个**静默打开"桌面"** |
| **`ShellExecuteExW(fMask=SEE_MASK_INVOKEIDLIST, lpVerb="open", lpIDList=目录 pidl)`** | ✅ **选定方案**: 在 PIDL 上执行 `open` 默认动作 = 进入该目录, 且**长路径安全**(全程 PIDL, 不碰字符串长度) |

`SEE_MASK_INVOKEIDLIST`(0x0C)已含 `SEE_MASK_IDLIST`, 故用 PIDL 而非字符串。`_win_shell_enter` 失败时降级回 `_win_shell_open`(至少把用户带到该目录所在处), 再不行落字符串路线 —— 与既有"容错优先, 不抛错"契约一致。两函数共用新抽的 `_win_shell_with_pidl(path, use)`(反斜杠归一 / `\\?\` 剥除 / `CoInitializeEx` 配对 / `ILFree` 释放 / 派发闭包), 把 COM 与 PIDL 生命周期收成一处。

### 解析口径收成两个嵌套单点

`api_open_path` 内新增两个嵌套函数(仍在同一响应闭包, 不进模块级):

- `_probe(rec) -> (target, select)`: 文件(content, root) → 目录(root, content) → save_path 四段, UNDETERMINED 走 `_determinable` 语义化 404(不冒充"不存在")。
- `_paths_consistent(recs) -> bool`: 上面那条组判据。

组分支改 `manager.store.groups.get(key)`(None → 404), 单成员或一致 → `_probe(recs[0])`, 否则 `target = key[0] or ""`。`select` 终检块与 `common.open_path(target, select=select)` 保持逐字不变。

## 实现计划

1. `routes/fs.py::api_open_path` 抽出 `_probe` / `_paths_consistent`, 组分支按"单成员或一致"走代表成员 →
2. `infra/utils.py` 抽 `_win_shell_with_pidl`, `_win_shell_open` 改走它, 新增 `_win_shell_enter`; `open_path` 目录分支改"enter 优先, 失败降级 open" →
3. `tests/sidefx.py` LAUNCH 记账器纳入 `_win_shell_enter` →
4. 测试同步/新增(`test_web_hr.py` 端点 + `test_utils.py` PIDL 路线 + `test_web_longtail.py` + 头部测试计划清单) →
5. 收尾: `commands run test.full` + 基线切片 + 坑档/模块文档回写 + activeContext 切片 + `kb.index`/`kb.check`。

## 子任务状态表

| 子任务 | 状态 | 说明 |
|---|---|---|
| 解析口径改造(`_probe` + `_paths_consistent`) | Done | `routes/fs.py`; 组按单个处理的条件落 `len==1 or _paths_consistent` |
| Windows 目录改"进入" | Done | `infra/utils.py`; 新 `_win_shell_enter`(`ShellExecuteExW`+PIDL) + 共用 `_win_shell_with_pidl`; `open_path` 目录分支 enter 优先 |
| 守阵扩展 | Done | `tests/sidefx.py` LAUNCH 纳入 `_win_shell_enter`; `test_web_hr.py` 加 HA–HL + 4 组(k_a 单成员 / k_b content 一致 / k_d root 一致 / k_c 不一致); `test_utils.py` 加 `test_win_shell_enter_pidl_routes` + 改写 `_win_shell_open` 分支 |
| 测试计划清单同步 | Done | 4 个测试文件头部「## 测试计划」清单同步 |
| 收尾(闸门 + 协议产物) | Done | `commands run test.full` **3126 passed + 4 skipped / TOTAL 99%**; 基线切片 `26-10-11-1905-webui-open-path-resolve`; 坑档 + 模块文档回写; activeContext 切片更新; `kb.index` |

## 进度日志

- **2026-10-11 (实施)** — 用户令「WEBUI 打开路径优化」四点; 开工前问清三处歧义(条目=文件管理器高亮 / 目录=进入 / 组路径一致=任一相同)。先查 qBittorrent 源码 `torrent.h` 定死 `root_path`(始终目录, 空串=无根)与 `content_path`(单文件=文件绝对路径 / 多文件=根目录)语义, 确认"文件 > root_path/content_path > save_path"顺序自洽。改 `routes/fs.py` 解析口径(新 `_probe` / `_paths_consistent`)。
- **2026-10-11 (打开层)** — 实测确认 `SHOpenFolderAndSelectItems` 对目录 pidl 也是"在父目录选中" ⇒ 目录"进入"另立 `_win_shell_enter`(`ShellExecuteExW` + 目录 PIDL, 长路径安全)。抽 `_win_shell_with_pidl` 收 COM/PIDL 生命周期; `open_path` 目录分支改 enter 优先、`_win_shell_open` 降级。
- **2026-10-11 (守阵 + 闸门)** — `tests/sidefx.py` LAUNCH 纳入 `_win_shell_enter`; 端点测试加 HA–HL 与 4 个组用例; `test_utils.py` 加 `test_win_shell_enter_pidl_routes` 并改写既有 PIDL 分支断言; 4 个测试文件头部测试计划清单同步。`dev.fmt` 过; 全量 `commands run test.full` 全绿 / 0 failed / TOTAL 99%(数字与耗时采样见基线切片)。
- **2026-10-11 (回写)** — 坑档 `pitfalls/backend/qb-content-path-semantics.md` 补解析顺序 + 组判据 + enter/reveal 分工; 模块文档 `modules/webui-static-contract.md` open-path 行更新; activeContext 切片 `26-10-05-2015-webui-open-path-fallback.md`(同专题)更新「最后活动」与完成项; `kb.index` 重建。
