# 26-09-25-webui-log-level-filter — 运行日志按等级查看恒空(生产格式无方括号)

**Status:** Done
**Added:** 2026-09-25
**Updated:** 2026-09-25
**Summary:** 用户报"新版设置里运行日志选 WARNING 显示『日志文件暂无内容』"。根因: `/api/log` 的等级过滤写死字面量 `f"[{lv}" in ln`, 锚死**默认格式**的方括号; 而 `log.format` 用户可配, 生产 `config.yml` 是 `%(asctime)s - %(levelname)s - %(message)s`(无方括号)⇒ 选任何等级恒空, 且与"确实没有该等级日志"完全同形(不报错、不返回 None)。修法: 新增 `infra/logging.py::filter_log_lines()` —— 按**配置的 format 反推** `%(levelname)s` 的位置编成正则(其余字段当"到下一个字面量为止"的通配符), 按**记录**取舍(多行 traceback 续行跟随上一条); 两种"筛不了"(格式无等级字段 / 已存行与当前格式不符)回**全部行 + `note` 提示语**, 不给静默空结果。后端单点修复同时治好经典设置页与新版 Console Hub 两处; 前端只加 `logs.note` 提示条(两套 UI 成对改 + 共用 CSS)。新增 7 条用例并两处红验(旧实现下 7 条全红); 真机流水线端到端复验(WARNING 1 行 / ERROR 连整段 traceback 5 行); 冒烟 82 项 0 失败 + 专项浏览器验证 18 项 0 失败(双 UI × 双设置形态 × 双格式)。**提交前与主线 M2/M3 五笔(HR 取数通道+判定联动)合流**(「出补丁 → ff-only → --3way 施回」, 5 个知识库文件冲突取并集), 合流后全量 **1527 collected: 1526 passed + 1 skipped** / TOTAL 91% / sidefx 越界 0。
**Topics:** webui-log-level-filter

## 原始请求

> 修复BUG: 新版设置中运行日志按等级查看失败, 选"WARNING"级显示"日志文件暂无内容"

## 思考过程与决策

### 根因: 字面量锚点 vs 用户可配的 format

`server/routes/system.py` 原实现:

```python
lv = (level or "").strip().upper()
if lv:
    all_lines = [ln for ln in all_lines if f"[{lv}" in ln]
```

`"[WARNING"` 只在默认格式 `%(asctime)s [%(levelname)s] %(name)s: %(message)s` 下存在;
生产 `config.yml` 的 `log.format` 是 `%(asctime)s - %(levelname)s - %(message)s`, 渲染出的行里
**没有方括号** ⇒ 过滤恒空。前端(两套 UI 的日志章节)拿到空列表就走"日志文件暂无内容"占位 ——
用户看到的是"没有 WARNING 日志", 实际是"筛不了"。

### 为什么既有测试没抓住(摆设断言)

`test_api_log_endpoint` 手写三行 `[INFO]/[WARNING]/[ERROR]` 语料, 而它用的 `web_env` 替身里
`logging.format` 是 **`%(message)s`**(没有等级字段)—— 配置从来没被读到, 被测的只是
"字面量在不在行里"。旧实现下绿、新实现下反而红; 真机 format 一换功能恒空, 测试照样绿。
⇒ 输入样本必须**由被测配置生成**(`_log_lines(fmt, recs)` 走 `logging.Formatter`), 且**显式设** format。
详见 `pitfalls/testing/assertions.md`(新条目)与 `pitfalls/backend/format-driven-parse.md`(新建主题)。

### 方案取舍

1. **按 format 反推正则**(采用) vs **词边界搜等级名**(否决): 后者会被消息正文误伤
   (日志消息完全可能提到 "WARNING"), 而且同样回答不了"格式里没有等级字段"的情形。
2. **正则只定位等级名, 不还原字段值**: `%(levelname)s` 编成 `(?P<level>[A-Za-z]+) *`, 其余字段当
   "到下一个字面量为止"的通配符(`message` 用 `.*` 吞到行尾)。两条实现要点都实测验证过:
   - **字面量空格不放宽成 `\s*`** —— 字面量是字段间的分隔证据; 放宽后 `%(name)s %(levelname)s` 的
     `auto_qb.core INFO 启动` 会把等级解析成 `core`(锚定版才解析出 `INFO`)。
   - **吸收字段宽度补的空格** —— `%(levelname)-8s` 在等级名后补空格, 漏了则该格式一行都对不上
     (本轮实测踩到后补上)。右对齐 `%(levelname)8s` 定位不到, 走"筛不了"提示, 不静默。
