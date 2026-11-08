# 闸门"冒烟探活"会真的执行动作 (`argv or []` 吃参数)

> 摘要: `parse_args(argv or [])` 在 CLI 直跑时把真实 `sys.argv` 整个丢掉 —— 冒烟闸门加的 `--help` 被当"无参", 于是 `sync.py --help` **真跑一次同步**、`push.py --help` **真推一次推送**; 修法是 `None` 才回退 `sys.argv`(显式 `[]` 仍是测试的动作入口), 并在 `_pipeline` 展开侧加 `|--with-safety` 让无参即真动作的脚本不参与 `--help` 冒烟。
> 触发: 冒烟闸门, --help, --safety, parse_args, argv or [], 陌生参数被当无参, 闸门真跑动作, 真推送, sync.py --help, push.py --help, 探测与动作同形, `<each:>` 展开侧过滤, action-without-args

**Refs:** memory-bank/tasks/26-10-03-commands-argv-flag-swallowed.md

### 缺陷形状: `main(argv=None)` 里写 `parse_args(argv or [])`

- **触发**: 任何**直跑 CLI** 的脚本(闸门 / 手册都直接 `python <脚本> --help`); 2026-10-03 实测于
  `.commands/my-commit-flow/scripts/sync.py`。
- **判别**: `argv or []` 把两种调用方**混成一个**:
  · `main()` 裸调(CLI 直跑, `argv=None`)→ `or []` 让 argparse 拿到**空表**,
    `sys.argv[1:]` 里的 `--help` / 陌生旗标**全部被吞** ⇒ 参数校验形同不存在, 直接落到动作分支;
  · `main([])` 显式空表(测试里裸调)→ 本来就是"走动作", 语义正确。
  **症状是静默的**: `sync.py --help` 输出的是 `已同步 <hash>` 而不是 usage —— 看起来"跑通了",
  其实**同步真的发生了**; `push.py --help` 更危险(本仓库推送顺序固定, 更不该有意外推送)。
  对照: `commit.py` / `run.py` / `gen_all.py` 一直写 `parse_args(argv)`(直接吃 None 语义)⇒ 陌生旗标
  正常 `error: unrecognized arguments` + Exit 2。**同包同形状的脚本行为不一致, 就是这一处漏改。**
- **处置**: 判据写成 `None` 才回退 `sys.argv`, 两入口各留各的语义:
  ```python
  args = parser.parse_args(sys.argv[1:] if argv is None else argv)
  ```
  ⚠ 改完**必须**复核测试侧: 裸调 `main()` 从此会去读 **pytest 自己的 `sys.argv`**(用例名/`-q`/`-k`
  都会被 argparse 拒), 所以"测动作"的既有用例要显式传 `[]`; "测 CLI 入口"的新用例才 `monkeypatch.setattr(sys, "argv", [...])`。
  复发: 1 —— 2026-10-03 首次定性(`verify_ref.py` 2026-09-22 与 `sync.py` 2026-09-28 两次教训只当个案修, 没归成一类)。

### 闸门侧的第二道闸: 冒烟不该拿 `--help` 去赌"无参会不会真跑"

- **触发**: `.my-commit-flow.toml` 的脚本冒烟闸门 `<each:...> --help`(改 `.commands/` 或 `.agents/skills/` 即命中)。
- **判别**: 冒烟给脚本加的参数只有 `--help` 一种, 而 `--help` **未必被脚本认**。上面那类脚本把陌生参数
  当无参 ⇒ 冒烟 = 真执行。**光修脚本不够**: 下一个写"无参即真动作"的人还会再踩, 且是静默的。
- **处置**: 展开侧加 `|--with-safety`(`_pipeline.EACH_RE` 认 `<each:GLOB|--flag>`): 展开前先拿
  `<脚本> --safety` 探针问脚本本人 —— 慢 / 挂住 / 非 0 / 没明说 `action-without-args` 一律按不安全**摘掉**,
  摘掉数量在展开输出里**写明**(不是静默丢文件)。判据**按探针内容而非文件名规则**, 因为文件名规则会在下次改名时静默失效。
  ⚠ 探针 `subprocess` 必须钉 `stdin=DEVNULL`: 父进程是 pytest 时 stdin 是被捕获的管道, 子进程继承后
  可能挂到 10s 超时(实测整轮卡住)。
  守阵: `test_pipeline.SmokeSafetyTest`(配置里两条 `--help` run 必须带 `|--with-safety`)+ `test_sync` 的
  `test_cli_flag_reaches_main_without_running_sync` / `test_cli_unknown_flag_exits_without_action`(断言 HEAD 不动)。

### 附带发现: 无参即真动作的脚本别进 `--help` 冒烟名单

- **触发**: 新增一个"无参 = 起点动作"的脚本(如 `kb.index` 调 `gen_all.py`)。
- **判别**: `gen_all.py` 无参 = **重建全部生成物**(写文件)。给它加 `--help` 只是让 argparse 早退,
  侥幸不跑动作, 但**语义上它属于"不能靠 --help 探活"的一类**。
- **处置**: 探针答 `action-without-args` 即被安全过滤摘掉; 新增同类脚本时在**它自己的 `--safety` 分支**里
  如实声明 —— 声明处放脚本里(脚本才知道自己无参干什么), 不要往 `_pipeline` 抄一张"危险文件名清单"。
