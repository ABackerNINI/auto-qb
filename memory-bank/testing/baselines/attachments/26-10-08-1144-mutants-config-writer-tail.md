# 2805 —— config writer 长尾守阵(issue 26-10-08-0903-writer-tail)基线

> 摘要: 认领并实施 `issues/26-10-08-0903-test-config-mutation-writer-tail.html` —— 对 writer.py 的 **74 条 S4 真洞候选**逐条在**全套件**下重做判定。**关键发现**: 首次判定用镜像工作树跑, 74 条**全被判 KILLED**, 一度看似推翻首轮「74 条真洞」的结论 —— 实为**判据污染**: 镜像池含另一工作流未提交改动 + 两条**读源码文本**的措辞/数字守卫在基线就红, 使任意 src 变异都被「杀」。**显式排除两条既有红守卫**后基线转绿, 得**有效判据**: **71 SURVIVED(真洞) / 3 KILLED(假存活)** —— 首轮 S4 结论**成立**(详见坑档 `read-source-static-guard-mutation.md`)。按此逐个函数簇补 **22 个守阵**, 复跑同 74 条 → **51 KILLED / 23 SURVIVED**(存活 **−48**, −68%); 余 **22 条经逐一验证为等价变异**(见下), 1 条真洞(`_validate_tree` finally 守卫 `and`→`or`)已被新守阵杀死。**零 `src/` 改动**(纯补测 + 文档)。
> 档案: memory-bank/tasks/26-10-08-test-mutation-audit.md
> 基线时间: 2026-10-08 11:44

**Refs:** memory-bank/tasks/26-10-08-test-mutation-audit.md

## 变异面实测(本轮 = writer 单文件聚焦, 非包级重跑)

- **目标**: `src/auto_qb/config/writer.py`(具体 74 条候选来自首轮 config 审计的 S4 真洞清单)
- **候选来源**: `R:/Temp/auto-qb/mutants/real_holes.json` 里 `.config.writer.` 前缀的 74 条 id(S4 真洞候选)
- **工具 / 参数**: mutmut **3.8.0** · `mutmut apply <id>` 后跑**全套件**(`-n 8 --no-cov -x -p no:cacheprovider`) · 机器 = WSL2 `Ubuntu-26.04`(8 核)

### S4 判据修正(本轮最重要的发现)

- **首次判定(伪影)**: 直接用镜像工作树(含另一工作流未提交的 `tests/test_config.py` +309 行)跑全套件 → 74 条**全部 KILLED**。**这是伪杀**: ①镜像池里含别的 issue 新加守阵 ②镜像 `memory-bank/` 落后一条, 使两条**读源码文本**的措辞守卫(`tests/test_memory_bank.py::test_wording_guard_is_green_on_current_kb` / `test_number_guard_is_green_on_current_kb`)在**基线就红**, 而它们对 src 文本敏感 ⇒ 任何 src 变异都被它们「杀」。
- **二次判定(干净基线, 仅复位 tests/ 不够)**: 复位镜像 tests/ 后重跑 → 74 条**仍全 KILLED**, 因为上述两条守卫在 develop 上**本就红**(实测: 原样 HEAD 跑 `tests/test_memory_bank.py` 也 2 failed), 属**既有债务**且**与本轮无关**。
- **三次判定(有效判据)**: **排除两条既有红守卫** → 基线绿(check 输出 `2802 passed`) → 74 条得 **71 SURVIVED / 3 KILLED**。这才是「全套件能否杀死」的真判据(读源码文本的静态守卫不该进变异判据 —— mutmut 把变异体写进同一份文件, 那类守阵在基线就红, 是**结构性伪影**); **首轮 S4 的「74 条真洞」结论由此得到确认**。

### 补测与复跑