3. **筛不了就直说**: 格式无等级字段 / 一行都对不上(改了 format、文件里还是旧格式历史行)两种情形
   回**全部行 + `note`**, 前端显示提示条 —— "筛选失效"与"确实没有"在界面上不再同形。
4. **多行记录按记录取舍**: 全仓 13 处 `exc_info=True`, traceback 折行后每行都不带等级标记;
   逐行独立判会让筛 ERROR 只剩标题行。解析得出的行开启新记录、解析不出的行跟随上一条的取舍。
5. **修在后端单点**: 两个日志章节(经典 `cfg.activeGroup==='__logs'` / 新版 `hub.view==='__logs'`)
   共用同一个 `loadLogs()` 与 `/api/log`, 后端一修两处同愈; 前端只加 `note` 展示(两套成对改)。

### 范围守恒

- `/api/log` 的 passkey 泄露面(issue 26-09-21-1408, P2)是**相邻既有问题**, 本轮未动。
- `logs.loaded` 缓存(进过一次日志页后切等级才重新拉)是既有设计, 未动。

## 实现计划

| # | 文件 | 改动 |
|---|---|---|
| 1 | `src/auto_qb/infra/logging.py` | 新增 `_level_line_re()`(format→正则, lru_cache)与 `filter_log_lines()`(含两条 `NOTE_*` 提示语) |
| 2 | `src/auto_qb/webui/server/routes/system.py` | `/api/log` 改用 `filter_log_lines`, 响应加 `note` |
| 3 | `shared/app.js` | `logs` 状态加 `note: ""`(data 初值 + 退出登录复位两处) |
| 4 | `shared/dialogs.js` | `loadLogs()` 接 `r.note` |
| 5 | `atlas/prism index.html` | 两套 UI × 经典/新版两处日志章节加 `<p v-if="logs.note" class="logs-note">` |
| 6 | `shared/console_hub.css` | `.logs-note` 一条(两套 UI 都引本文件, 单点覆盖四处) |
| 7 | `tests/test_logging.py` | +4 条纯函数用例(格式形状矩阵 / 多行记录 / 提示语 / 字段宽度与 `%%` 变体) |
| 8 | `tests/test_web.py` | 重写 `test_api_log_endpoint` + 新增 3 条端点用例(生产格式 / 多行记录 / note) |

## 子任务状态表

| 子任务 | 状态 |
|---|---|
| 定位根因(字面量锚点 × 生产 format) | Done |
| `filter_log_lines` + format 反推正则(两条实现要点实测) | Done |
| `/api/log` 接入 + `note` 字段 | Done |
| 双 UI × 双形态 `note` 提示条 + 共用 CSS | Done |
| 用例重写/新增(样本由配置生成) | Done |
| 红验(临时还原旧实现) | Done(7 条全红) |
| 真机流水线端到端复验 | Done |
| 冒烟 + 专项浏览器验证 | Done(82/0 + 18/0) |
| 全量测试 + 基线回写 | Done |
| 知识库回写(pitfalls×3 / baseline / archive) | Done |
| 与主线 M2/M3 五笔合流(补丁 → ff-only → 3way 施回 + 5 冲突并集) | Done |
| 提交 / 推送 | 待用户显式指令("提交") |

## 待用户处置

1. **提交 / 推送**: 本轮改动未入库(按 AGENTS.md, "提交"才授权 commit+push)。改动 9 个源/测文件 + 5 个知识库文件, 建议单独一笔 `🐛`。

## 进度日志

- 2026-09-25 00:3x 开工。`my-commit-flow.sync`: 主线前进 1 commit(`c3088c3` 新版设置"常规"改名), 工作区干净
  ⇒ `merge --ff-only` 快进后开工(先读 `pitfalls/git/_index.md` + `sync-pull.md`)。
- 定位: 前端两套 UI 的等级下拉都正确传 `level`, 问题在后端过滤; 用 `logging.Formatter` 复现
  "生产 format 渲染的行不含 `[WARNING`"。
- 实现 1–8 项。中途发现测试替身 format 是 `%(message)s` ⇒ 旧用例是摆设断言, 重写时样本一律由配置渲染。
- **红验**: 把 `filter_log_lines` 临时换成旧字面量实现 ⇒ **7 条新用例全红**(含生产格式用例), 复原后全绿。
  `test_api_log_endpoint` 在旧实现下也绿 —— 正是它此前漏报的原因。
