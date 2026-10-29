# 4155 passed + 2 skipped(根) —— mutants.verify 判据修复后的全量基线

> 摘要: `mutants.verify` 判据从「套件里有 failed 就算 KILLED」改为「本次失败 - 基线失败 差集, 且新增失败复跑复现」后的全量基线。改动面只有 `.commands/mutants/` 脚本 + 包内文档 + 知识库, `src/` 零改动。Windows 根实测 **4155 passed + 2 skipped**, 覆盖率 **99.27%**(门槛 99)。
> 基线时间: 2026-10-30 06:22

## 验收数字

`commands run test.full`(Windows 根, `-n 8` + 覆盖率闸):

| 项 | 值 |
|---|---|
| 汇总行 | `4155 passed, 2 skipped in 132.46s (0:02:12)` |
| 覆盖率 TOTAL | `21061 stmts / 99 miss / 7126 branch / 102 partial / 99%` |
| 覆盖率闸 | `Required test coverage of 99.0% reached. Total coverage: 99.27%`(平台定档后由 conftest 设值) |
| 包脚本面(`test.pkg`) | `185 passed`(含本轮新增 `.commands/mutants/scripts/test_mutants.py` 18 例) |

**Linux 侧(WSL2 `Ubuntu-26.04`, 镜像 `~/auto-qb-mut`)**: 修复前 `3 failed, 4144 passed, 10 skipped`,
修复后 **`4145 passed, 12 skipped` + `Required test coverage of 98.5% reached. Total coverage: 98.74%`**
(`commands run test.linux`, 容器 `python3.12-bookworm-slim`, 与 CI 同口径)。

修复前的 3 条失败(均已修, 见 `activeContext/26-10-30-0626-test-mutants-verify-baseline-fix.md` R1):

- `tests/test_alias_fs.py::test_win_interactive_session_station_failures` ·
  `tests/test_alias_fs.py::test_win_create_junction_kernel_failure_cleans_up` —— 两条都桩 `ctypes.WinDLL`,
  Linux 上 `ctypes` 无此属性 ⇒ `monkeypatch.setattr` 直接 AttributeError。补 `_WIN_ONLY` 标记。
- `tests/test_relocate_paths.py::test_precheck_empty_file_table_skips_representative_probe` —— 取证断言
  「src 不得被 `os.lstat`」过宽: 生产侧 `realpath_lexical` 走 `os.path.realpath`, 它在 **POSIX 上是 Python
  实现**(逐段 `os.lstat`), Windows 上走 `nt._getfinalpathname` 不碰 `os.lstat` ⇒ 同一条生产路径只在 Linux 假红。
  用例内把 `os.path.realpath` 换成恒等(取证对象是代表文件探测, 不是别名解析)。

**覆盖率闸同时改为平台定档**(`tests/conftest.py::pytest_configure`): Windows 99 / 其余 98.5 ——
Linux 侧 98.74% 永远够不到 99(差额是 Windows 独有代码), ubuntu CI 在此之前**恒红在覆盖率而非用例**。
坑档见 `pitfalls/testing/coverage-floor-platform.md`。

## 本改动面

- `.commands/mutants/scripts/mutants.py` —— `cmd_verify` 重写: ①基线感知(先量未变异套件的失败集合,
  逐条只判差集); ②去掉 `-x`(老口径会停在第一条既有失败上, 实测输出 `1 failed, 1395 passed` 即断);
  ③`-B` + `PYTHONDONTWRITEBYTECODE=1` + 开工清 `__pycache__`(防 .pyc 复用上一条变异体 ⇒ 假 SURVIVED);
  ④apply 后 `git diff --quiet -- src/` 校验变异**真的落地**(否则恒 SURVIVED); ⑤新增失败要**复跑复现**
  才算 KILLED, 复现不了记 FLAKY; ⑥单次套件 `timeout`(超时记 TIMEOUT); ⑦结果文件按输入清单定名
  (老实现带分钟戳 ⇒ 跨分钟重跑就换文件, 「已验 id 跳过」形同虚设)。
- `.commands/mutants/scripts/test_mutants.py`(新增) —— 18 例守阵: 解析 / 差集判定 / 未判定三态不落进
  SURVIVED / 全套件命令不得带 `-x`。
- `.commands/mutants/config.toml` · `.commands/mutants/references/why.md` —— `mutants.verify` 的口径与排障表同步。
- `.agents/skills/mutation-testing/SKILL.md` —— S4 判据、硬约束 10 的注记同步。
- `memory-bank/pitfalls/testing/mutmut-survived-verdict.md` —— 复发 +1, 处置 3 改写为「已修 + 守阵位置」。
- `tests/test_alias_fs.py` · `tests/test_relocate_paths.py` —— 3 条 Linux 平台失败(见上「Linux 侧」)。
- `tests/conftest.py` · `pytest.ini` —— 覆盖率闸改平台定档(99 / 98.5), 阈值从 addopts 移到 conftest 单点。
- `memory-bank/pitfalls/testing/coverage-floor-platform.md`(新增)—— 双 OS 单阈值恒红 + pytest-cov 阈值
  不能改 `config.option`(早期命名空间)两坑。

## 端到端实测(镜像 `~/auto-qb-mut`, HEAD `a00ee589`)

| 候选 | 老口径 | 新口径 |
|---|---|---|
| `config.site_presets.x__norm_domains__mutmut_3` | KILLED(假) | SURVIVED |
| `config.migrations.x__url_host__mutmut_6` | KILLED(假) | SURVIVED(另一轮曾因 flaky 判 KILLED, 复现校验未过 ⇒ 应记 FLAKY) |
| `config.migrations.x__migrate_config_1_2__mutmut_23` | KILLED(假) | SURVIVED |
| `config.writer.x_unmask_tree__mutmut_4` | KILLED | **KILLED(真, 复跑复现)** |
| 不存在的 id | SURVIVED | APPLY_FAIL |

- 基线量出 **3 条既有失败**(上列 3 条平台失败), 复用缓存 `s4-baseline-a00ee589-n8.json`。
- 单条墙时 28s(全套件 26.5-27s + 复现校验 ~1-2s), 与「~15s/条」的历史口径同量级。
