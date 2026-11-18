# commands run 透传 e2e 参数需三连 --(引擎 argparse / 引擎 _extra / 任务脚本手拆各吃一个)

> 摘要: `commands run test.linux-e2e` 想只跑单个 spec / 加 playwright 过滤参数时, 一层 `--` 不够 —— 三个 `--` 由引擎 argparse(REMAINDER)、引擎 `_extra` 前导剥离、任务脚本 `_parse_args` 手写拆分各吃一个, playwright 一层不吃; 且 `--grep` 值含 `|` 在引擎 `shell=True` 拼串处(任务脚本之前)就被 /bin/sh 当管道解析。
> 触发: commands run 透传, 三连 --, test.linux-e2e 单 spec, e2e 单用例重跑, playwright 透传参数, --grep 不生效, grep 竖线, -- -- --, --full 透传, 任务自有旗标
**Refs:** memory-bank/tasks/26-11-14-webui-flux-chip-glow-ancestor-clip.md

## 本篇只回答

`commands run <script 型任务>` 往任务脚本透传参数时的层数坑: 三个 `--` 分别被谁吃、症状怎么按被吃位置分辨、过滤正则里哪些字符会在引擎 /bin/sh 拼串处被吃掉。task id 的查找与收录协议见 commands skill, 不在本篇。

### e2e 单 spec / 过滤参数透传, 一层 `--` 到不了 playwright (2026-11-13 实测)

- **触发**: 对 `commands run test.linux-e2e` 这类 script 型任务想「只重跑一个 spec」或加 `--grep`/`-t` 过滤, 按习惯只写一层 `--`(`commands run test.linux-e2e -- spec.mjs`)。三个 `--` 的去向(源码核实 2026-11-14): ① 引擎 argparse(`run.py` 的 `extra nargs=REMAINDER`)吃第 1 个; ② 引擎 `_extra`(`run.py:209`)对 REMAINDER 结果做**前导剥离**吃第 2 个; ③ 任务脚本 `linux_e2e.py::_parse_args`(`:139`, **手写 if 链拆首个 `--`, 全程无 argparse**)吃第 3 个 —— playwright 一层不吃。
- **判别**(按被吃位置分三种): ① 一层 `--` + 过滤参数(无 `|`) → 过滤参数落在 `_parse_args` 左侧被当自有参数, **响亮**报 `未知参数: ...(本 task 只认 --python <3.12|3.13> / --name <slug> / --full / -- <playwright 参数透传>)` 收 rc 2 —— 不是静默; ② `--grep 'A|B'` 含 `|` → 在引擎 `_shell(shell=True)` 的 /bin/sh 拼串处(任务脚本还没启动)被解析成管道, 报错形态完全不像参数问题, 极易往「spec 写错」方向排障; ③ 被吞的恰是脚本**自认旗标**(`--full`/`--name`/`--python`)才静默 —— 全量照跑/会话名错位, 只能靠耗时与会话 slug 对出来。
- **处置**: ① 透传参数写**三连 `-- -- --`**(引擎 argparse、引擎 `_extra`、任务脚本 `_parse_args` 各过一层, playwright 一层不吃)—— 注意三连只服务**纯透传**件(playwright 自认的旗标/文件路径); ② 任务脚本**自有旗标**(`--full`/`--name`/`--python`)不进透传流 —— 写在分隔符 `--` **之前、前导不加任何层**: `commands run test.linux-e2e --full -- <paths>`(引擎 REMAINDER 从 `--full` 起整体直录, 内部 `--` 保真; 实测 2026-11-15)。把它放进三连流会让 playwright 吃到 `--full` 报 `unknown option '--full'`(commander 形态), 摘掉 `--full` 又会让路径落进 `_parse_args` 左侧报 `未知参数`; ③ `--grep` 正则**避开 `|`** —— 引擎以 `shell=True` 拼串执行, `|` 在任务脚本启动前就被 /bin/sh 解析, 别指望转义; alternation 拆成多次跑, 或改用不含 `|` 的等价正则。分层事实单点: `.commands/test/config.toml` 的 `test.linux-e2e` 条目 + `.agents/skills/commands/scripts/run.py`(`extra nargs=REMAINDER` / `_extra` 前导剥离 / `_shell(shell=True)`)。
- **复发**: 2(2026-11-15 认领 issue 26-11-13-0212 复验轮: 坑档读了、三连配方也照抄了, 但把任务自有旗标 `--full` 混进透传流 —— 只对齐了「几层 `--`」没对齐判别里「被吃的是脚本自认旗标」那句; 两次容器试错各 ~15s 才回到 `--full -- <paths>` 正形; 2026-11-19 认领 issue 26-11-19-0230 轮再踩: 开工没查坑档直接拿一层/两层 `--` 试了两次才写出三连 —— 路由没到(透传用法在开工排障前, 没触发 pitfalls 检索), 试错成本两次 ~1min, 提示: 凡 `commands run test.linux-e2e` 带过滤参数, 第一直觉就该是三连 `-- -- --`)