- 端到端(真机流水线, 一次性脚本不入库): `setup_logging` 按生产 `config.yml` 的 format/level 落盘 +
  `exc_info=True` 真实 traceback ⇒ `filter_log_lines`: 全部 8 行 / INFO 2 / WARNING 1 / **ERROR 5(整段栈保留)**。
- 冒烟: `ui_harness.py`(8137, 8099 被其它 clone 占用) + `ui_smoke.cjs` ⇒ **82 项 0 失败**(atlas 41 + prism 41),
  无 console.error / pageerror。
- 专项浏览器验证(一次性脚本 + 临时服务, 双端口双格式): 两 UI × 新版/经典 × 生产格式/无等级字段格式
  ⇒ **18 项 0 失败**; 截图确认提示条与日志正文版式正常(dark 主题下琥珀色提示条, 不挤压日志区)。
- 全量: `commands run test.full` ⇒ **2 failed**(`test_commands_engine.py` 两条 GBK 码页守阵)。
  按 `pitfalls/testing/patching.md` 判定为**本工具 shell 注入 `PYTHONUTF8=1` 的已知假红**(非本次改动),
  `env -u PYTHONUTF8 -u PYTHONIOENCODING` 后 **1383 passed + 1 skipped / 0 failed**。
- 知识库回写: 新建 `pitfalls/backend/format-driven-parse.md`(扩展枚举, HTML 抓取主题盖不住"配置驱动解析");
  `testing/assertions.md` 加"样本与配置脱节"条目; `testing/tmpdir.md` 复发 2(见下); 基线数字回写
  `testing/baseline.md` + `baseline-history.md`。
- ⚠ **tmpdir 坑复发 2**: 手工跑子集时把闸门的 cmd.exe 写法(`set "TMPDIR=..." &&`)照搬进 Git Bash,
  bash 里 `set` 是位置参数内建 ⇒ TMPDIR 没导出 ⇒ pytest 回落 `H:\Temp` ⇒ 收尾 `PermissionError … pytest-current`。
  **为什么没命中**: AGENTS.md「命令」节写明"`TMPDIR` 已内置在 `test.*` 里, 不要再手工加前缀", 读了没照做。
  另记一条实操: `test.one -- '<路径> -k "<表达式>"'` 必须**整串加引号**, 拆开传参会把 `-k` 的空格当分隔
  (实测报 "file or directory not found: or")。
- 环境坑(非复发, 判据按已记条目走通): `test_commands_engine.py` 两条恒红 = 工具 shell 注入
  `PYTHONUTF8=1`(`pitfalls/testing/patching.md`), `env -u` 后转绿; 未改那些断言(环境差异不是代码缺陷)。
- 行尾纪律: 新建文件 Write 工具落纯 LF, 收尾统一按检出态归一 CRLF 并逐个复核
  `bytes.count(b"\n") == bytes.count(b"\r\n")`(判据见 `pitfalls/kb/cap-counting.md`)。
- 2026-09-25 01:0x **收到「提交」指令, 提交前发现主线前进 5 笔**(`5c6e3d3` M2 取数通道 … `2c04a7a` M3 判定联动,
  77 文件 / +7025 −459, 收集数到 1520)。按「移出改动 → `merge --ff-only` → 施回改动」同步:
  `git diff --output` 出补丁(51,107 字节)+ 3 个新建文件另存, `cp -a .git` 备份到 R:/Temp 后
  `git restore --source=HEAD -- .` 清树, 快进到 `2c04a7a`, 再 `git apply --3way --ignore-whitespace` 施回。
  **代码文件 12 个全部干净施回**(logging.py / system.py / 双 index.html / app.js / console_hub.css /
  dialogs.js / test_logging.py / test_web.py / tmpdir.md); 5 个知识库文件冲突:
  两个生成索引(`pitfalls/*/_index.md`)重跑 `kb.index`; `assertions.md` 触发词行取并集(双方各加一词条);
  `baseline.md` 当前基线块**两侧都重写了同一段** ⇒ 以合流后重测数字为准、双方增量说明并列保留;
  `baseline-history.md` 对方已**轮转**(触顶 24,000 外迁 17 条)⇒ 取对方轮转版 + 我的条目置顶
  (注明"与 M2/M3 并行开发, 合流前旧基实测"), 我方重复的旧编号头(`1375 → 1377`, 对方已改为 `1466 → 1468`)弃用。
  合流后全量 **1526 passed + 1 skipped** / TOTAL 91%(10581 / 779 / 3512 / 310~311) / sidefx 2469 / 越界 0。