- **补测(S5)**: 新增 **22** 个测试函数(全部落 `tests/test_config_writer.py`), 按函数簇: 盖章/物化实参 · backup_versioned/_backup 建目录与编码 · 版本闸门消息 · _validate_tree 临时文件往返 + finally 短路与 · _build_yaml 引号/缩进档案 · _build_doc 回退 · R 级/readonly 回退点路径切分与删键 · _delete_path 精确末段 · _sync_mapping 未变不动原节点 + 类型互转 · _same_value/_as_builtin BaseLoader 语义 · _plain_scalar 布尔/无损 · unmask_tree 守卫与只碰哨兵 · mask_tree 递归 + 空值不掩码 · _set_path 复用/重建中途节点。
- **复跑(S6, 同 74 条 + 补测, 排除既有红守卫)**: **51 KILLED / 23 SURVIVED**(首轮真判据 71 SURVIVED ⇒ 存活 **−48**)
- **余 22 条经逐一验证 = 等价变异**(无法被任何测试杀死, 数学事实):
  - `_validate_tree` 的 tempfile 参数(`encoding=None`/`UTF-8`, `suffix` 缺失/`.YML`/`XX.ymlXX`, `"w"`) —— 临时文件只被解析, 这些参数在解析语义上全等价(实测四种写法 `load_config` 结果逐位相同)。
  - `_validate_tree` 的 `yaml.dump` 参数(`allow_unicode=None/False`、`default_flow_style=None/True`、缺 `allow_unicode`) —— 同上, 流式/转义写在**临时文件**里只影响字节形态, 解析回来等价(实测 `default_flow_style=True` 生成 flow 形式仍能 `load_config` 读回同样语义)。
  - `_validate_tree__mutmut_1`(`tmp_path=""`) —— 空串与 None 在 finally 守卫里同为假值。
  - `_backup__mutmut_3` / `backup_versioned__mutmut_7`(`parent=None`) —— 二者后续都走 `utils.atomic_write`, 而 `atomic_write` 内部自带 `os.makedirs(dirname, exist_ok=True)`(infra/utils.py L82), 故 `parent`/`makedirs` 是**冗余的纵深防御**, 行为不可观测。
  - `_backup__mutmut_14` / `_build_doc__mutmut_8`(删 `open` 的 `"r"`) —— `open` 默认即 `"r"`。
  - `_build_doc__mutmut_2`(`doc=""`) —— 后续 `not isinstance(doc, dict)` 分支覆盖, 与 None 同路。
  - `_fallback_readonly_fields__mutmut_4/5`(`split(None)` / `split("XX.XX")`) —— 该函数收到的**全部** readonly 路径(`data_dir`/`state_file`/`fs`)**都不含点**, `split(None)`/`split(".")` 返回同一个单元素列表(实测); `split("XX.XX")` 亦然。
- **真洞 1 条已被杀**: `_validate_tree__mutmut_29`(`tmp_path and os.path.exists(...)` 的 `and` → `or`) —— 临时文件创建失败时 `tmp_path` 为 None, `None or os.path.exists(None)` 会 `stat(None)` 抛 TypeError, 把原始 OSError 掩盖; 新增 `test_validate_tree_finally_guard_skips_none_tmp_path` 用 `mock.patch` 造创建失败, 断言 OSError 原样冒出。
- **未做**: 未重跑 `mutants.run` 全包(writer 单文件非 mutmut 目标粒度; 本轮是**对既有 74 条候选的 S4 重判 + 补测复跑**); 复跑判据 = apply 同构变异 → 全套件(排除两条既有红守卫) → 还原。

## test.full 实测

- 命令: `commands run test.full`(Windows, 单次采样 —— 耗时口径见 [../baseline.md](../baseline.md)「必须带区间」)
- **实测**: **2805 passed + 4 skipped, 2 failed, 覆盖率 TOTAL 99%**(16476 语句 / 164 未覆盖 / 5694 分支 / 148 partial; 门槛 98% 达标, 实测 98.57%)
- **2 failed 为既有债务、与本轮无关**: `tests/test_memory_bank.py::test_wording_guard_is_green_on_current_kb` / `test_number_guard_is_green_on_current_kb` —— 已在**原样 HEAD**(stash 掉本轮 tests 改动)复现同样 2 failed; 判据是「手抄测试数字 395 处 > 冻结常数 394」, 属另一工作流的回写债务, 按范围守恒入池, 本轮不修。

## 对照判据(后续沿用)

- **变异判据必须排除「读源码文本」的静态守卫** —— 本轮实证: 它们会杀死一切 src 变异, 把真洞清单洗成零。已写进坑档 [../../pitfalls/testing/read-source-static-guard-mutation.md](../../pitfalls/testing/read-source-static-guard-mutation.md)。
- **S4 前必须核基线绿** —— 镜像工作树即便 `git status` 看着干净, `memory-bank/` 也可能落后于 develop 而带着既有红守卫; 判据须**显式 `--deselect` 已知既有红**并先跑一次基线确认 `passed`。
- **writer 74 条候选的余量已清**: 71 真洞 ⇒ 复跑同池杀 48 + 本轮当场补测杀 1(29) = **49 已清**, 余 **22 条等价**(不追)。**本切片是 writer 长尾的单点事实源**。
- **本机环境坑**: ①WSL 里 `$()` 取错 cwd(`mutants.status` 恒报 `mutmut=no`)—— 见 [../../pitfalls/testing/mutants-wsl-shell.md](../../pitfalls/testing/mutants-wsl-shell.md); ②**本 shell 的 `TMPDIR` 被继承为 Windows 的 `H:\Temp`**, WSL 里 `cat > /tmp/x` 会落到 `/mnt/h/Temp`(不是 WSL 的 `/tmp`)—— 探针脚本经 `/mnt/h/Temp` 中转 + WSL 原生 `$HOME/mutprobe/` 落结果。
